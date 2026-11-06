"""Acceso a Supabase (esquema "proyectos"): guardar el estado actual + foto diaria, y reconstruir los DataFrames del CSV.

Los nombres de columna del dashboard y de calculos.py son los de los CSV; aqui solo se traducen de ida y vuelta.
Tambien llena las columnas que usa el Dashboard Value Generation (esquema "value_generation", solo vistas).
Requiere haber corrido antes value_generation.sql (crea esas columnas).
"""
import json
import math
import os
import re
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pandas as pd
from dotenv import load_dotenv

import calculos

try:                                    # el dashboard solo lee; psycopg2 se exige al conectar
    import psycopg2
except ImportError:                     # pragma: no cover
    psycopg2 = None

LOTE = 500

MAPA_PROYECTO = {
    "page_id": "proyecto_id", "Proyecto": "nombre", "Tipo de Proyecto": "tipo_proyecto", "Status": "status",
    "¿Delay?": "delay", "Propósito del Proyecto": "proposito", "Project Manager": "project_manager",
    "Product Owner": "product_owner", "Sponsor": "sponsor", "Riesgos del Delay": "riesgos_delay",
    "Plan para Mitigar Delay": "plan_mitigar_delay",
    "Start Date Proyecto Inicio": "inicio_plan", "End Date Proyecto Fin": "fin_plan",
    "Start Date Proyecto RE Inicio": "inicio_plan_re", "End Date Proyecto RE Fin": "fin_plan_re",
}
# Texto mixto: fecha -> (columna date, columna de estado)
REALES_PROYECTO = {
    "Start Date Real": ("inicio_real", "estado_inicio_real"),
    "End Date Real": ("fin_real", "estado_fin_real"),
}
FECHAS_PROYECTO = ("inicio_plan", "fin_plan", "inicio_plan_re", "fin_plan_re")

MAPA_ACTIVIDAD = {
    "page_id": "actividad_id", "Proyecto": "proyecto", "Tipo de Proyecto": "tipo_proyecto", "Actividad": "actividad",
    "Fase de Ejecución": "fase_ejecucion", "Fase Ruta": "fase_ruta", "Estado": "estado",
    "PM / Team Member": "pm_team_member", "Entregable": "entregable",
    "HH-Cost Unit": "hh_cost_unit", "HH Plan": "hh_plan", "HH Acumuladas": "hh_acumuladas",
    "HH Asignadas Hoy": "hh_asignadas_hoy",
    "Timeline Plan Inicio": "plan_inicio", "Timeline Plan Fin": "plan_fin",
    "Timeline Real Inicio": "real_inicio", "Timeline Real Fin": "real_fin",
}
NUMEROS_ACTIVIDAD = ("hh_cost_unit", "hh_plan", "hh_acumuladas", "hh_asignadas_hoy")
FECHAS_ACTIVIDAD = ("plan_inicio", "plan_fin", "real_inicio", "real_fin")

# ---- Value Generation: columnas propias. Se guardan ADEMAS en "extra", asi el
#      Dashboard de Proyectos sigue leyendo lo mismo de siempre (cargar_datos_db no cambia).
#      Un valor no interpretable se guarda NULL (no aborta la corrida).
VG_PROYECTO_TEXTO = {"Gerencia Central": "gerencia_central", "Gerencia Analizada": "gerencia_analizada",
                     "¿BC Aprobado?": "bc_aprobado"}
VG_PROYECTO_BOOL = {"¿Genera eficiencia?": "genera_eficiencia"}
VG_PROYECTO_NUM = {
    "FTE Diseño Organizacional": "fte_diseno_org", "FTE Make or Buy": "fte_make_or_buy",
    "FTE Optimización Procesos": "fte_optim_procesos", "FTE Real Optimizado": "fte_real_optimizado",
    "Total FTE Potencial": "fte_potencial_total", "Costo Benchmark $": "costo_benchmark",
    "Valorización As Is ($)": "valor_as_is_usd", "Valorización To Be ($)": "valor_to_be_usd",
    "Valorización Post-Intervencion ($)": "valor_real_post_usd",
    "Tiempo de Ciclo Inicial": "vsm_ciclo_ini", "Lead Time Inicial": "vsm_lead_ini",
    "Espera Inicial": "vsm_espera_ini", "Esfuerzo Inicial": "vsm_esfuerzo_ini",
    "Tiempo de Ciclo post-intervencion": "vsm_ciclo_post", "Lead Time post-intervencion": "vsm_lead_post",
    "Espera post-intervencion": "vsm_espera_post", "Esfuerzo post-intervencion": "vsm_esfuerzo_post",
}
COLS_VG_PROYECTO = (list(VG_PROYECTO_TEXTO.values()) + list(VG_PROYECTO_BOOL.values())
                    + list(VG_PROYECTO_NUM.values()))
# Actividad: primer nombre de Notion que traiga valor (Ruta, luego Modelo PM)
VG_ACTIVIDAD_NUM = {
    "desv_dias_plan": ("Desv Días Plan", "Desv Dias Plan"),
    "costo_plan": ("Costo Plan", "HH Plan * Cost Unit"),
    "costo_real": ("Costo Real", "HH Acum * Cost Unit"),
}
COLS_VG_ACTIVIDAD = ["base_origen"] + list(VG_ACTIVIDAD_NUM)

_MESES = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
     "november", "december"], 1)}
_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ].*)?$")
_LARGA = re.compile(r"^([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})$")


# ---------------------------------------------------------------- conexion
def url_disponible(var):
    """Valor de `var` en el entorno o en .env; None si no existe."""
    load_dotenv()
    return os.environ.get(var) or None


def conectar(solo_lectura=False, url=None):
    """Conexion psycopg2 sin autocommit. Ningun error incluye la cadena de conexion.
    `url` permite pasar la cadena ya resuelta (p. ej. desde st.secrets); si no, se lee del entorno o .env."""
    var = "SUPABASE_DB_URL_RO" if solo_lectura else "SUPABASE_DB_URL"
    url = url or url_disponible(var)
    if not url:
        raise RuntimeError(f"Falta la variable de entorno {var}")
    try:
        return psycopg2.connect(url, connect_timeout=15)
    except Exception as e:                           # psycopg2.Error o similares
        raise RuntimeError(f"No se pudo conectar a la base de datos ({type(e).__name__})") from None


# ---------------------------------------------------------------- limpieza de tipos
def _nulo(v):
    if v is None or v is pd.NA or v is pd.NaT:
        return True
    try:
        return bool(pd.isna(v))
    except (TypeError, ValueError):                  # listas, dicts...
        return False


def _fecha(v):
    """date si v es fecha ('2026-05-28', 'May 28, 2026', date, Timestamp); None si no se puede interpretar."""
    if _nulo(v):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    try:
        m = _ISO.match(s)
        if m:
            return date(int(m[1]), int(m[2]), int(m[3]))
        m = _LARGA.match(s)
        if m and m[1].lower() in _MESES:
            return date(int(m[3]), _MESES[m[1].lower()], int(m[2]))
    except ValueError:
        return None
    return None


def _fecha_estricta(v, col, id_):
    if _nulo(v) or (isinstance(v, str) and not v.strip()):
        return None
    f = _fecha(v)
    if f is None:
        raise ValueError(f"Fecha no interpretable en {col} (id {id_}): {v!r}")
    return f


def _numero(v, col, id_):
    if _nulo(v) or (isinstance(v, str) and not v.strip()):
        return None
    try:
        n = float(pd.to_numeric(v))
    except (TypeError, ValueError):
        raise ValueError(f"Numero no valido en {col} (id {id_}): {v!r}") from None
    return n if math.isfinite(n) else None


def _texto(v):
    if _nulo(v):
        return None
    return v if isinstance(v, str) else str(v)


def _numero_suave(v):
    """Como _numero pero sin abortar: vacio o no numerico -> None."""
    if _nulo(v) or (isinstance(v, str) and not v.strip()):
        return None
    try:
        n = float(pd.to_numeric(v))
    except (TypeError, ValueError):
        return None
    return n if math.isfinite(n) else None


def _booleano(v):
    """Checkbox de Notion (True/False) o texto del CSV ('True', 'Sí'...) -> bool; vacio -> False."""
    if _nulo(v):
        return False
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "1", "sí", "si", "yes")


def _texto_vacio_nulo(v):
    t = _texto(v)
    return t.strip() or None if t is not None else None


def _json_valor(v):
    """Valor JSON valido: NaN/NaT -> None, numpy -> nativo, fechas -> texto ISO."""
    if _nulo(v):
        return None
    if hasattr(v, "item") and not isinstance(v, (pd.Timestamp, str)):
        v = v.item()
    if isinstance(v, pd.Timestamp):
        return v.date().isoformat() if v == v.normalize() else v.isoformat()
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, Decimal):
        v = float(v)
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, (bool, int, str)):
        return v
    return str(v)


def _ids(df, col, tabla):
    if col not in df.columns:
        raise ValueError(f"{tabla}: falta la columna {col!r}")
    serie = df[col]
    vacios = serie.isna() | serie.astype(str).str.strip().eq("")
    if vacios.any():
        raise ValueError(f"{tabla}: {int(vacios.sum())} fila(s) sin {col}")
    rep = serie[serie.duplicated(keep=False)]
    if not rep.empty:
        raise ValueError(f"{tabla}: {col} repetido: {sorted(set(map(str, rep)))[:10]}")


# ---------------------------------------------------------------- DataFrame -> filas
def _filas_proyecto(df):
    _ids(df, "page_id", "proyectos")
    _ids(df, "Proyecto", "proyectos")      # nombre unico en la base
    conocidas = set(MAPA_PROYECTO) | set(REALES_PROYECTO)
    filas = []
    for rec in df.to_dict("records"):
        id_ = rec["page_id"]
        fila = {}
        for src, dst in MAPA_PROYECTO.items():
            v = rec.get(src)
            fila[dst] = _fecha_estricta(v, src, id_) if dst in FECHAS_PROYECTO else _texto(v)
        for src, (c_fecha, c_estado) in REALES_PROYECTO.items():
            v = rec.get(src)
            f = _fecha(v)
            fila[c_fecha] = f
            fila[c_estado] = None if f is not None or _nulo(v) or not str(v).strip() else str(v).strip()
        for src, dst in VG_PROYECTO_TEXTO.items():
            fila[dst] = _texto_vacio_nulo(rec.get(src))
        for src, dst in VG_PROYECTO_BOOL.items():
            fila[dst] = _booleano(rec.get(src))
        for src, dst in VG_PROYECTO_NUM.items():
            fila[dst] = _numero_suave(rec.get(src))
        fila["extra"] = json.dumps({c: _json_valor(v) for c, v in rec.items() if c not in conocidas},
                                   ensure_ascii=False, allow_nan=False)
        filas.append(fila)
    return filas


def _filas_actividad(df):
    _ids(df, "page_id", "actividades")
    if "Proyecto" not in df.columns or df["Proyecto"].isna().any():
        raise ValueError("actividades: toda fila necesita Proyecto")
    filas = []
    for rec in df.to_dict("records"):
        id_ = rec["page_id"]
        fila = {}
        for src, dst in MAPA_ACTIVIDAD.items():
            v = rec.get(src)
            if dst in NUMEROS_ACTIVIDAD:
                fila[dst] = _numero(v, src, id_)
            elif dst in FECHAS_ACTIVIDAD:
                fila[dst] = _fecha_estricta(v, src, id_)
            else:
                fila[dst] = _texto(v)
        fila["base_origen"] = _texto_vacio_nulo(rec.get("Base Origen"))
        for dst, fuentes in VG_ACTIVIDAD_NUM.items():
            fila[dst] = next((n for n in (_numero_suave(rec.get(s)) for s in fuentes) if n is not None), None)
        fila["extra"] = json.dumps({c: _json_valor(v) for c, v in rec.items()
                                    if c not in MAPA_ACTIVIDAD and c != "Base Origen"},
                                   ensure_ascii=False, allow_nan=False)
        filas.append(fila)
    return filas


def _acotar(v, limite=10000):
    """numeric(8,4) no admite |x| >= 10^4; un indice fuera de rango se guarda como NULL en vez de abortar."""
    if v is None or (isinstance(v, float) and not math.isfinite(v)) or abs(v) >= limite:
        return None
    return float(v)


def _foto(nombre, delay, fecha, k):
    return {
        "fecha": fecha, "proyecto": nombre,
        "progreso": _acotar(k["progreso"]), "spi": _acotar(k["spi"]), "cpi": _acotar(k["cpi"]),
        "bac": float(k["bac"]), "ac": float(k["ac"]), "ev": float(k["ev"]), "pv": float(k["pv"]),
        "actividades_total": int(k["n"]), "actividades_done": int(k["done"]),
        "entregables_total": int(k["ent_total"]), "entregables_cumplidos": int(k["ent_cumplidos"]),
        "delay": delay,
    }


def _fotos(proyectos_df, actividades_df, fecha, hoy):
    act = calculos.preparar(actividades_df)
    if "Tipo de Proyecto" in act.columns:
        act["Tipo de Proyecto"] = act["Tipo de Proyecto"].fillna("").astype(str).replace("", "Sin tipo")
    fotos = []
    for rec in proyectos_df.to_dict("records"):
        nombre = rec["Proyecto"]
        d = act[act[calculos.COL["proyecto"]] == nombre]
        k = calculos.calcular_proyecto(d, rec, hoy)
        fotos.append(_foto(nombre, _texto(rec.get("¿Delay?")), fecha, k))
    return fotos


# ---------------------------------------------------------------- SQL
def _insertar(cur, tabla, columnas, filas, jsonb=()):
    """INSERT multifila por lotes de LOTE filas."""
    cols = ", ".join(columnas)
    una = "(" + ", ".join("%s::jsonb" if c in jsonb else "%s" for c in columnas) + ")"
    for i in range(0, len(filas), LOTE):
        lote = filas[i:i + LOTE]
        sql = f"insert into {tabla} ({cols}) values " + ", ".join([una] * len(lote))
        cur.execute(sql, [f[c] for f in lote for c in columnas])


def _contar(cur, sql, params=None):
    cur.execute(sql, params)
    return int(cur.fetchone()[0])


def guardar(conn, proyectos_df, actividades_df, fecha, hoy=None):
    """Reemplaza proyecto y actividad, escribe la foto de `fecha` y registra la corrida, todo en UNA transaccion."""
    try:
        fecha_d = _fecha(fecha)
        if fecha_d is None:
            raise ValueError(f"fecha no valida: {fecha!r}")
        fecha = fecha_d
        hoy = pd.Timestamp(fecha) if hoy is None else pd.Timestamp(hoy).normalize()
        proyectos = _filas_proyecto(proyectos_df)
        actividades = _filas_actividad(actividades_df)
        fotos = _fotos(proyectos_df, actividades_df, fecha, hoy)
        cols_p = ([MAPA_PROYECTO[c] for c in MAPA_PROYECTO] + [x for p in REALES_PROYECTO.values() for x in p]
                  + COLS_VG_PROYECTO + ["extra"])
        cols_a = [MAPA_ACTIVIDAD[c] for c in MAPA_ACTIVIDAD] + COLS_VG_ACTIVIDAD + ["extra"]
        cols_f = list(fotos[0]) if fotos else []

        cur = conn.cursor()
        cur.execute("delete from proyectos.proyecto")
        cur.execute("delete from proyectos.actividad")
        _insertar(cur, "proyectos.proyecto", cols_p, proyectos, jsonb=("extra",))
        _insertar(cur, "proyectos.actividad", cols_a, actividades, jsonb=("extra",))
        cur.execute("delete from proyectos.proyecto_foto where fecha = %s", (fecha,))
        if fotos:
            _insertar(cur, "proyectos.proyecto_foto", cols_f, fotos)
        cur.execute("insert into proyectos.corrida (ok, filas_proyecto, filas_actividad) values (true, %s, %s)",
                    (len(proyectos), len(actividades)))

        en_base = {
            "proyecto": _contar(cur, "select count(*) from proyectos.proyecto"),
            "actividad": _contar(cur, "select count(*) from proyectos.actividad"),
            "proyecto_foto": _contar(cur, "select count(*) from proyectos.proyecto_foto where fecha = %s", (fecha,)),
        }
        esperado = {"proyecto": len(proyectos), "actividad": len(actividades), "proyecto_foto": len(fotos)}
        if en_base != esperado:
            raise RuntimeError(f"Los conteos no coinciden (base {en_base} vs recibidos {esperado}); se revirtio todo")
        conn.commit()
        return {"proyectos": len(proyectos), "actividades": len(actividades), "fotos": len(fotos),
                "fecha": fecha.isoformat()}
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------- base -> DataFrames
def _iso(v):
    return v.isoformat() if isinstance(v, (date, datetime)) else v


def _normalizar(df):
    """Columnas todo-nulas -> float NaN; columnas solo con numeros -> numericas (como lo infiere read_csv)."""
    for c in df.columns:
        col = df[c]
        if col.isna().all():
            df[c] = pd.Series([float("nan")] * len(df), index=df.index, dtype="float64")
        elif col.dtype == object:
            vals = col.dropna()
            if all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in vals):
                df[c] = pd.to_numeric(col)
    return df


def _expandir(filas, columnas_db, mapa, reales=None):
    inverso = {v: k for k, v in mapa.items()}
    out = []
    for fila in filas:
        r = dict(zip(columnas_db, fila))
        extra = r.pop("extra") or {}
        if isinstance(extra, str):
            extra = json.loads(extra)
        rec = {}
        for dst, v in r.items():
            if dst in inverso:
                v = _iso(v)
                rec[inverso[dst]] = float(v) if isinstance(v, Decimal) else v
        for src, (c_fecha, c_estado) in (reales or {}).items():
            rec[src] = _iso(r[c_fecha]) if r[c_fecha] is not None else r[c_estado]
        rec.update(extra)
        out.append(rec)
    return _normalizar(pd.DataFrame(out))


def cargar_datos_db(conn):
    """(actividades_df, proyectos_df) con los nombres de columna exactos de los CSV originales."""
    cur = conn.cursor()
    cols_p = list(MAPA_PROYECTO.values()) + [x for p in REALES_PROYECTO.values() for x in p] + ["extra"]
    cols_a = list(MAPA_ACTIVIDAD.values()) + ["extra"]
    cur.execute(f"select {', '.join(cols_p)} from proyectos.proyecto order by nombre")
    proyectos = _expandir(cur.fetchall(), cols_p, MAPA_PROYECTO, REALES_PROYECTO)
    cur.execute(f"select {', '.join(cols_a)} from proyectos.actividad order by proyecto, plan_inicio, actividad_id")
    actividades = _expandir(cur.fetchall(), cols_a, MAPA_ACTIVIDAD)
    return actividades, proyectos


def ultima_corrida(conn):
    """datetime (con zona) de la ultima corrida correcta, o None."""
    cur = conn.cursor()
    cur.execute("select max(ejecutado_en) from proyectos.corrida where ok")
    fila = cur.fetchone()
    return fila[0] if fila else None


# ---------------------------------------------------------------- CSV
def _leer_csv(carpeta):
    proy = pd.read_csv(os.path.join(carpeta, "proyectos.csv"), encoding="utf-8-sig")
    act = pd.read_csv(os.path.join(carpeta, "actividades_pm.csv"), encoding="utf-8-sig")
    return proy, act


def hoy_lima():
    return datetime.now(ZoneInfo("America/Lima")).date()


def migrar_csv(conn, carpeta="data", fecha=None):
    """Carga los dos CSV a la base (guardar) y devuelve los conteos."""
    proy, act = _leer_csv(carpeta)
    return guardar(conn, proy, act, fecha or hoy_lima())


def verificar(conn, carpeta="data"):
    """Compara filas y sumas de HH entre los CSV y la base."""
    proy, act = _leer_csv(carpeta)
    cur = conn.cursor()
    cur.execute("select count(*) from proyectos.proyecto")
    n_p = int(cur.fetchone()[0])
    cur.execute("select count(*), coalesce(sum(hh_plan), 0), coalesce(sum(hh_acumuladas), 0) from proyectos.actividad")
    n_a, hh_plan, hh_acum = cur.fetchone()
    suma = lambda c: float(pd.to_numeric(act[c], errors="coerce").fillna(0).sum())  # noqa: E731
    filas = [
        ("Filas proyectos", len(proy), n_p),
        ("Filas actividades", len(act), int(n_a)),
        ("HH Plan", suma("HH Plan"), float(hh_plan)),
        ("HH Acumuladas", suma("HH Acumuladas"), float(hh_acum)),
    ]
    df = pd.DataFrame(filas, columns=["Concepto", "CSV", "Base"])
    df["Coincide"] = (df["CSV"] - df["Base"]).abs() < 0.01
    return df


if __name__ == "__main__":              # python db.py verificar | migrar
    import sys
    accion = sys.argv[1] if len(sys.argv) > 1 else "verificar"
    c = conectar()
    try:
        if accion == "migrar":
            print(migrar_csv(c))
        else:
            print(verificar(c).to_string(index=False))
    finally:
        c.close()
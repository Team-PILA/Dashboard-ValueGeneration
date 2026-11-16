"""Dashboard Value Generation (Streamlit).

Secrets (Streamlit Cloud > Settings > Secrets; nunca en el repo):
    APP_USUARIO, APP_CLAVE      login (acceso.py)
    SUPABASE_DB_URL_RO          URL de Postgres con el rol vg_dashboard_ro
    ESQUEMA                     opcional: "value_generation" (por defecto) o "vg_demo" (datos de prueba)
Local:  streamlit run app.py   (con .streamlit/secrets.toml, que está en .gitignore)
"""
from __future__ import annotations

import html
import os

import pandas as pd
import streamlit as st

import fuente
import kpis
from acceso import exigir_acceso

st.set_page_config(page_title="Value Generation", page_icon="📈", layout="wide")
exigir_acceso()


def _secreto(nombre: str, defecto: str = "") -> str:
    try:
        v = st.secrets[nombre]
    except Exception:  # noqa: BLE001
        v = None
    return str(v) if v not in (None, "") else os.environ.get(nombre, defecto)


ESQUEMA = _secreto("ESQUEMA", "value_generation")

COLORES = {  # paleta del whiteboard
    "verde_fuerte": "#9FE2BF", "verde": "#CDE8A8", "azul": "#A9B8F8",
    "morado": "#CDA8DE", "salmon": "#F7C0A0", "gris": "#ECECEC",
}

st.markdown("""
<style>
.vg-card{border-radius:10px;padding:14px 16px;margin-bottom:12px;color:#1d1d1f;
         border:1px solid rgba(0,0,0,.12);text-align:center}
.vg-card .t{font-size:.85rem;font-weight:600;line-height:1.2}
.vg-card .v{font-size:1.7rem;font-weight:700;margin-top:6px;line-height:1.15}
.vg-card .s{font-size:.75rem;margin-top:4px;opacity:.75}
.vg-card.big .v{font-size:2.6rem}
.vg-card.pend .v{font-size:1rem;font-weight:600;opacity:.6}
.vg-sec{font-weight:700;text-align:center;margin:0}
.vg-sec-sub{font-size:.75rem;text-align:center;opacity:.7;margin-bottom:10px}
.vg-ger{font-size:.95rem;font-weight:600;text-align:center;padding:8px;border-radius:8px;
        border:1px solid rgba(0,0,0,.12);background:#F5EEFA;color:#1d1d1f;margin-bottom:12px}
.vg-nota{font-size:.72rem;text-align:center;opacity:.75;margin:-6px 0 10px}
</style>""", unsafe_allow_html=True)


def card(titulo: str, valor: str, sub: str | None = None, color: str = "gris",
         grande: bool = False, pendiente: bool = False) -> None:
    clases = "vg-card" + (" big" if grande else "") + (" pend" if pendiente else "")
    sub_html = f'<div class="s">{html.escape(sub).replace(chr(10), "<br>")}</div>' if sub else ""
    st.markdown(
        f'<div class="{clases}" style="background:{COLORES[color]}">'
        f'<div class="t">{html.escape(titulo)}</div><div class="v">{html.escape(valor)}</div>{sub_html}</div>',
        unsafe_allow_html=True)


def por_definir(titulo: str, color: str) -> None:
    card(titulo, "Por definir", color=color, pendiente=True)


@st.cache_data(ttl=600, show_spinner="Cargando datos…")
def cargar(esquema: str) -> dict | None:
    url = _secreto("SUPABASE_DB_URL_RO")
    if not url:
        return None
    try:
        return fuente.leer(url, esquema)
    except Exception:  # nunca se muestra el motivo (podría incluir datos de conexión)
        return None


datos = cargar(ESQUEMA)
if datos is None:
    st.error("No se pudo leer la base de datos. Revisa los secrets de la app.")
    st.stop()

# ---------------------------------------------------------------- encabezado + filtros
c_tit, c_anio, c_gc = st.columns([3.2, 1, 1.3])
with c_tit:
    st.markdown("<h1 style='color:#0B63C4;margin-bottom:0'>VALUE GENERATION</h1>", unsafe_allow_html=True)
    if ESQUEMA == "vg_demo":
        st.warning("Datos de prueba (vg_demo). No son datos reales.")
with c_anio:
    anios = kpis.anios_disponibles(datos["kpi"])
    opcion = st.selectbox("Filtrar por año", ["Todos"] + anios, help="Según Start Date Real")
with c_gc:
    gcs = st.multiselect("Filtrar por GC", kpis.gerencias_disponibles(datos["gerencias"]),
                         placeholder="Todas", help="Proyectos que impactan alguna de las GC elegidas")
anio = None if opcion == "Todos" else int(opcion)

kpi_df, ger_df = kpis.filtrar(datos["kpi"], datos["gerencias"], anio, gcs)
r = kpis.calcular(kpi_df, ger_df)

if r["proyectos"] == 0:
    st.info("No hay proyectos con «¿Genera eficiencia?» marcado para este filtro.")
    st.stop()


def tabla(columnas: dict, formatos: dict) -> None:
    """Tabla de desglose por proyecto con las columnas {origen: título} del DataFrame filtrado."""
    t = kpi_df[[c for c in columnas if c in kpi_df.columns]].rename(columns=columnas)
    st.dataframe(t, hide_index=True, width="stretch",
                 column_config={c: st.column_config.NumberColumn(format=f) for c, f in formatos.items()})


# ---------------------------------------------------------------- fila superior
izq, der = st.columns([3.3, 2], gap="medium")
with izq:
    a, b, c = st.columns(3)
    with a:
        card("% Accuracy", kpis.fmt_pct(r["pct_real_vs_potencial"]),
             f"Ahorro Real / Ahorro Potencial · {r['proyectos_con_real']} proyecto(s) con ahorro real",
             color="verde_fuerte")
    with b:
        card("AHORRO REAL [USD]", kpis.fmt_usd(r["ahorro_real"]), color="morado")
    with c:
        card("AHORRO POTENCIAL [USD]", kpis.fmt_usd(r["ahorro_usd"]),
             f"{r['proyectos_con_valorizacion']} proyecto(s) con valorización", color="morado")
    d, e = st.columns(2)
    with d:
        card("Tiempo promedio de diagnóstico",
             "Sin datos" if r["diag_promedio_dias"] is None else f"{r['diag_promedio_dias']:.0f} días",
             "Días calendario", color="verde")
    with e:
        card("Diagnósticos cerrados / prometidos", f"{r['diag_cerrados']} / {r['diag_prometidos']}",
             color="verde")
with der:
    card("# Total de Intervenciones", str(r["intervenciones"]),
         "Proyectos marcados con «¿Genera eficiencia?»", color="morado")
    detalle = "  |  ".join(f"{g}: {n}" for g, n in r["por_gerencia"].items()) or "Sin gerencias"
    st.markdown(f'<div class="vg-ger">{html.escape(detalle)}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- tres secciones
s1, s2, s3 = st.columns(3, gap="medium")

with s1, st.container(border=True):
    st.markdown('<p class="vg-sec">Análisis con Impacto Organizacional</p>'
                '<p class="vg-sec-sub">[FTE vs. HC]</p>', unsafe_allow_html=True)
    f1, f2 = st.columns(2)
    with f1:
        card("Total FTEs Potenciales", kpis.fmt_num(r["fte_potencial"]), color="salmon")
    with f2:
        card("FTE Reales", kpis.fmt_num(r["fte_real"]), color="morado")
    tabla({"proyecto": "Proyecto", "fte_potencial_total": "Total FTE Potencial", "fte_real": "FTE Real"},
          {"Total FTE Potencial": "%.1f", "FTE Real": "%.1f"})

with s2, st.container(border=True):
    st.markdown('<p class="vg-sec">Inhousing: Impacto en Gasto OPEX</p>'
                '<p class="vg-sec-sub">[Servicio Tercero vs. PI]</p>', unsafe_allow_html=True)
    card("Costo Evitado ante consultoras [USD]", kpis.fmt_usd(r["costo_evitado"]),
         f"Consultora {kpis.fmt_usd(r['costo_benchmark'])} − Proyecto PI {kpis.fmt_usd(r['costo_real_pi'])}",
         color="salmon")
    kpi_df = kpi_df.assign(
        _costo_evitado=pd.to_numeric(kpi_df.get("costo_benchmark"), errors="coerce")
        - pd.to_numeric(kpi_df.get("costo_evitado_usd"), errors="coerce"))
    tabla({"proyecto": "Proyecto", "alcance_e2e": "Alcance E2E del proyecto",
           "costo_evitado_usd": "Costo proyecto PI", "costo_benchmark": "Costo serv. con 3ro",
           "_costo_evitado": "Costo evitado"},
          {c: "$ %.0f" for c in ("Costo proyecto PI", "Costo serv. con 3ro", "Costo evitado")})

with s3, st.container(border=True):
    st.markdown('<p class="vg-sec">Optimización interna de Procesos</p>'
                '<p class="vg-sec-sub">[Calidad vs. Velocidad]</p>', unsafe_allow_html=True)
    o1, o2 = st.columns(2)
    with o1:
        card("FTE Total REALES", kpis.fmt_num(r["fte_impacto_real"]),
             f"{kpis.fmt_num(r['impacto_hrs_real'], 0)} hrs/mes" if r["impacto_hrs_real"] is not None else None,
             color="morado")
    with o2:
        card("FTE Total POTENCIALES", kpis.fmt_num(r["fte_impacto_potencial"]),
             f"{kpis.fmt_num(r['impacto_hrs_potencial'], 0)} hrs/mes" if r["impacto_hrs_potencial"] is not None
             else None, color="salmon")
    st.markdown(f'<p class="vg-nota">1 FTE = {kpis.HORAS_FTE_MES} horas mensuales</p>', unsafe_allow_html=True)
    tabla({"proyecto": "Proyecto", "servicio_requerido": "Servicio Requerido",
           "vsm_lead_ini": "Lead Time As Is (h)", "vsm_lead_post": "Lead Time To Be (h)",
           "impacto_hrs_potencial": "Impacto Potencial (h)", "impacto_hrs_real": "Impacto Real (h)"},
          {c: "%.0f" for c in ("Lead Time As Is (h)", "Lead Time To Be (h)",
                                "Impacto Potencial (h)", "Impacto Real (h)")})

corrida = datos["corrida"]
st.caption("Datos al corte: " + (corrida.strftime("%d/%m/%Y %H:%M") if corrida else "sin registro")
           + " · Se actualiza lun-vie 8:30 y 17:30 (Lima)")
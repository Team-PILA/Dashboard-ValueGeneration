"""Dashboard Value Generation (Streamlit).

Secrets (Streamlit Cloud > Settings > Secrets; nunca en el repo):
    APP_USUARIO, APP_CLAVE      login (acceso.py)
    SUPABASE_DB_URL_RO          URL de Postgres con el rol vg_dashboard_ro
    ESQUEMA                     opcional: "value_generation" (por defecto) o "vg_demo" (datos de prueba)
Local:  streamlit run app.py   (con .streamlit/secrets.toml, que está en .gitignore)
"""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st

import fuente
import kpis
import ui
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

st.markdown(ui.CSS, unsafe_allow_html=True)


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
c_tit, c_anio, c_gc = st.columns([3.2, 1, 1.4], vertical_alignment="center")
with c_tit:
    st.markdown(ui.encabezado("Value Generation",
                              "Portafolio de iniciativas de eficiencia – Impacto y avance"), unsafe_allow_html=True)
with c_anio:
    anios = kpis.anios_disponibles(datos["kpi"])
    opcion = st.selectbox("Filtrar por año", ["Todos"] + anios, help="Según Start Date Real")
with c_gc:
    gcs = st.multiselect("Filtrar por GC", kpis.gerencias_disponibles(datos["gerencias"]),
                         placeholder="Todas", help="Proyectos de las GC elegidas")
anio = None if opcion == "Todos" else int(opcion)
if ESQUEMA == "vg_demo":
    st.info("Datos de prueba (vg_demo). No son datos reales.")

kpi_df, ger_df = kpis.filtrar(datos["kpi"], datos["gerencias"], anio, gcs)
r = kpis.calcular(kpi_df, ger_df)

if r["proyectos"] == 0:
    st.info("No hay proyectos con «¿Genera eficiencia?» marcado para este filtro.")
    st.stop()


def html_(fragmento: str) -> None:
    st.markdown(fragmento, unsafe_allow_html=True)


def tabla(columnas: dict, formatos: dict) -> None:
    """Desglose por proyecto: {columna origen: título}; números con formato y vacíos como «—»."""
    t = kpi_df[[c for c in columnas if c in kpi_df.columns]].rename(columns=columnas)
    for c, f in formatos.items():
        if c in t:
            t[c] = pd.to_numeric(t[c], errors="coerce").map(lambda v, f=f: "—" if pd.isna(v) else f.format(v))
    for c in t.columns:
        if c not in formatos:
            t[c] = t[c].map(lambda v: "—" if v is None or (isinstance(v, float) and pd.isna(v))
                            or (isinstance(v, str) and not v.strip()) else v)
    st.dataframe(t, hide_index=True, width="stretch")


USD = "$ {:,.0f}"

# ---------------------------------------------------------------- KPIs principales
k1, k2, k3, k4 = st.columns([1, 1.45, 1, 1], gap="small")
with k1:
    html_(ui.hero("% Accuracy", kpis.fmt_pct(r["pct_real_vs_potencial"]),
                  f"Ahorro Real / Ahorro Potencial · {r['proyectos_con_real']} proyecto(s) con ahorro real",
                  "diana", "azul"))
with k2:
    html_(ui.hero("Ahorro Real [USD]", kpis.fmt_usd(r["ahorro_real"]), None, "monedas", "morado", grande=True))
with k3:
    html_(ui.hero("Ahorro Potencial [USD]", kpis.fmt_usd(r["ahorro_usd"]),
                  f"{r['proyectos_con_valorizacion']} proyecto(s) con valorización", "tendencia", "indigo"))
with k4:
    html_(ui.hero("# Total de Intervenciones", str(r["intervenciones"]),
                  "Proyectos marcados con «¿Genera eficiencia?»", "capas", "plomo"))

t1, t3 = st.columns([2, 1.45], gap="small")
with t1:
    html_(ui.diagnostico(
        "Sin datos" if r["diag_promedio_dias"] is None else f"{r['diag_promedio_dias']:.0f} días",
        r["diag_cerrados"], r["diag_prometidos"]))
with t3:
    html_(ui.gerencias(r["por_gerencia"]))

# ---------------------------------------------------------------- tres secciones
s1, s2, s3 = st.columns(3, gap="medium")

with s1, st.container(border=True, key="sec_org"):
    html_(ui.seccion("Análisis con Impacto Organizacional", "[FTE vs. HC]", "personas", "morado"))
    f1, f2 = st.columns(2, gap="small")
    with f1:
        html_(ui.metrica("Total FTEs Potenciales", kpis.fmt_num(r["fte_potencial"]), None, "tendencia", "azul"))
    with f2:
        html_(ui.metrica("FTE Reales", kpis.fmt_num(r["fte_real"]), None, "check", "morado"))
    tabla({"proyecto": "Proyecto", "fte_potencial_total": "Total FTE Potencial", "fte_real": "FTE Real"},
          {"Total FTE Potencial": "{:,.1f}", "FTE Real": "{:,.1f}"})

with s2, st.container(border=True, key="sec_inh"):
    html_(ui.seccion("Inhousing: Impacto en Gasto OPEX", "[Servicio Tercero vs. PI]", "intercambio", "azul"))
    html_(ui.metrica("Costo Evitado ante consultoras [USD]", kpis.fmt_usd(r["costo_evitado"]),
                     (f"Consultora {kpis.fmt_usd(r['costo_benchmark'])} − Proyecto PI {kpis.fmt_usd(r['costo_real_pi'])}"
                      if r["costo_evitado"] is not None else "Falta cargar horas reales en las actividades"),
                     "billete", "azul"))
    _pi = pd.to_numeric(kpi_df.get("costo_evitado_usd"), errors="coerce")
    kpi_df = kpi_df.assign(   # sin horas cargadas (costo PI = 0) no hay costo evitado que mostrar
        _costo_evitado=(pd.to_numeric(kpi_df.get("costo_benchmark"), errors="coerce") - _pi).where(_pi > 0))
    tabla({"proyecto": "Proyecto", "servicio_requerido": "Servicio Requerido",
           "costo_evitado_usd": "Costo proyecto PI", "costo_benchmark": "Costo serv. con 3ro",
           "_costo_evitado": "Costo evitado"},
          {c: USD for c in ("Costo proyecto PI", "Costo serv. con 3ro", "Costo evitado")})

with s3, st.container(border=True, key="sec_opt"):
    html_(ui.seccion("Optimización interna de Procesos", "[Calidad vs. Velocidad]", "engranaje", "plomo"))
    o1, o2 = st.columns(2, gap="small")
    with o1:
        html_(ui.metrica("FTE Total REALES", kpis.fmt_num(r["fte_impacto_real"]),
                         f"{kpis.fmt_num(r['impacto_hrs_real'], 0)} horas" if r["impacto_hrs_real"] is not None
                         else None, "reloj", "morado"))
    with o2:
        html_(ui.metrica("FTE Total POTENCIALES", kpis.fmt_num(r["fte_impacto_potencial"]),
                         f"{kpis.fmt_num(r['impacto_hrs_potencial'], 0)} horas"
                         if r["impacto_hrs_potencial"] is not None else None, "rayo", "azul"))
    html_(ui.nota(f"1 FTE = {kpis.HORAS_FTE_MES} horas (equivalencia referencial)"))
    tabla({"proyecto": "Proyecto", "alcance_e2e": "Alcance E2E del proyecto",
           "vsm_lead_ini": "Lead Time As Is (días)", "vsm_lead_post": "Lead Time To Be (días)",
           "impacto_hrs_potencial": "Impacto Potencial (h)", "impacto_hrs_real": "Impacto Real (h)"},
          {"Lead Time As Is (días)": "{:,.2f}", "Lead Time To Be (días)": "{:,.2f}",
           "Impacto Potencial (h)": "{:,.0f}", "Impacto Real (h)": "{:,.0f}"})

corrida = datos["corrida"]
st.caption("Datos al corte: " + (corrida.strftime("%d/%m/%Y %H:%M") if corrida else "sin registro")
           + " · Se actualiza lun-vie 8:30 y 17:30 (Lima)")
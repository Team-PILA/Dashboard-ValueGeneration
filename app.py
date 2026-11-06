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
</style>""", unsafe_allow_html=True)


def card(titulo: str, valor: str, sub: str | None = None, color: str = "gris",
         grande: bool = False, pendiente: bool = False) -> None:
    clases = "vg-card" + (" big" if grande else "") + (" pend" if pendiente else "")
    sub_html = f'<div class="s">{html.escape(sub)}</div>' if sub else ""
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

# ---------------------------------------------------------------- encabezado + filtro
c_tit, c_fil = st.columns([4, 1])
with c_tit:
    st.markdown("<h1 style='color:#0B63C4;margin-bottom:0'>VALUE GENERATION</h1>", unsafe_allow_html=True)
    if ESQUEMA == "vg_demo":
        st.warning("Datos de prueba (vg_demo). No son datos reales.")
with c_fil:
    anios = kpis.anios_disponibles(datos["kpi"])
    opcion = st.selectbox("Filtrar por año", ["Todos"] + anios, help="Según Start Date Real")
anio = None if opcion == "Todos" else int(opcion)

kpi_df, ger_df = kpis.filtrar(datos["kpi"], datos["gerencias"], anio)
r = kpis.calcular(kpi_df, ger_df)

if r["proyectos"] == 0:
    st.info("No hay proyectos con «¿Genera eficiencia?» marcado para este filtro.")
    st.stop()

# ---------------------------------------------------------------- layout del whiteboard
izq, der = st.columns([1.25, 3.75], gap="medium")

with izq:
    card("% [Monto Real vs. Potencial]", kpis.fmt_pct(r["pct_real_vs_potencial"]),
         (f"Real {kpis.fmt_usd(r['ahorro_real'])} de {kpis.fmt_usd(r['ahorro_potencial_cerrados'])} potencial "
          f"({r['proyectos_con_real']} proyecto(s) con valorización real)")
         if r["proyectos_con_real"] else "Aún sin valorización real post-intervención",
         color="verde_fuerte", grande=True)
    card("Tiempo promedio de diagnóstico",
         "Sin datos" if r["diag_promedio_dias"] is None else f"{r['diag_promedio_dias']:.0f} días",
         f"Días calendario · {r['diag_cerrados']} diagnóstico(s) cerrado(s)", color="verde")
    card("% de entregables cumplidos a la fecha", kpis.fmt_pct(r["pct_entregables_en_fecha"]), color="verde")
    por_definir("% WIP en prioridades vigentes", "azul")
    dias = fuente.meta(datos["umbral"], "diag_timebox_dias")
    st.caption(f"Lead Time estándar: {int(dias)} días hábiles" if dias else "Lead Time estándar: por definir")
    card("% Business case aprobados", kpis.fmt_pct(r["pct_bc_aprobados"]),
         f"{r['bc_aprobados']} de {r['bc_presentados']} presentados", color="azul")
    por_definir("Benefit sustainability rate", "azul")

with der:
    a, b, c = st.columns([2, 1, 2.4])
    with a:
        card("AHORRO POTENCIAL [USD]", kpis.fmt_usd(r["ahorro_usd"]),
             f"{r['proyectos_con_valorizacion']} proyecto(s) con valorización", color="morado")
    with b:
        card("FTE", kpis.fmt_num(r["fte_potencial"]), f"Real optimizado: {kpis.fmt_num(r['fte_real'])}",
             color="morado")
    with c:
        card("# Total de Intervenciones", str(r["intervenciones"]), f"{r['proyectos']} proyecto(s)",
             color="morado")
        detalle = "  |  ".join(f"{g}: {n}" for g, n in r["por_gerencia"].items()) or "Sin gerencias"
        st.markdown(f'<div class="vg-ger">{html.escape(detalle)}</div>', unsafe_allow_html=True)

    s1, s2, s3 = st.columns(3)
    with s1, st.container(border=True):
        st.markdown('<p class="vg-sec">Análisis con Impacto Organizacional</p>'
                    '<p class="vg-sec-sub">[FTE vs. HC]</p>', unsafe_allow_html=True)
        card("FTE Identificados", kpis.fmt_num(r["fte_diseno_org"]), "FTE Diseño Organizacional",
             color="salmon", grande=True)
    with s2, st.container(border=True):
        st.markdown('<p class="vg-sec">Inhousing: Impacto en Gasto OPEX</p>'
                    '<p class="vg-sec-sub">[Servicio Tercero vs. PI]</p>', unsafe_allow_html=True)
        card("USD Costo Evitado", kpis.fmt_usd(r["costo_evitado"]),
             f"Consultora {kpis.fmt_usd(r['costo_benchmark'])} − PI {kpis.fmt_usd(r['costo_real_pi'])}",
             color="salmon", grande=True)
        card("USD [Promedio de Consultoría]", kpis.fmt_usd(r["promedio_consultoria"]), color="salmon")
    with s3, st.container(border=True):
        st.markdown('<p class="vg-sec">Optimización interna de Procesos</p>'
                    '<p class="vg-sec-sub">[Calidad vs. Velocidad]</p>', unsafe_allow_html=True)
        p1, p2 = st.columns(2)
        with p1:
            por_definir("# Procesos Analizados", "salmon")
        with p2:
            por_definir("FTE Impactos para Calidad", "salmon")
        sub = (f"{kpis.fmt_num(r['lead_ini'], 0)} → {kpis.fmt_num(r['lead_post'], 0)} "
               f"({r['proyectos_con_vsm']} proyecto(s) con VSM)") if r["lead_ini"] is not None else None
        card("Reducción Lead Time", kpis.fmt_pct(r["pct_reduccion_lead"]), sub, color="salmon")

# ---------------------------------------------------------------- detalle
with st.expander("Detalle por proyecto"):
    cols = {
        "proyecto": "Proyecto", "tipo_proyecto": "Tipo", "anio": "Año", "gerencia_central": "Gerencia",
        "pct_entregables_en_fecha": "% entregables", "diag_dias": "Días diagnóstico",
        "ahorro_potencial_usd": "Ahorro potencial USD", "ahorro_real_usd": "Ahorro real USD",
        "pct_real_vs_potencial": "% Real vs Pot.",
        "pct_reduccion_lead_time": "% Red. Lead Time", "bc_aprobado": "¿BC Aprobado?",
    }
    tabla = kpi_df[[c for c in cols if c in kpi_df.columns]].rename(columns=cols)
    pcts = ("% entregables", "% Real vs Pot.", "% Red. Lead Time")
    for c in pcts:
        if c in tabla:
            tabla[c] = pd.to_numeric(tabla[c], errors="coerce") * 100
    st.dataframe(
        tabla, hide_index=True, use_container_width=True,
        column_config={c: st.column_config.NumberColumn(format="%.1f %%") for c in pcts}
        | {c: st.column_config.NumberColumn(format="$ %.0f") for c in ("Ahorro potencial USD", "Ahorro real USD")}
        | {"Año": st.column_config.NumberColumn(format="%d"),
           "Días diagnóstico": st.column_config.NumberColumn(format="%d")})

corrida = datos["corrida"]
st.caption("Datos al corte: " + (corrida.strftime("%d/%m/%Y %H:%M") if corrida else "sin registro")
           + " · Se actualiza lun-vie 8:30 y 17:30 (Lima)")
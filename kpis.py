"""Cálculo de los indicadores del dashboard a partir de las vistas de Supabase.

Sin streamlit ni base de datos, para poder probarlo con pytest.
Regla: los totales del portafolio son SUMA / SUMA (nunca promedio de porcentajes) y
solo cuentan los proyectos que tienen los dos datos del cociente.
"""
from __future__ import annotations

import math

import pandas as pd

ORDEN_GERENCIAS = ["GCO", "GCC", "GCAF", "GDSO", "GCDSO", "GG"]


def _num(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series([float("nan")] * len(df), index=df.index, dtype="float64")
    return pd.to_numeric(df[col], errors="coerce")


def _bool(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series([False] * len(df), index=df.index)
    return df[col].fillna(False).astype(bool)


def ratio(num, den):
    """num/den o None si no hay denominador válido."""
    if num is None or den is None:
        return None
    try:
        if math.isnan(num) or math.isnan(den) or den == 0:
            return None
    except TypeError:
        return None
    return float(num) / float(den)


def _suma(serie: pd.Series):
    """Suma o None si todos son nulos (para mostrar 'Sin datos' en vez de 0)."""
    s = serie.dropna()
    return float(s.sum()) if not s.empty else None


def anios_disponibles(kpi: pd.DataFrame) -> list[int]:
    if kpi.empty or "anio" not in kpi.columns:
        return []
    return sorted({int(a) for a in _num(kpi, "anio").dropna()}, reverse=True)


def filtrar(kpi: pd.DataFrame, gerencias: pd.DataFrame, anio: int | None):
    """anio=None -> todos los años (incluye proyectos sin Start Date Real)."""
    if anio is None:
        return kpi, gerencias
    k = kpi[_num(kpi, "anio") == anio]
    g = gerencias[_num(gerencias, "anio") == anio] if not gerencias.empty else gerencias
    return k, g


def calcular(kpi: pd.DataFrame, gerencias: pd.DataFrame) -> dict:
    """Todos los indicadores del dashboard para el conjunto ya filtrado."""
    r: dict = {"proyectos": int(len(kpi))}

    # --- Valor en USD
    #     potencial = As Is − To Be ; real = As Is − Real post-intervención
    as_is, to_be = _num(kpi, "valor_as_is_usd"), _num(kpi, "valor_to_be_usd")
    real_post = _num(kpi, "valor_real_post_usd")
    m = as_is.notna() & to_be.notna()
    r["ahorro_usd"] = _suma((as_is - to_be)[m])                 # tarjeta AHORRO POTENCIAL
    r["proyectos_con_valorizacion"] = int(m.sum())
    # % Real vs Potencial: solo proyectos que ya tienen los 3 valores
    mr = m & real_post.notna()
    r["ahorro_potencial_cerrados"] = _suma((as_is - to_be)[mr])
    r["ahorro_real"] = _suma((as_is - real_post)[mr])
    r["pct_real_vs_potencial"] = ratio(r["ahorro_real"], r["ahorro_potencial_cerrados"])
    r["proyectos_con_real"] = int(mr.sum())

    # --- Tiempo de diagnóstico (días calendario, solo diagnósticos cerrados)
    dias = _num(kpi, "diag_dias").dropna()
    r["diag_promedio_dias"] = float(dias.mean()) if not dias.empty else None
    r["diag_cerrados"] = int(len(dias))

    # --- FTE
    r["fte_potencial"] = _suma(_num(kpi, "fte_potencial_total"))
    r["fte_real"] = _suma(_num(kpi, "fte_real_optimizado"))
    r["fte_diseno_org"] = _suma(_num(kpi, "fte_diseno_org"))
    r["fte_make_or_buy"] = _suma(_num(kpi, "fte_make_or_buy"))
    r["fte_optim_procesos"] = _suma(_num(kpi, "fte_optim_procesos"))

    # --- Intervenciones por gerencia central
    if gerencias.empty:
        r["intervenciones"] = 0
        r["por_gerencia"] = {}
    else:
        cuenta = gerencias["gerencia"].value_counts()
        orden = [g for g in ORDEN_GERENCIAS if g in cuenta.index] + sorted(
            g for g in cuenta.index if g not in ORDEN_GERENCIAS)
        r["intervenciones"] = int(len(cuenta))
        r["por_gerencia"] = {g: int(cuenta[g]) for g in orden}

        print("========== DEBUG GERENCIAS ==========", flush=True)

        print("Cantidad de registros:", len(gerencias), flush=True)

        print("Datos de gerencias:", flush=True)
        print(gerencias.to_string(), flush=True)

        if gerencias.empty:
            r["intervenciones"] = 0
            r["por_gerencia"] = {}
        else:
            cuenta = gerencias["gerencia"].value_counts()

            print("Cuenta por gerencia:", len(cuenta), flush=True)
            print("Detalle:", cuenta.to_dict(), flush=True)

            # Resto de tu código

    # --- Ejecución
    r["pct_entregables_en_fecha"] = ratio(_num(kpi, "entregables_en_fecha").sum(),
                                          _num(kpi, "entregables_comprometidos").sum())

    # --- Business cases ("En evaluación" y "No aplica" no cuentan)
    presentados, aprobados = int(_bool(kpi, "bc_presentado").sum()), int(_bool(kpi, "bc_ok").sum())
    r["bc_presentados"], r["bc_aprobados"] = presentados, aprobados
    r["pct_bc_aprobados"] = ratio(aprobados, presentados)

    # --- Inhousing: costo de consultora (benchmark) vs costo real del equipo PI
    bench, costo_pi = _num(kpi, "costo_benchmark"), _num(kpi, "costo_evitado_usd")  # en la vista = Σ Costo Real PI
    mb = bench.notna() & costo_pi.notna()
    r["costo_benchmark"] = _suma(bench[mb])
    r["costo_real_pi"] = _suma(costo_pi[mb])
    r["costo_evitado"] = _suma((bench - costo_pi)[mb])
    r["promedio_consultoria"] = float(bench.dropna().mean()) if bench.notna().any() else None

    # --- Lead time (VSM): solo proyectos con inicial y post
    li, lp = _num(kpi, "vsm_lead_ini"), _num(kpi, "vsm_lead_post")
    mv = li.notna() & lp.notna()
    r["lead_ini"] = _suma(li[mv])
    r["lead_post"] = _suma(lp[mv])
    r["reduccion_lead"] = None if r["lead_ini"] is None else r["lead_ini"] - r["lead_post"]
    r["pct_reduccion_lead"] = ratio(r["reduccion_lead"], r["lead_ini"])
    r["proyectos_con_vsm"] = int(mv.sum())
    ei, ep = _num(kpi, "vsm_esfuerzo_ini"), _num(kpi, "vsm_esfuerzo_post")
    r["eficiencia_flujo_ini"] = ratio(_suma(ei[mv]), r["lead_ini"])
    r["eficiencia_flujo_post"] = ratio(_suma(ep[mv]), r["lead_post"])
    return r


# ---------------------------------------------------------------- formato
def fmt_pct(v) -> str:
    return "Sin datos" if v is None else f"{v * 100:.1f} %"


def fmt_usd(v) -> str:
    return "Sin datos" if v is None else f"$ {v:,.0f}"


def fmt_num(v, dec: int = 1) -> str:
    return "Sin datos" if v is None else f"{v:,.{dec}f}"
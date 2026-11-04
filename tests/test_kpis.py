import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kpis  # noqa: E402


def _kpi():
    return pd.DataFrame([
        # proyecto con todo
        dict(proyecto="A", anio=2025, valor_as_is_usd=100.0, valor_to_be_usd=60.0,
             fte_potencial_total=3.0, fte_real_optimizado=2.0, fte_diseno_org=1.0,
             diag_total=3, diag_en_timebox=2, entregables_comprometidos=4, entregables_en_fecha=3,
             bc_presentado=True, bc_ok=True, costo_benchmark=50.0, costo_evitado_usd=20.0,
             vsm_lead_ini=100.0, vsm_lead_post=50.0, vsm_esfuerzo_ini=20.0, vsm_esfuerzo_post=20.0),
        # sin To Be ni lead post: no debe entrar a esos cocientes
        dict(proyecto="B", anio=2026, valor_as_is_usd=900.0, valor_to_be_usd=None,
             fte_potencial_total=1.0, fte_real_optimizado=None, fte_diseno_org=None,
             diag_total=0, diag_en_timebox=0, entregables_comprometidos=0, entregables_en_fecha=0,
             bc_presentado=False, bc_ok=False, costo_benchmark=30.0, costo_evitado_usd=None,
             vsm_lead_ini=300.0, vsm_lead_post=None, vsm_esfuerzo_ini=None, vsm_esfuerzo_post=None),
    ])


def _ger():
    return pd.DataFrame([dict(proyecto="A", anio=2025, gerencia="GCC"),
                         dict(proyecto="A", anio=2025, gerencia="GCO"),
                         dict(proyecto="B", anio=2026, gerencia="GCC")])


def test_totales_solo_con_ambos_datos():
    r = kpis.calcular(_kpi(), _ger())
    assert r["usd_as_is"] == 100 and r["usd_to_be"] == 60
    assert r["ahorro_usd"] == 40
    assert abs(r["pct_real_vs_potencial"] - 0.6) < 1e-9
    assert r["lead_ini"] == 100 and r["lead_post"] == 50
    assert abs(r["pct_reduccion_lead"] - 0.5) < 1e-9
    assert r["proyectos_con_vsm"] == 1
    assert r["costo_evitado"] == 30           # 50 - 20; B no tiene costo real
    assert r["promedio_consultoria"] == 40    # (50 + 30) / 2


def test_ratios_suma_sobre_suma():
    r = kpis.calcular(_kpi(), _ger())
    assert abs(r["pct_diag_timebox"] - 2 / 3) < 1e-9
    assert abs(r["pct_entregables_en_fecha"] - 3 / 4) < 1e-9
    assert r["pct_bc_aprobados"] == 1.0 and r["bc_presentados"] == 1


def test_intervenciones_y_orden_gerencias():
    r = kpis.calcular(_kpi(), _ger())
    assert r["intervenciones"] == 3
    assert list(r["por_gerencia"]) == ["GCO", "GCC"]
    assert r["por_gerencia"]["GCC"] == 2


def test_filtro_anio():
    k, g = kpis.filtrar(_kpi(), _ger(), 2026)
    r = kpis.calcular(k, g)
    assert r["proyectos"] == 1 and r["intervenciones"] == 1
    assert r["pct_real_vs_potencial"] is None   # sin To Be -> "Sin datos", no 0 %
    assert r["pct_bc_aprobados"] is None
    assert kpis.anios_disponibles(_kpi()) == [2026, 2025]


def test_vacio_no_falla():
    r = kpis.calcular(_kpi().iloc[0:0], _ger().iloc[0:0])
    assert r["proyectos"] == 0 and r["intervenciones"] == 0
    assert kpis.fmt_pct(r["pct_reduccion_lead"]) == "Sin datos"


def test_formatos():
    assert kpis.fmt_pct(0.3281) == "32.8 %"
    assert kpis.fmt_usd(84000) == "$ 84,000"

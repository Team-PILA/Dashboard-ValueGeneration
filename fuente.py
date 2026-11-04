"""Lectura de las vistas de Value Generation en Supabase (rol de solo lectura vg_dashboard_ro).

Sin streamlit para poder probarlo. Nunca se devuelve ni se muestra la cadena de conexión
ni el texto de un error de la base.
"""
from __future__ import annotations

from zoneinfo import ZoneInfo

import pandas as pd

try:
    import psycopg2
    import psycopg2.extensions as _ext
except ImportError:  # pragma: no cover
    psycopg2 = None

# Solo estos esquemas: el nombre va dentro del SQL, así que no se acepta otro valor.
ESQUEMAS = ("value_generation", "vg_demo")
_DEC2FLOAT = None


def _conectar(url: str):
    global _DEC2FLOAT
    if psycopg2 is None:
        raise RuntimeError("Falta psycopg2")
    try:
        conn = psycopg2.connect(url, connect_timeout=15)
    except Exception:
        raise RuntimeError("No se pudo conectar a la base de datos") from None
    if _DEC2FLOAT is None:  # numeric -> float (y no Decimal)
        _DEC2FLOAT = _ext.new_type(_ext.DECIMAL.values, "DEC2FLOAT",
                                   lambda v, cur: float(v) if v is not None else None)
    _ext.register_type(_DEC2FLOAT, conn)
    conn.set_session(readonly=True, autocommit=True)
    return conn


def _df(cur, sql: str) -> pd.DataFrame:
    cur.execute(sql)
    return pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])


def leer(url: str, esquema: str = "value_generation") -> dict:
    """dict(kpi, gerencias, umbral, corrida). Lanza RuntimeError con mensaje genérico si falla."""
    if esquema not in ESQUEMAS:
        raise RuntimeError("Esquema no permitido")
    conn = _conectar(url)
    try:
        cur = conn.cursor()
        try:
            kpi = _df(cur, f"select * from {esquema}.v_kpi_proyecto order by proyecto")
            gerencias = _df(cur, f"select * from {esquema}.v_intervencion_gerencia")
        except Exception:
            raise RuntimeError("No se pudieron leer las vistas") from None
        # Adornos: si fallan, el dashboard igual se muestra
        try:
            umbral = _df(cur, "select kpi, meta, unidad from value_generation.umbral")
        except Exception:
            umbral = pd.DataFrame(columns=["kpi", "meta", "unidad"])
        try:
            cur.execute("select ejecutado_en from value_generation.v_ultima_corrida")
            fila = cur.fetchone()
            corrida = fila[0] if fila else None
        except Exception:
            corrida = None
    finally:
        conn.close()
    if corrida is not None and corrida.tzinfo is not None:
        corrida = corrida.astimezone(ZoneInfo("America/Lima"))
    return {"kpi": kpi, "gerencias": gerencias, "umbral": umbral, "corrida": corrida}


def meta(umbral: pd.DataFrame, clave: str):
    """Valor de value_generation.umbral para `clave`, o None."""
    if umbral is None or umbral.empty:
        return None
    fila = umbral[umbral["kpi"] == clave]
    return None if fila.empty else float(fila["meta"].iloc[0])

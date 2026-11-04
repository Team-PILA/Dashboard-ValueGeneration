# Value Generation

Dashboard en Streamlit de los proyectos con **«¿Genera eficiencia?»** marcado en Notion.
Solo lee vistas de Supabase (esquema `value_generation`). El ETL vive en el repo del Dashboard de Proyectos.

```
Notion → ETL (repo dashboard de proyectos, GitHub Actions lun-juev 8:30 y 17:30 y vie - 8:30 y 1:30)
       → Supabase proyectos.proyecto / proyectos.actividad
       → vistas value_generation.*  → esta app (rol vg_dashboard_ro, solo lectura)
```

## Archivos

| Archivo | Qué hace |
|---|---|
| `app.py` | Interfaz con el layout del whiteboard y filtro por año (Start Date Real) |
| `kpis.py` | Cálculos (Σ/Σ, solo proyectos con ambos datos). Sin Streamlit, probado con pytest |
| `fuente.py` | Lee las vistas con el rol de solo lectura |
| `acceso.py` | Login (igual que en los otros dashboards) |
| `sql/v_ultima_corrida.sql` | Vista con la hora del último corte (correr una vez en Supabase) |

## Secrets (solo en Streamlit Cloud o en `.streamlit/secrets.toml`, nunca en el repo)

`APP_USUARIO`, `APP_CLAVE`, `SUPABASE_DB_URL_RO` (usuario `vg_dashboard_ro`) y `ESQUEMA`
(`value_generation` para datos reales, `vg_demo` para datos de prueba). Ver `.streamlit/secrets.toml.example`.

## Local

```
pip install -r requirements.txt
pytest -q
streamlit run app.py
```

## Indicadores pendientes de definir (se muestran como «Por definir»)

% WIP en prioridades vigentes, Benefit sustainability rate, # Procesos Analizados, FTE Impactos para Calidad.

-- =====================================================================
-- Value Generation · cambio 06: # Procesos Analizados
--  Campo numérico nuevo en Intervenciones (Notion): "# Procesos Analizados".
--  Dashboard: Σ de ese campo (solo proyectos con «¿Genera eficiencia?» y del año filtrado).
--  Incluye todo lo de 04 y 05, así que los reemplaza.
-- Se puede ejecutar varias veces. Requiere 01 y 02 ya ejecutados.
-- =====================================================================

-- 1. Columnas nuevas (las llena el ETL desde Notion)
alter table proyectos.proyecto
  add column if not exists valor_real_post_usd numeric(14,2),  -- "Valorización Post-Intervencion ($)"
  add column if not exists ent_comprometidos   numeric(10,0),  -- fórmula "Entregables Comprometidos"
  add column if not exists ent_cumplidos       numeric(10,0),  -- fórmula "Entregables Cumplidos"
  add column if not exists procesos_analizados numeric(10,0);  -- "# Procesos Analizados"

-- 2. Fases que forman el diagnóstico (se editan aquí, sin tocar código).
--    Compara contra "Fase de Ejecución" o "Fase Ruta" de la actividad, sin importar mayúsculas.
create table if not exists value_generation.fase_diagnostico (
  fase text primary key
);
insert into value_generation.fase_diagnostico (fase) values
  ('1. Identificar'),
  ('2. Analizar')
on conflict (fase) do nothing;
-- Si las actividades de Ruta usan otros nombres de fase, agrégalos, por ejemplo:
-- insert into value_generation.fase_diagnostico values ('1. Análisis de Eficiencia') on conflict do nothing;

-- 3. Vistas: se recrean porque cambian sus columnas
drop view if exists value_generation.v_lead_time_anio;
drop view if exists value_generation.v_bc_anio;
drop view if exists value_generation.v_intervencion_gerencia;
drop view if exists value_generation.v_kpi_proyecto;
drop view if exists value_generation.v_proyecto;

create view value_generation.v_proyecto as
select p.proyecto_id, p.nombre as proyecto, p.tipo_proyecto, p.status,
       p.gerencia_central, p.gerencia_analizada, p.inicio_real, p.fin_real,
       extract(year from p.inicio_real)::int as anio, p.bc_aprobado,
       p.fte_potencial_total, p.fte_real_optimizado, p.fte_diseno_org,
       p.fte_make_or_buy, p.fte_optim_procesos, p.costo_benchmark,
       p.valor_as_is_usd, p.valor_to_be_usd, p.valor_real_post_usd,
       p.ent_comprometidos, p.ent_cumplidos, p.procesos_analizados,
       p.vsm_ciclo_ini,  p.vsm_lead_ini,  p.vsm_espera_ini,  p.vsm_esfuerzo_ini,
       p.vsm_ciclo_post, p.vsm_lead_post, p.vsm_espera_post, p.vsm_esfuerzo_post
from proyectos.proyecto p
where p.genera_eficiencia is true;

create view value_generation.v_kpi_proyecto as
with act as (
  select a.proyecto,
         count(*)                                                     as tareas_total,
         count(*) filter (where a.esta_done)                          as tareas_done,
         sum(a.costo_real)                                            as costo_real_usd
  from proyectos.actividad a
  group by a.proyecto
),
diag as (
  select a.proyecto,
         min(a.real_inicio)               as diag_inicio,
         max(a.real_fin)                  as diag_fin,
         count(*)                         as diag_actividades,
         bool_and(a.real_fin is not null and a.esta_done) as diag_cerrado
  from proyectos.actividad a
  where exists (select 1 from value_generation.fase_diagnostico f
                where lower(btrim(f.fase)) in (lower(btrim(coalesce(a.fase_ejecucion, ''))),
                                               lower(btrim(coalesce(a.fase_ruta, '')))))
  group by a.proyecto
)
select p.*,
       -- Project Delivery
       coalesce(act.tareas_total, 0)                                          as tareas_total,
       coalesce(act.tareas_done, 0)                                           as tareas_done,
       coalesce(p.ent_comprometidos, 0)                                       as entregables_comprometidos,  -- de Notion
       coalesce(p.ent_cumplidos, 0)                                           as entregables_en_fecha,       -- de Notion
       round(p.ent_cumplidos / nullif(p.ent_comprometidos, 0), 4)             as pct_entregables_en_fecha,
       lower(btrim(coalesce(p.bc_aprobado, ''))) in ('sí', 'si', 'no')        as bc_presentado,
       lower(btrim(coalesce(p.bc_aprobado, ''))) in ('sí', 'si')              as bc_ok,
       -- Diagnóstico (días calendario; null mientras no esté cerrado)
       diag.diag_inicio,
       diag.diag_fin,
       coalesce(diag.diag_cerrado, false)                                     as diag_cerrado,
       case when diag.diag_cerrado and diag.diag_inicio is not null
            then diag.diag_fin - diag.diag_inicio end                         as diag_dias,
       -- Consolidated value
       act.costo_real_usd                                                     as costo_evitado_usd,  -- = Σ Costo Real PI
       round(p.fte_real_optimizado / nullif(p.fte_potencial_total, 0), 4)       as pct_fte_real_vs_pot,
       p.valor_as_is_usd - p.valor_to_be_usd                                  as ahorro_potencial_usd,
       p.valor_as_is_usd - p.valor_real_post_usd                              as ahorro_real_usd,
       round((p.valor_as_is_usd - p.valor_real_post_usd)
             / nullif(p.valor_as_is_usd - p.valor_to_be_usd, 0), 4)           as pct_real_vs_potencial,
       -- Operational impact (VSM)
       (p.vsm_lead_ini is not null and p.vsm_lead_post is not null)           as tiene_vsm,
       p.vsm_lead_ini - p.vsm_lead_post                                       as reduccion_lead_time,
       round((p.vsm_lead_ini - p.vsm_lead_post) / nullif(p.vsm_lead_ini, 0), 4) as pct_reduccion_lead_time,
       round(p.vsm_esfuerzo_ini  / nullif(p.vsm_lead_ini, 0), 4)                as eficiencia_flujo_ini,
       round(p.vsm_esfuerzo_post / nullif(p.vsm_lead_post, 0), 4)               as eficiencia_flujo_post
from value_generation.v_proyecto p
left join act  on act.proyecto  = p.proyecto
left join diag on diag.proyecto = p.proyecto;

create view value_generation.v_intervencion_gerencia as
select p.proyecto_id, p.proyecto, p.anio, upper(btrim(g)) as gerencia
from value_generation.v_proyecto p
cross join lateral unnest(string_to_array(p.gerencia_central, ',')) as g
where btrim(g) <> '';

create view value_generation.v_bc_anio as
select anio,
       count(*) filter (where bc_presentado)   as bc_presentados,
       count(*) filter (where bc_ok)           as bc_aprobados,
       round((count(*) filter (where bc_ok))::numeric
             / nullif(count(*) filter (where bc_presentado), 0), 4) as pct_bc_aprobados
from value_generation.v_kpi_proyecto
group by anio;

create view value_generation.v_lead_time_anio as
select anio,
       count(*)                                  as proyectos_con_vsm,
       sum(vsm_lead_ini)                         as lead_time_inicial,
       sum(vsm_lead_post)                        as lead_time_post,
       sum(vsm_lead_ini) - sum(vsm_lead_post)    as reduccion_lead_time,
       round((sum(vsm_lead_ini) - sum(vsm_lead_post)) / nullif(sum(vsm_lead_ini), 0), 4) as pct_reduccion_lead_time,
       round(sum(vsm_esfuerzo_ini)  / nullif(sum(vsm_lead_ini), 0), 4)                    as eficiencia_flujo_ini,
       round(sum(vsm_esfuerzo_post) / nullif(sum(vsm_lead_post), 0), 4)                   as eficiencia_flujo_post
from value_generation.v_kpi_proyecto
where tiene_vsm
group by anio;

-- 4. Permisos de lectura (incluye la tabla umbral, que no se estaba pudiendo leer)
grant usage  on schema value_generation to vg_dashboard_ro;
grant select on all tables in schema value_generation to vg_dashboard_ro;

-- 5. Verificación
-- select proyecto, diag_inicio, diag_fin, diag_cerrado, diag_dias,
--        ahorro_potencial_usd, ahorro_real_usd, pct_real_vs_potencial
-- from value_generation.v_kpi_proyecto;

-- =====================================================================
-- Value Generation · migración (Supabase, proyecto team-pila-dashboards)
-- Reutiliza las tablas del esquema "proyectos" (una sola fuente, un solo ETL).
-- El esquema "value_generation" tiene VISTAS + una tabla de umbrales + rol RO.
-- Se puede ejecutar varias veces. NO lleva contraseñas (ver la sección 7).
-- =====================================================================

-- ---------------------------------------------------------------------
-- 0. ANTES: mira qué columnas de Notion ya están guardadas en "extra"
--    (ajusta los nombres de la sección 3 si alguno no coincide)
-- ---------------------------------------------------------------------
-- select distinct jsonb_object_keys(extra) as k from proyectos.proyecto  order by 1;
-- select distinct jsonb_object_keys(extra) as k from proyectos.actividad order by 1;

-- ---------------------------------------------------------------------
-- 1. Helper: texto -> numeric (null si viene vacío o no es número)
-- ---------------------------------------------------------------------
create or replace function proyectos.a_num(t text) returns numeric
language plpgsql immutable as $$
begin
  return nullif(btrim(t), '')::numeric;
exception when others then
  return null;
end $$;

-- ---------------------------------------------------------------------
-- 2. Columnas nuevas (todas nullable: no rompen el Dashboard de Proyectos)
-- ---------------------------------------------------------------------
alter table proyectos.proyecto
  add column if not exists gerencia_analizada   text,
  add column if not exists gerencia_central     text,           -- "GCO, GCC" (multi)
  add column if not exists genera_eficiencia    boolean,        -- checkbox "¿Genera Eficiencia?"
  add column if not exists bc_aprobado          text,           -- "¿BC Aprobado?": Sí / No / No aplica
  add column if not exists fte_diseno_org       numeric(10,2),
  add column if not exists fte_make_or_buy      numeric(10,2),
  add column if not exists fte_optim_procesos   numeric(10,2),
  add column if not exists fte_real_optimizado  numeric(10,2),
  add column if not exists fte_potencial_total  numeric(10,2),
  add column if not exists costo_benchmark      numeric(14,2),  -- "Costo Benchmark $" = precio consultora externa
  add column if not exists valor_as_is_usd      numeric(14,2),  -- "Valorización As Is ($)"
  add column if not exists valor_to_be_usd      numeric(14,2),  -- "Valorización To Be ($)"
  -- VSM (Value Stream Mapping). Misma unidad de tiempo en todos los proyectos.
  add column if not exists vsm_ciclo_ini        numeric(12,2),  -- "Tiempo de Ciclo Inicial"
  add column if not exists vsm_lead_ini         numeric(12,2),  -- "Lead Time Inicial"
  add column if not exists vsm_espera_ini       numeric(12,2),  -- "Espera Inicial"
  add column if not exists vsm_esfuerzo_ini     numeric(12,2),  -- "Esfuerzo Inicial"
  add column if not exists vsm_ciclo_post       numeric(12,2),  -- "Tiempo de Ciclo post-intervencion"
  add column if not exists vsm_lead_post        numeric(12,2),  -- "Lead Time post-intervencion"
  add column if not exists vsm_espera_post      numeric(12,2),  -- "Espera post-intervencion"
  add column if not exists vsm_esfuerzo_post    numeric(12,2);  -- "Esfuerzo post-intervencion"

alter table proyectos.actividad
  add column if not exists base_origen     text,                -- 'ruta' | 'pm'
  add column if not exists desv_dias_plan  numeric(10,2),
  add column if not exists costo_plan      numeric(14,2),       -- Ruta: Costo Plan | PM: HH Plan * Cost Unit
  add column if not exists costo_real      numeric(14,2);       -- Ruta: Costo Real | PM: HH Acum * Cost Unit

-- ---------------------------------------------------------------------
-- 3. Backfill desde "extra" (nombres verificados contra Notion el 03/11).
--    Toma el valor de "extra" si existe; si no, conserva el actual.
--    Se puede re-ejecutar tras cada corrida del ETL hasta que etl.py
--    escriba directo estas columnas.
-- ---------------------------------------------------------------------
update proyectos.proyecto set
  gerencia_central    = coalesce(extra->>'Gerencia Central', gerencia_central),
  bc_aprobado         = coalesce(extra->>'¿BC Aprobado?', bc_aprobado),
  genera_eficiencia   = coalesce(
                          case lower(btrim(extra->>'¿Genera eficiencia?'))
                            when 'true' then true  when 'sí' then true  when 'si' then true
                            when 'false' then false when 'no' then false
                          end, genera_eficiencia),
  fte_diseno_org      = coalesce(proyectos.a_num(extra->>'FTE Diseño Organizacional'),  fte_diseno_org),
  fte_make_or_buy     = coalesce(proyectos.a_num(extra->>'FTE Make or Buy'),            fte_make_or_buy),
  fte_optim_procesos  = coalesce(proyectos.a_num(extra->>'FTE Optimización Procesos'),  fte_optim_procesos),
  fte_real_optimizado = coalesce(proyectos.a_num(extra->>'FTE Real Optimizado'),        fte_real_optimizado),
  fte_potencial_total = coalesce(proyectos.a_num(extra->>'Total FTE Potencial'),        fte_potencial_total),
  costo_benchmark     = coalesce(proyectos.a_num(extra->>'Costo Benchmark $'),          costo_benchmark),
  valor_as_is_usd     = coalesce(proyectos.a_num(extra->>'Valorización As Is ($)'),     valor_as_is_usd),
  valor_to_be_usd     = coalesce(proyectos.a_num(extra->>'Valorización To Be ($)'),     valor_to_be_usd),
  vsm_ciclo_ini       = coalesce(proyectos.a_num(extra->>'Tiempo de Ciclo Inicial'),           vsm_ciclo_ini),
  vsm_lead_ini        = coalesce(proyectos.a_num(extra->>'Lead Time Inicial'),                 vsm_lead_ini),
  vsm_espera_ini      = coalesce(proyectos.a_num(extra->>'Espera Inicial'),                    vsm_espera_ini),
  vsm_esfuerzo_ini    = coalesce(proyectos.a_num(extra->>'Esfuerzo Inicial'),                  vsm_esfuerzo_ini),
  vsm_ciclo_post      = coalesce(proyectos.a_num(extra->>'Tiempo de Ciclo post-intervencion'), vsm_ciclo_post),
  vsm_lead_post       = coalesce(proyectos.a_num(extra->>'Lead Time post-intervencion'),       vsm_lead_post),
  vsm_espera_post     = coalesce(proyectos.a_num(extra->>'Espera post-intervencion'),          vsm_espera_post),
  vsm_esfuerzo_post   = coalesce(proyectos.a_num(extra->>'Esfuerzo post-intervencion'),        vsm_esfuerzo_post);

update proyectos.actividad set
  desv_dias_plan = coalesce(proyectos.a_num(coalesce(extra->>'Desv Días Plan', extra->>'Desv Dias Plan')),   desv_dias_plan),
  costo_plan     = coalesce(proyectos.a_num(coalesce(extra->>'Costo Plan', extra->>'HH Plan * Cost Unit')),  costo_plan),
  costo_real     = coalesce(proyectos.a_num(coalesce(extra->>'Costo Real', extra->>'HH Acum * Cost Unit')),  costo_real);

-- ---------------------------------------------------------------------
-- 4. Esquema value_generation
-- ---------------------------------------------------------------------
create schema if not exists value_generation;

-- 4.0 Umbrales (estándar de Gian). Se editan a mano aquí, no en el código.
create table if not exists value_generation.umbral (
  kpi         text primary key,
  meta        numeric not null,
  unidad      text,
  comentario  text
);
insert into value_generation.umbral (kpi, meta, unidad, comentario) values
  ('satisfaccion_respuesta_min', 4,    'escala 1-5',   'Respuesta satisfecha si >= 4'),
  ('diag_timebox_dias',          10,   'días hábiles', 'Scope freeze -> diagnóstico validado'),
  ('benefit_sustainability_min', 0.90, 'ratio',        'Sostenible si >= 90% en 2 mediciones seguidas')
on conflict (kpi) do nothing;

-- 4.1 Proyectos que entran al dashboard: solo los que tienen marcado
--     "¿Genera eficiencia?" en Notion (Ruta o Modelo PM). Sin check = no entra.
create or replace view value_generation.v_proyecto as
select p.proyecto_id,
       p.nombre                              as proyecto,
       p.tipo_proyecto,
       p.status,
       p.gerencia_central,
       p.gerencia_analizada,
       p.inicio_real,
       p.fin_real,
       extract(year from p.inicio_real)::int as anio,      -- filtro por año (Start Date Real)
       p.bc_aprobado,
       p.fte_potencial_total,
       p.fte_real_optimizado,
       p.fte_diseno_org,
       p.fte_make_or_buy,
       p.fte_optim_procesos,
       p.costo_benchmark,
       p.valor_as_is_usd,
       p.valor_to_be_usd,
       p.vsm_ciclo_ini,  p.vsm_lead_ini,  p.vsm_espera_ini,  p.vsm_esfuerzo_ini,
       p.vsm_ciclo_post, p.vsm_lead_post, p.vsm_espera_post, p.vsm_esfuerzo_post
from proyectos.proyecto p
where p.genera_eficiencia is true;

-- 4.2 KPIs por proyecto (los totales del portafolio se agregan en Streamlit como SUM/SUM)
create or replace view value_generation.v_kpi_proyecto as
with hoy as (
  select (now() at time zone 'America/Lima')::date as d
),
act as (
  select a.proyecto,
         count(*)                                                     as tareas_total,
         count(*) filter (where a.esta_done)                          as tareas_done,
         count(*) filter (where a.plan_fin <= hoy.d)                  as comprometidas,
         count(*) filter (where a.plan_fin <= hoy.d and a.esta_done
                            and a.real_fin <= a.plan_fin)             as cumplidas_en_fecha,
         sum(a.costo_real)                                            as costo_real_usd,
         count(*) filter (where x.es_diag and a.desv_dias_plan is not null) as diag_total,
         count(*) filter (where x.es_diag and a.desv_dias_plan >= 0)        as diag_en_timebox
  from proyectos.actividad a
  cross join hoy
  cross join lateral (
    select lower(btrim(coalesce(a.actividad, ''))) in (
             'actividades por persona',
             'matriz de capacidad vs ctg actividad',
             'informe de mudas') as es_diag
  ) x
  group by a.proyecto
)
select p.*,
       -- Project Delivery
       coalesce(act.tareas_total, 0)                                          as tareas_total,
       coalesce(act.tareas_done, 0)                                           as tareas_done,
       coalesce(act.comprometidas, 0)                                         as entregables_comprometidos,
       coalesce(act.cumplidas_en_fecha, 0)                                    as entregables_en_fecha,
       round(act.cumplidas_en_fecha::numeric / nullif(act.comprometidas, 0), 4) as pct_entregables_en_fecha,
       lower(btrim(coalesce(p.bc_aprobado, ''))) in ('sí', 'si', 'no')        as bc_presentado,  -- "En evaluación" y "No aplica" no cuentan
       lower(btrim(coalesce(p.bc_aprobado, ''))) in ('sí', 'si')              as bc_ok,
       -- Performance PI (provisional: Desv Días Plan >= 0 hasta tener scope freeze)
       coalesce(act.diag_total, 0)                                            as diag_total,
       coalesce(act.diag_en_timebox, 0)                                       as diag_en_timebox,
       round(act.diag_en_timebox::numeric / nullif(act.diag_total, 0), 4)       as pct_diag_timebox,
       -- Consolidated value
       act.costo_real_usd                                                     as costo_evitado_usd,
       round(p.fte_real_optimizado / nullif(p.fte_potencial_total, 0), 4)       as pct_fte_real_vs_pot,
       p.valor_as_is_usd - p.valor_to_be_usd                                  as ahorro_potencial_usd,
       round(p.valor_to_be_usd / nullif(p.valor_as_is_usd, 0), 4)               as pct_usd_real_vs_pot,
       -- Operational impact (VSM): solo cuenta si tiene Lead Time inicial y post
       (p.vsm_lead_ini is not null and p.vsm_lead_post is not null)           as tiene_vsm,
       p.vsm_lead_ini - p.vsm_lead_post                                       as reduccion_lead_time,
       round((p.vsm_lead_ini - p.vsm_lead_post) / nullif(p.vsm_lead_ini, 0), 4) as pct_reduccion_lead_time,
       round(p.vsm_esfuerzo_ini  / nullif(p.vsm_lead_ini, 0), 4)                as eficiencia_flujo_ini,
       round(p.vsm_esfuerzo_post / nullif(p.vsm_lead_post, 0), 4)               as eficiencia_flujo_post
from value_generation.v_proyecto p
left join act on act.proyecto = p.proyecto;

-- 4.3 # Total de Intervenciones por gerencia (GCO, GCC, GCAF, GDSO, GG)
create or replace view value_generation.v_intervencion_gerencia as
select p.proyecto_id,
       p.proyecto,
       p.anio,
       upper(btrim(g)) as gerencia
from value_generation.v_proyecto p
cross join lateral unnest(string_to_array(p.gerencia_central, ',')) as g
where btrim(g) <> '';

-- 4.4 % Business Cases aprobados = Sí / (Sí + No), por año
create or replace view value_generation.v_bc_anio as
select anio,
       count(*) filter (where bc_presentado)   as bc_presentados,
       count(*) filter (where bc_ok)           as bc_aprobados,
       round((count(*) filter (where bc_ok))::numeric
             / nullif(count(*) filter (where bc_presentado), 0), 4) as pct_bc_aprobados
from value_generation.v_kpi_proyecto
group by anio;

-- 4.5 Reducción Lead Time general, por año (solo proyectos con LT inicial y post)
--     Reducción = Σ LT inicial − Σ LT post ; % = Reducción / Σ LT inicial
--     Eficiencia de flujo del portafolio = Σ Esfuerzo / Σ Lead Time
create or replace view value_generation.v_lead_time_anio as
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

-- ---------------------------------------------------------------------
-- 5. ROL DE LECTURA (Streamlit). No hace falta rol RW: escribe proy_cron_rw.
--    Las vistas leen "proyectos" con permisos de su dueño, así que
--    vg_dashboard_ro NO ve las tablas de proyectos, solo este esquema.
-- ---------------------------------------------------------------------
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'vg_dashboard_ro') then
    create role vg_dashboard_ro nologin;
  end if;
end $$;

revoke all on schema value_generation from public;
do $$
declare r text;
begin
  foreach r in array array['anon', 'authenticated'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      execute format('revoke all on schema value_generation from %I', r);
      execute format('revoke all on all tables in schema value_generation from %I', r);
    end if;
  end loop;
end $$;

grant usage  on schema value_generation to vg_dashboard_ro;
grant select on all tables in schema value_generation to vg_dashboard_ro;
alter default privileges in schema value_generation
  grant select on tables to vg_dashboard_ro;

-- ---------------------------------------------------------------------
-- 6. VERIFICACIÓN RÁPIDA
-- ---------------------------------------------------------------------
-- select * from value_generation.v_kpi_proyecto limit 20;
-- select gerencia, count(*) from value_generation.v_intervencion_gerencia group by 1;
-- select * from value_generation.v_bc_anio;
-- select * from value_generation.v_lead_time_anio;

-- ---------------------------------------------------------------------
-- 7. CLAVE DEL ROL (EJECÚTALO APARTE, NO LO GUARDES EN EL REPO)
-- ---------------------------------------------------------------------
-- alter role vg_dashboard_ro with login password 'PON_AQUI_UNA_CLAVE_LARGA_5';
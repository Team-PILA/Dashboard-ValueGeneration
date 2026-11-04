-- =====================================================================
-- Value Generation · DEMO (Supabase). Datos ficticios para probar el dashboard
-- sin tocar Notion ni las tablas reales. El ETL nunca escribe en "vg_demo",
-- así que no importa la hora ni si alguien corre el workflow a mano.
-- Requiere haber corrido antes value_generation.sql. Se puede ejecutar varias veces
-- (borra y recarga los datos demo). Para eliminarlo todo: drop schema vg_demo cascade;
-- =====================================================================
create schema if not exists vg_demo;

-- 1. Tablas con la MISMA estructura que las reales
create table if not exists vg_demo.proyecto  (like proyectos.proyecto  including all);
create table if not exists vg_demo.actividad (like proyectos.actividad including all);

-- 2. Datos ficticios
truncate vg_demo.proyecto, vg_demo.actividad;

insert into vg_demo.proyecto (
  proyecto_id, nombre, tipo_proyecto, status, inicio_real, fin_real,
  genera_eficiencia, gerencia_central, bc_aprobado,
  fte_diseno_org, fte_make_or_buy, fte_optim_procesos, fte_potencial_total, fte_real_optimizado,
  costo_benchmark, valor_as_is_usd, valor_to_be_usd,
  vsm_ciclo_ini, vsm_lead_ini, vsm_espera_ini, vsm_esfuerzo_ini,
  vsm_ciclo_post, vsm_lead_post, vsm_espera_post, vsm_esfuerzo_post
) values
  ('demo-1','[DEMO] Optimización Compras','Ruta de Eficiencia','Done',        '2025-03-03','2025-06-27', true,'GCAF',       'Sí',            0,1.0,2.0, 3.0,2.5, 45000, 120000, 80000,  40,160,120,40,  30,100,70,30),
  ('demo-2','[DEMO] Rediseño Mesa de Ayuda','Ruta de Eficiencia','Done',      '2025-08-04','2025-11-28', true,'GCC, GCO',   'No',          1.5,0,  1.0, 2.5,1.5, 38000,  90000, 70000,  24, 96, 72,24,  20, 72, 52,20),
  ('demo-3','[DEMO] Make or Buy Mantenimiento','Ruta de Eficiencia','In progress','2026-02-02',null, true,'GCC',        'En evaluación', 0,3.0,0,   3.0,null, 60000, 200000,150000, null,null,null,null, null,null,null,null),
  ('demo-4','[DEMO] Flujo Facturación','Modelo PM','In progress',             '2026-04-06',null,         true,'GCAF, GCDSO','Sí',            0,0,  1.5, 1.5,1.0, 25000,  50000, 35000,  16, 80, 64,16,  12, 48, 36,12),
  ('demo-5','[DEMO] Diseño Org. Operaciones','Ruta de Eficiencia','Not started','2026-07-01',null,        true,'GCO, GG',    'No aplica',   4.0,0,  0,   4.0,null, 52000,   null,  null,  null,null,null,null, null,null,null,null),
  ('demo-6','[DEMO] No genera eficiencia','Modelo PM','In progress',          '2026-05-04',null,         false,'GG',        'No aplica',     0,0,  0,   0,  null, 10000,   null,  null,  null,null,null,null, null,null,null,null);

-- 8 actividades por proyecto: las 3 primeras son las de diagnóstico.
-- desv_dias_plan >= 0 = a tiempo; real_fin = plan_fin - desv.
insert into vg_demo.actividad (
  actividad_id, proyecto, tipo_proyecto, actividad, estado,
  plan_inicio, plan_fin, real_fin, desv_dias_plan, costo_plan, costo_real, base_origen
)
select 'demo-' || p.n || '-' || g,
       p.nombre, p.tipo,
       case g when 1 then 'Actividades por Persona'
              when 2 then 'Matriz de Capacidad vs Ctg Actividad'
              when 3 then 'Informe de mudas'
              else 'Entregable ' || g end,
       case when g <= p.hechas then 'Done' else 'In progress' end,
       p.ini + (g - 1) * 7,
       p.ini + g * 7,
       case when g <= p.hechas then p.ini + g * 7 - (1 - (g + p.n) % 4) end,
       case when g <= p.hechas then (1 - (g + p.n) % 4) end,
       8 * 25.0,
       case when g <= p.hechas then (8 + (g + p.n) % 3) * 25.0 end,
       case when p.tipo = 'Modelo PM' then 'pm' else 'ruta' end
from (values
  (1, '[DEMO] Optimización Compras',      'Ruta de Eficiencia', date '2025-03-03', 8),
  (2, '[DEMO] Rediseño Mesa de Ayuda',    'Ruta de Eficiencia', date '2025-08-04', 8),
  (3, '[DEMO] Make or Buy Mantenimiento', 'Ruta de Eficiencia', date '2026-02-02', 5),
  (4, '[DEMO] Flujo Facturación',         'Modelo PM',          date '2026-04-06', 4),
  (5, '[DEMO] Diseño Org. Operaciones',   'Ruta de Eficiencia', date '2026-07-01', 0),
  (6, '[DEMO] No genera eficiencia',      'Modelo PM',          date '2026-05-04', 3)
) as p(n, nombre, tipo, ini, hechas)
cross join generate_series(1, 8) as g;

-- 3. Las MISMAS vistas de value_generation, pero sobre las tablas demo
create or replace view vg_demo.v_proyecto as
select p.proyecto_id, p.nombre as proyecto, p.tipo_proyecto, p.status,
       p.gerencia_central, p.gerencia_analizada, p.inicio_real, p.fin_real,
       extract(year from p.inicio_real)::int as anio, p.bc_aprobado,
       p.fte_potencial_total, p.fte_real_optimizado, p.fte_diseno_org,
       p.fte_make_or_buy, p.fte_optim_procesos, p.costo_benchmark,
       p.valor_as_is_usd, p.valor_to_be_usd,
       p.vsm_ciclo_ini,  p.vsm_lead_ini,  p.vsm_espera_ini,  p.vsm_esfuerzo_ini,
       p.vsm_ciclo_post, p.vsm_lead_post, p.vsm_espera_post, p.vsm_esfuerzo_post
from vg_demo.proyecto p
where p.genera_eficiencia is true;

create or replace view vg_demo.v_kpi_proyecto as
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
  from vg_demo.actividad a
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
       coalesce(act.tareas_total, 0)                                          as tareas_total,
       coalesce(act.tareas_done, 0)                                           as tareas_done,
       coalesce(act.comprometidas, 0)                                         as entregables_comprometidos,
       coalesce(act.cumplidas_en_fecha, 0)                                    as entregables_en_fecha,
       round(act.cumplidas_en_fecha::numeric / nullif(act.comprometidas, 0), 4) as pct_entregables_en_fecha,
       lower(btrim(coalesce(p.bc_aprobado, ''))) in ('sí', 'si', 'no')        as bc_presentado,
       lower(btrim(coalesce(p.bc_aprobado, ''))) in ('sí', 'si')              as bc_ok,
       coalesce(act.diag_total, 0)                                            as diag_total,
       coalesce(act.diag_en_timebox, 0)                                       as diag_en_timebox,
       round(act.diag_en_timebox::numeric / nullif(act.diag_total, 0), 4)       as pct_diag_timebox,
       act.costo_real_usd                                                     as costo_evitado_usd,
       round(p.fte_real_optimizado / nullif(p.fte_potencial_total, 0), 4)       as pct_fte_real_vs_pot,
       p.valor_as_is_usd - p.valor_to_be_usd                                  as ahorro_potencial_usd,
       round(p.valor_to_be_usd / nullif(p.valor_as_is_usd, 0), 4)               as pct_usd_real_vs_pot,
       (p.vsm_lead_ini is not null and p.vsm_lead_post is not null)           as tiene_vsm,
       p.vsm_lead_ini - p.vsm_lead_post                                       as reduccion_lead_time,
       round((p.vsm_lead_ini - p.vsm_lead_post) / nullif(p.vsm_lead_ini, 0), 4) as pct_reduccion_lead_time,
       round(p.vsm_esfuerzo_ini  / nullif(p.vsm_lead_ini, 0), 4)                as eficiencia_flujo_ini,
       round(p.vsm_esfuerzo_post / nullif(p.vsm_lead_post, 0), 4)               as eficiencia_flujo_post
from vg_demo.v_proyecto p
left join act on act.proyecto = p.proyecto;

create or replace view vg_demo.v_intervencion_gerencia as
select p.proyecto_id, p.proyecto, p.anio, upper(btrim(g)) as gerencia
from vg_demo.v_proyecto p
cross join lateral unnest(string_to_array(p.gerencia_central, ',')) as g
where btrim(g) <> '';

create or replace view vg_demo.v_bc_anio as
select anio,
       count(*) filter (where bc_presentado)   as bc_presentados,
       count(*) filter (where bc_ok)           as bc_aprobados,
       round((count(*) filter (where bc_ok))::numeric
             / nullif(count(*) filter (where bc_presentado), 0), 4) as pct_bc_aprobados
from vg_demo.v_kpi_proyecto
group by anio;

create or replace view vg_demo.v_lead_time_anio as
select anio,
       count(*)                                  as proyectos_con_vsm,
       sum(vsm_lead_ini)                         as lead_time_inicial,
       sum(vsm_lead_post)                        as lead_time_post,
       sum(vsm_lead_ini) - sum(vsm_lead_post)    as reduccion_lead_time,
       round((sum(vsm_lead_ini) - sum(vsm_lead_post)) / nullif(sum(vsm_lead_ini), 0), 4) as pct_reduccion_lead_time,
       round(sum(vsm_esfuerzo_ini)  / nullif(sum(vsm_lead_ini), 0), 4)                    as eficiencia_flujo_ini,
       round(sum(vsm_esfuerzo_post) / nullif(sum(vsm_lead_post), 0), 4)                   as eficiencia_flujo_post
from vg_demo.v_kpi_proyecto
where tiene_vsm
group by anio;

-- 4. Permisos: el mismo rol de lectura de Value Generation
revoke all on schema vg_demo from public;
do $$
declare r text;
begin
  foreach r in array array['anon', 'authenticated'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      execute format('revoke all on schema vg_demo from %I', r);
      execute format('revoke all on all tables in schema vg_demo from %I', r);
    end if;
  end loop;
end $$;
grant usage  on schema vg_demo to vg_dashboard_ro;
grant select on all tables in schema vg_demo to vg_dashboard_ro;

-- 5. Verificación
-- select proyecto, anio, pct_entregables_en_fecha, pct_diag_timebox, ahorro_potencial_usd, pct_reduccion_lead_time from vg_demo.v_kpi_proyecto;
-- select * from vg_demo.v_lead_time_anio;
-- select * from vg_demo.v_bc_anio;


-- 6. Para borrar cuando no se necesite
-- drop schema vg_demo cascade;
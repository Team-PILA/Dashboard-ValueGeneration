-- Hora del último corte del ETL, visible para el rol de Value Generation
-- (vg_dashboard_ro no puede leer proyectos.corrida directamente).
create or replace view value_generation.v_ultima_corrida as
select max(ejecutado_en) as ejecutado_en
from proyectos.corrida
where ok;

grant select on value_generation.v_ultima_corrida to vg_dashboard_ro;

-- =============================================================
-- Флора Казахстана — ускорение карты (v3). Уже применено в Supabase 20.11.2026.
-- Таймаут anon поднят до 15 с; точки карты берутся из компактной копии mv_points.
-- =============================================================
set statement_timeout = 0;
create index if not exists obs_region_id_idx on public.observations (region, id desc) where lat is not null;
create index if not exists obs_zone_id_idx on public.observations (zone, id desc) where lat is not null;
create index if not exists obs_taxon_id_idx2 on public.observations (taxon_id, id desc);
create index if not exists obs_obstaxon_idx on public.observations (obs_taxon_id, id desc);
create index if not exists obs_user_id_idx on public.observations (user_login, id desc);
alter role anon set statement_timeout = '15s';
alter role authenticated set statement_timeout = '15s';
notify pgrst, 'reload config';

drop materialized view if exists public.mv_points cascade;
create materialized view public.mv_points as
select o.id, o.lng::real as lng, o.lat::real as lat, o.region, o.zone, o.taxon_id, o.obs_taxon_id, o.user_login,
       o.quality_grade, coalesce(o.obs_common_name, o.obs_taxon_name, '—') as title, o.obs_taxon_name as sci, o.observed_on
from public.observations o where o.lat is not null order by o.id desc;
create unique index on public.mv_points (id desc);
create index on public.mv_points (region, id desc);
create index on public.mv_points (zone, id desc);
create index on public.mv_points (taxon_id, id desc);
create index on public.mv_points (obs_taxon_id, id desc);
create index on public.mv_points (user_login, id desc);
grant select on public.mv_points to anon, authenticated;

create or replace function public.api_map_points(p_kind text default 'all', p_name text default 'all',
    p_taxon bigint default null, p_user text default null, p_quality text default null,
    p_limit int default 20000)
returns json language plpgsql stable as $f$
declare w text := 'true'; j json;
begin
  if p_kind = 'region' then w := w || format(' and p.region = %L', p_name);
  elsif p_kind = 'zone' then w := w || format(' and p.zone = %L', p_name); end if;
  if p_taxon is not null then w := w || format(' and (p.taxon_id = %s or p.obs_taxon_id = %s)', p_taxon, p_taxon); end if;
  if p_user is not null then w := w || format(' and p.user_login = %L', p_user); end if;
  if p_quality is not null then w := w || format(' and p.quality_grade = %L', p_quality); end if;
  execute format($q$select coalesce(json_agg(json_build_array(id, lng, lat, title, sci, quality_grade, user_login, observed_on)), '[]'::json)
    from (select * from public.mv_points p where %s order by p.id desc limit %s) s$q$, w,
    least(greatest(coalesce(p_limit, 20000), 1), 20000)) into j;
  return j;
end $f$;
grant execute on function public.api_map_points(text, text, bigint, text, text, int) to anon, authenticated;

create or replace function public.etl_refresh_stats() returns text
language plpgsql security definer set search_path = public as $$
begin
  refresh materialized view concurrently public.mv_scope_species;
  refresh materialized view concurrently public.mv_scope_observers;
  refresh materialized view concurrently public.mv_scope_identifiers;
  refresh materialized view concurrently public.mv_scope_stats;
  refresh materialized view concurrently public.mv_scope_month;
  refresh materialized view concurrently public.mv_scope_family;
  refresh materialized view concurrently public.mv_map_cells;
  refresh materialized view concurrently public.mv_points;
  return 'ok ' || now();
end $$;

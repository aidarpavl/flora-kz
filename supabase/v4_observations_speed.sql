-- =============================================================
-- Флора Казахстана — ускорение списка наблюдений (v4)
-- =============================================================
set statement_timeout = 0;
create extension if not exists pg_trgm with schema extensions;
create index if not exists obs_name_trgm on public.observations
  using gin (obs_taxon_name extensions.gin_trgm_ops);
create index if not exists obs_cname_trgm on public.observations
  using gin (obs_common_name extensions.gin_trgm_ops);
create index if not exists obs_quality_id_idx on public.observations (quality_grade, id desc);
create index if not exists obs_region_all_idx on public.observations (region, id desc);
create index if not exists obs_zone_all_idx on public.observations (zone, id desc);

create or replace function public.api_observations(p_kind text default 'all', p_name text default 'all',
    p_taxon bigint default null, p_user text default null, p_quality text default null,
    p_q text default null, p_date_from date default null, p_date_to date default null,
    p_limit int default 48, p_offset int default 0)
returns json language plpgsql stable set search_path = public, extensions as $f$
declare
  w text := 'true';
  filtered boolean := false;
  total bigint;
  rows json;
begin
  if p_kind = 'region' then w := w || format(' and o.region = %L', p_name);
  elsif p_kind = 'zone' then w := w || format(' and o.zone = %L', p_name); end if;
  if p_taxon is not null then
    w := w || format(' and (o.taxon_id = %s or o.obs_taxon_id = %s)', p_taxon, p_taxon); filtered := true; end if;
  if coalesce(p_user, '') <> '' then w := w || format(' and o.user_login = %L', p_user); filtered := true; end if;
  if coalesce(p_quality, '') <> '' then w := w || format(' and o.quality_grade = %L', p_quality); filtered := true; end if;
  if p_date_from is not null then w := w || format(' and o.observed_on >= %L', p_date_from); filtered := true; end if;
  if p_date_to is not null then w := w || format(' and o.observed_on <= %L', p_date_to); filtered := true; end if;
  if coalesce(p_q, '') <> '' then
    w := w || format(' and (o.obs_taxon_name ilike %L or o.obs_common_name ilike %L)',
                     '%' || p_q || '%', '%' || p_q || '%');
    filtered := true;
  end if;

  if filtered then
    execute format('select count(*) from (select 1 from public.observations o where %s limit 10001) c', w) into total;
  else
    select s.observations into total from public.mv_scope_stats s
    where s.kind = p_kind and s.name = coalesce(p_name, 'all');
  end if;

  execute format($q$select coalesce(json_agg(r), '[]'::json) from (
      select o.id, o.observed_on, o.created_at, o.lat, o.lng, o.place_guess, o.quality_grade,
             o.user_login, o.user_icon, o.photo_url, o.uri, o.identifications_count, o.region, o.zone,
             o.taxon_id, o.obs_taxon_id, o.obs_taxon_name, o.obs_taxon_rank, o.obs_common_name
      from public.observations o where %s order by o.id desc limit %s offset %s) r$q$,
      w, least(greatest(coalesce(p_limit, 48), 1), 500), greatest(coalesce(p_offset, 0), 0)) into rows;

  return json_build_object('total', coalesce(total, 0), 'capped', filtered and total > 10000, 'rows', rows);
end $f$;
grant execute on function public.api_observations(text, text, bigint, text, text, text, date, date, int, int)
  to anon, authenticated;
analyze public.observations;

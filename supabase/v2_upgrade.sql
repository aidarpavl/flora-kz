-- =============================================================
-- Флора Казахстана — обновление базы v2
-- Все наблюдения (любой ранг), определения (эксперты), быстрые
-- сводки (материализованные представления) и API-функции для фронтенда.
-- Выполнить в SQL Editor после schema.sql и etl_in_db.sql.
-- =============================================================

-- ---------- 1. Новые поля и таблицы ----------
alter table public.observations alter column taxon_id drop not null;
alter table public.observations
  add column if not exists obs_taxon_id bigint,
  add column if not exists obs_taxon_name text,
  add column if not exists obs_taxon_rank text,
  add column if not exists obs_common_name text,
  add column if not exists created_at timestamptz,
  add column if not exists place_guess text,
  add column if not exists user_icon text,
  add column if not exists identifications_count int;

create index if not exists obs_user_idx    on public.observations (user_login);
create index if not exists obs_quality_idx on public.observations (quality_grade);
create index if not exists obs_date_idx    on public.observations (observed_on);

create table if not exists public.identifications (
    id             bigint primary key,
    observation_id bigint not null,
    user_login     text,
    taxon_id       bigint,
    category       text,
    current        boolean,
    created_at     timestamptz
);
create index if not exists ident_obs_idx  on public.identifications (observation_id);
create index if not exists ident_user_idx on public.identifications (user_login);
alter table public.identifications enable row level security;
drop policy if exists "public read ident" on public.identifications;
create policy "public read ident" on public.identifications for select using (true);

-- ---------- 2. Загрузчик наблюдений v2 ----------
create or replace function public.etl_load_observations(p_pages int default 40) returns text
language plpgsql security definer set search_path = public, extensions as $$
declare v_last bigint; v_proj text; js jsonb; res jsonb; i int; total int := 0; n int;
begin
  if not pg_try_advisory_xact_lock(424242) then return 'уже выполняется'; end if;
  select value::bigint into v_last from etl_state where key = 'last_id';
  select value into v_proj from etl_state where key = 'project';
  for i in 1..p_pages loop
    js := etl_http_get('https://api.inaturalist.org/v1/observations?project_id=' || v_proj ||
                       '&per_page=200&order_by=id&order=asc&locale=ru&id_above=' || v_last);
    res := js->'results';
    exit when res is null or jsonb_array_length(res) = 0;

    insert into observations as o
      (id, taxon_id, obs_taxon_id, obs_taxon_name, obs_taxon_rank, obs_common_name,
       observed_on, created_at, lat, lng, place_guess, quality_grade, user_login, user_icon,
       photo_url, uri, identifications_count, region, zone, updated_at)
    select (x->>'id')::bigint,
           case when jsonb_typeof(x->'taxon') <> 'object' then null
                when (x->'taxon'->>'rank_level')::numeric = 10 then (x->'taxon'->>'id')::bigint
                when (x->'taxon'->>'rank_level')::numeric < 10 then
                     coalesce((x->'taxon'->>'min_species_taxon_id')::bigint,
                              (x->'taxon'->'ancestor_ids'->>-2)::bigint)
                else null end,
           (x->'taxon'->>'id')::bigint,
           x->'taxon'->>'name',
           x->'taxon'->>'rank',
           x->'taxon'->>'preferred_common_name',
           (x->>'observed_on')::date,
           (x->>'created_at')::timestamptz,
           case when jsonb_typeof(x->'geojson') = 'object'
                then round((x->'geojson'->'coordinates'->>1)::numeric, 5)::float8 end,
           case when jsonb_typeof(x->'geojson') = 'object'
                then round((x->'geojson'->'coordinates'->>0)::numeric, 5)::float8 end,
           x->>'place_guess',
           x->>'quality_grade',
           x->'user'->>'login',
           x->'user'->>'icon_url',
           replace(x->'photos'->0->>'url', 'square', 'medium'),
           x->>'uri',
           (x->>'identifications_count')::int,
           null, null, now()
    from jsonb_array_elements(res) x
    on conflict (id) do update set
      taxon_id = excluded.taxon_id, obs_taxon_id = excluded.obs_taxon_id,
      obs_taxon_name = excluded.obs_taxon_name, obs_taxon_rank = excluded.obs_taxon_rank,
      obs_common_name = excluded.obs_common_name, observed_on = excluded.observed_on,
      created_at = excluded.created_at, lat = excluded.lat, lng = excluded.lng,
      place_guess = excluded.place_guess, quality_grade = excluded.quality_grade,
      user_login = excluded.user_login, user_icon = excluded.user_icon,
      photo_url = excluded.photo_url, uri = excluded.uri,
      identifications_count = excluded.identifications_count,
      region = null, zone = null, updated_at = now();
    get diagnostics n = row_count;
    total := total + n;

    -- определения
    delete from identifications where observation_id in
      (select (x->>'id')::bigint from jsonb_array_elements(res) x);
    insert into identifications (id, observation_id, user_login, taxon_id, category, current, created_at)
    select (d->>'id')::bigint, (x->>'id')::bigint, d->'user'->>'login', (d->'taxon'->>'id')::bigint,
           d->>'category', (d->>'current')::boolean, (d->>'created_at')::timestamptz
    from jsonb_array_elements(res) x,
         jsonb_array_elements(coalesce(x->'identifications', '[]'::jsonb)) d
    on conflict (id) do nothing;

    v_last := (res->-1->>'id')::bigint;
    update etl_state set value = v_last::text where key = 'last_id';
    perform pg_sleep(1);
  end loop;
  perform etl_assign_areas();
  return format('загружено %s наблюдений, последний id %s', total, v_last);
end $$;

-- ---------- 3. Материализованные представления ----------
-- Территория (scope): kind ∈ all|region|zone, name ('all' для всего Казахстана)
drop materialized view if exists public.mv_scope_species cascade;
create materialized view public.mv_scope_species as
select s.kind, s.name, o.taxon_id, count(*)::int as n
from public.observations o
cross join lateral (values ('all', 'all'), ('region', o.region), ('zone', o.zone)) s(kind, name)
where s.name is not null and o.taxon_id is not null
group by 1, 2, 3;
create unique index on public.mv_scope_species (kind, name, taxon_id);
create index on public.mv_scope_species (kind, name, n desc);

drop materialized view if exists public.mv_scope_observers cascade;
create materialized view public.mv_scope_observers as
select s.kind, s.name, o.user_login,
       count(*)::int as observations, count(distinct o.taxon_id)::int as species,
       max(o.user_icon) as icon
from public.observations o
cross join lateral (values ('all', 'all'), ('region', o.region), ('zone', o.zone)) s(kind, name)
where s.name is not null and o.user_login is not null
group by 1, 2, 3;
create unique index on public.mv_scope_observers (kind, name, user_login);
create index on public.mv_scope_observers (kind, name, observations desc);

drop materialized view if exists public.mv_scope_identifiers cascade;
create materialized view public.mv_scope_identifiers as
select s.kind, s.name, i.user_login, count(*)::int as identifications
from public.identifications i
join public.observations o on o.id = i.observation_id
cross join lateral (values ('all', 'all'), ('region', o.region), ('zone', o.zone)) s(kind, name)
where s.name is not null and i.user_login is not null and i.user_login <> coalesce(o.user_login, '')
group by 1, 2, 3;
create unique index on public.mv_scope_identifiers (kind, name, user_login);
create index on public.mv_scope_identifiers (kind, name, identifications desc);

drop materialized view if exists public.mv_scope_stats cascade;
create materialized view public.mv_scope_stats as
with base as (
  select s.kind, s.name,
         count(*)::int as observations,
         count(distinct o.taxon_id)::int as species,
         count(distinct o.user_login)::int as observers,
         count(*) filter (where o.quality_grade = 'research')::int as research,
         count(*) filter (where o.quality_grade = 'needs_id')::int as needs_id,
         count(*) filter (where o.quality_grade = 'casual')::int as casual,
         max(o.observed_on) as last_observed
  from public.observations o
  cross join lateral (values ('all', 'all'), ('region', o.region), ('zone', o.zone)) s(kind, name)
  where s.name is not null
  group by 1, 2
)
select b.*, coalesce((select count(*) from public.mv_scope_identifiers i
                      where i.kind = b.kind and i.name = b.name), 0)::int as identifiers
from base b;
create unique index on public.mv_scope_stats (kind, name);

drop materialized view if exists public.mv_scope_month cascade;
create materialized view public.mv_scope_month as
select s.kind, s.name,
       coalesce(extract(year from o.observed_on), 0)::int as year,
       coalesce(extract(month from o.observed_on), 0)::int as month,
       count(*)::int as observations, count(distinct o.taxon_id)::int as species
from public.observations o
cross join lateral (values ('all', 'all'), ('region', o.region), ('zone', o.zone)) s(kind, name)
where s.name is not null
group by 1, 2, 3, 4;
create unique index on public.mv_scope_month (kind, name, year, month);

drop materialized view if exists public.mv_scope_family cascade;
create materialized view public.mv_scope_family as
select s.kind, s.name, coalesce(t.family, '—') as family,
       count(distinct o.taxon_id)::int as species, count(*)::int as observations
from public.observations o
join public.taxa t on t.id = o.taxon_id
cross join lateral (values ('all', 'all'), ('region', o.region), ('zone', o.zone)) s(kind, name)
where s.name is not null
group by 1, 2, 3;
create unique index on public.mv_scope_family (kind, name, family);

-- Сетка 0.05° для теплокарты
drop materialized view if exists public.mv_map_cells cascade;
create materialized view public.mv_map_cells as
select s.kind, s.name,
       round((round(o.lng / 0.05) * 0.05)::numeric, 2)::float8 as lng,
       round((round(o.lat / 0.05) * 0.05)::numeric, 2)::float8 as lat,
       count(*)::int as n
from public.observations o
cross join lateral (values ('all', 'all'), ('region', o.region), ('zone', o.zone)) s(kind, name)
where s.name is not null and o.lat is not null
group by 1, 2, 3, 4;
create unique index on public.mv_map_cells (kind, name, lng, lat);

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
  return 'ok ' || now();
end $$;

-- ---------- 4. API для фронтенда (возвращают json, без лимита строк PostgREST) ----------
create or replace function public.api_stats(p_kind text default 'all', p_name text default 'all')
returns json language sql stable as $$
  select coalesce((select row_to_json(s) from public.mv_scope_stats s
                   where s.kind = p_kind and s.name = coalesce(p_name, 'all')),
                  json_build_object('observations', 0, 'species', 0, 'observers', 0, 'identifiers', 0,
                                    'research', 0, 'needs_id', 0, 'casual', 0));
$$;

create or replace function public.api_species(p_kind text default 'all', p_name text default 'all',
    p_q text default null, p_limit int default 48, p_offset int default 0)
returns json language sql stable as $$
  with f as (
    select m.taxon_id, m.n, t.name, t.common_name_ru, t.common_name_en, t.family, t.photo_url, t.inat_url
    from public.mv_scope_species m
    left join public.taxa t on t.id = m.taxon_id
    where m.kind = p_kind and m.name = coalesce(p_name, 'all')
      and (coalesce(p_q, '') = '' or t.name ilike '%' || p_q || '%'
           or t.common_name_ru ilike '%' || p_q || '%' or t.common_name_en ilike '%' || p_q || '%'
           or t.family ilike '%' || p_q || '%')
  )
  select json_build_object(
    'total', (select count(*) from f),
    'rows', coalesce((select json_agg(r) from (
        select * from f order by n desc, name limit p_limit offset p_offset) r), '[]'::json));
$$;

create or replace function public.api_observers(p_kind text default 'all', p_name text default 'all',
    p_sort text default 'observations', p_limit int default 50, p_offset int default 0)
returns json language sql stable as $$
  with f as (select user_login, observations, species, icon from public.mv_scope_observers
             where kind = p_kind and name = coalesce(p_name, 'all'))
  select json_build_object(
    'total', (select count(*) from f),
    'rows', coalesce((select json_agg(r) from (
        select * from f
        order by case when p_sort = 'species' then species else observations end desc, user_login
        limit p_limit offset p_offset) r), '[]'::json));
$$;

create or replace function public.api_identifiers(p_kind text default 'all', p_name text default 'all',
    p_limit int default 50, p_offset int default 0)
returns json language sql stable as $$
  with f as (select user_login, identifications from public.mv_scope_identifiers
             where kind = p_kind and name = coalesce(p_name, 'all'))
  select json_build_object(
    'total', (select count(*) from f),
    'rows', coalesce((select json_agg(r) from (
        select * from f order by identifications desc, user_login limit p_limit offset p_offset) r), '[]'::json));
$$;

create or replace function public.api_observations(p_kind text default 'all', p_name text default 'all',
    p_taxon bigint default null, p_user text default null, p_quality text default null,
    p_q text default null, p_date_from date default null, p_date_to date default null,
    p_limit int default 48, p_offset int default 0)
returns json language sql stable as $$
  with f as (
    select o.id, o.observed_on, o.created_at, o.lat, o.lng, o.place_guess, o.quality_grade,
           o.user_login, o.user_icon, o.photo_url, o.uri, o.identifications_count, o.region, o.zone,
           o.taxon_id, o.obs_taxon_id, o.obs_taxon_name, o.obs_taxon_rank, o.obs_common_name
    from public.observations o
    where (p_kind = 'all' or (p_kind = 'region' and o.region = p_name) or (p_kind = 'zone' and o.zone = p_name))
      and (p_taxon is null or o.taxon_id = p_taxon or o.obs_taxon_id = p_taxon)
      and (p_user is null or o.user_login = p_user)
      and (p_quality is null or o.quality_grade = p_quality)
      and (p_date_from is null or o.observed_on >= p_date_from)
      and (p_date_to is null or o.observed_on <= p_date_to)
      and (coalesce(p_q, '') = '' or o.obs_taxon_name ilike '%' || p_q || '%'
           or o.obs_common_name ilike '%' || p_q || '%')
  )
  select json_build_object(
    'total', (select count(*) from (select 1 from f limit 100000) c),
    'rows', coalesce((select json_agg(r) from (
        select * from f order by id desc limit p_limit offset p_offset) r), '[]'::json));
$$;

create or replace function public.api_map_cells(p_kind text default 'all', p_name text default 'all')
returns json language sql stable as $$
  select coalesce(json_agg(json_build_array(lng, lat, n)), '[]'::json)
  from public.mv_map_cells where kind = p_kind and name = coalesce(p_name, 'all');
$$;

create or replace function public.api_map_points(p_kind text default 'all', p_name text default 'all',
    p_taxon bigint default null, p_user text default null, p_quality text default null,
    p_limit int default 20000)
returns json language sql stable as $$
  select coalesce(json_agg(json_build_array(id, lng, lat,
            coalesce(obs_common_name, obs_taxon_name, '—'), obs_taxon_name, quality_grade,
            user_login, observed_on)), '[]'::json)
  from (
    select * from public.observations o
    where o.lat is not null
      and (p_kind = 'all' or (p_kind = 'region' and o.region = p_name) or (p_kind = 'zone' and o.zone = p_name))
      and (p_taxon is null or o.taxon_id = p_taxon or o.obs_taxon_id = p_taxon)
      and (p_user is null or o.user_login = p_user)
      and (p_quality is null or o.quality_grade = p_quality)
    order by o.id desc limit p_limit
  ) s;
$$;

create or replace function public.api_months(p_kind text default 'all', p_name text default 'all')
returns json language sql stable as $$
  select coalesce(json_agg(r order by year, month), '[]'::json) from (
    select year, month, observations, species from public.mv_scope_month
    where kind = p_kind and name = coalesce(p_name, 'all')) r;
$$;

create or replace function public.api_families(p_kind text default 'all', p_name text default 'all',
    p_limit int default 30)
returns json language sql stable as $$
  select coalesce(json_agg(r), '[]'::json) from (
    select family, species, observations from public.mv_scope_family
    where kind = p_kind and name = coalesce(p_name, 'all')
    order by species desc limit p_limit) r;
$$;

create or replace function public.api_areas(p_kind text default 'region')
returns json language sql stable as $$
  select coalesce(json_agg(r order by r.species desc), '[]'::json) from (
    select a.name, a.name_en, a.geojson,
           coalesce(s.species, 0) as species, coalesce(s.observations, 0) as observations,
           coalesce(s.observers, 0) as observers
    from public.areas a
    left join public.mv_scope_stats s on s.kind = a.kind and s.name = a.name
    where a.kind = p_kind) r;
$$;

create or replace function public.api_taxon(p_id bigint)
returns json language sql stable as $$
  select json_build_object(
    'taxon', (select row_to_json(t) from public.taxa t where t.id = p_id),
    'observations', (select count(*) from public.observations where taxon_id = p_id),
    'observers', (select count(distinct user_login) from public.observations where taxon_id = p_id),
    'months', (select coalesce(json_agg(r order by month), '[]'::json) from (
        select extract(month from observed_on)::int as month, count(*) as n
        from public.observations where taxon_id = p_id and observed_on is not null group by 1) r),
    'areas', (select coalesce(json_agg(r), '[]'::json) from (
        select 'region' as kind, region as name, count(*) as n from public.observations
        where taxon_id = p_id and region is not null group by region
        union all
        select 'zone', zone, count(*) from public.observations
        where taxon_id = p_id and zone is not null group by zone
        order by 3 desc) r),
    'photos', (select coalesce(json_agg(r), '[]'::json) from (
        select id, photo_url, uri, user_login, observed_on from public.observations
        where taxon_id = p_id and photo_url is not null and quality_grade = 'research'
        order by id desc limit 24) r));
$$;

create or replace function public.api_search_taxa(p_q text, p_limit int default 30)
returns json language sql stable as $$
  select coalesce(json_agg(r), '[]'::json) from (
    select t.id, t.name, t.common_name_ru, t.family,
           (select n from public.mv_scope_species m where m.kind = 'all' and m.name = 'all' and m.taxon_id = t.id) as n
    from public.taxa t
    where t.name ilike '%' || p_q || '%' or t.common_name_ru ilike '%' || p_q || '%'
       or t.common_name_en ilike '%' || p_q || '%'
    order by n desc nulls last limit p_limit) r;
$$;

create or replace function public.api_progress()
returns json language sql stable security definer set search_path = public as $$
  select json_build_object(
    'last_id', (select value from etl_state where key = 'last_id'),
    'observations', (select count(*) from observations),
    'taxa', (select count(*) from taxa),
    'stats_refreshed', (select max(observations) from mv_scope_stats where kind = 'all'));
$$;

-- ---------- 5. Права ----------
grant select on public.mv_scope_species, public.mv_scope_observers, public.mv_scope_identifiers,
  public.mv_scope_stats, public.mv_scope_month, public.mv_scope_family, public.mv_map_cells
  to anon, authenticated;
grant execute on function public.api_stats(text, text), public.api_species(text, text, text, int, int),
  public.api_observers(text, text, text, int, int), public.api_identifiers(text, text, int, int),
  public.api_observations(text, text, bigint, text, text, text, date, date, int, int),
  public.api_map_cells(text, text), public.api_map_points(text, text, bigint, text, text, int),
  public.api_months(text, text), public.api_families(text, text, int), public.api_areas(text),
  public.api_taxon(bigint), public.api_search_taxa(text, int), public.api_progress()
  to anon, authenticated;
revoke all on function public.etl_refresh_stats() from public, anon, authenticated;

-- ---------- 6. Расписание ----------
select cron.unschedule(jobname) from cron.job where jobname = 'flora-stats';
select cron.schedule('flora-stats', '*/10 * * * *',
  $c$set statement_timeout = 0; select public.etl_refresh_stats();$c$);

-- ---------- 7. Перезапуск загрузки ----------
-- полная перезагрузка, чтобы заполнить новые поля (фото автора, место, определения и т.д.);
-- уже загруженные строки не удаляются, а обновляются
update public.etl_state set value = '0' where key = 'last_id';
select cron.unschedule(jobname) from cron.job where jobname = 'flora-load';
select cron.schedule('flora-load', '*/3 * * * *',
  $c$set statement_timeout = 0; select public.etl_load_observations(40); select public.etl_load_taxa(15);$c$);

select 'v2 ok' as status, (select count(*) from cron.job where jobname like 'flora%') as cron_jobs;

-- =============================================================
-- Флора Казахстана — схема базы данных Supabase
-- Выполнить один раз: Supabase → SQL Editor → New query → Run
-- =============================================================

create table if not exists public.taxa (
    id              bigint primary key,          -- iNaturalist taxon id
    name            text not null,               -- латинское название
    rank            text,
    common_name_ru  text,
    common_name_en  text,
    family          text,
    genus           text,
    photo_url       text,
    wikipedia_url   text,
    inat_url        text,
    updated_at      timestamptz default now()
);

create table if not exists public.observations (
    id            bigint primary key,            -- iNaturalist observation id
    taxon_id      bigint not null,               -- вид (подвиды сведены к виду)
    observed_on   date,
    lat           double precision,
    lng           double precision,
    quality_grade text,
    user_login    text,
    photo_url     text,
    uri           text,
    region        text,                          -- область
    zone          text,                          -- природная зона
    updated_at    timestamptz default now()
);

create index if not exists obs_taxon_idx  on public.observations (taxon_id);
create index if not exists obs_region_idx on public.observations (region);
create index if not exists obs_zone_idx   on public.observations (zone);
create index if not exists taxa_family_idx on public.taxa (family);

create table if not exists public.areas (
    id       serial primary key,
    kind     text not null check (kind in ('region', 'zone')),
    name     text not null,
    name_en  text,
    geojson  jsonb not null,                     -- geometry (Polygon/MultiPolygon)
    unique (kind, name)
);

-- ---------- Представления ----------

create or replace view public.project_stats as
select count(*)                    as observations,
       count(distinct taxon_id)    as species,
       count(distinct user_login)  as observers,
       max(observed_on)            as last_observed
from public.observations;

create or replace view public.area_stats as
select 'region'::text as kind, region as name,
       count(distinct taxon_id) as species,
       count(*) as observations,
       count(distinct user_login) as observers
from public.observations where region is not null group by region
union all
select 'zone', zone,
       count(distinct taxon_id), count(*), count(distinct user_login)
from public.observations where zone is not null group by zone;

create or replace view public.family_stats as
select coalesce(t.family, '—') as family,
       count(distinct o.taxon_id) as species,
       count(*) as observations
from public.observations o
left join public.taxa t on t.id = o.taxon_id
group by 1;

create or replace view public.observer_stats as
select user_login, count(*) as observations, count(distinct taxon_id) as species
from public.observations group by user_login;

create or replace view public.taxon_areas as
select taxon_id, 'region'::text as kind, region as name, count(*) as observations
from public.observations where region is not null group by taxon_id, region
union all
select taxon_id, 'zone', zone, count(*)
from public.observations where zone is not null group by taxon_id, zone;

-- ---------- Список видов для территории ----------
-- p_kind: 'all' | 'region' | 'zone';  p_name: название области/зоны
create or replace function public.species_list(
    p_kind text default 'all',
    p_name text default null,
    p_q text default null,
    p_limit int default 48,
    p_offset int default 0
)
returns table (
    id bigint, name text, common_name_ru text, common_name_en text,
    family text, photo_url text, inat_url text,
    observations bigint, total_count bigint
)
language sql stable
as $$
    with obs as (
        select o.taxon_id
        from public.observations o
        where p_kind = 'all'
           or (p_kind = 'region' and o.region = p_name)
           or (p_kind = 'zone'   and o.zone   = p_name)
    ),
    agg as (
        select taxon_id, count(*) as n from obs group by taxon_id
    ),
    res as (
        select t.id, t.name, t.common_name_ru, t.common_name_en, t.family,
               t.photo_url, t.inat_url, a.n as observations
        from agg a join public.taxa t on t.id = a.taxon_id
        where p_q is null or p_q = ''
           or t.name ilike '%' || p_q || '%'
           or t.common_name_ru ilike '%' || p_q || '%'
           or t.family ilike '%' || p_q || '%'
    )
    select r.*, count(*) over () as total_count
    from res r
    order by r.observations desc, r.name
    limit p_limit offset p_offset;
$$;

-- ---------- Доступ: только чтение для anon ----------
alter table public.taxa         enable row level security;
alter table public.observations enable row level security;
alter table public.areas        enable row level security;

drop policy if exists "public read taxa" on public.taxa;
drop policy if exists "public read obs"  on public.observations;
drop policy if exists "public read areas" on public.areas;
create policy "public read taxa"  on public.taxa         for select using (true);
create policy "public read obs"   on public.observations for select using (true);
create policy "public read areas" on public.areas        for select using (true);

grant select on public.project_stats, public.area_stats, public.family_stats,
                public.observer_stats, public.taxon_areas to anon, authenticated;
grant execute on function public.species_list(text, text, text, int, int) to anon, authenticated;

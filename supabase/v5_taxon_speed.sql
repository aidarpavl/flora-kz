-- =============================================================
-- Флора Казахстана — ускорение карточки вида и поиска (v5)
-- =============================================================
create or replace function public.api_taxon(p_id bigint)
returns json language sql stable as $$
  select json_build_object(
    'taxon', (select row_to_json(t) from public.taxa t where t.id = p_id),
    'observations', coalesce((select n from public.mv_scope_species
                              where kind = 'all' and name = 'all' and taxon_id = p_id), 0),
    'observers', (select count(distinct user_login) from public.mv_points where taxon_id = p_id),
    'months', (select coalesce(json_agg(r order by month), '[]'::json) from (
        select extract(month from observed_on)::int as month, count(*) as n
        from public.mv_points where taxon_id = p_id and observed_on is not null group by 1) r),
    'areas', (select coalesce(json_agg(r order by r.n desc), '[]'::json) from (
        select kind, name, n from public.mv_scope_species
        where taxon_id = p_id and kind in ('region', 'zone')) r),
    'photos', (select coalesce(json_agg(r), '[]'::json) from (
        select id, photo_url, uri, user_login, observed_on from public.observations
        where taxon_id = p_id and photo_url is not null and quality_grade = 'research'
        order by id desc limit 24) r));
$$;

create index if not exists mv_scope_species_taxon_idx on public.mv_scope_species (taxon_id);

create or replace function public.api_species(p_kind text default 'all', p_name text default 'all',
    p_q text default null, p_limit int default 48, p_offset int default 0)
returns json language sql stable as $$
  with t as (
    select id, name, common_name_ru, common_name_en, family, photo_url, inat_url from public.taxa
    where coalesce(p_q, '') = '' or name ilike '%' || p_q || '%' or common_name_ru ilike '%' || p_q || '%'
       or common_name_en ilike '%' || p_q || '%' or family ilike '%' || p_q || '%'
  ),
  f as (
    select m.taxon_id, m.n, t.name, t.common_name_ru, t.common_name_en, t.family, t.photo_url, t.inat_url
    from public.mv_scope_species m join t on t.id = m.taxon_id
    where m.kind = p_kind and m.name = coalesce(p_name, 'all')
  )
  select json_build_object(
    'total', (select count(*) from f),
    'rows', coalesce((select json_agg(r) from (
        select * from f order by n desc, name limit p_limit offset p_offset) r), '[]'::json));
$$;

create or replace function public.api_progress()
returns json language sql stable security definer set search_path = public as $$
  select json_build_object(
    'last_id', (select value from etl_state where key = 'last_id'),
    'observations', (select observations from mv_scope_stats where kind = 'all' and name = 'all'),
    'taxa', (select count(*) from taxa));
$$;

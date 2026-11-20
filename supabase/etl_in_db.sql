-- =============================================================
-- Флора Казахстана — загрузка данных iNaturalist ВНУТРИ Supabase
-- (без ключей и GitHub Actions: расширения http + postgis + pg_cron)
-- Выполнить один раз в SQL Editor после schema.sql
-- =============================================================
create extension if not exists http with schema extensions;
create extension if not exists postgis with schema extensions;
create extension if not exists pg_cron;

alter table public.areas add column if not exists geom extensions.geometry(Geometry, 4326);
create index if not exists areas_geom_idx on public.areas using gist (geom);

create table if not exists public.etl_state (key text primary key, value text);
insert into public.etl_state values ('last_id', '0'), ('project', 'flora-kazahstana') on conflict do nothing;
alter table public.etl_state enable row level security;

-- HTTP GET → jsonb
create or replace function public.etl_http_get(p_url text) returns jsonb
language plpgsql security definer set search_path = public, extensions as $$
declare r extensions.http_response;
begin
  perform extensions.http_set_curlopt('CURLOPT_TIMEOUT', '60');
  r := extensions.http_get(p_url);
  if r.status <> 200 then
    raise exception 'HTTP % for %: %', r.status, p_url, left(r.content, 200);
  end if;
  return r.content::jsonb;
end $$;

-- Английские названия областей → русские
create or replace function public.etl_region_ru(en text) returns text
language sql immutable as $$
select case
  when l ~ 'north kazakh'                then 'Северо-Казахстанская область'
  when l ~ 'west kazakh'                 then 'Западно-Казахстанская область'
  when l ~ 'east kazakh'                 then 'Восточно-Казахстанская область'
  when l ~ 'south kazakh|turkist'        then 'Туркестанская область'
  when l ~ 'akmol|aqmol'                 then 'Акмолинская область'
  when l ~ 'aktob|aqtob|aqtöb'           then 'Актюбинская область'
  when l ~ 'atyra'                       then 'Атырауская область'
  when l ~ 'jambyl|zhambyl'              then 'Жамбылская область'
  when l ~ 'karagand|qaragand'           then 'Карагандинская область'
  when l ~ 'kostanay|qostanay'           then 'Костанайская область'
  when l ~ 'kyzylord|qyzylord'           then 'Кызылординская область'
  when l ~ 'mangy|manggy|mangis'         then 'Мангистауская область'
  when l ~ 'pavlodar'                    then 'Павлодарская область'
  when l ~ 'abai|abay'                   then 'область Абай'
  when l ~ 'jetis|zhetys'                then 'область Жетысу'
  when l ~ 'ulytau'                      then 'область Улытау'
  when l ~ 'shymkent'                    then 'г. Шымкент'
  when l ~ 'astana|nur-sultan'           then 'г. Астана'
  when l ~ 'baikonur|bayqo'              then 'г. Байконур'
  when l in ('almaty', 'almaty city')    then 'г. Алматы'
  when l ~ 'almaty'                      then 'Алматинская область'
  else en end
from (select lower(trim(en)) as l) s $$;

-- Области (geoBoundaries) + природные зоны (схематичные, обрезаются по границе)
create or replace function public.etl_load_areas() returns text
language plpgsql security definer set search_path = public, extensions as $$
declare meta jsonb; fc jsonb; zones jsonb;
begin
  meta := etl_http_get('https://www.geoboundaries.org/api/current/gbOpen/KAZ/ADM1/');
  fc := etl_http_get(meta->>'simplifiedGeometryGeoJSON');

  delete from areas where kind = 'region';
  insert into areas (kind, name, name_en, geojson, geom)
  select 'region', etl_region_ru(en), min(en), '{}'::jsonb,
         ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_Union(g)), 3))
  from (
    select f->'properties'->>'shapeName' as en,
           ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON((f->'geometry')::text), 4326)) as g
    from jsonb_array_elements(fc->'features') f
  ) s
  group by etl_region_ru(en);

  zones := '{"type":"FeatureCollection","features":[
{"properties":{"name":"Лесостепь","name_en":"Forest-steppe","type":"lat"},"geometry":{"type":"Polygon","coordinates":[[[46.0,54.6],[55,54.2],[60,53.9],[65,53.8],[70,53.6],[75,53.4],[78,53.2],[88.0,52.8],[88.0,56.0],[46.0,56.0],[46.0,54.6]]]}},
{"properties":{"name":"Степь","name_en":"Steppe","type":"lat"},"geometry":{"type":"Polygon","coordinates":[[[46.0,49.6],[50,50.1],[54,49.9],[58,49.5],[62,49.1],[66,49.2],[70,49.3],[74,49.2],[78,49.4],[88.0,49.6],[88.0,52.8],[78,53.2],[75,53.4],[70,53.6],[65,53.8],[60,53.9],[55,54.2],[46.0,54.6],[46.0,49.6]]]}},
{"properties":{"name":"Полупустыня","name_en":"Semi-desert","type":"lat"},"geometry":{"type":"Polygon","coordinates":[[[46.0,47.6],[50,47.6],[54,47.3],[58,47.0],[62,46.9],[66,46.9],[70,46.9],[74,46.6],[78,46.5],[82,46.8],[88.0,47.0],[88.0,49.6],[78,49.4],[74,49.2],[70,49.3],[66,49.2],[62,49.1],[58,49.5],[54,49.9],[50,50.1],[46.0,49.6],[46.0,47.6]]]}},
{"properties":{"name":"Пустыня","name_en":"Desert","type":"lat"},"geometry":{"type":"Polygon","coordinates":[[[46.0,40.0],[88.0,40.0],[88.0,47.0],[82,46.8],[78,46.5],[74,46.6],[70,46.9],[66,46.9],[62,46.9],[58,47.0],[54,47.3],[50,47.6],[46.0,47.6],[46.0,40.0]]]}},
{"properties":{"name":"Алтай","name_en":"Altai","type":"mountain"},"geometry":{"type":"Polygon","coordinates":[[[82.6,49.7],[83.4,50.6],[84.3,51.2],[85.6,50.9],[86.8,50.1],[87.4,49.2],[86.3,48.7],[85.2,48.9],[84.0,49.1],[82.6,49.7]]]}},
{"properties":{"name":"Саур-Тарбагатай","name_en":"Saur-Tarbagatai","type":"mountain"},"geometry":{"type":"Polygon","coordinates":[[[79.8,47.0],[81.0,47.5],[82.8,47.7],[84.2,47.6],[85.4,47.5],[86.0,47.2],[85.5,46.9],[84.0,47.1],[82.5,46.9],[80.8,46.7],[79.8,47.0]]]}},
{"properties":{"name":"Джунгарский Алатау","name_en":"Dzungarian Alatau","type":"mountain"},"geometry":{"type":"Polygon","coordinates":[[[77.8,45.0],[78.6,45.6],[80.0,45.9],[81.2,45.6],[82.6,45.3],[82.3,44.8],[80.6,44.6],[79.3,44.4],[78.2,44.6],[77.8,45.0]]]}},
{"properties":{"name":"Северный Тянь-Шань","name_en":"Northern Tien Shan","type":"mountain"},"geometry":{"type":"Polygon","coordinates":[[[69.0,41.4],[70.0,42.2],[70.9,42.7],[71.8,42.9],[73.4,43.0],[74.9,43.05],[76.2,43.3],[77.4,43.4],[78.6,43.35],[79.6,43.2],[80.5,43.0],[80.4,42.4],[79.0,42.5],[76.5,42.6],[74.0,42.5],[71.8,42.0],[70.6,41.4],[69.6,41.0],[69.0,41.4]]]}},
{"properties":{"name":"Каратау","name_en":"Karatau","type":"mountain"},"geometry":{"type":"Polygon","coordinates":[[[67.9,44.1],[68.6,44.2],[69.6,43.6],[70.5,43.0],[70.4,42.6],[69.6,42.9],[68.7,43.4],[67.9,44.1]]]}}
]}';

  delete from areas where kind = 'zone';
  with kz as (select ST_Union(geom) g from areas where kind = 'region'),
  raw as (
    select f->'properties'->>'name' as name, f->'properties'->>'name_en' as en,
           f->'properties'->>'type' as typ,
           ST_SetSRID(ST_GeomFromGeoJSON((f->'geometry')::text), 4326) as g
    from jsonb_array_elements(zones->'features') f
  ),
  mtn as (select ST_Union(g) g from raw where typ = 'mountain')
  insert into areas (kind, name, name_en, geojson, geom)
  select 'zone', r.name, r.en, '{}'::jsonb,
         ST_Multi(ST_CollectionExtract(ST_MakeValid(
           case when r.typ = 'mountain' then ST_Intersection(r.g, kz.g)
                else ST_Difference(ST_Intersection(r.g, kz.g), mtn.g) end), 3))
  from raw r, kz, mtn;

  update areas set geojson = ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, 0.01), 4)::jsonb;
  update observations set region = null, zone = null;
  perform etl_assign_areas();
  return (select count(*) filter (where kind='region') || ' областей, ' ||
                 count(*) filter (where kind='zone') || ' зон' from areas);
end $$;

-- Область и зона для наблюдений без привязки
create or replace function public.etl_assign_areas() returns void
language plpgsql security definer set search_path = public, extensions as $$
begin
  update observations o set region = a.name
  from areas a
  where o.region is null and o.lat is not null and a.kind = 'region'
    and ST_Intersects(a.geom, ST_SetSRID(ST_MakePoint(o.lng, o.lat), 4326));
  update observations o set zone = a.name
  from areas a
  where o.zone is null and o.lat is not null and a.kind = 'zone'
    and ST_Intersects(a.geom, ST_SetSRID(ST_MakePoint(o.lng, o.lat), 4326));
end $$;

-- Наблюдения: p_pages страниц по 200, продолжая с последнего id
create or replace function public.etl_load_observations(p_pages int default 40) returns text
language plpgsql security definer set search_path = public, extensions as $$
declare v_last bigint; v_proj text; js jsonb; res jsonb; i int; total int := 0; n int;
begin
  if not pg_try_advisory_xact_lock(424242) then return 'уже выполняется'; end if;
  select value::bigint into v_last from etl_state where key = 'last_id';
  select value into v_proj from etl_state where key = 'project';
  for i in 1..p_pages loop
    js := etl_http_get('https://api.inaturalist.org/v1/observations?project_id=' || v_proj ||
                       '&per_page=200&order_by=id&order=asc&id_above=' || v_last);
    res := js->'results';
    exit when res is null or jsonb_array_length(res) = 0;

    insert into observations as o
      (id, taxon_id, observed_on, lat, lng, quality_grade, user_login, photo_url, uri, region, zone, updated_at)
    select id, sid, observed_on, lat, lng, qg, login, photo, uri, null, null, now()
    from (
      select (x->>'id')::bigint as id,
             case when (x->'taxon'->>'rank_level')::numeric = 10 then (x->'taxon'->>'id')::bigint
                  else coalesce((x->'taxon'->>'min_species_taxon_id')::bigint,
                                (x->'taxon'->'ancestor_ids'->>-2)::bigint) end as sid,
             (x->>'observed_on')::date as observed_on,
             round((x->'geojson'->'coordinates'->>1)::numeric, 5)::float8 as lat,
             round((x->'geojson'->'coordinates'->>0)::numeric, 5)::float8 as lng,
             x->>'quality_grade' as qg,
             x->'user'->>'login' as login,
             replace(x->'photos'->0->>'url', 'square', 'medium') as photo,
             x->>'uri' as uri
      from jsonb_array_elements(res) x
      where jsonb_typeof(x->'taxon') = 'object'
        and (x->'taxon'->>'rank_level')::numeric <= 10
        and jsonb_typeof(x->'geojson') = 'object'
    ) s
    where sid is not null
    on conflict (id) do update set
      taxon_id = excluded.taxon_id, observed_on = excluded.observed_on,
      lat = excluded.lat, lng = excluded.lng, quality_grade = excluded.quality_grade,
      user_login = excluded.user_login, photo_url = excluded.photo_url,
      region = null, zone = null, updated_at = now();
    get diagnostics n = row_count;
    total := total + n;

    v_last := (res->-1->>'id')::bigint;
    update etl_state set value = v_last::text where key = 'last_id';
    perform pg_sleep(1);
  end loop;
  perform etl_assign_areas();
  return format('загружено %s наблюдений, последний id %s', total, v_last);
end $$;

-- Сведения о видах (русские названия, семейство, фото)
create or replace function public.etl_load_taxa(p_batches int default 15) returns int
language plpgsql security definer set search_path = public, extensions as $$
declare ids bigint[]; js jsonb; i int; total int := 0;
begin
  for i in 1..p_batches loop
    select array_agg(taxon_id) into ids from (
      select distinct o.taxon_id from observations o
      left join taxa t on t.id = o.taxon_id
      where t.id is null limit 30) s;
    exit when ids is null;
    js := etl_http_get('https://api.inaturalist.org/v1/taxa/' || array_to_string(ids, ',') || '?locale=ru');
    insert into taxa (id, name, rank, common_name_ru, common_name_en, family, genus,
                      photo_url, wikipedia_url, inat_url, updated_at)
    select (t->>'id')::bigint, t->>'name', t->>'rank',
           t->>'preferred_common_name', t->>'english_common_name',
           (select a->>'name' from jsonb_array_elements(coalesce(t->'ancestors','[]')) a where a->>'rank' = 'family' limit 1),
           (select a->>'name' from jsonb_array_elements(coalesce(t->'ancestors','[]')) a where a->>'rank' = 'genus' limit 1),
           t->'default_photo'->>'medium_url', t->>'wikipedia_url',
           'https://www.inaturalist.org/taxa/' || (t->>'id'), now()
    from jsonb_array_elements(js->'results') t
    on conflict (id) do update set
      name = excluded.name, rank = excluded.rank, common_name_ru = excluded.common_name_ru,
      common_name_en = excluded.common_name_en, family = excluded.family, genus = excluded.genus,
      photo_url = excluded.photo_url, wikipedia_url = excluded.wikipedia_url, updated_at = now();
    -- виды, которых нет в ответе (удалены/объединены), чтобы не запрашивать их бесконечно
    insert into taxa (id, name, inat_url) select x, 'taxon ' || x, 'https://www.inaturalist.org/taxa/' || x
    from unnest(ids) x on conflict do nothing;
    total := total + array_length(ids, 1);
    perform pg_sleep(1);
  end loop;
  return total;
end $$;

-- Прогресс загрузки
create or replace view public.etl_progress as
select (select value from etl_state where key = 'last_id') as last_id,
       (select count(*) from observations) as observations,
       (select count(*) from taxa) as taxa,
       (select count(*) from observations where region is null) as without_region;

revoke all on function public.etl_load_observations(int), public.etl_load_taxa(int),
  public.etl_load_areas(), public.etl_assign_areas(), public.etl_http_get(text) from public, anon, authenticated;

-- Расписание: каждые 3 минуты — следующая порция; по воскресеньям — полное обновление
select cron.unschedule(jobname) from cron.job where jobname in ('flora-load', 'flora-weekly-full');
select cron.schedule('flora-load', '*/3 * * * *',
  $c$set statement_timeout = 0; select public.etl_load_observations(40); select public.etl_load_taxa(15);$c$);
select cron.schedule('flora-weekly-full', '17 21 * * 0',
  $c$update public.etl_state set value = '0' where key = 'last_id';$c$);

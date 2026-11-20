-- =============================================================
-- Флора Казахстана — v6
-- 1) 17 областей + 3 города (актуальные границы OpenStreetMap), казахские названия территорий
-- 2) Казахские названия и описания растений (Википедия ru/kk, Викиданные)
-- 3) Редактирование базы и добавление своих наблюдений (по паролю редактора)
-- =============================================================
set statement_timeout = 0;
create extension if not exists pgcrypto with schema extensions;

-- ---------- 1. Территории ----------
alter table public.areas add column if not exists name_kk text;

create table if not exists public.region_list (
  ord int primary key, name_ru text not null, name_kk text not null, query text not null);
alter table public.region_list enable row level security;
truncate public.region_list;
insert into public.region_list values
 (1,'Абайская область','Абай облысы','Абайская область'),
 (2,'Акмолинская область','Ақмола облысы','Акмолинская область'),
 (3,'Актюбинская область','Ақтөбе облысы','Актюбинская область'),
 (4,'Алматинская область','Алматы облысы','Алматинская область'),
 (5,'Атырауская область','Атырау облысы','Атырауская область'),
 (6,'Восточно-Казахстанская область','Шығыс Қазақстан облысы','Восточно-Казахстанская область'),
 (7,'Жамбылская область','Жамбыл облысы','Жамбылская область'),
 (8,'Жетысуская область','Жетісу облысы','Жетысуская область'),
 (9,'Западно-Казахстанская область','Батыс Қазақстан облысы','Западно-Казахстанская область'),
 (10,'Карагандинская область','Қарағанды облысы','Карагандинская область'),
 (11,'Костанайская область','Қостанай облысы','Костанайская область'),
 (12,'Кызылординская область','Қызылорда облысы','Кызылординская область'),
 (13,'Мангистауская область','Маңғыстау облысы','Мангистауская область'),
 (14,'Павлодарская область','Павлодар облысы','Павлодарская область'),
 (15,'Северо-Казахстанская область','Солтүстік Қазақстан облысы','Северо-Казахстанская область'),
 (16,'Туркестанская область','Түркістан облысы','Туркестанская область'),
 (17,'Улытауская область','Ұлытау облысы','Улытауская область'),
 (18,'г. Астана','Астана қаласы','Астана, Казахстан'),
 (19,'г. Алматы','Алматы қаласы','Алматы, Казахстан'),
 (20,'г. Шымкент','Шымкент қаласы','Шымкент, Казахстан');

create or replace function public.etl_load_regions_osm() returns text
language plpgsql security definer set search_path = public, extensions as $$
declare r record; js jsonb; f jsonb; g geometry; n int := 0; missing text := '';
begin
  perform http_set_curlopt('CURLOPT_USERAGENT', 'flora-kz/1.0 (github.com/aidarpavl/flora-kz)');
  perform http_set_curlopt('CURLOPT_TIMEOUT', '60');
  create temp table if not exists tmp_regions (name text, name_kk text, g geometry) on commit drop;
  for r in select * from region_list order by ord loop
    js := (http_get('https://nominatim.openstreetmap.org/search?format=json&polygon_geojson=1&polygon_threshold=0.003&limit=5&accept-language=ru&countrycodes=kz&q='
                    || urlencode(r.query))).content::jsonb;
    f := (select x from jsonb_array_elements(js) x
          where x->'geojson'->>'type' in ('Polygon', 'MultiPolygon')
          order by (x->>'class' = 'boundary') desc, (x->>'place_rank')::int limit 1);
    if f is null then missing := missing || r.name_ru || '; ';
    else
      g := ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON((f->'geojson')::text), 4326)), 3));
      insert into tmp_regions values (r.name_ru, r.name_kk, g);
      n := n + 1;
    end if;
    perform pg_sleep(1.2);   -- правила Nominatim: не чаще 1 запроса в секунду
  end loop;
  if n < 17 then
    raise exception 'Загружено только % территорий, не найдены: %', n, missing;
  end if;
  -- области не должны перекрывать города: вычитаем города из областей
  if exists (select 1 from tmp_regions x where x.name like 'г. %') then
    update tmp_regions t set g = ST_Multi(ST_CollectionExtract(ST_Difference(t.g,
        (select ST_Union(c.g) from tmp_regions c where c.name like 'г. %')), 3))
    where t.name not like 'г. %';
  end if;
  delete from areas where kind = 'region';
  insert into areas (kind, name, name_en, name_kk, geojson, geom)
  select 'region', tr.name, null, tr.name_kk, ST_AsGeoJSON(ST_SimplifyPreserveTopology(tr.g, 0.005), 4)::jsonb, tr.g
  from tmp_regions tr;
  return n || ' территорий загружено' || case when missing <> '' then ', не найдены: ' || missing else '' end;
end $$;

-- природные зоны: казахские названия
create or replace function public.etl_zone_kk() returns void language sql as $$
  update public.areas a set name_kk = z.kk from (values
    ('Лесостепь','Орманды дала'), ('Степь','Дала'), ('Полупустыня','Шөлейт'), ('Пустыня','Шөл'),
    ('Алтай','Алтай'), ('Саур-Тарбагатай','Сауыр-Тарбағатай'), ('Джунгарский Алатау','Жоңғар Алатауы'),
    ('Северный Тянь-Шань','Солтүстік Тянь-Шань'), ('Каратау','Қаратау')) z(ru, kk)
  where a.kind = 'zone' and a.name = z.ru;
$$;

-- пересчёт зон по новой границе страны и привязка всех наблюдений
create or replace function public.etl_rebuild_zones_and_assign() returns text
language plpgsql security definer set search_path = public, extensions as $$
begin
  -- зоны были обрезаны по старой границе; обрезаем заново по новой
  with kz as (select ST_Union(geom) g from areas where kind = 'region')
  update areas a set geom = ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_Intersection(a.geom, kz.g)), 3)),
                     geojson = ST_AsGeoJSON(ST_SimplifyPreserveTopology(ST_Intersection(a.geom, kz.g), 0.01), 4)::jsonb
  from kz where a.kind = 'zone';
  perform etl_zone_kk();
  update observations set region = null where region is not null;
  update observations o set region = a.name from areas a
   where a.kind = 'region' and o.lat is not null and ST_Intersects(a.geom, ST_SetSRID(ST_MakePoint(o.lng, o.lat), 4326));
  -- точки чуть за границей (берег, погрешность GPS) — ближайшая область в пределах ~10 км
  update observations o set region = (select a.name from areas a where a.kind = 'region'
        order by a.geom <-> ST_SetSRID(ST_MakePoint(o.lng, o.lat), 4326) limit 1)
   where o.region is null and o.lat is not null
     and exists (select 1 from areas a where a.kind = 'region'
                 and ST_DWithin(a.geom, ST_SetSRID(ST_MakePoint(o.lng, o.lat), 4326), 0.1));
  return (select count(*) filter (where region is not null) || ' из ' || count(*) || ' наблюдений привязано к областям'
          from observations);
end $$;

-- ---------- 2. Казахские названия и описания растений ----------
alter table public.taxa
  add column if not exists common_name_kk text,
  add column if not exists description_ru text,
  add column if not exists description_kk text,
  add column if not exists wiki_ru_url text,
  add column if not exists wiki_kk_url text,
  add column if not exists wiki_checked_at timestamptz,
  add column if not exists edited_by text,
  add column if not exists edited_at timestamptz,
  add column if not exists is_user_taxon boolean default false,
  add column if not exists parent_name text;

-- одна запись: Википедия ru → (ссылка kk) → Википедия kk; Викиданные — казахское название
create or replace function public.etl_fetch_wiki_one(p_id bigint) returns text
language plpgsql security definer set search_path = public, extensions as $$
declare t record; js jsonb; pg jsonb; kk_title text; kkjs jsonb; kkpg jsonb; wd jsonb; kk_label text;
begin
  select * into t from taxa where id = p_id;
  if t is null then return 'нет вида'; end if;
  perform http_set_curlopt('CURLOPT_USERAGENT', 'flora-kz/1.0 (github.com/aidarpavl/flora-kz)');
  perform http_set_curlopt('CURLOPT_TIMEOUT', '20');
  js := (http_get('https://ru.wikipedia.org/w/api.php?action=query&format=json&redirects=1&prop=extracts|langlinks|info&inprop=url&exintro=1&explaintext=1&lllang=kk&titles='
                  || urlencode(t.name))).content::jsonb;
  select v into pg from jsonb_each(js->'query'->'pages') e(k, v) where k <> '-1' limit 1;
  if pg is null and t.common_name_ru is not null then
    js := (http_get('https://ru.wikipedia.org/w/api.php?action=query&format=json&redirects=1&prop=extracts|langlinks|info&inprop=url&exintro=1&explaintext=1&lllang=kk&titles='
                    || urlencode(t.common_name_ru))).content::jsonb;
    select v into pg from jsonb_each(js->'query'->'pages') e(k, v) where k <> '-1' limit 1;
  end if;
  kk_title := pg->'langlinks'->0->>'*';
  if kk_title is null then  -- прямой поиск статьи в казахской Википедии по латинскому названию
    kkjs := (http_get('https://kk.wikipedia.org/w/api.php?action=query&format=json&redirects=1&prop=extracts|info&inprop=url&exintro=1&explaintext=1&titles='
                      || urlencode(t.name))).content::jsonb;
  else
    kkjs := (http_get('https://kk.wikipedia.org/w/api.php?action=query&format=json&redirects=1&prop=extracts|info&inprop=url&exintro=1&explaintext=1&titles='
                      || urlencode(kk_title))).content::jsonb;
  end if;
  select v into kkpg from jsonb_each(kkjs->'query'->'pages') e(k, v) where k <> '-1' limit 1;
  -- Викиданные: казахская подпись таксона
  begin
    wd := (http_get('https://query.wikidata.org/sparql?format=json&query=' || urlencode(
            'SELECT ?kk WHERE { ?i wdt:P225 "' || replace(t.name, '"', '') || '" . ?i rdfs:label ?kk FILTER(lang(?kk)="kk") } LIMIT 1'))).content::jsonb;
    kk_label := wd->'results'->'bindings'->0->'kk'->>'value';
  exception when others then kk_label := null;
  end;
  if kk_label = t.name then kk_label := null; end if;   -- латинская подпись нам не нужна
  update taxa set
    description_ru = coalesce(nullif(pg->>'extract', ''), description_ru),
    wiki_ru_url = coalesce(pg->>'fullurl', wiki_ru_url, wikipedia_url),
    description_kk = coalesce(nullif(kkpg->>'extract', ''), description_kk),
    wiki_kk_url = coalesce(kkpg->>'fullurl', wiki_kk_url),
    common_name_kk = coalesce(common_name_kk, kk_label,
                              case when kkpg->>'title' is not null and kkpg->>'title' <> t.name then kkpg->>'title' end),
    wiki_checked_at = now()
  where id = p_id;
  return 'ok';
end $$;

create or replace function public.etl_load_wiki(p_count int default 25) returns int
language plpgsql security definer set search_path = public, extensions as $$
declare r record; n int := 0;
begin
  if not pg_try_advisory_xact_lock(424243) then return 0; end if;
  for r in
    select t.id from taxa t
    left join mv_scope_species m on m.kind = 'all' and m.name = 'all' and m.taxon_id = t.id
    where t.wiki_checked_at is null and t.name not like 'taxon %'
    order by m.n desc nulls last limit p_count
  loop
    begin
      perform etl_fetch_wiki_one(r.id);
    exception when others then
      update taxa set wiki_checked_at = now() where id = r.id;  -- не застревать на ошибке
    end;
    n := n + 1;
    perform pg_sleep(0.3);
  end loop;
  return n;
end $$;

-- загрузчик видов: + казахское название из iNaturalist (если есть)
create or replace function public.etl_load_taxa(p_batches int default 15) returns int
language plpgsql security definer set search_path = public, extensions as $$
declare ids bigint[]; js jsonb; i int; total int := 0;
begin
  for i in 1..p_batches loop
    select array_agg(taxon_id) into ids from (
      select distinct o.taxon_id from observations o
      left join taxa t on t.id = o.taxon_id
      where o.taxon_id is not null and t.id is null limit 30) s;
    exit when ids is null;
    js := etl_http_get('https://api.inaturalist.org/v1/taxa/' || array_to_string(ids, ',') || '?locale=ru&all_names=true');
    insert into taxa (id, name, rank, common_name_ru, common_name_en, common_name_kk, family, genus,
                      photo_url, wikipedia_url, inat_url, updated_at)
    select (t->>'id')::bigint, t->>'name', t->>'rank',
           t->>'preferred_common_name', t->>'english_common_name',
           (select n->>'name' from jsonb_array_elements(coalesce(t->'names','[]')) n where n->>'locale' = 'kk' limit 1),
           (select a->>'name' from jsonb_array_elements(coalesce(t->'ancestors','[]')) a where a->>'rank' = 'family' limit 1),
           (select a->>'name' from jsonb_array_elements(coalesce(t->'ancestors','[]')) a where a->>'rank' = 'genus' limit 1),
           t->'default_photo'->>'medium_url', t->>'wikipedia_url',
           'https://www.inaturalist.org/taxa/' || (t->>'id'), now()
    from jsonb_array_elements(js->'results') t
    on conflict (id) do update set
      name = excluded.name, rank = excluded.rank, common_name_ru = coalesce(taxa.common_name_ru, excluded.common_name_ru),
      common_name_en = excluded.common_name_en, common_name_kk = coalesce(taxa.common_name_kk, excluded.common_name_kk),
      family = excluded.family, genus = excluded.genus,
      photo_url = excluded.photo_url, wikipedia_url = excluded.wikipedia_url, updated_at = now();
    insert into taxa (id, name, inat_url) select x, 'taxon ' || x, 'https://www.inaturalist.org/taxa/' || x
    from unnest(ids) x on conflict do nothing;
    total := total + array_length(ids, 1);
    perform pg_sleep(1);
  end loop;
  return total;
end $$;

-- ---------- 3. Редактирование и свои наблюдения ----------
create table if not exists public.app_secrets (key text primary key, value text not null);
alter table public.app_secrets enable row level security;   -- без политик: anon не видит

create or replace function public.set_editor_password(p_new text) returns text
language sql security definer set search_path = public, extensions as $$
  insert into app_secrets values ('editor_pwd', crypt(p_new, gen_salt('bf')))
  on conflict (key) do update set value = excluded.value;
  select 'пароль редактора установлен';
$$;
revoke all on function public.set_editor_password(text) from public, anon, authenticated;

create or replace function public.check_editor(p_pwd text) returns boolean
language sql stable security definer set search_path = public, extensions as $$
  select coalesce((select value = crypt(coalesce(p_pwd, ''), value) from app_secrets where key = 'editor_pwd'), false);
$$;
revoke all on function public.check_editor(text) from public, anon, authenticated;

create sequence if not exists public.user_taxon_seq start 1;

create table if not exists public.user_observations (
  id bigserial primary key,
  taxon_id bigint,
  taxon_name text,
  subspecies text,
  description_ru text,
  description_kk text,
  lat double precision not null,
  lng double precision not null,
  observed_on date,
  author text,
  region text,
  zone text,
  photo bytea,
  photo_mime text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
alter table public.user_observations enable row level security;
create index if not exists uobs_taxon_idx on public.user_observations (taxon_id);

create or replace function public.trg_uobs_area() returns trigger
language plpgsql security definer set search_path = public, extensions as $$
begin
  new.region := (select name from areas where kind = 'region'
                 and ST_Intersects(geom, ST_SetSRID(ST_MakePoint(new.lng, new.lat), 4326)) limit 1);
  new.zone := (select name from areas where kind = 'zone'
               and ST_Intersects(geom, ST_SetSRID(ST_MakePoint(new.lng, new.lat), 4326)) limit 1);
  new.updated_at := now();
  return new;
end $$;
drop trigger if exists uobs_area on public.user_observations;
create trigger uobs_area before insert or update of lat, lng on public.user_observations
  for each row execute function public.trg_uobs_area();

-- ---------- 4. API (чтение) ----------
create or replace function public.api_areas(p_kind text default 'region')
returns json language sql stable as $$
  select coalesce(json_agg(r order by r.species desc), '[]'::json) from (
    select a.name, a.name_en, a.name_kk, a.geojson,
           coalesce(s.species, 0) as species, coalesce(s.observations, 0) as observations,
           coalesce(s.observers, 0) as observers
    from public.areas a
    left join public.mv_scope_stats s on s.kind = a.kind and s.name = a.name
    where a.kind = p_kind) r;
$$;

create or replace function public.api_species(p_kind text default 'all', p_name text default 'all',
    p_q text default null, p_limit int default 48, p_offset int default 0)
returns json language sql stable as $$
  with t as (
    select id, name, common_name_ru, common_name_en, common_name_kk, family, photo_url, inat_url from public.taxa
    where coalesce(p_q, '') = '' or name ilike '%' || p_q || '%' or common_name_ru ilike '%' || p_q || '%'
       or common_name_en ilike '%' || p_q || '%' or common_name_kk ilike '%' || p_q || '%'
       or family ilike '%' || p_q || '%'
  ),
  f as (
    select m.taxon_id, m.n, t.name, t.common_name_ru, t.common_name_en, t.common_name_kk, t.family, t.photo_url, t.inat_url
    from public.mv_scope_species m join t on t.id = m.taxon_id
    where m.kind = p_kind and m.name = coalesce(p_name, 'all')
  )
  select json_build_object(
    'total', (select count(*) from f),
    'rows', coalesce((select json_agg(r) from (
        select * from f order by n desc, name limit p_limit offset p_offset) r), '[]'::json));
$$;

create or replace function public.api_search_taxa(p_q text, p_limit int default 30)
returns json language sql stable as $$
  select coalesce(json_agg(r), '[]'::json) from (
    select t.id, t.name, t.common_name_ru, t.common_name_kk, t.family, t.rank,
           (select n from public.mv_scope_species m where m.kind = 'all' and m.name = 'all' and m.taxon_id = t.id) as n
    from public.taxa t
    where t.name ilike '%' || p_q || '%' or t.common_name_ru ilike '%' || p_q || '%'
       or t.common_name_en ilike '%' || p_q || '%' or t.common_name_kk ilike '%' || p_q || '%'
    order by n desc nulls last limit p_limit) r;
$$;

create or replace function public.api_user_observations(p_taxon bigint default null, p_kind text default 'all',
    p_name text default 'all', p_limit int default 200)
returns json language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(r), '[]'::json) from (
    select u.id, u.taxon_id, coalesce(t.common_name_ru, u.taxon_name) as name_ru,
           coalesce(t.common_name_kk, t.common_name_ru, u.taxon_name) as name_kk,
           coalesce(t.name, u.taxon_name) as sci, u.subspecies, u.description_ru, u.description_kk,
           u.lat, u.lng, u.observed_on, u.author, u.region, u.zone, u.photo is not null as has_photo, u.created_at
    from public.user_observations u left join public.taxa t on t.id = u.taxon_id
    where (p_taxon is null or u.taxon_id = p_taxon)
      and (p_kind = 'all' or (p_kind = 'region' and u.region = p_name) or (p_kind = 'zone' and u.zone = p_name))
    order by u.id desc limit p_limit) r;
$$;

create or replace function public.api_user_photo(p_id bigint)
returns json language sql stable security definer set search_path = public as $$
  select json_build_object('mime', photo_mime, 'data', encode(photo, 'base64'))
  from public.user_observations where id = p_id and photo is not null;
$$;

-- описание из Википедии по кнопке (только чтение Википедии, запись в описание вида)
create or replace function public.api_fetch_wiki(p_id bigint)
returns json language plpgsql security definer set search_path = public as $$
begin
  perform etl_fetch_wiki_one(p_id);
  return (select json_build_object('description_ru', description_ru, 'description_kk', description_kk,
                                   'common_name_kk', common_name_kk, 'wiki_ru_url', wiki_ru_url,
                                   'wiki_kk_url', wiki_kk_url) from taxa where id = p_id);
end $$;

-- ---------- 5. API (запись, только с паролем редактора) ----------
create or replace function public.api_editor_login(p_pwd text) returns boolean
language sql stable security definer set search_path = public as $$ select check_editor(p_pwd); $$;

create or replace function public.api_edit_taxon(p_pwd text, p_id bigint, p_common_ru text, p_common_kk text,
    p_desc_ru text, p_desc_kk text, p_editor text default null)
returns json language plpgsql security definer set search_path = public as $$
begin
  if not check_editor(p_pwd) then raise exception 'Неверный пароль редактора'; end if;
  update taxa set common_name_ru = nullif(trim(p_common_ru), ''), common_name_kk = nullif(trim(p_common_kk), ''),
                  description_ru = nullif(trim(p_desc_ru), ''), description_kk = nullif(trim(p_desc_kk), ''),
                  edited_by = p_editor, edited_at = now()
  where id = p_id;
  return json_build_object('ok', found);
end $$;

create or replace function public.api_add_taxon(p_pwd text, p_name text, p_rank text, p_common_ru text,
    p_common_kk text, p_family text, p_genus text, p_parent text, p_desc_ru text, p_desc_kk text,
    p_editor text default null)
returns json language plpgsql security definer set search_path = public as $$
declare v_id bigint;
begin
  if not check_editor(p_pwd) then raise exception 'Неверный пароль редактора'; end if;
  if coalesce(trim(p_name), '') = '' then raise exception 'Укажите латинское название'; end if;
  select id into v_id from taxa where lower(name) = lower(trim(p_name)) limit 1;
  if v_id is not null then return json_build_object('ok', false, 'id', v_id, 'message', 'Такой вид уже есть'); end if;
  v_id := -nextval('user_taxon_seq');   -- отрицательные id: собственные виды, не пересекаются с iNaturalist
  insert into taxa (id, name, rank, common_name_ru, common_name_kk, family, genus, parent_name,
                    description_ru, description_kk, is_user_taxon, edited_by, edited_at, wiki_checked_at)
  values (v_id, trim(p_name), coalesce(nullif(p_rank, ''), 'species'), nullif(p_common_ru, ''), nullif(p_common_kk, ''),
          nullif(p_family, ''), nullif(p_genus, ''), nullif(p_parent, ''), nullif(p_desc_ru, ''), nullif(p_desc_kk, ''),
          true, p_editor, now(), now());
  return json_build_object('ok', true, 'id', v_id);
end $$;

create or replace function public.api_add_observation(p_pwd text, p_taxon_id bigint, p_taxon_name text,
    p_subspecies text, p_desc_ru text, p_desc_kk text, p_lat double precision, p_lng double precision,
    p_observed_on date, p_author text, p_photo_b64 text default null, p_photo_mime text default null)
returns json language plpgsql security definer set search_path = public as $$
declare v_id bigint;
begin
  if not check_editor(p_pwd) then raise exception 'Неверный пароль редактора'; end if;
  if p_lat is null or p_lng is null then raise exception 'Отметьте точку на карте'; end if;
  insert into user_observations (taxon_id, taxon_name, subspecies, description_ru, description_kk, lat, lng,
                                 observed_on, author, photo, photo_mime)
  values (p_taxon_id, nullif(p_taxon_name, ''), nullif(p_subspecies, ''), nullif(p_desc_ru, ''), nullif(p_desc_kk, ''),
          p_lat, p_lng, p_observed_on, nullif(p_author, ''),
          case when p_photo_b64 is not null then decode(p_photo_b64, 'base64') end, p_photo_mime)
  returning id into v_id;
  return json_build_object('ok', true, 'id', v_id);
end $$;

create or replace function public.api_edit_observation(p_pwd text, p_id bigint, p_taxon_id bigint,
    p_taxon_name text, p_subspecies text, p_desc_ru text, p_desc_kk text, p_lat double precision,
    p_lng double precision, p_observed_on date, p_author text)
returns json language plpgsql security definer set search_path = public as $$
begin
  if not check_editor(p_pwd) then raise exception 'Неверный пароль редактора'; end if;
  update user_observations set taxon_id = p_taxon_id, taxon_name = nullif(p_taxon_name, ''),
         subspecies = nullif(p_subspecies, ''), description_ru = nullif(p_desc_ru, ''),
         description_kk = nullif(p_desc_kk, ''), lat = p_lat, lng = p_lng, observed_on = p_observed_on,
         author = nullif(p_author, '')
  where id = p_id;
  return json_build_object('ok', found);
end $$;

create or replace function public.api_delete_observation(p_pwd text, p_id bigint)
returns json language plpgsql security definer set search_path = public as $$
begin
  if not check_editor(p_pwd) then raise exception 'Неверный пароль редактора'; end if;
  delete from user_observations where id = p_id;
  return json_build_object('ok', found);
end $$;

grant execute on function public.api_areas(text), public.api_species(text, text, text, int, int),
  public.api_search_taxa(text, int), public.api_user_observations(bigint, text, text, int),
  public.api_user_photo(bigint), public.api_fetch_wiki(bigint), public.api_editor_login(text),
  public.api_edit_taxon(text, bigint, text, text, text, text, text),
  public.api_add_taxon(text, text, text, text, text, text, text, text, text, text, text),
  public.api_add_observation(text, bigint, text, text, text, text, double precision, double precision, date, text, text, text),
  public.api_edit_observation(text, bigint, bigint, text, text, text, text, double precision, double precision, date, text),
  public.api_delete_observation(text, bigint)
  to anon, authenticated;
revoke all on function public.etl_fetch_wiki_one(bigint), public.etl_load_wiki(int),
  public.etl_load_regions_osm(), public.etl_rebuild_zones_and_assign() from public, anon, authenticated;

-- ---------- 6. Расписание ----------
select cron.unschedule(jobname) from cron.job where jobname in ('flora-wiki', 'flora-weekly-full');
select cron.schedule('flora-wiki', '*/2 * * * *',
  $c$set statement_timeout = 0; select public.etl_load_wiki(25);$c$);
-- полная перезагрузка — раз в месяц (экономия дисковых операций бесплатного тарифа)
select cron.schedule('flora-monthly-full', '17 21 1 * *',
  $c$update public.etl_state set value = '0' where key = 'last_id';$c$);

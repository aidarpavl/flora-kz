-- =============================================================
-- Флора Казахстана — v12: раздел «Красная книга Казахстана» (растения)
-- Виды/подвиды, категория (I–V), тексты на русском и казахском, фото,
-- точки находок и ареалы (полигоны), описание из Википедии.
-- Защита редких видов: точные координаты точек видят только редакторы,
-- остальным — округлённые до 0.1° (~10 км).
-- =============================================================
create table if not exists public.red_book_species (
  id bigserial primary key,
  taxon_id bigint,
  latin text not null,
  name_ru text,
  name_kk text,
  rank text not null default 'species',
  parent_latin text,
  family text,
  category text check (category in ('I', 'II', 'III', 'IV', 'V')),
  description_ru text, description_kk text,
  habitat_ru text, habitat_kk text,
  protection_ru text, protection_kk text,
  wiki_ru_url text, wiki_kk_url text,
  photo bytea, photo_mime text,
  user_id bigint references public.app_users(id),
  author text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create unique index if not exists rb_latin_uq on public.red_book_species (lower(latin));

create table if not exists public.red_book_points (
  id bigserial primary key,
  species_id bigint not null references public.red_book_species(id) on delete cascade,
  lat double precision not null, lng double precision not null,
  note_ru text, note_kk text, observed_on date,
  region text, zone text,
  user_id bigint references public.app_users(id),
  created_at timestamptz default now()
);
create index if not exists rbp_species_idx on public.red_book_points (species_id);

create table if not exists public.red_book_ranges (
  id bigserial primary key,
  species_id bigint not null references public.red_book_species(id) on delete cascade,
  geom extensions.geometry(MultiPolygon, 4326) not null,
  note_ru text, note_kk text,
  user_id bigint references public.app_users(id),
  created_at timestamptz default now()
);
create index if not exists rbr_species_idx on public.red_book_ranges (species_id);
create index if not exists rbr_geom_idx on public.red_book_ranges using gist (geom);

alter table public.red_book_species enable row level security;
alter table public.red_book_points enable row level security;
alter table public.red_book_ranges enable row level security;

create or replace function public.trg_rbp_area() returns trigger
language plpgsql security definer set search_path = public, extensions as $$
begin
  new.region := (select name from areas where kind = 'region'
                 and ST_Intersects(geom, ST_SetSRID(ST_MakePoint(new.lng, new.lat), 4326)) limit 1);
  new.zone := (select name from areas where kind = 'zone'
               and ST_Intersects(geom, ST_SetSRID(ST_MakePoint(new.lng, new.lat), 4326)) limit 1);
  return new;
end $$;
drop trigger if exists rbp_area on public.red_book_points;
create trigger rbp_area before insert or update of lat, lng on public.red_book_points
  for each row execute function public.trg_rbp_area();

-- права: редактор/админ — всё; пользователь — только своё
create or replace function public.rb_can_edit(p_auth text, p_species bigint) returns boolean
language plpgsql stable security definer set search_path = public as $$
declare w record;
begin
  select * into w from auth_who(p_auth);
  return w.role in ('editor', 'admin') or exists (select 1 from red_book_species where id = p_species and user_id = w.uid);
end $$;

create or replace function public.rb_is_editor(p_auth text) returns boolean
language plpgsql stable security definer set search_path = public as $$
declare w record;
begin
  if coalesce(p_auth, '') = '' then return false; end if;
  begin
    select * into w from auth_who(p_auth);
  exception when others then return false;
  end;
  return w.role in ('editor', 'admin');
end $$;
revoke all on function public.rb_can_edit(text, bigint), public.rb_is_editor(text) from public, anon, authenticated;

-- ---------- чтение ----------
create or replace function public.api_rb_list(p_kind text default 'all', p_name text default 'all',
    p_q text default null, p_category text default null)
returns json language sql stable security definer set search_path = public, extensions as $$
  select coalesce(json_agg(r order by r.category nulls last, r.latin), '[]'::json) from (
    select s.id, s.latin, s.name_ru, s.name_kk, s.rank, s.parent_latin, s.family, s.category, s.taxon_id,
           s.photo is not null as has_photo, s.author, s.updated_at,
           (select count(*) from red_book_points p where p.species_id = s.id) as n_points,
           (select count(*) from red_book_ranges g where g.species_id = s.id) as n_ranges
    from red_book_species s
    where (coalesce(p_q, '') = '' or s.latin ilike '%' || p_q || '%' or s.name_ru ilike '%' || p_q || '%'
           or s.name_kk ilike '%' || p_q || '%' or s.family ilike '%' || p_q || '%')
      and (coalesce(p_category, '') = '' or s.category = p_category)
      and (p_kind = 'all'
           or exists (select 1 from red_book_points p where p.species_id = s.id
                      and ((p_kind = 'region' and p.region = p_name) or (p_kind = 'zone' and p.zone = p_name)))
           or exists (select 1 from red_book_ranges g join areas a on a.kind = p_kind and a.name = p_name
                      where g.species_id = s.id and ST_Intersects(g.geom, a.geom)))
  ) r;
$$;

create or replace function public.api_rb_get(p_id bigint, p_auth text default null)
returns json language plpgsql stable security definer set search_path = public, extensions as $$
declare ed boolean := rb_is_editor(p_auth);
begin
  return (select json_build_object(
    'species', (select row_to_json(x) from (
        select s.id, s.taxon_id, s.latin, s.name_ru, s.name_kk, s.rank, s.parent_latin, s.family, s.category,
               s.description_ru, s.description_kk, s.habitat_ru, s.habitat_kk, s.protection_ru, s.protection_kk,
               s.wiki_ru_url, s.wiki_kk_url, s.photo is not null as has_photo, s.author, s.created_at, s.updated_at,
               (select login from app_users u where u.id = s.user_id) as owner
        from red_book_species s where s.id = p_id) x),
    'points', (select coalesce(json_agg(json_build_object(
        'id', p.id,
        'lat', case when ed then p.lat else round(p.lat::numeric, 1)::float8 end,
        'lng', case when ed then p.lng else round(p.lng::numeric, 1)::float8 end,
        'note_ru', p.note_ru, 'note_kk', p.note_kk, 'observed_on', p.observed_on,
        'region', p.region, 'zone', p.zone) order by p.id), '[]'::json)
        from red_book_points p where p.species_id = p_id),
    'ranges', (select coalesce(json_agg(json_build_object(
        'id', g.id, 'note_ru', g.note_ru, 'note_kk', g.note_kk,
        'geojson', ST_AsGeoJSON(ST_SimplifyPreserveTopology(g.geom, 0.002), 5)::json,
        'area_km2', round((ST_Area(g.geom::geography) / 1e6)::numeric))), '[]'::json)
        from red_book_ranges g where g.species_id = p_id),
    'precise', ed));
end $$;

create or replace function public.api_rb_map(p_kind text default 'all', p_name text default 'all',
    p_auth text default null)
returns json language plpgsql stable security definer set search_path = public, extensions as $$
declare ed boolean := rb_is_editor(p_auth);
begin
  return json_build_object(
    'points', (select coalesce(json_agg(json_build_array(
        case when ed then p.lat else round(p.lat::numeric, 1)::float8 end,
        case when ed then p.lng else round(p.lng::numeric, 1)::float8 end,
        s.id, s.latin, s.name_ru, s.name_kk, s.category)), '[]'::json)
        from red_book_points p join red_book_species s on s.id = p.species_id
        where p_kind = 'all' or (p_kind = 'region' and p.region = p_name) or (p_kind = 'zone' and p.zone = p_name)),
    'ranges', (select coalesce(json_agg(json_build_object(
        'species_id', s.id, 'latin', s.latin, 'name_ru', s.name_ru, 'name_kk', s.name_kk, 'category', s.category,
        'geojson', ST_AsGeoJSON(ST_SimplifyPreserveTopology(g.geom, 0.005), 4)::json)), '[]'::json)
        from red_book_ranges g join red_book_species s on s.id = g.species_id
        where p_kind = 'all' or exists (select 1 from areas a where a.kind = p_kind and a.name = p_name
                                        and ST_Intersects(a.geom, g.geom))));
end $$;

create or replace function public.api_rb_photo(p_id bigint)
returns json language sql stable security definer set search_path = public as $$
  select json_build_object('mime', photo_mime, 'data', encode(photo, 'base64'))
  from red_book_species where id = p_id and photo is not null;
$$;

-- ---------- запись ----------
create or replace function public.api_rb_save(p_auth text, p_id bigint, p_latin text, p_name_ru text, p_name_kk text,
    p_rank text, p_parent_latin text, p_family text, p_category text,
    p_desc_ru text, p_desc_kk text, p_habitat_ru text, p_habitat_kk text, p_protect_ru text, p_protect_kk text,
    p_photo_b64 text default null, p_photo_mime text default null)
returns json language plpgsql security definer set search_path = public as $$
declare w record; v_id bigint := p_id; v_taxon bigint;
begin
  select * into w from auth_who(p_auth);
  if coalesce(trim(p_latin), '') = '' then raise exception 'Укажите латинское название'; end if;
  if p_photo_b64 is not null and length(p_photo_b64) > 4000000 then raise exception 'Фото слишком большое'; end if;
  select id into v_taxon from taxa where lower(name) = lower(trim(p_latin)) limit 1;
  if v_id is null then
    if exists (select 1 from red_book_species where lower(latin) = lower(trim(p_latin))) then
      raise exception 'Этот вид уже есть в разделе «Красная книга»';
    end if;
    insert into red_book_species (taxon_id, latin, name_ru, name_kk, rank, parent_latin, family, category,
        description_ru, description_kk, habitat_ru, habitat_kk, protection_ru, protection_kk,
        photo, photo_mime, user_id, author)
    values (v_taxon, trim(p_latin), nullif(trim(p_name_ru), ''), nullif(trim(p_name_kk), ''),
        coalesce(nullif(p_rank, ''), 'species'), nullif(trim(p_parent_latin), ''), nullif(trim(p_family), ''),
        nullif(p_category, ''), nullif(p_desc_ru, ''), nullif(p_desc_kk, ''), nullif(p_habitat_ru, ''),
        nullif(p_habitat_kk, ''), nullif(p_protect_ru, ''), nullif(p_protect_kk, ''),
        case when p_photo_b64 is not null then decode(p_photo_b64, 'base64') end, p_photo_mime, w.uid, w.name)
    returning id into v_id;
  else
    if not rb_can_edit(p_auth, v_id) then raise exception 'Можно править только свои записи'; end if;
    update red_book_species set taxon_id = v_taxon, latin = trim(p_latin), name_ru = nullif(trim(p_name_ru), ''),
        name_kk = nullif(trim(p_name_kk), ''), rank = coalesce(nullif(p_rank, ''), 'species'),
        parent_latin = nullif(trim(p_parent_latin), ''), family = nullif(trim(p_family), ''),
        category = nullif(p_category, ''), description_ru = nullif(p_desc_ru, ''), description_kk = nullif(p_desc_kk, ''),
        habitat_ru = nullif(p_habitat_ru, ''), habitat_kk = nullif(p_habitat_kk, ''),
        protection_ru = nullif(p_protect_ru, ''), protection_kk = nullif(p_protect_kk, ''),
        photo = case when p_photo_b64 is not null then decode(p_photo_b64, 'base64') else photo end,
        photo_mime = case when p_photo_b64 is not null then p_photo_mime else photo_mime end,
        updated_at = now()
    where id = v_id;
  end if;
  return json_build_object('ok', true, 'id', v_id);
end $$;

create or replace function public.api_rb_add_point(p_auth text, p_species bigint, p_lat double precision,
    p_lng double precision, p_note_ru text default null, p_note_kk text default null, p_date date default null)
returns json language plpgsql security definer set search_path = public as $$
declare w record; v_id bigint;
begin
  select * into w from auth_who(p_auth);
  if not rb_can_edit(p_auth, p_species) then raise exception 'Можно дополнять только свои записи'; end if;
  if p_lat not between 40 and 56 or p_lng not between 46 and 88 then raise exception 'Точка вне Казахстана'; end if;
  insert into red_book_points (species_id, lat, lng, note_ru, note_kk, observed_on, user_id)
  values (p_species, p_lat, p_lng, nullif(p_note_ru, ''), nullif(p_note_kk, ''), p_date, w.uid) returning id into v_id;
  return json_build_object('ok', true, 'id', v_id);
end $$;

create or replace function public.api_rb_add_range(p_auth text, p_species bigint, p_geojson text,
    p_note_ru text default null, p_note_kk text default null)
returns json language plpgsql security definer set search_path = public, extensions as $$
declare w record; v_id bigint; g geometry;
begin
  select * into w from auth_who(p_auth);
  if not rb_can_edit(p_auth, p_species) then raise exception 'Можно дополнять только свои записи'; end if;
  g := ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(p_geojson), 4326)), 3));
  if ST_IsEmpty(g) then raise exception 'Нарисуйте многоугольник ареала'; end if;
  if ST_Area(g::geography) > 2.0e12 then raise exception 'Ареал слишком большой'; end if;
  insert into red_book_ranges (species_id, geom, note_ru, note_kk, user_id)
  values (p_species, g, nullif(p_note_ru, ''), nullif(p_note_kk, ''), w.uid) returning id into v_id;
  return json_build_object('ok', true, 'id', v_id);
end $$;

create or replace function public.api_rb_delete(p_auth text, p_what text, p_id bigint)
returns json language plpgsql security definer set search_path = public as $$
declare v_species bigint;
begin
  v_species := case p_what
    when 'species' then p_id
    when 'point' then (select species_id from red_book_points where id = p_id)
    when 'range' then (select species_id from red_book_ranges where id = p_id) end;
  if v_species is null or not rb_can_edit(p_auth, v_species) then raise exception 'Нет прав на удаление'; end if;
  if p_what = 'species' then delete from red_book_species where id = p_id;
  elsif p_what = 'point' then delete from red_book_points where id = p_id;
  else delete from red_book_ranges where id = p_id; end if;
  return json_build_object('ok', found);
end $$;

-- описание из Википедии (ru + kk) по латинскому названию; заполняет пустые поля, ссылки обновляет
create or replace function public.api_rb_wiki(p_auth text, p_id bigint, p_overwrite boolean default false)
returns json language plpgsql security definer set search_path = public, extensions as $$
declare w record; nm text; alt text; ru jsonb; pg jsonb; kt text; kpg jsonb;
begin
  select * into w from auth_who(p_auth);
  if not rb_can_edit(p_auth, p_id) then raise exception 'Можно править только свои записи'; end if;
  select latin, name_ru into nm, alt from red_book_species where id = p_id;
  begin
    ru := wiki_query('ru', array[nm]);
    pg := wiki_page(ru, nm);
    if pg is null and alt is not null then
      ru := wiki_query('ru', array[alt]); pg := wiki_page(ru, alt);
    end if;
    kt := pg->'langlinks'->0->>'*';
    kpg := wiki_page(wiki_query('kk', array[coalesce(kt, nm)]), coalesce(kt, nm));
  exception when others then
    if sqlerrm = 'WIKI_429' then return json_build_object('ok', false, 'message', 'Википедия временно ограничила запросы, попробуйте через минуту'); end if;
    raise;
  end;
  update red_book_species set
    description_ru = case when p_overwrite or coalesce(description_ru, '') = '' then coalesce(nullif(pg->>'extract', ''), description_ru) else description_ru end,
    description_kk = case when p_overwrite or coalesce(description_kk, '') = '' then coalesce(nullif(kpg->>'extract', ''), description_kk) else description_kk end,
    name_ru = coalesce(name_ru, case when pg->>'title' <> nm then regexp_replace(pg->>'title', ' \(.*\)$', '') end),
    name_kk = coalesce(name_kk, case when kpg->>'title' <> nm then regexp_replace(kpg->>'title', ' \(.*\)$', '') end),
    wiki_ru_url = coalesce(pg->>'fullurl', wiki_ru_url),
    wiki_kk_url = coalesce(kpg->>'fullurl', wiki_kk_url),
    updated_at = now()
  where id = p_id;
  return json_build_object('ok', true, 'ru', pg is not null, 'kk', kpg is not null);
end $$;

grant execute on function public.api_rb_list(text, text, text, text), public.api_rb_get(bigint, text),
  public.api_rb_map(text, text, text), public.api_rb_photo(bigint),
  public.api_rb_save(text, bigint, text, text, text, text, text, text, text, text, text, text, text, text, text, text, text),
  public.api_rb_add_point(text, bigint, double precision, double precision, text, text, date),
  public.api_rb_add_range(text, bigint, text, text, text), public.api_rb_delete(text, text, bigint),
  public.api_rb_wiki(text, bigint, boolean)
  to anon, authenticated;

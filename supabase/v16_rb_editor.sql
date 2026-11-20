-- =============================================================
-- v16: Красная книга — страница вида и ручное редактирование
-- api_rb_save_ext: сохраняет только переданные поля (jsonb), фото файлом или ссылкой
-- api_rb_wiki_fetch: текст из Википедии (ru + kk или перевод) — возвращается в форму, не сохраняется
-- api_rb_translate: машинный перевод текста (ru↔kk) для формы
-- api_rb_delete_points: удаление нескольких точек сразу
-- =============================================================
create or replace function public.api_rb_save_ext(p_auth text, p_id bigint, p_fields jsonb,
    p_photo_b64 text default null, p_photo_mime text default null)
returns json language plpgsql security definer set search_path = public as $$
declare f jsonb := coalesce(p_fields, '{}'::jsonb);
begin
  perform auth_who(p_auth);
  if p_id is null or not rb_can_edit(p_auth, p_id) then raise exception 'Нет прав на редактирование'; end if;
  if f ? 'latin' and coalesce(trim(f->>'latin'), '') = '' then raise exception 'Укажите латинское название'; end if;
  if p_photo_b64 is not null and length(p_photo_b64) > 4000000 then raise exception 'Фото слишком большое'; end if;
  update red_book_species s set
    latin          = case when f ? 'latin' then trim(f->>'latin') else s.latin end,
    name_ru        = case when f ? 'name_ru' then nullif(trim(f->>'name_ru'), '') else s.name_ru end,
    name_kk        = case when f ? 'name_kk' then nullif(trim(f->>'name_kk'), '') else s.name_kk end,
    rank           = case when f ? 'rank' then coalesce(nullif(f->>'rank', ''), 'species') else s.rank end,
    parent_latin   = case when f ? 'parent_latin' then nullif(trim(f->>'parent_latin'), '') else s.parent_latin end,
    family         = case when f ? 'family' then nullif(trim(f->>'family'), '') else s.family end,
    family_ru      = case when f ? 'family_ru' then nullif(trim(f->>'family_ru'), '') else s.family_ru end,
    family_kk      = case when f ? 'family_kk' then nullif(trim(f->>'family_kk'), '') else s.family_kk end,
    genus          = case when f ? 'genus' then nullif(trim(f->>'genus'), '') else s.genus end,
    category       = case when f ? 'category' then nullif(f->>'category', '') else s.category end,
    description_ru = case when f ? 'description_ru' then nullif(f->>'description_ru', '') else s.description_ru end,
    description_kk = case when f ? 'description_kk' then nullif(f->>'description_kk', '') else s.description_kk end,
    habitat_ru     = case when f ? 'habitat_ru' then nullif(f->>'habitat_ru', '') else s.habitat_ru end,
    habitat_kk     = case when f ? 'habitat_kk' then nullif(f->>'habitat_kk', '') else s.habitat_kk end,
    protection_ru  = case when f ? 'protection_ru' then nullif(f->>'protection_ru', '') else s.protection_ru end,
    protection_kk  = case when f ? 'protection_kk' then nullif(f->>'protection_kk', '') else s.protection_kk end,
    wiki_ru_url    = case when f ? 'wiki_ru_url' then nullif(trim(f->>'wiki_ru_url'), '') else s.wiki_ru_url end,
    wiki_kk_url    = case when f ? 'wiki_kk_url' then nullif(trim(f->>'wiki_kk_url'), '') else s.wiki_kk_url end,
    photo_url      = case when f ? 'photo_url' then nullif(trim(f->>'photo_url'), '') else s.photo_url end,
    photo_attr     = case when f ? 'photo_attr' then nullif(trim(f->>'photo_attr'), '') else s.photo_attr end,
    photo          = case when p_photo_b64 is not null then decode(p_photo_b64, 'base64')
                          when coalesce((f->>'remove_photo')::boolean, false) then null else s.photo end,
    photo_mime     = case when p_photo_b64 is not null then p_photo_mime
                          when coalesce((f->>'remove_photo')::boolean, false) then null else s.photo_mime end,
    taxon_id       = case when f ? 'latin' then coalesce((select t.id from taxa t where lower(t.name) = lower(trim(f->>'latin')) limit 1), s.taxon_id)
                          else s.taxon_id end,
    updated_at = now()
  where s.id = p_id;
  return json_build_object('ok', true, 'id', p_id);
end $$;

create or replace function public.rb_urldecode(p text) returns text language sql immutable as $$
  select convert_from(string_agg(case when m[1] ~ '^%[0-9A-Fa-f]{2}$' then decode(substr(m[1], 2), 'hex')
                                      else convert_to(m[1], 'UTF8') end, ''::bytea order by o), 'UTF8')
  from regexp_matches(p, '(%[0-9A-Fa-f]{2}|[^%]+|%)', 'g') with ordinality as r(m, o);
$$;

create or replace function public.api_rb_wiki_fetch(p_auth text, p_id bigint, p_title text default null)
returns json language plpgsql security definer set search_path = public, extensions as $$
declare s record; pg jsonb; kpg jsonb; en jsonb; kt text; d_ru text; d_kk text; ru_url text; kk_url text; thumb text; src text;
begin
  perform auth_who(p_auth);
  select * into s from red_book_species where id = p_id;
  begin
    if coalesce(trim(p_title), '') <> '' then
      -- можно вставить название статьи или ссылку на неё
      if p_title ~* 'wikipedia\.org/wiki/' then
        pg := rb_wiki(substring(p_title from '//([a-z\-]+)\.wikipedia'),
                      replace(rb_urldecode(substring(p_title from '/wiki/([^?#]+)')), '_', ' '));
        if substring(p_title from '//([a-z\-]+)\.wikipedia') = 'kk' then kpg := pg; pg := null; end if;
      else
        pg := rb_wiki('ru', p_title);
      end if;
    end if;
    if pg is null and kpg is null then
      pg := rb_wiki('ru', trim(regexp_replace(split_part(s.name_ru, ',', 1), '\s*\(.*\)', '')));
      if pg is null then pg := rb_wiki('ru', s.latin); end if;
    end if;
    if pg is not null then
      d_ru := pg->>'extract'; ru_url := pg->>'fullurl'; thumb := pg->'thumbnail'->>'source'; src := 'ru';
      kt := pg->'langlinks'->0->>'*';
    elsif kpg is null then
      en := rb_wiki('en', s.latin);
      if en is not null then d_ru := rb_tr(en->>'extract', 'en', 'ru'); ru_url := en->>'fullurl'; src := 'en'; end if;
    end if;
    if kpg is null then kpg := rb_wiki('kk', coalesce(kt, split_part(s.name_kk, ',', 1))); end if;
    if kpg is not null and length(kpg->>'extract') >= 100 then
      d_kk := kpg->>'extract'; kk_url := kpg->>'fullurl';
    elsif d_ru is not null then
      d_kk := rb_tr(d_ru, 'ru', 'kk');
    end if;
    if d_ru is null and d_kk is not null then d_ru := rb_tr(d_kk, 'kk', 'ru'); end if;
  exception when others then
    if sqlerrm like 'HTTP_429%' then
      return json_build_object('ok', false, 'message', 'Википедия временно ограничила запросы, попробуйте через минуту');
    end if;
    raise;
  end;
  return json_build_object('ok', d_ru is not null or d_kk is not null, 'ru', d_ru, 'kk', d_kk,
                           'ru_url', ru_url, 'kk_url', kk_url, 'thumb', thumb, 'kk_native', kk_url is not null, 'src', src);
end $$;

create or replace function public.api_rb_translate(p_auth text, p_text text, p_sl text, p_tl text)
returns json language plpgsql security definer set search_path = public, extensions as $$
begin
  perform auth_who(p_auth);
  if p_sl not in ('ru', 'kk', 'en') or p_tl not in ('ru', 'kk', 'en') then raise exception 'Язык не поддерживается'; end if;
  return json_build_object('text', rb_tr(p_text, p_sl, p_tl));
exception when others then
  if sqlerrm like 'HTTP_429%' then return json_build_object('text', null, 'message', 'Сервис перевода занят, попробуйте позже'); end if;
  raise;
end $$;

create or replace function public.api_rb_delete_points(p_auth text, p_species bigint, p_ids bigint[])
returns json language plpgsql security definer set search_path = public as $$
declare k int;
begin
  if not rb_can_edit(p_auth, p_species) then raise exception 'Нет прав на удаление'; end if;
  delete from red_book_points where species_id = p_species and id = any(p_ids);
  get diagnostics k = row_count;
  return json_build_object('ok', true, 'deleted', k);
end $$;

-- проверка прав для интерфейса
create or replace function public.api_rb_can_edit(p_auth text, p_id bigint)
returns json language plpgsql stable security definer set search_path = public as $$
begin
  return json_build_object('can', coalesce(p_auth, '') <> '' and rb_can_edit(p_auth, p_id));
exception when others then return json_build_object('can', false);
end $$;

grant execute on function public.api_rb_save_ext(text, bigint, jsonb, text, text),
  public.api_rb_wiki_fetch(text, bigint, text), public.api_rb_translate(text, text, text, text),
  public.api_rb_delete_points(text, bigint, bigint[]), public.api_rb_can_edit(text, bigint) to anon, authenticated;
select 'v16 ok' as status;

-- =============================================================
-- Флора Казахстана — v11: регистрация пользователей и вход на сайте
-- Аккаунты: app_users (bcrypt), сессии: app_sessions (случайный токен, 30 дней).
-- Все записывающие функции принимают p_auth = токен сессии ИЛИ пароль редактора.
-- Роли: user — добавляет наблюдения, правит/удаляет свои, загружает Википедию;
--        editor/admin — дополнительно правит виды и любые наблюдения.
-- =============================================================
create table if not exists public.app_users (
  id bigserial primary key,
  login text not null unique,
  pwd_hash text not null,
  display_name text,
  email text,
  role text not null default 'user' check (role in ('user', 'editor', 'admin')),
  created_at timestamptz default now(),
  last_login timestamptz
);
alter table public.app_users enable row level security;     -- без политик: anon не читает

create table if not exists public.app_sessions (
  token text primary key,
  user_id bigint not null references public.app_users(id) on delete cascade,
  created_at timestamptz default now(),
  expires_at timestamptz default now() + interval '30 days'
);
alter table public.app_sessions enable row level security;

alter table public.user_observations add column if not exists user_id bigint references public.app_users(id);
create index if not exists uobs_user_idx on public.user_observations (user_id);

-- кто выполняет действие: (user_id, role) по токену или паролю редактора
create or replace function public.auth_who(p_auth text, out uid bigint, out role text, out name text)
language plpgsql stable security definer set search_path = public, extensions as $$
begin
  if coalesce(p_auth, '') = '' then raise exception 'Войдите на сайт'; end if;
  if check_editor(p_auth) then uid := null; role := 'admin'; name := 'editor'; return; end if;
  select u.id, u.role, coalesce(u.display_name, u.login) into uid, role, name
  from app_sessions s join app_users u on u.id = s.user_id
  where s.token = p_auth and s.expires_at > now();
  if uid is null then raise exception 'Сессия истекла — войдите снова'; end if;
end $$;
revoke all on function public.auth_who(text) from public, anon, authenticated;

create or replace function public.api_register(p_login text, p_pwd text, p_name text default null,
    p_email text default null) returns json
language plpgsql security definer set search_path = public, extensions as $$
declare v_id bigint; v_token text; v_login text := lower(trim(p_login));
begin
  if v_login !~ '^[a-z0-9_.-]{3,32}$' then
    raise exception 'Логин: 3–32 символа, латинские буквы, цифры, точка, дефис, подчёркивание';
  end if;
  if length(coalesce(p_pwd, '')) < 6 then raise exception 'Пароль — не короче 6 символов'; end if;
  if exists (select 1 from app_users where login = v_login) then raise exception 'Такой логин уже занят'; end if;
  if (select count(*) from app_users where created_at > now() - interval '1 hour') > 50 then
    raise exception 'Слишком много регистраций, попробуйте позже';
  end if;
  insert into app_users (login, pwd_hash, display_name, email, last_login)
  values (v_login, crypt(p_pwd, gen_salt('bf')), nullif(trim(p_name), ''), nullif(trim(p_email), ''), now())
  returning id into v_id;
  v_token := encode(gen_random_bytes(24), 'hex');
  insert into app_sessions (token, user_id) values (v_token, v_id);
  return json_build_object('token', v_token, 'login', v_login,
                           'name', coalesce(nullif(trim(p_name), ''), v_login), 'role', 'user');
end $$;

create or replace function public.api_login(p_login text, p_pwd text) returns json
language plpgsql security definer set search_path = public, extensions as $$
declare u app_users; v_token text;
begin
  select * into u from app_users where login = lower(trim(p_login));
  if u.id is null or u.pwd_hash <> crypt(coalesce(p_pwd, ''), u.pwd_hash) then
    raise exception 'Неверный логин или пароль';
  end if;
  delete from app_sessions where user_id = u.id and expires_at < now();
  v_token := encode(gen_random_bytes(24), 'hex');
  insert into app_sessions (token, user_id) values (v_token, u.id);
  update app_users set last_login = now() where id = u.id;
  return json_build_object('token', v_token, 'login', u.login,
                           'name', coalesce(u.display_name, u.login), 'role', u.role);
end $$;

create or replace function public.api_logout(p_token text) returns json
language sql security definer set search_path = public as $$
  delete from app_sessions where token = p_token;
  select json_build_object('ok', true);
$$;

-- администратор (пароль редактора) назначает роль
create or replace function public.api_set_role(p_pwd text, p_login text, p_role text) returns json
language plpgsql security definer set search_path = public as $$
begin
  if not check_editor(p_pwd) then raise exception 'Нужен пароль редактора'; end if;
  update app_users set role = p_role where login = lower(trim(p_login));
  return json_build_object('ok', found);
end $$;

create or replace function public.api_users(p_pwd text) returns json
language plpgsql stable security definer set search_path = public as $$
begin
  if not check_editor(p_pwd) then raise exception 'Нужен пароль редактора'; end if;
  return (select coalesce(json_agg(r order by r.created_at desc), '[]'::json) from (
    select u.login, u.display_name, u.role, u.created_at, u.last_login,
           (select count(*) from user_observations o where o.user_id = u.id) as observations
    from app_users u) r);
end $$;

-- ---------- запись: наблюдения ----------
drop function if exists public.api_add_observation(text, bigint, text, text, text, text, double precision, double precision, date, text, text, text);
create or replace function public.api_add_observation(p_pwd text, p_taxon_id bigint, p_taxon_name text,
    p_subspecies text, p_desc_ru text, p_desc_kk text, p_lat double precision, p_lng double precision,
    p_observed_on date, p_author text, p_photo_b64 text default null, p_photo_mime text default null)
returns json language plpgsql security definer set search_path = public as $$
declare w record; v_id bigint;
begin
  select * into w from auth_who(p_pwd);
  if p_lat is null or p_lng is null or (p_lat = 0 and p_lng = 0) then raise exception 'Отметьте точку на карте'; end if;
  if p_lat not between 40 and 56 or p_lng not between 46 and 88 then raise exception 'Точка вне Казахстана'; end if;
  if p_taxon_id is null and coalesce(trim(p_taxon_name), '') = '' then raise exception 'Укажите вид'; end if;
  if p_photo_b64 is not null and length(p_photo_b64) > 4000000 then raise exception 'Фото слишком большое'; end if;
  insert into user_observations (taxon_id, taxon_name, subspecies, description_ru, description_kk, lat, lng,
                                 observed_on, author, photo, photo_mime, user_id)
  values (p_taxon_id, nullif(p_taxon_name, ''), nullif(p_subspecies, ''), nullif(p_desc_ru, ''), nullif(p_desc_kk, ''),
          p_lat, p_lng, p_observed_on, coalesce(nullif(p_author, ''), w.name),
          case when p_photo_b64 is not null then decode(p_photo_b64, 'base64') end, p_photo_mime, w.uid)
  returning id into v_id;
  return json_build_object('ok', true, 'id', v_id);
end $$;

create or replace function public.can_edit_obs(p_auth text, p_id bigint) returns boolean
language plpgsql stable security definer set search_path = public as $$
declare w record;
begin
  select * into w from auth_who(p_auth);
  return w.role in ('editor', 'admin') or exists (select 1 from user_observations where id = p_id and user_id = w.uid);
end $$;
revoke all on function public.can_edit_obs(text, bigint) from public, anon, authenticated;

create or replace function public.api_edit_observation(p_pwd text, p_id bigint, p_taxon_id bigint,
    p_taxon_name text, p_subspecies text, p_desc_ru text, p_desc_kk text, p_lat double precision,
    p_lng double precision, p_observed_on date, p_author text)
returns json language plpgsql security definer set search_path = public as $$
begin
  if not can_edit_obs(p_pwd, p_id) then raise exception 'Можно править только свои наблюдения'; end if;
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
  if not can_edit_obs(p_pwd, p_id) then raise exception 'Можно удалять только свои наблюдения'; end if;
  delete from user_observations where id = p_id;
  return json_build_object('ok', found);
end $$;

-- ---------- запись: виды (редакторы) ----------
create or replace function public.api_edit_taxon(p_pwd text, p_id bigint, p_common_ru text, p_common_kk text,
    p_desc_ru text, p_desc_kk text, p_editor text default null)
returns json language plpgsql security definer set search_path = public as $$
declare w record;
begin
  select * into w from auth_who(p_pwd);
  if w.role not in ('editor', 'admin') then raise exception 'Править виды могут только редакторы'; end if;
  update taxa set common_name_ru = nullif(trim(p_common_ru), ''), common_name_kk = nullif(trim(p_common_kk), ''),
                  description_ru = nullif(trim(p_desc_ru), ''), description_kk = nullif(trim(p_desc_kk), ''),
                  edited_by = coalesce(p_editor, w.name), edited_at = now()
  where id = p_id;
  return json_build_object('ok', found);
end $$;

create or replace function public.api_add_taxon(p_pwd text, p_name text, p_rank text, p_common_ru text,
    p_common_kk text, p_family text, p_genus text, p_parent text, p_desc_ru text, p_desc_kk text,
    p_editor text default null)
returns json language plpgsql security definer set search_path = public as $$
declare w record; v_id bigint;
begin
  select * into w from auth_who(p_pwd);   -- новый вид/подвид может предложить любой вошедший пользователь
  if coalesce(trim(p_name), '') = '' then raise exception 'Укажите латинское название'; end if;
  select id into v_id from taxa where lower(name) = lower(trim(p_name)) limit 1;
  if v_id is not null then return json_build_object('ok', false, 'id', v_id, 'message', 'Такой вид уже есть'); end if;
  v_id := -nextval('user_taxon_seq');
  insert into taxa (id, name, rank, common_name_ru, common_name_kk, family, genus, parent_name,
                    description_ru, description_kk, is_user_taxon, edited_by, edited_at, wiki_checked_at)
  values (v_id, trim(p_name), coalesce(nullif(p_rank, ''), 'species'), nullif(p_common_ru, ''), nullif(p_common_kk, ''),
          nullif(p_family, ''), nullif(p_genus, ''), nullif(p_parent, ''), nullif(p_desc_ru, ''), nullif(p_desc_kk, ''),
          true, coalesce(p_editor, w.name), now(), now());
  return json_build_object('ok', true, 'id', v_id);
end $$;

-- ---------- Википедия по кнопке: только для вошедших ----------
create or replace function public.api_fetch_wiki_auth(p_auth text, p_id bigint) returns json
language plpgsql security definer set search_path = public as $$
declare w record;
begin
  select * into w from auth_who(p_auth);
  return api_fetch_wiki(p_id);
end $$;

-- список добавленных наблюдений: + владелец
create or replace function public.api_user_observations(p_taxon bigint default null, p_kind text default 'all',
    p_name text default 'all', p_limit int default 200)
returns json language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(r), '[]'::json) from (
    select u.id, u.taxon_id, coalesce(t.common_name_ru, u.taxon_name) as name_ru,
           coalesce(t.common_name_kk, t.common_name_ru, u.taxon_name) as name_kk,
           coalesce(t.name, u.taxon_name) as sci, u.subspecies, u.description_ru, u.description_kk,
           u.lat, u.lng, u.observed_on, u.author, u.region, u.zone, u.photo is not null as has_photo, u.created_at,
           au.login as owner
    from public.user_observations u
    left join public.taxa t on t.id = u.taxon_id
    left join public.app_users au on au.id = u.user_id
    where (p_taxon is null or u.taxon_id = p_taxon)
      and (p_kind = 'all' or (p_kind = 'region' and u.region = p_name) or (p_kind = 'zone' and u.zone = p_name))
    order by u.id desc limit p_limit) r;
$$;

grant execute on function public.api_register(text, text, text, text), public.api_login(text, text),
  public.api_logout(text), public.api_set_role(text, text, text), public.api_users(text),
  public.api_add_observation(text, bigint, text, text, text, text, double precision, double precision, date, text, text, text),
  public.api_edit_observation(text, bigint, bigint, text, text, text, text, double precision, double precision, date, text),
  public.api_delete_observation(text, bigint), public.api_edit_taxon(text, bigint, text, text, text, text, text),
  public.api_add_taxon(text, text, text, text, text, text, text, text, text, text, text),
  public.api_fetch_wiki_auth(text, bigint), public.api_user_observations(bigint, text, text, int)
  to anon, authenticated;
-- прежняя открытая кнопка Википедии закрывается: теперь только через вход
revoke execute on function public.api_fetch_wiki(bigint) from anon, authenticated;

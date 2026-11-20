-- =============================================================
-- Флора Казахстана — v7: природные зоны с долями, близкими к справочным
--   пустыни ~44%, степи ~26%, полупустыни ~10–14%, горы ~10%, лесостепь ~2–5%
-- Форма границ схематичная; положение подбирается автоматически (бинарный поиск),
-- чтобы доли площадей совпали с целевыми (по границе 17 областей + 3 городов, OSM).
-- =============================================================
create or replace function public.etl_build_zones(
    p_fs numeric default 0.04, p_steppe numeric default 0.27, p_semi numeric default 0.13,
    p_mount numeric default 0.10) returns text
language plpgsql security definer set search_path = public, extensions as $$
declare
  kz geometry; kz_area float8; mtn_base geometry; mtn geometry; flat geometry;
  lo float8; hi float8; mid float8; b float8; i int; k int;
  lines float8[][]; d float8[] := array[0, 0, 0];
  targets float8[];
  W float8 := 46.0; E float8 := 88.0;
  res text := '';
begin
  kz := ST_SimplifyPreserveTopology(ST_Union(geom), 0.01) from areas where kind = 'region';
  kz_area := ST_Area(kz::geography);

  -- горные системы (схематично): Алтай, Калба, Саур-Тарбагатай, Джунгарский Алатау, Северный Тянь-Шань
  -- (Заилийский, Кунгей, Кетмень), Киргизский, Таласский и Угамский хребты, Каратау, Чу-Илийские горы, Мугоджары
  mtn_base := ST_Union(array[
    ST_GeomFromText('POLYGON((82.2 49.6,83.2 50.7,84.3 51.3,85.8 51.0,87.0 50.2,87.4 49.1,86.2 48.6,85.0 48.9,83.6 49.2,82.2 49.6))', 4326),
    ST_GeomFromText('POLYGON((81.2 49.5,82.6 49.9,83.4 49.4,82.6 48.9,81.6 49.0,81.2 49.5))', 4326),
    ST_GeomFromText('POLYGON((79.6 47.0,81.0 47.6,82.8 47.8,84.4 47.7,85.6 47.6,86.2 47.2,85.6 46.8,84.0 47.0,82.4 46.8,80.6 46.6,79.6 47.0))', 4326),
    ST_GeomFromText('POLYGON((77.6 45.1,78.6 45.8,80.0 46.0,81.3 45.7,82.7 45.4,82.4 44.7,80.6 44.5,79.2 44.3,78.0 44.5,77.6 45.1))', 4326),
    ST_GeomFromText('POLYGON((73.0 43.0,74.6 43.2,76.0 43.4,77.4 43.55,78.6 43.5,79.6 43.4,80.6 43.1,80.5 42.3,79.0 42.4,76.5 42.5,74.0 42.4,73.0 42.6,73.0 43.0))', 4326),
    ST_GeomFromText('POLYGON((69.0 41.2,69.8 42.0,70.8 42.6,71.8 42.9,73.0 43.0,73.0 42.6,71.8 42.1,70.6 41.4,69.6 40.9,69.0 41.2))', 4326),
    ST_GeomFromText('POLYGON((67.8 44.2,68.6 44.3,69.6 43.7,70.6 43.0,70.4 42.6,69.6 42.9,68.6 43.4,67.8 44.2))', 4326),
    ST_GeomFromText('POLYGON((72.6 44.6,74.2 44.9,75.6 44.5,75.0 43.9,73.4 44.0,72.6 44.6))', 4326),
    ST_GeomFromText('POLYGON((57.8 49.6,58.6 49.7,59.0 48.6,58.6 47.6,58.0 47.8,57.8 49.6))', 4326)
  ]);

  -- 1) горы: расширяем/сужаем полигоны, пока доля не станет p_mount
  lo := -0.5; hi := 1.5;
  for i in 1..25 loop
    mid := (lo + hi) / 2;
    mtn := ST_Intersection(ST_Buffer(mtn_base, mid), kz);
    if ST_Area(mtn::geography) / kz_area > p_mount then hi := mid; else lo := mid; end if;
  end loop;
  b := (lo + hi) / 2;
  mtn := ST_MakeValid(ST_Intersection(ST_Buffer(mtn_base, b), kz));
  flat := ST_MakeValid(ST_Difference(kz, mtn));

  -- 2) широтные границы (форма — с запада на восток), подбираем сдвиг по широте
  lines := array[
    array[54.6, 54.2, 53.9, 53.8, 53.6, 53.4, 53.2, 52.8],       -- лесостепь | степь
    array[49.6, 50.0, 49.7, 49.3, 49.2, 49.2, 49.4, 49.6],       -- степь | полупустыня
    array[47.6, 47.5, 47.0, 46.9, 46.8, 46.5, 46.5, 47.0]        -- полупустыня | пустыня
  ];
  targets := array[p_fs, p_fs + p_steppe, p_fs + p_steppe + p_semi];
  for k in 1..3 loop
    lo := -6; hi := 6;
    for i in 1..30 loop
      mid := (lo + hi) / 2;
      -- доля всей страны, лежащая севернее линии k (без гор)
      if ST_Area(ST_Intersection(flat, public.zone_north_of(lines[k:k][1:8], mid, W, E))::geography) / kz_area
         > targets[k] then lo := mid; else hi := mid; end if;
    end loop;
    d[k] := (lo + hi) / 2;
  end loop;

  delete from areas where kind = 'zone';
  insert into areas (kind, name, name_en, name_kk, geojson, geom)
  select 'zone', z.name, z.en, z.kk, '{}'::jsonb, ST_Multi(ST_CollectionExtract(ST_MakeValid(z.g), 3))
  from (values
    ('Лесостепь', 'Forest-steppe', 'Орманды дала',
       ST_Intersection(flat, public.zone_north_of(lines[1:1][1:8], d[1], W, E))),
    ('Степь', 'Steppe', 'Дала',
       ST_Difference(ST_Intersection(flat, public.zone_north_of(lines[2:2][1:8], d[2], W, E)),
                     public.zone_north_of(lines[1:1][1:8], d[1], W, E))),
    ('Полупустыня', 'Semi-desert', 'Шөлейт',
       ST_Difference(ST_Intersection(flat, public.zone_north_of(lines[3:3][1:8], d[3], W, E)),
                     public.zone_north_of(lines[2:2][1:8], d[2], W, E))),
    ('Пустыня', 'Desert', 'Шөл',
       ST_Difference(flat, public.zone_north_of(lines[3:3][1:8], d[3], W, E))),
    ('Горы', 'Mountains', 'Таулар', mtn)
  ) z(name, en, kk, g);
  update areas set geojson = ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, 0.01), 4)::jsonb where kind = 'zone';

  select string_agg(name || ' ' || round((100 * ST_Area(geom::geography) / kz_area)::numeric, 1) || '%', ', '
                    order by ST_Area(geom::geography) desc)
  into res from areas where kind = 'zone';
  return res;
end $$;

-- многоугольник «всё, что севернее ломаной» (8 узлов от 46° до 88° в.д.), сдвинутой на p_shift градусов
create or replace function public.zone_north_of(p_lats float8[], p_shift float8, p_w float8, p_e float8)
returns geometry language plpgsql immutable set search_path = public, extensions as $$
declare pts text := ''; i int; n int := array_length(p_lats, 2); x float8;
begin
  if n is null then n := array_length(p_lats, 1); end if;
  for i in 1..n loop
    x := p_w + (p_e - p_w) * (i - 1) / (n - 1);
    pts := pts || x || ' ' || (coalesce(p_lats[1][i], p_lats[i]) + p_shift) || ',';
  end loop;
  return ST_GeomFromText('POLYGON((' || pts || p_e || ' 60,' || p_w || ' 60,' || p_w || ' ' ||
                         (coalesce(p_lats[1][1], p_lats[1]) + p_shift) || '))', 4326);
end $$;

-- привязка наблюдений к новым зонам
create or replace function public.etl_assign_zones() returns text
language plpgsql security definer set search_path = public, extensions as $$
begin
  update observations set zone = null where zone is not null;
  update observations o set zone = a.name from areas a
   where a.kind = 'zone' and o.lat is not null and ST_Intersects(a.geom, ST_SetSRID(ST_MakePoint(o.lng, o.lat), 4326));
  update user_observations u set lat = lat;   -- триггер пересчитает зону
  return (select count(*) filter (where zone is not null) || ' из ' || count(*) from observations);
end $$;
revoke all on function public.etl_build_zones(numeric, numeric, numeric, numeric),
  public.etl_assign_zones() from public, anon, authenticated;

-- применено 20.11.2026:
-- select etl_build_zones(0.05, 0.27, 0.14, 0.10); select etl_assign_zones(); select etl_refresh_stats();

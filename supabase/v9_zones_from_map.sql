-- =============================================================
-- Флора Казахстана — v9: природные зоны по эталонной карте (лесостепь, степь, полупустыня, пустыня, горы)
-- Полигоны: data/kz_natural_zones.geojson (оцифровано по карте природных зон РК, привязка по 15 городам, ±0.1°).
-- Обрезаются по границе 17 областей (OSM); небольшие расхождения контуров заполняются ближайшей зоной.
-- =============================================================
create or replace function public.etl_load_zones_geojson(p_fc jsonb) returns text
language plpgsql security definer set search_path = public, extensions as $$
declare kz geometry; water geometry; res text; kz_area float8;
begin
  kz := ST_Union(geom) from areas where kind = 'region';
  kz_area := ST_Area(kz::geography);
  create temp table tz on commit drop as
    select f->'properties'->>'name' as name, f->'properties'->>'name_en' as en, f->'properties'->>'name_kk' as kk,
           ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON((f->'geometry')::text), 4326)) as g
    from jsonb_array_elements(p_fc->'features') f;
  water := coalesce((select ST_Union(g) from tz where name = 'Вода'), 'GEOMETRYCOLLECTION EMPTY'::geometry);
  delete from tz where name = 'Вода';
  update tz set g = ST_CollectionExtract(ST_MakeValid(ST_Difference(ST_Intersection(g, kz), water)), 3);
  -- непокрытые участки (контур рисунка ≠ граница OSM) → ближайшей зоне
  create temp table gaps on commit drop as
    select (ST_Dump(ST_CollectionExtract(ST_Difference(ST_Difference(kz, (select ST_Union(g) from tz)), water), 3))).geom as g;
  update tz set g = ST_CollectionExtract(ST_MakeValid(ST_Union(tz.g, x.gg)), 3)
  from (select z.name, ST_Union(gp.g) as gg from gaps gp
        cross join lateral (select t2.name from tz t2 order by t2.g <-> gp.g limit 1) z group by z.name) x
  where tz.name = x.name;
  delete from areas where kind = 'zone';
  insert into areas (kind, name, name_en, name_kk, geojson, geom)
  select 'zone', name, en, kk, ST_AsGeoJSON(ST_SimplifyPreserveTopology(g, 0.004), 4)::jsonb, ST_Multi(g) from tz;
  select string_agg(name || ' ' || round((100 * ST_Area(geom::geography) / kz_area)::numeric, 1) || '%', ', '
                    order by ST_Area(geom::geography) desc) into res from areas where kind = 'zone';
  return res;
end $$;

-- перепривязка зон: пишем только изменившиеся строки (экономия дисковых операций)
create or replace function public.etl_assign_zones() returns text
language plpgsql security definer set search_path = public, extensions as $$
declare n int;
begin
  update observations o set zone = z.name
  from (select o2.id, (select a.name from areas a where a.kind = 'zone'
                       and ST_Intersects(a.geom, ST_SetSRID(ST_MakePoint(o2.lng, o2.lat), 4326)) limit 1) as name
        from observations o2 where o2.lat is not null) z
  where o.id = z.id and o.zone is distinct from z.name;
  get diagnostics n = row_count;
  update user_observations set lat = lat;
  return n || ' наблюдений перепривязано';
end $$;
revoke all on function public.etl_load_zones_geojson(jsonb), public.etl_assign_zones() from public, anon, authenticated;

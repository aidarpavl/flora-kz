# 🌿 Флора Казахстана

Streamlit-приложение по данным проекта iNaturalist
[«Флора Казахстана»](https://www.inaturalist.org/projects/flora-kazahstana?tab=species)
с базой в Supabase и картой по **всему Казахстану**, **областям** и **природным зонам**.

| Страница | Что показывает |
|---|---|
| Обзор | счётчики, карта зон, топ семейств и наблюдателей, популярные виды |
| Виды | сетка карточек видов (как на iNaturalist) с фильтром по территории, поиском, CSV |
| Карта | хороплет «число видов» по областям / зонам, точки наблюдений, топ видов территории |
| Вид | фото, семейство, где встречается (области и зоны), карта находок |

```
app.py                     точка входа Streamlit
views/                     страницы
lib/db.py, lib/ui.py       доступ к Supabase и общие компоненты
etl/load_inat.py           загрузка iNaturalist → Supabase
supabase/schema.sql        таблицы, представления, функция species_list, RLS
data/kz_natural_zones.geojson  схематичные полигоны природных зон
.github/workflows/etl.yml  ежедневное обновление данных
PROMPT.md                  супер-промт (ТЗ проекта)
```

## 1. Supabase
1. Откройте проект `ucrhksetkgmhoxdwwhnh` → **SQL Editor** → **New query**, вставьте `supabase/schema.sql`, нажмите **Run**.
2. **Project Settings → API**: скопируйте `Project URL`, `anon public` и `service_role` ключи.
   `service_role` — секретный, только для ETL/GitHub Secrets, не вставляйте его в Streamlit.

## 2. GitHub
Репозиторий: https://github.com/aidarpavl/flora-kz

**Settings → Secrets and variables → Actions → New repository secret**:
- `SUPABASE_URL` = `https://ucrhksetkgmhoxdwwhnh.supabase.co`
- `SUPABASE_SERVICE_KEY` = service_role ключ

## 3. Загрузка данных
**Через GitHub:** вкладка **Actions → «Загрузка данных iNaturalist → Supabase» → Run workflow**.
Первая полная загрузка идёт примерно 1 секунду на 200 наблюдений (лимит API iNaturalist). Дальше данные
обновляются сами: по воскресеньям — полностью, в остальные дни — только новые наблюдения.

**Или локально:**
```bash
pip install -r etl/requirements.txt
export SUPABASE_URL=https://ucrhksetkgmhoxdwwhnh.supabase.co
export SUPABASE_SERVICE_KEY=...
python etl/load_inat.py --max-pages 5   # тест на 1000 наблюдений
python etl/load_inat.py                 # всё
```
Флаги: `--incremental`, `--quality research`, `--refresh-taxa`.

## 4. Streamlit
Локально:
```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # вставьте anon key
streamlit run app.py
```
Streamlit Community Cloud: **share.streamlit.io → New app** → репозиторий `flora-kz`, ветка `main`, файл `app.py` →
**Advanced settings → Secrets**: содержимое `secrets.toml.example` с вашим anon key → **Deploy**.

## Территории
- **Области** берутся из [geoBoundaries KAZ ADM1](https://www.geoboundaries.org/). Если там старое деление
  (без областей Абай, Жетісу, Ұлытау 2022 г.), положите актуальный GeoJSON в `data/kz_regions.geojson`
  (свойства `name_ru`/`name_en`) — ETL возьмёт его автоматически.
- **Природные зоны**: лесостепь, степь, полупустыня, пустыня + горные системы (Алтай, Саур-Тарбагатай,
  Джунгарский Алатау, Северный Тянь-Шань, Каратау). Полигоны **схематичные** и обрезаются по границе страны;
  для точной работы замените `data/kz_natural_zones.geojson` официальным шейп-файлом (свойства `name`, `name_en`,
  `type` = `lat`/`mountain`, `priority`).

Данные — iNaturalist; фотографии принадлежат авторам наблюдений (лицензии CC).

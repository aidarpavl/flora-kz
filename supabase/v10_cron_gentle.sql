-- Флора Казахстана — v10: щадящее расписание фоновых заданий

-- щадящее расписание для бесплатного тарифа (Nano)
select cron.unschedule(jobname) from cron.job where jobname like 'flora%';
select cron.schedule('flora-load', '*/5 * * * *', $c$set statement_timeout = 0; select public.etl_load_observations(15); select public.etl_load_taxa(5);$c$);
select cron.schedule('flora-wiki', '2-59/5 * * * *', $c$set statement_timeout = 0; select public.etl_load_wiki(20);$c$);
select cron.schedule('flora-stats', '7,37 * * * *', $c$set statement_timeout = 0; select public.etl_refresh_stats();$c$);
select cron.schedule('flora-monthly-full', '17 21 1 * *', $c$update public.etl_state set value = '0' where key = 'last_id';$c$);

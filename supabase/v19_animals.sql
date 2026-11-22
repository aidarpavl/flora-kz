
-- v19: животные Красной книги РК (217 видов) в общей таблице red_book_species (kingdom = 'animalia')
alter table public.red_book_species
  add column if not exists kingdom text not null default 'plantae',
  add column if not exists phylum text, add column if not exists phylum_ru text, add column if not exists phylum_kk text,
  add column if not exists class_lat text, add column if not exists class_ru text, add column if not exists class_kk text,
  add column if not exists order_lat text, add column if not exists order_ru text, add column if not exists order_kk text;
create index if not exists rb_species_kingdom_idx on public.red_book_species (kingdom);

with o(ph, ph_ru, ph_kk, cl, cl_ru, cl_kk, od, od_ru, od_kk) as (values
('Annelida','Кольчатые черви','Буылтық құрттар','Oligochaeta','Малощетинковые','Азқылшықтылар','Lumbricomorpha','Люмбрикоморфа','Люмбрикоморфалар'),
('Mollusca','Моллюски','Моллюскалар','Gastropoda','Брюхоногие','Бауыраяқтылар','Stylommatophora','Стебельчатоглазые','Сабақшакөзділер'),
('Arthropoda','Членистоногие','Буынаяқтылар','Crustacea','Ракообразные','Шаянтәрiздiлер','Decapoda','Десятиногие','Онаяқтылар'),
('Arthropoda','Членистоногие','Буынаяқтылар','Arachnida','Паукообразные','Өрмекшiтәрiздiлер','Solifugae','Сольпуги','Сольпугалар'),
('Arthropoda','Членистоногие','Буынаяқтылар','Arachnida','Паукообразные','Өрмекшiтәрiздiлер','Scorpiones','Скорпионы','Сарышаяндар'),
('Arthropoda','Членистоногие','Буынаяқтылар','Insecta','Насекомые','Жәндіктер','Odonata','Стрекозы','Инеліктер'),
('Arthropoda','Членистоногие','Буынаяқтылар','Insecta','Насекомые','Жәндіктер','Mantodea','Богомоловые','Дәуіттер'),
('Arthropoda','Членистоногие','Буынаяқтылар','Insecta','Насекомые','Жәндіктер','Orthoptera','Прямокрылые','Тікқанаттылар'),
('Arthropoda','Членистоногие','Буынаяқтылар','Insecta','Насекомые','Жәндіктер','Hemiptera','Полужесткокрылые','Жартылай қаттықанаттылар'),
('Arthropoda','Членистоногие','Буынаяқтылар','Insecta','Насекомые','Жәндіктер','Coleoptera','Жесткокрылые','Қаттықанаттылар'),
('Arthropoda','Членистоногие','Буынаяқтылар','Insecta','Насекомые','Жәндіктер','Hymenoptera','Перепончатокрылые','Жарғаққанаттылар'),
('Arthropoda','Членистоногие','Буынаяқтылар','Insecta','Насекомые','Жәндіктер','Lepidoptera','Чешуекрылые','Қабыршаққанаттылар'),
('Chordata','Хордовые','Хордалылар','Petromyzonti','Круглоротые','Миногалар','Petromyzoniformes','Миногообразные','Миногатәрізділер'),
('Chordata','Хордовые','Хордалылар','Actinopteri','Лучепёрые рыбы','Сәулеқанатты балықтар','Acipenseriformes','Осетрообразные','Бекіретәрізділер'),
('Chordata','Хордовые','Хордалылар','Actinopteri','Лучепёрые рыбы','Сәулеқанатты балықтар','Clupeiformes','Сельдеобразные','Майшабақтәрізділер'),
('Chordata','Хордовые','Хордалылар','Actinopteri','Лучепёрые рыбы','Сәулеқанатты балықтар','Salmoniformes','Лососеобразные','Албырттәрізділер'),
('Chordata','Хордовые','Хордалылар','Actinopteri','Лучепёрые рыбы','Сәулеқанатты балықтар','Cypriniformes','Карпообразные','Тұқытәрізділер'),
('Chordata','Хордовые','Хордалылар','Actinopteri','Лучепёрые рыбы','Сәулеқанатты балықтар','Perciformes','Окунеобразные','Алабұғатәрізділер'),
('Chordata','Хордовые','Хордалылар','Amphibia','Земноводные','Қосмекендiлер','Caudata','Хвостатые','Құйрықты қосмекенділер'),
('Chordata','Хордовые','Хордалылар','Amphibia','Земноводные','Қосмекендiлер','Anura','Бесхвостые','Құйрықсыз қосмекенділер'),
('Chordata','Хордовые','Хордалылар','Reptilia','Пресмыкающиеся','Бауырымен жорғалаушылар','Squamata','Чешуйчатые','Қабыршақтылар'),
('Chordata','Хордовые','Хордалылар','Aves','Птицы','Құстар','Pelecaniformes','Веслоногие','Ескекаяқтылар'),
('Chordata','Хордовые','Хордалылар','Aves','Птицы','Құстар','Ciconiiformes','Аистообразные','Дегелектәрізділер'),
('Chordata','Хордовые','Хордалылар','Aves','Птицы','Құстар','Phoenicopteriformes','Фламингообразные','Қоқиқазтәрізділер'),
('Chordata','Хордовые','Хордалылар','Aves','Птицы','Құстар','Anseriformes','Гусеобразные','Қазтәрізділер'),
('Chordata','Хордовые','Хордалылар','Aves','Птицы','Құстар','Accipitriformes','Ястребообразные','Қаршығатәрізділер'),
('Chordata','Хордовые','Хордалылар','Aves','Птицы','Құстар','Falconiformes','Соколообразные','Сұнқартәрізділер'),
('Chordata','Хордовые','Хордалылар','Aves','Птицы','Құстар','Galliformes','Курообразные','Тауықтәрізділер'),
('Chordata','Хордовые','Хордалылар','Aves','Птицы','Құстар','Gruiformes','Журавлеобразные','Тырнатәрізділер'),
('Chordata','Хордовые','Хордалылар','Aves','Птицы','Құстар','Charadriiformes','Ржанкообразные','Татреңтәрізділер'),
('Chordata','Хордовые','Хордалылар','Aves','Птицы','Құстар','Pterocletiformes','Рябкообразные','Бұлдырықтәрізділер'),
('Chordata','Хордовые','Хордалылар','Aves','Птицы','Құстар','Columbiformes','Голубеобразные','Кептертәрізділер'),
('Chordata','Хордовые','Хордалылар','Aves','Птицы','Құстар','Strigiformes','Совообразные','Жапалақтәрізділер'),
('Chordata','Хордовые','Хордалылар','Aves','Птицы','Құстар','Passeriformes','Воробьинообразные','Торғайтәрізділер'),
('Chordata','Хордовые','Хордалылар','Mammalia','Млекопитающие','Сүтқоректiлер','Insectivora','Насекомоядные','Жәндікқоректілер'),
('Chordata','Хордовые','Хордалылар','Mammalia','Млекопитающие','Сүтқоректiлер','Chiroptera','Рукокрылые','Қолқанаттылар'),
('Chordata','Хордовые','Хордалылар','Mammalia','Млекопитающие','Сүтқоректiлер','Carnivora','Хищные','Жыртқыштар'),
('Chordata','Хордовые','Хордалылар','Mammalia','Млекопитающие','Сүтқоректiлер','Perissodactyla','Непарнокопытные','Тақтұяқтылар'),
('Chordata','Хордовые','Хордалылар','Mammalia','Млекопитающие','Сүтқоректiлер','Artiodactyla','Парнокопытные','Жұптұяқтылар'),
('Chordata','Хордовые','Хордалылар','Mammalia','Млекопитающие','Сүтқоректiлер','Rodentia','Грызуны','Кеміргіштер')
), v(n, ru, la, kk, od) as (values
(1001,'Перелия змеевидная','Perelia ophiomorpha','Жылантәрізді перелия','Lumbricomorpha'),
(1002,'Эйзения великолепная','Eisenia magnifica','Ірі эйзения','Lumbricomorpha'),
(1003,'Псевдонапеус Шнитникова','Pseudonapaeus schnitnikovi','Шнитников псеудонапэусы','Stylommatophora'),
(1004,'Туркомилакс туркестанский','Turcomilax turkestanus','Түркістан туркомилаксы','Stylommatophora'),
(1005,'Туркомилакс Цветкова','Turcomilax tzvetkovi','Цветков туркомилаксы','Stylommatophora'),
(1006,'Монахоидес акулеата','Monachoides aculeata','Монахоидес акулеатасы','Stylommatophora'),
(1007,'Туркестанский рак','Astacus kessleri','Түркістан шаяны','Decapoda'),
(1008,'Сольпуга Рикмерса','Gylippus rickmersi','Рикмерс сольпугасы','Solifugae'),
(1009,'Скорпион Лоу','Anomalobuthus lowei','Лоу сарышаяны','Scorpiones'),
(1010,'Скорпион Кривохатского','Anomalobuthus krivochatskyi','Кривохатский сарышаяны','Scorpiones'),
(1011,'Скорпион Павловского','Anomalobuthus pavlovskyi','Павловский сарышаяны','Scorpiones'),
(1012,'Тонкохвост аральский','Ischnura aralensis','Арал жіңішкеқұйрықты инелігі','Odonata'),
(1013,'Булавобрюх заметный','Cordulegaster insignis','Көрнекті шоқпарқарынды инелік','Odonata'),
(1014,'Летодетка Кириченко','Anormogomphus kiritschenkoi','Кириченко инелігі','Odonata'),
(1015,'Красотка-девушка','Calopteryx virgo','Әдеміқыз инелік','Odonata'),
(1016,'Прямобрюх южноазиатский','Orthetrum sabina','Оңтүстіказиялық тікқарын инелік','Odonata'),
(1017,'Селисия черная','Selysiothemis nigra','Селисия қара инелігі','Odonata'),
(1018,'Боливария короткокрылая','Bolivaria brachyptera','Қысқақанатты боливария','Mantodea'),
(1019,'Богомол древесный','Hierodula tenuidentata','Ағаш дәуіті','Mantodea'),
(1020,'Гуловидка бугорчатая','Deracanthina granulata','Түйіршікті деракантина','Orthoptera'),
(1021,'Толстун пустынный','Damalacantha vacca','Дамалаканта вакка шекшегі','Orthoptera'),
(1022,'Дыбка степная','Saga pedo','Дала шекшегі','Orthoptera'),
(1023,'Севчук Сервилля','Onconotus servillei','Сервилль севчугі','Orthoptera'),
(1024,'Кузнечик темнокрылый','Ceraeocercus fuscipennis','Қоңырқанатты шекшек','Orthoptera'),
(1025,'Коранус коротококрылый','Coranus subapterus','Қысқақанатты коранус','Hemiptera'),
(1026,'Арма ольховая','Arma custos','Қандыағаш қандаласы','Hemiptera'),
(1027,'Зикрона синяя','Zicrona caerulea','Көк зикрона','Hemiptera'),
(1028,'Филлоргериус Якобсона','Phyllorgerius jacobsoni','Якобсон филлоргериусы','Hemiptera'),
(1029,'Червец удлиненный','Parafairmairia elongata','Ұзынша сымыр','Hemiptera'),
(1030,'Червец галловый','Kotejacoccus orbiculus','Беріштүзгіш сымыр','Hemiptera'),
(1031,'Скакун сумеречный','Cylindera nox','Күңгірттүсті барылдауық қоңызы','Coleoptera'),
(1032,'Красотел сетчатый','Calosoma reticulatum','Торқанатты әдемі барылдауық қоңыз','Coleoptera'),
(1033,'Жужелица Геблера','Carabus gebleri','Геблер барылдауық қоңызы','Coleoptera'),
(1034,'Жужелица Михайлова','Carabus michailovi','Михайлов барылдауық қоңызы','Coleoptera'),
(1035,'Жужелица Линдеманна','Carabus lindemanni','Линденманн барылдауық қоңызы','Coleoptera'),
(1036,'Жужелица илийская','Carabus iliensis','Іле барылдауық қоңызы','Coleoptera'),
(1037,'Жужелица Хике','Carabus hiekei','Хике барылдауық қоңызы','Coleoptera'),
(1038,'Жужелица Сольского','Carabus solskyi','Сольский барылдауық қоңызы','Coleoptera'),
(1039,'Жужелица-мальчик','Carabus puer','Балауса барылдауық қоңызы','Coleoptera'),
(1040,'Жужелица восхитительная','Carabus imperialis','Керемет барылдауық қоңызы','Coleoptera'),
(1041,'Жук-олень','Lucanus cervus','Бұғы қоңыз','Coleoptera'),
(1042,'Оленек','Dorcus parallelipipedus','Балауса бұғы қоңыз','Coleoptera'),
(1043,'Подвижнорогий навозник','Odonteus armiger','Мүйізді болбосерас қиқоңызы','Coleoptera'),
(1044,'Кравчик Чичерина','Lethrus tschitscherini','Чичерин летрус қоңызы','Coleoptera'),
(1045,'Кнемизус европейский','Cnemisus rufescens','Еуропа кнемизус қоңызы','Coleoptera'),
(1046,'Гаплозома обычная','Haplosoma ordinatum','Кәдімгі гаплозома қоңызы','Coleoptera'),
(1047,'Корнеед Гангльбауэра','Dorcadion ganglbaueri','Гангльбауэр тамыржегіш қоңызы','Coleoptera'),
(1048,'Корнеед большой','Dorcadion grande','Үлкен тамыржегіш қоңыз','Coleoptera'),
(1049,'Дровосек мускусный','Turkaromia pruinosa','Іле отыншы қоңызы','Coleoptera'),
(1050,'Дровосек тамарисковый','Hesperophanes heydeni','Жыңғыл отыншы қоңызы','Coleoptera'),
(1051,'Большая туранговая златка','Capnodis miliaris metallica','Үлкен тораңғы зерқоңызы','Coleoptera'),
(1052,'Коровка Седакова','Coccinella sedakovii','Седаков қанқызы','Coleoptera'),
(1053,'Хилокорус двуточечный','Chilocorus bipustulatus','Қоснүктелі қанқызы','Coleoptera'),
(1054,'Сколия-гигант','Megascolia maculata','Алып сколия','Hymenoptera'),
(1055,'Сколия степная','Scolia hirta','Дала сколиясы','Hymenoptera'),
(1056,'Сцелифрон Шестакова','Sceliphron shestakovi','Шестаков сцелифроны','Hymenoptera'),
(1057,'Сфекс желтокрылый','Sphex flavipennis','Сарықанатты сфекс','Hymenoptera'),
(1058,'Прионикс Хаберхауэра','Prionyx haberhaueri','Харберхауэр приониксі','Hymenoptera'),
(1059,'Прионикс траурный','Prionyx macula lugens','Қаралы прионикс','Hymenoptera'),
(1060,'Лестифорус горолюбивый','Lestiphorus oreophilus','Тау лестифорусы','Hymenoptera'),
(1061,'Гоплит рыжий','Hoplitis fulva','Жирен гоплит','Hymenoptera'),
(1062,'Металлинелла белобрюхая','Metallinella leucogastra','Ақбауыр металлинелла','Hymenoptera'),
(1063,'Парарофитес округлый','Pararophites orobinus','Жұмыр парарофитес','Hymenoptera'),
(1064,'Антофора тонконогая','Anthophora gracilipes','Жіңішкеаяқты антофора','Hymenoptera'),
(1065,'Ксилокопа рыжевато-красная','Xylocopa rufa','Жирен-қызыл ксилокопа','Hymenoptera'),
(1066,'Ксилокопа блестящебрюхая','Xylocopa nitidiventris','Жылтырбауыр ксилокопа','Hymenoptera'),
(1067,'Пестрянка туркменская','Zygaena truchmena','Түрікмен ала көбелегі','Lepidoptera'),
(1068,'Хохлатка тугайная','Gluphisia oxiana','Тоғай айдарлы көбелегі','Lepidoptera'),
(1069,'Лента орденская туранговая','Catocala optima','Жолақты тораңғы көбелегі','Lepidoptera'),
(1070,'Хаймоптена оперенная','Cheimoptena pennigera','Мамықты хаймоптена көбелегі','Lepidoptera'),
(1071,'Парусник Алексанор','Papilio alexanor','Алексанор көбелегі','Lepidoptera'),
(1072,'Поликсена','Zerynthia polyxena','Поликсена','Lepidoptera'),
(1073,'Микрозегрис пламенный','Microzegris pyrothoe','Алау түсті микрозегрис','Lepidoptera'),
(1074,'Желтушка Вискотта','Colias wiskotti draconis','Вискотт сары көбелегі','Lepidoptera'),
(1075,'Желтушка Ершова','Colias erschoffi','Ершов сары көбелегі','Lepidoptera'),
(1076,'Сенница монгольская','Coenonympha mongolica','Монғол барқыт түсті көбелегі','Lepidoptera'),
(1077,'Энейс мулла','Oeneis mulla','Энейс мулл көбелегі','Lepidoptera'),
(1078,'Голубянка Мирмекида','Aricia chinensis myrmecias','Мирмекида көгілдір көбелегі','Lepidoptera'),
(1079,'Голубянка Аргали','Glaucopsyche argali','Арғали көгілдір көбелегі','Lepidoptera'),
(1080,'Голубянка Бавия','Pseudophilotes bavius','Бавия көгілдір көбелегі','Lepidoptera'),
(1081,'Голубянка Панопа','Pseudophilotes panope','Панопа көгілдір көбелегі','Lepidoptera'),
(1082,'Голубянка Татьяна','Otnjukovia tatjana','Татьяна көгілдір көбелегі','Lepidoptera'),
(1083,'Каспийская минога','Caspiomyzon wagneri','Каспий тілтісі','Petromyzoniformes'),
(1084,'Сибирский осетр','Acipenser baeri','Сібір бекіресі','Acipenseriformes'),
(1085,'Шип','Acipenser nudiventris','Кәдімгі бекіре','Acipenseriformes'),
(1086,'Сырдарьинский лжелопатонос','Pseudoscaphirhynchus fedtschenkoi','Сырдария тасбекіресі','Acipenseriformes'),
(1087,'Волжская многотычинковая сельдь','Alosa volgensis','Еділ майшабағы','Clupeiformes'),
(1088,'Каспийский лосось','Salmo caspius','Каспий албырты','Salmoniformes'),
(1089,'Аральский лосось','Salmo trutta','Арал албырты','Salmoniformes'),
(1090,'Таймень','Hucho taimen','Таймен','Salmoniformes'),
(1091,'Нельма','Stenodus nelma','Сылан','Salmoniformes'),
(1092,'Белорыбица','Stenodus leucichthys','Ақбалық','Salmoniformes'),
(1093,'Щуковидный жерех','Aspiolucius esocinus','Шортантәрізді ақмарқа','Cypriniformes'),
(1094,'Остролучка','Capoetobrama kuschakewitschi','Сүйрікқанат','Cypriniformes'),
(1095,'Аральский усач','Luciobarbus brachycephalus','Арал қаязы','Cypriniformes'),
(1096,'Туркестанский усач','Luciobarbus capito','Түркістан қаязы','Cypriniformes'),
(1097,'Илейская маринка','Schizothorax pseudoaksaiensis','Іле қара-балығы','Cypriniformes'),
(1098,'Балкашский окунь (Балкаш-илейская популяция)','Perca schrenkii','Балқаш алабұғасы (Балқаш-іле популяциясы)','Perciformes'),
(1099,'Чаткальский подкаменщик','Cottus jaxartensis','Шатқал тас тасалағышы','Perciformes'),
(1100,'Семиреченский лягушкозуб','Ranodon sibiricus','Жетісу бақатісі','Caudata'),
(1101,'Жаба Певцова','Bufotes pewzowi','Певцов құрбақасы','Anura'),
(1102,'Центральноазиатская лягушка','Rana asiatica','Қызылаяқ бақа','Anura'),
(1103,'Круглоголовка Алфераки','Phrynocephalus alpherakii','Алфераки батбаты','Squamata'),
(1104,'Зайсанская круглоголовка','Phrynocephalus melanurus','Зайсан батбаты','Squamata'),
(1105,'Серый варан','Varanus griseus','Сұр келес','Squamata'),
(1106,'Желтопузик','Pseudopus apodus','Сарылан','Squamata'),
(1107,'Джунгарская ящурка','Eremias dzungarica','Жоңғар кесірті','Squamata'),
(1108,'Тянь-Шаньская ящурка','Eremias stummeri','Тянь-шань кесірті','Squamata'),
(1109,'Центральноазиатская ящурка','Eremias vermiculata','Шұбар кесірт','Squamata'),
(1110,'Краснополосый полоз','Platyceps rhodorachis','Қызылжолақ абжылан','Squamata'),
(1111,'Желтобрюхий полоз','Dolichophis caspius','Сарықұрсақ абжылан','Squamata'),
(1112,'Палласов полоз','Elaphe sauromates','Паллас абжыланы','Squamata'),
(1113,'Полосатый полоз','Orientocoluber spinalis','Жолақты абжылан','Squamata'),
(1114,'Розовый пеликан','Pelecanus onocrotalus','Қызғылт бірқазан','Pelecaniformes'),
(1115,'Кудрявый пеликан','Pelecanus crispus','Бұйра бірқазан','Pelecaniformes'),
(1116,'Желтая цапля','Ardeola ralloides','Сарықұтан','Ciconiiformes'),
(1117,'Малая белая цапля','Egretta garzetta','Кіші аққұтан','Ciconiiformes'),
(1118,'Колпица','Platalea leucorodia','Жалбағай','Ciconiiformes'),
(1119,'Каравайка','Plegadis falcinellus','Қарабай','Ciconiiformes'),
(1120,'Туркестанский белый аист','Ciconia ciconia asiatica','Түркістан ақдегелегі','Ciconiiformes'),
(1121,'Черный аист','Ciconia nigra','Қара дегелек','Ciconiiformes'),
(1122,'Розовый фламинго','Phoenicopterus roseus','Қызғылт қоқиқаз','Phoenicopteriformes'),
(1123,'Пискулька','Anser erythropus','Шиқылдақ қаз','Anseriformes'),
(1124,'Сухонос','Anser cygnoides','Қутұмсық қаз','Anseriformes'),
(1125,'Краснозобая казарка','Branta ruficollis','Қызылжемсаулы қарашақаз','Anseriformes'),
(1126,'Лебедь-кликун','Cygnus cygnus','Сұңқылдақ аққу','Anseriformes'),
(1127,'Малый лебедь','Cygnus bewickii','Кіші аққу','Anseriformes'),
(1128,'Мраморный чирок','Marmaronetta angustirostris','Мәрмәр шүрегей','Anseriformes'),
(1129,'Белоглазый нырок','Aythya nyroca','Алакөз сүңгуір','Anseriformes'),
(1130,'Горбоносый турпан','Melanitta deglandi','Дөнтұмсық тұрпан','Anseriformes'),
(1131,'Турпан','Melanitta fusca','Тұрпан','Anseriformes'),
(1132,'Савка','Oxyura leucocephala','Ақбас үйрек','Anseriformes'),
(1133,'Скопа','Pandion haliaetus','Балықшы тұйғын','Accipitriformes'),
(1134,'Змееяд','Circaetus gallicus','Жыланшы қыран','Accipitriformes'),
(1135,'Орел-карлик','Hieraaetus pennatus','Бақалтақ қыран','Accipitriformes'),
(1136,'Степной орел','Aquila nipalensis','Дала қыраны','Accipitriformes'),
(1137,'Могильник','Aquila heliaca','Қарақұс','Accipitriformes'),
(1138,'Беркут','Aquila chrysaetos','Бүркіт','Accipitriformes'),
(1139,'Орлан-долгохвост','Haliaeetus leucoryphus','Ақбас (ақиық) субүркіт','Accipitriformes'),
(1140,'Орлан-белохвост','Haliaeetus albicilla','Аққұйрық субүркіті','Accipitriformes'),
(1141,'Бородач','Gypaetus barbatus','Сақалтай','Accipitriformes'),
(1142,'Стервятник','Neophron percnopterus','Жұртшы','Accipitriformes'),
(1143,'Кумай','Gyps himalayensis','Құмай','Accipitriformes'),
(1144,'Белоголовый сип','Gyps fulvus','Ақбас құмай','Accipitriformes'),
(1145,'Чёрный гриф','Aegypius monachus','Тазқара','Accipitriformes'),
(1146,'Кречет','Falco rusticolus','Ақсұңқар','Falconiformes'),
(1147,'Балобан','Falco cherrug','Ителгі','Falconiformes'),
(1148,'Шахин','Falco pelegrinoides','Бидайық','Falconiformes'),
(1149,'Сапсан','Falco peregrinus','Лашын','Falconiformes'),
(1150,'Алтайский улар','Tetraogallus altaicus','Алтай ұлары','Galliformes'),
(1151,'Стерх','Grus leucogeranus','Ақтырна','Gruiformes'),
(1152,'Серый журавль','Grus grus','Сұр тырна','Gruiformes'),
(1153,'Журавль-красавка','Anthropoides virgo','Ақбас тырна','Gruiformes'),
(1154,'Султанка','Porphyrio porphyrio','Көкмаңдай','Gruiformes'),
(1155,'Дрофа','Otis tarda','Дуадақ','Gruiformes'),
(1156,'Стрепет','Tetrax tetrax','Безгелдек','Gruiformes'),
(1157,'Джек','Chlamydotis macqueenii','Жорға дуадақ','Gruiformes'),
(1158,'Кречетка','Chettusia gregaria','Тарғақ','Charadriiformes'),
(1159,'Серпоклюв','Ibidorhyncha struthersii','Орақтұмсық','Charadriiformes'),
(1160,'Кроншнеп-малютка','Numenius minutus','Құртамыш шалшықшы','Charadriiformes'),
(1161,'Тонкоклювый кроншнеп','Numenius tenuirostris','Сүйіртұмсықты шалшықшы','Charadriiformes'),
(1162,'Азиатский бекасовидный веретенник','Limnodromus semipalmatus','Азиялық тарбақ шырғалақ','Charadriiformes'),
(1163,'Черноголовый хохотун','Larus ichthyaetus','Қарабас өгізшағала','Charadriiformes'),
(1164,'Реликтовая чайка','Larus relictus','Мойнақ шағала','Charadriiformes'),
(1165,'Чернобрюхий рябок','Pterocles orientalis','Қарабауыр бұлдырық','Pterocletiformes'),
(1166,'Белобрюхий рябок','Pterocles alchata','Ақбауыр бұлдырық','Pterocletiformes'),
(1167,'Саджа','Syrrhaptes paradoxus','Қылаңтөс бұлдырық','Pterocletiformes'),
(1168,'Бурый голубь','Columba eversmanni','Қоңыр кептер','Columbiformes'),
(1169,'Филин','Bubo bubo','Укі','Strigiformes'),
(1170,'Илийская саксаульная сойка','Podoces panderi ilensis','Іле сексеуіл жорғаторғайы','Passeriformes'),
(1171,'Синяя птица','Myophonus caeruleus','Көкқұс','Passeriformes'),
(1172,'Большая чечевица','Carpodacus rubicilla','Үлкен құралай','Passeriformes'),
(1173,'Белозубка малютка','Suncus etruscus','Көптісті жертесер','Insectivora'),
(1174,'Выхухоль','Desmana moschata','Жұпар','Insectivora'),
(1175,'Ночница Иконникова','Myotis ikonnikovi','Иконников жарқанаты','Chiroptera'),
(1176,'Азиатская широкоушка','Barbastella leucomelas','Азия жалпаққұлақты жарқанаты','Chiroptera'),
(1177,'Кожанок Бобринского','Eptesicus bobrinskii','Бобринский жарқанаты','Chiroptera'),
(1178,'Белобрюхий стрелоух','Otonycteris hemprichii','Ақбауыр жарқанат','Chiroptera'),
(1179,'Широкоухий складчатогуб','Tadarida teniotis','Бүрмеерінді кеңқұлақ жарқанат','Chiroptera'),
(1180,'Красный волк','Cuon alpinus','Қызыл қасқыр','Carnivora'),
(1181,'Тянь-Шаньский бурый медведь','Ursus arctos isabellinus','Тянь-шань қоңыр аюы','Carnivora'),
(1182,'Каменная куница','Martes foina','Тас сусары','Carnivora'),
(1183,'Лесная куница','Martes martes','Орман сусары','Carnivora'),
(1184,'Европейская норка','Mustela lutreola','Еуропа күзені','Carnivora'),
(1185,'Перевязка','Vormela peregusna','Шұбар күзен','Carnivora'),
(1186,'Медоед','Mellivora capensis','Итаю','Carnivora'),
(1187,'Среднеазиатская речная выдра','Lutra lutra seistanica','Ортаазиялық өзен кәмшаты','Carnivora'),
(1188,'Гепард','Acinonyx jubatus','Қабылан','Carnivora'),
(1189,'Тигр','Panthera tigris','Жолбарыс','Carnivora'),
(1190,'Переднеазиатский леопард','Panthera pardus saxicolor','Парсы алабарысы','Carnivora'),
(1191,'Снежный барс','Panthera uncia','Барыс','Carnivora'),
(1192,'Барханный кот','Felis margarita','Шағыл мысығы','Carnivora'),
(1193,'Камышовый кот','Felis chaus','Қамыс мысығы','Carnivora'),
(1194,'Манул','Otocolobus manul','Сабаншы','Carnivora'),
(1195,'Каракал','Caracal caracal','Қарақал','Carnivora'),
(1196,'Туркестанская рысь','Lynx lynx isabellinus','Түркістан сілеусіні','Carnivora'),
(1197,'Каспийский тюлень','Pusa caspica','Каспий итбалығы','Carnivora'),
(1198,'Лошадь Пржевальского','Equus ferus przewalskii','Керқұлан','Perissodactyla'),
(1199,'Туркменский кулан','Equus hemionus kulan','Түрікмен құланы','Perissodactyla'),
(1200,'Тугайный олень','Cervus hanglu bactrianus','Тоғай кермаралы','Artiodactyla'),
(1201,'Джейран','Gazella subgutturosa','Қарақұйрық','Artiodactyla'),
(1202,'Устюртский горный баран','Ovis vignei arkal','Устірт арқары','Artiodactyla'),
(1203,'Алтайский горный баран','Ovis ammon ammon','Алтай арқары','Artiodactyla'),
(1204,'Кызылкумский горный баран','Ovis ammon severtzovi','Қызылқұм арқары','Artiodactyla'),
(1205,'Казахстанский горный баран','Ovis ammon collium','Қазақстан арқары','Artiodactyla'),
(1206,'Тянь-Шаньский горный баран','Ovis ammon karelini','Тянь-шань арқары','Artiodactyla'),
(1207,'Каратауский горный баран','Ovis ammon nigrimontana','Қаратау арқары','Artiodactyla'),
(1208,'Сурок Мензбира','Marmota menzbieri','Көк суыр','Rodentia'),
(1209,'Индийский дикобраз','Hystrix indica','Үнді жайрасы','Rodentia'),
(1210,'Селевиния','Selevinia betpakdalensis','Жалман','Rodentia'),
(1211,'Пятипалый карликовый тушканчик','Cardiocranius paradoxus','Бессаусақты ергежейлі қосаяқ','Rodentia'),
(1212,'Карликовый тушканчик Гептнера','Salpingotus heptneri','Гептнер ергежейлі қосаяғы','Rodentia'),
(1213,'Бледный карликовый тушканчик','Salpingotus pallidus','Боз ергежейлі қосаяқ','Rodentia'),
(1214,'Жирнохвостый карликовый тушканчик','Salpingotus crassicauda','Майқұйрық ергежейлі қосаяқ','Rodentia'),
(1215,'Уральский слепыш','Spalax uralensis','Жайық көртышқаны','Rodentia'),
(1216,'Хомячок Роборовского','Phodopus roborovskii','Роборовский атжалманы','Rodentia'),
(1217,'Желтая пеструшка','Eolagurus luteus','Сары алақоржын','Rodentia')
)
insert into public.red_book_species (list_no, name_ru, latin, name_kk, rank, parent_latin, phylum, phylum_ru, phylum_kk,
  class_lat, class_ru, class_kk, order_lat, order_ru, order_kk, kingdom, author)
select v.n, v.ru, v.la, v.kk,
       case when array_length(string_to_array(v.la, ' '), 1) >= 3 then 'subspecies' else 'species' end,
       case when array_length(string_to_array(v.la, ' '), 1) >= 3 then split_part(v.la, ' ', 1) || ' ' || split_part(v.la, ' ', 2) end,
       o.ph, o.ph_ru, o.ph_kk, o.cl, o.cl_ru, o.cl_kk, o.od, o.od_ru, o.od_kk, 'animalia', 'Красная книга РК (животные, импорт)'
from v join o on o.od = v.od
on conflict (lower(latin)) do update set list_no = excluded.list_no, name_ru = excluded.name_ru, name_kk = excluded.name_kk,
  rank = excluded.rank, parent_latin = excluded.parent_latin, kingdom = 'animalia',
  phylum = excluded.phylum, phylum_ru = excluded.phylum_ru, phylum_kk = excluded.phylum_kk,
  class_lat = excluded.class_lat, class_ru = excluded.class_ru, class_kk = excluded.class_kk,
  order_lat = excluded.order_lat, order_ru = excluded.order_ru, order_kk = excluded.order_kk;

-- обогащение: GBIF с учётом царства; у животных одна страница точек (≤300)
do $do$
declare src text := pg_get_functiondef('public.rb_enrich_one(bigint)'::regprocedure);
begin
  src := replace(src, $q$'https://api.gbif.org/v1/species/match?verbose=false&name='$q$,
         $q$'https://api.gbif.org/v1/species/match?verbose=false&kingdom=' || case when s.kingdom = 'animalia' then 'Animalia' else 'Plantae' end || '&name='$q$);
  src := replace(src, 'for off in 0..1 loop', $q$for off in 0..(case when s.kingdom = 'animalia' then 0 else 1 end) loop$q$);
  execute src;
end $do$;

create or replace function public.rb_fill_template() returns int language plpgsql security definer set search_path = public as $$
declare k int;
begin
  update red_book_species s set
    description_ru = coalesce(nullif(description_ru, ''), name_ru || ' (лат. ' || latin || ') — '
      || case when rank = 'species' then 'вид' else 'подвид' end || ' рода ' || coalesce(genus, split_part(latin, ' ', 1))
      || ' семейства ' || coalesce(family_ru || ' (' || family || ')', family, '—')
      || case when kingdom = 'animalia' then coalesce(', отряд ' || lower(order_ru), '') || coalesce(', класс ' || lower(class_ru), '')
              || '. Редкий вид животных, занесённый в Красную книгу Республики Казахстан.'
              else '. Редкое растение, занесённое в Красную книгу Республики Казахстан.' end
      || case when exists (select 1 from red_book_points p where p.species_id = s.id)
              then ' Известные места находок в Казахстане показаны на карте.' else '' end),
    description_kk = coalesce(nullif(description_kk, ''), name_kk || ' (лат. ' || latin || ') — '
      || coalesce(family_kk, family, '') || ', ' || coalesce(genus, split_part(latin, ' ', 1))
      || ' туысына жататын ' || case when rank = 'species' then 'түр' else 'түр тармағы' end
      || case when kingdom = 'animalia' then coalesce(' (' || order_kk || ' отряды, ' || class_kk || ' класы)', '')
              || '. Қазақстан Республикасының Қызыл кітабына енгізілген сирек жануар.'
              else '. Қазақстан Республикасының Қызыл кітабына енгізілген сирек өсімдік.' end
      || case when exists (select 1 from red_book_points p where p.species_id = s.id)
              then ' Қазақстандағы белгілі табылған жерлері картада көрсетілген.' else '' end)
  where list_no is not null and enrich ? 'pts' and (coalesce(description_ru, '') = '' or coalesce(description_kk, '') = '');
  get diagnostics k = row_count;
  return k;
end $$;
revoke all on function public.rb_fill_template() from public, anon, authenticated;

-- редактирование систематики животных
do $do$
declare src text := pg_get_functiondef('public.api_rb_save_ext(text,bigint,jsonb,text,text)'::regprocedure);
begin
  src := replace(src, '    updated_at = now()', $q$    phylum    = case when f ? 'phylum' then nullif(trim(f->>'phylum'), '') else s.phylum end,
    phylum_ru = case when f ? 'phylum_ru' then nullif(trim(f->>'phylum_ru'), '') else s.phylum_ru end,
    phylum_kk = case when f ? 'phylum_kk' then nullif(trim(f->>'phylum_kk'), '') else s.phylum_kk end,
    class_lat = case when f ? 'class_lat' then nullif(trim(f->>'class_lat'), '') else s.class_lat end,
    class_ru  = case when f ? 'class_ru' then nullif(trim(f->>'class_ru'), '') else s.class_ru end,
    class_kk  = case when f ? 'class_kk' then nullif(trim(f->>'class_kk'), '') else s.class_kk end,
    order_lat = case when f ? 'order_lat' then nullif(trim(f->>'order_lat'), '') else s.order_lat end,
    order_ru  = case when f ? 'order_ru' then nullif(trim(f->>'order_ru'), '') else s.order_ru end,
    order_kk  = case when f ? 'order_kk' then nullif(trim(f->>'order_kk'), '') else s.order_kk end,
    updated_at = now()$q$);
  execute src;
end $do$;

-- API с фильтром по царству
drop function if exists public.api_rb_list(text, text, text, text);
create or replace function public.api_rb_list(p_kind text default 'all', p_name text default 'all',
    p_q text default null, p_category text default null, p_kingdom text default 'plantae')
returns json language sql stable security definer set search_path = public, extensions as $$
  select coalesce(json_agg(r order by r.category nulls last, r.list_no, r.name_ru), '[]'::json) from (
    select s.id, s.latin, s.name_ru, s.name_kk, s.rank, s.parent_latin, s.family, s.family_ru, s.family_kk, s.genus,
           s.kingdom, s.class_lat, s.class_ru, s.class_kk, s.order_lat, s.order_ru, s.order_kk,
           s.category, s.taxon_id, s.photo is not null as has_photo, s.photo_url, s.author, s.updated_at, s.list_no,
           (select count(*) from red_book_points p where p.species_id = s.id) as n_points,
           (select count(*) from red_book_ranges g where g.species_id = s.id) as n_ranges
    from red_book_species s
    where s.kingdom = coalesce(p_kingdom, 'plantae')
      and (coalesce(p_q, '') = '' or s.latin ilike '%' || p_q || '%' or s.name_ru ilike '%' || p_q || '%'
           or s.name_kk ilike '%' || p_q || '%' or s.family ilike '%' || p_q || '%'
           or s.family_ru ilike '%' || p_q || '%' or s.family_kk ilike '%' || p_q || '%'
           or s.class_ru ilike '%' || p_q || '%' or s.order_ru ilike '%' || p_q || '%'
           or s.class_kk ilike '%' || p_q || '%' or s.order_kk ilike '%' || p_q || '%')
      and (coalesce(p_category, '') = '' or s.category = p_category)
      and (p_kind = 'all'
           or exists (select 1 from red_book_points p where p.species_id = s.id
                      and ((p_kind = 'region' and p.region = p_name) or (p_kind = 'zone' and p.zone = p_name)))
           or exists (select 1 from red_book_ranges g join areas a on a.kind = p_kind and a.name = p_name
                      where g.species_id = s.id and ST_Intersects(g.geom, a.geom)))
  ) r;
$$;

drop function if exists public.api_rb_map(text, text, text);
create or replace function public.api_rb_map(p_kind text default 'all', p_name text default 'all',
    p_auth text default null, p_kingdom text default 'plantae')
returns json language plpgsql stable security definer set search_path = public, extensions as $$
declare ed boolean := rb_is_editor(p_auth);
begin
  return json_build_object(
    'points', (select coalesce(json_agg(json_build_array(q.lat, q.lng, q.id, q.latin, q.name_ru, q.name_kk, q.category)), '[]'::json)
        from (select distinct on (s.id, case when ed then p.lat else round(p.lat::numeric, 1)::float8 end,
                                        case when ed then p.lng else round(p.lng::numeric, 1)::float8 end)
                     case when ed then p.lat else round(p.lat::numeric, 1)::float8 end as lat,
                     case when ed then p.lng else round(p.lng::numeric, 1)::float8 end as lng,
                     s.id, s.latin, s.name_ru, s.name_kk, s.category
              from red_book_points p join red_book_species s on s.id = p.species_id
              where s.kingdom = coalesce(p_kingdom, 'plantae')
                and (p_kind = 'all' or (p_kind = 'region' and p.region = p_name) or (p_kind = 'zone' and p.zone = p_name))) q),
    'ranges', (select coalesce(json_agg(json_build_object(
        'species_id', s.id, 'latin', s.latin, 'name_ru', s.name_ru, 'name_kk', s.name_kk, 'category', s.category,
        'geojson', ST_AsGeoJSON(ST_SimplifyPreserveTopology(g.geom, 0.005), 4)::json)), '[]'::json)
        from red_book_ranges g join red_book_species s on s.id = g.species_id
        where s.kingdom = coalesce(p_kingdom, 'plantae')
          and (p_kind = 'all' or exists (select 1 from areas a where a.kind = p_kind and a.name = p_name
                                         and ST_Intersects(a.geom, g.geom)))));
end $$;

do $do$
declare src text := pg_get_functiondef('public.api_rb_get(bigint,text)'::regprocedure);
begin
  src := replace(src, 's.family_kk, s.genus, s.category, s.gbif_key,',
    's.family_kk, s.genus, s.category, s.gbif_key, s.kingdom, s.phylum, s.phylum_ru, s.phylum_kk, s.class_lat, s.class_ru, s.class_kk, s.order_lat, s.order_ru, s.order_kk,');
  execute src;
end $do$;

grant execute on function public.api_rb_list(text, text, text, text, text), public.api_rb_map(text, text, text, text)
  to anon, authenticated;

-- запуск автозаполнения (Википедию для основного справочника на время ставим на паузу)
select cron.alter_job((select jobid from cron.job where jobname = 'flora-wiki'), active := false);
select cron.schedule('flora-redbook', '* * * * *',
  $c$set statement_timeout = 0; select public.rb_enrich_batch(3); select public.rb_fill_template(); select public.rb_finish_check();$c$);

select count(*) filter (where kingdom = 'animalia') animals, count(*) filter (where kingdom = 'plantae') plants,
       (select left(pg_get_functiondef('public.rb_enrich_one(bigint)'::regprocedure), 0) is not null) ok,
       position('kingdom=' in pg_get_functiondef('public.rb_enrich_one(bigint)'::regprocedure)) > 0 gbif_kingdom,
       position('class_lat' in pg_get_functiondef('public.api_rb_get(bigint,text)'::regprocedure)) > 0 get_cols,
       position('order_kk' in pg_get_functiondef('public.api_rb_save_ext(text,bigint,jsonb,text,text)'::regprocedure)) > 0 save_cols
from public.red_book_species;

-- раздел (царство) можно задать при сохранении — новые виды в разделе «Животные»
do $do$
declare src text := pg_get_functiondef('public.api_rb_save_ext(text,bigint,jsonb,text,text)'::regprocedure);
begin
  src := replace(src, '    phylum    = case', $q$    kingdom   = case when f->>'kingdom' in ('plantae', 'animalia') then f->>'kingdom' else s.kingdom end,
    phylum    = case$q$);
  execute src;
end $do$;

-- русские и казахские названия семейств животных
insert into public.rb_families (latin, ru, kk)
select v.* from (values
('Lumbricidae','Люмбрициды (дождевые черви)','Жауынқұрттар'),
('Enidae','Энидовые','Энидалар'),
('Limacidae','Слизни','Жалаңаш ұлулар'),
('Hygromiidae','Гигромииды','Гигромиидалар'),
('Astacidae','Речные раки','Өзен шаяндары'),
('Gylippidae','Гилиппиды','Гилиппидалар'),
('Buthidae','Бутиды','Бутидалар'),
('Coenagrionidae','Стрелки','Тілтебендер'),
('Cordulegastridae','Булавобрюхи','Шоқпарқарындар'),
('Gomphidae','Дедки','Гомфидалар'),
('Calopterygidae','Красотки','Әдеміқыздар'),
('Libellulidae','Настоящие стрекозы','Нағыз инеліктер'),
('Mantidae','Богомоловые','Дәуіттер'),
('Empusidae','Эмпузовые','Эмпузалар'),
('Tettigoniidae','Настоящие кузнечики','Нағыз шекшектер'),
('Reduviidae','Хищнецы','Жыртқыш қандалалар'),
('Pentatomidae','Щитники','Қалқанша қандалалар'),
('Dictyopharidae','Диктиофариды','Диктиофаридтер'),
('Eriococcidae','Войлочники','Кіз сымырлар'),
('Coccidae','Ложнощитовки','Жалған қалқаншалар'),
('Carabidae','Жужелицы','Барылдауық қоңыздар'),
('Cicindelidae','Скакуны','Секіргіш қоңыздар'),
('Lucanidae','Рогачи','Бұғы қоңыздар'),
('Bolboceratidae','Болбоцератиды','Болбоцератидтер'),
('Geotrupidae','Навозники-землерои','Жерқазғыш қиқоңыздар'),
('Glaphyridae','Глафириды','Глафиридтер'),
('Scarabaeidae','Пластинчатоусые','Пластинкамұрттылар'),
('Melolonthidae','Хрущи','Зауза қоңыздар'),
('Cerambycidae','Усачи','Мұртты қоңыздар'),
('Buprestidae','Златки','Зерқоңыздар'),
('Coccinellidae','Божьи коровки','Қанқызылар'),
('Scoliidae','Сколии','Сколиялар'),
('Sphecidae','Роющие осы','Жерқазғыш аралар'),
('Crabronidae','Краброниды','Крабронидтер'),
('Megachilidae','Пчёлы-листорезы','Жапырақкескіш аралар'),
('Apidae','Настоящие пчёлы','Нағыз аралар'),
('Zygaenidae','Пестрянки','Алакөбелектер'),
('Notodontidae','Хохлатки','Айдарлы көбелектер'),
('Erebidae','Эребиды','Эребидтер'),
('Noctuidae','Совки','Түнкөбелектер'),
('Geometridae','Пяденицы','Өлшеуіш көбелектер'),
('Papilionidae','Парусники','Желкенқанаттылар'),
('Pieridae','Белянки','Ақкөбелектер'),
('Nymphalidae','Нимфалиды','Нимфалидтер'),
('Lycaenidae','Голубянки','Көгілдір көбелектер'),
('Petromyzontidae','Миноговые','Тілтістер'),
('Acipenseridae','Осетровые','Бекірелер'),
('Clupeidae','Сельдевые','Майшабақтар'),
('Alosidae','Алозовые','Алозалар'),
('Salmonidae','Лососевые','Албырттар'),
('Cyprinidae','Карповые','Тұқылар'),
('Leuciscidae','Ельцовые','Ақмарқалар'),
('Xenocyprididae','Ксеноциприды','Ксеноципридтер'),
('Percidae','Окуневые','Алабұғалар'),
('Cottidae','Рогатковые','Тасалағыштар'),
('Hynobiidae','Углозубы','Бақатістілер'),
('Bufonidae','Жабы','Құрбақалар'),
('Ranidae','Лягушки','Бақалар'),
('Agamidae','Агамовые','Агамалар'),
('Varanidae','Варановые','Келестер'),
('Anguidae','Веретеницевые','Сарыландар'),
('Lacertidae','Настоящие ящерицы','Нағыз кесірткелер'),
('Colubridae','Ужеобразные','Сужыландар'),
('Pelecanidae','Пеликановые','Бірқазандар'),
('Ardeidae','Цаплевые','Құтандар'),
('Threskiornithidae','Ибисовые','Ибистер'),
('Ciconiidae','Аистовые','Дегелектер'),
('Phoenicopteridae','Фламинговые','Қоқиқаздар'),
('Anatidae','Утиные','Үйректер'),
('Pandionidae','Скопиные','Балықшы тұйғындар'),
('Accipitridae','Ястребиные','Қаршығалар'),
('Falconidae','Соколиные','Сұңқарлар'),
('Phasianidae','Фазановые','Қырғауылдар'),
('Gruidae','Журавлиные','Тырналар'),
('Rallidae','Пастушковые','Тартарлар'),
('Otididae','Дрофиные','Дуадақтар'),
('Charadriidae','Ржанковые','Татрендер'),
('Ibidorhynchidae','Серпоклювовые','Орақтұмсықтар'),
('Scolopacidae','Бекасовые','Шалшықшылар'),
('Laridae','Чайковые','Шағалалар'),
('Pteroclidae','Рябковые','Бұлдырықтар'),
('Columbidae','Голубиные','Кептерлер'),
('Strigidae','Совиные','Жапалақтар'),
('Corvidae','Врановые','Қарғалар'),
('Muscicapidae','Мухоловковые','Шыбыншылар'),
('Fringillidae','Вьюрковые','Құралайлар'),
('Soricidae','Землеройковые','Жертесерлер'),
('Talpidae','Кротовые','Кроттар'),
('Vespertilionidae','Гладконосые летучие мыши','Тегістұмсық жарқанаттар'),
('Molossidae','Бульдоговые летучие мыши','Бүрмеерінді жарқанаттар'),
('Canidae','Псовые','Иттер'),
('Ursidae','Медвежьи','Аюлар'),
('Mustelidae','Куньи','Сусарлар'),
('Felidae','Кошачьи','Мысықтар'),
('Phocidae','Настоящие тюлени','Итбалықтар'),
('Equidae','Лошадиные','Жылқылар'),
('Cervidae','Оленьи','Бұғылар'),
('Bovidae','Полорогие','Қуысмүйізділер'),
('Sciuridae','Беличьи','Тиіндер'),
('Hystricidae','Дикобразовые','Жайралар'),
('Gliridae','Соневые','Ұйқышылар'),
('Dipodidae','Тушканчиковые','Қосаяқтар'),
('Spalacidae','Слепышовые','Көртышқандар'),
('Cricetidae','Хомяковые','Атжалмандар')
) v(latin, ru, kk) where not exists (select 1 from public.rb_families f where f.latin = v.latin);
update public.red_book_species s set family_ru = coalesce(s.family_ru, f.ru), family_kk = coalesce(s.family_kk, f.kk)
  from public.rb_families f where f.latin = s.family and (s.family_ru is null or s.family_kk is null);
select cron.schedule('flora-redbook', '* * * * *',
  $c$set statement_timeout = 0; select public.rb_enrich_batch(3); update public.red_book_species s set family_ru = coalesce(s.family_ru, f.ru), family_kk = coalesce(s.family_kk, f.kk) from public.rb_families f where f.latin = s.family and (s.family_ru is null or s.family_kk is null); select public.rb_fill_template(); select public.rb_finish_check();$c$);
select count(*) from public.rb_families;

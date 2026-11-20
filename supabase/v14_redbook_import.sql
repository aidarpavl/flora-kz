
-- =============================================================
-- v14: Красная книга РК — импорт 387 видов + автозаполнение в БД
-- таксономия (GBIF), фото (iNaturalist / Википедия), описания (Википедия ru/kk,
-- перевод ru→kk при отсутствии казахской статьи), точки находок в Казахстане (GBIF + iNat).
-- =============================================================
alter table public.red_book_species
  add column if not exists genus text,
  add column if not exists family_ru text,
  add column if not exists family_kk text,
  add column if not exists photo_url text,
  add column if not exists photo_attr text,
  add column if not exists gbif_key bigint,
  add column if not exists list_no int,
  add column if not exists enrich jsonb not null default '{}'::jsonb;

insert into public.red_book_species (list_no, name_ru, latin, name_kk, author)
select v.n, v.ru, v.la, v.kk, 'Красная книга РК (импорт)'
from (values
(1,'Абелия щитковидная','Abelia corymbosa','Қалқанды асаймүсей'),
(2,'Абрикос обыкновенный','Armeniaca vulgaris','Кәдімгі өрік'),
(3,'Адиантум венерин волос','Adiantum capillus-veneris','Шолпаншаш сүмбіл'),
(4,'Адонис весенний','Adonis vernalis','Көктем жанаргүлі'),
(5,'Адонис волжский','Adonis wolgensis','Еділ жанаргүлі'),
(6,'Адонис золотистый','Adonis chrysocyathus','Жылтыр жанаргүл'),
(7,'Адонис пушистый','Adonis villosa','Түкті жанаргүл'),
(8,'Адонис тяньшанский','Adonis tianschanica','Тянь-Шань жанаргүлі'),
(9,'Акантолимон Линчевского','Acantholimon linczevskii','Линчевский кемпіршөбі'),
(10,'Акантолимон тарбагатайский','Acantholimon tarbagataicum','Тарбағатай кемпіршөбі'),
(11,'Акантолимон Титова','Acantholimon titovii','Титов кемпіршөбі'),
(12,'Аллохруза качимовидная','Allochrusa gypsophiloides','Қаңбақ тәрізді жерсабын'),
(13,'Альдрованда пузырчатая','Aldrovanda vesiculosa','Бүршікті дәнел'),
(14,'Анафалис кистеносный','Anaphalis racemifera','Шашақ тәріздес бозтүк'),
(15,'Арника Ильина','Arnica iljinii','Ильин арникасы'),
(16,'Аронник Королькова','Arum korolkowii','Корольков шаяноты'),
(17,'Арцевтобиум можжевельниковый','Arceuthobium oxycedri','Арша шажыр'),
(18,'Астеротамнус кустарниковый','Asterothamnus fruticosus','Буталық ақбасбалау'),
(19,'Астрагал беловойлочный','Astragalus candidissimus','Ақ түкті таспа'),
(20,'Астрагал волосистоцветковый','Astragalus trichanthus','Түкті гүлді таспа'),
(21,'Астрагал джимский','Astragalus dshimensis','Жым таспасы'),
(22,'Астрагал зайсанский','Astragalus zaissanensis','Зайсан таспасы'),
(23,'Астрагал каратауский','Astragalus karataviensis','Қаратау таспасы'),
(24,'Астрагал кендырлыкский','Astragalus kendyrlyki','Кендірлік таспасы'),
(25,'Астрагал кокашикский','Astragalus kokaschikii','Көкашық таспасы'),
(26,'Астрагал копальский','Astragalus kopalensis','Қопал таспасы'),
(27,'Астрагал ложноракитниковый','Astragalus pseudocytisoides','Жалған шілікті таспа'),
(28,'Астрагал почтитройчатый','Astragalus subternatus','Дерлік үшқабатты таспа'),
(29,'Астрагал птицеклювый','Astragalus ornithorrhynchus','Қос тұмсықты таспа'),
(30,'Астрагал Рубцова','Astragalus rubtzovii','Рубцов таспасы'),
(31,'Астрагал сладколистый','Astragalus glycyphyllos','Тәтті жапырақты таспа'),
(32,'Астрагал Сумневича','Astragalus sumneviczii','Сумневич таспасы'),
(33,'Астрагал тонкостебельный','Astragalus leptocaulis','Жіңішке сабақты таспа'),
(34,'Астрагал чарынский','Astragalus tscharynensis','Шарын таспасы'),
(35,'Астрагал Штейнберга','Astragalus steinbergianus','Штейнберг таспасы'),
(36,'Афлатуния вязолистая','Louiseania ulmifolia','Шегіршін жапырақты тасжаңғақ'),
(37,'Багульник болотный','Ledum palustre','Саз қазанақ'),
(38,'Бадан угамский','Bergenia ugamica','Үгем бадамы'),
(39,'Баранец обыкновенный','Huperzia selago','Таңдамалы гуперция'),
(40,'Барбарис илийский','Berberis iliensis','Іле бөріқарақаты'),
(41,'Барбарис каркаралинский','Berberis karkaralensis','Қарқаралы бөріқарақаты'),
(42,'Башмачок крупноцветный','Cypripedium macranthos','Ірі гүлді шолпанкебіс'),
(43,'Башмачок настоящий','Cypripedium calceolus','Нағыз шолпанкебіс'),
(44,'Башмачок пятнистый','Cypripedium guttatum','Секпіл шолпанкебіс'),
(45,'Безвременник жёлтый','Colchicum luteum','Сары лапыз'),
(46,'Безвременник Кессельринга','Colchicum kesselringii','Кессельринг лапызы'),
(47,'Берёза киргизская','Betula kirghisorum','Қырғыз қайыңы'),
(48,'Берёза таласская','Betula talassica','Талас қайыңы'),
(49,'Берёза Ярмоленковская','Betula jarmolenkoana','Ярмоленко қайыңы'),
(50,'Бересклет бородавчатый','Euonymus verrucosus','Сүйелді қабыржық'),
(51,'Бересклет Коопмана','Euonymus koopmannii','Коопман қабыржығы'),
(52,'Болотник Верещагина','Limnas veresczaginii','Верещагин саздақшөбі'),
(53,'Болотноцветник щитолистный','Nymphoides peltata','Қалқан жапырақты батпақгүл'),
(54,'Борец таласский','Aconitum talassicum','Талас бәрпісі'),
(55,'Бороздосемянник Попова','Aulacospermum popovii','Попов аулакоспермумы'),
(56,'Бочанцевия каратауская','Botschantzevia karatavica','Қаратау бочанцевиясы'),
(57,'Боярышник сомнительный','Crataegus ambigua','Күмәнді долана'),
(58,'Бузульник Павлова','Ligularia pavlovii','Павлов сарыандызы'),
(59,'Бурачок Федченко','Alyssum fedtschenkoanum','Федченко жауылшасы'),
(60,'Валериана снеголюбивая','Valeriana chionophila','Қаршыл шүйіншөп'),
(61,'Василёк Культиасова','Centaurea kultiassovii','Культиасов гүлкекіресі'),
(62,'Василёк Талиева','Centaurea taliewii','Талиев гүлкекіресі'),
(63,'Василёк туркестанский','Centaurea turkestanica','Түркістан гүлкекіресі'),
(64,'Василёк шерстистоногий','Centaurea lasiopoda','Түкті аяқ гүлкекіре'),
(65,'Вероника алатауская','Veronica alatavica','Алатау бөденешөбі'),
(66,'Вероника тимьянная','Veronica serpylloides','Жебір бөденешөбі'),
(67,'Виноград дикий','Vitis vinifera','Жабайы жүзім'),
(68,'Водосбор Виталия','Aquilegia vitalii','Виталий шөмішгүлі'),
(69,'Водосбор каратауский','Aquilegia karatavica','Қаратау шөмішгүлі'),
(70,'Водяной орех','Trapa natans','Сужаңғақ, шылым'),
(71,'Володушка розеточная','Bupleurum rosulare','Жертаран шоқсары'),
(72,'Волосореберник Голоскокова','Pilopleura goloskokovii','Голоскоков көкшолағы'),
(73,'Волчеягодник алтайский','Daphne altaica','Алтай қасқыржидегі'),
(74,'Вороний глаз обыкновенный','Paris quadrifolia','Кәдімгі қарғакөз'),
(75,'Вьюнок персидский','Convolvulus persicus','Парсы шырмауығы'),
(76,'Гвоздика Андржевского','Dianthus andrzejowskianus','Андржевский қалампыры'),
(77,'Гелиотроп маленький','Heliotropium parvulum','Кіші сүйелжазар'),
(78,'Гиалолена чу-илийская','Hyalolaena tschuiliensis','Шу-Іле шыбынқанаты'),
(79,'Гимноспермиум алтайский','Gymnospermium altaicum','Алтай гимноспермиумы'),
(80,'Гладкосемянница бесстебельная','Leiospora exscapa','Сабақсыз лейоспора'),
(81,'Горечавка джунгарская','Gentiana dshungarica','Жоңғар шерменгүлі'),
(82,'Горицвет кожистый','Coronaria coriacea','Қыртысты жалынгүл'),
(83,'Гребенщик Андросова','Tamarix androssowii','Андросов жыңғылы, кеңөзегі'),
(84,'Гусиный лук новый Попова','Gagea neopopovii','Жаңа Попов қазжуасы'),
(85,'Диктиофора сдвоенная','Dictyophora duplicata','Торлы диктиофора'),
(86,'Дифазиаструм альпийский','Diphasiastrum alpinum','Альпі дифизиаструмы'),
(87,'Долгоног снеговой','Macropodium nivale','Қар дәуаяғы'),
(88,'Дорема каратауская','Dorema karataviense','Қаратау сасыққурайы'),
(89,'Дремлик болотный','Epipactis palustris','Батпақ жылантамыры'),
(90,'Дуб обыкновенный','Quercus robur','Кәдімгі емен'),
(91,'Ежовник тургайский','Anabasis turgaica','Торғай бұйырғыны'),
(92,'Желтушник оранжевый','Erysimum croceum','Жирен ақбасқурай'),
(93,'Жестковенечник пятирогий','Sclerotiaria pentaceros','Бес мүйізді қаттыбас'),
(94,'Живокость клиновидная','Delphinium cuneatum','Сына жапырақты тегеурінгүл'),
(95,'Живокость саурская','Delphinium sauricum','Сауыр тегеурінгүлі'),
(96,'Жимолость илийская','Lonicera iliensis','Іле ұшқаты'),
(97,'Жимолость каратауская','Lonicera karataviensis','Қаратау ұшқаты'),
(98,'Жузгун печальный','Calligonum triste','Қоңыр жүзген'),
(99,'Зимолюбка зонтичная','Chimaphila umbellata','Шатырша қысшылшөп'),
(100,'Змееголовник каратауский','Dracocephalum karataviense','Қаратау жыланбасы'),
(101,'Иконниковия Кауфмановская','Ikonnikovia kaufmanniana','Кауфман ирекжапырағы'),
(102,'Иридодиктиум Винклера','Iridodictyum winkleri','Винклер иридодиктиумы'),
(103,'Иридодиктиум Колпаковского','Iridodictyum kolpakowskianum','Колпаковский иридодиктиумы'),
(104,'Камыш казахстанский','Scirpus kasachstanicus','Қазақстан өлеңшөбі'),
(105,'Кандык сибирский','Erythronium sibiricum','Сібір қандығы'),
(106,'Канкриниелла Крашенинникова','Cancriniella krascheninnikovii','Крашенинников сартүтігі'),
(107,'Карагана трагакантовая','Caragana tragacanthoides','Тікенді қараған'),
(108,'Каратавия Культиасова','Karatavia kultiassovii','Культиасов каратавиясы'),
(109,'Каркас кавказский','Celtis caucasica','Кавказ таудағаны'),
(110,'Касатик Альберта','Iris albertii','Альберт құртқашашы'),
(111,'Касатик Людвига','Iris ludwigii','Людвиг құртқашашы'),
(112,'Касатик тигровый','Iris tigridia','Тарғыл құртқашаш'),
(113,'Катран беззубый','Crambe edentula','Тіссіз қатыран'),
(114,'Катран татарский','Crambe tataria','Татар қатыраны'),
(115,'Кауфмания Семёнова','Kaufmannia semenovii','Семёнов лөңкесі'),
(116,'Качим аулиеатинский','Gypsophila aulieatensis','Әулиеата қаңбағы'),
(117,'Кермек Михельсона','Limonium michelsonii','Михельсон кермегі'),
(118,'Кермек Резниченковский','Limonium rezniczenkoanum','Резниченко кермегі'),
(119,'Кизильник каратауский','Cotoneaster karatavicus','Қаратау ырғайы'),
(120,'Клаваридельфус пестиковый','Clavariadelphus pistillaris','Аналық мүйіз саңырауқұлақ'),
(121,'Клавулина хрящеватая','Clavulina cartilaginea','Берішті клавулина'),
(122,'Кладина оленья (Кладония оленья), ягель','Cladonia rangiferina','Кладина, Бұғы мүгі'),
(123,'Клевеция удивительная','Queletia mirabilis','Керемет клевеция'),
(124,'Клоповник Мейера','Lepidium meyeri','Мейер шытырмағы'),
(125,'Клюква мелкоплодная','Oxycoccus microcarpus','Ұсақ жемісті мүкжидек'),
(126,'Ковыль каратауский','Stipa karataviensis','Қаратау бозы'),
(127,'Ковыль кунгейский','Stipa kungeica','Күнгей бозы'),
(128,'Ковыль перистый','Stipa pennata','Қау боз, ақ селеу'),
(129,'Ковыль уклоняющийся','Stipa anomala','Таспа боз'),
(130,'Ковыль южноалтайский','Stipa austroaltaica','Оңтүстік Алтай бозы'),
(131,'Козелец тау-сагыз','Scorzonera tau-saghyz','Таусағыз'),
(132,'Козелец хантауский','Scorzonera chantavica','Хантау таусағызы'),
(133,'Козополянския туркестанская','Kosopoljanskia turkestanica','Түркістан козополянскиясы'),
(134,'Копеечник бектауатауский','Hedysarum bectauatavicum','Бектауата тиынтағы'),
(135,'Копеечник каратауский','Hedysarum karataviense','Қаратау тиынтағы'),
(136,'Копеечник мынжылкинский','Hedysarum mindshilkense','Мыңжылқы тиынтағы'),
(137,'Копеечник прутьевидный','Hedysarum scoparium','Шыбықша тиынтағы'),
(138,'Копеечник Разумовского','Hedysarum razoumovianum','Разумовский тиынтағы'),
(139,'Котовник заилийский','Nepeta transiliensis','Іле көкжалбызы'),
(140,'Красноднев жёлтый','Hemerocallis lilioasphodelus','Сарғыш сарана'),
(141,'Крестовник огненноязычковый','Senecio pyroglossus','Қызыл тілді зиягул'),
(142,'Криптокодон одноглавый','Cryptocodon monocephalus','Дара бас ершін'),
(143,'Крупка мелкоплодная','Draba microcarpella','Ұсақ жемісті әжік'),
(144,'Кувшинка белая','Nymphaea alba','Ақ су лалагүл'),
(145,'Кузиния Вавилова','Cousinia vavilovii','Вавилов көбеңқұйрығы'),
(146,'Кузиния жесткая','Cousinia rigida','Қатты көбеңқұйрық'),
(147,'Кузиния крупнолистная','Cousinia grandifolia','Ірі жапырақты көбеңқұйрық'),
(148,'Кузиния мынжылкинская','Cousinia mindshelkensis','Мыңжылқы көбеңқұйрығы'),
(149,'Курчавка вальковатолистая','Atraphaxis teretifolia','Жұмыртқа жапырақ түйесіңір'),
(150,'Курчавка Мушкетова','Atraphaxis muschketowii','Мушкетов түйесіңірі'),
(151,'Ландыш майский','Convallaria majalis','Мамыр меруертгүлі'),
(152,'Лапчатка тяньшанская','Potentilla tianschanica','Тянь-Шань қазтабаны'),
(153,'Паракариум каратауский','Paracaryum karataviense','Қаратау емшені'),
(154,'Латук удивительный','Lactuca mira','Тамаша сүтжапырақ'),
(155,'Лебеда Фомина','Atriplex fominii','Фомин көкпегі'),
(156,'Ледебуриелла жабрицевидная','Ledebouriella seseloides','Желбезекше ледебуриелла'),
(157,'Ленец Минквица','Thesium minkwitzianum','Минквиц кендіршесі'),
(158,'Лепехиниелла Михаила','Lepechiniella michaelis','Михаил басағы'),
(159,'Лепидолофа каратауская','Lepidolopha karatavica','Қаратау сетені'),
(160,'Лещина обыкновенная','Corylus avellana','Кәдімгі шаттауық орманжаңғақ'),
(161,'Лжепустынноколосник Северцова','Pseuderemostachys sewerzowii','Северцов жалған шөлмасағы'),
(162,'Лилия кудреватая','Lilium martagon','Бұйра лалагүл'),
(163,'Липучка оголённая','Lappula glabrata','Жалаң кәріқыз'),
(164,'Ложная шандра пустынноколосниковая','Pseudomarrubium eremostachydioides','Шөлмасақты жалған бұйражапырақ'),
(165,'Ложноочиток каратауский','Pseudosedum karatavicum','Қаратау бозкілемі'),
(166,'Лотос орехоносный','Nelumbo nucifera','Жаңғақты лотос'),
(167,'Лук афлатунский','Allium aflatunense','Афлатун жуасы'),
(168,'Лук дернистый','Allium caespitosum','Қыртысты жуа'),
(169,'Лук желтоватый','Allium lutescens','Сары жуа'),
(170,'Лук кастекский','Allium kasteki','Қастек жуасы'),
(171,'Лук мелкосетчатый, черемша','Allium microdictyon','Ұсақ торлы жуа'),
(172,'Лук многокорневой','Allium polyrhizum','Көп тамырлы жуа'),
(173,'Лук монгольский','Allium mongolicum','Монғол жуасы'),
(174,'Лук пскемский','Allium pskemense','Піскем жуасы'),
(175,'Лук Сергея','Allium sergii','Сергей жуасы'),
(176,'Лук Суворова','Allium suworowii','Суворов жуасы'),
(177,'Лук турчинский','Allium turtschicum','Турчин жуасы'),
(178,'Лук Эдуарда','Allium eduardii','Эдуард жуасы'),
(179,'Льнянка меловая','Linaria cretacea','Бор сиякөгі'),
(180,'Любка двулистная','Platanthera bifolia','Қос жапырақты жұпаршөп'),
(181,'Люцерна тяньшанская','Medicago tianschanica','Тянь-Шань жоңышқасы'),
(182,'Майкараган волжский','Calophaca wolgarica','Еділ майқарағаны'),
(183,'Майкараган джунгарский','Calophaca soongorica','Жоңғар майқарағаны'),
(184,'Мак тоненький','Papaver tenellum','Жіңішке көкнәр'),
(185,'Марена меловая','Rubia cretacea','Бор рияны'),
(186,'Марена Павлова','Rubia pavlovii','Павлов рияны'),
(187,'Марена Резниченковская','Rubia rezniczenkoana','Резниченко рияны'),
(188,'Медиазия крупнолистная','Mediasia macrophylla','Ірі жапырақты медиазия'),
(189,'Мерендера коренастая','Merendera robusta','Мығым дестегүл'),
(190,'Мертензия джагастайская','Mertensia dshagastanica','Жағастай дембеті'),
(191,'Мертензия Попова','Mertensia popovii','Попов дембеті'),
(192,'Мертензия тарбагатайская','Mertensia tarbagataica','Тарбағатай дембеті'),
(193,'Метастахис стреловидный','Metastachydium sagittatum','Садақша найзабас'),
(194,'Меч-трава обыкновенная','Cladium mariscus','Кәдімгі семсершөп'),
(195,'Миндаль Ледебуровский','Amygdalus ledebouriana','Ледебур бадамы'),
(196,'Можжевельник зеравшанский','Juniperus seravschanica','Зеравшан аршасы'),
(197,'Молочай твердобокальчатый','Euphorbia sclerocyathium','Берік сүттіген'),
(198,'Молочай Ярослава','Euphorbia jaroslavii','Ярослав сүттігені'),
(199,'Мордовник зайсанский','Echinops saissanicus','Зайсан лаксасы'),
(200,'Мордовник казахский','Echinops kasakorum','Қазақ лаксасы'),
(201,'Мордовник равновысокий','Echinops fastigiatus','Біркелкі биік лакса'),
(202,'Морина кокандская','Morina kokanica','Қоқан салпысы'),
(203,'Мухомор щетинистый','Amanita solitaria','Тікенді шыбынжұт'),
(204,'Мытник тарбагатайский','Pedicularis tarbagataica','Тарбағатай қандыгүлі'),
(205,'Мытник чу-илийский','Pedicularis czuiliensis','Шу-Іле қандыгүлі'),
(206,'Мягкоплодник критмолистный','Malacocarpus crithmifolius','Критможапырақты жұмсақжеміс'),
(207,'Наголоватка алматинская','Jurinea almaatensis','Алматы ақжапырағы'),
(208,'Наголоватка головоногая','Jurinea cephalopoda','Аяқбас ақжапырақ'),
(209,'Наголоватка мощная','Jurinea robusta','Қалың ақжапырақ'),
(210,'Наголоватка мугоджарская','Jurinea mugodsharica','Мұғалжар ақжапырағы'),
(211,'Наголоватка превосходная','Jurinea eximia','Көркем ақжапырақ'),
(212,'Наголоватка Федченко','Jurinea fedtschenkoana','Федченко ақжапырағы'),
(213,'Надбородник безлистый','Epipogium aphyllum','Жапырақсыз орашық'),
(214,'Недзвецкия семиреченская','Niedzwedzkia semiretschenskia','Жетісу қызыладыраспаны'),
(215,'Неоторулария каратауская','Neotorularia karatavica','Қаратау неоторулариясы'),
(216,'Неуролома Бекетова','Neuroloma beketovii','Бекетов неуроломасы'),
(217,'Норичник джунгарский','Scrophularia dshungarica','Жоңғар сабынкөгі'),
(218,'Норичник Нурании','Scrophularia nuraniae','Нурания сабынкөгі'),
(219,'Одуванчик Виталия','Taraxacum vitalii','Виталий бақбағы'),
(220,'Одуванчик кок-сагыз','Taraxacum kok-saghyz','Көк-сағыз бақбағы'),
(221,'Ольха клейкая','Alnus glutinosa','Жабысқақ қандыағаш'),
(222,'Ортотрихум приглаженный','Orthotrichum laevigatum','Жатаған ортотрихум'),
(223,'Осмориза остистая','Osmorhiza aristata','Қылтанды дәлен'),
(224,'Островския великолепная','Ostrowskia magnifica','Әдемі ойраш'),
(225,'Остролодочник алматинский','Oxytropis almaatensis','Алматы кекегі'),
(226,'Остролодочник двулопастный','Oxytropis biloba','Қосбұдыр кекек'),
(227,'Остролодочник иглистый','Oxytropis hystrix','Инелі кекек'),
(228,'Остролодочник каратауский','Oxytropis karataviensis','Қаратау кекегі'),
(229,'Остролодочник Недзвецкого','Oxytropis niedzweckiana','Недзвецкий кекегі'),
(230,'Остролодочник почтимутовчатый','Oxytropis subverticillaris','Дерлік күлтебасты кекек'),
(231,'Остролодочник саурский','Oxytropis saurica','Сауыр кекегі'),
(232,'Остролодочник таласский','Oxytropis talassica','Талас кекегі'),
(233,'Остролодочник угамский','Oxytropis ugamica','Үгем кекегі'),
(234,'Остролодочник шиповатый','Oxytropis echidna','Бұдыр кекек'),
(235,'Пальчатокоренник Фукса','Dactylorhiza fuchsii','Фукс бармақтамыры'),
(236,'Паракариум цельнокрайний','Paracaryum integerrimum','Бүтін жиекті емшен'),
(237,'Парнолистник каратауский','Zygophyllum karatavicum','Қаратау түйетабаны'),
(238,'Парнолистник Потанина','Zygophyllum potaninii','Потанин түйетабаны'),
(239,'Пастернаковник ледниковый','Pastinacopsis glacialis','Мұз ботташ'),
(240,'Пахифиссиденс крупнолиственный','Pachyfissidens grandifrons','Ірі жапырақты пахифиссиденс'),
(241,'Первоцвет Минквица','Primula minkwitziae','Минквиц наурызгүлі, наурызшешегі'),
(242,'Переступень черноплодный','Bryonia melanocarpa','Қара жемісті итжүзім'),
(243,'Песчанка Потанина','Arenaria potaninii','Потанин құмдақшөбі'),
(244,'Печеночница Фальконера','Hepatica falconeri','Фальконер бауыршөбі'),
(245,'Пижма скальная','Tanacetum saxicola','Тастақ түймешетені'),
(246,'Пижма улытауская','Tanacetum ulutavicum','Ұлытау түймешетені'),
(247,'Пион Марьин-корень','Paeonia anomala','Шұғылық'),
(248,'Пион степной','Paeonia hybrida','Дала шұғылығы, сәлдегүл'),
(249,'Пиретрум Келлера','Pyrethrum kelleri','Келлер кестежусаны'),
(250,'Пиретрум североджунгарский','Pyrethrum arctodzhungaricum','Солтүстік жоңғар кестежусаны'),
(251,'Плагиобазис васильковый','Plagiobasis centauroides','Гүлкекірелі себетбас'),
(252,'Подлесник европейский','Sanicula europaea','Еуропа орманоты'),
(253,'Полипорус корнелюбивый','Polyporus rhizophilus','Тамырсүйгіш полипорус'),
(254,'Полынь цитварная','Artemisia cina','Дермене жусан'),
(255,'Прангос Гердера (Кахрис Гердера)','Prangos herderi','Гердер (Кахрис Гердер) сайсабағы'),
(256,'Прангос пушистоцветковый','Prangos lachnantha','Түктігүлді сайсабақ'),
(257,'Прангос хвощевидный','Prangos equisetoides','Қырықбуын тәрізді сайсабақ'),
(258,'Прострел желтоватый','Pulsatilla flavescens','Сарғылт құндызшөп'),
(259,'Прострел раскрытый, Сон-трава','Pulsatilla patens','Ашық құндызшөп, ұйқышөп'),
(260,'Птицемлечник Фишеровский','Ornithogalum fischerianum','Фишер құссүттігені'),
(261,'Пупавка Корнух-Троцкого','Anthemis trotzkiana','Корнух-Троцкий өгізкөзі'),
(262,'Пушистотычиночник лопатчатый','Pterygostemon spathulatus','Күрекше мамықбас'),
(263,'Рапонтикум аулиеатинский','Rhaponticum aulieatense','Әулиеата аюдәрісі'),
(264,'Рапонтикум каратауский','Rhaponticum karatavicum','Қаратау аюдәрісі'),
(265,'Рапонтикум сафлоровидный','Rhaponticum carthamoides','Сафлор тәріздес аюдәрі'),
(266,'Рафидофитон Регеля','Rhaphidophyton regelii','Регель рафидофитоны'),
(267,'Ревень алтайский','Rheum altaicum','Алтай рауғашы'),
(268,'Ревень Виттрока','Rheum wittrockii','Виттрок рауғашы'),
(269,'Резуха мынжылкинская','Arabis mindshilkensis','Мыңжылқы ақшешегі'),
(270,'Резуха Попова','Arabis popovii','Попов ақшешегі'),
(271,'Риндера светло-жёлтая','Rindera ochroleuca','Ақсары жуантамыр'),
(272,'Родиола розовая','Rhodiola rosea','Қызғылт семізот, алтынтамыр'),
(273,'Росянка круглолистая','Drosera rotundifolia','Дөңгелек жапырақты шықшөп'),
(274,'Рябина персидская','Sorbus persica','Парсы шетені'),
(275,'Рябчик бледноцветковый','Fritillaria pallidiflora','Ақшыл секпілгүл'),
(276,'Саксаульник илийский','Arthrophytum iliense','Іле сексеуілшесі'),
(277,'Семеновия Рубцова','Semenovia rubtzovii','Рубцов таушығы'),
(278,'Серпуха джунгарская','Serratula dshungarica','Жоңғар түймебасы'),
(279,'Сетчатоголовник оттянутый','Dictyocephalus attenuatus','Сопақша торлыбас'),
(280,'Сибирка алтайская','Sibiraea altaiensis','Алтай суықшөбі'),
(281,'Сибирка тяньшанская','Sibiraea tianschanica','Тянь-Шань суықшөбі'),
(282,'Синеголовник каратауский','Eryngium karatavicum','Қаратау көкбасы'),
(283,'Скутигер тянь-шанский','Scutiger tianschanicus','Тянь-Шань скутигері'),
(284,'Смолёвка бетпакдалинская','Silene betpakdalensis','Бетпақдала сылдыршөбі'),
(285,'Смолёвка меловая','Silene cretacea','Бор сылдыршөбі'),
(286,'Смолёвка Муслима','Silene muslimii','Мүслім сылдыршөбі'),
(287,'Смолёвка сырдарьинская','Silene jaxartica','Сырдария сылдыршөбі'),
(288,'Смолёвка тяньшанская','Silene tianschanica','Тянь-Шань сылдыршөбі'),
(289,'Смородина Янчевского','Ribes janczewskii','Янчевский қарақаты'),
(290,'Сморчок степной','Morchella steppicola','Дала тыржыңқұлағы'),
(291,'Солонечник скальный','Galatella saxatilis','Жартас далазығыры'),
(292,'Солянка хивинская','Salsola chiwensis','Хиуа сораңы'),
(293,'Солянка широколистная','Salsola euryphylla','Жалпақ жапырақты сораң'),
(294,'Соссюрея Микешина','Saussurea mikeschinii','Микешин шұбаршөбі'),
(295,'Соссюрея обвернутая','Saussurea involucrata','Орамалы шұбаршөп'),
(296,'Спарассис казахстанский','Sparassis kazakhstanica','Қазақстан спарасисы'),
(297,'Спаржа Введенского','Asparagus vvedenskyi','Введенский қасқыржемісі'),
(298,'Стеллеропсис тарбагатайский','Stelleropsis tarbagataica','Тарбағатай таушешегі'),
(299,'Стеллеропсис тяньшанский','Stelleropsis tianschanica','Тянь-Шань таушешегі'),
(300,'Стланиковая форма ели Шренка','Picea schrenkiana f. prostrata','Шренк шыршасы (жатаған түрі)'),
(301,'Строгановия коренастая','Stroganowia robusta','Тамыры нық ергеш'),
(302,'Строгановия сердцелистная','Stroganowia cardiophylla','Жүрек жапырақты ергеш'),
(303,'Строгановия стрелолистая','Stroganowia sagittata','Жебе жапырақты ергеш'),
(304,'Строгановия Траутфеттера','Stroganowia trautvetteri','Траутфеттер ергеші'),
(305,'Сфагнум гладкий','Sphagnum teres','Жатық сфагнум'),
(306,'Таволгоцвет Шренка','Spiraeanthus schrenkianus','Шренк тобылғытүсі'),
(307,'Танацетопсис Голоскокова','Tanacetopsis goloskokovii','Голоскоков сертебесі'),
(308,'Танацетопсис Пятаевой','Tanacetopsis pjataevae','Пятаева сертебесі'),
(309,'Толокнянка обыкновенная','Arctostaphylos uva-ursi','Кәдімгі аюжидек, аюбүлдірген'),
(310,'Тонконог жестколистный','Koeleria sclerophylla','Қатты жапырақты дұғаш'),
(311,'Тополь беркаринский','Populus berkarensis','Беркара терегі'),
(312,'Тополь сизолистый','Populus pruinosa','Тораңғыл терек'),
(313,'Трихантемис аулиеатинский','Trichanthemis aulieatensis','Әулиеата саржауы'),
(314,'Тугайя илийская','Tugaja iliensis','Іле тугайясы'),
(315,'Тюльпан Альберта','Tulipa alberti','Альберт қызғалдағы'),
(316,'Тюльпан Биберштейна','Tulipa biebersteiniana','Биберштейн қызғалдағы'),
(317,'Тюльпан Борщова','Tulipa borszczowii','Борщов қызғалдағы'),
(318,'Тюльпан Грейга','Tulipa greigii','Грейг қызғалдағы'),
(319,'Тюльпан двуцветковый','Tulipa biflora','Қос гүлді қызғалдақ'),
(320,'Тюльпан Зинаиды','Tulipa zenaidae','Зинаида қызғалдағы'),
(321,'Тюльпан Кауфмановский','Tulipa kaufmanniana','Кауфман қызғалдағы'),
(322,'Тюльпан Колпаковского','Tulipa kolpakowskiana','Колпаковский қызғалдағы'),
(323,'Тюльпан Королькова','Tulipa korolkowii','Корольков қызғалдағы'),
(324,'Тюльпан короткотычиночный','Tulipa brachystemon','Қысқа аталықты қызғалдақ'),
(325,'Тюльпан Леманновский','Tulipa lehmanniana','Леманн қызғалдағы'),
(326,'Тюльпан одноцветковый','Tulipa uniflora','Дара гүлді қызғалдақ'),
(327,'Тюльпан Островского','Tulipa ostrowskiana','Островский қызғалдағы'),
(328,'Тюльпан поздний','Tulipa tarda','Кеш қызғалдақ'),
(329,'Тюльпан поникающий','Tulipa patens','Жатаған қызғалдақ'),
(330,'Тюльпан разнолепестный','Tulipa heteropetala','Ала күлтелі қызғалдақ'),
(331,'Тюльпан Регеля','Tulipa regelii','Регель қызғалдағы'),
(332,'Тюльпан Шренка','Tulipa schrenkii','Шренк қызғалдағы'),
(333,'Угамия ангренская','Ugamia angrenica','Ангрен қалпақбасы'),
(334,'Унгерния Северцова','Ungernia sewerzowii','Северцов унгерниясы'),
(335,'Феллориния шишковатая','Phellorinia strobilina','Бүрлікті феллориния'),
(336,'Ферула белополосчатая','Ferula leucographa','Ақжолақ сасыр'),
(337,'Ферула гипсолюбивая','Ferula gypsacea','Гипсшіл сасыр'),
(338,'Ферула гладкая','Ferula glaberrima','Тегіс сасыр'),
(339,'Ферула горичниколистная','Ferula peucedanifolia','Ащы жапырақты сасыр'),
(340,'Ферула илийская','Ferula iliensis','Іле сасыры, илан'),
(341,'Ферула Крылова','Ferula krylovii','Крылов сасыры'),
(342,'Ферула ксероморфная','Ferula xeromorpha','Құрғақ сасыр'),
(343,'Ферула мягколистная','Ferula malacophylla','Жұмсақ жапырақты сасыр'),
(344,'Ферула сюгатинская','Ferula sugatensis','Сөгеті сасыры'),
(345,'Ферула таукумская','Ferula taucumica','Тауқұм сасыры'),
(346,'Фисташка настоящая','Pistacia vera','Кәдімгі пісте'),
(347,'Фломоидес Зинаиды, Пустынноколосник','Phlomoides zenaidae','Зинаида фломоидесі, Шөлмасақ'),
(348,'Хетолимон щетинчатый','Chaetolimon setiferum','Тікенді келіншекшөп'),
(349,'Хламидопус Мейена','Chlamydopus meyenianus','Мейен хламидопусы'),
(350,'Хондрила Кузнецова','Chondrilla kusnezovii','Кузнецов жерсағызы'),
(351,'Хохлатка Семёнова','Corydalis semenovii','Семёнов айдаршөбі'),
(352,'Цельнолистник джунгарский','Haplophyllum dshungaricum','Жоңғар тұтасжапырағы'),
(353,'Цельнолистник Евгения Коровина','Haplophyllum eugenii-korovinii','Евгений Коровин тұтасжапырағы'),
(354,'Цимбария даурская','Cymbaria daurica','Дауыр бақаауызы'),
(355,'Чезнея джунгарская','Chesneya dshungarica','Жоңғар аспарасы'),
(356,'Черепоплодник ёжистый','Craniospermum echioides','Кірпі бас сүйектұқым'),
(357,'Чина Ледебура','Lathyrus ledebourii','Ледебур әйкені'),
(358,'Чулактавия скальная','Tschulaktavia saxatilis','Жартас чулактавиясы'),
(359,'Шампиньон таблитчатый','Agaricus tabularis','Кестелі қозықұйрық'),
(360,'Шаровница точечная','Globularia punctata','Сопақша допшагүл'),
(361,'Шафран алатауский','Crocus alatavicus','Алатау запыраны, ботатабан'),
(362,'Шафран Королькова','Crocus korolkowii','Корольков запыраны'),
(363,'Шиповник Павлова','Rosa pavlovii','Павлов итмұрыны'),
(364,'Шлемник каратауский','Scutellaria karatavica','Қаратау томағашөбі'),
(365,'Шлемник лодочковый','Scutellaria navicularis','Қайықша томағашөп'),
(366,'Шлемник почтидернистый','Scutellaria subcaespitosa','Дерлік түбірлі томағашөп'),
(367,'Шмальгаузения гнездистая','Schmalhausenia nidulans','Ұялы шмальгаузения'),
(368,'Шпажник черепитчатый','Gladiolus imbricatus','Қатпар баршынгүл'),
(369,'Шренкия Культиасова','Schrenkia kultiassovii','Культиасов батаны'),
(370,'Штубендорфия тонкая','Stubendorffia gracilis','Жіңішке пайыз'),
(371,'Шуровския Маргариты','Schtschurowskia margaritae','Маргарита щуровскиясы'),
(372,'Щитница яруточная','Clypeola jonthlaspi','Яруткалық кірпікшөп'),
(373,'Щитовник мынжылкинский','Dryopteris mindshelkensis','Мыңжылқы усасыр қырыққұлағы'),
(374,'Эминиум Леманна','Eminium lehmannii','Леманн күшаласы, ит күшала'),
(375,'Эремогоне турланская','Eremogone turlanica','Түрлан құмдақшөбі'),
(376,'Эремурус Иларии','Eremurus hilariae','Илария шырышы'),
(377,'Эспарцет алатауский','Onobrychis alatavica','Алатау эспарцеті'),
(378,'Эутрема ложносердцелистная','Eutrema pseudocordifolium','Жалған жүрек жапырақты деңгел'),
(379,'Юнона алматинская','Juno almaatensis','Алматы шиқылдағы'),
(380,'Юнона голубая','Juno coerulea','Жасыл шиқылдақ'),
(381,'Юнона Кушакевича','Juno kuschakewiczii','Кушакевич шиқылдағы'),
(382,'Юнона орхидная','Juno orchioides','Сүйсін шиқылдақ'),
(383,'Яблоня Недзвецкого','Malus niedzwetzkyana','Недзвецкий алмасы'),
(384,'Яблоня Сиверса','Malus sieversii','Сиверс алмасы'),
(385,'Ясень согдийский','Fraxinus sogdiana','Соғды шағаны'),
(386,'Ястребинка кумбельская','Hieracium kumbelicum','Құмбел саршатыры'),
(387,'Ятрышник шлемовидный','Orchis militaris','Телпек сүйсін')
) as v(n, ru, la, kk)
on conflict (lower(latin)) do update
  set list_no = excluded.list_no, name_ru = excluded.name_ru, name_kk = excluded.name_kk;

-- ---------- HTTP-помощники ----------
create or replace function public.rb_get_json(p_url text) returns jsonb
language plpgsql security definer set search_path = public, extensions as $$
declare r extensions.http_response;
begin
  perform extensions.http_set_curlopt('CURLOPT_TIMEOUT', '20');
  r := extensions.http((('GET', p_url, array[extensions.http_header('User-Agent', 'FloraKZ/1.0 (flora-kz.streamlit.app)')],
                          null, null))::extensions.http_request);
  if r.status = 429 then raise exception 'HTTP_429'; end if;
  if r.status <> 200 then return null; end if;
  return r.content::jsonb;
exception when others then
  if sqlerrm = 'HTTP_429' then raise; end if;
  return null;
end $$;

-- машинный перевод (ru→kk, en→ru …), режет текст на куски по предложениям
create or replace function public.rb_tr(p_text text, p_sl text, p_tl text) returns text
language plpgsql security definer set search_path = public, extensions as $$
declare parts text[]; chunk text := ''; s text; outp text := ''; js jsonb; seg jsonb;
begin
  if coalesce(trim(p_text), '') = '' then return null; end if;
  parts := regexp_split_to_array(left(p_text, 6000), '(?<=[.!?;])\s+');
  foreach s in array parts || array[null::text] loop
    if s is null or length(chunk) + length(s) > 1200 then
      if chunk <> '' then
        js := rb_get_json('https://translate.googleapis.com/translate_a/single?client=gtx&dt=t&sl=' || p_sl
                          || '&tl=' || p_tl || '&q=' || extensions.urlencode(chunk));
        if js is null then return null; end if;
        for seg in select * from jsonb_array_elements(js->0) loop
          outp := outp || coalesce(seg->>0, '');
        end loop;
        outp := outp || ' ';
      end if;
      chunk := coalesce(s, '');
    else
      chunk := trim(chunk || ' ' || s);
    end if;
  end loop;
  return nullif(trim(outp), '');
end $$;

-- статья Википедии: вступление, ссылка, миниатюра, казахская интервики
create or replace function public.rb_wiki(p_lang text, p_title text) returns jsonb
language plpgsql security definer set search_path = public, extensions as $$
declare js jsonb; pg jsonb;
begin
  if coalesce(trim(p_title), '') = '' then return null; end if;
  js := rb_get_json('https://' || p_lang || '.wikipedia.org/w/api.php?action=query&format=json&redirects=1'
        || '&prop=extracts%7Cinfo%7Cpageimages%7Clanglinks&inprop=url&exintro=1&explaintext=1'
        || '&piprop=thumbnail&pithumbsize=640&lllang=kk&titles=' || extensions.urlencode(p_title));
  select value into pg from jsonb_each(js->'query'->'pages') limit 1;
  if pg is null or pg ? 'missing' or coalesce(pg->>'extract', '') = '' then return null; end if;
  -- страницы-неоднозначности не берём
  if pg->>'extract' ~* '(может означать|может относиться|may refer to)' then return null; end if;
  return pg;
end $$;

-- ---------- обогащение одного вида ----------
create or replace function public.rb_enrich_one(p_id bigint) returns jsonb
language plpgsql security definer set search_path = public, extensions as $$
declare s record; e jsonb; js jsonb; r jsonb; t_ru text; pg jsonb; kpg jsonb; en jsonb; kt text;
        k bigint; n int := 0; desc_ru text; desc_kk text; ru_url text; kk_url text; thumb text;
begin
  select * into s from red_book_species where id = p_id;
  e := s.enrich;

  -- 1. таксономия (GBIF) + фото и id (iNaturalist)
  if not e ? 'tax' then
    js := rb_get_json('https://api.gbif.org/v1/species/match?verbose=false&name=' || extensions.urlencode(s.latin));
    if js is not null and js->>'matchType' <> 'NONE' then
      update red_book_species set
        family = coalesce(js->>'family', family),
        genus = coalesce(js->>'genus', split_part(s.latin, ' ', 1)),
        rank = case lower(js->>'rank') when 'subspecies' then 'subspecies' when 'variety' then 'variety'
                                       when 'form' then 'form' else 'species' end,
        parent_latin = case when lower(js->>'rank') in ('subspecies', 'variety', 'form') then js->>'species' else parent_latin end,
        gbif_key = coalesce((js->>'acceptedUsageKey')::bigint, (js->>'usageKey')::bigint)
      where id = p_id;
    else
      update red_book_species set genus = split_part(s.latin, ' ', 1) where id = p_id;
    end if;
    js := rb_get_json('https://api.inaturalist.org/v1/taxa?per_page=10&locale=ru&q=' || extensions.urlencode(s.latin));
    select x into r from jsonb_array_elements(js->'results') x
      where lower(x->>'name') = lower(s.latin) or lower(x->>'matched_term') = lower(s.latin)
      order by (lower(x->>'name') = lower(s.latin)) desc limit 1;
    if r is null then
      select x into r from jsonb_array_elements(js->'results') x
        where lower(x->>'name') like lower(split_part(s.latin, ' ', 1) || ' ' || split_part(s.latin, ' ', 2)) || '%' limit 1;
    end if;
    if r is not null then
      update red_book_species set
        taxon_id = coalesce(taxon_id, (r->>'id')::bigint),
        photo_url = coalesce(photo_url, replace(r->'default_photo'->>'medium_url', 'square', 'medium')),
        photo_attr = coalesce(photo_attr, r->'default_photo'->>'attribution')
      where id = p_id;
    end if;
    e := e || '{"tax": true}';
    update red_book_species set enrich = e where id = p_id;
    select * into s from red_book_species where id = p_id;
  end if;

  -- 2. описание (Википедия) на двух языках
  if not e ? 'wiki' then
    t_ru := trim(regexp_replace(split_part(s.name_ru, ',', 1), '\s*\(.*\)', ''));
    pg := rb_wiki('ru', t_ru);
    if pg is null then pg := rb_wiki('ru', s.latin); end if;
    if pg is not null then
      desc_ru := pg->>'extract'; ru_url := pg->>'fullurl'; thumb := pg->'thumbnail'->>'source';
      kt := pg->'langlinks'->0->>'*';
    else
      en := rb_wiki('en', s.latin);
      if en is not null then
        desc_ru := rb_tr(en->>'extract', 'en', 'ru'); ru_url := en->>'fullurl'; thumb := en->'thumbnail'->>'source';
      end if;
    end if;
    kpg := rb_wiki('kk', coalesce(kt, split_part(s.name_kk, ',', 1)));
    if kpg is not null and length(kpg->>'extract') >= 150 then
      desc_kk := kpg->>'extract'; kk_url := kpg->>'fullurl';
    elsif desc_ru is not null then
      desc_kk := rb_tr(desc_ru, 'ru', 'kk');
    elsif en is not null then
      desc_kk := rb_tr(en->>'extract', 'en', 'kk');
    end if;
    update red_book_species set
      description_ru = coalesce(nullif(description_ru, ''), desc_ru),
      description_kk = coalesce(nullif(description_kk, ''), desc_kk),
      wiki_ru_url = coalesce(wiki_ru_url, ru_url), wiki_kk_url = coalesce(wiki_kk_url, kk_url),
      photo_url = coalesce(photo_url, thumb),
      photo_attr = case when photo_url is null and thumb is not null then 'Wikipedia / Wikimedia Commons' else photo_attr end
    where id = p_id;
    e := e || jsonb_build_object('wiki', true, 'wiki_ru', desc_ru is not null, 'wiki_kk_native', kk_url is not null);
    update red_book_species set enrich = e where id = p_id;
    select * into s from red_book_species where id = p_id;
  end if;

  -- 3. точки находок в Казахстане: GBIF + наблюдения iNaturalist из нашей базы
  if not e ? 'pts' then
    if s.gbif_key is not null then
      for off in 0..1 loop
        js := rb_get_json('https://api.gbif.org/v1/occurrence/search?country=KZ&hasCoordinate=true'
              || '&hasGeospatialIssue=false&limit=300&offset=' || (off * 300) || '&taxonKey=' || s.gbif_key);
        exit when js is null;
        insert into red_book_points (species_id, lat, lng, observed_on, note_ru, note_kk)
        select distinct on (round((x->>'decimalLatitude')::numeric, 2), round((x->>'decimalLongitude')::numeric, 2))
               p_id, (x->>'decimalLatitude')::float8, (x->>'decimalLongitude')::float8,
               case when left(x->>'eventDate', 10) ~ '^\d{4}-\d{2}-\d{2}$' then left(x->>'eventDate', 10)::date end,
               'GBIF: ' || coalesce(x->>'datasetName', x->>'institutionCode', '') ||
                 case x->>'basisOfRecord' when 'PRESERVED_SPECIMEN' then ' (гербарий)' when 'HUMAN_OBSERVATION' then ' (наблюдение)' else '' end,
               'GBIF: ' || coalesce(x->>'datasetName', x->>'institutionCode', '') ||
                 case x->>'basisOfRecord' when 'PRESERVED_SPECIMEN' then ' (гербарий)' when 'HUMAN_OBSERVATION' then ' (бақылау)' else '' end
        from jsonb_array_elements(js->'results') x
        where x ? 'decimalLatitude' and coalesce((x->>'coordinateUncertaintyInMeters')::float8, 0) <= 20000
          and not exists (select 1 from red_book_points q where q.species_id = p_id
                          and round(q.lat::numeric, 2) = round((x->>'decimalLatitude')::numeric, 2)
                          and round(q.lng::numeric, 2) = round((x->>'decimalLongitude')::numeric, 2));
        get diagnostics k = row_count; n := n + k;
        exit when coalesce((js->>'endOfRecords')::boolean, true);
      end loop;
    end if;
    if s.taxon_id is not null then
      insert into red_book_points (species_id, lat, lng, observed_on, note_ru, note_kk)
      select distinct on (round(o.lat::numeric, 2), round(o.lng::numeric, 2))
             p_id, o.lat, o.lng, o.observed_on, 'iNaturalist: ' || coalesce(o.user_login, ''), 'iNaturalist: ' || coalesce(o.user_login, '')
      from observations o
      where o.taxon_id = s.taxon_id and o.lat is not null
        and not exists (select 1 from red_book_points q where q.species_id = p_id
                        and round(q.lat::numeric, 2) = round(o.lat::numeric, 2) and round(q.lng::numeric, 2) = round(o.lng::numeric, 2))
      limit 300;
      get diagnostics k = row_count; n := n + k;
    end if;
    e := e || jsonb_build_object('pts', n);
    update red_book_species set enrich = e, updated_at = now() where id = p_id;
  end if;
  return e;
end $$;

create or replace function public.rb_enrich_batch(p_n int default 5) returns text
language plpgsql security definer set search_path = public, extensions as $$
declare r record; done int := 0;
begin
  for r in select id from red_book_species
           where list_no is not null and not (enrich ? 'pts') and coalesce((enrich->>'tries')::int, 0) < 3
           order by list_no limit p_n loop
    begin
      perform rb_enrich_one(r.id);
      done := done + 1;
    exception when others then
      update red_book_species set enrich = enrich || jsonb_build_object('tries', coalesce((enrich->>'tries')::int, 0) + 1,
                                                                        'err', left(sqlerrm, 200)) where id = r.id;
      if sqlerrm = 'HTTP_429' then exit; end if;
    end;
  end loop;
  if not exists (select 1 from red_book_species where list_no is not null and not (enrich ? 'pts')
                 and coalesce((enrich->>'tries')::int, 0) < 3) then
    perform cron.unschedule('flora-redbook');
  end if;
  return done || ' видов обработано';
end $$;
revoke all on function public.rb_get_json(text), public.rb_tr(text, text, text), public.rb_wiki(text, text),
  public.rb_enrich_one(bigint), public.rb_enrich_batch(int) from public, anon, authenticated;

select cron.schedule('flora-redbook', '* * * * *', $c$set statement_timeout = 0; select public.rb_enrich_batch(4);$c$);

-- ---------- API: новые поля ----------
create or replace function public.api_rb_list(p_kind text default 'all', p_name text default 'all',
    p_q text default null, p_category text default null)
returns json language sql stable security definer set search_path = public, extensions as $$
  select coalesce(json_agg(r order by r.category nulls last, r.name_ru, r.latin), '[]'::json) from (
    select s.id, s.latin, s.name_ru, s.name_kk, s.rank, s.parent_latin, s.family, s.family_ru, s.family_kk, s.genus,
           s.category, s.taxon_id, s.photo is not null as has_photo, s.photo_url, s.author, s.updated_at, s.list_no,
           (select count(*) from red_book_points p where p.species_id = s.id) as n_points,
           (select count(*) from red_book_ranges g where g.species_id = s.id) as n_ranges
    from red_book_species s
    where (coalesce(p_q, '') = '' or s.latin ilike '%' || p_q || '%' or s.name_ru ilike '%' || p_q || '%'
           or s.name_kk ilike '%' || p_q || '%' or s.family ilike '%' || p_q || '%'
           or s.family_ru ilike '%' || p_q || '%' or s.family_kk ilike '%' || p_q || '%')
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
        select s.id, s.taxon_id, s.latin, s.name_ru, s.name_kk, s.rank, s.parent_latin, s.family, s.family_ru,
               s.family_kk, s.genus, s.category, s.gbif_key,
               s.description_ru, s.description_kk, s.habitat_ru, s.habitat_kk, s.protection_ru, s.protection_kk,
               s.wiki_ru_url, s.wiki_kk_url, s.photo is not null as has_photo, s.photo_url, s.photo_attr,
               s.author, s.created_at, s.updated_at,
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

-- обзорная карта: для не-редакторов точки сгруппированы по ~10 км (без дублей)
create or replace function public.api_rb_map(p_kind text default 'all', p_name text default 'all',
    p_auth text default null)
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
              where p_kind = 'all' or (p_kind = 'region' and p.region = p_name) or (p_kind = 'zone' and p.zone = p_name)) q),
    'ranges', (select coalesce(json_agg(json_build_object(
        'species_id', s.id, 'latin', s.latin, 'name_ru', s.name_ru, 'name_kk', s.name_kk, 'category', s.category,
        'geojson', ST_AsGeoJSON(ST_SimplifyPreserveTopology(g.geom, 0.005), 4)::json)), '[]'::json)
        from red_book_ranges g join red_book_species s on s.id = g.species_id
        where p_kind = 'all' or exists (select 1 from areas a where a.kind = p_kind and a.name = p_name
                                        and ST_Intersects(a.geom, g.geom))));
end $$;

grant execute on function public.api_rb_list(text, text, text, text), public.api_rb_get(bigint, text),
  public.api_rb_map(text, text, text) to anon, authenticated;

select count(*) as species, count(*) filter (where list_no is not null) as imported from public.red_book_species;

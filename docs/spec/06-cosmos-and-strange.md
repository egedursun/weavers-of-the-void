# 06 — Multi-world cosmos and the strange side

Scope: the multi-world cosmos (stars, worlds, world physics, world birth), interworld travel (routes, travel methods,
journeys), exploration ("horizon"), sky events and time effects, the "beyond" (souls, living planets, cosmic archive,
cosmic plague, void storms, mirror worlds, legendary quests, cosmic law, immortality), foreign/old gods, cosmic horror
(leak, sanity, Outer Beings, horror events, doom-as-a-calling), creatures (traits, mutation, chimeras, megafauna,
ecology, taming), civilization tiers (with hysteresis), colonies, federations, previous creation, rule-based
interactions (loans, barter, adoption, interworld treaties), and the pantheon engine (foreign gods, cosmic actions of sons
and creator, threats to the creator).

Old source files (read-only): `src/kozmos.js`, `src/seyahat.js`, `src/ufuk.js`, `src/gok.js`, `src/otesi.js`,
`src/yabanci.js`, `src/korku.js`, `src/yaratik.js`, `src/medeniyet.js`, `src/panteon.js`. Supporting definitions read
from `src/rules.js`, `src/db.js`, `src/world.js`, `public/harita-gen.js`, `src/epoch.js`, `src/oyuncu.js`, `src/sim.js`.

Everything in this document is rule-based (no LLM) **except** world birth (§2.4), which is one structured LLM call.

---

## 0. Conventions used in this document

| Notation | Meaning (old helper) |
|---|---|
| `d(n)` | Uniform integer in `1..n` (`rules.d`). "base + d(die)" means `base + d(die)`. |
| `chance(p)` | `random() < p`, `p` a fraction. Rule values marked "%" are divided by 100 first. |
| `clamp(x, lo, hi)` | Clamp. |
| `pick(list)` | Uniform random element (`list[floor(random()*len)]`), `null` if empty. |
| `shuffle(list)` | Fisher–Yates copy. |
| `note(text, entity_ids)` | **Engine note** (`not`): appended to the epoch's note list, pushed to the live feed, and at the end of the engine run written to the chronicle with type `world` (`dunya`) (repeated same-pattern notes are folded; see engine spec). Notes are the main "side effect → narrative" channel. |
| `chronicle(epoch, son_id, type, text, entity_ids)` | Direct chronicle insert (`addKronik`). Chronicle `type` values are given as `english (turkish)`. |
| `open_record({...})` | `derin.kayitAc`: inserts an entity (`varliklar`) with `source='world'` (`kaynak='dunya'`), `pending=1` (`bekliyor`, awaiting Fate's naming/description pass), unique name (`benzersizAd`, appends Roman numeral on collision), auto-written description, and an `inside` (`icinde`) bond to `location_id` if given. Its `world_id` is inherited by DB trigger (see §1.8). |
| `kill(id, epoch, note, {status='dead', close_bonds})` | `derin.oldur`: sets status (`olu` dead / `yok_edildi` destroyed), `death_epoch` (`olum_cag`), fate note; optionally closes bonds immediately. |
| `knows(entity_id, branch)` | `mudahale.bilir`: the entity has an active `knows` (`bilir`) bond to a technology entity whose branch tag is `dal:<branch>`. |
| `teach(entity_id, tech_id, epoch, note)` | `mudahale.ogret`: adds `knows` bond, raises tech spread. |
| `canon()` | Snapshot list of entities with `status='canon'` (`kanonlar()`), with parsed `stats` and `tags`. |
| `world_of(x)` | `x.world_id ?? 1` (null world means world #1 everywhere). |
| `distance(a, b)` | `derin.mesafe`: hops in the location tree (sum of steps from `a` and `b` up to their lowest common ancestor via `location_id`); 99 if no common ancestor. |
| `top_region(x)` | `olumluler.ustBolge`: the top-level region containing `x`. |
| `addBond(src_type, src_id, dst_type, dst_id, bond_type, description, epoch)` | `world.addBag`. Types: `v` entity, `o` son, `y` foreign god, `t` creator. |
| `bondExists(a, b, type)` | `world.bagVar`. |
| `rel_change(a, b, delta, reason, epoch)` | `derin.tIliskiDegistir`: relationship score between two communities. `rel(a,b)` = `derin.tIliski`. |
| `son_rel_change(a, b, delta)` / `son_rel(a, b)` | Relationship between two sons (`world.iliskiDegistir` / `iliski`). |
| `add_tag(e, ...tags)`, `remove_tag(e, tag or predicate)` | `derin.etiketEkle` / `etiketSil`. |
| `save_stats(e)`, `save_son(s)` | Persist. |
| `COMMUNITY` | `['people','settlement','faction','cult']` (`['halk','yerlesim','hizip','tarikat']`). |
| `prosperity_add(stats, n)` | `sim.refahEkle` (adds to `refah` with the economy module's soft-cap rules). |

Entity types referenced (`varliklar.tur`): region (`bolge`), place (`yer`), people (`halk`), settlement (`yerlesim`),
faction (`hizip`), cult (`tarikat`), mortal (`olumlu`), species/creature (`tur`), language (`dil`), sky body (`gok`),
resource (`kaynak`), technology/knowledge (`teknoloji`), item (`esya`), vehicle (`arac`), work/structure (`yapit`),
legend (`efsane`), prophecy (`kehanet`), soul (`ruh`), Outer Being (`dis`), event (`olay`).

Bond types referenced (`baglar.tur`): `descends_from (soyundan)`, `governs (yonetir)`, `speaks (konusur)`,
`worships (tapar)`, `trade (ticaret)`, `enemy (dusman)`, `ally (muttefik)`, `owns (sahip)`, `tamed (evcil)`,
`knows (bilir)`, `discovered (kesfetti)`, `inside (icinde)`, `related (ilgili)`, `tells_of (anlatir)`,
`prophesies (kehanet_eder)`, `caused (neden_oldu)`, `hunts (avlar)`, `produced (uretti)`, `member_of (uyesi)`,
`pays_tribute (harac_oder)`, `indebted_to (borclu)`, `migrated_to (gocetti)`, `source_of (kaynagi)`, `protects (korur)`,
`killed (oldurdu)`, `defeated (dovdu)`, `destroyed (yok_etti)`, `captive (esir)`, `spy (casus)`, `rival (hasim)`.

Tunable rules: every balance number is registered with `tanimla(AREA, {key: [default, label, min, max, group]})` and is
editable at runtime ("World rules" settings). The new app must keep this: **every number below is a tunable**, stored
per cosmos, read live (never copied into a constant at import time). Tables give `old key` → `new key`. Percent values
are "%" in the label.

Randomness: the old code uses `Math.random` everywhere and relies on a globally seeded `Math.random` during engine
probes; comments repeatedly say "roll the dice only after a candidate is found so the seeded dice order does not change".
The new engine should inject an explicit seeded RNG per epoch run and preserve the rule "find candidate first, roll
afterwards" where noted (it changes which random numbers are consumed, i.e. determinism under a seed).

---

## 1. Data model (cosmos tables)

### 1.1 Star (`yildizlar`)
| field | type | notes |
|---|---|---|
| id | int PK | |
| name (`ad`) | text | unique across the cosmos (names of stars, worlds, foreign gods, entities, sons share one namespace via `benzersizAd`) |
| type (`tur`) | text | see enum §1.9.2; default `yellow dwarf`. Runtime values also `star remnant (yıldız kalıntısı)` (after supernova), `reborn star (yeniden doğmuş yıldız)` (after rekindling) |
| brightness (`parlaklik`) | int 0–100 | default 60; black sun = 0 |
| x, y | real | position on the star map. New stars: angle `θ = random·2π`, radius `260 + N·140` where `N` = current star count; `x = cos θ · r`, `y = sin θ · r` |
| description, image_prompt | text | |
| created_epoch (`olusturma_cag`) | int | |

### 1.2 World (`dunyalar`)
| field | type | notes |
|---|---|---|
| id | int PK | world #1 = the original world (migration: every pre-cosmos record belongs to world #1) |
| name | text | unique |
| type (`tur`) | text | world type key §1.9.1, default `ordinary (olagan)` |
| star_id (`yildiz_id`) | fk star | moons inherit the planet's star (`aylariHizala`: every moon and moon-of-moon follows the root planet's star) |
| parent_id (`ana_id`) | fk world | set if the world is a moon |
| orbit (`yorunge`) | real | relative distance. Planet: `1 + k·0.7 + random·0.4` where `k` = existing planets of that star (parent_id null). Moon: `0.15 + k·0.08` where `k` = existing moons of that parent |
| gravity (`yercekimi`) | enum | `low (düşük)` / `normal (olağan)` / `high (yüksek)` |
| atmosphere (`atmosfer`) | enum | `none (yok)` / `thin (ince)` / `normal (olağan)` / `dense (yoğun)` / `toxic (zehirli)` |
| time_factor (`zaman_katsayi`) | real | years-per-epoch multiplier; default 1 |
| seed | text | map generator seed: `"<name>:<random base36>"` |
| terrain (`arazi`) | JSON `{sea, mountains, humidity}` | copied from world type defaults (§1.9.1) |
| discovery (`kesif`) | enum | `known (bilinen)` / `legend (efsane)` / `unknown (bilinmeyen)` / `forgotten (unutulmus)` |
| danger (`tehlike`) | int | default 20; born worlds `clamp(30 + d(40), 0, 100)` |
| leak (`sizinti`) | int 0–100 | cosmic horror leak level (§8) |
| cosmology, dialect (`lehce`), description, image_prompt | text | dialect = naming phonology of this world |
| creator_son_id (`yaratan_id`) | int | son who birthed it (null = creator god) |
| created_epoch | int | |
| protector_son_id (`koruyucu_ogul`) | int | son who declared it his holy world |
| protector_auto (`koruyucu_oto`) | int 0/1 | 1 if the declaration came from the automatic rule (§11.4) |
| mortal_agents (`olumlu_ajan`) | int? | per-world mortal agent count override (null = automatic share) — see agents spec |
| star_of_epoch (`cagin_yildizi`) | fk entity | this world's "star of the epoch" (a `sky` entity) chosen each epoch (§5.2) |
| mirror_twin (`ayna_ikiz`) | fk world | for mirror worlds: the twin world (§2.6, §6.6) |

### 1.3 Route (`rotalar`)
| field | type | notes |
|---|---|---|
| id | int PK | |
| a_world, b_world | int | undirected edge |
| method (`yontem`) | text | travel method key §1.9.4 |
| duration (`sure`) | int | epochs; from method at creation |
| danger (`tehlike`) | int | 0–100 |
| known (`bilinen`) | 0/1 | hidden routes (0) are invisible to travellers until revealed |
| controller_id (`kontrol_id`) | entity | community holding the route (gate owner, port, monopoly) |
| vehicle_id (`arac_id`) | entity | the gate/bridge vehicle that *is* the route |
| builder_son (`kuran_ogul`) | son | builder of a divine bridge |
| description | text | |
| created_epoch | int | |
| active (`aktif`) | 0/1 | |
| temp_until (`gecici_son`) | int? | a sealed route temporarily opened by an alignment re-seals at the start of this epoch |
| severed_until (`kapali_son`) | int? | a storm-severed route re-opens ("stitch closes") at the start of this epoch |
| closed_by_forgetting (`unutma_kapatti`) | int? | id of the forgotten world that closed this route (trigger §1.8) |

### 1.4 Journey (`yolculuklar`)
| field | notes |
|---|---|
| traveller_id (`yolcu_id`) | community or mortal |
| route_id, vehicle_id (`arac_id`), target_world (`hedef_dunya`) | |
| intent (`niyet`) | `colony (koloni)` / `trade (ticaret)` / `exploration (kesif)` / `conquest (fetih)` / `pilgrimage (hac)` |
| population (`nufus`) | travellers carried |
| remaining (`kalan`) | epochs to arrival |
| status (`durum`) | `en_route (yolda)` / `arrived (vardi)` / `lost (kayip)` / `recalled (geri)` |
| events (`olaylar`) | JSON list `[{epoch, event, loss?}]`, only last 8 kept |
| start_epoch, result_id (`sonuc_id`) | result = colony/outpost/discovered land |

### 1.5 Foreign god (`yabanci_tanrilar`)
| field | notes |
|---|---|
| name, title (`unvan`), domains (`alanlar`, "A/B") | |
| world_id | home world |
| power (`guc`) int 0–100 | default 50; new: `40 + d(40)` |
| faith (`inanc`) int | recomputed from worshippers |
| attitude (`tutum`) int −100…+100 | toward the creator's pantheon |
| status (`durum`) | `awake (uyanik)` / `asleep (uykuda)` / `defeated (yenik)` / `dead (olu)` |
| contacted (`temas`) 0/1 | first contact with the pantheon happened |
| description, image_prompt, created_epoch | |
| stats JSON | the nine son stats (§7) |
| personality (`kisilik`), powers (`gucler`), existence (`varolus`), depth (`derinlik`) | JSON, written by the deepening LLM pass (agents spec) |
| defeat_epoch (`yenilgi_cag`), death_epoch (`olum_cag`) | |
| wake_pressure (`uyanis_baski`) int, wake_baseline (`uyanis_ortalama`) real | sleeping-god wake mechanic (§11.3) |

### 1.6 Horizon intuition (`ufuk_sezgi`) — queue of "a mortal sensed an unknown world"
`id, entity_id (varlik_id), world_id, epoch, how (nasil), method (yontem), status (bekliyor pending | isleniyor processing | dogdu born | bosa wasted), result_world (sonuc_dunya)`.

### 1.7 Cosmos singleton columns (`dunya` row id=1) used here
`cosmic_resource (kozmik_kaynak)` JSON `{name, description, rule, side_effect}` (the cosmos's unique travel substance;
defined once at the first world birth that supplies it); `alignment_until (hizalanma_son)` int (slingshot routes open
until this epoch, exclusive); `doom (kiyamet)` int (doom clock); `creator_essence (tanri_oz)`; `epoch (cag)`;
`creator_name (tanri_adi)`.

Threads table (`iplikler`, Fate's open story threads) gets column `legendary (buyuk)` JSON
`{type, target, end_epoch, by, opened_epoch, prior?}` for legendary quests (§6.7).

### 1.8 DB triggers (must be preserved as domain rules)
- **World inheritance on insert**: a new entity's `world_id` = its own if given, else its location's world, else the
  creating son's active world, else the producing mortal's world, else the smallest world id, else 1.
- **World follows location**: when `location_id` changes to non-null and the new location has a world, the entity
  takes that world.
- **Forgetting a world**: when `discovery` becomes `forgotten`, every *currently active* route touching it gets
  `closed_by_forgetting = world.id` (then `forget_world` deactivates all its routes).
- **Remembering a world**: when `discovery` leaves `forgotten`, routes with `closed_by_forgetting` set and touching it
  are re-activated (and the mark cleared), unless the other end is still forgotten. Routes closed for other reasons
  stay closed.

### 1.9 Shared enums and data tables

#### 1.9.1 World types (`DUNYA_TURLERI`, `public/harita-gen.js`) — full
Each type has a display name, terrain params `{sea fraction, mountain factor, humidity offset}`, ten biomes (map
generator elevation/moisture bands, index order: deep→shallow water, shore, lowland…, peak) and a 10-colour palette.

| key | English name (Turkish) | sea | mtn | hum | biomes (translated, in order) |
|---|---|---|---|---|---|
| ordinary (`olagan`) | Ordinary world (Olağan dünya) | 0.52 | 1 | 0 | shallow sea, deep sea, beach, steppe, meadow, forest, barren hills, wooded hills, rocky mountains, snowy peaks |
| ocean (`okyanus`) | Ocean world | 0.84 | 0.8 | 0.15 | coral shallows, abyssal sea, white beach, salt cliff, kelp island, mangrove, rocky island, misty island, volcanic summit, icy peak |
| sand (`kum`) | Sand world | 0.06 | 0.9 | −0.35 | salt lake, dried sea, sand sea, dune, glass desert, oasis, red cliffs, canyon, wind pillars, sand peak |
| ice (`buz`) | Ice world | 0.45 | 1.1 | 0.05 | ice floe, black water, snow shore, ice field, tundra, needle forest, glacier, blue ice, ice mountain, storm peak |
| lava (`lav`) | Lava world | 0.38 | 1.4 | −0.25 | lava lake, magma ocean, obsidian shore, ash plain, basalt plain, sulphur marsh, coal hills, smoke valley, volcano, ember peak |
| crystal (`kristal`) | Crystal world | 0.4 | 1.3 | 0 | light lake, prism depth, glass shore, quartz plain, echo meadow, crystal forest, ringing hills, rainbow valley, echoing mountains, pure peak |
| living (`yasayan`) | Living planet | 0.42 | 0.9 | 0.25 | fluid lake, blood sea, membrane shore, skin plain, hair meadow, flesh forest, bone hills, vein valley, tooth ridges, eye peak |
| dead (`olu`) | Realm of the dead | 0.5 | 0.9 | 0.1 | water of oblivion, black river, ash shore, bone plain, pale meadow, mist valley, grave hills, echo forest, silent mountains, dead peak |
| dream (`ruya`) | Dream realm | 0.6 | 1.2 | 0.2 | dream water, sleep depth, cotton shore, floating island, violet meadow, whisper forest, slanted hills, inverted valley, cloud mountain, star peak |
| mirror (`ayna`) | Mirror world | 0.48 | 1 | 0 | inverted water, silver depth, glass shore, reflecting plain, inverted meadow, mirror forest, echo hills, broken valley, silver mountains, inverted peak |
| gas (`gaz`) | Gas giant | 0.9 | 0.6 | 0.3 | low cloud, pressure abyss, cloud shore, wind island, storm band, floating forest, cloud hill, lightning valley, vortex, eye storm |

Palettes (hex, same order): see old file; port verbatim (UI concern).

Mechanical meaning of type keys outside the map: `dead` → route method `river of the dead` requires a dead-realm
endpoint, souls descend there (§6.2); `living` → planetary consciousness (§6.3); `mirror` → mirror twin births (§6.6);
`dream`/`gas` → hidden route method selection (§3.7).

#### 1.9.2 Star types (`YILDIZ_TURLERI`) — full
`yellow dwarf (sarı cüce)`, `red giant (kızıl dev)`, `blue giant (mavi dev)`, `binary star (ikiz yıldız)`,
`white dwarf (beyaz cüce)`, `dead star (ölü yıldız)`, `black sun (kara güneş)`, `broken star (kırık yıldız)`,
`pulsar / pulse star (nabız yıldızı)`. Runtime-only: `star remnant (yıldız kalıntısı)`, `reborn star (yeniden doğmuş yıldız)`.
"Dead" group for quests/leak: `dead star`, `black sun`, `star remnant` (quests) — leak uses regex on the type text
`/dead|black|broken/` (`/ölü|kara|kırık/`), which does **not** include `star remnant`. Supernova/black-sun candidates:
`red giant`, `blue giant`, `broken star`, `pulsar`.

#### 1.9.3 Gravity / atmosphere effects → `world_physics` (§2.7).

#### 1.9.4 Travel methods (`SEYAHAT_YONTEMLERI`, `rules.js`) — full. `duration` and `danger` per method are tunables
(`SEYAHAT_YONTEMLERI.<key>.sure` range 1–20, `.tehlike` range 0–100, group "Cosmos & travel").

| key | name | duration (epochs) | danger | required knowledge branch | required vehicle | narrative cost |
|---|---|---|---|---|---|---|
| gate (`kapi`) | Ancient gate (Kadim kapı) | 1 | 25 | gate_lore (`kapi_bilimi`) | gate | Opening needs a sacrifice or a true name. |
| fold (`katlama`) | Space folding (Uzay katlama) | 1 | 30 | pathfinding (`yol_biliciligi`) | — | Consumes the cosmic travel resource; addictive. |
| sail (`yelken`) | Light sail (Işık yelkeni) | 3 | 20 | shipbuilding (`gemi_yapimi`) | ship | Slow but free; snaps if the star dies. |
| mount (`binek`) | Cosmic mount (Kozmik binek) | 2 | 35 | — | mount | Must tame a void creature. |
| dream (`ruya`) | Dream journey (Rüya yolculuğu) | 1 | 45 | magic (`buyu`) | — | Body stays, soul goes; may not return. |
| dead_river (`olu_nehri`) | River of the dead (Ölüler nehri) | 1 | 40 | — | — | For the living the price is memory loss. |
| bridge (`kopru`) | Divine bridge (Tanrısal köprü) | 1 | 10 | — | bridge | Collapses if its builder god sleeps or dies. |
| slingshot (`sapan`) | Slingshot orbit (Sapan yörüngesi) | 2 | 25 | sky_navigation (`gokyuzu_seyri`) | ship | Opens only in epochs when planets align. |
| swallowing (`yutulma`) | Swallowing (Yutulma) | 2 | 60 | — | — | You ride inside a cosmic creature; exit not guaranteed. |

Note: the `required vehicle` field is a display string; mechanically only `mount` (needs a tamed flying/megafauna
creature) and `ship` (needs an owned vehicle whose subtype contains "ship") are enforced in `can_use_route` (§3.4).
The `gate` and `bridge` vehicles are the route's own `vehicle_id`.

#### 1.9.5 Cosmic knowledge branches (subset of `BILGI_DALLARI`)
| key | name | effect text (display) |
|---|---|---|
| sky_navigation (`gokyuzu_seyri`) | Sky navigation | Can discover interworld routes; risk of getting lost in travel halved. (Mechanically: travel risk × `travel.navigation_risk_pct`.) |
| shipbuilding (`gemi_yapimi`) | Shipbuilding | Can build interworld ships (vehicles). |
| gate_lore (`kapi_bilimi`) | Gate lore | Can open and close ancient gates; gate routes finish in one epoch. |
| pathfinding (`yol_biliciligi`) | Pathfinding | Can fold space: with the cosmic resource routes take one epoch. |
| void_living (`bosluk_yasami`) | Life in the void | Can colonize worlds with thin/no atmosphere; less loss in travel. |
| immortality (`olumsuzluk`) | Pursuit of immortality | Its mortals reach for immortality; succeeders stop ageing but gods see them as a threat. |
| biomancy (`biyobuyu`) | Biomancy | Combines and alters living things: can weave chimeras, steer mutations. |
| forbidden (`yasak`) | Forbidden knowledge | Great power: war +15, magic +15, forces gates. Cost: knowers lose sanity every epoch, leak flows into their world; Fate watches. |
Other branches used here: `magic (buyu)`, `seafaring (denizcilik)`, `astronomy (gokbilim)`, `writing (yazi)`, `medicine (tip)`.

#### 1.9.6 Strange resource mechanics (`KAYNAK_MEKANIKLERI`), tag `mechanic:<key>` (`mekanik:<key>`) — implemented in the economy module
| key | text |
|---|---|
| decays (`bozunur`) | Rots while stored: abundance drops fast each epoch, never regenerates. |
| addiction (`bagimlilik`) | The using community weakens without it: owning it two epochs makes it addicted; losing it causes withdrawal. |
| conscious (`bilincli`) | Chooses who mines it and makes demands; if unmet, abandons its owner. |
| depletion_price (`tukenme_bedeli`) | When the last drop is drawn a curse falls on its land and doom approaches. |
| fixed (`sabit`) | Fixed amount in the cosmos: never regenerates; one's gain is another's loss. |
| sacred (`kutsal`) | Belongs to a god (`mechanic:sacred:<son_id>`): if non-worshippers mine it the god is angered. |

#### 1.9.7 Creature traits (`OZELLIKLER`), tag `trait:<key>` (`ozellik:<key>`) — full; `war` bonus is tunable (`OZELLIKLER.<k>.savas`, 0–100, group Creatures)
| key | name | war bonus | effect text |
|---|---|---|---|
| flying (`ucan`) | Flying | 8 | Migrates easily, raids reach far; +war in battle. |
| venomous (`zehirli`) | Venomous | 10 | Heavy wounds in hunt and battle; kills heroes easily. |
| soul_eater (`ruh_yiyen`) | Soul-eater | 4 | Eats souls in its region; gnaws sanity of those nearby. |
| light_emitting (`isik_sacan`) | Light-emitting | 0 | Lowers its region's danger, raises fertility; keeps Outer Beings away. |
| splitting (`bolunerek`) | Reproduces by splitting | 2 | Spreads if unchecked: migration and invasion chance ×2. |
| swarm_mind (`suru_zekasi`) | Swarm-minded | 6 | Weak alone, smart together: intelligence +15, hard to hunt. |
| stone_skinned (`tas_derili`) | Stone-skinned | 12 | Heroes' weapons barely bite. |
| time_rewinding (`zaman_geri`) | Time-rewinding | 0 | Returns once in the epoch it is killed. |
| shapeshifter (`sekil_degistiren`) | Shapeshifter | 3 | Blends into peoples; espionage and discord. |
| mind_reader (`akil_okuyan`) | Mind-reader | 8 | Knows heroes' moves in advance; lowers sanity nearby. |

Only some effect texts are implemented in this module (§9); others (raids, hunting, time rewind) live in the battle/hero
engine (see engine spec) — flag for the integrator.

#### 1.9.8 Civilization tiers (`BASAMAKLAR`), tag `tier:<index>` (`basamak:<n>`)
`0 tribe (kabile)`, `1 city-state (şehir devleti)`, `2 kingdom (krallık)`, `3 world empire (dünya imparatorluğu)`,
`4 interstellar power (yıldızlararası güç)`, `5 cosmic power (kozmik güç)`.

#### 1.9.9 Notable tags used by these modules (English (Turkish))
`original resource (özgün kaynak)`, `world:<id> (dunya:<id>)`, `cosmic resource (kozmik kaynak)`, `native (yerli)`,
`name-from-language (dilden-ad)`, `colony (koloni)`, `independent (bağımsız)`, `pioneer (öncü)`, `discovery (keşif)`,
`cosmic monopoly (kozmik tekel)`, `addicted:<resource_id> (bağımlı:<id>)`, `godless (tanrısız)`, `outer cult (dış tarikat)`,
`whisper source (fısıltı kaynağı)`, `nameless (adsız)`, `mutation (mutasyon)`, `mutated (mutasyon geçirdi)`, `mutant`,
`chimera (kimera)`, `escaped (kaçtı)`, `megafauna`, `invasive (istilacı)`, `golem`, `soul-bound (ruhlu)`,
`soul descended (ruhu indi)`, `soul harvester (ruh hasatçısı)`, `worships the planet (gezegene tapar)`,
`planet closed (gezegen kapattı)`, `cosmic archive (kozmik arşiv)`, `wonder (harika)`, `burned (yandı)`,
`lost (kayıp)` (lost knowledge), `cosmic plague (kozmik salgın)`, `mirror (ayna)`, `mirror born (aynası doğdu)`,
`oathbreaker (yeminbozan)`, `cursed (lanetli)`, `exile (sürgün)`, `immortal (ölümsüz)`, `previous creation (önceki yaratılış)`,
`ruin (harabe)`, `federation (federasyon)`, `empire (imparatorluk)`, `omen (alamet)`, `time echo (zaman yankısı)`,
`thread:<id> (iplik:<id>)`, `two-timed (iki zamanlı)`, `void (boşluk)`, `bargain:<son_id> (pazarlik:<id>)`,
`fold:<count> (katlama:<n>)`, `in search of a god (tanrı arayışı)`.

LANGUAGE-SPECIFIC: tags are Turkish strings matched with SQL `LIKE '%…%'`. The new app should use a normalized
`entity_tags(entity_id, tag, arg)` table with English keys.

---

## 1.10 Engine order (per epoch, `sim.js`)

The rule engine runs once per epoch (`cag`). Relevant part of the order (other steps belong to other specs):

1. … diplomacy, wars (`seferler`) …
2. `travel_engine` (§3.8) — seyahatMotoru
3. `exploration_engine` (§4.6) — kesifMotoru
4. `resource_mechanics`, `cosmic_economy` (economy spec)
5. `horror_engine` (§8.4) — korkuMotoru
6. `creature_engine` (§9.3) — yaratikMotoru
7. `pantheon_engine` (§11.6) — panteonMotoru
8. `death_engine` (other spec)
9. `civilization_engine` (§10.3) — medeniyetMotoru
10. `sky_engine` (§5.4) — gokMotoru
11. `beyond_engine` (§6.10) — otesiMotoru
12. … monster raids, heroes, population growth (uses `world_physics`), ageing (uses `world_physics.time`) …
13. Epoch transition: doom clock; if doom ≥ threshold → `doom_calling` (§8.6) else apocalypse on the leakiest world.
    `choose_epoch_stars()` (§5.2) runs at epoch transition.
14. After the epoch (async, LLM): `process_intuitions()` (§4.5) births sensed worlds (skipped in no-LLM mode).

On server start: `recover_intuitions()` (processing → pending) and `pair_mirrors()` (§2.6).

---

## 2. Cosmos and worlds (`src/kozmos.js`)

### 2.1 Purpose
Stars and worlds; birth of a new world (one structured LLM call that produces name, type, physics, cosmology, naming
dialect, first regions, sky body, original resource, optional cosmic travel resource, native language with lexicon,
optional old god and natives); world physics consumed by the population/war engine; mirror-twin pairing; cosmos
overview payload for the UI.

### 2.2 Cosmos overview (`kozmos()`) — read model for the Cosmos page
Returns:
- `stars`: all stars ordered by id.
- `worlds`: all worlds, each with parsed `terrain`, `type_name`, and `counts` from canon entities of that world:
  `regions`, `peoples`, `settlements`, `living` (people+settlement+faction+cult+mortal+species), `population` (sum of
  `stats.population` for people and settlements), `outer` (canon Outer Beings in that world — so the UI does not let the
  player waste essence on cleansing when nothing is inside); and `sons`: non-dead sons whose `active_world` is this world.
- `targets` split into `regions` (regions/places, any world, ordered by name) and `communities`
  (people/settlement/faction/cult/mortal with population) — selectable targets for "open deposit" and "send expedition".
- `quest_targets` (`sefer_hedef`) — availability flags for legendary quests (§6.7), so the UI can disable impossible ones:
  - `dead_star`: a star of type dead star / black sun / star remnant exists;
  - `sealed_gate`: a route exists with `active=0`, `severed_until IS NULL`, `temp_until IS NULL`, neither end forgotten;
  - `archive`: a canon entity tagged `cosmic archive` exists in a non-forgotten world;
  - `expel_outer`: a canon Outer Being exists.
- `horizon` = `exploration_summary()` (§4.8), `foreign_gods` (with cover image url), `routes` (all, with state §3.2),
  `sky_calendar` (§3.3), `journeys` (§3.9), `types` (key → name, palette).

### 2.3 Tunables `DUNYA_DOGUS` (world birth) — group "Cosmos & travel"
Rolled stats use `base + d(die)` via helper `roll(k) = DK[k] + d(DK[k+'_zar'])`.

| old key | new key | default | min | max | label |
|---|---|---|---|---|---|
| bolge_en_az | regions_min | 2 | 1 | 50 | Minimum regions in a new world |
| bolge_en_cok | regions_max | 4 | 1 | 50 | Maximum regions in a new world |
| kelime_en_az | words_min | 8 | 0 | 200 | Minimum words in the new world's language |
| kelime_en_cok | words_max | 14 | 1 | 200 | Maximum words in the new world's language |
| mekanik_en_cok | resource_mechanics_max | 2 | 0 | 10 | Max rules (mechanics) of the original resource |
| yerli_en_cok | natives_max | 2 | 0 | 20 | Max natives (species or people) in a new world |
| yasak_ad | forbidden_local_names | 60 | 0 | 2000 | Region/people/language/place/sky names not to repeat in the prompt (newest first) |
| yasak_kozmik_ad | forbidden_cosmic_names | 200 | 0 | 2000 | World/star/foreign-god names not to repeat in the prompt (newest first) |
| ses_kumesi | phoneme_set_min | 8 | 1 | 100 | Min distinct letters for the language's letters to count as a phoneme set |
| yildiz_parlaklik / _zar | star_brightness_base / _die | 40 / 55 | 0/1 | 100 | New star brightness |
| tehlike / _zar | danger_base / _die | 30 / 40 | 0/1 | 100 | New world danger |
| bolge_guc | region_power_level | 6 | 1 | 12 | Power level of birth regions |
| bolge_genislik / _zar | region_size_base / _die | 50 / 30 | 0/1 | 100 | Birth region size (`genislik`) |
| bolge_tehlike | region_danger_default | 30 | 0 | 100 | Birth region danger if model omits |
| bolge_bereket | region_fertility_default | 50 | 0 | 100 | Birth region fertility if model omits |
| bolge_buyu | region_magic_default | 30 | 0 | 100 | Birth region magic if model omits |
| gok_guc | sky_power_level | 5 | 1 | 12 | Birth sky body power level |
| gok_parlaklik / _zar | sky_brightness_base / _die | 40 / 50 | 0/1 | 100 | Birth sky body brightness |
| gok_etki / _zar | sky_influence_base / _die | 30 / 50 | 0/1 | 100 | Birth sky body influence |
| kaynak_guc | resource_power_level | 6 | 1 | 12 | Original resource power level |
| kaynak_bolluk / _zar | resource_abundance_base / _die | 50 / 40 | 0/1 | 100 | Original resource abundance |
| kaynak_deger / _zar | resource_value_base / _die | 60 / 40 | 0/1 | 100 | Original resource value |
| kaynak_kudret / _zar | resource_might_base / _die | 40 / 50 | 0/1 | 100 | Original resource might |
| kozmik_guc | cosmic_deposit_power_level | 8 | 1 | 12 | Cosmic resource deposit power level |
| kozmik_bolluk / _zar | cosmic_abundance_base / _die | 70 / 30 | 0/1 | 100 | Cosmic deposit abundance |
| kozmik_deger | cosmic_value | 95 | 0 | 100 | Cosmic deposit value |
| kozmik_kudret / _zar | cosmic_might_base / _die | 80 / 20 | 0/1 | 100 | Cosmic deposit might |
| dil_guc | language_power_level | 4 | 1 | 12 | Native language power level |
| dil_yayginlik | language_spread | 40 | 0 | 100 | Native language spread |
| dil_karmasiklik / _zar | language_complexity_base / _die | 40 / 30 | 0/1 | 100 | Native language complexity |
| dil_kutsallik / _zar | language_sacredness_base / _die | 20 / 40 | 0/1 | 100 | Native language sacredness |
| yerli_guc | natives_power_level | 4 | 1 | 12 | Natives power level |
| halk_nufus / _zar | native_people_population_base / _die | 2000 / 8000 | 1 | 10,000,000 | Native people population |
| halk_savascilik / _zar | native_people_warlike_base / _die | 30 / 50 | 0/1 | 100 | Native people warlikeness |
| halk_buyu_zar | native_people_magic_die | 70 | 1 | 100 | Native people magic = d(die) |
| halk_zanaat / _zar | native_people_craft_base / _die | 20 / 50 | 0/1 | 100 | Native people craft |
| halk_inanc / _zar | native_people_faith_base / _die | 20 / 40 | 0/1 | 100 | Native people piety |
| tur_can / _zar | native_species_hp_base / _die | 100 / 400 | 1 | 100000 | Native species HP |
| tur_guc / _zar | native_species_strength_base / _die | 30 / 60 | 0/1 | 100 | Native species strength |
| tur_ceviklik / _zar | native_species_agility_base / _die | 20 / 60 | 0/1 | 100 | Native species agility |
| tur_zeka_zar | native_species_intelligence_die | 80 | 1 | 100 | Native species intelligence = d(die) |
| tur_tehlike / _zar | native_species_danger_base / _die | 20 / 70 | 0/1 | 100 | Native species danger |

(For `_base/_die` pairs the min/max are `0..100` for the base and `1..100` for the die unless stated.)

Note: the `minItems/maxItems` of the LLM schema read these rules live (getters).

### 2.4 World birth (`world_birth`, old `dunyaDogur`) — the only LLM call in this spec

**Triggers / callers**
- Creator action "Create world" (`epoch.dunyaYarat`): costs `DENGE.dunya` (default 120 essence), refunded if the call
  throws; guarded by a lock `world`. Player may pass `type`, `inspiration` (truncated to `TANRI.ilham_uzunluk`), and
  placement `{star_id | parent_world_id | new_star}`.
- Son tool `dunya_dogur` (legendary+ rarity gate `NADIRLIK_KAPI.dunya_dogur` default legendary, cost
  `DENGE.dunya_dogur` default 70) — see sons/tools spec. `creator_son` is passed.
- Horizon intuitions (§4.5) at epoch end, with inspiration "`<name>` mortals found the way to a world nobody knew while
  searching `<how>`."
- Mortal tool `rota_kesfet` success "intuition" branch (mortal agents spec) calls `sezgiyiDogur` → this.

**Inputs**: `type` (world type key or null → model chooses; invalid key throws "Invalid world type."), `inspiration`
text, `creator_son` (son object or null = creator god), `placement` (see above), `publish` (live event callback).

**Steps**
1. Publish live `fate_step` "`<creator or god name>` is birthing a new world (`<type name>`)…".
2. Model = model configured for the job `fate` (`modelFor('kader')`); reasoning effort `EFFORT.kader` (low) unless the
   model is the smallest (haiku, which takes no effort param); timeout 300 s; label "World birth"; retries publish
   progress via `onYeniden`.
3. Structured call with the system prompt, user prompt and JSON schema below.
4. `process_world_birth(result, …)` (§2.5) in one DB transaction → new world id.
5. Outside the transaction (errors swallowed so the caller does not refund the cost after the world exists):
   invalidate map cache; publish `{kind:'world_born', world_id, name}`.
6. Return the world row.

**System prompt (translated)**
> You are the architect of the `{cosmos_name}` cosmos. You write in English (image prompts in English). Every world
> runs on a strange, concrete logic of its own; no clichés. The new world connects to the rest of the cosmos but feels
> completely different.

(Old: "Türkçe yazarsın (görsel promptlar İngilizce)" — i.e. "You write Turkish (image prompts English)". New app: English.)

**User prompt template (translated, structure preserved)**
```
{world_header(cosmos)}                       ← shared header builder (world spec): cosmos name, epoch, creator, cosmology, tone, naming rule, doom warning, climate, star of the epoch, laws

KNOWN WORLDS OF THE COSMOS:
{cosmos_lines() or "- world#1 {cosmos_name}"}

STARS AND THEIR PLANETS:
{star_lines() or "none"}

FOREIGN AND OLD GODS OF THE COSMOS (old_god cannot be one of them; do not repeat their names):
{foreign_god_lines() or "none"}
{placement_instruction}

{creator_instruction}
{type_instruction}[\nINSPIRATION: {inspiration}]

RULES: This world is another world; another language, another sky, another logic. First build a new dialect (it must
not share the main world's sounds), then derive ALL names with that dialect. Do NOT USE these names or their roots:
{forbidden_names()}.
{cosmic_resource_instruction}
```
Variables:
- `cosmos_lines()` (`world.kozmosSatirlari`): one line per world: `- world#{id} {name} ({type name}[, {star name} star];
  {R} regions, {P} peoples, {S} settlements; gravity {g}, atmosphere {a}[, time ×{f} if ≠1][, {discovery} if ≠ known])`.
  Empty if only one world.
- `star_lines()`: `- star_id {id}: {name} ({type})[ — {description}] — planets: world#{id} {name}, … | none` (only
  planets, i.e. worlds with that star and no parent).
- `foreign_god_lines()`: `- {name}[, {title}] (world#{world_id}[; {domains}])`.
- `placement_instruction`:
  - player gave star: "This world will orbit star_id {id}; its description must not contradict that star's light."
  - player gave parent world: "This world will be the moon of world#{id}."
  - player asked new star: "A new sun is requested for this world: placement new_star; fill the star field (name, type, description)."
  - otherwise (PLACEMENT_GUIDE): "Choose the placement by looking at the stars above: if the light this world wants
    (yellow, red, blue, black sun, dead star…) exists at a star in the list, choose existing_star and give that
    star_id; most worlds are born this way. Choose a new sun only if no star of that type is in the list, and fill the
    star field. The world's description must not contradict the star it orbits."
- `creator_instruction`: son → "This world is being birthed by son {name} ({title}; {domain1}/{domain2}); the world
  should reflect his domains and temperament." / god → "The creator god {creator_name} is creating this world with
  his own hand."
- `type_instruction`: "World type: {type name} ({key})." or "Choose the world type that will enrich the cosmos most."
- `forbidden_names()`: first word of each name from (a) worlds ∪ stars ∪ foreign gods ordered by created_epoch desc,
  id desc, limit `forbidden_cosmic_names`; then (b) canon entities of type region/people/language/place/sky ordered by
  id desc, limit `forbidden_local_names`; de-duplicated, comma-joined.
- `cosmic_resource_instruction`: if cosmos already has one: "The cosmos already has a travel resource ({name}); leave
  the cosmic_resource field empty." else "The cosmos has no travel resource yet: fill the cosmic_resource field; this
  substance will determine the politics of the whole cosmos."

**Output JSON schema (translated descriptions; required fields marked *)**
| field | type | description |
|---|---|---|
| placement* (`yerlesim`) | enum `existing_star`/`new_star`/`moon` (`mevcut_yildiz`/`yeni_yildiz`/`uydu`) | existing_star: a new planet orbiting a listed star (most worlds; choose this if the light the world wants is in the list); new_star: only if a sun of a type NOT in the list is needed — a distant system with its own sun (star field becomes mandatory); moon: a moon of an existing world |
| star_id | int | if existing_star, the id of the star it orbits |
| parent_world_id (`ana_dunya_id`) | int | if moon, the world it orbits |
| star (`yildiz`) | object `{name, type ∈ star types, description}` | MANDATORY if you chose new_star: the new system's sun; its name cannot be any listed star's or world's name. If left empty no new star is born and the world settles at an existing star. |
| type* (`tur`) | enum world type keys | |
| dialect* (`lehce`) | string | BUILD THIS FIRST: this world's own naming dialect — vowels, consonants, syllable patterns and suffixes OTHER than the main world's. All names below (world, regions, sky, resource, natives) are derived with this dialect. |
| name* (`ad`) | string | The world's name; in the new dialect, repeating no existing name |
| description* (`aciklama`) | string | 3–5 sentences: what makes this world strange and concrete |
| cosmology* (`kozmoloji`) | string | This world's OWN understanding of creation and death, 2–4 sentences; do not repeat the main cosmology, extend it with this world's strangeness |
| gravity* (`yercekimi`) | enum low/normal/high | |
| atmosphere* (`atmosfer`) | enum none/thin/normal/dense/toxic | |
| time_factor* (`zaman_katsayi`) | number | Multiplier of years passing in one epoch on this world (`{time_min/100}`–`{time_max/100}`). In the dream realm time stretches, in the realm of the dead it almost stops. |
| day* (`gun`) | string | Its day, night and seasons in one sentence |
| regions* (`bolgeler`) | array [regions_min..regions_max] of `{name*, subtype* ("continent, inland sea, desert belt, archipelago, …"), description* (2–4 sentences), danger* 0–100, fertility* 0–100, magic* 0–100, image_prompt* (English photoreal prompt + IMAGE_RULES)}` | |
| sky* (`gok`) | object `{name*, subtype*, description*, image_prompt*}` | The most prominent body in this world's sky (moon, ring, wound, second sun…) |
| original_resource* (`ozgun_kaynak`) | object `{name*, subtype*, description*, rule*, mechanics* (array ≤ resource_mechanics_max of mechanic keys §1.9.6; description lists "key: text; …"), region_index* (int 0..regions_max−1), image_prompt*}` | A strange resource found only on this world; it should have a strange rule (rots, addicts, can only be gathered in one season…) |
| cosmic_resource (`kozmik_kaynak`) | object `{name, description, rule ("How it is extracted, how it is used, what it makes possible"), side_effect ("The price of long use: mutation, memory loss, eye colour…"), region_index, image_prompt}` | ONLY fill if the cosmos has no travel resource yet: the single cosmos-specific substance making interworld travel (space folding) possible; long use causes addiction and a side effect. It gets a deposit on this world. |
| language* (`dil`) | object `{name*, subtype*, description*, words* (array [words_min..words_max] of `{word*, meaning*, kind* ∈ noun/verb/adjective/suffix/title/place name/proper name/interjection/number, origin*}`)}` | This world's native language, matching the dialect exactly |
| old_god (`eski_tanri`) | object `{name, title, domains ("two domains separated by /"), description, attitude (int −100…100: toward the newcoming pantheon, −100 hostile, +100 friendly), image_prompt}` | OPTIONAL: an old or foreign god that existed on this world before the pantheon, with its own worshippers (not on every world; only if the world's logic requires it). It CANNOT be one of the cosmos's existing foreign gods: both name and identity must be new. |
| natives* (`yerliler`) | array ≤ natives_max of `{kind* ∈ people/species, name*, subtype*, description*, region_index*, image_prompt*}` | Optional: living things on this world before the gods (a species or a people) |
| image_prompt* | string | English photoreal prompt: the whole world seen from orbit, with its star and sky. + IMAGE_RULES |

`IMAGE_RULES` (`GORSEL_YAZIM`, already English, verbatim): "Image prompt rules: describe only what IS visible; never
use negations (no, without, not, lacking, absent) because the image model ignores them and draws the thing anyway;
describe the replacement instead (e.g. "a smooth blank head with a single thin dark slit" rather than "no face").
Whatever the subject (person, creature, place, object, event or god), name at least two details unique to this world
so the image never falls back to a generic real-world look."

### 2.5 Processing the birth output (`process_world_birth`, old `dunyaDogusuIsle`) — pure, testable with recorded outputs
Inputs: `r` (model output; non-object → `{}`), `type` (forced type or null), `creator_son`, `placement`, `cosmos`, `stars`.

1. Validate: empty `r.name` → throw "World birth output has no name." (no DB change).
2. `type_key = forced type || (r.type valid ? r.type : 'ordinary')`. `source = creator_son ? 'cosmos' : 'god'` (son-born
   content is *not* sent to Fate as a son "creation"; the creator id is still recorded).
3. `phonemes = phoneme_set(r)`: set of lowercase letters (Unicode letters only) of all lexicon words; null if fewer than
   `phoneme_set_min` distinct letters. `fits(name)` = phonemes null OR every letter of the **first word** of name is in
   the set. (LANGUAGE-SPECIFIC note: old code lowercases with Turkish locale; use plain Unicode lowercasing.)
4. Transaction:
   1. **Placement** (first match wins):
      1. player's `parent_world_id` exists → moon of it;
      2. player's `star_id` is a known star → that star;
      3. player asked `new_star` → new star below;
      4. `r.placement == moon` and `r.parent_world_id` exists → moon;
      5. else if NOT `needs_new_star(r)` and stars exist → star = `r.star_id` if valid, else the star whose type matches
         the narrative (`narrative_star_type(r)`), else a random star.
      - `narrative_star_type(r)`: lowercase concat of description + day + cosmology; find the longest star type string
        contained in it (so "dead star" wins over shorter matches).
      - `needs_new_star(r)` = `r.placement == new_star` AND (`r.star.name` given OR (a narrative star type exists AND no
        listed star has that type)).
      - If moon: star = parent's star.
   2. `name = unique_name(r.name)`.
   3. **New star** if no star and no parent: `star_def = r.star.name ? r.star : {name: "<world> Sun" (`<ad> Güneşi`),
      type: narrative type or 'yellow dwarf'}`; type must be a valid star type else 'yellow dwarf'; star name unique;
      if (normalized) equal to the world name → `unique("<world> Sun")`. Brightness: black sun → 0 else
      `star_brightness_base + d(die)`. Position per §1.1. created_epoch = current.
   4. Insert world: orbit per §1.2, gravity/atmosphere validated (fallback normal), `time_factor` =
      `clamp(Number(r.time_factor) || 1, DUNYA_FIZIK.time_min/100, time_max/100)`, seed, terrain = type defaults,
      `discovery='known'`, `danger=clamp(danger_base + d(danger_die), 0, 100)`, cosmology, dialect,
      `description = (r.description + ' ' + r.day).trim()`, image prompt, creator_son_id, created_epoch.
   5. If type is `mirror` → `assign_mirror_twin(world)` (§2.6).
   6. Helper `add(kind, v, stats, location_id, power)`: inserts a canon entity (unique name; fallback name
      `"<r.name> <kind>"`; description passed through the Turkish suffix fixer — LANGUAGE-SPECIFIC: drop), `source`,
      `world_id`, `creator_id = creator_son?.id`; if `location_id` → `inside` bond; if `!fits(v.name)` → queue for
      renaming.
   7. **Regions**: up to `regions_max` items with a name → `region` entities, stats `{size: roll(region_size), danger:
      clamp(model or default), fertility: …, magic: …}`, power `region_power_level`. **Zero regions → throw "A world
      cannot be born without regions." (transaction rolls back)**.
   8. **Sky body** (if `r.sky.name`) → `sky` entity, stats `{brightness: roll, influence: roll}`, power `sky_power_level`.
   9. **Original resource** (if name) → `resource` in region `regions[clamp(region_index,0,n−1)]`, description
      `"<description> Rule: <rule>"`, stats `{abundance, value, might}` rolled, power `resource_power_level`; tags
      `['original resource', 'world:<id>', ...mechanics]` where mechanics = valid keys, max `resource_mechanics_max`,
      `sacred` becomes `mechanic:sacred:<creator_son_id or 0>`.
   10. **Cosmic resource** — only if cosmos has none AND `r.cosmic_resource.name` AND that name ≠ original resource name
       AND no canon entity tagged `cosmic resource` exists: write cosmos `cosmic_resource = {name, description, rule,
       side_effect}`; add deposit resource `"<name> Deposit"` (`Yatağı`), subtype `cosmic travel resource`,
       description `"<description> <rule> Price: <side_effect>"`, stats `{abundance: roll(cosmic_abundance), value:
       cosmic_value, might: roll(cosmic_might)}`, power `cosmic_deposit_power_level`, in region index; tags
       `['cosmic resource','mechanic:addiction','mechanic:fixed']`.
   11. **Native language** (if `r.language.name`): `language` entity (subtype default "native language"), description
       `"<description> Dialect: <dialect>"`, stats `{spread, complexity: roll, sacredness: roll}`, power
       `language_power_level`; add lexicon words (≤ words_max) authored by son (`o`) or god (`t`). Then every queued
       name that did not fit the phoneme set is regenerated with the language's name generator
       (`dilmotoru.adUret(language_id, "dogus:<world>:<entity>", region→'place' else 'general')`) and tagged
       `name-from-language`.
   12. **Natives** (≤ natives_max with name): region by index; people → stats `{population, warlike, magic: d(die),
       craft, piety}`; species → `{hp, strength, agility, intelligence: d(die), danger}`; power `natives_power_level`;
       tags set to `['native']`; people `speaks` the native language ("native tongue"); a people in the same region
       as the original resource `owns` it ("native resource").
   13. **Old god** (if name) → `add_foreign_god({...old_god, world_id}, epoch)` (§11.2).
   14. If creator son: set son's `active_world` = new world; bond son `protects` first region ("the world he birthed").
   15. `connect_world(world, epoch, {target: creator_son.active_world (the son's previous world)})` (§3.7); errors swallowed.
   16. Chronicle `world_birth (dunya_dogusu)`: "`<son or creator>` birthed a new world: `<name>` (`<type name>`).
       `<description>`", entity ids = regions + sky + resource.
5. Return world id.

### 2.6 Mirror twin (`assign_mirror_twin`, `pair_mirrors`)
- `assign_mirror_twin(world)`: if world already has a twin → return it. Twin = among non-forgotten worlds other than
  itself: order by (same star first), then most mortals (`entity type mortal` count), then id; pick first. Store
  `mirror_twin`. Returns null if none.
- `pair_mirrors()` (server start): for every world of type `mirror` with no twin → assign; idempotent. The player can
  change the twin from world editing.
- Mechanic: §6.6.

### 2.7 World physics (`world_physics(world_id)`, old `dunyaFizigi`)
Cached per epoch (map of all worlds, rebuilt when `epoch` changes). Missing world → `{time:1, capacity:1, war:0,
type:'ordinary'}`. Otherwise:
- `time` = `time_factor || 1` → population engine multiplies ageing (`age += years × time`), growth rate by `sqrt(time)`;
  death-year math divides by it.
- `capacity` = atmosphere → `DUNYA_FIZIK.capacity_<atm>/100` (default normal) → multiplies carrying capacity.
- `war` = gravity → `DUNYA_FIZIK.war_<grav>` (default normal) → added to military power of people/settlement/faction.
- `type`.

Tunables `DUNYA_FIZIK` (defined in `world.js`, group "Cosmos & travel"):
| old key | new key | default | min | max | label |
|---|---|---|---|---|---|
| zaman_en_az | time_min_pct | 25 | 1 | 10000 | Min time factor Fate may give a born world (%; 100 = normal; does not limit the creator's manual value) |
| zaman_en_cok | time_max_pct | 400 | 1 | 10000 | Max time factor Fate may give a born world (%) |
| kapasite_yok | capacity_none_pct | 25 | 0 | 1000 | Life capacity of an airless world (%) |
| kapasite_ince | capacity_thin_pct | 60 | 0 | 1000 | Life capacity, thin atmosphere (%) |
| kapasite_olagan | capacity_normal_pct | 100 | 0 | 1000 | Life capacity, normal atmosphere (%) |
| kapasite_yogun | capacity_dense_pct | 115 | 0 | 1000 | Life capacity, dense atmosphere (%) |
| kapasite_zehirli | capacity_toxic_pct | 40 | 0 | 1000 | Life capacity, toxic atmosphere (%) |
| savas_dusuk | war_low_gravity | −4 | −100 | 100 | Warlikeness effect of low gravity |
| savas_olagan | war_normal_gravity | 0 | −100 | 100 | … normal gravity |
| savas_yuksek | war_high_gravity | 6 | −100 | 100 | … high gravity |

### 2.8 Cross-module calls
`world.getWorld, addKronik, addBag, benzersizAd, aramaNorm (normalize), dunyaBasligi (header), modelFor, kozmosSatirlari,
sozlukEkle (lexicon insert), kapak (cover url)`; `llm.structured`; `harita.haritaGecersiz`; `dilmotoru.adUret`;
`seyahat.dunyayiBagla, rotalar, yolculukListesi, gokTakvimi`; `panteon.yabanciTanriEkle, yabanciTanrilar`;
`ufuk.kesifOzeti`. Called by: `epoch.dunyaYarat`, `tools` (son `dunya_dogur`, `yildizSatirlari` for the son prompt),
`olumluler` (mortal `rota_kesfet`), `ufuk.sezgileriIsle`, `sim` (`dunyaFizigi`), server (`kozmos()`, `aynalariEsle`).

---

## 3. Interworld travel (`src/seyahat.js`)

### 3.1 Purpose
Routes between worlds (method, duration, danger, controller, state), the alignment calendar for slingshot routes,
hidden routes and their revelation, route-knowledge learning, spontaneous expeditions, journeys that last several
epochs with road events, arrival (colony, conquest outpost, trade, exploration, pilgrimage) with first contact, bridge
collapse, the creator's recall of expeditions and revelation of hidden routes.

### 3.2 Route state (`route_state(route, epoch, calendar, forgotten_set)`, old `rotaDurumu`)
Returns `{open, state, reason, opens_epoch, closes_epoch, aligned (slingshot only, else null), hidden: !known}`.
Evaluated in this priority order:
1. Either end world forgotten → `state='forgotten'`, closed, reason "The world at the end of the route was forgotten; the route is in the mist."
2. `!active && severed_until != null` → `state='severed'`, `opens_epoch = severed_until`, reason "A storm severed the route; its stitch closes at the start of Epoch N."
3. `!active && method == bridge && builder_son` → `state='collapsed'`, reason "The divine bridge collapsed when its builder fell."
4. `!active` → `state='sealed'`, reason "The route is sealed; only an alignment (temporarily), the creator's hand, or a legendary quest breaks the seal."
5. slingshot and calendar not aligned → `state='misaligned'`, `opens_epoch = calendar.opens_epoch`, reason "Slingshot orbit closed: planets align at the start of Epoch N."
6. Otherwise open: `state = temp_until != null ? 'temporary' : 'open'`, `closes_epoch = min(temp_until, slingshot ? calendar.closes_epoch : none)`,
   reason (temporary) "The alignment lifted the seal temporarily; it re-seals at the start of Epoch N."

`route_is_open(route)` = state.open. Used by engine, tools and UI.

### 3.3 Alignment calendar (`sky_calendar(epoch)`, old `gokTakvimi`; `alignment(epoch)`, old `hizalanma`)
- `P = max(1, travel.alignment_period)`; cycle aligned ⇔ `epoch % P == 0`.
- `alignment_until` (cosmos column, set by planetary alignment events §5.3) keeps slingshots open while `epoch < alignment_until`.
- `aligned = cycle_aligned OR (alignment_until != null AND epoch < alignment_until)`.
- `next_cycle = epoch + (P − epoch % P)`.
- If aligned and `P > 1`: `closes = max(epoch+1, alignment-driven ? alignment_until : epoch+1)`; if `closes` is itself a
  cycle-aligned epoch, `closes += 1`.
- If not aligned: `opens = next_cycle` (or current epoch if an alignment is in force).
- Text (display): aligned → "Planets aligned: slingshot orbits open[ (planetary alignment, until the start of Epoch N)][; closes at the start of Epoch K]. The cycle aligns every P epochs." / not → "Slingshot orbits closed; they open at the start of Epoch N (in M epochs). The cycle aligns every P epochs."
- Returns `{epoch, period, aligned, slingshot_open, cycle_aligned, alignment_until, next_cycle, opens_epoch, closes_epoch, text}`.

### 3.4 Creating and using routes
**`open_route({a, b, method, controller_id, vehicle_id, builder_son, known=1, description, epoch})`** (`rotaAc`)
- Invalid method → throw. `a == b` → throw "A route must connect two different worlds.". Either end forgotten → throw
  "A route cannot be opened to a forgotten world.".
- If an *active* route with the same method already connects the pair (either direction) → set `known=1`, return its id.
- Else insert: `duration = method.duration`, `danger = clamp(method.danger + d(route_danger_die) − route_danger_shift,
  route_danger_min, route_danger_max)`, given fields, `created_epoch`, active=1.

**`routes(world_id=null, {all=false})`** (`rotalar`): default = active AND known routes, filtered to state.open;
`all` = every route with state attached (hidden, severed, temporary, sealed, collapsed, forgotten, misaligned).
Adds `method_name, a_name, b_name, controller_name`. `route_lines(world_id)` for agent prompts:
"- route#{id}: {A} ↔ {B}, {method} ({duration} epochs, danger {d}[, controlled by {C}])".

**`can_use_route(traveller, route)`** (`rotaKullanabilir`) → error string or null:
1. Unknown method → "Unknown travel method".
2. Method requires a knowledge branch and traveller does not know it AND NOT (route has a controller ≠ traveller and
   traveller has a `trade` bond with the controller) → "{method} requires the "{branch}" knowledge (or trade with the
   route's controller)."
3. Method vehicle `mount`: traveller must have an active `tamed` bond to a canon creature tagged `trait:flying` or
   `megafauna` → "For a cosmic mount you must have tamed a flying or giant creature (tame)."
4. Method vehicle `ship`: traveller must have an active `owns` bond to a canon `vehicle` whose subtype contains "ship"
   (`gemi`) → "You need to own a ship for this route (build_ship)."
5. `dead_river` and neither end world is type `dead` → "The river of the dead only passes through the realm of the dead."
6. `fold` and no cosmic access → "To fold space you need access to the cosmic travel resource: own a deposit or trade with its owner."
   Cosmic access = exists canon resource tagged `cosmic resource` with abundance ≥ `fold_min_abundance`, and the traveller
   owns it, or is the owner, or trades with an owner.
7. Route not open now (§3.2) → its reason (or "This route is closed right now.").

**`start_journey({traveller, route, intent, population=0, vehicle_id, epoch})`** (`yolculukBaslat`)
1. Origin = `world_of(traveller)`; route must touch it else throw "This route does not leave the traveller's world.".
   Target = other end.
2. `population = max(0, round(population))`; if traveller has population, cap at `traveller.population − SINIR.population_floor`.
3. `speed = vehicle.stats.speed || vehicle_speed_default` (no vehicle → default).
4. `folding = (method == fold OR (traveller knows pathfinding AND method != swallowing)) AND economy.spend_cosmic_resource(traveller)`
   (spending deducts `ECONOMY.fold_cost` abundance from an accessible deposit and increments the traveller's fold
   counter tag; at `ECONOMY.fold_addiction` uses the traveller becomes `addicted:<deposit>` — economy spec).
5. `remaining = max(1, folding ? 1 : duration − (speed ≥ fast_vehicle ? 1 : 0))`.
6. Insert journey (status en_route). Deduct population from traveller (floored at `SINIR.population_floor`).
7. Return `{id, target, remaining}`.

**`recall_journey(id, {epoch, by=creator})`** (creator hand, free; `yolculukGeriCagir`): must exist and be en_route
else throw. Add carried population back to the traveller; append event "{by} recalled the expedition; travellers
returned home"; status `recalled`. Chronicle `god (tanri)`: "{by} recalled {traveller}'s expedition to {target}; {n}
souls returned home." Returns `{id, status, text}`.

**`reveal_hidden_route(route_id, {epoch, by})`** (creator hand, cost `travel.reveal_cost` default 20 essence via
`epoch.yolEylemi('aciga')`): route must exist and be hidden. Set known=1. Chronicle `cosmic (kozmik)`: "{by} revealed
the hidden route between {A} and {B}: {method}.[ The route is closed for now; it will be used when it opens.]"

### 3.5 Hidden routes and discovery of worlds
**`connect_world(world_id, epoch, {target})`** (`dunyayiBagla`) — "the cosmos's own stitch":
- World must exist and not be forgotten. If **any** route touches it (even sealed) → nothing.
- Candidates: all other non-forgotten worlds with `n` = count of canon people+settlements. Pick `target` if given and
  valid; else sort by (same star first), (n desc), (id asc).
- Method by world types of the pair: either is `dead` → dead_river; else either `dream` → dream; else either `gas` →
  sail; else gate.
- `open_route({a: other, b: world, method, known: 0, description: "The cosmos's own stitch: a passage nobody knows yet."})`.

**`mark_world_discovered(world_id, epoch, reason, note)`** (`dunyaKesfedildi`): only if discovery ∈ {legend, unknown}:
set `known`; chronicle `cosmic`: "{name} is no longer {only a legend | unknown}: {reason}." and note it.

**Reveal knowledge per method** (`ACIGA_CIKARAN`): gate→gate_lore, sail→sky_navigation, slingshot→sky_navigation,
fold→pathfinding, dream→magic, dead_river→none.

### 3.6 Tunables `SEYAHAT` — group "Cosmos & travel" unless noted
| old key | new key | default | min | max | label |
|---|---|---|---|---|---|
| liste_sefer | journey_list_size | 40 | 1 | 100000 | Number of latest journeys shown on the Cosmos page |
| gizli_bilen_sans | hidden_reveal_knower_pct | 35 | 0 | 100 | A hidden route is revealed at an end where someone knows the required knowledge (%) |
| gizli_taban_sans | hidden_reveal_base_pct | 12 | 0 | 100 | Spontaneous reveal of a hidden route (%) |
| gizli_sezen_ek | hidden_reveal_sage_bonus_pct | 10 | 0 | 100 | Bonus from a wise mortal at a route end (%) |
| gizli_ogul_ek | hidden_reveal_son_bonus_pct | 8 | 0 | 100 | Bonus from a son at a route end (%) |
| sezen_akil | sage_min_intellect | 60 | 0 | 100 | Intellect of a mortal able to sense a hidden route |
| sefer_nufus | expedition_min_population | 1200 | 0 | 1000000 | Min population of a community sending spontaneous expeditions |
| sefer_taban | expedition_base_pct | 6 | 0 | 100 | Spontaneous expedition (per epoch %) |
| sefer_kirac | expedition_barren_pct | 15 | 0 | 100 | Pressure from barren land (%) |
| sefer_kirac_esik | barren_fertility_threshold | 30 | 0 | 100 | Fertility below which land counts as barren |
| sefer_kalabalik | expedition_crowded_pct | 10 | 0 | 100 | Pressure from crowding (%) |
| sefer_kalabalik_esik | crowded_population_threshold | 20000 | 0 | 10000000 | Population counted as crowded |
| sefer_yoksul | expedition_poor_pct | 8 | 0 | 100 | Pressure from poverty (%) |
| sefer_yoksul_esik | poor_prosperity_threshold | 25 | 0 | 100 | Prosperity counted as poor |
| koloni_pay | colony_population_share_pct | 10 | 0 | 100 | Colony expedition's population share (%) |
| kayip_sans | lost_swallows_pct | 50 | 0 | 100 | A "lost" road event swallows the journey (%) |
| koloni_istila_sans | colony_seen_as_invader_pct | 35 | 0 | 100 | Natives see the colony as invaders (%) |
| temas_ticaret_sans | first_contact_trade_pct | 50 | 0 | 100 | First contact turns into trade (%) |
| dunyalar_arasi_ittifak | interworld_alliance_pct | 25 | 0 | 100 | Interworld alliance at first contact (%) |
| yol_bilgisi_sans | route_knowledge_pct | 12 | 0 | 100 | A community at a route end learns the route's knowledge (%) |
| koloni_niyet_sans | colony_intent_pct | 50 | 0 | 100 | Expedition to an inhabited world becomes a colony (else exploration/trade) (%) |
| kesif_niyet_sans | exploration_intent_pct | 35 | 0 | 100 | Non-colony spontaneous expedition becomes exploration (else trade) (%) |
| kesif_toprak_sans | exploration_land_pct | 80 | 0 | 100 | Exploration expedition finds new land at arrival (%) |
| hizalanma_donemi | alignment_period | 5 | 1 | 100 | Planets align (slingshot open) every N epochs |
| katlama_bolluk | fold_min_abundance | 12 | 0 | 100 | Min cosmic resource abundance enough for folding |
| rota_tehlike_zar | route_danger_die | 20 | 1 | 100 | New route danger die (1…n) |
| rota_tehlike_kayma | route_danger_shift | 10 | 0 | 100 | Subtracted from new route danger die |
| rota_tehlike_taban | route_danger_min | 5 | 0 | 100 | Lowest route danger |
| rota_tehlike_tavan | route_danger_max | 95 | 0 | 100 | Highest route danger |
| arac_hiz_varsayilan | vehicle_speed_default | 40 | 0 | 100 | Speed of an expedition without a vehicle or with unknown speed |
| hizli_arac | fast_vehicle_speed | 70 | 0 | 100 | Vehicle speed that shortens a journey by one epoch |
| seyir_risk | navigation_risk_pct | 60 | 0 | 100 | Travel risk multiplier for sky-navigation knowers (%) |
| bosluk_risk | void_living_risk_pct | 80 | 0 | 100 | Travel risk multiplier for void-living knowers (%) |
| zirh_bolen | armor_divisor | 250 | 1 | 10000 | Vehicle armour reduces risk by armour / this |
| hayalet_seviye | ghost_ship_power_level | 4 | 1 | 12 | Ghost-ship legend power level |
| hayalet_yayginlik | ghost_ship_spread | 50 | 0 | 100 | Ghost-ship legend spread |
| yol_kayip_taban | road_loss_base_pct | 10 | 0 | 100 | Base share of travellers lost in a road event (%) |
| yol_kayip_zar | road_loss_random_pct | 25 | 0 | 100 | Extra random share lost (up to %) |
| arac_zirh_varsayilan | vehicle_armor_default | 30 | 0 | 100 | Default armour of a vehicle with none written |
| arac_zirh_kayip | vehicle_armor_loss | 10 | 0 | 100 | Vehicle armour loss in attack or storm |
| koloni_refah | colony_prosperity | 30 | 0 | 100 | New colony prosperity |
| koloni_savunma | colony_defense | 25 | 0 | 100 | New colony defence |
| fetih_savunma | outpost_defense | 45 | 0 | 100 | New conquest outpost defence |
| temas_tavan | first_contact_max | 3 | 0 | 100 | Max native communities contacted on arrival |
| istila_iliski | invasion_relation_loss | 30 | 0 | 100 | Relation loss with natives on invasion |
| temas_ticaret_iliski | contact_trade_relation_gain | 15 | 0 | 100 | Relation gain from a contact that becomes trade |
| ittifak_iliski | alliance_relation_gain | 15 | 0 | 100 | Relation gain from interworld alliance |
| tedirgin_iliski | uneasy_contact_relation_loss | 5 | 0 | 100 | Relation loss of an uneasy first contact |
| kesif_karizma | exploration_charisma_gain | 8 | 0 | 100 | Charisma gain from an exploration or pilgrimage |
| ticaret_refah | trade_prosperity_gain | 8 | 0 | 100 | Prosperity gain from a trade expedition |
| yol_bilgisi_tavan | route_knowledge_max_per_epoch | 2 | 0 | 100 | Max communities learning route knowledge per epoch |
| yol_bilgisi_seviye | route_knowledge_power_level | 4 | 1 | 12 | Power level of knowledge born on the road |
| yol_bilgisi_yayginlik | route_knowledge_spread | 5 | 0 | 100 | Initial spread of knowledge born on the road |
| aciga_bedel | reveal_cost | 20 | 0 | 500 | Creator's cost to reveal a hidden route (essence) — group "Cosmic actions" |
| sefer_cag_tavan | expeditions_max_per_epoch | 1 | 0 | 100 | Max spontaneous expeditions per epoch |
| sefer_ziyaret_agirlik | expedition_visit_weight_pct | 50 | 0 | 10000 | Route choice: each earlier journey to the target divides its weight by this % |
| sefer_bos_agirlik | expedition_empty_weight_pct | 300 | 0 | 10000 | Route choice: weight multiplier for a route to a world with no peoples (%) |
| koloni_guc_taban | colony_power_min | 2 | 1 | 12 | Lowest power level of a new colony |
| koloni_guc_eksi | colony_power_minus | 1 | 0 | 11 | New colony power is this much below the sender's |
| koloni_inanc_varsayilan | colony_piety_default | 50 | 0 | 100 | New colony piety if the caravan's is unknown |
| bereket_varsayilan | fertility_default | 50 | 0 | 100 | Fertility assumed for regions with none (arrival land, barrenness) |
| refah_varsayilan | prosperity_default | 50 | 0 | 100 | Prosperity assumed for communities with none (poverty pressure) |

Other modules' rules used: `SINIR.nufus_taban` (population floor), `ECONOMY.katlama_bedel / katlama_bagimlilik`,
method `duration`/`danger` tunables (§1.9.4).

### 3.7 Travel engine (`travel_engine(epoch, note)`, old `seyahatMotoru`) — per epoch, in this order
**A. Hidden routes (`hidden_routes`)**
1. For every non-forgotten world: `connect_world(world)` (ensures no world is isolated; no-op if connected).
2. For every route with `known=0` and (`active=1` or `severed_until` set) and neither end forgotten, ordered by id:
   - `branch = reveal_knowledge[method]`; `ends = {a, b}`.
   - `knower` = some canon community at either end that knows `branch` (if branch exists).
   - `sage` = highest-intellect canon mortal at either end with intellect ≥ `sage_min_intellect`.
   - `son` = first active son (by id) whose active world is either end.
   - `p = ((knower ? hidden_reveal_knower : hidden_reveal_base) + (sage ? sage_bonus : 0) + (son ? son_bonus : 0)) / 100`.
   - If `chance(p)`: set known=1; note "A hidden route was revealed between {A} and {B}: {method}.[ {sage} sensed it in a
     dream. | {son} heard the passage tremble.][ The route is severed for now; it will open when its stitch closes.]"
     (sage/son phrase only when no knower; note ids = [sage] if sage credited). Then `mark_world_discovered` both ends
     ("the hidden route to it ({method}) was revealed").

**B. Route knowledge (`route_knowledge`)** — routes that are active and known; global counter `learned` capped by
`route_knowledge_max_per_epoch` (checked per route before scanning):
- `branch = method.knowledge`; skip if none.
- For each end world (a then b): candidates = canon communities of that world not knowing `branch`; pick the one with
  highest craft+magic. If none or `!chance(route_knowledge_pct)` → try other end.
- Find a canon technology on that world tagged `branch:<branch>`; if none create one with `open_record({type: technology,
  subtype: "road knowledge", name: "{community} {method} Knowledge", power: route_knowledge_power_level, location:
  community.location, tags: ['branch:<branch>'], stats: {level: 1, spread: route_knowledge_spread}, description:
  "[World engine] {community} solved the secret of {method} while trying to understand the route between {A} and {B}."})`.
- Bond community `knows` tech ("learned while trying to understand the route"); note "{community} learned the secret of
  {method}; the road to {other world} is now open to them."; `learned++`; stop this route (break).

**C. Spontaneous expeditions (`spontaneous_expeditions`)**
- `routes_now = routes()` (open & known). Skip if none or `expeditions_max_per_epoch ≤ 0`.
- Candidates: canon people/settlements with population ≥ `expedition_min_population` and not currently travelling.
  For each: `pressure = (location fertility (default) < barren_threshold ? barren_pct : 0) + (population >
  crowded_threshold ? crowded_pct : 0) + (prosperity (default) < poor_threshold ? poor_pct : 0)`;
  `p = (expedition_base_pct + pressure)/100`; `s = random()`. Sort by `p·s` desc (probability-weighted shuffle).
- For each candidate: usable routes = routes touching its world for which `can_use_route` is null. Choose
  `weighted_route(usable, here)`:
  - one route → it; else weight per route `w = 100 / (1 + visits·visit_weight/100) × (target population > 0 ? 1 :
    empty_weight/100)`, `visits` = all journeys ever to that target, population = sum of people+settlement population
    of the target world. Roulette pick.
  - If no route or `!chance(p)` → next.
  - `target_empty` = no canon people/settlement on target. Intent = `colony` if target_empty or `chance(colony_intent)`;
    else `exploration` if `chance(exploration_intent)`; else `trade`.
  - `start_journey({traveller, route, intent, population: colony ? round(pop × colony_share/100) : 0})`; note
    "{community} sent {a colony expedition | an exploration expedition | a trade expedition} to {target}[ by way of {method}]."
    Errors → skip. Stop when `expeditions_max_per_epoch` reached.

**D. Bridge collapse**: every active bridge route with a builder son: if the son is missing or not `active` (asleep or
dead) → route inactive; its vehicle entity (if any) → status dead, death_epoch now, fate note "Epoch N: collapsed when
its builder {son} became {status}."; note "{son or 'A god'}'s divine bridge between {A} and {B} collapsed because he
{died | fell asleep}."

**E. Journeys** — each journey en_route:
- Helper `save(status='en_route', {result_id})` writes remaining, status, events (last 8), population, result.
- Missing traveller or route → status `lost`.
- **Route inactive**: compute state. If `severed` (storm): the journey waits (remaining does not tick); append once the
  event "the route snapped; the expedition is waiting for the stitch to close (Epoch N)" and note "{traveller}'s
  expedition to {target} waits at the mouth of the broken road; it will continue when the stitch closes at the start of
  Epoch N." Otherwise (forgotten / collapsed / sealed / other): event "{reason}; travellers were left in the void",
  status `lost`, note "{traveller}'s journey to {target} vanished in the void: {reason}." Reasons: forgotten "the world
  at the end of the route was forgotten", collapsed "the divine bridge collapsed", sealed "the route was sealed", else
  "the route collapsed".
- **Road event** — `risk = danger/100 × (knows sky_navigation ? navigation_risk_pct/100 : 1) × (knows void_living ?
  void_living_risk_pct/100 : 1) × (vehicle ? 1 − vehicle.armor/armor_divisor : 1)`. If `chance(risk)`:
  - kind: swallowing method → `digested`; dream → `nightmare`; dead_river → `memory`; else uniform of
    `[pirates, storm, creature, lost]`.
  - `lost` and `chance(lost_swallows_pct)`: event "lost their bearings in the void"; status `lost`. If a vehicle: vehicle
    dies (fate note "Epoch N: lost in the void."), create legend `open_record({type: legend, subtype: "ghost ship",
    name: "{vehicle} Ghost", power: ghost_ship_power_level, stats: {spread: ghost_ship_spread}, description: "[World
    engine] {vehicle} vanished in the void with {traveller}'s travellers; on some nights its lights are still seen."})`
    + bond legend `tells_of` vehicle. Note "{traveller}'s expedition to {target} vanished without a trace in the
    void[; {vehicle} is now a ghost-ship legend]." → next journey (no tick).
  - Otherwise loss: `lost_n = round(pop × (road_loss_base/100 + random × road_loss_random/100))`; population −= lost_n.
    Event text by kind: pirates "void pirates attacked", storm "they were caught in a void storm", creature "they met a
    cosmic creature", lost "they lost their way and turned back" (but the journey continues — see smells), digested
    "some were digested inside the creature", nightmare "those left in the dream did not wake", memory "the river's
    water took their memories". If vehicle and kind ∈ {pirates, creature, storm}: `vehicle.armor = clamp((armor ||
    vehicle_armor_default) − vehicle_armor_loss, 0, 100)`. Note "On {traveller}'s journey to {target} {event}[; {n}
    people were lost]."
- `remaining -= 1`; if > 0 save and continue.
- **Arrival**: `result = arrive(journey, traveller, epoch, note)`; save status `arrived` with result;
  `mark_world_discovered(target, "{traveller}'s expedition arrived there")`.

### 3.8 Arrival (`arrive`, old `varis`)
1. Landing region = target world's canon region with the highest fertility (default `fertility_default`). None → note
   "{traveller}'s travellers reached {target} but found no land to set foot on." → return null.
2. `kin = kinship(traveller)` (`soydaslar`): walk `descends_from` up to the root (cycle-safe), collect the root and
   every descendant by BFS over `descends_from`, then add both ends of any `governs` bond touching a member. Natives =
   canon communities on the target world not in `kin` (a second expedition must not declare "invasion" on its own colony).
3. Stowaways: `creatures.stowaway(origin_world, landing_region, epoch)` (§9.6); if one → note "{traveller}'s ships
   carried a stowaway species to {target}; it became invasive there."
4. If intent ∈ {colony, conquest} and population > 0:
   - Atmosphere none/toxic and traveller does not know void_living → note "{traveller}'s colonists could not live under
     {target}'s {airless | toxic} sky; the colony died out in its first winter." → return null.
   - Name = language-derived place name (`dildenAd(traveller, "koloni:<journey_id>", 'place')`) or "{traveller} Colony".
   - `open_record({type: settlement, subtype: conquest ? "conquest outpost" : "colony", power: max(colony_power_min,
     traveller.power − colony_power_minus), location: region, stats: {population, prosperity: colony_prosperity,
     defense: conquest ? outpost_defense : colony_defense, piety: traveller.piety ?? colony_piety_default}, tags:
     ['colony'] (+ 'name-from-language' if derived), description: "[World engine] {n} travellers of {traveller}
     reached {target} and founded a {colony | conquest outpost} in {region}."})`.
   - Bonds: colony `descends_from` traveller ("its colony"); traveller `governs` colony ("colony beyond the worlds");
     colony `speaks` traveller's spoken language; colony `worships` traveller's patron son (if any).
   - `derin.dilVeInancBagla(colony, …, {source: traveller})`: if the caravan had no language/god, the colony takes the
     nearest language/god or a primitive language (other spec).
5. **First contact**: `alive = traveller.status == canon`. Contact candidates = (colony founded or alive) ? natives
   without existing trade/enemy/ally bond with traveller : []; take first `first_contact_max`. For each native:
   - If intent conquest OR (intent colony AND `chance(colony_seen_as_invader)`): `invader = colony or traveller`;
     `derin.savasIlan(invader, native, "first contact: invasion")` → text "{native} saw them as invaders" if war
     declared else "{native} looked at them with hostility"; `rel_change(traveller, native, −invasion_relation_loss, "invasion")`.
   - Else if alive AND (intent trade OR `chance(first_contact_trade)`): bond `trade` ("interworld trade ({target})"),
     `rel_change(+contact_trade_relation_gain, "first contact")`, text "trade began with {native}"; then if
     `chance(interworld_alliance)` and not already allied: bond `ally` ("interworld alliance ({target})"),
     `rel_change(+alliance_relation_gain)`, text "an interworld alliance was formed with {native}"; then cultural
     exchange both ways `derin.kulturTemasi(a, b, …, {first: true})` (loanwords, customs, knowledge, gods — other spec).
   - Else `rel_change(−uneasy_contact_relation_loss, "uneasy first contact")`, text "{native} watched them uneasily".
6. Intent exploration or pilgrimage: traveller charisma += `exploration_charisma_gain` (clamped 0–100, only if it has
   charisma). Find a canon `original resource` on target not yet known (no `knows` bond targets it — note: query
   checks `bilir` bonds to resources, effectively "not yet discovered") → bond traveller `discovered` it.
7. Intent exploration and `chance(exploration_land_pct)`: `horizon.find_land({explorer: traveller, world_id: target,
   near: region, pioneers: false, reason: "on the {target} expedition"})` (§4.4); result defaults to it.
8. Intent trade: `prosperity_add(traveller, trade_prosperity_gain)`.
9. Time difference: `sky.time_difference(traveller, origin, target, max(1, epoch − start_epoch), epoch)` (§5.5) → note.
10. Note "{traveller}'s travellers reached {target} and {founded a colony | founded a conquest outpost | opened trade |
    explored | reached their pilgrimage | landed}.[ First contact: …; ….]" with ids traveller, region, result, contacts.
11. Return result id.

### 3.9 Journey list (`journey_list(limit=journey_list_size)`)
Latest journeys desc, with parsed events, `traveller_name`, `target_name`, `vehicle_name`.

### 3.10 Cross-module calls
Uses: `mudahale.bilir`, `derin.kayitAc, etiketEkle, tIliskiDegistir, TOPLULUK, kanonlar, dilVeInancBagla, kulturTemasi,
savasIlan`, `dilmotoru.dildenAd`, `ekonomi.kozmikKaynaktanHarca`, `yaratik.kacakYolcu`, `gok.zamanFarki, hizaSonu`,
`ufuk.toprakBul`, `sim.refahEkle`, `world.getWorld, getSon, getVarlik, saveStat, addBag, bagVar, hami (patron),
konusulanDil (spoken language), nameOf, addKronik`.
Used by: `kozmos` (birth connection, overview), `ufuk` (rotaAc), `ekonomi` (open routes, danger rules), `medeniyet`
(open routes), `panteon` (open routes for reachability), `olumluler` (mortal tools `sefere_cik`/`rota_kesfet` →
`rotaKullanabilir`, `yolculukBaslat`, `rotaAc`, `rotaSatirlari`), `tools` (son vehicle creation `rotaAc` with bridge
builder; `rotaAcikMi`), `oyuncu` (manual route creation, manual expedition), `epoch` (reveal, recall), `kodeks`.

---

## 4. Exploration / horizon (`src/ufuk.js`)

### 4.1 Purpose
The world extends its own frontier:
- **On a planet**: crowded, hungry or curious communities and explorer-spirited mortals find unknown land (new
  regions, or new places inside regions); pioneers may settle there. An exploration expedition also finds land where
  it arrives (§3.8).
- **In the cosmos**: communities/mortals that know a way between worlds look for routes; very rarely they *sense* a world
  nobody knows (the intuition becomes, at epoch end, a new world birthed by Fate via the LLM).
- **Gods**: awake foreign gods raise new land on their worlds; sons get rewards for creating land when land is
  "narrow" (this module provides the measure; rewards live in tools/opportunities).
Engine-opened records are `pending` (Fate names them later). The creator can trigger each manually (player module:
"send to explore", "search for a route").

### 4.2 Tunables `KESIF` — group "Exploration"
| old key | new key | default | min | max | label |
|---|---|---|---|---|---|
| cag_tavan | lands_max_per_world_epoch | 2 | 0 | 100 | Max new lands mortals spontaneously discover in one world per epoch (0 = off) |
| taban_sans | base_pct | 4 | 0 | 100 | A community or explorer mortal sets out spontaneously per epoch (%) |
| en_az_nufus | min_population | 300 | 0 | 10000000 | Min population (or followers) of a spontaneously exploring community |
| dar_doluluk | crowded_fill_pct | 80 | 1 | 1000 | Region fill (population/carrying capacity) at or above which the community is "narrow" (%) |
| dar_ek | crowded_bonus_pct | 12 | 0 | 100 | Narrow-land bonus to exploration (%) |
| ac_erzak | hungry_food | 15 | 0 | 1000 | Community with food stock below this is hungry |
| yoksul_refah | poor_prosperity | 25 | 0 | 100 | Community with prosperity below this is poor |
| ac_ek | hungry_bonus_pct | 10 | 0 | 100 | Hungry or poor bonus (%) |
| bilgi_ek | knowledge_bonus_pct | 8 | 0 | 100 | Bonus for knowing seafaring, pathfinding or astronomy (%) |
| kasif_esik | explorer_threshold | 120 | 0 | 200 | Intellect + agility of a mortal counted as explorer-spirited |
| kasif_ek | explorer_bonus_pct | 10 | 0 | 100 | Explorer mortal's bonus (for itself or the community on its land) (%) |
| bolge_pay | region_share_pct | 40 | 0 | 100 | Found land is a new region (else a new place inside a region) (%) |
| guc | land_power_level | 3 | 1 | 12 | Power level of discovered land |
| stat_taban | land_stat_base | 15 | 0 | 100 | Base of discovered land's size, magic and mystery |
| stat_zar | land_stat_die | 60 | 1 | 100 | Die added to size, magic, mystery |
| bereket_taban | land_fertility_base | 35 | 0 | 100 | Fertility base |
| bereket_zar | land_fertility_die | 50 | 1 | 100 | Fertility die |
| tehlike_taban | land_danger_base | 10 | 0 | 100 | Danger base |
| tehlike_zar | land_danger_die | 50 | 1 | 100 | Danger die |
| oncu_sans | pioneer_pct | 50 | 0 | 100 | Pioneers settle land the community found (×2 when narrow) (%) |
| oncu_pay | pioneer_share_pct | 8 | 0 | 100 | Pioneer caravan's population share (%) |
| oncu_en_az | pioneer_min | 100 | 1 | 1000000 | Min pioneer settlement population |
| oncu_refah | pioneer_prosperity | 35 | 0 | 100 | Pioneer settlement prosperity |
| oncu_savunma | pioneer_defense | 20 | 0 | 100 | Pioneer settlement defence |
| oncu_inanc | pioneer_piety_default | 50 | 0 | 100 | Piety of pioneers from a community with none written |
| harita_uzaklik | map_distance | 300 | 50 | 2000 | New region's distance on the map from the source region |
| harita_deneme | map_tries | 12 | 1 | 360 | Directions tried when placing a new region on the map |
| rota_sans | route_search_pct | 6 | 0 | 100 | A community/mortal knowing a way between worlds (sky navigation, gate lore, pathfinding, magic, or a flying mount) searches for a route per epoch (%) |
| rota_cag_tavan | route_search_max_per_epoch | 1 | 0 | 100 | Max route searchers in the cosmos per epoch (0 = off) |
| dar_topluluk | narrow_communities_per_region | 3 | 1 | 100 | Communities (people + settlement) per region at/above which a world's land is narrow |
| toprak_bedava | land_free_first | 1 | 0 | 1 | In narrow land, a son's first land creation per epoch costs no action (1 on) |
| toprak_oz | land_essence_reward | 10 | 0 | 10000 | Essence reward for a son creating a region/place in narrow land |
| toprak_un | land_fame_reward | 3 | 0 | 10000 | Fame reward for the same |
| kozmos_durgun | cosmos_stagnant_epochs | 8 | 1 | 1000 | If no world was born for this many epochs, world-birthing sons are reminded of the cosmos |
| yabanci_sans | foreign_god_land_pct | 8 | 0 | 100 | An awake foreign god raises new land on its world per epoch (%) |
| arac_tur | tool_max_per_epoch | 1 | 0 | 20 | `toprak_kesfet` (mortal tool): max discoveries per mortal per epoch (0 disables) |
| arac_esik | tool_threshold | 45 | 0 | 200 | `toprak_kesfet` success threshold (d100 + intellect or craft / rota_akil_bolen + knowledge bonus) |
| arac_bilgi_ek | tool_knowledge_bonus | 15 | 0 | 200 | `toprak_kesfet`: die bonus for seafaring/pathfinding/astronomy knowers |
| liste | summary_list_size | 12 | 1 | 1000 | Latest discoveries in the exploration summary |

Shared with the mortal tool rules (`OLUMLU_ARAC`): `rota_esik` route_find_threshold 55 (0–200, "rota_kesfet: route
finding threshold (d100 + intellect/3)"), `bilinmeyen_esik` unknown_world_threshold 85 (0–200), `bilinmeyen_dunya_tur`
unknown_worlds_max_per_epoch 1 (0–20; worlds born by other means that epoch also count), `rota_akil_bolen`
route_intellect_divisor 3 (1–1000), `stat_varsayilan` stat_default 40, gate stats `kapi_hiz` 90, `kapi_menzil` 100,
`kapi_zirh` 60, `kapi_tuhaflik` 50 + `kapi_tuhaflik_zar` d40, `kapi_guc` 5 (1–30).
Keys `toprak_*`, `kozmos_durgun`, `arac_*` are consumed by tools/opportunities/mortal modules.

### 4.3 Measures
- `KNOWLEDGE_FOR_EXPLORING` = seafaring, pathfinding, astronomy, sky_navigation. `has_exploration_knowledge(v)`.
- `explorer(v)` = mortal with intellect + agility ≥ `explorer_threshold`.
- `land_measure(world)` (`toprakOlcusu`): canon regions, places, communities (people+settlement) of the world; per
  region count communities by `top_region`; `crowded` = regions with count ≥ `narrow_communities_per_region` sorted desc;
  `ratio = communities / max(1, regions)` (2 decimals); `narrow = no regions OR ratio ≥ narrow_communities_per_region`.
  `is_narrow(world)`.
- `exploration_pressure(v, explorers?)` (`kesifBaskisi`) → `{pct, reasons, explorer}`:
  - `p = base_pct`.
  - Community types (people/settlement/faction/cult): if people/settlement and `carrying_capacity(v).fill ≥
    crowded_fill_pct` → `+crowded_bonus`, reason "land narrow". If food < hungry_food OR prosperity < poor_prosperity →
    `+hungry_bonus`, reason "hunger" or "poverty". Explorer = a canon explorer mortal in the same top region who is
    not already on an expedition this epoch (`on_expedition(id)` = has a `discovered` bond created this epoch) →
    `+explorer_bonus`, reason "an explorer among them ({name})".
  - Else (a mortal) if explorer → `+explorer_bonus`, reason "explorer-spirited".
  - Knows exploration knowledge → `+knowledge_bonus`, reason "road knowledge".
  - `pct = clamp(p, 0, 100)`.
- `exploration_sentence(reasons, variant_no)` (`kesifCumlesi`): converts the reason list into a narrative clause
  (never raw measures in the chronicle). Phrase banks (variant chosen by `no` (deterministic, for repairs) or random):
  - narrow: "when their homeland grew too small" / "when their fields no longer fed the crowd" / "when they no longer fit their lands"
  - hunger: "when their granaries emptied" / "when hunger came to the door" / "when famine struck"
  - poverty: "when poverty pressed" / "when their purse tightened" / "when poverty engulfed the homeland"
  - explorer: "led by {X}" / "following {X}" / "when {X} went ahead of them"
  - knowledge: "trusting their road knowledge" / "with old road knowledge" / "finding their way by the stars"
  - spirit: "unable to stay still" / "giving in to curiosity" / "with the curiosity within"
  Assembly: `[narrow/hunger/poverty phrases joined by " and "] [explorer] [spirit] [knowledge]` space-joined.
  (LANGUAGE-SPECIFIC: Turkish suffix fixing of `{X}'in` dropped.)

### 4.4 Finding land (`find_land`, old `toprakBul`)
Params `{explorer, leader, foreign_god, world_id, near, epoch, note, kind ('region'|'place'|null), reason, pioneers=true, narrow=false}`.
1. World = `world_id ?? explorer.world ?? foreign_god.world ?? 1`.
2. Source region = explorer's top region if explorer is on this world, else `near`.
3. Kind: given, else `place` unless `chance(region_share_pct)`.
4. For a place: parent region = `place_region(world, source)`: candidates = source + its land-neighbours on the map
   (or all regions if no source); keep land (non-water elevation); pick the one with fewest places, then lowest id. If
   no parent → return null (a region must be found first).
5. Name: language-derived place name (`dildenAd(explorer, "<id>:<epoch>:kesif:<kind>", 'place')`) or
   "`{explorer or god or world} Discovery`" (place) / "`… Beyond`" (region) (`Keşfi`/`Ötesi`).
6. `open_record({type: kind, subtype: place ? "discovered place" : "discovered lands", power: land_power_level,
   location: parent, stats: land_stats(kind), tags: ['discovery'] (+ name-from-language), description: "[World engine]
   {how}: {place ? `a place inside {parent} no one had set foot in until that day` : 'a new region not on the map'}."})`
   where how = foreign god: "{god} raised it from the depths of the world {W}" / explorer: "{explorer}[, {reason}] set out
   into unknown lands and found it". Set its world.
   - `land_stats(kind)`: for each stat in the entity type schema: fertility → `fertility_base + d(fertility_die)`,
     danger → `danger_base + d(danger_die)`, others → `stat_base + d(stat_die)`, each clamped to schema bounds.
7. Region: `place_on_map(id, world, source)`: compute map; centre = source position; try `map_tries` directions
   (starting at random angle, evenly spaced), point at `map_distance` from centre clamped to map size; choose the point
   farthest from all other regions; write `map_xy` if null.
8. Bonds: place `inside` parent; explorer `discovered` land (description = reason); leader (if different) `discovered`
   land ("led {explorer}'s expedition"); foreign god: land `related` god ("the foreign god who raised it").
9. Pioneers: if `pioneers` and explorer is a canon people/settlement and `chance(min(1, pioneer_pct/100 × (narrow ? 2 : 1)))`
   → `pioneers(explorer, land)`.
10. Note: god → "{god} raised a new {place|region} on the world {W}: {land}[ (inside {parent})]." / explorer →
    "{explorer}[, {reason}] set out into unknown lands: {`{land} was found inside {parent}` | `a new region, {land},
    entered the map`}[ (on the world {W}) if different][; its pioneers founded {settlement} there]."
11. Return `{id, kind, pioneer_id, text}`.

**`pioneers(explorer, land)`** (`onculer`): requires population stat. Floor = people ? `SINIR.people_population_floor`
: `SINIR.population_floor`. `migrants = min(max(0, floor(pop − floor)), SINIR.city_population_cap, round(pop ×
pioneer_share/100))`; if `< max(pioneer_min, population_floor)` → null. Deduct; name language-derived or
"{explorer} Pioneers"; `open_record({type: settlement, subtype: "pioneer settlement", power: max(1, power−1),
location: land, stats: {population: migrants, prosperity: pioneer_prosperity, defense: pioneer_defense, piety:
explorer.piety ?? pioneer_piety_default}, tags: ['pioneer'] (+name-from-language), description: "[World engine]
{migrants} pioneers from {explorer} settled the newly found lands of {land}."})`. Bonds: settlement `inside` land;
explorer `migrated_to` settlement ("pioneers: N people"); settlement `descends_from` explorer; `dilVeInancBagla`.

### 4.5 Searching for routes and sensing worlds
- `route_method(v)` (`yolYontemi`) by first known: gate_lore → gate; pathfinding → fold; sky_navigation → sail; has a
  tamed flying/megafauna creature → mount; magic → dream; else null.
- **`search_route(me, {how, epoch, create, certain})`** (`yolAra`) — shared by mortal tool `rota_kesfet`, engine, and the
  creator's hand. Returns `{status: route|intuition|none|ignorant, …}`; the caller writes the chronicle.
  1. `method = route_method(me) || (certain ? 'dream' : null)`; none → `ignorant`.
  2. Own world forgotten → `none`.
  3. Unconnected = worlds ≠ own with discovery ∈ {known, legend} not linked by an active known route.
  4. `roll = certain ? ∞ : d(100) + (me.intellect ?? me.influence ?? stat_default) / route_intellect_divisor`.
  5. If unconnected exist and `roll ≥ route_find_threshold`: target = uniform unconnected. If method gate: create gate
     vehicle `{type: vehicle, name: "{me} Gate", subtype: "ancient gate", description: "An ancient stone ring found by
     {me}, opening onto the world {T}. {how}", stats: {speed: gate_speed, range: gate_range, crew: 0, armor: gate_armor,
     strangeness: gate_strangeness + d(die)}, power: gate_power, location: me if settlement else me.location}` via
     `create` (canon, mortal tool) or `open_record` (engine; description prefixed "[World engine]"). `open_route({a:
     own, b: target, method, controller: me, vehicle, description: how})`. Return `{status:'route', route_id, target,
     method, vehicle_id, duration, danger, text: "{me} found a route to the world {T}: {method} ({duration} epochs)."}`.
  6. Else if `roll ≥ unknown_world_threshold` AND `can_birth_world(epoch)` → `{status:'intuition', method}`.
     `can_birth_world` = (worlds created this epoch + pending intuitions) < `unknown_worlds_max_per_epoch`.
  7. Else `none`.
- **`record_intuition(me, {how, method, epoch})`** → insert pending row; returns "{me}, searching {how}, sensed the
  existence of a world nobody knew; at the end of the epoch that world will come to light."
- **`birth_intuited_world(me, {how, method, epoch, world_birth})`** (`sezgiyiDogur`): `world_birth({inspiration: "{me}
  mortals, searching {how}, found the way to a world nobody knew."})`; then try `open_route({a: me.world, b: new,
  method, controller: me, description: how})`; on failure set the new world's discovery to `legend`. Chronicle
  `exploration (kesif)`: "{me} discovered a world nobody knew: {W}.[ But its road dissolved into the mist; the world is
  remembered only as a legend.]"
- **`process_intuitions({world_birth, publish})`** (epoch end, async; skipped when LLM disabled): for each pending
  intuition by id: mark `processing`; if the entity is gone or not canon/fulfilled → `wasted`; else birth: success →
  `born` + result world, publish "{me}'s sensed world was born: {W}."; null → `wasted`. On exception → back to
  `pending`, publish error, **stop** (remaining stay queued).
- **`recover_intuitions()`** (startup): processing → pending.

### 4.6 Exploration engine (`exploration_engine(epoch, note)`, old `kesifMotoru`)
1. **Planet exploration** (`planet_exploration(epoch, note, {world_id})` — also the creator's "exploration round"
   for one world): if `lands_max_per_world_epoch ≤ 0` → none. Explorers = canon explorer mortals. For each
   non-forgotten world (optionally only one): `narrow = is_narrow(world)`; candidates = canon entities of the world that
   are (community with population/followers ≥ min_population) or explorer mortals; compute pressure; sort pct desc.
   Loop until `n ≥ cap`: skip mortals already on expedition this epoch; if the candidate's explorer went on another
   expedition meanwhile, recompute pressure; `chance(pct)`; `find_land({explorer: v, leader: its explorer, world,
   reason: exploration_sentence(reasons), narrow, kind: world has regions ? null : 'region'})`; count successes.
   Returns found lands.
2. **Cosmic exploration**: if `route_search_max_per_epoch > 0`: candidates = canon communities and mortals with a
   route_method, shuffled; for each until cap: `chance(route_search_pct)` → n++; `how = "watching the sky and following
   old roads"`; `search_route` → route: note its text; intuition: note `record_intuition(...)`; none: note "{v} searched
   for the road to other worlds but did not find it this epoch."
3. **Foreign god land**: for each awake foreign god: `chance(foreign_god_land_pct)` → `find_land({foreign_god, world:
   god.world, kind: world has regions ? null : 'region'})`.

### 4.7 Repair (`repair_exploration_reasons`, old `kesifNedenOnar`) — one-time data repair, idempotent
Old rows contained raw measure lists ("X, land narrow (fill %104), poverty, an explorer among them (Y), set out into
unknown lands: …"). The repair rewrites (a) chronicle texts containing ", set out into unknown lands", (b) `discovered`
bond descriptions consisting only of raw tags, (c) entity descriptions of the form "[World engine] X (tags) set out into
unknown lands and found it" — into narrative sentences, choosing the variant by the row id. Raw tag regex:
`land narrow( (fill %N))? | hunger | poverty | an explorer among them (…) | explorer-spirited | road knowledge`.
New app: not needed (never store raw measures), but the narrative sentence builder is needed.

### 4.8 Exploration summary (`exploration_summary()`) — UI
For each non-forgotten world: `land_measure` + latest `summary_list_size` discovered regions/places (tag discovery) with
their discoverer; latest `exploration` chronicle entries; latest intuitions (with entity name and born world name); and
the rule snapshot `{lands_max_per_world_epoch, base_pct, route_search_pct, narrow_communities_per_region}`.

### 4.9 Cross-module calls
Uses `derin.kayitAc, kanonlar, dilVeInancBagla, toplumOf (community economy/classes: food stock)`, `olumluler.ustBolge,
OLUMLU_K`, `mudahale.bilir`, `harita.haritaHesapla, HARITA_BOYUT`, `dilmotoru.dildenAd`, `sim.tasimaKapasitesi`,
`seyahat.rotaAc`, rules `VARLIK_TURLERI` (stat schemas), `SINIR`. Used by `seyahat` (arrival land), `olumluler` (tools
`rota_kesfet`, `toprak_kesfet`), `oyuncu` (creator "send to explore", "search route", land measure), `tools` (son land
reward, `darMi`), `firsatlar` (opportunities: narrow land, cosmos stagnant), `epoch` (process intuitions), `onarim`, server.

---

## 5. Time and sky (`src/gok.js`)

### 5.1 Purpose
Per-world "star of the epoch"; sky events (eclipse, comet, planetary alignment, supernova, black-sun birth) plus the
creator-ordered void storm; interworld time difference narration; time echoes (messengers from the future, prophecies
leaking into the past, two-timed heroes). Every event happens spontaneously and the creator can trigger it.

### 5.2 Star of the epoch
- `choose_epoch_stars()` (`cagYildizlariSec`, at epoch transition): for each non-forgotten world, sky bodies = canon
  `sky` entities of that world. None → `star_of_epoch = null`. Else weighted roulette with weight
  `star_pick_base + brightness` → store id. Returns map world → body. (World #1's choice is also used as the cosmos-wide
  "star of the epoch", whose domain makes creations cheaper — sons spec.)
- `world_star(world_id)` → the entity.

### 5.3 Alignment primitive (`open_alignment(epoch, methods, {danger_add=0, duration=alignment_duration})`, old `dizilimAc`)
Shared by the sky "planetary alignment" and the horror "stars aligned" event. All updates exclude routes touching a
forgotten world.
1. Count hidden routes (all methods), then set **all hidden routes known** (regardless of `methods`).
2. Routes of `methods` that are inactive with `severed_until` set → re-activate, clear `severed_until` (stitched).
3. Routes of `methods` inactive with `severed_until` null (sealed) → active with `temp_until = epoch + duration`.
4. If `danger_add`: active routes of `methods` → `danger = min(alignment_danger_max, danger + danger_add)`.
5. If `methods` includes slingshot → `extend_alignment(epoch + duration)` (cosmos `alignment_until = max(current, value)`).
6. Return number of hidden routes revealed.

### 5.4 Sky events (`sky_event(kind, {world_id, star_id, route_id, duration, epoch, by})`, old `gokOlayi`)
Event catalogue (`GOK_OLAYLARI`):
| key | name | description |
|---|---|---|
| eclipse (`tutulma`) | Eclipse | The sky darkens for an epoch; prophecies multiply, fears grow. |
| comet (`kuyruklu`) | Comet | An omen in the sky: seers speak, wars begin or end. |
| alignment (`dizilim`) | Planetary alignment | Planets align: slingshot orbits and gates open. |
| supernova | Supernova | A star explodes: nearby worlds burn, a new light remains in the sky. |
| black_sun (`kara_gunes`) | Birth of a black sun | A star swallows light: leak rises, worshippers of darkness grow strong. |
| storm (`firtina`) | Void storm | A storm breaks in the void: the chosen route snaps for a few epochs, expeditions on it fall into uncertainty. (Creator-ordered; spontaneous version is §6.5.) |

Resolution of the target world `W`: `world_id` ?? first non-forgotten world of `star_id` ?? `route.a_world` ?? random
non-forgotten world ?? 1. World-bound events (all except supernova/black sun) on a forgotten world → throw "{W} was
forgotten; no event can be ordered in the sky inside the mist." Star `S` = `star_id ?? W.star`. `inhabitants` = canon
entities of W.

- **Eclipse**: for every people/settlement/mortal of W: sanity −= `eclipse_sanity` (clamp; default sanity per §8),
  piety += `eclipse_piety` if present. Create prophecy `open_record({type: prophecy, subtype: "eclipse prophecy", name:
  "{W} Eclipse Prophecy", power: eclipse_prophecy_level, stats: {certainty: eclipse_certainty_base + d(die)},
  description: "[World engine] When {W}'s sky darkened the seers whispered the same words."})`, world W.
  `eclipse_seers(prophecy, W)`: top `eclipse_seers` communities of W (cults first, then importance desc) get
  `prophesies` bond ("whispered it during the eclipse"). Text: "In {W} the sky darkened: an eclipse lasted the whole
  epoch. The seers whisper the same prophecy."
- **Comet**: create sky entity `{subtype: "comet", name: "The Comet in {W}'s Sky", power: comet_level, stats:
  {brightness: base + d(die), influence: base + d(die)}, tags: ['omen'], description: "[World engine] A tailed light
  split {W}'s sky."}`, world W. Pick a random active `enemy` bond between entities whose source is in W; if found and
  `chance(comet_peace_pct)` → `derin.barisYap(a, b, epoch, "the comet's omen")` (peace), comet `caused` both ("its omen
  was read as peace"); text suffix " Reading the omen as peace, {a} and {b} laid down arms." Text: "A comet appeared in
  {W}'s sky." + suffix.
- **Alignment**: `slingshots` = count of slingshot routes (not forgotten); `near` = active routes touching any world of
  S; `hidden` = count hidden routes. If ordered by the creator and all three are 0 → throw "There is no route for the
  alignment to open, shorten or reveal: no slingshot orbit in the cosmos, no open route to this star's worlds, and no
  hidden route." (prevents wasting essence). `revealed = open_alignment(epoch, ['slingshot'])`. Active routes touching
  S's worlds: `danger = max(alignment_danger_floor, danger − alignment_danger_drop)`. Text: "The planets aligned[ (around
  {S})]: {routes shortened; slingshot orbits opened for {two} epochs; in the aligned light {n} hidden routes were
  revealed} | ; but there was no route for the alignment to open." (Numbers ≤ 10 written as words — LANGUAGE-SPECIFIC
  number words; use English words or digits.) Note: "routes shortened" only lowers danger, not duration.
- **Supernova**: requires S (throw "A supernova needs a star." / "No such star."). Star type → `star remnant`,
  brightness `supernova_remnant_brightness`. For each non-forgotten world of S: every canon entity's population ×= (1 −
  `supernova_population_pct`/100) (clamped to population floor/cap), fertility −= `supernova_fertility` (clamp 0–100);
  world leak += `supernova_leak` (cap 100). Doom += `supernova_doom` (cap at doom threshold). Text: "{S} exploded: the
  supernova's light burned the worlds around it; most of their peoples became ash, a new and terrible light remained in the sky."
- **Black sun**: requires S. Star type → `black sun`, brightness 0. Leak += `black_sun_leak` on each non-forgotten world
  of S. Outer cults (tag `outer cult`) **on those worlds**: followers = `clamp((followers || cult_followers_default) ×
  black_sun_followers_pct/100, 1, SINIR.followers_cap)`. Text: "{S} turned into a black sun: it gives no light, it swallows light."
- **Void storm** (creator): route = `route_id` or random active non-bridge route touching W (not forgotten) — none →
  throw "There is no open route to sever in {W}'s sky."; `sever_route(route, {epoch, duration: duration > 0 ? round :
  storm_duration, by: by || creator, write: false})` (§6.5); text = its text.
- Always: chronicle `sky (gok)`: "[{by} commanded the sky: ]{text}". Return `{kind, world_id, star_id, text}`.

Creator access: `epoch.kozmikEylem('gok', {olay, dunya_id|yildiz_id|rota_id, sure})`, cost `KOZMIK_BEDEL.gok` (50),
refunded on error; the creator must pick a world, star or (storm) route.

### 5.5 Sky engine (`sky_engine(epoch, note)`, old `gokMotoru`)
1. If `chance(sky_event_pct)`: build a weighted bag with **this exact order** (affects which index a die picks):
   `[eclipse × min(1, w_eclipse), comet × w_comet, alignment × w_alignment, eclipse × (w_eclipse − min(1,w_eclipse)),
   supernova × w_supernova, black_sun × w_black_sun]` (defaults → eclipse, comet, comet, alignment, eclipse, supernova,
   black sun). `kind = bag[d(len)−1]`.
   - supernova/black_sun: candidate star = random star of type red giant/blue giant/broken star/pulsar; if exists and
     `chance(star_event_pct)` → `sky_event(kind, {star})`, note text (errors swallowed).
   - else `sky_event(kind)` on a random world, note text (errors swallowed).
2. **Time echo** if `chance(time_echo_pct)`: pick a random open thread. `related` = first of its related entities that is
   a region/place/settlement.
   - If `chance(time_traveller_share_pct)` and related exists: create mortal `open_record({type: mortal, subtype: "time
     traveller", name: "The Traveller who came to {related}", power: traveller_level, location: related, tags: ['time
     echo', 'thread:<id>'], stats: {hp: traveller_hp, strength: base+d, agility: base+d, intellect: base+d, charisma:
     base+d, age: age_base+d(age_die), lifespan: traveller_lifespan, sanity: traveller_sanity}, description: "[World
     engine] Someone who came from the end of this story, from the future. They cannot fully tell what they saw; but
     they seem to know how this thread will end."})`; note "Someone from the future came to {related}: they seem to
     know the end of an ongoing story."
   - Else create prophecy `{subtype: "prophecy leaked into the past", name: "The Word that Fell Back (thread {id})",
     power: echo_prophecy_level, stats: {certainty: base + d}, tags: ['time echo','thread:<id>'], description: "[World
     engine] The word of something not yet lived fell into the past; it was found on old stones, as if written before
     this epoch."}`; note "The prophecy of something that has not happened yet was found on old stones (thread#{id})."
3. **Two-timed hero** if `chance(two_timed_pct)`: first canon mortal with charisma ≥ `two_timed_min_charisma` not tagged
   `two-timed` → tag; note "{h} was seen in two epochs at once: one young, one old. No one knows which is real."
   (Narrative only; no mechanics read this tag here.)

### 5.6 Time difference (`time_difference(traveller, origin, target, duration_epochs, epoch)`) — narrative only
`k1, k2` = time factors (default 1). If `|k1 − k2| < time_diff_threshold_pct/100` → null. Else `years =
round(EPOCH_YEARS × duration × |k1 − k2|)` (EPOCH_YEARS = live `ZAMAN.cag_yil`). Text: "When {traveller}'s travellers
reached {target}, {years} years {had passed extra in the world they left behind; those they knew had died, their
children had grown old (if k2 < k1) | had passed less; when they return they will have stayed young enough that nobody
recognises them}." Ages are **not** changed (each world already ages with its own factor).

### 5.7 Tunables `GOK` — group "Sky" unless noted
| old key | new key | default | min | max | label |
|---|---|---|---|---|---|
| supernova_kiyamet | supernova_doom | 10 | 0 | 100 | Supernova's contribution to doom (group Doom) |
| supernova_nufus | supernova_population_pct | 40 | 0 | 100 | Population lost in a supernova (%) |
| supernova_bereket | supernova_fertility | 30 | 0 | 100 | Fertility lost in a supernova |
| dizilim_sure | alignment_duration | 2 | 1 | 20 | Epochs an alignment keeps sealed routes open |
| dizilim_tehlike | alignment_danger (UNUSED) | 15 | 0 | 100 | "Horror alignment raises route danger" — dead key; horror uses `KORKU.dizilim_tehlike` |
| kuyruklu_baris_sans | comet_peace_pct | 50 | 0 | 100 | A comet ends a war (%) |
| gok_olay_sans | sky_event_pct | 18 | 0 | 100 | Spontaneous sky event (per epoch %) |
| yildiz_olay_sans | star_event_pct | 30 | 0 | 100 | A supernova or black sun actually happens (%) |
| zaman_yanki_sans | time_echo_pct | 6 | 0 | 100 | Time echo (%) |
| zaman_yolcu_orani | time_traveller_share_pct | 50 | 0 | 100 | Share of echoes that are time travellers (%) |
| iki_zamanli_sans | two_timed_pct | 3 | 0 | 100 | Two-timed hero (%) |
| dizilim_tehlike_tavan | alignment_danger_max | 95 | 0 | 100 | Max route danger the horror alignment can push to |
| dizilim_tehlike_azalma | alignment_danger_drop | 10 | 0 | 100 | Route danger drop in a planetary alignment |
| dizilim_tehlike_taban | alignment_danger_floor | 5 | 0 | 100 | Lowest route danger an alignment can lower to |
| yildiz_secim_taban | star_pick_base | 5 | 0 | 1000 | Base weight of every sky body in the star-of-the-epoch pick |
| olay_tutulma | weight_eclipse | 2 | 0 | 50 | Spontaneous event weight: eclipse |
| olay_kuyruklu | weight_comet | 2 | 0 | 50 | … comet |
| olay_dizilim | weight_alignment | 1 | 0 | 50 | … planetary alignment |
| olay_supernova | weight_supernova | 1 | 0 | 50 | … supernova |
| olay_kara_gunes | weight_black_sun | 1 | 0 | 50 | … black sun |
| tutulma_sagduyu | eclipse_sanity | 5 | 0 | 100 | Sanity loss of mortals in an eclipse |
| tutulma_inanc | eclipse_piety | 5 | 0 | 100 | Piety rise in an eclipse |
| tutulma_kehanet_seviye | eclipse_prophecy_level | 4 | 1 | 12 | Eclipse prophecy power level |
| tutulma_kahin | eclipse_seers | 2 | 0 | 20 | Communities whispering the eclipse prophecy (the world's most important) |
| tutulma_kesinlik_taban / _zar | eclipse_certainty_base / _die | 40 / 40 | 0/1 | 100 | Eclipse prophecy certainty |
| kuyruklu_seviye | comet_level | 4 | 1 | 12 | Comet power level |
| kuyruklu_parlaklik_taban / _zar | comet_brightness_base / _die | 60 / 30 | 0/1 | 100 | Comet brightness |
| kuyruklu_etki_taban / _zar | comet_influence_base / _die | 40 / 40 | 0/1 | 100 | Comet influence |
| supernova_kalinti_parlaklik | supernova_remnant_brightness | 15 | 0 | 100 | Supernova remnant brightness |
| supernova_sizinti | supernova_leak | 15 | 0 | 100 | Supernova leak to its worlds (group Cosmic horror) |
| kara_gunes_sizinti | black_sun_leak | 25 | 0 | 100 | Black sun leak to its worlds (group Cosmic horror) |
| kara_gunes_murit | black_sun_followers_pct | 140 | 100 | 1000 | Outer cults' follower multiplier under a black sun (%) |
| yolcu_seviye | traveller_level | 5 | 1 | 12 | Time traveller power level |
| yolcu_can | traveller_hp | 120 | 1 | 1000 | Time traveller HP |
| yolcu_guc_taban / _zar | traveller_strength_base / _die | 40 / 30 | 0/1 | 100 | Time traveller strength |
| yolcu_ceviklik_taban / _zar | traveller_agility_base / _die | 40 / 30 | 0/1 | 100 | … agility |
| yolcu_akil_taban / _zar | traveller_intellect_base / _die | 60 / 40 | 0/1 | 100 | … intellect |
| yolcu_karizma_taban / _zar | traveller_charisma_base / _die | 40 / 40 | 0/1 | 100 | … charisma |
| yolcu_yas_taban / _zar | traveller_age_base / _die | 30 / 40 | 0/1 | 1000 | … age (years) |
| yolcu_omur | traveller_lifespan | 200 | 1 | 50000 | … lifespan (years) |
| yolcu_sagduyu | traveller_sanity | 50 | 0 | 100 | … sanity |
| yanki_kehanet_seviye | echo_prophecy_level | 5 | 1 | 12 | Prophecy-leaked-into-the-past power level |
| yanki_kesinlik_taban / _zar | echo_certainty_base / _die | 70 / 30 | 0/1 | 100 | Its certainty |
| iki_zamanli_karizma | two_timed_min_charisma | 70 | 0 | 100 | Min charisma of a hero who may become two-timed |
| zaman_fark_esik | time_diff_threshold_pct | 75 | 0 | 1000 | Time-factor difference that yields a narrated age gap (%) |
| firtina_sure | storm_duration | 3 | 1 | 50 | Epochs a creator-ordered void storm severs the route (if not given) — group Cosmos & travel |
| murit_varsayilan | cult_followers_default | 50 | 1 | 100000 | Followers assumed for a cult with none written (black sun) |

### 5.8 Cross-module calls
Uses `korku.sagduyu`, `otesi.rotaKopar`, `derin.kayitAc, etiketEkle, kanonlar, barisYap`, rules `DENGE.kiyamet_esik`,
`SINIR`, `CAG_YIL`. Adds column `dunya.hizalanma_son` at module load (migration smell). Used by `sim` (engine, star
pick), `seyahat` (`zamanFarki`, `hizaSonu`), `korku` (`dizilimAc`), `tools` (`dunyaninYildizi`), `agonar` (network
repair re-links eclipse seers via `tutulmaKahinleri`), `epoch` (creator `gokOlayi`).

---

## 6. The Beyond (`src/otesi.js`) — proposals Ö-38…Ö-46
Soul economy, planetary consciousness, cosmic archive, cosmic plague, void storms (and route sever/stitch), mirror world,
legendary quests, cosmic law, pursuit of immortality. Each runs spontaneously; the creator can steer.

### 6.1 Tunables `OTESI` — group "Beyond" unless noted
| old key | new key | default | min | max | label |
|---|---|---|---|---|---|
| sefer_odul_oz | quest_reward_essence | 60 | 0 | 1000 | Essence the creator gains from a legendary quest |
| sefer_odul_kiyamet | quest_reward_doom | 15 | 0 | 100 | Legendary quest pushes doom back (group Doom) |
| sefer_ceza_kiyamet | quest_penalty_doom | 15 | 0 | 100 | Failed quest's doom contribution (group Doom) |
| sefer_sure | quest_duration | 6 | 1 | 50 | Legendary quest duration (epochs) |
| firtina_kapali_en_az | storm_closed_min | 2 | 0 | 20 | Min epochs a storm severs a route (group Cosmos & travel) |
| firtina_kapali_zar | storm_closed_die | 3 | 1 | 20 | Die added to storm severance (1…n epochs) (Cosmos & travel) |
| ruh_birikim_esik | soul_accumulation_threshold | 6 | 1 | 100 | Souls in a realm of the dead that raise its leak |
| ruh_inis_sans | soul_descent_pct | 35 | 0 | 100 | A dead mortal's soul descends to the realm of the dead (%) |
| ruh_hasat_sans | soul_harvest_pct | 20 | 0 | 100 | A fanatic cult harvests a soul (%) |
| gezegen_sans | planet_acts_pct | 35 | 0 | 100 | A living planet acts (%) |
| gezegen_ceza_sans | planet_punishes_pct | 50 | 0 | 100 | The planet shakes its polluter (%) |
| gezegene_tapma_sans | planet_worship_pct | 30 | 0 | 100 | A godless people starts worshipping the planet (%) |
| arsiv_sans | archive_appears_pct | 12 | 0 | 100 | The cosmic archive appears (%) |
| arsiv_bilgi_sans | archive_knowledge_pct | 30 | 0 | 100 | Knowledge is extracted from the archive (%) |
| kozmik_salgin_sans | cosmic_plague_pct | 12 | 0 | 100 | An arriving expedition carries a plague (%) |
| hiclik_firtina_sans | void_storm_pct | 8 | 0 | 100 | Void storm (per epoch %) (Cosmos & travel) |
| firtina_aciga_cikar | storm_reveals_pct | 50 | 0 | 100 | A hidden route swallowed by a storm is revealed (%) (Cosmos & travel) |
| firtina_kayip_sans | storm_loses_journey_pct | 50 | 0 | 100 | An en-route expedition is lost in the storm (%) (Cosmos & travel) |
| efsanevi_sefer_sans | quest_open_pct | 8 | 0 | 100 | Fate opens a legendary quest (%) |
| sefer_eszamanli | quest_concurrent_max | 1 | 0 | 20 | When open legendary quests (creator's included) reach this, Fate opens no new one |
| olumsuzluk_sans | immortality_pct | 15 | 0 | 100 | A wise mortal reaches immortality (%) |
| golem_seviye | golem_min_level | 4 | 1 | 12 | Min power level of a golem born from a soul-bound work |
| golem_can | golem_hp | 400 | 1 | 100000 | Golem HP |
| golem_guc_taban / _zar | golem_strength_base / _die | 70 / 25 | 0/1 | 100 | Golem strength |
| golem_ceviklik | golem_agility | 15 | 0 | 100 | Golem agility |
| golem_zeka_taban / _zar | golem_intelligence_base / _die | 20 / 30 | 0/1 | 100 | Golem intelligence |
| golem_tehlike_taban / _zar | golem_danger_base / _die | 40 / 30 | 0/1 | 100 | Golem danger |
| ruh_kudret | soul_might_gain | 30 | 0 | 100 | Might gain of a soul-bound item |
| ruh_tuhaflik | soul_strangeness_gain | 25 | 0 | 100 | Strangeness gain of a soul-bound vehicle |
| ruh_birikim_sizinti | soul_accumulation_leak | 2 | 0 | 100 | Per-epoch leak from soul accumulation in the realm of the dead |
| ruh_inis_tavan | soul_descent_max | 3 | 0 | 100 | Max souls descending to one realm of the dead per epoch |
| inen_ruh_seviye | descended_soul_level | 3 | 1 | 12 | Descended soul power level |
| inen_ruh_guc_taban / _zar | descended_soul_strength_base / _die | 30 / 30 | 0/1 | 100 | Descended soul strength |
| inen_ruh_huzursuzluk_taban / _zar | descended_soul_unrest_base / _die | 30 / 40 | 0/1 | 100 | Descended soul unrest |
| ruh_hasat_bagnazlik | soul_harvest_min_fanaticism | 65 | 0 | 100 | Min fanaticism of a cult that can harvest souls |
| ruh_hasat_murit | soul_harvest_followers_pct | 115 | 100 | 1000 | Follower multiplier on soul harvest (%) |
| ruh_hasat_etki | soul_harvest_influence | 5 | 0 | 100 | Cult influence gain on harvest |
| tarikat_etki_varsayilan | cult_influence_default | 30 | 0 | 100 | Default influence of a cult with none written |
| gezegen_deprem_siddet | planet_quake_severity_pct | 70 | 0 | 300 | Severity of the planet's quake on a polluter (%) |
| gezegen_refah | planet_prosperity | 6 | 0 | 100 | Prosperity the planet gives its worshippers |
| gezegen_nufus | planet_population_pct | 105 | 100 | 1000 | Population multiplier the planet gives its worshippers (%) |
| gezegen_kapat_tehlike | planet_close_danger | 25 | 0 | 100 | Region danger change when the planet closes/opens its skin |
| bolge_tehlike_varsayilan | region_danger_default | 30 | 0 | 100 | Default danger of a region with none written |
| gezegene_tapma_tavan | planet_worship_candidates | 1 | 0 | 100 | Godless communities per epoch that may start worshipping the planet |
| arsiv_dunya_esik | archive_min_worlds | 2 | 1 | 100 | Min worlds for the cosmic archive to appear |
| arsiv_seviye | archive_level | 9 | 1 | 12 | Cosmic archive power level |
| arsiv_ihtisam | archive_splendour | 95 | 0 | 100 | Archive splendour |
| arsiv_saglamlik | archive_durability | 70 | 0 | 100 | Archive durability |
| arsiv_islev | archive_function | 100 | 0 | 100 | Archive function |
| arsiv_bilgi_tavan | archive_readers_max | 2 | 0 | 100 | Max communities seeking knowledge from the archive per epoch |
| arsiv_yanma_pay | archive_burn_share_pct | 25 | 0 | 100 | Share of knowledge bonds lost when the archive burns (%) |
| kozmik_salgin_cag | cosmic_plague_window | 3 | 0 | 50 | Oldest start (epochs ago) of an expedition that can carry plague |
| kozmik_salgin_siddet | cosmic_plague_severity_pct | 80 | 0 | 300 | Cosmic plague severity (%) |
| ayna_tavan | mirror_births_max | 3 | 0 | 100 | Max mirror births per epoch in a mirror world |
| ayna_can | mirror_hp | 100 | 1 | 1000 | Mirror-born HP |
| ayna_omur_varsayilan | mirror_lifespan_default | 70 | 1 | 50000 | Lifespan of the mirror of a dead with none written (years) |
| sefer_un | quest_fame | 10 | 0 | 100 | Fame gained by every son when a quest completes |
| sefer_ceza_sizinti | quest_penalty_leak | 10 | 0 | 100 | Failed quest's leak on every world |
| mahkeme_mesafe | court_distance | 4 | 0 | 50 | Max distance (steps) of neighbours whose trust in an oathbreaker is shaken |
| mahkeme_komsu | court_neighbours | 6 | 0 | 100 | Max neighbours whose trust is shaken |
| mahkeme_iliski | court_relation_loss | 10 | 0 | 100 | Relation loss between oathbreaker and neighbours |
| olumsuzluk_esik | immortality_threshold | 120 | 0 | 200 | Intellect + charisma of a mortal who can reach immortality |
| olumsuzluk_ofke | immortality_son_anger | 4 | 0 | 100 | Sons' anger rise when a mortal becomes immortal |
| dik_bedel | seal_cost | 40 | 0 | 500 | Creator's cost to re-stitch a severed or sealed route (essence) (Cosmic actions) |
| kopar_bedel | sever_cost | 40 | 0 | 500 | Creator's cost to sever a route for a few epochs (essence) (Cosmic actions) |
| kopar_sure | sever_duration | 3 | 1 | 50 | Epochs a creator-severed route stays closed (if not given) (Cosmos & travel) |
| tarikat_murit_varsayilan | cult_followers_default | 50 | 1 | 100000 | Followers assumed for a cult with none written (soul harvest) |
| ayna_stat_varsayilan | mirror_stat_default | 50 | 0 | 100 | Unwritten stat of the dead (its mirror is born with the inverse) |

### 6.2 Soul economy (Ö-38)
**`soul_bind(soul_id, target_id, by, epoch)`** (`ruhKapla`; creator cosmic action `ruh` cost `KOZMIK_BEDEL.ruh` 15;
also mortal and son tools):
- Soul must be a canon `soul` → else "No such free soul."; target must be item/vehicle/work → else "A soul binds only to
  an item, a vehicle or a work."
- `kill(soul, "Epoch N: bound to {target}.", close_bonds)`; bond soul `inside` target ("soul binding").
- Work → golem: `open_record({type: species, subtype: golem, name: "{work} Golem", power: max(golem_min_level,
  work.power), location: work.location, stats: {hp: golem_hp, strength: base+d, agility: golem_agility, intelligence:
  base+d, danger: base+d}, tags: ['golem','trait:stone_skinned'], description: "[World engine] {soul} was bound to the
  stone of {work} and the stone began to walk."})`; if `by.id` → bond by `tamed` golem ("its own golem").
- Item/vehicle: might += soul_might_gain (clamp); vehicle strangeness += soul_strangeness_gain; tag `soul-bound`.
- Chronicle `soul (ruh)`: "{by or creator} bound {soul} to {target}[; the stone began to walk]." Returns golem id or target id.

**Soul economy per epoch**:
1. For each world of type `dead`: `n` = canon souls there; if `n ≥ soul_accumulation_threshold` → leak +=
   `soul_accumulation_leak` (cap 100). Then dead mortals with `death_epoch ≥ epoch−1` not tagged `soul descended`,
   ordered by death epoch, id, limit `soul_descent_max` (**query is not filtered by world** — see smells): for each,
   `chance(soul_descent_pct)` → random canon region of that dead realm (none → break); tag dead `soul descended`;
   `open_record({type: soul, subtype: "descended soul", name: "Shadow of {dead}", power: descended_soul_level,
   location: region, stats: {strength: base+d, unrest: base+d}, description: "[World engine] {dead} died and their soul
   descended to {realm}."})`.
2. Soul harvest: for each canon cult with fanaticism ≥ `soul_harvest_min_fanaticism`: first canon soul in the cult's
   world; if exists and `chance(soul_harvest_pct)`: kill soul ("Epoch N: harvested by {cult}."); followers ×=
   soul_harvest_followers_pct/100 (clamp 1..followers cap; default `cult_followers_default`); influence +=
   soul_harvest_influence (default `cult_influence_default`); tag `soul harvester`; note "{cult} harvested {soul}; the
   cult's power grew, the dead are restless." (The comment says world sanity falls — not implemented.)

### 6.3 Planetary consciousness (Ö-39) — worlds of type `living`, not forgotten
For each: if `chance(planet_acts_pct)`:
- `polluter` = first community of the world that knows `forbidden` or is tagged `cursed`; `protected` = first community
  tagged `worships the planet`; `region` = random region of the world.
- If polluter and `chance(planet_punishes_pct)` → `mudahale.afetUygula(polluter if settlement else its location or
  itself, 'earthquake', planet_quake_severity_pct/100)`; note "{W} stirred: the planet shook {polluter}, who polluted it."
- Else if protected → prosperity += planet_prosperity; population ×= planet_population_pct/100 (clamped); note "{W} fed
  {protected}, who worship it: the lands grew warm."
- Else if region → toggle tag `planet closed`: closing → danger += planet_close_danger, note "{W} closed its skin over
  {region}; entering it is dangerous."; opening → danger −= …, note "{W} opened {region} again." (default danger
  `region_danger_default`).
Then (regardless of the act roll? — no: inside the same `if chance` block) godless communities (no active `worships`
bond, not tagged) up to `planet_worship_candidates`: `chance(planet_worship_pct)` → tag `worships the planet`; note
"{h} began to worship the living planet beneath its feet."
(Precisely: the worship loop is inside the per-world block after the act roll succeeded.)

### 6.4 Cosmic archive (Ö-40)
- If no canon archive (tag `cosmic archive`) AND non-forgotten worlds ≥ `archive_min_worlds` AND `chance(archive_appears_pct)`:
  region = canon region with highest magic among non-forgotten worlds; `open_record({type: work, subtype: "cosmic
  archive", name: "Cosmic Archive", power: archive_level, location: region, tags: ['cosmic archive','wonder'], stats:
  {splendour, durability, function}, description: "[World engine] A place that gathers the knowledge of all worlds by
  itself. Nobody knows who built it; the shelves grow a little longer every epoch."})`; note "In {W} an archive gathering
  the knowledge of all worlds appeared."
- If an archive exists in a non-forgotten world: all knowledge = canon technologies not tagged `lost`. For each
  community of the archive's world that knows `writing`, up to `archive_readers_max`: first tech it does not know; if
  found and `chance(archive_knowledge_pct)` → `teach(community, tech, "From the Cosmic Archive")`; note "{community}'s
  scribes extracted the knowledge of {tech} from the Cosmic Archive."
- **`archive_burned(epoch, note)`** (`arsivYandiMi`): the archive entity exists with status ≠ canon and not tagged
  `burned` → tag `burned`; deactivate a random `floor(N × archive_burn_share_pct/100)` of **all** active `knows` bonds
  cosmos-wide (description "burned with the archive"); chronicle `age_change (cag_degisimi)`: "The Cosmic Archive
  burned. {pct}% of knowledge in all worlds turned to ash with it; this is the end of an age."; note "The Cosmic Archive
  burned; {pct}% of knowledge was lost."

### 6.5 Cosmic plague (Ö-41) and void storms (Ö-42)
- Plague: journeys with status arrived, result set, `start_epoch ≥ epoch − cosmic_plague_window`: result entity not
  tagged `cosmic plague` and `chance(cosmic_plague_pct)` → `afetUygula(result, 'plague', cosmic_plague_severity_pct/100)`;
  tag; note "A disease came to {place} from another world; no one knows its name." (Each arrival gets one roll per epoch
  while inside the window until infected.)
- Spontaneous void storm: `chance(void_storm_pct)` → random active non-bridge route (not forgotten) → `sever_route(route)`;
  note "A void storm swallowed a hidden route but the route was revealed." or "A void storm swallowed a route."

**`sever_route(route_id, {epoch, duration, by, reason, write=true})`** (`rotaKopar`) — shared by spontaneous storm,
creator's sky storm and creator's direct hand (cost `sever_cost` via `epoch.yolEylemi('kopar')`):
1. Route must exist ("No such route.") and be active ("This route is already closed.").
2. Dice order (preserve): first `revealed = !known && chance(storm_reveals_pct)`; then
   `n = duration > 0 ? round(duration) : by ? sever_duration : storm_closed_min + d(storm_closed_die)`.
3. Route: active=0, `severed_until = epoch + n`, known = revealed ? 1 : known.
4. Journeys on it: each `chance(storm_loses_journey_pct)` → status lost, event "the void storm swallowed the
   expedition". Survivors wait (§3.7E).
5. Text: "[{by} unleashed a void storm[ ({reason})]: | A void storm ]swallowed the [hidden ]route between {A} and {B};
   its stitch closes at the start of Epoch {epoch+n}[; of the N expeditions on the road, K were lost, M survived and wait
   for the stitch to close].[ As the route snapped, light leaking through the crack betrayed it: it is no longer
   hidden; it can be used again once the storm calms.]"
6. If `write`: chronicle (`cosmic` if by, else `horror (korku)`).
7. Return `{route_id, severed_until, duration, lost, waiting, revealed, text}`.
Re-opening on expiry happens in the horror engine (§8.4 step 1).

**`stitch_route(route_id, {epoch, by})`** (`rotaDik`, creator cost `seal_cost`): must exist, be inactive ("This route
is already open."), not touch a forgotten world ("…the route inside the mist cannot be stitched."), not a bridge whose
builder is not active ("The bridge's builder fell; the bridge collapsed with him, nothing remains to stitch."). Set
active=1, clear severed_until and temp_until. Chronicle `cosmic`: "{by} {re-stitched the severed route | broke the seal
of the sealed route and reopened it} between {A} and {B}."

### 6.6 Mirror world (Ö-43)
For each world with a mirror twin: dead mortals of the twin with `death_epoch ≥ epoch−1`, not tagged `mirror born`,
ordered by death epoch, id, limit `mirror_births_max`; random canon region of the mirror world (none → skip world). For
each dead: `open_record({type: mortal, subtype: "mirror birth", name: "{dead} (mirror)", power: dead.power, location:
region, tags: ['mirror'], stats: {hp: mirror_hp, strength: 100 − (s.strength || default), agility: 100 − …, intellect:
100 − …, charisma: 100 − …, age: 0, lifespan: s.lifespan || mirror_lifespan_default}, description: "[World engine]
{dead}, who died in {twin} in Epoch N, was born inverted in {mirror}. A mortal, not a son of a god." (or "the moment
{dead} died in {twin}, their inverse was born in {mirror}")})`; tag dead `mirror born`; bond mirror `related` dead
("its mirror"); note "{dead} died; their mirror was born in {mirror}." (or for earlier-epoch deaths "The mirror of
{dead}, who died in Epoch N, was born in {mirror}.") — "a mortal, not a son" is explicit because the naming LLM mistook
mirror births for sons.

### 6.7 Legendary quests (Ö-44) — stored as Fate threads with `legendary` JSON
Quest types (`BUYUK`):
| key | name | completed when | invalid when |
|---|---|---|---|
| dead_star (`olu_yildiz`) | Rekindle the dead star | target star exists and type ∉ {dead star, black sun, star remnant} | star no longer exists → "the target star was removed from the sky" |
| sealed_gate (`muhurlu_kapi`) | Reopen the sealed gate | target route active AND `temp_until IS NULL` (permanent opening only) | route gone → "the sealed route no longer exists" |
| archive (`arsiv`) | Reach the Cosmic Archive | some journey arrived at the archive's world that was not in `prior` (journeys already arrived at open time); old rows without `prior` use `start_epoch ≥ opened_epoch` | no reachable archive → "the Cosmic Archive vanished or was buried in mist" |
| expel_outer (`dis_kov`) | Expel the one from outside | target Outer Being no longer canon | — |

**`open_quest(type, epoch, by='Fate')`** (`buyukSeferAc`; creator action `sefer` cost `KOZMIK_BEDEL.sefer` 30):
- dead_star: first star of the dead group (else throw "There is no dead star."), text "{star} must be rekindled."
- sealed_gate: first route inactive, severed_until null, temp_until null, ends not forgotten (else "There is no sealed
  route."), text "The sealed route between {A} and {B} must be reopened."
- archive: archive exists (else "There is no Cosmic Archive (or its world was forgotten)."), `prior` = ids of journeys
  already arrived at its world, text "A people must pass between the worlds and reach the Cosmic Archive in {W}."
- expel_outer: first canon Outer Being (else "Nothing from outside exists."), text "The thing that entered {W} must be
  pushed outside."
- Insert thread: text "LEGENDARY QUEST — {name}: {text} Those who succeed will enter the epic of the cosmos; if it
  fails the price will be heavy.", related `[]`, legendary `{type, target, end_epoch: epoch + quest_duration, by,
  opened_epoch: epoch, prior?}`. Chronicle `legendary_quest (efsanevi_sefer)`: "{by} opened a legendary quest: {name}. {text}".

**Per epoch**:
1. If open legendary threads < `quest_concurrent_max` and `chance(quest_open_pct)`: try types in random order until one
   opens; note "Fate opened a new legendary quest."
2. For each open legendary thread: (legacy `opened_epoch` = thread epoch)
   - invalid → close thread ("Legendary quest fell: {reason}."), chronicle "Legendary quest fell: {name}. Its target
     vanished ({reason}); no one was rewarded, nor did the cosmos pay a price.", note.
   - completed → close ("completed successfully"); every active son fame += quest_fame; creator essence +=
     quest_reward_essence; doom −= quest_reward_doom (floor 0); chronicle "Legendary quest completed: {name}. The cosmos
     took a breath; doom receded, the gods' fame grew."
   - `epoch ≥ end_epoch` → close ("failed"); doom += quest_penalty_doom (cap threshold); every world leak +=
     quest_penalty_leak (cap 100); chronicle "Legendary quest failed: {name}. The cosmos pays the price: doom came closer,
     something leaked into the worlds."

`QUEST_NAMES` map exported for the UI.

### 6.8 Cosmic law (Ö-45)
- **`cosmic_court(traitor_id, victim_id, epoch)`** — called from diplomacy (`derin`) when an ally betrays its ally (alliance bond broken, betrayal roll) and the cosmos
  has ≥ 2 worlds: tag traitor `oathbreaker`, `cursed`; up to `court_neighbours` communities of the same world within
  `court_distance` → `rel_change(traitor, k, −court_relation_loss, "broke an oath")`; chronicle `cosmic_law
  (kozmik_hukuk)`: "Cosmic court (Fate's voice): {traitor} broke the oath given to {victim}. Verdict: a curse and the
  distrust of its neighbours."
- **`exile(entity_id, world_id, epoch)`** (creator): only communities and mortals ("Only communities and mortals can be
  exiled."), must be canon, world must exist and not be forgotten, world must have a region. Destination = the world's
  most dangerous region. Move entity (location, clear map xy, refresh location bond), tag `exile`. Everything located
  inside it (BFS by location, ≤ 5000 steps) moves to the new world. Hostile bonds (enemy, spy, rival, hunts) between moved
  entities and entities not in the destination world are deactivated (" (severed by exile)"). Chronicle `cosmic_law`:
  "{creator} exiled {v} to the world {W}."
- **`pardon(id, epoch)`**: remove tags oathbreaker, exile, cursed; chronicle "{creator} pardoned {v}."

### 6.9 Pursuit of immortality (Ö-46)
For each canon mortal not tagged `immortal` who knows `immortality` (or whose location knows it) and intellect +
charisma ≥ `immortality_threshold`: `chance(immortality_pct)` → tag `immortal`; every active son anger +=
`immortality_son_anger`; chronicle `immortality (olumsuzluk)`: "{o} defeated death: they no longer age. The gods saw
this as a threat."; note. (Ageing engine must skip `immortal` — other spec.)

### 6.10 Beyond engine order (`beyond_engine`, old `otesiMotoru`)
1. `fill_death_epochs(epoch)` (`derin.olumCagiDoldur`: back-fills death epoch for entities killed by tools/Fate).
2. Soul economy. 3. Planetary consciousness. 4. Cosmic archive, then `archive_burned`. 5. Cosmic plague & void storm.
6. Mirror world. 7. Legendary quests. 8. Immortality.

### 6.11 Cross-module calls
Uses `mudahale.bilir, bildikleri, ogret, afetUygula (apply disaster)`, `derin.kayitAc, etiketEkle, etiketSil,
tIliskiDegistir, TOPLULUK, mesafe, kanonlar, oldur, olumCagiDoldur`, `world.konumBaginiTazele, getSon, allSons, saveSon`,
`sim.refahEkle`. Used by `gok` (`rotaKopar`), `derin` (`kozmikMahkeme`), `epoch` (creator `ruhKapla`, `buyukSeferAc`,
`rotaKopar`, `rotaDik`), `olumluler`/`tools` (`ruhKapla`), server routes `POST /api/varliklar/:id/surgun` (exile, body `dunya_id`) and `/af` (pardon) — free creator actions, `kurallar` UI (`BUYUK_ADLAR`).

---

## 7. Foreign gods' attributes (`src/yabanci.js`)

### 7.1 Purpose
Foreign (old) gods have the same nine stats as sons, plus powers, personality, existence and depth. Every stat and power
maps to a mechanic in the pantheon engine (§11) or son tools. Stat-less records are filled from a **name-seeded** die so
the same god always gets the same stats (and the engine's global die order is not disturbed).

### 7.2 Stats
The nine son stats (`SON_STATS`): strength (`guc`), endurance (`dayaniklilik`), agility (`ceviklik`), wisdom
(`bilgelik`), cunning (`kurnazlik`), will (`irade`), creativity (`yaraticilik`), charisma (`karizma`), might (`kudret`).
Every stat's effect = `(stat − neutral) × rate / 100` (`yt_effect(god, stat, rate)`), so stats above neutral help,
below hurt. Stat effect texts (display, generated from live rules):
| stat | rule | effect |
|---|---|---|
| strength | war_stat_share | War power: (Strength + Will)/2 weighs `war_stat_share`% in battle (rest is general power). |
| will | talk_will | Half of war power; resistance to sons' alliance/threat/bargain rolls: each point above neutral lowers the son's roll by `talk_will/100`. |
| endurance | wake_endurance | Wakes faster after defeat: each point above neutral shortens by `wake_endurance/100` epochs. |
| agility | attack_agility | Hostile: chance to steal worshippers or destroy temples +`attack_agility/100` points per point. |
| wisdom | help_wisdom | Friendly: chance to help its worshippers. |
| cunning | steal_cunning | Chance to convert sons' worshippers. |
| charisma | attract_charisma | Chance to attract unowned communities on its world. |
| creativity | prosperity_creativity | Friendly: prosperity it adds to its worshippers. |
| might | power_faith_might | Lowers the faith threshold to grow in power. |

- `war_power(god)` (`ytSavasGucu`, no dice) = `power × (100 − war_stat_share)/100 + (strength + will)/2 ×
  war_stat_share/100 + (has shield power ? power_shield : 0)`.
- Seeded stats (`statZarla(seed)`): seed = `"{name}:{world_id}:{created_epoch}"`; hash: `a = 0; for each code point c:
  a = (a·31 + c) mod 2^32`; generator mulberry32: `a = (a + 0x6D2B79F5) mod 2^32; t = a; t = imul(t ^ (t>>>15), t|1);
  t ^= t + imul(t ^ (t>>>7), t|61); return ((t ^ (t>>>14)) >>> 0) / 2^32`. Each stat in SON_STATS order =
  `clamp(round(stat_base + r() × stat_die), 1, 100)`.
- `stats_of(god)` = parsed stats or seeded stats if missing.
- `clean_stats(s, old)` = each stat a finite number clamped 1–100 (rounded), else old value or neutral.

### 7.3 Powers (`YT_GUC_ETKILERI`) — a god's `powers` = list `{name, effect, description}`; only known effects kept
| effect key | name | rule | description |
|---|---|---|---|
| shield (`kalkan`) | Shield | power_shield | +N to war power in battle. |
| caller (`cagiran`) | Caller | power_attract | +N% chance to attract unowned communities. |
| thief (`hirsiz`) | Worshipper-thief | power_steal | +N% chance to steal sons' worshippers. |
| destroyer (`yikici`) | Destroyer | power_destroy | +N% hostile attack chance. |
| fertile (`bereketli`) | Bountiful | power_bounty | Friendly prosperity contribution × N/100. |
| reviving (`dirilen`) | Reviving | power_revive | Wake time after defeat becomes N%. |
| deathless (`olumsuz`) | Deathless | — | Never dies even in a crushing defeat; only defeated. |
| sharp_tongued (`sozu_keskin`) | Persuasive | power_word | A son talking to it gets −N on the roll. |

Personality fields (`YT_KISILIK`): appearance, temperament, obsession, fear, speech style, secret. Existence fields
(`YT_VAROLUS`): nature, state (∈ `VAROLUS_HALLERI` = concrete, semi-concrete, conceptual, reflection, scattered),
manifestation, true name. Depth text fields (`YT_DERIN_METIN`): history, what it really wants, view of the pantheon, how
it is worshipped, hidden truth. These are written by the foreign-god deepening LLM call (agents spec, uses
`YT.guc_sayi` powers and `YT.derin_kronik` chronicle lines).

Cleaners: `clean_powers` (array or `{0:…,1:…}` form → valid entries), `clean_texts(o, fields)`, `clean_existence` (drops
unknown state), `unwrap_text(x)` (`metinAc`: the model sometimes embeds JSON in text fields: arrays → paragraphs joined
by blank lines, objects → their string values).

Startup repairs (idempotent): `fill_statless()` gives seeded stats to gods with none; `repair_depth()` unwraps
embedded-JSON depth texts; a depth with empty history is reset to null (so it gets re-deepened).

### 7.4 Tunables `YABANCI` — group "Foreign gods"
| old key | new key | default | min | max | label |
|---|---|---|---|---|---|
| stat_taban | stat_base | 35 | 1 | 100 | Base of each stat of a new foreign god |
| stat_zar | stat_die | 45 | 0 | 100 | Die (continuous `r()×die`) added to each stat |
| stat_notr | stat_neutral | 50 | 0 | 100 | Neutral stat: above helps, below hurts |
| savas_stat_pay | war_stat_share_pct | 50 | 0 | 100 | Share of (Strength+Will)/2 in war power (%); rest is general power |
| konusma_irade | talk_will_rate | 30 | 0 | 500 | Will's resistance in talks with sons: (Will − neutral) × rate/100 off the son's roll |
| cekim_karizma | attract_charisma_rate | 20 | 0 | 500 | Charisma's contribution to attracting worshippers (% points) |
| calma_kurnazlik | steal_cunning_rate | 20 | 0 | 500 | Cunning's contribution to stealing worshippers (% points) |
| saldiri_ceviklik | attack_agility_rate | 20 | 0 | 500 | Agility's contribution to hostile actions (% points) |
| yardim_bilgelik | help_wisdom_rate | 20 | 0 | 500 | Wisdom's contribution to friendly help (% points) |
| refah_yaraticilik | prosperity_creativity_rate | 10 | 0 | 500 | Creativity's effect on friendly prosperity |
| uyanis_dayaniklilik | wake_endurance_rate | 10 | 0 | 500 | Endurance shortens wake time after defeat (epochs) |
| guc_inanc_kudret | power_faith_might_rate | 20 | 0 | 500 | Might lowers the faith threshold for growing |
| guc_sayi | powers_count | 2 | 0 | 20 | Powers given in deepening |
| guc_kalkan | power_shield | 15 | 0 | 500 | Shield: added to war power |
| guc_cekim | power_attract_pct | 15 | 0 | 100 | Caller: attraction chance (%) |
| guc_hirsiz | power_steal_pct | 15 | 0 | 100 | Thief: stealing chance (%) |
| guc_yikici | power_destroy_pct | 15 | 0 | 100 | Destroyer: hostile action chance (%) |
| guc_bereket | power_bounty_pct | 200 | 100 | 10000 | Bountiful: friendly prosperity multiplier (%) |
| guc_dirilis | power_revive_pct | 50 | 1 | 100 | Reviving: wake time percentage |
| guc_soz | power_word | 15 | 0 | 500 | Persuasive: subtracted from the talking son's roll |
| derin_kronik | deepen_chronicle_lines | 40 | 0 | 10000 | Chronicle lines naming the god given to the model when deepening |

Cross refs: used by `panteon` (all mechanics), `tools` (son talk tools use `talk_will`, `power_word`, war power),
`agents` (deepening), `kitap` (codex), `oyuncu` (manual edit), `olumluler` (mortal preaching vs foreign god charisma).

---

## 8. Cosmic horror (`src/korku.js`)

### 8.1 Purpose
Per-world **leak** (something from outside seeping in), **sanity** of communities and mortals, forbidden knowledge
effects, **Outer Beings** (no agent loop; run by the engine and Fate so they stay mysterious; their names are never
spoken), horror events, and doom-as-a-calling.

### 8.2 Tunables `KORKU` — group "Cosmic horror" unless noted
| old key | new key | default | min | max | label |
|---|---|---|---|---|---|
| dizilim_tehlike | alignment_danger | 15 | 0 | 100 | Route danger rise when the stars align |
| kiyamet_sizinti | doom_leak | 4 | 0 | 50 | Doom's leak contribution at threshold (per epoch, scaled by doom/threshold) |
| korku_olay_bolen | horror_event_divisor | 250 | 10 | 10000 | Horror event probability: leak / this |
| genc_tavan | young_cap | 25 | 0 | 100 | Initial leak cap in a young world |
| genc_tavan_artis | young_cap_growth | 8 | 0 | 100 | Young world's leak cap growth per epoch of age |
| onarim_esik | self_repair_threshold | 30 | 0 | 100 | Leak above which the fabric starts repairing itself |
| onarim_bolen | self_repair_divisor | 8 | 1 | 100 | Repair: −1 per this many points above the threshold |
| dis_varlik_esik | outer_threshold | 85 | 1 | 100 | Leak at which an Outer Being appears |
| cagri_esik | calling_threshold | 50 | 0 | 100 | Average leak at which doom becomes a calling (group Doom) |
| delilik_sans | madness_pct | 30 | 0 | 100 | Madness event on a community with collapsed sanity (%) |
| fisildayan_sans | whisperers_pct | 50 | 0 | 100 | Madness becomes an outer cult (%) |
| dis_varlik_sans | outer_appear_pct | 40 | 0 | 100 | An Outer Being appears once the threshold is passed (%) |
| yasak_sizinti | forbidden_leak | 4 | 0 | 50 | Leak per community knowing forbidden knowledge |
| kapi_sizinti | gate_leak | 2 | 0 | 50 | Leak per open gate, swallowing or dream route |
| olu_yildiz_sizinti | dead_star_leak | 3 | 0 | 50 | Leak from a dead, black or broken star |
| tanrisiz_sizinti | godless_leak | 1 | 0 | 50 | Leak per godless community |
| bagimli_sizinti | addicted_leak | 2 | 0 | 50 | Leak per addicted community |
| dis_tarikat_sizinti | outer_cult_leak | 3 | 0 | 50 | Leak per outer cult |
| dis_varlik_sizinti | outer_being_leak | 5 | 0 | 50 | Leak per Outer Being |
| tapinan_onarim | worship_repair_pct | 50 | 0 | 1000 | Repair per worshipping community (percentage points; total capped by worship_cap) |
| tapinan_tavan | worship_cap | 5 | 0 | 100 | Cap on repair from the number of worshipping communities (the rest comes from the worshipping ratio) |
| rahip_tavan | priest_cap | 3 | 0 | 100 | Cap on repair from priest-strong communities (1 each) |
| tapinan_oran_onarim | worship_ratio_repair | 3 | 0 | 50 | Repair from the worshipping ratio (if all worship) |
| tapinak_tavan | temple_cap | 3 | 0 | 50 | Max repair from temples (1 per temple) |
| rahip_esik | priest_min_share_pct | 10 | 0 | 100 | Min priest class share for repair (%) |
| doku_onarim | fabric_repair | 1 | 0 | 50 | Fabric's spontaneous repair per epoch |
| onarim_tam | maintenance_full_at | 25 | 1 | 100 | Worship/temple/priest repair reaches full power at this leak; below, it scales with leak (untorn fabric is not repaired) |
| genc_carpan | young_multiplier_pct | 50 | 0 | 100 | Remaining share of leak increase in a young world (%) |
| uyari1 | warning1 | 30 | 0 | 100 | Leak of the first warning |
| uyari2 | warning2 | 60 | 0 | 100 | Leak of the "geometry breaks" warning |
| sagduyu_varsayilan | sanity_default | 70 | 0 | 100 | Sanity assumed when none written |
| sizinti_asinma_bolen | leak_erosion_divisor | 20 | 1 | 1000 | Sanity erosion: leak / this |
| yasak_asinma | forbidden_erosion | 6 | 0 | 100 | Sanity loss per epoch for forbidden-knowledge knowers |
| dis_asinma | outer_erosion | 4 | 0 | 100 | Sanity loss per epoch in a world with an Outer Being |
| tip_onarim | medicine_repair | 3 | 0 | 100 | Sanity repair for medicine knowers |
| rahip_onarim_bolen | priest_repair_divisor | 5 | 1 | 100 | Sanity repair: priest share / this |
| tapar_onarim | worship_sanity_repair | 1 | 0 | 100 | Sanity repair for a worshipper of a god |
| sagduyu_onarim | sanity_self_repair | 1 | 0 | 100 | Spontaneous sanity repair per epoch |
| bulaniklik_esik | clouding_threshold | 40 | 0 | 100 | Sanity where the mind begins to cloud |
| delilik_esik | madness_threshold | 20 | 0 | 100 | Sanity where madness begins |
| delilik_kayip | madness_population_loss_pct | 6 | 0 | 100 | Population lost in a madness epidemic (%) |
| fisildayan_guc | whisperers_level | 3 | 1 | 12 | Whisperers cult power level |
| fisildayan_murit_en_az | whisperers_min_followers | 50 | 1 | 100000 | Whisperers' min followers |
| fisildayan_nufus_varsayilan | whisperers_population_default | 1000 | 1 | 1000000 | Population assumed for a people with none (Whisperers) |
| fisildayan_pay | whisperers_share_pct | 5 | 0 | 100 | Share of the people that becomes Whisperers (%) |
| fisildayan_bagnazlik | whisperers_fanaticism | 85 | 0 | 100 | Whisperers' fanaticism |
| fisildayan_etki | whisperers_influence | 40 | 0 | 100 | Whisperers' influence |
| fisildayan_sagduyu | whisperers_sanity | 10 | 0 | 100 | Whisperers' sanity |
| delilik_oz_bolen | madness_son_essence_divisor | 15 | 1 | 1000 | Madness-domain son's per-epoch essence: average leak / this |
| delilik_varlik | madness_son_existence | 1 | 0 | 100 | Madness-domain son's per-epoch existence gain |
| varlik_varsayilan | son_existence_default | 60 | 0 | 100 | Existence assumed for a son with none written |
| dis_guc | outer_level | 10 | 1 | 12 | Outer Being power level |
| dis_buyukluk / _zar | outer_size_base / _die | 60 / 40 | 0/1 | 100 | Outer Being size |
| dis_ilgi / _zar | outer_interest_base / _die | 30 / 40 | 0/1 | 100 | Outer Being interest |
| dis_etki / _zar | outer_influence_base / _die | 50 / 50 | 0/1 | 100 | Outer Being influence |
| dis_sizinti_dusus | outer_entry_leak_drop | 20 | 0 | 100 | Leak drop when an Outer Being enters |
| ilgi_varsayilan | interest_default | 40 | 0 | 100 | Interest assumed for an Outer Being with none |
| ilgi_zar | interest_die | 11 | 1 | 100 | Per-epoch interest die of an Outer Being |
| ilgi_dusus | interest_decay | 4 | 0 | 100 | Subtracted from interest each epoch |
| dis_kurban | outer_victims | 3 | 0 | 100 | Neighbours whose sanity an Outer Being gnaws each epoch |
| dis_sagduyu_bolen | outer_sanity_divisor | 10 | 1 | 1000 | Neighbour sanity loss: interest / this |
| dis_mutasyon_bolen | outer_mutation_divisor | 300 | 1 | 100000 | Neighbour species mutation chance: interest / this |
| kiyamet_olay_bolen | doom_event_divisor | 6 | 1 | 1000 | Doom's contribution to horror event chance: (clock / threshold) / this |
| dizilim_sizinti | alignment_leak | 8 | 0 | 100 | Every world's leak rise when the stars align |
| goz_sagduyu | eye_sanity | 10 | 0 | 100 | Sanity taken by the Eye in the sky |
| sessizlik_pay | silence_share_pct | 20 | 0 | 100 | Share of words forgotten in a wave of silence (%) |
| ters_yagmur_ruh | reverse_rain_souls | 4 | 0 | 100 | Max souls rising in reverse rain |
| bosluk_bolge_esik | void_min_regions | 5 | 1 | 1000 | Min regions a world needs before the Void can swallow a region |

External: `MOTOR.genc_dunya` young_world_epochs = 6 (0–50, "Young world duration (epochs; leak increase halved)") in
`derin.js`; `DENGE.kiyamet_esik` doom threshold.

### 8.3 Leak change (`leak_delta(world_id)`, old `sizintiDegisimi`) — also records a breakdown for the epoch report
Over canon entities `ts` of the world:
- Sources: `forbiddenKnowers` (count knowing `forbidden`) × forbidden_leak; `gates` = active routes of method
  gate/swallowing/dream touching the world × gate_leak; `deadStar` = dead_star_leak if the world's star type matches
  `/dead|black|broken/` (Turkish `/ölü|kara|kırık/`); `godless` tagged × godless_leak; `addicted` (any tag `addicted:*`)
  × addicted_leak; `outerCults` × outer_cult_leak; `outerBeings` (type `dis`) × outer_being_leak; `doom` =
  `cosmos.doom / doom_threshold × doom_leak`.
- `increase = sum of sources`.
- Maintenance (only repairs torn fabric): `m = min(1, leak / maintenance_full_at)`.
  - `worshipping` = communities (people/settlement/faction/cult) with an active `worships` bond to a son or the creator;
    `communities` = their total count.
  - `worshipRepair = (min(worship_cap, worshipping × worship_repair_pct/100) + (communities ? worshipping/communities : 0) ×
    worship_ratio_repair) × m`.
  - `temples` = canon works whose name+subtype matches `/temple|shrine|altar/` (`/tapınak|mabet|sunak/i`);
    `templeRepair = min(temple_cap, temples) × m`.
  - `priests` = min(priest_cap, people/settlements whose priest class share ≥ priest_min_share_pct); `priestRepair = priests × m`.
- `decrease = worshipRepair + templeRepair + priestRepair + fabric_repair + max(0, (leak − self_repair_threshold)/self_repair_divisor)`.
- Young world: `age = epoch − (created_epoch || 1) < young_world_epochs` → `k = young_multiplier_pct/100` else 1.
- Result `round(increase × k − decrease)`. Breakdown items (rounded 0.1, zero items dropped): forbidden knowledge, gates,
  star, godless, addicted, outer cults, outer beings, doom (all × k), worshippers, temples, priests, fabric repair
  (negative); plus a marker "young world (increase halved)". Stored in `leak_breakdown[world]` for the epoch report.
- **Young-world cap** `leak_cap(world, epoch)`: if age < young_world_epochs → `min(100, max(young_cap, young_cap +
  young_cap_growth × age))` else 100.

### 8.4 Horror engine (`horror_engine(epoch, note)`, old `korkuMotoru`)
1. Routes with `severed_until ≤ epoch` (neither end forgotten) → active, clear; note "The route severed by the void was
   stitched again (route#{id})."
2. Routes with `temp_until ≤ epoch` → active=0, clear temp_until **and** severed_until (an alignment-opened route that a
   storm severed meanwhile re-seals); note "The gate opened by the alignment closed again (route#{id})."
3. Leak per world (all worlds, including forgotten): `cap = leak_cap`, `raw = clamp(leak + leak_delta, 0, 100)`;
   `new = leak > cap ? min(raw, leak) : min(raw, cap)` (above-cap young worlds can only fall). Save. Threshold crossing
   notes (from below to ≥): warning1 "Something is leaking into {W}: nights are a moment too long, shadows a step
   behind. The peoples began to dream the same dream."; warning2 "{W}'s geometry is breaking: some valleys are bigger
   inside, some roads turn back onto themselves."; outer_threshold "A tear opened in {W}'s sky. Something outside is
   looking in."
4. Sanity, for every canon people/settlement/mortal/cult/faction: `s0 = sanity ?? sanity_default`;
   `erosion = world.leak/leak_erosion_divisor + (knows forbidden ? forbidden_erosion : 0) + (an Outer Being is in its
   world ? outer_erosion : 0)`; `repair = (knows medicine ? medicine_repair : 0) + (people/settlement ? priest_share /
   priest_repair_divisor : 0) + (has any worships bond ? worship_sanity_repair : 0) + sanity_self_repair`;
   `s1 = clamp(round(s0 − erosion + repair), 0, 100)`; save if changed.
   - Crossing below clouding_threshold → note "{v}'s mind is clouding: at night they speak in a language no one understands."
   - If `s1 < madness_threshold` and `chance(madness_pct)`:
     - If people/settlement, not itself an outer cult, has not already birthed whisperers (tag `whisper source`, or a
       living outer cult bonded `related` "born from within" to it), and `chance(whisperers_pct)`: tag `whisper
       source`; `open_record({type: cult, subtype: "cult of the unspoken", name: "{v} Whisperers", power:
       whisperers_level, location: settlement ? v : v.location, tags: ['outer cult'], stats: {followers: max(min,
       round((population || default) × share/100)), fanaticism, influence, sanity}, description: "[World engine] Among
       {v} a cult arose worshipping something whose name is not spoken; they pray not to the gods but to the outside."})`;
       bond cult `related` v ("born from within"); note.
     - Else if it has population: population ×= (100 − madness_population_loss_pct)/100 (clamped); note "Madness epidemic
       in {v}: people burned their homes and walked into the desert."
5. Madness-domain sons (domains ∈ Madness, Nightmare, Dream, Void, Secret, Lie, Sleep, Shadow — `Delilik, Kâbus, Rüya,
   Boşluk, Sır, Yalan, Uyku, Gölge`): `avg_leak` over all worlds; `gain = round(avg/madness_son_essence_divisor)`; if
   gain: essence += gain, existence = clamp((existence ?? default) + madness_son_existence). (Comment says death-domain
   sons are repelled by Outer Beings — not implemented.)
6. Outer Being appearance: for each world with leak ≥ outer_threshold, with no canon Outer Being, `chance(outer_appear_pct)`:
   region = most dangerous region of the world (none → skip); `open_record({type: outer (dis), subtype: "the unnamed",
   name: "The Unspoken ({W})", power: outer_level, location: region, tags: ['nameless','name-from-language'] (the second
   tag prevents automatic renaming), stats: {size, interest, influence} rolled, description: "[World engine] Something
   came in through the tear in {W}'s sky. It cannot be fully seen; those who look remember only what they could not
   see."})`; world leak −= outer_entry_leak_drop; chronicle `outer (dis)`: "Something entered {W} from outside. No one
   speaks its name."; note.
7. Outer Being influence, each canon Outer Being: `interest = clamp((interest || default) + d(interest_die) −
   interest_decay)`; first `outer_victims` people/settlement/species sharing its location: sanity −= round(interest /
   outer_sanity_divisor); species: `chance(interest/outer_mutation_divisor)` → tag `mutation`. Every outer cult of its
   world gets a `worships` bond to it ("without speaking its name") if missing.
8. `horror_events(epoch, note, worlds)` (§8.5).

### 8.5 Horror events (Ö-20) — at most one per epoch
`W` = world with the highest leak (sorted in place). `p = W.leak/horror_event_divisor + (doom/doom_threshold)/doom_event_divisor`.
If `chance(p)`, choose uniformly among:
- **Stars aligned** (`dizilis`): `open_alignment(epoch, ['gate','slingshot'], {danger_add: alignment_danger})`; every
  world leak += alignment_leak; chronicle `horror (korku)`: "The stars aligned: all gates opened at once and all worlds
  looked into the same darkness for a moment."; note "The stars aligned: all gates opened at once."
- **Eye in the sky** (`goz`): entities of W with a sanity stat, or people/settlement/mortal of W: sanity −= eye_sanity;
  chronicle "An eye stayed open in {W}'s sky for a whole epoch. Nobody looked at it; but everyone knew they were being
  watched."
- **Wave of silence** (`sessizlik`): for each canon language of W, delete a random `floor(n × silence_share_pct/100)` of
  its lexicon rows; chronicle "A wave of silence passed through {W}: {k} words were forgotten; people looked at things
  and could not remember their names."
- **Reverse rain** (`ters_yagmur`): first `reverse_rain_souls` canon souls of W are killed ("rose to the sky with the
  reverse rain"); chronicle "Reverse rain fell on {W}: the dead rose to the sky[; {names} are no longer here]."
- **Visit of the Void** (`bosluk`): candidate = entity of W that is a place, or a region if W has ≥ void_min_regions
  regions, and whose whole subtree (recursive by location) contains no people/settlement/cult/faction/mortal; prefer
  places. If none → nothing. Kill it and its whole canon subtree with status `destroyed`; tag `void`; chronicle "The Void
  visited {W}: {X} was erased from the map. In its place is a nothingness that tires the eye to look at."; note.

### 8.6 Doom as a calling (`doom_calling(epoch)`, old `kiyametCagri`)
Called at epoch transition when the doom clock reaches its threshold. If the average leak over all worlds <
calling_threshold → return false (normal apocalypse proceeds on the leakiest world, other spec). Else the leakiest world's
leak = 100; chronicle `doom (kiyamet)`: "DOOM BECAME A CALLING: {W}'s sky opened and the things outside were called by
their names. The world was not destroyed; but it is no longer alone." → true; the caller resets the clock to
`threshold × KIYAMET.cagri_sonrasi/100`.

### 8.7 Cross-module calls
Uses `mudahale.bilir`, `derin.kayitAc, etiketEkle, toplumOf (classes: priest share), kanonlar, oldur, MOTOR`,
`gok.dizilimAc`, `world.allSons, saveSon, addKronik`. Used by `sim` (engine, `kiyametCagri`, `sizintiDokumu` for the
epoch report), `gok`/`yaratik`/`olumluler` (`sagduyu`). Outer Beings are also referenced by `panteon` (gnawing,
bargains, cleansing) and quests.

---

## 9. Creatures and abominations (`src/yaratik.js`)

### 9.1 Purpose
Traits, mutation (species and peoples), hybrids and chimeras, cosmic megafauna, ecology (predator–prey, extinction,
danger mean-reversion, invasive species), taming/mounts' war contribution, stowaways carried between worlds.

### 9.2 Traits
- `traits_of(v)` = keys from tags `trait:<k>` that exist in the trait table (§1.9.7). `trait_war(v)` = sum of trait war
  bonuses (used in military power and monster combat).
- **`assign_traits(species)`** (`ozellikAta`): skip if it already has any trait. Text = name + subtype + description;
  keyword hints (regex, case-insensitive; LANGUAGE-SPECIFIC Turkish stems → replace with English keyword lists):
  | trait | Turkish stems (meaning) |
  |---|---|
  | flying | kanat, uçar, uçan, gök, kuş, süzül (wing, flies, flying, sky, bird, glide) |
  | venomous | zehir, iğne, diken, ağı (venom, needle/stinger, thorn, poison) |
  | soul_eater | ruh, can yiyen, gölge yiyen (soul, life-eater, shadow-eater) |
  | light_emitting | ışık, parıl, ışıl, yanar (light, glitter, shining, burning) |
  | splitting | bölün, çoğal, sürü halinde, tomurcuk (split, multiply, in swarms, bud) |
  | swarm_mind | sürü, koloni, kovan (swarm/herd, colony, hive) |
  | stone_skinned | taş, kabuk, zırh, pul (stone, shell, armour, scale) |
  | time_rewinding | zaman, geri sar, tekrar doğ (time, rewind, reborn) |
  | shapeshifter | şekil, kılık, taklit, ayna (shape, guise, mimic, mirror) |
  | mind_reader | akıl, zihin, düşünce okur, fısıltı (mind, intellect, reads thoughts, whisper) |
  Matches deduplicated, first `traits_max_from_text`; none → one uniformly random trait. Tag them. If swarm_mind:
  intelligence += swarm_intelligence.

### 9.3 Creature engine (`creature_engine(epoch, note)`, old `yaratikMotoru`) — order matters
1. `assign_traits` for every canon species.
2. Trait effects per species (`location` = its location entity):
   - light_emitting: location danger −= light_danger, fertility += light_fertility (if those stats exist).
   - soul_eater: first canon soul at the same location; `chance(soul_eater_pct)` → kill soul ("Epoch N: {species}
     swallowed it."); note "{species} swallowed {soul}; in those lands no dead return anymore."
   - mind_reader or soul_eater: up to `mind_reader_victims` people/settlement/mortal at that location: sanity −= mind_reader_sanity.
   - splitting: `chance(split_pct)` → danger += split_danger.
3. **Species mutation**, at most `mutations_max_per_epoch`: for canon species not tagged `mutated`:
   `p = world.leak/mutation_leak_divisor + (tag mutation ? mutation_tag_pct/100 : 0) + (tag cursed ? mutation_curse_pct/100
   : 0) + (has might stat ? mutation_might_pct/100 : 0)`. On `chance(p)`: new trait = random trait not yet owned;
   stats copy with strength/agility/intelligence/danger each `+ d(mutation_die) − mutation_shift` (clamp);
   `open_record({type: species, subtype: mutant, name: "{species} Corruption" (`Bozuntusu`), power, location, stats,
   tags: ['mutant', ...old traits, new trait], description: "[World engine] {species} changed {under the influence of
   what leaked in from outside (if leak ≥ mutation_leak_text) | under the influence of curse and magic}; a new form was
   born[: {new trait name}]."})`; bond mutant `descends_from` species ("mutation"); tag original `mutated`; note
   "{species} mutated; a new form was born."
4. **People mutation** — first people (canon, sanity < people_mutation_sanity, not `mutated`) passing
   `chance(people_mutation_pct)` (only one per epoch: `break` after success): `open_record({type: people, subtype:
   "changed people", name: "{people} Changed Ones", power, location, tags: ['mutant'], stats: {population: round((pop ||
   default) × share/100), warlike: clamp((w || default) + changed_warlike), magic: clamp((m || default) + changed_magic),
   craft: changed_craft, piety: changed_piety, sanity: changed_sanity}, description: "[World engine] A branch whose
   bodies and language changed split from {people}; they now consider themselves another people."})`; original
   population ×= (100 − share)/100; tag `mutated`; bond `descends_from` ("mutation"); note.
5. **Natural hybridization**: species pairs with a location, same location, `chance(hybrid_pct)` per pair, not already
   having a common child (an entity with `descends_from` both): `merge_species(a, b, {name: "{a first word} {b first
   word} Hybrid", description: "[World engine] {a} and {b} mixed over generations in the same lands and bore a
   hybrid."})`; set subtype `hybrid`; note "{a} and {b} hybridized." — at most one per epoch (loops exit).
6. **Spontaneous chimera weaving** (`merged_weaving`, no-LLM path): candidate search first — canon
   people/settlement/faction/cult/mortal knowing `biomancy`; nearby species (same world, distance ≤
   `species_merge_distance`, not megafauna) sorted by distance, id; first pair without a common child. If a candidate
   and `chance(species_merge_chance)`: `merge_species(A, B, {weaver: v, description: "[World engine] {v} joined {A} and
   {B} with biomancy and wove a chimera."})`; bond weaver `tamed` chimera ("its own weaving"); chronicle `chimera
   (kimera)`: "{v} wove a chimera from {A} and {B}: {chimera}."; note.
7. **Chimera escape**: chimeras (tag chimera, not `escaped`) with an active `produced` bond from a weaver:
   `chance((danger || merged_danger_default)/merged_escape_divisor)` → tag `escaped`; if weaver canon: bond chimera
   `hunts` weaver ("escaped and returned"), weaver population and followers ×= (100 − merged_escape_loss)/100 (clamp
   1..cap); note "{chimera} got out of control and turned on those who wove it."
8. **Megafauna**: canon species with power ≥ megafauna_level or tag megafauna: add tag if missing (note "{m} grew so
   large it is now as old and big as a world itself: a megafauna."). `chance(megafauna_trail_pct)` with a location →
   `open_record({type: resource, subtype: "trail resource", name: "{m} Trail", power: trail_level, location, stats:
   {abundance: trail_abundance, value: base+d, might: base+d}, tags: cosmos has a cosmic resource ? ['cosmic
   resource','mechanic:addiction'] : ['mechanic:decays'], description: "[World engine] The ground changed where {m}
   passed; a valuable and strange trail remained."})`; note. (Design: "killing a megafauna changes the age" — handled in
   the hero/monster engine, which adds `megafauna_power` in monster combat.)
9. **Predator–prey bond** (≤ `prey_bonds_max_per_epoch`): for each canon species `y` without an existing `hunts` bond to
   a species: candidate prey = other species in the same top region (or location) and world, with `y.danger ≥
   a.danger + prey_danger_gap`, `y.strength ≥ a.strength`, not megafauna; choose lowest danger. `chance(prey_bond_pct)`
   → bond `y hunts a` ("predator and prey"); note "{y} began hunting the herds of {a}."
10. **Predation pressure**: for every active species→species `hunts` bond with both canon: if `y.danger − a.danger ≥
    prey_extinction_gap` and `a.power ≤ prey_extinction_max_level` and `chance(prey_extinction_pct)` → kill prey
    ("Epoch N: {y} consumed it."); note "{a} became extinct as {y}'s prey."
11. **Danger mean reversion**: species (not megafauna) with danger > `danger_revert_threshold`: danger −= max(1,
    round((danger − danger_revert_mean)/danger_revert_divisor)).
12. **Starving predator**: active hunts bonds where the predator is canon and the prey species is no longer canon →
    deactivate bond; predator danger = clamp((danger || species_danger_default) + starving_predator_danger); note "{a}
    went extinct; {y}, which hunted it, starved and turned on the settlements."
13. **Invasive species**: each canon species tagged invasive lowers its location's fertility by invasive_fertility.

### 9.4 Chimera (`merge_species(a, b, {epoch, name, weaver, description})`, old `kimeraDok`) — also used by son tool `kimera_dok` and mortal tools
- `stat(k) = clamp(round(((a.k || merged_stat_default) + (b.k || merged_stat_default))/2 + d(merged_die) −
  merged_shift), 0, k == hp ? merged_hp_cap : 100)`.
- Traits = union of both, first `merged_traits_max`.
- `open_record({type: species, subtype: chimera, name: name || "{a first word}-{b first word}", power: max(a.power,
  b.power), location: a.location || b.location, stats: {hp, strength, agility, intelligence, danger: clamp(stat(danger)
  + merged_danger)}, tags: ['chimera', ...traits], description: description || "[World engine] A chimera woven by
  combining {a} and {b}."})`; bonds chimera `descends_from` a and b ("chimera"); weaver `produced` chimera ("wove a chimera").

### 9.5 Tamed creatures' war power (`tamed_power(v)`, old `evcilGucu`) — read by `sim.askeriGuc`
Sum over active `tamed` bonds from v to canon creatures: `tamed_base + round((strength || tamed_strength_default) /
tamed_strength_divisor) + trait_war(t) × tamed_trait_share_pct/100`.

### 9.6 Stowaways (`stowaway(origin_world, target_region, epoch)`, old `kacakYolcu`) — called on arrival
Candidates: canon species of the origin world with danger < `stowaway_danger_max`. None or `!chance(stowaway_pct)` →
null. Pick uniform; `open_record({type: species, subtype: "invasive species", name: "{t} (stowaway)", power, location:
target region, stats: copy, tags: ['invasive', ...traits], description: "[World engine] {t} was carried to another world
in ships' holds and became a non-native invader there."})`; bond `descends_from` ("stowaway").

### 9.7 Tunables `YARATIK` — group "Creatures"
| old key | new key | default | min | max | label |
|---|---|---|---|---|---|
| ruh_yiyen_sans | soul_eater_pct | 30 | 0 | 100 | Soul-eater swallows a soul (%) |
| bolunme_sans | split_pct | 10 | 0 | 100 | Splitting species grows stronger (%) |
| halk_mutasyon_sans | people_mutation_pct | 15 | 0 | 100 | A changed branch splits from a low-sanity people (%) |
| melez_sans | hybrid_pct | 3 | 0 | 100 | Species on the same land hybridize (%) |
| megafauna_iz_sans | megafauna_trail_pct | 12 | 0 | 100 | A resource forms on a megafauna's trail (%) |
| av_bag_sans | prey_bond_pct | 25 | 0 | 100 | A predator–prey relation forms (%) |
| av_tukenme_sans | prey_extinction_pct | 4 | 0 | 100 | A strong predator exhausts its prey (%) |
| kacak_sans | stowaway_pct | 30 | 0 | 100 | A species stows away on ships (%) |
| ozellik_tavan | traits_max_from_text | 2 | 1 | 10 | Max traits given to a species from its description |
| suru_zeka | swarm_intelligence | 15 | 0 | 100 | Swarm-minded species' intelligence gain |
| kimera_stat_varsayilan | merged_stat_default | 40 | 0 | 100 | Default value of an unwritten stat in a chimera |
| kimera_zar | merged_die | 21 | 1 | 100 | Chimera stat die (1…n) |
| kimera_kayma | merged_shift | 6 | 0 | 100 | Subtracted from the chimera stat die |
| kimera_can_tavan | merged_hp_cap | 1000 | 1 | 100000 | Chimera max HP |
| kimera_ozellik_tavan | merged_traits_max | 3 | 0 | 10 | Max traits a chimera can carry |
| kimera_tehlike | merged_danger | 10 | 0 | 100 | Chimera extra danger |
| kimera_dokuma_sans | species_merge_chance | 6 | 0 | 100 | A biomancy-knowing community/mortal spontaneously weaves a chimera (per epoch %) |
| kimera_dokuma_mesafe | species_merge_distance | 4 | 0 | 99 | Max distance (steps) from the weaver to the species |
| isik_tehlike | light_danger | 2 | 0 | 100 | Light-emitting species lowers region danger (per epoch) |
| isik_bereket | light_fertility | 2 | 0 | 100 | Light-emitting species raises region fertility (per epoch) |
| akil_okuyan_tavan | mind_reader_victims | 3 | 0 | 100 | Max neighbours whose sanity a mind-reader or soul-eater gnaws |
| akil_okuyan_sagduyu | mind_reader_sanity | 3 | 0 | 100 | Their sanity loss |
| bolunme_tehlike | split_danger | 5 | 0 | 100 | Splitting species' danger gain |
| mutasyon_tavan | mutations_max_per_epoch | 1 | 0 | 100 | Max species mutations per epoch |
| mutasyon_sizinti_bolen | mutation_leak_divisor | 400 | 1 | 100000 | Mutation chance: world leak / this |
| mutasyon_etiket | mutation_tag_pct | 25 | 0 | 100 | Extra mutation chance for species tagged mutation (%) |
| mutasyon_lanet | mutation_curse_pct | 8 | 0 | 100 | Extra chance for cursed species (%) |
| mutasyon_kudret | mutation_might_pct | 2 | 0 | 100 | Extra chance for species with might (%) |
| mutasyon_zar | mutation_die | 41 | 1 | 100 | Mutant stat change die (1…n) |
| mutasyon_kayma | mutation_shift | 15 | 0 | 100 | Subtracted from the mutant stat die |
| mutasyon_sizinti_metin | mutation_leak_text | 40 | 0 | 100 | World leak at which the mutation text blames the leak |
| halk_mutasyon_sagduyu | people_mutation_sanity | 30 | 0 | 100 | Below this sanity a changed branch may split from a people |
| halk_mutasyon_pay | people_mutation_share_pct | 20 | 0 | 100 | Population share moving to the changed branch (%) |
| degismis_savascilik | changed_warlike | 15 | 0 | 100 | Changed people's warlikeness gain |
| degismis_buyu | changed_magic | 20 | 0 | 100 | Changed people's magic gain |
| degismis_zanaat | changed_craft | 20 | 0 | 100 | Changed people's craft |
| degismis_inanc | changed_piety | 10 | 0 | 100 | Changed people's piety |
| degismis_sagduyu | changed_sanity | 40 | 0 | 100 | Changed people's sanity |
| halk_savascilik_varsayilan | people_warlike_default | 40 | 0 | 100 | Default warlikeness |
| halk_buyu_varsayilan | people_magic_default | 20 | 0 | 100 | Default magic |
| halk_nufus_varsayilan | people_population_default | 1000 | 1 | 100000000 | Population assumed when splitting a changed branch |
| kimera_tehlike_varsayilan | merged_danger_default | 50 | 0 | 100 | Danger assumed for escape chance |
| kimera_kacis_bolen | merged_escape_divisor | 500 | 1 | 100000 | Chimera escape chance: danger / this |
| kimera_kacis_kayip | merged_escape_loss_pct | 10 | 0 | 100 | Weaver's population loss when its chimera escapes (%) |
| megafauna_seviye | megafauna_level | 8 | 1 | 12 | Min power level counted as megafauna |
| iz_seviye | trail_level | 5 | 1 | 12 | Megafauna trail resource power level |
| iz_bolluk | trail_abundance | 60 | 0 | 100 | Trail abundance |
| iz_deger_taban / _zar | trail_value_base / _die | 70 / 30 | 0/1 | 100 | Trail value |
| iz_kudret_taban / _zar | trail_might_base / _die | 60 / 40 | 0/1 | 100 | Trail might |
| av_bag_tavan | prey_bonds_max_per_epoch | 1 | 0 | 100 | Max new predator–prey bonds per epoch |
| av_tehlike_fark | prey_danger_gap | 10 | 0 | 100 | Predator's min danger advantage over prey |
| av_tukenme_fark | prey_extinction_gap | 30 | 0 | 100 | Min danger advantage to exhaust prey |
| av_tukenme_seviye | prey_extinction_max_level | 4 | 0 | 12 | Max power level of prey that can go extinct |
| tehlike_donus_esik | danger_revert_threshold | 55 | 0 | 100 | Species above this danger revert toward the mean |
| tehlike_donus_orta | danger_revert_mean | 50 | 0 | 100 | Mean species danger reverts to |
| tehlike_donus_bolen | danger_revert_divisor | 12 | 1 | 1000 | Reversion: (danger − mean) / this |
| yirtici_ac_tehlike | starving_predator_danger | 15 | 0 | 100 | Danger gain of a predator whose prey died out |
| tur_tehlike_varsayilan | species_danger_default | 40 | 0 | 100 | Default species danger |
| istilaci_bereket | invasive_fertility | 3 | 0 | 100 | Invasive species lowers its location's fertility (per epoch) |
| evcil_taban | tamed_base | 6 | 0 | 100 | Base war contribution per tamed creature |
| evcil_guc_bolen | tamed_strength_divisor | 15 | 1 | 1000 | Tamed contribution: strength / this |
| evcil_guc_varsayilan | tamed_strength_default | 30 | 0 | 100 | Strength assumed for a tamed creature with none |
| evcil_ozellik_pay | tamed_trait_share_pct | 50 | 0 | 100 | Share of the creature's trait war bonus transferred (%) |
| kacak_tehlike_tavan | stowaway_danger_max | 70 | 0 | 100 | Danger limit (below) for a species to stow away |

### 9.8 Cross-module calls
Uses `derin.kayitAc, etiketEkle, mesafe, kanonlar, oldur`, `olumluler.ustBolge`, `mudahale.bilir`, `korku.sagduyu`.
Used by `sim` (engine; `evcilGucu`, `ozellikSavas` in military power and monster combat), `seyahat` (`kacakYolcu`),
`olumluler`/`tools` (`kimeraDok`). Taming itself (mortal tool `evcillestir`) is in the mortal agents spec.

---

## 10. Civilization scale (`src/medeniyet.js`)

### 10.1 Purpose
Civilization tiers (with hysteresis and minimum dwell), colony independence, interworld federations, previous-creation
ruins, and rule-based interactions that keep the world filling itself without agents: loans (and late repayment),
barter between trade partners, adoption, interworld treaties.

### 10.2 Tiers
- `tier_of(v)` = number in tag `tier:<n>` (default 0).
- Subjects of `v` (`tebaa`): v + entities it governs + entities paying it tribute, **only those in v's world**, unique.
- `base_tier(v)` (`temelBasamak`): `governed` = canon entities v governs; `worlds` = {v.world} ∪ worlds of governed;
  `pop` = v.population + Σ governed population; `old = tier_of(v)`; `thr(e, tier) = e × (old ≥ tier ? stay_factor : 1)`
  where `stay_factor = (100 − tier_drop_share_pct)/100`.
  - city-state if `pop ≥ thr(city_population, CITY)` and known techs ≥ city_knowledge.
  - kingdom if city-state and (governed count ≥ kingdom_governed OR pop ≥ thr(kingdom_population, KINGDOM)) and known
    techs ≥ kingdom_knowledge.
- `political_power(candidates)` (once per engine run, candidates = communities whose base tier ≥ kingdom):
  `region_world` map, `world_population` (people+settlements per world), `subject_population[v]`,
  `strongest[world]` = max subject population among candidates.
- `is_empire(v, political_map, power, stay=1)`: world regions (of v's world) must be ≥ empire_min_regions and settled
  regions (keys of the political map in v's world) non-empty. `ruled` = settled regions whose dominant holder is one of
  v's subjects. Empire if `ruled/settled ≥ empire_region_share/100 × stay`, OR (world population > 0 AND v's subject
  population ≥ strongest × stay AND subject_pop/world_pop ≥ empire_population_share/100 × stay).
  (`political_map` = `kesif.siyasiHarita()`: region → dominant holder; map spec.)
- `compute_tier(v)`: start from base; if ≥ kingdom and `is_empire(stay = old ≥ EMPIRE ? stay_factor : 1)` → EMPIRE; if ≥
  EMPIRE and |worlds| ≥ interstellar_worlds → INTERSTELLAR; if ≥ INTERSTELLAR and |worlds| ≥ cosmic_worlds and
  (owns a cosmic resource deposit OR tag `cosmic monopoly`) → COSMIC. Tiers climb in order (no skipping).

### 10.3 Civilization engine (`civilization_engine`, old `medeniyetMotoru`)
1. **Tiers** for canon people/faction/settlement: compute; if changed:
   - Minimum dwell: `dir = sign(new − old)`; `last_dir = sign(old − stats.tier_previous)` if recorded else `dir`. If
     `stats.tier_epoch` set and `epoch − tier_epoch < tier_min_epochs` and `last_dir ≠ dir` → skip (no reversal within
     the dwell; continuing in the same direction is allowed).
   - Write `tier_epoch = epoch`, `tier_previous = old`; replace tier tag.
   - Rising to ≥ kingdom: note "{v} rose: now a {tier}."; chronicle `civilization (medeniyet)` "{v} became a {tier}.";
     if ≥ empire add tag `empire`. Falling from ≥ kingdom: note "{v} declined: now a {tier}." Falling below empire from
     ≥ empire: remove tag `empire`.
2. **Colony independence**: settlements tagged colony with `epoch − created ≥ colony_min_age`; mother = source of an
   active `governs` bond to it (must be canon). `far = different worlds`. `rel_change(mother, colony, far ?
   −colony_far_cooling : −colony_near_cooling)`. `p = (far ? colony_far_pct : colony_near_pct)/100 + ((prosperity ??
   colony_prosperity_base) − colony_prosperity_base)/colony_prosperity_divisor + (rel(mother, colony) < 0 ?
   colony_grudge_pct/100 : 0)`. On `chance(p)`: deactivate governs; tags colony → independent; `war =
   chance(independence_war_pct) && savasIlan(mother, colony, "war of independence")`; chronicle "{colony} declared its
   independence from {mother}[; a war of independence began | and the motherland had to let it go]."; note.
3. **Federation** — if existing federations < `federation_max`: members already in a federation (active `member_of` or
   `related` bond to a federation) are excluded. Build an alliance graph from active `ally` bonds. For each node:
   members = node + its allies − already members, canon. Need ≥ `federation_min_members`, spanning ≥ `federation_min_worlds`
   worlds, and `chance(federation_pct)` (rolled per node checked). Create `open_record({type: faction, subtype:
   "interworld federation", name: "{first member} Federation", power: federation_level, location: first member's
   location, tags: ['federation'], stats: {power: federation_power, wealth: federation_wealth, influence:
   federation_influence}, description: "[World engine] {members} swore to each other across the worlds and founded a
   federation."})`; each member `member_of` it; chronicle "An interworld federation was founded: {members}."; note; stop
   (one per epoch).
4. `previous_creation(epoch, note)` (§10.5).
5. `ruleless_interactions(epoch, note)` (§10.4).

### 10.4 Rule-based interactions (`modelsizEtkilesimler`) — each finds a candidate first, then rolls; at most one each per epoch
`wealth_key(v)` = `wealth` if present else `prosperity` else none; `wealth(v)`; `transfer(v, delta)` clamps 0–100.
Loan bond description encoding/decoding (`borcAciklama`/`borcOku` in rules): `{amount, what, due, overdue}` —
see economy spec; overdue marked by suffix " · overdue" (`· vadesi geçti`).

**Loans (`spontaneous_loans`)**:
1. Repayments: every active `indebted_to` bond: parties must both be canon (else deactivate). `have = wealth(debtor)`;
   if `have != null and have − amount < repay_keep` → skip; `chance(repay_pct)`; paid = have == null ? 0 : amount;
   transfer −paid / +paid; deactivate bond; `rel_change(+repay_relation)` "debt paid"; chronicle `debt (borc)`: "{debtor}
   paid its debt ({amount} {what}) to {creditor}[ even though it was overdue]."; note.
2. `late_debts(epoch)` (`borcGecikmeleri`, also called at the start of mortal turns): each active debt not yet marked
   overdue whose due < epoch: if a party is not canon → deactivate; else `rel_change(creditor, debtor, −late_penalty,
   "unpaid debt")`, append " · overdue", chronicle "{debtor} did not pay its debt ({amount} {what}) to {creditor} on time
   (Epoch {due}); coldness fell between them." Returns count.
3. New loan: communities with a wealth key; lenders with wealth ≥ loan_rich sorted desc (id); first borrower in the same
   world with wealth ≤ loan_poor, distance ≤ loan_distance, not enemies, not already owing that lender. If candidate and
   `chance(loan_pct)`: `amount = max(1, min(loan_amount, wealth(L)))`, `what = wealth key == wealth ? "silver" :
   "grain"`, `due = epoch + loan_term`; transfer; bond borrower `indebted_to` lender (encoded description);
   `rel_change(+loan_relation)` "loan"; chronicle "{L} lent {amount} {what} to {B}, who was in need; due Epoch {due}."; note.

**Barter (`spontaneous_barter`)**: over active `trade` bonds (by id): both canon, different, not enemies; goods =
canon resource/item/vehicle/work owned (`owns`); value = `stats.value ?? max(might, damage, protection, splendour,
speed)`; first pair `x` of A and `y` of B with |value diff| ≤ barter_gap. Then `chance(barter_pct)`: transfer ownership
both ways (deactivate old `owns`, new `owns` "barter"), `rel_change(+barter_relation)`; chronicle `trade (ticaret)`:
"{A} and {B} bartered: {x} for {y}."; note.

**Adoption (`spontaneous_adoption`)**: mortals with age; captives excluded. Children (age ≤ adopt_child_age) ordered by
age, id; orphan = no canon mortal parent via `descends_from`. Adopter: other mortal, same world, age gap ≥
adopt_age_gap, same location or distance ≤ adopt_distance, no existing descends_from/enemy between them. On
`chance(adopt_pct)`: bond child `descends_from` adopter ("adopted: left alone, taken in"), `rel_change(+adopt_relation)`;
chronicle `lineage (soy)`: "{o} adopted the orphaned {c}."; note.

**Interworld treaty (`spontaneous_treaty`)**: for each open route (a ≠ b): top `treaty_candidates` most populous
communities on each end; for pairs not enemies or allies: `il = rel(a,b)`; type = `trade` if no trade bond and il ≥
treaty_trade_threshold; `ally` if trade bond and il ≥ treaty_alliance_threshold; best pair = highest il. On
`chance(treaty_pct)`: bond `a {type} b` ("interworld treaty (by way of {method})"), `rel_change(+treaty_relation)`;
chronicle `diplomacy (diplomasi)`: "{a} of the world {A} and {b} of the world {B} made an interworld {alliance | trade}
treaty over the {method} route between them."; note.

### 10.5 Previous creation (`previous_creation`, Ö-34)
Once per non-forgotten world (skip if any entity of the world tagged `previous creation`): needs a region and
`chance(previous_creation_pct)`. Region = most dangerous. Create:
- ruin place `{subtype: "ruin of the previous creation", name: "Ruins beneath {region}", power: ruin_level, location:
  region, tags: ['previous creation','ruin'], stats: {danger: base + d, fertility: ruin_fertility, mystery:
  ruin_mystery}, description: "[World engine] Beneath {region} were found the ruins of a civilization that {creator}
  created and forgot before this cosmos. The writing on the stones resembles no language; but the creator's name is
  written there in another form."}`;
- relic item `{subtype: "relic of the previous creation", name: "{region} Relic", power: relic_level, location: ruin,
  tags: ['previous creation','cursed'], stats: {damage, protection, might, curse} rolled, description: "[World engine] In
  the deepest part of the ruins, a powerful but cursed object from the hands of a forgotten civilization."}`;
- knowledge `{type: technology, subtype: "forgotten knowledge", name: "Knowledge of the Previous Creation ({W})", power:
  old_knowledge_level, tags: ['previous creation','lost', 'branch:forbidden' if chance(old_knowledge_forbidden_pct) else
  'branch:magic'], stats: {level: old_knowledge_tech_level, spread: 0}, description: "[World engine] A knowledge older than
  this cosmos, hidden in the ruins."}`, world W; bond ruin `source_of` knowledge ("hidden in the ruins");
- a Fate thread: "Ruins of a previous creation were found in {W}. What did {creator} create before this cosmos, and why
  did they forget it?" related [ruin, relic, knowledge];
- chronicle `previous_creation (onceki_yaratilis)`: "In {W}, the ruins of a creation before this cosmos came to light.";
  note. (Mortal tool `kalinti_kaz` digs them — mortal spec.)

### 10.6 Tunables `MEDENIYET` — group "Civilization" unless noted
| old key | new key | default | min | max | label |
|---|---|---|---|---|---|
| bagimsizlik_savas_sans | independence_war_pct | 60 | 0 | 100 | Independence turns into war (%) |
| federasyon_sans | federation_pct | 25 | 0 | 100 | An interworld federation forms (%) |
| onceki_yaratilis_sans | previous_creation_pct | 35 | 0 | 100 | A previous-creation ruin is found (%) |
| sehir_nufus | city_population | 3000 | 0 | 100000000 | Min population for city-state |
| sehir_bilgi | city_knowledge | 1 | 0 | 100 | Min known techs for city-state |
| krallik_nufus | kingdom_population | 20000 | 0 | 100000000 | Min population of a kingdom with no governed places |
| krallik_yonetim | kingdom_governed | 1 | 0 | 100 | Min governed places for kingdom |
| krallik_bilgi | kingdom_knowledge | 3 | 0 | 100 | Min known techs for kingdom |
| imparatorluk_bolge | empire_region_share_pct | 50 | 0 | 100 | World empire: share of settled regions ruled (own, governed and tributaries' dominant regions) (%) |
| imparatorluk_nufus | empire_population_share_pct | 25 | 0 | 100 | World empire alternative: be the world's most populous political power and hold this share of its population (subjects and tributaries included) (%) |
| imparatorluk_bolge_alt | empire_min_regions | 2 | 1 | 1000 | Min regions of a world where an empire can exist |
| yildizlararasi_dunya | interstellar_worlds | 2 | 1 | 100 | Min worlds spread for interstellar power |
| kozmik_dunya | cosmic_worlds | 3 | 1 | 100 | Min worlds spread for cosmic power |
| basamak_dusus_pay | tier_drop_share_pct | 15 | 0 | 100 | Hysteresis: a community in its tier declines only after falling this % below the thresholds |
| basamak_en_az_cag | tier_min_epochs | 3 | 0 | 100 | A community that changed tier does not reverse for this many epochs (0 off) |
| koloni_yas | colony_min_age | 3 | 0 | 100 | Min age (epochs) of a colony that can demand independence |
| koloni_uzak_iliski | colony_far_cooling | 4 | 0 | 100 | Per-epoch cooling of a colony on another world toward the motherland |
| koloni_yakin_iliski | colony_near_cooling | 1 | 0 | 100 | Same, same world |
| koloni_uzak_sans | colony_far_pct | 12 | 0 | 100 | Independence chance of a colony on another world (%) |
| koloni_yakin_sans | colony_near_pct | 4 | 0 | 100 | Same, same world (%) |
| koloni_refah_taban | colony_prosperity_base | 40 | 0 | 100 | Colony prosperity above which independence chance grows |
| koloni_refah_bolen | colony_prosperity_divisor | 400 | 10 | 100000 | Prosperity contribution: (prosperity − base) / this |
| koloni_kin_sans | colony_grudge_pct | 10 | 0 | 100 | Extra chance for a colony resentful of the motherland (%) |
| federasyon_uye | federation_min_members | 3 | 2 | 100 | Min federation members |
| federasyon_en_cok | federation_max | 1 | 0 | 100 | Max federations at once in the cosmos (a community joins at most one; 0 disables) |
| federasyon_dunya | federation_min_worlds | 2 | 1 | 100 | Min worlds spanned by members |
| federasyon_guc_seviye | federation_level | 6 | 1 | 12 | Federation power level |
| federasyon_guc | federation_power | 50 | 0 | 100 | Federation power stat |
| federasyon_servet | federation_wealth | 60 | 0 | 100 | Federation wealth |
| federasyon_nufuz | federation_influence | 70 | 0 | 100 | Federation influence |
| kalinti_guc_seviye | ruin_level | 7 | 1 | 12 | Ruin power level |
| kalinti_tehlike / _zar | ruin_danger_base / _die | 50 / 30 | 0/1 | 100 | Ruin danger |
| kalinti_bereket | ruin_fertility | 10 | 0 | 100 | Ruin fertility |
| kalinti_gizem | ruin_mystery | 95 | 0 | 100 | Ruin mystery |
| emanet_guc_seviye | relic_level | 8 | 1 | 12 | Relic power level |
| emanet_hasar / _zar | relic_damage_base / _die | 40 / 40 | 0/1 | 100 | Relic damage |
| emanet_koruma / _zar | relic_protection_base / _die | 30 / 40 | 0/1 | 100 | Relic protection |
| emanet_kudret / _zar | relic_might_base / _die | 80 / 20 | 0/1 | 100 | Relic might |
| emanet_lanet / _zar | relic_curse_base / _die | 50 / 40 | 0/1 | 100 | Relic curse |
| eski_bilgi_guc_seviye | old_knowledge_level | 7 | 1 | 12 | Previous-creation knowledge power level |
| eski_bilgi_seviye | old_knowledge_tech_level | 7 | 1 | 10 | Its tech level |
| eski_bilgi_yasak_sans | old_knowledge_forbidden_pct | 50 | 0 | 100 | It is forbidden knowledge (%) |
| borc_sans | loan_pct | 10 | 0 | 100 | A wealthy community lends to a poor neighbour (per epoch %) (Economy) |
| borc_zengin | loan_rich | 55 | 0 | 100 | Min wealth/prosperity of a lender (Economy) |
| borc_yoksul | loan_poor | 35 | 0 | 100 | Max wealth/prosperity of a borrower (Economy) |
| borc_miktar | loan_amount | 10 | 1 | 100 | Spontaneous loan amount (Economy) |
| borc_vade | loan_term | 3 | 1 | 50 | Loan term (epochs) (Economy) |
| borc_mesafe | loan_distance | 3 | 0 | 99 | Max distance between borrower and lender (Economy) |
| borc_ode_sans | repay_pct | 40 | 0 | 100 | A debtor able to pay repays (per epoch %) (Economy) |
| borc_ode_pay | repay_keep | 10 | 0 | 100 | Wealth/prosperity the debtor must keep after paying (Economy) |
| borc_iliski | loan_relation | 5 | 0 | 100 | Relation gain from a loan (Economy) |
| borc_ode_iliski | repay_relation | 8 | 0 | 100 | Relation gain from repayment (Economy) |
| borc_gecikme | late_penalty | 20 | 0 | 100 | Relation loss from an overdue debt (engine and mortal debts) (Economy) |
| takas_sans | barter_pct | 8 | 0 | 100 | Trade partners barter spontaneously (per epoch %) (Economy) |
| takas_fark | barter_gap | 25 | 0 | 100 | Max value difference of bartered goods (Economy) |
| takas_iliski | barter_relation | 6 | 0 | 100 | Relation gain from barter (Economy) |
| evlat_sans | adopt_pct | 6 | 0 | 100 | An old mortal adopts a nearby orphan (per epoch %) (Heroes & mortals) |
| evlat_cocuk_yas | adopt_child_age | 16 | 0 | 1000 | Max age of an adoptable child (Heroes & mortals) |
| evlat_yas_fark | adopt_age_gap | 15 | 0 | 1000 | Min age gap adopter–child (Heroes & mortals) |
| evlat_mesafe | adopt_distance | 1 | 0 | 99 | Max distance adopter–child (Heroes & mortals) |
| evlat_iliski | adopt_relation | 10 | 0 | 100 | Relation gain from adoption (Heroes & mortals) |
| antlasma_sans | treaty_pct | 8 | 0 | 100 | Communities of two worlds linked by an open route make a treaty (per epoch %) |
| antlasma_ticaret_esik | treaty_trade_threshold | 0 | −100 | 100 | Min relation for an interworld trade treaty |
| antlasma_ittifak_esik | treaty_alliance_threshold | 25 | −100 | 100 | Min relation of trade partners for an interworld alliance |
| antlasma_aday | treaty_candidates | 4 | 1 | 100 | Most populous communities considered on each end |
| antlasma_iliski | treaty_relation | 12 | 0 | 100 | Relation gain from a spontaneous interworld treaty |

### 10.7 Cross-module calls
Uses `mudahale.bildikleri`, `derin.kayitAc, etiketEkle, etiketSil, tIliskiDegistir, tIliski, kanonlar, savasIlan,
mesafe`, `seyahat.rotalar`, `kesif.siyasiHarita`, rules `borcAciklama/borcOku`. Used by `sim` (engine; `basamakOf` →
military power `+ tier × SG.basamak_guc`), `hedef` (goals), `olumluler` (`borcGecikmeleri`). Design intent (DENETIM
Ö-31): each tier unlocks new tools — check the agents/tools spec for tier-gated tools.

---

## 11. Pantheon and cosmos engine (`src/panteon.js`)

### 11.1 Purpose
Foreign/old gods (engine + summary, no agent loop — operator decision: "rival pantheons: engine + summary"), the cosmic
hand of sons and creator (holy world, gate sealing, hanging/extinguishing stars, cleansing leak, forgetting a world,
bargaining with Outer Beings), threats to the creator (Outer Beings gnaw the creator's essence), automatic holy-world
claims, and automatic rival-son clashes.

Module load adds columns (migration smell): `dunyalar.koruyucu_oto`, `yabanci_tanrilar.{yenilgi_cag, uyanis_baski,
olum_cag, uyanis_ortalama}`.

### 11.2 Foreign gods basics
- `foreign_gods(world_id?)` → rows parsed with `yt_open` (stats/personality/powers/existence/depth).
- **`add_foreign_god({name, title, domains, description, attitude=0, world_id, power = foreign_power_base +
  d(foreign_power_die), image_prompt}, epoch)`**: unique name (Roman numeral on collision), attitude clamped −100..100,
  status default `awake`, stats = `seeded_stats("{name}:{world}:{epoch}")`. Callers: world birth (old god), creator
  manual add (`oyuncu`), `epoch.yerelTanriDogur` (S6-17: a world ≥ `AJAN.yerel_tanri_cag` epochs old, with a people,
  no living foreign god (or the dead one mourned ≥ `yerel_tanri_yeniden_cag`), gets a sleeping local god named from the
  world's language, domains from `DUNYA_ALAN[type]`, title "the sleeping {domain} god of the {people} people", power
  `AJAN.yerel_tanri_guc`, status asleep, not contacted — agents spec).
- Worshippers: entities with an active `worships` bond to the god (`dst_type='y'`), canon.
- `faith(god)` = Σ worshippers `(population/foreign_faith_per_population) + (followers/foreign_faith_per_follower)`.
- `reachable(a, b)` (`yolVar`) = same world or an open known route between them.

### 11.3 Waking
**Defeated gods (`defeated_waking`)**: first clear `defeat_epoch` of non-defeated gods. For each defeated god:
`faith = round(faith(god))`; `start = defeat_epoch ?? epoch`; store both. `duration = max(1, round((wake_epochs −
yt_effect(endurance, wake_endurance_rate)) × (has reviving ? power_revive_pct/100 : 1)))`. Wakes if `epoch − start ≥
duration` OR (`faith ≥ wake_faith` and wake_faith > 0): status awake, clear defeat_epoch, `power = max(power,
wake_min_power)`, `attitude = max(−100, attitude − wake_grudge)`; rewrite title/description to remove "sleeping"
wording (`kronik-onar.uyanisMetniYaz`); chronicle `foreign_god (yabanci_tanri)`: "{W}'s defeated god {g} woke again:
{its worshippers' faith raised it again | epochs passed over the defeat and the wound closed}. It has not forgotten the
grudge of defeat."; note.

**Sleeping gods (`sleep_waking`)** — event-driven, not time-driven. Per sleeping god, `wake_pressure(god, epoch)`:
- Components for the god's world `dw`, this epoch:
  - `son` = active sons who left a trace in dw this epoch: created an entity of dw this epoch, OR have a chronicle line
    this epoch (owned by the son) referencing an entity of dw, excluding engine-bookkeeping types (`world, engine_raw,
    system, creator_reputation, existence, fate` = `dunya, motor_ham, sistem, tanri_itibar, varolus, kader`). (Merely
    standing there does not count.)
  - `expedition` = journeys to dw started this epoch + routes touching dw created this epoch.
  - `event` = entities of type event created this epoch in dw (wars, disasters, plagues, battles…).
  - `land` = regions/places created this epoch in dw by a son, mortal or the creator (`source ∈ {ogul, olumlu, tanri}`).
  - `ruin` = entities created this epoch in dw whose subtype contains "ruin"/starts with "previous creation" or tagged `ruin`.
  - `death` = mortals of dw whose death_epoch = epoch − 1.
- `noise = son×wake_son + event×wake_event + land×wake_land + death×wake_death`; `events = expedition×wake_expedition +
  ruin×wake_ruin` (always count).
- `baseline = god.wake_baseline ?? noise` (first measurement starts at this epoch's noise, so it accumulates nothing).
- `raw = events + max(0, noise − baseline × wake_ordinary_pct/100)`; `new_baseline = baseline + (noise − baseline) ×
  wake_average_weight/100` (EMA).
- `points = round(wake_epoch_cap > 0 ? min(raw, wake_epoch_cap) : raw)`.
Then: store new baseline; if points: `pressure += points`; if `< wake_threshold` store; else status awake, pressure 0,
rewrite texts, reason = top-2 components by weighted value, phrases: son "the footsteps of gods", expedition "foreign
sails and opened roads", event "the noise of war and disaster", land "the reshaping of its land", ruin "old ruins rising
from beneath the earth", death "the laments of the dead". Chronicle `foreign_god`: "{W}'s sleeping god {g} woke: {r1 and
r2} pulled it from its sleep."; note. (First contact comes later via the normal path.)

### 11.4 Automatic holy worlds (`auto_holy_worlds`) — also run by startup repair
If `auto_holy_min_worshippers == 0` or fewer than 2 worlds → none. Candidates = non-forgotten worlds with no protector
or a dead protector. For each, active sons with ≥ `auto_holy_min_worshippers` canon worshipping entities in that world
(grouped). Pairs (world, son, n) sorted by n desc, world id. For each pair: skip if the world was already claimed in this
run or the son already holds ≥ `auto_holy_max_per_son` automatic claims; `declare_holy_world(son, world)`; mark
`protector_auto = 1`.

### 11.5 Rival clashes (`rival_clashes`)
If `rival_max == 0` → none. Active sons; pairs with `son_rel ≤ −rival_relation` and reachable worlds. Process sorted by
relation ascending. For each pair: history = last `max(rival_loss_streak,1)×2+2` chronicle rows of type `duel (meydan)`
owned by either son whose text contains both names; winner parsed from ". {name} won" (LANGUAGE-SPECIFIC: parsing
narrative text — new design must store duel results structurally). If clashes ≥ rival_max, or last clash was < rival_gap
epochs ago, or `!chance(rival_pct)` → `rival_soften(a, b)` (relation moves toward −rival_relation by ≤ rival_soften, never
above the threshold) and continue. Else: attacker = weighted pick by `anger + ambition + 1`; arena stat = weighted pick
among strength/wisdom/cunning/charisma/will by `(attacker.stat + defender.stat)/2 + 1`; `tools.meydanOkuma(attacker,
defender, stat, "old feud")` (son duel — sons spec); note its text. Loss streak: if the last `rival_loss_streak` results
(including this) all have the same winner → `son_rel_change(+rival_retreat_relation)`; chronicle `duel` (owned by the
loser): "{loser}, beaten {N} times in a row by {winner}, withdrew; the feud between them calmed for a while."

### 11.6 Pantheon engine (`pantheon_engine`, old `panteonMotoru`) — order
1. `defeated_waking`; 2. `sleep_waking`; 3. `auto_holy_worlds`; 4. `rival_clashes`.
5. For each **awake** foreign god:
   - `natives` = canon people/settlements/cults of its world.
   - Attraction: first `foreign_attract_max` natives with no `worships` bond at all: `chance((foreign_attract_pct +
     yt_effect(charisma, attract_charisma_rate) + (caller ? power_attract_pct : 0))/100)` → bond `worships` god ("old
     god"); note "{v} began to worship {W}'s old god {g}."
   - Power growth: `faith = faith(god)`; store `faith = round`, `power = min(100, power + (faith > foreign_power_faith −
     yt_effect(might, power_faith_might_rate) ? foreign_power_growth : 0))`.
   - First contact: if not contacted and (an active son's active world is the god's world, or an active route touches it)
     → contacted=1; chronicle `foreign_god` (son id if present): "First contact: {W}'s old god {g}[, {title}] noticed
     {creator}'s pantheon. {Curiously. (attitude ≥ attitude_curious) | With hostility. (attitude ≤ −attitude_hostile) |
     Silently, measuring.}"; note "{g} noticed the pantheon." Not contacted → skip remaining steps.
   - Hostile (attitude < 0) with `chance((foreign_hostile_pct + yt_effect(agility, attack_agility_rate) + (destroyer ?
     power_destroy_pct : 0))/100 + (−attitude)/foreign_hostile_divisor)`:
     - victim = first canon entity of the god's world worshipping a son. If victim and `chance((sacrifice_pct +
       yt_effect(cunning, steal_cunning_rate) + (thief ? power_steal_pct : 0))/100)`: deactivate its son-worship, bond
       `worships` god ("stolen"); the son's anger += foreign_steal_anger; chronicle `foreign_god` (son): "{g} turned
       {son}'s worshipper {victim} to itself."; note.
     - else: first canon work in its world whose **subtype** matches temple/shrine/altar → status destroyed
       (fate note "Epoch N: destroyed by {g}."), bond god `destroyed` temple ("destroyed its temple"), chronicle "{g}
       destroyed {temple}.", note.
   - Friendly (attitude ≥ foreign_friend_attitude) and `chance((foreign_friend_pct + yt_effect(wisdom, help_wisdom_rate))/100)`:
     `gift = max(0, round((foreign_friend_prosperity + yt_effect(creativity, prosperity_creativity_rate)) × (bountiful ?
     power_bounty_pct/100 : 1)))`; first `foreign_friend_max` worshippers with prosperity get `prosperity_add(gift)`.
   - Attitude drift: `−rebels × foreign_rebel_drift` (rebels = non-dead sons whose active world is the god's world and flagged rebel
     `asi`) `− (any native tagged cursed ? foreign_curse_drift : 0)`; apply clamped −100..100.
6. `spontaneous_god_war` (§11.7).
7. Outer Beings gnaw the creator: if any canon Outer Being: `gnaw = Σ round((influence || outer_influence_default) /
   outer_gnaw_divisor)`; creator essence = max(0, essence − gnaw); note "The things outside gnawed {gnaw} from
   {creator}'s essence." (Design Ö-30 also wanted godless worlds to fade the creator — "loneliness" — handled by the
   creator-mood module, not here.)

### 11.7 Spontaneous war on a hostile foreign god (`spontaneous_god_war`) and the shared resolver
- Target = first foreign god that is awake, contacted and attitude ≤ −son_war_attitude. Son = active son passing the
  rarity gate `NADIRLIK_KAPI.yabanci_savas` (default rare), essence ≥ `OGUL_ARAC.ysavas_oz`, reachable; best by
  strength + will + level, then id. Then `chance(son_war_pct)` (roll after candidate found).
- **`foreign_god_war(god, son, epoch, {reason="to protect their worshippers and temples"})`** (`yabanciTanriSavasi`):
  - `p1 = round((son.strength + son.will)/2 + son.level × OGUL_ARAC.ysavas_seviye + d(OGUL_ARAC.ysavas_zar))`;
    `p2 = round(war_power(god) + d(ysavas_zar))`; `diff = |p1 − p2|`; son essence −= ysavas_oz.
  - Win (p1 ≥ p2): status `dead` if diff ≥ `ysavas_ezici` and god lacks deathless, else `defeated`; power −=
    ysavas_guc_kayip (floor 0); attitude −= ysavas_tutum; defeat_epoch/death_epoch accordingly; bond son `killed` /
    `defeated` god (reason); son xp += ysavas_xp, fame += ysavas_un. Text "{son} declared war on the foreign god {g}
    ({reason}) and {killed it | defeated it} ({p1}–{p2})."
  - Lose: `wound = ysavas_yara + diff`, `loss = min(ysavas_oz_kayip, max(0, essence))`; hp −= wound; essence −= loss;
    attitude −= ysavas_tutum; if hp ≤ 0 → hp 0, status asleep, `sleep_left = has revival ? 1 : ysavas_uyku`. Text
    "{son} declared war on the foreign god {g} ({reason}) but lost ({p1}–{p2}); lost {wound} HP and {loss}
    essence.[ {son} collapsed and fell into a sleep of N epochs.]"
  - essence floored 0; save; chronicle `foreign_god` (son). Note the text.
  - The son tool `yabanci_tanriyla_savas` (tools spec) implements the same fight but with
    `(strength+will)/ysavas_stat_bolen`, level-up via `kazan`, and revival sleep `dirilis_uyku` — **divergence**, see smells.

### 11.8 Cosmic actions (sons' tools and creator)
| function | effect |
|---|---|
| `declare_holy_world(son, world, epoch)` (`kutsalDunyaIlan`) | Throws if no world. If a previous protector exists, is a different son and not dead → `son_rel_change(son, old, −holy_world_relation)`. Set protector = son, `protector_auto=0` (the automatic path sets 1 afterwards). Chronicle `cosmic` (son): "{son} declared {W} his holy world[; trampling {old}'s claim]." Son tool `kutsal_dunya_ilan` gate rare. |
| `seal_gate(route_id, by, epoch)` (`kapiMuhurle`) | Route must be active ("No such open route."). Deactivate (sealed: severed_until null). Both worlds' leak −= `seal_leak`. Route's vehicle (gate) dies ("Epoch N: sealed by {by}."). Chronicle `cosmic`: "{by} sealed the route between {A} and {B}; the leak of both worlds decreased." Creator cost `KOZMIK_BEDEL.muhur` 30; son gate epic. |
| `hang_star({name, type='yellow dwarf', by, epoch, description})` (`yildizAs`) | Unique name; brightness `star_brightness_base + d(die)`; position per §1.1; chronicle `cosmic`: "{by} hung a new star in the sky: {name} ({type})." Creator `KOZMIK_BEDEL.yildiz` 80 (if name empty: a language-derived personal name for the given world, else "{cosmos} Sky's {N}th Star"; name ≥ 2 chars); son gate mythic. |
| `extinguish_star(star_id, by, epoch)` (`yildizSondur`) | Type → dead star, brightness `dead_star_brightness`. For each world of the star: leak += `extinguish_leak`; every canon region fertility −= `extinguish_fertility` (default `fertility_default`). Doom += `extinguish_doom` (cap threshold). Chronicle `cosmic`: "{by} extinguished {star}. {worlds or 'The void around it'} sank into darkness; the lands cooled, the things outside came closer." Son only (mythic). |
| `rekindle_star(star_id, by, epoch)` (`oyuncu.yildizTutustur`) | Only dead star/black sun/remnant ("{star} is already burning."). Type → `reborn star`, brightness `TANRI_ELI.tutustur_parlaklik` (75); its worlds' leak −= `TANRI_ELI.tutustur_sizinti` (20). Chronicle `sky`: "{by} rekindled {star}; light returned to the worlds buried in darkness." Creator `KOZMIK_BEDEL.tutustur` 60; son gate epic. Completes the dead_star quest. |
| `cleanse_leak(world_id, epoch)` (`sizintiTemizle`) | Leak −= `cleanse_leak`. If an Outer Being is in that world and `chance(expel_outer_pct)` → status destroyed ("Epoch N: the creator pushed it outside."). Chronicle `god (tanri)`: "{creator} stitched {W}'s tear; the leak receded[ and the thing that had come in was pushed outside]." Creator `KOZMIK_BEDEL.temizle` 80 — refused with no cost if the world has 0 leak and no Outer Being; son tool `sizinti_dik` gate epic. |
| `forget_world(world_id, epoch)` (`dunyayiUnut`) | World #1 cannot be forgotten ("You cannot forget your first world."). discovery → forgotten (trigger marks open routes), all its routes inactive, sons there moved to world 1. Chronicle `god`: "{creator} forgot {W}. The world sank into mist; its roads closed, its name remained only in tales." Creator `KOZMIK_BEDEL.unut` 20. Remembering = editing discovery back (trigger reopens). Forgotten worlds are excluded from almost every engine (events, archive, routes, exploration, quests, holy worlds, etc.). |
| `bargain_with_outer(son, outer_id, request, epoch)` (`disVarliklaPazarlik`) | Outer Being must be canon ("No such thing. Or there is, and you cannot see it."). `gain = bargain_essence + round((influence or default)/bargain_influence_divisor)`; son essence += gain, ambition += bargain_ambition, loyalty −= bargain_loyalty; that world's leak += bargain_leak; every other non-dead son: `son_rel_change(−bargain_relation)`; tag Outer Being `bargain:<son>`; open a Fate thread "{son} bargained with the thing outside ({request}). No one knows what they gave in return; but one day it will be paid." [outer]; chronicle `forbidden (yasak)` (son): "{son} bargained with the unnamed thing. Their siblings saw another shadow over them." Return gain. Forbidden; linked to rebellion (sons spec). |

### 11.9 Tunables `PANTEON` — group "Civilization" unless noted
| old key | new key | default | min | max | label |
|---|---|---|---|---|---|
| sondurme_kiyamet | extinguish_doom | 8 | 0 | 100 | Doom contribution of extinguishing a star (Doom) |
| yabanci_cekim_sans | foreign_attract_pct | 25 | 0 | 100 | Foreign god attracts a worshipper (%) |
| kurban_sans | sacrifice_pct | 50 | 0 | 100 | Foreign god demands a sacrifice / steals a worshipper (%) |
| yabanci_dost_sans | foreign_friend_pct | 15 | 0 | 100 | Friendly foreign god helps (%) |
| dis_kov_sans | expel_outer_pct | 50 | 0 | 100 | Creator pushes the Outer Being out (%) (Cosmic horror) |
| yabanci_guc / _zar | foreign_power_base / _die | 40 / 40 | 0/1 | 100 | New foreign god's power |
| yabanci_cekim_sayi | foreign_attract_max | 2 | 0 | 100 | Max unowned communities a foreign god turns to per epoch |
| yabanci_inanc_nufus | foreign_faith_per_population | 2000 | 1 | 10000000 | Worshipper population giving 1 faith |
| yabanci_inanc_murit | foreign_faith_per_follower | 60 | 1 | 10000000 | Followers giving 1 faith |
| yabanci_guc_inanc | foreign_power_faith | 10 | 0 | 100000 | Faith at which a foreign god starts growing |
| yabanci_guc_artis | foreign_power_growth | 1 | 0 | 100 | Per-epoch power growth with enough faith |
| tutum_merak | attitude_curious | 20 | 0 | 100 | Attitude at/above which first contact is curious |
| tutum_dusmanlik | attitude_hostile | 20 | 0 | 100 | Attitude at/below minus this is hostile at first contact |
| yabanci_dusman_sans | foreign_hostile_pct | 20 | 0 | 100 | Hostile foreign god's base attack chance (%) |
| yabanci_dusman_bolen | foreign_hostile_divisor | 300 | 1 | 100000 | Hostility contribution: hostility / this |
| yabanci_calma_ofke | foreign_steal_anger | 10 | 0 | 100 | Anger gain of a son whose worshipper was stolen |
| yabanci_dost_tutum | foreign_friend_attitude | 40 | 0 | 100 | Min attitude to count as friendly |
| yabanci_dost_sayi | foreign_friend_max | 2 | 0 | 100 | Max worshippers helped per epoch |
| yabanci_dost_refah | foreign_friend_prosperity | 4 | 0 | 100 | Friendly god's prosperity gift |
| yabanci_asi_kayma | foreign_rebel_drift | 3 | 0 | 100 | Attitude drop per rebel son in the world |
| yabanci_lanet_kayma | foreign_curse_drift | 1 | 0 | 100 | Attitude drop when a native is cursed |
| dis_kemir_bolen | outer_gnaw_divisor | 10 | 1 | 1000 | Essence an Outer Being gnaws from the creator: influence / this (Cosmic horror) |
| kutsal_dunya_iliski | holy_world_relation | 15 | 0 | 100 | Sibling relation cost of taking another's holy world (Cosmos & travel) |
| muhur_sizinti | seal_leak | 10 | 0 | 100 | Gate sealing lowers both worlds' leak (Cosmic horror) |
| yildiz_parlaklik / _zar | star_brightness_base / _die | 50 / 45 | 0/1 | 100 | New star brightness (Sky) |
| olu_yildiz_parlaklik | dead_star_brightness | 5 | 0 | 100 | Extinguished star brightness (Sky) |
| sondurme_sizinti | extinguish_leak | 20 | 0 | 100 | Leak flowing to its planets when a star dies (Sky) |
| sondurme_bereket | extinguish_fertility | 25 | 0 | 100 | Fertility loss of planet regions when a star dies (Sky) |
| temizle_sizinti | cleanse_leak | 40 | 0 | 100 | Leak removed by cleansing (Cosmic horror) |
| pazarlik_oz | bargain_essence | 40 | 0 | 1000 | Base essence gain of a bargain with an Outer Being (Cosmic horror) |
| pazarlik_etki_bolen | bargain_influence_divisor | 2 | 1 | 100 | Bargain: Outer Being influence / this (Cosmic horror) |
| pazarlik_hirs | bargain_ambition | 10 | 0 | 100 | Bargaining son's ambition gain (Cosmic horror) |
| pazarlik_sadakat | bargain_loyalty | 15 | 0 | 100 | Bargaining son's loyalty loss (Cosmic horror) |
| pazarlik_sizinti | bargain_leak | 20 | 0 | 100 | Leak the bargain adds to the world (Cosmic horror) |
| pazarlik_iliski | bargain_relation | 10 | 0 | 100 | Bargaining son's relation loss with siblings (Cosmic horror) |
| ogul_savas_sans | son_war_pct | 10 | 0 | 100 | A son spontaneously wars on a hostile foreign god (per epoch %) |
| ogul_savas_tutum | son_war_attitude | 30 | 0 | 100 | Max (negative) attitude of a god a son wars on spontaneously |
| uyku_esik | wake_threshold | 100 | 1 | 100000 | Sleeping local god: wake pressure needed (only events accumulate; no time-based waking) |
| uyku_cag_tavan | wake_epoch_cap | 25 | 0 | 100000 | Max pressure accumulated in one epoch |
| uyku_ogul | wake_son | 15 | 0 | 1000 | Pressure per son acting (creating or chronicled) in that world this epoch |
| uyku_sefer | wake_expedition | 20 | 0 | 1000 | Pressure per expedition leaving for that world or route opened |
| uyku_olay | wake_event | 6 | 0 | 1000 | Pressure per major event in that world this epoch |
| uyku_toprak | wake_land | 8 | 0 | 1000 | Pressure per new region/place opened there by sons or mortals |
| uyku_kalinti | wake_ruin | 25 | 0 | 1000 | Pressure per ancient ruin / previous-creation trace found there |
| uyku_olum | wake_death | 2 | 0 | 1000 | Pressure per named mortal who died there in the previous epoch |
| uyku_olagan_kat | wake_ordinary_pct | 100 | 0 | 1000 | % of the world's ordinary noise (moving average) ignored; only noise above it accumulates (0: all counts) |
| uyku_ortalama_agirlik | wake_average_weight_pct | 20 | 1 | 100 | Weight of each epoch in the ordinary-noise moving average (%) |
| kutsal_oto_ogul | auto_holy_max_per_son | 1 | 0 | 100 | Max worlds a son can claim automatically (tool or creator grants not counted) |
| hasim_iliski | rival_relation | 60 | 0 | 100 | Two active siblings with relation below minus this may clash spontaneously |
| hasim_sans | rival_pct | 15 | 0 | 100 | Chance a qualifying rival pair clashes in an epoch (%) |
| hasim_tavan | rival_max | 1 | 0 | 50 | Max spontaneous clashes per epoch (0 off) |
| hasim_ara_cag | rival_gap | 3 | 0 | 100 | Epochs before the same two siblings may clash again |
| hasim_donus | rival_soften | 2 | 0 | 100 | Per-epoch softening of non-clashing rivals' relation (up to the rivalry threshold) |
| hasim_yenilgi_seri | rival_loss_streak | 2 | 1 | 100 | Beaten this many times in a row by the same sibling → withdraws |
| hasim_geri_iliski | rival_retreat_relation | 25 | 0 | 100 | Relation improvement when the loser withdraws |
| kutsal_oto_tapan | auto_holy_min_worshippers | 3 | 0 | 1000 | In a world with no protector, the son with the most worshippers (at least this many) declares it holy (0 off) |
| uyanis_cag | wake_epochs | 8 | 1 | 1000 | Epochs after defeat for a defeated foreign god to wake by itself |
| uyanis_inanc | wake_faith | 15 | 0 | 100000 | Worshipper faith that wakes a defeated god immediately |
| uyanis_guc | wake_min_power | 30 | 0 | 100 | Min power of a waking god |
| uyanis_kin | wake_grudge | 15 | 0 | 200 | Attitude loss of a waking god (grudge of defeat) |
| bereket_varsayilan | fertility_default | 50 | 0 | 100 | Fertility assumed for a region with none when a star dies (Sky) |
| dis_etki_varsayilan | outer_influence_default | 50 | 0 | 100 | Influence assumed for an Outer Being with none (gnawing and bargaining) (Cosmic horror) |

External rules used: `OGUL_ARAC.ysavas_*` (son war tool), `KOZMIK_BEDEL.*`, `NADIRLIK_KAPI.*`, `DENGE.kiyamet_esik`.

### 11.10 Cross-module calls
Uses `world.getSon, allSons, getVarlik, saveSon, iliski, iliskiDegistir, benzersizAd`, `sim.refahEkle`,
`derin.etiketEkle, kanonlar`, `seyahat.rotalar`, `tools.OGUL_K, meydanOkuma`, `yabanci.*`, `kronik-onar.uyanisMetniYaz`,
rules `gucVar, kapiyiGecer`. Used by `sim` (engine), `kozmos` (`yabanciTanriEkle`, `yabanciTanrilar`), `epoch` (creator
cosmic actions, local god birth), `tools` (son cosmic tools), `oyuncu` (manual foreign god add/edit, forget world),
`onarim` (`kutsalDunyalar` at startup).

---

## 12. Creator's cosmic actions (summary for the integrator)
Implemented in `epoch.js` (`kozmikEylem`, `yolEylemi`, `dunyaYarat`, `seferGeriCagir`) + the functions above. All go
through the "ledger" (`defterli`: one undoable Fate ledger record per action), pay essence with `harca(cost, rule_key)`
and refund on any thrown error (`iade`).
| action | cost rule (default) | function |
|---|---|---|
| Create world | `DENGE.dunya` (120) | `world_birth` (§2.4) |
| Hang star (`yildiz`) | `KOZMIK_BEDEL.yildiz` (80) | `hang_star` |
| Seal gate (`muhur`) | `KOZMIK_BEDEL.muhur` (30) | `seal_gate` |
| Cleanse leak (`temizle`) | `KOZMIK_BEDEL.temizle` (80) | `cleanse_leak` (refused if nothing to cleanse) |
| Forget world (`unut`) | `KOZMIK_BEDEL.unut` (20) | `forget_world` |
| Rekindle dead star (`tutustur`) | `KOZMIK_BEDEL.tutustur` (60) | `rekindle_star` |
| Soul binding (`ruh`) | `KOZMIK_BEDEL.ruh` (15) | `soul_bind` |
| Legendary quest (`sefer`) | `KOZMIK_BEDEL.sefer` (30) | `open_quest` |
| Sky event (`gok`) | `KOZMIK_BEDEL.gok` (50) | `sky_event` (target required) |
| Sever route (`kopar`) | `OTESI.kopar_bedel` (40) | `sever_route` |
| Stitch route (`dik`) | `OTESI.dik_bedel` (40) | `stitch_route` |
| Reveal hidden route (`aciga`) | `SEYAHAT.aciga_bedel` (20) | `reveal_hidden_route` |
| Recall expedition | free | `recall_journey` |
| Exile / pardon | free | `exile` / `pardon` |
`KOZMIK_BEDEL.*` are tunable 0–500 (group "Cosmic actions"); English labels: yildiz "Kindle a star", muhur "Seal a
gate", temizle "Cleanse leak", unut "Forget a world", gok "Sky event", tutustur "Light a dead star", ruh "Soul binding",
sefer "Legendary quest". Additional manual "player control" edits (assign son to world, edit world/star/route/climate,
cosmic resource and deposits, foreign god add/edit, etc.) live in `oyuncu.js` — player-control spec.

---

## 13. Intended design (DENETIM.md "FAZ 2 — KOZMOS") vs. what is implemented

Operator decisions (2026-10-28): rival pantheons are run by the engine + summaries (no LLM agents); the cosmic travel
resource is unique per cosmos and generated at creation (first world birth that supplies it); existing worlds stay as
the first world of their cosmos; sons can truly die (resurrection only via a thread + ritual); map defaults to terrain.

Vision principles that the new design must keep: **Connection** (every new thing links to something existing),
**Mechanism** (every concept has a measurable simulation effect), **Narrative** (everything lands in the chronicle and
Fate's threads), **Visibility** (atlas, network, map, wiki, codex, live feed), **Scale** (agents see their own world in
detail and other worlds as one-line summaries; prompt size must not grow linearly with world count), **Cheapness**
(smallest model by default; one structured call per heavy job such as world birth).

| Proposal | Intended | Implemented (where) / gap |
|---|---|---|
| Ö-1 data model | stars, worlds (many fields), every entity/son job/chronicle row carries world_id | Done (§1). Chronicle world is derived from entity ids, not a column. |
| Ö-2 world types | ocean, sand, ice, lava, crystal, living, gas, ringed, moons, asteroid belt, tidally locked, dream, dead, mirror, void pocket, the god's palace, generation ship, corpse-world | **Only 11 types** (§1.9.1): no ringed, asteroid belt, tidally locked, void pocket, palace, generation ship, corpse-world (moons exist via `parent_id`). Decide whether to add. |
| Ö-3 terrain per world | sea ratio, temperature, humidity, mountains, glacier threshold, lava/crystal/organic masks; extra biomes (sand sea, glass desert, flesh forest, bone plain, mist valley, mushroom forest, salt flat, floating islands) | Terrain = `{sea, mountains, humidity}` + per-type biome lists (map spec). |
| Ö-4 physics | high gravity → strong but slow, hard escape; low → flyers, easy launch; thin air → breath resource; long day → calendar; time factor (dream epoch 500 years; dead realm no time) | gravity → war bonus; atmosphere → capacity (+ colonies need void_living for none/toxic); time factor → ageing/growth and narrated time gaps. No escape/launch effects, no calendar. |
| Ö-5 world birth | creator action, legendary/mythic son tool, explorers' discovery; one call; sons may declare holy world | Done (§2.4, §4.5, §11.8). |
| Ö-6 identity per world | own naming dialect, own sky / star of the epoch, own leak gauge | Done. |
| Ö-7/8 routes & 9 methods | each method its own knowledge branch, cost, risk; gates need sacrifice/key/true name; light sail snaps if the star dies; dream travel may not return; river of the dead costs memory | Methods exist with duration/danger/knowledge (§1.9.4). Costs are mostly **narrative**: no sacrifice for gates, sail routes do not snap when a star dies, dream/memory costs are road-event flavour only. |
| Ö-9 vehicles | ships/gates/mounts/bridges with stats; captured, sunk; captains are mortals; lost ships → ghost-ship legends | Vehicle entity type; ghost ships (§3.7E). Building/capture in tools/mortal specs. |
| Ö-10 journeys | mortal tools sefere_cik, koloni_kur, rota_kesfet; multi-epoch; road events (pirates, void storm, creature, getting lost, discovery); culture shock and first contact | Done (§3.7–3.8). |
| Ö-11 knowledge branches | sky navigation, shipbuilding, gate lore, pathfinding, void living, biomancy, forbidden | Done (§1.9.5); also immortality. |
| Ö-12–15 resources & economy | cosmic travel resource, original resources and their mechanics, travelling markets, void pirates, black market, currency value differences | Birth creates them (§2.5); mechanics, monopoly, markets, pirates are in `ekonomi.js` (economy spec). |
| Ö-16 Outer Beings | not part of the pantheon; no agent loop; names unspoken | Done (§8.4 step 6). |
| Ö-17 leak | raisers: forbidden knowledge, gate use, dead stars, godlessness, cosmic-resource addiction; results: hallucinations, mutation, geometry-breaking map cells, cults; doom can be a calling | Done (§8.3–8.6); map "breathing cells" are a UI concern. |
| Ö-18 sanity | for mortals, peoples **and sons**; low sanity: prophecies but bad decisions, strange rites, son existence gauge disturbed, Madness-domain sons fed; recovered by medicine, priests, forgetting (memory resource) | Communities/mortals only; sons' sanity not implemented; Madness-domain sons gain essence/existence (§8.4 step 5). "Bad decisions" for low-sanity heroes lives elsewhere if anywhere. |
| Ö-19 forbidden knowledge | big power (open gates, extinguish stars) at a sanity/leak price; Fate watches | Leak + sanity erosion (§8); war/magic bonus in sim. |
| Ö-20 horror events | stars align, eye in the sky, wave of silence, reverse rain, visit of the Void | Done (§8.5). |
| Ö-21–26 creatures | traits, mutation, hybrids and chimeras (`kimera_dok`), megafauna (travel means, threat, resource source; killing changes the age), ecology, invasive species across worlds, taming and mounts | Done (§9); megafauna-as-transport only via "mount" method check; "killing changes the age" not visible here. |
| Ö-27 rival pantheons | first contact, cosmic diplomacy, wars between gods, temple destruction, stealing worshippers | Done (§11). |
| Ö-28 sons' cosmic hand | holy world, sky bridge, hang/extinguish star (mythic), seal gate, birth world, bargain with Outer Beings | Done (§11.8, tools spec). |
| Ö-29 creator actions | create world, kindle star, seal gate, cleanse leak (expensive), forget world (soft destruction: mist) | Done (§12). |
| Ö-30 creator threatened | Outer Beings gnaw essence; godless worlds make the creator fade | Gnawing done (§11.6 step 7); fading is in the creator-mood module. |
| Ö-31 tiers | tribe → city-state → kingdom → world empire → interstellar → cosmic; **each tier unlocks new tools** | Tiers done (§10.2) with hysteresis; affect military power and goals; **no tier-gated tools found** — decide. |
| Ö-32 colonization | colonies diverge (language, religion, mutation) and may fight for independence | Independence done; divergence via other modules (language drift etc.). |
| Ö-33 cosmic politics | interworld empires, federations, trade guilds, resource monopolies, pirate kingdoms, exile worlds, neutral holy worlds | Federations (§10.3), monopoly (economy), exile (§6.8). No guilds, pirate kingdoms, neutral worlds as entities. |
| Ö-34 previous creation | ruins on every world, `kalinti_kaz` tool, powerful cursed artifacts, deepest Fate threads | Done (§10.5). |
| Ö-35 sky cycles | eclipses, comets, alignments, supernova burning a world, black-sun birth; star of the epoch per world | Done (§5). |
| Ö-36 time difference | returning travellers find relatives dead | Narrative only (§5.6). |
| Ö-37 time echoes | messengers from the future, prophecies leaking back, same hero in two times | Done (§5.5). |
| Ö-38–46 beyond | soul economy, golems, soul-harvesting cults; planetary consciousness; cosmic archive (burning changes the age); cosmic spores/plague and mycelium networks; void storms that also re-fog explored map; mirror world; legendary quests; cosmic law (treaties, oath stones, court, exile, pardon); immortality | Done (§6) except mycelium networks and storms re-fogging the map. |
| Ö-55/56 scale | per-world context; per-world engines; sons choose a world per epoch; mortal agents per world | Engine iterates worlds inside each module (not one engine per world). Context rules in world/agents specs. |

---

## 14. Known bugs, smells and how the new design should avoid them

1. **Tags as LIKE-matched Turkish strings** (`etiketler LIKE '%kozmik arşiv%'`) everywhere; fragile and slow. → tag table
   with enum keys; structured columns for `tier`, `traits`, `addicted_to`, `fold_count`, `bargains`.
2. **Schema migrations at module import** (`gok.js` adds `dunya.hizalanma_son`; `panteon.js` adds 5 columns). →
   versioned migrations only.
3. **Implicit global RNG** with "roll only after the candidate is found" comments to keep a seeded order. → explicit
   per-run RNG object passed to every engine function; document roll order where determinism matters.
4. **Dead tunable** `GOK.dizilim_tehlike` (horror uses `KORKU.dizilim_tehlike`). Drop it.
5. **Duplicated foreign-god war logic**: engine (`yabanciTanriSavasi`) uses `(strength+will)/2`, flat xp/fame and revival
   sleep 1; the son tool uses `/ysavas_stat_bolen`, `kazan()` (levels up) and `dirilis_uyku`. → one resolver.
6. **Soul descent not filtered by world** (§6.2): dead mortals of *any* world descend into the first `dead`-type world
   processed (and are tagged so others never get them). Decide: souls go to a dead realm reachable/linked to their
   world, or any dead realm, but make it explicit.
7. **Road event "lost" without swallowing** says "they lost their way and turned back" but the journey continues to
   arrive. Either turn it into a delay (+1 remaining) or a return home.
8. **`start_journey` folding side effect**: a pathfinder spends cosmic resource on any non-swallowing route (even
   gates/bridges with duration 1). Also `can_use_route` checks `fold_min_abundance` (12) while spending checks
   `ECONOMY.fold_cost` — a fold route can be usable but the spend can fail → normal duration silently.
9. **Alignment reveals all hidden routes cosmos-wide** regardless of method or star; the planetary alignment's danger
   drop is described as "routes shortened" (duration unchanged).
10. **Archive burning** deactivates a random 25% of *all* knowledge bonds in the cosmos (not just knowledge gained from
    the archive). Intended ("end of an age") but harsh; make the scope a rule.
11. **Cosmic plague re-roll**: an arrival is re-rolled every epoch for `cosmic_plague_window` epochs until infected
    (effective chance ≈ 1 − (1−p)^(window+1)). Decide whether one roll per arrival is intended.
12. **Rival duel history parsed from chronicle text** (". X won"); store duel results structurally.
13. **Temple detection by regex on Turkish words** (`tapınak|mabet|sunak`), and inconsistent: leak uses name+subtype,
    foreign-god destruction uses subtype only. → explicit `work.kind = temple`.
14. **Leak star check** uses regex `/ölü|kara|kırık/` on star type (dead/black/broken) but excludes `star remnant` (after
    supernova) while quests treat remnant as dead. Pick one "dark star" set.
15. **Phoneme check only on the first word** of a name; Turkish-locale lowercasing. Keep the concept (born-world names
    must fit the world's own dialect) but implement with a proper per-world phonology object.
16. **Horror "Eye" target filter** has operator-precedence ambiguity (`a && b || c && d`) — works as "entities of W with
    sanity, or people/settlement/mortal of W" but rewrite explicitly.
17. **Outer gnawing note** is emitted every epoch while any Outer Being exists, even when the gnaw rounds to 0.
18. **`kozmos()` overview** issues one COUNT query per world and per star (N+1). Fine for small cosmoses; use grouped
    queries.
19. **Stat defaults with `||`**: `0` is treated as "missing" in many places (e.g. mirror birth `100 − (st.guc || 50)`,
    chimera stats, trait effects). Use `??` semantics in the new code unless 0 must mean unknown.
20. **Planetary consciousness** worship loop runs only when the act roll succeeded (coupled); probably intended to be
    independent.
21. **Federation membership** treats any `related` bond to a federation as membership.
22. **Time difference** is narrative only; travellers' ages are untouched. Fine, but say so in UI.
23. **Kingdom population threshold** applies only through the OR with governed count; a community governing one place
    becomes a kingdom regardless of population (if ≥ 3 techs and city-state). Probably intended; document it.
24. **`world_physics` cache** keyed by epoch; editing a world mid-epoch (player control) is not reflected until the next
    epoch. Invalidate on edit.
25. **Turkish grammar fixing** (`ekDuzelt`) applied to many generated texts, and number words (`yaziyla`) — LANGUAGE-SPECIFIC: drop.
26. **Name collisions** resolved by appending Roman numerals across a single global namespace (entities, sons, stars,
    worlds, foreign gods). Keep the single namespace but consider a slug + display name.
27. **Engine notes vs direct chronicle**: some functions write both a chronicle row and a note (e.g. `sever_route` with
    `write=true` + spontaneous storm note) — the old engine folds/dedups (`motorTekrarlari`). New design: one event
    record with a narrative renderer.

---

## 15. Open questions for the integrator
1. Add the missing world types from the design (ringed, asteroid belt, tidally locked, void pocket, palace, generation
   ship, corpse-world) or keep 11?
2. Should travel-method costs become mechanical (gate sacrifice, sail snapping on star death, dream non-return, memory
   loss on the river of the dead)?
3. Sanity for sons (Ö-18) — implement or drop?
4. Tier-gated tools (Ö-31) — define which tools each tier unlocks, or keep tiers as power/goal modifiers only?
5. Soul descent world routing (smell 6) and archive-burn scope (smell 10).
6. Which foreign-god war formula is canonical (smell 5)?
7. The cosmic travel resource is defined at the first world birth whose model output supplies it — should cosmos
   creation (world #1) define it instead, as the operator decision wording suggests ("generated at creation")? (Today the
   player can also define it manually in player control, `oyuncu.js`, and a son cannot open deposits until it exists.)

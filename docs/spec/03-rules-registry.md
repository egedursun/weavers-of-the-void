# 03 — Rules registry and static game data

Source of truth (old repo, read-only): `src/rules.js`, `src/denge.js`, and every `tanimla(...)` block in `src/*.js` plus `server.js`.
Companion machine-readable file: `docs/spec/rules-registry.json` (3,323 entries, one per tunable).

This document has three parts:

1. **Part A — Static game data** (`src/rules.js`): rarities, stats, passions, resources, powers, domains, entity types, link types, knowledge branches, travel methods, natural laws, disasters, miracles, climates, social classes, relation labels, creature traits, resource mechanics, model defaults, and every helper formula as pseudo-code.
2. **Part B — The tunable-rules mechanism** (`src/denge.js`): how a balance number is declared, persisted, validated, applied and exposed.
3. **Part C — The complete registry**: every tunable (3,323 rows) grouped by namespace, with English key, old key, default, min, max, group, English label and defining module.

Conventions used throughout:

- Turkish original identifiers appear once in parentheses, e.g. "son (ogul)". Keys in code blocks are the *old* keys when written as `OLD_NS.old_key` and the *new* keys when written as `NEW_NS.new_key`.
- All tunables are **integers**. Probabilities and ratios are stored as **percent** and divided by 100 at use ("(%)" in labels). Dice "die N" means `d(N)` = uniform integer in `1..N`.
- "Power level" (guc_seviyesi) is an entity's 1–12ish strength tier; "rarity" (nadirlik) is a son's card tier.
- `clamp(v, lo, hi)` in the old code **rounds to an integer** (see helper section) — this matters for every formula below.

---

## Part A — Static game data (`src/rules.js`)

### A.0 Module role and cross-references

`src/rules.js` is a dependency-free module loaded by the server *and* shipped to the browser (the server's `/api/state` returns a `kurallar` (rules) object that embeds `RARITIES, SON_STATS, TUTKULAR, KAYNAKLAR, VARLIK_TURLERI, BAG_ETIKET, COSTS, ALANLAR, GUC_ETKILERI, GUC_SEVIYELERI, YILDIZ_MAX, DENGE, MODEL_ETIKET, MODELLER, OLUMLU_AJAN, BILGI_DALLARI, YASA_MEKANIKLERI, AFETLER, MUCIZELER, MUDAHALE_BEDEL, SINIFLAR, IKLIM, SEYAHAT_YONTEMLERI, …` — see `server.js kurallar()`).

Because `denge.js` imports `rules.js`, `rules.js` cannot import `denge.js`. It therefore has its **own local `tanimla()`** that only records definitions into an exported array `ON_TANIMLAR` (pre-definitions) and returns a plain object of defaults; `denge.js` at startup re-registers each with the real `tanimla(name, defs, existingObject)` which writes saved values *into the same object in place*. Consequence: every consumer that imported e.g. `KURAL` sees live values.

Main consumers (import graph, abbreviated):

| Export | Imported by |
|---|---|
| `clamp` | 25 modules (nearly all engine modules) |
| `SINIR` (LIMITS) | itibar, medeniyet, derin, sim, ufuk, yaratik, mudahale, olum, olumluler, gok, korku, hedef, ekonomi, yaratici, panteon, seyahat, otesi |
| `DENGE` (BALANCE) | firsatlar, denge, tools, agents, kozmos, world, sim, konsey, gok, korku, hedef, epoch, ekonomi, yaratici, panteon, otesi |
| `RARITIES` | denge, tools, agents, kitap, world, sim, tanriguc, oyuncu, epoch, kodeks, server |
| `VARLIK_TURLERI` (entity types) | dilmotoru, tools, agents, kitap, world, ufuk, defter, olumluler, oyuncu, kodeks, server |
| `canMax`, `ozMax` | tools, agents, derin, world, sim, tanriguc, oyuncu, epoch |
| `CAG_YIL` (years per epoch, live) | agents, kitap, world, sim, gok, kronik-onar, server |
| `KURAL` (CORE_RULES) | tools, world, olumluler, epoch |
| `COSTS` | denge, tools, agents, epoch, server |
| `KOZMIK_BEDEL`, `MUDAHALE_BEDEL` | denge, tools, epoch, server |
| `AFETLER` | tools, sim, tanriguc, epoch, yaratici |
| `MUCIZELER` | tools, epoch |
| `ALANLAR` | tools, agents, olumluler, tanriguc, epoch |
| `GUC_ETKILERI` | agents, world, tanriguc |
| `SON_STATS` | agents, kitap, epoch, yabanci, kodeks |
| `BILGI_DALLARI` | firsatlar, tools, agents, olumluler, kodeks |
| `SEYAHAT_YONTEMLERI` | denge, tools, ufuk, olumluler, oyuncu, ekonomi, seyahat |
| `IKLIM`, `iklimAgirligi` | kitap, derin, world, oyuncu / derin |
| `varlikHedefi` | sim | `varlikDurumu`: agents, world, sim, epoch |
| `eylemHakki` | agents | `yaratimBedeli`: tools | `gucVar`: tools, world, sim, panteon |
| `kapiyiGecer` | tools, panteon | `rarityAtLeast`: tools |
| `yildizSarti`, `sonrakiSinif`, `YUKSELIS_SARTI`, `YILDIZ_MAX`, `inisiyatif` | epoch (+ server for UI) |
| `iliskiEtiketT` | derin, world | `SINIFLAR`: ekonar, derin, world |
| `MODEL_VARSAYILAN`, `MODEL_YEDEK` | world (`modelFor`) | `EFFORT`: agents, kozmos, konsey |
| `girdiTemizle`, `esnekDeger`, `alanEsle` | tools, olumluler |
| `borcOku`, `borcAciklama` | medeniyet, olumluler, server |
| `OLUM_ALANLARI` | sim, korku | `OBUR_DUNYA_DESEN`: sim |
| `CANLI_TURLER` | tools, agents | `ANLATI_BAGLARI`: tools, agonar |

### A.1 Rarities (nadirlik) — `RARITIES`

Sons (god cards) have one of six rarities. `sira` is the ordinal used for gates and comparisons.

| Key (old) | EN key | Display (TR → EN) | Ordinal | Action points `ap` | Stat range on summon `stat` | Power-level cap `guc_tavan` | Essence regen / epoch `oz_yenilenme` | Agent turn limit `maxTurns` | Summon weight `agirlik` | Summon probability | Colour |
|---|---|---|---|---|---|---|---|---|---|---|---|
| yaygin | common | Yaygın → Common | 0 | 3 | 20–45 | 2 | 8 | 11 | 50 | 50% | `#9097a0` |
| seckin | uncommon | Seçkin → Uncommon | 1 | 3 | 30–55 | 3 | 10 | 13 | 27 | 27% | `#7fc489` |
| nadir | rare | Nadir → Rare | 2 | 3 | 40–65 | 5 | 12 | 15 | 14 | 14% | `#6fa0e6` |
| destansi | epic | Destansı → Epic | 3 | 3 | 50–80 | 7 | 15 | 17 | 7 | 7% | `#b48ae6` |
| efsanevi | legendary | Efsanevi → Legendary | 4 | 4 | 65–95 | 10 | 18 | 19 | 2 | 2% | `#e8ad48` |
| mitik | mythic | Mitik → Mythic | 5 | 5 | 80–100 | 12 | 24 | 21 | 0 (not tunable) | 0% — only via ascension | `#f07aa0` |

Notes:
- All numeric fields except `ad`/`sira` and mythic's weight are tunable (`RARITIES.<r>.ap|oz_yenilenme|stat.0|stat.1|guc_tavan|maxTurns|agirlik`); mythic `agirlik` is deliberately excluded from the editable list so mythic can never be summoned.
- `guc_tavan` = the maximum power level of entities the son can create (raised by stars, see A.3).
- `maxTurns` = the Agent-SDK step limit for one son turn.
- Colours come from the frontend (`public/style.css --r-*`, `public/core/bilesen.js RRENK`); the legendary card also has an animated conic-gradient border for mythic.
- Entities (non-son records) use the **same rarity vocabulary** derived from their power level via `varlikSinifi(g)` (A.17) with thresholds `CORE_RULES.tier_uncommon=3, tier_rare=5, tier_epic=7, tier_legendary=9, tier_mythic=11`.

#### Rarity gates (what each rarity may do) — `NADIRLIK_KAPI` (RARITY_GATES)

Each gate stores a rarity ordinal 0..5 (tunable). Defaults:

| Gate (old key) | EN key | Default min rarity | What it unlocks |
|---|---|---|---|
| tur_yer, tur_kaynak, tur_yerlesim, tur_tur, tur_halk, tur_olumlu, tur_efsane, tur_gelenek, tur_eser | create_place, create_resource, create_settlement, create_species, create_people, create_mortal, create_legend, create_tradition, create_artwork | 0 common | the matching creation tools |
| tur_esya, tur_yapit, tur_dil, tur_tarikat, tur_hizip, tur_kanun, tur_ruh | create_item, create_structure, create_language, create_cult, create_faction, create_law, create_spirit | 1 uncommon | creation tools |
| tur_gok, tur_teknoloji, tur_arac | create_celestial, create_knowledge, create_vessel | 2 rare | creation tools |
| tur_bolge, tur_kehanet, tur_olay, tur_ordu | create_region, create_prophecy, create_event, create_army | 3 epic | creation tools (army has no tool: engine-only) |
| tur_yasa | create_natural_law | 4 legendary | `yasa_koy` |
| tur_dis | create_outer_being | 5 mythic | no tool (engine-only) |
| etkile | influence_tools | 1 uncommon | `varligi_etkile` (influence entity), `secilmis_ilan_et` (declare chosen), `lanetle` (curse) |
| mucize | miracle_tool | 1 uncommon | `mucize` |
| ruh_kapla | spirit_cloak | 1 uncommon | `ruh_kapla` (only offered if a free spirit exists) |
| nadir_araclar | rare_tools | 2 rare | `ruya_gonder` (send dream), `afet_gonder` (send disaster), `bilgi_ver` (give knowledge), `savas_kiskirt` (incite war) |
| kutsal_dunya | holy_world | 2 rare | `kutsal_dunya_ilan` (only if >1 world) |
| antlasma | interworld_treaty | 2 rare | `antlasma_yap` (only if >1 world) |
| yabanci_savas | foreign_god_war | 2 rare | `yabanci_tanriyla_savas` tool and spontaneous son-vs-foreign-god war (panteon.js) |
| can_al | take_life | 2 rare | `can_al` (and only if `DEATH.take_life_per_epoch > 0`) |
| kapi_muhurle | seal_gate | 3 epic | `kapi_muhurle` |
| yildiz_tutustur | rekindle_star | 3 epic | `yildiz_tutustur` (only if a dead/black/remnant star exists) |
| sizinti_dik | stitch_leak | 3 epic | `sizinti_dik` |
| efsanevi_araclar | legendary_tools | 4 legendary | `donustur` (transform), `yok_et` (destroy), `evlat_dogur` (bear child) |
| yatak_ac | open_cosmic_bed | 4 legendary | `yatak_ac` (open cosmic travel-resource deposit) |
| dunya_dogur | birth_world | 4 legendary | `dunya_dogur` |
| yildiz_as | hang_extinguish_star | 5 mythic | `yildiz_as`, `yildiz_sondur` |

The creation-type gate is also exposed as a live getter `VARLIK_TURLERI[type].tier` (A.8).

Summarised per rarity (defaults): Common = basic land/life/culture creations; Uncommon adds items, structures, languages, cults, factions, laws, spirits, influence/curse/chosen, miracle, spirit-cloak; Rare adds celestial bodies, knowledge, vessels, dream/disaster/knowledge/incite-war, holy world, treaties, foreign-god war, take-life; Epic adds regions, prophecies, events, seal gate, rekindle star, stitch leak; Legendary adds natural laws, transform/destroy/bear-child, open cosmic bed, birth world, +1 base AP; Mythic adds hang/extinguish stars, +2 base AP.

### A.2 Son stats (SON_STATS), passions (TUTKULAR), resources (KAYNAKLAR)

Nine stats, 1–100, grouped Body/Mind/Spirit. The `etki` (effect) text is shown in the UI; three of them are computed from live rules.

| Key | EN | Group | Mechanical meaning |
|---|---|---|---|
| guc | strength | Body (Beden) | Weight in strength duels; added to the war strength of armies that worship him (`WORLD_WAR_STRENGTH.patron_strength_divisor`). |
| dayaniklilik | endurance | Body | Max HP = `CORE_RULES.max_hp_base + (max_hp_per_endurance/100) × endurance` (default 50 + 1.5×E). Increases per-epoch healing (`WORLD_EPOCH_TRANSITION.heal_endurance_divisor`). |
| ceviklik | agility | Body | Initiative: who acts first in the epoch. |
| bilgelik | wisdom | Mind (Zihin) | Wisdom duels; sees the world more widely (more context lines); harvests resources more efficiently. |
| kurnazlik | cunning | Mind | Cunning duels, initiative, inciting war. |
| irade | will | Mind | Resistance to punishments and curses; with low loyalty → disobeys orders. |
| yaraticilik | creativity | Spirit (Ruh) | Lowers creation cost (at 100 creativity by `CORE_RULES.creativity_discount_pct`%, default 40%). |
| karizma | charisma | Spirit | Cult growth, stealing worshippers via dreams, influence in sibling relations. |
| kudret | might | Spirit | Max essence = `CORE_RULES.max_essence_base + (max_essence_per_might/100) × might` (default 40 + 1.6×M). "The store needed for great creations." |

Passions (tutku), 0–100:

| Key | EN | Meaning |
|---|---|---|
| sadakat | loyalty | Tendency to obey the father's orders. |
| hirs | ambition | Pursuit of power and faith; if high, challenges siblings. |
| ofke | wrath | Tendency toward destructive creations and hostility. |
| merhamet | mercy | Compassion toward mortals and siblings. |

Son resources (KAYNAKLAR — UI/prompt single source):

| Key | EN | Meaning |
|---|---|---|
| can | HP | If it reaches 0 the son falls asleep for two epochs (tunable per cause: `SON_TOOLS.challenge_sleep_epochs`, `foreign_war_sleep_epochs`; 1 epoch with the Reviving power). |
| oz | essence | Fuel of creation. Refilled each epoch by rarity and faith; also gained by harvesting resources. |
| inanc | faith | Flows from worshipping cults, peoples and settlements. Every 10 faith = +1 essence per epoch (`WORLD_EPOCH_TRANSITION.faith_essence_divisor`); also gives a share to the Creator. |
| un | renown | Grows with creations, victories and fulfilled prophecies. Mortals love the chosen of a renowned god more. Decays: `ESSENCE.renown_keep_pct` (95%) kept per epoch. |
| xp | experience | Levels up; levels unlock stats and powers (new power at levels 3 and 5). |

### A.3 Levels, stars (★) and ascension

```
xpThreshold(level)   = CORE_RULES.xp_per_level × level            # xpEsik; default 100 × level
YILDIZ_MAX           = 5                                          # constant, not tunable
starRequirement(n)   = {                                          # yildizSarti(hedef=n), for going to ★n
    level:   n × CORE_RULES.star_level_step − 1,                  # default 2n−1 → ★2:3, ★3:5, ★4:7, ★5:9
    renown:  (n − 1) × CORE_RULES.star_renown_step,               # default 15(n−1)
    essence: CORE_RULES.star_essence_base + n × CORE_RULES.star_essence_step }  # default 15 + 10n (paid by the Creator)
powerCap(son)        = RARITIES[son.rarity].power_cap + floor((son.stars − 1) / CORE_RULES.stars_per_power_cap)   # gucTavani; stars default 1
nextRarity(r)        = RARITY_KEYS[RARITIES[r].ordinal + 1] or null                       # sonrakiSinif
```

Add-star action (epoch.js `yildizEkle`, Creator action): requires son not dead, `stars+1 ≤ 5`, `level ≥ req.level`, `renown ≥ req.renown`; Creator pays `req.essence`; every stat `+= GOD_ACTIONS.star_stat_gain` (clamped 1..100); `stars += 1`; HP reset to `canMax`; chronicle line.

Ascension (`yukselt`): requires not dead, a next rarity exists, `stars == 5`, `level ≥ ASCENSION.level (9)` and `renown ≥ ASCENSION.renown (90)`; Creator pays `ASCENSION.essence_cost (90)`. Then (transaction): for each stat `stat = clamp(max(stat, randInt(newLo,newHi)),1,100)`; rarity := next; stars := 1; HP := canMax; essence := ozMax; existence `+= GOD_ACTIONS.ascension_existence`; insert an engine "legend" record (subtype "ascension myth", spread `GOD_ACTIONS.ascension_myth_spread`, power level = new rarity's power cap, `bekliyor=1` so Fate names it), link legend→son `anlatir` (tells-of), chronicle + broadcast. Mythic is reachable only this way.

### A.4 Existence (varoluş/varlık) — gods exist through faith, renown and anchors

Existence is 0–100 per son.

```
existenceTarget({faith, renown, anchorAlive, worshipperCount=1}) =               # varlikHedefi
  clamp( CORE_RULES.existence_base                                               # 25
       + min(existence_faith_cap (40),  faith  / existence_faith_divisor (2))
       + min(existence_renown_cap (25), renown / existence_renown_divisor (4))
       + (anchorAlive ? existence_anchor_bonus (10) : −existence_anchorless_penalty (20))
       − (worshipperCount > 0 ? 0 : existence_no_worshipper_penalty (15)),
       0, 100)

existenceState(v) =                                                               # varlikDurumu
  v ≥ existence_radiant (80) → {k:'parlak'  'Radiant',   effect:"+3 essence per epoch"}   # actual value WORLD_EPOCH_TRANSITION.radiant_essence_bonus
  v ≥ existence_solid   (30) → {k:'saglam'  'Solid',     effect:"Normal."}
  v ≥ existence_faded   (12) → {k:'solgun'  'Faded',     effect:"One action point less; starts forgetting its body."}
  else                       → {k:'unutuluyor' 'Being forgotten', effect:"Cannot act. Needs a worshipper or the god's blessing."}
```

Epoch transition (sim.js): `anchorAlive = son has no anchor OR anchor record durum ∈ {kanon, gerceklesti}`; worshipperCount = active `tapar` links from canon entities to the son; existence moves toward target by at most `WORLD_EPOCH_TRANSITION.existence_step` (10) per epoch; state changes go to the chronicle. Fading-death: a son with existence ≤ `DEEP_LIFE.fading_threshold` (10) accumulates fading epochs; after `DEEP_LIFE.fading_death_epochs` (3) it dies (derin.js `tanrilarinKaderi`).

Existence modes (VAROLUS_HALLERI, narrative only): `somut` concrete, `yarı-somut` semi-concrete, `kavramsal` conceptual, `yansıma` reflection, `dağınık` scattered.

### A.5 Action points

```
actionPoints(son) =                                                    # eylemHakki
  ap = RARITIES[son.rarity].ap
     + (hasPower(son,'ek_eylem') ? CORE_RULES.tireless_extra_action : 0)      # 1
     + (son.stars ≥ 5            ? CORE_RULES.max_star_extra_action : 0)      # 1
  if son.existence != null and son.existence < CORE_RULES.existence_solid:   # 30
      ap −= CORE_RULES.faded_action_loss                                     # 1
  floor = (son.existence != null and son.existence < CORE_RULES.existence_faded) ? 0 : CORE_RULES.min_actions  # 12 / 1
  return max(floor, ap)
```

Also: the son's first *living* creation in an epoch (types in `CANLI_TURLER` = people, mortal, settlement, species, cult, faction) costs no action point if `SON_TOOLS.free_living_creation > 0`.

### A.6 Powers (GUC_ETKILERI) and power unlock levels

Each son has **three personal powers** (name/description written by the LLM at summon; the *effect key* and optional *param* are mechanical). They unlock at levels `GUC_SEVIYELERI = [1, 3, 5]` (each tunable as `POWER_UNLOCK_LEVELS.power_N_unlock_level`).

```
openPowers(son)            = son.powers.filter((p, i) => son.level ≥ GUC_SEVIYELERI[i])      # acikGucler
hasPower(son, effect, param=null) = openPowers(son).some(p => p.effect == effect and (param == null or p.param == param))  # gucVar
```

| Effect key | EN name (TR) | Param | UI text | Where implemented / actual tunable |
|---|---|---|---|---|
| ucuz | Master Creator (Usta yaratıcı) | entity type | "Creations of the chosen type are 40% cheaper." | tools.js: creation cost × `CORE_RULES.cheap_power_cost_pct` (60%) |
| meydan | Duel Master (Düello ustası) | stat key | "+15 in duels using the chosen stat." | tools.js challenge: `SON_TOOLS.challenge_power_bonus` (15) when duel field == param |
| oz_pinari | Essence Spring (Öz pınarı) | — | "+4 essence every epoch." | sim.js regen: `WORLD_EPOCH_TRANSITION.essence_spring_bonus` (4) |
| inanc_carpani | Worshipped (Tapınılan) | — | "Faith ×1.5." | world.js faith: `FAITH.multiplier_power_pct` (150) |
| ek_eylem | Tireless (Yorulmaz) | — | "+1 action point every epoch." | rules.js eylemHakki: `CORE_RULES.tireless_extra_action` |
| dokunulmaz | Untouchable (Dokunulmaz) | — | "Duels and curses against him −15." | `SON_TOOLS.challenge_untouchable` (15), `SON_TOOLS.curse_untouchable_resist` (15), mortal defy: `MORTAL_TOOLS.defy_god_untouchable` |
| fisilti | Dream Whisper (Rüya fısıltısı) | — | "+25 success when sending dreams." | `SON_TOOLS.dream_whisper_bonus_pct` (25) |
| savas_babasi | War Father (Savaş babası) | — | "Contribution to the war strength of armies that worship him ×2." | sim.js: `WORLD_WAR_STRENGTH.war_father_mult` (2) |
| hasat | Harvester (Hasatçı) | — | "Double essence when harvesting resources." | `SON_TOOLS.harvest_power_mult` (2) |
| kahin | Seer (Kâhin) | — | "Prophecies half price; fulfilled-prophecy reward ×2." | tools.js treats it as `ucuz` for type `kehanet` → cost × 60% (**not** half; text is stale); reward × `FATE.seer_power_mult` (2) |
| dirilis | Reviving (Dirilen) | — | "If his HP runs out he sleeps only one epoch." | `SON_TOOLS.reviving_sleep_epochs` (1); panteon.js foreign war hardcodes `1` |
| bereket | Bounty-giver (Bereket veren) | — | "Peoples and settlements that worship him grow twice as fast." | sim.js growth × `WORLD_EPOCH_TRANSITION.bounty_power_growth_mult` (2) when fertility ≥ `bounty_power_min_fertility` |
| lanetci | Curser (Lanetçi) | — | "Curses half price and 50% more severe." | `SON_TOOLS.curser_cost_pct` (50), `curser_severity_pct` (150) |

`SUMMONING.power_effect_cap` limits how many sons in the pantheon carry the same effect (extra choices are reassigned to the least-used effect).

### A.7 Domains (ALANLAR)

Sons have two domains (alan1, alan2) from a deliberately non-classical list of **40**. Creations "in domain" cost `CORE_RULES.cost_in_domain_pct` (60%), out-of-domain `cost_out_of_domain_pct` (130%).

| TR | EN | TR | EN | TR | EN | TR | EN |
|---|---|---|---|---|---|---|---|
| Deniz | Sea | Ateş | Fire | Toprak | Earth | Gök | Sky |
| Fırtına | Storm | Ölüm | Death | Yaşam | Life | Rüya | Dream |
| Zaman | Time | Işık | Light | Gölge | Shadow | Savaş | War |
| Zanaat | Craft | Bilgi | Knowledge | Aşk | Love | Hile | Trickery |
| Av | Hunt | Bitki | Plants | Kemik | Bone | Kan | Blood |
| Ses | Sound | Taş | Stone | Buz | Ice | Delilik | Madness |
| Ticaret | Trade | Yol | Road | Veba | Plague | Hasat | Harvest |
| Ay | Moon | Güneş | Sun | Yıldız | Star | Yalan | Lies |
| Yemin | Oath | Bellek | Memory | Açlık | Hunger | Cam | Glass |
| Tuz | Salt | Kül | Ash | Sınır | Border | Uyku | Sleep |

Special domain sets:
- **Death domains** (`OLUM_ALANLARI`): Death, Bone, Memory, Sleep, Ash. On every named mortal's death, every son having one of these as alan1/alan2 gets `essence = min(ozMax, essence + WORLD_EFFECTS.death_domain_essence)` and `existence = min(100, existence + WORLD_EFFECTS.death_domain_existence)` (sim.js `olumSonrasi`).
- **Madness** domain: per epoch essence `avg_leak / COSMIC_HORROR.madness_son_essence_divisor` and existence `+COSMIC_HORROR.madness_son_existence_gain` (korku.js).
- **Underworld pattern** (`OBUR_DUNYA_DESEN`, case-insensitive regex over a region's `name + subtype`): `ölü|yeraltı|öbür|cehennem|cennet|ruhlar|dip|mezar|ahiret|karanlık kat|alt dünya` (dead / underground / other-world / hell / heaven / spirits / depths / grave / afterlife / dark layer / lower world). A dying mortal's soul gets a `ruhu_indi` (soul-descended) link to the first matching region on its own world, else to one on a world of type `olu` (dead world), else none. LANGUAGE-SPECIFIC: replace with an English keyword list (dead, underworld, hell, heaven, spirit, abyss, grave, afterlife, netherworld…) or, better, an explicit `is_underworld` flag on regions.
- **Domain matching** (`alanEsle(value, fallback)`): lower-case (Turkish locale) trimmed value; exact match, else first domain where either string contains the other, else fallback. LANGUAGE-SPECIFIC casing: use case-insensitive Unicode matching.

### A.8 Entity type catalogue (VARLIK_TURLERI)

`stat: [key, label, min, max]`; `tier` = live getter → gate `RARITY_GATES.create_<type>`; `taban` (base cost) = live getter → `CREATION_BASE_COST.<type>`; `konum` = allowed parent types for `konum_id` (location); `konum_zorunlu` = location required.

| Type (old) | EN | Tool | Default tier | Base cost | Allowed locations | Loc. required | Examples (EN) | Stats (key EN range) |
|---|---|---|---|---|---|---|---|---|
| bolge | Region | bolge_yarat (create_region) | epic | 20 | region | no | continent, inland sea, desert belt, archipelago, underworld | genislik breadth 0–100; tehlike danger 0–100; bereket fertility 0–100; buyu magic density 0–100 |
| yer | Place | yer_yarat | common | 6 | region, place | yes | mountain, forest, river, lake, cave, ruin, island, swamp, pass, well | tehlike danger; bereket fertility; gizem mystery (0–100) |
| kaynak | Resource | kaynak_yarat | common | 7 | region, place | yes | ore vein, magical substance, healing herb, sacred spring, rare crystal, bone bed | bolluk abundance; deger value; kudret might (0–100) |
| yerlesim | Settlement | yerlesim_kur (found_settlement) | common | 6 | region, place | yes | village, port city, castle, monastery, nomad camp, capital | nufus population 10–2,000,000; refah prosperity; savunma defense; inanc piety (0–100) |
| tur | Species | tur_yarat | common | 5 | region, place | no | animal, plant, fungus, monster, spirit species | can HP 1–1000; guc strength; ceviklik agility; zeka intelligence; tehlike danger (0–100) |
| halk | People | halk_yarat | common | 9 | region, place | yes | race, tribe, caste, mortal lineage | nufus population 100–50,000,000; savascilik martiality; buyu magic; zanaat craft; inanc piety (0–100) |
| olumlu | Mortal | olumlu_yarat | common | 5 | region, place, settlement | yes | hero, king, seer, bandit, artisan, saint | can HP 1–300; guc strength; ceviklik agility; akil intellect; karizma charisma (0–100); yas age 0–50,000; omur lifespan 1–50,000 |
| esya | Item | esya_dov (forge_item) | uncommon | 10 | region, place, settlement | no | weapon (sword, spear, bow), armour, shield, crown, mirror, book, seal, instrument, tool, holy relic | hasar damage; koruma protection; kudret might; lanet curse (0–100) |
| yapit | Structure | yapit_insa (build_structure) | uncommon | 9 | region, place, settlement | yes | temple, tower, bridge, wall, monument, tomb, observatory, harbour, mine, library | ihtisam splendor; saglamlik durability; islev function (0–100) |
| dil | Language | dil_yarat | uncommon | 8 | — | no | spoken language, sacred language, script, sign language, merchant cant, language of the dead | yayginlik spread; karmasiklik complexity; kutsallik sacredness (0–100) |
| efsane | Legend | efsane_anlat (tell_legend) | common | 4 | — | no | lullaby, taboo, proverb, founding myth, ghost story | yayginlik spread |
| gelenek | Tradition | gelenek_kur | common | 5 | — | no | festival, taboo, funeral rite, initiation, oath ceremony, seasonal offering | yayginlik spread; katilik rigidity |
| tarikat | Cult | tarikat_kur | uncommon | 9 | region, place, settlement | yes | temple order, secret sect, priest caste | murit followers 1–10,000,000; bagnazlik zealotry; etki influence |
| hizip | Faction | hizip_kur | uncommon | 9 | region, place, settlement | yes | kingdom, guild, knightly order, pirate league, dynasty | guc military strength; servet wealth; nufuz sway |
| gok | Celestial Body | gok_cismi_as (hang_celestial) | rare | 14 | — | no | star, constellation, moon, comet, wandering light, wound in the sky | parlaklik brightness; etki influence |
| eser | Artwork | eser_yarat | common | 5 | region, place, settlement | no | folk song, epic, statue, fresco, play, book, dance, lament, weaving | un renown; etki influence |
| kanun | Law | kanun_koy (decree_law) | uncommon | 7 | region, place, settlement | no | penal code, inheritance rule, trade law, worship ban, blood-feud custom | katilik rigidity; adalet justice |
| ruh | Spirit | ruh_cagir (summon_spirit) | uncommon | 8 | region, place, settlement | no | ghost, ancestor spirit, haunt, guardian spirit, lost soul | guc strength; huzursuzluk unrest |
| teknoloji | Knowledge | bilgi_ilham_et (inspire_knowledge) | rare | 12 | — | no | agriculture, metallurgy, seafaring, writing, architecture, medicine, school of magic, art of war, astronomy, trade practice | seviye level 1–10; yayginlik spread 0–100 |
| kehanet | Prophecy | kehanet_soyle (utter_prophecy) | epic | 10 | — | no | prophecy, doom sign, cursed word | kesinlik certainty |
| olay | Event | olay_baslat (start_event) | epic | 18 | region, place, settlement | no | war, plague, flood, famine, migration, uprising, catastrophe | siddet severity |
| arac | Vessel | arac_yarat | rare | 14 | region, place, settlement | no | ship (light-sailer, bone-hulled, generation ship), ancient gate, cosmic mount, divine bridge | hiz speed; menzil range; murettebat crew 0–100,000; zirh armour; tuhaflik strangeness |
| dis | Outer Being | — (engine only) | mythic | 0 | region, place | no | something from outside the cosmos, the unnamed thing | buyukluk size; ilgi interest; etki influence |
| ordu | Army | — (engine only) | epic | 0 | region, place, settlement | no | army, legion, raider band, holy guard, fleet | buyukluk soldiers 10–10,000,000; moral morale; techizat equipment; deneyim experience |
| yasa | Natural Law | yasa_koy (decree_natural_law) | legendary | 30 | — | no | return of the dead, price of magic, order of the seasons | (no stats; mechanic via `mekanik:` tag, see A.12) |

`VARLIK_TUR_KEYS` = the 25 keys in this order. Creation tools are offered only if `tdef.arac` exists and `rarityAtLeast(son.rarity, tdef.tier)`.

Engine-assigned subtype vocabularies (`MOTOR_ALT_TURLERI`), stored as Turkish strings in old data — translate to English enums:
- event (`OLAY_ALT_TURLERI`): savaş war, muharebe battle, kuşatma siege, büyü fırtınası magic storm, deprem earthquake, sel flood, veba plague, kuraklık drought, fırtına storm (disaster subtypes are the Turkish display name; tags keep the key).
- structure: tapınak temple, sur wall, kütüphane library, kozmik arşiv cosmic archive.
- faction: isyancılar rebels, tüccar loncası merchant guild, rahipler meclisi priests' council, savaşçı birliği warrior brotherhood, dünyalar arası federasyon inter-world federation.
- army: halk ordusu people's army, kutsal muhafız holy guard, paralı ordu mercenary army.
- language: lehçe dialect, ilkel dil primitive language.

### A.9 Links (bağ) between records — BAG_TURLERI / BAG_ETIKET

Directed graph edges between sons (`o`), entities (`v`), the god (`t`), foreign gods (`y`), worlds (`d`). 50 types. "Narrative" links (`ANLATI_BAGLARI`) are the only ones `bag_kur` (create_link tool) and graph repair may create; mechanical links are created only by their own tools/engine.

| Old | EN key | Display (TR → EN) | Narrative? |
|---|---|---|---|
| icinde | inside | içinde → inside | |
| yasar | lives_in | yaşar → lives in | |
| tapar | worships | tapar → worships | |
| dusman | enemy | düşman → enemy of | |
| muttefik | ally | müttefik → ally of | |
| soyundan | descends_from | soyundan → descends from | yes |
| korur | protects | korur → protects | |
| yonetir | rules | yönetir → rules | |
| sahip | owns | sahibi → owner of | |
| dovdu | forged | dövdü → forged | |
| oldurdu | killed | öldürdü → killed | |
| lanetledi | cursed | lanetledi → cursed | |
| kutsadi | blessed | kutsadı → blessed | |
| kaynagi | source_of | kaynağı → source of | yes |
| anlatir | tells_of | anlatır → tells of | yes |
| yok_etti | destroyed | yok etti → destroyed | |
| sever | loves | sever → loves | yes |
| korkar | fears | korkar → fears | yes |
| avlar | hunts | avlar → hunts | |
| ticaret | trades_with | ticaret yapar → trades with | |
| kehanet_eder | prophesies | kehanet eder → prophesies | yes |
| neden_oldu | caused | neden oldu → caused | yes |
| kutlar | celebrates | kutlar → celebrates | yes |
| yasaklar | forbids | yasaklar → forbids | yes |
| konusur | speaks | konuşur → speaks | |
| uretti | produced | üretti → produced | |
| insa_etti | built | inşa etti → built | |
| gocetti | migrated_to | göç etti → migrated to | |
| kesfetti | discovered | keşfetti → discovered | |
| ruhu_indi | soul_descended_to | ruhu indi → soul descended to | |
| taraf | party_to | tarafı → party to | |
| uyesi | member_of | üyesi → member of | |
| bilirdi | knew | bilirdi → used to know | |
| konusurdu | spoke | konuşurdu → used to speak | |
| bilir | knows | bilir → knows | |
| harac_oder | pays_tribute | haraç öder → pays tribute to | |
| ilgili | related | ilgili → related to | yes |
| esir | holds_captive | esir tutar → holds captive | |
| casus | spy_network | casus ağı kurdu → set a spy network in | |
| pesinde | pursues | peşinde → in pursuit of | yes |
| yoldas | companion | yoldaşı → companion of | yes |
| hasim | rival | hasmı → rival of | |
| ustasi | master_of | çırağı → apprentice of (sic: key "master", label "apprentice") | |
| komutan | commands | komuta eder → commands | |
| parcasi | part_of | parçası → part of | yes |
| yolcusu | passenger_of | yolcusu → passenger of | |
| kaptan | captain_of | kaptanı → captain of | |
| evcil | tamed | evcilleştirdi → tamed | |
| ateskes | truce | ateşkes yaptı → made truce with | |
| borclu | owes | borçlu → owes (debtor → creditor) | |

Debt link description format (`borcAciklama(amount, what, due)`) = `"{amount} {what}; vade Çağ {due}"` (e.g. "12 gümüş; vade Çağ 15" = "12 silver; due Epoch 15"); after the due date passes, `" · vadesi geçti"` ("overdue") is appended. `borcOku(link)` parses it with `/^(\d+) (.*?); vade Çağ (\d+)/` → `{amount, what, due, overdue}`. LANGUAGE-SPECIFIC: in the new app store `amount`, `what`, `due_epoch`, `overdue` as structured link fields instead of parsing text.

### A.10 Costs (essence) — static cost tables

All are tunable (registry rows in Part C). Paid from the Creator's essence (tanri_oz) unless marked "(son)" — those are the base cost of a son's tool, further modified by `yaratimBedeli` or tool-specific formulas.

`COSTS` (God and son costs; editable range 0–500):

| Old | EN | Default | Meaning |
|---|---|---|---|
| cagirma | summon_son | 30 | Creator summons a new son |
| kutsa_oz | bless_essence | 15 | Bless: give the son essence (`GOD_ACTIONS.bless_essence_amount`) — also used for the existence blessing |
| kutsa_can | bless_hp | 15 | Bless: fully heal |
| kutsa_stat | bless_stat | 40 | Bless: +`GOD_ACTIONS.bless_stat_amount` to one stat |
| yildirim | lightning | 10 | Punish: lightning (HP loss `GOD_ACTIONS.lightning_hp_pct` % of max) |
| vahiy | revelation | 25 | An entity created by the Creator's own hand |
| donustur | transform | 15 | (son) base of transform |
| evlat_dogur | bear_child | 60 | (son) bear a child son |
| yok_et | destroy | 25 | (son) base of destroy |
| etkile | influence | 6 | (son) base of influence entity |
| lanet | curse | 12 | (son) base of curse |
| ruya | dream | 10 | (son) base of send dream |
| kiskirt | incite_war | 10 | (son) base of incite war |
| secilmis | declare_chosen | 14 | (son) declare a chosen one |
| ahit | covenant | 0 | (son) covenant |
| capa | anchor | 0 | (son) change anchor |

`DENGE` (Major actions and essence; editable 0–1000 except `oz_tavan` 0–100000, `kiyamet_esik` 1–1000, `kiyamet_hiz` 0–300):

| Old | EN | Default | Meaning |
|---|---|---|---|
| tanri_oz_yenilenme | creator_essence_regen | 20 | Creator's automatic essence per epoch |
| oz_tavan | creator_essence_soft_cap | 800 | Above it the Creator's income is reduced to `ESSENCE.over_cap_income_pct` (50%) and `ESSENCE.overflow_pct` (8%) of the excess leaks into the world each epoch (as fertility, see ESSENCE) |
| dirilis | resurrection | 150 | Resurrect a dead son |
| dunya | create_world | 120 | Creator creates a new world |
| dunya_dogur | birth_world | 70 | Legendary/mythic son births a world |
| konsey | council | 20 | Creator convenes the council |
| ruya | dream | 8 | Send a dream to a mortal |
| uyandir | awaken_peoples | 35 | Awaken the peoples (LLM generates peoples) |
| kiyamet_esik | apocalypse_threshold | 100 | Doomsday clock value at which apocalypse strikes (warnings at 50% and 80%: `APOCALYPSE.warning_1_pct/2_pct`) |
| kiyamet_hiz | apocalypse_speed | 100 | Percentage applied to the per-epoch clock increase (0 = clock stops) |
| bastir | suppress_revolt | 20 | Creator suppresses a son's uprising |
| baslangic_oz | creator_starting_essence | 150 | Creator's starting essence in a new cosmos |

`KOZMIK_BEDEL` (Cosmic actions; 0–500): yildiz ignite_star 80, muhur seal_gate 30, temizle cleanse_leak 80, unut forget_world 20, gok sky_event 50, tutustur rekindle_dead_star 60, ruh spirit_cloak 15, sefer legendary_expedition 30. Sons pay a percentage of these (`SON_TOOLS.cosmic_*_pct`).

`MUDAHALE_BEDEL` (Interventions; 0–300): mucize miracle 15, afet disaster 20, bilgi teach_knowledge 12, lanet curse 15. Sons pay `SON_TOOLS.intervention_cost_pct` % of these.

`YARATIM_TABANI` (CREATION_BASE_COST) — base cost per type, see A.8 column "Base cost".

### A.11 Knowledge branches (BILGI_DALLARI)

Every knowledge record has a branch tag `dal:<key>`; knowers get a mechanical edge. 18 branches:

| Key | EN | Effect (as documented; numbers come from the respective registries) |
|---|---|---|
| tarim | Agriculture | Knowers' population grows 50% faster; famine and drought strike at half severity. |
| metalurji | Metallurgy | +15 damage/protection to weapons and armour they produce. |
| denizcilik | Seafaring | Trade, war and migration with communities beyond the sea. |
| yazi | Writing | Their languages grow complex; what they know spreads to partners twice as fast. |
| mimarlik | Architecture | +20 splendor and durability to their structures; earthquake-resistant. |
| tip | Medicine | Plagues strike at half severity; mortals' lifespan +20. |
| buyu | Magic | Magic stat +10; items they produce +10 might. |
| savas | Art of War | +12 war strength. |
| gokbilim | Astronomy | Read the star of the epoch: sense disasters in advance, suffer them at half severity. |
| ticaret | Trade | Double prosperity from trade routes. |
| gokyuzu_seyri | Sky Navigation | Can discover inter-world routes; risk of getting lost on journeys halved. |
| gemi_yapimi | Shipbuilding | Can produce inter-world ships (vessels). |
| kapi_bilimi | Gate Science | Can open and close ancient gates; gate routes complete in one epoch. |
| yol_biliciligi | Pathfinding | Can fold space: with the cosmic resource, routes drop to one epoch. |
| bosluk_yasami | Void Living | Can found colonies on worlds with thin or no atmosphere; fewer losses on journeys. |
| olumsuzluk | Pursuit of Immortality | Knowers' mortals reach for immortality; those who succeed don't age but gods see them as a threat. |
| biyobuyu | Biomancy | Combines and alters living things: can weave chimeras, direct mutations. |
| yasak | Forbidden Knowledge | Great power: war +15, magic +15, forces gates. Price: knowers' sanity drops each epoch, leak flows into their world; Fate watches. |

(The texts are UI/prompt strings; several numbers are duplicated as literals in code paths rather than tunables — flagged in the bug list.)

### A.12 Natural laws (YASA_MEKANIKLERI) — mechanic keys for `yasa` records

| Key | EN | Effect |
|---|---|---|
| yok | none | Narrative only; no mechanical effect. |
| olumsuzluk | immortality | Mortals don't age; population grows at half speed (`WORLD_EPOCH_TRANSITION.immortality_law_growth_pct`). |
| kisa_omur | short_life | Mortals age twice as fast (`WORLD_EFFECTS.short_life_aging_mult`); population grows 50% faster (`short_life_law_growth_pct`). |
| olu_doner | dead_return | Fallen heroes return as ghosts half the time (`WORLD_ENGINE.ghost_chance`). |
| buyu_bedeli | magic_price | Peoples with high magic pay part of their population to magic every epoch (`WORLD_EFFECTS.magic_price_*`). |
| savas_yasagi | war_ban | Wars break out half as often but are twice as bloody (`DEEP_WORLD.battle_chance_war_ban`). |
| bereket | bounty | All lands' fertility rises every epoch (`WORLD_EPOCH_TRANSITION.bounty_law_fertility`). |
| kuraklik | drought | All lands' fertility falls every epoch (`drought_law_fertility`). |
| deniz_yasagi | sea_ban | Seas cannot be crossed; seafaring is useless. |
| tek_dil | one_language | Languages spread twice as fast through conquest and trade (`WORLD_ENGINE.language_spread_chance`). |
| afet | disasters | Natural events happen twice as often (`WORLD_EFFECTS.disaster_law_mult`). |

### A.13 Travel methods (SEYAHAT_YONTEMLERI)

`sure` (duration, epochs, tunable 1–20) and `tehlike` (danger 0–100, tunable); `bilgi` = required knowledge branch; `arac` = required vessel kind (Turkish words: kapı gate, gemi ship, binek mount, köprü bridge); `bedel` = narrative price.

| Key | EN | Duration | Danger | Requires knowledge | Requires vessel | Price (narrative) |
|---|---|---|---|---|---|---|
| kapi | Ancient gate | 1 | 25 | gate science | gate | A sacrifice or a true name is needed to open it. |
| katlama | Space folding | 1 | 30 | pathfinding | — | Consumes the cosmic travel resource; addictive (`ECONOMY.fold_*`). |
| yelken | Light sail | 3 | 20 | shipbuilding | ship | Slow but free; snaps if the star dies. |
| binek | Cosmic mount | 2 | 35 | — | mount | Requires taming a void creature. |
| ruya | Dream journey | 1 | 45 | magic | — | Body stays, soul goes; may not return. |
| olu_nehri | River of the dead | 1 | 40 | — | — | For the living the price is memory loss. |
| kopru | Divine bridge | 1 | 10 | — | bridge | Collapses if the god who built it sleeps or dies. |
| sapan | Slingshot orbit | 2 | 25 | sky navigation | ship | Only opens in epochs when planets align (`TRAVEL.alignment_period`). |
| yutulma | Being swallowed | 2 | 60 | — | — | Carried inside a cosmic creature; exit not guaranteed. |

### A.14 Disasters (AFETLER) and miracles (MUCIZELER)

Effect texts are generated from current `INTERVENTION_EFFECTS` (old `MUDAHALE`) values. Applied by `mudahale.js` (Creator via epoch.js `afet/mucize`, sons via tools `afet_gonder/mucize`, the Creator's wrath via yaratici.js, natural events via sim.js).

Disasters:

| Key | EN | Effect (defaults) | Knowledge mitigation |
|---|---|---|---|
| deprem | Earthquake | Population −10% (`earthquake_population_loss`), structures' durability −25 (`earthquake_durability_loss`); collapsed structures are destroyed. Each named mortal where it strikes dies with `earthquake_mortal_death_chance` (12%). | Architecture: structure damage × `architecture_quake_severity` (50%). Astronomy: whole disaster × `astronomy_disaster_severity` (50%). |
| sel | Flood | Prosperity −12, population −5%; afterwards fertility +5. Named-mortal death 8%. | Astronomy. |
| veba | Plague | Population −18%, followers −10%. Named-mortal death 15% (medicine mitigates). | Medicine × `medicine_plague_severity` (50%); Astronomy. |
| kuraklik | Drought | Fertility −20, population −6%. Named-mortal death 4%. | Agriculture × `agriculture_drought_severity` (50%); Astronomy. |
| firtina | Storm | Defense −10, prosperity −8. Named-mortal death 5%. | Astronomy. |

Common: a disaster record (event) is created with power level `clamp(round(severity / disaster_event_power_divisor), disaster_event_power_min, disaster_event_power_max)` (12 / 2 / 9). Surviving named mortals are wounded with `disaster_injury_chance` (30%), losing `disaster_injury_hp` (25) scaled by severity. Death text per type (`AFET_OLUM`, mudahale.js): earthquake "was buried under the rubble", flood "drowned in the flood", plague "died of the plague", drought "starved in the drought", storm "perished in the storm".

Miracles:

| Key | EN | Effect (defaults) |
|---|---|---|
| sifa | Healing | Population/followers +10% (`healing_growth_pct`), curse lifted, a mortal's HP set to 100 (`healing_hp`, capped by `LIMITS.hp_cap`); son tool also adds sanity (`SON_TOOLS.healing_sanity`). |
| bereket | Bounty | Fertility +20 (`bounty_fertility_gain`) or, for targets without fertility, prosperity +15 (`bounty_prosperity_gain`); resources: abundance +25 (`bounty_abundance_gain`). |
| baris | Peace | All of the target's hostilities end. |
| koruma | Protection | Defense +20 (`protection_defense_gain`); protected from the next disaster. |

A miracle landing on a resurrection cult raises its devotion by `resurrection_cult_devotion_gain` (25). An unclaimed community that receives a son's miracle starts worshipping him. Each miracle also pushes the doomsday clock back (`APOCALYPSE.miracle`).

### A.15 Climate ages (IKLIM) and world-type weights

Each age lasts several epochs (`DEEP_LIFE.climate_duration + d(climate_die)`; first age `climate_first_*`). All numbers are live getters on `CLIMATE_EFFECTS` (old `IKLIM_ETKI`).

| Key | EN | Fertility change / epoch | Base weight | Extra | Description |
|---|---|---|---|---|---|
| ilik | Temperate age | +1 | 40 | — | seasons in their place |
| kurak | Drought century | −5 | 18 | — | rivers receding, interiors scorched (coast hit divided by `DEEP_LIFE.climate_coast_drought_divisor`) |
| yagmur | Rain age | +4 | 18 | — | rain without end; floods on coasts, plenty in plains (coast bonus `climate_coast_rain_bonus`) |
| buzul | Ice age | −4 | 12 | population −3%/epoch (`nufus = −ice_age_population_loss/100`) | winters lengthen, mountain passes close (mountain extra loss `climate_mountain_ice_loss`) |
| sicak | Scorching age | −3 | 12 | plague frequency ×1.5 (`veba = scorching_age_plague_freq/100`) | the sun has lowered; disease and anger rise |

World-type multipliers (`CLIMATE_WORLD_TYPE`, old `IKLIM_TUR`, key `<worldType>_<age>`, percent, missing = 100):

| World type | Multipliers |
|---|---|
| okyanus (ocean) | ice 25, drought 30, rain 200 |
| kum (sand) | drought 250, rain 30, scorching 180 |
| buz (ice) | ice 300, scorching 20, drought 60 |
| lav (lava) | scorching 300, ice 10, rain 40 |
| gaz (gas) | rain 150 |
| olu (dead) | temperate 150, rain 50 |

```
climateWeight(worldType, age) = (CLIMATE_WORLD_TYPE[worldType + '_' + age] ?? 100) / 100 × IKLIM[age].weight     # iklimAgirligi
```
(World types themselves are defined in `public/harita-gen.js DUNYA_TURLERI` — covered by the world/cosmos spec.)

### A.16 Social classes (SINIFLAR) and relation labels

Classes (each community has a class distribution, see DEEP_SOCIETY):

| Key | EN plural | EN singular | Base share (DEEP_SOCIETY) |
|---|---|---|---|
| ciftci | Farmers | Farmer | `class_farmer_pct` |
| zanaatkar | Artisans | Artisan | `class_artisan_pct` |
| tuccar | Merchants | Merchant | `class_merchant_pct` |
| rahip | Priests | Priest | `class_priest_pct` |
| savasci | Warriors | Warrior | `class_warrior_pct` |
| katip | Scribes | Scribe | `class_scribe_pct` |

God-relation label (`iliskiEtiketT(d)`, d in −100..100; used for son↔son and community displays in derin.js/world.js):

```
d ≤ −relation_blood_enemy (70) → 'blood enemy'   (kan düşmanı)
d ≤ −relation_enemy (35)       → 'enemy'         (düşman)
d ≤ −relation_cold (10)        → 'cold'          (soğuk)
d <  relation_friend (15)      → 'neutral'       (tarafsız)
d <  relation_close_friend (45)→ 'friend'        (dost)
d <  relation_sibling (75)     → 'close friend'  (yakın dost)
else                           → 'sibling/brother' (kardeş)
```

A second, independent son↔son label set lives in world.js (`iliskiEtiket`, registry `SON_RELATIONS`, old `OGUL_ILISKI`), used in prompts ("toward you: friendship"):

```
v ≥ devotion (60)   → 'devotion'  (bağlılık)
v ≥ friendship (25) → 'friendship' (dostluk)
v > −hostility (25) → 'distance'  (mesafe)
v > −hatred (60)    → 'hostility' (husumet)
else                → 'hatred'    (nefret)
```

### A.17 Creature traits (OZELLIKLER) and strange resource mechanics (KAYNAK_MEKANIKLERI)

Creature traits (tag `ozellik:<key>` on species); `savas` = war-strength bonus (tunable `CREATURE_TRAITS.<trait>_war_bonus`):

| Key | EN | War bonus | Effect |
|---|---|---|---|
| ucan | Flying | 8 | Migrates easily, raids reach far; war +8. |
| zehirli | Venomous | 10 | Grievous wounds in hunt and war; kills heroes easily. |
| ruh_yiyen | Soul-eating | 4 | Devours spirits in its region; gnaws the sanity of those nearby. |
| isik_sacan | Light-radiating | 0 | Lowers its region's danger, raises fertility; keeps Outer Beings away. |
| bolunerek | Multiplies by splitting | 2 | Spreads if unchecked: migration and invasion chance ×2. |
| suru_zekasi | Swarm-minded | 6 | Weak alone, clever together: intelligence +15 (`CREATURES.hive_mind_intelligence`), hard to hunt. |
| tas_derili | Stone-skinned | 12 | Heroes' weapons barely bite. |
| zaman_geri | Time-rewinding | 0 | Returns once in the epoch it is killed. |
| sekil_degistiren | Shapeshifting | 3 | Blends among peoples; espionage and discord. |
| akil_okuyan | Mind-reading | 8 | Knows heroes' moves in advance; lowers the sanity of those nearby. |

Strange resource mechanics (tag `mekanik:<key>` on resources; behaviour in ekonomi.js / ECONOMY):

| Key | EN | Effect |
|---|---|---|
| bozunur | decaying | Rots in storage: abundance drops fast every epoch, never regenerates. |
| bagimlilik | addictive | The using community weakens without it: owning it two epochs makes them addicted; losing it causes withdrawal. |
| bilincli | sentient | Chooses who mines it and makes demands; if a demand isn't met it abandons its owner. |
| tukenme_bedeli | depletion_price | When its last drop is drawn, a curse falls on its land and the apocalypse approaches. |
| sabit | fixed | Fixed quantity in the cosmos: never regenerates; one's gain is another's loss. |
| kutsal | sacred | Belongs to a god: if non-worshippers mine it, the god is angered. |

### A.18 Model defaults (LLM routing)

```
MODEL_YEDEK (fallback) = 'haiku'
ISLER (jobs) = { kader: 'Fate and chronicler', yaratilis: 'Genesis', cagirma: 'Son summoning', derinlik: 'Deepening', vahiy: "The god's revelation" }
MODEL_VARSAYILAN = { <every rarity key>: 'haiku', <every job key>: 'haiku' }       # sons by rarity + jobs
MODEL_ETIKET     = { <rarity>: '<Rarity name> sons', ...ISLER }                     # UI labels
MODELLER         = ['haiku', 'sonnet', 'opus']
EFFORT           = { ogul: 'low', kader: 'low', yaratilis: 'low', cagirma: 'low', derinlik: 'low', vahiy: 'low' }  # not sent for haiku
modelFor(key) (world.js) = {...MODEL_VARSAYILAN, ...dunya.model_ayar}[key] || MODEL_YEDEK
```
Default is Haiku everywhere; larger models only if chosen in settings. Rarity keys are derived from `RARITIES` so a new rarity never lacks a default.

### A.19 Mortal agents (OLUMLU_AJAN)

`{ varsayilan: 4, ap: 3, maxTurns: 12, turler: ['halk','hizip','tarikat','yerlesim','olumlu','tur'], zeka_esigi: 55 }` — per epoch the `world.olumlu_sayisi ?? varsayilan` most eligible communities/mortals/creatures play an LLM turn with `ap` action points and `maxTurns` steps; eligible types are `turler` (people, faction, cult, settlement, mortal, species), and species only if intelligence ≥ `zeka_esigi`. `turler` is not tunable. Selection scoring lives in MORTAL_TOOLS (`agent_*`).

### A.20 Time — years per epoch (ZAMAN / CAG_YIL)

`TIME.years_per_epoch` (old `ZAMAN.cag_yil`, default 50, 1–100000). `CAG_YIL` is a *live binding*: `ZAMAN.cag_yil` is redefined with a setter that also reassigns the exported `let CAG_YIL`; modules must read `CAG_YIL` at use time (never cache it at module top). `db.js cagYili()` reads the saved value directly from `dunya.denge_ayar` (because migrations run before rules are applied). In-epoch phase years come from `EPOCH_FLOW.year_*` (defaults: gods until year 15, mortals until 30, world engine until 45, Fate/chronicler until 49, new-epoch transition years until 4 — see Part C). New design: make `years_per_epoch` a normal setting read via the settings service.

### A.21 Global caps — LIMITS (old SINIR)

| Old | EN | Default | Min | Max |
|---|---|---|---|---|
| nufus_taban | population_floor | 10 | 1 | 100,000 |
| halk_nufus_taban | people_population_floor | 100 | 1 | 1,000,000 |
| kent_nufus_tavan | settlement_population_cap | 2,000,000 | 1,000 | 1,000,000,000 |
| nufus_tavan | people_population_cap | 50,000,000 | 1,000 | 2,000,000,000 |
| murit_tavan | cult_follower_cap | 10,000,000 | 1,000 | 2,000,000,000 |
| ordu_tavan | army_soldier_cap | 10,000,000 | 1,000 | 2,000,000,000 |
| can_tavan | hp_cap | 300 | 10 | 100,000 |

(Note the entity-type stat ranges in A.8 hard-code the same numbers — e.g. settlement `nufus 10–2,000,000` — and are *not* linked to LIMITS; see bugs.)

### A.22 Helper functions (pseudo-code)

```
# Integer clamp — NOTE: rounds and coerces NaN/undefined to 0. Do not use for probabilities.
clamp(v, lo, hi)        = max(lo, min(hi, round(Number(v) or 0)))
d(n)                    = 1 + floor(random() × n)                 # die 1..n
randInt(lo, hi)         = lo + floor(random() × (hi − lo + 1))

rollRarity():
    total = Σ RARITIES[k].weight for k in RARITY_KEYS
    r = random() × total
    for k in RARITY_KEYS (order common→mythic):
        r −= RARITIES[k].weight
        if r ≤ 0: return k
    return 'common'

rollStats(rarity, strong=[], weak=[]):
    lo, hi = RARITIES[rarity].stat
    for k in SON_STAT_KEYS:
        v = randInt(lo, hi)
        if k in strong: v += CORE_RULES.strength_bonus      # 15
        if k in weak:   v −= CORE_RULES.weakness_penalty    # 15
        s[k] = clamp(v, 1, 100)
    return s

canMax(stats) = round(CORE_RULES.max_hp_base + (CORE_RULES.max_hp_per_endurance/100) × stats.endurance)
ozMax(stats)  = round(CORE_RULES.max_essence_base + (CORE_RULES.max_essence_per_might/100) × (stats.might ?? CORE_RULES.default_might))
xpEsik(level) = CORE_RULES.xp_per_level × level

creationCost(base, powerLevel, inDomain, creativity, cheapPower=false):     # yaratimBedeli
    domainMult = (inDomain ? cost_in_domain_pct : cost_out_of_domain_pct) / 100        # 0.60 / 1.30
    creatMult  = 1 − (creativity/100) × (creativity_discount_pct/100)                  # up to −40%
    return max(1, round((base + cost_per_power_level × powerLevel) × domainMult × creatMult × (cheapPower ? cheap_power_cost_pct/100 : 1)))
    # callers add repetition surcharge (SON_TOOLS.repeat_cost_*), star-domain discount (SON_TOOLS.star_domain_cost_pct), etc.

initiative(son) = son.stats.agility + son.stats.cunning / 2 + d(CORE_RULES.initiative_die) × 2      # float; higher acts first

entityTier(powerLevel)  (varlikSinifi):
    ≥ tier_mythic → mythic; ≥ tier_legendary → legendary; ≥ tier_epic → epic; ≥ tier_rare → rare; ≥ tier_uncommon → uncommon; else common

rarityAtLeast(r, min)    = RARITIES[r].ordinal ≥ RARITIES[min].ordinal
gateRarity(gateKey)      = RARITY_KEYS[clamp(round(RARITY_GATES[gateKey] ?? 0), 0, 5)]     # sinifKapi
passesGate(rarity, gate) = rarityAtLeast(rarity, gateRarity(gate))                          # kapiyiGecer

# Lenient schema helpers for small models (LANGUAGE-SPECIFIC folding of Turkish letters; in English keep: trim, lowercase, collapse [\s_-]+ to ' ')
simplify(v)   = String(v).trim().toLowerCase('tr').replace(ç→c ğ→g ı→i i̇→i ö→o ş→s ü→u â→a î→i û→u).replace(/[\s_-]+/g,' ')
flexValue(allowed, v):     # esnekDeger
    if v not string: return v
    n = simplify(v)
    return allowed.find(x => simplify(x) == n)
        ?? allowed.find(x => len(n) ≥ 3 and (simplify(x).startsWith(n) or n.startsWith(simplify(x))))
        ?? v

# Tool-input id cleaner: "#12"→12, " 12 "→12, "id 12"→12, prefixed ids "yabanci#12", "rota#1", "oğul#3", "dünya#2" → number
# (only if the whole string looks like an id: optional '#', 'id ', or up to 20 letters/underscore/space followed by '#'); recurses into arrays/objects.
cleanInput(v):     # girdiTemizle
    if string: m = /^(?:#|id\s*|[\p{L}_ ]{1,20}#\s*)?(-?\d+)$/iu on trim(v); return m ? Number(m[1]) : v
    if array: map cleanInput; if object: map values; else v

ROMA(n): Roman numerals 1..3999 (n ≤ 0 or ≥ 4000 → String(n)); standard subtractive table M CM D CD C XC L XL X IX V IV I.
```

Other constants: `YILDIZ_MAX = 5`; `RARITY_KEYS = ['yaygin','seckin','nadir','destansi','efsanevi','mitik']`; `GUC_ETKI_KEYS`, `SON_STAT_KEYS`, `TUTKU_KEYS`, `VARLIK_TUR_KEYS` are key lists of the respective tables.

---

## Part B — The tunable-rules mechanism ("World rules", `src/denge.js`)

### B.1 Concept

"No unconfigurable constant" (ayarsız sabit yok): every balance number in the engine is declared once, with a default, a human label, a min, a recommended max and a UI group, and is editable at runtime from *Settings → World rules* (Dünya kuralları). Changes take effect immediately everywhere because modules hold a reference to a shared mutable object and read `K.some_key` at use time.

### B.2 Declaration API

```
tanimla(namespace, definitions, existingObject = null) -> liveObject
  namespace   : must match /^[A-Z][A-Z0-9_]*$/ else throw "rule namespace must be upper case"
  definitions : { key: [default, label, min = 0, max = max(1000, |default| × 10), group = 'Other'] , ... }
  existingObject : if given, this object (owned by another module, e.g. db.js YEDEK_KOTA) becomes the target and is mutated in place
  behaviour:
    target = existingObject ? (HEDEF[namespace] = existingObject) : (HEDEF[namespace] ||= {})
    saved  = JSON.parse(dunya.denge_ayar) or {}           # per-world overrides
    for key, [def, label, min, max, group] in definitions:
        path = namespace + '.' + key
        KAYIT[path]     = {label, min, max, group}       # registry metadata
        VARSAYILAN[path]= def                            # factory default
        target[key]     = saved[path] ?? def
    return target
```
- Calling `tanimla('NS', {})` with an empty object is the idiom for "give me a live reference to a namespace defined in another module" (avoids circular imports). Same namespace may be declared in several calls/files; definitions merge.
- `rules.js` uses a local shim (see A.0) and `denge.js` registers its `ON_TANIMLAR` at load end.
- Besides `tanimla` blocks, `denge.js alanlar()` hard-codes editable paths into the static objects of `rules.js`: `COSTS.*` (0–500), `DENGE.*` (0–1000; `oz_tavan` max 100000; `kiyamet_esik` min 1; `kiyamet_hiz` max 300), `KOZMIK_BEDEL.*` (0–500), `MUDAHALE_BEDEL.*` (0–300), `OLUMLU_AJAN.ap` (1–6), `.varsayilan` (0–1000), `.maxTurns` (4–20), `.zeka_esigi` (0–100), `OZELLIKLER.<trait>.savas` (0–100), `SEYAHAT_YONTEMLERI.<m>.sure` (1–20) and `.tehlike` (0–100), `GUC_SEVIYELERI.<i>` (1–50), and per rarity `RARITIES.<r>.ap` (1–8), `.oz_yenilenme` (0–60), `.stat.0`/`.stat.1` (1–100), `.guc_tavan` (1–30), `.maxTurns` (4–40), `.agirlik` (0–100, not for mythic). Their labels come from an `AD` map and groups from a `GRUP` map (by root object).

### B.3 Storage

- Single column `dunya.denge_ayar TEXT` (JSON object `{ "COSTS.cagirma": 40, ... }`) on the singleton world row. Only values that **differ from the default** are stored; `NULL` when empty.
- On boot (`dengeUygula()` at module load) and after any world switch/restore (server calls `dengeUygula()` on "world changed"), every known path is written back into its live object: `value = saved[path] ?? default`.
- Path resolution: `path.split('.')` walked from `HEDEF = {COSTS, DENGE, KOZMIK_BEDEL, MUDAHALE_BEDEL, OLUMLU_AJAN, RARITIES, OZELLIKLER, SEYAHAT_YONTEMLERI, GUC_SEVIYELERI, …all tanimla namespaces}`; writing to an unknown leaf throws "Unknown rule".

### B.4 Listing (`dengeListesi()`, `GET /api/denge`)

Returns, for every editable path: `{ yol (path), ad (label), grup (group), min, max, deger (current value), varsayilan (default), degisti (changed: saved value exists and ≠ default) }`. Group = registry group, else the root-object group map, else "Other".

### B.5 Changing (`dengeAyarla(changes, {sifirla})`, `POST /api/denge {degisiklikler, sifirla}`)

```
bounds = {path: [min, max]} for all editable paths
k = sifirla ? {} : saved                     # sifirla = reset everything to defaults first
for path, v in changes:
    if path not in bounds: throw "Unknown rule: path"
    if v === null: delete k[path]; continue  # reset one rule
    n = round(Number(v)); if not finite: throw "path must be a number"
    if n < min: throw "path must be at least min"      # min is STRUCTURAL and enforced (prevents /0, negatives, empty worlds)
    if not safe integer: throw "path is too large"
    # max is only a RECOMMENDED range (UI shows a warning); the god may exceed it
    if n == default: delete k[path] else k[path] = n
UPDATE dunya SET denge_ayar = (k empty ? NULL : JSON(k))
dengeUygula(); return dengeListesi()
```

### B.6 Special cases

- `YEDEK` (BACKUP) is declared in `denge.js` with `existingObject = db.js YEDEK_KOTA` so the backup code in `db.js` sees live quotas.
- `ZAMAN.cag_yil` has a setter that also updates the exported `CAG_YIL` live binding (A.20).
- `server.js` declares namespace `SUNUCU` (SERVER) for API page sizes etc.
- `denge.js` contains a doc-comment example `tanimla('SAVAS', …)` — not a real namespace.
- Tests (`test/*.test.js`) declare throw-away namespaces; `.dev/` is a stale duplicate of the source tree. Both are excluded from the registry.
- The UI groups (`grup`) are display categories that cut across namespaces (e.g. "War and diplomacy" holds keys from DEEP_WORLD, DEEP_WARFARE, SON_RELATIONS, CORE_RULES…).

### B.7 New-design recommendation

Model this as a `rules` service: a static, typed registry (generated from `rules-registry.json`) of `{namespace, key, default, min, max, group, label, module}`; per-world overrides in a `world_rule_override(world_id, namespace, key, value)` table (or a JSON column); values exposed through an immutable snapshot object injected into engine steps (re-snapshotted after edits, not mutated in place). Keep "min enforced / max advisory" semantics, integer values, percent convention, and the single-row-reset (`null`) / reset-all (`sifirla`) operations. Keep the exact defaults from Part C to stay balance-compatible with the old game.

---

## Part C — Complete registry (3,323 tunables)

Columns: **key** (new English snake_case) · **old key** · **default** · **min** (enforced) · **max** (advisory) · **group** (UI group, English) · **label** (English).
Each namespace header gives the new namespace (old namespace), purpose, defining module(s) and other modules that read it. The JSON file has the same rows with fields `namespace, key, old_namespace, old_key, default, min, max, group, label, module`.

Completeness check (static count of `[default, label, …]` entries inside every `tanimla(…)` block per file, versus rows emitted for that module; `rules.js` additionally has 116 editable static-object paths from `denge.js alanlar()` and 40 generated `NADIRLIK_KAPI` gates):

| Old file | Static tanimla entries | Rows emitted |
|---|---|---|
| agents.js | 171 | 171 |
| agonar.js | 20 | 20 |
| arsiv.js | 19 | 19 |
| bildirim.js | 3 | 3 |
| bosdunya.js | 6 | 6 |
| defter.js | 1 | 1 |
| degisim.js | 3 | 3 |
| denge.js (YEDEK) | 5 | 5 |
| derin.js | 734 | 734 |
| dilmotoru.js | 29 | 29 |
| ekonomi.js | 47 | 47 |
| epoch.js | 55 | 55 |
| firsatlar.js | 25 | 25 |
| gok.js | 56 | 56 |
| gorsel-uret.js | 10 | 10 |
| harita.js | 2 | 2 |
| hedef.js | 51 | 51 |
| itibar.js | 60 | 60 |
| kesif.js | 8 | 8 |
| kodeks.js | 5 | 5 |
| konsey.js | 34 | 34 |
| korku.js | 71 | 71 |
| kozmos.js | 62 | 62 |
| kronik-onar.js | 2 | 2 |
| llm.js | 14 | 14 |
| medeniyet.js | 71 | 71 |
| mudahale.js | 7 | 7 |
| olcum.js | 3 | 3 |
| olum.js | 53 | 53 |
| olumluler.js | 223 | 223 |
| otesi.js | 73 | 73 |
| oyuncu.js | 18 | 18 |
| panteon.js | 64 | 64 |
| rules.js | 134 (+116 static paths +40 generated gates = 290) | 290 |
| server.js | 42 | 42 |
| seyahat.js | 62 | 62 |
| sihirbaz.js | 7 | 7 |
| sim.js | 359 | 359 |
| tanriguc.js | 76 | 76 |
| tools.js | 192 | 192 |
| toplu.js | 6 | 6 |
| ufuk.js | 39 | 39 |
| world.js | 94 | 94 |
| yabanci.js | 21 | 21 |
| yaratici.js | 64 | 64 |
| yaratik.js | 66 | 66 |
| **Total** | | **3,323** |

The 3,281 non-server rows were additionally cross-checked against the live registry produced by importing every `src/*.js` module into a scratch database and calling `dengeListesi()` (3,281 paths; exact match), and the 42 `SUNUCU` rows were evaluated from `server.js` source.

### Namespace index

| New namespace | Old namespace | Rows | Defining module(s) | Purpose |
|---|---|---|---|---|
| [AGENTS](#agents) | AJAN | 13 | src/epoch.js | Agent orchestration: concurrency, auto-deepening, sleeping local gods |
| [APOCALYPSE](#apocalypse) | KIYAMET | 17 | src/sim.js | Doomsday clock contributions |
| [ARCHIVE](#archive) | ARSIV | 19 | src/arsiv.js | Atlas archive: when records 'pass into history' and importance scoring |
| [ASCENSION](#ascension) | YUKSELIS | 3 | src/rules.js | Requirements to ascend to the next rarity |
| [AWAKENING](#awakening) | UYANIS | 34 | src/agents.js | Awakening of peoples (LLM-generated peoples) |
| [BACKUP](#backup) | YEDEK | 5 | src/denge.js | Backup retention quotas |
| [BALANCE](#balance) | DENGE | 12 | src/rules.js | Major actions, Creator essence economy, apocalypse threshold/speed — static object in rules.js |
| [BATCH](#batch) | TOPLU | 6 | src/toplu.js | Batch deepening jobs |
| [BEYOND](#beyond) | OTESI | 73 | src/otesi.js | The Beyond: legendary expeditions, void storms, souls, living planets, archives, golems, mirrors |
| [CHRONICLE_REPEAT](#chronicle_repeat) | KRONIK_TEKRAR | 2 | src/kronik-onar.js | Chronicle duplicate-line detection |
| [CIVILIZATION](#civilization) | MEDENIYET | 71 | src/medeniyet.js | Civilization stages, colonies/independence, federations, previous-creation relics, loans, barter, adoption, treaties |
| [CLIMATE_EFFECTS](#climate_effects) | IKLIM_ETKI | 12 | src/rules.js | Climate age effects and base weights |
| [CLIMATE_WORLD_TYPE](#climate_world_type) | IKLIM_TUR | 15 | src/rules.js | Climate weight multipliers by world type |
| [CONTENT](#content) | ICERIK | 14 | src/agents.js | Content jobs: image prompts, revelation, epics, deepening |
| [CONTEXT](#context) | BAGLAM | 57 | src/world.js | LLM prompt context budgets for sons, Fate and mortals |
| [CORE_RULES](#core_rules) | KURAL | 45 | src/rules.js | Core son/entity formulas: tiers, stars, existence, HP/essence, costs, relations, action points |
| [COSMIC_COSTS](#cosmic_costs) | KOZMIK_BEDEL | 8 | src/rules.js | Creator's cosmic action costs — static object in rules.js |
| [COSMIC_HORROR](#cosmic_horror) | KORKU | 71 | src/korku.js | Leak (seepage from beyond), sanity, Outer Beings, Whisperers |
| [COSTS](#costs) | COSTS | 16 | src/rules.js | Creator and son action costs (essence) — static object in rules.js |
| [COUNCIL](#council) | KONSEY | 34 | src/konsey.js | Council of sons, god-son chat, dream and translation limits |
| [CREATION_BASE_COST](#creation_base_cost) | YARATIM_TABANI | 25 | src/rules.js | Base creation cost per entity type |
| [CREATOR](#creator) | YARATICI | 64 | src/yaratici.js | The Creator's mood (wrath/contentment/attention/loneliness), cult and signs |
| [CREATURES](#creatures) | YARATIK | 66 | src/yaratik.js | Creature traits, chimeras, mutation, predation, taming |
| [CREATURE_TRAITS](#creature_traits) | OZELLIKLER | 10 | src/rules.js | War bonus per creature trait — static object in rules.js |
| [DEATH](#death) | OLUM | 53 | src/olum.js | Taking lives, killing sons, resurrection rites and intrigues |
| [DEEP_LIFE](#deep_life) | DERIN_YASAM | 348 | src/derin.js | Heroes, quests, knowledge spread, spies, wonders, climate, god death/resurrection, births, writing, legends, native life, refugees, structures, factions, culture |
| [DEEP_RELATIONS](#deep_relations) | DERIN_ILISKI | 33 | src/derin.js | Community-to-community relation model (initial, drift, decay) |
| [DEEP_SOCIETY](#deep_society) | DERIN_TOPLUM | 128 | src/derin.js | Social classes, stockpiles (food/ore/goods), prices, satisfaction, famine, revolts, trade flow |
| [DEEP_WARFARE](#deep_warfare) | DERIN_SEFER | 100 | src/derin.js | Armies, battles, sieges, duels, captives, ransoms, tribute |
| [DEEP_WORLD](#deep_world) | DERIN | 125 | src/derin.js | Deep simulation: diplomacy, wars, notable mortals, religion, culture, dark/golden ages |
| [ECONOMY](#economy) | EKONOMI | 47 | src/ekonomi.js | Strange resource mechanics, cosmic markets, void pirates, cosmic deposits |
| [EMPTY_WORLD](#empty_world) | BOS_DUNYA | 6 | src/bosdunya.js | Empty (uninhabited) worlds: dispatching sons, first-people rewards |
| [EPOCH_FLOW](#epoch_flow) | CAG_AKIS | 8 | src/epoch.js | In-epoch year schedule of phases and live-feed retention |
| [ESSENCE](#essence) | OZ | 7 | src/sim.js | Essence overflow, godless gnawing, renown decay, Creator income above cap |
| [EXPLORATION](#exploration) | KESIF | 39 | src/ufuk.js | Mortal exploration of new land and routes |
| [FAITH](#faith) | INANC | 6 | src/world.js | Faith computation for sons |
| [FATE](#fate) | KADER | 74 | src/agents.js | Fate (judge) and chronicler: budgets, threads, rewards, anti-repetition |
| [FOLK_BELIEF](#folk_belief) | HALK_INANC | 3 | src/agents.js | Folk-belief text generation guards |
| [FOREIGN_GODS](#foreign_gods) | YABANCI | 21 | src/yabanci.js | Foreign god stats and powers |
| [GENESIS](#genesis) | YARATILIS | 9 | src/agents.js | Initial world genesis |
| [GOALS](#goals) | HEDEF | 51 | src/hedef.js | Scenarios, achievements and score |
| [GOD_ACTIONS](#god_actions) | TANRI_EYLEM | 34 | src/epoch.js | The Creator's actions on sons (bless, star, ascend, punish, suppress, prayers) |
| [GOD_HAND](#god_hand) | TANRI_ELI | 18 | src/oyuncu.js | The Creator's manual decrees and son distribution |
| [GOD_POWER](#god_power) | TANRI_GUC | 76 | src/tanriguc.js | The Creator's dark/great powers and their automatic use |
| [GUIDE](#guide) | REHBER | 5 | src/kodeks.js | Codex/guide listing thresholds |
| [IMAGE_GEN](#image_gen) | GORSEL_URET | 10 | src/gorsel-uret.js | Local image generation worker |
| [INTERVENTION_COSTS](#intervention_costs) | MUDAHALE_BEDEL | 4 | src/rules.js | Creator's intervention costs — static object in rules.js |
| [INTERVENTION_EFFECTS](#intervention_effects) | MUDAHALE | 33 | src/mudahale.js, src/rules.js | Effects of miracles, disasters and taught knowledge |
| [LANGUAGE](#language) | DIL | 46 | src/dilmotoru.js, src/world.js | Name generation, language signatures, tired-motif detection, dialect checks |
| [LEDGER](#ledger) | DEFTER | 1 | src/defter.js | Action ledger retention |
| [LIMITS](#limits) | SINIR | 7 | src/rules.js | Global stat caps and floors |
| [LINK_GRAPH](#link_graph) | AG | 20 | src/agonar.js | Link-graph (entity network) repair, incl. Fate-proposed links |
| [METRICS](#metrics) | OLCUM | 3 | src/olcum.js | Model-call metrics |
| [MODEL](#model) | MODEL | 14 | src/llm.js | LLM call retries, timeouts, continuation |
| [MORTAL_AGENTS](#mortal_agents) | OLUMLU_AJAN | 4 | src/rules.js | Mortal agent counts and limits — static object in rules.js |
| [MORTAL_TOOLS](#mortal_tools) | OLUMLU_ARAC | 223 | src/olumluler.js | Mortal agent tool parameters |
| [NAMING](#naming) | ADLANDIRMA | 4 | src/agents.js | Fate's naming pass for engine-born records (batching, retries) |
| [NARRATIVE](#narrative) | ANLATI | 18 | src/agents.js | Size ranges of god epics and deepening (depth) outputs |
| [NOTIFICATIONS](#notifications) | BILDIRIM | 3 | src/bildirim.js | Notification retention and toast threshold |
| [OPPORTUNITIES](#opportunities) | FIRSAT | 25 | src/firsatlar.js | Opportunity hints shown to agents and the god |
| [PANTHEON](#pantheon) | PANTEON | 64 | src/panteon.js | Foreign gods, Outer Beings bargains, stars, sleeping local gods, rival clashes, holy worlds |
| [POLITICS](#politics) | SIYASET | 8 | src/kesif.js | Regional dominance and settlement tiers |
| [POWER_UNLOCK_LEVELS](#power_unlock_levels) | GUC_SEVIYELERI | 3 | src/rules.js | Levels at which a son's 3 powers unlock — static array in rules.js |
| [RARITIES](#rarities) | RARITIES | 41 | src/rules.js | Per-rarity son properties — static object in rules.js |
| [RARITY_GATES](#rarity_gates) | NADIRLIK_KAPI | 40 | src/rules.js | Minimum son rarity (0..5) to use each creation type / tool |
| [REPUTATION](#reputation) | ITIBAR | 60 | src/itibar.js | The Creator's reputation in each son's eyes (love/fear/neglect) |
| [SERVER](#server) | SUNUCU | 42 | server.js | HTTP API list sizes, search limits, health, thumbnails (server.js) |
| [SETUP_WIZARD](#setup_wizard) | SIHIRBAZ | 7 | src/sihirbaz.js | Genesis wizard defaults |
| [SKY](#sky) | GOK | 56 | src/gok.js | Sky events: eclipses, comets, alignments, supernovae, black suns, time echoes |
| [SON_RELATIONS](#son_relations) | OGUL_ILISKI | 4 | src/world.js | Son-to-son relation label thresholds |
| [SON_TOOLS](#son_tools) | OGUL_ARAC | 192 | src/tools.js | Son agent tool parameters |
| [SUMMONING](#summoning) | CAGIRMA | 15 | src/agents.js | Son summoning and birth (initial existence, world choice, domains) |
| [TIME](#time) | ZAMAN | 1 | src/rules.js | Years per epoch |
| [TRAVEL](#travel) | SEYAHAT | 62 | src/seyahat.js | Inter-world travel, expeditions, colonies, routes |
| [TRAVEL_METHODS](#travel_methods) | SEYAHAT_YONTEMLERI | 18 | src/rules.js | Duration and danger per travel method — static object in rules.js |
| [UI](#ui) | ARAYUZ | 5 | src/degisim.js, src/harita.js | UI-facing limits (graph view, map population trend, incremental change feed) |
| [WORLD_BIRTH](#world_birth) | DUNYA_DOGUS | 62 | src/kozmos.js | Generation of a newly born world (regions, sky, unique resource, natives) |
| [WORLD_EFFECTS](#world_effects) | DUNYA_ETKI | 166 | src/sim.js | World-engine side effects: raids, trade, curses, resources, magic storms, schisms, heroes, plagues, famine, uprisings, laws, coinage, births, dialects, spirits |
| [WORLD_ENGINE](#world_engine) | DUNYA_MOTORU | 81 | src/sim.js | World-engine event probabilities and growth |
| [WORLD_EPOCH_TRANSITION](#world_epoch_transition) | DUNYA_CAG_GECISI | 37 | src/sim.js | Epoch transition: capacity, growth laws, son regen/healing/existence, rivalry, apocalypse damage |
| [WORLD_HUNT](#world_hunt) | DUNYA_AV | 32 | src/sim.js | Hero vs monster encounters |
| [WORLD_PHYSICS](#world_physics) | DUNYA_FIZIK | 10 | src/world.js | World physics: time factor, atmosphere life capacity, gravity martiality |
| [WORLD_WAR_STRENGTH](#world_war_strength) | DUNYA_SAVAS_GUCU | 19 | src/sim.js | War-strength formula coefficients |

### AGENTS

Old namespace `AJAN` · 13 rows · defined in `src/epoch.js`. Agent orchestration: concurrency, auto-deepening, sleeping local gods.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| concurrent_jobs | eszamanli_is | 8 | 1 | 32 | Agents and model | Maximum simultaneous content jobs (deepening, epic, prompt); the rest are queued |
| auto_deepen | oto_derin | 3 | 0 | 20 | Agents and model | Records to auto-deepen at epoch end (0 off) |
| sons_parallel | ogul_paralel | 2 | 1 | 6 | Agents and model | Sons thinking at the same time |
| local_god_epochs | yerel_tanri_cag | 3 | 1 | 200 | Cosmos | Epochs for a sleeping local god to be born on a godless world |
| local_god_rebirth_epochs | yerel_tanri_yeniden_cag | 5 | 0 | 1000 | Cosmos | Epochs for a new sleeping god to be born on a world whose native god died (mourning) |
| local_god_strength | yerel_tanri_guc | 30 | 1 | 100 | Cosmos | Strength of a sleeping local god |
| auto_wait_seconds | oto_bekle_sn | 5 | 1 | 600 | Agents and model | Auto-deepening: wait interval if the job pool is full (s) |
| auto_wait_attempts | oto_bekle_deneme | 60 | 0 | 10,000 | Agents and model | Auto-deepening: maximum waits for the pool to empty |
| auto_reserve | oto_pay | 2 | 0 | 12 | Agents and model | Concurrent job share auto-deepening leaves to manual jobs |
| prompt_batches | prompt_tur | 10 | 1 | 1000 | Agents and model | Manual "write prompts": maximum number of batches |
| auto_deepen_power_weight | oto_derin_guc | 2 | 0 | 100 | Agents and model | Auto-deepening order: weight of one power level equivalent to one link |
| epic_refresh_epochs | destan_tazele | 8 | 0 | 1000 | Agents and model | Stale epic: when the Creator's and sons' epic/depth is this many epochs old it is rewritten in the background at epoch end (0 off) |
| epic_refresh_per_epoch | destan_tazele_adet | 1 | 0 | 20 | Agents and model | Stale epic: maximum refreshed per epoch (low priority: when the job pool is idle) |

### APOCALYPSE

Old namespace `KIYAMET` · 17 rows · defined in `src/sim.js`. Doomsday clock contributions.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| godless | tanrisiz | 2 | 0 | 50 | Apocalypse | Each godless community advances the clock |
| cursed | lanetli | 1 | 0 | 50 | Apocalypse | Each cursed entity advances the clock |
| restless_spirit | huzursuz_ruh | 2 | 0 | 50 | Apocalypse | Each restless spirit advances the clock |
| restless_threshold | huzursuz_esik | 60 | 0 | 100 | Apocalypse | Unrest of a spirit counted as restless |
| hostility_divisor | savas_bolen | 2 | 1 | 100 | Apocalypse | Every this many hostility links advance the clock by 1 |
| rebel_son | asi | 4 | 0 | 50 | Apocalypse | Each rebel son advances the clock |
| miracle | mucize | 3 | 0 | 50 | Apocalypse | Each miracle pushes the clock back |
| faith_divisor | inanc_bolen | 40 | 1 | 10,000 | Apocalypse | Every this much faith pushes the clock back by 1 |
| faith_cap | inanc_tavan | 4 | 0 | 100 | Apocalypse | Maximum push-back of the clock by faith in one epoch |
| peace | baris | 2 | 0 | 50 | Apocalypse | An epoch with no war pushes the clock back |
| wonder_cap | harika_tavan | 3 | 0 | 50 | Apocalypse | Maximum push-back of the clock by wonders (1 per wonder) |
| temple_cap | tapinak_tavan | 2 | 0 | 50 | Apocalypse | Maximum push-back of the clock by temples (1 per two temples) |
| golden_age | altin_cag | 3 | 0 | 50 | Apocalypse | Each world in a golden age pushes the clock back |
| warning_1_pct | uyari1 | 50 | 1 | 100 | Apocalypse | Point at which the first omen comes (% of threshold) |
| warning_2_pct | uyari2 | 80 | 1 | 100 | Apocalypse | Point at which the final warning comes (% of threshold) |
| after_calling_pct | cagri_sonrasi | 60 | 0 | 100 | Apocalypse | Where the clock falls when the apocalypse turns into the Calling (% of threshold) |
| after_ruin_pct | yikim_sonrasi | 40 | 0 | 100 | Apocalypse | Where the clock falls when the apocalypse destroys (% of threshold) |

### ARCHIVE

Old namespace `ARSIV` · 19 rows · defined in `src/arsiv.js`. Atlas archive: when records 'pass into history' and importance scoring.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| event_epochs | olay | 3 | 1 | 100 | Atlas archive | Epochs an event goes unmentioned before passing into history |
| prophecy_epochs | kehanet | 4 | 1 | 100 | Atlas archive | Epochs after which a prophecy passes into history |
| spirit_epochs | ruh | 4 | 1 | 100 | Atlas archive | Epochs after which a spirit passes into history |
| settlement_epochs | yerlesim | 5 | 1 | 100 | Atlas archive | Epochs after which a settlement passes into history |
| item_epochs | esya | 6 | 1 | 100 | Atlas archive | Epochs after which an item passes into history |
| tradition_epochs | gelenek | 8 | 1 | 100 | Atlas archive | Epochs after which a tradition passes into history |
| importance_threshold | onem_esik | 60 | 0 | 500 | Atlas archive | Records with importance above this never pass into history |
| w_power_level | w_guc | 10 | 0 | 100 | Atlas archive | Importance: per power level |
| w_link | w_bag | 3 | 0 | 50 | Atlas archive | Importance: per link |
| w_link_cap | w_bag_tavan | 40 | 0 | 500 | Atlas archive | Importance: maximum from links |
| w_mention | w_anma | 2 | 0 | 50 | Atlas archive | Importance: per mention in the chronicle |
| w_mention_cap | w_anma_tavan | 30 | 0 | 500 | Atlas archive | Importance: maximum from mentions |
| w_favorite | w_favori | 50 | 0 | 500 | Atlas archive | Importance: bonus for a favourite record |
| w_freshness | w_taze | 20 | 0 | 500 | Atlas archive | Importance: freshness bonus for a recently mentioned record |
| w_freshness_decay | w_taze_azalma | 4 | 0 | 500 | Atlas archive | Importance: decrease of the freshness bonus per epoch |
| w_population_log | w_nufus | 4 | 0 | 100 | Atlas archive | Importance: per log10 of population |
| w_population_cap | w_nufus_tavan | 20 | 0 | 500 | Atlas archive | Importance: maximum from population |
| w_not_living_penalty | w_yasamayan | 15 | 0 | 500 | Atlas archive | Importance: subtracted from a record that is no longer alive |
| dead_epochs | olu_cag | 2 | 0 | 100 | Atlas archive | Epochs a dead, destroyed or fulfilled record goes unmentioned before passing into history |

### ASCENSION

Old namespace `YUKSELIS` · 3 rows · defined in `src/rules.js` · also read by `src/epoch.js`. Requirements to ascend to the next rarity.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| level | seviye | 9 | 1 | 100 | Rarity tiers | Level required to ascend to the next rarity |
| renown | un | 90 | 0 | 100 | Rarity tiers | Renown required to ascend to the next rarity |
| essence_cost | oz | 90 | 0 | 1000 | Rarity tiers | Essence cost of ascending to the next rarity |

### AWAKENING

Old namespace `UYANIS` · 34 rows · defined in `src/agents.js` · also read by `src/epoch.js`. Awakening of peoples (LLM-generated peoples).

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| batch_cap | tavan | 3 | 1 | 20 | Awakening of the peoples | Maximum peoples in one awakening batch (one model call); more requested are split into batches |
| timeout | sure | 300 | 30 | 3600 | Agents and model | Awakening of the peoples timeout (s) |
| words_min | kelime_en_az | 6 | 0 | 100 | Awakening of the peoples | Minimum words of a new language |
| words_max | kelime_en_cok | 10 | 1 | 200 | Awakening of the peoples | Maximum words of a new language |
| people_power | guc | 4 | 1 | 11 | Awakening of the peoples | Power level of an awakened people |
| first_peoples | ilk_halk | 2 | 1 | 1000 | Awakening of the peoples | Peoples awakening automatically at startup on a world without peoples |
| people_population | halk_nufus | 20,000 | 1 | 1,000,000,000 | Awakening of the peoples | People's population (if the model gives none) |
| people_population_min | halk_nufus_en_az | 500 | 1 | 1,000,000,000 | Awakening of the peoples | Minimum population of an awakened people |
| people_population_max | halk_nufus_en_cok | 5,000,000 | 1 | 2,000,000,000 | Awakening of the peoples | Maximum population of an awakened people |
| people_martiality | halk_savascilik | 40 | 0 | 100 | Awakening of the peoples | People's martiality (if the model gives none) |
| people_magic | halk_buyu | 30 | 0 | 100 | Awakening of the peoples | People's magic (if the model gives none) |
| people_craft | halk_zanaat | 45 | 0 | 100 | Awakening of the peoples | People's craft (if the model gives none) |
| people_piety | halk_inanc | 60 | 0 | 100 | Awakening of the peoples | People's piety |
| language_spread | dil_yayginlik | 30 | 0 | 100 | Awakening of the peoples | New language spread |
| language_complexity | dil_karmasiklik | 45 | 0 | 100 | Awakening of the peoples | New language complexity |
| language_sacredness | dil_kutsallik | 25 | 0 | 100 | Awakening of the peoples | New language sacredness |
| language_power | dil_guc | 3 | 1 | 11 | Awakening of the peoples | New language power level |
| settlement_population | kent_nufus | 3000 | 1 | 1,000,000,000 | Awakening of the peoples | First settlement population (if the model gives none) |
| settlement_population_min | kent_nufus_en_az | 100 | 1 | 1,000,000,000 | Awakening of the peoples | Minimum population of the first settlement |
| settlement_population_max | kent_nufus_en_cok | 500,000 | 1 | 2,000,000,000 | Awakening of the peoples | Maximum population of the first settlement |
| settlement_prosperity | kent_refah | 45 | 0 | 100 | Awakening of the peoples | Prosperity of the first settlement |
| settlement_defense | kent_savunma | 30 | 0 | 100 | Awakening of the peoples | Defense of the first settlement |
| settlement_piety | kent_inanc | 60 | 0 | 100 | Awakening of the peoples | Piety of the first settlement |
| settlement_power | kent_guc | 3 | 1 | 11 | Awakening of the peoples | Power level of the first settlement |
| resource_abundance | kaynak_bolluk | 70 | 0 | 100 | Awakening of the peoples | Abundance of the people's resource |
| resource_value | kaynak_deger | 50 | 0 | 100 | Awakening of the peoples | Value of the people's resource |
| resource_might | kaynak_kudret | 35 | 0 | 100 | Awakening of the peoples | Might of the people's resource |
| resource_power | kaynak_guc | 3 | 1 | 11 | Awakening of the peoples | Power level of the people's resource |
| knowledge_level | bilgi_seviye | 1 | 1 | 100 | Awakening of the peoples | Level of the people's first knowledge |
| knowledge_spread | bilgi_yayginlik | 20 | 0 | 100 | Awakening of the peoples | Spread of the people's first knowledge |
| knowledge_power | bilgi_guc | 2 | 1 | 11 | Awakening of the peoples | Power level of the people's first knowledge |
| tradition_spread | gelenek_yayginlik | 60 | 0 | 100 | Awakening of the peoples | Spread of the people's tradition |
| tradition_rigidity | gelenek_katilik | 50 | 0 | 100 | Awakening of the peoples | Rigidity of the people's tradition |
| tradition_power | gelenek_guc | 2 | 1 | 11 | Awakening of the peoples | Power level of the people's tradition |

### BACKUP

Old namespace `YEDEK` · 5 rows · defined in `src/denge.js`. Backup retention quotas.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| recent_epoch_backups | cag | 10 | 1 | 200 | Backups | Most recent epoch backups kept |
| milestone_epoch_multiple | onluk | 10 | 1 | 100 | Backups | Backups of epochs that are multiples of this are always kept |
| manual_backups | elle | 30 | 1 | 500 | Backups | Manual backups kept |
| safety_backups_per_kind | guvenlik | 5 | 1 | 100 | Backups | Kept per safety-backup kind |
| secondary_target_backups | ikinci | 20 | 1 | 1000 | Backups | Kept on the secondary backup target (AERONA_YEDEK2) |

### BALANCE

Old namespace `DENGE` · 12 rows · defined in `src/rules.js` · also read by `src/agents.js`, `src/denge.js`, `src/ekonomi.js`, `src/epoch.js`, `src/firsatlar.js`, `src/gok.js`, `src/hedef.js`, `src/konsey.js`, `src/korku.js`, `src/kozmos.js`, `src/otesi.js`, `src/panteon.js`, `src/sim.js`, `src/tools.js`, `src/world.js`, `src/yaratici.js`. Major actions, Creator essence economy, apocalypse threshold/speed — static object in rules.js.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| creator_essence_regen | tanri_oz_yenilenme | 20 | 0 | 1000 | Major actions and essence | Creator's essence per epoch |
| creator_essence_soft_cap | oz_tavan | 800 | 0 | 100,000 | Major actions and essence | Soft cap of the Creator's essence |
| resurrection | dirilis | 150 | 0 | 1000 | Major actions and essence | Resurrection |
| create_world | dunya | 120 | 0 | 1000 | Major actions and essence | Create a world |
| birth_world | dunya_dogur | 70 | 0 | 1000 | Major actions and essence | Birth a world (son) |
| council | konsey | 20 | 0 | 1000 | Major actions and essence | Council |
| dream | ruya | 8 | 0 | 1000 | Major actions and essence | Dream (son) |
| awaken_peoples | uyandir | 35 | 0 | 1000 | Major actions and essence | Awaken the peoples |
| apocalypse_threshold | kiyamet_esik | 100 | 1 | 1000 | Major actions and essence | Apocalypse threshold (apocalypse happens when the clock reaches this) |
| apocalypse_speed | kiyamet_hiz | 100 | 0 | 300 | Major actions and essence | Apocalypse speed (%; 0 = clock stops) |
| suppress_revolt | bastir | 20 | 0 | 1000 | Major actions and essence | Suppress an uprising |
| creator_starting_essence | baslangic_oz | 150 | 0 | 1000 | Major actions and essence | Creator's starting essence in a new cosmos |

### BATCH

Old namespace `TOPLU` · 6 rows · defined in `src/toplu.js`. Batch deepening jobs.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| concurrent | eszamanli | 1 | 1 | 4 | Batch jobs | Records processed simultaneously in batch deepening |
| wait_seconds | bekle_sn | 0 | 0 | 600 | Batch jobs | Wait between two records in batch deepening (s) |
| retries | yeniden_dene | 2 | 0 | 5 | Batch jobs | Retry a failed record in batch deepening |
| pool_wait_seconds | havuz_bekle_sn | 5 | 1 | 600 | Batch jobs | Batch deepening: re-check interval if the job pool is full (s) |
| retry_wait_seconds | yeniden_bekle_sn | 3 | 0 | 600 | Batch jobs | Wait before retrying a failed record in batch deepening (s) |
| log_lines | gunluk_satir | 200 | 20 | 5000 | Batch jobs | Lines kept in the batch-job log |

### BEYOND

Old namespace `OTESI` · 73 rows · defined in `src/otesi.js` · also read by `src/epoch.js`. The Beyond: legendary expeditions, void storms, souls, living planets, archives, golems, mirrors.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| expedition_reward_essence | sefer_odul_oz | 60 | 0 | 1000 | The Beyond | Essence the legendary expedition earns the god |
| expedition_reward_apocalypse_push | sefer_odul_kiyamet | 15 | 0 | 100 | Apocalypse | Apocalypse push-back from a legendary expedition |
| expedition_fail_apocalypse | sefer_ceza_kiyamet | 15 | 0 | 100 | Apocalypse | Contribution of a failed legendary expedition to the apocalypse |
| expedition_epochs | sefer_sure | 6 | 1 | 50 | The Beyond | Duration of a legendary expedition (epochs) |
| storm_closed_min_epochs | firtina_kapali_en_az | 2 | 0 | 20 | Cosmos and travel | Minimum epochs a storm severs a route |
| storm_closed_die | firtina_kapali_zar | 3 | 1 | 20 | Cosmos and travel | Die added to the storm's severing (1…n epochs) |
| soul_buildup_threshold | ruh_birikim_esik | 6 | 1 | 100 | The Beyond | Number of souls in the realm of the dead that increases leakage |
| soul_descent_chance | ruh_inis_sans | 35 | 0 | 100 | The Beyond | A dead person's soul descends to the realm of the dead (%) |
| soul_harvest_chance | ruh_hasat_sans | 20 | 0 | 100 | The Beyond | A zealous cult harvests souls (%) |
| planet_acts_chance | gezegen_sans | 35 | 0 | 100 | The Beyond | A living planet acts (%) |
| planet_punish_chance | gezegen_ceza_sans | 50 | 0 | 100 | The Beyond | The planet shakes its polluter (%) |
| planet_worship_chance | gezegene_tapma_sans | 30 | 0 | 100 | The Beyond | A godless people worships the planet (%) |
| archive_appear_chance | arsiv_sans | 12 | 0 | 100 | The Beyond | A cosmic archive appears (%) |
| archive_knowledge_chance | arsiv_bilgi_sans | 30 | 0 | 100 | The Beyond | Knowledge is extracted from the archive (%) |
| cosmic_plague_chance | kozmik_salgin_sans | 12 | 0 | 100 | The Beyond | An arriving expedition carries plague (%) |
| void_storm_chance | hiclik_firtina_sans | 8 | 0 | 100 | Cosmos and travel | Void storm (% per epoch) |
| storm_reveal_chance | firtina_aciga_cikar | 50 | 0 | 100 | Cosmos and travel | A hidden route swallowed by the storm is revealed (%) |
| storm_loss_chance | firtina_kayip_sans | 50 | 0 | 100 | Cosmos and travel | An expedition on the route is lost in the storm (%) |
| fate_expedition_chance | efsanevi_sefer_sans | 8 | 0 | 100 | The Beyond | Fate opens a legendary expedition (%) |
| max_concurrent_expeditions | sefer_eszamanli | 1 | 0 | 20 | The Beyond | When open legendary expeditions (including the god's) reach this number, Fate opens no new one |
| immortality_chance | olumsuzluk_sans | 15 | 0 | 100 | The Beyond | A wise mortal attains immortality (%) |
| golem_min_power | golem_seviye | 4 | 1 | 12 | The Beyond | Minimum power level of a golem born from a spirit-cloaked structure |
| golem_hp | golem_can | 400 | 1 | 100,000 | The Beyond | Golem HP |
| golem_strength_base | golem_guc_taban | 70 | 0 | 100 | The Beyond | Golem base strength |
| golem_strength_die | golem_guc_zar | 25 | 1 | 100 | The Beyond | Golem strength die (1…n) |
| golem_agility | golem_ceviklik | 15 | 0 | 100 | The Beyond | Golem agility |
| golem_intelligence_base | golem_zeka_taban | 20 | 0 | 100 | The Beyond | Golem base intelligence |
| golem_intelligence_die | golem_zeka_zar | 30 | 1 | 100 | The Beyond | Golem intelligence die (1…n) |
| golem_danger_base | golem_tehlike_taban | 40 | 0 | 100 | The Beyond | Golem base danger |
| golem_danger_die | golem_tehlike_zar | 30 | 1 | 100 | The Beyond | Golem danger die (1…n) |
| spirit_cloak_item_might | ruh_kudret | 30 | 0 | 100 | The Beyond | Might increase of a spirit-cloaked item |
| spirit_cloak_vessel_strangeness | ruh_tuhaflik | 25 | 0 | 100 | The Beyond | Strangeness increase of a spirit-cloaked vessel |
| soul_buildup_leak | ruh_birikim_sizinti | 2 | 0 | 100 | The Beyond | Per-epoch leakage of soul buildup into the realm of the dead |
| soul_descent_cap | ruh_inis_tavan | 3 | 0 | 100 | The Beyond | Maximum souls that can descend into one realm of the dead per epoch |
| descended_spirit_power | inen_ruh_seviye | 3 | 1 | 12 | The Beyond | Power level of a descended spirit |
| descended_spirit_strength_base | inen_ruh_guc_taban | 30 | 0 | 100 | The Beyond | Base strength of a descended spirit |
| descended_spirit_strength_die | inen_ruh_guc_zar | 30 | 1 | 100 | The Beyond | Strength die of a descended spirit (1…n) |
| descended_spirit_unrest_base | inen_ruh_huzursuzluk_taban | 30 | 0 | 100 | The Beyond | Base unrest of a descended spirit |
| descended_spirit_unrest_die | inen_ruh_huzursuzluk_zar | 40 | 1 | 100 | The Beyond | Unrest die of a descended spirit (1…n) |
| soul_harvest_min_zealotry | ruh_hasat_bagnazlik | 65 | 0 | 100 | The Beyond | Minimum zealotry of a cult that can harvest souls |
| soul_harvest_follower_mult_pct | ruh_hasat_murit | 115 | 100 | 1000 | The Beyond | Follower multiplier in a soul harvest (%) |
| soul_harvest_influence_gain | ruh_hasat_etki | 5 | 0 | 100 | The Beyond | Cult influence gain in a soul harvest |
| cult_default_influence | tarikat_etki_varsayilan | 30 | 0 | 100 | The Beyond | Default influence of a cult with no recorded influence |
| planet_quake_severity | gezegen_deprem_siddet | 70 | 0 | 300 | The Beyond | Severity of the planet's earthquake shaking its polluter (%) |
| planet_worshipper_prosperity | gezegen_refah | 6 | 0 | 100 | The Beyond | Prosperity the planet gives its worshippers |
| planet_worshipper_population_pct | gezegen_nufus | 105 | 100 | 1000 | The Beyond | Population multiplier the planet gives its worshippers (%) |
| planet_close_skin_danger | gezegen_kapat_tehlike | 25 | 0 | 100 | The Beyond | Region danger change when the planet closes its skin |
| region_default_danger | bolge_tehlike_varsayilan | 30 | 0 | 100 | The Beyond | Default danger of a region with no recorded danger |
| planet_worship_candidates | gezegene_tapma_tavan | 1 | 0 | 100 | The Beyond | Godless communities eligible to worship the planet per epoch |
| archive_min_worlds | arsiv_dunya_esik | 2 | 1 | 100 | The Beyond | Minimum worlds required for a cosmic archive to appear |
| archive_power | arsiv_seviye | 9 | 1 | 12 | The Beyond | Power level of the cosmic archive |
| archive_splendor | arsiv_ihtisam | 95 | 0 | 100 | The Beyond | Splendor of the cosmic archive |
| archive_durability | arsiv_saglamlik | 70 | 0 | 100 | The Beyond | Durability of the cosmic archive |
| archive_function | arsiv_islev | 100 | 0 | 100 | The Beyond | Function of the cosmic archive |
| archive_seekers_cap | arsiv_bilgi_tavan | 2 | 0 | 100 | The Beyond | Maximum communities seeking knowledge from the archive per epoch |
| archive_burn_loss_pct | arsiv_yanma_pay | 25 | 0 | 100 | The Beyond | Share of knowledge links lost when the archive burns (%) |
| cosmic_plague_max_age | kozmik_salgin_cag | 3 | 0 | 50 | The Beyond | Oldest start of an expedition that can carry plague (epochs ago) |
| cosmic_plague_severity | kozmik_salgin_siddet | 80 | 0 | 300 | The Beyond | Severity of the cosmic plague (%) |
| mirror_births_cap | ayna_tavan | 3 | 0 | 100 | The Beyond | Maximum mirrors born on a mirror world per epoch |
| mirror_hp | ayna_can | 100 | 1 | 1000 | The Beyond | HP of a mirror birth |
| mirror_default_lifespan | ayna_omur_varsayilan | 70 | 1 | 50,000 | The Beyond | Lifespan of the mirror of a dead person with no recorded lifespan (years) |
| expedition_renown | sefer_un | 10 | 0 | 100 | The Beyond | Renown gain of each son when a legendary expedition completes |
| expedition_fail_leak | sefer_ceza_sizinti | 10 | 0 | 100 | The Beyond | Leakage into every world from a failed legendary expedition |
| oathbreaker_neighbor_distance | mahkeme_mesafe | 4 | 0 | 50 | The Beyond | Farthest distance of neighbours whose trust in an oathbreaker is shaken (steps) |
| oathbreaker_neighbors | mahkeme_komsu | 6 | 0 | 100 | The Beyond | Maximum neighbours whose trust in an oathbreaker is shaken |
| oathbreaker_relation_loss | mahkeme_iliski | 10 | 0 | 100 | The Beyond | Relation loss between the oathbreaker and its neighbours |
| immortality_threshold | olumsuzluk_esik | 120 | 0 | 200 | The Beyond | Intellect + charisma total of a mortal who can attain immortality |
| immortality_son_wrath | olumsuzluk_ofke | 4 | 0 | 100 | The Beyond | Wrath gain of the sons when a mortal becomes immortal |
| restitch_route_cost | dik_bedel | 40 | 0 | 500 | Cosmic actions | Cost for the god to re-stitch a severed or sealed route (essence) |
| sever_route_cost | kopar_bedel | 40 | 0 | 500 | Cosmic actions | Cost for the god to sever a route for a few epochs (essence) |
| sever_route_epochs | kopar_sure | 3 | 1 | 50 | Cosmos and travel | Epochs a route severed by the god stays closed (if no duration is given) |
| cult_default_followers | tarikat_murit_varsayilan | 50 | 1 | 100,000 | The Beyond | Followers assumed for a cult with no recorded follower count (soul harvest) |
| mirror_default_stat | ayna_stat_varsayilan | 50 | 0 | 100 | The Beyond | Unrecorded stat of the dead person (the mirror is born with its inverse) |

### CHRONICLE_REPEAT

Old namespace `KRONIK_TEKRAR` · 2 rows · defined in `src/kronik-onar.js`. Chronicle duplicate-line detection.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| root_letters | kok | 5 | 2 | 20 | Chronicle | Number of leading letters counted as a word root in chronicle repetition comparison |
| overlap_pct | ortak | 50 | 1 | 100 | Chronicle | Minimum share of an engine note's word roots appearing in a directly written line for the note to count as a repeat of it (%) |

### CIVILIZATION

Old namespace `MEDENIYET` · 71 rows · defined in `src/medeniyet.js` · also read by `src/oyuncu.js`. Civilization stages, colonies/independence, federations, previous-creation relics, loans, barter, adoption, treaties.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| independence_war_chance | bagimsizlik_savas_sans | 60 | 0 | 100 | Civilization | Independence turns into war (%) |
| federation_chance | federasyon_sans | 25 | 0 | 100 | Civilization | An inter-world federation is founded (%) |
| previous_creation_relic_chance | onceki_yaratilis_sans | 35 | 0 | 100 | Civilization | A remnant of a previous creation is found (%) |
| city_state_population | sehir_nufus | 3000 | 0 | 100,000,000 | Civilization | Minimum population to become a city-state |
| city_state_knowledge | sehir_bilgi | 1 | 0 | 100 | Civilization | Minimum known knowledge to become a city-state |
| kingdom_population | krallik_nufus | 20,000 | 0 | 100,000,000 | Civilization | Minimum population of a kingdom with no ruled places |
| kingdom_ruled_places | krallik_yonetim | 1 | 0 | 100 | Civilization | Minimum ruled places to become a kingdom |
| kingdom_knowledge | krallik_bilgi | 3 | 0 | 100 | Civilization | Minimum known knowledge to become a kingdom |
| empire_region_pct | imparatorluk_bolge | 50 | 0 | 100 | Civilization | Share of regions dominated for a world empire (% of settled regions; regions dominated by itself, its subjects and its tributaries) |
| empire_population_pct | imparatorluk_nufus | 25 | 0 | 100 | Civilization | For a world empire (if region share is not enough): be the most populous political power of its world and hold this share of the world's population (%; including subjects and tributaries) |
| empire_min_world_regions | imparatorluk_bolge_alt | 2 | 1 | 1000 | Civilization | Minimum regions of a world on which a world empire can count |
| interstellar_worlds | yildizlararasi_dunya | 2 | 1 | 100 | Civilization | Minimum worlds spread across for an interstellar power |
| cosmic_worlds | kozmik_dunya | 3 | 1 | 100 | Civilization | Minimum worlds spread across for a cosmic power |
| stage_demotion_pct | basamak_dusus_pay | 15 | 0 | 100 | Civilization | Demotion margin: a community at a stage regresses only when it drops this percentage below the population and dominated-share thresholds (so it doesn't flicker at the threshold) |
| stage_min_epochs | basamak_en_az_cag | 3 | 0 | 100 | Civilization | A community that changes stage doesn't reverse direction for at least this many epochs (a riser doesn't fall back, a faller doesn't rise back; 0: off) |
| colony_independence_min_age | koloni_yas | 3 | 0 | 100 | Civilization | Minimum age of a colony that can seek independence (epochs) |
| colony_far_cooling | koloni_uzak_iliski | 4 | 0 | 100 | Civilization | Per-epoch cooling of a colony on another world toward its homeland |
| colony_near_cooling | koloni_yakin_iliski | 1 | 0 | 100 | Civilization | Per-epoch cooling of a colony on the same world toward its homeland |
| colony_far_independence_chance | koloni_uzak_sans | 12 | 0 | 100 | Civilization | A colony on another world declares independence (%) |
| colony_near_independence_chance | koloni_yakin_sans | 4 | 0 | 100 | Civilization | A colony on the same world declares independence (%) |
| colony_prosperity_base | koloni_refah_taban | 40 | 0 | 100 | Civilization | Colony prosperity at which the independence chance starts to rise |
| colony_prosperity_divisor | koloni_refah_bolen | 400 | 10 | 100,000 | Civilization | Prosperity contribution to independence: (prosperity − base) / this number |
| colony_grudge_bonus_pct | koloni_kin_sans | 10 | 0 | 100 | Civilization | Independence contribution of a colony estranged from its homeland (%) |
| federation_min_members | federasyon_uye | 3 | 2 | 100 | Civilization | Minimum members of a federation |
| federation_max | federasyon_en_cok | 1 | 0 | 100 | Civilization | Maximum simultaneous federations in the cosmos (a community can only be a member of one; 0 disables) |
| federation_min_worlds | federasyon_dunya | 2 | 1 | 100 | Civilization | Minimum worlds federation members are spread across |
| federation_power | federasyon_guc_seviye | 6 | 1 | 12 | Civilization | Power level of a federation |
| federation_strength | federasyon_guc | 50 | 0 | 100 | Civilization | Strength of a federation |
| federation_wealth | federasyon_servet | 60 | 0 | 100 | Civilization | Wealth of a federation |
| federation_sway | federasyon_nufuz | 70 | 0 | 100 | Civilization | Sway of a federation |
| relic_site_power | kalinti_guc_seviye | 7 | 1 | 12 | Civilization | Power level of a previous-creation remnant |
| relic_site_danger | kalinti_tehlike | 50 | 0 | 100 | Civilization | Base danger of the remnant |
| relic_site_danger_die | kalinti_tehlike_zar | 30 | 1 | 100 | Civilization | Danger die of the remnant |
| relic_site_fertility | kalinti_bereket | 10 | 0 | 100 | Civilization | Fertility of the remnant |
| relic_site_mystery | kalinti_gizem | 95 | 0 | 100 | Civilization | Mystery of the remnant |
| heirloom_power | emanet_guc_seviye | 8 | 1 | 12 | Civilization | Power level of a previous-creation heirloom |
| heirloom_damage | emanet_hasar | 40 | 0 | 100 | Civilization | Base damage of the heirloom |
| heirloom_damage_die | emanet_hasar_zar | 40 | 1 | 100 | Civilization | Damage die of the heirloom |
| heirloom_protection | emanet_koruma | 30 | 0 | 100 | Civilization | Base protection of the heirloom |
| heirloom_protection_die | emanet_koruma_zar | 40 | 1 | 100 | Civilization | Protection die of the heirloom |
| heirloom_might | emanet_kudret | 80 | 0 | 100 | Civilization | Base might of the heirloom |
| heirloom_might_die | emanet_kudret_zar | 20 | 1 | 100 | Civilization | Might die of the heirloom |
| heirloom_curse | emanet_lanet | 50 | 0 | 100 | Civilization | Base curse of the heirloom |
| heirloom_curse_die | emanet_lanet_zar | 40 | 1 | 100 | Civilization | Curse die of the heirloom |
| ancient_knowledge_power | eski_bilgi_guc_seviye | 7 | 1 | 12 | Civilization | Power level of previous-creation knowledge |
| ancient_knowledge_level | eski_bilgi_seviye | 7 | 1 | 10 | Civilization | Level of previous-creation knowledge |
| ancient_knowledge_forbidden_chance | eski_bilgi_yasak_sans | 50 | 0 | 100 | Civilization | Previous-creation knowledge is forbidden knowledge (%) |
| loan_chance | borc_sans | 10 | 0 | 100 | Economy | A wealthy community lends to its poor neighbour on its own (% per epoch) |
| loan_lender_min | borc_zengin | 55 | 0 | 100 | Economy | Minimum wealth or prosperity of a community able to lend |
| loan_borrower_max | borc_yoksul | 35 | 0 | 100 | Economy | Maximum wealth or prosperity of a community asking for a loan |
| loan_amount | borc_miktar | 10 | 1 | 100 | Economy | Amount of a spontaneous loan |
| loan_term | borc_vade | 3 | 1 | 50 | Economy | Term of a spontaneous loan (epochs) |
| loan_distance | borc_mesafe | 3 | 0 | 99 | Economy | Farthest distance between borrowing communities (steps) |
| loan_repay_chance | borc_ode_sans | 40 | 0 | 100 | Economy | A debtor able to pay repays on its own (% per epoch) |
| loan_repay_reserve | borc_ode_pay | 10 | 0 | 100 | Economy | Wealth or prosperity the debtor must keep after paying |
| loan_relation | borc_iliski | 5 | 0 | 100 | Economy | Relation contribution of a spontaneous loan |
| loan_repay_relation | borc_ode_iliski | 8 | 0 | 100 | Economy | Relation contribution of a repaid loan |
| loan_default_relation | borc_gecikme | 20 | 0 | 100 | Economy | Relation damage of a loan not repaid on time (all loans of the engine and mortals) |
| barter_chance | takas_sans | 8 | 0 | 100 | Economy | Trade partners barter items on their own (% per epoch) |
| barter_max_value_diff | takas_fark | 25 | 0 | 100 | Economy | Maximum value difference between two bartered things |
| barter_relation | takas_iliski | 6 | 0 | 100 | Economy | Relation contribution of a spontaneous barter |
| adoption_chance | evlat_sans | 6 | 0 | 100 | Heroes and mortals | An old mortal adopts a nearby orphaned youth on their own (% per epoch) |
| adoption_max_child_age | evlat_cocuk_yas | 16 | 0 | 1000 | Heroes and mortals | Oldest age that can be adopted (years) |
| adoption_min_age_gap | evlat_yas_fark | 15 | 0 | 1000 | Heroes and mortals | Minimum age gap between adopter and child (years) |
| adoption_distance | evlat_mesafe | 1 | 0 | 99 | Heroes and mortals | Farthest distance between adopter and child (steps) |
| adoption_relation | evlat_iliski | 10 | 0 | 100 | Heroes and mortals | Relation contribution of adoption |
| treaty_chance | antlasma_sans | 8 | 0 | 100 | Civilization | Communities of two worlds connected by an open route make a treaty on their own (% per epoch) |
| treaty_trade_min_relation | antlasma_ticaret_esik | 0 | -100 | 100 | Civilization | Minimum relation for an inter-world trade treaty |
| treaty_alliance_min_relation | antlasma_ittifak_esik | 25 | -100 | 100 | Civilization | Minimum relation for an inter-world alliance of trade partners |
| treaty_candidates | antlasma_aday | 4 | 1 | 100 | Civilization | Number of most populous communities examined at each end of the route for a treaty |
| treaty_relation | antlasma_iliski | 12 | 0 | 100 | Civilization | Relation contribution of a spontaneous inter-world treaty |

### CLIMATE_EFFECTS

Old namespace `IKLIM_ETKI` · 12 rows · defined in `src/rules.js`. Climate age effects and base weights.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| temperate_fertility | ilik_bereket | 1 | -50 | 50 | Population and growth | Temperate age: fertility change per epoch |
| temperate_weight | ilik_agirlik | 40 | 0 | 1000 | Population and growth | Weight of the temperate age occurring |
| drought_century_fertility | kurak_bereket | -5 | -50 | 50 | Population and growth | Drought century: fertility change per epoch |
| drought_century_weight | kurak_agirlik | 18 | 0 | 1000 | Population and growth | Weight of the drought century occurring |
| rain_age_fertility | yagmur_bereket | 4 | -50 | 50 | Population and growth | Rain age: fertility change per epoch |
| rain_age_weight | yagmur_agirlik | 18 | 0 | 1000 | Population and growth | Weight of the rain age occurring |
| ice_age_fertility | buzul_bereket | -4 | -50 | 50 | Population and growth | Ice age: fertility change per epoch |
| ice_age_weight | buzul_agirlik | 12 | 0 | 1000 | Population and growth | Weight of the ice age occurring |
| scorching_age_fertility | sicak_bereket | -3 | -50 | 50 | Population and growth | Scorching age: fertility change per epoch |
| scorching_age_weight | sicak_agirlik | 12 | 0 | 1000 | Population and growth | Weight of the scorching age occurring |
| ice_age_population_loss | buzul_nufus | 3 | 0 | 100 | Population and growth | Ice age: population loss per epoch (%) |
| scorching_age_plague_freq | sicak_veba | 150 | 0 | 1000 | Population and growth | Scorching age: plague frequency (%) |

### CLIMATE_WORLD_TYPE

Old namespace `IKLIM_TUR` · 15 rows · defined in `src/rules.js`. Climate weight multipliers by world type.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| ocean_ice_age | okyanus_buzul | 25 | 0 | 1000 | Population and growth | Ocean world: ice-age weight (%) |
| ocean_drought | okyanus_kurak | 30 | 0 | 1000 | Population and growth | Ocean world: drought weight (%) |
| ocean_rain | okyanus_yagmur | 200 | 0 | 1000 | Population and growth | Ocean world: rain-age weight (%) |
| sand_drought | kum_kurak | 250 | 0 | 1000 | Population and growth | Sand world: drought weight (%) |
| sand_rain | kum_yagmur | 30 | 0 | 1000 | Population and growth | Sand world: rain-age weight (%) |
| sand_scorching | kum_sicak | 180 | 0 | 1000 | Population and growth | Sand world: scorching-age weight (%) |
| ice_ice_age | buz_buzul | 300 | 0 | 1000 | Population and growth | Ice world: ice-age weight (%) |
| ice_scorching | buz_sicak | 20 | 0 | 1000 | Population and growth | Ice world: scorching-age weight (%) |
| ice_drought | buz_kurak | 60 | 0 | 1000 | Population and growth | Ice world: drought weight (%) |
| lava_scorching | lav_sicak | 300 | 0 | 1000 | Population and growth | Lava world: scorching-age weight (%) |
| lava_ice_age | lav_buzul | 10 | 0 | 1000 | Population and growth | Lava world: ice-age weight (%) |
| lava_rain | lav_yagmur | 40 | 0 | 1000 | Population and growth | Lava world: rain-age weight (%) |
| gas_rain | gaz_yagmur | 150 | 0 | 1000 | Population and growth | Gas world: rain-age weight (%) |
| dead_temperate | olu_ilik | 150 | 0 | 1000 | Population and growth | Dead world: temperate-age weight (%) |
| dead_rain | olu_yagmur | 50 | 0 | 1000 | Population and growth | Dead world: rain-age weight (%) |

### CONTENT

Old namespace `ICERIK` · 14 rows · defined in `src/agents.js` · also read by `src/epoch.js`. Content jobs: image prompts, revelation, epics, deepening.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| image_prompt_batch | prompt_parti | 24 | 1 | 500 | Content jobs | Maximum entities in one image-prompt batch |
| image_prompt_description_chars | prompt_aciklama | 500 | 20 | 20,000 | Context budgets | Image-prompt request: entity description (characters) |
| image_prompt_min_chars | prompt_en_az | 20 | 0 | 2000 | Content jobs | An image prompt shorter than this is not accepted (characters) |
| cosmic_image_prompt_max_chars | prompt_tavan | 1200 | 50 | 20,000 | Content jobs | Maximum length of a cosmic body's image prompt (characters) |
| cosmic_prompt_batch | kozmos_parti | 16 | 1 | 500 | Content jobs | Cosmic bodies whose image prompts are written in one batch |
| cosmic_prompt_world_chars | kozmos_dunya | 400 | 20 | 20,000 | Context budgets | Cosmos prompt request: world description (characters) |
| cosmic_prompt_other_chars | kozmos_diger | 300 | 20 | 20,000 | Context budgets | Cosmos prompt request: star and foreign-god description (characters) |
| revelation_wisdom | vahiy_bilgelik | 130 | 1 | 1000 | Content jobs | Detail of the world summary the revelation sees (like wisdom) |
| revelation_max_power | vahiy_guc_tavan | 10 | 1 | 11 | Content jobs | Maximum power level of a revelation |
| god_epic_trace | tanri_iz | 160 | 0 | 10,000 | Context budgets | The god's epic: its trace in the chronicle (records) |
| god_deepen_trace | tanri_iz_derin | 80 | 0 | 10,000 | Context budgets | The god's deepening: its trace in the chronicle (records) |
| deepen_neighbor_links | derin_bag | 20 | 0 | 1000 | Context budgets | Deepening: neighbouring links |
| deepen_recent_events | derin_kronik | 20 | 0 | 1000 | Context budgets | Deepening: recent events |
| son_epic_trace | destan_iz | 120 | 0 | 10,000 | Context budgets | Son's epic: its trace in the chronicle (records) |

### CONTEXT

Old namespace `BAGLAM` · 57 rows · defined in `src/world.js` · also read by `src/olumluler.js`. LLM prompt context budgets for sons, Fate and mortals.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| canon_cache_batch | kanon_parti | 500 | 1 | 100,000 | Context budgets | Engine cache: changed entities are re-read in batches of this size |
| son_geography_chars | ogul_cografya | 5000 | 500 | 100,000 | Context budgets | Son: geography and inhabitants (characters) |
| son_map_chars | ogul_harita | 2500 | 200 | 50,000 | Context budgets | Son: map (characters) |
| son_cosmos_chars | ogul_kozmos | 1500 | 200 | 30,000 | Context budgets | Son: other worlds (characters) |
| son_language_chars | ogul_dil | 1600 | 200 | 30,000 | Context budgets | Son: languages and lexicon (characters) |
| son_unlocated_chars | ogul_konumsuz | 1500 | 200 | 30,000 | Context budgets | Son: legends and traditions (characters) |
| son_chronicle_chars | ogul_kronik | 2200 | 200 | 30,000 | Context budgets | Son: recent events (characters) |
| son_summary_chars | ogul_ozet | 14,000 | 2000 | 200,000 | Context budgets | Son: entire world summary (characters) |
| son_memory_chars | ogul_hafiza | 5000 | 500 | 100,000 | Context budgets | Son: memory (characters) |
| son_prompt_chars | ogul_istem | 24,000 | 4000 | 400,000 | Context budgets | Son: entire turn prompt (characters) |
| son_chronicle_lines | ogul_kronik_satir | 10 | 1 | 200 | Context budgets | Son: lines of recent events (+ wisdom/8) |
| read_tool_multiplier | arac_kat | 3 | 1 | 50 | Context budgets | Read tools: how many times longer recent events and memories are when a section cut from the prompt is shown in full |
| short_cosmology_chars | kisa_kozmoloji | 500 | 50 | 100,000 | Context budgets | Length of the cosmology in the mortals' short world header (characters) |
| section_min_chars | bolum_taban | 600 | 0 | 100,000 | Context budgets | Minimum space reserved for each context section (characters; whole section if it is short) |
| budget_trim_min_chars | butce_kirp_en_az | 120 | 0 | 10,000 | Context budgets | Context budget: minimum space for a non-fitting line to be included truncated (characters) |
| memory_named_worshippers | hafiza_tapan | 12 | 0 | 1000 | Context budgets | Son memory: worshippers shown by name (the rest as a count) |
| son_threads | ogul_iplik | 6 | 1 | 100 | Context budgets | Son: open story threads shown |
| fate_geography_chars | kader_cografya | 9000 | 500 | 200,000 | Context budgets | Fate: geography (characters) |
| fate_map_chars | kader_harita | 4000 | 200 | 100,000 | Context budgets | Fate: map (characters) |
| fate_cosmos_chars | kader_kozmos | 2500 | 200 | 50,000 | Context budgets | Fate: other worlds (characters) |
| fate_language_chars | kader_dil | 3000 | 200 | 50,000 | Context budgets | Fate: languages (characters) |
| fate_unlocated_chars | kader_konumsuz | 3000 | 200 | 50,000 | Context budgets | Fate: legends and traditions (characters) |
| fate_chronicle_chars | kader_kronik | 4000 | 200 | 50,000 | Context budgets | Fate: recent events (characters) |
| fate_summary_chars | kader_ozet | 26,000 | 2000 | 400,000 | Context budgets | Fate: entire world summary (characters) |
| fate_chronicle_lines | kader_kronik_satir | 24 | 1 | 400 | Context budgets | Fate: lines of recent events |
| mortal_context_chars | olumlu_baglam | 12,000 | 2000 | 200,000 | Context budgets | Mortal: entire context (characters) |
| memory_creations_chars | hafiza_yaratim | 1600 | 200 | 50,000 | Context budgets | Son memory: creations (characters) |
| memory_recollections_chars | hafiza_ani | 1200 | 200 | 50,000 | Context budgets | Son memory: recollections (characters) |
| memory_about_chars | hafiza_hakkinda | 900 | 100 | 50,000 | Context budgets | Son memory: events about the son (characters) |
| memory_folk_beliefs_chars | hafiza_inanc | 900 | 100 | 50,000 | Context budgets | Son memory: folk beliefs (characters) |
| memory_messages_chars | hafiza_soz | 1000 | 100 | 50,000 | Context budgets | Son memory: incoming messages (characters) |
| repeat_warning_threshold | tekrar_esik | 3 | 2 | 50 | Son tools | "You are repeating yourself" warning in memory: creations of the same subtype |
| repeat_window | tekrar_pencere | 20 | 1 | 500 | Son tools | Repetition check in memory: recent creations examined |
| son_location_tree_lines | ogul_agac | 90 | 10 | 5000 | Context budgets | Son: lines in the location tree (+ wisdom) |
| fate_location_tree_lines | kader_agac | 220 | 10 | 10,000 | Context budgets | Fate: lines in the location tree |
| son_chronicle_wisdom_step | ogul_kronik_bilgelik | 8 | 1 | 100 | Context budgets | Son: every this much wisdom adds one line to recent events |
| son_words_per_language | ogul_dil_ornek | 6 | 0 | 200 | Context budgets | Son: sample words per language |
| fate_words_per_language | kader_dil_ornek | 10 | 0 | 200 | Context budgets | Fate: sample words per language |
| near_language_extra_words | dil_yakin_ek | 4 | 0 | 100 | Context budgets | Extra sample words in the son's nearby languages |
| far_language_fewer_words | dil_uzak_eksik | 3 | 0 | 100 | Context budgets | Fewer sample words in the son's distant languages |
| far_language_min_words | dil_uzak_en_az | 3 | 0 | 100 | Context budgets | Minimum sample words in distant languages |
| unlocated_rows | konumsuz_satir | 45 | 1 | 1000 | Context budgets | Legends and traditions: newest records shown |
| inspect_lexicon_words | incele_sozluk | 40 | 0 | 2000 | Context budgets | Entity inspection: words shown from the language's lexicon |
| inspect_canon_facts | incele_gercek | 8 | 0 | 200 | Context budgets | Entity inspection: canon facts shown |
| canon_facts_default | gercek_sayi | 12 | 1 | 500 | Context budgets | Canon facts: default lines |
| chronicle_default | kronik_sayi | 12 | 1 | 500 | Context budgets | Recent events: default lines |
| search_results_max | arama_sonuc | 25 | 1 | 500 | Context budgets | search_entity (varlik_ara): maximum results |
| lexicon_default_words | sozluk_sayi | 400 | 1 | 100,000 | Context budgets | Default words from a language's lexicon |
| memory_creations_count | hafiza_yaratim_sayi | 30 | 1 | 500 | Context budgets | Son memory: number of recent creations |
| memory_recollections_count | hafiza_ani_sayi | 12 | 1 | 500 | Context budgets | Son memory: number of recent recollections |
| memory_about_count | hafiza_hakkinda_sayi | 10 | 1 | 500 | Context budgets | Son memory: number of recent events about the son |
| memory_messages_count | hafiza_soz_sayi | 10 | 1 | 500 | Context budgets | Son memory: number of recent incoming messages |
| thread_related_score | iplik_ilgili | 3 | 0 | 100 | Context budgets | Story priority: score per related record of the son |
| thread_name_score | iplik_ad | 4 | 0 | 100 | Context budgets | Story priority: score if the son's name appears in the text |
| thread_stale_penalty | iplik_durgun | 50 | 0 | 1000 | Context budgets | Story priority: score lost per stagnant epoch (percentage points) |
| thread_progressed_score | iplik_ilerlemis | 1 | 0 | 100 | Context budgets | Story priority: score if it has progressed at all |
| apocalypse_warning_pct | kiyamet_uyari | 30 | 0 | 100 | Apocalypse | Doomsday clock appears in the prompt at this percentage of the threshold |

### CORE_RULES

Old namespace `KURAL` · 45 rows · defined in `src/rules.js` · also read by `src/epoch.js`, `src/olumluler.js`, `src/tools.js`, `src/world.js`. Core son/entity formulas: tiers, stars, existence, HP/essence, costs, relations, action points.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| tier_uncommon | sinif_seckin | 3 | 1 | 30 | Rarity tiers | Entity power level: this and above is Uncommon |
| tier_rare | sinif_nadir | 5 | 1 | 30 | Rarity tiers | Entity power level: this and above is Rare |
| tier_epic | sinif_destansi | 7 | 1 | 30 | Rarity tiers | Entity power level: this and above is Epic |
| tier_legendary | sinif_efsanevi | 9 | 1 | 30 | Rarity tiers | Entity power level: this and above is Legendary |
| tier_mythic | sinif_mitik | 11 | 1 | 30 | Rarity tiers | Entity power level: this and above is Mythic |
| star_level_step | yildiz_seviye | 2 | 1 | 10 | Rarity tiers | Star requirement: level needed per star (for ★n: n × this − 1) |
| star_renown_step | yildiz_un | 15 | 0 | 100 | Rarity tiers | Star requirement: renown needed per star |
| star_essence_base | yildiz_oz_taban | 15 | 0 | 500 | Rarity tiers | Star requirement: base of the essence cost |
| star_essence_step | yildiz_oz | 10 | 0 | 500 | Rarity tiers | Star requirement: extra essence cost per star |
| stars_per_power_cap | yildiz_guc_adim | 2 | 1 | 10 | Rarity tiers | Every this many stars raises the power cap by 1 |
| existence_base | varlik_taban | 25 | 0 | 100 | Creator and essence | Base of a son's existence |
| existence_faith_cap | varlik_inanc_tavan | 40 | 0 | 100 | Creator and essence | Maximum contribution of faith to existence |
| existence_faith_divisor | varlik_inanc_bolen | 2 | 1 | 100 | Creator and essence | Faith contribution to existence: faith / this number |
| existence_renown_cap | varlik_un_tavan | 25 | 0 | 100 | Creator and essence | Maximum contribution of renown to existence |
| existence_renown_divisor | varlik_un_bolen | 4 | 1 | 100 | Creator and essence | Renown contribution to existence: renown / this number |
| existence_anchor_bonus | varlik_capa | 10 | 0 | 100 | Creator and essence | Contribution of a living anchor to existence |
| existence_anchorless_penalty | varlik_capasiz | 20 | 0 | 100 | Creator and essence | Existence loss of a son whose anchor has been destroyed |
| existence_no_worshipper_penalty | varlik_tapansiz | 15 | 0 | 100 | Creator and essence | Existence loss of a son with no worshippers at all |
| existence_radiant | varlik_parlak | 80 | 0 | 100 | Creator and essence | Existence at or above this is Radiant |
| existence_solid | varlik_saglam | 30 | 0 | 100 | Creator and essence | Existence at or above this is Solid (below it, one action point less) |
| existence_faded | varlik_solgun | 12 | 0 | 100 | Creator and essence | Existence at or above this is Faded (below it, cannot act) |
| strength_bonus | guclu_yan | 15 | 0 | 50 | Rarity tiers | Stat added to a summoned son's strong points |
| weakness_penalty | zayif_yan | 15 | 0 | 50 | Rarity tiers | Stat subtracted from a summoned son's weak point |
| max_hp_base | can_taban | 50 | 1 | 1000 | God and son costs | Base of a son's maximum HP |
| max_hp_per_endurance | can_dayaniklilik | 150 | 0 | 1000 | God and son costs | Contribution of endurance to maximum HP (% per endurance point) |
| max_essence_base | oz_taban | 40 | 1 | 1000 | God and son costs | Base of a son's maximum essence |
| max_essence_per_might | oz_kudret | 160 | 0 | 1000 | God and son costs | Contribution of might to maximum essence (% per might point) |
| default_might | oz_kudret_varsayilan | 20 | 0 | 100 | God and son costs | Might assumed for a son whose might is unknown |
| xp_per_level | xp_seviye | 100 | 1 | 10,000 | God and son costs | XP needed per level for the next level |
| cost_per_power_level | bedel_guc_seviye | 3 | 0 | 50 | God and son costs | Creation-cost surcharge per power level |
| cost_in_domain_pct | bedel_alan_uyumlu | 60 | 1 | 500 | God and son costs | Cost of a creation within one's own domain (%) |
| cost_out_of_domain_pct | bedel_alan_disi | 130 | 1 | 500 | God and son costs | Cost of a creation in another domain (%) |
| creativity_discount_pct | bedel_yaraticilik | 40 | 0 | 100 | God and son costs | Share of creation cost removed by 100 creativity (%) |
| cheap_power_cost_pct | bedel_ucuz_guc | 60 | 1 | 100 | God and son costs | Cost with the cheap-creation power (%) |
| initiative_die | inisiyatif_zar | 20 | 1 | 100 | God and son costs | Faces of the initiative die (result is added doubled) |
| relation_blood_enemy | iliski_kan | 70 | 0 | 100 | War and diplomacy | God relation at or below minus this is blood enemy |
| relation_enemy | iliski_dusman | 35 | 0 | 100 | War and diplomacy | God relation at or below minus this is enemy |
| relation_cold | iliski_soguk | 10 | 0 | 100 | War and diplomacy | God relation at or below minus this is cold |
| relation_friend | iliski_dost | 15 | 0 | 100 | War and diplomacy | God relation at or above this is friend |
| relation_close_friend | iliski_yakin | 45 | 0 | 100 | War and diplomacy | God relation at or above this is close friend |
| relation_sibling | iliski_kardes | 75 | 0 | 100 | War and diplomacy | God relation at or above this is sibling (brother) |
| tireless_extra_action | ek_eylem_guc | 1 | 0 | 10 | Rarity tiers | Extra action granted by the "Tireless" power |
| max_star_extra_action | ek_eylem_yildiz | 1 | 0 | 10 | Rarity tiers | Extra action of a son who reaches the highest star (★5) |
| faded_action_loss | solgun_eylem_kaybi | 1 | 0 | 10 | Rarity tiers | Actions lost by a son whose existence falls below the Solid threshold |
| min_actions | en_az_eylem | 1 | 0 | 10 | Rarity tiers | Minimum actions per epoch of a son who has not faded |

### COSMIC_COSTS

Old namespace `KOZMIK_BEDEL` · 8 rows · defined in `src/rules.js` · also read by `src/denge.js`, `src/epoch.js`, `src/tools.js`. Creator's cosmic action costs — static object in rules.js.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| ignite_star | yildiz | 80 | 0 | 500 | Cosmic actions | Ignite a star |
| seal_gate | muhur | 30 | 0 | 500 | Cosmic actions | Seal a gate |
| cleanse_leak | temizle | 80 | 0 | 500 | Cosmic actions | Cleanse a leak |
| forget_world | unut | 20 | 0 | 500 | Cosmic actions | Forget a world |
| sky_event | gok | 50 | 0 | 500 | Cosmic actions | Sky event |
| rekindle_dead_star | tutustur | 60 | 0 | 500 | Cosmic actions | Rekindle a dead star |
| spirit_cloak | ruh | 15 | 0 | 500 | Cosmic actions | Cloak with spirit |
| legendary_expedition | sefer | 30 | 0 | 500 | Cosmic actions | Legendary expedition |

### COSMIC_HORROR

Old namespace `KORKU` · 71 rows · defined in `src/korku.js` · also read by `src/olumluler.js`, `src/world.js`. Leak (seepage from beyond), sanity, Outer Beings, Whisperers.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| alignment_route_danger | dizilim_tehlike | 15 | 0 | 100 | Cosmic horror | Route danger increase when the stars align |
| apocalypse_leak | kiyamet_sizinti | 4 | 0 | 50 | Cosmic horror | Contribution to leak when the apocalypse reaches its threshold (per epoch) |
| horror_event_divisor | korku_olay_bolen | 250 | 10 | 10,000 | Cosmic horror | Horror event chance: leak / this number |
| young_cap | genc_tavan | 25 | 0 | 100 | Cosmic horror | Initial leak cap on a young world |
| young_cap_growth | genc_tavan_artis | 8 | 0 | 100 | Cosmic horror | Per-epoch increase of the leak cap on a young world |
| repair_threshold | onarim_esik | 30 | 0 | 100 | Cosmic horror | Leak at which the fabric starts repairing itself |
| repair_divisor | onarim_bolen | 8 | 1 | 100 | Cosmic horror | Repair: −1 for every this many points above the threshold |
| outer_being_threshold | dis_varlik_esik | 85 | 1 | 100 | Cosmic horror | Leak at which an Outer Being appears |
| calling_threshold | cagri_esik | 50 | 0 | 100 | Apocalypse | Average leak at which the apocalypse turns into the Calling |
| madness_chance | delilik_sans | 30 | 0 | 100 | Cosmic horror | Madness event in a community whose sanity collapses (%) |
| whisperers_chance | fisildayan_sans | 50 | 0 | 100 | Cosmic horror | Madness turns into an outer cult (%) |
| outer_being_chance | dis_varlik_sans | 40 | 0 | 100 | Cosmic horror | An Outer Being appears when the threshold is exceeded (%) |
| forbidden_knowledge_leak | yasak_sizinti | 4 | 0 | 50 | Cosmic horror | Leak contribution of each community knowing forbidden knowledge |
| gate_leak | kapi_sizinti | 2 | 0 | 50 | Cosmic horror | Leak contribution of each open gate, swallowing or dream route |
| dead_star_leak | olu_yildiz_sizinti | 3 | 0 | 50 | Cosmic horror | Leak contribution of a dead, black or broken star |
| godless_leak | tanrisiz_sizinti | 1 | 0 | 50 | Cosmic horror | Leak contribution of each godless community |
| addicted_leak | bagimli_sizinti | 2 | 0 | 50 | Cosmic horror | Leak contribution of each addicted community |
| outer_cult_leak | dis_tarikat_sizinti | 3 | 0 | 50 | Cosmic horror | Leak contribution of each outer cult |
| outer_being_leak | dis_varlik_sizinti | 5 | 0 | 50 | Cosmic horror | Leak contribution of each Outer Being |
| worshipper_repair | tapinan_onarim | 50 | 0 | 1000 | Cosmic horror | Leak repair by each worshipping community (percentage points; total limited by worshipper_cap) |
| worshipper_cap | tapinan_tavan | 5 | 0 | 100 | Cosmic horror | Cap of repair coming from the number of worshipping communities (a crowded world cannot repair the fabric infinitely; the rest comes from the worshipper ratio) |
| priest_cap | rahip_tavan | 3 | 0 | 100 | Cosmic horror | Cap of repair by communities with a strong priest class (1 per community) |
| worshipper_ratio_repair | tapinan_oran_onarim | 3 | 0 | 50 | Cosmic horror | Repair from the worshipper ratio (if everyone worships) |
| temple_cap | tapinak_tavan | 3 | 0 | 50 | Cosmic horror | Maximum leak repair by temples (1 per temple) |
| priest_min_pct | rahip_esik | 10 | 0 | 100 | Cosmic horror | Minimum priest-class share that repairs leak (%) |
| fabric_self_repair | doku_onarim | 1 | 0 | 50 | Cosmic horror | Spontaneous repair of the fabric each epoch |
| repair_full_at | onarim_tam | 25 | 1 | 100 | Cosmic horror | Repair by worship, temples and priests reaches full strength at this leak; below it, it decreases proportionally to leak (an untorn fabric is not repaired) |
| young_growth_pct | genc_carpan | 50 | 0 | 100 | Cosmic horror | Remaining share of leak growth on a young world (%) |
| warning_1 | uyari1 | 30 | 0 | 100 | Cosmic horror | Leak at which the first leak warning arrives |
| warning_2 | uyari2 | 60 | 0 | 100 | Cosmic horror | Leak at which the "geometry is breaking" warning arrives |
| default_sanity | sagduyu_varsayilan | 70 | 0 | 100 | Cosmic horror | Sanity assumed for a community with no recorded sanity |
| leak_erosion_divisor | sizinti_asinma_bolen | 20 | 1 | 1000 | Cosmic horror | Sanity erosion: leak / this number |
| forbidden_erosion | yasak_asinma | 6 | 0 | 100 | Cosmic horror | Per-epoch sanity loss of those who know forbidden knowledge |
| outer_being_erosion | dis_asinma | 4 | 0 | 100 | Cosmic horror | Per-epoch sanity loss on a world with an Outer Being |
| medicine_repair | tip_onarim | 3 | 0 | 100 | Cosmic horror | Per-epoch sanity repair for those who know medicine |
| priest_repair_divisor | rahip_onarim_bolen | 5 | 1 | 100 | Cosmic horror | Sanity repair: priest share / this number |
| worship_repair | tapar_onarim | 1 | 0 | 100 | Cosmic horror | Per-epoch sanity repair of someone who worships a god |
| sanity_self_repair | sagduyu_onarim | 1 | 0 | 100 | Cosmic horror | Per-epoch spontaneous sanity repair |
| clouding_threshold | bulaniklik_esik | 40 | 0 | 100 | Cosmic horror | Sanity at which the mind starts to cloud |
| madness_threshold | delilik_esik | 20 | 0 | 100 | Cosmic horror | Sanity at which madness begins |
| madness_population_loss_pct | delilik_kayip | 6 | 0 | 100 | Cosmic horror | Population lost in a madness epidemic (%) |
| whisperers_power | fisildayan_guc | 3 | 1 | 12 | Cosmic horror | Power level of the Whisperers cult |
| whisperers_min_followers | fisildayan_murit_en_az | 50 | 1 | 100,000 | Cosmic horror | Minimum followers of the Whisperers |
| whisperers_default_population | fisildayan_nufus_varsayilan | 1000 | 1 | 1,000,000 | Cosmic horror | Population assumed for a people with no recorded population (for the Whisperers) |
| whisperers_share_pct | fisildayan_pay | 5 | 0 | 100 | Cosmic horror | Share of the people passing to the Whisperers (%) |
| whisperers_zealotry | fisildayan_bagnazlik | 85 | 0 | 100 | Cosmic horror | Zealotry of the Whisperers |
| whisperers_influence | fisildayan_etki | 40 | 0 | 100 | Cosmic horror | Influence of the Whisperers |
| whisperers_sanity | fisildayan_sagduyu | 10 | 0 | 100 | Cosmic horror | Sanity of the Whisperers |
| madness_son_essence_divisor | delilik_oz_bolen | 15 | 1 | 1000 | Cosmic horror | Per-epoch essence of a son with the Madness domain: average leak / this number |
| madness_son_existence_gain | delilik_varlik | 1 | 0 | 100 | Cosmic horror | Per-epoch existence gain of a son with the Madness domain |
| default_existence | varlik_varsayilan | 60 | 0 | 100 | Cosmic horror | Existence assumed for a son with no recorded existence |
| outer_being_power | dis_guc | 10 | 1 | 12 | Cosmic horror | Power level of an Outer Being |
| outer_being_size_base | dis_buyukluk | 60 | 0 | 100 | Cosmic horror | Base size of an Outer Being |
| outer_being_size_die | dis_buyukluk_zar | 40 | 1 | 100 | Cosmic horror | Die added to an Outer Being's size |
| outer_being_interest_base | dis_ilgi | 30 | 0 | 100 | Cosmic horror | Base interest of an Outer Being |
| outer_being_interest_die | dis_ilgi_zar | 40 | 1 | 100 | Cosmic horror | Die added to an Outer Being's interest |
| outer_being_influence_base | dis_etki | 50 | 0 | 100 | Cosmic horror | Base influence of an Outer Being |
| outer_being_influence_die | dis_etki_zar | 50 | 1 | 100 | Cosmic horror | Die added to an Outer Being's influence |
| outer_being_entry_leak_drop | dis_sizinti_dusus | 20 | 0 | 100 | Cosmic horror | Leak drop when an Outer Being enters |
| default_interest | ilgi_varsayilan | 40 | 0 | 100 | Cosmic horror | Interest assumed for an Outer Being with no recorded interest |
| interest_die | ilgi_zar | 11 | 1 | 100 | Cosmic horror | Per-epoch interest die of an Outer Being |
| interest_decay | ilgi_dusus | 4 | 0 | 100 | Cosmic horror | Subtracted from an Outer Being's interest each epoch |
| outer_being_victims | dis_kurban | 3 | 0 | 100 | Cosmic horror | Neighbours whose sanity an Outer Being gnaws each epoch |
| outer_being_sanity_divisor | dis_sagduyu_bolen | 10 | 1 | 1000 | Cosmic horror | Neighbour's sanity loss: interest / this number |
| outer_being_mutation_divisor | dis_mutasyon_bolen | 300 | 1 | 100,000 | Cosmic horror | Mutation chance of a neighbouring species: interest / this number |
| apocalypse_event_divisor | kiyamet_olay_bolen | 6 | 1 | 1000 | Cosmic horror | Apocalypse contribution to horror event chance: (clock / threshold) / this number |
| alignment_leak | dizilim_sizinti | 8 | 0 | 100 | Cosmic horror | Leak increase of every world when the stars align |
| sky_eye_sanity_loss | goz_sagduyu | 10 | 0 | 100 | Cosmic horror | Sanity taken away by the Eye in the sky |
| silence_word_loss_pct | sessizlik_pay | 20 | 0 | 100 | Cosmic horror | Share of words forgotten in a wave of silence (%) |
| reverse_rain_souls | ters_yagmur_ruh | 4 | 0 | 100 | Cosmic horror | Maximum souls rising to the sky in reverse rain |
| void_min_regions | bosluk_bolge_esik | 5 | 1 | 1000 | Cosmic horror | Minimum regions on a world for the void to be able to swallow a region |

### COSTS

Old namespace `COSTS` · 16 rows · defined in `src/rules.js` · also read by `src/agents.js`, `src/denge.js`, `src/epoch.js`, `src/tools.js`. Creator and son action costs (essence) — static object in rules.js.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| summon_son | cagirma | 30 | 0 | 500 | God and son costs | Summon a son (Creator) |
| bless_essence | kutsa_oz | 15 | 0 | 500 | God and son costs | Blessing (essence) |
| bless_hp | kutsa_can | 15 | 0 | 500 | God and son costs | Blessing (HP) |
| bless_stat | kutsa_stat | 40 | 0 | 500 | God and son costs | Blessing (stat) |
| lightning | yildirim | 10 | 0 | 500 | God and son costs | Lightning (smite) |
| revelation | vahiy | 25 | 0 | 500 | God and son costs | Revelation |
| transform | donustur | 15 | 0 | 500 | God and son costs | Transform (son) |
| bear_child | evlat_dogur | 60 | 0 | 500 | God and son costs | Bear a child (son) |
| destroy | yok_et | 25 | 0 | 500 | God and son costs | Destroy (son) |
| influence | etkile | 6 | 0 | 500 | God and son costs | Influence (son) |
| curse | lanet | 12 | 0 | 500 | God and son costs | Curse (son) |
| dream | ruya | 10 | 0 | 500 | God and son costs | Dream (son) |
| incite_war | kiskirt | 10 | 0 | 500 | God and son costs | Incite war (son) |
| declare_chosen | secilmis | 14 | 0 | 500 | God and son costs | Declare a chosen one (son) |
| covenant | ahit | 0 | 0 | 500 | God and son costs | Covenant |
| anchor | capa | 0 | 0 | 500 | God and son costs | Anchor |

### COUNCIL

Old namespace `KONSEY` · 34 rows · defined in `src/konsey.js`. Council of sons, god-son chat, dream and translation limits.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| max_members | uye | 9 | 2 | 30 | Council | Maximum sons joining the council |
| min_members | en_az | 2 | 2 | 30 | Council | Minimum sons required for the council to convene |
| same_vote_closeness | oy_yakinlik | 3 | 0 | 50 | Council | Rapprochement between those casting the same vote |
| covenant_relation | ahit | 12 | 0 | 100 | Council | Relation contribution of a council covenant |
| rupture_relation | kopus | 15 | 0 | 100 | Council | Relation cost of a rupture in the council |
| apocalypse_motion_push | kiyamet_geri | 10 | 0 | 100 | Council | Clock push-back of an accepted motion against the apocalypse |
| blessing_existence | kutsama | 5 | 0 | 100 | Council | Contribution of a joint blessing to existence |
| censure_renown_cost | kinama_un | 10 | 0 | 200 | Council | Renown cost of censuring a rebel |
| agenda_apocalypse_pct | gundem_kiyamet | 50 | 0 | 100 | Council | Apocalypse comes onto the agenda at this percentage of the threshold |
| timeout | sure | 240 | 30 | 3600 | Agents and model | Council timeout (s) |
| relation_min_magnitude | iliski_esik | 20 | 0 | 100 | Council | Minimum magnitude (±) of sibling relations written into the council prompt |
| alliance_rupture_cap | ittifak_tavan | 3 | 0 | 20 | Council | Maximum alliances or ruptures in one council |
| default_interval | siklik_varsayilan | 4 | 0 | 100 | Council | On a world with no set council frequency, a council convenes once every this many epochs |
| agenda_thread_max_chars | gundem_metin | 260 | 20 | 5000 | Context budgets | Maximum length of an open story taken onto the agenda (characters) |
| agenda_cut_chars | gundem_kes | 250 | 10 | 5000 | Context budgets | A long story is cut at the last space before this character |
| persona_temperament_chars | persona_mizac | 160 | 0 | 5000 | Context budgets | Council and chat: son's temperament (characters) |
| persona_style_chars | persona_uslup | 120 | 0 | 5000 | Context budgets | Council and chat: son's style (characters) |
| persona_obsession_chars | persona_takinti | 100 | 0 | 5000 | Context budgets | Council and chat: son's obsession (characters) |
| persona_plan_chars | persona_plan | 160 | 0 | 5000 | Context budgets | Council and chat: son's plan (characters) |
| chat_appearance_chars | sohbet_gorunus | 200 | 0 | 5000 | Context budgets | Chat: son's appearance (characters) |
| chat_fear_secret_chars | sohbet_sir | 120 | 0 | 5000 | Context budgets | Chat: son's fear and secret (characters, each) |
| chat_memory_chars | sohbet_hafiza | 3500 | 200 | 100,000 | Context budgets | Chat: son's memory (characters) |
| chat_history_messages | sohbet_gecmis | 10 | 0 | 200 | Context budgets | Chat: number of previous messages in the prompt |
| chat_list_messages | sohbet_liste | 40 | 1 | 1000 | Interface | Messages shown in chat history |
| chat_max_chars | sohbet_metin | 800 | 10 | 20,000 | Council | Longest word the god can say to his son (characters) |
| chat_loyalty_max_change | sohbet_sadakat | 6 | 0 | 100 | Council | Maximum amount a chat changes the son's loyalty (±) |
| chat_timeout | sohbet_sure | 120 | 10 | 3600 | Agents and model | Chat timeout (s) |
| dream_max_chars | ruya_metin | 600 | 10 | 20,000 | Council | Longest text of a dream sent to a mortal (characters) |
| dream_min_chars | ruya_en_az | 5 | 1 | 1000 | Council | Shortest text of a dream (characters) |
| translate_max_chars | ceviri_metin | 300 | 10 | 20,000 | Language and names | Longest sentence to be translated (characters) |
| translate_lexicon_words | ceviri_sozluk | 250 | 0 | 10,000 | Language and names | Lexicon words sent to the translation prompt |
| translate_syllables | ceviri_hece | 12 | 0 | 200 | Language and names | Frequent initial and final syllables sent to the translation prompt (each) |
| translate_new_words_max | ceviri_yeni | 6 | 0 | 100 | Language and names | Maximum new words that can be added to the lexicon in one translation |
| translate_timeout | ceviri_sure | 120 | 10 | 3600 | Agents and model | Translation timeout (s) |

### CREATION_BASE_COST

Old namespace `YARATIM_TABANI` · 25 rows · defined in `src/rules.js`. Base creation cost per entity type.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| region | bolge | 20 | 0 | 500 | God and son costs | Base cost of creating a region |
| place | yer | 6 | 0 | 500 | God and son costs | Base cost of creating a place |
| resource | kaynak | 7 | 0 | 500 | God and son costs | Base cost of creating a resource |
| settlement | yerlesim | 6 | 0 | 500 | God and son costs | Base cost of founding a settlement |
| species | tur | 5 | 0 | 500 | God and son costs | Base cost of creating a species |
| people | halk | 9 | 0 | 500 | God and son costs | Base cost of creating a people |
| mortal | olumlu | 5 | 0 | 500 | God and son costs | Base cost of creating a mortal |
| item | esya | 10 | 0 | 500 | God and son costs | Base cost of forging an item |
| structure | yapit | 9 | 0 | 500 | God and son costs | Base cost of building a structure |
| language | dil | 8 | 0 | 500 | God and son costs | Base cost of creating a language |
| legend | efsane | 4 | 0 | 500 | God and son costs | Base cost of telling a legend |
| tradition | gelenek | 5 | 0 | 500 | God and son costs | Base cost of founding a tradition |
| cult | tarikat | 9 | 0 | 500 | God and son costs | Base cost of founding a cult |
| faction | hizip | 9 | 0 | 500 | God and son costs | Base cost of founding a faction |
| celestial | gok | 14 | 0 | 500 | God and son costs | Base cost of hanging a celestial body |
| artwork | eser | 5 | 0 | 500 | God and son costs | Base cost of creating an artwork |
| law | kanun | 7 | 0 | 500 | God and son costs | Base cost of decreeing a law |
| spirit | ruh | 8 | 0 | 500 | God and son costs | Base cost of summoning a spirit |
| knowledge | teknoloji | 12 | 0 | 500 | God and son costs | Base cost of inspiring knowledge |
| prophecy | kehanet | 10 | 0 | 500 | God and son costs | Base cost of uttering a prophecy |
| event | olay | 18 | 0 | 500 | God and son costs | Base cost of starting an event |
| vessel | arac | 14 | 0 | 500 | God and son costs | Base cost of creating a vessel |
| outer_being | dis | 0 | 0 | 500 | God and son costs | Base cost of an Outer Being |
| army | ordu | 0 | 0 | 500 | God and son costs | Base cost of an army |
| natural_law | yasa | 30 | 0 | 500 | God and son costs | Base cost of decreeing a natural law |

### CREATOR

Old namespace `YARATICI` · 64 rows · defined in `src/yaratici.js` · also read by `src/world.js`. The Creator's mood (wrath/contentment/attention/loneliness), cult and signs.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| cult_faith_per_essence | kult_oz_bolen | 4 | 1 | 100 | Creator and essence | Every this much cult faith gives the god 1 essence |
| cult_faith_per_apocalypse_push | kult_kiyamet_bolen | 25 | 1 | 1000 | Apocalypse | Every this much cult faith pushes the apocalypse back by 1 |
| cult_apocalypse_push_cap | kult_kiyamet_tavan | 5 | 0 | 100 | Apocalypse | Maximum apocalypse push-back by the cult in one epoch |
| wrath_threshold | ofke_esik | 70 | 0 | 100 | Creator and essence | Threshold at which the Creator's wrath overflows |
| content_threshold | hosnut_esik | 70 | 0 | 100 | Creator and essence | Contentment at which the Creator sends down grace |
| wrath_sign_chance | ofke_isaret_sans | 60 | 0 | 100 | Creator and essence | The wrathful Creator's punishment descends (%) |
| content_sign_chance | hosnut_isaret_sans | 60 | 0 | 100 | Creator and essence | The content Creator's grace descends (%) |
| silence_sign_chance | sessizlik_isaret_sans | 50 | 0 | 100 | Creator and essence | The indifferent Creator falls silent (sign %) |
| loneliness_sign_chance | yalnizlik_isaret_sans | 50 | 0 | 100 | Creator and essence | The lonely Creator sends a dream (%) |
| start_contentment | ruh_hosnutluk | 50 | 0 | 100 | Creator and essence | Creator's starting contentment |
| start_wrath | ruh_ofke | 20 | 0 | 100 | Creator and essence | Creator's starting wrath |
| start_attention | ruh_ilgi | 60 | 0 | 100 | Creator and essence | Creator's starting attention |
| start_loneliness | ruh_yalnizlik | 30 | 0 | 100 | Creator and essence | Creator's starting loneliness |
| label_wrathful | etiket_ofkeli | 70 | 0 | 100 | Creator and essence | Wrath at which the mood counts as "wrathful" |
| label_silent | etiket_sessiz | 20 | 0 | 100 | Creator and essence | Attention at which the mood counts as "distant and silent" (at most) |
| label_lonely | etiket_yalniz | 70 | 0 | 100 | Creator and essence | Loneliness at which the mood counts as "lonely" |
| label_content | etiket_hosnut | 70 | 0 | 100 | Creator and essence | Contentment at which the mood counts as "content" |
| label_restless | etiket_huzursuz | 45 | 0 | 100 | Creator and essence | Wrath at which the mood counts as "restless" |
| cult_population_per_faith | kult_inanc_nufus | 2000 | 1 | 10,000,000 | Creator and essence | Worshipping population giving 1 faith in the cult (at full piety) |
| cult_default_piety | kult_inanc_varsayilan | 60 | 0 | 100 | Creator and essence | Piety assumed for a cult worshipper with unknown piety |
| cult_followers_per_faith | kult_inanc_murit | 50 | 1 | 10,000,000 | Creator and essence | Followers giving 1 faith in the cult |
| cult_faith_per_mortal | kult_inanc_olumlu | 2 | 0 | 100 | Creator and essence | Faith of each mortal who worships the Creator |
| wrath_keep_pct | ofke_kalici | 85 | 0 | 100 | Creator and essence | Share of wrath kept from epoch to epoch (%) |
| wrath_godless_max | ofke_tanrisiz | 4 | 0 | 100 | Creator and essence | Maximum contribution of godless communities to wrath (per epoch; saturates toward this cap as the godless share grows) |
| wrath_godless_half_pct | ofke_tanrisiz_yari | 10 | 1 | 100 | Creator and essence | When this percentage of communities are godless, the godlessness contribution is half the cap |
| wrath_rebel_max | ofke_asi | 8 | 0 | 100 | Creator and essence | Maximum contribution of rebel sons to wrath (per epoch; saturates toward this cap as the number of rebels grows) |
| wrath_rebel_half | ofke_asi_yari | 1 | 1 | 100 | Creator and essence | With this many rebel sons the rebellion contribution is half the cap |
| wrath_war_max | ofke_savas | 6 | 0 | 100 | Creator and essence | Maximum contribution of ongoing community wars to wrath (per epoch; saturates toward this cap as war grows) |
| wrath_war_half_pct | ofke_savas_yari | 100 | 1 | 10,000 | Creator and essence | When ongoing wars are at this percentage of the world's war cap, the war contribution is half the cap |
| wrath_apocalypse_divisor | ofke_kiyamet_bolen | 12 | 1 | 1000 | Creator and essence | Doomsday clock contribution to wrath: clock (% of threshold) / this number |
| content_keep_pct | hosnut_kalici | 85 | 0 | 100 | Creator and essence | Share of contentment kept from epoch to epoch (%) |
| content_cult_max | hosnut_kult | 8 | 0 | 100 | Creator and essence | Maximum contribution of the cult to contentment (per epoch; saturates toward this cap as the cult grows) |
| content_cult_half | hosnut_kult_yari | 10 | 1 | 10,000 | Creator and essence | With this many cult worshippers the cult contribution is half the cap |
| content_new_life_max | hosnut_canli_tavan | 5 | 0 | 100 | Creator and essence | Maximum contribution of new living beings to contentment (per epoch; saturates toward this cap as births grow) |
| content_new_life_half | hosnut_canli_yari | 25 | 1 | 10,000 | Creator and essence | When this many new living beings are born in an epoch the life contribution is half the cap |
| content_action | hosnut_eylem | 4 | 0 | 100 | Creator and essence | Contribution to contentment of an epoch in which the god acted |
| mood_opposition_pct | ruh_zitlik | 5 | 0 | 100 | Creator and essence | Wrath and contentment soothe each other: each decreases every epoch by this percentage of the other |
| attention_keep_pct | ilgi_kalici | 80 | 0 | 100 | Creator and essence | Share of attention kept from epoch to epoch (%) |
| attention_per_action | ilgi_eylem | 6 | 0 | 100 | Creator and essence | Contribution of each of the god's actions to attention |
| attention_action_cap | ilgi_tavan | 30 | 0 | 100 | Creator and essence | Maximum contribution of actions to attention in one epoch |
| loneliness_keep_pct | yalniz_kalici | 85 | 0 | 100 | Creator and essence | Share of loneliness kept from epoch to epoch (%) |
| loneliness_son_threshold | yalniz_ogul_esik | 3 | 0 | 100 | Creator and essence | If there are fewer active sons than this, the Creator grows lonely |
| loneliness_few_sons | yalniz_ogul | 8 | 0 | 100 | Creator and essence | Loneliness contribution per epoch of having few sons |
| loneliness_cult_relief | yalniz_kult | 4 | 0 | 100 | Creator and essence | Per-epoch decrease of loneliness for a Creator who has a cult |
| loneliness_no_cult | yalniz_kultsuz | 6 | 0 | 100 | Creator and essence | Per-epoch loneliness increase for a Creator without a cult |
| loneliness_unanswered_cap | yalniz_cevapsiz_tavan | 10 | 0 | 100 | Creator and essence | Maximum contribution of unanswered prayers to loneliness (1 per prayer) |
| wrath_disaster_severity | ofke_afet_siddet | 80 | 0 | 300 | Creator and essence | Disaster severity of a wrath punishment (%) |
| wrath_event_severity_base | ofke_olay_siddet | 60 | 0 | 100 | Creator and essence | Base severity of a wrath-punishment event |
| wrath_event_severity_die | ofke_olay_siddet_zar | 30 | 1 | 100 | Creator and essence | Severity die of a wrath-punishment event |
| wrath_discharge | ofke_bosalma | 25 | 0 | 100 | Creator and essence | Drop in wrath after a punishment descends |
| indifferent_threshold | ilgisiz_esik | 20 | 0 | 100 | Creator and essence | Below this attention the Creator falls silent |
| indifferent_loyalty_loss | ilgisiz_sadakat | 4 | 0 | 100 | Creator and essence | Loyalty loss of the silent Creator's sons |
| indifferent_ambition_gain | ilgisiz_hirs | 3 | 0 | 100 | Creator and essence | Ambition gain of the silent Creator's sons |
| lonely_threshold | yalniz_esik | 70 | 0 | 100 | Creator and essence | Loneliness at which the Creator sends a dream |
| lonely_discharge | yalniz_bosalma | 20 | 0 | 100 | Creator and essence | Drop in loneliness after sending a dream |
| estranged_turn_chance | kus_sans | 8 | 0 | 100 | Creator and essence | A community estranged from its sons turns to the Creator (%) |
| estranged_content_threshold | kus_hosnut_esik | 60 | 0 | 100 | Creator and essence | Creator contentment that attracts the estranged more strongly |
| estranged_content_bonus_pct | kus_hosnut_ek | 7 | 0 | 100 | Creator and essence | Contribution of a content Creator to attracting the estranged (%) |
| prayer_faith_gain | dua_inanc | 10 | 0 | 100 | Creator and essence | Faith gain of a mortal whose prayer is answered |
| prayer_essence_per_stat | dua_oz_bolen | 3 | 1 | 100 | Creator and essence | Every this much essence given to a prayer adds 1 to stats |
| prayer_loneliness_relief | dua_yalnizlik | 10 | 0 | 100 | Creator and essence | Loneliness reduction from answering a prayer |
| prayer_contentment | dua_hosnutluk | 3 | 0 | 100 | Creator and essence | Contribution of answering a prayer to contentment |
| sign_candidates | isaret_aday | 4 | 1 | 100 | Creator and essence | The target of a spontaneous sign is picked by dice from this many best candidates |
| sign_exclusion_epochs | isaret_dislama_cag | 3 | 0 | 100 | Creator and essence | A place struck by a spontaneous sign is not picked again for this many epochs (can still be picked if no candidate remains) |

### CREATURES

Old namespace `YARATIK` · 66 rows · defined in `src/yaratik.js` · also read by `src/olumluler.js`. Creature traits, chimeras, mutation, predation, taming.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| soul_eater_chance | ruh_yiyen_sans | 30 | 0 | 100 | Creatures | A soul-eating species devours a spirit (%) |
| fission_chance | bolunme_sans | 10 | 0 | 100 | Creatures | A species multiplying by splitting grows stronger (%) |
| people_mutation_chance | halk_mutasyon_sans | 15 | 0 | 100 | Creatures | A changed branch splits from a people with falling sanity (%) |
| hybrid_chance | melez_sans | 3 | 0 | 100 | Creatures | Species on the same land hybridize (%) |
| megafauna_trace_chance | megafauna_iz_sans | 12 | 0 | 100 | Creatures | A resource forms in a megafauna's trace (%) |
| predation_link_chance | av_bag_sans | 25 | 0 | 100 | Creatures | A predator–prey relation is formed (%) |
| prey_depletion_chance | av_tukenme_sans | 4 | 0 | 100 | Creatures | A strong predator exhausts its prey (%) |
| stowaway_chance | kacak_sans | 30 | 0 | 100 | Creatures | A stowaway species is carried by ship (%) |
| traits_from_description_cap | ozellik_tavan | 2 | 1 | 10 | Creatures | Maximum traits given to a species from its description |
| hive_mind_intelligence | suru_zeka | 15 | 0 | 100 | Creatures | Intelligence gain of a swarm-minded species |
| chimera_default_stat | kimera_stat_varsayilan | 40 | 0 | 100 | Creatures | Default value of an unrecorded stat in a chimera |
| chimera_die | kimera_zar | 21 | 1 | 100 | Creatures | Die of chimera stats (1…n) |
| chimera_shift | kimera_kayma | 6 | 0 | 100 | Creatures | Subtracted from the chimera stat die |
| chimera_hp_cap | kimera_can_tavan | 1000 | 1 | 100,000 | Creatures | Maximum HP of a chimera |
| chimera_trait_cap | kimera_ozellik_tavan | 3 | 0 | 10 | Creatures | Maximum traits a chimera can carry |
| chimera_danger_bonus | kimera_tehlike | 10 | 0 | 100 | Creatures | Extra danger of a chimera |
| chimera_weave_chance | kimera_dokuma_sans | 6 | 0 | 100 | Creatures | A community or mortal knowing biomancy weaves a chimera on its own (% per epoch) |
| chimera_weave_distance | kimera_dokuma_mesafe | 4 | 0 | 99 | Creatures | Farthest distance of the spontaneous chimera weaver to the species (steps) |
| radiant_danger_drop | isik_tehlike | 2 | 0 | 100 | Creatures | Light-radiating species lowers region danger (per epoch) |
| radiant_fertility_gain | isik_bereket | 2 | 0 | 100 | Creatures | Light-radiating species raises region fertility (per epoch) |
| mind_reader_victims | akil_okuyan_tavan | 3 | 0 | 100 | Creatures | Maximum neighbours whose sanity a mind-reading or soul-eating species gnaws |
| mind_reader_sanity_loss | akil_okuyan_sagduyu | 3 | 0 | 100 | Creatures | Sanity loss to neighbours from a mind-reading or soul-eating species |
| fission_danger_gain | bolunme_tehlike | 5 | 0 | 100 | Creatures | Danger gain of a species multiplying by splitting |
| mutation_cap | mutasyon_tavan | 1 | 0 | 100 | Creatures | Maximum species mutations per epoch |
| mutation_leak_divisor | mutasyon_sizinti_bolen | 400 | 1 | 100,000 | Creatures | Mutation chance: world leak / this number |
| mutation_tagged_bonus_pct | mutasyon_etiket | 25 | 0 | 100 | Creatures | Extra mutation chance of a species tagged as mutated (%) |
| mutation_cursed_bonus_pct | mutasyon_lanet | 8 | 0 | 100 | Creatures | Extra mutation chance of a cursed species (%) |
| mutation_might_bonus_pct | mutasyon_kudret | 2 | 0 | 100 | Creatures | Extra mutation chance of a species with might (%) |
| mutation_die | mutasyon_zar | 41 | 1 | 100 | Creatures | Change die of mutant stats (1…n) |
| mutation_shift | mutasyon_kayma | 15 | 0 | 100 | Creatures | Subtracted from the mutant stat die |
| mutation_leak_text_threshold | mutasyon_sizinti_metin | 40 | 0 | 100 | Creatures | World leak at which the mutation is attributed to the leak (in text) |
| people_mutation_sanity | halk_mutasyon_sagduyu | 30 | 0 | 100 | Creatures | A changed branch may split from a people below this sanity |
| people_mutation_share_pct | halk_mutasyon_pay | 20 | 0 | 100 | Creatures | Population share passing to the changed branch (%) |
| changed_martiality_gain | degismis_savascilik | 15 | 0 | 100 | Creatures | Martiality gain of a changed people |
| changed_magic_gain | degismis_buyu | 20 | 0 | 100 | Creatures | Magic gain of a changed people |
| changed_craft | degismis_zanaat | 20 | 0 | 100 | Creatures | Craft of a changed people |
| changed_piety | degismis_inanc | 10 | 0 | 100 | Creatures | Piety of a changed people |
| changed_sanity | degismis_sagduyu | 40 | 0 | 100 | Creatures | Sanity of a changed people |
| people_default_martiality | halk_savascilik_varsayilan | 40 | 0 | 100 | Creatures | Default martiality of a people with no recorded martiality |
| people_default_magic | halk_buyu_varsayilan | 20 | 0 | 100 | Creatures | Default magic of a people with no recorded magic |
| people_default_population | halk_nufus_varsayilan | 1000 | 1 | 100,000,000 | Creatures | Population assumed when a changed branch splits from a people with no recorded population |
| chimera_default_danger | kimera_tehlike_varsayilan | 50 | 0 | 100 | Creatures | Danger assumed in the escape chance for a chimera with no recorded danger |
| chimera_escape_divisor | kimera_kacis_bolen | 500 | 1 | 100,000 | Creatures | Chimera escape chance: danger / this number |
| chimera_escape_population_loss_pct | kimera_kacis_kayip | 10 | 0 | 100 | Creatures | Population loss to the weavers of an escaped chimera (%) |
| megafauna_min_power | megafauna_seviye | 8 | 1 | 12 | Creatures | Minimum power level of a species counted as megafauna |
| trace_power | iz_seviye | 5 | 1 | 12 | Creatures | Power level of a megafauna-trace resource |
| trace_abundance | iz_bolluk | 60 | 0 | 100 | Creatures | Abundance of a megafauna-trace resource |
| trace_value_base | iz_deger_taban | 70 | 0 | 100 | Creatures | Base value of a megafauna trace |
| trace_value_die | iz_deger_zar | 30 | 1 | 100 | Creatures | Value die of a megafauna trace (1…n) |
| trace_might_base | iz_kudret_taban | 60 | 0 | 100 | Creatures | Base might of a megafauna trace |
| trace_might_die | iz_kudret_zar | 40 | 1 | 100 | Creatures | Might die of a megafauna trace (1…n) |
| predation_link_cap | av_bag_tavan | 1 | 0 | 100 | Creatures | Maximum new predator–prey links per epoch |
| predation_danger_margin | av_tehlike_fark | 10 | 0 | 100 | Creatures | Minimum danger advantage of a predator over its prey |
| depletion_danger_margin | av_tukenme_fark | 30 | 0 | 100 | Creatures | Minimum danger advantage of a predator able to exhaust its prey |
| depletion_max_prey_power | av_tukenme_seviye | 4 | 0 | 12 | Creatures | Highest power level of prey that can be exhausted |
| danger_reversion_threshold | tehlike_donus_esik | 55 | 0 | 100 | Creatures | A species with danger above this reverts toward the mean |
| danger_reversion_mean | tehlike_donus_orta | 50 | 0 | 100 | Creatures | Mean to which species danger reverts |
| danger_reversion_divisor | tehlike_donus_bolen | 12 | 1 | 1000 | Creatures | Danger reversion: (danger − mean) / this number |
| starving_predator_danger | yirtici_ac_tehlike | 15 | 0 | 100 | Creatures | Danger gain of a predator whose prey is exhausted |
| species_default_danger | tur_tehlike_varsayilan | 40 | 0 | 100 | Creatures | Default danger of a species with no recorded danger |
| invasive_fertility_loss | istilaci_bereket | 3 | 0 | 100 | Creatures | Invasive species lowers the fertility of where it lives (per epoch) |
| tamed_war_base | evcil_taban | 6 | 0 | 100 | Creatures | Base contribution of each tamed creature to war strength |
| tamed_strength_divisor | evcil_guc_bolen | 15 | 1 | 1000 | Creatures | Tamed creature contribution: strength / this number |
| tamed_default_strength | evcil_guc_varsayilan | 30 | 0 | 100 | Creatures | Default strength of a tamed creature with no recorded strength |
| tamed_trait_share_pct | evcil_ozellik_pay | 50 | 0 | 100 | Creatures | Share of a tamed creature's trait war bonus transferred (%) |
| stowaway_danger_cap | kacak_tehlike_tavan | 70 | 0 | 100 | Creatures | Danger limit of a species that can stow away on a ship (below) |

### CREATURE_TRAITS

Old namespace `OZELLIKLER` · 10 rows · defined in `src/rules.js` · also read by `src/denge.js`, `src/oyuncu.js`, `src/tools.js`, `src/yaratik.js`. War bonus per creature trait — static object in rules.js.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| flying_war_bonus | ucan.savas | 8 | 0 | 100 | Creatures | War-strength bonus of a Flying creature |
| venomous_war_bonus | zehirli.savas | 10 | 0 | 100 | Creatures | War-strength bonus of a Venomous creature |
| soul_eater_war_bonus | ruh_yiyen.savas | 4 | 0 | 100 | Creatures | War-strength bonus of a Soul-eating creature |
| radiant_war_bonus | isik_sacan.savas | 0 | 0 | 100 | Creatures | War-strength bonus of a Light-radiating creature |
| fissiparous_war_bonus | bolunerek.savas | 2 | 0 | 100 | Creatures | War-strength bonus of a creature that multiplies by splitting |
| hive_mind_war_bonus | suru_zekasi.savas | 6 | 0 | 100 | Creatures | War-strength bonus of a Swarm-minded creature |
| stoneskin_war_bonus | tas_derili.savas | 12 | 0 | 100 | Creatures | War-strength bonus of a Stone-skinned creature |
| time_rewinder_war_bonus | zaman_geri.savas | 0 | 0 | 100 | Creatures | War-strength bonus of a Time-rewinding creature |
| shapeshifter_war_bonus | sekil_degistiren.savas | 3 | 0 | 100 | Creatures | War-strength bonus of a Shapeshifting creature |
| mind_reader_war_bonus | akil_okuyan.savas | 8 | 0 | 100 | Creatures | War-strength bonus of a Mind-reading creature |

### DEATH

Old namespace `OLUM` · 53 rows · defined in `src/olum.js` · also read by `src/epoch.js`, `src/firsatlar.js`, `src/olumluler.js`, `src/tools.js`. Taking lives, killing sons, resurrection rites and intrigues.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| take_life_base_cost | can_al_taban | 25 | 0 | 10,000 | Death and resurrection | Base cost (essence) of a son taking a mortal's life |
| take_life_cost_per_power | can_al_guc | 6 | 0 | 1000 | Death and resurrection | Essence added to the take-life cost per power level of the victim |
| take_life_cost_importance_divisor | can_al_onem_bolen | 2 | 1 | 1000 | Death and resurrection | Victim's importance score / this number is added to the take-life cost as essence |
| take_life_notable_surcharge | can_al_onemli | 20 | 0 | 10,000 | Death and resurrection | Surcharge (essence) for an important mortal (ruler, hero, chosen one, titled) |
| take_life_per_epoch | can_al_tur | 1 | 0 | 20 | Death and resurrection | Maximum take-life attempts by a son in one epoch (0 disables the tool) |
| take_life_base_success | can_al_basari | 65 | 0 | 100 | Death and resurrection | Base success chance of taking a life (%) |
| take_life_might_divisor | can_al_kudret_bolen | 5 | 1 | 1000 | Death and resurrection | The son's might / this number is added to success |
| take_life_importance_resist | can_al_onem_direnc | 4 | 1 | 1000 | Death and resurrection | Victim's importance score / this number is subtracted from success |
| take_life_patron_resist | can_al_hami_direnc | 25 | 0 | 100 | Death and resurrection | Subtracted from success if another son protects the victim (its patron) (%) |
| take_life_creator_resist | can_al_yaratici_direnc | 35 | 0 | 100 | Death and resurrection | Subtracted from success if the victim worships the Creator directly (%) |
| take_life_protected_resist | can_al_korunmus | 40 | 0 | 100 | Death and resurrection | Subtracted from success if the victim is protected or chosen (%) |
| take_life_item_protection | can_al_esya_koruma | 50 | 0 | 100 | Death and resurrection | If an item owned by the victim has protection at or above this it can draw death's breath upon itself (mentioned in the story) |
| take_life_min_chance | can_al_en_az | 5 | 0 | 100 | Death and resurrection | Minimum success chance of taking a life (%) |
| take_life_max_chance | can_al_en_cok | 95 | 0 | 100 | Death and resurrection | Maximum success chance of taking a life (%) |
| take_life_refund_pct | can_al_iade | 0 | 0 | 100 | Death and resurrection | Share of essence returned on a failed take-life (%) |
| take_life_relation_loss | can_al_iliski | 15 | 0 | 100 | Death and resurrection | Relation loss of the life-taking son with the victim's patron and creator |
| survivor_charisma_gain | can_al_karizma | 10 | 0 | 100 | Death and resurrection | Charisma gain of a mortal who returns from death |
| survivor_legend_power | can_al_efsane_guc | 3 | 1 | 12 | Death and resurrection | Power level of the legend of the return from death |
| foreign_god_smite_chance | yabanci_carpma_sans | 4 | 0 | 100 | Death and resurrection | An awake foreign god strikes a named mortal on its own world who does not worship it (% per epoch) |
| creator_take_life_cost | tanri_can_al | 15 | 0 | 10,000 | Death and resurrection | Cost for Aeron (the Creator) to take a mortal's life (divine essence) |
| creator_kill_son_cost | tanri_ogul_oldur | 100 | 0 | 100,000 | Death and resurrection | Cost for Aeron to kill a son (divine essence) |
| kill_son_loyalty_gain | ogul_oldur_sadakat | 10 | 0 | 100 | Death and resurrection | Loyalty the other sons gain out of fear when Aeron kills a son |
| kill_son_friend_wrath | ogul_oldur_ofke | 15 | 0 | 100 | Death and resurrection | Wrath of the dead son's friendly siblings when Aeron kills a son |
| resurrection_min_epochs | dirilis_en_az_cag | 3 | 0 | 1000 | Death and resurrection | A dead son can resurrect on his own at the earliest after this many epochs (except by Aeron's hand) |
| rite_chance | ayin_sans | 20 | 0 | 100 | Death and resurrection | A community loyal to its dead god holds a resurrection rite on its own (% per epoch) |
| rite_devotion | ayin_adanmislik | 6 | 0 | 1000 | Death and resurrection | Contribution of a spontaneous rite (devotion) |
| rite_prosperity_cost | ayin_refah | 5 | 0 | 100 | Death and resurrection | Cost of the rite to the community (prosperity or wealth) |
| pilgrimage_multiplier_pct | hac_carpan | 200 | 100 | 1000 | Death and resurrection | Contribution multiplier if the rite is held in the region where the god's bones lie (%) |
| sacrifice_chance | kurban_sans | 5 | 0 | 100 | Death and resurrection | A loyal community makes a blood sacrifice on its own (% per epoch) |
| sacrifice_population_pct | kurban_nufus | 3 | 0 | 100 | Death and resurrection | Population lost in a blood sacrifice (%) |
| sacrifice_devotion | kurban_adanmislik | 20 | 0 | 1000 | Death and resurrection | Contribution of a blood sacrifice (devotion) |
| self_sacrifice_devotion | can_kurbani_adanmislik | 35 | 0 | 1000 | Death and resurrection | Contribution of a named mortal sacrificing themself (or their people sacrificing them) (devotion) |
| offering_devotion | servet_adanmislik | 10 | 0 | 1000 | Death and resurrection | Contribution of offering wealth and votive gifts (devotion) |
| offering_cost | servet_bedel | 15 | 0 | 100 | Death and resurrection | Cost of a wealth offering (prosperity or wealth) |
| prayer_devotion | dua_adanmislik | 4 | 0 | 1000 | Death and resurrection | Contribution of prayer (devotion) |
| rite_per_epoch | ayin_tur | 1 | 0 | 20 | Death and resurrection | resurrection_rite (dirilis_ayini): maximum rites by one mortal per epoch (0 disables the tool) |
| sibling_rite_cost | kardes_ayin_bedel | 45 | 0 | 10,000 | Death and resurrection | Sibling's resurrection rite: cost (essence) |
| sibling_rite_devotion | kardes_ayin_adanmislik | 25 | 0 | 1000 | Death and resurrection | Sibling's resurrection rite: contribution (devotion) |
| sibling_descent_cost | kardes_inis_bedel | 70 | 0 | 10,000 | Death and resurrection | Descent into the realm of the dead: cost (essence) |
| sibling_descent_devotion | kardes_inis_adanmislik | 50 | 0 | 1000 | Death and resurrection | Descent into the realm of the dead: contribution (devotion) |
| sibling_descent_success | kardes_inis_basari | 60 | 0 | 100 | Death and resurrection | Success chance of the descent into the realm of the dead (%); on failure the descender falls asleep |
| sibling_descent_sleep_epochs | kardes_inis_uyku | 2 | 1 | 100 | Death and resurrection | Sleep duration of a sibling who loses their way in the realm of the dead (epochs) |
| sibling_bargain_cost | kardes_pazarlik_bedel | 25 | 0 | 10,000 | Death and resurrection | Bargain with a foreign god: cost (essence); additionally one of the dead god's loyal communities converts to the foreign god |
| sibling_bargain_devotion | kardes_pazarlik_adanmislik | 40 | 0 | 1000 | Death and resurrection | Bargain with a foreign god: contribution (devotion) |
| sibling_intrigues_per_epoch | kardes_tur | 1 | 0 | 20 | Death and resurrection | Maximum resurrection intrigues or bone scatterings by one son in one epoch (0 disables the tools) |
| auto_intrigue_min_relation | kardes_oto_iliski | 40 | -100 | 100 | Death and resurrection | Minimum relation with the sibling for a spontaneous resurrection intrigue |
| auto_intrigue_chance | kardes_oto_sans | 25 | 0 | 100 | Death and resurrection | A sufficiently close sibling with enough essence enters an intrigue on their own (% per epoch) |
| auto_intrigue_essence_share | kardes_oto_oz_pay | 60 | 0 | 100 | Death and resurrection | In a spontaneous intrigue the sibling spends at most this share of their essence (%) |
| scatter_bones_cost | dagit_bedel | 30 | 0 | 10,000 | Death and resurrection | Cost of scattering the bones (essence) |
| scatter_bones_devotion_loss | dagit_adanmislik | 35 | 0 | 1000 | Death and resurrection | Devotion reduced by scattering the bones |
| auto_scatter_relation | dagit_oto_iliski | 40 | 0 | 100 | Death and resurrection | Relation with the dead for spontaneous bone scattering: below minus this |
| auto_scatter_chance | dagit_oto_sans | 15 | 0 | 100 | Death and resurrection | A hostile sibling scatters the bones on their own (% per epoch) |
| new_cult_followers | yeni_tarikat_murit | 80 | 1 | 1,000,000 | Death and resurrection | Followers of the new resurrection cult born when a rite is held for a dead god with no remaining cult |

### DEEP_LIFE

Old namespace `DERIN_YASAM` · 348 rows · defined in `src/derin.js` · also read by `src/bosdunya.js`, `src/firsatlar.js`, `src/mudahale.js`, `src/olum.js`, `src/oyuncu.js`, `src/tools.js`. Heroes, quests, knowledge spread, spies, wonders, climate, god death/resurrection, births, writing, legends, native life, refugees, structures, factions, culture.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| hero_strength_agility_sum | kahraman_guc | 90 | 0 | 200 | Heroes and mortals | Strength + agility total for a mortal to count as a hero |
| quest_resolution_cap | gorev_sonuc_tavan | 4 | 0 | 50 | Heroes and mortals | Maximum hero quests resolved per epoch |
| quest_new_cap | gorev_tavan | 3 | 0 | 50 | Heroes and mortals | Maximum new hero quests per epoch |
| companion_new_cap | yoldas_tavan | 1 | 0 | 20 | Heroes and mortals | Maximum new companionships per epoch |
| apprentice_new_cap | cirak_tavan | 1 | 0 | 20 | Heroes and mortals | Maximum new apprentices per epoch |
| apprentice_min_life_pct | cirak_yas_pay | 60 | 0 | 100 | Heroes and mortals | At least this share of lifespan must have been lived to train an apprentice (%) |
| apprentice_min_charisma | cirak_karizma | 50 | 0 | 100 | Heroes and mortals | Minimum charisma of a hero training an apprentice |
| apprentice_stat_fallback | cirak_stat_yedek | 40 | 0 | 100 | Heroes and mortals | Apprentice stat: value used in place of the master's missing stat |
| apprentice_stat_share_pct | cirak_stat_pay | 70 | 0 | 200 | Heroes and mortals | Apprentice stat: share taken from the master's stat (%) |
| apprentice_stat_die | cirak_stat_zar | 25 | 1 | 100 | Heroes and mortals | Die added to the apprentice's stat (maximum) |
| apprentice_hp | cirak_can | 90 | 1 | 1000 | Heroes and mortals | Apprentice HP |
| apprentice_power_gap | cirak_guc_fark | 1 | 0 | 12 | Heroes and mortals | The apprentice's power level is this much lower than the master's |
| apprentice_start_age | cirak_yas | 16 | 0 | 200 | Heroes and mortals | Apprentice's starting age (years) |
| apprentice_lifespan_die | cirak_omur_zar | 21 | 1 | 500 | Heroes and mortals | Apprentice lifespan: die added to the master's lifespan (years) |
| apprentice_lifespan_shift | cirak_omur_kayma | 11 | 0 | 500 | Heroes and mortals | Apprentice lifespan: years subtracted after the die |
| master_default_lifespan | cirak_omur_yedek | 70 | 1 | 50,000 | Heroes and mortals | Lifespan assumed for a master with no lifespan record (years) |
| apprentice_min_lifespan | cirak_omur_alt | 30 | 1 | 50,000 | Heroes and mortals | Shortest lifespan of an apprentice (years) |
| lifespan_cap | omur_tavan | 50,000 | 10 | 1,000,000 | Heroes and mortals | Longest lifespan of a mortal (years) |
| hunt_quest_min_danger | gorev_av_tehlike | 50 | 0 | 100 | Heroes and mortals | Minimum species danger for a hunt quest |
| quest_max_distance | gorev_mesafe | 4 | 0 | 20 | Heroes and mortals | Maximum distance of the quest target (map steps) |
| quest_weight_hunt | gorev_av_agirlik | 3 | 0 | 100 | Heroes and mortals | Quest selection: hunt weight |
| quest_weight_thread | gorev_iplik_agirlik | 4 | 0 | 100 | Heroes and mortals | Quest selection: open story-thread weight |
| quest_weight_lost_item | gorev_emanet_agirlik | 2 | 0 | 100 | Heroes and mortals | Quest selection: lost-item weight |
| quest_strong_item_power | gorev_emanet_guclu_esik | 5 | 0 | 12 | Heroes and mortals | Power level of a lost item counted as strong |
| quest_weight_strong_item_bonus | gorev_emanet_guclu_ek | 2 | 0 | 100 | Heroes and mortals | Quest selection: extra weight of a strong lost item |
| quest_weight_lost_knowledge | gorev_bilgi_agirlik | 2 | 0 | 100 | Heroes and mortals | Quest selection: lost-knowledge weight |
| quest_weight_vengeance | gorev_oc_agirlik | 3 | 0 | 100 | Heroes and mortals | Quest selection: blood-feud vengeance weight |
| quest_success_divisor | gorev_basari_bolen | 300 | 1 | 10,000 | Heroes and mortals | Quest success: (strength + agility + intellect) / this number |
| quest_companion_bonus_pct | gorev_yoldas_ek | 10 | 0 | 100 | Heroes and mortals | Contribution of each companion to quest success (%) |
| quest_chosen_bonus_pct | gorev_secilmis_ek | 12 | 0 | 100 | Heroes and mortals | Contribution of being chosen to quest success (%) |
| quest_success_min_pct | gorev_basari_alt | 15 | 0 | 100 | Heroes and mortals | Minimum quest success chance (%) |
| quest_success_max_pct | gorev_basari_ust | 90 | 0 | 100 | Heroes and mortals | Maximum quest success chance (%) |
| quest_charisma_gain | gorev_karizma | 4 | 0 | 100 | Heroes and mortals | Charisma gain of a hero who succeeds in a quest |
| quest_god_renown | gorev_un | 3 | 0 | 100 | Heroes and mortals | Renown gain of the god of a hero who succeeds in a quest |
| quest_abandon_epochs | gorev_vazgecme_cag | 3 | 1 | 50 | Heroes and mortals | Duration after which an inconclusive quest is abandoned (epochs) |
| quest_epoch_hp_loss | gorev_yara | 20 | 0 | 1000 | Heroes and mortals | Hero's HP loss in an inconclusive quest epoch |
| dark_age_forget_cap | karanlik_unutma_tavan | 2 | 0 | 50 | Civilization | Maximum knowledge forgotten per epoch |
| dark_age_min_severity | karanlik_siddet | 70 | 0 | 100 | Civilization | Minimum severity of an event counted as ruin |
| dark_age_scribe_pct | karanlik_katip | 10 | 0 | 100 | Civilization | Scribe share that protects knowledge from being forgotten (%) |
| relic_rediscovery_cap | kalinti_bulma_tavan | 1 | 0 | 20 | Civilization | Maximum knowledge rediscovered from remnants per epoch |
| relic_min_scribe_pct | kalinti_katip | 7 | 0 | 100 | Civilization | Minimum scribe share of a community able to decipher knowledge from remnants (%) |
| knowledge_spread_base | yayginlik_taban | 8 | 0 | 100 | Civilization | Base spread of a known knowledge |
| knowledge_spread_per_knower | yayginlik_bilen | 10 | 0 | 100 | Civilization | Contribution of each knowing community to knowledge spread |
| knowledge_spread_default | yayginlik_yedek | 10 | 0 | 100 | Civilization | Spread assumed for a knowledge with no spread record |
| knowledge_spread_step | yayginlik_adim | 5 | 0 | 100 | Civilization | Maximum per-epoch change of knowledge spread |
| spy_min_sway | casus_nufuz | 50 | 0 | 100 | War and diplomacy | Minimum sway of a faction able to set up a spy network |
| spy_net_cap | casus_ag_tavan | 1 | 0 | 20 | War and diplomacy | Maximum new spy networks per epoch |
| spy_target_relation | casus_iliski | 30 | 0 | 100 | War and diplomacy | Coldness counted as a spy target (relation below minus this) |
| spy_capture_base_pct | casus_yakalanma | 12 | 0 | 100 | War and diplomacy | Base chance of spies being captured (%) |
| spy_capture_default | casus_yakalanma_yedek | 30 | 0 | 100 | War and diplomacy | Capture: value assumed if the target has no sway/defense |
| spy_capture_divisor | casus_yakalanma_bolen | 400 | 1 | 100,000 | War and diplomacy | Capture: target's sway / this number is added |
| spy_caught_relation_loss | casus_iliski_dusus | 20 | 0 | 200 | War and diplomacy | Relation damage from captured spies |
| spy_sabotage_damage | casus_sabotaj | 6 | 0 | 100 | War and diplomacy | Damage of sabotage to defense, strength and wealth |
| wonder_min_splendor | harika_ihtisam | 80 | 0 | 100 | Civilization | Minimum splendor of a structure counted as a wonder |
| wonder_min_power | harika_guc | 7 | 0 | 12 | Civilization | Minimum power level of a structure counted as a wonder |
| wonder_prosperity | harika_refah | 2 | 0 | 100 | Civilization | Per-epoch prosperity contribution of a wonder to its owner |
| wonder_faith | harika_inanc | 1 | 0 | 100 | Civilization | Per-epoch faith contribution of a wonder to its owner |
| wonder_renown | harika_un | 1 | 0 | 100 | Civilization | Per-epoch renown to the god of a wonder's owner |
| wonder_envy_threshold | harika_kiskanclik_esik | 10 | -100 | 100 | War and diplomacy | A neighbour below this relation envies the wonder |
| wonder_envy_relation_loss | harika_kiskanclik | 2 | 0 | 100 | War and diplomacy | Relation loss of an envious neighbour (per epoch) |
| wonder_war_relation | harika_savas_iliski | 40 | 0 | 100 | War and diplomacy | Hostility of a neighbour going to war over a wonder (relation minus this) |
| climate_first_duration | iklim_ilk_sure | 3 | 1 | 100 | Population and growth | Base duration of the first climate age (epochs) |
| climate_first_die | iklim_ilk_zar | 3 | 1 | 100 | Population and growth | Die added to the first climate age (epochs) |
| climate_duration | iklim_sure | 3 | 1 | 100 | Population and growth | Base duration of a climate age (epochs) |
| climate_die | iklim_zar | 4 | 1 | 100 | Population and growth | Die added to a climate age (epochs) |
| climate_coast_drought_divisor | iklim_kiyi_kurak_bolen | 2 | 1 | 100 | Population and growth | Drought strikes the coast divided by this number |
| climate_coast_rain_bonus | iklim_kiyi_yagmur | 1 | 0 | 50 | Population and growth | Extra fertility of the coast in a rain age |
| climate_mountain_ice_loss | iklim_dag_buzul | 3 | 0 | 50 | Population and growth | Extra fertility loss of mountainous regions in an ice age |
| fertility_equilibrium | bereket_denge | 50 | 0 | 100 | Population and growth | Equilibrium value fertility is drawn to in the long run |
| god_corpse_power | ceset_guc | 8 | 1 | 12 | Creator and essence | Power level of a god's corpse |
| god_corpse_danger | ceset_tehlike | 45 | 0 | 100 | Creator and essence | Danger of a god's corpse |
| god_corpse_fertility | ceset_bereket | 30 | 0 | 100 | Creator and essence | Fertility of a god's corpse |
| god_corpse_mystery | ceset_gizem | 95 | 0 | 100 | Creator and essence | Mystery of a god's corpse |
| god_shade_power | tanri_ruhu_guc | 7 | 1 | 12 | Creator and essence | Power level of the dead god's shade |
| god_shade_strength | tanri_ruhu_stat_guc | 70 | 0 | 100 | Creator and essence | Strength of the dead god's shade |
| god_shade_unrest | tanri_ruhu_huzursuzluk | 75 | 0 | 100 | Creator and essence | Unrest of the dead god's shade |
| resurrection_cult_default_population | dirilis_murit_yedek | 500 | 0 | 1,000,000 | Creator and essence | Resurrection cult: population assumed for a loyal community with no population record |
| resurrection_cult_join_pct | dirilis_murit_pay | 10 | 0 | 100 | Creator and essence | Share of loyal communities joining the resurrection cult (%) |
| resurrection_cult_min_followers | dirilis_murit_alt | 50 | 1 | 1,000,000 | Creator and essence | Minimum followers of a resurrection cult |
| resurrection_cult_max_followers | dirilis_murit_ust | 1,000,000 | 1 | 100,000,000 | Creator and essence | Maximum followers of a resurrection cult |
| resurrection_cult_power | dirilis_tarikat_guc | 4 | 1 | 12 | Creator and essence | Power level of a resurrection cult |
| resurrection_cult_zealotry | dirilis_tarikat_bagnazlik | 75 | 0 | 100 | Creator and essence | Zealotry of a resurrection cult |
| resurrection_cult_influence | dirilis_tarikat_etki | 40 | 0 | 100 | Creator and essence | Influence of a resurrection cult |
| dead_essence_divisor | olu_oz_bolen | 2 | 1 | 100 | Creator and essence | The dead god's essence is divided by this number and returns to the Creator |
| god_death_relation_threshold | tanri_olum_iliski | 30 | 0 | 100 | Creator and essence | Hostility/friendship threshold toward the dead god |
| god_death_enemy_renown | tanri_olum_dusman_un | 5 | 0 | 100 | Creator and essence | Renown gain of the dead god's enemy |
| god_death_friend_wrath | tanri_olum_ofke | 10 | 0 | 100 | Creator and essence | Wrath gain of the dead god's friend |
| resurrected_existence | dirilis_varlik | 35 | 0 | 100 | Creator and essence | Existence of a resurrected god |
| resurrected_hp_divisor | dirilis_can_bolen | 2 | 1 | 100 | Creator and essence | Resurrected god's HP: max HP / this number |
| resurrected_essence_divisor | dirilis_oz_bolen | 3 | 1 | 100 | Creator and essence | Resurrected god's essence: max essence / this number |
| resurrected_renown | dirilis_un | 20 | 0 | 1000 | Creator and essence | Renown gain of a resurrected god |
| resurrected_stat_loss | dirilis_stat_kayip | 4 | 0 | 100 | Creator and essence | Loss in each stat of a resurrected god |
| devotion_follower_log_mult | adanmislik_murit | 6 | 0 | 100 | Creator and essence | Resurrection devotion: log10(followers) multiplier |
| devotion_influence_divisor | adanmislik_etki_bolen | 10 | 1 | 1000 | Creator and essence | Resurrection devotion: influence / this number |
| devotion_zealotry_divisor | adanmislik_bagnaz_bolen | 20 | 1 | 1000 | Creator and essence | Resurrection devotion: zealotry / this number |
| devotion_cap | adanmislik_tavan | 200 | 1 | 10,000 | Creator and essence | Cap of resurrection devotion |
| resurrection_devotion_required | dirilis_adanmislik | 100 | 0 | 10,000 | Creator and essence | Devotion required for the resurrection rite |
| existence_default | varlik_yedek | 60 | 0 | 100 | Creator and essence | Existence assumed for a son with no existence record |
| fading_threshold | solus_esik | 10 | 0 | 100 | Creator and essence | A son below this existence starts fading out |
| fading_death_epochs | solus_cag | 3 | 1 | 50 | Creator and essence | Epochs for a fading son to die |
| role_farmer_leader_strength | rol_ciftci_onder_guc | 10 | 0 | 100 | Heroes and mortals | Born folk leader: strength tendency |
| role_farmer_leader_charisma | rol_ciftci_onder_karizma | 15 | 0 | 100 | Heroes and mortals | Born folk leader: charisma tendency |
| role_farmer_shepherd_agility | rol_ciftci_coban_ceviklik | 15 | 0 | 100 | Heroes and mortals | Born shepherd: agility tendency |
| role_farmer_shepherd_strength | rol_ciftci_coban_guc | 5 | 0 | 100 | Heroes and mortals | Born shepherd: strength tendency |
| role_farmer_midwife_intellect | rol_ciftci_ebe_akil | 15 | 0 | 100 | Heroes and mortals | Born midwife: intellect tendency |
| role_farmer_midwife_charisma | rol_ciftci_ebe_karizma | 5 | 0 | 100 | Heroes and mortals | Born midwife: charisma tendency |
| role_artisan_master_intellect | rol_zanaatkar_usta_akil | 15 | 0 | 100 | Heroes and mortals | Born master artisan: intellect tendency |
| role_artisan_master_agility | rol_zanaatkar_usta_ceviklik | 10 | 0 | 100 | Heroes and mortals | Born master artisan: agility tendency |
| role_artisan_smith_strength | rol_zanaatkar_demirci_guc | 20 | 0 | 100 | Heroes and mortals | Born blacksmith: strength tendency |
| role_artisan_architect_intellect | rol_zanaatkar_mimar_akil | 20 | 0 | 100 | Heroes and mortals | Born architect: intellect tendency |
| role_merchant_trader_intellect | rol_tuccar_tuccar_akil | 10 | 0 | 100 | Heroes and mortals | Born merchant: intellect tendency |
| role_merchant_trader_charisma | rol_tuccar_tuccar_karizma | 15 | 0 | 100 | Heroes and mortals | Born merchant: charisma tendency |
| role_merchant_caravaneer_agility | rol_tuccar_kervanci_ceviklik | 10 | 0 | 100 | Heroes and mortals | Born caravaneer: agility tendency |
| role_merchant_caravaneer_strength | rol_tuccar_kervanci_guc | 10 | 0 | 100 | Heroes and mortals | Born caravaneer: strength tendency |
| role_merchant_moneychanger_intellect | rol_tuccar_sarraf_akil | 20 | 0 | 100 | Heroes and mortals | Born money-changer: intellect tendency |
| role_priest_seer_intellect | rol_rahip_kahin_akil | 20 | 0 | 100 | Heroes and mortals | Born seer: intellect tendency |
| role_priest_seer_charisma | rol_rahip_kahin_karizma | 10 | 0 | 100 | Heroes and mortals | Born seer: charisma tendency |
| role_priest_healer_intellect | rol_rahip_sifaci_akil | 15 | 0 | 100 | Heroes and mortals | Born healer: intellect tendency |
| role_priest_healer_charisma | rol_rahip_sifaci_karizma | 5 | 0 | 100 | Heroes and mortals | Born healer: charisma tendency |
| role_priest_bard_charisma | rol_rahip_ozan_karizma | 20 | 0 | 100 | Heroes and mortals | Born bard: charisma tendency |
| role_warrior_warrior_strength | rol_savasci_savasci_guc | 25 | 0 | 100 | Heroes and mortals | Born warrior: strength tendency |
| role_warrior_warrior_agility | rol_savasci_savasci_ceviklik | 15 | 0 | 100 | Heroes and mortals | Born warrior: agility tendency |
| role_warrior_hunter_agility | rol_savasci_avci_ceviklik | 25 | 0 | 100 | Heroes and mortals | Born hunter: agility tendency |
| role_warrior_hunter_strength | rol_savasci_avci_guc | 10 | 0 | 100 | Heroes and mortals | Born hunter: strength tendency |
| role_warrior_guard_strength | rol_savasci_muhafiz_guc | 20 | 0 | 100 | Heroes and mortals | Born guard: strength tendency |
| role_warrior_guard_charisma | rol_savasci_muhafiz_karizma | 5 | 0 | 100 | Heroes and mortals | Born guard: charisma tendency |
| role_scribe_sage_intellect | rol_katip_bilge_akil | 25 | 0 | 100 | Heroes and mortals | Born sage: intellect tendency |
| role_scribe_historian_intellect | rol_katip_tarihci_akil | 20 | 0 | 100 | Heroes and mortals | Born historian: intellect tendency |
| role_scribe_historian_charisma | rol_katip_tarihci_karizma | 5 | 0 | 100 | Heroes and mortals | Born historian: charisma tendency |
| role_scribe_cartographer_intellect | rol_katip_haritaci_akil | 15 | 0 | 100 | Heroes and mortals | Born cartographer: intellect tendency |
| role_scribe_cartographer_agility | rol_katip_haritaci_ceviklik | 10 | 0 | 100 | Heroes and mortals | Born cartographer: agility tendency |
| birth_stat_base | dogum_stat_taban | 35 | 0 | 100 | Heroes and mortals | Base stat of a born notable mortal |
| birth_stat_die | dogum_stat_zar | 30 | 1 | 100 | Heroes and mortals | Die added to the stat of a born notable mortal |
| birth_lifespan_base | dogum_omur | 60 | 1 | 50,000 | Heroes and mortals | Base lifespan of a born notable mortal (years) |
| birth_lifespan_die | dogum_omur_zar | 45 | 1 | 50,000 | Heroes and mortals | Die added to the lifespan of a born notable mortal (years) |
| birth_power_share_pct | dogum_guc_pay | 70 | 0 | 200 | Heroes and mortals | Power level of a born mortal: share of its community's (%) |
| birth_power_max | dogum_guc_ust | 6 | 1 | 12 | Heroes and mortals | Maximum power level of a born mortal |
| birth_age_min_pct | dogum_yas_alt | 18 | 0 | 100 | Heroes and mortals | Born mortal's age: minimum share of lifespan (%) |
| birth_age_range_pct | dogum_yas_aralik | 20 | 0 | 100 | Heroes and mortals | Born mortal's age: random share of lifespan added (%) |
| birth_hp | dogum_can | 100 | 1 | 1000 | Heroes and mortals | HP of a born mortal |
| notable_cap_share_pct | unlu_oran | 80 | 0 | 1000 | Heroes and mortals | Per-epoch notable-mortal cap: share of the number of communities (%) |
| notable_cap_min | unlu_alt | 2 | 0 | 100 | Heroes and mortals | Lowest per-epoch notable-mortal cap |
| notable_alive_base | unlu_yasayan_taban | 2 | 0 | 100 | Heroes and mortals | Living notable mortals per community: base (+ log10 population) |
| notable_crowd_max_pct | unlu_kalabalik_ust | 25 | 0 | 100 | Heroes and mortals | Maximum contribution of crowd size to notable-mortal chance (%) |
| notable_crowd_divisor | unlu_kalabalik_bolen | 25 | 1 | 1000 | Heroes and mortals | Crowd contribution: log10(population) / this number |
| notable_warrior_lifespan_bonus | unlu_savasci_omur | 10 | 0 | 500 | Heroes and mortals | Extra lifespan of someone born into the warrior class (years) |
| ruler_charisma_bias | hukumdar_karizma | 20 | 0 | 100 | Heroes and mortals | Charisma tendency of a ruler taking the throne |
| ruler_intellect_bias | hukumdar_akil | 10 | 0 | 100 | Heroes and mortals | Intellect tendency of a ruler taking the throne |
| ruler_lifespan_bonus | hukumdar_omur | 10 | 0 | 500 | Heroes and mortals | Extra lifespan of a ruler taking the throne (years) |
| village_cap | koy_tavan | 2 | 0 | 50 | Population and growth | Maximum new villages per epoch |
| first_village_chance | koy_ilk_sans | 60 | 0 | 100 | Population and growth | A people without a homeland founds its first homeland (%) |
| extra_village_chance | koy_ek_sans | 30 | 0 | 100 | Population and growth | A populous people founds an additional village (%) |
| village_migration_pct | koy_goc_pay | 8 | 0 | 100 | Population and growth | Share of population migrating to the new village (%) |
| village_prosperity | koy_refah | 40 | 0 | 100 | Population and growth | Prosperity of a new village |
| village_defense | koy_savunma | 20 | 0 | 100 | Population and growth | Defense of a new village |
| derived_min_power | turev_guc_alt | 2 | 1 | 12 | Population and growth | Minimum power level of a derived settlement, people, structure and faction |
| new_people_cap | yeni_halk_tavan | 1 | 0 | 20 | Population and growth | Maximum new peoples per epoch (ethnogenesis or sapience) |
| ethnogenesis_population_pct | etnogenez_nufus_pay | 50 | 0 | 100 | Population and growth | Population passing to the splitting people: share of the settlement's population (%; subtracted from the settlement) |
| ethno_stat_base | etno_stat_taban | 30 | 0 | 100 | Population and growth | Martiality and craft base of a splitting people |
| ethno_stat_die | etno_stat_zar | 40 | 1 | 100 | Population and growth | Die added to the martiality and craft of a splitting people |
| ethno_magic_die | etno_buyu_zar | 50 | 1 | 100 | Population and growth | Magic of a splitting people (die) |
| sapience_min_intelligence | akillanma_zeka | 70 | 0 | 100 | Creatures | Minimum intelligence of a species that can turn into a people |
| sapient_population_base | akil_nufus | 800 | 1 | 10,000,000 | Creatures | Base population of a people born from a sapient species |
| sapient_population_die | akil_nufus_zar | 3000 | 1 | 10,000,000 | Creatures | Die added to the population of a people born from a sapient species |
| sapient_default_strength | akil_guc_yedek | 40 | 0 | 100 | Creatures | Sapient species: strength assumed if unrecorded |
| sapient_martiality_die | akil_savas_zar | 20 | 1 | 100 | Creatures | Die added to the martiality of a sapient people |
| sapient_magic_die | akil_buyu_zar | 60 | 1 | 100 | Creatures | Magic of a sapient people (die) |
| sapient_craft_die | akil_zanaat_zar | 40 | 1 | 100 | Creatures | Craft of a sapient people (die) |
| sapient_piety_base | akil_inanc | 30 | 0 | 100 | Creatures | Base piety of a sapient people |
| sapient_piety_die | akil_inanc_zar | 40 | 1 | 100 | Creatures | Die added to the piety of a sapient people |
| script_alphabet_base | yazi_alfabe_taban | 2 | 0 | 100 | Religion and language | Script type choice: alphabet base weight |
| script_alphabet_divisor | yazi_alfabe_bolen | 4 | 1 | 1000 | Religion and language | Alphabet weight: merchant share / this number |
| script_syllabary_base | yazi_hece_taban | 2 | 0 | 100 | Religion and language | Script type choice: syllabary base weight |
| script_syllabary_divisor | yazi_hece_bolen | 20 | 1 | 1000 | Religion and language | Syllabary weight: language complexity / this number |
| script_pictographic_base | yazi_resim_taban | 1 | 0 | 100 | Religion and language | Script type choice: pictographic script base weight |
| script_pictographic_divisor | yazi_resim_bolen | 15 | 1 | 1000 | Religion and language | Pictographic weight: language sacredness / this number |
| script_knot_base | yazi_dugum_taban | 2 | 0 | 100 | Religion and language | Script type choice: knot script base weight |
| script_knot_divisor | yazi_dugum_bolen | 30 | 1 | 1000 | Religion and language | Knot-script weight: farmer share / this number |
| script_notch_base | yazi_oyma_taban | 1 | 0 | 100 | Religion and language | Script type choice: notch (carved) script base weight |
| script_notch_divisor | yazi_oyma_bolen | 8 | 1 | 1000 | Religion and language | Notch-script weight: priest share / this number |
| script_complexity_gain | yazi_karmasiklik | 8 | 0 | 100 | Religion and language | Complexity gain of a language that acquires a script |
| script_default_complexity | yazi_karmasiklik_yedek | 30 | 0 | 100 | Religion and language | Complexity assumed for a language with no complexity record |
| manifest_creature_hp | tez_tur_can | 200 | 1 | 100,000 | Religion and language | Creature born from a legend: base HP |
| manifest_creature_hp_die | tez_tur_can_zar | 300 | 1 | 100,000 | Religion and language | Creature born from a legend: die added to HP |
| manifest_creature_strength | tez_tur_guc | 50 | 0 | 100 | Religion and language | Creature born from a legend: base strength |
| manifest_creature_strength_die | tez_tur_guc_zar | 40 | 1 | 100 | Religion and language | Creature born from a legend: die added to strength |
| manifest_creature_agility | tez_tur_ceviklik | 30 | 0 | 100 | Religion and language | Creature born from a legend: base agility |
| manifest_creature_agility_die | tez_tur_ceviklik_zar | 40 | 1 | 100 | Religion and language | Creature born from a legend: die added to agility |
| manifest_creature_intelligence | tez_tur_zeka | 20 | 0 | 100 | Religion and language | Creature born from a legend: base intelligence |
| manifest_creature_intelligence_die | tez_tur_zeka_zar | 40 | 1 | 100 | Religion and language | Creature born from a legend: die added to intelligence |
| manifest_creature_danger | tez_tur_tehlike | 55 | 0 | 100 | Religion and language | Creature born from a legend: base danger |
| manifest_creature_danger_die | tez_tur_tehlike_zar | 35 | 1 | 100 | Religion and language | Creature born from a legend: die added to danger |
| manifest_spirit_strength | tez_ruh_guc | 40 | 0 | 100 | Religion and language | Spirit born from belief: base strength |
| manifest_spirit_strength_die | tez_ruh_guc_zar | 40 | 1 | 100 | Religion and language | Spirit born from belief: die added to strength |
| manifest_spirit_unrest | tez_ruh_huzursuzluk | 40 | 0 | 100 | Religion and language | Spirit born from belief: base unrest |
| manifest_spirit_unrest_die | tez_ruh_huzursuzluk_zar | 40 | 1 | 100 | Religion and language | Spirit born from belief: die added to unrest |
| manifest_resource_abundance | tez_kaynak_bolluk | 50 | 0 | 100 | Religion and language | Sanctified resource: base abundance |
| manifest_resource_abundance_die | tez_kaynak_bolluk_zar | 40 | 1 | 100 | Religion and language | Sanctified resource: die added to abundance |
| manifest_resource_value | tez_kaynak_deger | 40 | 0 | 100 | Religion and language | Sanctified resource: base value |
| manifest_resource_value_die | tez_kaynak_deger_zar | 40 | 1 | 100 | Religion and language | Sanctified resource: die added to value |
| manifest_resource_might | tez_kaynak_kudret | 30 | 0 | 100 | Religion and language | Sanctified resource: base might |
| manifest_resource_might_die | tez_kaynak_kudret_zar | 50 | 1 | 100 | Religion and language | Sanctified resource: die added to might |
| manifest_relic_damage_die | tez_esya_hasar_zar | 40 | 1 | 100 | Religion and language | Relic from the legend: damage (die) |
| manifest_relic_protection_die | tez_esya_koruma_zar | 40 | 1 | 100 | Religion and language | Relic from the legend: protection (die) |
| manifest_relic_might | tez_esya_kudret | 40 | 0 | 100 | Religion and language | Relic from the legend: base might |
| manifest_relic_might_die | tez_esya_kudret_zar | 50 | 1 | 100 | Religion and language | Relic from the legend: die added to might |
| manifest_relic_curse_die | tez_esya_lanet_zar | 30 | 1 | 100 | Religion and language | Relic from the legend: curse (die) |
| legend_default_spread | efsane_yayginlik_yedek | 30 | 0 | 100 | Religion and language | Spread assumed for a legend with no spread record |
| legend_spread_per_teller | efsane_anlatan | 2 | 0 | 100 | Religion and language | Per-epoch contribution of each teller to legend spread |
| legend_spread_decay | efsane_sonme | 2 | 0 | 100 | Religion and language | Per-epoch decay of legend spread |
| tradition_grace_epochs | gelenek_mehil | 3 | 0 | 100 | Religion and language | Grace period of a new tradition before it fades (epochs) |
| tradition_default_spread | gelenek_yayginlik_yedek | 40 | 0 | 100 | Religion and language | Spread assumed for a tradition with no spread record |
| tradition_celebrants_per_point | gelenek_kutlayan_ust | 2 | 1 | 100 | Religion and language | Tradition: this many celebrants raise spread by 1 (fewer preserve it) |
| tradition_decay | gelenek_sonme | 2 | 0 | 100 | Religion and language | Per-epoch decay of a tradition with no celebrants |
| engine_tradition_decay | gelenek_dunya_sonme | 4 | 0 | 100 | Religion and language | Per-epoch decay of an engine-made tradition with no celebrants |
| prophecy_forget_epochs | kehanet_unutulma | 20 | 0 | 1000 | Religion and language | An unfulfilled prophecy is forgotten after this many epochs (0: never forgotten) |
| tradition_forget_spread | gelenek_unutma | 5 | 0 | 100 | Religion and language | A celebrant-less tradition falling to this spread is forgotten |
| tale_forget_spread | masal_unutma_yayginlik | 3 | 0 | 100 | Religion and language | An old fairy tale falling to this spread is forgotten |
| tale_forget_min_age | masal_unutma_cag | 15 | 0 | 1000 | Religion and language | Age of a fairy tale before it can be forgotten (epochs) |
| manifestation_cap | tezahur_tavan | 1 | 0 | 20 | Religion and language | Maximum legends becoming real per epoch |
| manifestation_min_spread | tezahur_yayginlik | 70 | 0 | 100 | Religion and language | Minimum spread of a legend that can become real |
| manifestation_max_power | tezahur_guc_ust | 8 | 1 | 12 | Religion and language | Maximum power level of something born from a legend |
| manifestation_power_bonus | tezahur_guc_ek | 1 | 0 | 12 | Religion and language | Power level of something born from a legend is this much above the legend's |
| legend_power_gap | efsane_guc_fark | 1 | 0 | 12 | Religion and language | Power level of a legend born from an event is this much lower than the event's |
| legend_event_min_age | efsane_olay_yas | 5 | 0 | 1000 | Religion and language | Minimum age of an event that can turn into a legend (epochs) |
| legend_event_min_severity | efsane_siddet | 60 | 0 | 100 | Religion and language | Minimum severity of an event that can turn into a legend |
| legendization_cap | efsanelesme_tavan | 1 | 0 | 20 | Religion and language | Maximum events turning into legends per epoch |
| legend_spread_base | efsane_yayginlik | 45 | 0 | 100 | Religion and language | Base spread of a legend born from an event |
| legend_spread_die | efsane_yayginlik_zar | 25 | 1 | 100 | Religion and language | Die added to the spread of a legend born from an event |
| tale_min_age | masal_cag | 10 | 0 | 1000 | Religion and language | Age of a legend before it can turn into a fairy tale (epochs) |
| tale_spread_threshold | masal_yayginlik | 50 | 0 | 100 | Religion and language | An old legend with spread below this turns into a fairy tale |
| tale_keeper_distance | masal_koruyucu_mesafe | 3 | 0 | 20 | Religion and language | Distance within which a sage or bard protects a legend (map steps) |
| life_min_fertility | yasam_bereket | 30 | 0 | 100 | Population and growth | Minimum fertility of a region where life appears spontaneously |
| life_region_pick | yasam_bolge_secim | 2 | 1 | 100 | Population and growth | Life appears in one of this many most fertile regions |
| native_people_power | yerli_halk_guc | 3 | 1 | 12 | Population and growth | Power level of a native people |
| native_people_population | yerli_halk_nufus | 400 | 1 | 10,000,000 | Population and growth | Base population of a native people |
| native_people_population_die | yerli_halk_nufus_zar | 500 | 1 | 10,000,000 | Population and growth | Die added to the population of a native people |
| native_people_stat | yerli_halk_stat | 20 | 0 | 100 | Population and growth | Martiality, magic and craft base of a native people |
| native_people_stat_die | yerli_halk_stat_zar | 40 | 1 | 100 | Population and growth | Die added to the martiality, magic and craft of a native people |
| native_people_piety | yerli_halk_inanc | 30 | 0 | 100 | Population and growth | Base piety of a native people |
| native_people_piety_die | yerli_halk_inanc_zar | 40 | 1 | 100 | Population and growth | Die added to the piety of a native people |
| native_species_power | yerli_tur_guc | 2 | 1 | 12 | Creatures | Power level of a native living species |
| native_species_hp | yerli_tur_can | 60 | 1 | 100,000 | Creatures | Base HP of a native species |
| native_species_hp_die | yerli_tur_can_zar | 60 | 1 | 100,000 | Creatures | Die added to the HP of a native species |
| native_species_strength | yerli_tur_stat_guc | 20 | 0 | 100 | Creatures | Base strength of a native species |
| native_species_strength_die | yerli_tur_guc_zar | 50 | 1 | 100 | Creatures | Die added to the strength of a native species |
| native_species_agility | yerli_tur_ceviklik | 20 | 0 | 100 | Creatures | Base agility of a native species |
| native_species_agility_die | yerli_tur_ceviklik_zar | 60 | 1 | 100 | Creatures | Die added to the agility of a native species |
| native_species_intelligence | yerli_tur_zeka | 5 | 0 | 100 | Creatures | Base intelligence of a native species |
| native_species_intelligence_die | yerli_tur_zeka_zar | 30 | 1 | 100 | Creatures | Die added to the intelligence of a native species |
| native_species_danger | yerli_tur_tehlike | 10 | 0 | 100 | Creatures | Base danger of a native species |
| native_species_danger_die | yerli_tur_tehlike_zar | 50 | 1 | 100 | Creatures | Die added to the danger of a native species |
| nearest_language_region_weight | dil_bolge_agirlik | 3 | 1 | 100 | Religion and language | Nearest language: weight of a speaker in the same region |
| first_faith_region_weight | tanri_bolge_agirlik | 3 | 1 | 100 | Religion and language | First faith: weight of a worshipper in the same region in the god choice (a worshipper in another region counts 1) |
| first_faith_chance | ilk_inanc_sans | 60 | 0 | 100 | Religion and language | A community without faith binds to a god this epoch (%; one that doesn't stays a candidate for godlessness and retries next epoch) |
| first_faith_crowd_exponent | ilk_inanc_us | 50 | 0 | 100 | Religion and language | Pull of the crowd in first faith: god weight = worshipper weight ^ (this / 100); 100 is linear, smaller gives diminishing returns |
| first_faith_son_base_weight | ilk_inanc_ogul | 2 | 0 | 100 | Religion and language | Base weight in first faith of every active son on that world (young sons without worshippers still get a share) |
| primitive_language_spread | ilkel_yayginlik | 5 | 0 | 100 | Religion and language | Spread of a primitive language |
| primitive_language_complexity | ilkel_karmasiklik | 15 | 0 | 100 | Religion and language | Complexity of a primitive language |
| primitive_language_sacredness | ilkel_kutsallik | 10 | 0 | 100 | Religion and language | Sacredness of a primitive language |
| ruin_resettle_min_population | harabe_nufus_alt | 60 | 1 | 1,000,000 | Population and growth | Minimum population of a resettled ruin |
| ruin_resettle_prosperity | harabe_refah | 30 | 0 | 100 | Population and growth | Prosperity of a resettled ruin |
| ruin_resettle_min_defense | harabe_savunma_alt | 15 | 0 | 100 | Population and growth | Minimum defense of a resettled ruin |
| ruin_default_defense | harabe_savunma_yedek | 20 | 0 | 100 | Population and growth | Defense assumed for a ruin with no defense record |
| ruin_defense_divisor | harabe_savunma_bolen | 2 | 1 | 100 | Population and growth | A resettled ruin takes 1/this of its former defense |
| refugee_min_population | multeci_nufus | 600 | 0 | 10,000,000 | Population and growth | Minimum population of a community able to send refugees |
| refugee_cap | multeci_tavan | 1 | 0 | 20 | Population and growth | Maximum refugee migrations per epoch |
| refugee_disaster_min_severity | multeci_afet_siddet | 60 | 0 | 100 | Population and growth | Minimum severity of a disaster that produces refugees |
| refugee_min_people | multeci_en_az | 50 | 1 | 1,000,000 | Population and growth | Minimum people in a refugee migration |
| refugee_weight_ally | multeci_muttefik_agirlik | 3 | 0 | 100 | Population and growth | Refugee destination: ally weight |
| refugee_weight_language | multeci_dil_agirlik | 2 | 0 | 100 | Population and growth | Refugee destination: same-language weight |
| refugee_weight_god | multeci_tanri_agirlik | 1 | 0 | 100 | Population and growth | Refugee destination: same-god weight |
| refugee_weight_other_region | multeci_uzak_agirlik | 1 | 0 | 100 | Population and growth | Refugee destination: other-region weight |
| spirit_default_unrest | ruh_huzursuzluk_yedek | 40 | 0 | 100 | The Beyond | Unrest assumed for a spirit with no unrest record |
| spirit_rest_min_age | ruh_dinme_yas | 2 | 0 | 100 | The Beyond | Age of a spirit before it can come to rest (epochs) |
| spirit_passage_min_age | ruh_gecis_yas | 1 | 0 | 100 | The Beyond | Age of a spirit before it can pass to the land of the dead (epochs) |
| language_death_grace | dil_olum_mehil | 2 | 0 | 100 | Religion and language | Grace period of a new language before it counts as dead (epochs) |
| language_death_note_cap | dil_olum_not_tavan | 3 | 0 | 100 | Chronicle | Maximum language deaths written to the chronicle per epoch |
| temple_min_piety | tapinak_inanc | 50 | 0 | 100 | Civilization | Minimum piety of a community that builds a temple |
| temple_min_priest_pct | tapinak_rahip | 6 | 0 | 100 | Civilization | Minimum priest share of a community that builds a temple (%) |
| temple_piety_gain | tapinak_inanc_artis | 8 | 0 | 100 | Civilization | Contribution of a temple to piety |
| wall_default_defense | sur_savunma_yedek | 30 | 0 | 100 | Civilization | Defense assumed for a settlement with no defense record |
| wall_defense_threshold | sur_savunma | 55 | 0 | 100 | Civilization | A settlement below this defense builds walls |
| wall_defense_gain | sur_artis | 15 | 0 | 100 | Civilization | Contribution of walls to defense |
| library_min_scribe_pct | kutuphane_katip | 7 | 0 | 100 | Civilization | Minimum scribe share of a community that builds a library (%) |
| structure_people_prosperity_base | yapit_halk_refah | 40 | 0 | 100 | Civilization | A people's assumed prosperity: base |
| structure_people_craft_divisor | yapit_halk_zanaat_bolen | 4 | 1 | 1000 | Civilization | A people's assumed prosperity: craft / this number |
| structure_settlement_min_population | yapit_kent_nufus | 800 | 0 | 10,000,000 | Civilization | Minimum population of a settlement able to build a structure |
| structure_people_min_population | yapit_halk_nufus | 2000 | 0 | 100,000,000 | Civilization | Minimum population of a people able to build a structure |
| structure_min_artisan_pct | yapit_zanaatkar | 13 | 0 | 100 | Civilization | Minimum artisan share to build a structure (%) |
| structure_min_craft | yapit_zanaat | 50 | 0 | 100 | Civilization | Minimum craft to build a structure |
| structure_power_share_pct | yapit_guc_pay | 80 | 0 | 200 | Civilization | Structure power level: share of the builder's (%) |
| structure_max_power | yapit_guc_ust | 7 | 1 | 12 | Civilization | Maximum power level of an engine-built structure |
| structure_splendor_base | yapit_ihtisam | 25 | 0 | 100 | Civilization | Base splendor of a new structure |
| structure_splendor_die | yapit_ihtisam_zar | 30 | 1 | 100 | Civilization | Die added to the splendor of a new structure |
| structure_architecture_bonus | yapit_mimarlik_ek | 10 | 0 | 100 | Civilization | Extra splendor for a structure of those who know architecture |
| structure_durability_base | yapit_saglamlik | 45 | 0 | 100 | Civilization | Base durability of a new structure |
| structure_durability_die | yapit_saglamlik_zar | 35 | 1 | 100 | Civilization | Die added to the durability of a new structure |
| structure_function_base | yapit_islev | 40 | 0 | 100 | Civilization | Base function of a new structure |
| structure_function_die | yapit_islev_zar | 40 | 1 | 100 | Civilization | Die added to the function of a new structure |
| structure_prosperity_cost | yapit_refah_bedel | 4 | 0 | 100 | Civilization | Prosperity cost of building a structure |
| structure_default_goods | yapit_mal_yedek | 20 | 0 | 1000 | Civilization | Goods assumed for a community with no stockpile record |
| structure_goods_cost | yapit_mal_bedel | 15 | 0 | 1000 | Civilization | Goods cost of building a structure |
| adorn_min_prosperity | ihtisam_refah | 50 | 0 | 100 | Civilization | Minimum prosperity of an owner who adorns their structure |
| adorn_default_splendor | ihtisam_yedek | 30 | 0 | 100 | Civilization | Splendor assumed for a structure with no splendor record |
| adorn_min_artisan_pct | ihtisam_zanaatkar | 16 | 0 | 100 | Civilization | Minimum artisan share of the owner for extra splendor (%) |
| adorn_artisan_bonus | ihtisam_zanaatkar_ek | 2 | 0 | 100 | Civilization | Per-epoch extra splendor to the structure of an artisan owner |
| adorn_architecture_bonus | ihtisam_mimarlik_ek | 1 | 0 | 100 | Civilization | Per-epoch extra splendor to the structure of an owner who knows architecture |
| guild_min_merchant_pct | lonca_tuccar | 11 | 0 | 100 | War and diplomacy | Minimum merchant share of a community that founds a guild (%) |
| guild_min_prosperity | lonca_refah | 45 | 0 | 100 | War and diplomacy | Minimum prosperity of a community that founds a guild |
| guild_strength | lonca_guc | 25 | 0 | 100 | War and diplomacy | Base strength of a merchant guild |
| guild_wealth | lonca_servet | 55 | 0 | 100 | War and diplomacy | Base wealth of a merchant guild |
| guild_sway | lonca_nufuz | 45 | 0 | 100 | War and diplomacy | Base sway of a merchant guild |
| council_min_priest_pct | meclis_rahip | 10 | 0 | 100 | War and diplomacy | Minimum priest share of a community that founds a priests' council (%) |
| council_strength | meclis_guc | 20 | 0 | 100 | War and diplomacy | Base strength of a priests' council |
| council_wealth | meclis_servet | 30 | 0 | 100 | War and diplomacy | Base wealth of a priests' council |
| council_sway | meclis_nufuz | 55 | 0 | 100 | War and diplomacy | Base sway of a priests' council |
| brotherhood_min_warrior_pct | birlik_savasci | 14 | 0 | 100 | War and diplomacy | Minimum warrior share of a community that founds a warrior brotherhood (%) |
| brotherhood_at_war_min_warrior_pct | birlik_savasta_savasci | 11 | 0 | 100 | War and diplomacy | Minimum warrior share for a community at war (%) |
| brotherhood_strength | birlik_guc | 55 | 0 | 100 | War and diplomacy | Base strength of a warrior brotherhood |
| brotherhood_wealth | birlik_servet | 25 | 0 | 100 | War and diplomacy | Base wealth of a warrior brotherhood |
| brotherhood_sway | birlik_nufuz | 40 | 0 | 100 | War and diplomacy | Base sway of a warrior brotherhood |
| revolt_disband_min_age | isyan_dagilma_mehil | 2 | 0 | 100 | War and diplomacy | Age of an uprising before it can disband (epochs) |
| revolt_disband_note_cap | hizip_dagilma_not_tavan | 2 | 0 | 100 | War and diplomacy | Maximum disbanded uprisings written to the chronicle per epoch |
| faction_min_population | hizip_nufus | 1000 | 0 | 100,000,000 | War and diplomacy | Minimum population of a community able to spawn a faction |
| faction_power_share_pct | hizip_guc_pay | 70 | 0 | 200 | War and diplomacy | Faction power level: share of its community's (%) |
| faction_max_power | hizip_guc_ust | 6 | 1 | 12 | War and diplomacy | Maximum power level of an engine-founded faction |
| faction_stat_die | hizip_stat_zar | 25 | 1 | 100 | War and diplomacy | Die added to the stats of a new faction |
| faction_stat_shift | hizip_stat_kayma | 5 | 0 | 100 | War and diplomacy | Subtracted from a new faction's stats after the die |
| preach_base_pct | din_vaaz_taban | 2 | 0 | 100 | Religion and language | Base of conversion by cult preaching (%) |
| preach_influence_divisor | din_vaaz_etki_bolen | 800 | 1 | 100,000 | Religion and language | Preaching chance: cult influence / this number |
| preach_follower_max_pct | din_vaaz_murit_ust | 8 | 0 | 100 | Religion and language | Maximum contribution of followers to the preaching chance (%) |
| preach_follower_min_divisor | din_vaaz_murit_alt | 500 | 1 | 1,000,000 | Religion and language | Preaching chance: followers / at least this number |
| preach_population_mult | din_vaaz_nufus_carpan | 4 | 1 | 1000 | Religion and language | Preaching chance: followers / (population × this number) |
| conversion_renown_divisor | din_un_bolen | 1500 | 1 | 1,000,000 | Religion and language | Conversion: renown difference between gods / this number |
| conversion_seeker_bonus_pct | din_arayan_ek | 10 | 0 | 100 | Religion and language | Contribution of a god-seeking community to conversion (%) |
| culture_first_loanword_pct | kultur_ilk_kelime | 80 | 0 | 100 | Religion and language | Loanword on first contact (%) |
| culture_trade_loanword_pct | kultur_kelime | 50 | 0 | 100 | Religion and language | Loanword in trade contact (%) |
| culture_first_tradition_pct | kultur_ilk_gelenek | 50 | 0 | 100 | Religion and language | Tradition transfer on first contact (%) |
| culture_trade_tradition_pct | kultur_gelenek | 25 | 0 | 100 | Religion and language | Tradition transfer in trade contact (%) |
| culture_first_knowledge_pct | kultur_ilk_bilgi | 40 | 0 | 100 | Religion and language | Knowledge transfer on first contact (%) |
| culture_trade_knowledge_pct | kultur_bilgi | 10 | 0 | 100 | Religion and language | Knowledge transfer in trade contact (%) |
| culture_first_god_pct | kultur_ilk_tanri | 30 | 0 | 100 | Religion and language | God transfer on first contact (%) |
| culture_trade_god_pct | kultur_tanri | 6 | 0 | 100 | Religion and language | God transfer in trade contact (%) |
| world_age_apocalypse_push | dunya_yasi_kiyamet | 2 | 0 | 50 | Apocalypse | Push-back of the doomsday clock at a world's age turning |
| golden_age_min_world_age | altin_mehil | 3 | 0 | 1000 | Civilization | Minimum world age to enter a golden age (epochs) |
| golden_age_prosperity_gain | altin_refah_artis | 1 | 0 | 100 | Civilization | Per-epoch prosperity gain of communities in a golden age |
| golden_age_record_links | altin_kronik_bag | 6 | 0 | 100 | Chronicle | Maximum communities linked to the golden-age record |

### DEEP_RELATIONS

Old namespace `DERIN_ILISKI` · 33 rows · defined in `src/derin.js`. Community-to-community relation model (initial, drift, decay).

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| record_default_power | kayit_guc | 3 | 1 | 12 | Chronicle | Default power level of records opened by the engine |
| dead_link_note_threshold | olu_bag_not | 20 | 1 | 100,000 | Chronicle | If this many dead links close at epoch end, a note is added to the chronicle |
| relation_history_len | iliski_gecmis | 12 | 1 | 500 | Chronicle | Number of recent events kept in a community relation |
| relation_decay_threshold | iliski_sonme_esik | 50 | 0 | 100 | War and diplomacy | Community relation mean reversion: relation beyond this value (±) fades every epoch |
| relation_decay_pct | iliski_sonme_pay | 25 | 0 | 100 | War and diplomacy | Mean reversion: share of the difference beyond the threshold that fades per epoch (%; 0 disables) |
| neighbor_distance | komsu_mesafe | 3 | 0 | 20 | War and diplomacy | Maximum distance at which two communities with unknown map are counted as neighbours (steps) |
| initial_shared_god | ilk_ortak_tanri | 20 | 0 | 100 | War and diplomacy | Initial relation: bonus for worshipping the same god (points) |
| initial_different_god | ilk_farkli_tanri | 5 | 0 | 100 | War and diplomacy | Initial relation: penalty for worshipping different gods (points) |
| initial_shared_language | ilk_ortak_dil | 15 | 0 | 100 | War and diplomacy | Initial relation: bonus for speaking the same language (points) |
| initial_enemy | ilk_dusman | 50 | 0 | 100 | War and diplomacy | Initial relation: hostility penalty (points) |
| initial_ally | ilk_muttefik | 45 | 0 | 100 | War and diplomacy | Initial relation: alliance bonus (points) |
| initial_trade | ilk_ticaret | 20 | 0 | 100 | War and diplomacy | Initial relation: trade bonus (points) |
| initial_tribute | ilk_harac | 15 | 0 | 100 | War and diplomacy | Initial relation: tribute penalty (points) |
| blood_feud | kan_davasi | 30 | 0 | 200 | War and diplomacy | Relation reduced by a blood feud (points) |
| exhaustion_peace_relation | yorgunluk_baris_iliski | 15 | 0 | 100 | War and diplomacy | Relation bonus of an exhaustion peace (points) |
| drift_shared_god | kayma_ortak_tanri | 2 | 0 | 50 | War and diplomacy | Per-epoch drift: shared-god bonus (points) |
| drift_cult_other_god | kayma_tarikat_tanri | 2 | 0 | 50 | War and diplomacy | Per-epoch drift: penalty for a cult of a different god (points) |
| drift_shared_language | kayma_ortak_dil | 1 | 0 | 50 | War and diplomacy | Per-epoch drift: shared-language bonus (points) |
| drift_trade | kayma_ticaret | 3 | 0 | 50 | War and diplomacy | Per-epoch drift: trade bonus (points) |
| drift_ally | kayma_muttefik | 2 | 0 | 50 | War and diplomacy | Per-epoch drift: alliance bonus (points) |
| drift_enemy | kayma_dusman | 3 | 0 | 50 | War and diplomacy | Per-epoch drift: hostility penalty (points) |
| drift_tribute | kayma_harac | 2 | 0 | 50 | War and diplomacy | Per-epoch drift: tribute penalty (points) |
| drift_blood_feud | kayma_kan_davasi | 3 | 0 | 50 | War and diplomacy | Per-epoch drift: blood-feud penalty (points) |
| neighbor_exhaustion_start | komsu_yorgunluk_cag | 2 | 0 | 50 | War and diplomacy | War duration at which exhaustion peace begins between neighbouring enemies (epochs) |
| neighbor_exhaustion_growth_pct | komsu_yorgunluk_artis | 12 | 0 | 100 | War and diplomacy | Per-epoch increase of the exhaustion-peace chance between neighbouring enemies (%) |
| neighbor_exhaustion_cap_pct | komsu_yorgunluk_tavan | 60 | 0 | 100 | War and diplomacy | Cap of the exhaustion-peace chance between neighbouring enemies (%) |
| peace_relation | baris_iliski | 10 | 0 | 100 | War and diplomacy | Relation bonus of peace (points) |
| marriage_min_age | evlilik_yas | 16 | 0 | 200 | Heroes and mortals | Minimum age of a hero who can enter a marriage alliance (years) |
| default_hero_age | varsayilan_yas | 30 | 0 | 200 | Heroes and mortals | Age assumed for a hero with unknown age (years) |
| marriage_relation | evlilik_iliski | 10 | 0 | 100 | War and diplomacy | Relation bonus of a marriage alliance (points) |
| betrayal_cap | ihanet_tavan | 1 | 0 | 20 | War and diplomacy | Maximum betrayals per epoch |
| traitor_default_strength | hain_guc_varsayilan | 40 | 0 | 100 | War and diplomacy | Strength assumed in a betrayal for a party with unknown sway or strength |
| betrayal_relation | ihanet_iliski | 30 | 0 | 200 | War and diplomacy | Relation reduced by betrayal (points) |

### DEEP_SOCIETY

Old namespace `DERIN_TOPLUM` · 128 rows · defined in `src/derin.js`. Social classes, stockpiles (food/ore/goods), prices, satisfaction, famine, revolts, trade flow.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| class_farmer_pct | sinif_ciftci | 55 | 0 | 100 | Economy | Base share of farmers in society (%) |
| class_artisan_pct | sinif_zanaatkar | 15 | 0 | 100 | Economy | Base share of artisans in society (%) |
| class_merchant_pct | sinif_tuccar | 8 | 0 | 100 | Economy | Base share of merchants in society (%) |
| class_priest_pct | sinif_rahip | 7 | 0 | 100 | Economy | Base share of priests in society (%) |
| class_warrior_pct | sinif_savasci | 10 | 0 | 100 | Economy | Base share of warriors in society (%) |
| class_scribe_pct | sinif_katip | 5 | 0 | 100 | Economy | Base share of scribes in society (%) |
| class_initial_satisfaction | memnuniyet_ilk | 55 | 0 | 100 | Economy | Initial satisfaction of classes |
| initial_food | erzak_ilk | 60 | 0 | 1000 | Economy | Community's initial food (supplies) |
| initial_ore | maden_ilk | 10 | 0 | 1000 | Economy | Community's initial ore |
| initial_goods | mal_ilk | 20 | 0 | 1000 | Economy | Community's initial goods |
| stockpile_cap | ambar_tavan | 200 | 10 | 100,000 | Economy | Cap of the food, ore and goods stockpile |
| default_stat | stat_varsayilan | 50 | 0 | 100 | Economy | Value assumed for a community and land with unrecorded prosperity, faith or fertility |
| target_agriculture_farmer | hedef_tarim_ciftci | 10 | 0 | 100 | Economy | Farmer-share bonus for those who know agriculture |
| target_trade_merchant | hedef_ticaret_tuccar | 6 | 0 | 100 | Economy | Merchant-share bonus for those who trade |
| target_route_merchant | hedef_yol_tuccar | 2 | 0 | 100 | Economy | Merchant-share bonus per trade route |
| target_route_merchant_cap | hedef_yol_tavan | 6 | 0 | 100 | Economy | Maximum merchant-share bonus from trade routes |
| target_writing_scribe | hedef_yazi_katip | 6 | 0 | 100 | Economy | Scribe-share bonus for those who know writing |
| target_craft_threshold | hedef_zanaat_esik | 60 | 0 | 100 | Economy | Craft that raises the artisan share |
| target_artisan | hedef_zanaatkar | 7 | 0 | 100 | Economy | Artisan-share bonus with metallurgy or high craft |
| target_seafaring_merchant | hedef_deniz_tuccar | 3 | 0 | 100 | Economy | Merchant-share bonus for those who know seafaring |
| target_war_warrior | hedef_savas_savasci | 10 | 0 | 100 | Economy | Warrior-share bonus in a society at war |
| target_piety_threshold | hedef_inanc_esik | 60 | 0 | 100 | Economy | Piety that raises the priest share |
| target_priest | hedef_rahip | 6 | 0 | 100 | Economy | Priest-share bonus in a pious society |
| target_godless_priest | hedef_tanrisiz_rahip | 2 | 0 | 100 | Economy | Priest share in a godless society |
| class_drift_pct | sinif_kayma | 25 | 0 | 100 | Economy | Per-epoch drift of class shares toward the target (%) |
| fertility_place_share_pct | bereket_konum_pay | 40 | 0 | 100 | Economy | Place's own share in land fertility (%) |
| fertility_region_share_pct | bereket_bolge_pay | 60 | 0 | 100 | Economy | Parent region's share in land fertility (%) |
| food_farmer_divisor | uretim_ciftci_bolen | 45 | 1 | 1000 | Economy | Food production: farmer share / this number |
| food_base_pct | uretim_taban | 55 | 0 | 1000 | Economy | Base of food production independent of fertility (%) |
| food_fertility_divisor | uretim_bereket_bolen | 110 | 1 | 10,000 | Economy | Food production: fertility / this number |
| food_agriculture_pct | uretim_tarim | 135 | 0 | 1000 | Economy | Food-production multiplier for those who know agriculture (%) |
| food_bounty_law_pct | uretim_bereket_yasasi | 115 | 0 | 1000 | Economy | Food-production multiplier under the bounty law (%) |
| food_drought_pct | uretim_kurak | 80 | 0 | 1000 | Economy | Food-production multiplier in a drought age (%) |
| food_rain_pct | uretim_yagmur | 110 | 0 | 1000 | Economy | Food-production multiplier in a rain age (%) |
| food_rate_min_pct | uretim_alt | 20 | 0 | 1000 | Economy | Floor of the food-production rate (%) |
| food_rate_max_pct | uretim_ust | 300 | 0 | 10,000 | Economy | Cap of the food-production rate (%) |
| food_rate_effect | erzak_oran_carpan | 30 | 0 | 1000 | Economy | Per-epoch effect of the production rate on food |
| food_war_consumption | erzak_savas | 6 | 0 | 200 | Economy | Food consumed by war per epoch |
| food_low_threshold | erzak_dusuk | 30 | 0 | 200 | Economy | Below this food the stockpile switches to saving |
| food_saving_gain | erzak_dusuk_ek | 4 | 0 | 200 | Economy | Per-epoch food gain of a stockpile in saving mode |
| ore_abundance_divisor | maden_bolluk_bolen | 10 | 1 | 1000 | Economy | Ore gain: abundance of the ore resource / this number |
| ore_consumption | maden_tuketim | 1 | 0 | 200 | Economy | Ore consumed per epoch |
| goods_artisan_divisor | zanaat_bolen | 15 | 1 | 1000 | Economy | Goods production: artisan share / this number |
| ore_plenty_threshold | maden_bol | 20 | 0 | 200 | Economy | Above this ore, artisans find plenty of ore |
| goods_ore_plenty_pct | zanaat_maden_carpan | 140 | 0 | 1000 | Economy | Goods-production multiplier with plenty of ore (%) |
| goods_metallurgy_pct | zanaat_metalurji | 130 | 0 | 1000 | Economy | Goods-production multiplier for those who know metallurgy (%) |
| goods_production_mult | mal_uretim | 6 | 0 | 100 | Economy | Goods-production multiplier |
| goods_consumption | mal_tuketim | 3 | 0 | 200 | Economy | Goods consumed per epoch |
| goods_prosperity_divisor | mal_refah_bolen | 50 | 1 | 1000 | Economy | Goods consumption of prosperity: prosperity / this number |
| goods_ore_threshold | mal_maden_esik | 10 | 0 | 200 | Economy | Goods and ore threshold at which goods production spends ore |
| goods_ore_spend_mult | mal_maden_harcama | 1 | 0 | 100 | Economy | Ore-spending multiplier of goods production |
| price_food_rate_min_pct | fiyat_oran_alt | 30 | 1 | 1000 | Economy | Floor of the production rate in food price (%) |
| price_scarcity_food | fiyat_kitlik_erzak | 60 | 0 | 200 | Economy | Below this food, bread becomes expensive |
| price_scarcity_pct | fiyat_kitlik | 180 | 0 | 10,000 | Economy | Food-price multiplier in scarcity (%) |
| price_plenty_food | fiyat_bolluk_erzak | 120 | 0 | 100,000 | Economy | Above this food, bread becomes cheap |
| price_plenty_pct | fiyat_bolluk | 70 | 0 | 1000 | Economy | Food-price multiplier in plenty (%) |
| price_min_pct | fiyat_alt | 30 | 0 | 1000 | Economy | Floor of prices (%) |
| price_food_max_pct | fiyat_erzak_ust | 900 | 100 | 100,000 | Economy | Cap of food price (%) |
| price_max_pct | fiyat_ust | 400 | 100 | 100,000 | Economy | Cap of ore and goods price (%) |
| price_equilibrium_stock | fiyat_denge | 40 | 1 | 10,000 | Economy | Stock at which goods are at normal price |
| price_equilibrium_ore | fiyat_denge_maden | 10 | 1 | 10,000 | Economy | Stock at which ore is at normal price (ore stockpiles run much lower than goods) |
| price_stock_floor | fiyat_stok_alt | 10 | 1 | 10,000 | Economy | Floor of stock in ore and goods price |
| sat_hungry_food | m_ac_erzak | 60 | 0 | 200 | Economy | Below this food, farmers are hungry |
| sat_farmer_hungry | m_ciftci_ac | 25 | 0 | 100 | Economy | Satisfaction loss of hungry farmers |
| sat_farmer_fed | m_ciftci_tok | 5 | 0 | 100 | Economy | Satisfaction gain of well-fed farmers |
| sat_farmer_war | m_ciftci_savas | 8 | 0 | 100 | Economy | Farmer satisfaction reduced by war |
| sat_artisan_ore_plenty | m_zanaat_bol | 8 | 0 | 100 | Economy | Artisan satisfaction gain with plenty of ore |
| sat_artisan_ore_scarce | m_zanaat_kit | 6 | 0 | 100 | Economy | Artisan satisfaction loss with scarce ore |
| sat_merchant_per_route | m_tuccar_yol | 6 | 0 | 100 | Economy | Merchant satisfaction gain per trade route |
| sat_merchant_war | m_tuccar_savas | 12 | 0 | 100 | Economy | Merchant satisfaction reduced by war |
| sat_merchant_no_route | m_tuccar_yolsuz | 10 | 0 | 100 | Economy | Satisfaction loss of merchants without a trade route |
| sat_priest_with_god | m_rahip_tanri | 5 | 0 | 100 | Economy | Satisfaction gain of priests who have a god |
| sat_priest_godless | m_rahip_tanrisiz | 15 | 0 | 100 | Economy | Satisfaction loss of priests without a god |
| sat_priest_denial | m_rahip_inkar | 30 | 0 | 100 | Economy | Extra satisfaction loss of priests in a godless society |
| sat_warrior_base | m_savasci_taban | 45 | 0 | 100 | Economy | Base satisfaction of warriors |
| sat_warrior_war | m_savasci_savas | 12 | 0 | 100 | Economy | Satisfaction gain of warriors at war |
| sat_warrior_peace | m_savasci_baris | 5 | 0 | 100 | Economy | Satisfaction loss of warriors at peace |
| sat_warrior_warcraft | m_savasci_sanat | 6 | 0 | 100 | Economy | Satisfaction gain of warriors who know the art of war |
| sat_scribe_writing | m_katip_yazi | 12 | 0 | 100 | Economy | Satisfaction gain of scribes who know writing |
| sat_scribe_no_writing | m_katip_yazisiz | 10 | 0 | 100 | Economy | Satisfaction loss of scribes without writing |
| sat_tribute | m_harac | 8 | 0 | 100 | Economy | Satisfaction loss to all classes from paying tribute |
| sat_justice_divisor | m_adalet_bolen | 5 | 1 | 100 | Economy | Justice of laws to satisfaction: (justice − 50) / this number |
| sat_curse | m_lanet | 6 | 0 | 100 | Economy | Satisfaction loss to all classes from a curse |
| sat_drift_pct | m_kayma | 30 | 0 | 100 | Economy | Per-epoch drift of satisfaction toward the target (%) |
| effect_prosperity_divisor | etki_refah_bolen | 4 | 1 | 100 | Economy | Effect of merchant share on prosperity: (share − base) / this number |
| effect_goods_plenty | etki_mal_bol | 60 | 0 | 100,000 | Economy | Above this goods, prosperity rises additionally |
| effect_goods_prosperity | etki_mal_refah | 1 | 0 | 100 | Economy | Per-epoch prosperity gain from plentiful goods |
| effect_piety_divisor | etki_inanc_bolen | 3 | 1 | 100 | Economy | Effect of priest share on piety: (share − base) / this number |
| effect_defense_divisor | etki_savunma_bolen | 4 | 1 | 100 | Economy | Effect of warrior share on city defense: (share − base) / this number |
| effect_default_defense | etki_savunma_varsayilan | 30 | 0 | 100 | Economy | Defense assumed for a city with unknown defense |
| effect_martiality_divisor | etki_savascilik_bolen | 5 | 1 | 100 | Economy | Effect of warrior share on a people's martiality: (share − base) / this number |
| famine_rate_pct | kitlik_oran | 90 | 0 | 1000 | Population and growth | Value the production rate must stay below for famine (%) |
| famine_food | kitlik_erzak | 60 | 0 | 1000 | Population and growth | Food the stockpile must drop to for famine (it rarely reaches zero since the stockpile refills itself by saving) |
| famine_cap | kitlik_tavan | 1 | 0 | 100 | Population and growth | Maximum famines per epoch |
| famine_population_kept_pct | kitlik_nufus_kalan | 92 | 0 | 100 | Population and growth | Population remaining after famine (%) |
| famine_prosperity_loss | kitlik_refah | 6 | 0 | 100 | Population and growth | Prosperity reduced by famine |
| weapon_ore_required | silah_maden | 12 | 0 | 10,000 | Economy | Ore required to forge weapons (ore stockpiles run low in most communities) |
| weapon_warrior_pct | silah_savasci | 12 | 0 | 100 | Economy | Warrior share required to forge weapons (%) |
| weapon_batch_cap | silah_tavan | 2 | 0 | 100 | Economy | Maximum weapon batches per epoch |
| weapon_ore_cost | silah_maden_bedel | 8 | 0 | 10,000 | Economy | Ore spent by one weapon batch |
| weapon_power | silah_guc | 3 | 1 | 12 | Economy | Power level of a forged weapon |
| weapon_damage_base | silah_hasar | 30 | 0 | 100 | Economy | Base damage of a forged weapon |
| weapon_damage_die | silah_hasar_zar | 35 | 1 | 100 | Economy | Damage die of a forged weapon (1–N) |
| weapon_protection_base | silah_koruma | 5 | 0 | 100 | Economy | Base protection of a forged weapon |
| weapon_protection_die | silah_koruma_zar | 15 | 1 | 100 | Economy | Protection die of a forged weapon (1–N) |
| weapon_might_base | silah_kudret | 5 | 0 | 100 | Economy | Base might of a forged weapon |
| weapon_might_die | silah_kudret_zar | 10 | 1 | 100 | Economy | Might die of a forged weapon (1–N) |
| bankruptcy_merchant_pct | iflas_tuccar | 12 | 0 | 100 | Economy | Merchant share required for bankruptcy (%) |
| bankruptcy_prosperity | iflas_refah | 35 | 0 | 100 | Economy | Below this prosperity a guild may go bankrupt |
| bankruptcy_cap | iflas_tavan | 1 | 0 | 100 | Economy | Maximum guild bankruptcies per epoch |
| bankruptcy_satisfaction_loss | iflas_memnuniyet | 20 | 0 | 100 | Economy | Merchant satisfaction reduced by bankruptcy |
| bankruptcy_share_loss | iflas_pay | 4 | 0 | 100 | Economy | Merchant share reduced by bankruptcy |
| bankruptcy_prosperity_loss | iflas_refah_kayip | 5 | 0 | 100 | Economy | Prosperity reduced by bankruptcy |
| revolt_min_class_pct | ayaklanma_sinif_pay | 5 | 0 | 100 | War and diplomacy | Minimum share of a class that can revolt (%) |
| revolt_satisfaction | ayaklanma_memnuniyet | 22 | 0 | 100 | War and diplomacy | A class below this satisfaction may revolt |
| revolt_min_population | ayaklanma_nufus | 800 | 0 | 10,000,000 | War and diplomacy | Population required for a class revolt |
| revolt_cap | ayaklanma_tavan | 1 | 0 | 100 | War and diplomacy | Maximum class revolts per epoch |
| revolt_faction_power | ayaklanma_guc | 3 | 1 | 12 | War and diplomacy | Power level of the revolt faction |
| revolt_faction_strength | ayaklanma_hizip_guc | 25 | 0 | 100 | War and diplomacy | Base strength of the revolt faction |
| revolt_faction_strength_die | ayaklanma_hizip_guc_zar | 30 | 1 | 100 | War and diplomacy | Strength die of the revolt faction (1–N) |
| revolt_faction_wealth | ayaklanma_servet | 5 | 0 | 100 | War and diplomacy | Base wealth of the revolt faction |
| revolt_faction_wealth_die | ayaklanma_servet_zar | 15 | 1 | 100 | War and diplomacy | Wealth die of the revolt faction (1–N) |
| revolt_faction_sway | ayaklanma_nufuz | 20 | 0 | 100 | War and diplomacy | Base sway of the revolt faction |
| revolt_faction_sway_die | ayaklanma_nufuz_zar | 30 | 1 | 100 | War and diplomacy | Sway die of the revolt faction (1–N) |
| revolt_relief | ayaklanma_rahatlama | 15 | 0 | 100 | War and diplomacy | Satisfaction gain of the revolting class |
| trade_min_stock_diff | ticaret_fark | 20 | 0 | 1000 | Economy | Minimum stock difference for a trade route to carry goods |
| trade_flow_divisor | ticaret_akis_bolen | 4 | 1 | 100 | Economy | Trade flow: stock difference / this number |
| trade_seller_prosperity | ticaret_satan_refah | 1 | 0 | 100 | Economy | Seller's prosperity gain per trade |

### DEEP_WARFARE

Old namespace `DERIN_SEFER` · 100 rows · defined in `src/derin.js`. Armies, battles, sieges, duels, captives, ransoms, tribute.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| cult_soldier_pct | tarikat_asker | 15 | 0 | 100 | War and diplomacy | Share of followers joining a cult army (%) |
| faction_soldiers_per_strength | hizip_asker_guc | 60 | 0 | 10,000 | War and diplomacy | Faction army: soldiers per military-strength point |
| faction_soldiers_per_wealth | hizip_asker_servet | 20 | 0 | 10,000 | War and diplomacy | Faction army: soldiers per wealth point |
| faction_default_strength | hizip_guc_varsayilan | 30 | 0 | 100 | War and diplomacy | Strength assumed for a faction with unknown strength |
| faction_default_wealth | hizip_servet_varsayilan | 20 | 0 | 100 | War and diplomacy | Wealth assumed for a faction with unknown wealth |
| cult_default_followers | murit_varsayilan | 100 | 0 | 1,000,000 | War and diplomacy | Followers assumed in the army calculation for a cult with unknown followers |
| default_population | nufus_varsayilan | 1000 | 0 | 10,000,000 | War and diplomacy | Population assumed in the army calculation for a people or city with unknown population |
| default_zealotry | bagnazlik_varsayilan | 50 | 0 | 100 | War and diplomacy | Zealotry assumed in the holy guard's morale for a cult with unknown zealotry |
| min_soldier_pct | asker_en_az_pay | 4 | 0 | 100 | War and diplomacy | Minimum share of population in a people's or city's army (%) |
| army_power_min | ordu_guc_alt | 2 | 1 | 12 | War and diplomacy | Minimum power level of an army |
| army_power_max | ordu_guc_ust | 8 | 1 | 12 | War and diplomacy | Maximum power level of an army |
| army_min_soldiers | ordu_en_az | 30 | 1 | 100,000 | War and diplomacy | Minimum soldiers in an army |
| army_morale_base | ordu_moral_taban | 55 | 0 | 100 | War and diplomacy | Base morale of a new army |
| army_morale_die | ordu_moral_zar | 25 | 1 | 100 | War and diplomacy | Die added to a new army's morale (1–N) |
| holy_guard_zealotry_divisor | ordu_moral_bagnaz_bolen | 5 | 1 | 100 | War and diplomacy | Holy guard morale: zealotry / this number |
| army_equipment_base | ordu_techizat_taban | 20 | 0 | 100 | War and diplomacy | Base equipment of a new army |
| army_equipment_weapon_mult | ordu_techizat_silah | 2 | 0 | 20 | War and diplomacy | Multiplier of weapon strength on equipment |
| army_equipment_metallurgy | ordu_techizat_metalurji | 15 | 0 | 100 | War and diplomacy | Equipment bonus for those who know metallurgy |
| army_experience_warcraft | ordu_deneyim_savas | 30 | 0 | 100 | War and diplomacy | Initial experience of an army that knows the art of war |
| army_experience | ordu_deneyim | 10 | 0 | 100 | War and diplomacy | Initial experience of a new army |
| war_event_initial_power | savas_olay_guc | 4 | 1 | 12 | War and diplomacy | Initial power level of a war record |
| war_initial_severity | savas_siddet_ilk | 30 | 0 | 100 | War and diplomacy | Initial severity of a war |
| siege_min_defense | kusatma_savunma | 55 | 0 | 100 | War and diplomacy | Minimum defense of a settlement that undergoes a siege |
| strength_community_share_pct | guc_toplum_pay | 60 | 0 | 500 | War and diplomacy | Share of the community's military strength entering battle strength (%) |
| strength_size_log_mult | guc_buyukluk | 14 | 0 | 200 | War and diplomacy | Battle strength: multiplier of the logarithm of soldier count |
| strength_morale_divisor | guc_moral_bolen | 3 | 1 | 100 | War and diplomacy | Battle strength: morale / this number |
| strength_equipment_divisor | guc_techizat_bolen | 4 | 1 | 100 | War and diplomacy | Battle strength: equipment / this number |
| strength_experience_divisor | guc_deneyim_bolen | 5 | 1 | 100 | War and diplomacy | Battle strength: experience / this number |
| strength_commander_divisor | guc_komutan_bolen | 12 | 1 | 100 | War and diplomacy | Battle strength: commander's strength+intellect+charisma / this number |
| battle_die | muharebe_zar | 20 | 1 | 200 | War and diplomacy | Battle luck die (1–N) |
| battle_die_mult | muharebe_zar_carpan | 2 | 0 | 20 | War and diplomacy | Multiplier of the battle luck die |
| severity_per_battle | siddet_artis | 8 | 0 | 100 | War and diplomacy | War severity increase per battle |
| severity_diff_divisor | siddet_fark_bolen | 10 | 1 | 1000 | War and diplomacy | Contribution of strength difference to severity: difference / this number |
| war_power_min | savas_guc_alt | 2 | 1 | 12 | War and diplomacy | Minimum power level of a war record |
| war_power_max | savas_guc_ust | 9 | 1 | 12 | War and diplomacy | Maximum power level of a war record |
| war_power_battle_interval | savas_guc_aralik | 2 | 1 | 100 | War and diplomacy | The war record's power level rises once every this many battles |
| war_power_step | savas_guc_artis | 1 | 0 | 12 | War and diplomacy | Power-level increase of the war record at that battle |
| breach_diff_divisor | yarma_fark_bolen | 60 | 1 | 1000 | War and diplomacy | Chance to breach walls: strength difference / this number |
| breach_starving_supplies | yarma_ac_erzak | 15 | 0 | 200 | War and diplomacy | A besieged city with supplies below this counts as starving |
| breach_starving_bonus_pct | yarma_ac_ek | 35 | 0 | 100 | War and diplomacy | Bonus to the chance of breaching a starving city's walls (%) |
| breach_min_pct | yarma_alt | 10 | 0 | 100 | War and diplomacy | Floor of the wall-breach chance (%) |
| breach_max_pct | yarma_ust | 85 | 0 | 100 | War and diplomacy | Cap of the wall-breach chance (%) |
| siege_repelled_morale_loss | kusatma_puskurtme_moral | 6 | 0 | 100 | War and diplomacy | Attacker's morale loss when a siege is repelled |
| breach_defense_loss | sur_yarma_savunma | 25 | 0 | 100 | War and diplomacy | City's defense loss when its walls are breached |
| breach_war_score | kusatma_skor | 3 | 0 | 20 | War and diplomacy | Contribution of breaching walls to the war score |
| siege_population_kept_pct | kusatma_nufus_kalan | 94 | 0 | 100 | War and diplomacy | Population remaining in the city during a siege (%) |
| siege_prosperity_loss | kusatma_refah | 6 | 0 | 100 | War and diplomacy | Prosperity removed from the city by a siege |
| siege_supply_loss | kusatma_erzak | 20 | 0 | 200 | War and diplomacy | Supplies removed from the city's granary by a siege |
| siege_attacker_morale_loss | kusatma_moral | 4 | 0 | 100 | War and diplomacy | Attacker's morale loss in an ongoing siege |
| siege_default_supplies | kusatma_erzak_varsayilan | 50 | 0 | 100,000 | War and diplomacy | Supplies assumed for a besieged city with no granary record |
| siege_default_population | kusatma_nufus_varsayilan | 100 | 0 | 10,000,000 | War and diplomacy | Population assumed for a besieged city with no population record |
| great_victory_diff | buyuk_zafer_fark | 35 | 0 | 1000 | War and diplomacy | Strength difference counted as a great victory |
| great_victory_score | buyuk_zafer_skor | 2 | 0 | 20 | War and diplomacy | Contribution of a great victory to the war score |
| loser_base_loss_pct | maglup_kayip | 12 | 0 | 100 | War and diplomacy | Base loss of the defeated army (%) |
| loser_extra_loss_max_pct | maglup_kayip_ek | 30 | 0 | 100 | War and diplomacy | Maximum extra loss of the defeated army from strength difference (%) |
| loser_extra_loss_divisor | maglup_kayip_bolen | 220 | 1 | 100,000 | War and diplomacy | Defeated extra loss: strength difference / this number |
| winner_base_loss_pct | galip_kayip | 4 | 0 | 100 | War and diplomacy | Base loss of the victorious army (%) |
| winner_extra_loss_max_pct | galip_kayip_ek | 10 | 0 | 100 | War and diplomacy | Maximum extra loss of the victorious army from strength difference (%) |
| winner_extra_loss_divisor | galip_kayip_bolen | 600 | 1 | 100,000 | War and diplomacy | Victor extra loss: strength difference / this number |
| loser_morale_loss | maglup_moral | 10 | 0 | 100 | War and diplomacy | Morale loss of the defeated army |
| loser_morale_diff_divisor | maglup_moral_bolen | 8 | 1 | 1000 | War and diplomacy | Defeated extra morale loss: strength difference / this number |
| winner_morale_gain | galip_moral | 4 | 0 | 100 | War and diplomacy | Morale gain of the victorious army |
| winner_experience_gain | galip_deneyim | 6 | 0 | 100 | War and diplomacy | Experience gain of the victorious army |
| loser_experience_gain | maglup_deneyim | 3 | 0 | 100 | War and diplomacy | Experience gain of the defeated army |
| community_loss_divisor | topluluk_kayip_bolen | 5 | 1 | 100 | War and diplomacy | Defeated community's population loss: army loss / this number |
| loser_prosperity_loss | maglup_refah | 5 | 0 | 100 | War and diplomacy | Prosperity and wealth loss of the defeated community |
| winner_wealth_gain | galip_servet | 3 | 0 | 100 | War and diplomacy | Wealth gain of the victorious community |
| battle_relation | muharebe_iliski | 8 | 0 | 100 | War and diplomacy | Relation reduced by a battle (points) |
| patron_renown_per_battle | hami_un | 2 | 0 | 50 | War and diplomacy | Renown per battle of the victor's patron god |
| patron_xp_per_battle | hami_xp | 8 | 0 | 100 | War and diplomacy | XP per battle of the victor's patron god |
| patron_relation_loss | hami_iliski | 5 | 0 | 100 | War and diplomacy | Relation between the two patron gods reduced by a battle |
| battle_event_power_divisor | muharebe_olay_guc_bolen | 20 | 1 | 1000 | War and diplomacy | Battle record power: strength difference / this number |
| battle_event_power_min | muharebe_olay_guc_alt | 2 | 1 | 12 | War and diplomacy | Minimum power level of a battle record |
| battle_event_power_max | muharebe_olay_guc_ust | 7 | 1 | 12 | War and diplomacy | Maximum power level of a battle record |
| battle_event_severity_base | muharebe_siddet_taban | 30 | 0 | 100 | War and diplomacy | Base severity of a battle record |
| duel_agility_divisor | duello_ceviklik_bolen | 2 | 1 | 100 | Heroes and mortals | Duel strength: agility / this number |
| duel_weapon_mult | duello_silah | 2 | 0 | 20 | Heroes and mortals | Multiplier of weapon strength in a duel |
| duel_die | duello_zar | 20 | 1 | 200 | Heroes and mortals | Duel luck die (1–N) |
| duel_die_mult | duello_zar_carpan | 2 | 0 | 20 | Heroes and mortals | Multiplier of the duel luck die |
| duel_winner_charisma | duello_karizma | 6 | 0 | 100 | Heroes and mortals | Charisma gain of the duel winner |
| duel_loser_hp_loss | duello_yara | 40 | 0 | 1000 | Heroes and mortals | HP loss of the duel loser |
| hero_default_hp | can_varsayilan | 100 | 1 | 100,000 | Heroes and mortals | HP assumed when wounding a hero with no HP record |
| disband_morale | dagilma_moral | 12 | 0 | 100 | War and diplomacy | An army below this morale disbands |
| disband_soldiers | dagilma_asker | 30 | 0 | 100,000 | War and diplomacy | An army below this many soldiers disbands |
| decisive_score | zafer_skor | 3 | 1 | 50 | War and diplomacy | Decisive score that ends the war |
| exhaustion_min_battles | yorgunluk_muharebe | 4 | 1 | 100 | War and diplomacy | Number of battles at which exhaustion peace becomes possible |
| conquest_relation | fetih_iliski | 25 | 0 | 200 | War and diplomacy | Relation reduced by conquest (points) |
| tribute_relation | harac_iliski | 10 | 0 | 200 | War and diplomacy | Relation reduced by being bound to tribute (points) |
| white_peace_relation | beyaz_baris_iliski | 8 | 0 | 100 | War and diplomacy | Relation bonus of a white peace (points) |
| tribute_end_relation | harac_bitti_iliski | 5 | 0 | 100 | War and diplomacy | Relation bonus when tribute ends (points) |
| tribute_revolt_relation | harac_isyan_iliski | 15 | 0 | 200 | War and diplomacy | Relation reduced by a tribute revolt (points) |
| ransom_min_wealth | fidye_servet | 30 | 0 | 100 | Heroes and mortals | Minimum wealth of a homeland able to pay ransom |
| ransom_min_prosperity | fidye_refah | 50 | 0 | 100 | Heroes and mortals | Minimum prosperity of a homeland able to pay ransom |
| ransom_cost | fidye_bedel | 12 | 0 | 100 | Heroes and mortals | Wealth and prosperity cost of a ransom |
| ransom_relation | fidye_iliski | 5 | 0 | 100 | Heroes and mortals | Relation bonus of a ransom (points) |
| escape_agility_divisor | kacis_ceviklik_bolen | 250 | 1 | 100,000 | Heroes and mortals | Captive's escape chance: agility / this number |
| escape_intellect_divisor | kacis_akil_bolen | 400 | 1 | 100,000 | Heroes and mortals | Captive's escape chance: intellect / this number |
| captive_default_stat | esir_stat_varsayilan | 30 | 0 | 100 | Heroes and mortals | Value assumed for a captive with unknown agility or intellect |
| execution_relation | idam_iliski | 70 | 0 | 100 | Heroes and mortals | Below this hostility (negative points) the captive may be executed |
| captive_defection_epochs | esir_donme_cag | 3 | 0 | 100 | Heroes and mortals | Captivity duration after which the captive may switch sides (epochs) |

### DEEP_WORLD

Old namespace `DERIN` · 125 rows · defined in `src/derin.js` · also read by `src/yaratici.js`. Deep simulation: diplomacy, wars, notable mortals, religion, culture, dark/golden ages.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| battle_record_min_diff | muharebe_kayit_fark | 30 | 0 | 1000 | War and diplomacy | Strength difference required for a separate battle record (sieges are always recorded) |
| spy_net_enemy_bonus_pct | casus_ag_dusman_ek | 20 | 0 | 100 | War and diplomacy | Bonus to setting up a spy network against an enemy or a tribute counterpart (%) |
| grudge_threshold | kin_esik | -60 | -100 | 0 | War and diplomacy | Neighbours below this relation may declare war |
| peace_threshold | baris_esik | -15 | -100 | 100 | War and diplomacy | Enemies above this relation may make peace |
| alliance_threshold | ittifak_esik | 55 | 0 | 100 | War and diplomacy | Neighbours above this relation may become allies |
| declarations_cap | ilan_tavan | 2 | 0 | 20 | War and diplomacy | Maximum war declarations per epoch |
| peace_cap | baris_tavan | 3 | 0 | 20 | War and diplomacy | Maximum neighbour peaces per epoch (by oath or truce) |
| exhaustion_peace_cap | yorgunluk_baris_tavan | 3 | 0 | 20 | War and diplomacy | Maximum exhaustion peaces per epoch (long wars; counted separately from neighbour peace) |
| grudge_fade_relation | kin_sonme_iliski | 0 | -100 | 100 | War and diplomacy | Fading grudge: community hostility closes when relation has risen to this or above and there is no ongoing war |
| grudge_fade_min_age | kin_sonme_cag | 3 | 0 | 100 | War and diplomacy | Fading grudge: minimum age of the hostility (epochs) |
| grudge_forget_epochs | kin_unutma_cag | 12 | 0 | 1000 | War and diplomacy | Forgotten grudge: hostility lasting this many epochs without ever clashing (no ongoing war) closes even if the relation is bad (0: off) |
| grudge_fade_cap | kin_sonme_tavan | 6 | 0 | 1000 | War and diplomacy | Maximum fading grudges per epoch |
| grudge_pool_pct | kin_havuz | 300 | 100 | 10,000 | War and diplomacy | Grudge pool: when community hostilities (pair count) exceed this percentage of the world's war cap, old grudges lock diplomacy; the excess enlarges the fading-grudge cap |
| grudge_overflow_share_pct | kin_asim_pay | 25 | 0 | 1000 | War and diplomacy | Share of hostility pairs exceeding the grudge pool added to the per-epoch fading-grudge cap (%) |
| truce_without_war | savassiz_ateskes | 0 | 0 | 1 | War and diplomacy | When the hostility of two communities that never fought closes (grudge faded, forgotten, peace), is a truce recorded (1: yes, 0: no; pairs that fought always enter a truce) |
| mortal_grudge_forget_epochs | olumlu_kin_unutma_cag | 8 | 0 | 1000 | War and diplomacy | A mortal's hostility (with a mortal or a community): hostility lasting this many epochs without any new encounter is forgotten (0: off) |
| alliance_cap | ittifak_tavan | 2 | 0 | 20 | War and diplomacy | Maximum alliances per epoch |
| community_war_cap | topluluk_savas_tavan | 2 | 0 | 10 | War and diplomacy | Maximum simultaneous ongoing wars of one community (war event) |
| battle_cap | muharebe_tavan | 6 | 0 | 50 | War and diplomacy | Maximum battles per epoch (in ongoing wars; a new war's first clash counts against new_war_cap) |
| mobilization | seferberlik | 1 | 0 | 1 | War and diplomacy | A new war's first epoch is mobilization: armies gather, first clash the next epoch (1: on, 0: clash in the epoch of declaration) |
| new_war_cap | yeni_savas_tavan | 3 | 0 | 50 | War and diplomacy | Maximum new wars per epoch (from enemy pairs; only below the war caps) |
| battle_chance | muharebe_sans | 70 | 0 | 100 | War and diplomacy | Enemies clash this epoch (%) |
| battle_chance_war_ban | muharebe_yasak_sans | 35 | 0 | 100 | War and diplomacy | Clash while a war ban is in effect (%) |
| notable_min_population | unlu_nufus | 800 | 0 | 1,000,000 | Heroes and mortals | Minimum population of a community producing a notable mortal |
| notable_chance | unlu_sans | 45 | 0 | 100 | Heroes and mortals | A notable mortal arises from a populous community (base %) |
| notable_cap | unlu_tavan | 8 | 0 | 100 | Heroes and mortals | Maximum notable mortals born per epoch |
| ruler_cap | hukumdar_tavan | 2 | 0 | 50 | Heroes and mortals | Maximum rulers taking the throne per epoch |
| ruler_min_population | hukumdar_nufus | 800 | 0 | 1,000,000 | Heroes and mortals | Minimum population of a community acquiring a ruler |
| ethnogenesis_min_population | etnogenez_nufus | 3000 | 0 | 10,000,000 | Population and growth | Minimum population of a settlement turning into a new people |
| ethnogenesis_min_age | etnogenez_cag | 3 | 0 | 100 | Population and growth | Age required to turn into a new people (epochs) |
| world_war_cap | savas_tavan | 6 | 0 | 50 | War and diplomacy | Maximum simultaneous ongoing community wars in the world (war event; hostility links fade separately) |
| truce_epochs | ateskes_cag | 3 | 0 | 20 | War and diplomacy | Truce duration after peace (epochs) |
| tribute_epochs | harac_cag | 4 | 1 | 30 | War and diplomacy | Tribute duration (epochs) |
| tribute_flow | harac_akis | 2 | 0 | 20 | War and diplomacy | Prosperity and wealth transferred per epoch by tribute |
| tribute_goods_pct | harac_mal | 15 | 0 | 100 | War and diplomacy | Share of goods transferred by tribute (%) |
| tribute_revolt_strength_pct | harac_isyan_guc | 125 | 100 | 500 | War and diplomacy | Strength ratio required for a tributary to rebel (%) |
| conquest_conversion_chance | fetih_din_sans | 45 | 0 | 100 | Religion and language | On conquest the defeated converts to the victor's god (%) |
| tribute_conversion_chance | harac_din_sans | 20 | 0 | 100 | Religion and language | Under tribute the defeated converts to the victor's god (%) |
| spirits_per_place_cap | ruh_tavan | 3 | 0 | 30 | The Beyond | Maximum spirits roaming in one place |
| spirit_unrest_decay | ruh_sonme | 3 | 0 | 50 | The Beyond | Spirit's unrest decay per epoch |
| spirit_rest_threshold | ruh_dinme_esik | 40 | 0 | 100 | The Beyond | A spirit with unrest below this may come to rest |
| cult_population_share_pct | tarikat_oran | 30 | 1 | 100 | Population and growth | Cap on cult followers: percentage of the region's population |
| young_world_epochs | genc_dunya | 6 | 0 | 50 | Cosmic horror | Young world duration (epochs; leakage growth is halved) |
| hero_top_percentile | kahraman_yuzde | 80 | 0 | 100 | Heroes and mortals | Slice of communities producing heroes (top X% most populous in the world) |
| dark_age_prosperity | karanlik_refah | 12 | 0 | 100 | Civilization | Prosperity below this counts as ruin (dark age) |
| dark_age_forget_chance | karanlik_sans | 30 | 0 | 100 | Civilization | Knowledge forgotten after ruin (%) |
| dark_age_forget_protected_chance | karanlik_korunan_sans | 5 | 0 | 100 | Civilization | Forgetting when there are scribes or a library (%) |
| exhaustion_start_epoch | yorgunluk_bas | 3 | 1 | 30 | War and diplomacy | Epoch of a long war at which exhaustion peace begins |
| exhaustion_growth_pct | yorgunluk_artis | 10 | 0 | 100 | War and diplomacy | Per-epoch increase of the exhaustion-peace chance (%) |
| exhaustion_cap_pct | yorgunluk_tavan | 50 | 0 | 100 | War and diplomacy | Cap of the exhaustion-peace chance (%) |
| exhaustion_victory_margin | yorgunluk_ustunluk | 2 | 1 | 50 | War and diplomacy | Minimum score advantage to count as the victor in an exhaustion peace (below it, white peace) |
| first_village_population | koy_ilk_nufus | 600 | 50 | 100,000 | Population and growth | Population at which a people founds its first homeland |
| extra_village_population | koy_ek_nufus | 1500 | 100 | 1,000,000 | Population and growth | Population at which a people founds an additional village |
| village_min_population | koy_en_az | 150 | 10 | 10,000 | Population and growth | Minimum population of a new village |
| village_people_remainder | koy_kalan | 300 | 10 | 100,000 | Population and growth | Minimum population remaining in the people after founding a village |
| people_per_village | koy_basina | 15,000 | 1000 | 1,000,000 | Population and growth | One village per this many people in the region |
| ruin_population_threshold | harabe_esik | 60 | 0 | 10,000 | Population and growth | A settlement below this population is abandoned |
| ruin_grace_epochs | harabe_mehil | 2 | 0 | 20 | Population and growth | Epochs a new settlement takes root without being abandoned |
| fertility_recovery_divisor | bereket_toparlanma | 8 | 1 | 100 | Population and growth | Rate at which depleted land returns to 50 (divisor) |
| fertility_decline_divisor | bereket_inis | 10 | 1 | 200 | Population and growth | Rate at which fertile land declines to 50 (divisor; balanced by climate push: ~60 in temperate age, ~90 in rain age) |
| structure_cap | yapit_tavan | 2 | 0 | 20 | Civilization | Maximum structures the engine builds per epoch |
| structure_min_prosperity | yapit_refah | 50 | 0 | 100 | Civilization | Prosperity required to build a structure |
| splendor_gain | ihtisam_artis | 2 | 0 | 50 | Civilization | Splendor per epoch to the structure of a prosperous owner |
| faction_cap | hizip_tavan | 1 | 0 | 10 | Civilization | Maximum factions founded spontaneously per epoch |
| conversion_cap | din_gecis_tavan | 1 | 0 | 10 | Religion and language | Maximum communities changing religion per epoch |
| seeker_pull_chance | arayan_cekim | 12 | 0 | 100 | Religion and language | A god-seeking community converts to its neighbour's god (%) |
| conversion_chance_cap | din_sans_tavan | 30 | 0 | 100 | Religion and language | Cap of a religious conversion chance (%) |
| dominant_god_threshold_pct | din_baskin_esik | 30 | 0 | 100 | Religion and language | Dominant god: if more than this percentage of worshipping communities are with one god, the chance of converting to it decreases as its share grows (reaching zero as its share approaches 100%) |
| culture_exchange_cap | kultur_tavan | 2 | 0 | 20 | Religion and language | Maximum cultural exchanges per epoch |
| golden_age_prosperity | altin_refah | 50 | 0 | 100 | Apocalypse | Average prosperity required for a golden age |
| golden_age_peace_epochs | altin_baris | 4 | 0 | 50 | Apocalypse | Epochs that must pass without war for a golden age |
| era_turn_interval | cag_donumu | 10 | 1 | 1000 | Apocalypse | Era turning every this many epochs |
| era_turn_apocalypse_push | cag_donumu_kiyamet | 5 | 0 | 100 | Apocalypse | Apocalypse push-back at an era turning |
| world_age_step | dunya_yasi_adim | 25 | 1 | 1000 | Apocalypse | World aging threshold (epochs) |
| refugee_share_pct | multeci_pay | 8 | 0 | 100 | Population and growth | Population share of refugees (%) |
| famine_migration_share_pct | kitlik_goc_pay | 15 | 0 | 100 | Population and growth | Population share of famine migration (%) |
| war_declaration_chance | savas_ilan_sans | 25 | 0 | 100 | War and diplomacy | A grudge turns into a war declaration (%) |
| peace_chance | baris_sans | 30 | 0 | 100 | War and diplomacy | A softening relation turns into peace (%) |
| alliance_chance | ittifak_sans | 20 | 0 | 100 | War and diplomacy | Friendly neighbours become allies (%) |
| marriage_alliance_share_pct | evlilik_ittifak_sans | 40 | 0 | 100 | War and diplomacy | Share of alliances made through marriage (%) |
| betrayal_chance | ihanet_sans | 30 | 0 | 100 | War and diplomacy | Betrayal in a breaking alliance (%) |
| betrayal_war_chance | ihanet_savas_sans | 50 | 0 | 100 | War and diplomacy | Betrayal turns into war (%) |
| duel_chance | duello_sans | 30 | 0 | 100 | War and diplomacy | Heroes engage in a duel during a battle (%) |
| duel_death_chance | duello_olum_sans | 45 | 0 | 100 | War and diplomacy | A duel ends in death (%) |
| capture_chance | esir_sans | 20 | 0 | 100 | War and diplomacy | A hero of the defeated side is captured (%) |
| four_battle_exhaustion_chance | savas_yorgunluk_sans | 25 | 0 | 100 | War and diplomacy | Exhaustion peace after four battles (%) |
| conquest_syncretism_pct | senkretizm_fetih | 35 | 0 | 100 | Religion and language | Share of conquest conversions that are syncretic (%) |
| tribute_revolt_chance | harac_isyan_sans | 40 | 0 | 100 | War and diplomacy | A strengthened tributary rebels (%) |
| ransom_chance | fidye_sans | 40 | 0 | 100 | War and diplomacy | A wealthy homeland pays ransom (%) |
| execution_chance | idam_sans | 25 | 0 | 100 | War and diplomacy | A blood enemy executes the captive (%) |
| captive_defection_chance | esir_donme_sans | 30 | 0 | 100 | War and diplomacy | Switching sides after long captivity (%) |
| forge_weapon_chance | silah_uretim_sans | 20 | 0 | 100 | Economy | A forge forges a weapon (%) |
| guild_bankruptcy_chance | lonca_iflas_sans | 18 | 0 | 100 | Economy | A merchant guild goes bankrupt (%) |
| class_revolt_chance | sinif_ayaklanma_sans | 22 | 0 | 100 | War and diplomacy | A discontented class revolts (%) |
| quest_chance | gorev_sans | 35 | 0 | 100 | Heroes and mortals | A hero sets out on a new quest (%) |
| companion_chance | yoldas_sans | 10 | 0 | 100 | Heroes and mortals | Two heroes of the same side become companions (%) |
| apprentice_chance | cirak_sans | 30 | 0 | 100 | Heroes and mortals | An aging hero trains an apprentice (%) |
| weapon_bequest_chance | silah_emanet_sans | 50 | 0 | 100 | Heroes and mortals | A master hands their weapon to their apprentice (%) |
| quest_death_chance | gorev_olum_sans | 25 | 0 | 100 | Heroes and mortals | Death on a failed quest (%) |
| relic_decipher_chance | kalinti_bulma_sans | 12 | 0 | 100 | Heroes and mortals | Scribes decipher lost knowledge from remnants (%) |
| spy_net_chance | casus_ag_sans | 20 | 0 | 100 | War and diplomacy | An influential faction sets up a spy network (%) |
| spy_war_chance | casus_savas_sans | 30 | 0 | 100 | War and diplomacy | Captured spies lead to war (%) |
| spy_action_chance | casus_eylem_sans | 40 | 0 | 100 | War and diplomacy | The spy network acts this epoch (%) |
| spy_steal_knowledge_pct | casus_bilgi_sans | 50 | 0 | 100 | War and diplomacy | Share of spy actions that steal knowledge (otherwise sabotage) (%) |
| wonder_envy_war_chance | harika_kiskanc_sans | 5 | 0 | 100 | War and diplomacy | A jealous neighbour goes to war over a wonder (%) |
| apostasy_chance | inkar_sans | 50 | 0 | 100 | Religion and language | A worshipper of a dead god falls into denial (%) |
| cult_resurrection_chance | dirilis_sans | 50 | 0 | 100 | Religion and language | A devoted cult resurrects its god (%) |
| ruler_chance | hukumdar_sans | 50 | 0 | 100 | Heroes and mortals | A ruler takes over a leaderless community (%) |
| ethnogenesis_chance | etnogenez_sans | 20 | 0 | 100 | Population and growth | An isolated settlement turns into a new people (%) |
| sapience_chance | akillanma_sans | 12 | 0 | 100 | Population and growth | An intelligent species turns into a people (%) |
| script_chance | yazi_sans | 50 | 0 | 100 | Religion and language | A language whose speakers know writing gains a script (%) |
| manifestation_chance | tezahur_sans | 10 | 0 | 100 | Religion and language | A widespread legend becomes real (%) |
| legendization_chance | efsanelesme_sans | 25 | 0 | 100 | Religion and language | An old violent event turns into a legend (%) |
| fairy_tale_chance | masal_sans | 15 | 0 | 100 | Religion and language | An old legend turns into a fairy tale (%) |
| native_people_chance | yerli_halk_sans | 20 | 0 | 100 | Population and growth | A native people appears on a world without a people (%) |
| native_species_chance | yerli_tur_sans | 25 | 0 | 100 | Population and growth | A living species appears on a world without species (%) |
| new_people_worship_creator_chance | yaratici_ilk_inanc | 50 | 0 | 100 | Religion and language | A new godless people worships the Creator (otherwise seeks a god) (%) |
| refugee_chance | multeci_sans | 40 | 0 | 100 | Population and growth | Refugee migration after war or disaster (%) |
| spirit_rest_chance | ruh_dinme_sans | 30 | 0 | 100 | The Beyond | A calm spirit comes to rest (%) |
| spirit_passage_chance | ruh_gecis_sans | 12 | 0 | 100 | The Beyond | A spirit passes to the land of the dead (%) |
| structure_chance | yapit_sans | 25 | 0 | 100 | Civilization | A prosperous city builds a structure (%) |
| revolt_disband_chance | isyan_dagilma_sans | 50 | 0 | 100 | War and diplomacy | An uprising whose war ended disbands (%) |
| faction_chance | hizip_sans | 15 | 0 | 100 | Civilization | A faction is founded within a community (%) |
| syncretism_pct | senkretizm_sans | 40 | 0 | 100 | Religion and language | Share of religious conversions that are syncretic (%) |
| culture_exchange_chance | kultur_sans | 12 | 0 | 100 | Religion and language | Cultural exchange along a trade route (%) |

### ECONOMY

Old namespace `EKONOMI` · 47 rows · defined in `src/ekonomi.js`. Strange resource mechanics, cosmic markets, void pirates, cosmic deposits.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| depletion_apocalypse | tukenme_kiyamet | 6 | 0 | 100 | Apocalypse | Contribution of a depleted costly resource to the apocalypse |
| cosmic_deposit_chance | yatak_sans | 6 | 0 | 100 | Economy | A people finds a cosmic resource deposit (% per epoch) |
| sentient_resource_choose_chance | bilincli_kaynak_sans | 35 | 0 | 100 | Economy | A sentient resource chooses its owner (%) |
| sentient_resource_keep_chance | bilincli_kaynak_kabul | 60 | 0 | 100 | Economy | A wealthy owner keeps the resource (%) |
| sacred_resource_curse_chance | ekonomi_olay1 | 30 | 0 | 100 | Economy | The resource's god curses its foreign owner (%) |
| withdrawal_recovery_chance | ekonomi_olay2 | 30 | 0 | 100 | Economy | One suffering withdrawal recovers from addiction (%) |
| market_found_chance | pazar_sans | 25 | 0 | 100 | Economy | A cosmic market is founded (%) |
| market_move_chance | pazar_goc_sans | 60 | 0 | 100 | Economy | The market moves to another region (%) |
| market_trade_chance | pazar_ticaret_sans | 20 | 0 | 100 | Economy | The market forms new trade links (%) |
| pirate_chance | korsan_sans | 30 | 0 | 100 | Economy | Pirates spawn on a busy route (%) |
| decay_loss | bozunma | 8 | 0 | 100 | Economy | Per-epoch abundance loss of a decaying resource |
| fixed_regen_clawback | sabit_kayip | 4 | 0 | 100 | Economy | Per-epoch regeneration clawed back from a fixed-quantity resource |
| addiction_epochs | bagimlilik_cag | 2 | 0 | 100 | Economy | Epochs of owning the resource needed to become addicted |
| addiction_immunity_epochs | bagimlilik_bagisiklik | 6 | 0 | 1000 | Economy | Epochs during which a community that recovered from addiction cannot become addicted to the same resource again |
| sentient_owner_prosperity | bilincli_zengin | 45 | 0 | 100 | Economy | Prosperity of an owner able to meet a sentient resource's demand |
| sentient_owner_default | bilincli_varsayilan | 40 | 0 | 100 | Economy | Prosperity assumed for an owner with unknown prosperity and wealth |
| sentient_demand_cost | bilincli_bedel | 8 | 0 | 100 | Economy | Prosperity and wealth cost of a sentient resource's demand |
| sacred_wrath | kutsal_ofke | 5 | 0 | 100 | Economy | God's wrath gain when a foreigner mines a sacred resource |
| withdrawal_min_abundance | yoksunluk_bolluk | 10 | 0 | 100 | Economy | Minimum resource abundance an addict can make do with |
| withdrawal_loss | yoksunluk_kayip | 8 | 0 | 100 | Economy | Prosperity, defense, strength and faith loss in withdrawal |
| withdrawal_population_kept_pct | yoksunluk_nufus | 95 | 0 | 100 | Economy | Share of population kept in withdrawal (%) |
| fold_abundance_cost | katlama_bedel | 12 | 0 | 100 | Cosmos and travel | Cosmic resource abundance spent by space folding |
| fold_addiction_count | katlama_bagimlilik | 2 | 1 | 100 | Cosmos and travel | Addiction to the resource after this many space folds |
| monopoly_gain | tekel_kazanc | 3 | 0 | 100 | Economy | Per-epoch wealth, prosperity and sway gain of a cosmic monopoly |
| traffic_window_epochs | trafik_cag | 3 | 0 | 100 | Economy | Number of recent epochs counted for route traffic |
| market_power | pazar_guc_seviye | 4 | 1 | 12 | Economy | Power level of a wandering market |
| market_strength | pazar_guc | 20 | 0 | 100 | Economy | Strength of a wandering market |
| market_wealth | pazar_servet | 70 | 0 | 100 | Economy | Wealth of a wandering market |
| market_sway | pazar_nufuz | 55 | 0 | 100 | Economy | Sway of a wandering market |
| market_reach | pazar_etki_sayi | 6 | 0 | 1000 | Economy | Maximum communities a wandering market enlivens |
| market_prosperity | pazar_refah | 2 | 0 | 100 | Economy | Prosperity contribution of a wandering market to communities on its world |
| pirate_min_traffic | korsan_trafik | 2 | 0 | 1000 | Economy | Minimum journeys in recent epochs for pirates to spawn |
| pirate_power | korsan_guc_seviye | 4 | 1 | 12 | Economy | Power level of void pirates |
| pirate_strength | korsan_guc | 55 | 0 | 100 | Economy | Base strength of void pirates |
| pirate_strength_die | korsan_guc_zar | 25 | 1 | 100 | Economy | Strength die of void pirates |
| pirate_wealth | korsan_servet | 40 | 0 | 100 | Economy | Wealth of void pirates |
| pirate_sway | korsan_nufuz | 30 | 0 | 100 | Economy | Sway of void pirates |
| pirate_route_danger | korsan_tehlike | 2 | 0 | 100 | Cosmos and travel | Danger pirates add to routes per epoch |
| pirate_route_danger_cap | korsan_tehlike_tavan | 95 | 0 | 100 | Cosmos and travel | Highest route danger pirates can cause |
| market_max | pazar_en_cok | 1 | 0 | 20 | Economy | Maximum simultaneous wandering markets in the cosmos (0 disables) |
| pirate_max | korsan_en_cok | 1 | 0 | 20 | Economy | Maximum simultaneous void-pirate communities in the cosmos (0 disables) |
| pirate_danger_decay | korsan_tehlike_azalma | 1 | 0 | 100 | Cosmos and travel | When no pirates remain, per-epoch decrease of danger on pirate routes (sail, slingshot, mount); does not drop below the highest danger a new route can have |
| deposit_power | yatak_guc_seviye | 7 | 1 | 12 | Economy | Power level of a new cosmic resource deposit |
| deposit_abundance | yatak_bolluk | 40 | 0 | 100 | Economy | Base abundance of a new cosmic resource deposit |
| deposit_abundance_die | yatak_bolluk_zar | 30 | 1 | 100 | Economy | Abundance die of a new cosmic resource deposit |
| deposit_value | yatak_deger | 90 | 0 | 100 | Economy | Value of a cosmic resource deposit |
| deposit_might | yatak_kudret | 80 | 0 | 100 | Economy | Might of a cosmic resource deposit |

### EMPTY_WORLD

Old namespace `BOS_DUNYA` · 6 rows · defined in `src/bosdunya.js` · also read by `src/derin.js`, `src/epoch.js`, `src/firsatlar.js`, `src/tools.js`. Empty (uninhabited) worlds: dispatching sons, first-people rewards.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| dispatch_wait_epochs | dagit_bekle | 1 | 0 | 1000 | Cosmos and travel | When an empty but habitable world stays empty this many epochs, a son turns to it on his own (0 = immediately) |
| first_people_essence | ilk_halk_oz | 30 | 0 | 10,000 | Cosmos and travel | Essence reward for the son who creates the first people, settlement or named mortal of an empty world |
| first_people_renown | ilk_halk_un | 10 | 0 | 10,000 | Cosmos and travel | Renown reward for the son who creates the first people of an empty world |
| first_people_xp | ilk_halk_xp | 20 | 0 | 10,000 | Cosmos and travel | XP reward for the son who creates the first people of an empty world |
| native_guarantee_epochs | yerli_guvence | 3 | 0 | 1000 | Population and growth | If a world stays without a people this many epochs, a native people certainly appears (0 = no guarantee) |
| opportunity_regions | firsat_bolge | 3 | 1 | 50 | Opportunities | Habitable regions listed in the new-world opportunity |

### EPOCH_FLOW

Old namespace `CAG_AKIS` · 8 rows · defined in `src/epoch.js`. In-epoch year schedule of phases and live-feed retention.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| year_gods | yil_ogul | 15 | 0 | 100,000 | Epoch flow | Gods' turn: until this year of the epoch |
| year_mortals | yil_olumlu | 30 | 0 | 100,000 | Epoch flow | Mortals' turn: until this year of the epoch |
| year_engine | yil_motor | 45 | 0 | 100,000 | Epoch flow | The world's own flow: until this year of the epoch |
| year_fate | yil_kader | 49 | 0 | 100,000 | Epoch flow | Fate and chronicler: until this year of the epoch |
| year_transition | yil_gecis | 4 | 0 | 100,000 | Epoch flow | First years of the new epoch after the transition (until this year) |
| live_log_memory | gunluk | 600 | 10 | 100,000 | Interface | Recent live-feed events kept in memory |
| live_log_db | gunluk_db | 1000 | 10 | 1,000,000 | Interface | Recent live-feed events kept in the database |
| epoch_end_summary_lines | bildirim_ozet | 6 | 0 | 100 | Interface | Summary lines shown in the epoch-ended notification |

### ESSENCE

Old namespace `OZ` · 7 rows · defined in `src/sim.js`. Essence overflow, godless gnawing, renown decay, Creator income above cap.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| overflow_pct | tasma | 8 | 0 | 100 | Creator and essence | Share of essence above the cap overflowing into the world each epoch (%) |
| overflow_per_fertility | tasma_bereket | 10 | 1 | 1000 | Creator and essence | Every this much overflowing essence gives regions 1 fertility in total (shared starting from the most barren region) |
| overflow_fertility_cap | tasma_bereket_ust | 70 | 0 | 100 | Creator and essence | Overflowing essence does not raise a region's fertility above this |
| godless_gnaw | tanrisiz_kemirme | 3 | 0 | 100 | Creator and essence | Essence gnawed by each godless community per epoch |
| renown_keep_pct | un_sonme | 95 | 0 | 100 | Creator and essence | Share of a son's renown kept each epoch (%) |
| over_cap_income_pct | tavan_gelir | 50 | 0 | 100 | Creator and essence | Share of the Creator's epoch income remaining while above the essence cap (BALANCE.creator_essence_soft_cap) (%) |
| exile_regen_pct | surgun_oz | 0 | 0 | 100 | Creator and essence | Ratio of an exiled son's per-epoch essence regeneration to normal regeneration (%) |

### EXPLORATION

Old namespace `KESIF` · 39 rows · defined in `src/ufuk.js` · also read by `src/firsatlar.js`, `src/olumluler.js`, `src/tools.js`. Mortal exploration of new land and routes.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| per_epoch_cap | cag_tavan | 2 | 0 | 100 | Exploration | Maximum new lands mortals discover spontaneously on one world in one epoch (0 off) |
| base_chance | taban_sans | 4 | 0 | 100 | Exploration | A community or explorer mortal sets out to explore on its own (% per epoch) |
| min_population | en_az_nufus | 300 | 0 | 10,000,000 | Exploration | Minimum population (or followers) of a community setting out to explore on its own |
| crowded_fill_pct | dar_doluluk | 80 | 1 | 1000 | Exploration | If its region's fill (population / carrying capacity) is at or above this, the community counts as living on cramped land (%) |
| crowded_bonus_pct | dar_ek | 12 | 0 | 100 | Exploration | Contribution of cramped land to a community's exploration chance (%) |
| hungry_food | ac_erzak | 15 | 0 | 1000 | Exploration | A community with food below this counts as hungry |
| poor_prosperity | yoksul_refah | 25 | 0 | 100 | Exploration | A community with prosperity below this counts as poor |
| hungry_bonus_pct | ac_ek | 10 | 0 | 100 | Exploration | Contribution of being hungry or poor to the exploration chance (%) |
| knowledge_bonus_pct | bilgi_ek | 8 | 0 | 100 | Exploration | Contribution to exploration chance for those knowing seafaring, pathfinding or astronomy (%) |
| explorer_threshold | kasif_esik | 120 | 0 | 200 | Exploration | Intellect + agility total for a mortal to count as having an explorer spirit |
| explorer_bonus_pct | kasif_ek | 10 | 0 | 100 | Exploration | Exploration contribution of an explorer-spirited mortal (for themself or the community on their land) (%) |
| new_region_pct | bolge_pay | 40 | 0 | 100 | Exploration | Chance the found land is a new region; otherwise a new place inside a region (%) |
| land_power | guc | 3 | 1 | 12 | Exploration | Power level of a discovered land |
| land_stat_base | stat_taban | 15 | 0 | 100 | Exploration | Base of the breadth, magic and mystery of a discovered land |
| land_stat_die | stat_zar | 60 | 1 | 100 | Exploration | Die added to the breadth, magic and mystery of a discovered land (1…n) |
| land_fertility_base | bereket_taban | 35 | 0 | 100 | Exploration | Base fertility of a discovered land |
| land_fertility_die | bereket_zar | 50 | 1 | 100 | Exploration | Die added to the fertility of a discovered land (1…n) |
| land_danger_base | tehlike_taban | 10 | 0 | 100 | Exploration | Base danger of a discovered land |
| land_danger_die | tehlike_zar | 50 | 1 | 100 | Exploration | Die added to the danger of a discovered land (1…n) |
| pioneer_chance | oncu_sans | 50 | 0 | 100 | Exploration | Pioneers settle the land the community found (doubled on cramped land) (%) |
| pioneer_share_pct | oncu_pay | 8 | 0 | 100 | Exploration | Population share of the pioneer party (%) |
| pioneer_min_population | oncu_en_az | 100 | 1 | 1,000,000 | Exploration | Minimum population of a pioneer settlement |
| pioneer_prosperity | oncu_refah | 35 | 0 | 100 | Exploration | Prosperity of a pioneer settlement |
| pioneer_defense | oncu_savunma | 20 | 0 | 100 | Exploration | Defense of a pioneer settlement |
| pioneer_default_piety | oncu_inanc | 50 | 0 | 100 | Exploration | Piety of pioneers coming from a community with no recorded piety |
| map_distance | harita_uzaklik | 300 | 50 | 2000 | Exploration | Distance of the new region on the map from the region it was found from (close enough to be neighbours) |
| map_attempts | harita_deneme | 12 | 1 | 360 | Exploration | Number of directions tried when searching for the new region's map position |
| route_search_chance | rota_sans | 6 | 0 | 100 | Exploration | A community or mortal knowing a way to other worlds (sky navigation, gate science, pathfinding, magic or a flying mount) searches for a route on its own (% per epoch) |
| route_search_cap | rota_cag_tavan | 1 | 0 | 100 | Exploration | Maximum communities or mortals searching for a route on their own in the cosmos in one epoch (0 off) |
| crowded_communities_per_region | dar_topluluk | 3 | 1 | 100 | Exploration | If communities (peoples + settlements) per region on a world are at or above this, land counts as cramped |
| free_land_creation | toprak_bedava | 1 | 0 | 1 | Exploration | On cramped land the son's first land creation (region or place) in the epoch costs no action (1 on, 0 off) |
| land_creation_essence | toprak_oz | 10 | 0 | 10,000 | Exploration | Essence reward for a son creating a new region or place on cramped land |
| land_creation_renown | toprak_un | 3 | 0 | 10,000 | Exploration | Renown reward for a son creating a new region or place on cramped land |
| cosmos_stagnant_epochs | kozmos_durgun | 8 | 1 | 1000 | Exploration | If no new world has been born for this many epochs, sons able to birth worlds are reminded of the cosmos |
| foreign_god_raise_land_chance | yabanci_sans | 8 | 0 | 100 | Exploration | An awake foreign god raises a new land on its own world (% per epoch) |
| tool_per_epoch | arac_tur | 1 | 0 | 20 | Exploration | discover_land (toprak_kesfet): maximum discoveries by one mortal per epoch (0 disables the tool) |
| tool_success_threshold | arac_esik | 45 | 0 | 200 | Exploration | discover_land: success threshold (d100 + intellect or craft / MORTAL_TOOLS.route_intellect_divisor + knowledge bonus) |
| tool_knowledge_bonus | arac_bilgi_ek | 15 | 0 | 200 | Exploration | discover_land: die bonus for those knowing seafaring, pathfinding or astronomy |
| summary_list | liste | 12 | 1 | 1000 | Exploration | Number of recent discoveries shown in the exploration summary |

### FAITH

Old namespace `INANC` · 6 rows · defined in `src/world.js`. Faith computation for sons.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| followers_per_faith | murit_bolen | 50 | 1 | 100,000 | Religion and language | Faith: every this many cult followers give 1 faith |
| pious_population_per_faith | nufus_bolen | 2000 | 1 | 10,000,000 | Religion and language | Faith: every this much pious population gives 1 faith |
| default_piety | dindarlik | 50 | 0 | 100 | Religion and language | Faith: piety of a community whose piety is unknown |
| other_worshipper | diger | 2 | 0 | 1000 | Religion and language | Faith: contribution of every other worshipping entity |
| community_min | topluluk_en_az | 1 | 0 | 1000 | Religion and language | Faith: minimum contribution of each worshipping people, settlement and cult (a small community's faith is not rounded to zero) |
| multiplier_power_pct | carpan | 150 | 100 | 1000 | Religion and language | Effect of the faith-multiplier power (%) |

### FATE

Old namespace `KADER` · 74 rows · defined in `src/agents.js`. Fate (judge) and chronicler: budgets, threads, rewards, anti-repetition.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| budget_new_creations_chars | butce_yeni | 60,000 | 2000 | 1,000,000 | Context budgets | Fate: creations in a single judgment call (characters); those that don't fit are weighed in extra rounds in the same epoch |
| budget_old_prophecies_chars | butce_kehanet | 12,000 | 500 | 200,000 | Context budgets | Fate: old prophecies (characters) |
| budget_epoch_events_chars | butce_olaylar | 20,000 | 1000 | 400,000 | Context budgets | Fate: the epoch's events (characters) |
| budget_engine_notes_chars | butce_motor | 12,000 | 500 | 200,000 | Context budgets | Fate: engine notes (characters) |
| budget_judgment_prompt_chars | butce_istem | 140,000 | 10,000 | 2,000,000 | Context budgets | Fate: entire judgment prompt (characters) |
| budget_chronicler_prompt_chars | butce_kronikci | 30,000 | 2000 | 400,000 | Context budgets | Entire chronicler prompt (characters) |
| open_thread_cap | iplik_tavan | 12 | 2 | 100 | Fate and chronicle | Open story-thread cap (when exceeded, Fate closes more) |
| forced_close_cap | kapat_tavan | 6 | 0 | 50 | Fate and chronicle | Maximum forced thread closures in one epoch |
| new_thread_cap | yeni_iplik_tavan | 4 | 0 | 50 | Fate and chronicle | Maximum new threads in one epoch |
| stale_thread_epochs | durgun_cag | 4 | 1 | 100 | Fate and chronicle | A thread not advancing for this many epochs becomes a closure candidate |
| long_thread_steps | uzun_iplik | 8 | 2 | 200 | Fate and chronicle | After this many advances a thread should be concluded |
| reward_cap | odul_tavan | 15 | 0 | 500 | Fate and chronicle | Maximum renown a son can receive from Fate in one epoch |
| canon_facts_max | gercek_tavan | 24 | 0 | 200 | Fate and chronicle | Maximum canon facts in a judgment |
| canon_facts_min | gercek_en_az | 3 | 0 | 50 | Fate and chronicle | Minimum canon facts in a judgment |
| words_per_epoch_cap | kelime_tavan | 10 | 0 | 100 | Fate and chronicle | Maximum words Fate adds to languages in one epoch |
| seer_correct_charisma | kahin_dogru | 10 | 0 | 100 | Fate and chronicle | Charisma to the seer for a prophecy that comes true |
| seer_wrong_charisma_loss | kahin_yanlis | 8 | 0 | 100 | Fate and chronicle | Charisma taken from the seer for a misinterpreted prophecy |
| reward_streak_window | odul_seri_pencere | 5 | 0 | 100 | Fate and chronicle | Fate reward: epochs looked back for consecutive rewards (0: no decay) |
| reward_streak_keep_pct | odul_seri_azalma | 75 | 0 | 100 | Fate and chronicle | Fate reward: share remaining for each reward received in recent epochs (%) |
| thread_advance_cap | ilerleme_tavan | 6 | 0 | 50 | Fate and chronicle | Maximum threads Fate advances with events in one epoch |
| prophecy_renown | kehanet_un | 10 | 0 | 500 | Fate and chronicle | Renown to the creating son for a fulfilled prophecy |
| prophecy_xp | kehanet_xp | 30 | 0 | 1000 | Fate and chronicle | XP to the creating son for a fulfilled prophecy |
| banned_previous_openings | onceki_acilis | 6 | 0 | 50 | Fate and chronicle | Previous narrative openings forbidden to the chronicler |
| previous_epoch_names_shown | onceki_ad | 12 | 0 | 200 | Fate and chronicle | Previous epoch names shown to the chronicler |
| banned_son_message_openings | soz_acilis | 3 | 0 | 20 | Fate and chronicle | Recent message openings forbidden to a son |
| fate_timeout | kader_sure | 480 | 30 | 3600 | Agents and model | Fate and chronicler timeout (s); safety margin for a judgment whose output grows |
| judgment_parallel | hukum_paralel | 3 | 1 | 16 | Agents and model | Fate: extra judgment rounds (for creations not fitting the context) running at the same time |
| reason_max_words | gerekce_sozcuk | 24 | 4 | 400 | Fate and chronicle | Fate: maximum words in a judgment's reasoning (stated in the prompt; excess cut at a sentence boundary; output and time shrink) |
| historians_per_epoch | tarihci | 2 | 0 | 20 | Fate and chronicle | Peoples writing a perspective in one epoch |
| folk_beliefs_per_epoch | inanc_cift | 5 | 0 | 50 | Fate and chronicle | New folk beliefs written in one epoch |
| voices_timeout | ses_sure | 240 | 30 | 3600 | Agents and model | Voices-of-the-peoples timeout (s) |
| model_retries | model_deneme | 3 | 1 | 10 | Agents and model | Total attempts on a transient model error |
| son_turn_timeout | ogul_sure | 420 | 60 | 3600 | Agents and model | Son turn timeout (s) |
| prescreen_min_description | on_eleme_aciklama | 140 | 0 | 2000 | Fate and chronicle | Prescreen: a description shorter than this gets a warning (characters) |
| prescreen_max_off_domain_power | on_eleme_guc | 7 | 1 | 11 | Fate and chronicle | Prescreen: an off-domain creation stronger than this gets a warning |
| voices_events_chars | ses_olay | 6000 | 500 | 100,000 | Context budgets | Events sent to the voices of the peoples (characters) |
| pantheon_root_threshold_pct | panteon_kok_esik | 50 | 1 | 100 | Fate and chronicle | Summoning: a root appearing in the titles/obsessions of this percentage of sons is forbidden to the new son |
| pantheon_root_min_sons | panteon_kok_en_az | 4 | 1 | 100 | Fate and chronicle | Summoning: minimum sons for the pantheon-root measurement |
| council_sentences | konsey_cumle | 2 | 1 | 50 | Fate and chronicle | Sentences taken from the council line in epoch events (so the minutes aren't copied into the narrative) |
| name_type_lines | ad_tur_satir | 60 | 0 | 1000 | Fate and chronicle | Chronicler prompt: types of records mentioned in the epoch (maximum lines) |
| budget_name_type_chars | butce_ad_tur | 3000 | 0 | 50,000 | Context budgets | Chronicler prompt: name and type list (characters) |
| message_tic_window | soz_tik_pencere | 8 | 0 | 200 | Fate and chronicle | Message tic: recent messages examined |
| message_tic_threshold_pct | soz_tik_esik | 60 | 1 | 100 | Fate and chronicle | Message tic: a word appearing in this percentage of recent messages is forbidden |
| shared_tic_window | soz_ortak_pencere | 24 | 0 | 500 | Fate and chronicle | Shared message tic: recent messages of all sons examined |
| shared_tic_threshold_pct | soz_ortak_esik | 30 | 1 | 100 | Fate and chronicle | Shared message tic: a root appearing in this percentage of recent messages is forbidden to all |
| budget_previous_judgments_chars | butce_onceki_hukum | 2500 | 0 | 50,000 | Context budgets | Chronicler prompt: Fate's judgments from the previous epoch (characters) |
| historian_opening_chars | bakis_acilis | 160 | 20 | 2000 | Fate and chronicle | Historian prompt: length of the previous narrative opening shown (characters) |
| prescreen_tired_images | on_eleme_motif | 3 | 1 | 50 | Fate and chronicle | Prescreen: warning if this many tired images appear in the description |
| chronicler_min_tenure | kronikci_sure | 6 | 1 | 1000 | Fate and chronicle | Chronicler continuity: minimum epochs a chronicler writes before handing over to a successor |
| shared_tic_forms | soz_ortak_bicim | 3 | 1 | 20 | Fate and chronicle | Shared message tic: forms shown from the root family |
| shared_tic_cap | soz_ortak_tavan | 3 | 0 | 20 | Fate and chronicle | Shared message tic: maximum forbidden roots |
| message_tic_min_messages | soz_tik_en_az | 4 | 1 | 200 | Fate and chronicle | Message tic: minimum messages before checking starts |
| message_tic_cap | soz_tik_tavan | 3 | 0 | 20 | Fate and chronicle | Message tic: maximum forbidden words per message |
| son_opening_words | soz_acilis_kelime | 3 | 1 | 20 | Fate and chronicle | Length of the message opening forbidden to a son (words) |
| chronicler_opening_words | acilis_kelime | 14 | 1 | 80 | Fate and chronicle | Length of the narrative opening forbidden to the chronicler (words; about the first sentence so it sees the template) |
| summary_min_chars | ozet_en_az | 120 | 0 | 2000 | Fate and chronicle | Shortest form of the epoch summary (characters) |
| thread_recent_advancers | iplik_ilerleten | 3 | 0 | 50 | Context budgets | Recent creations advancing each thread in the Fate prompt |
| closure_candidates_shown | kapat_aday_goster | 6 | 0 | 100 | Context budgets | Threads written into the Fate prompt as priority closure candidates |
| budget_chronicler_engine_chars | butce_kronik_motor | 6000 | 500 | 200,000 | Context budgets | Chronicler: engine notes (characters) |
| seer_default_charisma | kahin_karizma | 40 | 0 | 100 | Fate and chronicle | Charisma of a seer with unknown charisma |
| creator_belief_max_people | inanc_yaratici_halk | 6 | 0 | 100 | Fate and chronicle | Largest people for which the Creator's belief can be written in one epoch |
| budget_engine_born_chars | butce_dogan | 20,000 | 500 | 400,000 | Context budgets | Fate prompt: section of those born from the world's own flow (characters; those not fitting are named in a separate naming round) |
| budget_world_records_chars | butce_dunya_kayit | 4000 | 0 | 100,000 | Context budgets | Fate prompt: list of this epoch's world records (characters) |
| chronicler_side_share_pct | kronik_yan_pay | 25 | 0 | 100 | Context budgets | Chronicler prompt: maximum share for engine results and unnamed records (% of data budget) |
| opening_window | acilis_pencere | 12 | 0 | 200 | Fate and chronicle | Opening template: recent epoch narratives examined |
| opening_pattern_threshold | acilis_kalip_esik | 3 | 2 | 50 | Fate and chronicle | Opening template: a two-word pair appearing in this many separate openings is forbidden |
| opening_fix | acilis_duzelt | 1 | 0 | 1 | Fate and chronicle | If an opening starts with a forbidden template, the chronicler is asked to rewrite only the first sentence (1 on, 0 off) |
| epoch_name_root_threshold | ad_kok_esik | 3 | 2 | 100 | Fate and chronicle | Epoch name: a root appearing in this many previous names is forbidden |
| complete_missing_worlds | eksik_dunya_tamamla | 1 | 0 | 1 | Fate and chronicle | If the chronicler skips a world's section, a second short call for those worlds (1 on, 0 off) |
| backfill_world_sections | kayip_dunya_bolum | 2 | 0 | 100 | Fate and chronicle | Missing world sections written retroactively for past epochs in one completion |
| backfill_chronicles | kayip_kronik | 3 | 0 | 100 | Fate and chronicle | Missing epoch chronicles written retroactively in one completion |
| backfill_timeout | kayip_sure | 300 | 30 | 3600 | Agents and model | Missing epoch chronicle timeout (s) |
| seer_power_mult | kahin_kat | 2 | 1 | 20 | Fate and chronicle | Renown and XP multiplier a son with the Seer power receives from a fulfilled prophecy |
| xp_per_renown | odul_xp_kat | 2 | 0 | 50 | Fate and chronicle | Son's XP per renown granted by Fate |

### FOLK_BELIEF

Old namespace `HALK_INANC` · 3 rows · defined in `src/agents.js`. Folk-belief text generation guards.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| pattern_window | kalip_pencere | 12 | 0 | 500 | Fate and chronicle | Folk belief: recent beliefs examined for patterns piling up in the deviation sentence |
| pattern_threshold_pct | kalip_esik | 30 | 1 | 100 | Fate and chronicle | Folk belief: a pattern appearing in this percentage of recent beliefs is forbidden |
| god_name_max_letters | ad_harf | 40 | 3 | 200 | Fate and chronicle | Folk belief: maximum letters of the god name the model gives |

### FOREIGN_GODS

Old namespace `YABANCI` · 21 rows · defined in `src/yabanci.js` · also read by `src/agents.js`, `src/panteon.js`, `src/tools.js`. Foreign god stats and powers.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| stat_base | stat_taban | 35 | 1 | 100 | Foreign gods | Base of each stat of a new foreign god |
| stat_die | stat_zar | 45 | 0 | 100 | Foreign gods | Die added to each stat of a new foreign god |
| stat_neutral | stat_notr | 50 | 0 | 100 | Foreign gods | Neutral stat: above this has a positive effect, below a negative one |
| war_stat_share_pct | savas_stat_pay | 50 | 0 | 100 | Foreign gods | Share of (Strength + Will) / 2 in war strength (%); the rest is general power |
| talk_will | konusma_irade | 30 | 0 | 500 | Foreign gods | Will's resistance in talking with a son: (Will − neutral) × this / 100 is subtracted from the die |
| attract_charisma | cekim_karizma | 20 | 0 | 500 | Foreign gods | Charisma contribution to the chance of attracting worshippers: (Charisma − neutral) × this / 100 points (%) |
| steal_cunning | calma_kurnazlik | 20 | 0 | 500 | Foreign gods | Cunning contribution to the chance of stealing worshippers: (Cunning − neutral) × this / 100 points (%) |
| attack_agility | saldiri_ceviklik | 20 | 0 | 500 | Foreign gods | Agility contribution to the chance of a hostile action: (Agility − neutral) × this / 100 points (%) |
| help_wisdom | yardim_bilgelik | 20 | 0 | 500 | Foreign gods | Wisdom contribution to the chance of friendly help: (Wisdom − neutral) × this / 100 points (%) |
| prosperity_creativity | refah_yaraticilik | 10 | 0 | 500 | Foreign gods | Creativity effect on the friendly prosperity contribution: (Creativity − neutral) × this / 100 prosperity |
| wake_endurance | uyanis_dayaniklilik | 10 | 0 | 500 | Foreign gods | Endurance effect on the wake-up time after defeat: shortened by (Endurance − neutral) × this / 100 epochs |
| growth_faith_might | guc_inanc_kudret | 20 | 0 | 500 | Foreign gods | Might effect on the strengthening threshold: (Might − neutral) × this / 100 faith lower |
| powers_count | guc_sayi | 2 | 0 | 20 | Foreign gods | Number of powers given to a foreign god when deepened |
| power_shield | guc_kalkan | 15 | 0 | 500 | Foreign gods | Shield power: added to war strength |
| power_caller | guc_cekim | 15 | 0 | 100 | Foreign gods | Caller power: added to the chance of attracting worshippers (%) |
| power_thief | guc_hirsiz | 15 | 0 | 100 | Foreign gods | Worshipper-thief power: added to the chance of stealing worshippers (%) |
| power_destroyer | guc_yikici | 15 | 0 | 100 | Foreign gods | Destroyer power: added to the chance of a hostile action (%) |
| power_bountiful | guc_bereket | 200 | 100 | 10,000 | Foreign gods | Bountiful power: multiplier of the friendly prosperity contribution (%) |
| power_reviving | guc_dirilis | 50 | 1 | 100 | Foreign gods | Reviving power: percentage of the wake-up time after defeat |
| power_sharp_tongue | guc_soz | 15 | 0 | 500 | Foreign gods | Sharp-tongued power: subtracted from the die of a son talking with it |
| deepen_chronicle_lines | derin_kronik | 40 | 0 | 10,000 | Foreign gods | Chronicle lines mentioning its name given to the model when a foreign god is deepened |

### GENESIS

Old namespace `YARATILIS` · 9 rows · defined in `src/agents.js`. Initial world genesis.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| regions_min | bolge_en_az | 3 | 1 | 50 | Genesis | Minimum regions at genesis |
| regions_max | bolge_en_cok | 5 | 1 | 50 | Genesis | Maximum regions at genesis |
| region_breadth | bolge_genislik | 60 | 0 | 100 | Genesis | Breadth of the initial regions |
| region_power | bolge_guc | 8 | 1 | 11 | Genesis | Power level of the initial regions |
| sky_brightness | gok_parlaklik | 70 | 0 | 100 | Genesis | Brightness of the first celestial body |
| sky_influence | gok_etki | 60 | 0 | 100 | Genesis | Influence of the first celestial body |
| sky_power | gok_guc | 7 | 1 | 11 | Genesis | Power level of the first celestial body |
| initial_son_relation | iliski | 80 | 0 | 100 | Genesis | Maximum magnitude (±) of the starting relation between the first sons |
| timeout | sure | 360 | 30 | 3600 | Agents and model | Genesis timeout (s) |

### GOALS

Old namespace `HEDEF` · 51 rows · defined in `src/hedef.js`. Scenarios, achievements and score.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| keep_apocalypse_away_epochs | kiyamet_uzak_cag | 20 | 1 | 200 | Apocalypse | Scenario: duration to keep the apocalypse away (epochs) |
| keep_apocalypse_away_pct | kiyamet_uzak_esik | 80 | 1 | 100 | Apocalypse | Scenario: point the clock must not reach (% of threshold) |
| score_apocalypse_penalty | puan_kiyamet | 150 | 0 | 1000 | Apocalypse | Score: penalty for the apocalypse when the clock is at the threshold |
| keep_apocalypse_away_points | kiyamet_uzak_puan | 300 | 0 | 10,000 | Goals and achievements | Scenario points: keep the apocalypse away |
| one_faith_min_peoples | tek_inanc_halk | 3 | 1 | 100 | Goals and achievements | Scenario: minimum peoples that must unite in one faith |
| one_faith_points | tek_inanc_puan | 250 | 0 | 10,000 | Goals and achievements | Scenario points: all peoples in one faith |
| lost_star_points | kayip_yildiz_puan | 200 | 0 | 10,000 | Goals and achievements | Scenario points: rekindle the lost star |
| inhabited_worlds | dunya_sayi | 5 | 1 | 100 | Goals and achievements | Scenario: number of worlds with living peoples |
| multiworld_points | dunya_puan | 250 | 0 | 10,000 | Goals and achievements | Scenario points: multi-world cosmos |
| peace_epochs | baris_cag | 5 | 1 | 200 | Goals and achievements | Scenario: consecutive epochs of peace |
| peace_points | baris_puan | 200 | 0 | 10,000 | Goals and achievements | Scenario points: long peace |
| cosmic_stage | kozmik_basamak | 4 | 1 | 20 | Goals and achievements | Scenario: stage civilization must reach |
| cosmic_points | kozmik_puan | 300 | 0 | 10,000 | Goals and achievements | Scenario points: civilization reaching for the stars |
| loyal_epochs | sadik_cag | 10 | 1 | 200 | Goals and achievements | Scenario: epochs that must pass without rebellion |
| loyal_min_loyalty | sadik_sadakat | 60 | 0 | 100 | Goals and achievements | Scenario: loyalty all sons must exceed |
| default_loyalty | sadakat_varsayilan | 50 | 0 | 100 | Goals and achievements | Scenario: loyalty assumed for a son with no recorded loyalty |
| loyal_points | sadik_puan | 250 | 0 | 10,000 | Goals and achievements | Scenario points: loyal pantheon |
| horizon_lands | ufuk_toprak | 8 | 1 | 1000 | Goals and achievements | Scenario: new lands that must be opened (region or place; by exploration, a son or the god's hand) |
| horizon_regions | ufuk_bolge | 2 | 0 | 1000 | Goals and achievements | Scenario: at least this many of them must be new regions |
| horizon_points | ufuk_puan | 250 | 0 | 10,000 | Goals and achievements | Scenario points: new horizons |
| ach_worlds | b_dunya | 2 | 1 | 100 | Goals and achievements | Achievement: number of worlds in the cosmos |
| ach_worlds_points | b_dunya_puan | 50 | 0 | 10,000 | Goals and achievements | Achievement points: new sky |
| ach_stars | b_yildiz | 3 | 1 | 100 | Goals and achievements | Achievement: number of stars in the cosmos |
| ach_stars_points | b_yildiz_puan | 40 | 0 | 10,000 | Goals and achievements | Achievement points: constellation |
| ach_prophecy_points | b_kehanet_puan | 40 | 0 | 10,000 | Goals and achievements | Achievement points: prophecy fulfilled |
| ach_resurrection_points | b_dirilis_puan | 60 | 0 | 10,000 | Goals and achievements | Achievement points: return from death |
| ach_revolt_points | b_isyan_puan | 40 | 0 | 10,000 | Goals and achievements | Achievement points: rebellion suppressed |
| ach_languages | b_dil | 10 | 1 | 1000 | Goals and achievements | Achievement: number of spoken languages |
| ach_languages_points | b_dil_puan | 50 | 0 | 10,000 | Goals and achievements | Achievement points: Babel |
| ach_population | b_nufus | 1,000,000 | 1000 | 2,000,000,000 | Goals and achievements | Achievement: total population of peoples |
| ach_population_points | b_nufus_puan | 60 | 0 | 10,000 | Goals and achievements | Achievement points: crowded world |
| ach_first_prayer_points | b_dua_puan | 30 | 0 | 10,000 | Goals and achievements | Achievement points: first prayer |
| ach_cult | b_kult | 3 | 1 | 100 | Goals and achievements | Achievement: communities worshipping the Creator directly |
| ach_cult_points | b_kult_puan | 60 | 0 | 10,000 | Goals and achievements | Achievement points: the Creator's cult |
| ach_voyager_points | b_sefer_puan | 50 | 0 | 10,000 | Goals and achievements | Achievement points: interstellar traveller |
| ach_epic_points | b_efsane_puan | 80 | 0 | 10,000 | Goals and achievements | Achievement points: epic completed |
| ach_epochs | b_cag | 10 | 1 | 1000 | Goals and achievements | Achievement: epochs passed (first threshold) |
| ach_epochs_points | b_cag_puan | 50 | 0 | 10,000 | Goals and achievements | Achievement points: first epoch threshold |
| ach_ancient_epochs | b_kadim_cag | 50 | 1 | 10,000 | Goals and achievements | Achievement: epochs passed (ancient) |
| ach_ancient_points | b_kadim_puan | 150 | 0 | 10,000 | Goals and achievements | Achievement points: ancient |
| ach_sons | b_ogul | 8 | 1 | 100 | Goals and achievements | Achievement: sons alive at the same time |
| ach_sons_points | b_ogul_puan | 50 | 0 | 10,000 | Goals and achievements | Achievement points: crowded pantheon |
| ach_peace_min_peoples | b_baris_halk | 3 | 1 | 100 | Goals and achievements | Achievement: minimum peoples for a warless epoch |
| ach_peace_points | b_baris_puan | 40 | 0 | 10,000 | Goals and achievements | Achievement points: the weapons fell silent |
| ach_explorers_points | b_kesif_puan | 40 | 0 | 10,000 | Goals and achievements | Achievement points: first explorers (mortals found an unknown land) |
| ach_sensed_world_points | b_sezgi_puan | 80 | 0 | 10,000 | Goals and achievements | Achievement points: sensed world (a world sensed by mortals was born) |
| score_population | puan_nufus | 20 | 0 | 1000 | Goals and achievements | Score: per tenfold of population |
| score_diversity_cap | puan_cesitlilik_tavan | 150 | 0 | 100,000 | Goals and achievements | Score: maximum points for record diversity |
| score_language | puan_dil | 5 | 0 | 1000 | Goals and achievements | Score: per language |
| score_world | puan_dunya | 25 | 0 | 1000 | Goals and achievements | Score: per world |
| score_stage | puan_basamak | 20 | 0 | 1000 | Goals and achievements | Score: per step of the highest civilization stage |

### GOD_ACTIONS

Old namespace `TANRI_EYLEM` · 34 rows · defined in `src/epoch.js`. The Creator's actions on sons (bless, star, ascend, punish, suppress, prayers).

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| bless_essence_amount | kutsa_oz | 20 | 0 | 1000 | The god's actions | Essence given to the son by an essence blessing |
| bless_stat_amount | kutsa_stat | 5 | 0 | 100 | The god's actions | Stat contribution of a stat blessing |
| bless_existence_amount | kutsa_varlik | 20 | 0 | 100 | The god's actions | Contribution of an existence blessing to the son's existence |
| bless_loyalty | kutsa_sadakat | 3 | 0 | 100 | The god's actions | Loyalty contribution of each blessing |
| star_stat_gain | yildiz_stat | 3 | 0 | 100 | The god's actions | Contribution of adding a star to each stat |
| ascension_existence | yukselis_varlik | 25 | 0 | 100 | The god's actions | Contribution of ascension to the son's existence |
| ascension_myth_spread | yukselis_efsane | 80 | 0 | 100 | The god's actions | Starting spread of the ascension myth |
| defiant_will | asi_irade | 70 | 0 | 100 | The god's actions | Will of a son who doesn't submit to punishment (above this) |
| lightning_hp_pct | yildirim_can | 30 | 0 | 100 | The god's actions | HP taken by lightning (% of max HP) |
| suppress_base | bastir_taban | 70 | 0 | 1000 | The god's actions | Suppressing a rebellion: base of the god's strength |
| suppress_essence_divisor | bastir_oz_bolen | 10 | 1 | 10,000 | The god's actions | Suppressing a rebellion: essence / this number is added to the god's strength |
| suppress_die | bastir_zar | 30 | 1 | 1000 | The god's actions | Suppressing a rebellion: each side's die (1–this number) |
| suppress_son_strength_pct | bastir_guc | 50 | 0 | 1000 | The god's actions | Suppressing a rebellion: contribution of the son's strength (%) |
| suppress_son_per_level | bastir_seviye | 3 | 0 | 100 | The god's actions | Suppressing a rebellion: son's contribution per level |
| suppress_loyalty_gain | bastir_sadakat | 15 | 0 | 100 | The god's actions | Loyalty gain of a suppressed rebel |
| suppress_hp_left_pct | bastir_can | 50 | 1 | 100 | The god's actions | Remaining HP of a suppressed rebel (%) |
| suppress_renown_loss | bastir_un | 10 | 0 | 1000 | The god's actions | Renown loss of a suppressed rebel |
| suppress_fail_renown | bastir_basarisiz_un | 10 | 0 | 1000 | The god's actions | Renown gain of a rebel who couldn't be suppressed |
| suppress_fail_ambition | bastir_basarisiz_hirs | 5 | 0 | 100 | The god's actions | Ambition gain of a rebel who couldn't be suppressed |
| suppress_fail_essence | bastir_basarisiz_oz | 20 | 0 | 10,000 | The god's actions | Extra essence loss of the god on a failed suppression |
| pardon_loyalty | af_sadakat | 8 | 0 | 100 | The god's actions | Loyalty contribution of a pardon |
| punish_defiant_loyalty_loss | ceza_asi_sadakat | 8 | 0 | 100 | The god's actions | Loyalty loss of a defiant son after punishment |
| punish_defiant_wrath | ceza_asi_ofke | 8 | 0 | 100 | The god's actions | Wrath gain of a defiant son after punishment |
| punish_submissive_loyalty | ceza_sadakat | 3 | 0 | 100 | The god's actions | Loyalty gain of a submissive son after punishment |
| punish_submissive_wrath | ceza_ofke | 4 | 0 | 100 | The god's actions | Wrath gain of a submissive son after punishment |
| prayer_essence_cap | dua_oz_tavan | 100 | 0 | 100,000 | The god's actions | Maximum essence that can be granted to one prayer |
| prayer_reply_loyalty | dua_sadakat | 4 | 0 | 100 | The god's actions | Contribution of a verbal reply to the son's loyalty |
| prayer_essence_per_loyalty | dua_oz_sadakat | 10 | 1 | 10,000 | The god's actions | Every this much essence granted to a prayer gives +1 loyalty |
| prayer_existence | dua_varlik | 3 | 0 | 100 | The god's actions | Contribution of an answered prayer to the son's existence |
| disaster_severity_pct | afet_siddet | 110 | 0 | 1000 | The god's actions | Severity multiplier of a disaster sent manually by the god (%) |
| disaster_event_severity | afet_olay | 75 | 0 | 100 | The god's actions | Severity in the event record of the god's disaster |
| curse_stat_loss | lanet_stat | 15 | 0 | 100 | The god's actions | Taken from community stats by the god's curse |
| note_max_chars | not_uzunluk | 6000 | 100 | 200,000 | Context budgets | Maximum length of the god's own note (characters; goes into prompts) |
| inspiration_max_chars | ilham_uzunluk | 600 | 10 | 20,000 | Context budgets | Maximum length of the inspiration text in world creation (characters) |

### GOD_HAND

Old namespace `TANRI_ELI` · 18 rows · defined in `src/oyuncu.js` · also read by `src/epoch.js`. The Creator's manual decrees and son distribution.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| decree_war_relation | buyruk_savas | 40 | 0 | 200 | Intervention | Community relation reduced when the god decrees war |
| decree_peace_relation | buyruk_baris | 20 | 0 | 200 | Intervention | Community relation added when the god decrees peace |
| decree_alliance_relation | buyruk_ittifak | 30 | 0 | 200 | Intervention | Community relation added when the god decrees an alliance |
| decree_trade_relation | buyruk_ticaret | 10 | 0 | 200 | Intervention | Community relation added when the god decrees trade |
| decree_expedition_pct | sefer_yuzde | 10 | 1 | 100 | Intervention | Population joining an expedition decreed by the god (default %) |
| decree_expedition_max_pct | sefer_tavan | 30 | 1 | 100 | Intervention | Maximum population joining an expedition decreed by the god (%) |
| decree_climate_epochs | iklim_cag | 4 | 1 | 100 | Intervention | Default duration of a climate age decreed by the god (epochs) |
| decree_climate_max_epochs | iklim_cag_tavan | 50 | 1 | 1000 | Intervention | Longest climate age the god can decree (epochs) |
| rekindle_brightness | tutustur_parlaklik | 75 | 0 | 100 | Intervention | Brightness of a rekindled star |
| rekindle_leak_drain | tutustur_sizinti | 20 | 0 | 100 | Intervention | Leak drawn from the worlds of a rekindled star |
| dispatch_donor_min_sons | dagitim_verici_en_az | 2 | 1 | 100 | Intervention | In automatic distribution, minimum active sons (including himself) that must remain on his world for a son to leave |
| assignment_protection_epochs | atama_koruma | 3 | 0 | 1000 | Intervention | Epochs during which automatic distribution does not touch a son the god manually sent to a world |
| mortal_agents_per_world_cap | olumlu_ajan_tavan | 12 | 0 | 1000 | Intervention | Maximum mortal agents that can be manually assigned per world |
| protector_bond_weight | koruyucu_bag | 5 | 0 | 1000 | Intervention | Bond weight to the world a son protects when sons are distributed |
| deposit_power | yatak_guc | 8 | 1 | 12 | Intervention | Power level of a cosmic resource deposit opened by the god |
| deposit_abundance | yatak_bolluk | 80 | 0 | 100 | Intervention | Abundance of a cosmic resource deposit opened by the god |
| deposit_value | yatak_deger | 95 | 0 | 100 | Intervention | Value of a cosmic resource deposit opened by the god |
| deposit_might | yatak_kudret | 85 | 0 | 100 | Intervention | Might of a cosmic resource deposit opened by the god |

### GOD_POWER

Old namespace `TANRI_GUC` · 76 rows · defined in `src/tanriguc.js`. The Creator's dark/great powers and their automatic use.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| drain_son_pct | ogul_em_pay | 50 | 1 | 100 | The god's power | Drain essence from a son: percentage of the son's essence per drain |
| drain_son_efficiency_pct | ogul_em_verim | 80 | 0 | 100 | The god's power | Percentage of essence drained from a son that passes to the god (the rest scatters) |
| drain_son_loyalty_loss | ogul_em_sadakat | 10 | 0 | 100 | The god's power | Loyalty loss of a drained son |
| drain_son_wrath | ogul_em_ofke | 15 | 0 | 100 | The god's power | Wrath gain of a drained son |
| drain_son_existence_loss | ogul_em_varlik | 5 | 0 | 100 | The god's power | Existence loss of a drained son |
| drain_witness_loyalty | ogul_em_korku | 3 | 0 | 100 | The god's power | Loyalty gain out of fear of other sons witnessing a drain |
| devour_son_essence_per_might | ogul_yut_kudret | 3 | 0 | 100 | The god's power | Devour a son: extra essence passing to the god per might point |
| devour_son_essence_per_level | ogul_yut_seviye | 20 | 0 | 1000 | The god's power | Devour a son: extra essence passing to the god per level |
| devour_son_witness_loyalty | ogul_yut_sadakat | 10 | 0 | 100 | The god's power | Devour a son: loyalty gain out of fear of the other sons |
| devour_son_friend_wrath | ogul_yut_ofke | 25 | 0 | 100 | The god's power | Devour a son: wrath gain of those who loved the devoured |
| drain_mortal_pct | olumlu_em_pay | 50 | 1 | 100 | The god's power | Drain life from a mortal: percentage of their HP |
| drain_mortal_hp_per_essence | olumlu_em_bolen | 10 | 1 | 1000 | The god's power | Every this much HP drained from a mortal becomes 1 essence for the god |
| devour_mortal_essence_per_power | olumlu_guc_oz | 2 | 0 | 100 | The god's power | Devour a mortal: extra essence per power level |
| harvest_population_pct | hasat_nufus | 10 | 0 | 100 | The god's power | Faith harvest: percentage of the community's population sacrificed |
| harvest_piety_loss | hasat_inanc | 20 | 0 | 100 | The god's power | Faith harvest: community's piety loss |
| harvest_victims_per_essence | hasat_nufus_bolen | 500 | 1 | 1,000,000 | The god's power | Faith harvest: every this many victims become 1 essence |
| harvest_essence_per_piety | hasat_inanc_oz | 1 | 0 | 100 | The god's power | Faith harvest: essence of each piety point lost |
| harvest_patron_loyalty_loss | hasat_tapanin_kini | 8 | 0 | 100 | The god's power | Loyalty loss of the son worshipped by the harvested community |
| drain_foreign_pct | yt_em_pay | 30 | 1 | 100 | The god's power | Drain essence from a foreign god: percentage of its strength |
| foreign_essence_per_strength | yt_guc_oz | 3 | 0 | 100 | The god's power | Essence of each strength point of a foreign god |
| drain_foreign_attitude_loss | yt_em_tutum | 20 | 0 | 200 | The god's power | A drained foreign god's attitude drops by this much |
| kill_foreign_base_cost | yt_oldur_taban | 60 | 0 | 2000 | The god's power | Base cost of killing a foreign god |
| kill_foreign_strength_pct | yt_oldur_guc | 100 | 0 | 1000 | The god's power | Killing a foreign god: this percentage of its strength is added to the cost |
| kill_immortal_foreign_mult | yt_olumsuz_kat | 2 | 1 | 10 | The god's power | Cost multiplier for killing a foreign god with the immortal power |
| foreign_worshipper_convert_pct | yt_tapan_donus | 50 | 0 | 100 | The god's power | Chance a dead foreign god's worshippers turn to the Creator (%); those who don't become godless |
| resurrect_mortal_base_cost | olumlu_dirilt | 40 | 0 | 1000 | The god's power | Base cost of resurrecting a mortal |
| resurrect_mortal_cost_per_power | olumlu_dirilt_guc | 2 | 0 | 100 | The god's power | Resurrect a mortal: extra cost per power level |
| resurrect_mortal_hp | olumlu_dirilt_can | 50 | 1 | 300 | The god's power | HP of a resurrected mortal |
| resurrect_mortal_lifespan_years | olumlu_dirilt_omur | 20 | 0 | 50,000 | The god's power | Years added to the lifespan of a mortal who died of old age when resurrected |
| deify_cost | tanrilastir | 150 | 0 | 5000 | The god's power | Cost of raising a mortal to godhood |
| deify_loyalty | tanrilastir_sadakat | 80 | 0 | 100 | The god's power | Loyalty of the deified mortal toward you |
| deify_existence | tanrilastir_varlik | 50 | 1 | 100 | The god's power | Starting existence of the deified |
| demote_cost | alcalt | 40 | 0 | 1000 | The god's power | Cost of demoting a son one rarity down |
| demote_loyalty_loss | alcalt_sadakat | 15 | 0 | 100 | The god's power | Loyalty loss of a demoted son |
| demote_wrath | alcalt_ofke | 25 | 0 | 100 | The god's power | Wrath gain of a demoted son |
| strip_power_cost | guc_sok | 30 | 0 | 1000 | The god's power | Cost of stripping one of a son's powers |
| strip_power_wrath | guc_sok_ofke | 20 | 0 | 100 | The god's power | Wrath gain of a son whose power is stripped |
| strip_power_essence | guc_sok_oz | 15 | 0 | 1000 | The god's power | Essence passing to the god from the stripped power |
| absolute_command_cost | mutlak_buyruk | 25 | 0 | 1000 | The god's power | Cost of an irrefusable command |
| absolute_command_loyalty_loss | mutlak_sadakat | 5 | 0 | 100 | The god's power | Loyalty loss of a son receiving an irrefusable command |
| prophet_cost | peygamber | 20 | 0 | 1000 | The god's power | Cost of choosing a mortal as prophet |
| prophet_charisma | peygamber_karizma | 15 | 0 | 100 | The god's power | Charisma gain of the prophet |
| prophet_piety | peygamber_inanc | 10 | 0 | 100 | The god's power | Piety gain of the prophet's community |
| prophet_convert_chance | peygamber_donus_sans | 15 | 0 | 100 | The god's power | Chance each epoch that the prophet's community turns to the Creator (%) |
| manifest_cost | tezahur | 10 | 0 | 1000 | The god's power | Cost of appearing to a mortal or community while awake |
| manifest_piety | tezahur_inanc | 10 | 0 | 100 | The god's power | Piety gain from a manifestation |
| manifest_worship_chance | tezahur_tapin_sans | 30 | 0 | 100 | The god's power | Chance the witness of a manifestation starts worshipping the Creator (%) |
| manifest_message_max_chars | tezahur_uzunluk | 600 | 50 | 5000 | The god's power | Maximum length of the words spoken in a manifestation (characters) |
| bloodline_curse_cost | soy_laneti | 40 | 0 | 1000 | The god's power | Cost of cursing a bloodline |
| bloodline_curse_lift_cost | soy_laneti_kaldir | 20 | 0 | 1000 | The god's power | Cost of lifting a bloodline's curse |
| bloodline_curse_depth | soy_derinlik | 6 | 1 | 50 | The god's power | How many generations down a bloodline curse reaches |
| bloodline_curse_stat_loss | soy_stat | 10 | 0 | 100 | The god's power | Strength, prosperity and similar removed from each cursed member by a bloodline curse |
| convert_cost | cevir | 30 | 0 | 1000 | The god's power | Cost of converting a community to yourself (it leaves its previous god) |
| convert_patron_loyalty_loss | cevir_kin | 10 | 0 | 100 | The god's power | Loyalty loss of the son whose worshipper is taken away |
| wrath_base_cost | gazap_taban | 60 | 0 | 5000 | The god's power | Wrath: base cost of destroying a record |
| wrath_cost_per_power | gazap_guc | 5 | 0 | 1000 | The god's power | Wrath: extra cost per power level |
| wrath_death_chance | gazap_olum | 70 | 0 | 100 | The god's power | Wrath: chance named mortals at the destroyed place die (%) |
| world_wrath_cost | dunya_gazap | 200 | 0 | 10,000 | The god's power | Cost of bringing wrath upon an entire world |
| world_wrath_severity | dunya_gazap_siddet | 60 | 1 | 100 | The god's power | Severity of the disaster striking each region in world wrath (%) |
| auto_drain_wrath | oto_em_ofke | 70 | 0 | 100 | The god's power | When the Creator's wrath exceeds this, it may automatically drain the essence of rebel sons |
| auto_drain_chance | oto_em_sans | 30 | 0 | 100 | The god's power | Chance in one epoch that a wrathful Creator drains a rebel son's essence (%) |
| auto_drain_loyalty | oto_em_sadakat | 20 | 0 | 100 | The god's power | If there are no rebel sons, the wrathful Creator may drain the most defiant son with loyalty below this |
| auto_rebel_loyalty | oto_isyan_sadakat | 15 | 0 | 100 | The god's power | A son whose loyalty fell below this may rebel on his own |
| auto_rebel_wrath | oto_isyan_ofke | 60 | 0 | 100 | The god's power | Minimum wrath of a son for spontaneous rebellion |
| auto_rebel_chance | oto_isyan_sans | 20 | 0 | 100 | The god's power | Chance in one epoch that a son meeting the conditions rebels on his own (%) |
| auto_return_loyalty | oto_donus_sadakat | 50 | 0 | 100 | The god's power | A rebel son whose loyalty rises back to this may return to his father on his own |
| auto_return_chance | oto_donus_sans | 25 | 0 | 100 | The god's power | Chance in one epoch that a rebel son with restored loyalty abandons the rebellion (%) |
| auto_curse_epochs | oto_lanet_cag | 3 | 0 | 100 | The god's power | Whoever kills a prophet or a Creator worshipper becomes a candidate for a spontaneous bloodline curse within this many epochs |
| auto_curse_chance | oto_lanet_sans | 30 | 0 | 100 | The god's power | Chance in one epoch that the bloodline of the bloody hand is cursed automatically (%) |
| auto_curse_wrath | oto_lanet_ofke | 55 | 0 | 100 | The god's power | When the Creator's wrath exceeds this, it may automatically curse the bloodline of a cursed, temple-razing or many-lives-taking mortal |
| auto_curse_min_kills | oto_lanet_kanli | 2 | 0 | 100 | The god's power | The wrathful Creator may also curse the bloodline of a mortal who took at least this many lives (0: off) |
| auto_curse_wrath_chance | oto_lanet_ofke_sans | 15 | 0 | 100 | The god's power | Chance in one epoch that the wrathful Creator automatically curses a cursed bloodline (%) |
| auto_prophet_contentment | oto_peygamber_hosnut | 70 | 0 | 100 | The god's power | When the Creator's contentment exceeds this, it may automatically choose one of its cult's devotees as prophet |
| auto_prophet_chance | oto_peygamber_sans | 20 | 0 | 100 | The god's power | Chance in one epoch that a content Creator automatically chooses a prophet (%) |
| auto_prophet_cap | oto_peygamber_tavan | 2 | 0 | 100 | The god's power | When living prophets reach this number the Creator does not automatically choose a new one (0: never automatically) |
| auto_candidates | oto_aday | 4 | 1 | 100 | The god's power | In automatic choice, picked by dice from this many best candidates |

### GUIDE

Old namespace `REHBER` · 5 rows · defined in `src/kodeks.js`. Codex/guide listing thresholds.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| dangerous_place | tehlikeli_yer | 55 | 0 | 100 | Codex and guide | Guide: danger of a region or place counted as dangerous |
| dangerous_species | tehlikeli_tur | 50 | 0 | 100 | Codex and guide | Guide: danger of a species counted as a predator |
| leak_threshold | sizinti | 30 | 0 | 100 | Codex and guide | Guide: level at which leak counts as a danger |
| danger_list | tehlike_liste | 6 | 0 | 100 | Codex and guide | Guide: listed from each danger type |
| people_list | halk_liste | 14 | 0 | 500 | Codex and guide | Guide: most populous communities listed |

### IMAGE_GEN

Old namespace `GORSEL_URET` · 10 rows · defined in `src/gorsel-uret.js`. Local image generation worker.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| width | genislik | 720 | 256 | 2048 | Image generation | Width of the generated image (px) |
| height | yukseklik | 720 | 256 | 2048 | Image generation | Height of the generated image (px) |
| steps | adim | 4 | 1 | 50 | Image generation | Denoising steps per image (few: fast, many: detailed) |
| auto | oto | 1 | 0 | 1 | Image generation | At epoch end, automatically start generation for all records without an image (0 off) |
| idle_unload_seconds | bosta_kapat_sn | 600 | 0 | 86,400 | Image generation | Time for an idle image worker to release the model from memory (s; 0 never releases) |
| startup_timeout_seconds | acilis_sn | 300 | 10 | 3600 | Image generation | Maximum wait for the image worker to load the model (s) |
| image_timeout_seconds | zaman_asimi_sn | 300 | 10 | 3600 | Image generation | Maximum time for a single image (s); if exceeded the worker is restarted |
| retries | yeniden_dene | 1 | 0 | 5 | Image generation | Retry a failed image in batch generation |
| log_lines | gunluk_satir | 200 | 20 | 5000 | Image generation | Lines kept in the image-generation log |
| error_lines | hata_satir | 20 | 1 | 500 | Image generation | Last worker-output lines shown in the error if the worker crashes |

### INTERVENTION_COSTS

Old namespace `MUDAHALE_BEDEL` · 4 rows · defined in `src/rules.js` · also read by `src/denge.js`, `src/epoch.js`, `src/tools.js`. Creator's intervention costs — static object in rules.js.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| miracle | mucize | 15 | 0 | 300 | Interventions in the mortal world | Miracle |
| disaster | afet | 20 | 0 | 300 | Interventions in the mortal world | Disaster |
| teach_knowledge | bilgi | 12 | 0 | 300 | Interventions in the mortal world | Teach knowledge |
| curse | lanet | 15 | 0 | 300 | Interventions in the mortal world | Curse (son) |

### INTERVENTION_EFFECTS

Old namespace `MUDAHALE` · 33 rows · defined in `src/mudahale.js`, `src/rules.js`. Effects of miracles, disasters and taught knowledge.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| knowledge_spread_gain | bilgi_yayginlik | 8 | 0 | 100 | Intervention | Spread increase of taught knowledge |
| astronomy_disaster_severity | gokbilim_siddet | 50 | 0 | 100 | Intervention | Disaster severity for those who know astronomy (%) |
| earthquake_population_loss | deprem_nufus | 10 | 0 | 100 | Intervention | Earthquake: population loss (%) |
| earthquake_durability_loss | deprem_saglamlik | 25 | 0 | 100 | Intervention | Earthquake: durability loss of structures |
| architecture_quake_severity | mimarlik_siddet | 50 | 0 | 100 | Intervention | Earthquake severity on structures of those who know architecture (%) |
| flood_prosperity_loss | sel_refah | 12 | 0 | 100 | Intervention | Flood: prosperity loss |
| flood_population_loss | sel_nufus | 5 | 0 | 100 | Intervention | Flood: population loss (%) |
| flood_fertility_after | sel_bereket | 5 | 0 | 100 | Intervention | Flood: fertility gained afterwards |
| plague_population_loss | veba_nufus | 18 | 0 | 100 | Intervention | Plague: population loss (%) |
| plague_follower_loss | veba_murit | 10 | 0 | 100 | Intervention | Plague: follower loss (%) |
| medicine_plague_severity | tip_siddet | 50 | 0 | 100 | Intervention | Plague severity for those who know medicine (%) |
| drought_fertility_loss | kuraklik_bereket | 20 | 0 | 100 | Intervention | Drought: fertility loss |
| drought_population_loss | kuraklik_nufus | 6 | 0 | 100 | Intervention | Drought: population loss (%) |
| agriculture_drought_severity | tarim_siddet | 50 | 0 | 100 | Intervention | Drought severity for those who know agriculture (%) |
| storm_defense_loss | firtina_savunma | 10 | 0 | 100 | Intervention | Storm: defense loss |
| storm_prosperity_loss | firtina_refah | 8 | 0 | 100 | Intervention | Storm: prosperity loss |
| healing_growth_pct | sifa_artis | 10 | 0 | 1000 | Intervention | Healing miracle: population and follower increase (%) |
| healing_hp | sifa_can | 100 | 1 | 100,000 | Intervention | Healing miracle: value a mortal's HP is raised to |
| bounty_fertility_gain | bereket_bereket | 20 | 0 | 100 | Intervention | Bounty miracle: land fertility increase |
| bounty_prosperity_gain | bereket_refah | 15 | 0 | 100 | Intervention | Bounty miracle: prosperity increase for targets without fertility |
| bounty_abundance_gain | bereket_bolluk | 25 | 0 | 100 | Intervention | Bounty miracle: resource abundance increase |
| protection_defense_gain | koruma_savunma | 20 | 0 | 100 | Intervention | Protection miracle: defense increase |
| resurrection_cult_devotion_gain | dirilis_adanmislik | 25 | 0 | 200 | Intervention | Devotion increase from a miracle landing on a resurrection cult |
| disaster_event_power_divisor | olay_guc_bolen | 12 | 1 | 100 | Intervention | Power level of a disaster event: severity / this number |
| disaster_event_power_min | olay_guc_alt | 2 | 1 | 12 | Intervention | Minimum power level of a disaster event |
| disaster_event_power_max | olay_guc_ust | 9 | 1 | 12 | Intervention | Maximum power level of a disaster event |
| earthquake_mortal_death_chance | deprem_olumlu_olum | 12 | 0 | 100 | Intervention | Earthquake: chance a named mortal where it strikes dies (%) |
| flood_mortal_death_chance | sel_olumlu_olum | 8 | 0 | 100 | Intervention | Flood: chance a named mortal dies (%) |
| plague_mortal_death_chance | veba_olumlu_olum | 15 | 0 | 100 | Intervention | Plague: chance a named mortal dies (%; medicine mitigates) |
| drought_mortal_death_chance | kuraklik_olumlu_olum | 4 | 0 | 100 | Intervention | Drought: chance a named mortal dies (%) |
| storm_mortal_death_chance | firtina_olumlu_olum | 5 | 0 | 100 | Intervention | Storm: chance a named mortal dies (%) |
| disaster_injury_chance | afet_yara_sans | 30 | 0 | 100 | Intervention | Chance a named mortal surviving a disaster is injured (%) |
| disaster_injury_hp | afet_yara | 25 | 0 | 1000 | Intervention | HP lost by an injured mortal (scaled by severity) |

### LANGUAGE

Old namespace `DIL` · 46 rows · defined in `src/dilmotoru.js`, `src/world.js` · also read by `src/agents.js`. Name generation, language signatures, tired-motif detection, dialect checks.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| similar_name_max_length | benzer_uzunluk | 7 | 0 | 20 | Language and names | Longest name for which a single-letter difference is forbidden (letters) |
| name_family_cap | aile_tavani | 3 | 1 | 50 | Language and names | Maximum names starting with the same root (first letters, see root letters) |
| motif_threshold_pct | motif_esik | 18 | 1 | 100 | Language and names | Tired motif: if it appears in this percentage of recent descriptions |
| motifs_in_prompt | motif_sayisi | 14 | 0 | 60 | Language and names | Tired motifs shown in the prompt |
| motif_window | motif_pencere | 120 | 15 | 2000 | Language and names | Recent descriptions examined for tired motifs |
| motif_root_max_letters | motif_kok | 5 | 1 | 30 | Language and names | Tired motif: maximum letters of the compared word root (after suffixes are stripped) |
| motif_pair_threshold_pct | motif_cift_esik | 15 | 1 | 100 | Language and names | Tired image: if a two-word image appears in this percentage of recent deepenings and epoch narratives |
| motif_suffix_strip_steps | motif_ek_adim | 3 | 0 | 10 | Language and names | Tired motif: maximum suffixes stripped from a word in a row |
| motif_root_min_letters | motif_kok_en_kisa | 3 | 1 | 20 | Language and names | Tired motif: minimum letters of the root left after suffix stripping; shorter words are not counted either |
| motif_narratives | motif_anlati | 5 | 0 | 100 | Language and names | Tired motif: recent epoch narratives examined |
| motif_min_repeats | motif_en_az | 6 | 1 | 1000 | Language and names | Tired motif: minimum repetitions |
| motif_min_records | motif_en_az_kayit | 15 | 1 | 2000 | Language and names | Tired motif: minimum descriptions before checking starts |
| root_letters | kok_harf | 4 | 1 | 20 | Language and names | Name family and common root: letters compared from the start |
| motif_cache_per_world | motif_onbellek | 16 | 1 | 1000 | Language and names | Tired motif: measurements cached per world |
| native_word_window | turkce_pencere | 3000 | 10 | 100,000 | Language and names | Dialect check: recent descriptions examined to separate real (Turkish) words |
| native_word_min_count | turkce_en_az | 3 | 1 | 1000 | Language and names | Dialect check: a word appearing lowercase in prose at least this many times is a real (Turkish) word, not an invented root |
| dialect_root_min_letters | lehce_kok_en_az | 3 | 1 | 20 | Language and names | Dialect check: minimum letters of an invented root examined |
| signature_consonant_pct | imza_unsuz | 62 | 10 | 100 | Language and names | Language signature: share chosen from the world's consonants (%) |
| signature_ending_pct | imza_son | 50 | 0 | 100 | Language and names | Chance names end with the language's own ending (%) |
| signature_cluster_pct | imza_kume | 30 | 0 | 100 | Language and names | Chance the language's favourite consonant cluster appears in names (%) |
| name_attempts | ad_deneme | 24 | 1 | 200 | Language and names | Maximum attempts in one name generation |
| epoch_words_per_language | kelime_dil_basi | 3 | 0 | 50 | Language and names | Epoch words: maximum per language |
| epoch_words_total | kelime_toplam | 12 | 0 | 200 | Language and names | Epoch words: maximum in total |
| alphabet_min_samples | alfabe_en_az | 60 | 1 | 100,000 | Language and names | World alphabet: minimum letter samples before filtering starts |
| alphabet_min_per_mille | alfabe_binde | 5 | 0 | 1000 | Language and names | World alphabet: minimum frequency for a letter to count in the alphabet (per mille) |
| dialect_sample_names | lehce_ornek | 30 | 0 | 500 | Language and names | Maximum sample names taken from the dialect text |
| ancestry_depth | soy_derinlik | 3 | 0 | 20 | Language and names | Ancestor-language generations included in the phonology |
| phonology_min_words | kelime_en_az | 8 | 0 | 200 | Language and names | Minimum sample words for the phonology (if fewer, filled from names) |
| phonology_max_syllables | hece_en_cok | 6 | 1 | 30 | Language and names | Maximum syllables of a word entering the phonology |
| default_avg_syllables | ort_hece | 24 | 10 | 100 | Language and names | Average syllables if there are no samples (tenths) |
| signature_min_consonants | imza_en_az_unsuz | 3 | 1 | 30 | Language and names | Minimum consonants for a language signature |
| signature_kept_consonants | imza_kalici_unsuz | 2 | 0 | 30 | Language and names | Most frequent consonants always kept in the language signature |
| signature_consonant_floor | imza_unsuz_en_az | 5 | 1 | 30 | Language and names | Minimum consonants in the language signature |
| signature_ending_max_letters | imza_ek_harf | 4 | 1 | 20 | Language and names | Maximum letters of the language signature's ending |
| inherited_shift_min_consonants | imza_miras_unsuz | 3 | 0 | 30 | Language and names | Minimum consonants for a consonant shift in an inherited signature |
| ugly_same_onset_syllables | cirkin_ayni_bas | 3 | 2 | 20 | Language and names | Ugly name: number of syllables starting with the same consonant |
| name_min_syllables | ad_hece_en_az | 2 | 1 | 10 | Language and names | Minimum syllables of a generated name |
| name_max_syllables | ad_hece_en_cok | 4 | 1 | 20 | Language and names | Maximum syllables of a generated name |
| person_syllable_bias | hece_kisi | -3 | -50 | 50 | Language and names | Syllable tendency in person names (tenths) |
| place_syllable_bias | hece_yer | 4 | -50 | 50 | Language and names | Syllable tendency in place and people names (tenths) |
| syllable_repeat_retries | hece_tekrar_deneme | 4 | 0 | 50 | Language and names | Re-picks to avoid the same syllable twice in a row |
| name_min_letters | ad_harf_en_az | 3 | 1 | 30 | Language and names | Minimum letters of a generated name |
| name_max_letters | ad_harf_en_cok | 12 | 1 | 60 | Language and names | Maximum letters of a generated name |
| max_cognates | kognat_en_cok | 30 | 0 | 1000 | Language and names | Maximum common roots (cognates) shown between two languages |
| local_language_depth | yerel_dil_derinlik | 6 | 1 | 50 | Language and names | Depth of the location chain searched for a local language for the epoch word |
| epoch_word_min_letters | kelime_harf_en_az | 3 | 1 | 30 | Language and names | Minimum letters of an epoch word |

### LEDGER

Old namespace `DEFTER` · 1 rows · defined in `src/defter.js`. Action ledger retention.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| keep_epochs | sakla_cag | 6 | 1 | 200 | Records | Epochs kept in the action ledger |

### LIMITS

Old namespace `SINIR` · 7 rows · defined in `src/rules.js` · also read by `src/derin.js`, `src/ekonomi.js`, `src/gok.js`, `src/hedef.js`, `src/itibar.js`, `src/korku.js`, `src/medeniyet.js`, `src/mudahale.js`, `src/olum.js`, `src/olumluler.js`, `src/otesi.js`, `src/panteon.js`, `src/seyahat.js`, `src/sim.js`, `src/ufuk.js`, `src/yaratici.js`, `src/yaratik.js`. Global stat caps and floors.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| population_floor | nufus_taban | 10 | 1 | 100,000 | Population and growth | Minimum population of settlements and communities |
| people_population_floor | halk_nufus_taban | 100 | 1 | 1,000,000 | Population and growth | Minimum population of a people |
| settlement_population_cap | kent_nufus_tavan | 2,000,000 | 1000 | 1,000,000,000 | Population and growth | Maximum population of a settlement |
| people_population_cap | nufus_tavan | 50,000,000 | 1000 | 2,000,000,000 | Population and growth | Maximum population of a people |
| cult_follower_cap | murit_tavan | 10,000,000 | 1000 | 2,000,000,000 | Religion and language | Maximum followers of a cult |
| army_soldier_cap | ordu_tavan | 10,000,000 | 1000 | 2,000,000,000 | War and diplomacy | Maximum soldiers in an army |
| hp_cap | can_tavan | 300 | 10 | 100,000 | Heroes and mortals | Maximum HP of a mortal or creature |

### LINK_GRAPH

Old namespace `AG` · 20 rows · defined in `src/agonar.js` · also read by `src/epoch.js`. Link-graph (entity network) repair, incl. Fate-proposed links.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| auto_repair | oto_onar | 1 | 0 | 1 | Link graph | Dangling ends are repaired automatically at epoch end (1 on, 0 off) |
| fate_auto | kader_oto | 1 | 0 | 1 | Link graph | At epoch end Fate proposes justified links for weakly linked records and names vague links (1 on, 0 off) |
| weak_degree | zayif_derece | 1 | 0 | 100 | Link graph | A record with this many links or fewer counts as weakly linked |
| fate_batch | kader_parti | 12 | 1 | 200 | Link graph | Fate proposes links for at most this many records per request |
| fate_epoch_cap | kader_cag_tavan | 36 | 0 | 100,000 | Link graph | Maximum weak records Fate examines at epoch end |
| candidates | aday | 10 | 1 | 100 | Link graph | Number of candidate neighbours shown to Fate per record |
| proposal_cap | oneri_tavan | 3 | 1 | 20 | Link graph | Fate creates at most this many new links for one record at a time |
| reason_min_chars | gerekce_en_az | 15 | 0 | 1000 | Link graph | Minimum length of Fate's link justification (characters); shorter ones are rejected |
| companion_reason_min_chars | yoldas_gerekce_en_az | 40 | 0 | 1000 | Link graph | Minimum length of Fate's "companion" link justification (characters): companionship must describe something lived together |
| companion_reason_min_words | yoldas_sozcuk_en_az | 6 | 0 | 100 | Link graph | Minimum word count of Fate's "companion" link justification |
| revisit_epochs | tekrar_cag | 10 | 0 | 10,000 | Link graph | A record Fate examined is re-examined at the earliest after this many epochs |
| related_batch | ilgili_parti | 40 | 1 | 1000 | Link graph | Fate names at most this many unexplained "related" links per request |
| related_epoch_cap | ilgili_cag_tavan | 80 | 0 | 100,000 | Link graph | Maximum unexplained "related" links named at epoch end |
| description_trim_chars | aciklama_kirp | 300 | 50 | 10,000 | Link graph | Length of a record description shown to Fate (characters) |
| summary_list | liste | 20 | 1 | 1000 | Link graph | Number of weakest records and recent repairs listed in the connectivity summary |
| name_min_chars | ad_en_az | 4 | 1 | 100 | Link graph | Minimum length of a name for linking a record whose name appears in text (short names mismatch) |
| event_proposal_cap | olay_oneri_tavan | 8 | 1 | 100 | Link graph | Fate creates at most this many links at a time for an event much mentioned in the chronicle (war, disaster participants) |
| priority_share_pct | oncelik_payi | 50 | 0 | 100 | Link graph | Share reserved on each Fate pass for events, legends and traditions mentioned in the chronicle but not linked (%) |
| subject_cap | konu_tavan | 5 | 0 | 100 | Link graph | At most this many subjects named in its description are linked to a legend, tradition or artwork |
| main_cluster_healthy_pct | ana_obek_iyi | 95 | 0 | 100 | Link graph | Connectivity is shown as healthy when the main cluster exceeds this percentage of nodes |

### METRICS

Old namespace `OLCUM` · 3 rows · defined in `src/olcum.js`. Model-call metrics.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| slow_call_seconds | yavas_sn | 120 | 5 | 3600 | Records | A model call exceeding this many seconds counts as slow |
| keep_epochs | sakla_cag | 100 | 1 | 10,000 | Records | Epochs kept in model metrics |
| eta_average_epochs | ortalama_cag | 6 | 1 | 1000 | Records | Remaining-time estimate: number of recent epochs averaged |

### MODEL

Old namespace `MODEL` · 14 rows · defined in `src/llm.js`. LLM call retries, timeouts, continuation.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| retry_attempts | deneme | 3 | 1 | 10 | Agents and model | Total attempts on a transient model error (if the caller gives no rule of its own) |
| retry_wait_1 | bekle_1 | 2 | 0 | 600 | Agents and model | Wait before retrying: after the 1st error (s) |
| retry_wait_2 | bekle_2 | 6 | 0 | 600 | Agents and model | Wait before retrying: after the 2nd error (s) |
| retry_wait_3 | bekle_3 | 15 | 0 | 600 | Agents and model | Wait before retrying: after the 3rd and later errors (s) |
| structured_timeout | yapisal_sure | 300 | 10 | 3600 | Agents and model | Default timeout of a structured model call (s) |
| structured_max_steps | yapisal_adim | 8 | 1 | 20 | Agents and model | Maximum model steps in a structured call |
| agent_timeout | ajan_sure | 420 | 30 | 3600 | Agents and model | Default timeout of an agent turn (s) |
| agent_max_steps | ajan_adim | 10 | 1 | 100 | Agents and model | Default step limit of an agent turn |
| sessions_per_turn_cap | tur_tavan | 6 | 1 | 30 | Agents and model | Maximum sessions in one agent turn (including restarts and continuations) |
| restart_attempts | bastan | 2 | 0 | 10 | Agents and model | Number of restarts for a turn that crashed without leaving a trace |
| restart_wait | bastan_bekle | 3 | 0 | 600 | Agents and model | Wait before a restart (s; multiplied by the attempt number) |
| max_continuations | devam | 2 | 0 | 10 | Agents and model | Maximum continuation sessions for an interrupted turn |
| continuation_wait | devam_bekle | 3 | 0 | 600 | Agents and model | Wait before a continuation session after a connection error (s) |
| continuation_action_summary_chars | ozet_karakter | 220 | 40 | 5000 | Context budgets | Summary of each performed action in the continuation prompt (characters) |

### MORTAL_AGENTS

Old namespace `OLUMLU_AJAN` · 4 rows · defined in `src/rules.js` · also read by `src/denge.js`, `src/epoch.js`, `src/olumluler.js`. Mortal agent counts and limits — static object in rules.js.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| action_points | ap | 3 | 1 | 6 | Mortal agents | Mortal action points |
| agents_per_epoch | varsayilan | 4 | 0 | 1000 | Mortal agents | Mortal agents per epoch |
| max_turns | maxTurns | 12 | 4 | 20 | Mortal agents | Mortal turn limit (steps) |
| creature_min_intelligence | zeka_esigi | 55 | 0 | 100 | Mortal agents | Minimum intelligence for a creature to play as an agent |

### MORTAL_TOOLS

Old namespace `OLUMLU_ARAC` · 223 rows · defined in `src/olumluler.js` · also read by `src/etiket-onar.js`, `src/ufuk.js`. Mortal agent tool parameters.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| coin_word_per_epoch | kelime_tur | 2 | 0 | 20 | Language and names | Mortal: coin_word (kelime_tureti) per epoch |
| coin_word_max_words | kelime_adet | 8 | 1 | 40 | Language and names | Mortal: maximum words per call |
| route_threshold | rota_esik | 55 | 0 | 200 | Mortal agents | discover_route (rota_kesfet): route-finding die threshold (d100 + intellect/3) |
| unknown_world_threshold | bilinmeyen_esik | 85 | 0 | 200 | Mortal agents | discover_route: threshold for discovering an unknown world |
| preach_follower_gain_pct | vaaz_murit | 15 | 0 | 200 | Mortal agents | Follower increase of a successful sermon (%) |
| escape_max_pct | kac_tavan | 85 | 0 | 100 | Mortal agents | Cap of a captive's escape chance (%) |
| escape_caught_wound | kac_yara | 15 | 0 | 500 | Mortal agents | Wound of a captive caught while escaping |
| ransom_amount | fidye | 12 | 0 | 100 | Mortal agents | Wealth/prosperity changing hands in a ransom |
| ransom_min_wealth | fidye_esik | 20 | 0 | 100 | Mortal agents | Minimum wealth required for a ransom (+5 for prosperity) |
| raise_army_default_pct | ordu_yuzde | 5 | 1 | 50 | Mortal agents | raise_army (ordu_topla): default levy (% of population) |
| raise_army_max_pct | ordu_tavan | 15 | 1 | 100 | Mortal agents | raise_army: maximum levy (% of population) |
| ~~raise_army_population_pct~~ | ordu_kayip | — | — | — | Mortal agents | Removed by spec 13 F28: an army levies exactly the soldiers it holds, so headcount is conserved |
| ctx_self_chars | sen_butce | 3500 | 500 | 100,000 | Context budgets | Mortal context: own details (characters) |
| barter_ap | takas_ap | 1 | 1 | 5 | Mortal agents | barter (takas) action cost |
| barter_die | takas_zar | 30 | 1 | 200 | Mortal agents | barter: acceptance die faces (offer + relation + die ≥ asked) |
| barter_relation_scale | takas_iliski_olcek | 4 | 1 | 100 | Mortal agents | barter: every this many relation points add +1 value to acceptance |
| barter_relation | takas_iliski | 8 | 0 | 100 | Mortal agents | Relation contribution of a successful barter |
| barter_reject_relation | takas_red_iliski | 3 | 0 | 100 | Mortal agents | Relation damage of a rejected barter |
| debt_ap | borc_ap | 1 | 1 | 5 | Mortal agents | lend / repay (borc_ver / borc_ode) action cost |
| debt_max_amount | borc_tavan | 30 | 1 | 100 | Mortal agents | Maximum amount in a single debt |
| debt_default_term | borc_vade | 3 | 1 | 50 | Mortal agents | Default debt term (epochs) |
| debt_max_term | borc_vade_tavan | 12 | 1 | 100 | Mortal agents | Longest debt term (epochs) |
| debt_lend_relation | borc_iliski | 5 | 0 | 100 | Mortal agents | Relation contribution of lending |
| debt_repay_relation | borc_ode_iliski | 8 | 0 | 100 | Mortal agents | Relation contribution of a repaid debt |
| adopt_ap | evlat_ap | 1 | 1 | 5 | Mortal agents | adopt (evlat_edin) action cost |
| adopt_relation | evlat_iliski | 10 | 0 | 100 | Mortal agents | Relation contribution of adoption |
| discover_resource_per_epoch | kesif_tur | 1 | 0 | 20 | Mortal agents | discover_resource (kaynak_kesfet): maximum discoveries by one mortal per epoch |
| chronicle_named_communities | liste_ad | 4 | 1 | 100 | Context budgets | Maximum communities named in a chronicle line (the rest as "and N more communities") |
| seizure_relation_loss | el_koyma_iliski | 25 | 0 | 200 | War and diplomacy | Relation loss of a community whose resource is seized toward the seizer (when war cannot be declared) |
| ctx_character_chars | karakter_butce | 1500 | 100 | 50,000 | Context budgets | Mortal context: character and way-of-life section (characters) |
| ctx_event_lines | olay_satir | 12 | 1 | 200 | Context budgets | Mortal context: lines of recent events |
| claim_per_epoch | sahiplen_tur | 1 | 0 | 20 | Mortal agents | claim (sahiplen): maximum claims per epoch |
| worship_per_epoch | tapin_tur | 1 | 0 | 20 | Religion and language | worship (tapin): maximum worships or god changes per epoch |
| pray_creator_per_epoch | dua_tur | 1 | 0 | 20 | Religion and language | pray_to_creator (yaraticiya_dua): maximum prayers per epoch |
| learn_per_epoch | ogren_tur | 1 | 0 | 20 | Mortal agents | learn (ogren): maximum knowledge learned per epoch |
| prophesy_per_epoch | kehanet_tur | 1 | 0 | 20 | Mortal agents | prophesy (kehanet_et): maximum prophecies per epoch |
| appoint_commander_per_epoch | komutan_tur | 1 | 0 | 20 | War and diplomacy | appoint_commander (komutan_ata): maximum commander appointments per epoch |
| adopt_per_epoch | evlat_tur | 1 | 0 | 20 | Mortal agents | adopt: maximum adoptions per epoch |
| unknown_world_per_epoch | bilinmeyen_dunya_tur | 1 | 0 | 20 | Cosmos and travel | discover_route: maximum new-world discoveries in the cosmos per epoch (worlds born another way that epoch also count) |
| agent_power_weight | ajan_guc_kat | 2 | 0 | 1000 | Mortal agents | Agent selection: score multiplier of power level |
| agent_population_weight | ajan_nufus_kat | 2 | 0 | 1000 | Mortal agents | Agent selection: score multiplier of log10(population or followers) |
| agent_default_crowd | ajan_nufus_varsayilan | 100 | 10 | 100,000,000 | Mortal agents | Agent selection: crowd size assumed for one with no recorded population or followers |
| agent_wait_weight | ajan_bekleme_kat | 2 | 0 | 1000 | Mortal agents | Agent selection: score per epoch passed without acting (limited by MORTAL_TOOLS.agent_wait_cap) |
| preach_default_piety | vaaz_inanc_varsayilan | 50 | 0 | 100 | Religion and language | Sermon: piety assumed for a target with no recorded piety |
| commander_default_morale | komutan_moral_varsayilan | 50 | 0 | 100 | War and diplomacy | appoint_commander: morale assumed for an army with no recorded morale |
| cult_min_followers_kept | murit_taban | 1 | 1 | 100,000 | Population and growth | found_settlement / raise_army: minimum followers remaining in the cult |
| mercenary_cost | ordu_parali_servet | 10 | 0 | 100 | War and diplomacy | raise_army: wealth/prosperity cost of a mercenary army for a community with no population or followers |
| default_stat | stat_varsayilan | 40 | 0 | 100 | Mortal agents | Mortal tools: stat assumed for a party with no recorded stat (craft, intellect, strength, defense…) |
| agent_chosen_bonus | ajan_secilmis | 4 | 0 | 1000 | Mortal agents | Agent selection: score bonus of a chosen mortal |
| agent_wait_cap | ajan_bekleme_tavan | 30 | 0 | 1000 | Mortal agents | Agent selection: maximum score from not having acted for a long time |
| agent_random_die | ajan_zar | 10 | 1 | 1000 | Mortal agents | Agent selection: faces of the random score die |
| agent_dream_bonus | ajan_ruya | 40 | 0 | 1000 | Mortal agents | Agent selection: score bonus for one with a pending dream |
| agent_type_share_divisor | ajan_tur_pay | 3 | 1 | 100 | Mortal agents | Agent selection: a single type gets at most 1/this of the agent count (diversity) |
| ctx_nearby_chars | yakin_butce | 2500 | 200 | 50,000 | Context budgets | Mortal context: those nearby (characters) |
| ctx_knowledge_chars | bilgi_butce | 1200 | 200 | 50,000 | Context budgets | Mortal context: knowledge in the world (characters) |
| ctx_mentions_chars | ani_butce | 1500 | 200 | 50,000 | Context budgets | Mortal context: records mentioning you (characters) |
| ctx_languages_chars | dil_butce | 1500 | 200 | 50,000 | Context budgets | Mortal context: the world's languages (characters) |
| ctx_events_chars | olay_butce | 1800 | 200 | 50,000 | Context budgets | Mortal context: recent events (characters) |
| creation_power_pct | guc_oran | 80 | 1 | 100 | Mortal agents | Power level of a mortal creation: percentage of the creator's power |
| creation_power_cap | guc_tavan | 8 | 1 | 30 | Mortal agents | Maximum power level of a mortal creation |
| language_spread | dil_yayginlik | 20 | 0 | 100 | Religion and language | Spread of a language founded by a mortal |
| dialect_spread | dil_lehce_yayginlik | 8 | 0 | 100 | Religion and language | Spread of a dialect founded by a single mortal |
| language_complexity | dil_karmasiklik | 40 | 0 | 100 | Religion and language | Complexity of a language founded by a mortal |
| language_sacredness | dil_kutsallik | 20 | 0 | 100 | Religion and language | Sacredness of a language founded by a mortal |
| craft_max_resources | uret_kaynak_adet | 3 | 1 | 20 | Mortal agents | Maximum resources used in one production |
| craft_min_abundance | uret_bolluk_esik | 10 | 0 | 100 | Mortal agents | Production: a resource below this abundance cannot be used |
| craft_abundance_loss | uret_bolluk_kayip | 10 | 0 | 100 | Mortal agents | Abundance loss of a resource used in production |
| craft_metallurgy_bonus | uret_metalurji | 15 | 0 | 100 | Mortal agents | Weapon/armor bonus for those who know metallurgy |
| craft_magic_bonus | uret_buyu | 10 | 0 | 100 | Mortal agents | Item might bonus for those who know magic |
| craft_region_magic_divisor | uret_bolge_buyu_bolen | 8 | 1 | 1000 | Mortal agents | Item might: + region's magic / this number |
| craft_skill_pct | uret_zanaat | 50 | 0 | 300 | Mortal agents | Weapon/armor value: percentage of craft |
| craft_resource_might_pct | uret_kudret | 40 | 0 | 300 | Mortal agents | Weapon/armor value: percentage of the resources' average might |
| craft_die | uret_zar | 15 | 1 | 100 | Mortal agents | Die faces of weapon/armor value |
| craft_min_value | uret_en_az | 5 | 0 | 100 | Mortal agents | Minimum damage/protection of a weapon/armor |
| craft_side_die | uret_yan_zar | 10 | 1 | 100 | Mortal agents | Damage of a non-weapon, protection of a non-armor: die faces |
| craft_item_might_pct | uret_kudret_orani | 60 | 0 | 300 | Mortal agents | Item might: percentage of the resources' average might |
| craft_item_might_die | uret_kudret_zar | 20 | 1 | 100 | Mortal agents | Die faces of item might |
| craft_curse_die | uret_lanet_zar | 12 | 1 | 100 | Mortal agents | Item's curse: die faces |
| craft_curse_shift | uret_lanet_eksi | 4 | 0 | 100 | Mortal agents | Item's curse: subtracted from the die |
| craft_masterwork | uret_usta | 60 | 0 | 200 | Mortal agents | If damage + protection is at or above this, the item enters the chronicle as "masterwork" |
| craft_sturdy | uret_saglam | 30 | 0 | 200 | Mortal agents | If damage + protection is at or above this, the item enters the chronicle as "sturdy" |
| build_splendor_pct | insa_ihtisam | 70 | 0 | 300 | Mortal agents | Structure splendor: percentage of craft |
| build_splendor_die | insa_ihtisam_zar | 25 | 1 | 100 | Mortal agents | Structure splendor: die faces |
| build_durability_pct | insa_saglamlik | 60 | 0 | 300 | Mortal agents | Structure durability: percentage of craft |
| build_durability_die | insa_saglamlik_zar | 30 | 1 | 100 | Mortal agents | Structure durability: die faces |
| build_architecture_bonus | insa_mimarlik | 20 | 0 | 100 | Mortal agents | Splendor and durability bonus for those who know architecture |
| build_function_base | insa_islev_taban | 40 | 0 | 100 | Mortal agents | Structure function: base |
| build_function_die | insa_islev_zar | 40 | 1 | 100 | Mortal agents | Structure function: die faces |
| build_cost | insa_bedel | 4 | 0 | 100 | Mortal agents | Prosperity and wealth removed by construction |
| culture_max_related | kultur_ilgili_adet | 4 | 0 | 20 | Mortal agents | Maximum related entities in a culture creation |
| artwork_base | eser_taban | 20 | 0 | 100 | Mortal agents | Artwork renown and influence: base |
| artwork_die | eser_zar | 40 | 1 | 100 | Mortal agents | Artwork renown and influence: die faces |
| law_rigidity_base | kanun_katilik_taban | 30 | 0 | 100 | Mortal agents | Law rigidity: base |
| law_rigidity_die | kanun_katilik_zar | 60 | 1 | 100 | Mortal agents | Law rigidity: die faces |
| law_justice_base | kanun_adalet_taban | 20 | 0 | 100 | Mortal agents | Law justice: base |
| law_justice_die | kanun_adalet_zar | 70 | 1 | 100 | Mortal agents | Law justice: die faces |
| tradition_spread | gelenek_yayginlik | 35 | 0 | 100 | Mortal agents | Spread of a new tradition or legend |
| tradition_rigidity | gelenek_katilik | 50 | 0 | 100 | Mortal agents | Rigidity of a new tradition or legend |
| discover_abundance_base | kesif_bolluk_taban | 40 | 0 | 100 | Economy | Discovered resource abundance: base |
| discover_abundance_die | kesif_bolluk_zar | 40 | 1 | 100 | Economy | Discovered resource abundance: die faces |
| discover_value_base | kesif_deger_taban | 20 | 0 | 100 | Economy | Discovered resource value: base |
| discover_value_die | kesif_deger_zar | 50 | 1 | 100 | Economy | Discovered resource value: die faces |
| discover_might_base | kesif_kudret_taban | 10 | 0 | 100 | Economy | Discovered resource might: base |
| discover_might_die | kesif_kudret_zar | 50 | 1 | 100 | Economy | Discovered resource might: die faces |
| settle_migration_pct | goc_oran | 12 | 0 | 100 | Population and growth | Migrants to a new settlement: percentage of population |
| settle_min_migrants | goc_en_az | 20 | 1 | 100,000 | Population and growth | Minimum migrants to a new settlement |
| new_settlement_prosperity | yeni_kent_refah | 35 | 0 | 100 | Population and growth | Prosperity of a settlement founded by mortals |
| new_settlement_defense | yeni_kent_savunma | 25 | 0 | 100 | Population and growth | Defense of a settlement founded by mortals |
| new_settlement_piety | yeni_kent_inanc | 60 | 0 | 100 | Population and growth | Piety of a settlement founded by mortals |
| trade_relation | ticaret_iliski | 10 | 0 | 100 | War and diplomacy | Relation contribution of establishing trade |
| war_declare_relation | savas_iliski | 25 | 0 | 200 | War and diplomacy | Relation damage of a war declaration |
| war_declare_patron_relation | savas_hami_iliski | 5 | 0 | 200 | War and diplomacy | Relation damage between the two sides' gods from a war declaration |
| worship_foreign_attitude_loss | tapin_yabanci_tutum | 5 | 0 | 200 | Religion and language | Attitude loss of an abandoned foreign god |
| worship_switch_relation | tapin_iliski | 10 | 0 | 200 | Religion and language | Relation damage between the old and new god from changing gods |
| knowledge_max_prereqs | bilgi_temel_adet | 3 | 0 | 20 | Mortal agents | Maximum prerequisite knowledge of a new knowledge |
| knowledge_craft_threshold | bilgi_zanaat_esik | 60 | 0 | 100 | Mortal agents | Knowledge of one with craft above this is one level higher |
| knowledge_level_cap | bilgi_seviye_tavan | 10 | 1 | 100 | Mortal agents | Highest level of knowledge developed by mortals |
| knowledge_spread | bilgi_yayginlik | 10 | 0 | 100 | Mortal agents | Spread of newly developed knowledge |
| diplomacy_default_strength | dip_guc_varsayilan | 30 | 0 | 100 | War and diplomacy | Diplomacy strength: strength assumed for a party with no recorded strength |
| diplomacy_population_mult | dip_nufus_kat | 8 | 0 | 100 | War and diplomacy | Diplomacy strength: + log10(population) × this number |
| diplomacy_relation_divisor | dip_iliski_bolen | 4 | 1 | 1000 | War and diplomacy | Diplomacy die: − relation / this number |
| diplomacy_alliance_threshold | dip_ittifak_esik | 60 | 0 | 200 | War and diplomacy | Acceptance threshold of an alliance or marriage proposal (d100) |
| diplomacy_alliance_relation | dip_ittifak_iliski | 15 | 0 | 100 | War and diplomacy | Relation contribution of an accepted alliance |
| diplomacy_marriage_relation | dip_evlilik_iliski | 20 | 0 | 100 | War and diplomacy | Relation contribution of an accepted marriage |
| diplomacy_reject_relation | dip_ret_iliski | 3 | 0 | 100 | War and diplomacy | Relation damage of a rejected alliance or marriage |
| diplomacy_peace_threshold | dip_baris_esik | 45 | 0 | 200 | War and diplomacy | Acceptance threshold of a peace proposal (d100) |
| diplomacy_peace_relation | dip_baris_iliski | 15 | 0 | 100 | War and diplomacy | Relation contribution of an accepted peace |
| tribute_superiority_pct | harac_ustunluk | 120 | 0 | 1000 | War and diplomacy | Strength superiority required for tribute (% of the other side's strength) |
| tribute_insolence_relation | harac_red_iliski | 25 | 0 | 200 | War and diplomacy | Relation damage of a tribute insolence |
| tribute_payer_loss | harac_kayip | 10 | 0 | 100 | War and diplomacy | Wealth/prosperity loss of the tribute payer |
| tribute_taker_gain | harac_kazanc | 8 | 0 | 100 | War and diplomacy | Wealth/prosperity gain of the tribute taker |
| tribute_relation | harac_iliski | 15 | 0 | 200 | War and diplomacy | Relation damage of tribute |
| seize_item_die | macera_zar | 30 | 1 | 200 | Heroes and mortals | Seize an item: die faces of both sides |
| seize_item_fail_wound | macera_yara | 30 | 0 | 300 | Heroes and mortals | Wound of a hero who fails to seize an item |
| route_intellect_divisor | rota_akil_bolen | 3 | 1 | 1000 | Cosmos and travel | Route die: + intellect / this number |
| gate_speed | kapi_hiz | 90 | 0 | 100 | Cosmos and travel | Speed of a found ancient gate |
| gate_range | kapi_menzil | 100 | 0 | 100 | Cosmos and travel | Range of a found ancient gate |
| gate_armor | kapi_zirh | 60 | 0 | 100 | Cosmos and travel | Armor of a found ancient gate |
| gate_strangeness_base | kapi_tuhaflik | 50 | 0 | 100 | Cosmos and travel | Strangeness of a found ancient gate: base |
| gate_strangeness_die | kapi_tuhaflik_zar | 40 | 1 | 100 | Cosmos and travel | Strangeness of a found ancient gate: die faces |
| gate_power | kapi_guc | 5 | 1 | 30 | Cosmos and travel | Power level of a found ancient gate |
| ship_miners_divisor | gemi_maden_bolen | 3 | 1 | 1000 | Cosmos and travel | Shipcraft: + miners / this number |
| ship_metallurgy_bonus | gemi_metalurji | 15 | 0 | 100 | Cosmos and travel | Shipcraft: metallurgy bonus |
| ship_speed_base | gemi_hiz_taban | 30 | 0 | 100 | Cosmos and travel | Ship speed: base |
| ship_speed_craft_divisor | gemi_hiz_bolen | 3 | 1 | 1000 | Cosmos and travel | Ship speed: + craft / this number |
| ship_speed_die | gemi_hiz_zar | 20 | 1 | 100 | Cosmos and travel | Ship speed: die faces |
| ship_range_base | gemi_menzil_taban | 40 | 0 | 100 | Cosmos and travel | Ship range: base |
| ship_range_die | gemi_menzil_zar | 40 | 1 | 100 | Cosmos and travel | Ship range: die faces |
| ship_crew_base | gemi_murettebat_taban | 50 | 0 | 100,000 | Cosmos and travel | Ship crew: base |
| ship_crew_die | gemi_murettebat_zar | 400 | 1 | 100,000 | Cosmos and travel | Ship crew: die faces |
| ship_armor_base | gemi_zirh_taban | 20 | 0 | 100 | Cosmos and travel | Ship armor: base |
| ship_armor_craft_divisor | gemi_zirh_bolen | 4 | 1 | 1000 | Cosmos and travel | Ship armor: + craft / this number |
| ship_armor_die | gemi_zirh_zar | 20 | 1 | 100 | Cosmos and travel | Ship armor: die faces |
| ship_strangeness_die | gemi_tuhaflik_zar | 60 | 1 | 100 | Cosmos and travel | Ship strangeness: die faces |
| ship_miners_cost | gemi_maden | 20 | 0 | 100 | Cosmos and travel | Removed from the community's miners by shipbuilding |
| expedition_default_pct | sefer_yuzde | 10 | 1 | 100 | Cosmos and travel | Those setting out on an expedition: default population percentage |
| expedition_max_pct | sefer_yuzde_tavan | 30 | 1 | 100 | Cosmos and travel | Those setting out on an expedition: maximum population percentage |
| expedition_min_people | sefer_en_az | 20 | 1 | 100,000 | Cosmos and travel | Minimum people for a colony or conquest expedition |
| tame_charisma_divisor | evcil_karizma_bolen | 3 | 1 | 1000 | Creatures | Taming skill: + charisma / this number |
| tame_die | evcil_zar | 60 | 1 | 200 | Creatures | Taming skill: die faces |
| tame_default_danger | evcil_tehlike_varsayilan | 30 | 0 | 100 | Creatures | Taming: danger assumed for a species with no recorded danger |
| tame_danger_divisor | evcil_tehlike_bolen | 150 | 1 | 10,000 | Creatures | Taming difficulty: danger / (this number / 100) |
| tame_default_intelligence | evcil_zeka_varsayilan | 20 | 0 | 100 | Creatures | Taming: intelligence assumed for a species with no recorded intelligence |
| tame_megafauna_difficulty | evcil_megafauna | 40 | 0 | 200 | Creatures | Extra difficulty of taming megafauna |
| tame_difficulty_die | evcil_zor_zar | 30 | 1 | 200 | Creatures | Taming difficulty: die faces |
| tame_attack_divisor | evcil_ofke_bolen | 200 | 1 | 10,000 | Creatures | Attack chance of an untamed species: danger / this number |
| tame_attack_loss_pct | evcil_kayip | 5 | 0 | 100 | Creatures | Population/HP loss of the one attacked (%) |
| relic_scribe_mult | kalinti_katip | 2 | 0 | 100 | Mortal agents | Relic investigation: scribe-class multiplier |
| relic_die | kalinti_zar | 50 | 1 | 200 | Mortal agents | Relic investigation: die faces |
| relic_knowledge_threshold | kalinti_bilgi_esik | 70 | 0 | 300 | Mortal agents | At or above this a lost knowledge is found |
| relic_item_threshold | kalinti_esya_esik | 55 | 0 | 300 | Mortal agents | At or above this an ownerless item is found |
| relic_curse_threshold | kalinti_lanet_esik | 35 | 0 | 300 | Mortal agents | Below this the investigators are cursed |
| sabotage_die | sabotaj_zar | 40 | 1 | 200 | War and diplomacy | Sabotage: die faces of both sides |
| sabotage_caught_margin | sabotaj_yakalanma | 15 | 0 | 200 | War and diplomacy | The saboteur is caught if the target's vigilance exceeds the trick by this much |
| poison_population_pct | zehir_nufus | 10 | 0 | 100 | War and diplomacy | Population/follower loss from poison (%) |
| poison_hp | zehir_can | 40 | 0 | 300 | War and diplomacy | HP loss from poison |
| arson_loss | kundak | 12 | 0 | 100 | War and diplomacy | Prosperity, defense and wealth loss from arson |
| sabotage_caught_relation | sabotaj_iliski | 20 | 0 | 200 | War and diplomacy | Relation damage of a caught sabotage |
| preach_base_pct | vaaz_taban | 35 | 0 | 100 | Religion and language | Sermon success chance: base (%) |
| preach_default_influence | vaaz_etki_varsayilan | 30 | 0 | 100 | Religion and language | Sermon: influence assumed for a cult with no recorded influence |
| preach_god_charisma_divisor | vaaz_tanri_bolen | 4 | 1 | 1000 | Religion and language | Sermon chance: + god's charisma / this number |
| preach_old_god_divisor | vaaz_eski_bolen | 3 | 1 | 1000 | Religion and language | Sermon chance: − charisma of the target's old god / this number |
| preach_piety_divisor | vaaz_inanc_bolen | 5 | 1 | 1000 | Religion and language | Sermon chance: − target's piety / this number |
| preach_relation | vaaz_iliski | 10 | 0 | 200 | Religion and language | Relation damage with the god who loses a worshipper to a sermon |
| defy_god_damage_divisor | meydan_hasar_bolen | 4 | 1 | 1000 | Heroes and mortals | Defy a god: weapon strength = damage / this number |
| defy_god_might_divisor | meydan_kudret_bolen | 6 | 1 | 1000 | Heroes and mortals | Defy a god: + item might / this number |
| defy_god_intellect_divisor | meydan_akil_bolen | 3 | 1 | 1000 | Heroes and mortals | Defy a god: + intellect / this number |
| defy_god_die | meydan_zar | 40 | 1 | 200 | Heroes and mortals | Defy a god: die faces of both sides |
| defy_god_strength_per_level | meydan_tanri_seviye | 5 | 0 | 100 | Heroes and mortals | Defy a god: the god's strength per level |
| defy_god_untouchable | meydan_dokunulmaz | 15 | 0 | 100 | Heroes and mortals | Defy a god: bonus of an Untouchable god |
| godslayer_margin | tanri_katli_fark | 40 | 0 | 300 | Heroes and mortals | A mortal winning by this margin kills a fading god |
| godslayer_max_existence | tanri_katli_varlik | 35 | 0 | 100 | Heroes and mortals | A god with existence below this can die at a mortal's hand |
| god_default_existence | tanri_varlik_varsayilan | 60 | 0 | 100 | Heroes and mortals | Existence assumed for a god with no recorded existence |
| godslayer_charisma | tanri_katli_karizma | 25 | 0 | 100 | Heroes and mortals | Charisma gain of a godslayer |
| god_wound_pct | tanri_yara | 25 | 0 | 100 | Heroes and mortals | Wound of a god defeated by a mortal: percentage of max HP |
| god_wound_renown_loss | tanri_yara_un | 8 | 0 | 100 | Heroes and mortals | Renown loss of a god defeated by a mortal |
| god_wounder_charisma | tanri_yara_karizma | 15 | 0 | 100 | Heroes and mortals | Charisma gain of a mortal who wounds a god |
| defy_god_death_chance | tanri_olum_sans | 50 | 0 | 100 | Heroes and mortals | Chance a mortal defeated by a god dies (%; otherwise cursed) |
| god_crush_renown | tanri_ezme_un | 4 | 0 | 100 | Heroes and mortals | Renown of a god who crushes a defiant mortal |
| deny_foreign_attitude | inkar_tutum | 10 | 0 | 200 | Religion and language | Attitude loss of a denied foreign god |
| deny_foreign_faith | inkar_inanc | 5 | 0 | 100 | Religion and language | Faith loss of a denied foreign god |
| deny_son_existence | inkar_varlik | 6 | 0 | 100 | Religion and language | Existence loss of a denied son |
| prophecy_max_related | kehanet_ilgili_adet | 3 | 0 | 20 | Religion and language | Maximum related entities in a prophecy |
| prophecy_certainty_base | kehanet_kesinlik | 30 | 0 | 100 | Religion and language | Prophecy certainty: base (+ intellect / 2) |
| escape_default_stat | kac_varsayilan | 30 | 0 | 100 | Mortal agents | Escape: stat assumed for a captive with no recorded agility/intellect |
| escape_intellect_divisor | kac_akil_bolen | 3 | 1 | 1000 | Mortal agents | Escape chance: + intellect / this number |
| escape_captor_defense_divisor | kac_savunma_bolen | 3 | 1 | 1000 | Mortal agents | Escape chance: − captor's defense / this number |
| escape_min_pct | kac_taban | 5 | 0 | 100 | Mortal agents | Lowest escape chance (%) |
| ransom_prosperity_extra | fidye_refah_ek | 5 | 0 | 100 | Mortal agents | Ransom: threshold surcharge for one paying with prosperity |
| ransom_relation | fidye_iliski | 5 | 0 | 100 | Mortal agents | Relation contribution of a paid ransom |
| rescue_die | kurtar_zar | 40 | 1 | 200 | Mortal agents | Rescue a captive: die faces of both sides |
| army_default_strength | ordu_guc_varsayilan | 30 | 0 | 100 | War and diplomacy | Army: strength assumed for a community with no recorded population |
| army_strength_mult | ordu_guc_kat | 60 | 0 | 100,000 | War and diplomacy | Army: base of a community with no recorded population = strength × this number |
| army_min_soldiers | ordu_en_az | 30 | 1 | 100,000 | War and diplomacy | Minimum soldiers of a raised army |
| army_morale_base | ordu_moral | 50 | 0 | 100 | War and diplomacy | New army morale: base |
| army_morale_die | ordu_moral_zar | 25 | 1 | 100 | War and diplomacy | New army morale: die faces |
| army_equipment_base | ordu_techizat | 20 | 0 | 100 | War and diplomacy | New army equipment: base |
| army_metallurgy_bonus | ordu_metalurji | 15 | 0 | 100 | War and diplomacy | Army equipment bonus for those who know metallurgy |
| army_craft_divisor | ordu_zanaat_bolen | 4 | 1 | 1000 | War and diplomacy | Army equipment: + craft / this number |
| army_experience_warcraft | ordu_deneyim_savas | 30 | 0 | 100 | War and diplomacy | Experience of a new army of a community knowing war |
| army_experience | ordu_deneyim | 10 | 0 | 100 | War and diplomacy | Experience of a new army |
| commander_charisma_divisor | komutan_karizma_bolen | 10 | 1 | 1000 | War and diplomacy | Commander's morale contribution: charisma / this number |
| barter_max_items | takas_adet | 3 | 1 | 20 | Mortal agents | Maximum things on one side of a barter |

### NAMING

Old namespace `ADLANDIRMA` · 4 rows · defined in `src/agents.js`. Fate's naming pass for engine-born records (batching, retries).

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| batch | parti | 12 | 1 | 500 | Agents and model | Records per naming model call (not a limit: all pending ones are named in batches in the same epoch) |
| retries | deneme | 2 | 0 | 20 | Agents and model | Retries for a record that couldn't be named; then its temporary description is cleared and it is left for deepening |
| parallel | paralel | 4 | 1 | 32 | Agents and model | Naming: number of batches (calls) running at the same time; batches don't wait in sequence |
| dialect_check | lehce_denetim | 1 | 0 | 1 | Agents and model | Naming: an invented name not fitting its own world's dialect (forbidden vowel) is retried once (1 on, 0 off) |

### NARRATIVE

Old namespace `ANLATI` · 18 rows · defined in `src/agents.js`. Size ranges of god epics and deepening (depth) outputs.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| epic_sections_min | destan_bolum_en_az | 3 | 0 | 50 | Content jobs | Sections of a god's epic (minimum) |
| epic_sections_max | destan_bolum_en_cok | 7 | 1 | 100 | Content jobs | Sections of a god's epic (maximum) |
| god_names_min | tanri_ad_en_az | 2 | 0 | 50 | Content jobs | God's depth: names (minimum) |
| god_names_max | tanri_ad_en_cok | 6 | 1 | 100 | Content jobs | God's depth: names (maximum) |
| secrets_min | sir_en_az | 2 | 0 | 50 | Content jobs | God's depth: secrets (minimum) |
| secrets_max | sir_en_cok | 4 | 1 | 100 | Content jobs | God's depth: secrets (maximum) |
| fears_min | korku_en_az | 1 | 0 | 50 | Content jobs | God's depth: fears (minimum) |
| fears_max | korku_en_cok | 3 | 1 | 100 | Content jobs | God's depth: fears (maximum) |
| taboos_min | yasak_en_az | 2 | 0 | 50 | Content jobs | God's depth: taboos (minimum) |
| taboos_max | yasak_en_cok | 5 | 1 | 100 | Content jobs | God's depth: taboos (maximum) |
| gifts_min | armagan_en_az | 2 | 0 | 50 | Content jobs | God's depth: gifts (minimum) |
| gifts_max | armagan_en_cok | 5 | 1 | 100 | Content jobs | God's depth: gifts (maximum) |
| quotes_min | soz_en_az | 2 | 0 | 50 | Content jobs | Depth: mortals' sayings (minimum) |
| quotes_max | soz_en_cok | 4 | 1 | 100 | Content jobs | Depth: mortals' sayings (maximum) |
| rumors_min | soylenti_en_az | 3 | 0 | 50 | Content jobs | Depth: rumours (minimum) |
| rumors_max | soylenti_en_cok | 5 | 1 | 100 | Content jobs | Depth: rumours (maximum) |
| sensory_details_min | ayrinti_en_az | 3 | 0 | 50 | Content jobs | Depth: sensory details (minimum) |
| sensory_details_max | ayrinti_en_cok | 6 | 1 | 100 | Content jobs | Depth: sensory details (maximum) |

### NOTIFICATIONS

Old namespace `BILDIRIM` · 3 rows · defined in `src/bildirim.js`. Notification retention and toast threshold.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| read_kept | okunmus_tut | 1500 | 10 | 100,000 | Notifications | Read notifications kept |
| total_cap | tavan | 5000 | 100 | 100,000 | Notifications | Total notification cap |
| toast_min_importance | toast_onem | 3 | 1 | 5 | Notifications | Notifications of this importance and above also appear as a short on-screen toast (5: none) |

### OPPORTUNITIES

Old namespace `FIRSAT` · 25 rows · defined in `src/firsatlar.js`. Opportunity hints shown to agents and the god.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| list_max | liste | 5 | 1 | 50 | Opportunities | Maximum records listed in one opportunity line |
| stale_epochs | durgun_cag | 4 | 1 | 100 | Opportunities | A story untouched for this many epochs counts as "about to be forgotten" |
| long_thread_steps | uzun_iplik | 8 | 1 | 200 | Opportunities | After this many advances a story counts as "should be concluded" |
| silence_epochs | sessizlik_cag | 3 | 1 | 100 | Opportunities | Reminder to a son who hasn't talked with his siblings for this many epochs |
| rich_essence | zengin_oz | 150 | 0 | 100,000 | Opportunities | Essence for a "great deed" reminder to the Creator |
| list_short | liste_kisa | 4 | 1 | 50 | Opportunities | Maximum records in short opportunity lists |
| list_narrow | liste_dar | 3 | 1 | 50 | Opportunities | Maximum records in the narrowest opportunity lists |
| list_wide | liste_genis | 6 | 1 | 100 | Opportunities | Maximum records in wide opportunity lists |
| life_people_surplus | canli_halk_fazla | 2 | 0 | 50 | Opportunities | "Breathe life": if the number of peoples doesn't exceed the number of regions by this much |
| life_mortals_below | canli_olumlu | 6 | 0 | 200 | Opportunities | "Breathe life": if named mortals are fewer than this |
| life_species_below | canli_tur | 4 | 0 | 200 | Opportunities | "Breathe life": if species are fewer than this |
| rival_relation | rakip_iliski | 20 | 0 | 100 | Opportunities | Relation with a sibling counted as a rival: below minus this |
| target_sibling_relation | hasim_kardes | 25 | 0 | 100 | Opportunities | Relation with a sibling whose creations are pointed out as targets: below minus this |
| rebel_loyalty | sadakat_isyan | 40 | 0 | 100 | Opportunities | Rebellion reminder if loyalty is below this |
| fading_existence | sonmek_uzere | 20 | 0 | 100 | Opportunities | "You are about to fade out" if existence is at or below this |
| fading_sons_existence | solan_ogul | 25 | 0 | 100 | Opportunities | To the god: sons with existence at or below this are "being forgotten" |
| apocalypse_warning_pct | kiyamet_uyari | 50 | 0 | 100 | Opportunities | Apocalypse reminder to the god: at this percentage of the threshold |
| hungry_food | ac_erzak | 60 | 0 | 1000 | Opportunities | Worshippers count as hungry: food below this |
| granary_food | ambar_erzak | 60 | 0 | 1000 | Opportunities | To a mortal "your granary is emptying": food below this |
| discontented | hosnutsuz | 30 | 0 | 100 | Opportunities | A class counts as discontented: satisfaction below this |
| friendly_neighbor | dost_komsu | 45 | -100 | 100 | Opportunities | Loving neighbour: community relation at or above this |
| monster_danger | canavar_tehlike | 50 | 0 | 100 | Opportunities | Dangerous creature: danger at or above this |
| tense_neighbor | gergin_komsu | 20 | 0 | 100 | Opportunities | To a mortal "tense neighbour": community relation below minus this (with no hostility link) |
| tension_first | gerilim_once | 1 | 0 | 1 | Opportunities | Tension lines (rivals, hostilities, wars, rebellion) are placed at the top of the opportunity list (1 on, 0 off) |
| challenge_god_strength | meydan_guc | 110 | 0 | 1000 | Opportunities | Suggestion to challenge a god: strength + agility at or above this |

### PANTHEON

Old namespace `PANTEON` · 64 rows · defined in `src/panteon.js`. Foreign gods, Outer Beings bargains, stars, sleeping local gods, rival clashes, holy worlds.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| extinguish_star_apocalypse | sondurme_kiyamet | 8 | 0 | 100 | Apocalypse | Contribution of extinguishing a star to the apocalypse |
| foreign_attract_chance | yabanci_cekim_sans | 25 | 0 | 100 | Civilization | A foreign god attracts a worshipper (%) |
| foreign_sacrifice_chance | kurban_sans | 50 | 0 | 100 | Civilization | A foreign god demands a sacrifice (%) |
| foreign_friend_help_chance | yabanci_dost_sans | 15 | 0 | 100 | Civilization | A friendly foreign god helps (%) |
| outer_expel_chance | dis_kov_sans | 50 | 0 | 100 | Cosmic horror | The Creator pushes an Outer Being out (%) |
| foreign_strength_base | yabanci_guc | 40 | 0 | 100 | Civilization | Base strength of a new foreign god |
| foreign_strength_die | yabanci_guc_zar | 40 | 1 | 100 | Civilization | Strength die of a new foreign god |
| foreign_attract_targets | yabanci_cekim_sayi | 2 | 0 | 100 | Civilization | Maximum unclaimed communities a foreign god turns to per epoch |
| foreign_population_per_faith | yabanci_inanc_nufus | 2000 | 1 | 10,000,000 | Civilization | Worshipping population giving 1 faith to a foreign god |
| foreign_followers_per_faith | yabanci_inanc_murit | 60 | 1 | 10,000,000 | Civilization | Followers giving 1 faith to a foreign god |
| foreign_growth_faith | yabanci_guc_inanc | 10 | 0 | 100,000 | Civilization | Faith at which a foreign god starts to grow stronger |
| foreign_growth | yabanci_guc_artis | 1 | 0 | 100 | Civilization | Per-epoch strength growth of a foreign god with enough faith |
| attitude_curious | tutum_merak | 20 | 0 | 100 | Civilization | Attitude of a foreign god showing curiosity at first contact |
| attitude_hostile | tutum_dusmanlik | 20 | 0 | 100 | Civilization | Attitude of a foreign god showing hostility at first contact (negative) |
| foreign_attack_base_pct | yabanci_dusman_sans | 20 | 0 | 100 | Civilization | Base attack chance of a hostile foreign god (%) |
| foreign_attack_hostility_divisor | yabanci_dusman_bolen | 300 | 1 | 100,000 | Civilization | Hostility contribution to attack chance: hostility / this number |
| foreign_steal_wrath | yabanci_calma_ofke | 10 | 0 | 100 | Civilization | Wrath gain of a son whose worshipper is stolen |
| foreign_friend_min_attitude | yabanci_dost_tutum | 40 | 0 | 100 | Civilization | Minimum attitude of a foreign god counted as friendly |
| foreign_friend_help_targets | yabanci_dost_sayi | 2 | 0 | 100 | Civilization | Maximum worshippers a friendly foreign god helps per epoch |
| foreign_friend_prosperity | yabanci_dost_refah | 4 | 0 | 100 | Civilization | Prosperity contribution of a friendly foreign god to its worshippers |
| foreign_rebel_attitude_drift | yabanci_asi_kayma | 3 | 0 | 100 | Civilization | Each rebel son on the world lowers the foreign god's attitude |
| foreign_curse_attitude_drift | yabanci_lanet_kayma | 1 | 0 | 100 | Civilization | Foreign god attitude drop when a native is cursed |
| outer_gnaw_divisor | dis_kemir_bolen | 10 | 1 | 1000 | Cosmic horror | Essence an Outer Being gnaws from the Creator: influence / this number |
| holy_world_take_relation | kutsal_dunya_iliski | 15 | 0 | 100 | Cosmos and travel | Sibling-relation cost of taking someone else's holy world |
| seal_leak_reduction | muhur_sizinti | 10 | 0 | 100 | Cosmic horror | Leak reduction on both worlds from sealing a gate |
| star_brightness_base | yildiz_parlaklik | 50 | 0 | 100 | Sky | Base brightness of a new star |
| star_brightness_die | yildiz_parlaklik_zar | 45 | 1 | 100 | Sky | Brightness die of a new star |
| dead_star_brightness | olu_yildiz_parlaklik | 5 | 0 | 100 | Sky | Brightness of an extinguished star |
| extinguish_leak | sondurme_sizinti | 20 | 0 | 100 | Sky | Leak flowing to its planets when a star is extinguished |
| extinguish_fertility_loss | sondurme_bereket | 25 | 0 | 100 | Sky | Fertility loss of planet regions when a star is extinguished |
| cleanse_leak_amount | temizle_sizinti | 40 | 0 | 100 | Cosmic horror | Leak reduced by cleansing |
| bargain_essence_base | pazarlik_oz | 40 | 0 | 1000 | Cosmic horror | Base essence gain from bargaining with an Outer Being |
| bargain_influence_divisor | pazarlik_etki_bolen | 2 | 1 | 100 | Cosmic horror | Outer Being influence contribution to the bargain: influence / this number |
| bargain_ambition | pazarlik_hirs | 10 | 0 | 100 | Cosmic horror | Ambition gain of the bargaining son |
| bargain_loyalty_loss | pazarlik_sadakat | 15 | 0 | 100 | Cosmic horror | Loyalty loss of the bargaining son |
| bargain_leak | pazarlik_sizinti | 20 | 0 | 100 | Cosmic horror | Leak the bargain adds to the world |
| bargain_sibling_relation_loss | pazarlik_iliski | 10 | 0 | 100 | Cosmic horror | Relation loss of the bargaining son with his siblings |
| son_war_chance | ogul_savas_sans | 10 | 0 | 100 | Civilization | A son spontaneously goes to war with a hostile foreign god (% per epoch) |
| son_war_max_attitude | ogul_savas_tutum | 30 | 0 | 100 | Civilization | Maximum attitude (negative) of a foreign god a son spontaneously goes to war with |
| sleep_wake_threshold | uyku_esik | 100 | 1 | 100,000 | Civilization | Sleeping local god: accumulated awakening pressure needed to wake (only events accumulate; it never wakes by itself over time) |
| sleep_epoch_cap | uyku_cag_tavan | 25 | 0 | 100,000 | Civilization | Awakening pressure: maximum pressure that can accumulate in one epoch (even the god of a crowded world wakes through sustained events, not in a single epoch) |
| sleep_per_son | uyku_ogul | 15 | 0 | 1000 | Civilization | Awakening pressure: each son acting (creating or entering the chronicle) on that world this epoch; merely staying there doesn't count |
| sleep_per_expedition | uyku_sefer | 20 | 0 | 1000 | Civilization | Awakening pressure: each expedition setting out to that world or each route opened |
| sleep_per_event | uyku_olay | 6 | 0 | 1000 | Civilization | Awakening pressure: each major event on that world this epoch (war, disaster, plague, battle…) |
| sleep_per_land | uyku_toprak | 8 | 0 | 1000 | Civilization | Awakening pressure: each new region or place opened on that world by sons or mortals |
| sleep_per_relic | uyku_kalinti | 25 | 0 | 1000 | Civilization | Awakening pressure: each ancient remnant or trace of a previous creation found on that world |
| sleep_per_death | uyku_olum | 2 | 0 | 1000 | Civilization | Awakening pressure: each named mortal who died on that world in the previous epoch (old-age deaths happen at the engine's end; each death counts once) |
| sleep_baseline_ignore_pct | uyku_olagan_kat | 100 | 0 | 1000 | Civilization | Awakening pressure: percentage of the world's usual noise (moving average) ignored; only shaking above the usual accumulates (0: all counts) |
| sleep_average_weight_pct | uyku_ortalama_agirlik | 20 | 1 | 100 | Civilization | Awakening pressure: each epoch's contribution to the usual-noise average (%) |
| auto_holy_world_per_son | kutsal_oto_ogul | 1 | 0 | 100 | Civilization | Spontaneous holy world: maximum worlds a son can claim this way (those given by tool or the god's hand don't count) |
| rival_relation | hasim_iliski | 60 | 0 | 100 | Civilization | Rival clash: two active siblings with relation below minus this may clash on their own |
| rival_chance | hasim_sans | 15 | 0 | 100 | Civilization | Rival clash: chance of a suitable rival pair clashing in one epoch (%) |
| rival_cap | hasim_tavan | 1 | 0 | 50 | Civilization | Rival clash: maximum spontaneous clashes in one epoch (0: off) |
| rival_cooldown_epochs | hasim_ara_cag | 3 | 0 | 100 | Civilization | Rival clash: epochs that must pass before the same two siblings clash again |
| rival_soften | hasim_donus | 2 | 0 | 100 | Civilization | Rival clash: per-epoch softening of the relation of rivals who don't clash (up to the rivalry threshold) |
| rival_defeat_streak | hasim_yenilgi_seri | 2 | 1 | 100 | Civilization | Rival clash: one defeated this many times in a row by the same sibling withdraws |
| rival_withdraw_relation | hasim_geri_iliski | 25 | 0 | 100 | Civilization | Rival clash: improvement of the relation between the one withdrawing and the victor (leaves rivalry) |
| auto_holy_world_worshippers | kutsal_oto_tapan | 3 | 0 | 1000 | Civilization | On a world without a protector, the son with the most worshippers declares it his holy world on his own if he has this many worshippers (0: off) |
| foreign_wake_epochs | uyanis_cag | 8 | 1 | 1000 | Civilization | Number of epochs after which a defeated foreign god wakes on its own (after defeat) |
| foreign_wake_faith | uyanis_inanc | 15 | 0 | 100,000 | Civilization | Worshipper faith that immediately wakes a defeated foreign god |
| foreign_wake_min_strength | uyanis_guc | 30 | 0 | 100 | Civilization | Minimum strength of a waking foreign god |
| foreign_wake_grudge | uyanis_kin | 15 | 0 | 200 | Civilization | Attitude loss toward the pantheon of a waking foreign god (the grudge of defeat) |
| default_fertility | bereket_varsayilan | 50 | 0 | 100 | Sky | Fertility assumed when a star is extinguished for a region with no recorded fertility |
| outer_default_influence | dis_etki_varsayilan | 50 | 0 | 100 | Cosmic horror | Influence assumed for an Outer Being with no recorded influence (gnawing and bargaining) |

### POLITICS

Old namespace `SIYASET` · 8 rows · defined in `src/kesif.js`. Regional dominance and settlement tiers.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| faction_strength_weight | hizip_guc | 200 | 0 | 1,000,000 | Civilization | Regional dominance: weight per faction strength point |
| faction_sway_weight | hizip_nufuz | 50 | 0 | 1,000,000 | Civilization | Regional dominance: weight per faction sway point |
| faction_default | hizip_varsayilan | 30 | 0 | 100 | Civilization | Regional dominance: faction with unknown strength or sway |
| cult_follower_share_pct | tarikat_murit | 30 | 0 | 1000 | Civilization | Regional dominance: counted share of cult followers (%) |
| rule_chain_depth | yonetim_zinciri | 4 | 0 | 50 | Civilization | Regional dominance: steps looked up in the rule chain |
| town_population | kasaba | 2000 | 1 | 100,000,000 | Civilization | Settlement tier: town population |
| city_population | kent | 10,000 | 1 | 100,000,000 | Civilization | Settlement tier: city population |
| metropolis_population | buyuk_kent | 50,000 | 1 | 100,000,000 | Civilization | Settlement tier: great-city population |

### POWER_UNLOCK_LEVELS

Old namespace `GUC_SEVIYELERI` · 3 rows · defined in `src/rules.js` · also read by `src/agents.js`, `src/denge.js`, `src/kodeks.js`, `src/olumluler.js`, `src/tools.js`, `src/world.js`. Levels at which a son's 3 powers unlock — static array in rules.js.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| power_1_unlock_level | 0 | 1 | 1 | 50 | God and son costs | Level at which the son's 1st power unlocks |
| power_2_unlock_level | 1 | 3 | 1 | 50 | God and son costs | Level at which the son's 2nd power unlocks |
| power_3_unlock_level | 2 | 5 | 1 | 50 | God and son costs | Level at which the son's 3rd power unlocks |

### RARITIES

Old namespace `RARITIES` · 41 rows · defined in `src/rules.js` · also read by `src/agents.js`, `src/denge.js`, `src/epoch.js`, `src/kitap.js`, `src/kodeks.js`, `src/oyuncu.js`, `src/sim.js`, `src/tanriguc.js`, `src/tools.js`, `src/world.js`. Per-rarity son properties — static object in rules.js.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| common_action_points | yaygin.ap | 3 | 1 | 8 | Rarity tiers | Common: action points |
| common_essence_regen | yaygin.oz_yenilenme | 8 | 0 | 60 | Rarity tiers | Common: essence regeneration per epoch |
| common_stat_min | yaygin.stat.0 | 20 | 1 | 100 | Rarity tiers | Common: lower bound of stats when summoned |
| common_stat_max | yaygin.stat.1 | 45 | 1 | 100 | Rarity tiers | Common: upper bound of stats when summoned |
| common_power_cap | yaygin.guc_tavan | 2 | 1 | 30 | Rarity tiers | Common: power-level cap |
| common_max_turns | yaygin.maxTurns | 11 | 4 | 40 | Rarity tiers | Common: son turn limit (steps) |
| common_summon_weight | yaygin.agirlik | 50 | 0 | 100 | Rarity tiers | Common: summon weight |
| uncommon_action_points | seckin.ap | 3 | 1 | 8 | Rarity tiers | Uncommon: action points |
| uncommon_essence_regen | seckin.oz_yenilenme | 10 | 0 | 60 | Rarity tiers | Uncommon: essence regeneration per epoch |
| uncommon_stat_min | seckin.stat.0 | 30 | 1 | 100 | Rarity tiers | Uncommon: lower bound of stats when summoned |
| uncommon_stat_max | seckin.stat.1 | 55 | 1 | 100 | Rarity tiers | Uncommon: upper bound of stats when summoned |
| uncommon_power_cap | seckin.guc_tavan | 3 | 1 | 30 | Rarity tiers | Uncommon: power-level cap |
| uncommon_max_turns | seckin.maxTurns | 13 | 4 | 40 | Rarity tiers | Uncommon: son turn limit (steps) |
| uncommon_summon_weight | seckin.agirlik | 27 | 0 | 100 | Rarity tiers | Uncommon: summon weight |
| rare_action_points | nadir.ap | 3 | 1 | 8 | Rarity tiers | Rare: action points |
| rare_essence_regen | nadir.oz_yenilenme | 12 | 0 | 60 | Rarity tiers | Rare: essence regeneration per epoch |
| rare_stat_min | nadir.stat.0 | 40 | 1 | 100 | Rarity tiers | Rare: lower bound of stats when summoned |
| rare_stat_max | nadir.stat.1 | 65 | 1 | 100 | Rarity tiers | Rare: upper bound of stats when summoned |
| rare_power_cap | nadir.guc_tavan | 5 | 1 | 30 | Rarity tiers | Rare: power-level cap |
| rare_max_turns | nadir.maxTurns | 15 | 4 | 40 | Rarity tiers | Rare: son turn limit (steps) |
| rare_summon_weight | nadir.agirlik | 14 | 0 | 100 | Rarity tiers | Rare: summon weight |
| epic_action_points | destansi.ap | 3 | 1 | 8 | Rarity tiers | Epic: action points |
| epic_essence_regen | destansi.oz_yenilenme | 15 | 0 | 60 | Rarity tiers | Epic: essence regeneration per epoch |
| epic_stat_min | destansi.stat.0 | 50 | 1 | 100 | Rarity tiers | Epic: lower bound of stats when summoned |
| epic_stat_max | destansi.stat.1 | 80 | 1 | 100 | Rarity tiers | Epic: upper bound of stats when summoned |
| epic_power_cap | destansi.guc_tavan | 7 | 1 | 30 | Rarity tiers | Epic: power-level cap |
| epic_max_turns | destansi.maxTurns | 17 | 4 | 40 | Rarity tiers | Epic: son turn limit (steps) |
| epic_summon_weight | destansi.agirlik | 7 | 0 | 100 | Rarity tiers | Epic: summon weight |
| legendary_action_points | efsanevi.ap | 4 | 1 | 8 | Rarity tiers | Legendary: action points |
| legendary_essence_regen | efsanevi.oz_yenilenme | 18 | 0 | 60 | Rarity tiers | Legendary: essence regeneration per epoch |
| legendary_stat_min | efsanevi.stat.0 | 65 | 1 | 100 | Rarity tiers | Legendary: lower bound of stats when summoned |
| legendary_stat_max | efsanevi.stat.1 | 95 | 1 | 100 | Rarity tiers | Legendary: upper bound of stats when summoned |
| legendary_power_cap | efsanevi.guc_tavan | 10 | 1 | 30 | Rarity tiers | Legendary: power-level cap |
| legendary_max_turns | efsanevi.maxTurns | 19 | 4 | 40 | Rarity tiers | Legendary: son turn limit (steps) |
| legendary_summon_weight | efsanevi.agirlik | 2 | 0 | 100 | Rarity tiers | Legendary: summon weight |
| mythic_action_points | mitik.ap | 5 | 1 | 8 | Rarity tiers | Mythic: action points |
| mythic_essence_regen | mitik.oz_yenilenme | 24 | 0 | 60 | Rarity tiers | Mythic: essence regeneration per epoch |
| mythic_stat_min | mitik.stat.0 | 80 | 1 | 100 | Rarity tiers | Mythic: lower bound of stats when summoned |
| mythic_stat_max | mitik.stat.1 | 100 | 1 | 100 | Rarity tiers | Mythic: upper bound of stats when summoned |
| mythic_power_cap | mitik.guc_tavan | 12 | 1 | 30 | Rarity tiers | Mythic: power-level cap |
| mythic_max_turns | mitik.maxTurns | 21 | 4 | 40 | Rarity tiers | Mythic: son turn limit (steps) |

### RARITY_GATES

Old namespace `NADIRLIK_KAPI` · 40 rows · defined in `src/rules.js`. Minimum son rarity (0..5) to use each creation type / tool.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| create_region | tur_bolge | 3 | 0 | 5 | Rarity tiers | Lowest son rarity that can create a Region (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_place | tur_yer | 0 | 0 | 5 | Rarity tiers | Lowest son rarity that can create a Place (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_resource | tur_kaynak | 0 | 0 | 5 | Rarity tiers | Lowest son rarity that can create a Resource (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_settlement | tur_yerlesim | 0 | 0 | 5 | Rarity tiers | Lowest son rarity that can create a Settlement (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_species | tur_tur | 0 | 0 | 5 | Rarity tiers | Lowest son rarity that can create a Species (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_people | tur_halk | 0 | 0 | 5 | Rarity tiers | Lowest son rarity that can create a People (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_mortal | tur_olumlu | 0 | 0 | 5 | Rarity tiers | Lowest son rarity that can create a Mortal (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_item | tur_esya | 1 | 0 | 5 | Rarity tiers | Lowest son rarity that can create an Item (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_structure | tur_yapit | 1 | 0 | 5 | Rarity tiers | Lowest son rarity that can create a Structure (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_language | tur_dil | 1 | 0 | 5 | Rarity tiers | Lowest son rarity that can create a Language (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_legend | tur_efsane | 0 | 0 | 5 | Rarity tiers | Lowest son rarity that can create a Legend (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_tradition | tur_gelenek | 0 | 0 | 5 | Rarity tiers | Lowest son rarity that can create a Tradition (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_cult | tur_tarikat | 1 | 0 | 5 | Rarity tiers | Lowest son rarity that can create a Cult (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_faction | tur_hizip | 1 | 0 | 5 | Rarity tiers | Lowest son rarity that can create a Faction (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_celestial | tur_gok | 2 | 0 | 5 | Rarity tiers | Lowest son rarity that can create a Celestial Body (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_artwork | tur_eser | 0 | 0 | 5 | Rarity tiers | Lowest son rarity that can create an Artwork (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_law | tur_kanun | 1 | 0 | 5 | Rarity tiers | Lowest son rarity that can create a Law (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_spirit | tur_ruh | 1 | 0 | 5 | Rarity tiers | Lowest son rarity that can create a Spirit (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_knowledge | tur_teknoloji | 2 | 0 | 5 | Rarity tiers | Lowest son rarity that can create Knowledge (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_prophecy | tur_kehanet | 3 | 0 | 5 | Rarity tiers | Lowest son rarity that can create a Prophecy (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_event | tur_olay | 3 | 0 | 5 | Rarity tiers | Lowest son rarity that can create an Event (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_vessel | tur_arac | 2 | 0 | 5 | Rarity tiers | Lowest son rarity that can create a Vessel (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_outer_being | tur_dis | 5 | 0 | 5 | Rarity tiers | Lowest son rarity that can create an Outer Being (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_army | tur_ordu | 3 | 0 | 5 | Rarity tiers | Lowest son rarity that can create an Army (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| create_natural_law | tur_yasa | 4 | 0 | 5 | Rarity tiers | Lowest son rarity that can create a Natural Law (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| influence_tools | etkile | 1 | 0 | 5 | Rarity tiers | Tools to influence an entity, mark a chosen one and curse: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| miracle_tool | mucize | 1 | 0 | 5 | Rarity tiers | The son's miracle tool: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| rare_tools | nadir_araclar | 2 | 0 | 5 | Rarity tiers | Send-dream, disaster, give-knowledge and incite-war tools: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| legendary_tools | efsanevi_araclar | 4 | 0 | 5 | Rarity tiers | Transform, destroy and bear-child tools: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| holy_world | kutsal_dunya | 2 | 0 | 5 | Rarity tiers | Declaring a holy world: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| seal_gate | kapi_muhurle | 3 | 0 | 5 | Rarity tiers | Sealing a gate: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| rekindle_star | yildiz_tutustur | 3 | 0 | 5 | Rarity tiers | Rekindling a dead star: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| spirit_cloak | ruh_kapla | 1 | 0 | 5 | Rarity tiers | Spirit cloaking: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| hang_extinguish_star | yildiz_as | 5 | 0 | 5 | Rarity tiers | Hanging and extinguishing stars: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| interworld_treaty | antlasma | 2 | 0 | 5 | Rarity tiers | Inter-world treaty: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| stitch_leak | sizinti_dik | 3 | 0 | 5 | Rarity tiers | Stitching a leak: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| open_cosmic_bed | yatak_ac | 4 | 0 | 5 | Rarity tiers | Opening a cosmic bed (channel): lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| foreign_god_war | yabanci_savas | 2 | 0 | 5 | Rarity tiers | War with a foreign god (tool and spontaneous war): lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| birth_world | dunya_dogur | 4 | 0 | 5 | Rarity tiers | Birthing a world: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |
| take_life | can_al | 2 | 0 | 5 | Rarity tiers | Taking a mortal's life (can_al): lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic) |

### REPUTATION

Old namespace `ITIBAR` · 60 rows · defined in `src/itibar.js`. The Creator's reputation in each son's eyes (love/fear/neglect).

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| decay_keep_pct | sonum | 75 | 0 | 100 | Reputation | Share of past events' effect kept each epoch (%) |
| window_epochs | pencere | 8 | 1 | 100 | Reputation | Epochs looked back when computing reputation |
| passion_window_epochs | tutku_pencere | 5 | 1 | 100 | Reputation | Epochs looked back when reading passions |
| passion_points_per_action | tutku_puan | 2 | 1 | 100 | Reputation | Points each action adds to the related passion |
| max_passions | tutku_sayi | 3 | 1 | 8 | Reputation | Maximum number of the god's passions |
| love_per_grace_event | sevgi_olay | 14 | 0 | 100 | Reputation | Contribution of a blessing, pardon or ascension to love |
| fear_per_punish_event | korku_olay | 22 | 0 | 100 | Reputation | Contribution of a lightning bolt, chain or exile to fear |
| love_per_message | mesaj_sevgi | 5 | 0 | 100 | Reputation | Contribution of each non-threatening word from the god to love |
| fear_per_threat | tehdit_korku | 10 | 0 | 100 | Reputation | Contribution of each threat from the god to fear |
| default_loyalty | sadakat_varsayilan | 50 | 0 | 100 | Reputation | Loyalty assumed for a son with no recorded loyalty |
| default_wrath | ofke_varsayilan | 20 | 0 | 100 | Reputation | Wrath assumed for a son and the god with no recorded wrath |
| default_attention | ilgi_varsayilan | 60 | 0 | 100 | Reputation | Attention assumed for a god with no recorded attention |
| love_base | sevgi_taban | 20 | 0 | 100 | Reputation | Base of love |
| love_loyalty_divisor | sadakat_bolen | 4 | 1 | 100 | Reputation | Loyalty contribution to love: loyalty / this number |
| love_per_unanswered_prayer | cevapsiz_sevgi | 6 | 0 | 100 | Reputation | Love removed by each unanswered prayer |
| fear_base | korku_taban | 10 | 0 | 100 | Reputation | Base of fear |
| fear_wrath_divisor | ofke_bolen | 3 | 1 | 100 | Reputation | God's wrath contribution to fear: (wrath − default) / this number |
| chained_fear | zincir_korku | 15 | 0 | 100 | Reputation | Extra fear of a chained son |
| neglect_per_epoch | unutma_cag | 12 | 0 | 100 | Reputation | Contribution of each epoch without contact to neglect (forgottenness) |
| neglect_per_unanswered_prayer | cevapsiz_unutma | 5 | 0 | 100 | Reputation | Contribution of each unanswered prayer to neglect |
| attention_threshold | ilgi_esik | 40 | 0 | 100 | Reputation | If the god's attention is below this, neglect rises |
| neglect_attention_divisor | ilgi_bolen | 2 | 1 | 100 | Reputation | Inattention contribution to neglect: missing attention / this number |
| forgotten_min_neglect | unutulan_unutma | 60 | 0 | 100 | Reputation | Minimum neglect to count as "Forgotten" |
| forgotten_love_below | unutulan_sevgi | 50 | 0 | 100 | Reputation | Love must stay below this to count as "Forgotten" |
| forgotten_fear_below | unutulan_korku | 50 | 0 | 100 | Reputation | Fear must stay below this to count as "Forgotten" |
| hated_min_fear | nefret_korku | 55 | 0 | 100 | Reputation | Minimum fear to count as "Hated" |
| hated_love_below | nefret_sevgi | 35 | 0 | 100 | Reputation | Love must stay below this to count as "Hated" |
| hated_loyalty_below | nefret_sadakat | 35 | 0 | 100 | Reputation | Loyalty must stay below this to count as "Hated" |
| respected_min_fear | saygi_korku | 50 | 0 | 100 | Reputation | Minimum fear to count as "Respected" |
| respected_min_love | saygi_sevgi | 50 | 0 | 100 | Reputation | Minimum love to count as "Respected" |
| feared_min_fear | korkulan_korku | 50 | 0 | 100 | Reputation | Minimum fear to count as "Feared" |
| loved_min_love | sevilen_sevgi | 55 | 0 | 100 | Reputation | Minimum love to count as "Loved" |
| distant_min_neglect | uzak_unutma | 40 | 0 | 100 | Reputation | Minimum neglect to count as "Distant" |
| loved_loyalty_gain | sevilen_sadakat | 2 | 0 | 50 | Reputation | Loyalty gain per epoch of a son who loves his father |
| respected_loyalty_gain | saygi_sadakat | 1 | 0 | 50 | Reputation | Loyalty gain per epoch of a son who respects his father |
| respected_wrath_gain | saygi_ofke | 1 | 0 | 50 | Reputation | Wrath gain per epoch of a son who respects his father |
| feared_wrath_gain | korkulan_ofke | 2 | 0 | 50 | Reputation | Wrath gain per epoch of a son who fears his father |
| hated_loyalty_loss | nefret_sadakat_kayip | 2 | 0 | 50 | Reputation | Loyalty loss per epoch of a son who hates his father |
| hated_wrath_gain | nefret_ofke | 3 | 0 | 50 | Reputation | Wrath gain per epoch of a son who hates his father |
| forgotten_loyalty_loss | unutulan_sadakat_kayip | 2 | 0 | 50 | Reputation | Loyalty loss per epoch of a forgotten son |
| distant_loyalty_loss | uzak_sadakat_kayip | 1 | 0 | 50 | Reputation | Loyalty loss per epoch of a son whose father is distant |
| manual_push_keep_pct | elle_kalan | 60 | 0 | 100 | Reputation | Share of the god's manual push kept each epoch (%) |
| manual_push_floor | elle_esik | 2 | 1 | 100 | Reputation | A manual push fading below this value is deleted |
| manual_push_cap | elle_tavan | 60 | 0 | 100 | Reputation | Maximum value of a manual push on each axis |
| manual_love_click | elle_sevgi | 10 | 1 | 100 | Reputation | Love push of one click on the "Win his heart" button in the son drawer |
| manual_fear_click | elle_korku | 10 | 1 | 100 | Reputation | Fear push of one click on the "Instil fear" button in the son drawer |
| manual_neglect_click | elle_unutma | 15 | 1 | 100 | Reputation | Push of one click on the make-forget button in the son drawer |
| power_trace_keep_pct | olay_kalan | 60 | 0 | 100 | Reputation | Share of the reputation trace left by the god's power that is kept each epoch (%) |
| power_trace_cap | olay_tavan | 80 | 0 | 100 | Reputation | Maximum value on each axis of the reputation trace left by the god's power |
| drain_fear | em_korku | 15 | 0 | 100 | Reputation | Extra fear of a son whose essence is drained, toward his father |
| drain_love_loss | em_sevgi | 12 | 0 | 100 | Reputation | Love toward his father lost by a son whose essence is drained |
| drain_sibling_fear | em_kardes_korku | 6 | 0 | 100 | Reputation | Extra fear of siblings who witness essence draining |
| devour_sibling_fear | yut_kardes_korku | 20 | 0 | 100 | Reputation | Extra fear of siblings who witness a son being devoured |
| devour_friend_love_loss | yut_dost_sevgi | 15 | 0 | 100 | Reputation | Love toward the father lost by those who loved the devoured son |
| demote_fear | alcalt_korku | 12 | 0 | 100 | Reputation | Extra fear of a demoted (humbled) son |
| demote_love_loss | alcalt_sevgi | 12 | 0 | 100 | Reputation | Love lost by a demoted son |
| demote_sibling_fear | alcalt_kardes_korku | 4 | 0 | 100 | Reputation | Extra fear of those who see a sibling demoted |
| strip_power_fear | sok_korku | 10 | 0 | 100 | Reputation | Extra fear of a son whose power is stripped |
| strip_power_love_loss | sok_sevgi | 8 | 0 | 100 | Reputation | Love lost by a son whose power is stripped |
| strip_power_sibling_fear | sok_kardes_korku | 3 | 0 | 100 | Reputation | Extra fear of those who see a sibling's power stripped |

### SERVER

Old namespace `SUNUCU` · 42 rows · defined in `server.js`. HTTP API list sizes, search limits, health, thumbnails (server.js).

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| community_relations_shown | iliski_liste | 10 | 0 | 1000 | Interface | Relations shown on the community page |
| son_chronicle_lines | ogul_kronik | 80 | 0 | 10,000 | Interface | Chronicle lines shown on the son page |
| foreign_god_chronicle_lines | yabanci_kronik | 80 | 0 | 10,000 | Interface | Chronicle lines shown on the foreign-god page |
| son_messages_shown | ogul_mesaj | 40 | 0 | 10,000 | Interface | Messages shown on the son page |
| entity_canon_facts | varlik_gercek | 30 | 0 | 10,000 | Interface | Canon facts shown on the entity page |
| people_perspective_lines | varlik_bakis | 8 | 0 | 1000 | Interface | Partisan chronicle (perspectives) shown on the people page |
| entity_mentions | varlik_anilan | 40 | 0 | 10,000 | Interface | "Where it was mentioned" list on the entity page |
| chronicle_latest | kronik_son | 600 | 1 | 100,000 | Interface | Chronicle: latest lines returned for a request without parameters |
| chronicle_page_size | kronik_sayfa | 200 | 1 | 100,000 | Interface | Chronicle: backward page size |
| chronicle_page_max | kronik_sayfa_tavan | 500 | 1 | 100,000 | Interface | Chronicle: largest page that can be requested |
| lexicon_words_per_language | sozluk_kelime | 2000 | 1 | 1,000,000 | Interface | Words per language shown on the lexicon page |
| notification_page_size | bildirim_sayfa | 60 | 1 | 100,000 | Interface | Page size of the notification list |
| notification_page_max | bildirim_tavan | 500 | 1 | 100,000 | Interface | Largest page of the notification list |
| ledger_page_size | defter_sayfa | 80 | 1 | 100,000 | Interface | Fate's ledger: page size |
| ledger_page_max | defter_tavan | 300 | 1 | 100,000 | Interface | Fate's ledger: largest page |
| metrics_default_epochs | olcum_cag | 10 | 1 | 10,000 | Interface | Model metrics: default epoch window |
| metrics_max_epochs | olcum_cag_tavan | 50 | 1 | 10,000 | Interface | Model metrics: widest epoch window |
| live_feed_history | gunluk_api | 300 | 1 | 100,000 | Interface | Latest events returned in the live-feed history |
| cosmic_chronicle_default | kozmik_kronik | 30 | 1 | 100,000 | Interface | Cosmic chronicle: default lines |
| cosmic_chronicle_max | kozmik_kronik_tavan | 200 | 1 | 100,000 | Interface | Cosmic chronicle: maximum lines |
| gallery_missing | galeri_eksik | 40 | 1 | 100,000 | Interface | Gallery: list of important records missing an image |
| gallery_missing_max | galeri_eksik_tavan | 500 | 1 | 100,000 | Interface | Gallery: largest size of the missing-image list |
| prayer_list | dua_liste | 100 | 1 | 100,000 | Interface | Prayers: shown separately from sons and from mortals |
| council_minutes_list | konsey_liste | 30 | 1 | 100,000 | Interface | Council minutes list |
| god_traces | tanri_iz | 40 | 0 | 100,000 | Interface | Chronicle traces on the god page |
| search_sons | ara_ogul | 8 | 0 | 1000 | Search | Search: son results |
| search_cosmos | ara_kozmos | 10 | 0 | 10,000 | Search | Foreign gods, worlds and stars shown in search (each) |
| search_entities | ara_varlik | 25 | 0 | 1000 | Search | Search: entity results |
| search_lexicon | ara_kelime | 10 | 0 | 1000 | Search | Search: lexicon results |
| search_epochs | ara_cag | 5 | 0 | 1000 | Search | Search: epoch results |
| search_chronicle | ara_kronik | 15 | 0 | 1000 | Search | Search: chronicle results |
| search_personal_notes | ara_not | 6 | 0 | 1000 | Search | Search: personal-note results |
| search_map_notes | ara_harita | 6 | 0 | 1000 | Search | Search: map-note results |
| search_messages | ara_mesaj | 8 | 0 | 1000 | Search | Search: message results |
| search_councils | ara_konsey | 5 | 0 | 1000 | Search | Search: council results |
| search_total | ara_toplam | 60 | 1 | 10,000 | Search | Search: total results |
| cheat_essence_max | hile_oz_tavan | 1,000,000 | 1 | 1,000,000,000 | The god's actions | Cheat: maximum essence that can be added at once |
| health_error_minutes | saglik_hata_dk | 10 | 0 | 100,000 | Server | Health: errors in the last this many minutes make the status "warning" |
| health_errors_shown | saglik_hata_liste | 10 | 0 | 1000 | Server | Health: recent errors shown |
| thumbnail_concurrency | kucuk_esz | 3 | 1 | 64 | Server | Maximum simultaneous thumbnail generations |
| thumbnail_timeout | kucuk_sure | 30 | 1 | 3600 | Server | Thumbnail generation timeout (s) |
| auto_complete_delay_ms | tamamla_gecikme | 1500 | 0 | 600,000 | Agents and model | Delay of automatic completion after startup (ms) |

### SETUP_WIZARD

Old namespace `SIHIRBAZ` · 7 rows · defined in `src/sihirbaz.js`. Genesis wizard defaults.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| magic | buyu | 50 | 0 | 100 | Genesis wizard | Wizard: default magic density |
| darkness | karanlik | 50 | 0 | 100 | Genesis wizard | Wizard: default darkness |
| peoples | halk | 2 | 1 | 50 | Genesis wizard | Wizard: default number of initial peoples |
| peoples_max | halk_en_cok | 5 | 1 | 50 | Genesis wizard | Wizard: maximum initial peoples |
| small_cosmos_worlds | kucuk_kozmos | 1 | 0 | 20 | Genesis wizard | Small cosmos: worlds added at genesis |
| large_cosmos_worlds | buyuk_kozmos | 2 | 0 | 20 | Genesis wizard | Large cosmos: worlds added at genesis |
| setting_pull_pct | cekim | 50 | 0 | 100 | Genesis wizard | After genesis, regions' magic/danger is pulled toward the setting by this percentage |

### SKY

Old namespace `GOK` · 56 rows · defined in `src/gok.js`. Sky events: eclipses, comets, alignments, supernovae, black suns, time echoes.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| supernova_apocalypse | supernova_kiyamet | 10 | 0 | 100 | Apocalypse | Contribution of a supernova to the apocalypse |
| supernova_population_loss_pct | supernova_nufus | 40 | 0 | 100 | Sky | Population lost in a supernova (%) |
| supernova_fertility_loss | supernova_bereket | 30 | 0 | 100 | Sky | Fertility loss in a supernova |
| alignment_open_epochs | dizilim_sure | 2 | 1 | 20 | Sky | Epochs a planetary alignment keeps a sealed route open |
| alignment_danger | dizilim_tehlike | 15 | 0 | 100 | Sky | A dread alignment increases route danger |
| comet_peace_chance | kuyruklu_baris_sans | 50 | 0 | 100 | Sky | A comet ends a war (%) |
| sky_event_chance | gok_olay_sans | 18 | 0 | 100 | Sky | Spontaneous sky event (% per epoch) |
| star_event_chance | yildiz_olay_sans | 30 | 0 | 100 | Sky | A supernova or black sun occurs (%) |
| time_echo_chance | zaman_yanki_sans | 6 | 0 | 100 | Sky | Time echo (%) |
| time_traveler_share_pct | zaman_yolcu_orani | 50 | 0 | 100 | Sky | Share of echoes that are time travellers (%) |
| two_timed_hero_chance | iki_zamanli_sans | 3 | 0 | 100 | Sky | Two-timed hero (%) |
| alignment_danger_cap | dizilim_tehlike_tavan | 95 | 0 | 100 | Sky | Highest value to which alignment dread can raise route danger |
| alignment_danger_drop | dizilim_tehlike_azalma | 10 | 0 | 100 | Sky | Route danger drop during a planetary alignment |
| alignment_danger_floor | dizilim_tehlike_taban | 5 | 0 | 100 | Sky | Lowest value to which an alignment can lower route danger |
| star_pick_base_weight | yildiz_secim_taban | 5 | 0 | 1000 | Sky | Base weight of each celestial body when choosing the star of the epoch |
| event_weight_eclipse | olay_tutulma | 2 | 0 | 50 | Sky | Spontaneous sky event weight: eclipse |
| event_weight_comet | olay_kuyruklu | 2 | 0 | 50 | Sky | Spontaneous sky event weight: comet |
| event_weight_alignment | olay_dizilim | 1 | 0 | 50 | Sky | Spontaneous sky event weight: planetary alignment |
| event_weight_supernova | olay_supernova | 1 | 0 | 50 | Sky | Spontaneous sky event weight: supernova |
| event_weight_black_sun | olay_kara_gunes | 1 | 0 | 50 | Sky | Spontaneous sky event weight: black sun |
| eclipse_sanity_loss | tutulma_sagduyu | 5 | 0 | 100 | Sky | Mortals' sanity loss during an eclipse |
| eclipse_piety_gain | tutulma_inanc | 5 | 0 | 100 | Sky | Piety increase during an eclipse |
| eclipse_prophecy_power | tutulma_kehanet_seviye | 4 | 1 | 12 | Sky | Power level of the eclipse prophecy |
| eclipse_prophet_communities | tutulma_kahin | 2 | 0 | 20 | Sky | Number of communities whispering the eclipse prophecy (the world's most important) |
| eclipse_certainty_base | tutulma_kesinlik_taban | 40 | 0 | 100 | Sky | Base certainty of the eclipse prophecy |
| eclipse_certainty_die | tutulma_kesinlik_zar | 40 | 1 | 100 | Sky | Certainty die of the eclipse prophecy (1…n) |
| comet_power | kuyruklu_seviye | 4 | 1 | 12 | Sky | Power level of a comet |
| comet_brightness_base | kuyruklu_parlaklik_taban | 60 | 0 | 100 | Sky | Base brightness of a comet |
| comet_brightness_die | kuyruklu_parlaklik_zar | 30 | 1 | 100 | Sky | Brightness die of a comet (1…n) |
| comet_influence_base | kuyruklu_etki_taban | 40 | 0 | 100 | Sky | Base influence of a comet |
| comet_influence_die | kuyruklu_etki_zar | 40 | 1 | 100 | Sky | Influence die of a comet (1…n) |
| supernova_remnant_brightness | supernova_kalinti_parlaklik | 15 | 0 | 100 | Sky | Brightness of a supernova remnant |
| supernova_leak | supernova_sizinti | 15 | 0 | 100 | Cosmic horror | Leak contribution of a supernova to nearby worlds |
| black_sun_leak | kara_gunes_sizinti | 25 | 0 | 100 | Cosmic horror | Leak contribution of a black sun to its worlds |
| black_sun_outer_cult_mult_pct | kara_gunes_murit | 140 | 100 | 1000 | Sky | Follower multiplier of outer cults under a black sun (%) |
| traveler_power | yolcu_seviye | 5 | 1 | 12 | Sky | Power level of a time traveller |
| traveler_hp | yolcu_can | 120 | 1 | 1000 | Sky | HP of a time traveller |
| traveler_strength_base | yolcu_guc_taban | 40 | 0 | 100 | Sky | Base strength of a time traveller |
| traveler_strength_die | yolcu_guc_zar | 30 | 1 | 100 | Sky | Strength die of a time traveller (1…n) |
| traveler_agility_base | yolcu_ceviklik_taban | 40 | 0 | 100 | Sky | Base agility of a time traveller |
| traveler_agility_die | yolcu_ceviklik_zar | 30 | 1 | 100 | Sky | Agility die of a time traveller (1…n) |
| traveler_intellect_base | yolcu_akil_taban | 60 | 0 | 100 | Sky | Base intellect of a time traveller |
| traveler_intellect_die | yolcu_akil_zar | 40 | 1 | 100 | Sky | Intellect die of a time traveller (1…n) |
| traveler_charisma_base | yolcu_karizma_taban | 40 | 0 | 100 | Sky | Base charisma of a time traveller |
| traveler_charisma_die | yolcu_karizma_zar | 40 | 1 | 100 | Sky | Charisma die of a time traveller (1…n) |
| traveler_age_base | yolcu_yas_taban | 30 | 0 | 1000 | Sky | Base age of a time traveller (years) |
| traveler_age_die | yolcu_yas_zar | 40 | 1 | 1000 | Sky | Age die of a time traveller (1…n years) |
| traveler_lifespan | yolcu_omur | 200 | 1 | 50,000 | Sky | Lifespan of a time traveller (years) |
| traveler_sanity | yolcu_sagduyu | 50 | 0 | 100 | Sky | Sanity of a time traveller |
| echo_prophecy_power | yanki_kehanet_seviye | 5 | 1 | 12 | Sky | Power level of a prophecy leaking into the past |
| echo_certainty_base | yanki_kesinlik_taban | 70 | 0 | 100 | Sky | Base certainty of a prophecy leaking into the past |
| echo_certainty_die | yanki_kesinlik_zar | 30 | 1 | 100 | Sky | Certainty die of a prophecy leaking into the past (1…n) |
| two_timed_min_charisma | iki_zamanli_karizma | 70 | 0 | 100 | Sky | Minimum charisma of a hero who can become two-timed |
| time_factor_diff_threshold_pct | zaman_fark_esik | 75 | 0 | 1000 | Sky | Time-factor difference that causes an age difference (%) |
| god_storm_epochs | firtina_sure | 3 | 1 | 50 | Cosmos and travel | Epochs a void storm unleashed by the god severs a route (if no duration is given) |
| cult_default_followers | murit_varsayilan | 50 | 1 | 100,000 | Sky | Followers assumed for a cult with no recorded follower count (black sun) |

### SON_RELATIONS

Old namespace `OGUL_ILISKI` · 4 rows · defined in `src/world.js`. Son-to-son relation label thresholds.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| devotion | baglilik | 60 | -100 | 100 | War and diplomacy | Between sons: this and above is devotion |
| friendship | dostluk | 25 | -100 | 100 | War and diplomacy | Between sons: this and above is friendship |
| hostility | husumet | 25 | 0 | 100 | War and diplomacy | Between sons: minus this and below is hostility |
| hatred | nefret | 60 | 0 | 100 | War and diplomacy | Between sons: minus this and below is hatred |

### SON_TOOLS

Old namespace `OGUL_ARAC` · 192 rows · defined in `src/tools.js` · also read by `src/agents.js`, `src/panteon.js`, `src/tanriguc.js`, `src/world.js`. Son agent tool parameters.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| anchor_per_epoch | capa_tur | 1 | 0 | 20 | Son tools | Maximum times a son can change his anchor in one epoch |
| gift_per_epoch | armagan_tur | 1 | 0 | 20 | Son tools | Maximum gifts a son can give in one epoch |
| prayer_per_epoch | dua_tur | 1 | 0 | 20 | Son tools | Maximum prayers a son can make to his father in one epoch |
| holy_world_per_epoch | kutsal_dunya_tur | 1 | 0 | 20 | Son tools | Maximum holy-world declarations a son can make in one epoch |
| stitch_per_epoch | sizinti_dik_tur | 1 | 0 | 20 | Son tools | Maximum rifts a son can stitch in one epoch |
| free_living_creation | canli_bedava | 1 | 0 | 1 | Son tools | The epoch's first living creation costs no action (1 on, 0 off) |
| link_cost | bag_bedel | 2 | 0 | 100 | Son tools | create_link (bag_kur) cost (essence) |
| link_per_epoch | bag_tavan | 3 | 0 | 50 | Son tools | create_link per epoch |
| coin_word_per_epoch | kelime_tur | 2 | 0 | 20 | Language and names | coin_word (kelime_tureti) per epoch |
| coin_word_max_words | kelime_adet | 8 | 1 | 40 | Language and names | Maximum words in one coin_word call |
| sibling_message_per_epoch | mesaj_tavan | 2 | 0 | 20 | Son tools | Words to a sibling per epoch |
| covenant_min_relation | ahit_esik | 25 | -100 | 100 | Son tools | Minimum relation required for a covenant |
| covenant_relation_bonus | ahit_bonus | 15 | 0 | 100 | Son tools | Contribution of a covenant to the relation |
| gift_max_essence | armagan_oz | 40 | 0 | 1000 | Son tools | Maximum essence in a single gift |
| challenge_min_wound | meydan_yara | 8 | 0 | 200 | Son tools | Minimum wound of the loser in a challenge |
| challenge_max_steal | meydan_calinti | 10 | 0 | 200 | Son tools | Maximum essence the winner snatches in a challenge |
| challenge_xp | meydan_xp | 25 | 0 | 500 | Son tools | XP of the challenge winner |
| challenge_renown | meydan_un | 5 | 0 | 200 | Son tools | Renown of the challenge winner |
| covenant_break_renown_cost | ahit_bozma_un | 10 | 0 | 200 | Son tools | Renown cost of challenging a covenanted sibling |
| rebel_loyalty | isyan_sadakat | 40 | 0 | 100 | Son tools | Below this loyalty, rebellion is possible |
| harvest_abundance_loss | sag_bolluk | 8 | 0 | 100 | Son tools | Abundance loss when a resource is harvested |
| harvest_depleted_threshold | sag_tukenme | 5 | 0 | 100 | Son tools | Below this abundance a resource counts as depleted |
| repeat_cost_increase_pct | tekrar_artis | 25 | 0 | 500 | Son tools | Cost increase of each new creation of the same subtype (%) |
| repeat_cost_cap_pct | tekrar_tavan | 250 | 100 | 1000 | Son tools | Cap of the repetition cost (%) |
| repeat_window_epochs | tekrar_pencere | 6 | 1 | 100 | Son tools | Epochs in which repetition is counted |
| influence_max_change_pct | etkile_oran | 30 | 1 | 100 | Son tools | Maximum stat change with influence_entity (varligi_etkile) (%) |
| intervention_cost_pct | mudahale_oran | 70 | 0 | 500 | Son tools | Son's miracle/disaster/knowledge cost as a percentage of the Creator's intervention cost |
| cosmic_seal_pct | kozmik_muhur | 70 | 0 | 500 | Son tools | Gate-seal cost as a percentage of the Creator's |
| cosmic_rekindle_pct | kozmik_tutustur | 85 | 0 | 500 | Son tools | Star-rekindle cost as a percentage of the Creator's |
| cosmic_spirit_cloak_pct | kozmik_ruh | 80 | 0 | 500 | Son tools | Spirit-cloak cost as a percentage of the Creator's |
| cosmic_hang_star_pct | kozmik_yildiz | 75 | 0 | 500 | Son tools | Star-hanging cost as a percentage of the Creator's |
| cosmic_extinguish_pct | kozmik_sondur | 100 | 0 | 500 | Son tools | Star-extinguishing cost as a percentage of the Creator's star cost |
| foreign_bargain_essence | yabanci_pazarlik | 15 | 0 | 500 | Son tools | Essence from a successful bargain with a foreign god |
| birth_world_xp | dunya_dogur_xp | 60 | 0 | 1000 | Son tools | XP of a son who births a world |
| birth_world_renown | dunya_dogur_un | 15 | 0 | 500 | Son tools | Renown of a son who births a world |
| treaty_cost | antlasma_oz | 20 | 0 | 500 | Son tools | make_treaty (antlasma_yap) cost (essence) |
| treaty_ap | antlasma_ap | 1 | 1 | 5 | Son tools | make_treaty action cost |
| treaty_relation | antlasma_iliski | 15 | 0 | 100 | Son tools | Contribution of an inter-world treaty to the two communities' relation |
| stitch_cost | sizinti_oz | 35 | 0 | 500 | Son tools | stitch_leak (sizinti_dik) cost (essence) |
| stitch_ap | sizinti_ap | 1 | 1 | 5 | Son tools | stitch_leak action cost |
| stitch_leak_reduction | sizinti_azalis | 25 | 1 | 100 | Son tools | Leak reduction from stitch_leak |
| open_deposit_cost | yatak_oz | 60 | 0 | 1000 | Son tools | open_deposit (yatak_ac) cost (essence) |
| open_deposit_ap | yatak_ap | 2 | 1 | 5 | Son tools | open_deposit action cost |
| location_suggestions | konum_oneri | 5 | 0 | 50 | Son tools | Number of locations suggested on a missing-location creation error |
| foreign_war_cost | ysavas_oz | 30 | 0 | 500 | Son tools | war_with_foreign_god (yabanci_tanriyla_savas): cost of entering the war (essence) |
| foreign_war_ap | ysavas_ap | 2 | 1 | 5 | Son tools | war_with_foreign_god action cost |
| foreign_war_die | ysavas_zar | 40 | 1 | 200 | Son tools | Die faces for both sides in a war with a foreign god |
| foreign_war_strength_per_level | ysavas_seviye | 3 | 0 | 50 | Son tools | Son's strength per level in a war with a foreign god |
| foreign_war_crushing_margin | ysavas_ezici | 35 | 1 | 300 | Son tools | In a war won by this margin, the foreign god dies |
| foreign_war_min_wound | ysavas_yara | 15 | 0 | 500 | Son tools | Minimum wound of a son defeated by a foreign god |
| foreign_war_essence_loss | ysavas_oz_kayip | 25 | 0 | 500 | Son tools | Essence lost by a son defeated by a foreign god |
| foreign_war_sleep_epochs | ysavas_uyku | 2 | 1 | 20 | Son tools | Sleep duration of a son whose HP runs out (epochs) |
| foreign_war_xp | ysavas_xp | 40 | 0 | 1000 | Son tools | XP of a son who defeats a foreign god |
| foreign_war_renown | ysavas_un | 12 | 0 | 500 | Son tools | Renown of a son who defeats a foreign god |
| foreign_war_attitude_loss | ysavas_tutum | 30 | 0 | 200 | Son tools | Damage of the war to the foreign god's attitude toward the pantheon |
| foreign_war_strength_loss | ysavas_guc_kayip | 20 | 0 | 100 | Son tools | Strength loss of a defeated foreign god |
| healing_sanity | sifa_sagduyu | 12 | 0 | 100 | Son tools | Contribution of the healing miracle to the sanity of affected communities |
| default_sanity | sagduyu_taban | 70 | 0 | 100 | Son tools | Sanity of a community with no recorded sanity (same as the horror module default) |
| mortal_age_min_pct | yas_min | 20 | 0 | 100 | Mortals | New mortal's starting age: minimum percentage of lifespan |
| mortal_age_max_pct | yas_max | 50 | 0 | 100 | Mortals | New mortal's starting age: maximum percentage of lifespan |
| default_stat_base | stat_taban | 15 | 0 | 100 | Son tools | Unspecified stat of a created entity (0–100 scale): base |
| default_stat_per_power | stat_guc | 7 | 0 | 50 | Son tools | Unspecified stat of a created entity: extra per power level |
| default_mortal_age | varsayilan_yas | 20 | 0 | 2000 | Mortals | Age of a new mortal with no specified age |
| default_mortal_lifespan | varsayilan_omur | 70 | 1 | 50,000 | Mortals | Lifespan of a new mortal with no specified lifespan |
| people_population_per_power_sq | nufus_halk | 2000 | 1 | 1,000,000 | Population and growth | New people with no specified population: population per power level squared |
| other_population_per_power_sq | nufus_diger | 300 | 1 | 1,000,000 | Population and growth | New settlement or community with no specified population: population per power level squared |
| cult_followers_per_power_sq | murit_guc | 60 | 1 | 1,000,000 | Religion and language | New cult with no specified followers: followers per power level squared |
| level_up_stat_1 | seviye_stat1 | 3 | 0 | 50 | Son tools | Added to a random first stat of a levelling-up son |
| level_up_stat_2 | seviye_stat2 | 2 | 0 | 50 | Son tools | Added to a random second stat of a levelling-up son |
| message_relation_base | ses_taban | 3 | 0 | 100 | Son tools | Relation effect of a word to a sibling: base |
| message_charisma_divisor | ses_karizma_bolen | 12 | 1 | 1000 | Son tools | Relation effect of a word to a sibling: + charisma / this number |
| message_alliance_bonus | ses_ittifak | 2 | 0 | 100 | Son tools | Extra relation contribution of an alliance message |
| message_love_bonus | ses_ask | 4 | 0 | 100 | Son tools | Extra relation contribution of a love message |
| message_threat_penalty | ses_tehdit | 3 | 0 | 100 | Son tools | Extra relation damage of a threat |
| message_warning_penalty | ses_uyari | 2 | 0 | 100 | Son tools | Relation damage of a warning |
| message_bargain_effect | ses_pazarlik | 1 | -100 | 100 | Son tools | Relation effect of a bargaining message |
| gift_min_remaining | armagan_kalan | 5 | 0 | 1000 | Son tools | Minimum essence the son must keep after a gift |
| transfer_base_pct | devir_taban | 45 | 0 | 100 | Son tools | Acceptance chance of a worshipper transfer: base (%; + (recipient's charisma − worshipper's piety/2) / 2) |
| gift_relation_base | armagan_iliski | 4 | 0 | 100 | Son tools | Relation contribution of a gift: base |
| gift_relation_essence_divisor | armagan_oz_bolen | 5 | 1 | 1000 | Son tools | Relation contribution of a gift: + essence given / this number |
| gift_worshipper_relation | armagan_tapan_iliski | 10 | 0 | 100 | Son tools | Extra relation contribution of an accepted worshipper transfer |
| challenge_die | meydan_zar | 20 | 1 | 200 | Son tools | Challenge die faces (double the result is added) |
| challenge_power_bonus | meydan_guc_bonus | 15 | 0 | 100 | Son tools | Challenge bonus for a son with the duel power in his own field |
| challenge_untouchable | meydan_dokunulmaz | 15 | 0 | 100 | Son tools | Subtracted from the challenging rival by the Untouchable power |
| challenge_loser_renown_loss | meydan_un_kayip | 2 | 0 | 100 | Son tools | Renown loss of the challenge loser |
| challenge_sleep_epochs | meydan_uyku | 2 | 1 | 20 | Son tools | Sleep duration of a son whose HP runs out in a challenge (epochs) |
| challenge_relation | meydan_iliski | 15 | 0 | 200 | Son tools | Relation damage of a challenge |
| challenge_covenant_relation | meydan_ahit_iliski | 40 | 0 | 200 | Son tools | Relation damage of challenging a covenanted sibling |
| rebel_loyalty_loss | isyan_sadakat_kayip | 10 | 0 | 100 | Son tools | Loyalty loss of a rebelling son |
| rebel_ambition | isyan_hirs | 5 | 0 | 100 | Son tools | Ambition gain of a rebelling son |
| rebel_loyal_threshold | isyan_sadik_esik | 60 | 0 | 100 | Son tools | Siblings with loyalty at or above this cool toward the rebel |
| rebel_sibling_relation | isyan_kardes_iliski | 12 | 0 | 200 | Son tools | Relation damage of a rebellion with loyal siblings |
| harvest_abundance_divisor | sag_bolluk_bolen | 8 | 1 | 1000 | Son tools | Resource harvest gain: resource abundance / this number |
| harvest_wisdom_divisor | sag_bilgelik_bolen | 20 | 1 | 1000 | Son tools | Resource harvest gain: + wisdom / this number |
| harvest_might_divisor | sag_kudret_bolen | 25 | 1 | 1000 | Son tools | Resource harvest gain: + resource might / this number |
| harvest_power_mult | sag_hasat_kat | 2 | 1 | 20 | Son tools | Multiplier of resource harvest gain with the Harvester power |
| star_domain_cost_pct | yildiz_indirim | 70 | 1 | 100 | Son tools | Cost of a creation in the domain of the epoch's star (%) |
| event_severity_base | olay_siddet_taban | 15 | 0 | 100 | Son tools | Severity of an event with no specified severity: base |
| event_severity_per_power | olay_siddet_guc | 7 | 0 | 50 | Son tools | Severity of an event with no specified severity: per power level |
| item_resource_might_divisor | esya_kaynak_bolen | 4 | 1 | 1000 | Son tools | Might bonus of an item forged from a resource: resource might / this number |
| megafauna_power | megafauna_guc | 8 | 1 | 30 | Creatures | A new creature species at or above this power level counts as megafauna |
| creation_xp_base | yaratim_xp | 10 | 0 | 500 | Son tools | XP of a creation: base |
| creation_xp_per_power | yaratim_xp_guc | 3 | 0 | 100 | Son tools | XP of a creation: per power level |
| co_creator_xp_base | ortak_xp | 8 | 0 | 500 | Son tools | Co-creator's XP: base |
| co_creator_xp_per_power | ortak_xp_guc | 2 | 0 | 100 | Son tools | Co-creator's XP: per power level |
| co_creator_renown | ortak_un | 1 | 0 | 100 | Son tools | Co-creator's renown |
| co_creation_relation | ortak_iliski | 5 | 0 | 100 | Son tools | Contribution of a joint creation to the two siblings' relation |
| creation_max_links | yaratim_bag_adet | 6 | 1 | 30 | Son tools | Maximum links in one creation |
| knowledge_first_learners | ogrenen_adet | 3 | 0 | 20 | Son tools | Maximum communities first learning new knowledge |
| creature_max_traits | ozellik_adet | 3 | 0 | 10 | Creatures | Maximum traits of a new creature species |
| event_max_effects | olay_etki_adet | 5 | 0 | 20 | Son tools | Maximum stat effects of an event |
| influence_max_stats | etkile_stat_adet | 3 | 1 | 20 | Son tools | Maximum stats changed in one influence_entity call |
| influence_foreign_cost_mult | etkile_yabanci_kat | 2 | 1 | 10 | Son tools | Cost multiplier of influencing someone else's creation |
| influence_foreign_relation | etkile_iliski | 6 | 0 | 200 | Son tools | Relation damage with the creator when influencing someone else's creation |
| chosen_strength | secilmis_guc | 12 | 0 | 100 | Son tools | Strength gain of a mortal declared chosen |
| chosen_charisma | secilmis_karizma | 10 | 0 | 100 | Son tools | Charisma gain of a mortal declared chosen |
| chosen_lifespan | secilmis_omur | 40 | 0 | 50,000 | Son tools | Lifespan gain of a mortal declared chosen |
| chosen_foreign_relation | secilmis_iliski | 5 | 0 | 200 | Son tools | Relation damage with the creator when declaring someone else's mortal chosen |
| curse_cost_per_power | lanet_guc | 2 | 0 | 50 | Son tools | Curse cost: essence per power level of the cursed |
| curser_cost_pct | lanetci_bedel | 50 | 1 | 100 | Son tools | Curse cost with the Curser power (%) |
| curser_severity_pct | lanetci_siddet | 150 | 100 | 500 | Son tools | Curse severity with the Curser power (%) |
| curse_resist_divisor | lanet_direnc_bolen | 4 | 1 | 1000 | Son tools | Patron's resistance to the curse: patron's will / this number |
| curse_untouchable_resist | lanet_dokunulmaz | 15 | 0 | 100 | Son tools | Extra resistance to the curse of an Untouchable patron |
| curse_severity_base | lanet_siddet_taban | 12 | 0 | 100 | Son tools | Curse severity: base (+ might / divisor − resistance / 2) |
| curse_might_divisor | lanet_kudret_bolen | 10 | 1 | 1000 | Son tools | Curse severity: + might / this number |
| curse_min_severity | lanet_siddet_en_az | 5 | 0 | 100 | Son tools | Minimum curse severity |
| curse_creator_relation | lanet_yaratan_iliski | 12 | 0 | 200 | Son tools | Relation damage of a curse with the cursed's creator |
| curse_patron_relation | lanet_hami_iliski | 8 | 0 | 200 | Son tools | Relation damage of a curse with the cursed's patron |
| miracle_xp | mucize_xp | 12 | 0 | 500 | Son tools | XP of a miracle |
| miracle_renown | mucize_un | 2 | 0 | 100 | Son tools | Renown of a miracle |
| dream_base_pct | ruya_taban | 45 | 0 | 100 | Son tools | Dream success chance: base (%) |
| dream_default_rival_charisma | ruya_karizma_varsayilan | 30 | 0 | 100 | Son tools | Dream: rival charisma assumed if the target has no god |
| dream_whisper_bonus_pct | ruya_fisilti | 25 | 0 | 100 | Son tools | Bonus of the Whisper power to dream chance (%) |
| dream_zealotry_divisor | ruya_bagnaz_bolen | 4 | 1 | 1000 | Son tools | Dream chance: − target's zealotry / this number |
| dream_min_pct | ruya_sans_min | 5 | 0 | 100 | Son tools | Lowest dream success chance (%) |
| dream_max_pct | ruya_sans_max | 95 | 0 | 100 | Son tools | Highest dream success chance (%) |
| dream_steal_relation | ruya_iliski | 20 | 0 | 200 | Son tools | Relation damage with the old god from losing a worshipper to a dream |
| dream_fail_relation | ruya_sezen_iliski | 8 | 0 | 200 | Son tools | Relation damage with the old god from a failed dream |
| dream_xp | ruya_xp | 20 | 0 | 500 | Son tools | XP of a successful dream |
| dream_renown | ruya_un | 4 | 0 | 100 | Son tools | Renown of a successful dream |
| disaster_cost_per_power | afet_guc | 2 | 0 | 50 | Son tools | Disaster cost: essence per power level of the target |
| disaster_severity_base | afet_siddet_taban | 40 | 0 | 100 | Son tools | Son's disaster severity: base (+ might / divisor + die) |
| disaster_might_divisor | afet_kudret_bolen | 3 | 1 | 1000 | Son tools | Son's disaster severity: + might / this number |
| disaster_die | afet_zar | 20 | 1 | 100 | Son tools | Son's disaster severity: die faces |
| disaster_min_severity | afet_siddet_min | 20 | 0 | 100 | Son tools | Lowest severity of a son's disaster |
| disaster_scale_divisor | afet_siddet_olcek | 70 | 1 | 1000 | Son tools | Disaster effect multiplier: severity / this number |
| disaster_patron_relation | afet_hami_iliski | 12 | 0 | 200 | Son tools | Relation damage of a disaster with the target's patron |
| disaster_creator_relation | afet_yaratan_iliski | 8 | 0 | 200 | Son tools | Relation damage of a disaster with the target's creator |
| knowledge_xp | bilgi_xp | 10 | 0 | 500 | Son tools | XP of teaching knowledge |
| knowledge_renown | bilgi_un | 2 | 0 | 100 | Son tools | Renown of teaching knowledge |
| incite_base_pct | kiskirt_taban | 45 | 0 | 100 | Son tools | Success chance of inciting war: base (%) |
| incite_cunning_divisor | kiskirt_kurnaz_bolen | 3 | 1 | 1000 | Son tools | Incite-war chance: + cunning / this number |
| incite_min_pct | kiskirt_sans_min | 10 | 0 | 100 | Son tools | Lowest incite-war chance (%) |
| incite_max_pct | kiskirt_sans_max | 95 | 0 | 100 | Son tools | Highest incite-war chance (%) |
| incite_patron_relation | kiskirt_iliski | 5 | 0 | 200 | Son tools | Relation damage of a successful incitement with the parties' patrons |
| transform_cost_per_power | donustur_guc | 2 | 0 | 50 | Son tools | Transform cost: essence per power level of the target |
| transform_creator_relation | donustur_iliski | 18 | 0 | 200 | Son tools | Relation damage of transforming with the creator |
| destroy_cost_per_power | yok_et_guc | 3 | 0 | 50 | Son tools | Destroy cost: essence per power level of the target |
| destroy_creator_relation | yok_et_iliski | 30 | 0 | 200 | Son tools | Relation damage of destroying with the creator |
| bear_child_ap | evlat_dogur_ap | 2 | 1 | 10 | Son tools | bear_child (evlat_dogur) action cost |
| rekindle_star_ap | tutustur_ap | 2 | 1 | 10 | Son tools | rekindle_star (yildiz_tutustur) action cost |
| rekindle_star_renown | tutustur_un | 15 | 0 | 500 | Son tools | Renown of a son who rekindles a star |
| hang_star_ap | yildiz_as_ap | 2 | 1 | 10 | Son tools | hang_star (yildiz_as) action cost |
| extinguish_star_ap | sondur_ap | 2 | 1 | 10 | Son tools | extinguish_star (yildiz_sondur) action cost |
| extinguish_star_renown | sondur_un | 25 | 0 | 500 | Son tools | Renown of a son who extinguishes a star |
| extinguish_star_relation | sondur_iliski | 15 | 0 | 200 | Son tools | Relation damage with all siblings from extinguishing a star |
| birth_world_ap | dunya_dogur_ap | 2 | 1 | 10 | Son tools | birth_world (dunya_dogur) action cost |
| foreign_alliance_threshold | yk_ittifak_esik | 80 | 0 | 300 | Son tools | Alliance with a foreign god: die threshold |
| foreign_alliance_attitude | yk_ittifak_tutum | 25 | 0 | 200 | Son tools | Attitude contribution of an accepted alliance |
| foreign_reject_attitude | yk_ret_tutum | 5 | 0 | 200 | Son tools | Attitude damage of a rejected alliance or bargain |
| foreign_threat_threshold | yk_tehdit_esik | 90 | 0 | 300 | Son tools | Threatening a foreign god: die threshold |
| foreign_threat_attitude | yk_tehdit_tutum | 10 | 0 | 200 | Son tools | Attitude damage of a successful threat |
| foreign_threat_strength | yk_tehdit_guc | 15 | 0 | 100 | Son tools | Strength taken from the foreign god by a successful threat |
| foreign_threat_fail_attitude | yk_tehdit_ofke | 25 | 0 | 200 | Son tools | Attitude damage of a failed threat |
| foreign_bargain_threshold | yk_pazarlik_esik | 70 | 0 | 300 | Son tools | Bargaining with a foreign god: die threshold |
| foreign_bargain_attitude | yk_pazarlik_tutum | 10 | 0 | 200 | Son tools | Attitude contribution of a successful bargain |
| challenge_die_mult | meydan_zar_kat | 2 | 0 | 20 | Son tools | Challenge: multiplier of the die result |
| challenge_strength_per_level | meydan_seviye_kat | 2 | 0 | 50 | Son tools | Challenge: son's strength per level |
| challenge_wound_diff_divisor | meydan_fark_bolen | 2 | 1 | 100 | Son tools | Challenge: loser's extra wound = score difference / this number |
| transfer_default_piety | devir_inanc_varsayilan | 50 | 0 | 100 | Son tools | Worshipper transfer: piety of a community with no recorded piety |
| transfer_piety_divisor | devir_inanc_bolen | 2 | 1 | 100 | Son tools | Worshipper transfer: worshipper's piety / this number (subtracted from the recipient's charisma) |
| transfer_diff_divisor | devir_fark_bolen | 2 | 1 | 100 | Son tools | Worshipper transfer: (charisma − piety share) / this number is added to the chance |
| dream_charisma_divisor | ruya_karizma_bolen | 2 | 1 | 100 | Son tools | Dream chance: + (charisma − rival charisma) / this number |
| curse_resist_effect_divisor | lanet_direnc_etki_bolen | 2 | 1 | 100 | Son tools | Curse severity: − patron's resistance / this number |
| foreign_talk_charisma_divisor | yk_karizma_bolen | 2 | 1 | 100 | Son tools | Talk die with a foreign god: + charisma / this number |
| foreign_threat_strength_divisor | yk_guc_bolen | 2 | 1 | 100 | Son tools | Threat die against a foreign god: + (strength − its strength) / this number |
| foreign_attitude_divisor | yk_tutum_bolen | 2 | 1 | 100 | Son tools | Alliance and bargain die with a foreign god: + attitude / this number |
| foreign_war_stat_divisor | ysavas_stat_bolen | 2 | 1 | 100 | Son tools | Son's strength in a war with a foreign god: (strength + will) / this number |
| reviving_sleep_epochs | dirilis_uyku | 1 | 1 | 20 | Son tools | Sleep duration when HP runs out for a son with the Reviving power (epochs) |
| default_loyalty | sadakat_varsayilan | 50 | 0 | 100 | Son tools | Loyalty of a son with no recorded loyalty (rebellion check) |
| outer_bargain_per_epoch | dis_pazarlik_tur | 1 | 0 | 20 | Son tools | Maximum bargains a son can make with an outer being in one epoch |
| inspect_sibling_creations | kardes_yaratim | 15 | 1 | 500 | Context budgets | inspect_sibling (kardesi_incele): maximum creations shown |

### SUMMONING

Old namespace `CAGIRMA` · 15 rows · defined in `src/agents.js` · also read by `server.js`, `src/epoch.js`. Son summoning and birth (initial existence, world choice, domains).

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| start_existence | varlik_baslangic | 60 | 0 | 100 | Son summoning and birth | A new son's existence (also assumed if unknown) |
| world_unclaimed_weight_pct | dunya_sahipsiz | 200 | 0 | 10,000 | Son summoning and birth | New son's world: score per community without worshipped god (%) |
| world_living_weight_pct | dunya_canli | 30 | 0 | 10,000 | Son summoning and birth | New son's world: score per living community (%) |
| world_son_penalty_pct | dunya_ogul | 300 | 0 | 10,000 | Son summoning and birth | New son's world: penalty per son already there (%) |
| domain_shift | alan_kaydir | 7 | 1 | 100 | Son summoning and birth | For a son whose two domains came out the same, how many positions away the second domain is taken |
| shared_domain_relation_loss | rakip_alan | 20 | 0 | 100 | Son summoning and birth | Relation loss of a new son with a sibling for each shared domain |
| parent_relation | ebeveyn_iliski | 40 | -100 | 100 | Son summoning and birth | Child's starting relation with its parent |
| other_parent_relation | es_iliski | 30 | -100 | 100 | Son summoning and birth | Child's starting relation with its other parent |
| child_rarity_rolls | dogur_deneme | 20 | 1 | 1000 | Son summoning and birth | Maximum rolls for a child's rarity (until it comes out lower than the parent) |
| recent_events | kronik | 15 | 0 | 500 | Context budgets | Recent events in the summoning prompt |
| rebel_ambition | isyan_hirs | 60 | 0 | 100 | Son summoning and birth | Son prompt: above this ambition (with low loyalty) prone to rebellion |
| rebel_will | isyan_irade | 70 | 0 | 100 | Son summoning and birth | Son prompt: above this will (with low loyalty) prone to rebellion |
| opportunities_chars | firsat_butce | 2500 | 0 | 100,000 | Context budgets | Son prompt: opportunities section (characters) |
| power_effect_cap | guc_etki_tavan | 2 | 1 | 100 | Son summoning and birth | Maximum sons in the pantheon carrying the same power effect (excess choices revert to the least-used effect) |
| default_passion | tutku_varsayilan | 50 | 0 | 100 | Son summoning and birth | A new son's passion not written by the model |

### TIME

Old namespace `ZAMAN` · 1 rows · defined in `src/rules.js` · also read by `src/agents.js`, `src/db.js`, `src/gok.js`, `src/kitap.js`, `src/kronik-onar.js`, `src/sim.js`, `src/world.js`. Years per epoch.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| years_per_epoch | cag_yil | 50 | 1 | 100,000 | Epoch flow | Length of one epoch (years) |

### TRAVEL

Old namespace `SEYAHAT` · 62 rows · defined in `src/seyahat.js` · also read by `src/ekonomi.js`, `src/epoch.js`, `src/tools.js`. Inter-world travel, expeditions, colonies, routes.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| list_expeditions | liste_sefer | 40 | 1 | 100,000 | Cosmos and travel | Number of recent expeditions shown on the cosmos page |
| hidden_knower_chance | gizli_bilen_sans | 35 | 0 | 100 | Cosmos and travel | A hidden route is revealed at an end that knows the required knowledge (%) |
| hidden_base_chance | gizli_taban_sans | 12 | 0 | 100 | Cosmos and travel | A hidden route is revealed on its own (%) |
| hidden_sensing_mortal_bonus_pct | gizli_sezen_ek | 10 | 0 | 100 | Cosmos and travel | Sensing contribution of a wise mortal at the route's end (%) |
| hidden_son_bonus_pct | gizli_ogul_ek | 8 | 0 | 100 | Cosmos and travel | Sensing contribution of a son at the route's end (%) |
| sensing_min_intellect | sezen_akil | 60 | 0 | 100 | Cosmos and travel | Intellect of a mortal able to sense a hidden route |
| expedition_min_population | sefer_nufus | 1200 | 0 | 1,000,000 | Cosmos and travel | Minimum population of a community sending a spontaneous expedition |
| expedition_base_pct | sefer_taban | 6 | 0 | 100 | Cosmos and travel | Spontaneous expedition (% per epoch) |
| expedition_barren_pct | sefer_kirac | 15 | 0 | 100 | Cosmos and travel | Expedition pressure of barren land (%) |
| expedition_barren_threshold | sefer_kirac_esik | 30 | 0 | 100 | Cosmos and travel | Fertility counted as barren |
| expedition_crowd_pct | sefer_kalabalik | 10 | 0 | 100 | Cosmos and travel | Expedition pressure of crowding (%) |
| expedition_crowd_threshold | sefer_kalabalik_esik | 20,000 | 0 | 10,000,000 | Cosmos and travel | Population counted as crowded |
| expedition_poverty_pct | sefer_yoksul | 8 | 0 | 100 | Cosmos and travel | Expedition pressure of poverty (%) |
| expedition_poverty_threshold | sefer_yoksul_esik | 25 | 0 | 100 | Cosmos and travel | Prosperity counted as poor |
| colony_share_pct | koloni_pay | 10 | 0 | 100 | Cosmos and travel | Population share of the colony party (%) |
| lost_chance | kayip_sans | 50 | 0 | 100 | Cosmos and travel | A getting-lost event on the road swallows the expedition (%) |
| colony_invasion_chance | koloni_istila_sans | 35 | 0 | 100 | Cosmos and travel | The colony is seen as invaders by the natives (%) |
| contact_trade_chance | temas_ticaret_sans | 50 | 0 | 100 | Cosmos and travel | First contact turns into trade (%) |
| interworld_alliance_chance | dunyalar_arasi_ittifak | 25 | 0 | 100 | Cosmos and travel | Inter-world alliance at first contact (%) |
| route_knowledge_chance | yol_bilgisi_sans | 12 | 0 | 100 | Cosmos and travel | A community at the route's end learns the route knowledge (%) |
| colony_intent_chance | koloni_niyet_sans | 50 | 0 | 100 | Cosmos and travel | An expedition to an inhabited world becomes a colony (otherwise exploration or trade) (%) |
| exploration_intent_chance | kesif_niyet_sans | 35 | 0 | 100 | Cosmos and travel | A non-colony spontaneous expedition becomes an exploration expedition (otherwise trade) (%) |
| exploration_land_chance | kesif_toprak_sans | 80 | 0 | 100 | Cosmos and travel | An exploration expedition finds a new land (region or place) on the world it reaches (%) |
| alignment_period | hizalanma_donemi | 5 | 1 | 100 | Cosmos and travel | Planetary alignment (slingshot orbit open) once every this many epochs |
| fold_min_abundance | katlama_bolluk | 12 | 0 | 100 | Cosmos and travel | Minimum abundance of a cosmic resource sufficient for space folding |
| route_danger_die | rota_tehlike_zar | 20 | 1 | 100 | Cosmos and travel | Danger die of a new route (1…n) |
| route_danger_shift | rota_tehlike_kayma | 10 | 0 | 100 | Cosmos and travel | Subtracted from the new route's danger die |
| route_danger_min | rota_tehlike_taban | 5 | 0 | 100 | Cosmos and travel | Lowest danger of a route |
| route_danger_max | rota_tehlike_tavan | 95 | 0 | 100 | Cosmos and travel | Highest danger of a route |
| default_vessel_speed | arac_hiz_varsayilan | 40 | 0 | 100 | Cosmos and travel | Speed of an expedition without a vessel or with no recorded speed |
| fast_vessel_speed | hizli_arac | 70 | 0 | 100 | Cosmos and travel | Vessel speed that shortens the journey by one epoch |
| sky_navigation_risk_pct | seyir_risk | 60 | 0 | 100 | Cosmos and travel | Route risk multiplier for those knowing sky navigation (%) |
| void_life_risk_pct | bosluk_risk | 80 | 0 | 100 | Cosmos and travel | Route risk multiplier for those knowing life in the void (%) |
| armor_risk_divisor | zirh_bolen | 250 | 1 | 10,000 | Cosmos and travel | Vessel armor reduces risk: armor / this number |
| ghost_ship_legend_power | hayalet_seviye | 4 | 1 | 12 | Cosmos and travel | Power level of the ghost-ship legend |
| ghost_ship_legend_spread | hayalet_yayginlik | 50 | 0 | 100 | Cosmos and travel | Spread of the ghost-ship legend |
| road_loss_base_pct | yol_kayip_taban | 10 | 0 | 100 | Cosmos and travel | Base share of travellers lost in a road event (%) |
| road_loss_random_pct | yol_kayip_zar | 25 | 0 | 100 | Cosmos and travel | Random share added to travellers lost in a road event (max %) |
| default_vessel_armor | arac_zirh_varsayilan | 30 | 0 | 100 | Cosmos and travel | Default armor of a vessel with no recorded armor |
| vessel_armor_loss | arac_zirh_kayip | 10 | 0 | 100 | Cosmos and travel | Vessel armor loss in an attack or storm |
| colony_prosperity | koloni_refah | 30 | 0 | 100 | Cosmos and travel | Prosperity of a new colony |
| colony_defense | koloni_savunma | 25 | 0 | 100 | Cosmos and travel | Defense of a new colony |
| conquest_outpost_defense | fetih_savunma | 45 | 0 | 100 | Cosmos and travel | Defense of a new conquest outpost |
| contact_cap | temas_tavan | 3 | 0 | 100 | Cosmos and travel | Maximum native communities contacted on arrival |
| invasion_relation_loss | istila_iliski | 30 | 0 | 100 | Cosmos and travel | Relation loss with the natives in an invasion |
| contact_trade_relation | temas_ticaret_iliski | 15 | 0 | 100 | Cosmos and travel | Relation gain of a first contact that turns into trade |
| alliance_relation | ittifak_iliski | 15 | 0 | 100 | Cosmos and travel | Relation gain of an inter-world alliance |
| uneasy_relation_loss | tedirgin_iliski | 5 | 0 | 100 | Cosmos and travel | Relation loss of an uneasy first contact |
| exploration_charisma | kesif_karizma | 8 | 0 | 100 | Cosmos and travel | Charisma gain from an exploration or pilgrimage expedition |
| trade_prosperity | ticaret_refah | 8 | 0 | 100 | Cosmos and travel | Prosperity gain from a trade expedition |
| route_knowledge_cap | yol_bilgisi_tavan | 2 | 0 | 100 | Cosmos and travel | Maximum communities learning route knowledge per epoch |
| route_knowledge_power | yol_bilgisi_seviye | 4 | 1 | 12 | Cosmos and travel | Power level of knowledge born on the road |
| route_knowledge_spread | yol_bilgisi_yayginlik | 5 | 0 | 100 | Cosmos and travel | Initial spread of knowledge born on the road |
| reveal_route_cost | aciga_bedel | 20 | 0 | 500 | Cosmic actions | Cost for the god to reveal a hidden route (essence) |
| expedition_cap | sefer_cag_tavan | 1 | 0 | 100 | Cosmos and travel | Maximum expeditions communities send on their own (per epoch) |
| expedition_visit_weight_pct | sefer_ziyaret_agirlik | 50 | 0 | 10,000 | Cosmos and travel | Expedition route choice: each previous expedition to the destination divides its selection weight by this percentage |
| expedition_empty_world_weight_pct | sefer_bos_agirlik | 300 | 0 | 10,000 | Cosmos and travel | Expedition route choice: weight multiplier of a route to a world with no people at all (%) |
| colony_min_power | koloni_guc_taban | 2 | 1 | 12 | Cosmos and travel | Minimum power level of a new colony |
| colony_power_gap | koloni_guc_eksi | 1 | 0 | 11 | Cosmos and travel | A new colony's power level is this much lower than the sender's |
| colony_default_piety | koloni_inanc_varsayilan | 50 | 0 | 100 | Cosmos and travel | Piety of a new colony if the party's piety is unrecorded |
| default_fertility | bereket_varsayilan | 50 | 0 | 100 | Cosmos and travel | Fertility assumed for a region with no recorded fertility (arrival land and barrenness) |
| default_prosperity | refah_varsayilan | 50 | 0 | 100 | Cosmos and travel | Prosperity assumed for a community with no recorded prosperity (poverty pressure) |

### TRAVEL_METHODS

Old namespace `SEYAHAT_YONTEMLERI` · 18 rows · defined in `src/rules.js` · also read by `src/denge.js`, `src/ekonomi.js`, `src/olumluler.js`, `src/oyuncu.js`, `src/seyahat.js`, `src/tools.js`, `src/ufuk.js`. Duration and danger per travel method — static object in rules.js.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| ancient_gate_duration | kapi.sure | 1 | 1 | 20 | Cosmos and travel | Ancient gate: journey duration (epochs) |
| ancient_gate_danger | kapi.tehlike | 25 | 0 | 100 | Cosmos and travel | Ancient gate: danger |
| space_fold_duration | katlama.sure | 1 | 1 | 20 | Cosmos and travel | Space folding: journey duration (epochs) |
| space_fold_danger | katlama.tehlike | 30 | 0 | 100 | Cosmos and travel | Space folding: danger |
| light_sail_duration | yelken.sure | 3 | 1 | 20 | Cosmos and travel | Light sail: journey duration (epochs) |
| light_sail_danger | yelken.tehlike | 20 | 0 | 100 | Cosmos and travel | Light sail: danger |
| cosmic_mount_duration | binek.sure | 2 | 1 | 20 | Cosmos and travel | Cosmic mount: journey duration (epochs) |
| cosmic_mount_danger | binek.tehlike | 35 | 0 | 100 | Cosmos and travel | Cosmic mount: danger |
| dream_journey_duration | ruya.sure | 1 | 1 | 20 | Cosmos and travel | Dream journey: journey duration (epochs) |
| dream_journey_danger | ruya.tehlike | 45 | 0 | 100 | Cosmos and travel | Dream journey: danger |
| river_of_dead_duration | olu_nehri.sure | 1 | 1 | 20 | Cosmos and travel | River of the dead: journey duration (epochs) |
| river_of_dead_danger | olu_nehri.tehlike | 40 | 0 | 100 | Cosmos and travel | River of the dead: danger |
| divine_bridge_duration | kopru.sure | 1 | 1 | 20 | Cosmos and travel | Divine bridge: journey duration (epochs) |
| divine_bridge_danger | kopru.tehlike | 10 | 0 | 100 | Cosmos and travel | Divine bridge: danger |
| slingshot_orbit_duration | sapan.sure | 2 | 1 | 20 | Cosmos and travel | Slingshot orbit: journey duration (epochs) |
| slingshot_orbit_danger | sapan.tehlike | 25 | 0 | 100 | Cosmos and travel | Slingshot orbit: danger |
| swallowed_duration | yutulma.sure | 2 | 1 | 20 | Cosmos and travel | Being swallowed: journey duration (epochs) |
| swallowed_danger | yutulma.tehlike | 60 | 0 | 100 | Cosmos and travel | Being swallowed: danger |

### UI

Old namespace `ARAYUZ` · 5 rows · defined in `src/degisim.js`, `src/harita.js`. UI-facing limits (graph view, map population trend, incremental change feed).

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| graph_focus_node_cap | ag_odak_tavan | 10,000 | 10 | 100,000 | Interface | Graph: maximum nodes shown around the focus (if exceeded, the step count is reduced) |
| graph_auto_focus_max_links | ag_oto_odak_bag | 50 | 3 | 100,000 | Interface | Graph: maximum links of an automatically chosen focus node (so hub nodes don't become the focus and turn the view into a hairball) |
| map_population_trend_min_pct | nufus_yon | 5 | 0 | 100 | Interface | Minimum change for population to count as growing or shrinking on the map (%) |
| delta_max_changes | degisim_sinir | 1500 | 50 | 100,000 | Interface | Maximum changes in one incremental-update response (more triggers a full refresh) |
| change_log_max_rows | degisim_tut | 20,000 | 100 | 10,000,000 | Interface | Maximum rows kept in the change log (pruned at epoch end) |

### WORLD_BIRTH

Old namespace `DUNYA_DOGUS` · 62 rows · defined in `src/kozmos.js`. Generation of a newly born world (regions, sky, unique resource, natives).

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| regions_min | bolge_en_az | 2 | 1 | 50 | Cosmos and travel | Minimum regions in a new world |
| regions_max | bolge_en_cok | 4 | 1 | 50 | Cosmos and travel | Maximum regions in a new world |
| words_min | kelime_en_az | 8 | 0 | 200 | Cosmos and travel | Minimum words in the new world's language |
| words_max | kelime_en_cok | 14 | 1 | 200 | Cosmos and travel | Maximum words in the new world's language |
| resource_mechanics_max | mekanik_en_cok | 2 | 0 | 10 | Cosmos and travel | Maximum rules (mechanics) of the native unique resource |
| natives_max | yerli_en_cok | 2 | 0 | 20 | Cosmos and travel | Maximum natives (species or people) in a new world |
| banned_names | yasak_ad | 60 | 0 | 2000 | Cosmos and travel | Number of region, people, language, place and sky names not to be repeated in the new-world prompt (newest first) |
| banned_cosmic_names | yasak_kozmik_ad | 200 | 0 | 2000 | Cosmos and travel | Number of world, star and foreign-god names not to be repeated in the new-world prompt (newest first) |
| phoneme_set_min | ses_kumesi | 8 | 1 | 100 | Cosmos and travel | Minimum distinct letters for a dialect to count as a sound set |
| star_brightness_base | yildiz_parlaklik | 40 | 0 | 100 | Cosmos and travel | New star brightness: base |
| star_brightness_die | yildiz_parlaklik_zar | 55 | 1 | 100 | Cosmos and travel | New star brightness: die |
| danger_base | tehlike | 30 | 0 | 100 | Cosmos and travel | New world danger: base |
| danger_die | tehlike_zar | 40 | 1 | 100 | Cosmos and travel | New world danger: die |
| region_power | bolge_guc | 6 | 1 | 12 | Cosmos and travel | Power level of a birth region |
| region_breadth_base | bolge_genislik | 50 | 0 | 100 | Cosmos and travel | Birth region breadth: base |
| region_breadth_die | bolge_genislik_zar | 30 | 1 | 100 | Cosmos and travel | Birth region breadth: die |
| region_danger | bolge_tehlike | 30 | 0 | 100 | Cosmos and travel | Birth region danger (if the model gives none) |
| region_fertility | bolge_bereket | 50 | 0 | 100 | Cosmos and travel | Birth region fertility (if the model gives none) |
| region_magic | bolge_buyu | 30 | 0 | 100 | Cosmos and travel | Birth region magic (if the model gives none) |
| sky_power | gok_guc | 5 | 1 | 12 | Cosmos and travel | Power level of the birth sky |
| sky_brightness_base | gok_parlaklik | 40 | 0 | 100 | Cosmos and travel | Birth sky brightness: base |
| sky_brightness_die | gok_parlaklik_zar | 50 | 1 | 100 | Cosmos and travel | Birth sky brightness: die |
| sky_influence_base | gok_etki | 30 | 0 | 100 | Cosmos and travel | Birth sky influence: base |
| sky_influence_die | gok_etki_zar | 50 | 1 | 100 | Cosmos and travel | Birth sky influence: die |
| resource_power | kaynak_guc | 6 | 1 | 12 | Cosmos and travel | Power level of the native unique resource |
| resource_abundance_base | kaynak_bolluk | 50 | 0 | 100 | Cosmos and travel | Unique resource abundance: base |
| resource_abundance_die | kaynak_bolluk_zar | 40 | 1 | 100 | Cosmos and travel | Unique resource abundance: die |
| resource_value_base | kaynak_deger | 60 | 0 | 100 | Cosmos and travel | Unique resource value: base |
| resource_value_die | kaynak_deger_zar | 40 | 1 | 100 | Cosmos and travel | Unique resource value: die |
| resource_might_base | kaynak_kudret | 40 | 0 | 100 | Cosmos and travel | Unique resource might: base |
| resource_might_die | kaynak_kudret_zar | 50 | 1 | 100 | Cosmos and travel | Unique resource might: die |
| cosmic_deposit_power | kozmik_guc | 8 | 1 | 12 | Cosmos and travel | Power level of a cosmic resource deposit |
| cosmic_deposit_abundance_base | kozmik_bolluk | 70 | 0 | 100 | Cosmos and travel | Cosmic deposit abundance: base |
| cosmic_deposit_abundance_die | kozmik_bolluk_zar | 30 | 1 | 100 | Cosmos and travel | Cosmic deposit abundance: die |
| cosmic_deposit_value | kozmik_deger | 95 | 0 | 100 | Cosmos and travel | Cosmic deposit value |
| cosmic_deposit_might_base | kozmik_kudret | 80 | 0 | 100 | Cosmos and travel | Cosmic deposit might: base |
| cosmic_deposit_might_die | kozmik_kudret_zar | 20 | 1 | 100 | Cosmos and travel | Cosmic deposit might: die |
| language_power | dil_guc | 4 | 1 | 12 | Cosmos and travel | Power level of the native language |
| language_spread | dil_yayginlik | 40 | 0 | 100 | Cosmos and travel | Spread of the native language |
| language_complexity_base | dil_karmasiklik | 40 | 0 | 100 | Cosmos and travel | Native language complexity: base |
| language_complexity_die | dil_karmasiklik_zar | 30 | 1 | 100 | Cosmos and travel | Native language complexity: die |
| language_sacredness_base | dil_kutsallik | 20 | 0 | 100 | Cosmos and travel | Native language sacredness: base |
| language_sacredness_die | dil_kutsallik_zar | 40 | 1 | 100 | Cosmos and travel | Native language sacredness: die |
| native_power | yerli_guc | 4 | 1 | 12 | Cosmos and travel | Power level of the natives |
| people_population_base | halk_nufus | 2000 | 1 | 10,000,000 | Cosmos and travel | Native people population: base |
| people_population_die | halk_nufus_zar | 8000 | 1 | 10,000,000 | Cosmos and travel | Native people population: die |
| people_martiality_base | halk_savascilik | 30 | 0 | 100 | Cosmos and travel | Native people martiality: base |
| people_martiality_die | halk_savascilik_zar | 50 | 1 | 100 | Cosmos and travel | Native people martiality: die |
| people_magic_die | halk_buyu_zar | 70 | 1 | 100 | Cosmos and travel | Native people magic: die |
| people_craft_base | halk_zanaat | 20 | 0 | 100 | Cosmos and travel | Native people craft: base |
| people_craft_die | halk_zanaat_zar | 50 | 1 | 100 | Cosmos and travel | Native people craft: die |
| people_piety_base | halk_inanc | 20 | 0 | 100 | Cosmos and travel | Native people piety: base |
| people_piety_die | halk_inanc_zar | 40 | 1 | 100 | Cosmos and travel | Native people piety: die |
| species_hp_base | tur_can | 100 | 1 | 100,000 | Cosmos and travel | Native species HP: base |
| species_hp_die | tur_can_zar | 400 | 1 | 100,000 | Cosmos and travel | Native species HP: die |
| species_strength_base | tur_guc | 30 | 0 | 100 | Cosmos and travel | Native species strength: base |
| species_strength_die | tur_guc_zar | 60 | 1 | 100 | Cosmos and travel | Native species strength: die |
| species_agility_base | tur_ceviklik | 20 | 0 | 100 | Cosmos and travel | Native species agility: base |
| species_agility_die | tur_ceviklik_zar | 60 | 1 | 100 | Cosmos and travel | Native species agility: die |
| species_intelligence_die | tur_zeka_zar | 80 | 1 | 100 | Cosmos and travel | Native species intelligence: die |
| species_danger_base | tur_tehlike | 20 | 0 | 100 | Cosmos and travel | Native species danger: base |
| species_danger_die | tur_tehlike_zar | 70 | 1 | 100 | Cosmos and travel | Native species danger: die |

### WORLD_EFFECTS

Old namespace `DUNYA_ETKI` · 166 rows · defined in `src/sim.js`. World-engine side effects: raids, trade, curses, resources, magic storms, schisms, heroes, plagues, famine, uprisings, laws, coinage, births, dialects, spirits.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| afterdeath_cap | olum_sonrasi_tavan | 2 | 0 | 50 | The Beyond | Maximum mourning traditions or spirits born from deaths per epoch (each) |
| language_faith_adopt_cap | dil_inanc_tavan | 4 | 0 | 100 | Religion and language | Maximum communities acquiring a language or faith per epoch |
| god_grudge_cap | kin_tavan | 1 | 0 | 20 | War and diplomacy | Maximum new hostilities born from god grudges per epoch |
| god_grudge_distance | kin_mesafe | 3 | 0 | 20 | War and diplomacy | Maximum map distance of communities a grudge can seep between (steps) |
| god_grudge_relation | kin_iliski | 40 | 0 | 100 | War and diplomacy | For a grudge, the patron gods' relation must be at most minus this |
| raid_distance | baskin_mesafe | 2 | 0 | 20 | Creatures | Maximum distance a monster can raid (steps) |
| raid_prosperity_loss | baskin_refah | 6 | 0 | 100 | Creatures | Prosperity loss of a raided settlement |
| raid_defense_gain | baskin_savunma | 2 | 0 | 100 | Creatures | Wall (defense) increase of a settlement after a raid |
| unknown_stat | bilinmeyen_stat | 30 | 0 | 100 | Population and growth | Default of an unrecorded defense, influence or value (and prosperity in uprisings) |
| unknown_prosperity | bilinmeyen_refah | 50 | 0 | 100 | Population and growth | Default of unrecorded prosperity (raid, famine, haunting, law, growth) |
| unknown_fertility | bilinmeyen_bereket | 50 | 0 | 100 | Population and growth | Default of unrecorded fertility (drought, famine migration, growth) |
| unknown_breadth | bilinmeyen_genislik | 50 | 0 | 100 | Population and growth | Breadth in carrying capacity of a region with no recorded breadth |
| unknown_justice | bilinmeyen_adalet | 50 | 0 | 100 | War and diplomacy | Justice of a law with no recorded justice |
| unknown_piety | bilinmeyen_inanc | 50 | 0 | 100 | Religion and language | Piety in the godlessness calculation of a community with no recorded piety |
| raid_default_danger | baskin_tehlike | 50 | 0 | 100 | Creatures | Danger in a raid of a monster with no recorded danger |
| raid_default_population | baskin_nufus | 100 | 1 | 1,000,000 | Creatures | Population in a raid of a settlement with no recorded population |
| hunt_distance | av_mesafe | 3 | 0 | 20 | Heroes and mortals | Maximum distance of a monster a hero can hunt (steps) |
| trade_prosperity | ticaret_refah | 3 | 0 | 100 | Economy | Prosperity a trade route gives each epoch |
| trade_wealth | ticaret_servet | 3 | 0 | 100 | Economy | Wealth a trade route gives each epoch |
| trade_knowledge_mult | ticaret_bilgi_carpan | 2 | 1 | 20 | Economy | Trade prosperity multiplier for those knowing trade (times) |
| trade_prosperity_cap | ticaret_refah_tavan | 6 | 0 | 100 | Economy | Maximum prosperity trade routes give one community in one epoch (all routes together) |
| trade_wealth_cap | ticaret_servet_tavan | 6 | 0 | 100 | Economy | Maximum wealth trade routes give one community in one epoch (all routes together) |
| prosperity_target | refah_hedef | 50 | 0 | 100 | Economy | Equilibrium value prosperity is drawn to in the long run; trade and resource gains have diminishing returns above it |
| prosperity_reversion_pct | refah_donus | 10 | 0 | 100 | Economy | Gap toward the equilibrium value that prosperity closes each epoch (%) |
| curse_population_kept_pct | lanet_nufus_kalan | 95 | 0 | 100 | Heroes and mortals | Share of population and followers a cursed community keeps each epoch (%) |
| curse_stat_loss | lanet_stat | 3 | 0 | 100 | Heroes and mortals | Prosperity, fertility, strength and wealth a cursed entity loses each epoch |
| resource_min_abundance | kaynak_bolluk_esik | 15 | 0 | 100 | Economy | Minimum abundance of a resource that gives its owners income |
| resource_income | kaynak_kazanc | 1 | 0 | 100 | Economy | Base prosperity, wealth and craft a resource owner gains each epoch |
| resource_value_divisor | kaynak_deger_bolen | 40 | 1 | 1000 | Economy | Value contribution to resource income: value / this number |
| resource_consumption | kaynak_tuketim | 2 | 0 | 100 | Economy | Abundance each owner consumes from the resource per epoch |
| resource_regen | kaynak_yenilenme | 4 | 0 | 100 | Economy | Per-epoch abundance regeneration of resources |
| barter_cap | ticaret_tavan | 2 | 0 | 50 | Economy | Maximum resource barters established spontaneously per epoch |
| item_curse_threshold | esya_lanet_esik | 50 | 0 | 100 | Heroes and mortals | Minimum curse of an item that harms its owner |
| item_curse_hp_divisor | lanet_can_bolen | 5 | 1 | 1000 | Heroes and mortals | HP damage of a cursed item to its owner: curse / this number |
| item_curse_stat_divisor | lanet_stat_bolen | 20 | 1 | 1000 | Heroes and mortals | Prosperity and defense damage of a cursed item: curse / this number |
| magic_storm_min_magic | buyu_firtina_esik | 70 | 0 | 100 | Cosmic horror | Minimum magic of a region where a magic storm can break out |
| magic_storm_might_gain | firtina_kudret | 5 | 0 | 100 | Cosmic horror | Might increase of resources and items in a magic storm |
| magic_storm_curse_gain | firtina_lanet | 10 | 0 | 100 | Cosmic horror | Curse increase of an item cursed in a magic storm |
| magic_storm_power | firtina_guc | 5 | 1 | 12 | Cosmic horror | Power level of a magic storm event |
| magic_storm_severity_base | firtina_siddet_taban | 40 | 0 | 100 | Cosmic horror | Base of magic storm severity |
| magic_storm_severity_die | firtina_siddet_zar | 40 | 1 | 100 | Cosmic horror | Die added to magic storm severity (1–X) |
| schism_cap | bolunme_tavan | 1 | 0 | 20 | Religion and language | Maximum cult schisms per epoch |
| schism_top_pct | bolunme_yuzde | 50 | 0 | 100 | Religion and language | Cults that can split: the world's top X% most populous |
| schism_always_followers | bolunme_ust | 3000 | 0 | 10,000,000 | Religion and language | A cult with this many followers can always split |
| schism_min_age | bolunme_yas | 2 | 0 | 100 | Religion and language | Minimum age of a cult that can split (epochs) |
| schism_large_min_age | bolunme_buyuk_yas | 4 | 0 | 100 | Religion and language | Minimum age for a non-zealous cult to split (epochs) |
| schism_zealotry_gain | bolunme_bagnazlik_artis | 10 | 0 | 100 | Religion and language | Zealotry gain of the breakaway sect |
| schism_influence_loss | bolunme_etki_dusus | 10 | 0 | 100 | Religion and language | Influence deficit of the breakaway sect |
| schism_patron_relation | bolunme_iliski | 10 | 0 | 100 | Religion and language | Relation loss between old and new patron in a schism |
| split_min_power | ayrilan_guc_taban | 2 | 1 | 12 | Population and growth | Minimum power level of a new entity that splits, migrates or converts |
| creature_migration_min_danger | yaratik_goc_tehlike | 45 | 0 | 100 | Creatures | Minimum danger of a species able to migrate to a neighbouring region |
| creature_migration_cap | goc_tavan | 1 | 0 | 20 | Creatures | Maximum creature migrations per epoch |
| hero_always_population | kahraman_ust | 8000 | 0 | 100,000,000 | Heroes and mortals | A people this populous can always produce a hero (people) |
| hero_cap | kahraman_tavan | 1 | 0 | 20 | Heroes and mortals | Maximum spontaneously born heroes per epoch |
| hero_power | kahraman_guc_seviye | 4 | 1 | 12 | Heroes and mortals | Power level of a spontaneously born hero |
| hero_hp | kahraman_can | 120 | 1 | 1000 | Heroes and mortals | HP of a spontaneously born hero |
| hero_strength_base | kahraman_guc_taban | 45 | 0 | 100 | Heroes and mortals | Hero strength: base |
| hero_strength_die | kahraman_guc_zar | 40 | 1 | 100 | Heroes and mortals | Hero strength: added die (1–X) |
| hero_agility_base | kahraman_cev_taban | 40 | 0 | 100 | Heroes and mortals | Hero agility: base |
| hero_agility_die | kahraman_cev_zar | 40 | 1 | 100 | Heroes and mortals | Hero agility: added die (1–X) |
| hero_intellect_base | kahraman_akil_taban | 30 | 0 | 100 | Heroes and mortals | Hero intellect: base |
| hero_intellect_die | kahraman_akil_zar | 50 | 1 | 100 | Heroes and mortals | Hero intellect: added die (1–X) |
| hero_charisma_base | kahraman_kar_taban | 30 | 0 | 100 | Heroes and mortals | Hero charisma: base |
| hero_charisma_die | kahraman_kar_zar | 50 | 1 | 100 | Heroes and mortals | Hero charisma: added die (1–X) |
| hero_age_base | kahraman_yas_taban | 16 | 0 | 200 | Heroes and mortals | Age at which the hero emerges: base (years) |
| hero_age_die | kahraman_yas_zar | 6 | 1 | 200 | Heroes and mortals | Die added to the hero's age (1–X years) |
| hero_lifespan_base | kahraman_omur_taban | 75 | 1 | 50,000 | Heroes and mortals | Hero lifespan: base (years) |
| hero_lifespan_die | kahraman_omur_zar | 40 | 1 | 50,000 | Heroes and mortals | Die added to the hero's lifespan (1–X years) |
| knowledge_spread_cap | yayilim_tavan | 4 | 0 | 100 | Religion and language | Maximum knowledge spreading along links per epoch |
| writing_spread_mult | yazi_carpan | 2 | 1 | 20 | Religion and language | Knowledge-spread multiplier from those knowing writing (times) |
| disaster_law_mult | afet_yasasi_carpan | 2 | 1 | 20 | Population and growth | Natural-event frequency multiplier under the disaster law (times) |
| drought_fertility_threshold | kurak_bereket | 35 | 0 | 100 | Population and growth | Drought can occur in a region with fertility below this |
| plague_crowd_max_pct | veba_ek_tavan | 5 | 0 | 100 | Population and growth | Maximum contribution of crowding to region plague chance (%) |
| plague_crowd_divisor | veba_nufus_bolen | 1,000,000 | 1000 | 1,000,000,000 | Population and growth | Crowding contribution to region plague: population / this number |
| disaster_severity_base | afet_siddet_taban | 30 | 0 | 100 | Population and growth | Base of natural-event severity |
| disaster_severity_die | afet_siddet_zar | 50 | 1 | 100 | Population and growth | Die added to natural-event severity (1–X) |
| disaster_scale_divisor | afet_siddet_olcek | 70 | 1 | 1000 | Population and growth | Effect strength of a natural event: severity / this number |
| city_plague_top_pct | kent_veba_yuzde | 80 | 0 | 100 | Population and growth | Cities that can see plague: the world's top X% most populous |
| city_plague_always_population | kent_veba_ust | 40,000 | 0 | 100,000,000 | Population and growth | A city this populous can always see plague (people) |
| city_plague_min_population | kent_veba_en_az | 1500 | 0 | 10,000,000 | Population and growth | Minimum population of a city that can see plague (even if hungry or at war) |
| default_food | erzak_varsayilan | 60 | 0 | 100 | Population and growth | Default food of a community with no stockpile record |
| hungry_food | ac_erzak | 15 | 0 | 100 | Population and growth | A community with food below this counts as hungry |
| plague_spread_epochs | veba_yayilim_cag | 1 | 0 | 20 | Population and growth | Period over which plague spreads along routes (plagues of the last X epochs) |
| plague_spread_severity_pct | veba_yayilim_siddet | 60 | 0 | 100 | Population and growth | Severity of plague transmitted along routes (% of the original plague) |
| famine_migration_min_population | kitlik_nufus | 1500 | 0 | 10,000,000 | Population and growth | Minimum population of a community able to make a famine migration |
| famine_migration_cap | kitlik_tavan | 1 | 0 | 20 | Population and growth | Maximum famine migrations per epoch |
| famine_prosperity | kitlik_refah | 20 | 0 | 100 | Population and growth | A community below this prosperity counts as in famine |
| famine_fertility_margin | kitlik_bereket_fark | 5 | 0 | 100 | Population and growth | The destination region must be at least this much more fertile than the source |
| migrant_prosperity | gocmen_refah | 30 | 0 | 100 | Population and growth | Starting prosperity of a migrant settlement |
| migrant_defense | gocmen_savunma | 20 | 0 | 100 | Population and growth | Starting defense of a migrant settlement |
| migrant_piety | gocmen_inanc | 55 | 0 | 100 | Population and growth | Starting piety of a migrant settlement |
| revolt_top_pct | isyan_yuzde | 50 | 0 | 100 | War and diplomacy | Cities that can revolt: the world's top X% most populous |
| revolt_always_population | isyan_ust | 5000 | 0 | 100,000,000 | War and diplomacy | A poor city this populous can always revolt (people) |
| just_law_threshold | adil_kanun | 60 | 0 | 100 | War and diplomacy | Minimum justice of a law counted as just |
| revolt_cap | isyan_tavan | 1 | 0 | 20 | War and diplomacy | Maximum uprisings per epoch |
| rebel_power | isyanci_guc_seviye | 3 | 1 | 12 | War and diplomacy | Power level of the rebel faction |
| rebel_strength_base | isyanci_guc_taban | 30 | 0 | 100 | War and diplomacy | Rebels' strength: base |
| rebel_strength_die | isyanci_guc_zar | 30 | 1 | 100 | War and diplomacy | Die added to rebels' strength (1–X) |
| rebel_wealth_base | isyanci_servet_taban | 10 | 0 | 100 | War and diplomacy | Rebels' wealth: base |
| rebel_wealth_die | isyanci_servet_zar | 15 | 1 | 100 | War and diplomacy | Die added to rebels' wealth (1–X) |
| rebel_sway_base | isyanci_nufuz_taban | 25 | 0 | 100 | War and diplomacy | Rebels' sway: base |
| rebel_sway_die | isyanci_nufuz_zar | 30 | 1 | 100 | War and diplomacy | Die added to rebels' sway (1–X) |
| revolt_defense_loss | isyan_savunma | 10 | 0 | 100 | War and diplomacy | Defense loss of a revolting city |
| revolt_prosperity_loss | isyan_refah | 5 | 0 | 100 | War and diplomacy | Prosperity loss of a revolting city |
| haunt_prosperity_loss | musallat_refah | 6 | 0 | 100 | The Beyond | Prosperity loss of a settlement haunted by a spirit |
| haunt_unrest_drop | musallat_huzur | 5 | 0 | 100 | The Beyond | Decrease of the haunting spirit's unrest |
| law_just_avg_threshold | kanun_adil_esik | 50 | 0 | 100 | War and diplomacy | If the average justice of laws is above this, walls strengthen |
| law_just_defense_gain | kanun_savunma | 2 | 0 | 100 | War and diplomacy | Per-epoch defense gain of a settlement with just laws |
| law_unjust_avg_threshold | kanun_adaletsiz | 30 | 0 | 100 | War and diplomacy | If the average justice of laws is below this, prosperity drops |
| law_unjust_prosperity_loss | kanun_refah | 2 | 0 | 100 | War and diplomacy | Per-epoch prosperity loss of a settlement with unjust laws |
| coinage_min_wealth | sikke_esik | 50 | 0 | 100 | Economy | Minimum prosperity or wealth of a community able to mint coins |
| currency_power | sikke_guc | 3 | 1 | 12 | Economy | Power level of a currency |
| currency_might_base | sikke_kudret_taban | 10 | 0 | 100 | Economy | Currency might: base |
| currency_might_die | sikke_kudret_zar | 20 | 1 | 100 | Economy | Die added to currency might (1–X) |
| shared_currency_prosperity | ortak_para_refah | 2 | 0 | 100 | Economy | Per-epoch prosperity gain of trade partners using a shared currency |
| sorcerer_min_intellect | buyucu_akil | 60 | 0 | 100 | Heroes and mortals | Minimum intellect of a mortal who can be a sorcerer |
| sorcerer_protect_chance | buyucu_koruma_sans | 50 | 0 | 100 | Heroes and mortals | A sorcerer weaves a protection (otherwise bounty) spell over their homeland (%) |
| creature_revolt_min_intelligence | yaratik_isyan_zeka | 50 | 0 | 100 | Creatures | Minimum intelligence of a creature able to rebel against its creator |
| creature_revolt_min_danger | yaratik_isyan_tehlike | 55 | 0 | 100 | Creatures | Minimum danger of a creature able to rebel against its creator |
| creature_revolt_population_kept_pct | yaratik_isyan_kalan | 92 | 0 | 100 | Creatures | Population share remaining in the community attacked by a rebelling creature (%) |
| creature_revolt_son_existence_loss | yaratik_isyan_varlik | 4 | 0 | 100 | Creatures | Existence loss of the son whose creature rebelled |
| godlessness_piety | tanrisizlik_inanc | 35 | 0 | 100 | Religion and language | A community below this piety may become godless |
| speciation_min_epochs | evrim_cag | 2 | 0 | 100 | Creatures | Minimum time for a migrated species to split into a subspecies (epochs) |
| speciation_cap | evrim_tavan | 1 | 0 | 20 | Creatures | Maximum species evolutions per epoch |
| speciation_stat_deviation | evrim_sapma | 15 | 0 | 100 | Creatures | Deviation (±) of a subspecies' stats from its ancestor |
| birth_cap | dogum_tavan | 2 | 0 | 50 | Heroes and mortals | Maximum births from lovers and spouses per epoch |
| inheritance_default_stat | kalitim_stat | 40 | 0 | 100 | Heroes and mortals | Default of an unrecorded mortal stat (inheritance and spirits) |
| inheritance_deviation | kalitim_sapma | 10 | 0 | 100 | Heroes and mortals | Deviation (±) of children's and heirs' stats from the parent |
| child_hp | cocuk_can | 80 | 1 | 1000 | Heroes and mortals | HP of a newborn child |
| default_lifespan | omur_varsayilan | 70 | 1 | 50,000 | Heroes and mortals | Lifespan of a mortal with no recorded lifespan (years) |
| child_min_lifespan | cocuk_omur_en_az | 20 | 1 | 50,000 | Heroes and mortals | Shortest lifespan of a newborn child (years) |
| lifespan_cap | omur_tavan | 50,000 | 1 | 1,000,000 | Heroes and mortals | Longest lifespan of mortals (years) |
| love_min_age | ask_yas | 16 | 0 | 200 | Heroes and mortals | Minimum age of a mortal able to enter love or rivalry |
| dialect_min_settlement_age | lehce_cag | 4 | 0 | 100 | Religion and language | Minimum settlement age for a dialect split (epochs) |
| dialect_cap | lehce_tavan | 1 | 0 | 20 | Religion and language | Maximum dialect splits per epoch |
| dialect_power | lehce_guc | 2 | 1 | 12 | Religion and language | Power level of a new dialect |
| dialect_spread | lehce_yayginlik | 15 | 0 | 100 | Religion and language | Spread of a new dialect |
| dialect_complexity | lehce_karmasiklik | 40 | 0 | 100 | Religion and language | Complexity of a new dialect |
| dialect_sacredness | lehce_kutsallik | 10 | 0 | 100 | Religion and language | Sacredness of a new dialect |
| dialect_inherited_words | lehce_kelime | 5 | 0 | 1000 | Religion and language | Words passing from the parent language to the new dialect |
| magic_price_min_magic | buyu_bedeli_esik | 60 | 0 | 100 | Population and growth | Under the price-of-magic law, minimum magic of a people that pays the price |
| magic_price_population_kept_pct | buyu_bedeli_kalan | 95 | 0 | 100 | Population and growth | Under the price-of-magic law, population share a people keeps each epoch (%) |
| architecture_defense_gain | mimarlik_savunma | 5 | 0 | 100 | Civilization | Per-epoch wall gain of a settlement that knows architecture |
| notable_min_charisma | onemli_karizma | 70 | 0 | 100 | Heroes and mortals | Minimum charisma of a mortal counted as notable (lives longer) |
| rejuvenate_years_left | yasli_pay | 10 | 0 | 3000 | Heroes and mortals | A created mortal with only this many years left of their lifespan in the epoch of birth is rejuvenated (years) |
| rejuvenate_age_min_pct | genclesme_taban | 20 | 0 | 100 | Heroes and mortals | Age of a rejuvenated mortal: at least % of lifespan |
| rejuvenate_age_random_pct | genclesme_zar | 30 | 0 | 100 | Heroes and mortals | Random share of lifespan added to a rejuvenated mortal's age (max %) |
| short_life_aging_mult | kisa_omur_carpan | 2 | 1 | 20 | Heroes and mortals | Aging multiplier under the short-life law (times) |
| heir_hp | varis_can | 80 | 1 | 1000 | Heroes and mortals | HP of an heir |
| heir_age_base | varis_yas_taban | 16 | 0 | 200 | Heroes and mortals | Heir's age: base (years) |
| heir_age_die | varis_yas_zar | 12 | 1 | 200 | Heroes and mortals | Die added to the heir's age (1–X years) |
| heir_lifespan_deviation | varis_omur_sapma | 15 | 0 | 1000 | Heroes and mortals | Deviation (± years) of the heir's lifespan from the deceased's |
| heir_min_lifespan | varis_omur_en_az | 45 | 1 | 50,000 | Heroes and mortals | Shortest lifespan of an heir (years) |
| death_domain_essence | olum_alani_oz | 2 | 0 | 100 | The Beyond | Essence a death-domain god gains on each death |
| death_domain_existence | olum_alani_varlik | 1 | 0 | 100 | The Beyond | Existence gain of a death-domain god on each death |
| default_existence | varlik_varsayilan | 60 | 0 | 100 | Creator and essence | Existence value of a son with no recorded existence |
| famous_min_charisma | unlu_karizma | 60 | 0 | 100 | The Beyond | Minimum charisma of a deceased counted as famous |
| spirit_unrest_murdered | ruh_huzursuz_katil | 70 | 0 | 100 | The Beyond | Base unrest of the spirit of a murdered famous person |
| spirit_unrest_natural | ruh_huzursuz_dogal | 40 | 0 | 100 | The Beyond | Base unrest of the spirit of a famous person who died naturally |
| spirit_unrest_die | ruh_huzursuz_zar | 20 | 1 | 100 | The Beyond | Die added to the spirit's unrest (1–X) |
| spirit_restless_threshold | ruh_huzursuz_sinif | 50 | 0 | 100 | The Beyond | A spirit with unrest above this counts as restless (below: ancestor spirit) |
| spirit_strength_divisor | ruh_guc_bolen | 2 | 1 | 100 | The Beyond | Spirit's strength: deceased's strength / this number |
| spirit_strength_bonus | ruh_guc_ek | 20 | 0 | 100 | The Beyond | Added to the spirit's strength |
| mourning_power | yas_guc | 2 | 1 | 12 | Heroes and mortals | Power level of a mourning tradition |
| mourning_spread | yas_yayginlik | 50 | 0 | 100 | Heroes and mortals | Spread of a mourning tradition |
| mourning_rigidity | yas_katilik | 40 | 0 | 100 | Heroes and mortals | Rigidity of a mourning tradition |

### WORLD_ENGINE

Old namespace `DUNYA_MOTORU` · 81 rows · defined in `src/sim.js`. World-engine event probabilities and growth.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| chronicle_fold_threshold | katlama_esik | 3 | 2 | 100 | Chronicle | This many chronicle lines of the same template are folded into one line |
| raid_danger_divisor | baskin_bolen | 160 | 10 | 10,000 | Creatures | Monster raid chance: danger / this number |
| raid_loss_divisor | baskin_kayip_bolen | 400 | 10 | 10,000 | Creatures | Population lost in a raid: danger / this number |
| monster_top_pct | canavar_yuzde | 80 | 0 | 100 | Creatures | Species counted as monsters: the world's top X% most dangerous |
| monster_min_danger | canavar_alt | 40 | 0 | 100 | Creatures | Minimum danger to count as a monster |
| monster_always_danger | canavar_ust | 55 | 0 | 100 | Creatures | A species at this danger is always a monster |
| hunt_chance | av_sans | 30 | 0 | 100 | Heroes and mortals | A strong mortal hunts a monster in pursuit of renown (%) |
| hunt_chosen_chance | av_secilmis_sans | 50 | 0 | 100 | Heroes and mortals | A chosen mortal hunts a monster (%) |
| hunter_strength_agility | av_guc | 90 | 0 | 200 | Heroes and mortals | Strength + agility total of a mortal counted as a hunter |
| curse_lift_chance | lanet_kalkma | 12 | 0 | 100 | Heroes and mortals | A curse lifts on its own (%) |
| curse_hp_loss | lanet_can | 10 | 0 | 1000 | Heroes and mortals | HP lost each epoch by a cursed mortal (if it runs out the curse kills them; 0 off) |
| curse_magic_bonus_pct | lanet_buyu_ek | 15 | 0 | 100 | Heroes and mortals | Contribution of knowing magic to escaping a curse (%) |
| curse_medicine_bonus_pct | lanet_tip_ek | 10 | 0 | 100 | Heroes and mortals | Contribution of knowing medicine to escaping a curse (%) |
| schism_zealous_chance | bolunme_bagnaz_sans | 22 | 0 | 100 | Religion and language | A zealous cult splits (%) |
| schism_large_chance | bolunme_buyuk_sans | 10 | 0 | 100 | Religion and language | A large and old cult splits over doctrinal dispute (%) |
| schism_zealotry | bolunme_bagnazlik | 60 | 0 | 100 | Religion and language | Zealotry of a cult counted as zealous |
| schism_min_followers | bolunme_alt | 400 | 0 | 1,000,000 | Religion and language | Minimum followers of a cult that can split |
| schism_large_followers | bolunme_buyuk | 800 | 0 | 1,000,000 | Religion and language | Followers needed for a non-zealous cult to split |
| schism_split_pct | bolunme_pay | 30 | 0 | 100 | Religion and language | Share of followers leaving in a split (%) |
| hero_birth_chance | kahraman_sans | 12 | 0 | 100 | Heroes and mortals | A hero is born from a populous people (%) |
| hero_war_bonus_pct | kahraman_savas_ek | 15 | 0 | 100 | Heroes and mortals | Contribution of being at war to a people's hero birth (%) |
| hero_min_population | kahraman_alt | 1500 | 0 | 1,000,000 | Heroes and mortals | Minimum population of a community producing heroes |
| knowledge_spread_chance | bilgi_yayilim_sans | 18 | 0 | 100 | Religion and language | Knowledge spreads along trade and rule links (%) |
| disaster_cap | afet_tavan | 2 | 0 | 20 | Population and growth | Maximum natural events per epoch |
| earthquake_chance | deprem_sans | 8 | 0 | 100 | Population and growth | Earthquake in a mountainous region (%) |
| flood_chance | sel_sans | 6 | 0 | 100 | Population and growth | Flood on the coast (%) |
| storm_chance | firtina_sans | 6 | 0 | 100 | Population and growth | Storm on the coast (%) |
| drought_chance | kuraklik_sans | 10 | 0 | 100 | Population and growth | Drought in a barren region (%) |
| region_plague_population | bolge_veba_nufus | 3000 | 0 | 10,000,000 | Population and growth | Region population at which plague can be a natural event |
| region_plague_chance | bolge_veba_sans | 6 | 0 | 100 | Population and growth | Plague in a crowded region (%) |
| city_plague_min_population | kent_veba_alt | 3000 | 0 | 10,000,000 | Population and growth | Minimum crowding for city plague |
| city_plague_chance | kent_veba_sans | 10 | 0 | 100 | Population and growth | Plague in a crowded city (%) |
| hungry_plague_chance | ac_veba_sans | 12 | 0 | 100 | Population and growth | Plague in a hungry city (%) |
| war_plague_chance | savas_veba_sans | 8 | 0 | 100 | Population and growth | Plague in a city at war (%) |
| plague_spread_chance | veba_yayilim_sans | 35 | 0 | 100 | Population and growth | Plague jumps to a neighbour along links (%) |
| plague_spread_medicine_chance | veba_yayilim_tip_sans | 18 | 0 | 100 | Population and growth | Plague jumps to one who knows medicine (%) |
| revolt_chance | isyan_sans | 22 | 0 | 100 | War and diplomacy | Uprising in a poor city (%) |
| revolt_just_law_chance | isyan_adil_sans | 8 | 0 | 100 | War and diplomacy | Uprising in a city with a just law (%) |
| revolt_prosperity | isyan_refah | 30 | 0 | 100 | War and diplomacy | A city below this prosperity may revolt |
| revolt_min_population | isyan_alt | 600 | 0 | 1,000,000 | War and diplomacy | Minimum population of a revolting city |
| first_epoch_years_engine | ilk_cag_motor | 15 | 0 | 50 | Heroes and mortals | Years an engine-born mortal lives in the epoch of birth |
| first_epoch_years_son | ilk_cag_ogul | 35 | 0 | 50 | Heroes and mortals | Years a son-created mortal lives in the epoch of creation |
| notable_lifespan_bonus | onemli_omur | 15 | 0 | 500 | Heroes and mortals | Extra lifespan of notable mortals (years) |
| medicine_lifespan_bonus | tip_omur | 20 | 0 | 500 | Heroes and mortals | Extra lifespan in a region that knows medicine (years) |
| growth_base_pct | buyume_taban | 6 | 0 | 100 | Population and growth | Base of population growth (% per epoch) |
| growth_min_pct | buyume_en_az | 3 | 0 | 100 | Population and growth | Minimum rate of population growth (%) |
| growth_fertility_divisor | buyume_bereket_bolen | 600 | 10 | 100,000 | Population and growth | Fertility contribution to growth: fertility / this number |
| growth_prosperity_divisor | buyume_refah_bolen | 400 | 10 | 100,000 | Population and growth | Prosperity contribution to growth in a city: (prosperity − 40) / this number |
| growth_agriculture_pct | buyume_tarim | 140 | 0 | 1000 | Population and growth | Growth multiplier for those who know agriculture (%) |
| growth_max_pct | buyume_ust | 60 | 0 | 1000 | Population and growth | Maximum growth in one epoch (%) |
| shrink_max_pct | kucilme_ust | 25 | 0 | 100 | Population and growth | Maximum shrinkage in one epoch (%) |
| carrying_capacity | kapasite | 60,000 | 100 | 100,000,000 | Population and growth | Base carrying capacity of a region (people) |
| capacity_agriculture_pct | kapasite_tarim | 120 | 0 | 1000 | Population and growth | Contribution of agriculture to capacity (by share of those knowing agriculture, %) |
| capacity_crowded_cap_pct | kapasite_kalabalik | 150 | 100 | 1000 | Population and growth | Capacity cap of a region with many communities (%) |
| cult_growth_base_pct | tarikat_buyume_taban | 5 | 0 | 100 | Population and growth | Base of cult growth (%) |
| cult_growth_influence_divisor | tarikat_etki_bolen | 400 | 10 | 100,000 | Population and growth | Influence contribution to cult growth: influence / this number |
| cult_growth_charisma_divisor | tarikat_karizma_bolen | 500 | 10 | 100,000 | Population and growth | Patron charisma contribution to cult growth: charisma / this number |
| god_grudge_spill_chance | kin_sans | 30 | 0 | 100 | War and diplomacy | The gods' grudge seeps into mortals (% per pair) |
| resource_rivalry_war_chance | rekabet_sans | 15 | 0 | 100 | War and diplomacy | Rivalry war over the same resource (%) |
| resource_barter_chance | takas_sans | 30 | 0 | 100 | Economy | Resource barter between neighbours begins (%) |
| cursed_item_contagion_chance | lanet_bulas_sans | 25 | 0 | 100 | Heroes and mortals | A cursed item infects its owner (%) |
| magic_storm_chance | buyu_firtina_sans | 8 | 0 | 100 | Cosmic horror | Magic storm in a magic-dense region (%) |
| magic_storm_curse_chance | buyu_firtina_lanet | 30 | 0 | 100 | Cosmic horror | An item is cursed in a magic storm (%) |
| creature_migration_chance | yaratik_goc_sans | 15 | 0 | 100 | Creatures | A dangerous species migrates to a neighbouring region (%) |
| language_spread_chance | dil_yayilim_sans | 20 | 0 | 100 | Religion and language | Under the one-language law a language spreads along links (%) |
| famine_migration_chance | kitlik_goc_sans | 25 | 0 | 100 | Population and growth | Famine migration (%) |
| spirit_haunt_chance | ruh_musallat_sans | 30 | 0 | 100 | The Beyond | A restless spirit haunts a settlement (%) |
| coinage_chance | sikke_sans | 25 | 0 | 100 | Economy | A wealthy community mints coins (%) |
| currency_adopt_chance | para_benimse_sans | 30 | 0 | 100 | Economy | A trade partner adopts the currency (%) |
| sorcerer_act_chance | buyucu_eylem_sans | 30 | 0 | 100 | Heroes and mortals | A sorcerer casts magic this epoch (%) |
| sorcerer_curse_chance | buyucu_lanet_sans | 50 | 0 | 100 | Heroes and mortals | A sorcerer curses an enemy (otherwise protects) (%) |
| creature_revolt_chance | yaratik_isyan_sans | 8 | 0 | 100 | Creatures | An intelligent creature rebels against its creator (%) |
| godlessness_chance | tanrisizlik_sans | 15 | 0 | 100 | Religion and language | A community with weak faith becomes godless (%) |
| speciation_chance | evrim_sans | 18 | 0 | 100 | Creatures | A migrated species splits into a subspecies (%) |
| birth_chance | dogum_sans | 30 | 0 | 100 | Heroes and mortals | A child from lover or married mortals (%) |
| love_rivalry_chance | ask_rekabet_sans | 8 | 0 | 100 | Heroes and mortals | Love or rivalry between mortals in the same place (%) |
| love_share_pct | ask_orani | 55 | 0 | 100 | Heroes and mortals | Share of these that are love (%) |
| dialect_split_chance | lehce_sans | 15 | 0 | 100 | Religion and language | Dialect divergence in an isolated settlement (%) |
| ghost_chance | hayalet_sans | 50 | 0 | 100 | The Beyond | If the dead return, the deceased becomes a ghost (%) |
| famous_spirit_chance | ruh_dogus_sans | 30 | 0 | 100 | The Beyond | A famous dead person's spirit does not rest (%) |
| mourning_tradition_chance | yas_ayini_sans | 40 | 0 | 100 | Heroes and mortals | Mourning tradition for a famous dead person (%) |

### WORLD_EPOCH_TRANSITION

Old namespace `DUNYA_CAG_GECISI` · 37 rows · defined in `src/sim.js`. Epoch transition: capacity, growth laws, son regen/healing/existence, rivalry, apocalypse damage.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| bounty_law_fertility | yasa_bereket | 3 | 0 | 100 | Population and growth | Per-epoch fertility gain of lands under the bounty law |
| drought_law_fertility | yasa_kuraklik | 3 | 0 | 100 | Population and growth | Per-epoch fertility loss of lands under the drought law |
| capacity_architecture_pct | kapasite_mimarlik | 120 | 0 | 1000 | Population and growth | Carrying-capacity multiplier of a settlement knowing architecture (%) |
| capacity_fertility_base_pct | kapasite_bereket_taban | 30 | 0 | 1000 | Population and growth | Share of carrying capacity independent of fertility (%) |
| capacity_fertility_divisor | kapasite_bereket_bolen | 60 | 1 | 1000 | Population and growth | Fertility contribution to carrying capacity: fertility / this number |
| capacity_breadth_base_pct | kapasite_genislik_taban | 50 | 0 | 1000 | Population and growth | Share of carrying capacity independent of breadth (%) |
| place_fertility_share_pct | konum_bereket_pay | 40 | 0 | 100 | Population and growth | Share of the place in the fertility of one living in a place outside the region (%; the rest is the region's) |
| bounty_power_growth_mult | bereket_gucu_carpan | 2 | 1 | 20 | Population and growth | Growth multiplier of a patron with the Bounty power (times) |
| bounty_power_min_fertility | bereket_pozitif | 35 | 0 | 100 | Population and growth | Minimum fertility at which the Bounty power multiplies growth |
| cult_default_charisma | tarikat_karizma_varsayilan | 30 | 0 | 100 | Population and growth | Default charisma in the growth of a cult without a patron |
| cult_capacity_min | tarikat_kapasite_en_az | 150 | 0 | 10,000,000 | Population and growth | Lowest cap of cult followers in a region (people) |
| cult_shrink_max_pct | tarikat_kucilme_ust | 20 | 0 | 100 | Population and growth | Maximum shrinkage of a cult in one epoch (%) |
| cult_growth_max_pct | tarikat_buyume_ust | 50 | 0 | 1000 | Population and growth | Maximum growth of a cult in one epoch (%) |
| growth_prosperity_threshold | buyume_refah_esik | 40 | 0 | 100 | Population and growth | A city above this prosperity grows faster (below it, slower) |
| immortality_law_growth_pct | olumsuzluk_buyume | 50 | 0 | 1000 | Population and growth | Population growth rate under the immortality law (%) |
| short_life_law_growth_pct | kisa_omur_buyume | 150 | 0 | 1000 | Population and growth | Population growth rate under the short-life law (%) |
| star_pick_base_weight | gok_taban_agirlik | 5 | 0 | 1000 | Sky | Base weight of each celestial body when picking the star of the epoch |
| wake_hp_divisor | uyanis_can_bolen | 2 | 1 | 100 | Creator and essence | HP of a son waking from sleep: max HP / this number |
| heal_base | iyilesme_taban | 5 | 0 | 1000 | Creator and essence | Son's per-epoch HP healing: base |
| heal_endurance_divisor | iyilesme_bolen | 10 | 1 | 1000 | Creator and essence | Endurance contribution to a son's healing: endurance / this number |
| existence_step | varlik_adim | 10 | 0 | 100 | Creator and essence | Maximum approach of a son's existence toward its target in one epoch |
| faith_essence_divisor | inanc_oz_bolen | 10 | 1 | 1000 | Creator and essence | Essence income from faith: faith / this number (son and Creator) |
| essence_spring_bonus | oz_pinari | 4 | 0 | 100 | Creator and essence | Extra essence income of a son with the Essence Spring power |
| radiant_essence_bonus | parlak_oz | 3 | 0 | 100 | Creator and essence | Extra essence income of a son whose existence is Radiant |
| star_domain_essence_bonus | yildiz_alan_oz | 3 | 0 | 100 | Sky | Extra essence income of a son bearing the domain of the epoch's star |
| artwork_renown | eser_un | 1 | 0 | 100 | Creator and essence | Per-epoch renown contribution of an artwork depicting a god |
| artwork_existence | eser_varlik | 1 | 0 | 100 | Creator and essence | Per-epoch existence contribution of an artwork depicting a god |
| domain_rivalry | alan_rekabet | 3 | 0 | 100 | Creator and essence | Per-epoch relation loss of sons sharing the same domain (per shared domain) |
| domain_rivalry_floor | alan_rekabet_taban | 70 | 0 | 100 | Creator and essence | Domain rivalry lowers the relation at most to minus this value (deeper hostility comes from conflict and slowly reverts) |
| rebel_steal_base | asi_calma_taban | 6 | 0 | 1000 | Creator and essence | Essence a rebel son steals from his father: base |
| rebel_steal_per_level | asi_calma_seviye | 2 | 0 | 100 | Creator and essence | Extra essence a rebel son steals per level |
| temples_per_apocalypse_push | tapinak_bolen | 2 | 1 | 100 | Apocalypse | Number of temples that push the apocalypse back by 1 |
| apocalypse_disaster_severity | kiyamet_siddet | 90 | 0 | 100 | Apocalypse | Severity of the apocalypse's disasters destroying regions (%) |
| apocalypse_event_severity | kiyamet_olay_siddet | 100 | 0 | 100 | Apocalypse | Severity of the apocalypse event record |
| apocalypse_chronicle_regions | kiyamet_kronik_id | 12 | 0 | 1000 | Chronicle | Maximum regions linked to the apocalypse chronicle entry |
| folded_chronicle_ids_cap | kronik_id_tavan | 40 | 0 | 1000 | Chronicle | Maximum entities linked to a folded chronicle line |
| essence_overflow_note | oz_tasma_not | 20 | 0 | 100,000 | Chronicle | When overflowing essence exceeds this, a note is added to the chronicle |

### WORLD_HUNT

Old namespace `DUNYA_AV` · 32 rows · defined in `src/sim.js`. Hero vs monster encounters.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| intellect_divisor | akil_bolen | 3 | 1 | 100 | Heroes and mortals | Intellect contribution to the hero's strength: intellect / this number |
| agility_divisor | ceviklik_bolen | 2 | 1 | 100 | Heroes and mortals | Agility contribution in the encounter: agility / this number |
| danger_divisor | tehlike_bolen | 2 | 1 | 100 | Heroes and mortals | Danger contribution to the monster's strength: danger / this number |
| die | zar | 20 | 1 | 100 | Heroes and mortals | Encounter die (1–X) |
| die_mult | zar_carpan | 3 | 0 | 20 | Heroes and mortals | Multiplier of the encounter die |
| patron_charisma_divisor | hami_karizma_bolen | 10 | 1 | 1000 | Heroes and mortals | Patron god's contribution to the hero: charisma / this number |
| weapon_mult | silah_carpan | 2 | 0 | 20 | Heroes and mortals | Multiplier of the hero's weapons in the encounter (times) |
| sorcerer_intellect_divisor | buyucu_akil_bolen | 3 | 1 | 100 | Heroes and mortals | Extra strength of a sorcerer hero: intellect / this number |
| megafauna_bonus | megafauna_guc | 40 | 0 | 500 | Creatures | Extra strength of megafauna in the encounter |
| singular_power | tekil_guc | 5 | 1 | 12 | Creatures | A monster at this power level dies after a single defeat |
| defeat_danger_loss | tehlike_kaybi | 25 | 0 | 100 | Creatures | Danger loss of a defeated monster |
| death_danger | olum_tehlike | 5 | 0 | 100 | Creatures | A monster whose danger falls to this dies |
| rewind_danger_gain | geri_sarma_tehlike | 20 | 0 | 100 | Creatures | Danger gained on return by a time-rewinding creature |
| megafauna_slayer_power_gain | megafauna_guc_artis | 2 | 0 | 12 | Heroes and mortals | Power-level gain of a megafauna slayer |
| power_cap | guc_tavan | 10 | 1 | 12 | Heroes and mortals | Power-level cap of heroes and items |
| epic_power | destan_guc | 8 | 1 | 12 | Heroes and mortals | Power level of an age-changing epic |
| epic_spread | destan_yayginlik | 90 | 0 | 100 | Heroes and mortals | Spread of an age-changing epic |
| victory_charisma | zafer_karizma | 5 | 0 | 100 | Heroes and mortals | Charisma gain of a victorious hero |
| patron_renown | hami_un | 4 | 0 | 100 | Heroes and mortals | Patron god's renown gain from the hero's victory |
| patron_xp | hami_xp | 12 | 0 | 1000 | Heroes and mortals | Patron god's XP gain from the hero's victory |
| weapon_might_gain | silah_kudret | 6 | 0 | 100 | Heroes and mortals | Might gain of the hero's weapon on victory |
| legendary_weapon_victories | efsane_zafer | 2 | 1 | 100 | Heroes and mortals | Victories needed for a weapon to become legendary |
| ballad_power | turku_guc | 3 | 1 | 12 | Heroes and mortals | Power level of a heroic ballad |
| ballad_spread | turku_yayginlik | 55 | 0 | 100 | Heroes and mortals | Spread of a heroic ballad |
| armor_save_min_protection | zirh_esik | 40 | 0 | 100 | Heroes and mortals | Minimum protection of armor able to turn death into a wound |
| armor_save_base_pct | zirh_sans_taban | 50 | 0 | 100 | Heroes and mortals | Chance armor protects the hero from death: base (%) |
| armor_save_divisor | zirh_sans_bolen | 250 | 1 | 10,000 | Heroes and mortals | Armor contribution to the save chance: protection / this number |
| armor_save_hp_loss | zirh_can | 60 | 0 | 1000 | Heroes and mortals | HP loss of a hero saved by their armor |
| unknown_hp | bilinmeyen_can | 100 | 1 | 1000 | Heroes and mortals | HP before armor damage of a hero with no recorded HP |
| armor_save_wear | zirh_asinma | 15 | 0 | 100 | Heroes and mortals | Protection loss of the armor that saved the hero |
| lament_power | agit_guc | 2 | 1 | 12 | Heroes and mortals | Power level of the fallen hero's lament |
| lament_spread | agit_yayginlik | 45 | 0 | 100 | Heroes and mortals | Spread of the fallen hero's lament |

### WORLD_PHYSICS

Old namespace `DUNYA_FIZIK` · 10 rows · defined in `src/world.js` · also read by `src/kozmos.js`, `src/oyuncu.js`. World physics: time factor, atmosphere life capacity, gravity martiality.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| time_factor_min | zaman_en_az | 25 | 1 | 10,000 | Cosmos and travel | Minimum time factor Fate gives a world it births (%; 100 = normal; does not limit a value the god sets manually) |
| time_factor_max | zaman_en_cok | 400 | 1 | 10,000 | Cosmos and travel | Maximum time factor Fate gives a world it births (%; does not limit a value the god sets manually) |
| capacity_no_atmosphere | kapasite_yok | 25 | 0 | 1000 | Cosmos and travel | Life capacity of a world without atmosphere (%) |
| capacity_thin | kapasite_ince | 60 | 0 | 1000 | Cosmos and travel | Life capacity of a world with thin atmosphere (%) |
| capacity_normal | kapasite_olagan | 100 | 0 | 1000 | Cosmos and travel | Life capacity of a world with normal atmosphere (%) |
| capacity_dense | kapasite_yogun | 115 | 0 | 1000 | Cosmos and travel | Life capacity of a world with dense atmosphere (%) |
| capacity_toxic | kapasite_zehirli | 40 | 0 | 1000 | Cosmos and travel | Life capacity of a world with toxic atmosphere (%) |
| martiality_low_gravity | savas_dusuk | -4 | -100 | 100 | Cosmos and travel | Martiality effect in low gravity |
| martiality_normal_gravity | savas_olagan | 0 | -100 | 100 | Cosmos and travel | Martiality effect in normal gravity |
| martiality_high_gravity | savas_yuksek | 6 | -100 | 100 | Cosmos and travel | Martiality effect in high gravity |

### WORLD_WAR_STRENGTH

Old namespace `DUNYA_SAVAS_GUCU` · 19 rows · defined in `src/sim.js`. War-strength formula coefficients.

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| patron_strength_divisor | hami_guc_bolen | 8 | 1 | 1000 | War and diplomacy | Patron god's war contribution: god's strength / this number |
| war_father_mult | savas_babasi_carpan | 2 | 1 | 20 | War and diplomacy | The War Father power multiplies the patron contribution (times) |
| weapon_damage_divisor | silah_hasar_bolen | 8 | 1 | 1000 | War and diplomacy | Weapon's war contribution: damage / this number |
| armor_protection_divisor | silah_koruma_bolen | 10 | 1 | 1000 | War and diplomacy | Armor's war contribution: protection / this number |
| item_might_divisor | silah_kudret_bolen | 20 | 1 | 1000 | War and diplomacy | Item might's war contribution: might / this number |
| warrior_threshold_pct | savasci_esik | 10 | 0 | 100 | War and diplomacy | The warrior class adds war strength if above this share (%) |
| warrior_coeff_pct | savasci_katsayi | 60 | 0 | 1000 | War and diplomacy | Coefficient of warrior-class share on war strength (%) |
| cult_zealotry_coeff_pct | tarikat_bagnazlik | 60 | 0 | 1000 | War and diplomacy | Zealotry coefficient of a cult's war strength (%) |
| default_zealotry | varsayilan_bagnazlik | 50 | 0 | 100 | War and diplomacy | Zealotry in war of a cult with no recorded zealotry |
| cult_follower_log_coeff | tarikat_murit_log | 8 | 0 | 100 | War and diplomacy | Coefficient of follower count (log10) on a cult's war strength |
| faction_sway_coeff_pct | hizip_nufuz | 20 | 0 | 1000 | War and diplomacy | Sway coefficient of a faction's war strength (%) |
| settlement_defense_coeff_pct | yerlesim_savunma | 80 | 0 | 1000 | War and diplomacy | Walls (defense) coefficient of a settlement's war strength (%) |
| mortal_agility_divisor | olumlu_ceviklik_bolen | 2 | 1 | 100 | War and diplomacy | Agility contribution to a mortal's war strength: agility / this number |
| species_strength_divisor | tur_guc_bolen | 2 | 1 | 100 | War and diplomacy | Strength contribution to a creature species' war strength: strength / this number |
| default_stat | varsayilan_stat | 30 | 0 | 100 | War and diplomacy | Default strength of a community with no recorded war stat |
| warcraft_bonus | savas_bilgisi | 12 | 0 | 200 | War and diplomacy | War strength gain of those knowing the art of war |
| forbidden_knowledge_bonus | yasak_bilgi | 15 | 0 | 200 | War and diplomacy | War strength gain of those knowing forbidden knowledge |
| civilization_stage_bonus | basamak_guc | 5 | 0 | 100 | War and diplomacy | War strength gain per civilization stage |
| ally_share_pct | muttefik_pay | 40 | 0 | 100 | War and diplomacy | Share of strength allies add to a war (%) |

---

## Part D — Known bugs, design smells and recommendations

1. **Stale numbers in static text.** Many UI/prompt strings embed literal numbers instead of reading the live rule: power descriptions in `GUC_ETKILERI` ("40% cheaper", "+15", "+4 essence", "×1.5", "+25", "×2", "half price", "50% more severe"), `varlikDurumu('parlak').etki` ("+3 essence"), `KAYNAKLAR` ("every 10 faith = +1 essence", "sleeps two epochs", "new power at levels 3 and 5"), and `BILGI_DALLARI` effect texts. Worse, the **Seer** power is advertised as "prophecies half price" but is implemented as the generic cheap-creation multiplier (60%). New design: render every effect text from the rule snapshot (templated strings), never literals.
2. **Hard-coded ranges duplicating LIMITS.** `VARLIK_TURLERI` stat ranges hard-code the same caps that `LIMITS` tunes (settlement pop 2,000,000, people 50,000,000, cult followers 10,000,000, army 10,000,000, mortal HP 300, age/lifespan 50,000). Changing a LIMITS value does not change the validation ranges shown to agents. Derive entity stat ranges from the rules.
3. **Duplicated tunables with the same meaning** (they drift independently): `SKY.star_pick_base_weight` vs `WORLD_EPOCH_TRANSITION.star_pick_base_weight` (both 5); `DEEP_LIFE.lifespan_cap` vs `WORLD_EFFECTS.lifespan_cap` (both 50,000, different mins); `BEYOND.cult_default_followers` vs `SKY.cult_default_followers` (50); `COSMIC_HORROR.default_sanity` vs `SON_TOOLS.default_sanity` (70; the label even says "same as korku.js default"); default existence 60 in `DEEP_LIFE.existence_default`, `COSMIC_HORROR.default_existence`, `WORLD_EFFECTS.default_existence`, `SUMMONING.start_existence`; default loyalty 50 in `REPUTATION`, `SON_TOOLS`, `GOALS`; `FATE.model_retries` vs `MODEL.retry_attempts` (3); `OPPORTUNITIES.long_thread_steps`/`stale_epochs` vs `FATE.long_thread_steps`/`stale_thread_epochs` (8/4); apocalypse warning % appears three times with different defaults (`CONTEXT` 30, `OPPORTUNITIES` 50, `COUNCIL` 50). Recommendation: consolidate into one key each (keep the old keys as aliases in an import mapping); the integrator must decide whether the differing apocalypse-warning defaults are intentional.
4. **Two independent son↔son relation label systems** (`CORE_RULES.relation_*` via `iliskiEtiketT`, 7 labels, `≤`/`<` boundaries; and `SON_RELATIONS` via `iliskiEtiket`, 5 labels, `>` boundaries). Pick one vocabulary in the new app.
5. **`clamp` silently rounds** and maps NaN to 0. It is used across 25 modules, including on values that are conceptually fractional. New code: `clamp_int` and `clamp_float` separately; validate inputs instead of coercing.
6. **Missing cross-field validation.** Only per-key `min` is enforced. Inconsistent combinations are accepted: rarity `stat_min > stat_max` (breaks `randInt`), `*_min > *_max` pairs (WORLD_BIRTH regions/words, NARRATIVE `*_min/*_max`, DEATH take-life min/max chance, SON_TOOLS dream/incite min/max chance), non-monotonic phase years in `EPOCH_FLOW.year_*`, non-monotonic tier thresholds in `CORE_RULES.tier_*` and existence thresholds (`existence_faded ≤ existence_solid ≤ existence_radiant`), relation thresholds. Add declarative constraints to the registry.
7. **Global mutable state.** Rules live in module-level objects mutated in place; `CAG_YIL` is an exported `let` rebound by a setter; `VARLIK_TURLERI[t].tier/taban` are `Object.defineProperty` getters. This makes per-world isolation, testing and concurrency fragile. New: an immutable `RuleSnapshot` per world/tick injected into services.
8. **Circular-import workarounds.** `tanimla('NS', {})` empty declarations and the `rules.js` `ON_TANIMLAR` shim exist only to dodge import cycles. New: one `rules` package that owns the registry; modules import keys, not each other.
9. **Two declaration styles.** Most rules use `tanimla` tuples; the `rules.js` static objects (`COSTS`, `DENGE`, `RARITIES`, …) get their ranges/labels from a separate hard-coded `alanlar()` list and `AD` map. Use one schema for all.
10. **Only diffs are persisted.** `denge_ayar` stores values that differ from defaults, so shipping a new default silently rebalances existing worlds. Store a `rules_version` with each world (or persist the full effective set) and migrate explicitly.
11. **Booleans as 0/1 integers** (`LINK_GRAPH.auto_repair`, `FATE.opening_fix`, `SON_TOOLS.free_living_creation`, `DEEP_WORLD.mobilization`, …). In the new registry add a `type` (int | bool | percent | seconds | chars) to drive UI and validation; keep values numerically compatible.
12. **Reviving power not fully wired**: `panteon.js` foreign-god war sets sleep to literal `1` for the Reviving power instead of `SON_TOOLS.reviving_sleep_epochs`.
13. **Turkish-dependent logic** — LANGUAGE-SPECIFIC, drop or replace: `OBUR_DUNYA_DESEN` underworld regex; `sadelestir` Turkish letter folding and `toLocaleLowerCase('tr')`; `alanEsle` Turkish casing; debt amounts encoded in Turkish link descriptions (`borcAciklama`/`borcOku` — use structured fields); disaster subtypes stored as Turkish display names (`OLAY_ALT_TURLERI`); DIL registry keys about Turkish-word detection (`native_word_window`, `native_word_min_count` — in the old app they detect real Turkish words vs invented roots; in English re-target to an English dictionary/stop-list or drop) and suffix stripping (`motif_suffix_strip_steps`, `motif_root_*` — Turkish agglutination; in English use simple stemming).
14. **Naming collision**: "varlık" means both *entity* (record) and a son's *existence* score; old keys `varlik_*` in CORE_RULES are existence. The new spec uses `existence_*` consistently.
15. **Link label mismatch**: link key `ustasi` ("master of") is labelled "çırağı" ("apprentice of"). Decide direction explicitly in the new link schema.
16. **Mythic summon weight** is excluded from the editable list by special-casing in `alanlar()`; if every other weight is set to 0, `rollRarity` returns common by fallback. Make "summonable" an explicit flag per rarity.
17. **Rule labels contain the gate legend** (`NADIRLIK_KAPI` labels repeat "0 Common, 1 Uncommon…"). In the new UI render gates as a rarity dropdown.
18. **Max is advisory but not consistently sane**: defaults `max = max(1000, |default|×10)` produce odd ranges (e.g. 0–1000 for percentages). Review per key when typing the registry.

## Part E — Items the integrator must decide

- **Namespace names.** I translated old namespaces to English names (table in Part C index, e.g. `KURAL→CORE_RULES`, `DERIN_YASAM→DEEP_LIFE`, `DERIN_SEFER→DEEP_WARFARE`, `OGUL_ARAC→SON_TOOLS`, `OLUMLU_ARAC→MORTAL_TOOLS`, `KORKU→COSMIC_HORROR`, `SUNUCU→SERVER`, `DENGE→BALANCE`, `NADIRLIK_KAPI→RARITY_GATES`, `MUDAHALE→INTERVENTION_EFFECTS`). Other spec parts should reference keys as `NEW_NS.new_key` from `rules-registry.json`; if another author chose different names, `old_namespace`/`old_key` are the join columns.
- **Rarity names**: yaygin/seckin/nadir/destansi/efsanevi/mitik → common/uncommon/rare/epic/legendary/mythic ("seçkin" literally means "distinguished/elite"; "uncommon" chosen for the conventional ladder).
- **Whether to consolidate the duplicated tunables** listed in D.3 (changes the key set; JSON currently keeps every original key 1:1).
- **Whether to keep the static `RARITIES`/`COSTS`/`DENGE` objects as tunables** (they are in the registry here, flattened, e.g. `RARITIES.common_stat_min`) or model rarities as a typed table edited as a whole.
- **Server/UI-only tunables** (`SERVER`, `UI`, `NOTIFICATIONS`, `METRICS`, `IMAGE_GEN`, `BATCH`, `BACKUP`, `MODEL`) are operational settings rather than game balance; the new app may move them out of the per-world rules into app config.

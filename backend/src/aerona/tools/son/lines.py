from aerona.catalog.god_lines import Line

ANCHOR = Line("tools.son.anchor", "{son} bound their existence to {entity}: {reason}")
BIND_MORTALS = Line("tools.son.bind_mortals", "{son} bound {first} and {second} ({binding}): {reason}")
PLANT_IDEA = Line("tools.son.plant_idea", "{son} planted {idea} in the mind of {mortal}: {reason}")
SET_AIM = Line("tools.son.set_aim", "{son} set out to {aim}")
MORTAL_FORM = Line("tools.son.mortal_form", "{son} took a mortal form among {place}: {reason}")
WARD_OUTER = Line("tools.son.ward_outer", "{son} warded the cosmos against {outsider}: {reason}")
DIVINE_PACT = Line("tools.son.divine_pact", "{son} and {god} sealed a divine pact: {reason}")
SHAPE_BLOOD = Line("tools.son.shape_blood", "{son} worked {trait} into the blood of {mortal}: {reason}")
REVEAL_TRUE_NAME = Line("tools.son.reveal_true_name", "{son} revealed the true name of {bearer} to {learner}: {reason}")
TEND_LAND = Line("tools.son.tend_land", "{son} {verb} the land of {region}: {reason}")
SPREAD_WORD = Line("tools.son.spread_word", "{son} spread word of {subject} in {community}: {reason}")
STIR_HEARTS = Line("tools.son.stir_hearts", "{son} stirred {stir} in {first} toward {second}: {reason}")
TOUCH_MORTAL = Line("tools.son.touch_mortal", "{son} touched {mortal} ({touch}): {reason}")
WORDS = Line("tools.son.words", "{son} added new words to {language}: {words}.")
TENET = Line("tools.son.tenet", "{son} revealed a new tenet to {cult}: {tenet}.")
REBORN = Line("tools.son.reborn", "{son} had the soul of {spirit} reborn as {child}.")
MESSAGE = Line("tools.son.message", '{son} {phrase} to {sibling}: "{message}"')
COVENANT = Line("tools.son.covenant", '{son} and {sibling} swore a covenant: "{terms}"')
COVENANT_BROKEN = Line("tools.son.covenant_broken", "{son} thereby broke the covenant with {sibling}.")
GIFT_REFUSED = Line("tools.son.gift_refused", "{community} refused {son}'s transfer of it to {sibling}; it stayed loyal to its old god.")
GIFT_BOND = "{son}'s gift"
GIFT = Line("tools.son.gift", '{son} gave {sibling} a gift: {notes}. "{words}"')
PRAYER = Line("tools.son.prayer", '{son} prayed to the Creator{request}: "{message}"')
BOND = Line("tools.son.bond", "{son} declared a bond: {source} {relation} {target}{description}.")
CREATED = Line("tools.son.created", "{son}{partner} created {type:an}: {name}{subtype}{location}.{effects}")
CROWDED_LAND = Line("tools.son.crowded_land", "{son} opened a new {type} for mortals squeezed into crowded lands: {name}.")
FIRST_LIFE = Line(
    "tools.son.first_life",
    "{son} created the first people of the {world} world: {name}.",
)
HARVEST = Line("tools.son.harvest", "{son} drew {gain} essence from {resource}; the resource's abundance fell to {abundance}.")
COSMIC_BED = Line("tools.son.cosmic_bed", "{son} opened {bed} in {region}: {reason}")
AFFECT = Line("tools.son.affect", "{son} changed {entity}: {changes}. ({reason})")
CHOSEN = Line("tools.son.chosen", "{son} declared the mortal {mortal} their chosen one: {boon}")
CURSE = Line("tools.son.curse", '{son} cursed {entity}: "{curse}" ({notes})')
DREAM_TAKEN = Line("tools.son.dream_taken", '{son} sent {target} a dream and turned it to themselves{lost}. Dream: "{dream}"')
DREAM_FAILED = Line("tools.son.dream_failed", "{son} sent {target} a dream but the dream did not take hold{sensed}.")
TEACH = Line("tools.son.teach", "{son} taught {target} the knowledge of {knowledge}: {how}")
SOW_CROP = Line("tools.son.sow_crop", "{son} had {name} sown in the fields of {place}.")
REVEAL_TRUTH = Line("tools.son.reveal_truth", "{son} made the scholars of {place} hold {name} as their account of {domain}.")
ADVANCE_KNOWLEDGE = Line("tools.son.advance_knowledge", "{son} deepened the knowledge of {knowledge} (level {level}): {how}")
MIRACLE = Line("tools.son.miracle", "{son} sent down {miracle:an} miracle upon {target}: {how}{notes}")
DISASTER = Line("tools.son.disaster", "{son} sent {disaster} upon {target}: {name}. ({reason}){notes}")
TRANSFORM = Line("tools.son.transform", "{son} transformed {old}{renamed}. ({reason})")
DESTROY = Line("tools.son.destroy", "{son} destroyed {name}. ({reason})")
INCITE = Line("tools.son.incite", "{son} sowed hostility between {first} and {second}: {pretext}")
WAGE_WAR = Line("tools.son.wage_war", "By the will of {son}, {attacker} declared war on {defender}: {reason}")
RAISE_HOST = Line("tools.son.raise_host", "At the call of {son}, {community} raised {army}.")
DISBAND_HOST = Line("tools.son.disband_host", "{son} sent {army} home: {reason}")
LAY_SIEGE = Line("tools.son.lay_siege", "{son} set {army} against the walls of {city}.")
OFFER_PEACE = Line("tools.son.offer_peace", "{son} ended the war between {first} and {second}.")
COMMISSION_VESSEL = Line("tools.son.commission_vessel", "{son} had {owner} lay down the {hull} {name}.")
DESIGN_UNIT = Line("tools.son.design_unit", "{son} taught {owner} to field {name}.")
PLANT_SPIES = Line("tools.son.plant_spies", "{son} planted the spies of {owner} inside {target}.")
TREATY = Line(
    "tools.son.treaty",
    "{son} established an interworld {treaty} treaty between {first} in the {first_world} world and {second} in the {second_world} world: {terms}",
)
FOREIGN_TALK = Line("tools.son.foreign_talk", '{son} spoke with the foreign god {god} {manner}: "{words}" ({outcome}).')
MOVE = Line("tools.son.move", "{son} turned from {old} to {new}.")
HIDE_SECRET = Line("tools.son.hide_secret", "{son} hid something in {place}: {reason}")
SANCTIFY_PLACE = Line("tools.son.sanctify_place", "{son} sanctified {place}: {reason}")
RAISE_NEXUS = Line("tools.son.raise_nexus", "{son} drew the ley lines together at {place}: {reason}")
SEVER_LEY = Line("tools.son.sever_ley", "{son} cut the ley line between {first} and {second}: {reason}")
CONVENE_GATHERING = Line("tools.son.convene_gathering", "{son} called {kind:an} at {host}: {reason}")
RAISE_CREATURE = Line("tools.son.raise_creature", "{son} raised {name} as a divine creature at {home}")
MAKE_SERVITOR = Line("tools.son.make_servitor", "{son} made {name} its {rank}")
LAY_GEAS = Line("tools.son.lay_geas", "{son} laid a geas on {bearer}: {reason}")
CALL_HEROQUEST = Line("tools.son.call_heroquest", "{son} called {quester} to a heroquest: {reason}")
LAY_ENCHANTMENT = Line("tools.son.lay_enchantment", "{son} laid {name} as a global enchantment: {reason}")
SHIELD_CONVOY = Line("tools.son.shield_convoy", "{son} guarded a convoy on {route}: {reason}")
ANSWER_ORACLE = Line("tools.son.answer_oracle", "{son} answered the oracle of {town}: {reason}")
READ_DREAMS = Line("tools.son.read_dreams", "{son} read the dreams of {mortal}: {reason}")
SCOUR_STREETS = Line("tools.son.scour_streets", "{son} scoured the streets of {town}: {reason}")
MARK_LINEAGE = Line("tools.son.mark_lineage", "{son} {word} the line of {species}: {reason}")
MOVE_PLAGUE_RESPONSE = Line("tools.son.move_plague_response", "{son} moved {community} to answer {disease}: {response}. {reason}")
REVEAL_TONGUE = Line("tools.son.reveal_tongue", "{son} taught {mortal} words of its sacred tongue: {reason}")
DECREE_SOUND = Line("tools.son.decree_sound", "{son} changed a sound of {language}: {reason}")
VEIL_NAME = Line("tools.son.veil_name", "{son} made the name {name} unspeakable: {reason}")
RELEASE_CREATURE = Line("tools.son.release_creature", "{son} set {name} free of its service: {reason}")
SHAPE_IMAGE = Line("tools.son.shape_image", "{son} chose to {stance} the image its peoples hold of it: {reason}")
LOOSE_DISEASE = Line("tools.son.loose_disease", "{son} loosed a sickness of its own making, {disease}, upon {target}: {reason}")
SHAPE_FOLK = Line("tools.son.shape_folk", "{son} taught {people} new ways: {changes}. {reason}")
FORGE_MATERIAL = Line("tools.son.forge_material", "{son} forged {name} into the world: {reason}")
RESHAPE_LAND = Line("tools.son.reshape_land", "{son} reshaped {region} ({act}): {reason}")
SANCTIFY_REGION = Line("tools.son.sanctify_region", "{son} sanctified {region}; its ground is holy now: {reason}.")
CURSE_REGION = Line("tools.son.curse_region", "{son} loosed {danger} upon {region}: {reason}.")
REDIRECT_RIVER = Line("tools.son.redirect_river", "{son} turned the {river} of {source} into {target}: {reason}.")
SHAPE_WEATHER = Line("tools.son.shape_weather", "{son} held {weather} over {region} for {epochs} ages: {reason}.")
RAISE_DISTRICT = Line("tools.son.raise_district", "{son} raised {district:an} in {town}: {reason}")
DESIGN_DISTRICT = Line("tools.son.design_district", "{son} devised the {design}, a new kind of {base} for the cities of the world.")
REORDER_SEASONS = Line("tools.son.reorder_seasons", "{son} turned the year of {world}: its seasons now run {order}.")
STITCH = Line("tools.son.stitch", "{son} sealed the leak of the {world} world ({how}); leakage {old} to {new}.")

MESSAGE_PHRASES = {
    "friendship": "spoke warmly",
    "alliance": "proposed an alliance",
    "love": "declared their love",
    "threat": "spoke with a threat",
    "mockery": "spoke mockingly",
    "warning": "gave a warning",
    "bargain": "proposed a bargain",
}
PRAYER_REQUESTS = {
    "essence": ", asked for essence",
    "blessing": ", asked for a blessing",
    "permission": ", asked permission",
    "vengeance": ", asked for revenge",
    "forgiveness": ", asked forgiveness",
    "none": "",
}
TALK_MANNERS = {"alliance": "in alliance", "threat": "with a threat", "bargain": "in bargaining"}
TOGETHER = " together with {partner}"
SUBTYPE_SUFFIX = " ({subtype})"
INSIDE_SUFFIX = ", inside {location}"
EFFECT_NOTE = "{label} {old} to {new}"
CO_CREATOR = "co-creator"
VESSEL_ROUTE = "{son}'s {vessel}"
TAUGHT_BY = "{son} inspired"
STRUCTURE_RAISED = "it stands as {kind:an}, working at {effect}%"
COMMISSIONED = "{site} began to raise {name}, {kind:an}, in your name"
BOND_DESCRIPTION = ": {description}"
CHOSEN_BOND = "chosen"
DREAM_BOND = "turned by a dream"
KNOWLEDGE_GIFT = "gift of knowledge"
TEACH_NOTE = "{son}: {how}"
EMPTY_BRANCHES = " or choose a branch nobody knows in this world: {branches}"
LOST_WORSHIPPER = "; {old} lost a worshipper"
SENSED = "; {old} sensed it"
MIRACLE_GROWTH = "{what} grew"
MIRACLE_HEALTH = "health restored"
MIRACLE_CURSE = "curse lifted"
MIRACLE_BOUNTY = "the land and stores filled"
MIRACLE_PEACE = "enmity ended ({count})"
MIRACLE_DEFENSE = "defence rose"
MIRACLE_SHIELD = "shielded from the next disaster"
MIRACLE_SENSES = "{names} came to their senses"
MIRACLE_WORSHIP = "{miracle} miracle"
MIRACLE_BOND = "{miracle}: {how}"
PEACE_REASON = "a miracle of peace"
TRANSFORM_NOTE = "{description}\n\n(Transformed in Age {epoch} by {son}. Previous form: {old}: {old_description})"
TRANSFORM_BOND = "transformed: {reason}"
RENAMED = "; its name is now {new}"
DESTROY_NOTE = "Age {epoch}: {son} destroyed it; {reason}"
SEALED = Line("tools.son.sealed", "{son} sealed {treaty}.")
BLOODLINE = Line("tools.son.bloodline", "{son} marked the blood of {house}: {trait}.")
TREATY_EVENT = "interworld treaty"
TREATY_LABELS = {"alliance": "an alliance", "trade": "trade"}
TALK_OUTCOMES = {
    ("alliance", True): "{god} extended a hand",
    ("alliance", False): "{god} did not trust",
    ("threat", True): "{god} withdrew",
    ("threat", False): "{god} answered the threat with hostility",
    ("bargain", True): "you came to terms with {god}; you gained {gain} essence",
    ("bargain", False): "{god} refused the bargain",
}
OPEN_RIFT = Line("tools.son.open_rift", "{son} opened a rift in {place} into {dimension}: {reason}")
SEAL_RIFT = Line("tools.son.seal_rift", "{son} sealed a rift: {reason}")
CALL_BEING = Line("tools.son.call_being", "{son} called {being}: {reason}")
BIND_BEING = Line("tools.son.bind_being", "{son} bound a cosmic being: {reason}")
BANISH_BEING = Line("tools.son.banish_being", "{son} banished a cosmic being: {reason}")
CONTAIN_PHENOMENON = Line("tools.son.contain_phenomenon", "{son} warded {phenomenon}: {reason}")
CREATE_GALAXY = Line("tools.son.create_galaxy", "{son} made a new galaxy, {galaxy}: {description}")
CREATE_CLUSTER = Line("tools.son.create_cluster", "{son} gathered a new cluster, {cluster}: {description}")
CREATE_DIMENSION = Line("tools.son.create_dimension", "{son} brought a new dimension into being, {dimension}: {description}")
SHAPE_STRUCTURE = Line("tools.son.shape_galactic_structure", "{son} shaped {structure} in {galaxy}: {reason}")
STIR_GALAXY = Line("tools.son.stir_galaxy", "{son} stirred {galaxy}: {reason}")
STIR_DIMENSION = Line("tools.son.stir_dimension", "{son} stirred {dimension}: {reason}")
BIND_DIMENSION_LAW = Line("tools.son.bind_law_across_dimension", "{son} made {law} hold across {dimension}: {reason}")
SET_COSMIC_FEATURE = Line("tools.son.set_cosmic_feature", "{son} set {feature} in the heavens: {reason}")
GATHER_STAR_SYSTEM = Line("tools.son.gather_star_system", "{son} gathered stars into {system}: {reason}")
RAISE_PHENOMENON = Line("tools.son.raise_phenomenon", "{son} raised {phenomenon} in {place}: {reason}")
OPEN_BREACH = Line("tools.son.open_breach", "{son} opened a breach for {being} in {place}: {reason}")
FORGE_LEY = Line("tools.son.forge_ley_line", "{son} forged a ley line between {first} and {second}: {reason}")
ADD_SEASON = Line("tools.son.add_season", "{son} added {season} to the year of {world}")
OPEN_ROAD = Line("tools.son.open_road", "{son} opened a road between {first} and {second}: {reason}")
RAISE_THRONE = Line("tools.son.raise_throne", "{son} raised a throne of power at {place}: {reason}")
LAY_MAGIC_SITE = Line("tools.son.lay_magic_site", "{son} laid a magic site at {place}: {reason}")
CARRY_SPECIES = Line("tools.son.carry_species", "{son} carried {kind} to {place}: {reason}")
SEED_LIFE = Line("tools.son.seed_life", "{son} let {life} take root on {world}: {reason}")
CALL_UP_SOUL = Line("tools.son.call_up_soul", "{son} called up the soul of {mortal}: {reason}")
CROWN_RULER = Line("tools.son.crown_ruler", "{son} crowned {ruler} over {community}: {reason}")
FOUND_HOUSE = Line("tools.son.found_house", "{son} founded {house} on {mortal}: {reason}")
BLESS_HOST = Line("tools.son.bless_host", "{son} strengthened the {aspect} of {army}: {reason}")
CLAIM_GALAXY = Line("tools.son.claim_galaxy", "{son} took {galaxy} under their patronage: {reason}")
RULE_DIMENSION = Line("tools.son.rule_dimension", "{son} took rule of {dimension}: {reason}")
CLAIM_STAR = Line("tools.son.claim_star", "{son} took {star} under their patronage: {reason}")
CALL_IMPACT = Line("tools.son.call_impact", "{son} called a body down upon {place}: {reason}")
DEFLECT_IMPACT = Line("tools.son.deflect_impact", "{son} turned a falling body aside from {world}: {reason}")
TERRAFORM_WORLD = Line("tools.son.terraform_world", "{son} began to reshape {world}: {reason}")
BREAK_MOON = Line("tools.son.break_moon", "{son} broke {moon} into a ring: {reason}")
STIR_CROWD = Line("tools.son.stir_crowd", "{son} stirred the folk of {town}: {reason}")
REVEAL_TRUE_HISTORY = Line("tools.son.reveal_true_history", "{son} brought an older account of {realm} to light: {reason}")
SET_STORYLET = Line("tools.son.set_storylet", "{son} set {title} in motion: {reason}")
ANSWER_OFFERINGS = Line("tools.son.answer_offerings", "{son} answered the offerings of {community}: {reason}")
BEGIN_LONG_PLAN = Line("tools.son.begin_long_plan", "{son} set a long plan in motion, {plan}: {reason}")
FURTHER_PLAN = Line("tools.son.further_plan", "{son} furthered {plan}: {reason}")
SHAPE_KINSHIP = Line("tools.son.shape_kinship", "{son} reshaped the ways of kin of {people}: {reason}")
SHAPE_REPRODUCTION = Line("tools.son.shape_reproduction", "{son} changed how {people} bear their young: {reason}")
TRY_REALM = Line("tools.son.try_realm", "{son} tried {realm} with {kind}: {reason}")
SET_CIRCUIT = Line("tools.son.set_circuit", "{son} set {circuit} turning: {reason}")
SHAPE_RULE = Line("tools.son.shape_rule", "{son} reshaped who chooses the rulers of {realm}: {reason}")
ANOINT_FOUNDER = Line("tools.son.anoint_founder", "{son} marked {ruler} as the founder of {realm}: {reason}")
FREE_LEARNING = Line("tools.son.free_learning", "{son} set the freedom of learning at {house}: {reason}")
INSPIRE_SCHOOL = Line("tools.son.inspire_school", "{son} moved {founder} to found {school}: {reason}")
DESIGNATE_KEYSTONE = Line("tools.son.designate_keystone", "{son} made {name} what the world depends on: {reason}")
INSPIRE_RELIEF = Line("tools.son.inspire_relief", "{son} moved {giver} to send aid to {town}: {reason}")
SHAPE_VEHICLE_TYPE = Line("tools.son.shape_vehicle_type", "{son} gave {owner} a vehicle type of its own: {name}.")
SHAPE_EQUIPMENT = Line("tools.son.shape_equipment", "{son} gave {owner} a model of its own: {name}.")
SHAPE_DISH = Line("tools.son.shape_dish", "{son} gave {owner} a dish of its own: {name}.")
SHAPE_STRUCTURE_TYPE = Line("tools.son.shape_structure_type", "{son} gave {owner} a building type of its own: {name}.")
STRIKE_BEING = Line("tools.son.strike_being", "{son} struck {being}: {reason}")
SEND_EXPEDITION = Line("tools.son.send_expedition", "{son} sent {leader} on an expedition to {target}: {reason}")
STOCK_DEPOT = Line("tools.son.stock_depot", "{son} moved {owner} to stock a depot in {land}: {reason}")
STEER_THEATRE = Line("tools.son.steer_theatre", "{son} steered the reserves of {owner} to one front, {priority} in a hundred: {reason}")
MARK_QUIRK = Line("tools.son.mark_quirk", "{son} left {mortal} with a quirk, {quirk}: {reason}")
LIMIT_FLEETS = Line("tools.son.limit_fleets", "{son} bound {first} and {second} to a naval treaty: {reason}")
BIND_GENIUS_LOCUS = Line("tools.son.bind_genius_locus", "{son} raised a spirit to dwell in {place}: {reason}")
JUDGE_PETITION = Line("tools.son.judge_petition", "{son} judged a petition before {office}, and it was {verdict}: {reason}")
APPOINT_SPIRIT = Line("tools.son.appoint_spirit", "{son} saw {spirit} {standing}: {reason}")
ANSWER_MYSTIC = Line("tools.son.answer_mystic", "{son} answered {mortal} in a vision: {reason}")
EASE_THEODICY = Line("tools.son.ease_theodicy", "{son} answered the suffering of {town}: {reason}")
TEACH_SACRAMENT = Line("tools.son.teach_sacrament", "{son} taught {cult} the {sacrament}: {reason}")
ALIGN_AFTERLIFE = Line("tools.son.align_afterlife", "{son} made the afterlife match what {cult} teaches, the {model}: {reason}")
SWAY_DIVINER = Line("tools.son.sway_diviner", "{son} swayed the diviners of {realm} to read an {verdict} omen: {reason}")
GRANT_FORESIGHT = Line("tools.son.grant_foresight", "{son} showed {mortal} the likely future of {subject}: {reason}")
FEED_ON = Line("tools.son.feed_on", "{son} turned to feed on {emotion}: {reason}")
BUILD_CONSTRUCT = Line("tools.son.build_construct", "{son} moved {maker} to build {name}: {reason}")
ORDER_CONSTRUCT = Line("tools.son.order_construct", "{son} gave {name} the order to {order}: {reason}")
SEIZE_CONSTRUCT = Line("tools.son.seize_construct", "{son} took command of {name}: {reason}")
EXPOSE_FORGERY = Line("tools.son.expose_forgery", "{son} showed {item} to be a forgery: {reason}")
CANONISE_WORK = Line("tools.son.canonise_work", "{son} set {work} into the canon of {people}: {reason}")
INSPIRE_MOVEMENT = Line("tools.son.inspire_movement", "{son} moved the makers of {town} to band into {name}: {reason}")
RIG_MATCH = Line("tools.son.rig_match", "{son} gave the match to {winner}: {reason}")
SET_BEAST_BOUNTY = Line("tools.son.set_beast_bounty", "{son} moved {town} to post a bounty on {beast}: {reason}")
MARK_BIRTH = Line("tools.son.mark_birth", "{son} marked {mortal} with {sign}: {reason}")
UNSETTLE_SEASONS = Line("tools.son.unsettle_seasons", "{son} unsettled the seasons of {world}: {reason}")
NUDGE_BIAS = Line("tools.son.nudge_bias", "{son} swayed the {bias} of {mortal}: {reason}")
DECLARE_IMPURITY = Line("tools.son.declare_impurity", "{son} made the {people} count {source} impure: {reason}")
BLESS_CHARM = Line("tools.son.bless_charm", "{son} made {item} a true charm of {power}: {reason}")
SEND_MISFORTUNE = Line("tools.son.send_misfortune", "{son} sent a misfortune ({kind}) on {town}: {reason}")
STIR_REVIVAL = Line("tools.son.stir_revival", "{son} stirred a movement among the {people} to {goal}: {reason}")
PROCLAIM_RIGHT = Line("tools.son.proclaim_right", "{son} proclaimed in {realm} the right of {right}: {reason}")
WAKE_SPIRIT = Line("tools.son.wake_spirit", "{son} gave {emotion} a spirit's shape in {region}: {reason}")
LAY_AFFINITY = Line("tools.son.lay_affinity", "{son} laid an affinity for {school} into the material of {resource}: {reason}")
STIR_MONSOON = Line("tools.son.stir_monsoon", "{son} brought {told} over {world}: {reason}")
TURN_WIND = Line("tools.son.turn_wind", "{son} turned the wind of {region} to blow from the {direction}: {reason}")
STIR_WITCH_HUNT = Line("tools.son.stir_witch_hunt", "{son} stirred a witch hunt in {town}: {reason}")
LENGTHEN_WINTER = Line("tools.son.lengthen_winter", "{son} lengthened the long winter of {world}: {reason}")
PRESS_TALE = Line("tools.son.press_tale", "{son} pressed the tale of {tale} of {subject}: {reason}")
FORESHADOW = Line("tools.son.foreshadow", "{son} set something up about {subject}: {reason}")
ECHO_LIFE = Line("tools.son.echo_life", "{son} marked the life of {mortal} to echo into the next age: {reason}")

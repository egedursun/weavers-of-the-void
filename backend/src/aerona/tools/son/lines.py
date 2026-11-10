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
TOUCH_MORTAL = Line("tools.son.touch_mortal", "The touch of {son} fell on {mortal} ({touch}): {reason}")
WORDS = Line("tools.son.words", "{son} whispered new words into the {language} tongue: {words}.")
TENET = Line("tools.son.tenet", "{son} revealed a new tenet to {cult}: {tenet}.")
REBORN = Line("tools.son.reborn", "{son} opened the gate of rebirth; the soul of {spirit} was born again as {child}.")
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
    "{son} created the first people of the {world} world: {name}. They will be remembered as the god who breathed life into an empty world.",
)
HARVEST = Line("tools.son.harvest", "{son} drew {gain} essence from {resource}; the resource's abundance fell to {abundance}.")
COSMIC_BED = Line("tools.son.cosmic_bed", "{son} opened {bed} in {region}: {reason}")
AFFECT = Line("tools.son.affect", "{son} passed their hand over {entity}: {changes}. ({reason})")
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
SHAPE_IMAGE = Line("tools.son.shape_image", "{son} chose to {stance} the image its peoples hold of it: {reason}")
LOOSE_DISEASE = Line("tools.son.loose_disease", "{son} loosed a sickness of its own making, {disease}, upon {target}: {reason}")
SHAPE_FOLK = Line("tools.son.shape_folk", "{son} taught {people} new ways: {changes}. {reason}")
FORGE_MATERIAL = Line("tools.son.forge_material", "{son} forged {name} into the world: {reason}")
RESHAPE_LAND = Line("tools.son.reshape_land", "{son} laid a hand on {region} and {act}: {reason}")
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
    ("threat", True): "{god} withdrew but will hold a grudge",
    ("threat", False): "{god} answered the threat with fury",
    ("bargain", True): "you came to terms with {god}; you gained {gain} essence",
    ("bargain", False): "{god} refused the bargain",
}
OPEN_RIFT = Line("tools.son.open_rift", "{son} tore a rift in {place} into {dimension}: {reason}")
SEAL_RIFT = Line("tools.son.seal_rift", "{son} sealed a rift: {reason}")
CALL_BEING = Line("tools.son.call_being", "{son} called {being}: {reason}")
BIND_BEING = Line("tools.son.bind_being", "{son} bound a cosmic being: {reason}")
BANISH_BEING = Line("tools.son.banish_being", "{son} banished a cosmic being: {reason}")
CONTAIN_PHENOMENON = Line("tools.son.contain_phenomenon", "{son} warded {phenomenon}: {reason}")
CLAIM_GALAXY = Line("tools.son.claim_galaxy", "{son} took {galaxy} under their patronage: {reason}")
RULE_DIMENSION = Line("tools.son.rule_dimension", "{son} took rule of {dimension}: {reason}")
CLAIM_STAR = Line("tools.son.claim_star", "{son} took {star} under their patronage: {reason}")
CALL_IMPACT = Line("tools.son.call_impact", "{son} called a body down upon {place}: {reason}")
DEFLECT_IMPACT = Line("tools.son.deflect_impact", "{son} turned a falling body aside from {world}: {reason}")
TERRAFORM_WORLD = Line("tools.son.terraform_world", "{son} began to reshape {world}: {reason}")
BREAK_MOON = Line("tools.son.break_moon", "{son} broke {moon} into a ring: {reason}")

from aerona.catalog.god_lines import Line

LEVEL_UP = Line("tools.son.level_up", "{son} grew stronger and rose to rank {level}.")
POWER_AWOKE = Line("tools.son.power_awoke", "A new power awoke within {son}: {power}.")
ANCHOR = Line("tools.son.anchor", "{son} bound their existence to {entity}: {reason}")
WORDS = Line("tools.son.words", "{son} whispered new words into the {language} tongue: {words}.")
MESSAGE = Line("tools.son.message", '{son} {phrase} to {sibling}: "{message}"')
COVENANT = Line("tools.son.covenant", '{son} and {sibling} swore a covenant: "{terms}"')
COVENANT_BROKEN = Line("tools.son.covenant_broken", "{son} thereby broke the covenant with {sibling}.")
GIFT_REFUSED = Line("tools.son.gift_refused", "{community} refused {son}'s transfer of it to {sibling}; it stayed loyal to its old god.")
GIFT_BOND = "{son}'s gift"
GIFT = Line("tools.son.gift", '{son} gave {sibling} a gift: {notes}. "{words}"')
PRAYER = Line("tools.son.prayer", '{son} prayed to their father{request}: "{message}"')
BOND = Line("tools.son.bond", "{son} wove a bond: {source} {relation} {target}{description}.")
CREATED = Line("tools.son.created", "{son}{partner} created a {type}: {name}{subtype}{location}.{effects}")
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
ADVANCE_KNOWLEDGE = Line("tools.son.advance_knowledge", "{son} deepened the knowledge of {knowledge} (level {level}): {how}")
MIRACLE = Line("tools.son.miracle", "{son} sent down a {miracle} miracle upon {target}: {how}{notes}")
DISASTER = Line("tools.son.disaster", "{son} sent {disaster} upon {target}: {name}. ({reason}){notes}")
TRANSFORM = Line("tools.son.transform", "{son} transformed {old}{renamed}. ({reason})")
DESTROY = Line("tools.son.destroy", "{son} destroyed {name}. ({reason})")
INCITE = Line("tools.son.incite", "{son} sowed hostility between {first} and {second}: {pretext}")
TREATY = Line(
    "tools.son.treaty",
    "{son} established an interworld {treaty} treaty between {first} in the {first_world} world and {second} in the {second_world} world: {terms}",
)
FOREIGN_TALK = Line("tools.son.foreign_talk", '{son} spoke with the foreign god {god} {manner}: "{words}" ({outcome}).')
MOVE = Line("tools.son.move", "{son} turned from {old} to {new}.")
SEVER_LEY = Line("tools.son.sever_ley", "{son} cut the ley line between {first} and {second}: {reason}")
LOOSE_DISEASE = Line("tools.son.loose_disease", "{son} loosed a sickness of its own making, {disease}, upon {target}: {reason}")
SHAPE_WEATHER = Line("tools.son.shape_weather", "{son} held {weather} over {region} for {epochs} ages: {reason}.")
RAISE_DISTRICT = Line("tools.son.raise_district", "{son} raised a {district} in {town}: {reason}")
DESIGN_DISTRICT = Line("tools.son.design_district", "{son} devised the {design}, a new kind of {base} for the cities of the world.")
REORDER_SEASONS = Line("tools.son.reorder_seasons", "{son} turned the year of {world}: its seasons now run {order}.")
SEAL = Line("tools.son.seal", "{son} sealed the road between {first} and {second}; the two worlds' leakage decreased.")
STITCH = Line("tools.son.stitch", "{son} stitched the tear of the {world} world ({how}); leakage {old} to {new}.")
OUTER_BARGAIN = Line("tools.son.outer_bargain", "{son} bargained with the nameless thing. Their siblings saw another shadow over them.")
OUTER_THREAD = Line(
    "tools.son.outer_thread",
    "{son} bargained with the thing outside ({request}). Nobody knows what they gave in return; but one day it will be paid.",
)
SPIRIT_BOUND = Line("tools.son.spirit_bound", "{son} bound {spirit} to {target}{golem}.")
GOLEM_SUFFIX = "; the stone began to walk"
WORLD_BORN = Line("tools.son.world_born", "{son} gave birth to the world {world}.")
CHILD_BORN = Line("tools.son.child_born", "{son} gave birth to {child}.")

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
TREATY_BOND = "interworld treaty ({son}): {terms}"
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

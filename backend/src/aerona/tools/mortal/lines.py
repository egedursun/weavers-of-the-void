from aerona.catalog.god_lines import Line

LANGUAGE_BORN = Line("tools.mortal.language_born", "{me} gave birth to its own language: {name}. Its first words: {words}.")
WORDS = Line("tools.mortal.words", "New words were born among {me} ({language}): {words}.")
PRODUCED = Line("tools.mortal.produced", "{me}, using {resources}, produced {name} ({category}; {quality}).")
BUILT = Line("tools.mortal.built", "{me} built {name} in {location}{subtype}{dedication}.")
CULTURE = Line("tools.mortal.culture", "A new {kind} was born among {me}: {name}.")
DISCOVERED = Line("tools.mortal.discovered", "{me} discovered {name} in {location}{subtype}.")
CLAIMED = Line("tools.mortal.claimed", "{me} claimed {resource}{angered}.")
SEIZE_REPELLED = Line("tools.mortal.seize_repelled", "{me} tried to seize {resource}, but {owners} drove them back.")
MIGRATED = Line("tools.mortal.migrated", "{count} people from among {me} migrated and founded {name} in {location}.")
TRADE = Line("tools.mortal.trade", "Trade began between {me} and {target}: {goods}.")
WAR = Line("tools.mortal.war", "{me} declared war on {target}: {reason}")
WORSHIP_CREATOR = Line("tools.mortal.worship_creator", "{me} began to worship the creator {creator} directly: {offering}")
WORSHIP = Line("tools.mortal.worship", "{me} worshipped {son}{abandoned}: {offering}")
KNOWLEDGE = Line("tools.mortal.knowledge", "{me} developed new knowledge: {name} ({branch}, level {level}).")
LEARNED = Line("tools.mortal.learned", "{me} learned {knowledge} from {teacher}.")
KNOWLEDGE_DEEPENED = Line("tools.mortal.knowledge_deepened", "{me} deepened the knowledge of {name} ({branch}, level {level}).")
KNOWLEDGE_FOUND = Line("tools.mortal.knowledge_found", "{me} reached the knowledge of {name} by its own road ({branch}).")
RESEARCH_CHOSEN = Line("tools.mortal.research_chosen", "{me} set the scholars of {place} to work on {technique}.")
DIPLOMACY = Line("tools.mortal.diplomacy", "{me} offered {offer} to {target}: {outcome}.")
HUNT = Line("tools.mortal.hunt", "{me} set out to hunt {species}: {goal}")
SEIZED = Line("tools.mortal.seized", "{me} seized {item}{owner}: {goal}")
SEIZE_FAILED = Line("tools.mortal.seize_failed", "{me} tried to seize {item} but was wounded and fled.")
ROUTE_FOUND = Line("tools.mortal.route_found", "{me} found a way to the world {world}: {method} ({epochs} ages).")
ROUTE_SENSED = Line("tools.mortal.route_sensed", "{me} sensed a world no one knew, somewhere beyond the sky ({how}).")
ROUTE_NOT_FOUND = Line("tools.mortal.route_not_found", "{me} searched for the way to other worlds ({how}) but did not find it.")
EXPLORE_FAILED = Line("tools.mortal.explore_failed", "{me} set out into unknown lands but the road turned them back empty-handed.")
EXPLORED = Line("tools.mortal.explored", "{me} set out into unknown lands and found {found}: {name}{pioneers}.")
SHIP = Line("tools.mortal.ship", "{me} built an inter-world ship: {name}.")
EXPEDITION = Line(
    "tools.mortal.expedition", "{me} set out on {intent:an} expedition to the world {world} ({count} people{vessel}, it will take {epochs} ages)."
)
TAMED = Line("tools.mortal.tamed", "{me} tamed {species} ({how}).")
TAME_FAILED = Line("tools.mortal.tame_failed", "{me} tried to tame {species} but failed.")
CHIMERA = Line("tools.mortal.chimera", "{me} merged {first} and {second} into a chimera: {chimera}.")
RUIN_KNOWLEDGE = Line("tools.mortal.ruin_knowledge", "{me} rediscovered the forgotten knowledge {knowledge} in the ruins of {ruin}.")
RUIN_ITEM = Line("tools.mortal.ruin_item", "{me} found and took {item} in the ruins of {ruin}.")
RUIN_CURSE = Line("tools.mortal.ruin_curse", "{me} awakened something sleeping while digging the ruins of {ruin}; a curse settled upon it.")
RUIN_NOTHING = Line("tools.mortal.ruin_nothing", "{me} searched the ruins of {ruin} but found nothing but dust, bone and whisper.")
SABOTAGE_CAUGHT = Line("tools.mortal.sabotage_caught", "{me} plotted {kind} against {target} and was caught: {note}.")
SABOTAGE_HIDDEN = Line("tools.mortal.sabotage_hidden", "A mysterious {kind} happened within {target}.")
PREACHED = Line("tools.mortal.preached", '{me} preached and {target} turned to {god}{lost}: "{sermon}"')
PREACH_FAILED = Line("tools.mortal.preach_failed", "{me} preached among {target} but no one listened.")
GODSLAYER = Line("tools.mortal.godslayer", "The mortal {me} killed the fading god {son} ({mine}-{theirs}): {reason}")
GOD_WOUNDED = Line("tools.mortal.god_wounded", "The mortal {me} stood up to the god {son} and wounded them ({mine}-{theirs}): {reason}")
DEFIER_DIED = Line("tools.mortal.defier_died", "The mortal {me} stood up to the god {son} and died: {reason}")
DEFIER_CURSED = Line("tools.mortal.defier_cursed", "The mortal {me} stood up to the god {son}; was defeated and cursed: {reason}")
DENIED = Line("tools.mortal.denied", "{me} denied {god} and became godless: {reason}")
PRAYED = Line("tools.mortal.prayed", '{me} prayed to the creator{request}: "{prayer}"')
PROPHESIED = Line("tools.mortal.prophesied", "{me} made a prophecy: {name}.")
ESCAPED = Line("tools.mortal.escaped", "{me} escaped from {captor}: {how}")
ESCAPE_FAILED = Line("tools.mortal.escape_failed", "{me} tried to escape from {captor} but was caught.")
RANSOMED = Line("tools.mortal.ransomed", "{me} paid a ransom to {captor} for {captive}; the captive returned home.")
RESCUED = Line("tools.mortal.rescued", "{me} rescued {captive} from {captor}: {plan}")
RESCUE_FAILED = Line("tools.mortal.rescue_failed", "{me} tried to rescue {captive} but {captor} repelled the raid.")
ARMY = Line("tools.mortal.army", "{me} called {count} people to arms: {name}.")
COMMANDER = Line("tools.mortal.commander", "{mortal} took command of {army}.")
SPIES = Line("tools.mortal.spies", "Strange faces appeared among {target} ({cover}).")
BARTER_REFUSED = Line("tools.mortal.barter_refused", "{me} asked {target} for {take} in exchange for {give}; {target} found the offer too little.")
BARTERED = Line("tools.mortal.bartered", "{me} and {target} bartered: {give} for {take} ({terms}).")
GIFTED = Line("tools.mortal.gifted", "{me} gave {give} to {target} as a gift ({terms}).")
LENT = Line("tools.mortal.lent", "{me} lent {amount} {what} to {debtor}; due Age {due}.")
REPAID = Line("tools.mortal.repaid", "{me} repaid its debt ({amount} {what}) to {creditor}{late}.")
ADOPTED = Line("tools.mortal.adopted", "{me} adopted {child}: {reason}")

DIALECT_SUBTYPE = "{parent} dialect{suffix}"
DIALECT_BOND = "dialect"
ITEM_SUBTYPE = "{label}: {subtype}"
DIALECT_SUFFIX = ": {subtype}"
SUBTYPE_SUFFIX = " ({subtype})"
DEDICATION = "; dedicated to {son}"
OFFERING = "offering"
ANGERED = "; {owners} were angered by it"
SEIZED_NOTE = "{me} seized it (Age {epoch})"
CONFISCATION = "because of {resource}"
SEIZE_ATTEMPT = "attempt to seize {resource}"
MIGRANTS = "{count} people"
TELLS_OF_GOD = "tells of its god"
SUBJECT_OF = "subject of the {kind}"
DISCOVERED_BOND = "discovered"
ABANDONED = "; abandoned {old}"
BUILT_UPON = "built upon"
DEVELOPED = "developed"
LEARNED_FROM = "learned from {teacher}"
FOUND_ALONE = "found by itself"
EMPTY_BRANCHES = ": branches nobody knows in this world are {branches}"
ITEM_OWNER = " from {owner}"
SEIZE_BOND = "seized: {goal}"
STOLEN = "{item} was stolen"
GATE_NAME = "{me} Gate"
GATE_SUBTYPE = "ancient gate"
NEW_REGION = "a new region not on the map"
NEW_PLACE = "a new place in {parent}"
PIONEERS = "; its pioneers founded {settlement} there"
SHIP_SUBTYPE = "ship{suffix}"
SHIPYARD = "built in its shipyard"
WITH_VESSEL = ", with {vessel}"
ENRAGED = "enraged by the taming"
WOVEN = "made by itself"
CHIMERA_DESCRIPTION = "{me} joined {first} with {second} by biomancy: {goal}"
RUIN_FOUND = "found in the ruins of {ruin}"
CAUGHT_SUFFIX = "; and you were caught"
SABOTAGE_BOND = "{kind} caught"
POISON_DEATH = "died of poisoning"
SERMON_BOND = "by {me}'s sermon"
LOST_WORSHIPPER = "; {names} lost a worshipper"
GODSLAYER_TITLE = "God-slayer"
WOUNDER_TITLE = "Wounder of {son}"
DEFEAT_BOND = "defeat: {reason}"
INSOLENCE = "for its insolence"
DEFIANCE_DEATH = "Age {epoch}: stood up to {son} and died."
DENIAL_BOND = "denial: {reason}"
THE_GODS = "the gods"
PROPHECY_TEXT = '{me} said: "{saying}"{concerns} If it comes true {me}\'s word will pass from tongue to tongue; if it comes to nothing its name will be shaken.'
PROPHECY_CONCERNS = " The saying concerns {names}."
PROPHECY_BOND = "subject of the prophecy"
RAID_BOND = "raid for {captive}"
COMMANDS = "commands"
ADOPTION_BOND = "adopted: {reason}"
ADOPTION_EVENT = "adoption"
SLAIN_BY = "killed by the mortal {me}"
BARTER_BOND = "barter: {terms}"
DEBT_TEXT = "{amount} {what}; due Age {due}"
LATE = " although it was overdue"
INSOLENT_TRIBUTE = "insolence of tribute"
UNION_BOND = "{kind}: {terms}"
SABOTAGE_KINDS = {"poison": "poisoning", "arson": "fire", "discord": "split"}
CULTURE_KINDS = {"tradition": "tradition", "legend": "legend", "artwork": "work of art", "law": "law"}
QUALITY = {"masterwork": "masterwork", "sturdy": "sturdy", "crude": "crude"}
DIPLOMACY_OUTCOMES = {
    "accepted": "{target} accepted",
    "refused": "{target} refused",
    "peace": "peace was made",
    "no_peace": "the peace offer was turned down",
    "laughed": "{target} laughed and became your enemy",
    "tribute": "{target} agreed to pay tribute",
}
ARMY_ORIGINS = {
    "population": "The soldiers were taken from {me}'s own people, from field and workbench.",
    "followers": "Disciples fill the ranks; bound by oath before the sword.",
    "mercenary": "The soldiers are mercenaries; {me} hired them with its wealth.",
}
ARMY_TEXT = "{me} raised an army of {count}{war}. {origin} {state}"
ARMY_WAR = "; it marches for {war}"
ARMY_STATE = "The army is {equipment}, its morale {morale}{veterans}."
ARMY_EQUIPPED = {True: "well-equipped", False: "poorly equipped"}
ARMY_MORALE = {True: "high", False: "broken"}
ARMY_VETERANS = "; those who know war lead it"
PRAYER_REQUEST = " and asked: {request}"
PROPHECY_SUBTYPES = {"cult": "cult prophecy", "mortal": "seer's word"}
SPIES_CAUGHT = Line("tools.mortal.spies_caught", "The spies of {me} were caught among {target}; the network was broken.")
SPIES_CAUGHT_EVENT = "caught spies"

LAW_LAID = Line("tools.mortal.law_laid", "{me} laid down {law} for {realm}.")
HOME_TENDED = Line("tools.mortal.home_tended", "{me} decided for {household}: {deed}.")
SCHEME_BEGUN = Line("tools.mortal.scheme_begun", "{me} began to plot {scheme:an}.")
LEVERAGE_PRESSED = Line("tools.mortal.leverage_pressed", "{me} leaned on {target}: {deed}.")
DISPATCH_SENT = Line("tools.mortal.dispatch_sent", "{me} sent {deed} to {target}.")
TITLE_SEIZED = Line("tools.mortal.title_seized", "{me} {deed} {title}.")
ESTATE_BARGAIN = Line("tools.mortal.estate_bargain", "{me} {deed} {privilege} for the {estate}.")
LAW_PROPOSED = Line("tools.mortal.law_proposed", "{me} brought {law} before {realm}.")
ACCUSATION = Line("tools.mortal.accusation", "{me} accused {accused} of {crime}.")
DEMAND = Line("tools.mortal.demand", "{me} demanded that {realm} {demand}.")
BACKED = Line("tools.mortal.backed", "{me} backed the {side} in a crisis.")
MANDATE = Line("tools.mortal.mandate", "{me} issued {kind:an} mandate in {realm}.")
TASK = Line("tools.mortal.task", "{me} set the {office} to {task}.")
METHOD_CHOSEN = Line("tools.mortal.method_chosen", "{me} took up {method} for {process}.")
WORKSHOP_BOUGHT = Line("tools.mortal.workshop_bought", "{me} bought the {workshop} of {place} for {price}.")
POLICY_LAID = Line("tools.mortal.policy_laid", "{me} laid down this {policy} on {good}.")
HOARD_OPENED = Line("tools.mortal.hoard_opened", "{me} bought up {good} in {place} and held it back.")

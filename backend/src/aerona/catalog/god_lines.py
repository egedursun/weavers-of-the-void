from dataclasses import dataclass


@dataclass(frozen=True)
class Line:
    key: str
    text: str

    def render(self, **fields: object) -> str:
        return self.text.format(**fields)


def _lines(prefix: str, *texts: str) -> tuple[Line, ...]:
    return tuple(Line(f"{prefix}.{index + 1}", text) for index, text in enumerate(texts))


WRATH_SIGNS = _lines(
    "gods.mood.wrath",
    "{creator}'s anger overflowed: {disaster} fell upon {place}. The sky darkened before anyone could pray.",
    "The people of {place} had forgotten to look to the sky; {creator} reminded them. His anger fell as {disaster}.",
    "The sky split above {place}: {creator}'s patience ran out, and {disaster} followed.",
    "{creator} turned to {place} in an angry silence; {disaster} broke that silence.",
)
GRACE_SIGNS = _lines(
    "gods.mood.grace",
    "{creator} is content: the creator's grace descended upon {place}; granaries filled, children were born laughing.",
    "The fields of {place} came into ear overnight; the elders said it was {creator}'s smile.",
    "{creator} looked kindly on {place}: wells overflowed, the sick rose up, and no one asked why.",
    "A warm rain fell over {place}; {creator}'s contentment seeped into the soil.",
)
SILENCE_SIGNS = _lines(
    "gods.mood.silence",
    "{creator} fell silent. For an entire epoch the sky gave no answer; his sons whisper, 'our father has forgotten us.'",
    "Prayers rose to the sky and never came back: {creator} did not speak at all this epoch.",
    "{creator}'s voice has not been heard for an epoch; in the temples the lamps go out by themselves.",
)
LONELINESS_SIGNS = _lines(
    "gods.mood.loneliness",
    "{creator}'s loneliness seeped into {mortal}'s dream.",
    "One night {mortal} heard their own name being called; they did not know the voice, but it was {creator}'s loneliness.",
    "{creator} searched for someone and found {mortal}: in a dream the sky told them its name.",
)
LONELY_DREAM = Line("gods.mood.lonely_dream", "The creator is lonely. No one in the heavens speaks his name; he is calling you.")
ESTRANGED_TURN = Line("gods.mood.estranged_turn", "{entity} turned its face from its sons and began worshipping the creator {creator} directly.")
ESTRANGED_VOW = "turned from the sons to the creator"

DRAIN_SON = _lines(
    "gods.power.drain",
    "{creator}, {anger}{again}drained {son}'s essence: {drawn} essence was drawn, {gained} of it passed to the creator. {son} withered{witness}.",
    "{creator} {anger}laid a hand on {son} and {again}drained his essence ({drawn} essence; {gained} passed to the creator). "
    "{son}'s light went out for a moment{witness}.",
    "{creator} {anger}{again}drained {son}'s essence in one breath: {drawn} essence lost, {gained} returned to the father.{witness}",
    "{creator}, {anger}{again}drained {son}'s essence and took {gained} into his own ({drawn} essence drawn). {son} was shaken{witness}.",
)
DRAIN_WITNESSES = (
    "; his brothers watched in fear",
    "; the other sons fell silent",
    " His brothers understood their turn might come too.",
    "; no one in the pantheon raised a voice",
)
DRAIN_ANGER = "his anger overflowing, "
DRAIN_AGAIN = "again "
DRAIN_REPEAT_SUFFIX = " (the {count} time this epoch)."
DEVOUR_SON = Line("gods.power.devour", "{creator} devoured his son {son}; all his essence and might returned to the creator ({gained} essence).")
DEVOUR_CAUSE = "{creator} devoured him"
DRAIN_MORTAL = Line("gods.power.drain_mortal", "{creator} drew {drawn} of {mortal}'s life; {mortal} lives but is hollow inside ({gained} essence).")
DEVOUR_MORTAL = Line("gods.power.devour_mortal", "{creator} devoured {mortal}'s life and soul ({gained} essence).")
DEVOUR_MORTAL_HOW = "life and soul devoured by the creator"
HARVEST = Line("gods.power.harvest", "{creator} harvested the faith of {community}{victims}{faith} ({gained} essence).{grudge}")
FOREIGN_DRAIN = Line("gods.power.foreign_drain", "{creator} drained {drawn} of the foreign god {god}'s power ({gained} essence){defeated}.")
FOREIGN_KILL = Line(
    "gods.power.foreign_kill",
    "{creator} {verb} the foreign god {god}{reason}{gain}. {converted} of its worshippers turned to the creator, {godless} were left godless.",
)
FOREIGN_CONVERT_VOW = "{god} died and it turned to the creator"
RESURRECT_MORTAL = Line("gods.power.resurrect_mortal", "{creator} called {mortal} back from death. Having seen the other side, they walk again.")
RESURRECT_MORTAL_NOTE = " Epoch {epoch}: {creator} called them back from death."
DEMOTE = Line("gods.power.demote", "{creator} demoted {son} from {old} class to {new} class. Their might narrowed; a grudge remained inside.")
STRIP_POWER = Line("gods.power.strip", '{creator} tore away {son}\'s power "{power}" ({gained} essence returned to the creator).')
ABSOLUTE_COMMAND = Line("gods.power.absolute_command", '{creator} gave {son} an irrefusable command: "{command}"')
PROPHET = Line("gods.power.prophet", "{creator}{content} chose {mortal} as his prophet{community}.")
PROPHET_VOW = "became his prophet"
PROPHET_CONTENT = ", contentment overflowing,"
MANIFEST = Line("gods.power.manifest", '{creator} appeared to {entity} while awake and spoke: "{words}"{worship}')
MANIFEST_VOW = "saw the creator with their own eyes"
BLOODLINE_CURSE = Line(
    "gods.power.bloodline_curse",
    "{creator}, {reason}cursed {root}'s bloodline: {count} living descendants fell under the curse; those yet to be born will carry it too.",
)
BLOODLINE_LIFT = Line("gods.power.bloodline_lift", "{creator} lifted the curse from {root}'s bloodline ({count} people).")
BLOODLINE_NEWBORNS = Line("gods.power.bloodline_newborns", "The bloodline curse passed to {count} newborns: {names}.")
PROPHET_COMMUNITY = Line("gods.power.prophet_community", "{community} began worshipping the creator {creator} by the word of the prophet {prophet}.")
PROPHET_COMMUNITY_VOW = "by the word of the prophet {prophet}"
CONVERT = Line("gods.power.convert", "{creator} turned {entity} to himself{old}. It now worships the creator directly.")
CONVERT_VOW = "{creator} turned them to himself"
WRATH = Line("gods.power.wrath", "{creator} destroyed {entity} with his wrath{reason}{deaths}.")
WRATH_NOTE = "Epoch {epoch}: destroyed by {creator}'s wrath{reason}."
WRATH_HOW = "together with {entity}"
WORLD_WRATH = Line("gods.power.world_wrath", "{creator} sent {disaster} upon all of {world}: all {count} regions were shaken.")
REBELLION = Line("gods.power.rebellion_declared", "{son} rebelled against his father {creator}: {manifesto}")
REBELLION_SPONTANEOUS_MANIFESTO = (
    "his loyalty exhausted and his anger overflowing; no one heard a declaration, only his father's name was erased from his altars."
)
REBELLION_ENDED = Line(
    "gods.power.rebellion_ended", "{son}'s rebellion died out: his loyalty returned and he again recognized his father {creator}'s commands."
)
CURSE_REASON_BLOODY_HAND = "{victim}'s blood did not stay on the ground"
CURSE_REASON_TEMPLE = "{creator} did not forget the hand that tore down {place}"
CURSE_REASON_CURSED = "anger overflowing, he cursed the blood of the cursed too"
CURSE_REASON_KILLER = "the hand that took {count} lives became the target of his anger"

REPUTATION_CHANGE = Line("gods.reputation.change", "{son} now sees his father as a {label} god.")
PASSIONS_REVEALED = Line("gods.reputation.passions", "{creator} revealed himself: his passions are {passions}.")

GOAL_SET = Line("gods.goals.set", "{creator} set himself a goal: {name}.")
GOAL_ACHIEVED = Line("gods.goals.achieved", "Goal achieved: {name}.")
GOAL_LOST = Line("gods.goals.lost", "Goal lost: {name}. {detail}")
ACHIEVEMENT_TITLE = "Achievement: {name}"

GOD_DEATH = Line(
    "gods.death.god_death",
    "{creator}'s son {son} died ({cause}). Their body became {corpse}; {apostates} of their worshippers fell into denial, {loyal} await their resurrection.",
)
GOD_DEATH_FADED = "faded away, forgotten"
GOD_DEATH_KILLED = "killed by {creator}'s hand"
CORPSE_NAME = "Bones of {son}"
CORPSE_DESCRIPTION = "{son}, {title}, died ({cause}). Their body fell {where} and became a place; {domain_1} and {domain_2} still seep from it."
CORPSE_WHERE_LAND = "onto the lands of {home}"
CORPSE_WHERE_WORLD = "to the world"
SHADE_NAME = "Shade of {son}"
SHADE_DESCRIPTION = "The shade of the dead god {son} wanders above their bones."
ORDER_NAME = "Those Who Await {son}'s Return"
ORDER_DESCRIPTION = "Those who stayed loyal to {son} gathered at their bones; they believe the god will return."
ORDER_REBORN_DESCRIPTION = "{source} gathered again for {son}'s return."
ORDER_REBORN_SOURCE = "A handful of believers who had not forgotten the name"
ORDER_WORSHIP = "to the dead god"
DEATH_THREAD = "{son} died; their bones lie in {where}. The loyal await the resurrection. Who will call them back, who will scatter the bones?"
DEATH_THREAD_WORLD = "the world"
CORPSE_BOND = "corpse"
SHADE_BOND = "shade"
SON_RESURRECTED = Line(
    "gods.death.son_resurrected",
    "{son} was reborn from where they died ({path}){tomb}. The mark of death is on them: their power slightly diminished, but now they know what death is.",
)
EMPTY_TOMB_CLAUSE = "; {corpse} is now an empty tomb"
RESURRECTION_BY_RITE = "by the rite of {order}"
RESURRECTION_BY_CREATOR = "by {creator}'s hand"
FADING_TWO = Line(
    "gods.death.fading_two", "{son} is nearly forgotten; their name lingers in only a few mouths. If two more epochs pass like this, they will fade."
)
FADING_ONE = Line("gods.death.fading_one", "{son}'s voice is no longer heard even in dreams; if they are forgotten one more epoch, they will fade.")
FADING_MANY = Line(
    "gods.death.fading_many", "{son} is nearly forgotten; their name lingers in only a few mouths. If {left} more epochs pass like this, they will fade."
)

KILL_REASON = "life taken by the hand of {killer}{how}"
KILL_IMMORTAL = Line("gods.death.kill_immortal", "{victim} is immortal; death does not touch them.")
KILL_FAILED = Line("gods.death.kill_failed", "{killer} sought to take {victim}'s life but it did not hold: {story}.")
KILL_DIED = Line("gods.death.kill_died", "{victim} died: {reason}.")
KILL_RELATION_NOTE = "took {victim}'s life"
KILL_PROTECT_NOTE = "protected {victim}"
LEGEND_NAME = "{victim}'s Return from Death"
LEGEND_SUBTYPE = "return from death"
LEGEND_DESCRIPTION = "{story}."
STORY_CREATOR = "When {killer} reached for {victim}'s life, {creator}'s hand descended from above the sky; no son could take a life devoted to the creator"
STORY_PATRON = "{patron} stepped in front of {victim}; {killer}'s death command struck a brother's shield and scattered"
STORY_ITEM = "The {item} that {victim} carried drew death's breath onto itself and cracked; its owner survived"
STORY_CHOSEN = "{victim} was one of the chosen; the threads of fate have not let go of them yet"
STORY_PROTECTED = "{victim} was protected; death's hand slid off them"
STORY_FATES = (
    "That night {victim} heard death's footsteps in a dream and fled before dawn",
    "The death {killer} sent knocked on the wrong door; a stranger died in {victim}'s place",
    "{victim} looked death in the face and did not look away; death retreated before such courage",
    "Just as death's hand was about to touch {victim}, {killer}'s own domain trembled and the command fell empty",
    "That night {victim}'s people spoke their name so often that death could not find them in the crowd",
)
FOREIGN_STRIKE_HOW = "the wrath of the old god of the world {world}"
GOD_KILL_MORTAL_HOW = "by {creator}'s hand"

RITE = Line("gods.death.rite", "{worshipper} offered {kind} for {son}'s return ({cost}){pilgrimage}; devotion {devotion}.")
RITE_PILGRIMAGE = ", at the foot of their bones"
RITE_KIND_NAMES = {"prayer": "a prayer", "offering": "a wealth offering", "blood": "a blood sacrifice", "life": "a life sacrifice", "rite": "a rite"}
RITE_COST_PRAYER = "only their prayers"
RITE_COST_PAID = "{source} {amount}"
RITE_COST_SOURCES = {"wealth": "from its wealth", "prosperity": "from its prosperity", "craft": "from its craft labour"}
RITE_COST_LIVES = "{count} lives"
RITE_COST_LIFE = "{victim}'s life"
RITE_SACRIFICE_REASON = "sacrificed for {son}'s return"
SCHEME = Line("gods.death.scheme", "{sibling} performed {kind} for their dead sibling {son} ({cost} essence){extra}{devotion}.")
SCHEME_KIND_NAMES = {"rite": "a resurrection rite", "descent": "a descent to the underworld", "bargain": "a bargain with a foreign god"}
SCHEME_DESCENT_SUCCESS = "; pulled {son}'s shadow one step back from the shore of the dead"
SCHEME_DESCENT_FAILURE = "; but lost their way in the underworld and fell asleep for {epochs} epochs"
SCHEME_BARGAIN_PRICE = "; the price was {community} passing to {god}"
SCHEME_BARGAIN_PROMISE = "; a promise given to {god}"
SCHEME_BARGAIN_VOW = "by {sibling}'s bargain"
SCHEME_DEVOTION = "; devotion {devotion}"
SCATTER = Line("gods.death.scatter", "{sibling} scattered {son}'s bones ({cost} essence); resurrection rites fell back {loss} devotion.")
SCATTER_NOTE = "scattered their bones"
SCATTER_ENEMY = "scattered {son}'s bones"
SCHEME_RELATION_NOTE = "schemed for their return"
KILL_SON_NOTE = "killed by the creator"

ECONOMY_ADDICTED = Line("gods.economy.addicted", "{owner} can no longer do without {resource}.")
ECONOMY_SENTIENT_PAID = Line("gods.economy.sentient_paid", "{resource} demanded {demand} from {owner}; {owner} paid the price.")
ECONOMY_SENTIENT_LEFT = Line("gods.economy.sentient_left", "{resource} demanded {demand} from {owner}, and when it did not get it, abandoned them{chosen}.")
ECONOMY_SENTIENT_CHOSEN = "; now it chooses {owner}"
ECONOMY_SENTIENT_BOND = "the resource chose it"
SENTIENT_DEMANDS = (
    "an epoch of silence",
    "the eyes of the oldest seer",
    "the first names of the newborns",
    "a song, every night",
    "a settlement of their enemy",
    "the entire harvest of a year",
)
ECONOMY_SACRED_CURSE = Line("gods.economy.sacred_curse", "{son} cursed {owner} for digging the sacred {resource}.")
ECONOMY_SACRED_BOND = "for the sacred {resource}"
ECONOMY_DEPLETED = Line("gods.economy.depleted", "The last drop of {resource} was drawn;{place} the doomsday clock advanced.")
ECONOMY_DEPLETED_PLACE = " {place} was cursed and"
ECONOMY_WITHDRAWAL = Line("gods.economy.withdrawal", "{entity} suffers withdrawal from {resource}: cities silent, eyes clouded.")
ECONOMY_RECOVERED = Line("gods.economy.recovered", "{entity} survived the withdrawal from {resource}; the addiction was broken.")
ECONOMY_DEPOSIT_CLAIMED = Line("gods.economy.deposit_claimed", "{owner} claimed {deposit}; the key to travel between worlds is now in their hands.")
ECONOMY_DEPOSIT_CLAIM_BOND = "claimed the cosmic resource"
ECONOMY_DEPOSIT_BORN = Line("gods.economy.deposit_born", "A {resource} deposit appeared in {world} ({region}).")
DEPOSIT_NAME = "{resource} Deposit ({region})"
DEPOSIT_SUBTYPE = "cosmic travel resource"
DEPOSIT_DESCRIPTION = "A vein of {resource} appeared in {world}, in the soil of {region}. {rule}"
ECONOMY_MONOPOLY = Line("gods.economy.monopoly", "{owner} seized all the cosmos's travel resource: now it decides who travels between worlds.")
ECONOMY_MONOPOLY_BROKEN = Line("gods.economy.monopoly_broken", "{owner}'s cosmic monopoly was broken.")
MARKET_NAME = "Wandering Market"
MARKET_SUBTYPE = "wandering market"
MARKET_DESCRIPTION = (
    "A market carried from ship to ship between worlds, pitched under a different sky each epoch. Everything is for sale; some things only there."
)
ECONOMY_MARKET_BORN = Line("gods.economy.market_born", "A wandering market was born on the routes between worlds.")
ECONOMY_MARKET_MOVED = Line("gods.economy.market_moved", "{market} packed up and moved to the world {world}, to {region}.")
MARKET_TRADE_BOND = "wandering market"
PIRATES_NAME = "Void Pirates"
PIRATES_SUBTYPE = "void pirates"
PIRATES_DESCRIPTION = "As the routes between worlds grew crowded, pirates appeared to ambush ships."
ECONOMY_PIRATES_BORN = Line("gods.economy.pirates_born", "Void pirates appeared in {region}, preying on the crowded routes between worlds.")
PRAYER_ANSWERED = Line("gods.mood.prayer_answered", "{creator} heard {entity}'s prayer{grace}.")
PRAYER_GRACE = " and sent down his grace"
PRAYER_ANSWERED_VOW = "their prayer was answered"
PROPHET_LISTENS = "; {community} began to listen to their words"
PASSION_JOIN = ", "

SON_LEVEL_UP = Line("sons.level_up", "{son} grew stronger and rose to rank {level}.")
SON_POWER_AWOKE = Line("sons.power_awoke", "A new power awoke within {son}: {power}.")

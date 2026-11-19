from dataclasses import dataclass

from aerona.core.grammar import fill


@dataclass(frozen=True)
class Line:
    key: str
    text: str

    def render(self, **fields: object) -> str:
        return fill(self.text, **fields)


LONELY_DREAM = "The creator is lonely and is calling you."
ESTRANGED_VOW = "turned from the sons to the creator"

DRAIN_WITNESS = "; the other sons saw it"
DRAIN_ANGER = "in anger "
DRAIN_AGAIN = "again "
DRAIN_REPEAT_SUFFIX = " (the {count} time this epoch)."
DEVOUR_CAUSE = "devoured by {creator}"
DEVOUR_MORTAL_HOW = "life and soul devoured by the creator"
FOREIGN_CONVERT_VOW = "{god} died and it turned to the creator"
RESURRECT_MORTAL_NOTE = " Epoch {epoch}: {creator} brought them back to life."
PROPHET_VOW = "became the creator's prophet"
PROPHET_CONTENT = ", content,"
MANIFEST_VOW = "saw the creator with their own eyes"
PROPHET_COMMUNITY_VOW = "by the word of the prophet {prophet}"
CONVERT_VOW = "{creator} turned them to the creator"
WRATH_NOTE = "Epoch {epoch}: destroyed by {creator}'s wrath{reason}."
WRATH_HOW = "together with {entity}"
REBELLION_SPONTANEOUS_MANIFESTO = "their loyalty ran out; they made no declaration."
CURSE_REASON_BLOODY_HAND = "for killing {victim}"
CURSE_REASON_TEMPLE = "for tearing down {place}"
CURSE_REASON_CURSED = "the curse reached the kin of one already cursed"
CURSE_REASON_KILLER = "for taking {count:life|lives}"


ACHIEVEMENT_TITLE = "Achievement: {name}"

GOD_DEATH_FADED = "faded away, forgotten"
FALLEN_BODY_DIED = "died in the mortal body {body}"
GOD_DEATH_KILLED = "killed by {creator}'s hand"
CORPSE_NAME = "Remains of {son}"
OUTER_CULT_BOND = "worship carried over from a son who left the cosmos"
CORPSE_DESCRIPTION = "{son}, {title}, died ({cause}). Their body fell {where} and became a place that still carries {domain_1} and {domain_2}."
CORPSE_WHERE_LAND = "onto the lands of {home}"
CORPSE_WHERE_WORLD = "to the world"
SHADE_NAME = "Shade of {son}"
SHADE_DESCRIPTION = "The shade of the dead god {son}, which stays near their remains."
ORDER_NAME = "Those Who Await {son}'s Return"
ORDER_DESCRIPTION = "Those who stayed loyal to {son} gathered at their remains; they believe the god will return."
ORDER_REBORN_DESCRIPTION = "{source} gathered again for {son}'s return."
ORDER_REBORN_SOURCE = "Believers who still worshipped them"
ORDER_WORSHIP = "to the dead god"
DEATH_THREAD = "{son} died; their remains lie in {where}. The loyal await their return."
DEATH_THREAD_WORLD = "the world"
CORPSE_BOND = "corpse"
SHADE_BOND = "shade"
EMPTY_TOMB_CLAUSE = "; {corpse} is now empty"
RESURRECTION_BY_RITE = "by the rite of {order}"
RESURRECTION_BY_CREATOR = "by {creator}'s hand"

KILL_REASON = "life taken by the hand of {killer}{how}"
KILL_IMMORTAL = "{victim} is immortal and cannot be killed."
KILL_DIED = "{victim} died: {reason}."
KILL_RELATION_NOTE = "took {victim}'s life"
KILL_PROTECT_NOTE = "protected {victim}"
LEGEND_NAME = "{victim}'s Return from Death"
LEGEND_SUBTYPE = "return from death"
LEGEND_DESCRIPTION = "{story}."
STORY_CREATOR = "{creator} protects those devoted to the creator"
STORY_PATRON = "{patron} shielded {victim} from {killer}"
STORY_ITEM = "the {item} that {victim} carried protected its bearer"
STORY_CHOSEN = "{victim} is one of the chosen"
STORY_PROTECTED = "{victim} was under protection"
STORY_CHANCE = "the attempt did not succeed"
FOREIGN_STRIKE_HOW = "the wrath of the old god of the world {world}"
GOD_KILL_MORTAL_HOW = "by {creator}'s hand"

RITE_PILGRIMAGE = ", at their remains"
RITE_KIND_NAMES = {"prayer": "a prayer", "offering": "a wealth offering", "blood": "a blood sacrifice", "life": "a life sacrifice", "rite": "a rite"}
RITE_COST_PRAYER = "only their prayers"
RITE_COST_PAID = "{source} {amount}"
RITE_COST_SOURCES = {"wealth": "from its wealth", "prosperity": "from its prosperity", "craft": "from its craft labour"}
RITE_COST_LIVES = "{count:life|lives}"
RITE_COST_LIFE = "{victim}'s life"
RITE_SACRIFICE_REASON = "sacrificed for {son}'s return"
SCHEME_KIND_NAMES = {"rite": "a resurrection rite", "descent": "a journey among the dead", "bargain": "a bargain with a foreign god"}
SCHEME_DESCENT_SUCCESS = "; it brought {son} one step closer to return"
SCHEME_DESCENT_FAILURE = "; it failed, and {sibling} was dormant for {epochs:epoch|epochs}"
SCHEME_BARGAIN_PRICE = "; the price was {community} passing to {god}"
SCHEME_BARGAIN_PROMISE = "; a promise given to {god}"
SCHEME_BARGAIN_VOW = "by {sibling}'s bargain"
SCHEME_DEVOTION = "; devotion {devotion}"
HINDERED_NOTE = "hindered their return"
HINDERED_ENEMY = "hindered the return of {son}"
SCHEME_RELATION_NOTE = "schemed for their return"

ECONOMY_SENTIENT_CHOSEN = "; now it chooses {owner}"
ECONOMY_SENTIENT_BOND = "the resource chose it"
SENTIENT_DEMANDS = (
    ("wealth", None, 0),
    ("sacred goods", "sacred_goods", 20),
    ("luxuries", "luxuries", 15),
    ("a year's grain", "grain", 400),
)
ECONOMY_SACRED_BOND = "for the sacred {resource}"
ECONOMY_DEPLETED_PLACE = " {place} was cursed and"
ECONOMY_DEPOSIT_CLAIM_BOND = "claimed the cosmic resource"
DEPOSIT_NAME = "{resource} Deposit ({region})"
DEPOSIT_SUBTYPE = "cosmic travel resource"
DEPOSIT_DESCRIPTION = "A deposit of {resource} appeared in {world}, in {region}. {rule}"
MARKET_NAME = "Wandering Market"
MARKET_SUBTYPE = "wandering market"
MARKET_DESCRIPTION = "A market carried by ships between worlds, moving to a new world each epoch."
MARKET_TRADE_BOND = "wandering market"
PIRATES_NAME = "Route Raiders"
PIRATES_SUBTYPE = "route raiders"
PIRATES_DESCRIPTION = "As the routes between worlds grew crowded, pirates appeared to ambush ships."
PRAYER_GRACE = " and sent down grace"
PRAYER_ANSWERED_VOW = "their prayer was answered"
PROPHET_LISTENS = "; {community} began to listen to their words"
PASSION_JOIN = ", "

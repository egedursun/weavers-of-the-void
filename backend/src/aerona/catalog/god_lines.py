from dataclasses import dataclass

from aerona.core.grammar import fill


@dataclass(frozen=True)
class Line:
    key: str
    text: str

    def render(self, **fields: object) -> str:
        return fill(self.text, **fields)


WRATH_SIGN = Line("gods.mood.wrath", "{creator}'s anger sent {disaster} upon {place}.")
GRACE_SIGN = Line("gods.mood.grace", "{creator}'s grace came upon {place}.")
SILENCE_SIGN = Line("gods.mood.silence", "{creator} gave no sign this epoch; the sons' loyalty fell and their ambition rose.")
LONELINESS_SIGN = Line("gods.mood.loneliness", "{creator} sent {mortal} a dream, calling to them.")
LONELY_DREAM = Line("gods.mood.lonely_dream", "The creator is lonely and is calling you.")
ESTRANGED_TURN = Line("gods.mood.estranged_turn", "{entity} turned its face from its sons and began worshipping the creator {creator} directly.")
ESTRANGED_VOW = "turned from the sons to the creator"

DRAIN_SON = Line("gods.power.drain", "{creator} {anger}{again}drained {son}'s essence: {drawn} essence drawn, {gained} of it passed to the creator{witness}.")
DRAIN_WITNESS = "; the other sons saw it"
DRAIN_ANGER = "in anger "
DRAIN_AGAIN = "again "
DRAIN_REPEAT_SUFFIX = " (the {count} time this epoch)."
DEVOUR_SON = Line("gods.power.devour", "{creator} devoured the son {son}; all their essence and might returned to the creator ({gained} essence).")
DEVOUR_CAUSE = "devoured by {creator}"
DRAIN_MORTAL = Line("gods.power.drain_mortal", "{creator} drew {drawn} of {mortal}'s life ({gained} essence); {mortal} still lives.")
DEVOUR_MORTAL = Line("gods.power.devour_mortal", "{creator} devoured {mortal}'s life and soul ({gained} essence).")
DEVOUR_MORTAL_HOW = "life and soul devoured by the creator"
HARVEST = Line("gods.power.harvest", "{creator} harvested the faith of {community}{victims}{faith} ({gained} essence).{grudge}")
FOREIGN_DRAIN = Line("gods.power.foreign_drain", "{creator} drained {drawn} of the foreign god {god}'s power ({gained} essence){defeated}.")
FOREIGN_KILL = Line(
    "gods.power.foreign_kill",
    "{creator} {verb} the foreign god {god}{reason}{gain}. {converted} of its worshippers turned to the creator, {godless} were left godless.",
)
FOREIGN_CONVERT_VOW = "{god} died and it turned to the creator"
RESURRECT_MORTAL = Line("gods.power.resurrect_mortal", "{creator} brought {mortal} back to life.")
RESURRECT_MORTAL_NOTE = " Epoch {epoch}: {creator} brought them back to life."
DEMOTE = Line("gods.power.demote", "{creator} demoted {son} from {old} class to {new} class; their stats were capped, their loyalty fell and their wrath rose.")
STRIP_POWER = Line("gods.power.strip", '{creator} took {son}\'s power "{power}" ({gained} essence returned to the creator).')
ABSOLUTE_COMMAND = Line("gods.power.absolute_command", '{creator} gave {son} an irrefusable command: "{command}"')
PROPHET = Line("gods.power.prophet", "{creator}{content} chose {mortal} as the creator's prophet{community}.")
PROPHET_VOW = "became the creator's prophet"
PROPHET_CONTENT = ", content,"
MANIFEST = Line("gods.power.manifest", '{creator} appeared to {entity} while awake and spoke: "{words}"{worship}')
MANIFEST_VOW = "saw the creator with their own eyes"
BLOODLINE_CURSE = Line(
    "gods.power.bloodline_curse",
    "{creator} cursed {root}'s bloodline{reason}: {count} living descendants fell under the curse; those yet to be born will carry it too.",
)
BLOODLINE_LIFT = Line("gods.power.bloodline_lift", "{creator} lifted the curse from {root}'s bloodline ({count:person|people}).")
BLOODLINE_NEWBORNS = Line("gods.power.bloodline_newborns", "The bloodline curse passed to {count:newborn|newborns}: {names}.")
PROPHET_COMMUNITY = Line("gods.power.prophet_community", "{community} began worshipping the creator {creator} by the word of the prophet {prophet}.")
PROPHET_COMMUNITY_VOW = "by the word of the prophet {prophet}"
CONVERT = Line("gods.power.convert", "{creator} turned {entity} to the creator{old}. It now worships the creator directly.")
CONVERT_VOW = "{creator} turned them to the creator"
WRATH = Line("gods.power.wrath", "{creator} destroyed {entity} in wrath{reason}{deaths}.")
WRATH_NOTE = "Epoch {epoch}: destroyed by {creator}'s wrath{reason}."
WRATH_HOW = "together with {entity}"
WORLD_WRATH = Line("gods.power.world_wrath", "{creator} sent {disaster} upon all of {world}: all {count:region|regions} were struck.")
REBELLION = Line("gods.power.rebellion_declared", "{son} rebelled against the creator {creator}: {manifesto}")
REBELLION_SPONTANEOUS_MANIFESTO = "their loyalty ran out; they made no declaration."
REBELLION_ENDED = Line(
    "gods.power.rebellion_ended", "{son}'s rebellion ended: their loyalty returned and they again follow the commands of the creator {creator}."
)
CURSE_REASON_BLOODY_HAND = "for killing {victim}"
CURSE_REASON_TEMPLE = "for tearing down {place}"
CURSE_REASON_CURSED = "the curse reached the kin of one already cursed"
CURSE_REASON_KILLER = "for taking {count:life|lives}"

REPUTATION_CHANGE = Line("gods.reputation.change", "{son} now sees the creator as {label:an} god.")
PASSIONS_REVEALED = Line("gods.reputation.passions", "{creator} was revealed: the creator's passions are {passions}.")

GOAL_SET = Line("gods.goals.set", "{creator} set a goal: {name}.")
GOAL_ACHIEVED = Line("gods.goals.achieved", "Goal achieved: {name}.")
GOAL_LOST = Line("gods.goals.lost", "Goal lost: {name}. {detail}")
ACHIEVEMENT_TITLE = "Achievement: {name}"

GOD_DEATH = Line(
    "gods.death.god_death",
    "{creator}'s son {son} died ({cause}). Their body became {corpse}; {apostates} of their worshippers turned away, {loyal} await their return.",
)
GOD_LEFT_COSMOS = Line(
    "gods.death.left_cosmos",
    "{creator}'s son {son} left the cosmos ({cause}) and lives on outside it as {successor}; {moved} of their worshippers now worship it.",
)
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
SON_RESURRECTED = Line(
    "gods.death.son_resurrected",
    "{son} returned to life where they died ({path}){tomb}; their power is lower than before.",
)
EMPTY_TOMB_CLAUSE = "; {corpse} is now empty"
RESURRECTION_BY_RITE = "by the rite of {order}"
RESURRECTION_BY_CREATOR = "by {creator}'s hand"
FADING_TWO = Line("gods.death.fading_two", "{son} is nearly forgotten; few still worship them. If two more epochs pass like this, they will fade.")
FADING_ONE = Line("gods.death.fading_one", "{son} is almost forgotten; if they are forgotten one more epoch, they will fade.")
FADING_MANY = Line("gods.death.fading_many", "{son} is nearly forgotten; few still worship them. If {left} more epochs pass like this, they will fade.")

KILL_REASON = "life taken by the hand of {killer}{how}"
KILL_IMMORTAL = Line("gods.death.kill_immortal", "{victim} is immortal and cannot be killed.")
KILL_FAILED = Line("gods.death.kill_failed", "{killer} tried to take {victim}'s life and failed: {story}.")
KILL_DIED = Line("gods.death.kill_died", "{victim} died: {reason}.")
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

RITE = Line("gods.death.rite", "{worshipper} offered {kind} for {son}'s return ({cost}){pilgrimage}; devotion {devotion}.")
RITE_PILGRIMAGE = ", at their remains"
RITE_KIND_NAMES = {"prayer": "a prayer", "offering": "a wealth offering", "blood": "a blood sacrifice", "life": "a life sacrifice", "rite": "a rite"}
RITE_COST_PRAYER = "only their prayers"
RITE_COST_PAID = "{source} {amount}"
RITE_COST_SOURCES = {"wealth": "from its wealth", "prosperity": "from its prosperity", "craft": "from its craft labour"}
RITE_COST_LIVES = "{count:life|lives}"
RITE_COST_LIFE = "{victim}'s life"
RITE_SACRIFICE_REASON = "sacrificed for {son}'s return"
SCHEME = Line("gods.death.scheme", "{sibling} performed {kind} for their dead sibling {son} ({cost} essence){extra}{devotion}.")
SCHEME_KIND_NAMES = {"rite": "a resurrection rite", "descent": "a journey among the dead", "bargain": "a bargain with a foreign god"}
SCHEME_DESCENT_SUCCESS = "; it brought {son} one step closer to return"
SCHEME_DESCENT_FAILURE = "; it failed, and {sibling} was dormant for {epochs} epochs"
SCHEME_BARGAIN_PRICE = "; the price was {community} passing to {god}"
SCHEME_BARGAIN_PROMISE = "; a promise given to {god}"
SCHEME_BARGAIN_VOW = "by {sibling}'s bargain"
SCHEME_DEVOTION = "; devotion {devotion}"
SCATTER = Line("gods.death.scatter", "{sibling} scattered {son}'s remains ({cost} essence); resurrection rites lost {loss} devotion.")
SCATTER_NOTE = "scattered their remains"
SCATTER_ENEMY = "scattered {son}'s remains"
SCHEME_RELATION_NOTE = "schemed for their return"

ECONOMY_ADDICTED = Line("gods.economy.addicted", "{owner} can no longer do without {resource}.")
ECONOMY_SENTIENT_PAID = Line("gods.economy.sentient_paid", "{resource} demanded {demand} from {owner}; {owner} paid the price.")
ECONOMY_SENTIENT_LEFT = Line("gods.economy.sentient_left", "{resource} demanded {demand} from {owner}, and when it did not get it, abandoned them{chosen}.")
ECONOMY_SENTIENT_CHOSEN = "; now it chooses {owner}"
ECONOMY_SENTIENT_BOND = "the resource chose it"
SENTIENT_DEMANDS = (
    ("wealth", None, 0),
    ("sacred goods", "sacred_goods", 20),
    ("luxuries", "luxuries", 15),
    ("a year's grain", "grain", 400),
)
ECONOMY_SENTIENT_PACT = Line(
    "gods.economy.sentient_pact", "{negotiator} struck a pact with {resource} for {owner}: {demand}, owed on a set term, in return for its gifts."
)
ECONOMY_SENTIENT_PACT_KEPT = Line("gods.economy.sentient_pact_kept", "{owner} gave {resource} {demand} as the pact bids; the resource gave of itself in turn.")
ECONOMY_SENTIENT_PACT_BROKEN = Line(
    "gods.economy.sentient_pact_broken", "{owner} broke the pact with {resource} and withheld {demand}; the resource left them."
)
ECONOMY_SACRED_CURSE = Line("gods.economy.sacred_curse", "{son} cursed {owner} for digging the sacred {resource}.")
ECONOMY_SACRED_BOND = "for the sacred {resource}"
ECONOMY_DEPLETED = Line("gods.economy.depleted", "{resource} ran out;{place} doom advanced.")
ECONOMY_DEPLETED_PLACE = " {place} was cursed and"
ECONOMY_WITHDRAWAL = Line("gods.economy.withdrawal", "{entity} suffers withdrawal from {resource}.")
ECONOMY_RECOVERED = Line("gods.economy.recovered", "{entity} survived the withdrawal from {resource}; the addiction was broken.")
ECONOMY_DEPOSIT_CLAIMED = Line("gods.economy.deposit_claimed", "{owner} claimed {deposit}; they now hold a source of travel between worlds.")
ECONOMY_DEPOSIT_CLAIM_BOND = "claimed the cosmic resource"
ECONOMY_DEPOSIT_BORN = Line("gods.economy.deposit_born", "{resource:An} deposit appeared in {world} ({region}).")
DEPOSIT_NAME = "{resource} Deposit ({region})"
DEPOSIT_SUBTYPE = "cosmic travel resource"
DEPOSIT_DESCRIPTION = "A deposit of {resource} appeared in {world}, in {region}. {rule}"
ECONOMY_MONOPOLY = Line("gods.economy.monopoly", "{owner} holds all of the cosmos's travel resource and now decides who travels between worlds.")
ECONOMY_MONOPOLY_BROKEN = Line("gods.economy.monopoly_broken", "{owner}'s cosmic monopoly was broken.")
MARKET_NAME = "Wandering Market"
MARKET_SUBTYPE = "wandering market"
MARKET_DESCRIPTION = "A market carried by ships between worlds, moving to a new world each epoch."
ECONOMY_MARKET_BORN = Line("gods.economy.market_born", "A wandering market began on the routes between worlds.")
ECONOMY_MARKET_MOVED = Line("gods.economy.market_moved", "{market} packed up and moved to the world {world}, to {region}.")
MARKET_TRADE_BOND = "wandering market"
PIRATES_NAME = "Route Raiders"
PIRATES_SUBTYPE = "route raiders"
PIRATES_DESCRIPTION = "As the routes between worlds grew crowded, pirates appeared to ambush ships."
ECONOMY_PIRATES_BORN = Line("gods.economy.pirates_born", "Raiders appeared in {region} on the crowded routes between worlds.")
PRAYER_ANSWERED = Line("gods.mood.prayer_answered", "{creator} heard {entity}'s prayer{grace}.")
PRAYER_GRACE = " and sent down grace"
PRAYER_ANSWERED_VOW = "their prayer was answered"
PROPHET_LISTENS = "; {community} began to listen to their words"
PASSION_JOIN = ", "

SON_LEVEL_UP = Line("sons.level_up", "{son} grew stronger and rose to rank {level}.")
SON_POWER_AWOKE = Line("sons.power_awoke", "A new power awoke within {son}: {power}.")

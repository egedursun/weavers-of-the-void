from dataclasses import dataclass
from types import MappingProxyType

from aerona.domain.enums.divine import DomainActivity, DomainHook
from aerona.domain.enums.domain import Domain

D = Domain
H = DomainHook
A = DomainActivity
MAJOR = 2
MINOR = 1


@dataclass(frozen=True)
class HookSpec:
    hook: DomainHook
    label: str
    effect: str
    harmful: bool = False


@dataclass(frozen=True)
class DomainEffect:
    domain: Domain
    hooks: MappingProxyType[DomainHook, int]
    activity: DomainActivity


@dataclass(frozen=True)
class Synergy:
    pair: frozenset[Domain]
    hook: DomainHook
    label: str


HOOKS: MappingProxyType[DomainHook, HookSpec] = MappingProxyType(
    {
        spec.hook: spec
        for spec in (
            HookSpec(H.NAVAL_MIGHT, "Naval might", "Fleets of the faithful strike harder at sea."),
            HookSpec(H.SEA_CALM, "Calm seas", "Voyages of the faithful lose fewer ships and sailors."),
            HookSpec(H.CATCH, "Rich catch", "Fisheries and catches of the faithful yield more."),
            HookSpec(H.FIRE_CURSE, "Fire on the foe", "Towns at war with the faithful burn more often.", harmful=True),
            HookSpec(H.LEVY_MORALE, "Levy morale", "Armies of the faithful hold their nerve longer."),
            HookSpec(H.DUEL_WOUNDS, "Telling blows", "Champions of the faithful deal deeper wounds in duels."),
            HookSpec(H.SOUL_HOLD, "Hold on souls", "The god gains more from the souls held in its realm."),
            HookSpec(H.DEATH_TOLL, "Death toll", "The god gains more essence from deaths among its faithful."),
            HookSpec(H.PLAGUE_TITHE, "Plague tithe", "The god gains more essence from outbreaks."),
            HookSpec(H.IMMUNITY, "Immunity", "The faithful catch sickness less often."),
            HookSpec(H.HARVEST_FLOOR, "Harvest floor", "The fields of the faithful never fall below a floor."),
            HookSpec(H.OATH_TITHE, "Oath tithe", "The god gains more essence from oaths kept among its faithful."),
            HookSpec(H.MEMORY_KEEPING, "Memory keeping", "Legends told by the faithful change more slowly."),
            HookSpec(H.BORDER_GUARD, "Border guard", "Places of the faithful hold out longer under siege."),
            HookSpec(H.PRESERVATION, "Preservation", "Stores of the faithful spoil more slowly."),
            HookSpec(H.STARGAZING, "Stargazing", "Research among the faithful advances faster."),
            HookSpec(H.FASTING, "Fasting", "Hunger weighs less on the faithful."),
            HookSpec(H.SIEGE_STARVING, "Starving siege", "Places besieged by the faithful starve faster.", harmful=True),
            HookSpec(H.RUMOUR_TWIST, "Twisted rumours", "Rumours passed by the faithful change more in the telling."),
            HookSpec(H.SPY_DEPTH, "Deep spies", "Spy networks of the faithful gather more."),
            HookSpec(H.ROAD_SAFETY, "Safe roads", "Routes travelled by the faithful are safer."),
            HookSpec(H.BLOOD_RITE, "Blood rites", "Rites cast by the faithful are stronger."),
            HookSpec(H.BLOODLINE, "Marked bloodlines", "The gift is born more often among the faithful."),
            HookSpec(H.RELIC_POWER, "Relic power", "Relics kept by the faithful are more potent."),
            HookSpec(H.AGING, "Slow years", "The faithful age more slowly."),
            HookSpec(H.PROPHECY, "Certain prophecy", "Prophecies of the faithful come true more often."),
            HookSpec(H.TRADE_GAIN, "Trade gain", "Trade of the faithful earns more."),
            HookSpec(H.CRAFT_SKILL, "Craft skill", "Works of the faithful are of finer quality."),
            HookSpec(H.LEARNING, "Learning", "The faithful learn skills faster."),
            HookSpec(H.KINDLING_LOVE, "Kindled love", "Love among the faithful grows faster."),
            HookSpec(H.HUNT_YIELD, "Hunt yield", "Hunters of the faithful bring back more."),
            HookSpec(H.FERTILITY, "Fertility", "Peoples of the faithful grow faster."),
            HookSpec(H.HEALING, "Healing", "Wounds of the faithful heal faster."),
            HookSpec(H.DREAM_SENDING, "Dream sending", "The faithful dream more often."),
            HookSpec(H.STONEWORK, "Stonework", "Building among the faithful goes faster."),
            HookSpec(H.SANITY_WARD, "Sanity ward", "The faithful lose less sanity."),
            HookSpec(H.FRENZY, "Frenzy", "The faithful lose more sanity, and rage in battle.", harmful=True),
            HookSpec(H.COLD_ENDURANCE, "Cold endurance", "Armies of the faithful suffer less from the cold."),
            HookSpec(H.REST, "Rest", "Strain among the faithful eases faster."),
            HookSpec(H.LEGEND_SPREAD, "Spreading legends", "Legends of the faithful spread further."),
        )
    }
)

ACTIVITY_LABELS: MappingProxyType[DomainActivity, str] = MappingProxyType(
    {
        A.BATTLES: "Battles",
        A.DEATHS: "Deaths",
        A.BIRTHS: "Births",
        A.VOYAGES: "Voyages",
        A.TRADE: "Trade",
        A.SICKNESS: "Sickness",
        A.OATHS: "Oaths kept",
        A.LEGENDS: "Legends",
        A.WORKS: "Works made",
        A.DISCOVERIES: "Discoveries",
        A.MARRIAGES: "Marriages",
        A.HUNTS: "Hunts",
        A.SCHEMES: "Schemes",
        A.RITES: "Rites cast",
        A.DREAMS: "Dreams",
        A.HUNGER: "Hunger",
        A.MADNESS: "Madness",
        A.JOURNEYS: "Journeys",
        A.HARVESTS: "Harvests",
        A.BUILDING: "Building",
    }
)


def _effect(domain: Domain, activity: DomainActivity, major: tuple[DomainHook, ...], minor: tuple[DomainHook, ...] = ()) -> DomainEffect:
    return DomainEffect(domain, MappingProxyType({**{hook: MINOR for hook in minor}, **{hook: MAJOR for hook in major}}), activity)


DOMAIN_EFFECTS: MappingProxyType[Domain, DomainEffect] = MappingProxyType(
    {
        effect.domain: effect
        for effect in (
            _effect(D.SEA, A.VOYAGES, (H.NAVAL_MIGHT, H.SEA_CALM), (H.CATCH,)),
            _effect(D.FIRE, A.BUILDING, (H.FIRE_CURSE, H.CRAFT_SKILL)),
            _effect(D.EARTH, A.HARVESTS, (H.HARVEST_FLOOR, H.STONEWORK)),
            _effect(D.SKY, A.VOYAGES, (H.HARVEST_FLOOR,), (H.SEA_CALM, H.PROPHECY)),
            _effect(D.STORM, A.BATTLES, (H.NAVAL_MIGHT, H.LEVY_MORALE)),
            _effect(D.DEATH, A.DEATHS, (H.SOUL_HOLD, H.DEATH_TOLL)),
            _effect(D.LIFE, A.BIRTHS, (H.FERTILITY, H.HEALING)),
            _effect(D.DREAM, A.DREAMS, (H.DREAM_SENDING,), (H.PROPHECY, H.REST)),
            _effect(D.TIME, A.LEGENDS, (H.AGING, H.PROPHECY)),
            _effect(D.LIGHT, A.DISCOVERIES, (H.SANITY_WARD,), (H.HEALING, H.STARGAZING)),
            _effect(D.SHADOW, A.SCHEMES, (H.SPY_DEPTH,), (H.RUMOUR_TWIST,)),
            _effect(D.WAR, A.BATTLES, (H.LEVY_MORALE, H.DUEL_WOUNDS)),
            _effect(D.CRAFT, A.WORKS, (H.CRAFT_SKILL, H.STONEWORK)),
            _effect(D.KNOWLEDGE, A.DISCOVERIES, (H.LEARNING, H.STARGAZING)),
            _effect(D.LOVE, A.MARRIAGES, (H.KINDLING_LOVE,), (H.FERTILITY,)),
            _effect(D.TRICKERY, A.SCHEMES, (H.RUMOUR_TWIST, H.SPY_DEPTH)),
            _effect(D.HUNT, A.HUNTS, (H.HUNT_YIELD,), (H.LEVY_MORALE,)),
            _effect(D.PLANTS, A.HARVESTS, (H.HARVEST_FLOOR,), (H.HEALING,)),
            _effect(D.BONE, A.DEATHS, (H.RELIC_POWER,), (H.SOUL_HOLD,)),
            _effect(D.BLOOD, A.RITES, (H.BLOOD_RITE, H.BLOODLINE)),
            _effect(D.SOUND, A.LEGENDS, (H.LEGEND_SPREAD,), (H.LEVY_MORALE,)),
            _effect(D.STONE, A.BUILDING, (H.STONEWORK, H.BORDER_GUARD)),
            _effect(D.ICE, A.HUNGER, (H.COLD_ENDURANCE,), (H.PRESERVATION,)),
            _effect(D.MADNESS, A.MADNESS, (H.FRENZY,), (H.PROPHECY,)),
            _effect(D.TRADE, A.TRADE, (H.TRADE_GAIN,), (H.ROAD_SAFETY,)),
            _effect(D.ROAD, A.JOURNEYS, (H.ROAD_SAFETY,), (H.TRADE_GAIN,)),
            _effect(D.PLAGUE, A.SICKNESS, (H.PLAGUE_TITHE, H.IMMUNITY)),
            _effect(D.HARVEST, A.HARVESTS, (H.HARVEST_FLOOR,), (H.PRESERVATION,)),
            _effect(D.MOON, A.DREAMS, (H.DREAM_SENDING,), (H.HUNT_YIELD, H.CATCH)),
            _effect(D.SUN, A.HARVESTS, (H.HARVEST_FLOOR,), (H.SANITY_WARD,)),
            _effect(D.STAR, A.DISCOVERIES, (H.PROPHECY,), (H.ROAD_SAFETY, H.STARGAZING)),
            _effect(D.LIES, A.SCHEMES, (H.RUMOUR_TWIST,), (H.SPY_DEPTH,)),
            _effect(D.OATH, A.OATHS, (H.OATH_TITHE,), (H.LEVY_MORALE,)),
            _effect(D.MEMORY, A.LEGENDS, (H.MEMORY_KEEPING,), (H.LEARNING,)),
            _effect(D.HUNGER, A.HUNGER, (H.FASTING, H.SIEGE_STARVING)),
            _effect(D.GLASS, A.DISCOVERIES, (H.STARGAZING,), (H.CRAFT_SKILL,)),
            _effect(D.SALT, A.HUNGER, (H.PRESERVATION,), (H.CATCH,)),
            _effect(D.ASH, A.DEATHS, (H.FIRE_CURSE,), (H.DEATH_TOLL,)),
            _effect(D.BORDER, A.BATTLES, (H.BORDER_GUARD,), (H.LEVY_MORALE,)),
            _effect(D.SLEEP, A.DREAMS, (H.REST,), (H.DREAM_SENDING,)),
        )
    }
)

SYNERGIES: tuple[Synergy, ...] = (
    Synergy(frozenset({D.SEA, D.DEATH}), H.SOUL_HOLD, "Drowned souls go to the god's realm"),
    Synergy(frozenset({D.SEA, D.STORM}), H.NAVAL_MIGHT, "Storms strengthen the faithful fleets"),
    Synergy(frozenset({D.WAR, D.DEATH}), H.DEATH_TOLL, "Deaths in battle feed the god"),
    Synergy(frozenset({D.PLAGUE, D.DEATH}), H.PLAGUE_TITHE, "Outbreaks feed the god"),
    Synergy(frozenset({D.FIRE, D.CRAFT}), H.CRAFT_SKILL, "Crafts of fire are finer"),
    Synergy(frozenset({D.HARVEST, D.SUN}), H.HARVEST_FLOOR, "Fields of the faithful do not fail"),
    Synergy(frozenset({D.LOVE, D.LIFE}), H.FERTILITY, "Marriages bear more children"),
    Synergy(frozenset({D.LIES, D.TRICKERY}), H.SPY_DEPTH, "Spies of the faithful learn more"),
    Synergy(frozenset({D.ROAD, D.TRADE}), H.TRADE_GAIN, "Roads bring more trade"),
    Synergy(frozenset({D.STAR, D.KNOWLEDGE}), H.STARGAZING, "Watching the sky speeds research"),
    Synergy(frozenset({D.MEMORY, D.SOUND}), H.LEGEND_SPREAD, "Songs carry legends further"),
    Synergy(frozenset({D.OATH, D.WAR}), H.LEVY_MORALE, "Sworn armies hold together"),
    Synergy(frozenset({D.DREAM, D.SLEEP}), H.DREAM_SENDING, "Sleep brings more dreams"),
    Synergy(frozenset({D.STONE, D.BORDER}), H.BORDER_GUARD, "Walls hold longer"),
    Synergy(frozenset({D.HUNT, D.MOON}), H.HUNT_YIELD, "Night hunts bring back more"),
    Synergy(frozenset({D.ICE, D.SALT}), H.PRESERVATION, "Stores keep longer"),
)

SYNERGY_OF: MappingProxyType[frozenset[Domain], Synergy] = MappingProxyType({synergy.pair: synergy for synergy in SYNERGIES})

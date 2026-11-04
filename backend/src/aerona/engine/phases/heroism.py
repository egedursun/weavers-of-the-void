from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.ecology import BeastTemper
from aerona.domain.enums.entity import COMMUNITY_TYPES, SOCIETY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.mortal import DeathCause
from aerona.domain.enums.society import CreatureTrait
from aerona.domain.enums.war import WarCause
from aerona.domain.models.entity_stats import LegendStats
from aerona.engine.body.book import effective, strike_style
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.ecology.beasts import rob_hoard, wound_harm
from aerona.engine.economy.money import inject_hoard
from aerona.engine.economy.sanctity import holy_strike
from aerona.engine.gods.queries import community_of
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lifecycle.mortal_death import die
from aerona.engine.lifecycle.wounds import apply_hits, fatal_injury
from aerona.engine.mind.memories import remember
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, fraction, round_half_up
from aerona.engine.primitives.queries import active_bonds, add_flag, canon, close, connect, living_entity
from aerona.engine.primitives.records import RecordSpec, open_record, retire
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.primitives.strength import equipment, species_trait_bonus, weapon_power
from aerona.engine.primitives.thresholds import relative_threshold
from aerona.engine.services.war import declare_war

VICTORY_KINDS = (BondKind.KILLED, BondKind.BEAT)
CARRIER_BOND_KINDS = (BondKind.LIVES_IN, BondKind.DESCENDS_FROM)
EPIC_SUBTYPE = "age-changing epic"
BALLAD_SUBTYPE = "heroic ballad"
LAMENT_SUBTYPE = "lament"


class EncounterOutcome(StrEnum):
    KILLED = "killed"
    DROVE_BACK = "drove_back"
    REWOUND = "rewound"
    WOUNDED = "wounded"
    FELL = "fell"


@dataclass(frozen=True)
class EncounterResult:
    outcome: EncounterOutcome
    legend: EntityRow | None = None


async def monsters_of(ctx: TickContext, *, beasts: bool = True) -> list[EntityRow]:
    engine = ctx.rules.world_engine
    species = await canon(ctx.session, [EntityType.SPECIES])
    threshold = relative_threshold(species, "danger", fraction(engine.monster_top_pct), engine.monster_min_danger, engine.monster_always_danger)
    found = [creature for creature in species if (stat(creature, "danger") or 0) >= threshold(creature)]
    return found + (await wild_beasts(ctx) if beasts else [])


async def wild_beasts(ctx: TickContext) -> list[EntityRow]:
    held = select(BeastProfileRow.beast_entity_id).where(BeastProfileRow.temper.in_([BeastTemper.BOUND, BeastTemper.TAMED]))
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.BEAST, EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(held))
        .order_by(EntityRow.id)
    )
    return list(rows)


async def legend_carrier(ctx: TickContext, hero: EntityRow) -> EntityRow | None:
    location = await living_entity(ctx.session, hero.location_id)
    if location is not None and location.entity_type in COMMUNITY_TYPES:
        return location
    repository = BondRepository(ctx.session)
    bonds = [bond for kind in CARRIER_BOND_KINDS for bond in await repository.outgoing(hero.id, kind, active_only=False)]
    for bond in sorted(bonds, key=lambda item: (item.active, item.id), reverse=True):
        target = await living_entity(ctx.session, bond.target_node_id)
        if target is not None and target.entity_type in COMMUNITY_TYPES:
            return target
    return None


async def carry_legend(ctx: TickContext, hero: EntityRow, legend: EntityRow, description: str) -> None:
    carrier = await legend_carrier(ctx, hero)
    if carrier is not None:
        await connect(ctx.session, carrier.id, legend.id, BondKind.TELLS_OF, ctx.epoch, description=description)


async def _legend(ctx: TickContext, *, name: str, subtype: str, body: str, power: int, spread: int, subjects: list[EntityRow]) -> EntityRow:
    legend = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.LEGEND,
            name=name,
            body=body,
            stats=LegendStats(spread=spread),
            power=power,
            world_id=subjects[0].world_id,
            subtype=subtype,
        ),
    )
    for subject in subjects:
        await connect(ctx.session, legend.id, subject.id, BondKind.TELLS_OF, ctx.epoch)
    return legend


async def hero_power(ctx: TickContext, hero: EntityRow, patron: SonRow | None, roll: int) -> float:
    hunt = ctx.rules.world_hunt
    flags = await EntityRepository(ctx.session).flags(hero.id)
    intellect = await effective(ctx.session, hero, "intellect", rules=ctx.rules)
    total = (
        await effective(ctx.session, hero, "strength", rules=ctx.rules)
        + await effective(ctx.session, hero, "agility", rules=ctx.rules) / hunt.agility_divisor
        + intellect / hunt.intellect_divisor
    )
    total += roll * hunt.die_mult
    total += round_half_up(patron.charisma / hunt.patron_charisma_divisor) if patron is not None else 0
    total += await weapon_power(ctx.session, ctx.rules, hero.id, hunt.weapon_mult)
    if EntityFlag.WIZARD in flags:
        total += round_half_up(intellect / hunt.sorcerer_intellect_divisor)
    return total


async def monster_power(ctx: TickContext, monster: EntityRow, roll: int) -> float:
    hunt = ctx.rules.world_hunt
    flags = await EntityRepository(ctx.session).flags(monster.id)
    total = (stat(monster, "strength") or 0) + (stat(monster, "agility") or 0) / hunt.agility_divisor + (stat(monster, "danger") or 0) / hunt.danger_divisor
    total += roll * hunt.die_mult + await species_trait_bonus(ctx.session, ctx.rules, monster.id)
    if EntityFlag.MEGAFAUNA in flags:
        total += hunt.megafauna_bonus
    return total


async def _reward_weapon(ctx: TickContext, hero: EntityRow, monster: EntityRow) -> None:
    hunt = ctx.rules.world_hunt
    items = await equipment(ctx.session, hero.id)
    if not items:
        return
    weapon = max(items, key=lambda item: (stat(item, "damage") or 0, -item.id))
    set_stats(weapon, might=clamp_int((stat(weapon, "might") or 0) + hunt.weapon_might_gain, 0, PERCENT))
    await connect(ctx.session, weapon.id, monster.id, BondKind.BEAT, ctx.epoch, description=f"in the hands of {hero.name}")
    victories = len(await active_bonds(ctx.session, VICTORY_KINDS, sources=[weapon.id]))
    if victories >= hunt.legendary_weapon_victories and await add_flag(ctx.session, weapon.id, EntityFlag.LEGENDARY, ctx.epoch):
        weapon.power_level = min(hunt.power_cap, weapon.power_level + 1)
        await note(ctx, f"{weapon.name} became legendary after {victories} victories.", key="heroism.legendary_weapon", ids=[weapon.id, hero.id])


async def _hero_wins(ctx: TickContext, hero: EntityRow, monster: EntityRow, patron: SonRow | None, context: str) -> EncounterResult:
    hunt = ctx.rules.world_hunt
    repository = EntityRepository(ctx.session)
    monster_flags = await repository.flags(monster.id)
    danger = clamp_int((stat(monster, "danger") or 0) - hunt.defeat_danger_loss, 0, PERCENT)
    set_stats(monster, danger=danger)
    slain = monster.power_level >= hunt.singular_power or danger <= hunt.death_danger
    if slain and CreatureTrait.TIME_REWINDER in await repository.traits(monster.id) and EntityFlag.TIME_RETURNED not in monster_flags:
        set_stats(monster, danger=clamp_int(danger + hunt.rewind_danger_gain, 0, PERCENT))
        await add_flag(ctx.session, monster.id, EntityFlag.TIME_RETURNED, ctx.epoch)
        await note(ctx, f"{monster.name} died but rewound time; {hero.name} will see it once more.", key="heroism.rewind", ids=[monster.id, hero.id])
        slain = False
        rewound = True
    else:
        rewound = False
    if monster.entity_type is EntityType.BEAST:
        if slain:
            await connect(ctx.session, hero.id, monster.id, BondKind.KILLED, ctx.epoch, description="slew the beast")
        else:
            await remember(
                ctx.session,
                ctx.rules,
                holder_id=monster.id,
                subject_id=hero.id,
                kind=MemoryKind.HARMED_ME,
                magnitude=-PERCENT // 4,
                epoch=ctx.epoch,
                note="wounded it",
            )
            await rob_hoard(ctx, monster, hero)
            await apply_hits(
                ctx,
                monster,
                Harm(
                    wound_harm(ctx.rules, await ctx.session.get(BeastProfileRow, monster.id)),
                    HarmCause.MONSTER,
                    f"slain by {hero.name}",
                    killer_id=hero.id,
                    source_node_id=hero.id,
                ),
            )
    if slain:
        await retire(ctx.session, monster, ctx.epoch, f"Epoch {ctx.epoch}: killed by {hero.name}.")
        home = await community_of(ctx.session, hero)
        if (
            home is not None
            and home.entity_type in SOCIETY_TYPES
            and monster.entity_type is not EntityType.BEAST
            and ctx.rng(f"hoard.{monster.id}").chance(ctx.rules.money.beast_hoard_chance)
        ):
            await inject_hoard(ctx, home, ctx.rules.money.hoard_luxury_units, MaterialKind.GOLD)
    if slain and EntityFlag.MEGAFAUNA in monster_flags:
        hero.title = f"{monster.name} Slayer"
        await add_flag(ctx.session, hero.id, EntityFlag.AGE_CHANGER, ctx.epoch)
        hero.power_level = min(hunt.power_cap, hero.power_level + hunt.megafauna_slayer_power_gain)
        epic = await _legend(
            ctx,
            name=f"The Fall of {monster.name}",
            subtype=EPIC_SUBTYPE,
            body=f"{hero.name} slew {monster.name}, as old as the world. This death was the end of an age.",
            power=hunt.epic_power,
            spread=hunt.epic_spread,
            subjects=[hero, monster],
        )
        await carry_legend(ctx, hero, epic, "tells their epic")
        await note(
            ctx,
            f"{hero.name} slew the megafauna {monster.name}. The balance of the world changed; nothing will be the same again.",
            key="heroism.age_change",
            ids=[hero.id, monster.id, epic.id],
            kind=ChronicleKind.AGE_CHANGE,
        )
    set_stats(hero, charisma=clamp_int((stat(hero, "charisma") or 0) + hunt.victory_charisma, 0, PERCENT))
    if slain and not hero.title:
        hero.title = f"{monster.name} Slayer"
    await connect(ctx.session, hero.id, monster.id, BondKind.KILLED if slain else BondKind.BEAT, ctx.epoch, description=context)
    if patron is not None:
        patron.fame += hunt.patron_renown
        patron.xp += hunt.patron_xp
    await _reward_weapon(ctx, hero, monster)
    ballad: EntityRow | None = None
    if slain:
        ballad = await _legend(
            ctx,
            name=f"{hero.name} and {monster.name}",
            subtype=BALLAD_SUBTYPE,
            body=f"{hero.name}, {context}, killed {monster.name}. The mortals began to tell of it.",
            power=hunt.ballad_power,
            spread=hunt.ballad_spread,
            subjects=[hero, monster],
        )
        await carry_legend(ctx, hero, ballad, "sings their ballad")
    deed = "killed it" if slain else "drove it back"
    ids = [hero.id, monster.id] + ([ballad.id] if ballad is not None else [])
    await note(ctx, f"{hero.name}, {context}, faced {monster.name} and {deed}.", key="heroism.victory", ids=ids, son_id=patron.id if patron else None)
    ctx.count("hero_victories")
    if rewound:
        return EncounterResult(EncounterOutcome.REWOUND)
    return EncounterResult(EncounterOutcome.KILLED if slain else EncounterOutcome.DROVE_BACK, ballad)


async def _hero_loses(ctx: TickContext, hero: EntityRow, monster: EntityRow, patron: SonRow | None, context: str) -> EncounterResult:
    hunt = ctx.rules.world_hunt
    rng = ctx.rng(seed_of("armor", hero.id, monster.id))
    items = await equipment(ctx.session, hero.id)
    armor = max(items, key=lambda item: (stat(item, "protection") or 0, -item.id)) if items else None
    protection = stat(armor, "protection") or 0 if armor is not None else 0
    son_id = patron.id if patron is not None else None
    if (
        armor is not None
        and protection >= hunt.armor_save_min_protection
        and rng.chance(hunt.armor_save_base_pct + protection / hunt.armor_save_divisor * PERCENT)
    ):
        style = await strike_style(ctx.session, ctx.rules, monster, hero)
        if stat(hero, "hp") is None:
            set_stats(hero, hp=hunt.unknown_hp)
        await apply_hits(
            ctx, hero, Harm(hunt.armor_save_hp_loss, HarmCause.MONSTER, f"fell before {monster.name}", style=style, source_node_id=monster.id), lethal=False
        )
        set_stats(armor, protection=clamp_int(protection - hunt.armor_save_wear, 0, PERCENT))
        await declare_war(ctx, monster.id, hero.id, context, cause=WarCause.BEAST, world_cap=False)
        await note(
            ctx,
            f"{hero.name} was defeated by {monster.name} but {armor.name} saved them from death; they withdrew gravely wounded.",
            key="heroism.armor_save",
            ids=[hero.id, monster.id, armor.id],
            son_id=son_id,
        )
        return EncounterResult(EncounterOutcome.WOUNDED)
    style = await strike_style(ctx.session, ctx.rules, monster, hero)
    await fatal_injury(ctx, hero, Harm(hunt.armor_save_hp_loss, HarmCause.MONSTER, f"fell before {monster.name}", style=style, killer_id=monster.id))
    await die(ctx, hero, cause=f"fell before {monster.name}", manner=DeathCause.MONSTER, killer_id=monster.id, forced=True)
    lament = await _legend(
        ctx,
        name=f"Lament for {hero.name}",
        subtype=LAMENT_SUBTYPE,
        body=f"{hero.name}, {context}, gave their life before {monster.name}.",
        power=hunt.lament_power,
        spread=hunt.lament_spread,
        subjects=[hero],
    )
    await carry_legend(ctx, hero, lament, "sings their lament")
    await note(ctx, f"{hero.name}, {context}, fell before {monster.name}.", key="heroism.defeat", ids=[hero.id, monster.id, lament.id], son_id=son_id)
    ctx.count("hero_defeats")
    return EncounterResult(EncounterOutcome.FELL, lament)


async def encounter(ctx: TickContext, hero: EntityRow, monster: EntityRow, context: str) -> EncounterResult | None:
    if hero.status is not EntityStatus.CANON or monster.status is not EntityStatus.CANON:
        return None
    rng = ctx.rng(seed_of("encounter", hero.id, monster.id))
    patron = await living_patron(ctx.session, hero)
    hero_total = await hero_power(ctx, hero, patron, rng.die(ctx.rules.world_hunt.die)) * await holy_strike(ctx.session, ctx.rules, hero.id, monster)
    monster_total = await monster_power(ctx, monster, rng.die(ctx.rules.world_hunt.die))
    if hero_total >= monster_total:
        return await _hero_wins(ctx, hero, monster, patron, context)
    return await _hero_loses(ctx, hero, monster, patron, context)


ENCOUNTER_READS = (
    "table.house_members",
    "table.marriages",
    "table.mortal_profiles",
    "item.damage",
    "item.might",
    "item.protection",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "species.agility",
    "species.danger",
    "species.strength",
    "table.beast_profiles",
    "table.bodies",
    "table.bonds",
    "table.community_societies",
    "table.conditions",
    "table.cosmos",
    "table.designated_heirs",
    "table.entities",
    "table.entity_flags",
    "table.entity_tags",
    "table.entity_traits",
    "table.epoch_year_cursors",
    "table.holder_levels",
    "table.injuries",
    "table.language_profiles",
    "table.lexemes",
    "table.memories",
    "table.minds",
    "table.name_registry",
    "table.node_materials",
    "table.nodes",
    "table.people_biology",
    "table.people_culture",
    "table.personality_values",
    "table.polity_members",
    "table.prostheses",
    "table.routes",
    "table.skills",
    "table.spirit_profiles",
    "table.tradition_profiles",
    "table.traits",
    "table.world_maps",
    "table.world_materials",
)
ENCOUNTER_WRITES = (
    "table.mortal_profiles",
    "item.might",
    "item.protection",
    "mortal.charisma",
    "mortal.death_year",
    "mortal.hp",
    "species.danger",
    "table.bodies",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.memories",
    "table.name_registry",
    "table.sons",
    "table.spirit_profiles",
)


@reads(*ENCOUNTER_READS)
@writes(*ENCOUNTER_WRITES)
async def sworn_hunts(ctx: TickContext) -> None:
    for bond in await active_bonds(ctx.session, [BondKind.HUNTS]):
        hunter = await living_entity(ctx.session, bond.source_node_id)
        prey = await living_entity(ctx.session, bond.target_node_id)
        if hunter is None or prey is None or hunter.entity_type is not EntityType.MORTAL or prey.entity_type is not EntityType.SPECIES:
            continue
        await close(ctx.session, bond, ctx.epoch, "sworn hunt")
        await encounter(ctx, hunter, prey, "in a sworn hunt")


@reads(*ENCOUNTER_READS)
@writes(*ENCOUNTER_WRITES)
async def glory_hunts(ctx: TickContext) -> None:
    engine = ctx.rules.world_engine
    rng = ctx.rng()
    atlas = await RegionAtlas.load(ctx.session)
    monsters = await monsters_of(ctx)
    for hero in await canon(ctx.session, [EntityType.MORTAL]):
        if (
            hero.status is not EntityStatus.CANON
            or await effective(ctx.session, hero, "strength", rules=ctx.rules) + await effective(ctx.session, hero, "agility", rules=ctx.rules)
            < engine.hunter_strength_agility
        ):
            continue
        beaten = {bond.target_node_id for bond in await active_bonds(ctx.session, VICTORY_KINDS, sources=[hero.id])}
        prey = [
            monster
            for monster in monsters
            if monster.status is EntityStatus.CANON
            and monster.id not in beaten
            and atlas.distance(hero.id, monster.id) <= ctx.rules.world_effects.hunt_distance
        ]
        chosen = await EntityRepository(ctx.session).has_flag(hero.id, EntityFlag.CHOSEN)
        if not prey or not rng.chance(engine.hunt_chosen_chance if chosen else engine.hunt_chance):
            continue
        await encounter(ctx, hero, rng.pick(prey), "in pursuit of glory")


async def send_hero_to_hunt(ctx: TickContext, hero_id: int, monster_id: int) -> EncounterResult:
    hero = await living_entity(ctx.session, hero_id)
    monster = await living_entity(ctx.session, monster_id)
    if hero is None or hero.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only a living mortal can be sent on a hunt.")
    if monster is None or monster.entity_type is not EntityType.SPECIES:
        raise ValidationFailedError("A hunt needs a living species as prey.")
    result = await encounter(ctx, hero, monster, "at the bidding of the gods")
    if result is None:
        raise ValidationFailedError("The hunt could not take place.")
    return result


PHASES = (Phase("sworn_hunts", sworn_hunts), Phase("glory_hunts", glory_hunts))

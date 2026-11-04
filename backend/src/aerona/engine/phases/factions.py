from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.constants.warfare import FACTION_NAME_TEMPLATE
from aerona.core.errors import ConflictError, ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import SOCIETY_TYPES, EngineKind, EntityStatus, EntityType
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.context import TickContext
from aerona.engine.demography.recruitment import founding_factor, recruit
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.drives import faction_drive
from aerona.engine.phase import Phase
from aerona.engine.phases.warfare import is_uprising
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon, living_entity, spoken_language
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import stat
from aerona.engine.services.war import ongoing_war_count
from aerona.rules.registry import Rules


class FactionKind(StrEnum):
    GUILD = "guild"
    COUNCIL = "council"
    BROTHERHOOD = "brotherhood"


@dataclass(frozen=True)
class FactionBlueprint:
    kind: FactionKind
    engine_kind: EngineKind
    subtype: str
    suffix: str
    members: str


BLUEPRINTS = (
    FactionBlueprint(FactionKind.GUILD, EngineKind.MERCHANT_GUILD, "merchant guild", "Guild", "merchants"),
    FactionBlueprint(FactionKind.COUNCIL, EngineKind.PRIESTS_COUNCIL, "priests' council", "Priests' Council", "priests"),
    FactionBlueprint(FactionKind.BROTHERHOOD, EngineKind.WARRIOR_BAND, "warrior brotherhood", "Warrior Brotherhood", "warriors"),
)


def blueprint(kind: FactionKind) -> FactionBlueprint:
    return next(item for item in BLUEPRINTS if item.kind is kind)


def base_stats(rules: Rules, kind: FactionKind) -> tuple[int, int, int]:
    factions = rules.factions
    return {
        FactionKind.GUILD: (factions.guild_strength, factions.guild_wealth, factions.guild_sway),
        FactionKind.COUNCIL: (factions.council_strength, factions.council_wealth, factions.council_sway),
        FactionKind.BROTHERHOOD: (factions.brotherhood_strength, factions.brotherhood_wealth, factions.brotherhood_sway),
    }[kind]


async def _note(ctx: TickContext, text: str, key: str, ids: tuple[int, ...]) -> None:
    await ctx.chronicle(ChronicleKind.CIVILIZATION, text, template_key=key, entity_ids=ids)


async def disband_uprisings(ctx: TickContext) -> int:
    rules = ctx.rules.factions
    rng = ctx.rng("disband")
    bonds = BondRepository(ctx.session)
    disbanded = 0
    for faction in await canon(ctx.session, [EntityType.FACTION]):
        if not is_uprising(faction) or ctx.epoch - faction.birth_epoch < rules.revolt_disband_min_age:
            continue
        if await bonds.outgoing(faction.id, BondKind.ENEMY) or await bonds.incoming(faction.id, BondKind.ENEMY) or not rng.chance(rules.revolt_disband_chance):
            continue
        await retire_in(ctx, faction, "the uprising died out; the rebels dispersed or melted back into the people", close_bonds=True)
        if disbanded < rules.revolt_disband_note_cap:
            await _note(ctx, f"{faction.name} died out; the rebels buried their weapons and went home.", "faction.uprising_disbanded", (faction.id,))
        disbanded += 1
    return disbanded


async def _existing(ctx: TickContext, community_id: int, engine_kind: EngineKind) -> bool:
    statement = select(EntityRow.id).where(
        EntityRow.entity_type == EntityType.FACTION,
        EntityRow.status == EntityStatus.CANON,
        EntityRow.engine_kind == engine_kind,
        EntityRow.affiliated_entity_id == community_id,
    )
    return await ctx.session.scalar(statement.limit(1)) is not None


async def eligible_kinds(ctx: TickContext, community: EntityRow) -> list[FactionKind]:
    rules = ctx.rules.factions
    shares = await class_shares(ctx.session, ctx.rules, community.id)
    bonds = BondRepository(ctx.session)
    kinds: list[FactionKind] = []
    trade = bool(await bonds.outgoing(community.id, BondKind.TRADES_WITH) or await bonds.incoming(community.id, BondKind.TRADES_WITH))
    if shares[SocialClass.MERCHANT] >= rules.guild_min_merchant_pct and trade and (stat(community, "prosperity") or 0) >= rules.guild_min_prosperity:
        kinds.append(FactionKind.GUILD)
    if shares[SocialClass.PRIEST] >= rules.council_min_priest_pct and await bonds.patron(community.id) is not None:
        kinds.append(FactionKind.COUNCIL)
    warriors = shares[SocialClass.WARRIOR]
    at_war = await ongoing_war_count(ctx.session, community.id) > 0
    if warriors >= rules.brotherhood_min_warrior_pct or (at_war and warriors >= rules.brotherhood_at_war_min_warrior_pct):
        kinds.append(FactionKind.BROTHERHOOD)
    return [kind for kind in kinds if not await _existing(ctx, community.id, blueprint(kind).engine_kind)]


async def found_faction(ctx: TickContext, community: EntityRow, kind: FactionKind) -> EntityRow:
    rules = ctx.rules.factions
    plan = blueprint(kind)
    rng = ctx.rng("faction_stats")
    strength, wealth, sway = (
        clamp_int(base + rng.die(rules.faction_stat_die) - rules.faction_stat_shift, 0, PERCENT_MAX) for base in base_stats(ctx.rules, kind)
    )
    power = clamp_int(
        round_half_up(community.power_level * rules.faction_power_share_pct / PERCENT) + 1, ctx.rules.deep_life.derived_min_power, rules.faction_max_power
    )
    faction = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.FACTION,
            name=FACTION_NAME_TEMPLATE.format(root=community.name, suffix=plan.suffix),
            body=f"The {plan.members} of {community.name} organised among themselves.",
            stats=FactionStats(strength=strength, wealth=wealth, sway=sway),
            power=power,
            location_id=community.id if community.entity_type is EntityType.SETTLEMENT else community.location_id,
            world_id=community.world_id,
            subtype=plan.subtype,
            engine_kind=plan.engine_kind,
        ),
    )
    faction.affiliated_entity_id = community.id
    bonds = BondRepository(ctx.session)
    await bonds.connect(BondDraft(faction.id, community.id, BondKind.DESCENDS_FROM, ctx.epoch, "born from within"))
    language = await spoken_language(ctx.session, community.id)
    if language is not None and language.status is EntityStatus.CANON:
        await bonds.connect(BondDraft(faction.id, language.id, BondKind.SPEAKS, ctx.epoch, f"the tongue of {community.name}"))
    patron = await bonds.patron(community.id)
    if patron is not None:
        await bonds.connect(BondDraft(faction.id, patron, BondKind.WORSHIPS, ctx.epoch, f"the faith of {community.name}"))
    await _note(ctx, f"A {plan.subtype} was founded in {community.name}.", f"faction.founded_{kind.value}", (faction.id, community.id))
    ctx.count("factions_founded")
    return faction


async def found_factions(ctx: TickContext) -> int:
    rules = ctx.rules.factions
    rng = ctx.rng("founding")
    founded = 0
    for community in await canon(ctx.session, SOCIETY_TYPES):
        if founded >= rules.faction_cap:
            break
        if (stat(community, "population") or 0) < rules.faction_min_population:
            continue
        kinds = await eligible_kinds(ctx, community)
        discontent = await founding_factor(ctx.session, ctx.rules, community.id, blueprint(kinds[0]).engine_kind) if kinds else 1.0
        if not rng.chance(rules.faction_chance * await faction_drive(ctx.session, ctx.rules, community.id) * discontent):
            continue
        if kinds:
            await found_faction(ctx, community, kinds[0])
            founded += 1
    return founded


@reads(
    "faction.strength",
    "people.population",
    "people.prosperity",
    "settlement.population",
    "settlement.prosperity",
    "table.bonds",
    "table.community_societies",
    "table.epoch_year_cursors",
    "table.name_registry",
    "table.nodes",
    "table.pressures",
    "table.routes",
    "table.war_sides",
    "table.wars",
)
@writes(
    "faction.strength",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
)
async def factions(ctx: TickContext) -> None:
    ctx.count("uprisings_disbanded", await disband_uprisings(ctx))
    ctx.count("faction_recruits", await recruit(ctx))
    await found_factions(ctx)


async def decree_faction(ctx: TickContext, community_id: int, kind: FactionKind) -> EntityRow:
    community = await living_entity(ctx.session, community_id)
    if community is None or community.entity_type not in SOCIETY_TYPES:
        raise ValidationFailedError("Factions are founded inside a living people or settlement.")
    if await _existing(ctx, community.id, blueprint(kind).engine_kind):
        raise ConflictError(f"{community.name} already has a {blueprint(kind).subtype}.")
    return await found_faction(ctx, community, kind)


async def dissolve_faction(ctx: TickContext, faction_id: int) -> EntityRow:
    faction = await living_entity(ctx.session, faction_id)
    if faction is None or faction.entity_type is not EntityType.FACTION:
        raise ValidationFailedError("Only a living faction can be dissolved.")
    await retire_in(ctx, faction, "dissolved by decree", close_bonds=True)
    await _note(ctx, f"{faction.name} was dissolved; its members went their own ways.", "faction.dissolved", (faction.id,))
    return faction


PHASES = (Phase("factions", factions),)

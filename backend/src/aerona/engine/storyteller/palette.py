from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.base import Base
from aerona.db.tables.concealment import HiddenTruthRow
from aerona.db.tables.divine import NaturalLawProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import HouseholdRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.living import LivingLineRow
from aerona.db.tables.made import ReplicatorLineRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.networks import NetworkNodeRow
from aerona.db.tables.powers import PowerRow, PowerSourceRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.storyteller import StorytellerRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.enums.storyteller import PaletteDirection, PaletteSubsystem, RecoveryKind, SpontaneousKind, TensionBand
from aerona.engine.context import TickContext

P = PaletteSubsystem
D = PaletteDirection
E = EntityType
WAR_BAN = (NaturalLaw.WAR_BAN,)


@dataclass(frozen=True)
class PaletteEntry:
    key: str
    subsystem: PaletteSubsystem
    direction: PaletteDirection
    struck: tuple[str, ...]
    magnitude: int
    tension_weight: int
    entity: EntityType | None = None
    table: type[Base] | None = None
    excluded_by: tuple[NaturalLaw, ...] = ()


def entry(key: str, subsystem: P, direction: D, struck: tuple[str, ...], *, magnitude: int = 10, weight: int = 10, **cause: object) -> PaletteEntry:
    entity = cause.get("entity")
    table = cause.get("table")
    excluded = cause.get("excluded_by", ())
    return PaletteEntry(
        key,
        subsystem,
        direction,
        struck,
        magnitude,
        weight,
        entity if isinstance(entity, EntityType) else None,
        table if isinstance(table, type) else None,
        tuple(excluded) if isinstance(excluded, tuple) else (),
    )


PALETTE: tuple[PaletteEntry, ...] = (
    entry(
        SpontaneousKind.BEAST_AWAKENING.value,
        P.ECOLOGY,
        D.DISRUPTION,
        ("monsters.emerged", "monsters.void_roamed", "pantheon.sleeper_woke"),
        entity=E.SPECIES,
    ),
    entry(
        SpontaneousKind.RAID.value,
        P.WAR,
        D.DISRUPTION,
        ("vendetta.raid", "faction.raid", "monsters.raid"),
        entity=E.SETTLEMENT,
        excluded_by=WAR_BAN,
    ),
    entry(SpontaneousKind.COMET.value, P.COSMOS, D.DISRUPTION, ("sky.", "feature.comet_returned"), weight=5),
    entry(
        SpontaneousKind.PLAGUE.value,
        P.DISEASE,
        D.DISRUPTION,
        ("disasters.plague", "disasters.city_plague", "disasters.plague_spread"),
        entity=E.SETTLEMENT,
    ),
    entry(SpontaneousKind.CLAIMANT.value, P.IDEOLOGY, D.DISRUPTION, ("polity.usurper_accepted", "titles.usurped", "polity.coup"), entity=E.POLITY),
    entry(
        RecoveryKind.HARVEST.value,
        P.ECONOMY,
        D.RECOVERY,
        ("gatherings.harvest", "storyteller.harvest"),
        entity=E.SETTLEMENT,
        excluded_by=(NaturalLaw.DROUGHT,),
    ),
    entry(RecoveryKind.PEACE_ENVOY.value, P.WAR, D.RECOVERY, ("diplomacy.peace", "diplomacy.treaty"), table=WarRow),
    entry(RecoveryKind.HEALER_BIRTH.value, P.DISEASE, D.RECOVERY, ("births.healer",), entity=E.MORTAL),
    entry(
        "war_outbreak",
        P.WAR,
        D.DISRUPTION,
        ("war.declared", "war.battle"),
        magnitude=20,
        weight=20,
        entity=E.POLITY,
        excluded_by=WAR_BAN,
    ),
    entry("schism", P.FAITH, D.DISRUPTION, ("faith.schism", "faith.heresy"), entity=E.CULT),
    entry("revival", P.FAITH, D.RECOVERY, ("faith.revival", "faith.conversion"), entity=E.CULT),
    entry("market_crash", P.ECONOMY, D.DISRUPTION, ("finance.crash", "economy.famine"), entity=E.SETTLEMENT),
    entry("die_off", P.ECOLOGY, D.DISRUPTION, ("ecology.extinct", "ecology.collapse"), entity=E.SPECIES),
    entry("renewal", P.ECOLOGY, D.RECOVERY, ("ecology.recovered", "ecology.spread"), entity=E.SPECIES),
    entry("cure_found", P.DISEASE, D.RECOVERY, ("disease.cured", "disease.ended"), entity=E.DISEASE),
    entry("hard_season", P.CLIMATE, D.DISRUPTION, ("climate.", "disasters.drought"), entity=E.SETTLEMENT),
    entry("mild_season", P.CLIMATE, D.RECOVERY, ("climate.mild",), entity=E.SETTLEMENT),
    entry("sky_event", P.COSMOS, D.DISRUPTION, ("cosmos.", "heavens."), weight=5),
    entry("mind_unrest", P.MADE_MINDS, D.DISRUPTION, ("minds.revolt", "minds.unbound"), table=MindProfileRow),
    entry("mind_accord", P.MADE_MINDS, D.RECOVERY, ("minds.accord", "minds.freed"), table=MindProfileRow),
    entry("network_outage", P.NETWORKS, D.DISRUPTION, ("networks.outage", "networks.cut"), table=NetworkNodeRow),
    entry("network_repair", P.NETWORKS, D.RECOVERY, ("networks.repaired",), table=NetworkNodeRow),
    entry("replicator_bloom", P.REPLICATORS, D.DISRUPTION, ("replicators.spread",), table=ReplicatorLineRow),
    entry("replicator_contained", P.REPLICATORS, D.RECOVERY, ("replicators.contained",), table=ReplicatorLineRow),
    entry("power_surge", P.POWERS, D.DISRUPTION, ("powers.surge", "powers.wild"), table=PowerRow),
    entry("power_mastery", P.POWERS, D.RECOVERY, ("powers.mastered",), table=PowerRow),
    entry("source_failing", P.SOURCES, D.DISRUPTION, ("sources.failing", "sources.dried"), table=PowerSourceRow),
    entry("source_renewed", P.SOURCES, D.RECOVERY, ("sources.renewed",), table=PowerSourceRow),
    entry("truth_exposed", P.CONCEALMENT, D.DISRUPTION, ("truths.revealed", "concealment.exposed"), table=HiddenTruthRow),
    entry("truth_kept", P.CONCEALMENT, D.RECOVERY, ("truths.kept",), table=HiddenTruthRow),
    entry("line_drift", P.LIVING_CRAFT, D.DISRUPTION, ("living.drift", "living.escaped"), table=LivingLineRow),
    entry("line_steadied", P.LIVING_CRAFT, D.RECOVERY, ("living.steadied",), table=LivingLineRow),
    entry("god_quarrel", P.GODS, D.DISRUPTION, ("divine.duel", "divine.feud", "divine.league"), table=SonRow),
    entry("god_accord", P.GODS, D.RECOVERY, ("divine.pact", "council."), table=SonRow),
    entry("outer_horror", P.OUTER_BEINGS, D.DISRUPTION, ("horror.",), magnitude=15, weight=15),
    entry("outer_sealed", P.OUTER_BEINGS, D.RECOVERY, ("horror.sealed", "rifts.sealed"), entity=E.OUTER_BEING),
    entry("household_strife", P.HOUSEHOLDS, D.DISRUPTION, ("households.split", "households.feud"), table=HouseholdRow),
    entry("household_union", P.HOUSEHOLDS, D.RECOVERY, ("households.joined", "unions."), table=HouseholdRow),
    entry("exodus", P.MIGRATION, D.DISRUPTION, ("migration.flight", "migration.exodus"), entity=E.PEOPLE),
    entry("homecoming", P.MIGRATION, D.RECOVERY, ("migration.return", "migration.settled"), entity=E.PEOPLE),
    entry("ideology_rising", P.IDEOLOGY, D.DISRUPTION, ("ideology.spread", "polity.revolt"), entity=E.IDEOLOGY),
    entry("ideology_settles", P.IDEOLOGY, D.RECOVERY, ("ideology.accepted",), entity=E.IDEOLOGY),
    entry("art_scandal", P.ART, D.DISRUPTION, ("art.banned", "art.destroyed"), entity=E.ARTWORK),
    entry("art_flowering", P.ART, D.RECOVERY, ("art.made", "art.masterwork"), entity=E.ARTWORK),
)
BY_KEY: Mapping[str, PaletteEntry] = {item.key: item for item in PALETTE}
BAND_DIRECTION: Mapping[TensionBand, PaletteDirection | None] = {
    TensionBand.QUIET: PaletteDirection.DISRUPTION,
    TensionBand.HEATED: PaletteDirection.RECOVERY,
    TensionBand.IN_BAND: None,
}


async def cause_holds(ctx: TickContext, world_id: int, item: PaletteEntry, laws: set[NaturalLaw]) -> bool:
    if laws & set(item.excluded_by):
        return False
    if item.entity is not None:
        here = select(func.count(EntityRow.id)).where(
            EntityRow.world_id == world_id, EntityRow.entity_type == item.entity, EntityRow.status == EntityStatus.CANON
        )
        return int(await ctx.session.scalar(here) or 0) > 0
    if item.table is not None:
        return int(await ctx.session.scalar(select(func.count()).select_from(item.table)) or 0) > 0
    return True


async def world_laws(ctx: TickContext, world_id: int) -> set[NaturalLaw]:
    laws = select(NaturalLawProfileRow.effect).join(EntityRow, EntityRow.id == NaturalLawProfileRow.law_entity_id).where(EntityRow.world_id == world_id)
    return set(await ctx.session.scalars(laws))


async def subsystem_activity(ctx: TickContext, world_id: int) -> Counter[PaletteSubsystem]:
    since = ctx.epoch - ctx.rules.storyteller.variety_window
    keys = await ctx.session.scalars(select(IncidentRow.kind).where(IncidentRow.epoch >= since, IncidentRow.world_id == world_id))
    acted: Counter[PaletteSubsystem] = Counter()
    for key in keys:
        for item in PALETTE:
            if key.startswith(item.struck):
                acted[item.subsystem] += 1
    return acted


async def keep_palette(ctx: TickContext, row: StorytellerRow) -> dict[str, int]:
    table = ctx.rules.storyteller
    laws = await world_laws(ctx, row.world_id)
    acted = await subsystem_activity(ctx, row.world_id)
    favoured = BAND_DIRECTION[row.band]
    weights: dict[str, int] = {}
    for item in PALETTE:
        if not await cause_holds(ctx, row.world_id, item, laws):
            continue
        rest = max(0, table.variety_window - acted[item.subsystem]) * table.palette_rest_pct // table.variety_window
        lean = table.palette_lean_pct * (item.tension_weight + item.magnitude) // PERCENT if item.direction is favoured else 0
        weights[item.key] = PERCENT + rest + lean
    if "palette" not in row.locked:
        row.palette = weights
    return row.palette


def weight_of(row: StorytellerRow, key: str) -> float:
    palette = row.palette or {}
    return palette.get(key, PERCENT) / PERCENT

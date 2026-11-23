from dataclasses import dataclass

from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow
from aerona.db.write_guard import held
from aerona.domain.enums.faction import FactionKind, FactionRank
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.law.appeals import AppealTally, hear_appeals
from aerona.engine.law.jurisdictions import JurisdictionTally, press_claims
from aerona.engine.law.outlawry import OutlawTally, band_candidates, hunt_outlaws
from aerona.engine.law.pardons import PardonTally, grant_pardons
from aerona.engine.law.prisons import PrisonTally, keep_prisons
from aerona.engine.law.registries import RegistryTally, keep_registries
from aerona.engine.law.systems import SystemTally, adopt_systems, drift_precedents
from aerona.engine.military.mole_hunts import MoleTally, hunt_moles
from aerona.engine.military.spy_depth import CellTally, tend_cells
from aerona.engine.military.templates import seat_of
from aerona.engine.mythic.divine_spies import DivineSpyTally, spy_for_gods
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count
from aerona.engine.phases.factions import found_faction


@dataclass
class BandTally:
    bands: int = 0


@reads("table.entities", "table.holder_techniques", "table.legal_systems", "table.nodes", "table.polity_profiles", "table.precedents")
@writes("table.legal_systems", "table.precedents")
async def legal_systems(ctx: TickContext) -> None:
    tally = SystemTally()
    await adopt_systems(ctx, tally)
    await drift_precedents(ctx, tally)
    count(ctx, "legal_system", tally)


@reads("table.appeals", "table.crime_cases", "table.node_births")
@writes(
    "table.appeals",
    "table.chronicle",
    "table.chronicle_entities",
    "table.crime_cases",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
)
async def appeals(ctx: TickContext) -> None:
    tally = AppealTally()
    await hear_appeals(ctx, tally)
    count(ctx, "appeal", tally)


@reads(
    "table.blueprints",
    "table.company_profiles",
    "table.designs",
    "table.entities",
    "table.holder_techniques",
    "table.incorporeal_rights",
    "table.living_lines",
    "table.memberships",
    "table.mind_profiles",
    "table.mortal_profiles",
    "table.nodes",
    "table.polity_members",
    "table.registries",
)
@writes("table.registries")
async def registries(ctx: TickContext) -> None:
    tally = RegistryTally()
    await keep_registries(ctx, tally)
    count(ctx, "registry", tally)


@reads("table.entities", "table.faction_profiles", "table.jurisdictions", "table.nodes", "table.polity_members", "table.polity_profiles", "table.trading_posts")
@writes("table.jurisdictions")
async def jurisdictions(ctx: TickContext) -> None:
    tally = JurisdictionTally()
    await press_claims(ctx, tally)
    count(ctx, "jurisdiction", tally)


@reads(
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.incident_participants",
    "table.incidents",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.outlaws",
    "table.pardons",
    "table.prisoners",
    "table.sons",
    "table.stars",
    "table.war_sides",
    "table.wars",
    "table.worlds",
)
@writes(
    "table.chronicle", "table.chronicle_entities", "table.incident_facts", "table.incident_participants", "table.incidents", "table.outlaws", "table.pardons"
)
async def pardons(ctx: TickContext) -> None:
    tally = PardonTally()
    await grant_pardons(ctx, tally)
    count(ctx, "pardon", tally)


async def form_bands(ctx: TickContext, tally: BandTally) -> None:
    for polity_id, rows in (await band_candidates(ctx)).items():
        members = {row.mortal_entity_id for row in rows}
        joined = await ctx.session.scalar(select(FactionMembershipRow.faction_entity_id).where(FactionMembershipRow.mortal_entity_id.in_(members)).limit(1))
        seat = await seat_of(ctx, polity_id)
        if joined is not None or seat is None or held(seat.id):
            continue
        band = await found_faction(ctx, seat, FactionKind.BANDITS)
        for mortal_id in sorted(members):
            ctx.session.add(
                FactionMembershipRow(faction_entity_id=band.id, mortal_entity_id=mortal_id, rank=FactionRank.MEMBER, joined_epoch=ctx.epoch, locked=[])
            )
            outlaw = await ctx.session.get(EntityRow, mortal_id)
            if outlaw is not None:
                outlaw.affiliated_entity_id = band.id
        tally.bands += 1
    await ctx.session.flush()


@reads("table.outlaws")
@writes("table.outlaws")
async def outlawry(ctx: TickContext) -> None:
    tally = OutlawTally()
    await hunt_outlaws(ctx, tally)
    count(ctx, "outlaw", tally)
    bands = BandTally()
    await form_bands(ctx, bands)
    count(ctx, "outlaw_band", bands)


@reads("table.prisoners", "table.prisons", "table.structure_profiles")
@writes("table.prisoners", "table.prisons")
async def prisons(ctx: TickContext) -> None:
    tally = PrisonTally()
    await keep_prisons(ctx, tally)
    count(ctx, "prison", tally)


@reads(
    "table.defections",
    "table.mind_facets",
    "table.mortal_profiles",
    "table.node_births",
    "table.offices",
    "table.secrets",
    "table.spy_agents",
    "table.spy_cells",
    "table.spy_networks",
    "table.thoughts",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.defections",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.mortal_profiles",
    "table.spy_agents",
    "table.spy_cells",
    "table.spy_networks",
    "table.thoughts",
)
async def spy_cells(ctx: TickContext) -> None:
    tally = CellTally()
    await tend_cells(ctx, tally)
    count(ctx, "spy_cell", tally)


@reads("table.mole_hunts", "table.offices")
@writes("table.mole_hunts")
async def mole_hunts(ctx: TickContext) -> None:
    tally = MoleTally()
    await hunt_moles(ctx, tally)
    count(ctx, "mole_hunt", tally)


@reads("table.servitors")
async def divine_spies(ctx: TickContext) -> None:
    tally = DivineSpyTally()
    await spy_for_gods(ctx, tally)
    count(ctx, "divine_spy", tally)


PHASES = (
    Phase("legal_systems", legal_systems),
    Phase("appeals", appeals),
    Phase("registries", registries),
    Phase("jurisdictions", jurisdictions),
    Phase("pardons", pardons),
    Phase("outlawry", outlawry),
    Phase("prisons", prisons),
    Phase("spy_cells", spy_cells),
    Phase("mole_hunts", mole_hunts),
    Phase("divine_spies", divine_spies),
)

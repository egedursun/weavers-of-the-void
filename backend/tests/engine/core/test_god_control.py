import traceback
from collections import Counter
from collections.abc import Callable
from dataclasses import fields, replace
from typing import Any

from sqlalchemy import event, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState, Session, object_mapper

from aerona.db.base import Base
from aerona.db.profile_guard import owned_shape, owner_ids, profile_mapper
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.session import Database
from aerona.db.tables.culture import IdeologyAdherentRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.faith import SpiritProfileRow
from aerona.db.tables.military import SpyNetworkRow
from aerona.db.tables.warfare import SiegeRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import CurseKind, IdeologyTenet
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.faith import SpiritAlignment
from aerona.domain.enums.intrigue import PlotKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.models.entity_stats import BeastStats, FactionStats, ItemStats, PeopleStats, SpeciesStats, SpiritStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.foreign_gods import NewForeignGod, add_foreign_god
from aerona.engine.disease.control import DiseaseDesign, create_disease
from aerona.engine.ecology.beasts import profile_beast
from aerona.engine.interconnect.guards import run_guarded
from aerona.engine.intrigue.schemes import begin_scheme
from aerona.engine.lore import items
from aerona.engine.lore.control import create_lore
from aerona.engine.phases.native_faith import syncretize
from aerona.engine.pipeline import all_phases, current_environment, simulate
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.sides import SideIndex
from aerona.engine.services.war import open_war, raise_army, take_captive
from aerona.engine.services.war_geography import Neighbourhood
from aerona.rules.model import RULE_METADATA_KEY, rule_meta
from aerona.rules.registry import Rules
from tests.engine.core.factories import entity, mortal, settlement
from tests.engine.integration.factories import RichCosmos, seed_rich_cosmos
from tests.engine.lore.test_every_lore_kind import FIRST_VALUES

BLOCK_EVERY_NODE = -1
CERTAIN = 100
DATACLASS_FIELDS = "__dataclass_fields__"
WARM_EPOCHS = 2
ENGINE_MARK = "/aerona/engine/"
HELPER_MARKS = ("/engine/notes.py", "/engine/context.py", "/engine/primitives/", "/engine/interconnect/guards.py")


def table_of(row: object) -> str:
    return str(getattr(type(row), "__tablename__", type(row).__name__))


def tied_to_a_node(row: object) -> bool:
    shape = owned_shape(object_mapper(row))
    return shape is not None and bool(owner_ids(row, shape))


def owned_table(name: str) -> bool:
    mapper = profile_mapper(name)
    return mapper is not None and owned_shape(mapper) is not None


def origin() -> str:
    frames = [frame for frame in traceback.extract_stack() if ENGINE_MARK in frame.filename and not any(mark in frame.filename for mark in HELPER_MARKS)]
    return " > ".join(f"{frame.filename.split(ENGINE_MARK)[-1]}:{frame.lineno}:{frame.name}" for frame in frames[-3:]) or "?"


class Watcher:
    def __init__(self) -> None:
        self.changes: Counter[str] = Counter()
        self.origins: dict[int, str] = {}

    def pending(self, _session: Session, row: object) -> None:
        self.origins[id(row)] = origin()

    def after_flush(self, session: Session, _context: object) -> None:
        for row in session.new:
            if tied_to_a_node(row):
                self.changes[f"created {table_of(row)} at {self.origins.get(id(row), '?')}"] += 1
        for row in session.deleted:
            if tied_to_a_node(row):
                self.changes[f"deleted {table_of(row)}"] += 1
        for row in session.dirty:
            if tied_to_a_node(row):
                for attribute in inspect(row).attrs:
                    if attribute.history.has_changes():
                        self.changes[f"changed {table_of(row)}.{attribute.key}"] += 1

    def statement(self, state: ORMExecuteState) -> Any:
        if not (state.is_insert or state.is_update or state.is_delete):
            return None
        result = state.invoke_statement()
        table = getattr(getattr(state.statement, "table", None), "name", "")
        if getattr(result, "rowcount", 0) and owned_table(table):
            self.changes[f"bulk write to {table} at {origin()}"] += 1
        return result


def eager(rules: Rules) -> Rules:
    changes: dict[str, Any] = {}
    for space in fields(rules):
        table: Any = getattr(rules, space.name)
        if not hasattr(table, DATACLASS_FIELDS):
            continue
        sure = {
            definition.name: min(CERTAIN, rule_meta(definition).maximum)
            for definition in fields(table)
            if RULE_METADATA_KEY in definition.metadata and (definition.name.endswith("_chance") or rule_meta(definition).label.startswith("Chance"))
        }
        if sure:
            changes[space.name] = replace(table, **sure)
    return replace(rules, **changes)


async def run_watched(database: Database, phase_name: str, only: int) -> tuple[Counter[str], str | None]:
    phase = next(item for item in all_phases() if item.name == phase_name)
    environment = await current_environment(database)
    if only == BLOCK_EVERY_NODE:
        environment = replace(environment, rules=eager(environment.rules))
    watcher = Watcher()
    listeners: list[tuple[str, Callable[..., Any]]] = [
        ("transient_to_pending", watcher.pending),
        ("after_flush", watcher.after_flush),
        ("do_orm_execute", watcher.statement),
    ]
    error: str | None = None
    async with database.write() as session:
        nested = await session.begin_nested()
        for name, listener in listeners:
            event.listen(session.sync_session, name, listener)
        try:
            await run_guarded(phase, TickContext(environment, session, phase.name), only=only)
            await session.flush()
        except Exception as failure:
            error = f"{type(failure).__name__}: {failure}"
        finally:
            for name, listener in listeners:
                event.remove(session.sync_session, name, listener)
            await nested.rollback()
            await session.rollback()
    return watcher.changes, error


async def stir(session: AsyncSession, cosmos: RichCosmos) -> None:
    home = cosmos.home
    ctx = await manual_context(session, "stir")
    creed = await create_lore(
        ctx,
        EntityType.IDEOLOGY,
        name="Stirring Creed",
        description="",
        world_id=home.world.id,
        location_id=None,
        power=3,
        values={"tenets": [IdeologyTenet.EGALITARIANISM.value]},
    )
    communities = list(await session.scalars(select(EntityRow.id).where(EntityRow.entity_type.in_(list(COMMUNITY_TYPES)), EntityRow.world_id == home.world.id)))
    for community_id in communities[:2]:
        session.add(IdeologyAdherentRow(ideology_entity_id=creed.id, adherent_entity_id=community_id, strength=90))
    god = await add_foreign_god(session, ctx.rules, ctx.rng(), ctx.epoch, NewForeignGod("Stirring Old God", home.world.id, (Domain.EARTH, None), power=40))
    await syncretize(session, ctx.rules, home.people.id, god.id)
    town = await settlement(session, "Stirring Town", home, home.regions[0], population=12000)
    plotter = await mortal(session, "Stirring Plotter", home, town.id)
    mark = await mortal(session, "Stirring Mark", home, town.id)
    await begin_scheme(ctx, plotter, PlotKind.SWAY, mark)
    await take_captive(ctx, plotter, await mortal(session, "Stirring Captive", home, town.id), None, description="held", home_id=town.id)
    session.add(SpyNetworkRow(owner_entity_id=town.id, target_entity_id=home.people.id, intel=90, since_epoch=1, locked=[]))
    spirit = await entity(session, "Stirring Shade", EntityType.SPIRIT, SpiritStats(unrest=95), world_id=home.world.id, location_id=town.id)
    session.add(SpiritProfileRow(spirit_entity_id=spirit.id, alignment=SpiritAlignment.VENGEFUL, imprint={}, traits=[], deeds={}, locked=[]))
    design = DiseaseDesign(name=None, values={"virulence": 60, "lethality": 20, "stigma": 90}, hold=False)
    await create_disease(ctx, home.regions[0].id, design, son_id=None)
    relic = await entity(session, "Stirring Ring", EntityType.ITEM, ItemStats(damage=5, protection=0, might=5, curse=90), world_id=home.world.id)
    await BondRepository(session).connect(BondDraft(plotter.id, relic.id, BondKind.OWNS, 1, None))
    (await items.profile_of(ctx, relic)).curse = CurseKind.BETRAYAL
    company = await entity(session, "Stirring Lances", EntityType.FACTION, FactionStats(strength=60), world_id=home.world.id)
    session.add(FactionProfileRow(faction_entity_id=company.id, kind=FactionKind.MERCENARY_COMPANY, influence_over={}, loyalty=5, locked=[]))
    other = await entity(session, "Stirring Folk", EntityType.PEOPLE, PeopleStats(population=3000), world_id=home.world.id, location_id=home.regions[0].id)
    await change_relation(ctx, home.people.id, other.id, -90, MemoryKind.ILL_WILL)
    for kind, values in FIRST_VALUES.items():
        await create_lore(ctx, kind, name=f"Stirring {kind.value}", description="", world_id=home.world.id, location_id=town.id, power=3, values=dict(values))
    species = await entity(session, "Stirring Wyrm Kin", EntityType.SPECIES, SpeciesStats(danger=90), world_id=home.world.id, location_id=home.regions[0].id)
    beast = await entity(session, "Stirring Wyrm", EntityType.BEAST, BeastStats(danger=90, hp=200), world_id=home.world.id, location_id=home.regions[0].id)
    await profile_beast(ctx, beast, species)
    rival = await settlement(session, "Stirring Rival", home, home.regions[1], population=8000)
    war = await open_war(ctx, town, rival)
    strength = await MilitaryStrength.load(session, ctx.rules)
    await raise_army(ctx, strength, await SideIndex.load(session, await Neighbourhood.load(session, ctx.rules)), town, war)
    session.add(SiegeRow(war_id=war.id, besieged_entity_id=rival.id, besieger_entity_id=town.id, started_epoch=ctx.epoch))
    await session.flush()


async def test_every_engine_step_obeys_a_hold_and_runs_when_forced_on_one_node(database: Database) -> None:
    async with database.write() as session:
        await stir(session, await seed_rich_cosmos(session))
    await simulate(database, WARM_EPOCHS)
    async with database.read() as session:
        target = await session.scalar(
            select(EntityRow.id).where(EntityRow.entity_type.in_(list(COMMUNITY_TYPES)), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    assert target is not None and Base.metadata.tables
    disobeyed: dict[str, list[str]] = {}
    broken: dict[str, str] = {}
    for phase in all_phases():
        changes, error = await run_watched(database, phase.name, BLOCK_EVERY_NODE)
        if changes:
            disobeyed[phase.name] = [f"{count}x {change}" for change, count in changes.most_common()]
        if error is not None:
            broken[f"{phase.name} held"] = error
        _, forced = await run_watched(database, phase.name, target)
        if forced is not None:
            broken[f"{phase.name} forced"] = forced
    assert broken == {}, "\n".join(f"{name}: {error}" for name, error in broken.items())
    assert disobeyed == {}, "Engine steps that still act on held nodes; skip held nodes where they choose whom to act on:\n" + "\n".join(
        f"{name}: {'; '.join(lines)}" for name, lines in disobeyed.items()
    )

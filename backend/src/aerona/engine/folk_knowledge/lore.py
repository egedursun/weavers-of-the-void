from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import func, or_, select

from aerona.catalog.life.crafts import SCHOOLING
from aerona.catalog.life.domain import GROWN
from aerona.catalog.life.folk_knowledge import THEORY_DOMAINS
from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.crafts import NumberSystemRow
from aerona.db.tables.discovery import TheoryAdherentRow, TheoryProfileRow
from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.folk_knowledge import FolkClassRow, FolkKnowledgeRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass
from aerona.domain.enums.folk_knowledge import FolkDomain, FolkTaking, LoreHolders, LoreTransmission, NumberReading
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.crafts.games import neighbours
from aerona.engine.folk_knowledge.truth import KIND_DOMAINS, ROAMING, blames, hurts, misjudged, mistaken, truth_of
from aerona.engine.forecasting.reading import sky_marks
from aerona.engine.lore.research import has_technique
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import folk_among, towns_of_people
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term

FRAIL = frozenset({LoreHolders.ELDERS, LoreHolders.SPECIALISTS})
UNWRITTEN = frozenset({LoreTransmission.ORAL, LoreTransmission.APPRENTICESHIP, LoreTransmission.RITE})
CALMING = frozenset({NumberReading.LUCKY})
TROUBLING = frozenset({NumberReading.UNLUCKY, NumberReading.FORBIDDEN})


@dataclass
class FolkTally:
    seeded: int = 0
    learned: int = 0
    corrected: int = 0
    harmed: int = 0
    exchanged: int = 0
    pulled: int = 0
    schooled: int = 0
    lost: int = 0
    read: int = 0


@dataclass(frozen=True)
class Candidate:
    name: str
    node_id: int | None = None
    material_id: int | None = None


def editable(row: FolkKnowledgeRow | FolkClassRow, field: str) -> bool:
    return field not in (row.locked or [])


def raise_accuracy(row: FolkKnowledgeRow, amount: int, key: str, source: int) -> int:
    if not amount or not editable(row, "accuracy"):
        return 0
    before = row.accuracy
    with explaining():
        term(key, amount, source_node_id=source)
        row.accuracy = clamp_int(row.accuracy + amount, 0, PERCENT)
    return row.accuracy - before


async def entity_candidates(ctx: TickContext, people: EntityRow, domain: FolkDomain, taken: set[int]) -> list[Candidate]:
    statement = select(EntityRow).where(EntityRow.world_id == people.world_id, EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(sorted(taken)))
    if domain in (FolkDomain.PLANTS, FolkDomain.ANIMALS):
        kinds = GROWN if domain is FolkDomain.PLANTS else ROAMING
        statement = statement.join(SpeciesProfileRow, SpeciesProfileRow.species_entity_id == EntityRow.id).where(
            SpeciesProfileRow.species_class.in_(sorted(kinds))
        )
    elif domain is FolkDomain.ILLNESS:
        statement = statement.join(DiseaseProfileRow, DiseaseProfileRow.disease_entity_id == EntityRow.id)
    elif domain is FolkDomain.LAND:
        statement = statement.where(EntityRow.entity_type == EntityType.REGION)
    else:
        statement = (
            statement.where(EntityRow.entity_type == EntityType.REGION)
            .join(RegionEnvironmentRow, RegionEnvironmentRow.entity_id == EntityRow.id)
            .where(or_(RegionEnvironmentRow.coast_kind != CoastKind.NONE, RegionEnvironmentRow.river_class != RiverClass.NONE))
        )
    atlas = await RegionAtlas.load(ctx.session)
    found = list(await ctx.session.scalars(statement.order_by(EntityRow.id)))
    nearest = min(found, key=lambda row: (atlas.distance(people.id, row.id), row.id), default=None)
    return [Candidate(nearest.name, node_id=nearest.id)] if nearest is not None else []


async def sky_candidates(ctx: TickContext, people: EntityRow, taken: set[int]) -> list[Candidate]:
    world = await ctx.session.get(WorldRow, people.world_id) if people.world_id is not None else None
    if world is None:
        return []
    planet = await ctx.session.get(WorldRow, world.parent_world_id) if world.parent_world_id is not None else None
    moons = list(await ctx.session.scalars(select(WorldRow).where(WorldRow.parent_world_id == world.id).order_by(WorldRow.id)))
    star_id = world.star_id if world.star_id is not None else (planet.star_id if planet is not None else None)
    star = await ctx.session.get(StarRow, star_id) if star_id is not None else None
    bodies: list[NodeRow] = [*([star] if star is not None else []), *([planet] if planet is not None else []), *moons]
    return [Candidate(body.name, node_id=body.id) for body in bodies if body.id not in taken][:1]


async def candidates(ctx: TickContext, people: EntityRow, domain: FolkDomain, mine: list[FolkClassRow]) -> list[Candidate]:
    classed = [(row.grouped_node_id, row.material_id) for row in mine if row.domain is domain]
    nodes = {node for node, _ in classed if node is not None}
    if domain is FolkDomain.MATTER:
        materials = {material for _, material in classed if material is not None}
        found = await ctx.session.scalar(
            select(WorldMaterialRow)
            .where(WorldMaterialRow.world_id == people.world_id, WorldMaterialRow.id.not_in(sorted(materials)))
            .order_by(WorldMaterialRow.id)
            .limit(1)
        )
        if found is None:
            return []
        return [Candidate(found.name or (found.base_kind.value.replace("_", " ") if found.base_kind else "a material"), material_id=found.id)]
    if domain is FolkDomain.SKY:
        return await sky_candidates(ctx, people, nodes)
    return await entity_candidates(ctx, people, domain, nodes)


async def learn(ctx: TickContext, people: EntityRow, row: FolkKnowledgeRow, mine: list[FolkClassRow], tally: FolkTally) -> None:
    if row.domain not in KIND_DOMAINS:
        return
    known = sum(1 for cls in mine if cls.domain is row.domain)
    if known >= row.depth // ctx.rules.folk_knowledge.class_span:
        return
    for found in await candidates(ctx, people, row.domain, mine):
        draft = FolkClassRow(
            people_entity_id=people.id,
            domain=row.domain,
            name=found.name,
            grouped_node_id=found.node_id,
            material_id=found.material_id,
            learned_epoch=ctx.epoch,
            locked=[],
        )
        truth = await truth_of(ctx.session, draft)
        right = truth is not None and ctx.rng(f"folk_learn.{people.id}.{row.domain}.{ctx.epoch}").chance(row.accuracy)
        draft.taken_as = truth if right and truth is not None else mistaken(row.domain, truth)
        draft.misclassified = misjudged(draft.taken_as, truth)
        ctx.session.add(draft)
        mine.append(draft)
        await record(
            ctx,
            "folk.class_learned",
            roles={IncidentRole.SUBJECT: people.id},
            facts={"name": found.name, "domain": row.domain, "taken_as": draft.taken_as},
        )
        tally.learned += 1


async def victim_among(ctx: TickContext, people: EntityRow, stream: str) -> EntityRow | None:
    towns = await towns_of_people(ctx.session, people.id)
    if not towns:
        return None
    folk = [
        being
        for being in await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await folk_among(ctx.session, towns))
            .order_by(EntityRow.id)
        )
        if not held(being.id)
    ]
    return ctx.rng(stream).pick(folk) if folk else None


async def blamed_town(ctx: TickContext, people: EntityRow) -> SettlementProfileRow | None:
    for town_id in await towns_of_people(ctx.session, people.id):
        profile = await ctx.session.get(SettlementProfileRow, town_id)
        if profile is not None and not held(town_id) and editable_town(profile):
            return profile
    return None


def editable_town(profile: SettlementProfileRow) -> bool:
    return "unrest" not in (profile.locked or [])


async def correct(ctx: TickContext, people: EntityRow, row: FolkKnowledgeRow, cls: FolkClassRow, *, truth: FolkTaking, tally: FolkTally) -> None:
    if not editable(cls, "taken_as"):
        return
    cls.taken_as = truth
    if editable(cls, "misclassified"):
        cls.misclassified = False
    raise_accuracy(row, ctx.rules.folk_knowledge.failure_correction, "folk_knowledge.failure_correction", people.id)
    await record(
        ctx,
        "folk.class_corrected",
        roles={IncidentRole.SUBJECT: people.id},
        facts={"name": cls.name, "domain": cls.domain, "taken_as": truth},
    )
    tally.corrected += 1


async def suffer(ctx: TickContext, people: EntityRow, row: FolkKnowledgeRow, cls: FolkClassRow, tally: FolkTally) -> None:
    table = ctx.rules.folk_knowledge
    truth = await truth_of(ctx.session, cls)
    if editable(cls, "misclassified"):
        cls.misclassified = misjudged(cls.taken_as, truth)
    if truth is None or not (hurts(cls.taken_as, truth) or blames(cls.taken_as, truth)):
        return
    if not ctx.rng(f"folk_harm.{cls.id}.{ctx.epoch}").chance(table.harm_chance_pct * (PERCENT - row.accuracy) / PERCENT):
        return
    if hurts(cls.taken_as, truth):
        victim = await victim_among(ctx, people, f"folk_victim.{cls.id}.{ctx.epoch}")
        if victim is None:
            return
        with explaining():
            term("folk_knowledge.harm_hp", -table.harm_hp, source_node_id=people.id)
            shift_stat(victim, "hp", -table.harm_hp, low=1)
        roles = {IncidentRole.SUBJECT: people.id, IncidentRole.VICTIM: victim.id}
    else:
        town = await blamed_town(ctx, people)
        if town is None:
            return
        with explaining():
            term("folk_knowledge.curse_blame_unrest", table.curse_blame_unrest, source_node_id=people.id)
            town.unrest = clamp_int(town.unrest + table.curse_blame_unrest, 0, PERCENT)
        roles = {IncidentRole.SUBJECT: people.id, IncidentRole.PLACE: town.settlement_entity_id}
    await record(ctx, "folk.misclassification_harm", roles=roles, facts={"name": cls.name, "domain": cls.domain, "taken_as": cls.taken_as})
    tally.harmed += 1
    if ctx.rng(f"folk_correct.{cls.id}.{ctx.epoch}").chance(row.accuracy):
        await correct(ctx, people, row, cls, truth=truth, tally=tally)


async def exchange(ctx: TickContext, people: EntityRow, rows: dict[FolkDomain, FolkKnowledgeRow], tally: FolkTally) -> None:
    gain = ctx.rules.folk_knowledge.contact_gain
    for neighbour in await neighbours(ctx, people.id):
        theirs = {
            row.domain: row
            for row in await ctx.session.scalars(select(FolkKnowledgeRow).where(FolkKnowledgeRow.people_entity_id == neighbour).order_by(FolkKnowledgeRow.id))
        }
        best: tuple[int, FolkDomain] | None = None
        for domain, row in rows.items():
            other = theirs.get(domain)
            if other is None or other.accuracy <= row.accuracy:
                continue
            moved = raise_accuracy(row, min(gain, other.accuracy - row.accuracy), "folk_knowledge.contact_gain", neighbour)
            if moved and (best is None or moved > best[0]):
                best = (moved, domain)
        if best is not None:
            await record(
                ctx,
                "folk.lore_exchanged",
                roles={IncidentRole.LEARNER: people.id, IncidentRole.TEACHER: neighbour},
                facts={"domain": best[1], "gain": best[0]},
            )
            tally.exchanged += 1


async def pull_of_theories(ctx: TickContext, people: EntityRow, rows: dict[FolkDomain, FolkKnowledgeRow], tally: FolkTally) -> None:
    holders = [people.id, *await towns_of_people(ctx.session, people.id)]
    held_theories = await ctx.session.execute(
        select(TheoryProfileRow.domain, TheoryProfileRow.correctness, TheoryProfileRow.theory_entity_id)
        .join(TheoryAdherentRow, TheoryAdherentRow.theory_entity_id == TheoryProfileRow.theory_entity_id)
        .where(TheoryAdherentRow.adherent_entity_id.in_(holders))
        .order_by(TheoryProfileRow.theory_entity_id)
    )
    for theory_domain, correctness, theory_id in list(held_theories):
        for domain in THEORY_DOMAINS.get(theory_domain, ()):
            row = rows.get(domain)
            if row is None:
                continue
            step = round_half_up((correctness - row.accuracy) * ctx.rules.folk_knowledge.theory_pull_pct / PERCENT)
            if raise_accuracy(row, step, "folk_knowledge.theory_pull_pct", theory_id):
                tally.pulled += 1


async def school(ctx: TickContext, people: EntityRow, rows: dict[FolkDomain, FolkKnowledgeRow], tally: FolkTally) -> None:
    if not any([await has_technique(ctx.session, people.id, technique) for technique in SCHOOLING]):
        return
    for row in rows.values():
        if raise_accuracy(row, ctx.rules.folk_knowledge.schooling_gain, "folk_knowledge.schooling_gain", people.id):
            tally.schooled += 1


async def lose(ctx: TickContext, people: EntityRow, rows: dict[FolkDomain, FolkKnowledgeRow], tally: FolkTally) -> None:
    towns = await towns_of_people(ctx.session, people.id)
    if not towns:
        return
    dead = await ctx.session.scalar(
        select(func.count())
        .select_from(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.end_epoch == ctx.epoch, await folk_among(ctx.session, towns))
    )
    if not dead:
        return
    table = ctx.rules.folk_knowledge
    for row in rows.values():
        if row.holders not in FRAIL or row.transmission not in UNWRITTEN or not editable(row, "depth") or row.depth == 0:
            continue
        if not ctx.rng(f"folk_lost.{row.id}.{ctx.epoch}").chance(table.loss_on_holder_death_pct):
            continue
        loss = min(row.depth, table.class_span)
        with explaining():
            term("folk_knowledge.loss_on_holder_death_pct", -loss, source_node_id=people.id)
            row.depth -= loss
        await record(ctx, "folk.lore_lost", roles={IncidentRole.SUBJECT: people.id}, facts={"domain": row.domain, "depth": row.depth})
        tally.lost += 1


async def read_the_epoch(ctx: TickContext, people: EntityRow, tally: FolkTally) -> None:
    system = await ctx.session.get(NumberSystemRow, people.id)
    if system is None or not system.numerology:
        return
    number = ctx.epoch % system.base
    found = system.numerology.get(str(number))
    if found not in set(NumberReading):
        return
    reading = NumberReading(found)
    table = ctx.rules.folk_knowledge
    towns = await towns_of_people(ctx.session, people.id)
    for town_id in towns:
        town = await ctx.session.get(EntityRow, town_id)
        profile = await ctx.session.get(SettlementProfileRow, town_id)
        if town is None or held(town_id):
            continue
        if reading is NumberReading.SACRED:
            with explaining():
                term("folk_knowledge.numerology_piety", table.numerology_piety, source_node_id=people.id)
                shift_stat(town, "piety", table.numerology_piety, low=0, high=PERCENT)
        elif profile is not None and editable_town(profile):
            shift = table.numerology_unrest if reading in TROUBLING else -table.numerology_unrest
            with explaining():
                term("folk_knowledge.numerology_unrest", shift, source_node_id=people.id)
                profile.unrest = clamp_int(profile.unrest + shift, 0, PERCENT)
    if reading in CALMING and towns:
        for child in await ctx.session.scalars(
            select(MortalProfileRow)
            .join(EntityRow, EntityRow.id == MortalProfileRow.entity_id)
            .where(EntityRow.birth_epoch == ctx.epoch, await folk_among(ctx.session, towns))
            .order_by(MortalProfileRow.entity_id)
        ):
            if held(child.entity_id) or "renown" in (child.locked or []):
                continue
            with explaining():
                term("folk_knowledge.numerology_name_renown", table.numerology_name_renown, source_node_id=people.id)
                child.renown = clamp_int(child.renown + table.numerology_name_renown, 0, PERCENT)
    await record(ctx, "folk.number_read", roles={IncidentRole.SUBJECT: people.id}, facts={"number": number, "reading": reading})
    tally.read += 1


async def watch_the_heavens(ctx: TickContext, people: EntityRow, sky: FolkKnowledgeRow | None) -> None:
    if sky is None or not editable(sky, "accuracy"):
        return
    floor = await sky_marks(ctx.session, ctx.rules, people.id)
    if sky.accuracy >= floor:
        return
    with explaining():
        term("forecasting.sky_mark_accuracy", floor - sky.accuracy, source_node_id=people.id)
        sky.accuracy = clamp_int(floor, 0, PERCENT)


async def keep_folk_knowledge(ctx: TickContext, tally: FolkTally) -> None:
    classes: dict[int, list[FolkClassRow]] = defaultdict(list)
    for cls in await ctx.session.scalars(select(FolkClassRow).order_by(FolkClassRow.id)):
        classes[cls.people_entity_id].append(cls)
    for people in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        if held(people.id):
            continue
        rows = {
            row.domain: row
            for row in await ctx.session.scalars(select(FolkKnowledgeRow).where(FolkKnowledgeRow.people_entity_id == people.id).order_by(FolkKnowledgeRow.id))
        }
        mine = classes[people.id]
        await watch_the_heavens(ctx, people, rows.get(FolkDomain.SKY))
        for row in rows.values():
            await learn(ctx, people, row, mine, tally)
        await ctx.session.flush()
        for cls in list(mine):
            known = rows.get(cls.domain)
            if known is not None:
                await suffer(ctx, people, known, cls, tally)
        await exchange(ctx, people, rows, tally)
        await pull_of_theories(ctx, people, rows, tally)
        await school(ctx, people, rows, tally)
        await lose(ctx, people, rows, tally)
        await read_the_epoch(ctx, people, tally)
    await ctx.session.flush()

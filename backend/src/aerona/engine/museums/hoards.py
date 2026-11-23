from dataclasses import dataclass

from sqlalchemy import func, or_, select

from aerona.catalog.life.museums import PIECE_OF_CLASS, PIECE_PRESTIGE, WAR_PIECES
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.fossils import FossilBedRow
from aerona.db.tables.museums import MuseumCollectionRow, MuseumPieceRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.museum import HoardKind, PieceKind
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.records import FactUnit, StepAction
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.services.community_relations import change_relation

HALLS = {StructureKind.MUSEUM: HoardKind.MUSEUM, StructureKind.TEMPLE: HoardKind.TEMPLE_TREASURY}
RELICS = frozenset(item for item, kind in PIECE_OF_CLASS.items() if kind is PieceKind.RELIC)
ARTIFACTS = frozenset(item for item, kind in PIECE_OF_CLASS.items() if kind is not PieceKind.RELIC)


@dataclass
class HoardTally:
    founded: int = 0
    gathered: int = 0
    looted: int = 0


async def hoard_of(ctx: TickContext, keeper_id: int, kind: HoardKind, structure_id: int | None = None) -> MuseumCollectionRow:
    kept = select(MuseumCollectionRow).where(MuseumCollectionRow.keeper_entity_id == keeper_id, MuseumCollectionRow.kind == kind)
    row = await ctx.session.scalar(kept.limit(1))
    if row is None:
        row = MuseumCollectionRow(keeper_entity_id=keeper_id, structure_entity_id=structure_id, kind=kind, founded_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def found_hoards(ctx: TickContext, tally: HoardTally) -> None:
    halls = await ctx.session.execute(
        select(StructureProfileRow.structure_entity_id, StructureProfileRow.host_entity_id, StructureProfileRow.kind).where(
            StructureProfileRow.kind.in_(list(HALLS)), StructureProfileRow.host_entity_id.is_not(None)
        )
    )
    known = {(row.keeper_entity_id, row.kind) for row in await ctx.session.scalars(select(MuseumCollectionRow))}
    for structure_id, host_id, kind in halls.all():
        if host_id is None or held(host_id) or (host_id, HALLS[kind]) in known:
            continue
        await hoard_of(ctx, host_id, HALLS[kind], structure_id)
        known.add((host_id, HALLS[kind]))
        tally.founded += 1
    for ruler_id, polity_id in await ctx.session.execute(
        select(OfficeRow.holder_entity_id, OfficeRow.polity_entity_id).where(OfficeRow.kind == OfficeKind.RULER, OfficeRow.holder_entity_id.is_not(None))
    ):
        if ruler_id is None or held(polity_id) or (polity_id, HoardKind.ROYAL_COLLECTION) in known:
            continue
        if len(await prized_of(ctx, ruler_id)) >= ctx.rules.museums.royal_from:
            await hoard_of(ctx, polity_id, HoardKind.ROYAL_COLLECTION)
            known.add((polity_id, HoardKind.ROYAL_COLLECTION))
            tally.founded += 1
    for finder in set(await ctx.session.scalars(select(FossilBedRow.finder_entity_id).where(FossilBedRow.finder_entity_id.is_not(None)))):
        if finder is None or held(finder) or any((finder, kind) in known for kind in HoardKind):
            continue
        await hoard_of(ctx, finder, HoardKind.CABINET)
        known.add((finder, HoardKind.CABINET))
        tally.founded += 1


async def prized_of(ctx: TickContext, owner_id: int) -> list[tuple[int, PieceKind]]:
    owned = select(BondRow.target_node_id).where(BondRow.source_node_id == owner_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    rows = await ctx.session.execute(
        select(ItemProfileRow.item_entity_id, ItemProfileRow.item_class)
        .join(EntityRow, EntityRow.id == ItemProfileRow.item_entity_id)
        .where(ItemProfileRow.item_entity_id.in_(owned), EntityRow.status == EntityStatus.CANON, ItemProfileRow.item_class.in_(list(RELICS | ARTIFACTS)))
        .order_by(ItemProfileRow.item_entity_id)
    )
    return [(item_id, PIECE_OF_CLASS[item_class]) for item_id, item_class in rows.all()]


async def prized_in(ctx: TickContext, town_id: int, classes: frozenset[ItemClass]) -> list[tuple[int, PieceKind]]:
    residents = select(EntityRow.id).where(EntityRow.location_id == town_id, EntityRow.status == EntityStatus.CANON)
    kept = select(BondRow.target_node_id).where(BondRow.source_node_id.in_(residents), BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    rows = await ctx.session.execute(
        select(ItemProfileRow.item_entity_id, ItemProfileRow.item_class)
        .join(EntityRow, EntityRow.id == ItemProfileRow.item_entity_id)
        .where(
            EntityRow.status == EntityStatus.CANON,
            ItemProfileRow.item_class.in_(list(classes)),
            or_(EntityRow.location_id == town_id, ItemProfileRow.item_entity_id.in_(kept)),
        )
        .order_by(ItemProfileRow.item_entity_id)
    )
    return [(item_id, PIECE_OF_CLASS.get(item_class, PieceKind.ARTIFACT)) for item_id, item_class in rows.all()]


async def ruler_of(ctx: TickContext, polity_id: int) -> int | None:
    found = await ctx.session.scalar(
        select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == polity_id, OfficeRow.kind == OfficeKind.RULER).limit(1)
    )
    return int(found) if found is not None else None


async def offered(ctx: TickContext, atlas: RegionAtlas, hoard: MuseumCollectionRow) -> list[tuple[int | None, int | None, PieceKind]]:
    found: list[tuple[int | None, int | None, PieceKind]] = []
    owner = await ruler_of(ctx, hoard.keeper_entity_id) if hoard.kind is HoardKind.ROYAL_COLLECTION else hoard.keeper_entity_id
    if owner is not None:
        found.extend((item_id, None, kind) for item_id, kind in await prized_of(ctx, owner))
    if hoard.kind is HoardKind.ROYAL_COLLECTION:
        return found
    classes = RELICS if hoard.kind is HoardKind.TEMPLE_TREASURY else RELICS | ARTIFACTS
    found.extend((item_id, None, kind) for item_id, kind in await prized_in(ctx, hoard.keeper_entity_id, classes))
    if hoard.kind is HoardKind.TEMPLE_TREASURY:
        return found
    art = await ctx.session.scalars(
        select(EntityRow.id)
        .where(EntityRow.entity_type == EntityType.ARTWORK, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == hoard.keeper_entity_id)
        .order_by(EntityRow.id)
    )
    found.extend((art_id, None, PieceKind.ART) for art_id in art)
    beds = await ctx.session.scalars(select(FossilBedRow.id).where(FossilBedRow.finder_entity_id == hoard.keeper_entity_id).order_by(FossilBedRow.id))
    found.extend((None, bed_id, PieceKind.FOSSIL) for bed_id in beds)
    region = atlas.top_region(hoard.keeper_entity_id)
    if region is not None:
        kinds = await ctx.session.scalars(
            select(SpeciesRangeRow.species_entity_id)
            .where(SpeciesRangeRow.region_entity_id == region, SpeciesRangeRow.abundance > 0)
            .order_by(SpeciesRangeRow.species_entity_id)
        )
        found.extend((species_id, None, PieceKind.SPECIMEN) for species_id in ctx.rng(f"specimens.{hoard.id}").shuffled(kinds))
    return found


async def gather(ctx: TickContext, atlas: RegionAtlas, hoard: MuseumCollectionRow, tally: HoardTally) -> None:
    taken_items = set(await ctx.session.scalars(select(MuseumPieceRow.item_entity_id).where(MuseumPieceRow.item_entity_id.is_not(None))))
    taken_beds = set(await ctx.session.scalars(select(MuseumPieceRow.fossil_bed_id).where(MuseumPieceRow.fossil_bed_id.is_not(None))))
    specimens = 0
    for item_id, bed_id, kind in await offered(ctx, atlas, hoard):
        if (item_id is not None and item_id in taken_items) or (bed_id is not None and bed_id in taken_beds):
            continue
        if kind is PieceKind.SPECIMEN:
            if specimens >= ctx.rules.museums.per_epoch(ctx.rules.museums.specimens_per_epoch):
                continue
            specimens += 1
        polity = hoard.keeper_entity_id if kind is PieceKind.REGALIA and hoard.kind is HoardKind.ROYAL_COLLECTION else None
        ctx.session.add(
            MuseumPieceRow(
                collection_id=hoard.id, kind=kind, item_entity_id=item_id, fossil_bed_id=bed_id, polity_entity_id=polity, acquired_epoch=ctx.epoch, locked=[]
            )
        )
        tally.gathered += 1
    await ctx.session.flush()


async def weigh(ctx: TickContext, hoard: MuseumCollectionRow) -> None:
    if "prestige" in hoard.locked:
        return
    kinds = list(await ctx.session.scalars(select(MuseumPieceRow.kind).where(MuseumPieceRow.collection_id == hoard.id).order_by(MuseumPieceRow.id)))
    hoard.prestige = clamp_int(sum(int(getattr(ctx.rules.museums, PIECE_PRESTIGE[kind])) for kind in kinds), 0, PERCENT)


async def keep_hoards(ctx: TickContext, tally: HoardTally) -> None:
    await found_hoards(ctx, tally)
    atlas = await RegionAtlas.load(ctx.session)
    for hoard in list(await ctx.session.scalars(select(MuseumCollectionRow).order_by(MuseumCollectionRow.id))):
        if held(hoard.keeper_entity_id):
            continue
        await gather(ctx, atlas, hoard, tally)
        await weigh(ctx, hoard)
    looted = await ctx.session.scalar(
        select(func.count(MuseumPieceRow.id)).where(MuseumPieceRow.looted_from_entity_id.is_not(None), MuseumPieceRow.acquired_epoch == ctx.epoch)
    )
    tally.looted += int(looted or 0)
    await ctx.session.flush()


async def loot(ctx: TickContext, victim_id: int, sacker_id: int) -> int:
    if held(victim_id) or held(sacker_id):
        return 0
    pieces = list(
        await ctx.session.scalars(
            select(MuseumPieceRow)
            .join(MuseumCollectionRow, MuseumCollectionRow.id == MuseumPieceRow.collection_id)
            .where(MuseumCollectionRow.keeper_entity_id == victim_id)
            .order_by(MuseumPieceRow.id)
        )
    )
    taking = round_half_up(len(pieces) * ctx.rules.museums.loot_pct / PERCENT)
    if not taking:
        return 0
    spoils = await hoard_of(ctx, sacker_id, HoardKind.TROPHY_HALL)
    moved = 0
    shamed: set[int] = set()
    for piece in pieces[:taking]:
        if piece.locked:
            continue
        piece.collection_id, piece.looted_from_entity_id, piece.acquired_epoch = spoils.id, victim_id, ctx.epoch
        if piece.kind in WAR_PIECES:
            piece.kind = PieceKind.TROPHY
        if piece.kind is PieceKind.REGALIA and piece.polity_entity_id is not None:
            shamed.add(piece.polity_entity_id)
        moved += 1
    await take_trophies(ctx, victim_id, sacker_id, moved, shamed)
    victim, sacker = await ctx.session.get(EntityRow, victim_id), await ctx.session.get(EntityRow, sacker_id)
    if moved and victim is not None and sacker is not None:
        await record(
            ctx,
            "museum.looted",
            roles={IncidentRole.ACTOR: sacker_id, IncidentRole.VICTIM: victim_id},
            facts={"pieces": moved},
            steps=(StepDraft(StepAction.PILLAGE, actor=sacker_id, target=victim_id, amount=moved, unit=FactUnit.COUNT),),
        )
    await ctx.session.flush()
    return moved


async def take_trophies(ctx: TickContext, victim_id: int, sacker_id: int, moved: int, shamed: set[int]) -> None:
    if moved <= 0:
        return
    table = ctx.rules.museums
    await change_relation(ctx, victim_id, sacker_id, -table.trophy_grievance, MemoryKind.ILL_WILL, note="carried off its banners and treasures")
    for polity_id in sorted(shamed):
        realm = await ctx.session.get(PolityProfileRow, polity_id)
        if realm is not None and not held(polity_id) and "legitimacy" not in realm.locked:
            realm.legitimacy = clamp_int(realm.legitimacy - table.regalia_shame, 0, PERCENT)
    await record(
        ctx,
        "collection.trophy_taken",
        roles={IncidentRole.ACTOR: sacker_id, IncidentRole.VICTIM: victim_id},
        facts={"pieces": moved, "regalia": len(shamed)},
    )


async def return_trophies(ctx: TickContext, victor_id: int, loser_id: int) -> int:
    pieces = await ctx.session.scalars(
        select(MuseumPieceRow)
        .join(MuseumCollectionRow, MuseumCollectionRow.id == MuseumPieceRow.collection_id)
        .where(MuseumCollectionRow.keeper_entity_id == victor_id, MuseumPieceRow.looted_from_entity_id == loser_id)
        .order_by(MuseumPieceRow.id)
    )
    returned = 0
    for piece in list(pieces):
        if not piece.locked and await restitute(ctx, piece) is not None:
            returned += 1
    return returned


async def restitute(ctx: TickContext, piece: MuseumPieceRow) -> MuseumCollectionRow | None:
    if piece.looted_from_entity_id is None:
        return None
    home = await hoard_of(ctx, piece.looted_from_entity_id, HoardKind.CABINET)
    giver = await ctx.session.get(MuseumCollectionRow, piece.collection_id)
    piece.returned_by_entity_id = giver.keeper_entity_id if giver is not None else None
    piece.collection_id, piece.looted_from_entity_id, piece.returned_epoch = home.id, None, ctx.epoch
    await ctx.session.flush()
    return home

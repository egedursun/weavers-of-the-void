from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.marks import AUGMENT_MEANINGS, CALMING, EVENT_BONDS, MARKABLE, MARKS, MEANINGS, SEEDED_MEANINGS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.customs import BodyMarkRow, MarkCustomRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.made import AugmentRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.customs import MarkKind, MarkMeaning
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.justice import Verdict
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import realm_of
from aerona.engine.mortal.kin import close_kin_of
from aerona.engine.mortal.profile import is_held
from aerona.engine.mortal.standing import add_renown
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record


@dataclass
class MarkTally:
    seeded: int = 0
    placed: int = 0


async def customs_of(ctx: TickContext, people_id: int) -> dict[MarkMeaning, MarkKind]:
    rows = await ctx.session.scalars(select(MarkCustomRow).where(MarkCustomRow.people_entity_id == people_id).order_by(MarkCustomRow.kind))
    return {row.meaning: row.kind for row in rows}


async def seed_customs(ctx: TickContext, people: EntityRow, tally: MarkTally) -> dict[MarkMeaning, MarkKind]:
    found = await customs_of(ctx, people.id)
    if found or held(people.id):
        return found
    rng = ctx.rng(seed_of("marks", people.id))
    meanings = list(SEEDED_MEANINGS)
    for kind in rng.sample(list(MARKABLE), min(len(MARKABLE), ctx.rules.marks.customs_per_people)):
        meaning = rng.pick([item for item in meanings if item not in found] or meanings)
        ctx.session.add(MarkCustomRow(people_entity_id=people.id, kind=kind, meaning=meaning, locked=[]))
        found[meaning] = kind
    tally.seeded += 1
    return found


async def place(
    ctx: TickContext, mortal: EntityRow, kind: MarkKind, meaning: MarkMeaning, tally: MarkTally, *, augment_id: int | None = None, told: bool = True
) -> BodyMarkRow:
    row = BodyMarkRow(holder_node_id=mortal.id, kind=kind, meaning=meaning, augment_id=augment_id, placed_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await read_mark(ctx, mortal, meaning)
    tally.placed += 1
    if told:
        await record(ctx, "body.marked", roles={IncidentRole.SUBJECT: mortal.id}, facts={"kind": kind, "meaning": meaning})
    return row


async def unshown_augment(ctx: TickContext, bearer_id: int) -> AugmentRow | None:
    shown = select(BodyMarkRow.augment_id).where(BodyMarkRow.augment_id.is_not(None))
    return await ctx.session.scalar(
        select(AugmentRow).where(AugmentRow.bearer_node_id == bearer_id, AugmentRow.id.not_in(shown)).order_by(AugmentRow.id).limit(1)
    )


async def read_mark(ctx: TickContext, mortal: EntityRow, meaning: MarkMeaning) -> None:
    table = ctx.rules.marks
    profile = await ctx.session.get(MortalProfileRow, mortal.id)
    if profile is None:
        return
    spec = MEANINGS[meaning]
    field = spec.reading
    if field is None or is_held(profile, field):
        return
    if field == "renown":
        amount = table.beauty_per_mark if meaning is MarkMeaning.BEAUTY else table.renown_per_deed
        await add_renown(ctx.session, mortal.id, amount, ctx.epoch, rules=ctx.rules)
    elif spec.shames:
        profile.honour = clamp_int(profile.honour - table.shame_per_brand, 0, PERCENT)
    else:
        amount = table.faith_per_mark if field == "loyalty_god" else table.belonging_per_mark
        setattr(profile, field, clamp_int(getattr(profile, field) + amount, 0, PERCENT))


async def happened(ctx: TickContext, mortal: EntityRow, meaning: MarkMeaning) -> bool:
    bond = EVENT_BONDS.get(meaning)
    if bond is not None:
        query = select(BondRow.id).where(BondRow.source_node_id == mortal.id, BondRow.kind == bond, BondRow.epoch == ctx.epoch)
        return await ctx.session.scalar(query.limit(1)) is not None
    spec = MEANINGS[meaning]
    if spec.at_birth:
        return mortal.birth_epoch == ctx.epoch
    if spec.guild:
        joined = select(FactionMembershipRow.faction_entity_id).where(
            FactionMembershipRow.mortal_entity_id == mortal.id, FactionMembershipRow.joined_epoch == ctx.epoch
        )
        return await ctx.session.scalar(joined.limit(1)) is not None
    if spec.mourns:
        kin = await close_kin_of(ctx.session, mortal.id)
        dead = select(EntityRow.id).where(EntityRow.id.in_(kin), EntityRow.status == EntityStatus.DEAD, EntityRow.end_epoch == ctx.epoch)
        return bool(kin) and await ctx.session.scalar(dead.limit(1)) is not None
    return False


async def calm_marked(ctx: TickContext) -> None:
    table = ctx.rules.marks
    calming = CALMING
    for holder in sorted(set(await ctx.session.scalars(select(BodyMarkRow.holder_node_id).where(BodyMarkRow.meaning.in_(calming))))):
        profile = await ctx.session.get(MortalProfileRow, holder)
        if profile is not None and not held(holder) and not is_held(profile, "stress"):
            profile.stress = clamp_int(profile.stress - table.calm_per_charm, 0, PERCENT)


async def cut_hair(ctx: TickContext) -> int:
    quick = [kind for kind, spec in MARKS.items() if spec.quick]
    since = ctx.epoch - ctx.rules.marks.epochs(ctx.rules.marks.hair_years)
    gone = 0
    for row in list(
        await ctx.session.scalars(select(BodyMarkRow).where(BodyMarkRow.kind.in_(quick), BodyMarkRow.placed_epoch <= since).order_by(BodyMarkRow.id))
    ):
        if not held(row.holder_node_id) and not row.locked:
            await ctx.session.delete(row)
            gone += 1
    return gone


async def show_augments(ctx: TickContext, tally: MarkTally) -> None:
    shown = [kind for kind, spec in MARKS.items() if spec.shows_augment]
    marked = set(await ctx.session.scalars(select(BodyMarkRow.augment_id).where(BodyMarkRow.kind.in_(shown), BodyMarkRow.augment_id.is_not(None))))
    fresh = await ctx.session.scalars(select(AugmentRow).where(AugmentRow.installed_epoch == ctx.epoch).order_by(AugmentRow.id))
    for augment in list(fresh):
        mortal = await ctx.session.get(EntityRow, augment.bearer_node_id)
        if augment.id in marked or mortal is None or held(mortal.id):
            continue
        await place(ctx, mortal, shown[0], await implant_meaning(ctx, mortal, augment), tally, augment_id=augment.id)


FAITH_CLASSES = frozenset({SocialClass.PRIEST, SocialClass.MONASTIC})


async def implant_meaning(ctx: TickContext, mortal: EntityRow, augment: AugmentRow) -> MarkMeaning:
    convicted = await ctx.session.scalar(
        select(CrimeCaseRow.id)
        .where(CrimeCaseRow.accused_entity_id == mortal.id, CrimeCaseRow.verdict == Verdict.GUILTY, CrimeCaseRow.closed_epoch == ctx.epoch)
        .limit(1)
    )
    if convicted is not None:
        return MarkMeaning.CRIME
    fitter = await ctx.session.get(EntityRow, augment.installed_by_node_id) if augment.installed_by_node_id is not None else None
    if fitter is not None and (fitter.entity_type is EntityType.CULT or fitter.social_class in FAITH_CLASSES):
        return MarkMeaning.FAITH
    return AUGMENT_MEANINGS[augment.kind]


async def faith_marked_stress(ctx: TickContext) -> None:
    laws = await LawBook.load(ctx.session)
    for row in list(await ctx.session.scalars(select(BodyMarkRow).where(BodyMarkRow.meaning == MarkMeaning.FAITH).order_by(BodyMarkRow.id))):
        mortal = await ctx.session.get(EntityRow, row.holder_node_id)
        realm = await realm_of(ctx.session, mortal.id) if mortal is not None else None
        profile = await ctx.session.get(MortalProfileRow, row.holder_node_id)
        if realm is None or profile is None or held(row.holder_node_id) or is_held(profile, "stress"):
            continue
        if laws.param(realm, LawKind.RELIGIOUS_TOLERANCE, "level") == "persecution":
            profile.stress = clamp_int(profile.stress + ctx.rules.marks.persecuted_faith_stress, 0, PERCENT)


async def keep_marks(ctx: TickContext, tally: MarkTally) -> None:
    await cut_hair(ctx)
    await show_augments(ctx, tally)
    await faith_marked_stress(ctx)
    for people in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        customs = await seed_customs(ctx, people, tally)
        if not customs:
            continue
        here = await present_among(ctx.session, [people.id])
        for mortal in list(
            await ctx.session.scalars(
                select(EntityRow).where(here, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
            )
        ):
            if held(mortal.id) or (await people_of(ctx.session, mortal) or people).id != people.id:
                continue
            for meaning, kind in sorted(customs.items(), key=lambda item: item[0].value):
                if meaning is not MarkMeaning.AGE_SET and await happened(ctx, mortal, meaning):
                    await place(ctx, mortal, kind, meaning, tally)
    await calm_marked(ctx)
    await ctx.session.flush()

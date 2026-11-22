from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.art_modes import ART_MODES
from aerona.catalog.life_traits import RIGHT_KIND_TRAITS, having
from aerona.db.tables.crafts import IncorporealRightRow
from aerona.db.tables.culture import ArtworkProfileRow, RiteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import HouseMemberRow
from aerona.db.write_guard import held
from aerona.domain.enums.crafts import RightAcquired, RightKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.life_traits import RightKindTrait
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.records import FactUnit, StepAction
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.polity.trials import report_crime
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import seed_of
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.sacred.places import ruler_of
from aerona.engine.services.community_relations import change_relation

MEDIUM_RIGHTS = {mode: spec.right for mode, spec in ART_MODES.items()}
COPIED = having(RIGHT_KIND_TRAITS, RightKindTrait.COPIED)


@dataclass
class RightsTally:
    claimed: int = 0
    infringed: int = 0
    licensed: int = 0


async def house_of(ctx: TickContext, maker_id: int) -> int:
    house = await ctx.session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == maker_id).limit(1))
    return house if house is not None else maker_id


async def claim_works(ctx: TickContext, tally: RightsTally) -> None:
    limit = ctx.rules.incorporeal.seed_per_epoch
    budget: float = limit if limit > 0 else float("inf")
    held_subjects = set(await ctx.session.scalars(select(IncorporealRightRow.subject_node_id).where(IncorporealRightRow.subject_node_id.is_not(None))))
    works = await ctx.session.execute(
        select(ArtworkProfileRow, EntityRow)
        .join(EntityRow, EntityRow.id == ArtworkProfileRow.artwork_entity_id)
        .where(EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for profile, work in works:
        if budget <= 0:
            return
        if work.id in held_subjects or profile.author_entity_id is None or held(profile.author_entity_id):
            continue
        holder = await house_of(ctx, profile.author_entity_id)
        ctx.session.add(
            IncorporealRightRow(
                holder_node_id=holder,
                kind=MEDIUM_RIGHTS[profile.medium],
                subject_node_id=work.id,
                name=work.name,
                acquired=RightAcquired.CREATED,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        tally.claimed += 1
        budget -= 1
    rites = await ctx.session.execute(
        select(RiteProfileRow, EntityRow)
        .join(EntityRow, EntityRow.id == RiteProfileRow.rite_entity_id)
        .where(EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for known, rite in rites:
        if budget <= 0:
            return
        if rite.id in held_subjects or known.inventor_entity_id is None or held(known.inventor_entity_id):
            continue
        holder = await house_of(ctx, known.inventor_entity_id)
        ctx.session.add(
            IncorporealRightRow(
                holder_node_id=holder,
                kind=RightKind.RITE,
                subject_node_id=rite.id,
                name=rite.name,
                acquired=RightAcquired.CREATED,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        tally.claimed += 1
        budget -= 1
    await claim_names(ctx, tally, held_subjects, budget)


async def claim_names(ctx: TickContext, tally: RightsTally, held_subjects: set[int | None], budget: float) -> None:
    houses = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.HOUSE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    realms = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.POLITY, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    claims = [(house.id, RightKind.NAME, house) for house in houses]
    for realm in realms:
        ruler = await ruler_of(ctx.session, realm.id)
        if ruler is not None:
            claims.append((ruler, RightKind.TITLE, realm))
    for holder, kind, subject in claims:
        if budget <= 0:
            return
        if subject.id in held_subjects or held(holder):
            continue
        ctx.session.add(
            IncorporealRightRow(
                holder_node_id=holder,
                kind=kind,
                subject_node_id=subject.id,
                name=subject.name,
                acquired=RightAcquired.CREATED,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        held_subjects.add(subject.id)
        tally.claimed += 1
        budget -= 1


async def place_of(ctx: TickContext, holder_id: int) -> int | None:
    holder = await ctx.session.get(EntityRow, holder_id)
    if holder is None:
        return None
    if holder.entity_type is EntityType.HOUSE:
        member = await ctx.session.scalar(
            select(EntityRow.location_id)
            .join(HouseMemberRow, HouseMemberRow.mortal_entity_id == EntityRow.id)
            .where(HouseMemberRow.house_entity_id == holder.id)
            .limit(1)
        )
        return member
    return holder.location_id


async def infringe(ctx: TickContext, row: IncorporealRightRow, tally: RightsTally) -> None:
    table = ctx.rules.incorporeal
    rng = ctx.rng(seed_of("right.infringe", row.id, ctx.epoch))
    if not rng.chance(table.infringe_chance):
        return
    town = await place_of(ctx, row.holder_node_id)
    if town is None:
        return
    kin = set(await ctx.session.scalars(select(HouseMemberRow.mortal_entity_id).where(HouseMemberRow.house_entity_id == row.holder_node_id)))
    others = [
        mortal
        for mortal in await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [town]))
            .order_by(EntityRow.id)
        )
        if mortal.id not in kin | {row.holder_node_id, row.licensed_to_node_id} and not held(mortal.id)
    ]
    if not others:
        return
    culprit = rng.pick(others)
    await change_relation(ctx, row.holder_node_id, culprit.id, -table.insult_opinion, MemoryKind.ILL_WILL, note=f"took {row.name} that is ours")
    tally.infringed += 1
    if row.kind in COPIED:
        await report_crime(ctx, town, culprit.id, CrimeKind.THEFT)
        if rng.chance(table.steal_chance):
            ctx.session.add(
                IncorporealRightRow(
                    holder_node_id=culprit.id,
                    kind=row.kind,
                    subject_node_id=row.subject_node_id,
                    name=row.name,
                    acquired=RightAcquired.STOLEN,
                    since_epoch=ctx.epoch,
                    locked=[],
                )
            )
    await record(
        ctx,
        "rights.infringed",
        roles={IncidentRole.ACTOR: culprit.id, IncidentRole.VICTIM: row.holder_node_id},
        facts={"right": row.name, "kind": row.kind, "opinion": -table.insult_opinion},
        place=town,
    )


async def collect_licence(ctx: TickContext, row: IncorporealRightRow, tally: RightsTally) -> None:
    if row.licensed_to_node_id is None:
        return
    fee = ctx.rules.incorporeal.licence_fee
    licensee = await ctx.session.get(EntityRow, row.licensed_to_node_id)
    holder = await ctx.session.get(EntityRow, row.holder_node_id)
    if licensee is None or holder is None or held(licensee.id):
        return
    if await points_of(ctx.session, licensee) < fee:
        if "licensed_to_node_id" not in row.locked:
            row.licensed_to_node_id = None
        return
    price = ctx.rules.incorporeal.buy_price
    if await points_of(ctx.session, holder) < fee and await points_of(ctx.session, licensee) >= price and "holder_node_id" not in row.locked:
        await shift_points(ctx.session, licensee, -price)
        await shift_points(ctx.session, holder, price)
        row.holder_node_id, row.acquired, row.licensed_to_node_id = licensee.id, RightAcquired.BOUGHT, None
        await record(
            ctx,
            "rights.bought",
            roles={IncidentRole.BUYER: licensee.id, IncidentRole.SELLER: holder.id},
            facts={"right": row.name, "kind": row.kind, "price": price},
            steps=(StepDraft(StepAction.PAY, actor=licensee.id, target=holder.id, amount=price, unit=FactUnit.WEALTH_POINTS),),
        )
        return
    await shift_points(ctx.session, licensee, -fee)
    await shift_points(ctx.session, holder, fee)
    await licensed_copy(ctx, row, licensee.id)
    tally.licensed += 1


async def licensed_copy(ctx: TickContext, row: IncorporealRightRow, licensee_id: int) -> None:
    found = await ctx.session.scalar(
        select(IncorporealRightRow.id).where(
            IncorporealRightRow.holder_node_id == licensee_id,
            IncorporealRightRow.subject_node_id == row.subject_node_id,
            IncorporealRightRow.acquired == RightAcquired.LICENSED,
        )
    )
    if found is None and not held(licensee_id):
        ctx.session.add(
            IncorporealRightRow(
                holder_node_id=licensee_id,
                kind=row.kind,
                subject_node_id=row.subject_node_id,
                name=row.name,
                acquired=RightAcquired.LICENSED,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )


async def keep_rights(ctx: TickContext, tally: RightsTally) -> None:
    await claim_works(ctx, tally)
    await ctx.session.flush()
    for row in list(await ctx.session.scalars(select(IncorporealRightRow).order_by(IncorporealRightRow.id))):
        if held(row.holder_node_id):
            continue
        await infringe(ctx, row, tally)
        await collect_licence(ctx, row, tally)
    await ctx.session.flush()

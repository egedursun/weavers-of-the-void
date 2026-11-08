from itertools import pairwise

from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OathRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held, unheld
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import HERO_ROLES, EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.intrigue import IntrigueSecret
from aerona.domain.enums.mind import ActKind, MemoryKind, WantKind
from aerona.domain.enums.polity import OathKind, OathStatus
from aerona.domain.enums.son import SonStatus
from aerona.engine.context import TickContext
from aerona.engine.faith.book import faith_tenets, patron_node
from aerona.engine.gods.progress import cap_gained_essence
from aerona.engine.intrigue.secrets import keep_secret
from aerona.engine.mind.aspirations import open_wants
from aerona.engine.mind.hooks import judged
from aerona.engine.mind.memories import remember
from aerona.engine.mortal.standing import add_honour
from aerona.engine.notes import note
from aerona.engine.primitives.queries import add_flag, living_entity
from aerona.engine.relations.passions import invoke
from aerona.engine.services.community_relations import change_relation

TIMED = frozenset({OathKind.VENGEANCE, OathKind.PILGRIMAGE})
CLERGY = frozenset({MortalRole.PRIEST, MortalRole.SAINT, MortalRole.SEER})


async def oath_god(ctx: TickContext, world_id: int | None) -> SonRow | None:
    sons = await ctx.session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE, SonRow.current_world_id == world_id).order_by(SonRow.id))
    fitting = [son for son in sons if Domain.OATH in (son.domain_primary, son.domain_secondary)]
    return max(fitting, key=lambda son: (son.charisma, -son.id), default=None)


async def swear(
    ctx: TickContext, swearer: EntityRow, kind: OathKind, *, recipient_id: int | None, note_text: str | None = None, witness: SonRow | None = None
) -> OathRow:
    open_oath = await ctx.session.scalar(
        select(OathRow).where(
            OathRow.swearer_entity_id == swearer.id, OathRow.kind == kind, OathRow.recipient_node_id == recipient_id, OathRow.status == OathStatus.SWORN
        )
    )
    if open_oath is not None:
        return open_oath
    table = ctx.rules.oaths
    if witness is None and ctx.rng(f"oath_witness.{swearer.id}.{kind.value}.{recipient_id}").chance(table.witness_chance):
        witness = await oath_god(ctx, swearer.world_id)
    row = OathRow(
        swearer_entity_id=swearer.id,
        recipient_node_id=recipient_id,
        kind=kind,
        witness_son_id=witness.id if witness is not None else None,
        status=OathStatus.SWORN,
        sworn_epoch=ctx.epoch,
        deadline_epoch=ctx.epoch + table.deadline_epochs if kind in TIMED else None,
        ended_epoch=None,
        note=(note_text or "")[:120] or None,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    ctx.count(f"oath.{kind.value}")
    return row


async def wrath(ctx: TickContext, witness: SonRow, swearer: EntityRow) -> None:
    table = ctx.rules.oaths
    if witness.status is not SonStatus.ACTIVE:
        return
    before = witness.essence
    witness.essence += table.wrath_essence
    cap_gained_essence(ctx.rules, witness, before)
    cursed = ctx.rng(f"wrath.{witness.id}.{swearer.id}.{ctx.epoch}").chance(table.wrath_curse_chance)
    if cursed:
        await add_flag(ctx.session, swearer.id, EntityFlag.CURSED, ctx.epoch)
    await note(
        ctx,
        f"{witness.name} turned in wrath on {swearer.name}, who broke an oath sworn before it" + ("; a curse fell on the oathbreaker." if cursed else "."),
        key="oaths.wrath",
        ids=[swearer.id],
        son_id=witness.id,
        kind=ChronicleKind.DIVINE_SIGN,
    )


async def keep(ctx: TickContext, oath: OathRow, *, fulfilled: bool) -> None:
    oath.status = OathStatus.FULFILLED if fulfilled else OathStatus.KEPT
    oath.ended_epoch = ctx.epoch
    await add_honour(ctx.session, oath.swearer_entity_id, ctx.rules.standing.honour_kept_oath, ctx.epoch)
    if oath.recipient_node_id is not None:
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=oath.recipient_node_id,
            subject_id=oath.swearer_entity_id,
            kind=MemoryKind.KEPT_OATH,
            magnitude=10,
            epoch=ctx.epoch,
        )
    await reward_witness(ctx, oath)


async def reward_witness(ctx: TickContext, oath: OathRow) -> None:
    if oath.witness_son_id is None:
        return
    son = await ctx.session.get(SonRow, oath.witness_son_id)
    if son is None or son.status is not SonStatus.ACTIVE:
        return
    before = son.essence
    son.essence += ctx.rules.oaths.essence_per_kept
    cap_gained_essence(ctx.rules, son, before)


async def break_oath(ctx: TickContext, oath: OathRow, reason: str) -> None:
    table = ctx.rules.oaths
    oath.status = OathStatus.BROKEN
    oath.ended_epoch = ctx.epoch
    swearer = await ctx.session.get(EntityRow, oath.swearer_entity_id)
    if swearer is None:
        return
    swearer.importance = max(0, (swearer.importance or 0) - table.honour_loss)
    await judged(ctx, swearer.id, oath.recipient_node_id or swearer.id, ActKind.OATHBREAKING)
    if swearer.entity_type is EntityType.MORTAL:
        await add_honour(ctx.session, swearer.id, -ctx.rules.standing.honour_broken_oath, ctx.epoch)
    await add_flag(ctx.session, swearer.id, EntityFlag.OATHBREAKER, ctx.epoch)
    await keep_secret(
        ctx,
        swearer.id,
        IntrigueSecret.BROKEN_OATH,
        about_id=oath.recipient_node_id,
        known_by=tuple(filter(None, (oath.recipient_node_id,))),
        source=f"oath.{oath.id}",
    )
    if oath.recipient_node_id is not None:
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=oath.recipient_node_id,
            subject_id=swearer.id,
            kind=MemoryKind.BROKE_OATH,
            magnitude=-table.breach_relation,
            epoch=ctx.epoch,
        )
    witness = await ctx.session.get(SonRow, oath.witness_son_id) if oath.witness_son_id is not None else None
    if witness is not None and swearer.location_id is not None:
        home = await living_entity(ctx.session, swearer.location_id)
        if home is not None and home.entity_type in {EntityType.SETTLEMENT, EntityType.PEOPLE} and home.status is EntityStatus.CANON:
            await change_relation(ctx, home.id, swearer.id, -table.wrath_relation, MemoryKind.BROKE_OATH, note=f"broke an oath sworn before {witness.name}")
    if witness is not None:
        await wrath(ctx, witness, swearer)
    await note(
        ctx,
        f"{swearer.name} broke the {oath.kind.value.replace('_', ' ')} oath{f' sworn before {witness.name}' if witness else ''}: {reason}.",
        key="oaths.broken",
        ids=[swearer.id],
        son_id=witness.id if witness else None,
        kind=ChronicleKind.WORLD,
    )


async def lapse(ctx: TickContext) -> tuple[int, int]:
    kept = broken = 0
    rows = await ctx.session.scalars(select(OathRow).where(OathRow.status == OathStatus.SWORN).order_by(OathRow.id))
    for oath in rows:
        swearer = await ctx.session.get(EntityRow, oath.swearer_entity_id)
        if swearer is None or swearer.status is not EntityStatus.CANON:
            await keep(ctx, oath, fulfilled=True)
            kept += 1
            continue
        if oath.kind is OathKind.VENGEANCE and await avenged(ctx, oath):
            await keep(ctx, oath, fulfilled=True)
            kept += 1
            continue
        if oath.kind is OathKind.PILGRIMAGE and await journeyed(ctx, oath, swearer):
            await keep(ctx, oath, fulfilled=True)
            kept += 1
            continue
        if oath.deadline_epoch is not None and ctx.epoch > oath.deadline_epoch and await invoke(ctx, swearer, [oath.recipient_node_id or swearer.id]) > 1:
            oath.deadline_epoch = ctx.epoch + 1
            continue
        if oath.deadline_epoch is not None and ctx.epoch > oath.deadline_epoch:
            await break_oath(ctx, oath, "the blood went unavenged" if oath.kind is OathKind.VENGEANCE else "the road was never walked")
            broken += 1
        elif oath.kind in {OathKind.FEALTY, OathKind.PROTECTION, OathKind.SWORN_KINSHIP, OathKind.CELIBACY, OathKind.SILENCE}:
            await reward_witness(ctx, oath)
    return kept, broken


async def avenged(ctx: TickContext, oath: OathRow) -> bool:
    if oath.recipient_node_id is None:
        return False
    target = await ctx.session.get(EntityRow, oath.recipient_node_id)
    if target is None or target.status is EntityStatus.CANON:
        return False
    return target.end_epoch is None or target.end_epoch >= oath.sworn_epoch


async def journeyed(ctx: TickContext, oath: OathRow, swearer: EntityRow) -> bool:
    if oath.recipient_node_id is None:
        return swearer.location_id is not None and ctx.epoch > oath.sworn_epoch and swearer.location_id != home_at_oath(oath)
    return swearer.location_id == oath.recipient_node_id


def home_at_oath(oath: OathRow) -> int | None:
    return int(oath.note) if oath.note is not None and oath.note.isdigit() else None


async def break_on(ctx: TickContext, swearer_ids: list[int], kind: OathKind, reason: str, *, recipient_id: int | None = None) -> int:
    broken = 0
    for swearer_id in swearer_ids:
        for oath in await oaths_of(ctx, swearer_id, kind):
            if recipient_id is not None and oath.recipient_node_id != recipient_id:
                continue
            await break_oath(ctx, oath, reason)
            broken += 1
    return broken


async def vows(ctx: TickContext) -> int:
    table = ctx.rules.oaths
    sworn = 0
    for mortal in await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.is_not(None))
    ):
        if held(mortal.id):
            continue
        tenets = await faith_tenets(ctx.session, mortal.location_id or 0)
        chaste = mortal.mortal_role in CLERGY and TenetKind.CELIBATE_CLERGY in tenets
        if chaste and ctx.rng(f"celibacy.{mortal.id}.{ctx.epoch}").chance(table.celibacy_chance) and not await oaths_of(ctx, mortal.id, OathKind.CELIBACY):
            await swear(ctx, mortal, OathKind.CELIBACY, recipient_id=None, note_text="for the faith")
            sworn += 1
        dutiful = TenetKind.PILGRIMAGE_DUTY in tenets and ctx.rng(f"pilgrimage.{mortal.id}.{ctx.epoch}").chance(table.pilgrimage_chance)
        longing = WantKind.VISIT_A_SHRINE in await open_wants(ctx.session, mortal.id)
        pilgrim = dutiful or (longing and ctx.rng(f"shrine_want.{mortal.id}.{ctx.epoch}").chance(ctx.rules.aspirations.want_shrine_pct))
        if pilgrim and not await oaths_of(ctx, mortal.id, OathKind.PILGRIMAGE):
            holy = await holy_site(ctx, mortal)
            await swear(ctx, mortal, OathKind.PILGRIMAGE, recipient_id=holy, note_text=None if holy is not None else str(mortal.location_id))
            sworn += 1
    return sworn


async def holy_site(ctx: TickContext, mortal: EntityRow) -> int | None:
    god = await patron_node(ctx.session, mortal.location_id or 0)
    if god is None:
        return None
    cults = await ctx.session.scalars(
        select(EntityRow.location_id)
        .join(BondRow, BondRow.source_node_id == EntityRow.id)
        .where(
            BondRow.target_node_id == god, BondRow.kind == BondKind.WORSHIPS, EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON
        )
        .order_by(EntityRow.id)
    )
    return next((place for place in cults if place is not None and place != mortal.location_id), None)


async def oaths_of(ctx: TickContext, swearer_id: int, kind: OathKind | None = None) -> list[OathRow]:
    statement = select(OathRow).where(OathRow.swearer_entity_id == swearer_id, OathRow.status == OathStatus.SWORN)
    if kind is not None:
        statement = statement.where(OathRow.kind == kind)
    return list(await ctx.session.scalars(statement.order_by(OathRow.id)))


async def pledges(ctx: TickContext, rulers: dict[int, int]) -> int:
    table = ctx.rules.oaths
    made = 0
    mortals = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.mortal_role.in_(list(HERO_ROLES)))
    )
    companions: dict[int, list[EntityRow]] = {}
    for mortal in unheld(mortals):
        lord = rulers.get(mortal.location_id or -1)
        sworn = mortal.mortal_role is MortalRole.KNIGHT and lord is not None and lord != mortal.id
        if sworn and ctx.rng(f"protection.{mortal.id}.{ctx.epoch}").chance(table.protection_chance):
            await swear(ctx, mortal, OathKind.PROTECTION, recipient_id=lord, note_text="to guard the ruler")
            made += 1
        companions.setdefault(mortal.location_id or -1, []).append(mortal)
    for group in companions.values():
        for first, second in pairwise(group):
            if ctx.rng(f"kinship.{first.id}.{second.id}.{ctx.epoch}").chance(table.kinship_chance):
                await swear(ctx, first, OathKind.SWORN_KINSHIP, recipient_id=second.id, note_text="companions in arms")
                await swear(ctx, second, OathKind.SWORN_KINSHIP, recipient_id=first.id, note_text="companions in arms")
                made += 2
    return made

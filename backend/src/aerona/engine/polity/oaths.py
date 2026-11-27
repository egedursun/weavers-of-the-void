from itertools import pairwise

from sqlalchemy import select

from aerona.catalog.life.polity import LAPSE_OATH_KINDS
from aerona.catalog.life_traits import OATH_KIND_TRAITS, having
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OathRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held, unheld
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import HERO_ROLES, EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.fortune import FortuneSourceKind
from aerona.domain.enums.intrigue import IntrigueSecret
from aerona.domain.enums.life_traits import OathKindTrait
from aerona.domain.enums.mind import ActKind, MemoryKind, TraitKind, TraitSource, WantKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OathBreach, OathKind, OathStatus
from aerona.domain.enums.records import StepAction
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.enums.son import SonStatus
from aerona.engine.body.conditions import gain_condition
from aerona.engine.context import TickContext
from aerona.engine.divine.laws import binds
from aerona.engine.faith.book import faith_tenets, patron_node
from aerona.engine.fortune.profiles import shift_fortune
from aerona.engine.gods.progress import cap_gained_essence
from aerona.engine.intrigue.secrets import keep_secret
from aerona.engine.mind.aspirations import open_wants
from aerona.engine.mind.hooks import judged
from aerona.engine.mind.memories import remember
from aerona.engine.mind.traits import gain_trait
from aerona.engine.mortal.standing import add_honour
from aerona.engine.polity.oath_terms import answer_breach, honour_weight, scaled_loss, terms_for, witness_answer
from aerona.engine.polity.vows import BREACHES, VOWS
from aerona.engine.primitives.queries import add_flag, living_entity
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.recording.terms import explaining
from aerona.engine.relations.passions import invoke
from aerona.engine.services.community_relations import change_relation

TIMED = having(OATH_KIND_TRAITS, OathKindTrait.TIMED)
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
    if witness is None and ctx.rng(f"oath_witness.{swearer.id}.{kind.value}.{recipient_id if recipient_id is not None else 'unbound'}").chance(
        table.witness_chance
    ):
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
        note=note_text or None,
    )
    row.witness_node_id, row.penalty = await terms_for(ctx, swearer)
    ctx.session.add(row)
    await ctx.session.flush()
    ctx.count(f"oath.{kind.value}")
    return row


async def wrath(ctx: TickContext, witness: SonRow, swearer: EntityRow, cause: int | None) -> None:
    if witness.status is not SonStatus.ACTIVE:
        return
    with explaining():
        table = ctx.rules.oaths
        before = witness.essence
        witness.essence += table.wrath_essence
        cap_gained_essence(ctx.rules, witness, before)
        cursed = ctx.rng(f"wrath.{witness.id}.{swearer.id}.{ctx.epoch}").chance(table.wrath_curse_chance)
        if cursed:
            await add_flag(ctx.session, swearer.id, EntityFlag.CURSED, ctx.epoch)
        await record(
            ctx,
            "oaths.wrath_cursed" if cursed else "oaths.wrath",
            roles={IncidentRole.PATRON: witness.id, IncidentRole.TARGET: swearer.id},
            facts={"essence": witness.essence - before, "curse_chance": table.wrath_curse_chance},
            place=swearer.location_id,
            cause=cause,
            son_id=witness.id,
        )


async def keep(ctx: TickContext, oath: OathRow, *, fulfilled: bool) -> None:
    oath.status = OathStatus.FULFILLED if fulfilled else OathStatus.KEPT
    oath.ended_epoch = ctx.epoch
    await add_honour(ctx.session, oath.swearer_entity_id, ctx.rules.standing.honour_kept_oath, ctx.epoch)
    swearer = await ctx.session.get(EntityRow, oath.swearer_entity_id)
    if swearer is not None and await binds(ctx, NaturalLaw.OATHS_BIND, swearer):
        await shift_fortune(ctx, swearer.id, ctx.rules.fortune.oath_strength, FortuneSourceKind.OATH_KEPT)
    if swearer is not None and swearer.entity_type is EntityType.MORTAL:
        await gain_trait(ctx, swearer.id, (TraitKind.LOYAL,), ctx.rules.traits.oath_chance, TraitSource.EXPERIENCE, stream="oath_kept_trait")
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
    await witness_answer(ctx, oath, kept=True)


async def reward_witness(ctx: TickContext, oath: OathRow) -> None:
    if oath.witness_son_id is None:
        return
    son = await ctx.session.get(SonRow, oath.witness_son_id)
    if son is None or son.status is not SonStatus.ACTIVE:
        return
    before = son.essence
    son.essence += round(ctx.rules.oaths.essence_per_kept * (1 + await ctx.god_share(son.id, DomainHook.OATH_TITHE)))
    cap_gained_essence(ctx.rules, son, before)


async def break_oath(ctx: TickContext, oath: OathRow, breach: OathBreach, *, occasion: int | None = None, cause: int | None = None) -> None:
    with explaining():
        await broken_oath(ctx, oath, breach, occasion, cause)


async def broken_oath(ctx: TickContext, oath: OathRow, breach: OathBreach, occasion: int | None, cause: int | None) -> None:
    table = ctx.rules.oaths
    oath.status = OathStatus.BROKEN
    oath.ended_epoch = ctx.epoch
    swearer = await ctx.session.get(EntityRow, oath.swearer_entity_id)
    if swearer is None:
        return
    weight = await honour_weight(ctx, swearer)
    standing_before = swearer.importance or 0
    swearer.importance = max(0, standing_before - scaled_loss(table.honour_loss, weight))
    await judged(ctx, swearer.id, oath.recipient_node_id or swearer.id, ActKind.OATHBREAKING)
    if swearer.entity_type is EntityType.MORTAL:
        await add_honour(ctx.session, swearer.id, -scaled_loss(ctx.rules.standing.honour_broken_oath, weight), ctx.epoch)
    await answer_breach(ctx, oath, swearer)
    await add_flag(ctx.session, swearer.id, EntityFlag.OATHBREAKER, ctx.epoch)
    if await binds(ctx, NaturalLaw.OATHS_BIND, swearer):
        await shift_fortune(ctx, swearer.id, -ctx.rules.fortune.oath_strength, FortuneSourceKind.OATH_BROKEN)
    if swearer.entity_type is EntityType.MORTAL:
        await gain_trait(ctx, swearer.id, (TraitKind.DISLOYAL,), ctx.rules.traits.oath_chance, TraitSource.EXPERIENCE, stream="oath_broken_trait")
    if swearer.entity_type is EntityType.MORTAL and await binds(ctx, NaturalLaw.OATHS_BIND, swearer):
        await gain_condition(ctx, swearer, ConditionKind.DIVINE_BRAND, HarmCause.GOD)
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
    written = await record(
        ctx,
        "oaths.broken",
        roles={
            IncidentRole.SUBJECT: swearer.id,
            IncidentRole.RECEIVER: oath.recipient_node_id,
            IncidentRole.PATRON: witness.id if witness is not None else None,
        },
        facts={"oath_kind": oath.kind, "breach": breach, "occasion": occasion, "standing_lost": standing_before - swearer.importance},
        place=swearer.location_id,
        cause=cause,
        son_id=witness.id if witness else None,
        steps=(StepDraft(StepAction.BREAK_OATH, actor=swearer.id, target=oath.recipient_node_id, record_table=OathRow.__tablename__, record_key=str(oath.id)),),
    )
    if witness is not None:
        await wrath(ctx, witness, swearer, written.incident_id)


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
        if await sworn_to_the_dead(ctx, oath):
            oath.status, oath.ended_epoch = OathStatus.FULFILLED, ctx.epoch
            kept += 1
            continue
        if oath.deadline_epoch is not None and ctx.epoch > oath.deadline_epoch and await invoke(ctx, swearer, [oath.recipient_node_id or swearer.id]) > 1:
            oath.deadline_epoch = ctx.epoch + 1
            continue
        if oath.deadline_epoch is not None and ctx.epoch > oath.deadline_epoch:
            await break_oath(ctx, oath, OathBreach.BLOOD_UNAVENGED if oath.kind is OathKind.VENGEANCE else OathBreach.ROAD_UNWALKED)
            broken += 1
        elif oath.kind in BREACHES and (breach := await BREACHES[oath.kind](ctx, oath, swearer)) is not None:
            await break_oath(ctx, oath, breach)
            broken += 1
        elif oath.kind in LAPSE_OATH_KINDS or oath.kind in BREACHES:
            await reward_witness(ctx, oath)
    return kept, broken


async def sworn_to_the_dead(ctx: TickContext, oath: OathRow) -> bool:
    if oath.recipient_node_id is None or oath.kind is OathKind.VENGEANCE:
        return False
    recipient = await ctx.session.get(EntityRow, oath.recipient_node_id)
    return recipient is not None and recipient.entity_type is EntityType.MORTAL and recipient.status is not EntityStatus.CANON


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


async def break_on(
    ctx: TickContext, swearer_ids: list[int], kind: OathKind, breach: OathBreach, *, recipient_id: int | None = None, occasion: int | None = None
) -> int:
    broken = 0
    for swearer_id in swearer_ids:
        for oath in await oaths_of(ctx, swearer_id, kind):
            if recipient_id is not None and oath.recipient_node_id != recipient_id:
                continue
            await break_oath(ctx, oath, breach, occasion=occasion)
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
        sworn += await take_vows(ctx, mortal, frozenset(tenets))
    return sworn


async def take_vows(ctx: TickContext, mortal: EntityRow, tenets: frozenset[TenetKind]) -> int:
    sworn = 0
    for kind, swore in VOWS.items():
        wanted, recipient = await swore(ctx, mortal, tenets)
        if not wanted or await oaths_of(ctx, mortal.id, kind) or not ctx.rng(f"vow.{kind.value}.{mortal.id}.{ctx.epoch}").chance(ctx.rules.oaths.vow_chance):
            continue
        await swear(ctx, mortal, kind, recipient_id=recipient, note_text=None)
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
        sworn = mortal.mortal_role is MortalRole.SWORN_WARRIOR and lord is not None and lord != mortal.id
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

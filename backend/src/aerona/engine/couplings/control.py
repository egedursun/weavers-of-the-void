from collections.abc import Mapping
from typing import Any

from sqlalchemy import select

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.couplings import (
    CARRION_FIELDS,
    FIELD_AGREEMENT_FIELDS,
    NOVELTY_FIELDS,
    SEAL_FIELDS,
    SIGN_FIELDS,
    SOCIOLECT_FIELDS,
    TEACHING_FIELDS,
    CaptiveRestraintRow,
    CarrionPulseRow,
    DeepSealRow,
    FieldAgreementRow,
    NoveltyStockRow,
    RiteComponentRow,
    SignOriginRow,
    SociolectRow,
    TeachingRow,
)
from aerona.db.tables.cuisine import DishRow
from aerona.db.tables.culture import RiteProfileRow
from aerona.db.tables.discovery import ArtFormProfileRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import CollectionRow
from aerona.db.tables.warfare import CaptiveRow, WarSideRow
from aerona.domain.enums.collective import AccountKind, AccountMedium
from aerona.domain.enums.couplings import (
    CarrionRest,
    FieldAgreementKind,
    FieldAgreementState,
    RestraintKind,
    RiteComponent,
    SealKind,
    SignCause,
    SociolectKind,
    TeachingKind,
    TeachingState,
)
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.engine.context import TickContext
from aerona.engine.couplings.deep import seal_deep
from aerona.engine.couplings.field import agree
from aerona.engine.couplings.registers import SPEECH_PRESTIGE, make_sign_language
from aerona.engine.couplings.teachers import BEAST_LESSONS, lesson
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import allowed
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import living_entity, spoken_language


async def require[Row](ctx: TickContext, model: type[Row], key: Any, label: str) -> Row:
    row = await ctx.session.get(model, key)
    if row is None:
        raise NotFoundError(f"No such {label}.")
    return row


async def edited[Row: Base](ctx: TickContext, row: Row, values: Mapping[str, Any], release: list[str], *, fields: tuple[str, ...], label: str) -> Row:
    allowed(values, fields, label)
    apply(row, values, release)
    await ctx.session.flush()
    return row


async def removed(ctx: TickContext, row: Any) -> None:
    await ctx.session.delete(row)
    await ctx.session.flush()


async def set_component(ctx: TickContext, rite_id: int, component: RiteComponent, present: bool) -> bool:
    await require(ctx, RiteProfileRow, rite_id, "rite")
    row = await ctx.session.get(RiteComponentRow, (rite_id, component))
    if present and row is None:
        ctx.session.add(RiteComponentRow(rite_entity_id=rite_id, component=component))
    elif not present and row is not None:
        await ctx.session.delete(row)
    await ctx.session.flush()
    return present


async def set_restraint(ctx: TickContext, captive_id: int, restraint: RestraintKind, present: bool) -> bool:
    await require(ctx, CaptiveRow, captive_id, "captive")
    row = await ctx.session.get(CaptiveRestraintRow, (captive_id, restraint))
    if present and row is None:
        ctx.session.add(CaptiveRestraintRow(captive_id=captive_id, restraint=restraint))
    elif not present and row is not None:
        await ctx.session.delete(row)
    await ctx.session.flush()
    return present


async def living(ctx: TickContext, entity_id: int, label: str) -> EntityRow:
    entity = await living_entity(ctx.session, entity_id)
    if entity is None:
        raise NotFoundError(f"No such {label} among the living.")
    return entity


async def create_sociolect(ctx: TickContext, holder_id: int, kind: SociolectKind) -> SociolectRow:
    holder = await living(ctx, holder_id, "group")
    language = await spoken_language(ctx.session, holder.id if holder.entity_type is not EntityType.FACTION else holder.location_id or holder.id)
    if language is None:
        raise ValidationFailedError(f"{holder.name} speaks no language to make a way of speaking from.")
    row = SociolectRow(
        language_entity_id=language.id,
        holder_entity_id=holder.id,
        kind=kind,
        prestige=SPEECH_PRESTIGE[kind],
        secret=kind is SociolectKind.CANT,
        salience=ctx.rules.couplings.sociolect_start,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def merge_sociolects(ctx: TickContext, kept_id: int, merged_id: int) -> SociolectRow:
    kept = await require(ctx, SociolectRow, kept_id, "way of speaking")
    merged = await require(ctx, SociolectRow, merged_id, "way of speaking")
    if kept.id == merged.id or kept.language_entity_id != merged.language_entity_id:
        raise ValidationFailedError("Only two different ways of speaking one language can be merged.")
    kept.salience = clamp_percent(max(kept.salience, merged.salience))
    kept.prestige = (kept.prestige + merged.prestige) // 2
    await ctx.session.delete(merged)
    await ctx.session.flush()
    return kept


async def create_sign_language(ctx: TickContext, community_id: int, cause: SignCause) -> EntityRow:
    community = await living(ctx, community_id, "community")
    if community.entity_type not in COMMUNITY_TYPES:
        raise ValidationFailedError("Only a community can come to share a signed language.")
    return await make_sign_language(ctx, community, cause)


async def keep_dead(ctx: TickContext, region_id: int, kept: bool) -> CarrionPulseRow:
    region = await living(ctx, region_id, "region")
    row = await ctx.session.get(CarrionPulseRow, region.id)
    if row is None:
        row = CarrionPulseRow(
            region_entity_id=region.id, carrion=0, scavenged=0, preserved=False, rest=CarrionRest.ROTTING, kept=kept, epoch=ctx.epoch, locked=[]
        )
        ctx.session.add(row)
    row.kept = kept
    await ctx.session.flush()
    return row


async def clear_dead(ctx: TickContext, region_id: int) -> int:
    row = await require(ctx, CarrionPulseRow, region_id, "carrion of a region")
    cleared = row.carrion
    await ctx.session.delete(row)
    await ctx.session.flush()
    return cleared


async def grant_teaching(ctx: TickContext, teacher_id: int, learner_id: int, kind: TeachingKind) -> TeachingRow:
    teacher = await living(ctx, teacher_id, "teacher")
    learner = await living(ctx, learner_id, "learner")
    if teacher.entity_type not in (EntityType.SPIRIT, EntityType.BEAST):
        raise ValidationFailedError("Only a spirit or a beast teaches the living this way.")
    row = await lesson(ctx, teacher, learner, kinds=(kind,), forced=True)
    if row is None:
        raise ValidationFailedError(f"{teacher.name} has nothing of that kind left to teach {learner.name}.")
    return row


async def block_teaching(ctx: TickContext, teacher_id: int, learner_id: int) -> TeachingRow:
    teacher = await living(ctx, teacher_id, "teacher")
    learner = await living(ctx, learner_id, "learner")
    row = TeachingRow(
        teacher_node_id=teacher.id,
        learner_entity_id=learner.id,
        kind=TeachingKind.ACCOUNT,
        fidelity=0,
        state=TeachingState.BLOCKED,
        price=0,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def grant_lore(ctx: TickContext, beast_id: int, collection_id: int) -> AccountRow:
    beast = await living(ctx, beast_id, "beast")
    profile = await require(ctx, BeastProfileRow, beast.id, "beast")
    await require(ctx, CollectionRow, collection_id, "gathering of happenings")
    row = AccountRow(
        holder_entity_id=beast.id,
        author_node_id=beast.id,
        kind=AccountKind.ELDER_MEMORY,
        medium=AccountMedium.ORAL,
        collection_id=collection_id,
        fidelity=clamp_percent(profile.intelligence),
        credence=clamp_percent(profile.age),
        defaced=False,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def reveal_lore(ctx: TickContext, beast_id: int, learner_id: int) -> TeachingRow:
    beast = await living(ctx, beast_id, "beast")
    learner = await living(ctx, learner_id, "learner")
    row = await lesson(ctx, beast, learner, kinds=BEAST_LESSONS, forced=True)
    if row is None:
        raise ValidationFailedError(f"{beast.name} has nothing it has not already told {learner.name}.")
    return row


async def force_agreement(
    ctx: TickContext, kind: FieldAgreementKind, war_id: int | None, *, commander_id: int | None, counterpart_id: int | None, place_id: int | None
) -> FieldAgreementRow:
    term = ctx.epoch + ctx.rules.field_diplomacy.truce_epochs
    return await agree(ctx, war_id, kind, commander=commander_id, counterpart=counterpart_id, place=place_id, term=term, honour=0)


async def void_agreement(ctx: TickContext, agreement_id: int) -> FieldAgreementRow:
    row = await require(ctx, FieldAgreementRow, agreement_id, "field agreement")
    if row.state is not FieldAgreementState.KEPT:
        raise ValidationFailedError("Only an agreement still kept can be voided.")
    row.state = FieldAgreementState.REPUDIATED
    row.ended_epoch = ctx.epoch
    if row.war_id is not None:
        for side in await ctx.session.scalars(select(WarSideRow).where(WarSideRow.war_id == row.war_id)):
            if "support" not in side.locked:
                side.support = clamp_percent(side.support - ctx.rules.field_diplomacy.broken_memory // 4)
    await ctx.session.flush()
    return row


async def seal(ctx: TickContext, place_id: int, kind: SealKind, strength: int) -> DeepSealRow:
    place = await living(ctx, place_id, "place")
    return await seal_deep(ctx, place.id, kind, None, strength)


async def unseal(ctx: TickContext, seal_id: int) -> DeepSealRow:
    row = await require(ctx, DeepSealRow, seal_id, "seal")
    row.strength = 0
    row.broken_epoch = ctx.epoch
    await ctx.session.flush()
    return row


async def set_novelty(ctx: TickContext, holder_id: int, values: Mapping[str, Any], release: list[str]) -> NoveltyStockRow:
    holder = await living(ctx, holder_id, "art form or dish")
    dish = await ctx.session.scalar(select(DishRow.id).where(DishRow.entity_id == holder.id).limit(1))
    if await ctx.session.get(ArtFormProfileRow, holder.id) is None and dish is None:
        raise ValidationFailedError(f"{holder.name} is neither an art form nor a dish, so it has no fashion.")
    row = await ctx.session.get(NoveltyStockRow, holder.id)
    if row is None:
        row = NoveltyStockRow(holder_entity_id=holder.id, novelty=ctx.rules.fashion.start, adoption=0, revivals=0, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    return await edited(ctx, row, values, release, fields=NOVELTY_FIELDS, label="fashion of a form")


EDITABLE = {
    "sociolect": (SociolectRow, SOCIOLECT_FIELDS, "way of speaking"),
    "sign_origin": (SignOriginRow, SIGN_FIELDS, "signed language"),
    "carrion": (CarrionPulseRow, CARRION_FIELDS, "carrion of a region"),
    "teaching": (TeachingRow, TEACHING_FIELDS, "teaching"),
    "field_agreement": (FieldAgreementRow, FIELD_AGREEMENT_FIELDS, "field agreement"),
    "deep_seal": (DeepSealRow, SEAL_FIELDS, "seal"),
    "novelty": (NoveltyStockRow, NOVELTY_FIELDS, "fashion of a form"),
}


async def edit_record(ctx: TickContext, table: str, key: int, values: Mapping[str, Any], release: list[str]) -> Any:
    model, fields, label = EDITABLE[table]
    return await edited(ctx, await require(ctx, model, key, label), values, release, fields=fields, label=label)


async def remove_record(ctx: TickContext, table: str, key: int) -> None:
    model, _fields, label = EDITABLE[table]
    await removed(ctx, await require(ctx, model, key, label))

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.discovery import ArtFormPractitionerRow, ArtFormProfileRow, TheoryAdherentRow, TheoryAnomalyRow, TheoryProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.discovery import AnomalyKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.engine.context import TickContext
from aerona.engine.lore.truth import ruling
from aerona.engine.polity.control import lock
from aerona.engine.primitives.queries import living_entity

HOLDERS = frozenset({*COMMUNITY_TYPES, EntityType.MORTAL, EntityType.CULT, EntityType.FACTION})


async def theory_of(ctx: TickContext, theory_id: int) -> TheoryProfileRow:
    row = await ctx.session.get(TheoryProfileRow, theory_id)
    if row is None:
        raise NotFoundError("No such theory.")
    return row


async def holder_of(ctx: TickContext, holder_id: int) -> EntityRow:
    entity = await living_entity(ctx.session, holder_id)
    if entity is None or entity.entity_type not in HOLDERS:
        raise NotFoundError("No such living community or mortal.")
    return entity


def percent(value: int, label: str) -> int:
    if not 0 <= value <= PERCENT:
        raise ValidationFailedError(f"{label} runs from 0 to {PERCENT}.")
    return value


async def set_adherent(ctx: TickContext, theory_id: int, holder_id: int, *, strength: int, orthodox: bool, present: bool) -> TheoryAdherentRow | None:
    profile = await theory_of(ctx, theory_id)
    holder = await holder_of(ctx, holder_id)
    row = await ctx.session.get(TheoryAdherentRow, (theory_id, holder.id))
    if not present:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if row is None:
        row = TheoryAdherentRow(theory_entity_id=theory_id, adherent_entity_id=holder.id, strength=0, orthodox=False, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    if orthodox and not row.orthodox:
        current = await ruling(ctx.session, holder.id, profile.domain)
        if current is not None and current.theory_entity_id != theory_id:
            other = await ctx.session.get(TheoryAdherentRow, (current.theory_entity_id, holder.id))
            if other is not None:
                other.orthodox = False
    row.strength, row.orthodox = percent(strength, "Strength"), orthodox
    row.locked = lock(lock(row.locked, "strength"), "orthodox")
    await ctx.session.flush()
    return row


async def add_anomaly(ctx: TickContext, theory_id: int, kind: AnomalyKind, weight: int, witness_id: int | None) -> TheoryAnomalyRow:
    await theory_of(ctx, theory_id)
    if weight < 1:
        raise ValidationFailedError("An anomaly weighs at least 1.")
    row = TheoryAnomalyRow(theory_entity_id=theory_id, kind=kind, weight=weight, witness_entity_id=witness_id, epoch=ctx.epoch)
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def reveal_truth(ctx: TickContext, theory_id: int, community_id: int) -> TheoryProfileRow:
    profile = await theory_of(ctx, theory_id)
    profile.correctness = PERCENT
    profile.locked = lock(profile.locked, "correctness")
    await set_adherent(ctx, theory_id, community_id, strength=PERCENT, orthodox=True, present=True)
    ctx.session.add(TheoryAnomalyRow(theory_entity_id=theory_id, kind=AnomalyKind.DIVINE_SIGN, weight=0, witness_entity_id=community_id, epoch=ctx.epoch))
    await ctx.session.flush()
    return profile


async def set_practitioner(ctx: TickContext, form_id: int, holder_id: int, *, mastery: int, present: bool) -> ArtFormPractitionerRow | None:
    if await ctx.session.get(ArtFormProfileRow, form_id) is None:
        raise NotFoundError("No such art form.")
    holder = await holder_of(ctx, holder_id)
    row = await ctx.session.get(ArtFormPractitionerRow, (form_id, holder.id))
    if not present:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if row is None:
        row = ArtFormPractitionerRow(art_form_entity_id=form_id, practitioner_entity_id=holder.id, mastery=0, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    row.mastery = percent(mastery, "Mastery")
    row.locked = lock(row.locked, "mastery")
    await ctx.session.flush()
    return row

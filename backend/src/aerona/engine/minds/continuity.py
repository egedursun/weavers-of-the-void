from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow, PersonalityValueRow, SkillRow, TraitRow
from aerona.db.tables.minds import MindProfileRow, MindStateRow
from aerona.db.tables.titles import TitleProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.made import MadeMindStance
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.minds import MindOrigin, MindSeat, SoulContinuity, StateMedium
from aerona.domain.enums.polity import LawKind
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import shift_points
from aerona.engine.made.doctrine import doctrine_here
from aerona.engine.mind.memories import remember
from aerona.engine.minds.profiles import profile_of
from aerona.engine.minds.souls import soul_law
from aerona.engine.notes import note
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.numbers import clamp_int, clamp_percent, round_half_up
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.services.community_relations import change_relation

RUNNING_SEATS = frozenset(set(MindSeat) - {MindSeat.NONE})


async def law_for(ctx: TickContext, entity: EntityRow, kind: LawKind, key: str) -> str | None:
    found = await law_param(ctx.session, entity.location_id or entity.id, kind, key)
    return str(found) if found is not None else None


async def living(ctx: TickContext, node_id: int) -> EntityRow:
    entity = await ctx.session.get(EntityRow, node_id)
    if entity is None or entity.status is not EntityStatus.CANON:
        raise ValidationFailedError("That mind has no living record to act on.")
    return entity


def running(profile: MindProfileRow) -> bool:
    return profile.seat in RUNNING_SEATS and not profile.dormant


async def generation(ctx: TickContext, node_id: int) -> int:
    depth, current = 0, node_id
    while depth < PERCENT:
        parent = await ctx.session.scalar(select(BondRow.target_node_id).where(BondRow.source_node_id == current, BondRow.kind == BondKind.COPY_OF).limit(1))
        if parent is None:
            return depth
        depth, current = depth + 1, parent
    return depth


async def running_copies(ctx: TickContext, source_id: int) -> int:
    copies = select(BondRow.source_node_id).where(BondRow.target_node_id == source_id, BondRow.kind == BondKind.COPY_OF)
    rows = await ctx.session.scalars(select(MindProfileRow).where(MindProfileRow.node_id.in_(copies)))
    return sum(1 for row in rows if running(row))


async def world_copies(ctx: TickContext, world_id: int | None) -> int:
    copies = select(MindProfileRow).join(EntityRow, EntityRow.id == MindProfileRow.node_id)
    statement = copies.where(MindProfileRow.origin == MindOrigin.COPIED, EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
    return sum(1 for row in await ctx.session.scalars(statement) if running(row))


async def copy_stack(ctx: TickContext, source_id: int, copy_id: int, fidelity: int) -> None:
    keep = fidelity / PERCENT
    rng = ctx.rng(f"mind.copy.{source_id}.{copy_id}")
    for value in await ctx.session.scalars(select(PersonalityValueRow).where(PersonalityValueRow.node_id == source_id)):
        if rng.chance(fidelity):
            ctx.session.add(PersonalityValueRow(node_id=copy_id, axis=value.axis, value=value.value))
    for skill in await ctx.session.scalars(select(SkillRow).where(SkillRow.holder_node_id == source_id)):
        level = round_half_up(skill.level * keep)
        if level > 0:
            ctx.session.add(
                SkillRow(
                    holder_node_id=copy_id,
                    skill=skill.skill,
                    subject_node_id=skill.subject_node_id,
                    level=level,
                    peak=level,
                    xp=0,
                    last_used_epoch=ctx.epoch,
                    source=skill.source,
                )
            )
    for trait in await ctx.session.scalars(select(TraitRow).where(TraitRow.node_id == source_id)):
        if rng.chance(fidelity):
            ctx.session.add(TraitRow(node_id=copy_id, trait=trait.trait, source=trait.source, epoch=ctx.epoch, source_node_id=trait.source_node_id))
    for memory in await ctx.session.scalars(select(MemoryRow).where(MemoryRow.holder_node_id == source_id)):
        if rng.chance(fidelity):
            ctx.session.add(
                MemoryRow(
                    holder_node_id=copy_id,
                    subject_node_id=memory.subject_node_id,
                    kind=memory.kind,
                    magnitude=memory.magnitude,
                    decay_pct=memory.decay_pct,
                    epoch=memory.epoch,
                    note=memory.note,
                    inherited_from_node_id=source_id,
                )
            )
    await ctx.session.flush()


def mirror(source: MindProfileRow, target: MindProfileRow, *, origin: MindOrigin, seat: MindSeat, seat_node_id: int | None, fidelity: int) -> None:
    for key in (
        "will",
        "affect",
        "purpose",
        "capacity",
        "speed_pct",
        "stability",
        "upkeep",
        "upkeep_energy",
        "perfect_recall",
        "made_by_node_id",
        "maker_bond",
    ):
        setattr(target, key, getattr(source, key))
    target.origin, target.seat, target.seat_node_id, target.fidelity_pct, target.dormant = origin, seat, seat_node_id, fidelity, False
    target.copyable, target.restorable, target.mergeable, target.transferable = source.copyable, source.restorable, source.mergeable, source.transferable


async def copy_mind(ctx: TickContext, source_id: int, seat: MindSeat, seat_node_id: int | None, *, forced: bool = False) -> EntityRow:
    source = await living(ctx, source_id)
    profile = await profile_of(ctx.session, ctx.rules, source_id, ctx.epoch)
    if not forced and not profile.copyable:
        raise ValidationFailedError(f"The mind of {source.name} cannot be copied.")
    if not forced and await law_for(ctx, source, LawKind.COPY_LAW, "level") == "banned":
        raise ValidationFailedError("The law here forbids copying a mind.")
    table = ctx.rules.continuity
    fidelity = clamp_percent(profile.fidelity_pct - table.copy_fidelity_loss - table.generation_loss * await generation(ctx, source_id))
    if (
        await running_copies(ctx, source_id) >= ctx.rules.minds.copy_cap_per_mind
        or await world_copies(ctx, source.world_id) >= ctx.rules.minds.copy_cap_per_world
    ):
        raise ValidationFailedError(f"{source.name} or its world already runs as many copies as the rules allow; save its state instead.")
    copy = await create_record(
        ctx,
        RecordSpec(
            entity_type=source.entity_type,
            name=f"{source.name} the copy",
            body=f"A copy of the mind of {source.name}, made in epoch {ctx.epoch}.",
            stats=source.stats,
            power=source.power_level,
            world_id=source.world_id,
            location_id=source.location_id,
            mortal_role=source.mortal_role,
        ),
    )
    target = await profile_of(ctx.session, ctx.rules, copy.id, ctx.epoch)
    mirror(
        profile,
        target,
        origin=MindOrigin.COPIED,
        seat=seat,
        seat_node_id=seat_node_id or copy.id,
        fidelity=fidelity,
    )
    await copy_stack(ctx, source_id, copy.id, fidelity)
    await carry_soul(ctx, profile, target)
    doctrine = await doctrine_here(ctx.session, source)
    if doctrine is not None and doctrine.copy_stance is MadeMindStance.ABOMINATION and "stability" not in target.locked:
        target.stability = clamp_percent(target.stability - ctx.rules.continuity.merge_stress)
    await connect(ctx.session, copy.id, source_id, BondKind.COPY_OF, ctx.epoch, description=f"copied at {fidelity} of 100")
    await note(ctx, f"The mind of {source.name} was copied.", key="mind.copied", ids=[copy.id, source_id])
    return copy


async def carry_soul(ctx: TickContext, source: MindProfileRow, copy: MindProfileRow) -> None:
    rule = (await soul_law(ctx.session, source.node_id)).soul_continuity
    copy.souled = source.souled and rule is SoulContinuity.DIVIDES
    if rule is SoulContinuity.FOLLOWS_THE_RUNNING_MIND and source.souled and source.dormant:
        source.souled, copy.souled = False, True
    if rule is SoulContinuity.NONE:
        source.souled = False
    if rule is SoulContinuity.STAYS_WITH_BODY and source.seat is not MindSeat.BODY:
        source.souled = False


async def save_mind(ctx: TickContext, mind_id: int, holder_id: int | None, owner_id: int | None, medium: StateMedium, *, forced: bool = False) -> MindStateRow:
    entity = await living(ctx, mind_id)
    profile = await profile_of(ctx.session, ctx.rules, mind_id, ctx.epoch)
    if not forced and not profile.restorable:
        raise ValidationFailedError(f"The mind of {entity.name} cannot be saved.")
    payer = await ctx.session.get(EntityRow, owner_id) if owner_id is not None else None
    if payer is not None and not held(payer.id):
        await shift_points(ctx.session, payer, -ctx.rules.continuity.save_cost)
    row = MindStateRow(
        mind_node_id=mind_id,
        taken_epoch=ctx.epoch,
        fidelity_pct=profile.fidelity_pct,
        holder_node_id=holder_id,
        medium_kind=medium,
        sealed=False,
        copies=1,
        owner_node_id=owner_id,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await note(ctx, f"The mind of {entity.name} was saved.", key="mind.saved", ids=[mind_id])
    return row


async def restore_mind(ctx: TickContext, state_id: int, seat: MindSeat, seat_node_id: int | None) -> EntityRow:
    state = await ctx.session.get(MindStateRow, state_id)
    if state is None:
        raise ValidationFailedError("No such saved mind.")
    entity = await ctx.session.get(EntityRow, state.mind_node_id)
    profile = await ctx.session.get(MindProfileRow, state.mind_node_id)
    if entity is None or profile is None:
        raise ValidationFailedError("The mind this state was taken from is gone from the record.")
    if running(profile) and entity.status is EntityStatus.CANON:
        return await copy_mind(ctx, entity.id, seat, seat_node_id, forced=True)
    fidelity = clamp_percent(state.fidelity_pct - ctx.rules.continuity.restore_fidelity_loss)
    profile.dormant, profile.seat, profile.seat_node_id, profile.fidelity_pct = False, seat, seat_node_id or entity.id, fidelity
    if entity.status is not EntityStatus.CANON:
        entity.status, entity.end_epoch = EntityStatus.CANON, None
    span = ctx.epoch - state.taken_epoch
    payer = await ctx.session.get(EntityRow, state.owner_node_id) if state.owner_node_id is not None else None
    if payer is not None and not held(payer.id):
        await shift_points(ctx.session, payer, -ctx.rules.continuity.restore_cost)
    keeper = next((node for node in (state.owner_node_id, state.holder_node_id, profile.made_by_node_id) if node not in {None, entity.id}), None)
    if keeper is not None:
        await connect(ctx.session, entity.id, keeper, BondKind.RESTORED_FROM, ctx.epoch, description=f"restored from a state of epoch {state.taken_epoch}")
    await remember(
        ctx.session,
        ctx.rules,
        holder_id=entity.id,
        subject_id=keeper or entity.id,
        kind=MemoryKind.MEMORY_GAP,
        magnitude=-ctx.rules.minds.gap_memory_weight,
        epoch=ctx.epoch,
        note=f"nothing from epoch {state.taken_epoch} to epoch {ctx.epoch}" if span else "a moment lost",
    )
    await note(ctx, f"{entity.name} was restored from what was saved in epoch {state.taken_epoch}.", key="mind.restored", ids=[entity.id])
    return entity


async def transfer_mind(ctx: TickContext, mind_id: int, seat: MindSeat, seat_node_id: int | None, *, forced: bool = False) -> MindProfileRow:
    entity = await living(ctx, mind_id)
    profile = await profile_of(ctx.session, ctx.rules, mind_id, ctx.epoch)
    if not forced and not profile.transferable:
        raise ValidationFailedError(f"The mind of {entity.name} cannot be moved.")
    former = profile.seat_node_id
    profile.seat, profile.seat_node_id = seat, seat_node_id
    profile.fidelity_pct = clamp_percent(profile.fidelity_pct - ctx.rules.continuity.transfer_fidelity_loss)
    if former is not None and former not in {mind_id, seat_node_id}:
        await connect(ctx.session, mind_id, former, BondKind.TRANSFERRED_FROM, ctx.epoch, description="left this seat")
    await ctx.session.flush()
    await note(ctx, f"The mind of {entity.name} moved to another seat.", key="mind.transferred", ids=[mind_id])
    return profile


async def merge_minds(ctx: TickContext, first_id: int, second_id: int, *, forced: bool = False) -> MindProfileRow:
    first, second = await living(ctx, first_id), await living(ctx, second_id)
    keep = await profile_of(ctx.session, ctx.rules, first_id, ctx.epoch)
    lose = await profile_of(ctx.session, ctx.rules, second_id, ctx.epoch)
    if first_id == second_id or (not forced and not (keep.mergeable and lose.mergeable)):
        raise ValidationFailedError("Those two minds cannot be merged.")
    weight = keep.capacity / max(1, keep.capacity + lose.capacity)
    theirs = {row.axis: row for row in await ctx.session.scalars(select(PersonalityValueRow).where(PersonalityValueRow.node_id == second_id))}
    for row in await ctx.session.scalars(select(PersonalityValueRow).where(PersonalityValueRow.node_id == first_id)):
        if row.axis in theirs:
            row.value = round_half_up(row.value * weight + theirs[row.axis].value * (1 - weight))
    mine = {(row.skill, row.subject_node_id): row for row in await ctx.session.scalars(select(SkillRow).where(SkillRow.holder_node_id == first_id))}
    for skill in await ctx.session.scalars(select(SkillRow).where(SkillRow.holder_node_id == second_id)):
        kept = mine.get((skill.skill, skill.subject_node_id))
        if kept is not None:
            kept.level, kept.peak = max(kept.level, skill.level), max(kept.peak, skill.peak)
    for memory in await ctx.session.scalars(select(MemoryRow).where(MemoryRow.holder_node_id == second_id)):
        memory.holder_node_id = first_id
    keep.capacity = clamp_percent(max(keep.capacity, lose.capacity))
    keep.stability = clamp_percent(keep.stability - ctx.rules.continuity.merge_stress)
    keep.origin = MindOrigin.MERGED
    await connect(ctx.session, second_id, first_id, BondKind.MERGED_INTO, ctx.epoch, description="joined into one mind")
    await retire_in(ctx, second, f"merged into the mind of {first.name}")
    await note(ctx, f"The minds of {second.name} and {first.name} became one.", key="mind.merged", ids=[first_id, second_id])
    return keep


async def divide_mind(ctx: TickContext, mind_id: int, seat: MindSeat, seat_node_id: int | None) -> EntityRow:
    entity = await living(ctx, mind_id)
    profile = await profile_of(ctx.session, ctx.rules, mind_id, ctx.epoch)
    share = ctx.rules.continuity.divide_share_pct
    part = await create_record(
        ctx,
        RecordSpec(
            entity_type=entity.entity_type,
            name=f"{entity.name} the divided",
            body=f"A part of the mind of {entity.name}, divided from it in epoch {ctx.epoch}.",
            stats=entity.stats,
            power=entity.power_level,
            world_id=entity.world_id,
            location_id=entity.location_id,
            mortal_role=entity.mortal_role,
        ),
    )
    split = await profile_of(ctx.session, ctx.rules, part.id, ctx.epoch)
    mirror(profile, split, origin=MindOrigin.DIVIDED, seat=seat, seat_node_id=seat_node_id or part.id, fidelity=profile.fidelity_pct)
    split.capacity = clamp_percent(profile.capacity * share // PERCENT)
    profile.capacity = clamp_percent(profile.capacity - split.capacity)
    await copy_stack(ctx, mind_id, part.id, profile.fidelity_pct)
    await connect(ctx.session, part.id, mind_id, BondKind.DIVIDED_FROM, ctx.epoch, description="divided from this mind")
    await note(ctx, f"The mind of {entity.name} divided in two.", key="mind.divided", ids=[mind_id, part.id])
    return part


async def contest(ctx: TickContext, copy: EntityRow, source: EntityRow) -> bool:
    rule = await law_for(ctx, source, LawKind.COPY_SUCCESSION, "rule") or "first_only"
    if rule == "none":
        return False
    copy_mind_row = await ctx.session.get(MindProfileRow, copy.id)
    source_mind = await ctx.session.get(MindProfileRow, source.id)
    if copy_mind_row is None or source_mind is None:
        return False
    winner = source
    if (rule == "by_fidelity" and copy_mind_row.fidelity_pct > source_mind.fidelity_pct) or (
        rule == "by_court" and ctx.rng(f"mind.court.{copy.id}.{ctx.epoch}").chance(PERCENT // 2)
    ):
        winner = copy
    loser = copy if winner is source else source
    if rule != "all_equal":
        for title in await ctx.session.scalars(select(TitleProfileRow).where(TitleProfileRow.holder_node_id == loser.id)):
            if "holder_node_id" not in title.locked and not held(title.title_entity_id):
                title.holder_node_id = winner.id
    await change_relation(ctx, copy.id, source.id, -clamp_int(ctx.rules.continuity.dispute_chance, 1, PERCENT), MemoryKind.BETRAYED_ME)
    await note(ctx, f"{copy.name} and {source.name} contested what one mind once held.", key="mind.disputed", ids=[copy.id, source.id])
    return True


async def keep_disputes(ctx: TickContext) -> int:
    disputes = 0
    bonds = await ctx.session.scalars(select(BondRow).where(BondRow.kind == BondKind.COPY_OF, BondRow.state == BondState.ACTIVE).order_by(BondRow.id))
    for bond in list(bonds):
        copy, source = await ctx.session.get(EntityRow, bond.source_node_id), await ctx.session.get(EntityRow, bond.target_node_id)
        if copy is None or source is None or copy.status is not EntityStatus.CANON or source.status is not EntityStatus.CANON or held(copy.id, source.id):
            continue
        if ctx.rng(f"mind.dispute.{bond.id}.{ctx.epoch}").chance(ctx.rules.continuity.dispute_chance):
            disputes += int(await contest(ctx, copy, source))
    return disputes

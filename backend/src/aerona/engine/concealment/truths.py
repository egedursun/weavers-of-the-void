from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.concealment import BreachRow, HiddenTruthRow, PublicKnowledgeRow, TruthKeeperRow, TruthSeekerRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.made import InformationTrustRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.powers import GiftedAttitudeRow
from aerona.db.write_guard import held
from aerona.domain.enums.concealment import BreachCause, ConcealScope, HiddenTruthKind, KeeperResponse, KeeperRole, SeekerAim, TruthAttitude
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.powers import GiftedAttitude
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.book import values_for
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_percent, round_half_up

LEAN = 25
ATTITUDE_BY_FEAR = {True: TruthAttitude.FEARED, False: TruthAttitude.ACCEPTED}


async def population_for(ctx: TickContext, truth: HiddenTruthRow, place_id: int | None) -> int | None:
    if truth.hidden_from in {ConcealScope.A_PEOPLE, ConcealScope.A_POLITY, ConcealScope.A_WORLD} and truth.scope_node_id is not None:
        return truth.scope_node_id
    place = await ctx.session.get(EntityRow, place_id) if place_id is not None else None
    if place is not None and place.entity_type is EntityType.SETTLEMENT:
        return place.id
    return truth.scope_node_id


async def knowledge(ctx: TickContext, truth_id: int, population_id: int) -> PublicKnowledgeRow:
    row = await ctx.session.scalar(
        select(PublicKnowledgeRow).where(PublicKnowledgeRow.truth_id == truth_id, PublicKnowledgeRow.population_node_id == population_id)
    )
    if row is None:
        row = PublicKnowledgeRow(truth_id=truth_id, population_node_id=population_id, know_pct=0, believe_pct=0, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def trust_in(ctx: TickContext, population_id: int) -> int:
    trust = await ctx.session.get(InformationTrustRow, population_id)
    return trust.information_trust if trust is not None else PERCENT // 2


async def answer(ctx: TickContext, truth: HiddenTruthRow, row: PublicKnowledgeRow) -> KeeperResponse:
    table = ctx.rules.concealment
    keepers = list(await ctx.session.scalars(select(TruthKeeperRow).where(TruthKeeperRow.truth_id == truth.id)))
    payer = None
    for keeper in keepers:
        found = await ctx.session.get(EntityRow, keeper.keeper_node_id)
        if found is not None and found.status is EntityStatus.CANON and not held(found.id):
            payer = found
            break
    if payer is None or await points_of(ctx.session, payer) < table.keeper_cost:
        return KeeperResponse.NONE
    await shift_points(ctx.session, payer, -table.keeper_cost)
    if truth.by_memory_removal:
        row.know_pct = clamp_percent(row.know_pct - row.know_pct * table.memory_cut_pct // PERCENT)
        return KeeperResponse.MEMORY_REMOVAL
    if truth.by_cover_story:
        row.believe_pct = clamp_percent(row.believe_pct - row.believe_pct * table.cover_cut_pct // PERCENT)
        return KeeperResponse.COVER_STORY
    if truth.by_discrediting:
        row.believe_pct = clamp_percent(row.believe_pct - row.believe_pct * table.discredit_cut_pct // PERCENT)
        return KeeperResponse.DISCREDITING
    if truth.by_silencing:
        row.know_pct = clamp_percent(row.know_pct - row.know_pct * table.memory_cut_pct // PERCENT // 2)
        return KeeperResponse.SILENCING
    return KeeperResponse.LAW if truth.by_law else KeeperResponse.NONE


async def breach(
    ctx: TickContext, truth: HiddenTruthRow, cause: BreachCause, *, place_id: int | None = None, witnesses: list[int] | None = None
) -> BreachRow | None:
    if held(truth.subject_node_id) or truth.revealed:
        return None
    table = ctx.rules.concealment
    population = await population_for(ctx, truth, place_id)
    seen = witnesses or []
    spread = clamp_percent(table.spread_pct * (PERCENT - truth.strength // 2) // PERCENT + len(seen))
    response = KeeperResponse.NONE
    if population is not None and not held(population):
        row = await knowledge(ctx, truth.id, population)
        trust = await trust_in(ctx, population)
        if "know_pct" not in row.locked:
            row.know_pct = clamp_percent(row.know_pct + spread)
        if "believe_pct" not in row.locked:
            row.believe_pct = clamp_percent(row.believe_pct + round_half_up(spread * trust / PERCENT * table.belief_pct / PERCENT))
        if row.attitude is TruthAttitude.UNKNOWN and "attitude" not in row.locked:
            row.attitude = TruthAttitude.RUMOURED
        row.updated_epoch = ctx.epoch
        response = await answer(ctx, truth, row)
        await harm_knowers(ctx, truth, seen)
    record = BreachRow(
        truth_id=truth.id,
        epoch=ctx.epoch,
        cause=cause,
        witnesses=len(seen),
        witness_node_ids=seen,
        place_node_id=place_id,
        spread=spread,
        response=response,
    )
    ctx.session.add(record)
    await ctx.session.flush()
    await note(ctx, f"Something hidden showed itself: {truth.title}.", key="truth.breached", ids=[truth.subject_node_id, *seen])
    return record


async def harm_knowers(ctx: TickContext, truth: HiddenTruthRow, knowers: list[int]) -> None:
    if not truth.sanity_cost:
        return
    for knower in knowers:
        profile = await ctx.session.get(MortalProfileRow, knower)
        if profile is not None and not held(knower) and "stress" not in (profile.locked or []):
            profile.stress = clamp_percent(profile.stress + ctx.rules.concealment.sanity_harm * truth.sanity_cost // PERCENT)


async def truths_about(ctx: TickContext, subject_id: int) -> list[HiddenTruthRow]:
    return list(await ctx.session.scalars(select(HiddenTruthRow).where(HiddenTruthRow.subject_node_id == subject_id, HiddenTruthRow.revealed.is_(False))))


async def overt_breach(ctx: TickContext, user: EntityRow, overt: bool, witnesses: list[int]) -> int:
    table = ctx.rules.concealment
    chance = table.overt_breach if overt else table.subtle_breach
    made = 0
    for truth in await truths_about(ctx, user.id):
        if ctx.rng(f"truth.use.{truth.id}.{user.id}.{ctx.epoch}").chance(chance * (PERCENT - truth.strength // 2) // PERCENT):
            made += int(await breach(ctx, truth, BreachCause.OVERT_USE, place_id=user.location_id, witnesses=witnesses) is not None)
    return made


async def seek(ctx: TickContext, seeker: TruthSeekerRow, truth: HiddenTruthRow) -> None:
    table = ctx.rules.concealment
    if "progress" not in seeker.locked:
        seeker.progress = clamp_percent(seeker.progress + table.seeker_gain)
    chance = seeker.progress * table.seeker_breach_pct // PERCENT * (PERCENT - truth.strength) // PERCENT
    if ctx.rng(f"truth.seek.{seeker.id}.{ctx.epoch}").chance(chance):
        found = await ctx.session.get(EntityRow, seeker.seeker_node_id)
        await breach(ctx, truth, BreachCause.INVESTIGATOR, place_id=found.location_id if found is not None else None, witnesses=[seeker.seeker_node_id])
        if seeker.aim is SeekerAim.JOIN_THE_HIDDEN:
            exists = await ctx.session.scalar(
                select(TruthKeeperRow.id).where(TruthKeeperRow.truth_id == truth.id, TruthKeeperRow.keeper_node_id == seeker.seeker_node_id)
            )
            if exists is None:
                ctx.session.add(TruthKeeperRow(truth_id=truth.id, keeper_node_id=seeker.seeker_node_id, role=KeeperRole.MEMBER, locked=[]))
        seeker.progress = 0


async def tend(ctx: TickContext, truth: HiddenTruthRow) -> None:
    table = ctx.rules.concealment
    keepers = await ctx.session.scalar(select(TruthKeeperRow.id).where(TruthKeeperRow.truth_id == truth.id).limit(1))
    if "strength" in truth.locked:
        return
    if keepers is not None:
        truth.strength = clamp_percent(truth.strength + table.tend_gain)
        truth.tended_epoch = ctx.epoch
    elif not truth.by_nature and not truth.by_isolation:
        truth.strength = clamp_percent(truth.strength - table.strength_decay)


async def attitude_on_reveal(ctx: TickContext, population_id: int) -> TruthAttitude:
    values = dict(await values_for(ctx.session, population_id))
    fear = values.get(ValueAxis.TRADITION, 0) + values.get(ValueAxis.PURITY, 0) >= LEAN
    if values.get(ValueAxis.PIETY, 0) >= LEAN * 2:
        return TruthAttitude.REVERED
    if values.get(ValueAxis.WEALTH, 0) >= LEAN * 2:
        return TruthAttitude.EXPLOITED
    return ATTITUDE_BY_FEAR[fear]


async def reveal_or_fade(ctx: TickContext, truth: HiddenTruthRow, row: PublicKnowledgeRow) -> None:
    table = ctx.rules.concealment
    if row.revealed_epoch is None and row.know_pct >= table.reveal_know and row.believe_pct >= table.reveal_believe:
        row.revealed_epoch = ctx.epoch
        if "attitude" not in row.locked:
            row.attitude = await attitude_on_reveal(ctx, row.population_node_id)
        await note(ctx, f"What was hidden became known: {truth.title}.", key="truth.revealed", ids=[truth.subject_node_id, row.population_node_id])
        if truth.hidden_from is not ConcealScope.EVERYONE and "revealed" not in truth.locked:
            truth.revealed = True
        return
    recent = await ctx.session.scalar(select(BreachRow.id).where(BreachRow.truth_id == truth.id, BreachRow.epoch >= ctx.epoch - table.legend_after).limit(1))
    if recent is None and "know_pct" not in row.locked:
        row.know_pct = clamp_percent(row.know_pct - table.fade_pct)
        row.believe_pct = min(row.believe_pct, row.know_pct)
        if row.know_pct == 0 and "attitude" not in row.locked:
            row.attitude = TruthAttitude.UNKNOWN
            row.revealed_epoch = None
    row.updated_epoch = ctx.epoch


async def presence_breaches(ctx: TickContext, truth: HiddenTruthRow) -> None:
    if truth.kind is not HiddenTruthKind.PRESENCE or not truth.by_passing:
        return
    if ctx.rng(f"truth.presence.{truth.id}.{ctx.epoch}").chance(ctx.rules.concealment.witness_breach * (PERCENT - truth.strength) // PERCENT):
        subject = await ctx.session.get(EntityRow, truth.subject_node_id)
        await breach(ctx, truth, BreachCause.WITNESS, place_id=subject.location_id if subject is not None else None)


async def keep_hidden_folk(ctx: TickContext, attitudes: dict[int, GiftedAttitude]) -> int:
    hid = 0
    for people_id, attitude in sorted(attitudes.items()):
        if attitude is not GiftedAttitude.PERSECUTED or held(people_id):
            continue
        if await truths_about(ctx, people_id) or not ctx.rng(f"truth.hide.{people_id}.{ctx.epoch}").chance(ctx.rules.concealment.hide_chance):
            continue
        people = await ctx.session.get(EntityRow, people_id)
        if people is None:
            continue
        truth = HiddenTruthRow(
            title=f"those with powers among {people.name}",
            description="",
            subject_node_id=people_id,
            kind=HiddenTruthKind.PRESENCE,
            hidden_from=ConcealScope.THE_UNINITIATED,
            scope_node_id=None,
            strength=PERCENT // 2,
            by_passing=True,
            by_oath=True,
            founded_epoch=ctx.epoch,
            tended_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(truth)
        await ctx.session.flush()
        ctx.session.add(TruthKeeperRow(truth_id=truth.id, keeper_node_id=people_id, role=KeeperRole.MEMBER, locked=[]))
        await note(ctx, f"The gifted among {people.name} went into hiding.", key="truth.hidden", ids=[people_id])
        hid += 1
    return hid


@reads(
    "table.breaches",
    "table.entities",
    "table.gifted_attitudes",
    "table.hidden_truths",
    "table.information_trust",
    "table.mortal_profiles",
    "table.personality_values",
    "table.public_knowledge",
    "table.truth_keepers",
    "table.truth_seekers",
)
@writes(
    "table.breaches", "table.entities", "table.hidden_truths", "table.mortal_profiles", "table.public_knowledge", "table.truth_keepers", "table.truth_seekers"
)
async def keep_concealment(ctx: TickContext) -> None:
    for truth in list(await ctx.session.scalars(select(HiddenTruthRow).order_by(HiddenTruthRow.id))):
        if held(truth.subject_node_id):
            continue
        await tend(ctx, truth)
        await presence_breaches(ctx, truth)
        for seeker in list(await ctx.session.scalars(select(TruthSeekerRow).where(TruthSeekerRow.truth_id == truth.id).order_by(TruthSeekerRow.id))):
            if not held(seeker.seeker_node_id):
                await seek(ctx, seeker, truth)
        for row in list(await ctx.session.scalars(select(PublicKnowledgeRow).where(PublicKnowledgeRow.truth_id == truth.id).order_by(PublicKnowledgeRow.id))):
            if not held(row.population_node_id):
                await reveal_or_fade(ctx, truth, row)
        ctx.count("hidden_truths_kept")
    attitudes = {row.people_entity_id: row.attitude for row in await ctx.session.scalars(select(GiftedAttitudeRow))}
    ctx.count("folk_gone_into_hiding", await keep_hidden_folk(ctx, attitudes))
    await ctx.session.flush()

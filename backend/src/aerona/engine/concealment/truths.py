from sqlalchemy import select

from aerona.catalog.life.concealment import JOINING_AIMS, POPULATION_FOR_CONCEAL_SCOPES, RELOCATING_TRUTHS, REVEALED_ATTITUDES
from aerona.catalog.life_traits import BREACH_CAUSE_TRAITS, HIDDEN_TRUTH_KIND_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.record_context import Term
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.concealment import BreachRow, HiddenTruthRow, PublicKnowledgeRow, TruthKeeperRow, TruthSeekerRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.industry import CommunityIndustryRow
from aerona.db.tables.made import InformationTrustRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import TreatyProfileRow
from aerona.db.tables.powers import GiftedAttitudeRow
from aerona.db.tables.sites import ExcavationRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.collective import CollectiveActKind, CollectiveTrigger
from aerona.domain.enums.concealment import BreachCause, ConcealScope, HiddenTruthKind, KeeperResponse, KeeperRole, SeekerAim, TruthAttitude
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.life_traits import BreachCauseTrait, HiddenTruthKindTrait
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import TreatyBreach, TreatyStatus
from aerona.domain.enums.powers import GiftedAttitude
from aerona.domain.enums.site import ExcavationStatus
from aerona.domain.enums.society import NaturalLaw
from aerona.engine.body.customs import people_of
from aerona.engine.collective.crowds import begin_movement
from aerona.engine.concealment.kinds import after_seeking, answer_weight, by_accident, denied, keepers_by_role, leaked, spread_of, strain_of
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.book import values_for
from aerona.engine.mortal.standing import add_renown
from aerona.engine.polity.treaties import breach as treaty_breach
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.primitives.numbers import clamp_percent, round_half_up
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import record as record_incident
from aerona.engine.recording.terms import explaining, term

LEAN = 25
ACCORD_BREAKING = having(BREACH_CAUSE_TRAITS, BreachCauseTrait.ACCORD_BREAKING)
GIFTED_TRUTHS = having(HIDDEN_TRUTH_KIND_TRAITS, HiddenTruthKindTrait.GIFTED_TRUTHS)
ATTITUDE_BY_FEAR = {True: TruthAttitude.FEARED, False: TruthAttitude.ACCEPTED}


async def population_for(ctx: TickContext, truth: HiddenTruthRow, place_id: int | None) -> int | None:
    if truth.hidden_from in POPULATION_FOR_CONCEAL_SCOPES and truth.scope_node_id is not None:
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


async def answer(ctx: TickContext, truth: HiddenTruthRow, row: PublicKnowledgeRow, seen: list[int]) -> KeeperResponse:
    table = ctx.rules.concealment
    keepers = await keepers_by_role(ctx, truth.id)
    weight = await answer_weight(ctx, truth.id)
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
        row.know_pct = clamp_percent(row.know_pct - row.know_pct * table.memory_cut_pct * weight // PERCENT // PERCENT)
        return KeeperResponse.MEMORY_REMOVAL
    if truth.by_cover_story:
        row.believe_pct = clamp_percent(row.believe_pct - row.believe_pct * table.cover_cut_pct * weight // PERCENT // PERCENT)
        return KeeperResponse.COVER_STORY
    if truth.by_discrediting:
        row.believe_pct = clamp_percent(row.believe_pct - row.believe_pct * table.discredit_cut_pct // PERCENT)
        return KeeperResponse.DISCREDITING
    if truth.by_silencing:
        row.know_pct = clamp_percent(row.know_pct - row.know_pct * table.memory_cut_pct // PERCENT // 2)
        return KeeperResponse.SILENCING
    dealt = await deal(ctx, truth, row, seen, payer=payer, roles={keeper.role for keeper in keepers})
    return dealt or (KeeperResponse.LAW if truth.by_law else KeeperResponse.NONE)


async def deal(
    ctx: TickContext, truth: HiddenTruthRow, row: PublicKnowledgeRow, seen: list[int], *, payer: EntityRow, roles: set[KeeperRole]
) -> KeeperResponse | None:
    if KeeperRole.GO_BETWEEN in roles and seen:
        await strike_bargain(ctx, truth, row, seen)
        return KeeperResponse.BARGAIN
    if truth.kind in RELOCATING_TRUTHS and row.know_pct >= ctx.rules.concealment.relocate_at and await relocate(ctx, truth, payer, row):
        return KeeperResponse.RELOCATION
    return None


async def strike_bargain(ctx: TickContext, truth: HiddenTruthRow, row: PublicKnowledgeRow, seen: list[int]) -> None:
    kept = set(await ctx.session.scalars(select(TruthKeeperRow.keeper_node_id).where(TruthKeeperRow.truth_id == truth.id)))
    for finder in sorted(set(seen) - kept):
        if not held(finder):
            ctx.session.add(TruthKeeperRow(truth_id=truth.id, keeper_node_id=finder, role=KeeperRole.MEMBER, locked=[]))
    if "know_pct" not in row.locked:
        row.know_pct = clamp_percent(row.know_pct - row.know_pct * ctx.rules.concealment.bargain_cut_pct // PERCENT)


async def relocate(ctx: TickContext, truth: HiddenTruthRow, payer: EntityRow, row: PublicKnowledgeRow) -> bool:
    subject = await ctx.session.get(EntityRow, truth.subject_node_id)
    if subject is None or held(subject.id) or subject.world_id is None:
        return False
    if await points_of(ctx.session, payer) < ctx.rules.concealment.relocate_cost:
        return False
    refuges = [
        region
        for region in await ctx.session.scalars(
            select(EntityRow.id)
            .where(EntityRow.world_id == subject.world_id, EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON)
            .order_by(EntityRow.id)
        )
        if region != subject.location_id and not held(region)
    ]
    if not refuges:
        return False
    await shift_points(ctx.session, payer, -ctx.rules.concealment.relocate_cost)
    subject.location_id = ctx.rng(f"truth.relocate.{truth.id}.{ctx.epoch}").pick(refuges)
    if "know_pct" not in row.locked:
        row.know_pct = 0
        row.believe_pct = 0
    await record_incident(
        ctx, "truth.relocated", roles={IncidentRole.SUBJECT: subject.id, IncidentRole.DESTINATION: subject.location_id}, facts={"truth": truth.title}
    )
    return True


async def breach(
    ctx: TickContext, truth: HiddenTruthRow, cause: BreachCause, *, place_id: int | None = None, witnesses: list[int] | None = None
) -> BreachRow | None:
    if held(truth.subject_node_id) or truth.revealed:
        return None
    table = ctx.rules.concealment
    population = await population_for(ctx, truth, place_id)
    seen = witnesses or []
    spread = clamp_percent(spread_of(truth, table.spread_pct * (PERCENT - truth.strength // 2) // PERCENT) + len(seen))
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
        response = await answer(ctx, truth, row, seen)
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
    await record_incident(
        ctx,
        "truth.breached",
        roles={IncidentRole.SUBJECT: truth.subject_node_id, IncidentRole.WITNESS: list(seen)},
        facts={"truth": truth.title, "truth_kind": truth.kind, "cause": cause, "spread": spread},
        place=place_id,
    )
    await break_accord(ctx, truth, cause)
    return record


async def break_accord(ctx: TickContext, truth: HiddenTruthRow, cause: BreachCause) -> None:
    if truth.accord_entity_id is None or cause not in ACCORD_BREAKING:
        return
    accord = await ctx.session.get(TreatyProfileRow, truth.accord_entity_id)
    if accord is None or accord.status is not TreatyStatus.IN_FORCE or held(accord.treaty_entity_id):
        return
    await treaty_breach(ctx, accord, truth.subject_node_id, clause=None, reason=TreatyBreach.HIDDEN_SHOWN)


async def harm_knowers(ctx: TickContext, truth: HiddenTruthRow, knowers: list[int]) -> None:
    if not truth.sanity_cost:
        return
    for knower in knowers:
        profile = await ctx.session.get(MortalProfileRow, knower)
        if profile is not None and not held(knower) and "stress" not in (profile.locked or []):
            profile.stress = clamp_percent(profile.stress + ctx.rules.concealment.sanity_harm * strain_of(truth) // PERCENT)


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
    archived = await ctx.session.scalar(
        select(TruthKeeperRow.id).where(TruthKeeperRow.truth_id == truth.id, TruthKeeperRow.role == KeeperRole.ARCHIVIST).limit(1)
    )
    if archived is not None and "progress" not in seeker.locked:
        seeker.progress = clamp_percent(seeker.progress + table.seeker_gain * table.archivist_seek_pct // PERCENT)
    chance = seeker.progress * table.seeker_breach_pct // PERCENT * (PERCENT - truth.strength) // PERCENT
    if ctx.rng(f"truth.seek.{seeker.id}.{ctx.epoch}").chance(chance):
        found = await ctx.session.get(EntityRow, seeker.seeker_node_id)
        if seeker.aim is not SeekerAim.PROTECT:
            cause = BreachCause.RECORD_LEAK if archived is not None else BreachCause.INVESTIGATOR
            await breach(ctx, truth, cause, place_id=found.location_id if found is not None else None, witnesses=[seeker.seeker_node_id])
        await after_seeking(ctx, seeker, truth)
        if seeker.aim in JOINING_AIMS:
            exists = await ctx.session.scalar(
                select(TruthKeeperRow.id).where(TruthKeeperRow.truth_id == truth.id, TruthKeeperRow.keeper_node_id == seeker.seeker_node_id)
            )
            if exists is None:
                role = KeeperRole.GUARDIAN if seeker.aim is SeekerAim.PROTECT else KeeperRole.MEMBER
                ctx.session.add(TruthKeeperRow(truth_id=truth.id, keeper_node_id=seeker.seeker_node_id, role=role, locked=[]))
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


async def attitude_on_reveal(ctx: TickContext, population_id: int, truth: HiddenTruthRow) -> TruthAttitude:
    if truth.accord_entity_id is not None:
        return TruthAttitude.BARGAINED
    place = await ctx.session.get(EntityRow, population_id)
    folk = await people_of(ctx.session, place) if place is not None else None
    values = dict(await values_for(ctx.session, folk.id if folk is not None else population_id))
    fear = values.get(ValueAxis.TRADITION, 0) + values.get(ValueAxis.PURITY, 0) >= LEAN
    trust = await trust_in(ctx, population_id)
    if values.get(ValueAxis.LAW, 0) + values.get(ValueAxis.MERCY, 0) >= LEAN * 2:
        return denied(trust, TruthAttitude.PROTECTED)
    if values.get(ValueAxis.PIETY, 0) >= LEAN * 2:
        return denied(trust, TruthAttitude.REVERED)
    if values.get(ValueAxis.WEALTH, 0) >= LEAN * 2:
        return denied(trust, TruthAttitude.EXPLOITED)
    return denied(trust, ATTITUDE_BY_FEAR[fear])


async def react(ctx: TickContext, truth: HiddenTruthRow, row: PublicKnowledgeRow) -> None:
    place = await ctx.session.get(EntityRow, row.population_node_id)
    if place is None or held(place.id):
        return
    if row.attitude is TruthAttitude.DENIED and "believe_pct" not in row.locked:
        row.believe_pct //= 2
        return
    if row.attitude is TruthAttitude.FEARED and place.entity_type is EntityType.SETTLEMENT:
        await begin_movement(ctx, place, CollectiveActKind.PANIC, CollectiveTrigger.RUMOUR, members=0, share=row.believe_pct)
    if truth.kind is HiddenTruthKind.LINEAGE:
        heir = await ctx.session.get(EntityRow, truth.subject_node_id)
        if heir is not None and heir.entity_type is EntityType.MORTAL and not held(heir.id):
            await add_renown(ctx.session, heir.id, ctx.rules.concealment.lineage_renown, ctx.epoch, rules=ctx.rules)
    if truth.kind not in GIFTED_TRUTHS:
        return
    folk = await people_of(ctx.session, place)
    attitude = await ctx.session.get(GiftedAttitudeRow, folk.id) if folk is not None else None
    settled = REVEALED_ATTITUDES.get(row.attitude)
    if attitude is not None and settled is not None and "attitude" not in attitude.locked:
        attitude.attitude = settled


async def reveal_or_fade(ctx: TickContext, truth: HiddenTruthRow, row: PublicKnowledgeRow) -> None:
    table = ctx.rules.concealment
    if row.revealed_epoch is None and row.know_pct >= table.reveal_know and row.believe_pct >= table.reveal_believe:
        row.revealed_epoch = ctx.epoch
        if "attitude" not in row.locked:
            row.attitude = await attitude_on_reveal(ctx, row.population_node_id, truth)
        await record_incident(
            ctx,
            "truth.revealed",
            roles={IncidentRole.SUBJECT: truth.subject_node_id, IncidentRole.RECEIVER: row.population_node_id},
            facts={"truth": truth.title, "truth_kind": truth.kind, "know": row.know_pct, "believe": row.believe_pct},
            terms=[Term("rules.concealment.reveal_know", table.reveal_know), Term("rules.concealment.reveal_believe", table.reveal_believe)],
        )
        await react(ctx, truth, row)
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


async def passing_trade(ctx: TickContext, truth: HiddenTruthRow) -> int:
    subject = await ctx.session.get(EntityRow, truth.subject_node_id)
    if subject is None:
        return 0
    towns = await towns_of_people(ctx.session, subject.id) if subject.entity_type is EntityType.PEOPLE else [subject.location_id] if subject.location_id else []
    traded = 0
    for town in towns:
        row = await ctx.session.get(CommunityIndustryRow, town)
        if row is None or held(town) or "black_market" in row.locked:
            continue
        row.black_market = clamp_percent(row.black_market + ctx.rules.concealment.black_market_gain)
        traded += 1
    return traded


async def presence_breaches(ctx: TickContext, truth: HiddenTruthRow) -> None:
    if truth.kind is not HiddenTruthKind.PRESENCE or not truth.by_passing:
        return
    ctx.count("hidden_folk_trading_towns", await passing_trade(ctx, truth))
    if ctx.rng(f"truth.presence.{truth.id}.{ctx.epoch}").chance(ctx.rules.concealment.witness_breach * (PERCENT - truth.strength) // PERCENT):
        subject = await ctx.session.get(EntityRow, truth.subject_node_id)
        await breach(ctx, truth, BreachCause.WITNESS, place_id=subject.location_id if subject is not None else None)


async def slipped(ctx: TickContext, truth: HiddenTruthRow) -> BreachCause | None:
    table = ctx.rules.concealment
    rng = ctx.rng(f"truth.slip.{truth.id}.{ctx.epoch}")
    weak = (PERCENT - truth.strength) / PERCENT
    subject = await ctx.session.get(EntityRow, truth.subject_node_id)
    if subject is None:
        return None
    keepers = [*await ctx.session.scalars(select(TruthKeeperRow.keeper_node_id).where(TruthKeeperRow.truth_id == truth.id)), subject.id]
    young = select(BondRow.target_node_id).where(BondRow.kind == BondKind.PARENT_OF, BondRow.source_node_id.in_(keepers))
    child = await ctx.session.scalar(select(EntityRow.id).where(EntityRow.id.in_(young), EntityRow.birth_epoch >= ctx.epoch - 1).limit(1))
    if child is not None and rng.chance(round_half_up(table.children_breach * weak)):
        return BreachCause.CHILDREN
    if (
        subject.world_id is not None
        and (await ctx.laws()).has(NaturalLaw.DREAMS_ARE_REAL, subject.world_id)
        and rng.chance(round_half_up(table.dream_breach * weak))
    ):
        return BreachCause.DREAMS
    region = subject.location_id
    digs = (
        select(ExcavationRow.id)
        .join(EntityRow, EntityRow.id == ExcavationRow.site_entity_id)
        .where(ExcavationRow.status == ExcavationStatus.OPEN, EntityRow.location_id == region)
        .limit(1)
    )
    if region is not None and await ctx.session.scalar(digs) is not None and rng.chance(round_half_up(table.dig_breach * weak)):
        return BreachCause.EXCAVATION
    return None


async def live_with_truth(ctx: TickContext, truth: HiddenTruthRow, row: PublicKnowledgeRow) -> None:
    table = ctx.rules.concealment
    if row.attitude is TruthAttitude.PROTECTED:
        for seeker in await ctx.session.scalars(select(TruthSeekerRow).where(TruthSeekerRow.truth_id == truth.id, TruthSeekerRow.aim != SeekerAim.PROTECT)):
            if "progress" not in seeker.locked and not held(seeker.seeker_node_id):
                seeker.progress = max(0, seeker.progress - table.protected_seek_cut)
    elif row.attitude is TruthAttitude.BARGAINED:
        subject = await ctx.session.get(EntityRow, truth.subject_node_id)
        towns = await towns_of_people(ctx.session, subject.id) if subject is not None and subject.entity_type is EntityType.PEOPLE else []
        for town_id in towns:
            town = await ctx.session.get(EntityRow, town_id)
            if town is not None and not held(town.id):
                with explaining():
                    term("concealment.bargained_trade", table.bargained_trade, source_node_id=row.population_node_id)
                    shift_stat(town, "prosperity", table.bargained_trade, ctx.rules.society.default_stat, high=PERCENT)


async def pass_on(ctx: TickContext, truth: HiddenTruthRow) -> None:
    if truth.hidden_from is ConcealScope.A_HOUSE:
        for keeper in list(await ctx.session.scalars(select(TruthKeeperRow).where(TruthKeeperRow.truth_id == truth.id).order_by(TruthKeeperRow.id))):
            dead = await ctx.session.get(EntityRow, keeper.keeper_node_id)
            if dead is None or dead.status is EntityStatus.CANON or "keeper_node_id" in keeper.locked:
                continue
            heir = await ctx.session.scalar(
                select(EntityRow.id)
                .join(BondRow, BondRow.target_node_id == EntityRow.id)
                .where(BondRow.kind == BondKind.PARENT_OF, BondRow.source_node_id == dead.id, EntityRow.status == EntityStatus.CANON)
                .order_by(EntityRow.birth_epoch, EntityRow.id)
                .limit(1)
            )
            if heir is not None:
                keeper.keeper_node_id = heir
            else:
                await ctx.session.delete(keeper)
    elif truth.hidden_from is ConcealScope.A_FAITH and truth.scope_node_id is not None:
        kept = set(await ctx.session.scalars(select(TruthKeeperRow.keeper_node_id).where(TruthKeeperRow.truth_id == truth.id)))
        adherents = [bond.source_node_id for bond in await active_bonds(ctx.session, [BondKind.ADHERENT_OF], targets=[truth.scope_node_id])]
        fresh = [node for node in sorted(set(adherents) - kept) if not held(node)][: ctx.rules.concealment.faith_initiates]
        for node in fresh:
            ctx.session.add(TruthKeeperRow(truth_id=truth.id, keeper_node_id=node, role=KeeperRole.MEMBER, locked=[]))


async def draw_seekers(ctx: TickContext, truth: HiddenTruthRow) -> None:
    if truth.kind is not HiddenTruthKind.LOCATION or truth.revealed:
        return
    sought = await ctx.session.scalar(select(TruthSeekerRow.id).where(TruthSeekerRow.truth_id == truth.id).limit(1))
    subject = await ctx.session.get(EntityRow, truth.subject_node_id)
    if sought is not None or subject is None or subject.world_id is None:
        return
    if not ctx.rng(f"truth.draw.{truth.id}.{ctx.epoch}").chance(ctx.rules.concealment.location_seek_chance):
        return
    kept = select(TruthKeeperRow.keeper_node_id).where(TruthKeeperRow.truth_id == truth.id)
    seeker = await ctx.session.scalar(
        select(EntityRow.id)
        .where(
            EntityRow.world_id == subject.world_id,
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.id.not_in(kept),
        )
        .order_by(EntityRow.id)
        .limit(1)
    )
    if seeker is not None and not held(seeker):
        ctx.session.add(TruthSeekerRow(truth_id=truth.id, seeker_node_id=seeker, aim=SeekerAim.EXPLOIT, progress=0, began_epoch=ctx.epoch, locked=[]))


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
        await record_incident(ctx, "truth.hidden", roles={IncidentRole.SUBJECT: people_id}, facts={"truth": truth.title})
        hid += 1
    return hid


@reads(
    "table.breaches",
    "table.community_industry",
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
    "table.breaches",
    "table.community_industry",
    "table.entities",
    "table.hidden_truths",
    "table.mortal_profiles",
    "table.public_knowledge",
    "table.truth_keepers",
    "table.truth_seekers",
)
async def keep_concealment(ctx: TickContext) -> None:
    for truth in list(await ctx.session.scalars(select(HiddenTruthRow).order_by(HiddenTruthRow.id))):
        if held(truth.subject_node_id):
            continue
        await tend(ctx, truth)
        await presence_breaches(ctx, truth)
        cause = await leaked(ctx, truth) or await slipped(ctx, truth) or (BreachCause.ACCIDENT if by_accident(ctx, truth) else None)
        if cause is not None:
            await breach(ctx, truth, cause, place_id=None)
        for seeker in list(await ctx.session.scalars(select(TruthSeekerRow).where(TruthSeekerRow.truth_id == truth.id).order_by(TruthSeekerRow.id))):
            if not held(seeker.seeker_node_id):
                await seek(ctx, seeker, truth)
        for row in list(await ctx.session.scalars(select(PublicKnowledgeRow).where(PublicKnowledgeRow.truth_id == truth.id).order_by(PublicKnowledgeRow.id))):
            if not held(row.population_node_id):
                await reveal_or_fade(ctx, truth, row)
                await live_with_truth(ctx, truth, row)
        await pass_on(ctx, truth)
        await draw_seekers(ctx, truth)
        ctx.count("hidden_truths_kept")
    attitudes = {row.people_entity_id: row.attitude for row in await ctx.session.scalars(select(GiftedAttitudeRow))}
    ctx.count("folk_gone_into_hiding", await keep_hidden_folk(ctx, attitudes))
    await ctx.session.flush()

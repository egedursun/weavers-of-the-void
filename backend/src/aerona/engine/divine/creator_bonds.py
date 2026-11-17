from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import select

from aerona.catalog.kinds.motifs import MOTIF_SOURCES
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.creator_bonds import CovenantRow, CreatorChosenRow, CreatorDepictionRow, CreatorStandingRow
from aerona.db.tables.divine import WorldAttentionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.creator import (
    ChosenFavour,
    CovenantDuty,
    CovenantState,
    CreatorHeresy,
    CreatorNature,
    CreatorPromise,
    CreatorSignKind,
    CreatorStance,
)
from aerona.domain.enums.demography import MotifSource
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind, PressureKind, ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.gods.queries import creator_row
from aerona.engine.gods.worship import creator_worshippers
from aerona.engine.lore.motifs import people_motifs
from aerona.engine.mind.book import pressures_of, values_for
from aerona.engine.mind.memories import remember
from aerona.engine.primitives.naming import Namer
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.recording.record import record
from aerona.engine.services.war import ongoing_war_count
from aerona.language.generator import NameKind

Sign = Callable[[TickContext, CreatorRow, EntityRow | None], Awaitable[EntityRow | None]]
SHARES = ("awe", "love", "dread", "gratitude", "resentment", "ignorance")


async def living_peoples(ctx: TickContext) -> list[EntityRow]:
    query = select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON)
    return list(await ctx.session.scalars(query.order_by(EntityRow.id)))


async def mark_memory(ctx: TickContext, holder: int, subject: int, kind: MemoryKind, *, magnitude: int, why: str) -> None:
    await remember(ctx.session, ctx.rules, holder_id=holder, subject_id=subject, kind=kind, magnitude=magnitude, epoch=ctx.epoch, note=why)


async def standing_of(ctx: TickContext, people_id: int) -> CreatorStandingRow:
    row = await ctx.session.get(CreatorStandingRow, people_id)
    if row is None:
        row = CreatorStandingRow(people_entity_id=people_id, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    return row


def move(row: CreatorStandingRow, **shifts: int) -> None:
    for name, amount in shifts.items():
        if name not in row.locked:
            setattr(row, name, clamp_percent(getattr(row, name) + amount))


async def people_for(ctx: TickContext, target: EntityRow | None) -> EntityRow | None:
    if target is None:
        return None
    return target if target.entity_type is EntityType.PEOPLE else await people_of(ctx.session, target)


async def least_aware(ctx: TickContext) -> EntityRow | None:
    peoples = [people for people in await living_peoples(ctx) if not held(people.id)]
    if not peoples:
        return None
    unknowing: dict[int, int] = {}
    for people in peoples:
        standing = await ctx.session.get(CreatorStandingRow, people.id)
        unknowing[people.id] = standing.ignorance if standing is not None else PERCENT
    return max(peoples, key=lambda people: (unknowing[people.id], -people.id))


async def read_sign(ctx: TickContext, creator: CreatorRow, target: EntityRow | None, shifts: dict[str, int], memory: MemoryKind) -> EntityRow | None:
    people = await people_for(ctx, target)
    if target is None or people is None or held(people.id):
        return None
    superstition = (await values_for(ctx.session, people.id)).get(ValueAxis.SUPERSTITION, 0)
    reading = PERCENT + superstition // 2
    move(await standing_of(ctx, people.id), **{name: amount * reading // PERCENT for name, amount in shifts.items()})
    await mark_memory(ctx, people.id, creator.id, memory, magnitude=sum(shifts.values()), why="a sign of the Creator")
    creator.mood_interest = clamp_percent(creator.mood_interest - ctx.rules.creator_bonds.sign_attention)
    return target


async def omen(ctx: TickContext, creator: CreatorRow, target: EntityRow | None) -> EntityRow | None:
    return await read_sign(ctx, creator, target, {"awe": 6, "ignorance": -4}, MemoryKind.DIVINE_WILL)


async def warning(ctx: TickContext, creator: CreatorRow, target: EntityRow | None) -> EntityRow | None:
    return await read_sign(ctx, creator, target, {"dread": 8, "awe": 3}, MemoryKind.DREADS)


async def revelation(ctx: TickContext, creator: CreatorRow, target: EntityRow | None) -> EntityRow | None:
    return await read_sign(ctx, creator, target, {"ignorance": -15, "awe": 8}, MemoryKind.DIVINE_WILL)


async def visitation(ctx: TickContext, creator: CreatorRow, target: EntityRow | None) -> EntityRow | None:
    if target is not None and not held(target.id):
        shift_stat(target, "piety", ctx.rules.creator_bonds.sign_piety, 0)
    return await read_sign(ctx, creator, target, {"love": 8, "awe": 8, "ignorance": -8}, MemoryKind.GOODWILL)


async def mark(ctx: TickContext, creator: CreatorRow, target: EntityRow | None) -> EntityRow | None:
    if target is not None and not held(target.id) and await ctx.session.get(CreatorChosenRow, target.id) is None:
        ctx.session.add(CreatorChosenRow(node_id=target.id, favour=ChosenFavour.GIFT, since_epoch=ctx.epoch, locked=[]))
    return await read_sign(ctx, creator, target, {"awe": 5}, MemoryKind.DIVINE_WILL)


async def wonder(ctx: TickContext, creator: CreatorRow, target: EntityRow | None) -> EntityRow | None:
    if target is not None and not held(target.id):
        shift_stat(target, "prestige", ctx.rules.creator_bonds.sign_piety, 0)
    return await read_sign(ctx, creator, target, {"awe": 10, "gratitude": 4}, MemoryKind.GOODWILL)


async def withdrawal(ctx: TickContext, creator: CreatorRow, target: EntityRow | None) -> EntityRow | None:
    return await read_sign(ctx, creator, target, {"resentment": 8, "love": -6, "ignorance": 6}, MemoryKind.ILL_WILL)


async def test(ctx: TickContext, creator: CreatorRow, target: EntityRow | None) -> EntityRow | None:
    if target is not None and not held(target.id):
        shift_stat(target, "prosperity", -ctx.rules.creator_bonds.sign_piety, 0)
        shift_stat(target, "piety", ctx.rules.creator_bonds.sign_piety, 0)
    return await read_sign(ctx, creator, target, {"dread": 5, "awe": 5}, MemoryKind.DREADS)


async def reward(ctx: TickContext, creator: CreatorRow, target: EntityRow | None) -> EntityRow | None:
    if target is not None and not held(target.id):
        shift_stat(target, "prosperity", ctx.rules.creator_bonds.sign_piety, 0)
    return await read_sign(ctx, creator, target, {"gratitude": 10, "love": 6}, MemoryKind.GOODWILL)


async def covenant_offer(ctx: TickContext, creator: CreatorRow, target: EntityRow | None) -> EntityRow | None:
    people = await people_for(ctx, target)
    if people is not None and not held(people.id):
        await offer(ctx, people.id, CovenantDuty.WORSHIP, CreatorPromise.PROTECTION, None)
    return await read_sign(ctx, creator, target, {"awe": 4, "love": 4}, MemoryKind.DIVINE_WILL)


def aimed(sign: Sign) -> Sign:
    async def send(ctx: TickContext, creator: CreatorRow, target: EntityRow | None) -> EntityRow | None:
        return await sign(ctx, creator, target or await least_aware(ctx))

    return send


WIDER_SIGNS: Mapping[CreatorSignKind, Sign] = {
    CreatorSignKind.OMEN: aimed(omen),
    CreatorSignKind.WARNING: aimed(warning),
    CreatorSignKind.REVELATION: aimed(revelation),
    CreatorSignKind.VISITATION: aimed(visitation),
    CreatorSignKind.MARK: aimed(mark),
    CreatorSignKind.WONDER: aimed(wonder),
    CreatorSignKind.WITHDRAWAL: aimed(withdrawal),
    CreatorSignKind.TEST: aimed(test),
    CreatorSignKind.REWARD: aimed(reward),
    CreatorSignKind.COVENANT_OFFER: aimed(covenant_offer),
}


async def offer(ctx: TickContext, people_id: int, duty: CovenantDuty, promise: CreatorPromise, until: int | None) -> CovenantRow:
    row = CovenantRow(people_entity_id=people_id, duty=duty, promise=promise, seal_sign=CreatorSignKind.COVENANT_OFFER, state=CovenantState.OFFERED)
    row.since_epoch, row.until_epoch, row.breaches, row.locked = ctx.epoch, until, 0, []
    ctx.session.add(row)
    await ctx.session.flush()
    return row


def stance_for(row: CreatorStandingRow) -> CreatorStance:
    if row.heresy is CreatorHeresy.DENIAL:
        return CreatorStance.DENIAL
    shares = {name: getattr(row, name) for name in SHARES}
    top = max(shares, key=lambda name: (shares[name], name))
    return {
        "love": CreatorStance.WORSHIP,
        "gratitude": CreatorStance.WORSHIP,
        "awe": CreatorStance.REVERENCE,
        "dread": CreatorStance.FEAR,
        "resentment": CreatorStance.REJECTION,
        "ignorance": CreatorStance.INDIFFERENCE,
    }[top]


def heresy_for(ctx: TickContext, row: CreatorStandingRow, far: bool, gods: int) -> CreatorHeresy:
    table = ctx.rules.creator_bonds
    if row.resentment >= table.heresy_at:
        return CreatorHeresy.ANTI_GOD
    if row.ignorance >= table.denial_at:
        return CreatorHeresy.DENIAL
    if far and row.ignorance >= table.heresy_at:
        return CreatorHeresy.ABSENT_CREATOR
    if gods > table.many_gods:
        return CreatorHeresy.MANY_CREATORS
    if row.dread >= table.heresy_at and row.love < table.heresy_at // 2:
        return CreatorHeresy.RIVAL_CREATOR
    return CreatorHeresy.NONE


async def world_far(ctx: TickContext, world_id: int | None) -> bool:
    row = await ctx.session.get(WorldAttentionRow, world_id) if world_id is not None else None
    return row is not None and row.attention < ctx.rules.creator.far_eye_below


async def unknowing_people_of(ctx: TickContext, world_id: int) -> EntityRow | None:
    peoples = [people for people in await living_peoples(ctx) if people.world_id == world_id and not held(people.id)]
    if not peoples:
        return None
    unknowing: dict[int, int] = {}
    for people in peoples:
        standing = await ctx.session.get(CreatorStandingRow, people.id)
        unknowing[people.id] = standing.ignorance if standing is not None else PERCENT
    return max(peoples, key=lambda people: (unknowing[people.id], -people.id))


async def bound(ctx: TickContext, people_id: int) -> bool:
    open_states = [CovenantState.OFFERED, CovenantState.SEALED]
    found = await ctx.session.scalar(select(CovenantRow.id).where(CovenantRow.people_entity_id == people_id, CovenantRow.state.in_(open_states)).limit(1))
    return found is not None


async def eye_returns(ctx: TickContext, creator: CreatorRow, world_id: int) -> bool:
    people = await unknowing_people_of(ctx, world_id)
    if people is None:
        return False
    await warning(ctx, creator, people)
    if not await bound(ctx, people.id):
        await covenant_offer(ctx, creator, people)
    return True


async def keep_absence(ctx: TickContext, creator: CreatorRow) -> tuple[int, int]:
    absent = returned = 0
    for row in list(await ctx.session.scalars(select(WorldAttentionRow).order_by(WorldAttentionRow.world_id))):
        if "far_epochs" in row.locked:
            continue
        was_absent = row.far_epochs >= ctx.rules.creator_bonds.absence_epochs
        row.far_epochs = row.far_epochs + 1 if row.attention < ctx.rules.creator.far_eye_below else 0
        absent += row.far_epochs >= ctx.rules.creator_bonds.absence_epochs
        if was_absent and row.far_epochs == 0 and await eye_returns(ctx, creator, row.world_id):
            returned += 1
    return absent, returned


async def keep_standing(ctx: TickContext, creator: CreatorRow) -> int:
    table = ctx.rules.creator_bonds
    worshippers = {row.id for row in await creator_worshippers(ctx.session)}
    peoples = await living_peoples(ctx)
    kept = 0
    for people in peoples:
        if held(people.id):
            continue
        row = await standing_of(ctx, people.id)
        far = await world_far(ctx, people.world_id)
        attention = await ctx.session.get(WorldAttentionRow, people.world_id) if people.world_id is not None else None
        absent = attention is not None and attention.far_epochs >= table.absence_epochs
        if far:
            move(row, ignorance=table.drift, resentment=table.drift if absent else 0, awe=-table.drift)
        else:
            move(row, awe=table.drift, ignorance=-table.drift)
        if people.id in worshippers:
            move(row, love=table.drift)
        if "heresy" not in row.locked:
            gods = len(await active_bonds(ctx.session, [BondKind.WORSHIPS], sources=[people.id]))
            row.heresy = heresy_for(ctx, row, far, gods)
        if row.heresy is not CreatorHeresy.NONE:
            move(row, love=-table.drift)
        if "stance" not in row.locked:
            row.stance = stance_for(row)
        if row.stance is CreatorStance.WORSHIP:
            creator.essence += table.worship_essence
        creator.essence += row.awe * table.awe_essence // PERCENT
        row.updated_epoch = ctx.epoch
        kept += 1
    return kept


async def lower_doom(ctx: TickContext) -> None:
    rows = list(await ctx.session.scalars(select(CreatorStandingRow)))
    if not rows:
        return
    warm = sum(row.love + row.awe for row in rows)
    cold = sum(row.dread + row.resentment for row in rows)
    cosmos = await CosmosRepository(ctx.session).get()
    if cosmos is not None and warm > cold + ctx.rules.creator_bonds.doom_margin * len(rows):
        cosmos.doom_clock = max(0, cosmos.doom_clock - ctx.rules.creator_bonds.doom_relief)


DUTY_PRESSURE: Mapping[CovenantDuty, PressureKind | None] = total(
    CovenantDuty,
    {
        CovenantDuty.WORSHIP: None,
        CovenantDuty.PEACE: None,
        CovenantDuty.OFFERINGS: None,
        CovenantDuty.KEEP_LAW: PressureKind.INSECURITY,
        CovenantDuty.PROTECT_THE_WEAK: PressureKind.POVERTY,
        CovenantDuty.SEEK_KNOWLEDGE: PressureKind.STAGNATION,
    },
)
PROMISE_STATS: Mapping[CreatorPromise, str | None] = total(
    CreatorPromise,
    {
        CreatorPromise.PROTECTION: "defense",
        CreatorPromise.PLENTY: "prosperity",
        CreatorPromise.GUIDANCE: "knowledge",
        CreatorPromise.LONG_LIFE: "fertility",
        CreatorPromise.PRESENCE: None,
    },
)


async def duty_kept(ctx: TickContext, duty: CovenantDuty, people: EntityRow) -> bool:
    table = ctx.rules.creator_bonds
    if duty is CovenantDuty.WORSHIP:
        return people.id in {row.id for row in await creator_worshippers(ctx.session)}
    if duty is CovenantDuty.PEACE:
        return await ongoing_war_count(ctx.session, people.id) == 0
    if duty is CovenantDuty.OFFERINGS:
        return stat_or(people, "piety", 0) >= table.offering_piety
    pressure = DUTY_PRESSURE[duty]
    pressures = await pressures_of(ctx.session, people.id)
    return pressure is None or pressures.get(pressure, 0) < table.duty_pressure


async def keep_promise(ctx: TickContext, promise: CreatorPromise, people: EntityRow) -> None:
    table = ctx.rules.creator_bonds
    given = PROMISE_STATS[promise]
    if given is not None:
        shift_stat(people, given, table.promise_step, 0)
    else:
        attention = await ctx.session.get(WorldAttentionRow, people.world_id) if people.world_id is not None else None
        if attention is not None and "attention" not in attention.locked:
            attention.attention = clamp_percent(attention.attention + table.promise_step)


async def keep_covenants(ctx: TickContext, creator: CreatorRow) -> int:
    table = ctx.rules.creator_bonds
    moved = 0
    for row in list(
        await ctx.session.scalars(select(CovenantRow).where(CovenantRow.state.in_([CovenantState.OFFERED, CovenantState.SEALED])).order_by(CovenantRow.id))
    ):
        people = await ctx.session.get(EntityRow, row.people_entity_id)
        if people is None or held(people.id) or "state" in row.locked:
            continue
        standing = await standing_of(ctx, people.id)
        if row.state is CovenantState.OFFERED:
            if standing.stance in {CreatorStance.WORSHIP, CreatorStance.REVERENCE}:
                row.state = CovenantState.SEALED
                await record(ctx, "creator.covenant_sealed", roles={IncidentRole.SUBJECT: people.id})
            elif ctx.epoch - row.since_epoch >= table.offer_epochs:
                row.state = CovenantState.ENDED
            moved += 1
            continue
        await keep_promise(ctx, row.promise, people)
        if not await duty_kept(ctx, row.duty, people):
            row.breaches += 1
            move(standing, resentment=table.drift)
            await mark_memory(ctx, people.id, creator.id, MemoryKind.BROKE_OATH, magnitude=-table.drift, why="a covenant strained")
        if row.breaches >= table.breach_limit:
            row.state = CovenantState.BROKEN
            creator.mood_anger = clamp_percent(creator.mood_anger + table.drift)
            await record(ctx, "creator.covenant_broken", roles={IncidentRole.SUBJECT: people.id})
        elif row.until_epoch is not None and ctx.epoch >= row.until_epoch:
            row.state = CovenantState.KEPT
            move(standing, love=table.drift * 2, gratitude=table.drift * 2)
            creator.essence += table.kept_essence
        moved += 1
    return moved


async def keep_chosen(ctx: TickContext) -> int:
    table = ctx.rules.creator_bonds
    kept = 0
    for row in list(await ctx.session.scalars(select(CreatorChosenRow).order_by(CreatorChosenRow.node_id))):
        chosen = await ctx.session.get(EntityRow, row.node_id)
        if chosen is None or held(chosen.id) or chosen.status is not EntityStatus.CANON:
            continue
        profile = await ctx.session.get(MortalProfileRow, chosen.id)
        if profile is not None and "renown" not in (profile.locked or []):
            profile.renown = clamp_percent(profile.renown + table.chosen_renown)
        favour = {
            ChosenFavour.RENOWN: ("renown", table.chosen_renown),
            ChosenFavour.PROTECTION: ("defense", table.chosen_renown),
            ChosenFavour.LONG_LIFE: ("hp", table.chosen_renown),
            ChosenFavour.GIFT: ("prosperity", table.chosen_renown),
            ChosenFavour.FORESIGHT: ("wisdom", table.chosen_renown),
        }[row.favour]
        shift_stat(chosen, favour[0], favour[1], 0)
        if chosen.location_id is not None:
            rival = await ctx.session.scalar(
                select(EntityRow.id)
                .where(EntityRow.location_id == chosen.location_id, EntityRow.id != chosen.id, EntityRow.entity_type == chosen.entity_type)
                .limit(1)
            )
            if rival is not None and not held(rival):
                await mark_memory(ctx, rival, chosen.id, MemoryKind.ENVIED, magnitude=-table.chosen_renown, why="the Creator's chosen")
        kept += 1
    return kept


def nature_for(values: Mapping[ValueAxis, int], motifs: list[MotifSource] | None = None, lean: int = 0) -> CreatorNature:
    leans = {
        CreatorNature.JUDGE: values.get(ValueAxis.LAW, 0),
        CreatorNature.SOURCE: values.get(ValueAxis.NATURE, 0),
        CreatorNature.MANY_FACED: values.get(ValueAxis.SUPERSTITION, 0),
        CreatorNature.ABSENT_ONE: -values.get(ValueAxis.PIETY, 0),
        CreatorNature.UNKNOWABLE: values.get(ValueAxis.KNOWLEDGE, 0),
        CreatorNature.MAKER: values.get(ValueAxis.CRAFTSMANSHIP, 0),
    }
    for source in motifs or []:
        nature = MOTIF_SOURCES[source].nature
        if nature is not None:
            leans[nature] += lean
    return max(leans, key=lambda nature: (leans[nature], nature.value))


async def depict(ctx: TickContext) -> int:
    namer = Namer(ctx.session, ctx.rules)
    made = 0
    peoples = await living_peoples(ctx)
    for people in peoples:
        if held(people.id) or await ctx.session.get(CreatorDepictionRow, people.id) is not None:
            continue
        name = await namer.from_speaker(people.id, f"creator.{people.id}", NameKind.PERSON) or people.name
        nature = nature_for(await values_for(ctx.session, people.id), await people_motifs(ctx.session, people.id), ctx.rules.customs.motif_lean)
        ctx.session.add(CreatorDepictionRow(people_entity_id=people.id, name=name, nature=nature, aspect=None, updated_epoch=ctx.epoch, locked=[]))
        made += 1
    return made


async def keep_creator_bonds(ctx: TickContext) -> None:
    creator = await creator_row(ctx.session)
    if creator is None:
        return
    absent, returned = await keep_absence(ctx, creator)
    ctx.count("creator_absent_worlds", absent)
    ctx.count("creator_returned_worlds", returned)
    ctx.count("creator_standing_kept", await keep_standing(ctx, creator))
    ctx.count("creator_covenants_moved", await keep_covenants(ctx, creator))
    ctx.count("creator_chosen_kept", await keep_chosen(ctx))
    ctx.count("creator_depictions_made", await depict(ctx))
    await lower_doom(ctx)
    await ctx.session.flush()

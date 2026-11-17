from sqlalchemy import select

from aerona.catalog.civics import TENET_GATES
from aerona.catalog.lore import IDEOLOGY_APPEAL, IDEOLOGY_VALUES, VALUE_IDEOLOGY
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import IdeologyAdherentRow, IdeologyProfileRow, IdeologyTenetRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultTenetRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held, unheld
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import IdeologyTenet, ItemClass
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.mind import MemoryKind, ValueAxis, ValueHolder
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.war import WarCause
from aerona.domain.models.entity_stats import IdeologyStats, ItemStats
from aerona.engine.context import TickContext
from aerona.engine.faith.book import patron_node
from aerona.engine.lifecycle.states import ended_ids
from aerona.engine.lore.civics import holders_know
from aerona.engine.lore.creed_change import media_factor
from aerona.engine.lore.items import profile_of
from aerona.engine.lore.printing import banned_for, printed, read_in_secret
from aerona.engine.lore.research import institutions
from aerona.engine.mind.book import stored_values, values_for, write_values
from aerona.engine.mind.memories import remember
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.services.war import declare_war

IT = IdeologyTenet
FOUNDER_INTELLECT = 70
SEED_VALUE = 30
ANTI_FAITH = {
    IT.ANTI_GOD: frozenset(TenetKind),
    IT.RATIONALISM: frozenset({TenetKind.SANCTIFIED_MAGIC, TenetKind.REINCARNATION}),
    IT.EGALITARIANISM: frozenset({TenetKind.DIVINE_RULE}),
    IT.DIVINE_RIGHT: frozenset({TenetKind.PACIFISM}),
    IT.MILITARISM: frozenset({TenetKind.PACIFISM}),
    IT.CREATORISM: frozenset({TenetKind.SYNCRETIC_OPENNESS}),
    IT.XENOPHOBIA: frozenset({TenetKind.PROSELYTISM, TenetKind.SYNCRETIC_OPENNESS}),
    IT.COSMOPOLITANISM: frozenset({TenetKind.EXCLUSIVITY}),
}


async def tenets_of(ctx: TickContext, ideology_id: int) -> set[IdeologyTenet]:
    return set(await ctx.session.scalars(select(IdeologyTenetRow.tenet).where(IdeologyTenetRow.ideology_entity_id == ideology_id)))


async def found(ctx: TickContext, founder: EntityRow) -> EntityRow | None:
    values = await values_for(ctx.session, founder.id)
    tenets = [high if values.get(axis, 0) >= SEED_VALUE else low for axis, (high, low) in VALUE_IDEOLOGY.items() if abs(values.get(axis, 0)) >= SEED_VALUE]
    taught = await teachable(ctx, founder, list(dict.fromkeys(tenets)))
    if not taught:
        return None
    return await found_school(ctx, founder, taught[: ctx.rules.ideologies.founding_tenets])


async def teachable(ctx: TickContext, founder: EntityRow, tenets: list[IdeologyTenet]) -> list[IdeologyTenet]:
    homes = [founder.id, *([founder.location_id] if founder.location_id is not None else [])]
    return [tenet for tenet in tenets if await holders_know(ctx.session, homes, TENET_GATES.get(tenet))]


async def found_school(ctx: TickContext, founder: EntityRow, tenets: list[IdeologyTenet], name: str | None = None) -> EntityRow:
    asked = list(dict.fromkeys(tenets))
    tenets = await teachable(ctx, founder, asked)
    if not tenets:
        needs = ", ".join(sorted({TENET_GATES[tenet].value.replace("_", " ") for tenet in asked if tenet in TENET_GATES}))
        raise ValidationFailedError(f"No one around {founder.name} has yet learned what such a creed needs: {needs}.")
    name = (name or "").strip() or f"The {spoken(tenets[0]).title()} of {founder.name}"
    creed = await create_record(
        ctx,
        RecordSpec(
            name=name,
            entity_type=EntityType.IDEOLOGY,
            stats=IdeologyStats(adherents=1, appeal=PERCENT // 4),
            body=f"A creed taught by {founder.name}: {', '.join(tenet.value.replace('_', ' ') for tenet in tenets)}.",
            power=2,
            world_id=founder.world_id,
            location_id=founder.location_id,
        ),
    )
    delta: dict[str, int] = {}
    for tenet in tenets:
        ctx.session.add(IdeologyTenetRow(ideology_entity_id=creed.id, tenet=tenet))
        for axis, value in IDEOLOGY_VALUES[tenet].items():
            delta[axis.value] = delta.get(axis.value, 0) + value
    appeal: dict[str, int] = {}
    for tenet in tenets:
        for social_class, value in IDEOLOGY_APPEAL[tenet].items():
            appeal[social_class.value] = max(appeal.get(social_class.value, 0), value)
    ctx.session.add(
        IdeologyProfileRow(
            ideology_entity_id=creed.id,
            value_delta=delta,
            tenets=[tenet.value for tenet in tenets],
            founder_entity_id=founder.id,
            appeal=appeal,
            texts=[],
            updated_epoch=ctx.epoch,
            locked=[],
        )
    )
    if founder.location_id is not None:
        ctx.session.add(
            IdeologyAdherentRow(ideology_entity_id=creed.id, adherent_entity_id=founder.location_id, strength=PERCENT // 4, state=False, since_epoch=ctx.epoch)
        )
    ctx.session.add(IdeologyAdherentRow(ideology_entity_id=creed.id, adherent_entity_id=founder.id, strength=PERCENT, state=False, since_epoch=ctx.epoch))
    return creed


async def emerge(ctx: TickContext) -> EntityRow | None:
    scholars = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    founders = set(await ctx.session.scalars(select(IdeologyProfileRow.founder_entity_id)))
    for mortal in unheld(scholars):
        if mortal.id in founders or (stat(mortal, "intellect") or 0) < FOUNDER_INTELLECT:
            continue
        if ctx.rng(f"creed.{mortal.id}.{ctx.epoch}").chance(ctx.rules.ideologies.emergence_chance * await media_factor(ctx, mortal)):
            return await found(ctx, mortal)
    return None


def appeal_for(profile: IdeologyProfileRow, society: CommunitySocietyRow | None, discontent_pct: int) -> float:
    if society is None:
        return 0.0
    total = 0.0
    for key, value in profile.appeal.items():
        social_class = SocialClass(key)
        unhappy = (PERCENT - society.satisfaction(social_class)) / PERCENT
        total += society.share(social_class) / PERCENT * value / PERCENT * (1 + unhappy * discontent_pct / PERCENT)
    return total


async def learned_paths(ctx: TickContext, creed: EntityRow, profile: IdeologyProfileRow, adherents: dict[int, IdeologyAdherentRow]) -> list[tuple[int, int]]:
    paths: list[tuple[int, int]] = []
    for book in profile.texts:
        owner = await ctx.session.scalar(
            select(BondRow.source_node_id).where(BondRow.target_node_id == book, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE).limit(1)
        )
        reader = await living_entity(ctx.session, owner)
        home = reader.location_id if reader is not None and reader.entity_type is EntityType.MORTAL else owner
        source = next(iter(adherents), None)
        if home is not None and source is not None:
            paths.append((source, home))
    scholars = select(IdeologyAdherentRow.adherent_entity_id).where(IdeologyAdherentRow.ideology_entity_id == creed.id)
    for mortal in await ctx.session.scalars(
        select(EntityRow).where(EntityRow.id.in_(scholars), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
    ):
        if mortal.location_id is not None and mortal.id in adherents:
            paths.append((mortal.id, mortal.location_id))
    return paths


async def write_text(ctx: TickContext, creed: EntityRow, profile: IdeologyProfileRow) -> EntityRow | None:
    if profile.texts and len(profile.texts) >= ctx.rules.ideologies.texts_max:
        return None
    founder = await living_entity(ctx.session, profile.founder_entity_id)
    if founder is None or founder.entity_type is not EntityType.MORTAL or (stat(founder, "intellect") or 0) < FOUNDER_INTELLECT:
        return None
    if held(creed.id, founder.id, founder.location_id):
        return None
    if not ctx.rng(f"creed_text.{creed.id}.{ctx.epoch}").chance(ctx.rules.ideologies.text_chance):
        return None
    book = await create_record(
        ctx,
        RecordSpec(
            name=f"The Book of {creed.name.removeprefix('The ')}",
            entity_type=EntityType.ITEM,
            stats=ItemStats(might=PERCENT // 10),
            body=f"{founder.name} set down the teachings of {creed.name}.",
            power=2,
            world_id=founder.world_id,
            location_id=founder.location_id,
            maker_entity_id=founder.id,
        ),
    )
    await profile_of(ctx, book, ItemClass.BOOK)
    await connect(ctx.session, founder.id, book.id, BondKind.OWNS, ctx.epoch, description="wrote it")
    profile.texts = [*profile.texts, book.id]
    return book


async def spread(ctx: TickContext, creed: EntityRow, profile: IdeologyProfileRow) -> int:
    table = ctx.rules.ideologies
    adherents = {
        row.adherent_entity_id: row for row in await ctx.session.scalars(select(IdeologyAdherentRow).where(IdeologyAdherentRow.ideology_entity_id == creed.id))
    }
    gained = 0
    links = await ctx.session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(
            BondRow.source_node_id.in_(list(adherents)),
            BondRow.kind.in_([BondKind.TRADES_WITH, BondKind.ALLY, BondKind.RULES]),
            BondRow.state == BondState.ACTIVE,
        )
    )
    paths = [*links.all(), *await learned_paths(ctx, creed, profile, adherents)]
    for source, target in paths:
        if target in adherents:
            continue
        community = await living_entity(ctx.session, target)
        if community is None or community.entity_type not in COMMUNITY_TYPES or held(community.id):
            continue
        society = await ctx.session.get(CommunitySocietyRow, target)
        if await banned_for(ctx.session, target, creed.id) and not await read_in_secret(ctx, target, creed.id):
            continue
        schooled = 1 + table.school_pct / PERCENT if await institutions(ctx.session, target) else 1.0
        presses = 1 + ctx.rules.discovery.printed_creed_pct / PERCENT if await printed(ctx.session, source) else 1.0
        chance = table.spread_chance * (1 + appeal_for(profile, society, table.discontent_pct)) * schooled * presses
        if ctx.rng(f"creed_spread.{creed.id}.{target}.{ctx.epoch}").chance(chance):
            row = IdeologyAdherentRow(
                ideology_entity_id=creed.id, adherent_entity_id=target, strength=adherents[source].strength // 2, state=False, since_epoch=ctx.epoch
            )
            ctx.session.add(row)
            adherents[target] = row
            gained += 1
    for row in adherents.values():
        society = await ctx.session.get(CommunitySocietyRow, row.adherent_entity_id)
        row.strength = clamp_int(row.strength + round_half_up(appeal_for(profile, society, table.discontent_pct) * table.value_pressure * 5), 0, PERCENT)
    set_stats(creed, adherents=len(adherents))
    return gained


async def press(ctx: TickContext, creed: EntityRow, profile: IdeologyProfileRow) -> int:
    table = ctx.rules.ideologies
    pressed = 0
    for row in await ctx.session.scalars(select(IdeologyAdherentRow).where(IdeologyAdherentRow.ideology_entity_id == creed.id)):
        values = await stored_values(ctx.session, ValueHolder.CULTURE, row.adherent_entity_id)
        if not values:
            continue
        for key, value in profile.value_delta.items():
            values[ValueAxis(key)] = values.get(ValueAxis(key), 0) + round_half_up(value * row.strength / PERCENT * table.value_pressure / 5)
        await write_values(ctx.session, ValueHolder.CULTURE, row.adherent_entity_id, values)
        pressed += 1
    return pressed


async def realm_communities(ctx: TickContext, realm: PolityProfileRow) -> set[int]:
    members = set(await ctx.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == realm.polity_entity_id)))
    return members | ({realm.core_entity_id} if realm.core_entity_id is not None else set())


async def adopt(ctx: TickContext, creed: EntityRow) -> int:
    table = ctx.rules.ideologies
    adopted = 0
    held_by = {
        row.adherent_entity_id: row for row in await ctx.session.scalars(select(IdeologyAdherentRow).where(IdeologyAdherentRow.ideology_entity_id == creed.id))
    }
    for realm in list(await ctx.session.scalars(select(PolityProfileRow).order_by(PolityProfileRow.polity_entity_id))):
        if held(realm.polity_entity_id) or "ideology_entity_id" in realm.locked:
            continue
        rows = [held_by[community] for community in sorted(await realm_communities(ctx, realm)) if community in held_by]
        wanted = max((row.strength for row in rows), default=0) >= table.adoption_strength
        if wanted and realm.ideology_entity_id is None:
            realm.ideology_entity_id = creed.id
            adopted += 1
        elif not wanted and realm.ideology_entity_id == creed.id:
            realm.ideology_entity_id = None
        for row in rows:
            row.state = realm.ideology_entity_id == creed.id
    return adopted


async def clash_with_faith(ctx: TickContext, creed: EntityRow) -> int:
    table = ctx.rules.ideologies
    tenets = await tenets_of(ctx, creed.id)
    hated = frozenset().union(*(ANTI_FAITH.get(tenet, frozenset()) for tenet in tenets))
    if not hated:
        return 0
    struck = 0
    for row in list(await ctx.session.scalars(select(IdeologyAdherentRow).where(IdeologyAdherentRow.ideology_entity_id == creed.id))):
        god = await patron_node(ctx.session, row.adherent_entity_id)
        if god is None:
            continue
        cults = select(BondRow.source_node_id).where(BondRow.target_node_id == god, BondRow.kind == BondKind.WORSHIPS)
        opposed = await ctx.session.scalar(
            select(CultTenetRow.cult_entity_id).where(CultTenetRow.cult_entity_id.in_(cults), CultTenetRow.tenet.in_(list(hated))).limit(1)
        )
        if opposed is None or not ctx.rng(f"creed_heresy.{creed.id}.{row.adherent_entity_id}.{ctx.epoch}").chance(table.persecution_chance):
            continue
        row.strength = clamp_int(row.strength - PERCENT // 5, 0, PERCENT)
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=row.adherent_entity_id,
            subject_id=opposed,
            kind=MemoryKind.ILL_WILL,
            magnitude=-10,
            epoch=ctx.epoch,
            note=f"persecuted {creed.name}",
        )
        struck += 1
    return struck


async def godless(ctx: TickContext, creed: EntityRow) -> int:
    if IT.ANTI_GOD not in await tenets_of(ctx, creed.id):
        return 0
    drained = 0
    for row in await ctx.session.scalars(select(IdeologyAdherentRow).where(IdeologyAdherentRow.ideology_entity_id == creed.id)):
        god = await patron_node(ctx.session, row.adherent_entity_id)
        son = await ctx.session.get(SonRow, god) if god is not None else None
        if son is None:
            continue
        loss = round_half_up(son.faith * ctx.rules.ideologies.anti_god_faith_pct / PERCENT * row.strength / PERCENT)
        if loss:
            son.faith = max(0, son.faith - loss)
            son.existence = clamp_int(son.existence - 1, 0, PERCENT)
            drained += loss
            await answer(ctx, son, creed, row)
    return drained


async def answer(ctx: TickContext, son: SonRow, creed: EntityRow, row: IdeologyAdherentRow) -> str:
    table = ctx.rules.ideologies
    if son.mercy < table.persecuting_mercy:
        row.strength = clamp_int(row.strength - table.persecution_blow, 0, PERCENT)
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=row.adherent_entity_id,
            subject_id=son.id,
            kind=MemoryKind.ILL_WILL,
            magnitude=-table.persecution_blow,
            epoch=ctx.epoch,
            note=f"struck down for {creed.name}",
        )
        await note(
            ctx, f"{son.name} struck at those who follow {creed.name}.", key="lore.godless_persecuted", ids=[creed.id, row.adherent_entity_id], son_id=son.id
        )
        return "persecuted"
    if son.essence < table.miracle_essence:
        return "silent"
    son.essence -= table.miracle_essence
    son.faith += table.miracle_faith
    row.strength = clamp_int(row.strength - table.miracle_doubt, 0, PERCENT)
    await note(
        ctx,
        f"{son.name} answered {creed.name} with a sign, and some of its followers wavered.",
        key="lore.godless_miracle",
        ids=[creed.id, row.adherent_entity_id],
        son_id=son.id,
    )
    return "miracle"


async def suppress(ctx: TickContext, creed: EntityRow, authority_id: int | None) -> int:
    table = ctx.rules.ideologies
    rows = list(await ctx.session.scalars(select(IdeologyAdherentRow).where(IdeologyAdherentRow.ideology_entity_id == creed.id)))
    for row in rows:
        row.strength = clamp_int(row.strength - table.suppression_blow, 0, PERCENT)
        if row.state:
            row.state = False
            realm = await ctx.session.scalar(select(PolityProfileRow).where(PolityProfileRow.ideology_entity_id == creed.id).limit(1))
            if realm is not None:
                realm.ideology_entity_id = None
        if authority_id is not None and authority_id != row.adherent_entity_id:
            await remember(
                ctx.session,
                ctx.rules,
                holder_id=row.adherent_entity_id,
                subject_id=authority_id,
                kind=MemoryKind.ILL_WILL,
                magnitude=-table.suppression_blow,
                epoch=ctx.epoch,
                note=f"suppressed {creed.name}",
            )
    return len(rows)


async def revolution(ctx: TickContext, creed: EntityRow) -> str | None:
    table = ctx.rules.ideologies
    if IT.EGALITARIANISM not in await tenets_of(ctx, creed.id):
        return None
    for row in await ctx.session.scalars(
        select(IdeologyAdherentRow).where(IdeologyAdherentRow.ideology_entity_id == creed.id, IdeologyAdherentRow.strength >= table.adoption_strength // 2)
    ):
        society = await ctx.session.get(CommunitySocietyRow, row.adherent_entity_id)
        if society is None or held(row.adherent_entity_id):
            continue
        unhappy = min(society.satisfaction(social_class) for social_class in (SocialClass.FARMER, SocialClass.SERF_OR_SLAVE, SocialClass.ARTISAN))
        realm_id = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == row.adherent_entity_id).limit(1))
        realm = await ctx.session.get(PolityProfileRow, realm_id) if realm_id is not None else None
        if (
            realm is None
            or unhappy >= table.revolution_satisfaction
            or realm.stability >= table.revolution_stability
            or realm.core_entity_id in {None, row.adherent_entity_id}
        ):
            continue
        if not ctx.rng(f"revolution.{creed.id}.{row.adherent_entity_id}.{ctx.epoch}").chance(table.revolution_chance):
            continue
        from_id, against = row.adherent_entity_id, realm.core_entity_id
        if against is None or held(against) or not await declare_war_for(ctx, from_id, against, creed.name):
            continue
        rebels = await living_entity(ctx.session, from_id)
        return f"Moved by {creed.name}, {rebels.name if rebels else 'the people'} rose against their rulers to overturn the government."
    return None


async def declare_war_for(ctx: TickContext, rebels: int, rulers: int, creed: str) -> bool:
    return await declare_war(ctx, rebels, rulers, f"the revolution of {creed}", cause=WarCause.IDEOLOGY, world_cap=False)


async def living_creeds(ctx: TickContext) -> list[tuple[EntityRow, IdeologyProfileRow]]:
    rows = await ctx.session.execute(
        select(EntityRow, IdeologyProfileRow)
        .join(IdeologyProfileRow, IdeologyProfileRow.ideology_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    gone = await ended_ids(ctx.session)
    return [(entity, profile) for entity, profile in rows.all() if entity.id not in gone]

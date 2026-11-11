from sqlalchemy import func, select

from aerona.agents.context.scope import Scope
from aerona.catalog.collective import ACT_TEXT
from aerona.catalog.storylets import STORYLETS
from aerona.core.grammar import an
from aerona.db.tables.collective import (
    AccountRow,
    ArmsRow,
    CommemorationRow,
    CrowdMoodRow,
    DiasporaRow,
    FoundingMythRow,
    GenerationRow,
    LostLandRow,
    MemoryStrikeRow,
    MobRow,
    MovementRow,
    RoleNormRow,
    StoryletRunRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import CollectionRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.polity import HouseMemberRow, OfficeRow, PolityMemberRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.collective import MobStatus, RoleEligibility, StoryletStatus
from aerona.domain.enums.mind import EthicalStance
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.body.customs import people_of
from aerona.engine.collective.dating import render_date
from aerona.engine.collective.heraldry import blazon
from aerona.engine.collective.norms import norms_of
from aerona.engine.collective.storylets import choice_texts, situation

STRICT = (EthicalStance.UNTHINKABLE, EthicalStance.SHAMEFUL, EthicalStance.REQUIRED)
NORM_LINES = 6
MOOD_AT = 30
MEMORY_LINES = 3
GENERATION_LINES = 2
RECENT = 1
SON_MOOD_AT = 50
SON_LINES = 4


async def town_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    if me.location_id is None:
        return found
    mood = await session.get(CrowdMoodRow, me.location_id)
    if mood is not None and max(mood.anger, mood.anxiety, mood.fervour) >= MOOD_AT:
        found.append(f"your town's mood: anger {mood.anger}, fear {mood.anxiety}, fervour {mood.fervour}, held back by the watch at {mood.deterrence}")
    for mob in await session.scalars(select(MobRow).where(MobRow.settlement_entity_id == me.location_id, MobRow.status != MobStatus.DISPERSED)):
        found.append(f"a crowd of {mob.size} has {ACT_TEXT[mob.act]} and goes for the {mob.target.value}, anger {mob.anger}")
    for movement in await session.scalars(select(MovementRow).where(MovementRow.settlement_entity_id == me.location_id, MovementRow.ended_epoch.is_(None))):
        found.append(f"a movement of {movement.members} that {ACT_TEXT[movement.act]} stands at strength {movement.strength}")
    return found


async def custom_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    people = await people_of(session, me)
    if people is None:
        return []
    found: list[str] = []
    year = scope.cosmos.epoch_start_year
    found.append(f"by your people's reckoning it is {await render_date(session, people.id, year)}")
    norms = await norms_of(session, people.id)
    strict = sorted(((situation, behaviour), stance) for (situation, behaviour), stance in norms.items() if stance in STRICT)
    for (where, behaviour), stance in strict[:NORM_LINES]:
        found.append(f"{behaviour.value.replace('_', ' ')} at {an(where.value.replace('_', ' '))} is {stance.value.replace('_', ' ')}")
    for row in await session.scalars(select(RoleNormRow).where(RoleNormRow.holder_entity_id == people.id).order_by(RoleNormRow.role)):
        if row.eligibility is not RoleEligibility.ANY or row.classes:
            classes = f", only for {', '.join(row.classes)}" if row.classes else ""
            found.append(f"the {row.role.value} role is {row.eligibility.value.replace('_', ' ')} from age {row.min_age}{classes}")
    return found


async def own_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    house = await session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == me.id).limit(1))
    arms = await session.get(ArmsRow, house) if house is not None else None
    if arms is not None:
        found.append(f"your house bears {blazon(arms)}" + (f", with the words: {arms.motto}" if arms.motto else ""))
    for run in await session.scalars(
        select(StoryletRunRow)
        .where(StoryletRunRow.chooser_node_id == me.id, StoryletRunRow.status == StoryletStatus.OPEN, StoryletRunRow.opened_epoch <= scope.epoch)
        .order_by(StoryletRunRow.id)
    ):
        options = "; ".join(f"{index}: {text}" for index, text in enumerate(await choice_texts(session, run)))
        found.append(f"storylet {run.id} waits for your choice by epoch {run.due_epoch}: {await situation(session, run)} Choices: {options}")
    ruler = await session.scalar(select(OfficeRow.id).where(OfficeRow.holder_entity_id == me.id, OfficeRow.kind == OfficeKind.RULER).limit(1))
    if ruler is not None:
        found.append("as ruler you may commission your realm's account of an event or strike a figure from its records")
    return found


async def realm_of(scope: Scope, me: EntityRow) -> int | None:
    profile = await scope.session.get(MortalProfileRow, me.id)
    if profile is not None and profile.polity_id is not None:
        return profile.polity_id
    if me.location_id is None:
        return None
    return await scope.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == me.location_id).limit(1))


async def named(scope: Scope, node_id: int | None) -> str | None:
    node = await scope.session.get(NodeRow, node_id) if node_id is not None else None
    return node.name if node is not None else None


async def myth_line(scope: Scope, holder: EntityRow) -> str | None:
    myth = await scope.session.get(FoundingMythRow, holder.id)
    if myth is None:
        return None
    account = await scope.session.get(AccountRow, myth.account_id) if myth.account_id is not None else None
    event = await scope.session.get(CollectionRow, account.collection_id) if account is not None and account.collection_id is not None else None
    told = f" ({event.name})" if event is not None else ""
    if myth.debunked_epoch is not None:
        return f"the founding story of {holder.name}{told} was shown untrue in epoch {myth.debunked_epoch}"
    return f"the founding story of {holder.name}{told} is believed at credence {myth.credence}"


async def memory_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    realm_id = await realm_of(scope, me)
    realm = await session.get(EntityRow, realm_id) if realm_id is not None else None
    people = await people_of(session, me)
    for holder in (holder for holder in (realm, people) if holder is not None):
        line = await myth_line(scope, holder)
        if line is not None:
            found.append(line)
        for kept in await session.scalars(
            select(CommemorationRow)
            .where(CommemorationRow.holder_entity_id == holder.id, CommemorationRow.last_observed_epoch >= scope.epoch - RECENT)
            .order_by(CommemorationRow.collection_id)
            .limit(MEMORY_LINES)
        ):
            event = await session.get(CollectionRow, kept.collection_id)
            if event is not None:
                found.append(f"{holder.name} {'celebrated' if kept.pride else 'mourned'} the anniversary of {event.name}")
    if realm is not None:
        for lost in await session.scalars(
            select(LostLandRow)
            .where(LostLandRow.claimant_entity_id == realm.id, LostLandRow.strength > 0)
            .order_by(LostLandRow.strength.desc())
            .limit(MEMORY_LINES)
        ):
            region = await named(scope, lost.region_entity_id)
            claimed = f", claimed back in epoch {lost.claimed_epoch}" if lost.claimed_epoch is not None else ""
            found.append(f"{realm.name} remembers losing {region} in epoch {lost.lost_epoch}, memory strength {lost.strength}{claimed}")
        for strike in await session.scalars(
            select(MemoryStrikeRow).where(MemoryStrikeRow.by_entity_id == realm.id, MemoryStrikeRow.active.is_(True)).limit(MEMORY_LINES)
        ):
            found.append(f"{await named(scope, strike.node_id)} is struck from the records of {realm.name}")
    if me.location_id is not None:
        for generation in await session.scalars(
            select(GenerationRow)
            .where(GenerationRow.community_entity_id == me.location_id, GenerationRow.passed_epoch.is_(None), GenerationRow.alive > 0)
            .order_by(GenerationRow.generation_epoch.desc())
            .limit(GENERATION_LINES)
        ):
            shaped = ", ".join(kind.replace("_", " ") for kind in generation.formative) or "quiet years"
            found.append(f"the generation of your town young in epoch {generation.generation_epoch} was shaped by {shaped}; {generation.alive} of them live")
        for diaspora in await session.scalars(
            select(DiasporaRow)
            .where(DiasporaRow.host_entity_id == me.location_id, DiasporaRow.population > 0)
            .order_by(DiasporaRow.population.desc())
            .limit(MEMORY_LINES)
        ):
            found.append(f"{await named(scope, diaspora.people_entity_id)} keep a diaspora of {diaspora.population} here, ties to home {diaspora.ties}")
    return found


async def mortal_collective_lines(scope: Scope, me: EntityRow) -> list[str]:
    return [*await own_lines(scope, me), *await town_lines(scope, me), *await custom_lines(scope, me), *await memory_lines(scope, me)]


async def son_collective_lines(scope: Scope, son: SonRow) -> list[str]:
    session = scope.session
    world = son.current_world_id
    if world is None:
        return []
    found: list[str] = []
    stirred = await session.execute(
        select(EntityRow, CrowdMoodRow)
        .join(CrowdMoodRow, CrowdMoodRow.settlement_entity_id == EntityRow.id)
        .where(EntityRow.world_id == world, func.max(CrowdMoodRow.anger, CrowdMoodRow.anxiety, CrowdMoodRow.fervour) >= SON_MOOD_AT)
        .order_by(func.max(CrowdMoodRow.anger, CrowdMoodRow.anxiety, CrowdMoodRow.fervour).desc(), EntityRow.id)
        .limit(SON_LINES)
    )
    for town, mood in stirred.all():
        found.append(f"{town.name} (town {town.id}) is stirred: anger {mood.anger}, fear {mood.anxiety}, fervour {mood.fervour}, watch {mood.deterrence}")
    crowds = await session.execute(
        select(EntityRow, MobRow)
        .join(MobRow, MobRow.settlement_entity_id == EntityRow.id)
        .where(EntityRow.world_id == world, MobRow.status != MobStatus.DISPERSED)
        .order_by(MobRow.size.desc())
        .limit(SON_LINES)
    )
    for town, mob in crowds.all():
        found.append(f"a crowd of {mob.size} in {town.name} has {ACT_TEXT[mob.act]}")
    rewritten = await session.execute(
        select(EntityRow, AccountRow)
        .join(AccountRow, AccountRow.holder_entity_id == EntityRow.id)
        .where(EntityRow.world_id == world, AccountRow.revised_from_id.is_not(None), AccountRow.defaced.is_(False))
        .order_by(AccountRow.credence.desc(), AccountRow.id)
        .limit(SON_LINES)
    )
    for holder, account in rewritten.all():
        event = await session.get(CollectionRow, account.collection_id) if account.collection_id is not None else None
        about = f" of {event.name}" if event is not None else ""
        found.append(f"account {account.id}: the {account.kind.value.replace('_', ' ')}{about} kept by {holder.name} hides an older telling")
    for run in await session.scalars(
        select(StoryletRunRow)
        .where(StoryletRunRow.world_id == world, StoryletRunRow.status == StoryletStatus.OPEN)
        .order_by(StoryletRunRow.id)
        .limit(SON_LINES)
    ):
        chooser = await named(scope, run.chooser_node_id)
        found.append(f"the storylet {STORYLETS[run.storylet].title} waits on {chooser or 'its chooser'} until epoch {run.due_epoch}")
    return found

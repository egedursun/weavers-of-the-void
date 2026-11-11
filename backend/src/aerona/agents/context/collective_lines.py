from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.catalog.collective import ACT_TEXT
from aerona.core.grammar import an
from aerona.db.tables.collective import ArmsRow, CrowdMoodRow, MobRow, MovementRow, RoleNormRow, StoryletRunRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import HouseMemberRow, OfficeRow
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


async def mortal_collective_lines(scope: Scope, me: EntityRow) -> list[str]:
    return [*await own_lines(scope, me), *await town_lines(scope, me), *await custom_lines(scope, me)]

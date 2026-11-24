from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.body_systems import BodySystemRow, SensitivityRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.standing import ProfessionOfValueRow
from aerona.domain.enums.body_systems import BodySystem
from aerona.engine.body.customs import people_of

RECENT = 3


async def mortal_body_system_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    folk = await people_of(session, me)
    if folk is not None:
        rows = list(await session.scalars(select(BodySystemRow).where(BodySystemRow.holder_entity_id == folk.id).order_by(BodySystemRow.id)))
        for row in rows:
            if not row.present:
                found.append(f"your body has no {spoken(row.system)}")
            elif row.failed:
                found.append(f"the {spoken(row.system)} of your people is failing under this world")
            elif row.strained:
                found.append(f"the {spoken(row.system)} of your people strains against this world")
        breath = next((row for row in rows if row.system is BodySystem.BREATH and row.present), None)
        if breath is not None:
            found.append(f"your body bears weight up to {breath.gravity_max} and poison up to {breath.toxin_tolerance}")
            found.append(f"it bears warmth from {breath.cold_min} to {breath.heat_max}")
            found.append(f"it bears rays up to {breath.radiation_max} and needs light of at least {breath.light_min}")
            found.append(f"it bears air as dry or damp as {breath.humidity_range}")
    for sensitive in await session.scalars(select(SensitivityRow).where(SensitivityRow.holder_entity_id == me.id).order_by(SensitivityRow.id)):
        what = spoken(sensitive.trigger_commodity) if sensitive.trigger_commodity is not None else spoken(sensitive.kind)
        found.append(f"you fall ill from {what}, at a severity of {sensitive.severity}")
    return found


async def mortal_standing_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    for row in await session.scalars(select(ProfessionOfValueRow).where(ProfessionOfValueRow.holder_node_id == me.id).order_by(ProfessionOfValueRow.id)):
        shown = ", and it is known" if row.exposed else ""
        found.append(f"you profess {spoken(row.axis)} at {row.strength}; your deeds fall short of it by {row.gap}{shown}")
    near = await session.execute(
        select(ProfessionOfValueRow.axis, EntityRow.name)
        .join(EntityRow, EntityRow.id == ProfessionOfValueRow.holder_node_id)
        .where(EntityRow.location_id == me.location_id, ProfessionOfValueRow.holder_node_id != me.id, ProfessionOfValueRow.exposed.is_(True))
        .order_by(ProfessionOfValueRow.id)
        .limit(RECENT)
    )
    found.extend(f"it is known that {name} professes {spoken(axis)} and acts against it" for axis, name in near)
    return found

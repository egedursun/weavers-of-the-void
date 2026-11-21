from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.mass_weapons import DeterrencePostureRow, MassWeaponRow, WarRemnantRow
from aerona.db.tables.polity import OfficeRow
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.primitives.distance import RegionAtlas


async def led_by(scope: Scope, me: EntityRow) -> set[int]:
    session = scope.session
    realms = await session.scalars(select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == me.id, OfficeRow.kind == OfficeKind.RULER))
    orgs = await session.scalars(select(OrgGovernanceRow.org_node_id).where(OrgGovernanceRow.head_node_id == me.id))
    return {*realms, *orgs}


async def weapon_line(scope: Scope, weapon: MassWeaponRow, *, own: bool) -> str:
    whose = "" if own else f" held by {await named(scope, weapon.holder_entity_id)}"
    state = f"at its {spoken(weapon.stage)} stage, {weapon.count} ready, readiness {weapon.readiness}"
    return f"weapon {weapon.id}{whose}: {spoken(weapon.harm)} with {spoken(weapon.reach)} reach, {state}"


async def mortal_arsenal_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    mine = await led_by(scope, me)
    found: list[str] = []
    if mine:
        for weapon in await session.scalars(select(MassWeaponRow).order_by(MassWeaponRow.id)):
            if weapon.holder_entity_id in mine or mine & set(weapon.seen_by or []):
                found.append(await weapon_line(scope, weapon, own=weapon.holder_entity_id in mine))
        postures = select(DeterrencePostureRow).where(DeterrencePostureRow.holder_entity_id.in_(sorted(mine)))
        for posture in await session.scalars(postures.order_by(DeterrencePostureRow.id)):
            toward = await named(scope, posture.toward_entity_id) if posture.toward_entity_id is not None else "all"
            found.append(f"posture of {spoken(posture.posture)} toward {toward}, credibility {posture.credibility}")
    region = (await RegionAtlas.load(session)).top_region(me.location_id) if me.location_id is not None else None
    if region is not None:
        for remnant in await session.scalars(select(WarRemnantRow).where(WarRemnantRow.region_entity_id == region).order_by(WarRemnantRow.id)):
            found.append(f"{spoken(remnant.kind)} left by war in your land, density {remnant.density}")
    return found

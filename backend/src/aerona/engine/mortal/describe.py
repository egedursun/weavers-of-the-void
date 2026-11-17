from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind_split import SUMMARIES
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalEquipmentRow, MortalProfileRow
from aerona.engine.mortal.kin import children_of, parents_of, spouses_of
from aerona.engine.mortal.life import sex_of_stats
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

FULL = 100


async def names(session: AsyncSession, ids: list[int]) -> str:
    found = [entity.name for node in ids if (entity := await session.get(EntityRow, node)) is not None]
    return ", ".join(found)


async def life_lines(session: AsyncSession, rules: Rules, mortal: EntityRow, *, private: bool) -> list[str]:
    profile = await session.get(MortalProfileRow, mortal.id)
    if profile is None:
        return []
    lines = [f"Life: {spoken(profile.life_stage)}, {spoken(sex_of_stats(mortal))}; health {profile.health}/{FULL}"]
    body_and_mind = ", ".join(f"{name} {stat(mortal, name) or 0}" for name in SUMMARIES)
    lines.append(f"Body and mind: {body_and_mind}")
    lines.append(f"Standing: wealth {profile.wealth}, renown {profile.renown}, honour {profile.honour}, infamy {profile.infamy}")
    if profile.cause_of_death is not None:
        lines.append(f"Died of {spoken(profile.cause_of_death)}")
    kin = []
    for label, ids in (
        ("parents", await parents_of(session, mortal.id)),
        ("spouses", await spouses_of(session, mortal.id)),
        ("children", await children_of(session, mortal.id)),
    ):
        if ids:
            kin.append(f"{label} {await names(session, ids)}")
    if kin:
        lines.append("Kin: " + "; ".join(kin))
    if not private:
        return lines
    lines.append(f"Loyalty: to your liege {profile.loyalty_liege}, to your people {profile.loyalty_community}, to your god {profile.loyalty_god}")
    strain = "near breaking" if profile.stress >= rules.stress.break_threshold * 3 // 4 else "bearable"
    lines.append(f"Stress: {profile.stress}/{FULL} ({strain})")
    if profile.career is not None:
        lines.append(f"Path in life: {spoken(profile.career)}")
    gear = await session.get(MortalEquipmentRow, mortal.id)
    if gear is not None:
        carried = [item for item in (gear.wielded_main_id, gear.armour_body_id, gear.mount_id, gear.focus_id) if item is not None]
        if carried:
            lines.append(f"You carry: {await names(session, carried)}")
    return lines

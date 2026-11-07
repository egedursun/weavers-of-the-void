from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.genetics import DWELLINGS, GIFT_STANCE_LABELS, HOUSEHOLD_ROLE_LABELS
from aerona.core.grammar import an
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import AllelePoolRow, GenomeRow
from aerona.db.tables.households import HouseholdMemberRow
from aerona.engine.body.customs import people_of
from aerona.engine.genetics.genome import appearance_text, gifted_schools
from aerona.engine.households.homes import expectation, home_of
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class LineageBits:
    looks: str = ""
    gift: str = ""
    household: str = ""
    dwelling: str = ""


def school_label(value: str) -> str:
    return value.replace("elemental_", "").replace("_", " ")


async def lineage_lines(session: AsyncSession, rules: Rules, me: EntityRow) -> LineageBits:
    genome = await session.get(GenomeRow, me.id)
    looks = appearance_text(genome.genes, genome.marks) if genome is not None else ""
    gift = ""
    if genome is not None and (schools := gifted_schools(rules, genome.genes)):
        people = await people_of(session, me)
        pool = await session.get(AllelePoolRow, people.id) if people is not None else None
        stance = f", which your people hold {GIFT_STANCE_LABELS[pool.gift_stance].lower()}" if pool is not None else ""
        gift = f"gifted in {', '.join(school_label(school.value) for school in schools)}{stance}"
    household, dwelling, quality, members = await home_of(session, rules, me.id)
    role = await session.get(HouseholdMemberRow, me.id)
    household_text = (
        f"{HOUSEHOLD_ROLE_LABELS[role.role].lower()} of {household.name}, {members} strong, purse {household.wealth}, burden {household.burden}"
        if household is not None and role is not None
        else ""
    )
    dwelling_text = (
        f"{an(DWELLINGS[dwelling.kind].label.lower())} of {dwelling.rooms} rooms, quality {quality}, your class expects {expectation(household.social_class)}"
        if dwelling is not None and household is not None
        else ""
    )
    return LineageBits(looks, gift, household_text, dwelling_text)

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.rules.registry import Rules
from aerona.services.integrity.age_consistency import raise_lifespans


async def repair_mortal_ages(session: AsyncSession, rules: Rules) -> int:
    return await raise_lifespans(session, rules)

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.interconnect import WAR_CAUSE_INCIDENTS
from aerona.db.repositories.chronicle import ChronicleRepository
from aerona.domain.enums.war import WarCause

SUCCESSION_INCIDENTS = ("mortal.death", "polity.usurped", "polity.succession")
KILLING_INCIDENTS = ("mortal.death.cause", "war.battle.", "duel.", "memory.vengeance")


async def war_cause_incident(session: AsyncSession, cause: WarCause, attacker_id: int, defender_id: int, epoch: int) -> int | None:
    chronicle = ChronicleRepository(session)
    kinds = WAR_CAUSE_INCIDENTS.get(cause, ())
    pair = [attacker_id, defender_id]
    if kinds:
        found = await chronicle.prior_incident(pair, kinds, before_epoch=epoch, shared=True) or await chronicle.prior_incident(pair, kinds, before_epoch=epoch)
        if found is not None:
            return found
    return await chronicle.prior_incident(pair, before_epoch=epoch, shared=True)


async def succession_incident(session: AsyncSession, realm_id: int, ruler_ids: list[int]) -> int | None:
    chronicle = ChronicleRepository(session)
    return await chronicle.prior_incident([realm_id, *ruler_ids], SUCCESSION_INCIDENTS)


async def killing_incident(session: AsyncSession, victim_id: int, killer_id: int | None) -> int | None:
    chronicle = ChronicleRepository(session)
    if killer_id is not None:
        found = await chronicle.prior_incident([victim_id, killer_id], KILLING_INCIDENTS, shared=True)
        if found is not None:
            return found
    return await chronicle.prior_incident([victim_id], KILLING_INCIDENTS)

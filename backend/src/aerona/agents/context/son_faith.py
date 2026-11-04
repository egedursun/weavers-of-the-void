from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import HeresyRow
from aerona.db.tables.sons import SonRow
from aerona.engine.faith.book import Church, FaithBook
from aerona.engine.faith.souls import realm_population
from aerona.engine.primitives.stats import stat


def words(value: str) -> str:
    return value.replace("_", " ")


async def church_line(scope: Scope, church: Church) -> str:
    doctrine = church.doctrine
    cult = church.cult
    zeal, devotion = stat(cult, "zeal") or 0, stat(cult, "devotion") or 0
    tenets = ", ".join(sorted((row.name or words(tenet.value)) for tenet, row in church.tenets.items())) or "none yet"
    if doctrine is None:
        return f"- {cult.name} (#{cult.id}): zeal {zeal}, devotion {devotion}; no doctrine is written yet; tenets: {tenets}"
    liturgy = await scope.session.get(EntityRow, doctrine.liturgical_language_id) if doctrine.liturgical_language_id is not None else None
    heresies = len(list(await scope.session.scalars(select(HeresyRow.heresy_entity_id).where(HeresyRow.parent_entity_id == cult.id))))
    parts = [
        f"judges the dead by {words(doctrine.judgement.value)}",
        f"orthodoxy {doctrine.orthodoxy}",
        f"zeal {zeal}",
        f"devotion {devotion}",
        f"treasury {doctrine.treasury} (tithe {doctrine.tithe_rate}%)",
        f"{doctrine.clergy_count} clergy of learning {doctrine.clergy_quality}",
        f"souls reborn by {words(doctrine.rebirth_path.value)}",
    ]
    if liturgy is not None:
        parts.append(f"liturgy in {liturgy.name}")
    if heresies:
        parts.append(f"{heresies} heresies split from it")
    if doctrine.fanaticism is not None:
        parts.append(f"lately turned to {words(doctrine.fanaticism.value)}")
    return f"- {cult.name} (#{cult.id}): {'; '.join(parts)}; tenets: {tenets}"


async def son_faith(scope: Scope, son: SonRow) -> str:
    book = await FaithBook.load(scope.session)
    churches = book.by_god.get(son.id, [])
    souls = await realm_population(scope.session, son.id)
    if not churches and not souls:
        return ""
    lines = [await church_line(scope, church) for church in churches]
    lines.append(f"Souls of your faithful dwelling in the realms of the dead: {souls}.")
    return "\n".join(lines)

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.anatomy import ANATOMIES
from aerona.catalog.tongues import MODALITY_NEEDS, MODALITY_ORDER, WRITABLE
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.made import PeopleSubstrateRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import BodyFunction
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.minds import MindSeat
from aerona.domain.enums.tongues import LanguageModality
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.gods.queries import community_of
from aerona.engine.primitives.queries import canon, spoken_language
from aerona.rules.registry import Rules


def speaking(language_id: int) -> Select[int]:
    return select(BondRow.source_node_id).where(BondRow.target_node_id == language_id, BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.ACTIVE)


async def modality_of(session: AsyncSession, language_id: int | None) -> LanguageModality:
    profile = await session.get(LanguageProfileRow, language_id) if language_id is not None else None
    return profile.modality if profile is not None else LanguageModality.VOCAL


async def writable(session: AsyncSession, language_id: int | None) -> bool:
    return WRITABLE[await modality_of(session, language_id)]


async def telepathic(session: AsyncSession, tongues: set[int]) -> bool:
    for tongue in sorted(tongues):
        if await modality_of(session, tongue) is LanguageModality.TELEPATHIC:
            return True
    return False


async def unwritten_factor(session: AsyncSession, rules: Rules, language_id: int | None) -> float:
    return 1.0 if await writable(session, language_id) else rules.modality.unwritten_literacy_pct / PERCENT


def suited(functions: frozenset[BodyFunction]) -> LanguageModality:
    for modality in MODALITY_ORDER:
        if MODALITY_NEEDS[modality] <= functions:
            return modality
    return LanguageModality.TELEPATHIC


async def body_functions(session: AsyncSession, people_id: int) -> frozenset[BodyFunction] | None:
    biology = await session.get(PeopleBiologyRow, people_id)
    if biology is None:
        return None
    return frozenset(function for part in ANATOMIES[biology.body_plan].parts for function in part.functions)


async def made_people(session: AsyncSession, people: EntityRow) -> bool:
    if people.entity_type is not EntityType.PEOPLE:
        return False
    shares = list(await session.scalars(select(PeopleSubstrateRow).where(PeopleSubstrateRow.people_entity_id == people.id)))
    return bool(shares) and all(row.seat is not MindSeat.BODY for row in shares if row.share_pct > 0)


async def settle_modalities(ctx: TickContext) -> int:
    settled = 0
    for language in await canon(ctx.session, [EntityType.LANGUAGE]):
        profile = await ctx.session.get(LanguageProfileRow, language.id)
        if profile is None or held(language.id) or profile.modality is not LanguageModality.VOCAL:
            continue
        peoples = list(await ctx.session.scalars(select(EntityRow).where(EntityRow.id.in_(speaking(language.id)))))
        bodies = [await body_functions(ctx.session, row.id) for row in peoples if row.entity_type is EntityType.PEOPLE]
        known = [body for body in bodies if body is not None]
        made = [await made_people(ctx.session, row) for row in peoples]
        if made and all(made):
            profile.modality = LanguageModality.DATA
            settled += 1
        elif known and all(BodyFunction.SPEECH not in body for body in known):
            profile.modality = suited(known[0])
            settled += 1
    return settled


async def own_tongue(session: AsyncSession, entity: EntityRow) -> EntityRow | None:
    for holder in (entity.id, entity.location_id, entity.affiliated_entity_id):
        found = await spoken_language(session, holder) if holder is not None else None
        if found is not None:
            return found
    community = await community_of(session, entity)
    people = await people_of(session, community) if community is not None else None
    for group in (community, people):
        spoken = await spoken_language(session, group.id) if group is not None else None
        if spoken is not None:
            return spoken
    return None

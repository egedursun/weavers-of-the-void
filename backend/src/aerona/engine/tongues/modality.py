from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.anatomy import ANATOMIES
from aerona.catalog.tongues import BASE_SENSES, FIELD_MODALITIES, MODALITY_NEEDS, MODALITY_ORDER, MODALITY_SENSE, TEXTURE_MODALITY, WRITABLE
from aerona.constants.units import PERCENT
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.made import PeopleSubstrateRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import BodyFunction
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.minds import MindSeat
from aerona.domain.enums.nature import SenseKind
from aerona.domain.enums.tongues import LanguageModality
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.gods.queries import community_of
from aerona.engine.nature.senses import senses_of
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


def perceivable(modality: LanguageModality, senses: frozenset[SenseKind]) -> bool:
    sense = MODALITY_SENSE[modality]
    return sense is None or sense in senses


def suited(functions: frozenset[BodyFunction], senses: frozenset[SenseKind] = BASE_SENSES) -> LanguageModality:
    for modality in FIELD_MODALITIES:
        if MODALITY_NEEDS[modality] <= functions and MODALITY_SENSE[modality] in senses:
            return modality
    for modality in MODALITY_ORDER:
        if MODALITY_NEEDS[modality] <= functions and perceivable(modality, senses):
            return modality
    return LanguageModality.TELEPATHIC


async def perceiving(session: AsyncSession, people_id: int, functions: frozenset[BodyFunction]) -> frozenset[SenseKind]:
    held_senses = frozenset(sense for sense, acuity in (await senses_of(session, people_id)).items() if acuity > 0)
    found = held_senses or BASE_SENSES
    if BodyFunction.SIGHT not in functions:
        found -= {SenseKind.SIGHT}
    if BodyFunction.HEARING not in functions:
        found -= {SenseKind.HEARING}
    return found


def fits(modality: LanguageModality, functions: frozenset[BodyFunction], senses: frozenset[SenseKind]) -> bool:
    return MODALITY_NEEDS[modality] <= functions and perceivable(modality, senses)


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


async def texture_modality(session: AsyncSession) -> LanguageModality | None:
    cosmos = await CosmosRepository(session).get()
    settings = cosmos.genesis_settings if cosmos is not None else None
    return TEXTURE_MODALITY.get(settings.language_texture) if settings is not None else None


async def settle_modalities(ctx: TickContext) -> int:
    settled = 0
    for language in await canon(ctx.session, [EntityType.LANGUAGE]):
        profile = await ctx.session.get(LanguageProfileRow, language.id)
        if profile is None or held(language.id) or profile.modality is not LanguageModality.VOCAL:
            continue
        peoples = list(await ctx.session.scalars(select(EntityRow).where(EntityRow.id.in_(speaking(language.id)))))
        folk = [row for row in peoples if row.entity_type is EntityType.PEOPLE]
        bodies = [(row.id, await body_functions(ctx.session, row.id)) for row in folk]
        known = [(people_id, body) for people_id, body in bodies if body is not None]
        made = [await made_people(ctx.session, row) for row in peoples]
        textured = await texture_modality(ctx.session) if language.birth_epoch <= ctx.rules.sound_changes.texture_epochs else None
        if made and all(made):
            profile.modality = LanguageModality.DATA
            settled += 1
        elif textured is not None:
            profile.modality = textured
            settled += 1
        elif known and all(BodyFunction.SPEECH not in body for _, body in known):
            first, functions = known[0]
            profile.modality = suited(functions, await perceiving(ctx.session, first, functions))
            settled += 1
        elif known and not any([await hears(ctx.session, people_id, body) for people_id, body in known]):
            first, functions = known[0]
            profile.modality = suited(functions - {BodyFunction.SPEECH}, await perceiving(ctx.session, first, functions))
            settled += 1
    return settled


async def hears(session: AsyncSession, people_id: int, functions: frozenset[BodyFunction]) -> bool:
    return SenseKind.HEARING in await perceiving(session, people_id, functions)


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

import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.ask import ask
from aerona.agents.chronicle import write_line
from aerona.agents.context.geography import geography_lines
from aerona.agents.context.scope import load_scope
from aerona.agents.context.world_summary import world_summary
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.agents.stats import stats_from
from aerona.agents.text import sanitize
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.economy.resources import set_resource_yield
from aerona.prompts import PromptId
from aerona.prompts.contexts.genesis import AwakenPeoplesContext
from aerona.prompts.data.images import fix_image_prompt
from aerona.prompts.schemas.genesis import AwakenedPeople, AwakenedRecord, AwakenPeoplesOutput
from aerona.rules.registry import Rules

KNOWLEDGE_TAG = "branch:{branch}"


async def add_record(
    session: AsyncSession,
    rules: Rules,
    record: AwakenedRecord,
    entity_type: EntityType,
    stats: dict[str, int],
    *,
    power: int,
    epoch: int,
    region: EntityRow,
    located: bool,
    domain: Domain | None = None,
    branch: KnowledgeBranch | None = None,
) -> EntityRow:
    return await EntityRepository(session).create(
        EntityDraft(
            name=await NameRepository(session).unique_name(record.name),
            entity_type=entity_type,
            description=sanitize(record.description),
            stats=stats_from(entity_type, stats, rules),
            power_level=power,
            origin=EntityOrigin.ENGINE,
            birth_epoch=epoch,
            world_id=None if located else region.world_id,
            location_id=region.id if located else None,
            subtype=record.subtype.strip() or None,
            domain=domain,
            knowledge_branch=branch,
            image_prompt=fix_image_prompt(record.image_prompt, entity_type, False, rules.content.cosmic_image_prompt_max_chars)
            if record.image_prompt.strip()
            else None,
            tags=[KNOWLEDGE_TAG.format(branch=branch.value)] if branch is not None else (),
            split_title=False,
        )
    )


def bounded(value: int | None, default: int, low: int, high: int) -> int:
    return max(low, min(high, value if value else default))


async def awaken_one(
    session: AsyncSession, rules: Rules, item: AwakenedPeople, regions: dict[int, EntityRow], *, first: EntityRow, epoch: int
) -> list[EntityRow]:
    awaken = rules.awakening
    region = regions.get(item.region_id, first)
    people = await add_record(
        session,
        rules,
        item.people,
        EntityType.PEOPLE,
        {
            "population": bounded(item.people.population, awaken.people_population, awaken.people_population_min, awaken.people_population_max),
            "martiality": item.people.martiality or awaken.people_martiality,
            "magic": item.people.magic or awaken.people_magic,
            "craft": item.people.craft or awaken.people_craft,
            "piety": awaken.people_piety,
        },
        power=awaken.people_power,
        epoch=epoch,
        region=region,
        located=True,
    )
    language = await add_record(
        session,
        rules,
        item.language,
        EntityType.LANGUAGE,
        {"spread": awaken.language_spread, "complexity": awaken.language_complexity, "sacredness": awaken.language_sacredness},
        power=awaken.language_power,
        epoch=epoch,
        region=region,
        located=False,
    )
    settlement = await add_record(
        session,
        rules,
        item.settlement,
        EntityType.SETTLEMENT,
        {
            "population": bounded(item.settlement.population, awaken.settlement_population, awaken.settlement_population_min, awaken.settlement_population_max),
            "prosperity": awaken.settlement_prosperity,
            "defense": awaken.settlement_defense,
            "piety": awaken.settlement_piety,
        },
        power=awaken.settlement_power,
        epoch=epoch,
        region=region,
        located=True,
    )
    resource = await add_record(
        session,
        rules,
        item.resource,
        EntityType.RESOURCE,
        {"abundance": awaken.resource_abundance, "value": awaken.resource_value, "might": awaken.resource_might},
        power=awaken.resource_power,
        epoch=epoch,
        region=region,
        located=True,
        domain=item.resource.domain,
    )
    await set_resource_yield(session, rules, resource.id, item.resource.commodity, item.resource.material)
    knowledge = await add_record(
        session,
        rules,
        item.knowledge,
        EntityType.KNOWLEDGE,
        {"level": awaken.knowledge_level, "spread": awaken.knowledge_spread},
        power=awaken.knowledge_power,
        epoch=epoch,
        region=region,
        located=False,
        branch=item.knowledge.branch,
    )
    tradition = await add_record(
        session,
        rules,
        item.tradition,
        EntityType.TRADITION,
        {"spread": awaken.tradition_spread, "rigidity": awaken.tradition_rigidity},
        power=awaken.tradition_power,
        epoch=epoch,
        region=region,
        located=False,
    )
    session.add_all(
        LexemeRow(
            language_entity_id=language.id,
            word=word.word,
            meaning=word.meaning,
            part_of_speech=word.kind,
            etymology=word.origin or None,
            added_by_kind=ActorKind.MORTAL,
            added_by_node_id=people.id,
            epoch=epoch,
        )
        for word in {entry.word.casefold(): entry for entry in item.language.words if entry.word.strip()}.values()
    )
    bonds = BondRepository(session)
    for source, target, kind in (
        (people, language, BondKind.SPEAKS),
        (settlement, language, BondKind.SPEAKS),
        (people, settlement, BondKind.RULES),
        (settlement, resource, BondKind.OWNS),
        (people, knowledge, BondKind.KNOWS),
        (settlement, knowledge, BondKind.KNOWS),
        (people, tradition, BondKind.CELEBRATES),
    ):
        await bonds.connect(BondDraft(source.id, target.id, kind, epoch))
    son = await session.get(SonRow, item.worshipped_son_id) if item.worshipped_son_id else None
    if son is not None:
        await bonds.connect(BondDraft(people.id, son.id, BondKind.WORSHIPS, epoch))
        await bonds.connect(BondDraft(settlement.id, son.id, BondKind.WORSHIPS, epoch))
    created = [people, language, settlement, resource, knowledge, tradition]
    text = (
        f"A new people awoke in the lands of {region.name}: {people.name}. It speaks {language.name}, founded {settlement.name}, "
        f"owns {resource.name} and knows the knowledge of {knowledge.name}."
    )
    await write_line(
        session, rules, epoch, ChronicleKind.BIRTH, text, key="awakening.people", entity_ids=[row.id for row in created], son_id=son.id if son else None
    )
    return created


async def awaken_peoples(runtime: AgentRuntime, count: int, world_id: int | None = None) -> list[int]:
    runtime.require_llm("awakening of the peoples")
    rules = await runtime.current_rules()
    requested = max(1, count)
    batch = rules.awakening.batch_cap
    names: list[str] = []
    ids: list[int] = []
    for _ in range(math.ceil(requested / batch)):
        if len(names) >= requested:
            break
        wanted = min(batch, requested - len(names))
        async with runtime.database.read() as session:
            scope = await load_scope(session, rules)
            statement = select(EntityRow).where(EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
            if world_id is not None:
                statement = statement.where(EntityRow.world_id == world_id)
            regions = {region.id: region for region in await session.scalars(statement)}
            if not regions:
                raise ValidationFailedError("There is no region for the peoples to awaken in.")
            target = world_id or next(iter(regions.values())).world_id
            context = AwakenPeoplesContext(
                lore_language=scope.cosmos.lore_language,
                rules=rules,
                world_name=scope.cosmos.name,
                world_summary=await world_summary(scope),
                map=await geography_lines(scope, target),
                count=wanted,
                earlier=names,
            )
        try:
            output = await ask(
                runtime.model,
                rules,
                label=AgentRole.AWAKENING,
                system=(PromptId.AWAKEN_PEOPLES_SYSTEM, context),
                user=(PromptId.AWAKEN_PEOPLES_USER, context),
                output=AwakenPeoplesOutput,
                time_limit=rules.awakening.timeout,
            )
        except Exception:
            if not names:
                raise
            break
        async with runtime.database.write() as session:
            epoch = (await load_scope(session, rules)).epoch
            first = next(iter(regions.values()))
            for item in output.peoples[:wanted]:
                created = await awaken_one(session, rules, item, regions, first=first, epoch=epoch)
                names.append(created[0].name)
                ids.append(created[0].id)
    if names:
        runtime.note(f"Awakened peoples: {', '.join(names)}")
    return ids

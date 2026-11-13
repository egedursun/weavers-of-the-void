from collections.abc import Callable

from sqlalchemy import select

from aerona.agents.chronicler import backfill_epoch
from aerona.agents.creative import agent_creative_ports
from aerona.agents.deepener import deepen_entity, deepen_foreign_god
from aerona.agents.fate.naming import name_pending_records
from aerona.agents.genesis import GenesisRequest as AgentGenesisRequest
from aerona.agents.genesis import genesis
from aerona.agents.image_prompter import missing_cosmos_prompts, missing_image_prompts
from aerona.agents.runtime import AgentRuntime
from aerona.agents.summoner import complete_son_powers
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.node import NodeKind
from aerona.domain.models.genesis import GenesisOutcome
from aerona.epoch import retry
from aerona.rules.registry import Rules
from aerona.services.images.records import resolve_target
from aerona.services.lore_ports import GenesisRequest, LorePorts
from aerona.services.player.ports import CreativePorts


class AgentDeepener:
    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    async def deepen_entity(self, entity_id: int) -> None:
        await deepen_entity(self._runtime, entity_id)

    async def deepen_foreign_god(self, god_id: int) -> None:
        await deepen_foreign_god(self._runtime, god_id)


class AgentNamer:
    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    async def name_pending(self) -> int:
        return (await name_pending_records(self._runtime)).named


class AgentPromptWriter:
    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    async def _kinds(self, node_ids: list[int]) -> dict[int, NodeKind]:
        async with self._runtime.database.read() as session:
            rows = await session.execute(select(NodeRow.id, NodeRow.kind).where(NodeRow.id.in_(node_ids)))
            return {node_id: kind for node_id, kind in rows}

    async def write_prompt(self, node_id: int) -> str | None:
        await self.write_batch([node_id])
        async with self._runtime.database.read() as session:
            target = await resolve_target(session, node_id)
            return target.image_prompt

    async def write_batch(self, node_ids: list[int]) -> int:
        kinds = await self._kinds(node_ids)
        entities = [node_id for node_id in node_ids if kinds.get(node_id) is NodeKind.ENTITY]
        cosmic = [node_id for node_id in node_ids if node_id in kinds and kinds[node_id] is not NodeKind.ENTITY]
        written = await missing_image_prompts(self._runtime, len(entities), entities) if entities else 0
        if cosmic:
            written += await missing_cosmos_prompts(self._runtime, cosmic)
        return written


class AgentGenesisAuthor:
    def __init__(self, runtime: AgentRuntime, rules: Callable[[], Rules]) -> None:
        self._runtime = runtime
        self._rules = rules

    async def create(self, request: GenesisRequest) -> GenesisOutcome:
        order = AgentGenesisRequest(
            god_name=request.creator_name,
            seed_idea=request.seed,
            lore_language=request.lore_language,
            rng_seed=request.rng_seed,
            tone=request.tone,
            settings=request.settings,
            first_sons=request.first_sons,
        )
        return await genesis(self._runtime, order, self._rules())


class AgentPowerWriter:
    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    async def write_powers(self, son_id: int) -> None:
        await complete_son_powers(self._runtime, son_id)


class AgentNarrator:
    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    async def narrate(self, epoch: int) -> None:
        await backfill_epoch(self._runtime, epoch)


class AgentFateControls:
    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    async def retry_fate(self) -> dict[str, int]:
        return await retry.retry_fate(self._runtime)

    async def rejudge_debt(self) -> dict[str, int]:
        return await retry.rejudge_debt(self._runtime)

    async def rejudge_limbo(self) -> dict[str, int]:
        return await retry.rejudge_limbo(self._runtime)

    async def retry_voices(self) -> dict[str, int]:
        return await retry.retry_voices(self._runtime)

    async def retry_births(self) -> dict[str, int]:
        return await retry.retry_births(self._runtime)

    async def audit_chronicle(self, epoch: int) -> dict[str, int]:
        return await retry.audit_epoch_chronicle(self._runtime, epoch)


def agent_lore_ports(runtime: AgentRuntime, rules: Callable[[], Rules]) -> LorePorts:
    if not runtime.llm_enabled:
        return LorePorts()
    creative = agent_creative_ports(runtime)
    return LorePorts(
        deepener=AgentDeepener(runtime),
        namer=AgentNamer(runtime),
        prompts=AgentPromptWriter(runtime),
        genesis=AgentGenesisAuthor(runtime, rules),
        powers=AgentPowerWriter(runtime),
        narrator=AgentNarrator(runtime),
        awakener=creative.awakener,
        worlds=creative.worlds,
        revelations=creative.revelations,
        writer=creative.writer,
    )


def player_creative_ports(runtime: AgentRuntime) -> CreativePorts:
    if not runtime.llm_enabled:
        return CreativePorts()
    creative = agent_creative_ports(runtime)
    return CreativePorts(
        summoner=creative.summoner,
        revelations=creative.revelations,
        worlds=creative.worlds,
        awakener=creative.awakener,
        writer=creative.writer,
        fate=AgentFateControls(runtime),
        mortals=creative.mortals,
    )

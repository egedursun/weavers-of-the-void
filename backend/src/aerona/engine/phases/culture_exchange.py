from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import LexemeRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import AGENT_TYPES, COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw
from aerona.engine.context import TickContext
from aerona.engine.demography.tongues import tongue_link
from aerona.engine.economy.routes import link_weight, trade_links
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore.research import books_of, has_technique, masters
from aerona.engine.mind.hooks import converted
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.society_support.knowledge import KnowledgeHoldings, teach
from aerona.engine.primitives.faith import FaithIndex, change_religion, faith_dominance, faith_shares, worships_creator
from aerona.engine.primitives.knowledge import LawBook, times_of
from aerona.engine.primitives.numbers import scaled_cap
from aerona.engine.primitives.queries import BondIndex, canon, spoken_language
from aerona.language.titles import community_phrase

DIFFUSION_BOND_KINDS = (BondKind.ALLY, BondKind.RULES, BondKind.PAYS_TRIBUTE)
ITEM_SEPARATOR = "; "


@dataclass(frozen=True)
class Borrowing:
    word: str
    language_id: int


@dataclass(frozen=True)
class ContactRates:
    loanword: int
    tradition: int
    knowledge: int
    god: int


def contact_rates(ctx: TickContext, first_contact: bool) -> ContactRates:
    culture = ctx.rules.culture
    if first_contact:
        return ContactRates(culture.first_loanword_pct, culture.first_tradition_pct, culture.first_knowledge_pct, culture.first_god_pct)
    return ContactRates(culture.trade_loanword_pct, culture.trade_tradition_pct, culture.trade_knowledge_pct, culture.trade_god_pct)


async def _diffuse_direction(
    ctx: TickContext, source: EntityRow, target: EntityRow, holdings: KnowledgeHoldings, spread: list[int], *, cap: int, weight: float = 1.0
) -> None:
    if target.entity_type not in AGENT_TYPES:
        return
    settings = ctx.rules.knowledge
    rng = ctx.rng(f"diffusion.{source.id}.{target.id}")
    writing = times_of(ctx.rules.knowledge, holdings.branch_level(source.id, KnowledgeBranch.WRITING), settings.writing_diffusion_mult)
    chance = min(100.0, settings.diffusion_chance * writing * weight)
    written = await books_of(ctx.session, source.id)
    paper = ctx.rules.technique_effects.paper_pct if await has_technique(ctx.session, source.id, Technique.PAPER) else 0
    taught = ctx.rules.research.teacher_pct / PERCENT if await masters(ctx.session, ctx.rules, source.id) else 0.0
    for knowledge in holdings.known_by(source.id):
        if spread[0] >= cap or holdings.knows(target.id, knowledge.id):
            continue
        books = (ctx.rules.research.book_diffusion_pct + paper) / PERCENT if knowledge.id in written else 0.0
        if not rng.chance(min(100.0, chance * (1 + books + taught))):
            continue
        if await teach(ctx, target.id, knowledge, f"spread from {source.name}", holdings):
            spread[0] += 1
            await note(
                ctx,
                f"Knowledge of {knowledge.name} spread from {source.name} to {target.name}.",
                key="culture.knowledge_diffusion",
                ids=[source.id, target.id, knowledge.id],
                kind=ChronicleKind.KNOWLEDGE,
            )


async def _spread_language(ctx: TickContext, source: EntityRow, target: EntityRow, laws: LawBook) -> None:
    if not laws.has(NaturalLaw.ONE_LANGUAGE, target.world_id):
        return
    language = await spoken_language(ctx.session, source.id)
    if language is None or language.status is not EntityStatus.CANON:
        return
    bonds = BondRepository(ctx.session)
    if await bonds.exists_between(target.id, language.id, BondKind.SPEAKS):
        return
    if not ctx.rng(f"language.{target.id}").chance(ctx.rules.knowledge.language_spread_chance):
        return
    await bonds.connect(BondDraft(target.id, language.id, BondKind.SPEAKS, ctx.epoch, "spread"))
    await note(
        ctx,
        f"The {language.name} language spread among {target.name}.",
        key="culture.language_spread",
        ids=[target.id, language.id],
        kind=ChronicleKind.LANGUAGE,
    )


@reads(
    "knowledge.spread",
    "table.bonds",
    "table.book_contents",
    "table.epoch_year_cursors",
    "table.holder_techniques",
    "table.nodes",
    "table.people_biology",
    "table.people_culture",
    "table.skills",
    "table.speaker_cohorts",
    "table.trade_flows",
    "table.trade_route_profiles",
    "table.trade_route_regions",
    "table.trade_route_tolls",
)
@writes(
    "knowledge.spread",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
)
async def knowledge_diffusion(ctx: TickContext) -> None:
    session = ctx.session
    entities = {entity.id: entity for entity in await canon(session)}
    bonds = await BondIndex.load(session, DIFFUSION_BOND_KINDS)
    holdings = await KnowledgeHoldings.load(session)
    laws = await LawBook.load(session)
    spread = [0]
    settings = ctx.rules.knowledge
    cap = scaled_cap(
        settings.diffusion_cap, settings.diffusion_cap_community_divisor, sum(1 for item in entities.values() if item.entity_type in COMMUNITY_TYPES)
    )
    pairs = [(bond.source_node_id, bond.target_node_id, 1.0) for bond in sorted(bonds.bonds, key=lambda item: item.id)]
    pairs += [(link.first, link.second, link_weight(ctx, link)) for link in await trade_links(ctx)]
    for first_id, second_id, weight in pairs:
        first, second = entities.get(first_id), entities.get(second_id)
        if first is None or second is None:
            continue
        linked = weight * await tongue_link(session, ctx.rules, first_id, second_id)
        await _diffuse_direction(ctx, first, second, holdings, spread, cap=cap, weight=linked)
        await _diffuse_direction(ctx, second, first, holdings, spread, cap=cap, weight=linked)
        await _spread_language(ctx, first, second, laws)
    ctx.count("knowledge_spread", spread[0])


async def borrow_word(ctx: TickContext, lender: EntityRow, borrower: EntityRow) -> Borrowing | None:
    session = ctx.session
    lender_language = await spoken_language(session, lender.id)
    borrower_language = await spoken_language(session, borrower.id)
    if lender_language is None or borrower_language is None or lender_language.id == borrower_language.id:
        return None
    known = set(await session.scalars(select(LexemeRow.word_key).where(LexemeRow.language_entity_id == borrower_language.id)))
    lender_words = list(await session.scalars(select(LexemeRow).where(LexemeRow.language_entity_id == lender_language.id).order_by(LexemeRow.id)))
    candidates = [lexeme for lexeme in lender_words if lexeme.word_key not in known]
    if not candidates:
        return None
    chosen = ctx.rng(f"loanword.{lender.id}.{borrower.id}").pick(candidates)
    session.add(
        LexemeRow(
            language_entity_id=borrower_language.id,
            word=chosen.word,
            meaning=chosen.meaning,
            part_of_speech=chosen.part_of_speech,
            etymology=f"borrowed from the {lender_language.name} language",
            added_by_kind=ActorKind.ENGINE,
            added_by_node_id=borrower.id,
            epoch=ctx.epoch,
        )
    )
    await session.flush()
    return Borrowing(chosen.word, borrower_language.id)


async def _celebrated(ctx: TickContext, entity_id: int) -> list[EntityRow]:
    traditions: list[EntityRow] = []
    for bond in await BondRepository(ctx.session).outgoing(entity_id, BondKind.CELEBRATES):
        tradition = await ctx.session.get(EntityRow, bond.target_node_id)
        if tradition is not None and tradition.entity_type is EntityType.TRADITION and tradition.status is EntityStatus.CANON:
            traditions.append(tradition)
    return traditions


async def _pass_tradition(ctx: TickContext, source: EntityRow, target: EntityRow, rate: int) -> str | None:
    held = {tradition.id for tradition in await _celebrated(ctx, target.id)}
    offered = [tradition for tradition in await _celebrated(ctx, source.id) if tradition.id not in held]
    rng = ctx.rng(f"tradition.{source.id}.{target.id}")
    if not offered or not rng.chance(rate):
        return None
    tradition = rng.pick(offered)
    await BondRepository(ctx.session).connect(BondDraft(target.id, tradition.id, BondKind.CELEBRATES, ctx.epoch, f"passed from {source.name}"))
    return f"{target.name} adopted the {tradition.name} tradition"


async def _pass_knowledge(ctx: TickContext, source: EntityRow, target: EntityRow, rate: int, first_contact: bool) -> str | None:
    holdings = await KnowledgeHoldings.load(ctx.session)
    offered = [
        knowledge
        for knowledge in holdings.known_by(source.id)
        if not holdings.knows(target.id, knowledge.id) and (first_contact or knowledge.world_id == target.world_id)
    ]
    rng = ctx.rng(f"contact_knowledge.{source.id}.{target.id}")
    if not offered or not rng.chance(rate):
        return None
    knowledge = rng.pick(offered)
    if not await teach(ctx, target.id, knowledge, f"in contact with {source.name}", holdings):
        return None
    return f"the {knowledge.name} knowledge passed to {target.name}"


async def _pass_god(ctx: TickContext, source: EntityRow, target: EntityRow, rate: int) -> str | None:
    faith = await FaithIndex.load(ctx.session)
    god = faith.patron(source.id)
    if god is None or not faith.is_living_god(god) or god == faith.patron(target.id) or await worships_creator(ctx.session, target.id):
        return None
    if not ctx.rng(f"contact_god.{source.id}.{target.id}").chance(rate * faith_dominance(ctx.rules, god, await faith_shares(ctx.session))):
        return None
    syncretic = faith.has_living_god(target.id)
    if not await change_religion(ctx.session, target, god, ctx.epoch, f"contact with {source.name}", syncretic=syncretic, faith=faith):
        return None
    await converted(ctx, target.id, source.id, note=f"contact with {source.name}")
    name = faith.sons[god].name if god in faith.sons else "the Creator"
    return f"{target.name} began making offerings to {name} too" if syncretic else f"{target.name} began to worship {name}"


async def cultural_contact(ctx: TickContext, source: EntityRow, target: EntityRow, *, first_contact: bool = False) -> int:
    rates = contact_rates(ctx, first_contact)
    items: list[str] = []
    if ctx.rng(f"contact_word.{source.id}.{target.id}").chance(rates.loanword):
        borrowing = await borrow_word(ctx, source, target)
        if borrowing is not None:
            language = await ctx.session.get(EntityRow, borrowing.language_id)
            items.append(f'{language.name if language else target.name} borrowed the word "{borrowing.word}"')
    for outcome in (
        await _pass_tradition(ctx, source, target, rates.tradition),
        await _pass_knowledge(ctx, source, target, rates.knowledge, first_contact),
        await _pass_god(ctx, source, target, rates.god),
    ):
        if outcome is not None:
            items.append(outcome)
    if items:
        await note(
            ctx,
            f"Cultural exchange {community_phrase(source.entity_type, source.name)} and {community_phrase(target.entity_type, target.name)}: "
            f"{ITEM_SEPARATOR.join(items)}.",
            key="culture.contact",
            ids=[source.id, target.id],
            kind=ChronicleKind.CULTURE,
        )
    return len(items)


def _trading_communities(bond_entities: tuple[EntityRow | None, EntityRow | None]) -> tuple[EntityRow, EntityRow] | None:
    first, second = bond_entities
    if first is None or second is None or first.entity_type not in COMMUNITY_TYPES or second.entity_type not in COMMUNITY_TYPES:
        return None
    return first, second


@reads(
    "knowledge.spread",
    "table.bonds",
    "table.epoch_year_cursors",
    "table.lexemes",
    "table.nodes",
    "table.reverences",
    "table.trade_flows",
    "table.trade_route_profiles",
    "table.trade_route_regions",
    "table.trade_route_tolls",
)
@writes(
    "knowledge.spread",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.lexemes",
)
async def cultural_exchange(ctx: TickContext) -> None:
    culture = ctx.rules.culture
    entities: Mapping[int, EntityRow] = {entity.id: entity for entity in await canon(ctx.session, COMMUNITY_TYPES)}
    rng = ctx.rng("exchange")
    exchanges = 0
    for link in sorted(await trade_links(ctx), key=lambda item: (-item.volume, item.first, item.second)):
        if exchanges >= culture.exchange_cap:
            break
        pair = _trading_communities((entities.get(link.first), entities.get(link.second)))
        if pair is None or not rng.chance(min(100.0, culture.exchange_chance * link_weight(ctx, link))):
            continue
        source, target = pair if rng.chance(culture.exchange_direction_pct) else (pair[1], pair[0])
        if await cultural_contact(ctx, source, target) > 0:
            exchanges += 1
    ctx.count("exchanges", exchanges)


async def order_cultural_contact(ctx: TickContext, source_id: int, target_id: int, *, first_contact: bool = False) -> int:
    source = await ctx.session.get(EntityRow, source_id)
    target = await ctx.session.get(EntityRow, target_id)
    if source is None or target is None:
        raise NotFoundError("No such community.")
    if source.id == target.id or source.entity_type not in COMMUNITY_TYPES or target.entity_type not in COMMUNITY_TYPES:
        raise ValidationFailedError("Cultural contact joins two different communities.")
    if source.status is not EntityStatus.CANON or target.status is not EntityStatus.CANON:
        raise ValidationFailedError("Both communities must still be part of the world.")
    return await cultural_contact(ctx, source, target, first_contact=first_contact)


PHASES = (
    Phase("knowledge_diffusion", knowledge_diffusion),
    Phase("cultural_exchange", cultural_exchange),
)

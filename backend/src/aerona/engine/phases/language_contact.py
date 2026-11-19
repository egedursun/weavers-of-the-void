from collections.abc import Mapping
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.write_guard import held, unheld
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import PartOfSpeech
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.tongues import LanguageStage
from aerona.domain.models.entity_stats import LanguageStats
from aerona.engine.context import TickContext
from aerona.engine.economy.routes import link_weight, trade_links
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.first_bonds import store_words
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.language_profile import has_script, language_profile
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import clamp_int, scaled_cap
from aerona.engine.primitives.queries import active_bonds, canon, close, connect, living_entity
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.primitives.stats import headcount, set_stats, stat, stat_or
from aerona.engine.recording.record import RoleValue
from aerona.engine.recording.record import record as record_incident
from aerona.engine.tongues.grammar import loan_factor, simplify
from aerona.engine.tongues.loans import adapted
from aerona.language.lexicon import LexiconEntry
from aerona.rules.registry import Rules

POPULATED = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})
CREOLE_SUBTYPE = "creole"
MINIMUM_BILINGUAL = 2
HALF = 0.5


@dataclass
class ContactTally:
    events: int = 0
    loans_left: int = 0
    borrowed: int = 0
    creoles: int = 0
    event_cap: int = 0
    creole_cap: int = 0
    words: dict[int, set[str]] = field(default_factory=dict)


async def spoken(session: AsyncSession, speaker_id: int) -> list[EntityRow]:
    statement = (
        select(EntityRow)
        .join(BondRow, BondRow.target_node_id == EntityRow.id)
        .where(
            BondRow.source_node_id == speaker_id,
            BondRow.kind == BondKind.SPEAKS,
            BondRow.state == BondState.ACTIVE,
            EntityRow.entity_type == EntityType.LANGUAGE,
            EntityRow.status.in_([EntityStatus.CANON, EntityStatus.DEAD]),
        )
        .order_by(BondRow.id)
    )
    return list((await session.scalars(statement)).unique())


async def mother_tongue(session: AsyncSession, speaker_id: int) -> EntityRow | None:
    languages = await spoken(session, speaker_id)
    return languages[-1] if languages else None


async def speaks(session: AsyncSession, speaker_id: int, language_id: int) -> bool:
    return any(item.id == language_id for item in await spoken(session, speaker_id))


async def known_words(ctx: TickContext, tally: ContactTally, language_id: int) -> set[str]:
    if language_id not in tally.words:
        tally.words[language_id] = set(await ctx.session.scalars(select(LexemeRow.word_key).where(LexemeRow.language_entity_id == language_id)))
    return tally.words[language_id]


async def borrow(ctx: TickContext, tally: ContactTally, lender: EntityRow, borrower: EntityRow, speaker_id: int, *, count: int) -> int:
    if lender.id == borrower.id or tally.loans_left <= 0 or count <= 0:
        return 0
    have = await known_words(ctx, tally, borrower.id)
    rows = list(await ctx.session.scalars(select(LexemeRow).where(LexemeRow.language_entity_id == lender.id).order_by(LexemeRow.id)))
    candidates = [row for row in rows if row.word_key not in have]
    rng = ctx.rng(f"loan.{lender.id}.{borrower.id}")
    count = max(1, round(count * await loan_factor(ctx.session, ctx.rules, borrower.id)))
    taken = 0
    while candidates and taken < count and tally.loans_left > 0:
        row = candidates.pop(rng.below(len(candidates)))
        form = await adapted(ctx.session, row.word, borrower.id)
        entry = entry_of(row, f"borrowed from the {lender.name} language, where it is {row.word}").model_copy(update={"word": form})
        if await store_words(ctx, borrower, [entry], speaker_id):
            have.add(row.word_key)
            taken += 1
            tally.loans_left -= 1
    tally.borrowed += taken
    return taken


def entry_of(row: LexemeRow, origin: str) -> LexiconEntry:
    return LexiconEntry(word=row.word, meaning=row.meaning, part_of_speech=row.part_of_speech or PartOfSpeech.NOUN, origin=origin)


async def learn(ctx: TickContext, speaker: EntityRow, language: EntityRow, reason: str) -> bool:
    if await speaks(ctx.session, speaker.id, language.id):
        return False
    await connect(ctx.session, speaker.id, language.id, BondKind.SPEAKS, ctx.epoch, description=reason)
    return True


async def drop(ctx: TickContext, speaker: EntityRow, language: EntityRow, reason: str) -> bool:
    if len(await spoken(ctx.session, speaker.id)) < MINIMUM_BILINGUAL:
        return False
    for bond in await active_bonds(ctx.session, [BondKind.SPEAKS], sources=[speaker.id], targets=[language.id]):
        await close(ctx.session, bond, ctx.epoch, reason)
    return True


async def tell(ctx: TickContext, tally: ContactTally, key: str, roles: Mapping[IncidentRole, RoleValue]) -> None:
    tally.events += 1
    await record_incident(ctx, f"language_contact.{key}", roles=roles)


async def communities_pair(session: AsyncSession, bond: BondRow) -> tuple[EntityRow, EntityRow] | None:
    first, second = await living_entity(session, bond.source_node_id), await living_entity(session, bond.target_node_id)
    if first is None or second is None or first.entity_type not in COMMUNITY_TYPES or second.entity_type not in COMMUNITY_TYPES:
        return None
    return first, second


async def conquest_contact(ctx: TickContext, tally: ContactTally) -> None:
    table = ctx.rules.language_contact
    for bond in ctx.rng("conquest.order").shuffled(sorted(await active_bonds(ctx.session, [BondKind.RULES]), key=lambda item: item.id)):
        if tally.events >= tally.event_cap:
            return
        pair = await communities_pair(ctx.session, bond)
        if pair is None:
            continue
        ruler, ruled = pair
        ruler_tongue, own = await mother_tongue(ctx.session, ruler.id), await mother_tongue(ctx.session, ruled.id)
        if ruler_tongue is None or own is None or ruler_tongue.id == own.id:
            continue
        rng = ctx.rng(f"conquest.{ruler.id}.{ruled.id}")
        if not await speaks(ctx.session, ruled.id, ruler_tongue.id):
            if rng.chance(table.conquest_bilingual_chance) and await learn(ctx, ruled, ruler_tongue, f"learned under the rule of {ruler.name}"):
                await borrow(ctx, tally, ruler_tongue, own, ruled.id, count=table.contact_words)
                await tell(
                    ctx, tally, "conquest_bilingual", {IncidentRole.LEARNER: ruled.id, IncidentRole.AUTHORITY: ruler.id, IncidentRole.SUBJECT: ruler_tongue.id}
                )
            continue
        native = next((item for item in await spoken(ctx.session, ruled.id) if item.id != ruler_tongue.id), None)
        if native is not None and rng.chance(table.conquest_shift_chance) and await drop(ctx, ruled, native, "language shift"):
            await tell(ctx, tally, "shift", {IncidentRole.SUBJECT: ruled.id, IncidentRole.PREDECESSOR: native.id, IncidentRole.SUCCESSOR: ruler_tongue.id})


async def migration_contact(ctx: TickContext, tally: ContactTally) -> None:
    table = ctx.rules.language_contact
    statement = select(BondRow).where(BondRow.kind == BondKind.MIGRATED_TO, BondRow.epoch >= ctx.epoch - table.migration_window).order_by(BondRow.id)
    communities = await canon(ctx.session, COMMUNITY_TYPES)
    for bond in ctx.rng("migration.order").shuffled(await ctx.session.scalars(statement)):
        if tally.events >= tally.event_cap:
            return
        migrants = await living_entity(ctx.session, bond.target_node_id)
        if migrants is None or migrants.entity_type not in COMMUNITY_TYPES or migrants.location_id is None:
            continue
        own = await mother_tongue(ctx.session, migrants.id)
        neighbour_tongue: EntityRow | None = None
        neighbour: EntityRow | None = None
        for other in communities:
            if other.id == migrants.id or migrants.location_id not in (other.location_id, other.id):
                continue
            tongue = await mother_tongue(ctx.session, other.id)
            if tongue is not None and (own is None or tongue.id != own.id):
                neighbour, neighbour_tongue = other, tongue
                break
        if neighbour is None or neighbour_tongue is None or not ctx.rng(f"migration.{migrants.id}").chance(table.migration_bilingual_chance):
            continue
        if not await learn(ctx, migrants, neighbour_tongue, f"learned as neighbours of {neighbour.name}"):
            continue
        if own is not None:
            await borrow(ctx, tally, neighbour_tongue, own, migrants.id, count=table.contact_words)
        await tell(
            ctx,
            tally,
            "migration_bilingual",
            {IncidentRole.LEARNER: migrants.id, IncidentRole.TEACHER: neighbour.id, IncidentRole.SUBJECT: neighbour_tongue.id},
        )


async def trade_contact(ctx: TickContext, tally: ContactTally) -> None:
    table = ctx.rules.language_contact
    borrowed_before = tally.borrowed
    tongues: dict[int, None] = {}
    for link in sorted(await trade_links(ctx), key=lambda item: (-item.volume, item.first, item.second)):
        if tally.loans_left <= 0:
            break
        if held(link.first, link.second):
            continue
        rng = ctx.rng(f"trade.{link.first}.{link.second}")
        if not rng.chance(min(100.0, table.trade_loan_chance * link_weight(ctx, link))):
            continue
        first, second = await living_entity(ctx.session, link.first), await living_entity(ctx.session, link.second)
        if first is None or second is None:
            continue
        lender, borrower = (first, second) if rng.random() < HALF else (second, first)
        lender_tongue, borrower_tongue = await mother_tongue(ctx.session, lender.id), await mother_tongue(ctx.session, borrower.id)
        if lender_tongue is None or borrower_tongue is None or lender_tongue.id == borrower_tongue.id:
            continue
        await borrow(ctx, tally, lender_tongue, borrower_tongue, borrower.id, count=table.contact_words)
        tongues.update(dict.fromkeys((lender_tongue.id, borrower_tongue.id)))
        if tally.events >= tally.event_cap or first.entity_type not in COMMUNITY_TYPES or second.entity_type not in COMMUNITY_TYPES:
            continue
        if not rng.chance(table.trade_bilingual_chance):
            continue
        small, large = (first, second) if headcount(first) <= headcount(second) else (second, first)
        large_tongue = await mother_tongue(ctx.session, large.id)
        if large_tongue is not None and await learn(ctx, small, large_tongue, f"learned in trade with {large.name}"):
            await tell(ctx, tally, "trade_bilingual", {IncidentRole.LEARNER: small.id, IncidentRole.TEACHER: large.id, IncidentRole.SUBJECT: large_tongue.id})
    if tally.borrowed > borrowed_before:
        await record_incident(ctx, "language_contact.loans", roles={IncidentRole.SUBJECT: tuple(tongues)}, facts={"words": tally.borrowed - borrowed_before})


async def plague_contact(ctx: TickContext, tally: ContactTally) -> None:
    table = ctx.rules.language_contact
    statement = select(EntityRow.location_id).where(EntityRow.engine_kind == EngineKind.PLAGUE, EntityRow.birth_epoch == ctx.epoch)
    places = {item for item in await ctx.session.scalars(statement) if item is not None}
    if not places:
        return
    for community in await canon(ctx.session, COMMUNITY_TYPES):
        if community.id not in places and community.location_id not in places:
            continue
        tongues = await spoken(ctx.session, community.id)
        if len(tongues) >= MINIMUM_BILINGUAL:
            minority = min(tongues, key=lambda item: (stat_or(item, "spread", 0), item.id))
            if (
                tally.events < tally.event_cap
                and ctx.rng(f"plague.{community.id}").chance(table.plague_shift_chance)
                and await drop(ctx, community, minority, "plague")
            ):
                await tell(ctx, tally, "plague_shift", {IncidentRole.SUBJECT: community.id, IncidentRole.PREDECESSOR: minority.id})
        elif tongues:
            set_stats(tongues[0], spread=clamp_int(stat_or(tongues[0], "spread", 0) - table.plague_spread_loss, 0, PERCENT))


async def birth_creole(ctx: TickContext, community: EntityRow, first: EntityRow, second: EntityRow, by: str | None = None) -> EntityRow:
    table = ctx.rules.language_contact
    complexity = min(stat_or(first, "complexity", table.complexity_base), stat_or(second, "complexity", table.complexity_base))
    spread = round((stat_or(first, "spread", 0) + stat_or(second, "spread", 0)) / MINIMUM_BILINGUAL / MINIMUM_BILINGUAL)
    how = f"by the hand of {by}" if by else "over the generations"
    creole = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.LANGUAGE,
            name=f"{community.name} Creole",
            body=f"Among {community.name}, {first.name} and {second.name} mixed {how}, and a new tongue was born from the two.",
            stats=LanguageStats(spread=spread, complexity=complexity, sacredness=0),
            power=table.creole_power,
            world_id=community.world_id,
            subtype=CREOLE_SUBTYPE,
        ),
    )
    profile = await language_profile(ctx.session, creole, first.id)
    profile.stage = LanguageStage.CREOLE
    await simplify(ctx.session, ctx.rules, creole.id, ctx.epoch)
    for parent in (first, second):
        await connect(ctx.session, creole.id, parent.id, BondKind.DESCENDS_FROM, ctx.epoch, description=CREOLE_SUBTYPE)
        rows = list(await ctx.session.scalars(select(LexemeRow).where(LexemeRow.language_entity_id == parent.id).order_by(LexemeRow.id)))
        rng = ctx.rng(f"creole.{creole.id}.{parent.id}")
        rng.shuffle(rows)
        entries = [entry_of(row, f"from {parent.name} (creole)") for row in rows[: table.creole_words]]
        await store_words(ctx, creole, entries, community.id)
        for bond in await active_bonds(ctx.session, [BondKind.SPEAKS], sources=[community.id], targets=[parent.id]):
            await close(ctx.session, bond, ctx.epoch, CREOLE_SUBTYPE)
    await connect(ctx.session, community.id, creole.id, BondKind.SPEAKS, ctx.epoch, description=CREOLE_SUBTYPE)
    return creole


async def creole_round(ctx: TickContext, tally: ContactTally) -> None:
    table = ctx.rules.language_contact
    for community in ctx.rng("creole.order").shuffled(unheld(await canon(ctx.session, COMMUNITY_TYPES))):
        if tally.creoles >= tally.creole_cap or tally.events >= tally.event_cap:
            return
        bonds = sorted(await active_bonds(ctx.session, [BondKind.SPEAKS], sources=[community.id]), key=lambda item: item.id)
        if len(bonds) < MINIMUM_BILINGUAL or ctx.epoch - max(bond.epoch for bond in bonds) < table.creole_epochs:
            continue
        if not ctx.rng(f"creole.{community.id}").chance(table.creole_chance):
            continue
        first, second = await living_language(ctx.session, bonds[0].target_node_id), await living_language(ctx.session, bonds[-1].target_node_id)
        if first is None or second is None or first.id == second.id:
            continue
        creole = await birth_creole(ctx, community, first, second)
        tally.creoles += 1
        await tell(ctx, tally, "creole", {IncidentRole.SUBJECT: community.id, IncidentRole.PARENT: [first.id, second.id], IncidentRole.PRODUCT: creole.id})


async def living_language(session: AsyncSession, language_id: int) -> EntityRow | None:
    language = await session.get(EntityRow, language_id)
    return language if language is not None and language.entity_type is EntityType.LANGUAGE and language.status is not EntityStatus.REJECTED else None


def drifted(current: int | None, target: float, step: int) -> int:
    value = target if current is None else current
    return clamp_int(value + max(-step, min(step, target - value)), 0, PERCENT)


async def language_stats(ctx: TickContext) -> int:
    table = ctx.rules.language_contact
    knowledge = await KnowledgeMap.load(ctx.session)
    populations: dict[int, int] = {}
    for community in await canon(ctx.session, POPULATED):
        populations[community.world_id] = populations.get(community.world_id, 0) + headcount(community)
    changed = 0
    for language in await canon(ctx.session, [EntityType.LANGUAGE]):
        speakers = [
            item
            for item in [
                await living_entity(ctx.session, bond.source_node_id) for bond in await active_bonds(ctx.session, [BondKind.SPEAKS], targets=[language.id])
            ]
            if item is not None
        ]
        if not speakers:
            continue
        share = sum(headcount(item) for item in speakers if item.entity_type in POPULATED) / max(1, populations.get(language.world_id, 0))
        words = int(await ctx.session.scalar(select(func.count()).select_from(LexemeRow).where(LexemeRow.language_entity_id == language.id)) or 0)
        written = await has_script(ctx.session, language.id) or any(knowledge.knows(item.id, KnowledgeBranch.WRITING) for item in speakers)
        piety = sum(stat_or(item, "piety", table.default_piety) for item in speakers) / len(speakers)
        cults = sum(1 for item in speakers if item.entity_type is EntityType.CULT)
        targets = {
            "spread": share * table.spread_mult_pct,
            "complexity": table.complexity_base
            + min(table.complexity_word_cap, words / table.complexity_word_divisor)
            + (table.complexity_writing if written else 0),
            "sacredness": piety * table.sacredness_piety_pct / PERCENT + min(table.sacredness_cult_cap, cults * table.sacredness_cult),
        }
        update = {key: drifted(stat(language, key), min(PERCENT, value), table.stat_step) for key, value in targets.items()}
        if set_stats(language, **update):
            changed += 1
    return changed


@reads(
    "language.complexity",
    "language.sacredness",
    "language.spread",
    "people.piety",
    "people.population",
    "settlement.piety",
    "settlement.population",
    "table.bonds",
    "table.entities",
    "table.holder_levels",
    "table.language_profiles",
    "table.lexemes",
    "table.name_registry",
    "table.nodes",
    "table.polity_profiles",
    "table.trade_flows",
    "table.trade_route_profiles",
    "table.trade_route_regions",
    "table.trade_route_tolls",
    "trade_route.culture",
)
@writes(
    "language.complexity",
    "language.sacredness",
    "language.spread",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_participants",
    "table.incidents",
    "table.language_profiles",
    "table.lexemes",
    "table.name_registry",
)
async def language_contact(ctx: TickContext) -> None:
    table = ctx.rules.language_contact
    communities = len(await canon(ctx.session, COMMUNITY_TYPES))
    tally = ContactTally(
        loans_left=table.loan_cap + table.loan_words_per_community * communities,
        event_cap=scaled_cap(table.event_cap, table.event_communities_per_extra, communities),
        creole_cap=scaled_cap(table.creole_cap, table.creole_communities_per_extra, communities),
    )
    await conquest_contact(ctx, tally)
    await migration_contact(ctx, tally)
    await trade_contact(ctx, tally)
    await plague_contact(ctx, tally)
    await creole_round(ctx, tally)
    ctx.count("events", tally.events)
    ctx.count("borrowed", tally.borrowed)
    ctx.count("creoles", tally.creoles)
    ctx.count("stats", await language_stats(ctx))


async def order_creole(session: AsyncSession, rules: Rules, community_id: int) -> EntityRow:
    community = await living_entity(session, community_id)
    if community is None:
        raise ValidationFailedError("This record is not in the world.")
    bonds = sorted(await active_bonds(session, [BondKind.SPEAKS], sources=[community.id]), key=lambda item: item.id)
    if len(bonds) < MINIMUM_BILINGUAL:
        raise ValidationFailedError(f"{community.name} does not speak two languages; teach it a second tongue first.")
    first, second = await living_language(session, bonds[0].target_node_id), await living_language(session, bonds[-1].target_node_id)
    if first is None or second is None or first.id == second.id:
        raise ValidationFailedError(f"{community.name} does not speak two distinct languages.")
    ctx = await manual_context(session, "creole", rules, key=str(community_id))
    creole = await birth_creole(ctx, community, first, second, by="the Creator")
    await record_incident(
        ctx,
        "language_contact.creator_creole",
        roles={IncidentRole.SUBJECT: community.id, IncidentRole.PARENT: [first.id, second.id], IncidentRole.PRODUCT: creole.id},
    )
    return creole


async def run_language_contact(session: AsyncSession, rules: Rules) -> None:
    await language_contact(await manual_context(session, "language_contact", rules))


PHASES = (Phase("language_contact", language_contact),)

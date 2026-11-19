from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.write_guard import unheld
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.entity_stats import LanguageStats
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.first_bonds import store_words
from aerona.engine.primitives.language_profile import language_profile
from aerona.engine.primitives.numbers import scaled_cap
from aerona.engine.primitives.queries import BondIndex, active_bonds, canon, close, connect, living_entity, spoken_language
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.recording.record import record as record_incident
from aerona.engine.tongues.sounds import inherit
from aerona.language.dialect import dialect_should_split, plan_engine_dialect
from aerona.language.lexicon import LexiconEntry

CONTACT_KINDS = (BondKind.TRADES_WITH, BondKind.RULES, BondKind.ALLY, BondKind.PAYS_TRIBUTE)
DIALECT_SUBTYPE = "dialect"
HOMELAND_TYPES = (EntityType.PEOPLE, EntityType.SETTLEMENT)


async def lexicon_of(ctx: TickContext, language: EntityRow) -> list[LexiconEntry]:
    rows = await ctx.session.scalars(select(LexemeRow).where(LexemeRow.language_entity_id == language.id).order_by(LexemeRow.id))
    return [LexiconEntry(word=row.word, meaning=row.meaning, part_of_speech=row.part_of_speech) for row in rows if row.part_of_speech is not None]


async def found_dialect(ctx: TickContext, settlement: EntityRow, parent: EntityRow) -> EntityRow:
    rng = ctx.rng(f"dialect.{settlement.id}")
    plan = plan_engine_dialect(parent.name, settlement.name, await lexicon_of(ctx, parent), rng.random, ctx.rules)
    dialect = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.LANGUAGE,
            name=plan.name,
            body=plan.description,
            stats=LanguageStats(spread=plan.spread, complexity=plan.complexity, sacredness=plan.sacredness),
            power=plan.power,
            world_id=settlement.world_id,
            subtype=DIALECT_SUBTYPE,
            engine_kind=EngineKind.DIALECT,
        ),
    )
    await language_profile(ctx.session, dialect, parent.id)
    await connect(ctx.session, dialect.id, parent.id, BondKind.DESCENDS_FROM, ctx.epoch, description="dialect")
    for bond in await active_bonds(ctx.session, [BondKind.SPEAKS], sources=[settlement.id], targets=[parent.id]):
        await close(ctx.session, bond, ctx.epoch, "dialect")
    await connect(ctx.session, settlement.id, dialect.id, BondKind.SPEAKS, ctx.epoch, description="dialect")
    await store_words(ctx, dialect, plan.inherited_words, settlement.id)
    await inherit(ctx, parent.id, dialect.id)
    await record_incident(
        ctx,
        "dialects.split",
        roles={IncidentRole.SUBJECT: settlement.id, IncidentRole.PREDECESSOR: parent.id, IncidentRole.PRODUCT: dialect.id},
        facts={"words": len(plan.inherited_words)},
        place=settlement.id,
    )
    return dialect


@reads("table.bonds", "table.entities", "table.language_profiles", "table.lexemes", "table.name_registry", "table.nodes", "table.world_maps")
@writes(
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
async def dialect_divergence(ctx: TickContext) -> None:
    rules = ctx.rules
    rng = ctx.rng()
    atlas = await RegionAtlas.load(ctx.session)
    contacts = await BondIndex.load(ctx.session, CONTACT_KINDS)
    founded = 0
    settlements = unheld(await canon(ctx.session, [EntityType.SETTLEMENT]))
    cap = scaled_cap(rules.world_effects.dialect_cap, rules.world_effects.dialect_cap_settlement_divisor, len(settlements))
    for settlement in ctx.rng("order").shuffled(settlements):
        if founded >= cap:
            return
        if settlement.status is not EntityStatus.CANON:
            continue
        language = await spoken_language(ctx.session, settlement.id)
        if language is None or language.status is not EntityStatus.CANON:
            continue
        homeland = []
        for bond in await active_bonds(ctx.session, [BondKind.SPEAKS], targets=[language.id]):
            member = await living_entity(ctx.session, bond.source_node_id)
            if member is not None and member.id != settlement.id and member.entity_type in HOMELAND_TYPES:
                homeland.append(member)
        in_contact = any(
            atlas.same_region(settlement.id, member.id) or any(contacts.between(settlement.id, member.id, kind) for kind in CONTACT_KINDS)
            for member in homeland
        )
        if not dialect_should_split(ctx.epoch - settlement.birth_epoch, len(homeland), in_contact, rng.random, rules):
            continue
        await found_dialect(ctx, settlement, language)
        founded += 1


PHASES = (Phase("dialect_divergence", dialect_divergence),)

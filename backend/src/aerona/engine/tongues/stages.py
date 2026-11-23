from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.repositories.lexicon import add_lexeme
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.tongues import LanguageGrammarRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.tongues import LanguageStage, MorphologyType, NumberSystem, WordOrder, WordRegister
from aerona.domain.models.entity_stats import LanguageStats
from aerona.engine.context import TickContext
from aerona.engine.primitives.language_profile import language_profile
from aerona.engine.primitives.queries import active_bonds, close, connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.recording.record import record

REGULAR = {
    "word_order": WordOrder.SVO,
    "morphology": MorphologyType.AGGLUTINATIVE,
    "cases": 0,
    "noun_classes": 0,
    "evidentiality": False,
    "honorific_levels": 0,
    "number_system": NumberSystem.SINGULAR_PLURAL,
}


async def regular_grammar(ctx: TickContext, language_id: int) -> LanguageGrammarRow:
    row = await ctx.session.get(LanguageGrammarRow, language_id)
    if row is None:
        row = LanguageGrammarRow(language_entity_id=language_id, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    for key, value in REGULAR.items():
        if key not in row.locked:
            setattr(row, key, value)
    row.updated_epoch = ctx.epoch
    return row


async def made_tongue(ctx: TickContext, language: EntityRow, maker_id: int | None) -> LanguageProfileRow:
    profile = await language_profile(ctx.session, language)
    profile.stage = LanguageStage.CONSTRUCTED
    profile.parent_language_id = None
    await regular_grammar(ctx, language.id)
    roles = {IncidentRole.PRODUCT: language.id}
    if maker_id is not None:
        roles[IncidentRole.ACTOR] = maker_id
    await record(ctx, "language.constructed", roles=roles)
    await ctx.session.flush()
    return profile


async def revived_tongue(ctx: TickContext, dead: EntityRow, community: EntityRow) -> EntityRow:
    name = await NameRepository(ctx.session).unique_name(f"{dead.name} Restored")
    language = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.LANGUAGE,
            name=name,
            body=f"{dead.name}, spoken again by {community.name}, its old forms kept and new words added.",
            stats=LanguageStats(spread=0, complexity=PERCENT // 2, sacredness=0),
            power=max(1, community.power_level // 2),
            world_id=community.world_id,
        ),
    )
    profile = await language_profile(ctx.session, language, dead.id)
    old = await ctx.session.get(LanguageProfileRow, dead.id)
    profile.stage = LanguageStage.REVIVED
    if old is not None:
        profile.numeral_base, profile.modality, profile.writing_system, profile.script_id = old.numeral_base, old.modality, old.writing_system, old.script_id
    for word in list(await ctx.session.scalars(select(LexemeRow).where(LexemeRow.language_entity_id == dead.id).order_by(LexemeRow.id))):
        await add_lexeme(
            ctx.session,
            LexemeRow(
                language_entity_id=language.id,
                word=word.word,
                meaning=word.meaning,
                part_of_speech=word.part_of_speech,
                etymology=f"kept from {dead.name}",
                added_by_kind=ActorKind.ENGINE,
                added_by_node_id=None,
                epoch=ctx.epoch,
                register=WordRegister.COMMON if word.register is WordRegister.ARCHAIC else word.register,
            ),
        )
    for bond in await active_bonds(ctx.session, [BondKind.SPEAKS], sources=[community.id], targets=[dead.id]):
        await close(ctx.session, bond, ctx.epoch, "speaks it restored")
    await connect(ctx.session, language.id, dead.id, BondKind.DESCENDS_FROM, ctx.epoch, description="restored")
    await connect(ctx.session, community.id, language.id, BondKind.SPEAKS, ctx.epoch, description="restored")
    await record(ctx, "language.revived", roles={IncidentRole.PRODUCT: language.id, IncidentRole.PREDECESSOR: dead.id, IncidentRole.LEARNER: community.id})
    await ctx.session.flush()
    return language

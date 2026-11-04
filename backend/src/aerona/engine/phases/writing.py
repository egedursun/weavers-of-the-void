from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.language_profile import has_script, language_profile
from aerona.engine.primitives.queries import active_bonds, canon, living_entity
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import set_stats, stat
from aerona.language.writing import ScriptChoiceInputs, choose_writing_system, complexity_after_script, script_note


async def adopt_script(ctx: TickContext, language: EntityRow, writer: EntityRow, system: WritingSystem) -> None:
    profile = await language_profile(ctx.session, language)
    profile.writing_system = system
    profile.script_epoch = ctx.epoch
    set_stats(language, complexity=complexity_after_script(stat(language, "complexity"), ctx.rules))
    await note(ctx, script_note(writer.name, language.name, system), key="writing.script", ids=[writer.id, language.id])


@reads(
    "language.complexity",
    "language.sacredness",
    "table.bonds",
    "table.community_societies",
    "table.epoch_year_cursors",
    "table.holder_levels",
    "table.language_profiles",
)
@writes(
    "language.complexity",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.language_profiles",
)
async def writing_systems(ctx: TickContext) -> None:
    rules = ctx.rules
    rng = ctx.rng()
    knowledge = await KnowledgeMap.load(ctx.session)
    for language in await canon(ctx.session, [EntityType.LANGUAGE]):
        if await has_script(ctx.session, language.id):
            continue
        writer: EntityRow | None = None
        for bond in await active_bonds(ctx.session, [BondKind.SPEAKS], targets=[language.id]):
            speaker = await living_entity(ctx.session, bond.source_node_id)
            if speaker is not None and knowledge.knows(speaker.id, KnowledgeBranch.WRITING):
                writer = speaker
                break
        if writer is None or not rng.chance(rules.deep_world.script_chance):
            continue
        shares = await class_shares(ctx.session, rules, writer.id)
        inputs = ScriptChoiceInputs(
            merchant_share=shares[SocialClass.MERCHANT],
            farmer_share=shares[SocialClass.FARMER],
            priest_share=shares[SocialClass.PRIEST],
            complexity=stat(language, "complexity") or 0,
            sacredness=stat(language, "sacredness") or 0,
        )
        await adopt_script(ctx, language, writer, choose_writing_system(inputs, rng.random, rules))


PHASES = (Phase("writing_systems", writing_systems),)

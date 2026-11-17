from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held, unheld
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.tongues import ScriptChangeCause
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.language_profile import has_script, language_profile
from aerona.engine.primitives.queries import active_bonds, canon, living_entity
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.recording.record import record as record_incident
from aerona.engine.tongues.modality import writable
from aerona.engine.tongues.scripts import record_script
from aerona.language.writing import ScriptChoiceInputs, choose_writing_system, complexity_after_script


async def adopt_script(ctx: TickContext, language: EntityRow, writer: EntityRow, system: WritingSystem) -> None:
    profile = await language_profile(ctx.session, language)
    await record_script(ctx, language, profile, system, cause=ScriptChangeCause.INVENTION)
    set_stats(language, complexity=complexity_after_script(stat(language, "complexity"), ctx.rules))
    await record_incident(ctx, "writing.script", roles={IncidentRole.MAKER: writer.id, IncidentRole.SUBJECT: language.id}, facts={"system": system})


@reads(
    "language.complexity",
    "language.sacredness",
    "table.bonds",
    "table.community_societies",
    "table.entities",
    "table.holder_levels",
    "table.incident_participants",
    "table.incidents",
    "table.language_profiles",
    "table.nodes",
)
@writes(
    "language.complexity",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.language_profiles",
    "table.scripts",
)
async def writing_systems(ctx: TickContext) -> None:
    rules = ctx.rules
    rng = ctx.rng()
    knowledge = await KnowledgeMap.load(ctx.session)
    for language in unheld(await canon(ctx.session, [EntityType.LANGUAGE])):
        if await has_script(ctx.session, language.id) or not await writable(ctx.session, language.id):
            continue
        writer: EntityRow | None = None
        for bond in await active_bonds(ctx.session, [BondKind.SPEAKS], targets=[language.id]):
            speaker = await living_entity(ctx.session, bond.source_node_id)
            if speaker is not None and not held(speaker.id) and knowledge.knows(speaker.id, KnowledgeBranch.WRITING):
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

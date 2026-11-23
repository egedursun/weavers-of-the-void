from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.tongues import SCRIPT_CHAIN, SCRIPT_SIGNS, WRITABLE
from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.constants.units import PERCENT
from aerona.db.tables.culture import LanguageStandingRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.tongues import DivineTongueRow, LanguagePolicyRow, ScriptRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.tongues import LanguagePolicy, ScriptChangeCause
from aerona.engine.context import TickContext
from aerona.engine.lore.language import speakers, standardisation_of
from aerona.engine.primitives.language_profile import language_profile
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import canon, has_flag, spoken_language
from aerona.engine.primitives.society import class_shares
from aerona.engine.recording.record import record as record_incident
from aerona.engine.tongues.policy import communities_under
from aerona.engine.tongues.sounds import contacts_of


@dataclass
class ScriptTally:
    recorded: int = 0
    evolved: int = 0
    borrowed: int = 0
    imposed: int = 0
    revealed: int = 0


def script_name(language: EntityRow, system: WritingSystem) -> str:
    return f"{language.name} {system.value}"[:NAME_MAX_LENGTH]


async def record_script(
    ctx: TickContext,
    language: EntityRow,
    profile: LanguageProfileRow,
    system: WritingSystem,
    *,
    cause: ScriptChangeCause,
    parent: ScriptRow | None = None,
    extra_signs: int = 0,
) -> ScriptRow:
    row = ScriptRow(
        name=script_name(language, system),
        system=system,
        parent_script_id=parent.id if parent is not None else None,
        origin_language_id=language.id,
        signs=(parent.signs if parent is not None and parent.system is system else SCRIPT_SIGNS[system]) + extra_signs,
        cause=cause,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    profile.script_id, profile.writing_system, profile.script_epoch = row.id, system, ctx.epoch
    return row


async def script_of(ctx: TickContext, language: EntityRow, profile: LanguageProfileRow) -> ScriptRow | None:
    if profile.script_id is not None:
        found = await ctx.session.get(ScriptRow, profile.script_id)
        if found is not None:
            return found
    if profile.writing_system is None:
        return None
    return await record_script(ctx, language, profile, profile.writing_system, cause=ScriptChangeCause.INVENTION)


async def merchant_share(ctx: TickContext, language_id: int) -> float:
    shares = [(await class_shares(ctx.session, ctx.rules, community))[SocialClass.MERCHANT] for community in await speakers(ctx.session, language_id)]
    return sum(shares) / len(shares) if shares else 0.0


async def evolve(ctx: TickContext, language: EntityRow, profile: LanguageProfileRow, tally: ScriptTally) -> ScriptRow | None:
    table = ctx.rules.script_evolution
    current = await script_of(ctx, language, profile)
    following = SCRIPT_CHAIN[current.system] if current is not None else None
    if current is None or following is None or "system" in current.locked:
        return None
    if await merchant_share(ctx, language.id) >= table.merchant_share:
        cause = ScriptChangeCause.SIMPLIFICATION
    elif await standardisation_of(ctx.session, language.id) >= table.reform_standard:
        cause = ScriptChangeCause.REFORM
    else:
        return None
    if not ctx.rng(f"script.evolve.{language.id}.{ctx.epoch}").chance(table.evolve_pct):
        return None
    row = await record_script(ctx, language, profile, following, cause=cause, parent=current)
    tally.evolved += 1
    await record_incident(ctx, "tongues.script_evolved", roles={IncidentRole.SUBJECT: language.id}, facts={"system": following, "cause": cause})
    return row


async def borrow(ctx: TickContext, language: EntityRow, profile: LanguageProfileRow, tally: ScriptTally) -> ScriptRow | None:
    table = ctx.rules.script_evolution
    if not WRITABLE[profile.modality]:
        return None
    for lender_id in sorted(await contacts_of(ctx, language.id)):
        lender = await ctx.session.get(EntityRow, lender_id)
        lent = await ctx.session.get(LanguageProfileRow, lender_id)
        source = await script_of(ctx, lender, lent) if lender is not None and lent is not None else None
        if source is None or not ctx.rng(f"script.borrow.{language.id}.{lender_id}.{ctx.epoch}").chance(table.borrow_pct):
            continue
        row = await record_script(ctx, language, profile, source.system, cause=ScriptChangeCause.BORROWING, parent=source, extra_signs=table.borrowed_signs)
        tally.borrowed += 1
        await record_incident(
            ctx,
            "tongues.script_borrowed",
            roles={IncidentRole.LEARNER: language.id, IncidentRole.TEACHER: lender_id},
            facts={"system": source.system, "signs_added": table.borrowed_signs},
        )
        return row
    return None


async def impose(ctx: TickContext, ruler_id: int, subject: EntityRow, source: ScriptRow, *, by: int | None = None) -> ScriptRow | None:
    profile = await ctx.session.get(LanguageProfileRow, subject.id)
    if profile is None or held(subject.id) or profile.script_id == source.id:
        return None
    row = await record_script(ctx, subject, profile, source.system, cause=ScriptChangeCause.IMPOSITION, parent=source)
    grievance = ctx.rules.script.imposition_grievance
    for community_id in await speakers(ctx.session, subject.id):
        town = await ctx.session.get(SettlementProfileRow, community_id)
        if town is not None and "unrest" not in town.locked and not held(community_id):
            town.unrest = clamp_int(town.unrest + grievance, 0, PERCENT)
    roles = {IncidentRole.AUTHORITY: ruler_id, IncidentRole.SUBJECT: subject.id}
    if by is not None:
        roles[IncidentRole.ACTOR] = by
    await record_incident(ctx, "script.imposed", roles=roles, facts={"system": source.system})
    return row


async def impose_scripts(ctx: TickContext, tally: ScriptTally) -> None:
    officials = list(
        await ctx.session.scalars(
            select(LanguagePolicyRow).where(LanguagePolicyRow.policy == LanguagePolicy.OFFICIAL).order_by(LanguagePolicyRow.holder_entity_id)
        )
    )
    for policy in officials:
        if held(policy.holder_entity_id):
            continue
        official = await ctx.session.get(EntityRow, policy.language_entity_id)
        own = await ctx.session.get(LanguageProfileRow, policy.language_entity_id)
        source = await script_of(ctx, official, own) if official is not None and own is not None else None
        if source is None or official is None:
            continue
        for community_id in sorted(await realm_subjects(ctx, policy.holder_entity_id)):
            tongue = await spoken_language(ctx.session, community_id)
            if tongue is None or tongue.id == official.id:
                continue
            if not ctx.rng(f"script.impose.{policy.holder_entity_id}.{tongue.id}.{ctx.epoch}").chance(ctx.rules.script.imposition_pct):
                continue
            if await impose(ctx, policy.holder_entity_id, tongue, source) is not None:
                tally.imposed += 1


async def realm_subjects(ctx: TickContext, holder_id: int) -> set[int]:
    return {community.id for community in await communities_under(ctx, holder_id)}


async def reveal(ctx: TickContext, god_id: int, language: EntityRow, system: WritingSystem, *, prophet_id: int | None = None) -> ScriptRow:
    profile = await language_profile(ctx.session, language)
    row = await record_script(ctx, language, profile, system, cause=ScriptChangeCause.REVELATION)
    standing = await ctx.session.get(LanguageStandingRow, language.id)
    if standing is not None and "liturgical" not in standing.locked:
        standing.liturgical = True
    roles = {IncidentRole.ACTOR: god_id, IncidentRole.SUBJECT: language.id}
    if prophet_id is not None:
        roles[IncidentRole.LEARNER] = prophet_id
    await record_incident(ctx, "script.revealed", roles=roles, facts={"system": system})
    return row


async def reveal_scripts(ctx: TickContext, tally: ScriptTally) -> None:
    for tongue in list(await ctx.session.scalars(select(DivineTongueRow).order_by(DivineTongueRow.god_node_id))):
        language = await ctx.session.get(EntityRow, tongue.language_entity_id)
        profile = await ctx.session.get(LanguageProfileRow, tongue.language_entity_id)
        if language is None or profile is None or profile.writing_system is not None or held(language.id, tongue.god_node_id):
            continue
        rng = ctx.rng(f"script.reveal.{tongue.god_node_id}.{ctx.epoch}")
        if rng.chance(ctx.rules.script.revelation_pct):
            await reveal(ctx, tongue.god_node_id, language, rng.pick(list(WritingSystem)))
            tally.revealed += 1


async def evolve_scripts(ctx: TickContext, tally: ScriptTally) -> None:
    for language in await canon(ctx.session, [EntityType.LANGUAGE]):
        profile = await ctx.session.get(LanguageProfileRow, language.id)
        if profile is None or held(language.id) or await has_flag(ctx.session, language.id, EntityFlag.DEAD_LANGUAGE):
            continue
        if profile.writing_system is None:
            await borrow(ctx, language, profile, tally)
            continue
        if profile.script_id is None:
            await script_of(ctx, language, profile)
            tally.recorded += 1
        await evolve(ctx, language, profile, tally)
    await impose_scripts(ctx, tally)
    await reveal_scripts(ctx, tally)
    await ctx.session.flush()

from sqlalchemy import select

from aerona.agents.context.divine_lines import divine_lines
from aerona.agents.context.intrigue import name_knowers, names_known
from aerona.agents.context.powers import powers_text
from aerona.agents.context.reputation_line import reputation_line
from aerona.agents.context.scope import Scope
from aerona.agents.context.sky_calendar import sky_calendar
from aerona.agents.context.son_faith import son_faith
from aerona.agents.context.son_memory import son_memory
from aerona.agents.context.world_summary import world_summary
from aerona.agents.turns.ports import ToolCatalogue
from aerona.catalog.creator import CREATOR_PASSIONS
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.rarities import RARITY_LABELS
from aerona.catalog.scenarios import SCENARIOS
from aerona.catalog.stats import EXISTENCE_BAND_LABELS, EXISTENCE_MODES, STATS, existence_band, existence_band_effect, max_essence, max_hp
from aerona.core.grammar import several
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.meta import ScenarioRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.domain.enums.meta import ScenarioStatus
from aerona.engine.body.describe import body_lines
from aerona.engine.gods.dedication import dedicated_structures, incited_wars
from aerona.engine.gods.opportunities import son_opportunities
from aerona.engine.gods.progress import power_ceiling
from aerona.engine.mind.describe import mind_lines
from aerona.engine.primitives.holds import ANCHOR_KEY, is_held
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.opportunities import SonOpportunitiesContext
from aerona.prompts.contexts.son_turn import (
    AnchorLine,
    CreatorWishesContext,
    ExistenceProfile,
    PassionHint,
    Passions,
    ScenarioLine,
    SonTurnSystemContext,
    SonTurnUserContext,
    StatValue,
)


async def creator_wishes(scope: Scope) -> str:
    passions = [PassionHint(label=CREATOR_PASSIONS[item].label, hint=CREATOR_PASSIONS[item].hint) for item in scope.creator.passions]
    running = await scope.session.scalars(select(ScenarioRow).where(ScenarioRow.status == ScenarioStatus.RUNNING).order_by(ScenarioRow.id))
    scenarios = [ScenarioLine(name=SCENARIOS[row.key].name(scope.rules), description=SCENARIOS[row.key].description(scope.rules)) for row in running]
    if not passions and not scenarios:
        return ""
    return render(PromptId.CREATOR_WISHES, CreatorWishesContext(passions=passions, scenarios=scenarios))


async def anchor_line(scope: Scope, son: SonRow) -> AnchorLine | None:
    anchor = await scope.session.get(EntityRow, son.anchor_entity_id) if son.anchor_entity_id is not None else None
    return AnchorLine(id=anchor.id, name=anchor.name, status_label=anchor.status.value) if anchor is not None else None


async def shrine_lines(scope: Scope, son: SonRow) -> list[AnchorLine]:
    return [AnchorLine(id=work.id, name=work.name, status_label=work.status.value) for work in await dedicated_structures(scope.session, son.id)]


async def incitement_lines(scope: Scope, son: SonRow) -> list[str]:
    lines: list[str] = []
    for war in await incited_wars(scope.session, son.id):
        event = await scope.session.get(EntityRow, war.event_entity_id)
        name = event.name if event is not None else f"war #{war.id}"
        state = (
            f"ended in age {war.ended_epoch} ({war.ending.value.replace('_', ' ')})"
            if war.ending is not None
            else f"still burning, {several(war.battles, 'battle', 'battles')}"
        )
        lines.append(f"{name}, begun in age {war.started_epoch}, {state}")
    return lines


async def son_system_context(scope: Scope, son: SonRow, points: int, catalogue: ToolCatalogue) -> SonTurnSystemContext:
    rules = scope.rules
    powers = list(await scope.session.scalars(select(SonPowerRow).where(SonPowerRow.son_id == son.id)))
    personality = son.personality
    profile = son.existence_profile
    band = existence_band(rules, son.existence)
    horror = rules.cosmic_horror
    return SonTurnSystemContext(
        lore_language=scope.cosmos.lore_language,
        rules=rules,
        son_name=son.name,
        son_title=son.title,
        god_name=scope.creator.name,
        world_name=scope.world_name(son.current_world_id) or scope.cosmos.name,
        rarity_label=RARITY_LABELS[son.rarity],
        stars=son.stars,
        level=son.level,
        domain_1=DOMAIN_LABELS[son.domain_primary],
        domain_2=DOMAIN_LABELS[son.domain_secondary],
        existence=ExistenceProfile(
            nature=profile.nature or None if profile else None,
            state_label=EXISTENCE_MODES[profile.mode] if profile and profile.mode else None,
            manifestation=profile.manifestation or None if profile else None,
            true_name=profile.true_name or None if profile else None,
            known_by=await name_knowers(scope.session, son.id),
            names_known=await names_known(scope.session, son.id, scope.rules.context.son_location_tree_lines),
        ),
        appearance=personality.appearance,
        temperament=personality.temperament,
        obsession=personality.obsession,
        fear=personality.fear,
        speech_style=personality.speech_style,
        secret=personality.secret,
        stats=[StatValue(label=spec.label, value=int(getattr(son, stat.value))) for stat, spec in STATS.items()],
        passions=Passions(loyalty=son.loyalty, ambition=son.ambition, wrath=son.wrath, mercy=son.mercy),
        hp=son.hp,
        max_hp=max_hp(rules, son.endurance),
        wounds=await body_lines(scope.session, rules, son, private=True),
        mind=await mind_lines(scope.session, rules, son, scope.epoch, private=True),
        essence=son.essence,
        max_essence=max_essence(rules, son.might),
        faith=son.faith,
        fame=son.fame,
        existence_value=son.existence,
        existence_band_label=EXISTENCE_BAND_LABELS[band],
        existence_band_effect=existence_band_effect(rules, band),
        anchor=await anchor_line(scope, son),
        anchor_held=await is_held(scope.session, son.id, ANCHOR_KEY, scope.epoch),
        shrines=await shrine_lines(scope, son),
        incitements=await incitement_lines(scope, son),
        powers=powers_text(rules, son, powers),
        action_points=points,
        paid_tools=catalogue.paid,
        free_tools=catalogue.free,
        power_ceiling=power_ceiling(rules, son),
        sky_calendar=sky_calendar(rules, scope.epoch),
        tools=catalogue.names,
        reputation_line=reputation_line(son, [CREATOR_PASSIONS[item].label for item in scope.creator.passions]),
        rebel=son.rebel,
        rebel_prone=not son.rebel and son.will > rules.god_actions.defiant_will and son.loyalty < rules.son_tools.rebel_loyalty,
        creator_wishes=await creator_wishes(scope),
        sanity=son.sanity,
        clouded=son.sanity is not None and son.sanity < horror.son_clouding_threshold,
        divine=await divine_lines(scope, son),
    )


async def son_opportunity_text(scope: Scope, son: SonRow, catalogue: ToolCatalogue) -> str:
    lines = await son_opportunities(scope.session, scope.rules, son, scope.epoch)
    if not lines:
        return ""
    available = catalogue.names or None
    return render(PromptId.SON_OPPORTUNITIES, SonOpportunitiesContext(rules=scope.rules, lines=lines, available_tools=available))


async def son_user_context(scope: Scope, son: SonRow, points: int, catalogue: ToolCatalogue, *, resumed: bool, continuation: str = "") -> SonTurnUserContext:
    return SonTurnUserContext(
        rules=scope.rules,
        age=scope.epoch,
        order=son.standing_order,
        absolute_order=son.order_absolute,
        world_summary=await world_summary(scope, son),
        memory=await son_memory(scope, son),
        opportunities=await son_opportunity_text(scope, son, catalogue),
        faith=await son_faith(scope, son),
        action_points=points,
        resumed=resumed,
        continuation=continuation,
    )

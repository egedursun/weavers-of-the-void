from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.techniques import TECHNIQUES
from aerona.constants.units import PERCENT
from aerona.db.tables.collective import MovementRow
from aerona.db.tables.cycles import ChallengeRow, PolityStressRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.cycles import ChallengeKind, ChallengeResponse
from aerona.domain.enums.folkways import BiasedDecision
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.collective.book import shift
from aerona.engine.context import TickContext
from aerona.engine.cycles.asabiyya import asabiyya_row
from aerona.engine.cycles.book import polities, put, realm_towns
from aerona.engine.cycles.challenge_signals import signalled
from aerona.engine.cycles.stress import realm_capacity, stress_row
from aerona.engine.folkways.biases import lean_community
from aerona.engine.interconnect.flows import FlowCategory
from aerona.engine.interconnect.guards import HEADCOUNT_KEY
from aerona.engine.lore.research_depth import add_progress, research_choices
from aerona.engine.primitives.capacity import CapacityModel
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import FactInput, record

CLIMATE_PHASES = frozenset({"climate_transition", "planetary_climate"})
SEASON_PHASES = frozenset({"long_seasons"})
SUCCESSION_PHASES = frozenset({"polity_cycles"})
FLOW_KINDS = {
    FlowCategory.DISASTER: ChallengeKind.DISASTER,
    FlowCategory.PLAGUE: ChallengeKind.PLAGUE,
    FlowCategory.FAMINE: ChallengeKind.FAMINE,
    FlowCategory.CASUALTY: ChallengeKind.INVASION,
}


@dataclass
class ChallengeTally:
    met: int = 0
    responses: int = 0
    stagnations: int = 0
    collapses: int = 0


def kind_of(phase: str, category: str) -> ChallengeKind | None:
    if category not in FlowCategory._value2member_map_:
        return None
    found = FLOW_KINDS.get(FlowCategory(category))
    if found is ChallengeKind.DISASTER and phase in CLIMATE_PHASES:
        return ChallengeKind.CLIMATE
    if found is not None and phase in SEASON_PHASES:
        return ChallengeKind.LONG_SEASON
    if found is ChallengeKind.INVASION and phase in SUCCESSION_PHASES:
        return ChallengeKind.SUCCESSION_CRISIS
    return found


def losses_by_town(flows: Counter[tuple[str, str, int, str]]) -> dict[int, Counter[ChallengeKind]]:
    found: dict[int, Counter[ChallengeKind]] = {}
    for (phase, key, node_id, category), delta in flows.items():
        if key != HEADCOUNT_KEY or delta >= 0:
            continue
        kind = kind_of(phase, category)
        if kind is not None:
            found.setdefault(node_id, Counter())[kind] += -delta
    return found


async def movements_in(ctx: TickContext, profile: PolityProfileRow) -> bool:
    if profile.capital_entity_id is None:
        return False
    found = await ctx.session.scalar(select(MovementRow.id).where(MovementRow.settlement_entity_id == profile.capital_entity_id).limit(1))
    return found is not None


def response_to(ctx: TickContext, index: int, moving: bool = False) -> ChallengeResponse:
    table = ctx.rules.challenge_response
    if index > table.band_high and moving:
        return ChallengeResponse.TRANSFORMATION
    if index > table.band_high:
        return ChallengeResponse.COLLAPSE
    if index >= table.band_low:
        return ChallengeResponse.RESPONSE
    return ChallengeResponse.STAGNATION


async def civic_leap(ctx: TickContext, holder_id: int, index: int) -> bool:
    table = ctx.rules.challenge_response
    choices = await research_choices(ctx.session, holder_id)
    if not choices:
        return False
    leaning = await lean_community(ctx, holder_id, BiasedDecision.RESEARCH)
    await add_progress(ctx, holder_id, choices[0], round_half_up(table.research_progress * index * leaning / PERCENT))
    civic = [technique for technique in choices if TECHNIQUES[technique].branch is KnowledgeBranch.CIVICS]
    if civic and ctx.rng(f"challenge.civic.{holder_id}.{ctx.epoch}").chance(table.civic_pct):
        await add_progress(ctx, holder_id, civic[0], table.civic_progress)
        return True
    return False


async def answer(ctx: TickContext, polity: EntityRow, profile: PolityProfileRow, row: PolityStressRow, response: ChallengeResponse) -> None:
    table = ctx.rules.challenge_response
    standing = await asabiyya_row(ctx, polity.id)
    if response is ChallengeResponse.RESPONSE:
        shift(standing, "value", table.response_asabiyya)
        capital = profile.capital_entity_id or polity.id
        if await civic_leap(ctx, capital, row.challenge):
            await record(ctx, "challenge.civic", roles={IncidentRole.SUBJECT: polity.id}, facts={"challenge": row.challenge}, place=capital)
        facts: dict[str, FactInput] = {"challenge": row.challenge, "asabiyya_gain": table.response_asabiyya}
        await record(ctx, "challenge.response", roles={IncidentRole.SUBJECT: polity.id}, facts=facts)
    elif response is ChallengeResponse.TRANSFORMATION:
        shift(standing, "value", table.response_asabiyya)
        shift(profile, "legitimacy", -table.collapse_legitimacy // 2)
        shift(profile, "stability", table.transformation_stability)
        await record(ctx, "challenge.transformation", roles={IncidentRole.SUBJECT: polity.id}, facts={"challenge": row.challenge})
    elif response is ChallengeResponse.COLLAPSE:
        shift(standing, "value", -table.collapse_asabiyya)
        shift(profile, "stability", -table.collapse_stability)
        shift(profile, "legitimacy", -table.collapse_legitimacy)
        lost: dict[str, FactInput] = {
            "challenge": row.challenge,
            "asabiyya_loss": table.collapse_asabiyya,
            "stability_loss": table.collapse_stability,
            "legitimacy_loss": table.collapse_legitimacy,
        }
        await record(ctx, "challenge.collapse", roles={IncidentRole.SUBJECT: polity.id}, facts=lost)
    else:
        shift(standing, "value", -table.stagnation_asabiyya)


async def meet_challenges(ctx: TickContext, tally: ChallengeTally) -> None:
    table = ctx.rules.challenge_response
    model = await CapacityModel.load(ctx.session, ctx.rules)
    losses = losses_by_town(ctx.environment.stats.flows)
    for polity, profile in await polities(ctx.session):
        if held(polity.id):
            continue
        towns = await realm_towns(ctx.session, polity.id)
        capacity = max(1.0, realm_capacity(model, towns))
        kinds: Counter[ChallengeKind] = Counter()
        sources: dict[ChallengeKind, int] = {}
        for town in towns:
            for kind, lost in losses.get(town.id, Counter()).items():
                kinds[kind] += lost
                if lost >= kinds[kind] - lost:
                    sources[kind] = town.id
        row = await stress_row(ctx, polity.id)
        struck = 0
        severities = {kind: clamp_int(kinds[kind] * PERCENT / capacity * table.severity_scale, 0, PERCENT) for kind in kinds}
        severities.update(await signalled(ctx, profile, towns))
        for kind in sorted(severities, key=lambda item: item.value):
            severity = severities[kind]
            if severity < table.notice_at:
                continue
            struck += severity
            ctx.session.add(
                ChallengeRow(
                    holder_entity_id=polity.id,
                    kind=kind,
                    severity=severity,
                    response=response_to(ctx, clamp_int(row.challenge * (PERCENT - table.fade_pct) / PERCENT + severity, 0, PERCENT)),
                    source_node_id=sources.get(kind),
                    epoch=ctx.epoch,
                )
            )
        put(row, "challenge", row.challenge * (PERCENT - table.fade_pct) / PERCENT + struck)
        if not struck:
            if row.challenge < table.band_low:
                shift(await asabiyya_row(ctx, polity.id), "value", -table.calm_decay)
            continue
        tally.met += 1
        moving = ctx.rng(f"challenge.transform.{polity.id}.{ctx.epoch}").chance(table.transformation_pct) and await movements_in(ctx, profile)
        response = response_to(ctx, row.challenge, moving)
        await answer(ctx, polity, profile, row, response)
        if response is ChallengeResponse.RESPONSE:
            tally.responses += 1
        elif response is ChallengeResponse.COLLAPSE:
            tally.collapses += 1
        else:
            tally.stagnations += 1
    await ctx.session.flush()

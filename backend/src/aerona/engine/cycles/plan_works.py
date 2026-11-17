from sqlalchemy import or_, select

from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import agree, several, spoken
from aerona.db.tables.cycles import LongPlanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.eras import TechProgrammeRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.routes import RouteRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.eras import ProgrammeStage
from aerona.domain.enums.living import CultivationMethod
from aerona.domain.enums.networks import NetworkCarrier
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.living.lines import LineDraft, make_line
from aerona.engine.lore.research import techniques_of
from aerona.engine.made.control import found_network
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.structures.construction import Commission, begin

PERCENT_SPAN = 100


async def realm_of_plan(ctx: TickContext, plan: LongPlanRow) -> PolityProfileRow | None:
    for node in (plan.target_node_id, plan.holder_node_id):
        entity = await living_entity(ctx.session, node) if node is not None else None
        if entity is None:
            continue
        polity = entity.id if entity.entity_type is EntityType.POLITY else entity.affiliated_entity_id
        profile = await ctx.session.get(PolityProfileRow, polity) if polity is not None else None
        if profile is not None and not held(profile.polity_entity_id):
            return profile
    return None


async def fulfil_network(ctx: TickContext, plan: LongPlanRow, holder: EntityRow | None) -> str:
    place = plan.target_node_id if plan.target_node_id is not None and await living_entity(ctx.session, plan.target_node_id) is not None else None
    network = await found_network(ctx, holder.id if holder is not None else None, plan.name, NetworkCarrier.WIRED, place)
    return f"a network was laid under the name of {plan.name}" if network is not None else "no network was laid"


async def fulfil_megastructure(ctx: TickContext, plan: LongPlanRow, holder: EntityRow | None) -> str:
    site = await living_entity(ctx.session, plan.target_node_id) if plan.target_node_id is not None else holder
    if site is None or held(site.id):
        return "no site could bear the work"
    work, construction = await begin(ctx, Commission(site=site, kind=StructureKind.HABITAT_RING, name=plan.name))
    construction.funds += plan.steps * plan.step_cost * ctx.rules.long_plans.wonder_funds_pct // PERCENT_SPAN
    return f"{work.name} was begun on a scale beyond any town"


async def fulfil_programme(ctx: TickContext, plan: LongPlanRow, _holder: EntityRow | None) -> str:
    realm = await realm_of_plan(ctx, plan)
    if realm is None:
        return "no realm took up the programme"
    known = await techniques_of(ctx.session, realm.polity_entity_id)
    technique = next((item for item in Technique if item not in known), None)
    if technique is None:
        return "the realm already knew all that a programme could seek"
    row = TechProgrammeRow(polity_entity_id=realm.polity_entity_id, technique=technique, stage=ProgrammeStage.PLANNING)
    row.progress, row.started_epoch, row.locked = ctx.rules.long_plans.programme_head_start, ctx.epoch, []
    ctx.session.add(row)
    return f"a programme to master {spoken(technique)} was opened"


async def fulfil_realm(ctx: TickContext, plan: LongPlanRow, _holder: EntityRow | None) -> str:
    realm = await realm_of_plan(ctx, plan)
    if realm is None:
        return "no realm was there to bind together"
    gain = ctx.rules.long_plans.realm_gain
    if "administration" not in realm.locked:
        realm.administration = clamp_int(realm.administration + gain, 0, PERCENT_SPAN * 2)
    if "legitimacy" not in realm.locked:
        realm.legitimacy = clamp_int(realm.legitimacy + gain, 0, PERCENT_SPAN)
    return "the realm was bound more closely together"


async def fulfil_reform(ctx: TickContext, plan: LongPlanRow, _holder: EntityRow | None) -> str:
    realm = await realm_of_plan(ctx, plan)
    if realm is None:
        return "no realm was there to reform"
    if "corruption" not in realm.locked:
        realm.corruption = clamp_int(realm.corruption - ctx.rules.long_plans.reform_cut, 0, PERCENT_SPAN)
    return "the ways of the realm were reformed"


async def fulfil_line(ctx: TickContext, plan: LongPlanRow, holder: EntityRow | None) -> str:
    source = await living_entity(ctx.session, plan.target_node_id) if plan.target_node_id is not None else None
    if holder is None or source is None or held(source.id):
        return "no living source was there to shape a line from"
    try:
        line = await make_line(ctx, LineDraft(plan.name, CultivationMethod.SELECTIVE_BREEDING, holder.id, holder.id, (source.id,), ()), forced=True)
    except ValidationFailedError as refused:
        return str(refused).rstrip(".").lower()
    return f"{line.name} was shaped from {source.name}"


async def fulfil_exploration(ctx: TickContext, plan: LongPlanRow, holder: EntityRow | None) -> str:
    world = holder.world_id if holder is not None else None
    if world is None:
        return "nothing was found"
    hidden = list(
        await ctx.session.scalars(
            select(RouteRow).where(RouteRow.known.is_(False), or_(RouteRow.world_a_id == world, RouteRow.world_b_id == world)).order_by(RouteRow.id)
        )
    )
    found = hidden[: ctx.rules.long_plans.routes_found]
    for route in found:
        route.known = True
    return f"{several(len(found), 'hidden way', 'hidden ways')} {agree(len(found), 'was', 'were')} charted" if found else "the search found no hidden way"

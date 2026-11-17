from collections import Counter
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.dominion import ALIGNMENT_MANIFESTATIONS, MANIFESTATION_ORDER
from aerona.catalog.kinds.belief_stances import BELIEF_STANCES
from aerona.constants.units import PERCENT
from aerona.db.tables.divine import DivineStandingRow
from aerona.db.tables.dominion import GodImageRow, MiracleRecordRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.lore import FolkBeliefRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.dominion import Manifestation, PerceivedAlignment
from aerona.domain.enums.intervention import Miracle
from aerona.domain.enums.mind import Facet, PressureKind
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import God, domains_of, faithful_communities, living_gods
from aerona.engine.dominion.miracles import MIRACLE_DOMAINS, MIRACLE_KINDS
from aerona.engine.dominion.worship import perceived_of
from aerona.engine.mind.book import pressures_of
from aerona.engine.mind.ethics import at_war
from aerona.engine.mind.split import facets_of, write_facets
from aerona.engine.notes import note
from aerona.engine.primitives.holds import is_held
from aerona.engine.primitives.numbers import clamp_int, round_half_up

DISASTER_KEY = "disaster."
NEUTRAL = PERCENT // 2


@dataclass
class ImageTally:
    images: int = 0
    pulled: int = 0
    resisted: int = 0
    embraced: int = 0
    turned: int = 0


async def image_row(ctx: TickContext, god_id: int) -> GodImageRow:
    row = await ctx.session.get(GodImageRow, god_id)
    if row is None:
        row = GodImageRow(god_node_id=god_id, locked=[])
        ctx.session.add(row)
    return row


async def believed_domain(ctx: TickContext, god: God) -> Domain | None:
    kinds = Counter(
        kind
        for kind in await ctx.session.scalars(
            select(MiracleRecordRow.kind).where(
                MiracleRecordRow.credited_node_id == god.id, MiracleRecordRow.epoch >= ctx.epoch - ctx.rules.miracle_impression.repeat_window
            )
        )
        if kind in MIRACLE_KINDS
    )
    if not kinds:
        return None
    kind = max(sorted(kinds), key=lambda item: kinds[item])
    lacking = sorted(domain for domain in MIRACLE_DOMAINS[Miracle(kind)] if domain not in domains_of(god))
    return lacking[0] if lacking else None


async def crisis_of(ctx: TickContext, god: God, communities: list[int]) -> int:
    table = ctx.rules.god_images
    if not communities:
        return 0
    wars = 0
    hungers = 0
    for community in communities:
        wars += int(await at_war(ctx.session, [community]))
        hungers += (await pressures_of(ctx.session, community)).get(PressureKind.HUNGER, 0)
    war, hunger = wars / len(communities), hungers / len(communities)
    struck = await ctx.session.scalar(
        select(func.count()).select_from(IncidentRow).where(IncidentRow.epoch == ctx.epoch, IncidentRow.kind.like(f"{DISASTER_KEY}%"))
    )
    disaster = table.crisis_disaster_pct if struck else 0
    return clamp_int(war * table.crisis_war_pct + hunger * table.crisis_hunger_pct / PERCENT + disaster, 0, PERCENT)


def malleability_of(ctx: TickContext, god: God) -> int:
    table = ctx.rules.god_images
    if isinstance(god, SonRow):
        base = table.fading_malleability + (table.radiant_malleability - table.fading_malleability) * god.existence / PERCENT
        resolve = (god.will + god.ambition) / 2
    else:
        base = table.fading_malleability + (table.radiant_malleability - table.fading_malleability) * god.power / PERCENT
        resolve = god.will
    return clamp_int(base * (1 - table.will_resist_pct / PERCENT * resolve / PERCENT), 0, PERCENT)


def toward(current: int, target: int, pull: int) -> int:
    return clamp_int(current + round_half_up((target - current) * pull / PERCENT), 0, PERCENT)


async def pull_facets(ctx: TickContext, god: God, row: GodImageRow, pull: int) -> None:
    share = pull * ctx.rules.god_images.facet_pull_pct / PERCENT
    current = await facets_of(ctx.session, god.id)
    aims = {Facet.ANGER: row.believed_wrath - NEUTRAL, Facet.ALTRUISM: row.believed_mercy - NEUTRAL}
    moved = {facet: current.get(facet, 0) + round_half_up((aim - current.get(facet, 0)) * share / PERCENT) for facet, aim in aims.items()}
    if any(moved[facet] != current.get(facet, 0) for facet in moved):
        await write_facets(ctx.session, god.id, moved)


async def shape(ctx: TickContext, god: God, row: GodImageRow, tally: ImageTally) -> None:
    table = ctx.rules.god_images
    pull = row.pull
    stance = BELIEF_STANCES[row.stance]
    if isinstance(god, SonRow) and stance.resists and god.essence >= table.resist_cost:
        god.essence -= table.resist_cost
        tally.resisted += 1
        return
    if isinstance(god, SonRow) and stance.pull_rule is not None:
        pull = clamp_int(pull * int(getattr(table, stance.pull_rule)) / PERCENT, 0, PERCENT)
    if isinstance(god, SonRow) and stance.fame_rule is not None:
        god.fame = god.fame + int(getattr(table, stance.fame_rule))
        tally.embraced += 1
    if pull <= 0:
        return
    tally.pulled += 1
    if isinstance(god, SonRow):
        if not await is_held(ctx.session, god.id, "wrath", ctx.epoch):
            god.wrath = toward(god.wrath, row.believed_wrath, pull)
        if not await is_held(ctx.session, god.id, "mercy", ctx.epoch):
            god.mercy = toward(god.mercy, row.believed_mercy, pull)
    await pull_facets(ctx, god, row, pull)
    if isinstance(god, ForeignGodRow) and not await is_held(ctx.session, god.id, "stance", ctx.epoch):
        aim = PERCENT if row.believed_alignment is PerceivedAlignment.BENEVOLENT else -PERCENT if row.believed_alignment is PerceivedAlignment.MALEVOLENT else 0
        god.stance = clamp_int(god.stance + round_half_up((aim - god.stance) * pull / PERCENT), -PERCENT, PERCENT)
    domain = row.believed_domain
    if domain is None or domain in domains_of(god) or await is_held(ctx.session, god.id, "domain_secondary", ctx.epoch):
        row.domain_pressure = 0
        return
    row.domain_pressure += round_half_up(table.domain_pressure_gain * pull / PERCENT)
    if row.domain_pressure < table.domain_pressure_at or domain == god.domain_primary:
        return
    god.domain_secondary = domain
    row.domain_pressure = 0
    tally.turned += 1
    await note(
        ctx,
        f"{god.name} became what its peoples believed: a god of {domain.value.replace('_', ' ')}.",
        key="dominion.image_turned",
        ids=[god.id],
        son_id=god.id if isinstance(god, SonRow) else None,
    )


def manifestation_of(ctx: TickContext, alignment: PerceivedAlignment, *, wrath: float, mercy: float) -> Manifestation:
    if alignment is PerceivedAlignment.AMBIVALENT and wrath - mercy >= ctx.rules.god_images.stern_gap:
        return Manifestation.STERN
    return ALIGNMENT_MANIFESTATIONS[alignment]


async def bear_image(ctx: TickContext, manifestation: Manifestation, believers: list[int]) -> None:
    shift = MANIFESTATION_ORDER[manifestation] * ctx.rules.god_images.manifest_order // PERCENT
    if not shift:
        return
    for town_id in believers:
        town = await ctx.session.get(SettlementProfileRow, town_id)
        if town is not None and not held(town_id) and "unrest" not in town.locked:
            town.unrest = clamp_int(town.unrest + shift, 0, PERCENT)


async def read_image(ctx: TickContext, god: God, tally: ImageTally) -> None:
    table = ctx.rules.god_images
    rows = list(await ctx.session.scalars(select(DivineStandingRow).where(DivineStandingRow.god_node_id == god.id)))
    if not rows:
        return
    row = await image_row(ctx, god.id)
    views = [perceived_of(ctx.rules, standing.love, standing.fear) for standing in rows]
    common = Counter(views).most_common(1)[0]
    love = sum(standing.love for standing in rows) / len(rows)
    fear = sum(standing.fear for standing in rows) / len(rows)
    believers = [community.id for community in await faithful_communities(ctx.session, god.id)]
    values = {
        "believed_alignment": common[0],
        "believed_wrath": clamp_int(NEUTRAL + (fear - love) / 2, 0, PERCENT),
        "believed_mercy": clamp_int(NEUTRAL + (love - fear) / 2, 0, PERCENT),
        "believed_domain": await believed_domain(ctx, god),
        "manifestation": manifestation_of(ctx, common[0], wrath=NEUTRAL + (fear - love) / 2, mercy=NEUTRAL + (love - fear) / 2),
    }
    for key, value in values.items():
        if key not in row.locked:
            setattr(row, key, value)
    told = int(await ctx.session.scalar(select(func.count()).select_from(FolkBeliefRow).where(FolkBeliefRow.god_node_id == god.id)) or 0)
    credence = table.folk_credence_pct / PERCENT
    uniformity = common[1] / len(views)
    row.intensity = clamp_int(uniformity * (1 - credence + credence * min(1.0, told / len(views))) * PERCENT, 0, PERCENT)
    row.worship_share = clamp_int(len(believers) * PERCENT / len(rows), 0, PERCENT)
    row.crisis = await crisis_of(ctx, god, believers)
    row.malleability = malleability_of(ctx, god)
    row.pull = round_half_up(table.base_pull * row.intensity / PERCENT * row.worship_share / PERCENT * (1 + row.crisis / PERCENT) * row.malleability / PERCENT)
    row.epoch = ctx.epoch
    await bear_image(ctx, row.manifestation, believers)
    tally.images += 1
    await shape(ctx, god, row, tally)


async def shape_gods(ctx: TickContext, tally: ImageTally) -> None:
    for god in await living_gods(ctx.session):
        if held(god.id):
            continue
        await read_image(ctx, god, tally)
    await ctx.session.flush()

from sqlalchemy import select

from aerona.catalog.units import UNITS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyTemplateRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.write_guard import held
from aerona.domain.enums.demography import MartialStyle
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.context import TickContext
from aerona.engine.lore.research import techniques_of
from aerona.engine.military.templates import seat_of, upgrades, weights_of
from aerona.engine.military.units import allowed, composition, doctrine_of
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import living_entity

TEMPLATE_SIZE = 1000


async def allowed_for(ctx: TickContext, community: EntityRow, knowledge: KnowledgeMap) -> set[UnitKind]:
    techniques = await techniques_of(ctx.session, community.id)
    return {kind for kind, spec in UNITS.items() if allowed(spec, community.id, knowledge, techniques)}


async def draw_template(ctx: TickContext, polity: EntityRow, seat: EntityRow, knowledge: KnowledgeMap) -> ArmyTemplateRow:
    counts = await composition(ctx, seat, TEMPLATE_SIZE, knowledge)
    whole = sum(counts.values()) or 1
    style = await doctrine_of(ctx.session, seat)
    row = ArmyTemplateRow(
        polity_entity_id=polity.id,
        name=f"{polity.name} host",
        doctrine=MartialStyle(style) if style in {item.value for item in MartialStyle} else MartialStyle.SHIELDWALL,
        composition={kind.value: max(1, round_half_up(count * PERCENT / whole)) for kind, count in sorted(counts.items())},
        active=True,
        obsolete=False,
        created_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    return row


def refit(template: ArmyTemplateRow, swaps: dict[UnitKind, UnitKind], epoch: int) -> None:
    weights = weights_of(template)
    template.composition = {swaps.get(kind, kind).value: weight for kind, weight in weights.items()}
    template.obsolete = False
    template.upgraded_epoch = epoch


async def keep_templates(ctx: TickContext) -> dict[str, int]:
    counts = {"drawn": 0, "outdated": 0, "upgraded": 0}
    knowledge = await KnowledgeMap.load(ctx.session)
    marshals = {
        office.polity_entity_id
        for office in await ctx.session.scalars(select(OfficeRow).where(OfficeRow.kind == OfficeKind.MARSHAL, OfficeRow.holder_entity_id.is_not(None)))
    }
    polities = sorted(marshals | set(await ctx.session.scalars(select(ArmyTemplateRow.polity_entity_id).distinct())))
    for polity_id in polities:
        polity = await living_entity(ctx.session, polity_id)
        seat = await seat_of(ctx, polity_id) if polity is not None else None
        if polity is None or seat is None or held(polity_id):
            continue
        templates = list(await ctx.session.scalars(select(ArmyTemplateRow).where(ArmyTemplateRow.polity_entity_id == polity_id).order_by(ArmyTemplateRow.id)))
        if not templates and polity_id in marshals:
            await draw_template(ctx, polity, seat, knowledge)
            counts["drawn"] += 1
            continue
        kinds = await allowed_for(ctx, seat, knowledge)
        for template in templates:
            swaps = upgrades(weights_of(template), template.doctrine, kinds)
            if "obsolete" not in template.locked and template.obsolete != bool(swaps):
                template.obsolete = bool(swaps)
                counts["outdated"] += int(bool(swaps))
            if swaps and polity_id in marshals and "composition" not in template.locked:
                refit(template, swaps, ctx.epoch)
                counts["upgraded"] += 1
    return counts

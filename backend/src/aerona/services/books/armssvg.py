from html import escape

from markupsafe import Markup
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.collective import HERALDIC_NAMES
from aerona.catalog.heraldry import CHARGES, DIVISIONS, SHIELD
from aerona.core.total import total
from aerona.db.tables.collective import ArmsRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.collective import HeraldicCharge, HeraldicDivision, Tincture
from aerona.engine.collective.heraldry import blazon
from aerona.services.books.citysvg import Plan

INK = "#2b2118"
TINCTURES = total(
    Tincture,
    {
        Tincture.GOLD: "#d4a62a",
        Tincture.SILVER: "#e9e6df",
        Tincture.RED: "#b3262b",
        Tincture.BLUE: "#1f4e9c",
        Tincture.GREEN: "#2f7a3a",
        Tincture.BLACK: "#1d1b1a",
        Tincture.PURPLE: "#6b2f7a",
        Tincture.ORANGE: "#d0702a",
    },
)
LINE_CHARGES = frozenset({HeraldicCharge.SUN})


def shield(arms: ArmsRow, label: str) -> Markup:
    field = TINCTURES[arms.field]
    second = TINCTURES[arms.second] if arms.second is not None else field
    charge = TINCTURES[arms.charge_tincture] if arms.charge_tincture is not None else INK
    division = DIVISIONS[arms.division]
    parts = [f'<path d="{SHIELD}" fill="{field}"/>']
    if division:
        rule = ' fill-rule="evenodd"' if arms.division is HeraldicDivision.BORDURE else ""
        parts.append(f'<path d="{division}" fill="{second}"{rule}/>')
    glyph = CHARGES[arms.charge]
    if glyph:
        stroke = f' stroke="{charge}" stroke-width="4" stroke-linecap="round"' if arms.charge in LINE_CHARGES else ""
        parts.append(f'<path d="{glyph}" fill="{charge}"{stroke} fill-rule="evenodd"/>')
    parts.append(f'<path d="{SHIELD}" fill="none" stroke="{INK}" stroke-width="3"/>')
    return Markup(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 132" role="img" aria-label="{escape(label)}">{"".join(parts)}</svg>')


async def arms_plan(session: AsyncSession, entity: EntityRow) -> Plan | None:
    arms = await session.get(ArmsRow, entity.id)
    if arms is None:
        return None
    parent = await session.get(EntityRow, arms.parent_entity_id) if arms.parent_entity_id is not None else None
    quartered = await session.get(EntityRow, arms.quartered_entity_id) if arms.quartered_entity_id is not None else None
    text = blazon(arms)
    facts = [
        ("Bearer", arms.holder_kind.value.replace("_", " ")),
        ("Field", HERALDIC_NAMES[arms.field]),
        ("Division", arms.division.value.replace("_", " ")),
        ("Second tincture", HERALDIC_NAMES[arms.second] if arms.second is not None else "none"),
        ("Charge", arms.charge.value),
        ("Charge tincture", HERALDIC_NAMES[arms.charge_tincture] if arms.charge_tincture is not None else "none"),
        ("Motto", arms.motto or "none"),
        ("Differenced from", parent.name if parent is not None else "none"),
        ("Quartered with", quartered.name if quartered is not None else "none"),
        ("Borne since", f"Epoch {arms.since_epoch}"),
    ]
    return Plan(figure=shield(arms, f"Arms of {entity.name}"), caption=f"Arms of {entity.name}: {text}", facts=facts)

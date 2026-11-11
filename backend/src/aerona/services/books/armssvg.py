from html import escape

from markupsafe import Markup
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.collective import HERALDIC_NAMES
from aerona.catalog.heraldry import CHARGE_NAMES, DIVISION_NAMES, LINE_NAMES, RIM_NAMES, SHAPE_NAMES
from aerona.core.total import total
from aerona.db.tables.collective import ArmsRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.collective import ArmsInk, HeraldicCharge, Tincture
from aerona.engine.collective.armory import Drawing, draw
from aerona.engine.collective.heraldry import blazon, design_of
from aerona.services.books.citysvg import Plan

INKS = total(
    ArmsInk,
    {
        ArmsInk.GOLD: "#d4a62a",
        ArmsInk.SILVER: "#e9e6df",
        ArmsInk.RED: "#b3262b",
        ArmsInk.BLUE: "#1f4e9c",
        ArmsInk.GREEN: "#2f7a3a",
        ArmsInk.BLACK: "#1d1b1a",
        ArmsInk.PURPLE: "#6b2f7a",
        ArmsInk.ORANGE: "#d0702a",
        ArmsInk.CELESTE: "#7fb3de",
        ArmsInk.MURREY: "#7a2448",
        ArmsInk.ROSE: "#e8a0ac",
        ArmsInk.BROWN: "#7a5232",
        ArmsInk.GREY: "#9a9ea6",
        ArmsInk.LINE: "#2b2118",
    },
)


def svg(drawing: Drawing, label: str, key: str) -> Markup:
    defs = [f'<clipPath id="{key}-o"><path d="{drawing.outline}"/></clipPath>']
    body: list[str] = []
    for index, layer in enumerate(drawing.layers):
        rule = "evenodd" if layer.evenodd else "nonzero"
        paint = (
            f'fill="{INKS[layer.ink]}" fill-rule="{rule}"'
            if layer.filled
            else f'fill="none" stroke="{INKS[layer.ink]}" stroke-width="{layer.width}" stroke-linecap="round" stroke-linejoin="round"'
        )
        extra = f' opacity="{layer.opacity}"' if layer.opacity < 1 else ""
        extra += f' transform="{layer.transform}"' if layer.transform else ""
        if layer.clip is not None:
            defs.append(f'<clipPath id="{key}-c{index}" clip-rule="{rule}"><path d="{layer.clip}"/></clipPath>')
            extra += f' clip-path="url(#{key}-c{index})"'
        element = f'<path d="{layer.d}" {paint}{extra}/>'
        body.append(f'<g clip-path="url(#{key}-o)">{element}</g>' if layer.clipped else element)
    return Markup(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{drawing.view_box}" role="img" aria-label="{escape(label)}">'
        f"<defs>{''.join(defs)}</defs>{''.join(body)}</svg>"
    )


def shield(arms: ArmsRow, label: str) -> Markup:
    return svg(draw(design_of(arms)), label, f"arms{arms.holder_entity_id}")


def tinct(tincture: Tincture | None) -> str:
    return HERALDIC_NAMES[tincture] if tincture is not None else "contrasting"


def charged(charge: HeraldicCharge, tincture: Tincture | None) -> str:
    return "none" if charge is HeraldicCharge.NONE else f"{CHARGE_NAMES[charge][0]} ({tinct(tincture)})"


async def arms_plan(session: AsyncSession, entity: EntityRow) -> Plan | None:
    arms = await session.get(ArmsRow, entity.id)
    if arms is None:
        return None
    parent = await session.get(EntityRow, arms.parent_entity_id) if arms.parent_entity_id is not None else None
    quartered = await session.get(EntityRow, arms.quartered_entity_id) if arms.quartered_entity_id is not None else None
    text = blazon(arms)
    facts = [
        ("Bearer", arms.holder_kind.value.replace("_", " ")),
        ("Shield", SHAPE_NAMES[arms.shape]),
        ("Field", HERALDIC_NAMES[arms.field]),
        ("Division", DIVISION_NAMES[arms.division][0] or "plain"),
        ("Line of the division", LINE_NAMES[arms.line] or "straight"),
        ("Second tincture", tinct(arms.second)),
        ("First charge", charged(arms.charge, arms.charge_tincture)),
        ("Second charge", charged(arms.charge_two, arms.charge_two_tincture)),
        ("Third charge", charged(arms.charge_three, arms.charge_three_tincture)),
        ("Arrangement", arms.arrangement.value.replace("_", " ")),
        ("Rim", RIM_NAMES[arms.rim] or "a plain line"),
        ("Edge of the shield", LINE_NAMES[arms.rim_line] or "straight"),
        ("Rim tincture", tinct(arms.rim_tincture)),
        ("Supporters", charged(arms.supporter, arms.supporter_tincture)),
        ("Supporters' pose", arms.supporter_pose.value),
        ("Crest", charged(arms.crest, arms.crest_tincture)),
        ("Motto", arms.motto or "none"),
        ("Differenced from", parent.name if parent is not None else "none"),
        ("Quartered with", quartered.name if quartered is not None else "none"),
        ("Borne since", f"Epoch {arms.since_epoch}"),
    ]
    return Plan(figure=shield(arms, f"Arms of {entity.name}"), caption=f"Arms of {entity.name}: {text}", facts=facts)

from dataclasses import dataclass
from html import escape

from markupsafe import Markup
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.grammar import several
from aerona.domain.enums.bond import BondKind
from aerona.services.books.armssvg import INKS
from aerona.services.kinship.layout import CARD_HEIGHT, CARD_WIDTH, FamilyLayout, PartnerMark, PlacedCard, lay_out
from aerona.services.kinship.naming import relations_of
from aerona.services.kinship.tree import Kin, TracedFamily, trace_family

BOOK_REACH = 3
SCREEN_SCALE = 0.5
NAME_LIMIT = 18
RELATION_LIMIT = 30
PAPER = "#fbf7ee"
FADED = "#ebe6dc"
GOLD = "#b88a2a"
INK = "#2b2118"
UMBER = "#7a4f12"
GREY = "#6b6259"
ENDED = "#8a8580"
BAND = "#f3ecdc"
LOOKS = {
    BondKind.PARENT_OF: (GOLD, "6 6"),
    BondKind.FOSTERED_BY: ("#2f8f83", "9 5"),
    BondKind.GODPARENT_OF: ("#3b6fb6", "2 6"),
    BondKind.SWORN_KIN: ("#c27c1a", "12 4 2 4"),
    BondKind.CONCUBINE_OF: ("#a03a7a", "7 5"),
    BondKind.BETROTHED_TO: ("#3b6fb6", "1 6"),
}


@dataclass(frozen=True)
class KinRow:
    name: str
    relation: str
    generation: str
    life: str
    house: str


@dataclass(frozen=True)
class FamilyPlan:
    figure: Markup
    caption: str
    rows: list[KinRow]


def clipped(text: str, limit: int) -> str:
    return text if len(text) <= limit else f"{text[: limit - 1]}…"


def generation_word(generation: int) -> str:
    if generation == 0:
        return "Their generation"
    steps = abs(generation)
    return f"{several(steps, 'generation', 'generations')} {'up' if generation < 0 else 'down'}"


def life_word(person: Kin) -> str:
    if person.living:
        return f"Born epoch {person.birth_epoch}, living"
    if person.end_epoch is None:
        return f"Born epoch {person.birth_epoch}, dead"
    return f"Epoch {person.birth_epoch} to {person.end_epoch}"


def initials(name: str) -> str:
    parts = name.split()
    return "".join(part[:1] for part in parts[:2]).upper() if len(parts) > 1 else name[:2].upper()


def card_svg(person: Kin, place: PlacedCard, *, relation: str, root: bool, inks: dict[int, str]) -> str:
    x, y = place.x, place.y
    fill = PAPER if person.living else FADED
    stroke = UMBER if root else GOLD
    dash = "" if person.blood else ' stroke-dasharray="6 4"'
    stripe = (
        f'<rect x="{x}" y="{y + 14}" width="6" height="{CARD_HEIGHT - 28}" rx="3" fill="{inks[person.house_id]}"/>'
        if person.house_id is not None and person.house_id in inks
        else ""
    )
    cx = x + 41
    cy = y + CARD_HEIGHT / 2
    name = f"{'' if person.living else '† '}{clipped(person.name, NAME_LIMIT)}"
    return (
        f'<g><rect x="{x}" y="{y}" width="{CARD_WIDTH}" height="{CARD_HEIGHT}" rx="16" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="{2.5 if root else 1.25}"{dash}/>{stripe}'
        f'<circle cx="{cx}" cy="{cy}" r="27" fill="{BAND}" stroke="{GOLD}" stroke-width="1.5"/>'
        f'<text x="{cx}" y="{cy + 6}" text-anchor="middle" font-size="17" fill="{UMBER}" font-family="Georgia, serif">{escape(initials(person.name))}</text>'
        f'<text x="{x + 78}" y="{y + 30}" font-size="15" font-weight="600" fill="{INK}" font-family="Georgia, serif">{escape(name)}</text>'
        f'<text x="{x + 78}" y="{y + 50}" font-size="11" font-weight="600" fill="{UMBER}" font-family="sans-serif">'
        f"{escape(clipped(relation, RELATION_LIMIT))}</text>"
        f'<text x="{x + 78}" y="{y + 68}" font-size="11" fill="{GREY}" font-family="sans-serif">{escape(life_word(person))}</text></g>'
    )


def partner_svg(mark: PartnerMark) -> str:
    color, dash = LOOKS.get(mark.kind, (GOLD, ""))
    if mark.ended:
        line = f'<path d="{mark.path}" fill="none" stroke="{ENDED}" stroke-width="2" stroke-dasharray="5 6"/>'
    elif mark.kind is BondKind.SPOUSE_OF:
        outer = ENDED if mark.widowed else GOLD
        line = f'<path d="{mark.path}" fill="none" stroke="{outer}" stroke-width="6"/><path d="{mark.path}" fill="none" stroke="{PAPER}" stroke-width="2"/>'
    else:
        line = f'<path d="{mark.path}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>'
    knot = f'<circle cx="{mark.knot.x}" cy="{mark.knot.y}" r="7" fill="{PAPER}" stroke="{ENDED if mark.ended or mark.widowed else color}" stroke-width="1.5"/>'
    return line + knot


def tree_svg(family: TracedFamily, layout: FamilyLayout, relations: dict[int, str], label: str) -> Markup:
    inks = {house.id: INKS[house.ink] for house in family.houses if house.ink is not None}
    people = {person.id: person for person in family.people}
    bands = "".join(
        f'<rect x="0" y="{row.y - 38}" width="{layout.width}" height="{CARD_HEIGHT + 76}" fill="{BAND}" opacity="{0.6 if index % 2 == 0 else 0}"/>'
        f'<text x="18" y="{row.y - 12}" font-size="12" letter-spacing="1.5" fill="{GREY}" font-family="Georgia, serif">'
        f"{escape(generation_word(row.generation).upper())}</text>"
        for index, row in enumerate(layout.rows)
    )
    lines = "".join(f'<path d="{line.path}" fill="none" stroke="{GOLD}" stroke-width="2" stroke-linejoin="round"/>' for line in layout.families)
    care = "".join(
        f'<path d="{line.path}" fill="none" stroke="{look[0]}" stroke-width="2" stroke-dasharray="{look[1]}" opacity="0.7"/>'
        for line in layout.care
        for look in [LOOKS.get(line.tie.kind, (GOLD, ""))]
    )
    partners = "".join(partner_svg(mark) for mark in layout.partners)
    cards = "".join(
        card_svg(people[card.person_id], card, relation=relations[card.person_id], root=card.person_id == family.root, inks=inks)
        for card in layout.cards.values()
    )
    return Markup(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {layout.width} {layout.height}" width="{round(layout.width * SCREEN_SCALE)}" '
        f'role="img" aria-label="{escape(label)}"><rect width="{layout.width}" height="{layout.height}" fill="{PAPER}"/>'
        f"{bands}{lines}{care}{partners}{cards}</svg>"
    )


async def family_plan(session: AsyncSession, root: int, name: str) -> FamilyPlan | None:
    family = await trace_family(session, root, BOOK_REACH, BOOK_REACH)
    if len(family.people) < 2:
        return None
    relations = relations_of(family)
    layout = lay_out(family)
    houses = {house.id: house.name for house in family.houses}
    caption = f"The family of {name}: {several(len(family.people), 'kin', 'kin')} across {several(len(layout.rows), 'generation', 'generations')}"
    rows = [
        KinRow(
            name=person.name,
            relation=relations[person.id],
            generation=generation_word(person.generation),
            life=life_word(person),
            house=houses.get(person.house_id, "No house") if person.house_id is not None else "No house",
        )
        for person in family.people
    ]
    return FamilyPlan(figure=tree_svg(family, layout, relations, caption), caption=caption, rows=rows)

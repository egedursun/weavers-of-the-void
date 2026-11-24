from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.schemas.mortals import (
    FamilyTreeView,
    TreeCard,
    TreeCare,
    TreeFamily,
    TreeHouse,
    TreeLayout,
    TreePartner,
    TreePerson,
    TreeRow,
    TreeTie,
    TreeUnion,
)
from aerona.api.views.common import node_refs
from aerona.domain.enums.bond import BondKind
from aerona.services.kinship.layout import CARD_HEIGHT, CARD_WIDTH, FamilyLayout, lay_out
from aerona.services.kinship.naming import relations_of
from aerona.services.kinship.tree import trace_family


def layout_view(layout: FamilyLayout) -> TreeLayout:
    return TreeLayout(
        width=layout.width,
        height=layout.height,
        card_width=CARD_WIDTH,
        card_height=CARD_HEIGHT,
        cards=[TreeCard(person_id=card.person_id, x=card.x, y=card.y) for card in layout.cards.values()],
        partners=[
            TreePartner(
                key=mark.key,
                first_id=mark.first,
                second_id=mark.second,
                kind=mark.kind,
                ended=mark.ended,
                widowed=mark.widowed,
                marriage_id=mark.marriage_id,
                bond_id=mark.bond_id,
                path=mark.path,
                knot_x=mark.knot.x,
                knot_y=mark.knot.y,
            )
            for mark in layout.partners
        ],
        families=[TreeFamily(key=line.key, parent_ids=line.parents, child_ids=line.children, path=line.path) for line in layout.families],
        care=[TreeCare(bond_id=line.tie.bond_id, path=line.path) for line in layout.care],
        rows=[TreeRow(generation=row.generation, y=row.y) for row in layout.rows],
    )


async def family_tree_view(session: AsyncSession, root: int, up: int, down: int, care: frozenset[BondKind]) -> FamilyTreeView:
    family = await trace_family(session, root, up, down, care)
    relations = relations_of(family)
    refs = await node_refs(session, [house.id for house in family.houses])
    return FamilyTreeView(
        root=family.root,
        up=family.up,
        down=family.down,
        deeper_up=family.deeper_up,
        deeper_down=family.deeper_down,
        people=[
            TreePerson(
                id=person.id,
                name=person.name,
                title=person.title,
                relation=relations[person.id],
                living=person.living,
                sex=person.sex,
                role=person.role,
                generation=person.generation,
                birth_epoch=person.birth_epoch,
                end_epoch=person.end_epoch,
                cover=person.cover,
                house_id=person.house_id,
                blood=person.blood,
            )
            for person in family.people
        ],
        houses=[TreeHouse(house=refs[house.id], ink=house.ink) for house in family.houses if house.id in refs],
        unions=[
            TreeUnion(
                marriage_id=union.marriage_id,
                first_id=union.first_id,
                second_id=union.second_id,
                form=union.form,
                purpose=union.purpose,
                start_epoch=union.start_epoch,
                end_epoch=union.end_epoch,
                cause_end=union.cause_end,
                forced=union.forced,
            )
            for union in family.unions
        ],
        ties=[
            TreeTie(bond_id=tie.bond_id, kind=tie.kind, source_id=tie.source_id, target_id=tie.target_id, past=tie.past, epoch=tie.epoch) for tie in family.ties
        ],
        layout=layout_view(lay_out(family)),
    )

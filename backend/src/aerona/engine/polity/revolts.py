from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import select

from aerona.core.total import total
from aerona.db.tables.military import WarAimRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.military import WarAimKind
from aerona.domain.enums.polity import RevoltKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.war import WarCause, WarStatus
from aerona.engine.context import TickContext
from aerona.engine.military.aims import DEFENDER_AIMS, REGION_AIMS
from aerona.engine.primitives.distance import RegionAtlas

A = WarAimKind


@dataclass(frozen=True)
class RevoltSpec:
    aims: tuple[WarAimKind, ...]
    rising: SocialClass | None
    cause: WarCause
    text: str


R = RevoltKind
C = SocialClass
W = WarCause
REVOLTS: Mapping[RevoltKind, RevoltSpec] = total(
    RevoltKind,
    {
        R.PEASANT: RevoltSpec((A.LOOT, A.CHANGE_GOVERNMENT), None, W.UPRISING, "poverty and crowding"),
        R.NOBLE: RevoltSpec((A.CHANGE_GOVERNMENT, A.HUMILIATE), C.NOBLE, W.UPRISING, "the bitterness of the nobles"),
        R.RELIGIOUS: RevoltSpec((A.CONVERT, A.CHANGE_GOVERNMENT), C.PRIEST, W.UPRISING, "a faith the realm does not keep"),
        R.SECESSION: RevoltSpec((A.LIBERATE,), None, W.INDEPENDENCE, "a wish to stand apart"),
        R.SLAVE: RevoltSpec((A.LIBERATE, A.LOOT), C.SERF_OR_SLAVE, W.UPRISING, "bondage"),
        R.WORKER: RevoltSpec((A.CHANGE_GOVERNMENT, A.LOOT), C.WORKER, W.UPRISING, "the grievances of the workers"),
        R.URBAN: RevoltSpec((A.LOOT, A.CHANGE_GOVERNMENT), C.CITIZEN, W.UPRISING, "the crowding of a great city"),
        R.MUTINY: RevoltSpec((A.CHANGE_GOVERNMENT,), C.WARRIOR, W.UPRISING, "the anger of its soldiers"),
        R.MINORITY: RevoltSpec((A.LIBERATE, A.HUMILIATE), None, W.LIBERATION, "a people ruled by another"),
        R.COLONIAL: RevoltSpec((A.LIBERATE,), None, W.INDEPENDENCE, "rule from a distant seat"),
        R.TAX: RevoltSpec((A.HUMILIATE, A.LOOT), C.FARMER, W.TRIBUTE_REVOLT, "the weight of taxes"),
        R.SUCCESSION: RevoltSpec((A.PRESS_CLAIM, A.CHANGE_GOVERNMENT), C.NOBLE, W.SUCCESSION, "a pressed claim to rule"),
        R.SCHOLAR: RevoltSpec((A.CHANGE_GOVERNMENT,), C.SCRIBE, W.IDEOLOGY, "the discontent of the learned"),
        R.MADE_MINDS: RevoltSpec((A.LIBERATE, A.CHANGE_GOVERNMENT), None, W.LIBERATION, "made minds that want their own will"),
        R.GIFTED: RevoltSpec((A.LIBERATE, A.CHANGE_GOVERNMENT), None, W.LIBERATION, "the binding of the gifted"),
    },
)


async def seed_aims(ctx: TickContext, attacker_id: int, defender_id: int, kinds: tuple[WarAimKind, ...]) -> int:
    war = await ctx.session.scalar(
        select(WarRow)
        .join(WarSideRow, WarSideRow.war_id == WarRow.id)
        .where(WarSideRow.entity_id == attacker_id, WarRow.status == WarStatus.ONGOING)
        .order_by(WarRow.id.desc())
        .limit(1)
    )
    if war is None or await ctx.session.scalar(select(WarAimRow.id).where(WarAimRow.war_id == war.id).limit(1)) is not None:
        return 0
    region = (await RegionAtlas.load(ctx.session)).top_region(defender_id)
    made = 0
    for side, enemy, wanted in ((attacker_id, defender_id, kinds), (defender_id, attacker_id, DEFENDER_AIMS)):
        for kind in wanted:
            target = region if kind in REGION_AIMS and side == attacker_id else enemy
            ctx.session.add(WarAimRow(war_id=war.id, side_entity_id=side, kind=kind, target_entity_id=target, params={}, achieved=0))
            made += 1
    return made

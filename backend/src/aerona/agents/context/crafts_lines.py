from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.catalog.kinds.crafts_labels import GAME_LABELS, MEANING_LABELS
from aerona.core.grammar import an, spoken
from aerona.db.tables.crafts import (
    AssistiveAidRow,
    ChemicalWorksRow,
    EmotionSpiritRow,
    GameRow,
    IncorporealRightRow,
    InsurancePolicyRow,
    NumberSystemRow,
    PublicClockRow,
    SympatheticLinkRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kind_crafts import ColourMeaningRow, ColourTermRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.crafts import Notation
from aerona.domain.enums.kind_crafts import ColourMeaning
from aerona.domain.enums.kinds import KindConcept
from aerona.engine.body.customs import people_of
from aerona.engine.primitives.distance import RegionAtlas

LIST_LINES = 3


async def people_lines(scope: Scope, folk_id: int) -> list[str]:
    session = scope.session
    found: list[str] = []
    games = await session.execute(
        select(GameRow, KindHoldingRow.strength)
        .join(KindHoldingRow, KindHoldingRow.kind_id == GameRow.id)
        .where(KindHoldingRow.concept == KindConcept.GAME, KindHoldingRow.holder_node_id == folk_id)
        .order_by(KindHoldingRow.strength.desc(), GameRow.id)
        .limit(LIST_LINES)
    )
    found += [
        f"your people play {game.name}, {an(GAME_LABELS[game.category.value].lower())}, left {game.chance_share} of 100 to chance" for game, _ in games.all()
    ]
    meanings = await session.execute(
        select(ColourTermRow.name, ColourMeaningRow.meaning)
        .join(ColourMeaningRow, ColourMeaningRow.colour_term_id == ColourTermRow.id)
        .where(ColourMeaningRow.culture_node_id == folk_id, ColourMeaningRow.meaning != ColourMeaning.NONE)
        .order_by(ColourMeaningRow.weight.desc(), ColourTermRow.id)
        .limit(LIST_LINES)
    )
    found += [f"to your people the colour {name} means {MEANING_LABELS[meaning.value].lower()}" for name, meaning in meanings.all()]
    system = await session.get(NumberSystemRow, folk_id)
    if system is not None:
        marks = [*(["with a zero"] if system.zero else []), *(["written by place"] if system.notation is Notation.POSITIONAL else [])]
        found.append(f"your people count in base {system.base}{(', ' + ' and '.join(marks)) if marks else ''}; numeracy {system.numeracy} of 100")
    return found


async def mortal_crafts_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    for aid in await session.scalars(select(AssistiveAidRow).where(AssistiveAidRow.holder_node_id == me.id).order_by(AssistiveAidRow.kind)):
        found.append(f"you have {spoken(aid.kind)}")
    for right in await session.scalars(
        select(IncorporealRightRow).where(IncorporealRightRow.holder_node_id == me.id).order_by(IncorporealRightRow.id).limit(LIST_LINES)
    ):
        found.append(f"you hold the right to {right.name} ({spoken(right.kind)})")
    for policy in await session.scalars(
        select(InsurancePolicyRow).where(InsurancePolicyRow.holder_node_id == me.id, InsurancePolicyRow.active.is_(True)).order_by(InsurancePolicyRow.id)
    ):
        found.append(f"your {spoken(policy.cover)} is insured with {await named(scope, policy.insurer_entity_id)}")
    for link in await session.scalars(
        select(SympatheticLinkRow).where(SympatheticLinkRow.holder_node_id == me.id).order_by(SympatheticLinkRow.id).limit(LIST_LINES)
    ):
        found.append(f"you hold {spoken(link.token)} that links you to {await named(scope, link.target_node_id)}")
    folk = await people_of(session, me)
    if folk is not None:
        found += await people_lines(scope, folk.id)
    if me.location_id is not None:
        clock = await session.get(PublicClockRow, me.location_id)
        if clock is not None:
            found.append(f"your town keeps its hours by {an('public ' + spoken(clock.kind))}")
        for works in await session.scalars(
            select(ChemicalWorksRow).where(ChemicalWorksRow.settlement_entity_id == me.location_id).order_by(ChemicalWorksRow.product)
        ):
            found.append(f"your town has works for {spoken(works.product)}")
    region = (await RegionAtlas.load(session)).top_region(me.id)
    if region is not None:
        for spirit in await session.scalars(
            select(EmotionSpiritRow).where(EmotionSpiritRow.region_entity_id == region).order_by(EmotionSpiritRow.id).limit(LIST_LINES)
        ):
            found.append(f"a spirit of {spoken(spirit.emotion)} roams your land")
    return found


async def son_crafts_lines(scope: Scope, son: SonRow) -> list[str]:
    if son.current_world_id is None:
        return []
    lands = select(EntityRow.id).where(EntityRow.world_id == son.current_world_id)
    found: list[str] = []
    for spirit in await scope.session.scalars(
        select(EmotionSpiritRow)
        .where(EmotionSpiritRow.region_entity_id.in_(lands))
        .order_by(EmotionSpiritRow.strength.desc(), EmotionSpiritRow.id)
        .limit(LIST_LINES)
    ):
        found.append(f"a spirit of {spoken(spirit.emotion)} in {await named(scope, spirit.region_entity_id)} (strength {spirit.strength})")
    return found

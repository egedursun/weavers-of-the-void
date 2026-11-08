from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.culture import HolderLevelRow, HolderTechniqueRow, InstitutionRow, ResearchBoostRow, ResearchFocusRow, ResearchProgressRow
from aerona.db.tables.economy import LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import CultureValueRow, SkillRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.communication import Medium
from aerona.domain.enums.culture import BoostTrigger, Capability, IdeologyTenet, ResearchChooser, Technique
from aerona.domain.enums.economy import LoanStatus
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import SkillKind, SkillSource, ValueAxis
from aerona.domain.enums.polity import ClauseKind, PartyRole, TreatyKind
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.engine.communication import post
from aerona.engine.lore import ideology, research, research_control, research_depth
from aerona.engine.lore.learning import institution_factor
from aerona.engine.polity.accords import Clause, sign
from aerona.engine.primitives.distance import RegionAtlas
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm
from tests.engine.warfare.factories import bond, make, make_ctx, society

RULES = Rules()
B = KnowledgeBranch


def level(holder_id: int, branch: KnowledgeBranch, value: int) -> HolderLevelRow:
    return HolderLevelRow(holder_entity_id=holder_id, branch=branch, level=value, practitioners=1, progress=0, secret=False, updated_epoch=1, locked=[])


async def folk(session: AsyncSession, realm: Realm, name: str) -> EntityRow:
    return await make(session, name, EntityType.PEOPLE, realm.world.id, location_id=realm.region.id, population=4000)


async def test_scholars_draw_choices_and_the_focus_outpaces_the_rest(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session)
    people = await folk(session, realm, "Oren Folk")
    session.add(level(people.id, B.CIVICS, 1))
    await session.flush()
    tally = research_depth.DepthTally()
    await research_depth.set_focus(ctx, tally)
    civic = {Technique.ORAL_LAW, Technique.GUILDS, Technique.ORGANISED_CLERGY, Technique.LOGIC}
    row = await session.get(ResearchFocusRow, people.id)
    assert row is not None and row.technique in civic and row.chooser is ResearchChooser.SCHOLARS
    assert {Technique(item) for item in row.options} <= civic and len(row.options) == RULES.research_depth.options
    assert row.technique.value in row.options and tally.counts["focus_chosen"] == 1
    table = RULES.research_depth
    assert await research_depth.focus_factor(session, RULES, people.id, row.technique) == table.focus_pct / 100
    assert await research_depth.focus_factor(session, RULES, people.id, Technique.SAILING) == table.unfocused_pct / 100


async def test_a_held_focus_is_kept_against_the_scholars(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session)
    people = await folk(session, realm, "Vel Folk")
    session.add_all([level(people.id, B.CIVICS, 1), level(people.id, B.SEAFARING, 1)])
    session.add(
        ResearchFocusRow(holder_entity_id=people.id, technique=Technique.SAILING, chooser=ResearchChooser.GOD, options=[], epoch=1, locked=["technique"])
    )
    await session.flush()
    await research_depth.set_focus(ctx, research_depth.DepthTally())
    row = await session.get(ResearchFocusRow, people.id)
    assert row is not None and row.technique is Technique.SAILING and row.chooser is ResearchChooser.GOD


async def test_a_great_debt_boosts_banking_once(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session)
    lender = await folk(session, realm, "Coin Folk")
    other = await folk(session, realm, "Debt Folk")
    session.add(
        LoanRow(
            lender_entity_id=lender.id,
            borrower_entity_id=other.id,
            principal=RULES.research_depth.great_debt,
            interest_pct=5,
            issued_epoch=ctx.epoch,
            due_epoch=ctx.epoch + 5,
            status=LoanStatus.OPEN,
            purpose="trade",
        )
    )
    await session.flush()
    tally = research_depth.DepthTally()
    await research_depth.deeds_push_research(ctx, tally)
    boosts = list(await session.scalars(select(ResearchBoostRow).where(ResearchBoostRow.holder_entity_id == lender.id)))
    assert {row.technique for row in boosts} == {Technique.BANKING, Technique.DOUBLE_ENTRY}
    assert all(row.trigger is BoostTrigger.GREAT_DEBT and row.progress == RULES.research_depth.boost_progress for row in boosts)
    progress = await session.get(ResearchProgressRow, (lender.id, Technique.BANKING))
    assert progress is not None and progress.progress == RULES.research_depth.boost_progress
    await research_depth.deeds_push_research(ctx, research_depth.DepthTally())
    again = list(await session.scalars(select(ResearchBoostRow).where(ResearchBoostRow.holder_entity_id == lender.id)))
    assert len(again) == len(boosts)


async def test_neighbours_who_know_a_technique_speed_it(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session)
    slow = await folk(session, realm, "Slow Folk")
    near = await folk(session, realm, "Near Folk")
    atlas = await RegionAtlas.load(session)
    assert await research_depth.catch_up(ctx, atlas, slow.id, Technique.SAILING) == 1
    session.add(HolderTechniqueRow(holder_entity_id=near.id, technique=Technique.SAILING, since_epoch=1, secret=False))
    await session.flush()
    assert await research_depth.catch_up(ctx, atlas, slow.id, Technique.SAILING) == 1 + RULES.research_depth.catch_up_pct / 100


async def test_an_institution_is_born_spreads_and_a_refusal_holds_research_back(session: AsyncSession, realm: Realm) -> None:
    rules = replace(RULES, research_depth=replace(RULES.research_depth, spread_pct=100, origin_trade=1))
    ctx = make_ctx(session, rules)
    home = await make(session, "Ledger Town", EntityType.SETTLEMENT, realm.world.id, location_id=realm.region.id, population=4000, prosperity=90)
    partner = await make(session, "Far Folk", EntityType.PEOPLE, realm.world.id, location_id=realm.far_region.id, population=4000)
    scholar = await make(session, "Ama Reed", EntityType.MORTAL, realm.world.id, location_id=home.id)
    await bond(session, home.id, partner.id, BondKind.TRADES_WITH)
    session.add(HolderTechniqueRow(holder_entity_id=home.id, technique=Technique.BUREAUCRACY, since_epoch=1, secret=False))
    session.add(SkillRow(holder_node_id=scholar.id, skill=SkillKind.LAW, level=40, xp=0, peak=40, last_used_epoch=1, source=SkillSource.PRACTICE))
    await session.flush()
    tally = research_depth.DepthTally()
    await research_depth.institutions_round(ctx, tally)
    born = await session.get(InstitutionRow, (Technique.BUREAUCRACY, home.id))
    spread = await session.get(InstitutionRow, (Technique.BUREAUCRACY, partner.id))
    assert born is not None and born.origin and born.embraced
    assert spread is not None and not spread.embraced and tally.counts["institutions_spread"] == 1
    assert await institution_factor(session, rules, home.id) > 1
    await research_depth.institutions_round(ctx, research_depth.DepthTally())
    assert spread.refused_epochs == 1 and await institution_factor(session, rules, partner.id) < 1


async def test_a_research_agreement_lifts_the_party_behind(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session)
    ahead = await folk(session, realm, "Star Folk")
    behind = await folk(session, realm, "Dusk Folk")
    session.add_all([level(ahead.id, B.CIVICS, 3), level(behind.id, B.CIVICS, 1)])
    await session.flush()
    await sign(
        ctx,
        TreatyKind.TRADE_PACT,
        [(ahead.id, PartyRole.SIGNATORY), (behind.id, PartyRole.SIGNATORY)],
        clauses=[Clause(ClauseKind.RESEARCH_AGREEMENT, ahead.id, behind.id)],
        witnessed=False,
    )
    tally = research_depth.DepthTally()
    await research_depth.share_agreements(ctx, tally)
    gained = await session.get(ResearchProgressRow, (behind.id, Technique.ORAL_LAW))
    assert gained is not None and gained.progress > 0 and tally.counts["agreement_shares"] >= 1
    assert await session.get(ResearchProgressRow, (ahead.id, Technique.ORAL_LAW)) is None


async def test_adopting_banking_moves_values_and_classes(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session)
    people = await folk(session, realm, "Mint Folk")
    await society(session, people.id)
    session.add(HolderTechniqueRow(holder_entity_id=people.id, technique=Technique.BANKING, since_epoch=ctx.epoch, secret=False))
    await session.flush()
    society_row = await session.get(CommunitySocietyRow, people.id)
    assert society_row is not None
    merchants = society_row.share_merchant
    assert await research_depth.changes_of_adoption(ctx) == 1
    value = await session.get(CultureValueRow, (people.id, ValueAxis.WEALTH))
    assert value is not None and value.value > 0
    assert society_row.share_merchant > merchants
    total = sum(getattr(society_row, f"share_{item.value}") for item in SocialClass)
    assert total == pytest.approx(100)


async def test_blue_water_navigation_needs_its_branches_and_cartography(session: AsyncSession, realm: Realm) -> None:
    people = await folk(session, realm, "Wave Folk")
    session.add_all([level(people.id, B.ASTRONOMY, 2), level(people.id, B.SHIPBUILDING, 1)])
    await session.flush()
    assert not await research_depth.capable(session, people.id, Capability.BLUE_WATER_NAVIGATION)
    session.add(HolderTechniqueRow(holder_entity_id=people.id, technique=Technique.CARTOGRAPHY, since_epoch=1, secret=False))
    await session.flush()
    assert await research_depth.capable_among(session, [people.id], Capability.BLUE_WATER_NAVIGATION) == {people.id}


async def test_a_creed_its_founders_cannot_teach_is_skipped_by_the_engine_and_refused_to_a_tool(
    session: AsyncSession, realm: Realm, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = make_ctx(session)
    founder = await make(session, "Iro Vane", EntityType.MORTAL, realm.world.id, location_id=realm.region.id)

    async def lawful(_session: AsyncSession, _node_id: int) -> dict[ValueAxis, int]:
        return {ValueAxis.TRADITION: 80}

    monkeypatch.setattr(ideology, "values_for", lawful)
    assert await ideology.teachable(ctx, founder, [IdeologyTenet.LEGALISM]) == []
    assert await ideology.found(ctx, founder) is None
    with pytest.raises(ValidationFailedError):
        await ideology.found_school(ctx, founder, [IdeologyTenet.LEGALISM])
    session.add(HolderTechniqueRow(holder_entity_id=founder.id, technique=Technique.WRITTEN_LAW, since_epoch=1, secret=False))
    await session.flush()
    creed = await ideology.found(ctx, founder)
    assert creed is not None


async def test_the_god_sets_focus_institutions_and_boosts(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session)
    people = await folk(session, realm, "Lamp Folk")
    focus = await research_control.set_focus(ctx, people.id, Technique.LOGIC, [Technique.GUILDS], hold=True)
    assert focus is not None and focus.chooser is ResearchChooser.GOD and focus.locked == ["technique"]
    assert focus.options == [Technique.LOGIC.value, Technique.GUILDS.value]
    assert await research_control.set_focus(ctx, people.id, None, None, hold=False) is None
    with pytest.raises(ValidationFailedError):
        await research_control.set_institution(ctx, people.id, Technique.LOGIC, {}, [], present=True)
    founded = await research_control.set_institution(ctx, people.id, Technique.UNIVERSITIES, {"embraced": False, "refused_epochs": 3}, [], present=True)
    assert founded is not None and not founded.embraced and founded.refused_epochs == 3 and set(founded.locked) == {"embraced", "refused_epochs"}
    released = await research_control.set_institution(ctx, people.id, Technique.UNIVERSITIES, {}, ["embraced"], present=True)
    assert released is not None and released.locked == ["refused_epochs"]
    assert await research_control.set_institution(ctx, people.id, Technique.UNIVERSITIES, {}, [], present=False) is None
    boost = await research_control.grant_boost(ctx, people.id, Technique.PRINTING, BoostTrigger.GREAT_TRIAL, 30)
    progress = await session.get(ResearchProgressRow, (people.id, Technique.PRINTING))
    assert progress is not None and progress.progress == 30
    edited = await research_control.edit_boost(ctx, boost.id, {"progress": 12, "trigger": BoostTrigger.GREAT_DEBT.value})
    assert edited.progress == 12 and edited.trigger is BoostTrigger.GREAT_DEBT
    await research_control.remove_boost(ctx, boost.id)
    assert await session.get(ResearchBoostRow, boost.id) is None


async def test_civic_thought_quickens_research(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session)
    people = await folk(session, realm, "Quill Folk")
    assert await research.thought_factor(ctx, people.id, B.ASTRONOMY) == 1
    session.add_all(
        [
            HolderTechniqueRow(holder_entity_id=people.id, technique=Technique.NATURAL_PHILOSOPHY, since_epoch=1, secret=False),
            HolderTechniqueRow(holder_entity_id=people.id, technique=Technique.EMPIRICISM, since_epoch=1, secret=False),
        ]
    )
    await session.flush()
    table = RULES.technique_effects
    assert await research.thought_factor(ctx, people.id, B.ASTRONOMY) == 1 + (table.philosophy_pct + table.empiricism_pct) / 100
    assert await research.thought_factor(ctx, people.id, B.CIVICS) == 1 + table.empiricism_pct / 100


async def test_a_postal_service_speeds_letters(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session)
    sender = await folk(session, realm, "Post Folk")
    far = await make(session, "Far Post Folk", EntityType.PEOPLE, realm.world.id, location_id=realm.far_region.id, population=4000)
    atlas = await RegionAtlas.load(session)
    slow = await post.delay(ctx, atlas, sender.id, far.id, medium=Medium.LETTER, owner_id=sender.id)
    session.add(HolderTechniqueRow(holder_entity_id=sender.id, technique=Technique.POSTAL_SERVICE, since_epoch=1, secret=False))
    await session.flush()
    assert await post.posted(ctx, sender.id)
    assert await post.delay(ctx, atlas, sender.id, far.id, medium=Medium.LETTER, owner_id=sender.id) <= slow

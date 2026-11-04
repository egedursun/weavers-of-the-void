from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.culture import LanguageRegisterRow, LanguageStandingRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.mind import MemoryRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import LanguageRegister
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import ClauseKind
from aerona.domain.models.entity_stats import LanguageStats
from aerona.domain.models.phonology import Phonology
from aerona.engine.lore import language
from aerona.engine.polity.treaties import Clause, misread
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, chronicle_keys, context, link, make, settlement, tuned


async def tongue(
    realm: Realm, name: str, *, vowels: tuple[str, ...] = ("a", "e"), consonants: tuple[str, ...] = ("k", "t"), parent: int | None = None
) -> EntityRow:
    entity = await make(realm.session, name, EntityType.LANGUAGE, LanguageStats(spread=20), world_id=realm.world.id)
    phonology = Phonology(vowels=vowels, consonants=consonants, syllable_patterns=("CV",), min_syllables=1, max_syllables=3)
    realm.session.add(LanguageProfileRow(entity_id=entity.id, phonology=phonology, parent_language_id=parent, seed=name))
    await realm.session.flush()
    return entity


async def registers_of(session: AsyncSession, holder: int) -> dict[LanguageRegister, int]:
    rows = await session.scalars(select(LanguageRegisterRow).where(LanguageRegisterRow.holder_entity_id == holder))
    return {row.register: row.language_entity_id for row in rows}


async def test_hearth_and_market_registers_are_drawn_and_a_held_register_is_kept(realm: Realm) -> None:
    session = realm.session
    common, franca = await tongue(realm, "Ossic"), await tongue(realm, "Trader")
    home, market = await settlement(realm, "Ashford"), await settlement(realm, "Brindle")
    await link(session, home.id, common.id, BondKind.SPEAKS)
    await link(session, market.id, franca.id, BondKind.SPEAKS)
    await link(session, home.id, market.id, BondKind.TRADES_WITH)
    ctx = context(session, epoch=4)
    await language.learn_second(ctx, home.id, franca.id, 40)
    await language.derive_registers(ctx, {}, {}, franca.id)
    found = await registers_of(session, home.id)
    assert found[LanguageRegister.COMMON] == common.id
    assert found[LanguageRegister.TRADE] == franca.id
    row = await session.get(LanguageRegisterRow, (home.id, LanguageRegister.TRADE))
    assert row is not None
    row.language_entity_id, row.locked = common.id, ["language_entity_id"]
    await language.derive_registers(ctx, {}, {}, franca.id)
    assert (await registers_of(session, home.id))[LanguageRegister.TRADE] == common.id


async def test_courts_that_share_a_tongue_understand_each_other_though_their_people_do_not(realm: Realm) -> None:
    session = realm.session
    first, second, court = await tongue(realm, "Ossic"), await tongue(realm, "Varn"), await tongue(realm, "High Speech")
    left, right = await settlement(realm, "Ashford"), await settlement(realm, "Brindle")
    await link(session, left.id, first.id, BondKind.SPEAKS)
    await link(session, right.id, second.id, BondKind.SPEAKS)
    ctx = context(session, epoch=4)
    rules = Rules()
    assert await language.barrier(session, rules, left.id, right.id, 4) < 1
    await language.derive_registers(ctx, {left.id: court.id, right.id: court.id}, {}, None)
    courtly = LanguageRegister.COURT
    assert await language.register_barrier(session, rules, left.id, right.id, 4, ours=courtly, theirs=courtly) == 1.0


async def test_shared_sounds_raise_intelligibility_between_kin_tongues(realm: Realm) -> None:
    root = await tongue(realm, "Proto")
    alike = await tongue(realm, "Alike", parent=root.id)
    unlike = await tongue(realm, "Unlike", vowels=("u", "o"), consonants=("z", "q"), parent=root.id)
    rules = Rules()
    near = await language.compute(realm.session, rules, root.id, alike.id)
    far = await language.compute(realm.session, rules, root.id, unlike.id)
    assert near > far
    assert near - far == rules.interpreters.phonology_pct - round(rules.interpreters.phonology_pct / 3)


async def test_a_standardised_tongue_spreads_letters_faster(realm: Realm) -> None:
    session = realm.session
    spoken = await tongue(realm, "Ossic")
    home = await settlement(realm, "Ashford")
    await link(session, home.id, spoken.id, BondKind.SPEAKS)
    rules = Rules()
    plain = await language.script_factor(session, rules, home.id)
    session.add(LanguageStandingRow(language_entity_id=spoken.id, prestige=30, standardisation=100, prestige_parts={}, locked=[]))
    await session.flush()
    assert await language.standardisation_of(session, spoken.id) == 100
    assert await language.script_factor(session, rules, home.id) == plain * (1 + rules.prestige.standard_literacy_pct / 100)


async def test_a_misread_clause_between_strangers_is_a_breach(realm: Realm) -> None:
    session = realm.session
    first, second = await tongue(realm, "Ossic"), await tongue(realm, "Varn", vowels=("u",), consonants=("z",))
    left, right = await settlement(realm, "Ashford"), await settlement(realm, "Brindle")
    await link(session, left.id, first.id, BondKind.SPEAKS)
    await link(session, right.id, second.id, BondKind.SPEAKS)
    ctx = context(session, tuned(Rules(), interpreters={"misread_chance": 100}), epoch=4)
    clause = await misread(ctx, Clause(ClauseKind.TRIBUTE, left.id, right.id, {"amount": 10}))
    assert clause.params["misread"] is True
    assert clause.params["amount"] == 5
    assert "treaty.misread_breach" in await chronicle_keys(session)
    grudge = await session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == right.id, MemoryRow.subject_node_id == left.id))
    assert grudge is not None and grudge.magnitude < 0

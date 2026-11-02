import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.son_state import turn_order
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.chronicle import ChronicleDraft, ChronicleRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.lore import ChronicleRow, FolkBeliefRow, LexemeRow, MessageRow
from aerona.db.tables.meta import MapSnapshotRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.node import ActorKind
from aerona.domain.models.entity_stats import LanguageStats, SettlementStats
from aerona.domain.models.phonology import Phonology
from aerona.engine.primitives.folk_names import clashes, guarded_names
from aerona.engine.primitives.language_profile import DEFAULT_PHONOLOGY
from aerona.rules.registry import Rules
from aerona.services.integrity.folk_names import repair_belief_names
from aerona.services.player import canon, cosmic_orders, curation, languages, messages, settlements, son_tools
from aerona.services.player.scope import PlayerScope
from aerona.services.wiki import SettlementTier, settlement_tiers
from aerona.tools.framework.shared_inputs import WordInput
from aerona.tools.son.kin import SpokenIntent, intent_delta
from tests.services.player.factories import PlayerWorld, bond, chronicle_keys, make_entity, make_son

WORDS = ("karvelon", "tirnasul", "morvekan", "salterin", "veldranor", "kormalis", "tarvenik", "silmorak", "nerovat", "varkelith", "dorsimal", "lanterik")
STRICT_VOWELS = Phonology(vowels=("a",), consonants=("k", "l", "m", "n", "r", "t"), syllable_patterns=("CV", "CVC"), min_syllables=1, max_syllables=3)


async def speaking_people(session: AsyncSession, world: PlayerWorld) -> EntityRow:
    language = await make_entity(session, "Tarnic", EntityType.LANGUAGE, world_id=world.world.id, stats=LanguageStats(spread=10))
    phonology = DEFAULT_PHONOLOGY.model_copy(update={"sample_names": ("Kelar", "Mirnar", "Tovaren", "Salmik")})
    session.add(LanguageProfileRow(entity_id=language.id, phonology=phonology, seed="Tarnic"))
    for word in WORDS:
        session.add(LexemeRow(language_entity_id=language.id, word=word, meaning="thing", added_by_kind=ActorKind.ENGINE, epoch=1))
    people = await make_entity(session, "Tarfolk", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    await bond(session, people.id, language.id, BondKind.SPEAKS)
    await session.flush()
    return people


async def test_region_toggles_as_a_realm_of_the_dead(scope: PlayerScope, world: PlayerWorld) -> None:
    await canon.edit_record(scope, canon.EditRecord(entity_id=world.region.id, is_underworld=True))
    assert world.region.is_underworld
    await canon.edit_record(scope, canon.EditRecord(entity_id=world.region.id, is_underworld=False))
    assert not world.region.is_underworld
    people = await make_entity(scope.session, "Folk", EntityType.PEOPLE, world_id=world.world.id)
    with pytest.raises(ValidationFailedError):
        await canon.edit_record(scope, canon.EditRecord(entity_id=people.id, is_underworld=True))


async def test_chronicle_line_edit_collapses_repetition_and_hides(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    written = await ChronicleRepository(session).append(ChronicleDraft(2, ChronicleKind.WORLD, "A storm passed."))
    outcome = await curation.edit_chronicle_line(scope, curation.EditChronicleLine(chronicle_id=written.row.id, text="The Sand Language language spread."))
    assert written.row.text == "The Sand Language spread."
    assert outcome.values["text"] == "The Sand Language spread."
    await curation.edit_chronicle_line(scope, curation.EditChronicleLine(chronicle_id=written.row.id, visible=False))
    assert not written.row.visible
    with pytest.raises(ValidationFailedError):
        await curation.edit_chronicle_line(scope, curation.EditChronicleLine(chronicle_id=written.row.id, text="   "))


async def test_folk_god_name_never_echoes_the_god_and_can_be_derived_anew(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    people = await speaking_people(session, world)
    son = await make_son(session, "Velkar", world.world.id)
    belief = FolkBeliefRow(people_entity_id=people.id, god_node_id=son.id, local_name="Velkar", account="Velkar raised the hills.", epoch=2)
    session.add(belief)
    await session.flush()
    assert await repair_belief_names(session, scope.rules) == 1
    derived = belief.local_name
    assert derived is not None and not clashes(derived, guarded_names(son.name, son.title))
    assert derived in belief.account and "Velkar" not in belief.account
    outcome = await curation.rename_folk_god(scope, curation.BeliefTarget(people_id=people.id, son_id=son.id))
    assert belief.local_name == outcome.values["name"] and belief.local_name != derived
    assert "player.belief.renamed" in await chronicle_keys(session)


async def test_belief_edit_without_a_name_derives_one_from_the_language(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    people = await speaking_people(session, world)
    son = await make_son(session, "Morvain", world.world.id)
    await canon.edit_belief(scope, canon.EditBelief(people_id=people.id, son_id=son.id, narrative="He walks the tides."))
    belief = await session.get(FolkBeliefRow, (people.id, son.id))
    assert belief is not None and belief.local_name and not clashes(belief.local_name, guarded_names(son.name, son.title))


async def test_accepting_a_name_overrides_the_dialect(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    world.world.phonology = STRICT_VOWELS
    pending = await make_entity(session, "Unnamed Tale", EntityType.PLACE, world_id=world.world.id)
    pending.pending_name = True
    outcome = await curation.accept_name(scope, curation.AcceptName(entity_id=pending.id, name="Oruvel"))
    assert pending.name == "Oruvel" and not pending.pending_name
    assert outcome.values["overridden_letters"] == "e, o, u, v"
    assert "player.naming.accepted" in await chronicle_keys(session)


async def test_creator_adds_words_skipping_known_and_empty_ones(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    language = await make_entity(session, "Velic", EntityType.LANGUAGE, world_id=world.world.id, stats=LanguageStats(spread=5))
    command = languages.AddWords(
        language_id=language.id,
        words=[WordInput(word="karn", meaning="stone"), WordInput(word="Karn", meaning="rock"), WordInput(word="vel", meaning="river")],
    )
    outcome = await languages.add_lexicon_words(scope, command)
    stored = list(await session.scalars(select(LexemeRow.word).where(LexemeRow.language_entity_id == language.id).order_by(LexemeRow.id)))
    assert stored == ["karn", "vel"]
    assert outcome.values == {"added": 2, "skipped": 1}
    with pytest.raises(ValidationFailedError):
        await languages.add_lexicon_words(scope, languages.AddWords(language_id=language.id, words=[WordInput(word="karn", meaning="stone")]))


async def test_son_addresses_a_sibling_with_the_intent_effect(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    sibling = await make_son(session, "Morvain", world.world.id)
    outcome = await messages.address_sibling(
        scope, messages.AddressSibling(son_id=son.id, sibling_id=sibling.id, intent=SpokenIntent.THREAT, text="Leave my shores.")
    )
    expected = intent_delta(rules, son.charisma, SpokenIntent.THREAT)
    assert expected < 0 and outcome.values["delta"] == expected
    assert await SonRepository(session).relation(son.id, sibling.id) == outcome.values["relation"]
    message = await session.scalar(select(MessageRow))
    assert message is not None and message.intent is MessageIntent.THREAT and message.recipient_node_id == sibling.id
    assert "player.son.address" in await chronicle_keys(session)
    with pytest.raises(ValidationFailedError):
        await messages.address_sibling(scope, messages.AddressSibling(son_id=son.id, sibling_id=son.id, intent=SpokenIntent.LOVE, text="Me."))


async def test_pinned_sons_act_first_in_rank_order(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    fast = await make_son(session, "Fast", world.world.id)
    slow = await make_son(session, "Slow", world.world.id)
    pinned = await make_son(session, "Pinned", world.world.id)
    await son_tools.set_turn_rank(scope, son_tools.TurnRank(son_id=pinned.id, rank=1))
    assert [son.name for son, _ in turn_order([(fast, 90.0), (slow, 10.0), (pinned, 5.0)])] == ["Pinned", "Fast", "Slow"]
    await son_tools.set_turn_rank(scope, son_tools.TurnRank(son_id=pinned.id))
    assert [son.name for son, _ in turn_order([(fast, 90.0), (slow, 10.0), (pinned, 5.0)])] == ["Fast", "Slow", "Pinned"]


async def test_creator_seats_a_capital_over_the_most_populous(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    realm = await make_entity(session, "Ardmark", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    big = await make_entity(
        session, "Greatford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id, stats=SettlementStats(population=9000)
    )
    small = await make_entity(
        session, "Littlebury", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id, stats=SettlementStats(population=300)
    )
    await bond(session, realm.id, big.id, BondKind.RULES)
    await bond(session, realm.id, small.id, BondKind.RULES)
    epoch = world.cosmos.epoch
    assert (await settlement_tiers(session, rules, world.world.id, epoch))[big.id].tier is SettlementTier.CAPITAL
    await settlements.seat_capital(scope, settlements.SettlementTarget(settlement_id=small.id))
    tiers = await settlement_tiers(session, rules, world.world.id, epoch)
    assert tiers[small.id].tier is SettlementTier.CAPITAL and tiers[big.id].tier is not SettlementTier.CAPITAL
    await settlements.seat_capital(scope, settlements.SettlementTarget(settlement_id=big.id))
    assert not await EntityRepository(session).has_flag(small.id, EntityFlag.CAPITAL)
    lone = await make_entity(session, "Freehold", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    with pytest.raises(ValidationFailedError):
        await settlements.seat_capital(scope, settlements.SettlementTarget(settlement_id=lone.id))


async def test_snapshot_now_records_every_world(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    outcome = await cosmic_orders.snapshot_now(scope, cosmic_orders.Empty())
    rows = list(await session.scalars(select(MapSnapshotRow)))
    assert outcome.values["worlds"] == 1 and [(row.epoch, row.world_id) for row in rows] == [(world.cosmos.epoch, world.world.id)]


async def test_hidden_line_stays_out_of_the_feed(session: AsyncSession, scope: PlayerScope) -> None:
    written = await ChronicleRepository(session).append(ChronicleDraft(2, ChronicleKind.WORLD, "A quiet year."))
    await curation.edit_chronicle_line(scope, curation.EditChronicleLine(chronicle_id=written.row.id, visible=False))
    visible = list(await session.scalars(select(ChronicleRow.id).where(ChronicleRow.visible.is_(True))))
    assert written.row.id not in visible

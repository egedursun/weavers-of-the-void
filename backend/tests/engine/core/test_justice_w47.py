from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.crimes import CRIMES, PENALTY_WORDS, PUNISHMENTS, TRIALS
from aerona.catalog.laws import LAW_PARAMS
from aerona.catalog.taxes import TAXES
from aerona.db.tables.cycles import KinshipSystemRow
from aerona.db.tables.finance import TradePolicyRow
from aerona.db.tables.unions import UnionCustomRow
from aerona.domain.enums.cycles import KinshipDescent, ResidenceRule
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.finance import TradePolicyKind
from aerona.domain.enums.military import SabotageKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.mortal import CrimeKind, PunishmentKind
from aerona.domain.enums.polity import LawArea, LawKind, RevoltKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.unions import PartnerScope, PluralSide, UnionDescent, UnionDissolution, UnionForm, UnionResidence
from aerona.engine.demography.peoples import spousing_for
from aerona.engine.finance.policy import PolicyBook
from aerona.engine.law.offences import OWN_DETECTION, WIDE_OFFENCES
from aerona.engine.law.sentences import SENTENCES
from aerona.engine.military.sabotage import WIDER_SABOTAGE
from aerona.engine.mortal.justice import sentence
from aerona.engine.polity.revolt_causes import CAUSES
from aerona.engine.polity.revolts import REVOLTS
from aerona.engine.unions.axes import fresh_custom
from aerona.engine.unions.customs import DIVORCE_RULE, sides
from tests.engine.core.factories import CoreWorld, mortal, settlement
from tests.engine.core.test_minds_w44 import at

LEGACY_PUNISHMENTS = 16
LEGACY_SABOTAGE = 4


def test_every_crime_has_a_family_proof_and_a_place_in_the_penal_code() -> None:
    code = LAW_PARAMS[LawKind.PENAL_CODE]
    assert all(CRIMES[crime].evidence and crime.value in code for crime in CrimeKind)
    assert {spec.area for spec in CRIMES.values()} == set(LawArea)
    assert set(WIDE_OFFENCES) | OWN_DETECTION == set(CrimeKind)


def test_every_new_punishment_bears_an_effect_and_every_word_names_one_punishment() -> None:
    assert set(PENALTY_WORDS.values()) == set(PunishmentKind)
    assert len(PENALTY_WORDS) == len(PUNISHMENTS)
    assert len(SENTENCES) == len(PunishmentKind) - LEGACY_PUNISHMENTS
    assert all(spec.text for spec in TRIALS.values())


async def test_servitude_binds_the_condemned(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    culprit = await mortal(session, "Oru", world, world.regions[0].id)
    assert await sentence(ctx, culprit, CrimeKind.SMUGGLING, PunishmentKind.SERVITUDE)
    assert culprit.social_class is SocialClass.SERF_OR_SLAVE


async def test_the_banished_are_sent_to_more_than_one_town(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    home = await settlement(session, "Ardun", world, world.regions[0])
    for name in ("Belmar", "Corvel", "Dunhal", "Eskarn"):
        await settlement(session, name, world, world.regions[1])
    sent = set()
    for index in range(12):
        culprit = await mortal(session, f"Oru {index}", world, home.id)
        assert await sentence(ctx, culprit, CrimeKind.SMUGGLING, PunishmentKind.BANISHMENT_FROM_PLACE)
        sent.add(culprit.location_id)
    assert home.id not in sent and len(sent) > 1


def test_a_people_s_values_set_its_union_axes_without_gender() -> None:
    kinship = KinshipSystemRow(descent=KinshipDescent.THROUGH_SECOND_LINE, residence=ResidenceRule.WITH_FIRST_FAMILY)
    spousing = spousing_for({ValueAxis.HIERARCHY: -40, ValueAxis.KINSHIP: 40})
    custom = fresh_custom(7, spousing, kinship, 10)
    assert custom.form is UnionForm.PLURAL and custom.plural_side is PluralSide.SECOND
    assert custom.endogamy is PartnerScope.PEOPLE
    assert custom.descent is UnionDescent.THROUGH_SECOND
    assert custom.residence is UnionResidence.WITH_FIRST_FAMILY
    assert custom.exchange_value == 10
    assert DIVORCE_RULE[UnionDissolution.NONE] == "forbidden"


def test_residence_moves_the_side_the_custom_names(world: CoreWorld) -> None:
    first, second = world.people, world.language
    custom = UnionCustomRow(people_entity_id=1, residence=UnionResidence.WITH_SECOND_FAMILY)
    assert sides(custom, first, second) == (first, second)
    custom.residence = UnionResidence.SEPARATE
    assert sides(custom, first, second) is None


def test_trade_policies_reach_the_terms_of_a_sale() -> None:
    book = PolicyBook(member_of={1: 10, 2: 20})
    book.policies[20] = [
        TradePolicyRow(issuer_node_id=20, kind=TradePolicyKind.TARIFF, rate_pct=30, since_epoch=0),
        TradePolicyRow(issuer_node_id=20, kind=TradePolicyKind.QUOTA, rate_pct=40, since_epoch=0),
        TradePolicyRow(issuer_node_id=20, kind=TradePolicyKind.PRICE_CONTROL, rate_pct=10, since_epoch=0),
    ]
    terms = book.terms(1, 2, CommodityKind.GRAIN)
    assert (terms.tariff_pct, terms.quota_pct, terms.price_cap_pct) == (30, 40, 10)
    book.policies[20].append(TradePolicyRow(issuer_node_id=20, kind=TradePolicyKind.FREE_TRADE, partner_node_id=10, rate_pct=1, since_epoch=0))
    book.policies[10] = [TradePolicyRow(issuer_node_id=10, kind=TradePolicyKind.FREE_TRADE, partner_node_id=20, rate_pct=1, since_epoch=0)]
    assert book.terms(1, 2, CommodityKind.GRAIN).tariff_pct == 0
    book.policies[10].append(TradePolicyRow(issuer_node_id=10, kind=TradePolicyKind.EXPORT_BAN, rate_pct=1, since_epoch=0))
    assert book.terms(1, 2, CommodityKind.GRAIN).blocked


def test_every_tax_revolt_and_sabotage_is_typed_and_reachable() -> None:
    assert set(TAXES) and all(spec.classes for spec in TAXES.values())
    assert {kind for kind, _ in CAUSES} | {RevoltKind.PEASANT} == set(RevoltKind)
    assert all(REVOLTS[kind].aims for kind in RevoltKind)
    assert len(WIDER_SABOTAGE) == len(SabotageKind) - LEGACY_SABOTAGE

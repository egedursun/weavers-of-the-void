from aerona.db.tables.culture import TraditionParticipationRow, TraditionProfileRow
from aerona.db.tables.discovery import ArtFormProfileRow
from aerona.domain.enums.culture import ArtMode, TraditionFunction
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import TraditionStats
from aerona.engine.lore.art_forms import found_form, tend_forms
from tests.engine.society.factories import Realm, context, make, settlement


async def kept(realm: Realm, town_id: int, kind: TraditionFunction, *, locked: list[str] | None = None) -> TraditionParticipationRow:
    tradition = await make(realm.session, f"The {kind.value} of {town_id}", EntityType.TRADITION, TraditionStats(), world_id=realm.world.id)
    realm.session.add(TraditionProfileRow(tradition_entity_id=tradition.id, kind=kind, cost={}, effects={}, locked=[]))
    row = TraditionParticipationRow(tradition_entity_id=tradition.id, community_entity_id=town_id, participation=50, locked=locked or [])
    realm.session.add(row)
    await realm.session.flush()
    return row


async def form_at(realm: Realm, name: str, *, occasions: list[str], sacred: bool) -> tuple[int, ArtFormProfileRow]:
    ctx = context(realm.session)
    town = await settlement(realm, name)
    form = await found_form(ctx, town, next(iter(ArtMode)), f"The songs of {name}", founder=None, parents=[], structure={})
    profile = await realm.session.get(ArtFormProfileRow, form.id)
    assert profile is not None
    profile.occasions, profile.sacred = occasions, sacred
    await realm.session.flush()
    return town.id, profile


async def test_a_form_kept_at_an_occasion_draws_people_to_that_rite_only(realm: Realm) -> None:
    town, _ = await form_at(realm, "Corrin", occasions=[TraditionFunction.FESTIVAL.value], sacred=False)
    feast = await kept(realm, town, TraditionFunction.FESTIVAL)
    fast = await kept(realm, town, TraditionFunction.FAST)
    result = await tend_forms(context(realm.session))
    assert result["traditions_hallowed"] == 1
    assert feast.participation > 50 and fast.participation == 50


async def test_a_sacred_form_hallows_every_rite_its_holders_keep_but_a_held_share(realm: Realm) -> None:
    town, _ = await form_at(realm, "Dunmere", occasions=[], sacred=True)
    feast = await kept(realm, town, TraditionFunction.FESTIVAL)
    fast = await kept(realm, town, TraditionFunction.FAST)
    frozen = await kept(realm, town, TraditionFunction.MOURNING, locked=["participation"])
    result = await tend_forms(context(realm.session))
    assert result["traditions_hallowed"] == 2
    lift = context(realm.session).rules.art_forms.sacred_tradition_pct
    assert feast.participation == fast.participation == 50 + round(50 * lift / 100)
    assert frozen.participation == 50


async def test_a_plain_form_hallows_nothing(realm: Realm) -> None:
    town, _ = await form_at(realm, "Eldham", occasions=[], sacred=False)
    feast = await kept(realm, town, TraditionFunction.FESTIVAL)
    assert (await tend_forms(context(realm.session)))["traditions_hallowed"] == 0
    assert feast.participation == 50

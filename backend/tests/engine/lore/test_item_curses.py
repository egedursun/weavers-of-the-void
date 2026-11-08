from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow, TraitRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import CurseKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import MemoryKind, TraitKind, ValueAxis, ValueHolder
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.models.entity_stats import ItemStats
from aerona.engine.cosmos.sanity import sanity_of
from aerona.engine.lore import items
from aerona.engine.mind.book import stored_values
from aerona.engine.phases.made_things import afflict
from aerona.engine.polity.book import RealmBook
from aerona.engine.primitives.stats import stat
from tests.engine.society.factories import Realm, context, link, make, mortal, settlement
from tests.engine.statecraft.crowns import crown


async def cursed(realm: Realm, bearer: EntityRow, curse: CurseKind, strength: int = 100) -> EntityRow:
    ctx = context(realm.session)
    item = await make(
        realm.session, f"Cursed {curse.value}", EntityType.ITEM, ItemStats(damage=10, protection=0, might=5, curse=strength), world_id=realm.world.id
    )
    profile = await items.profile_of(ctx, item)
    profile.curse = curse
    await link(realm.session, bearer.id, item.id, BondKind.OWNS)
    await realm.session.flush()
    return item


async def realm_town(realm: Realm) -> tuple[EntityRow, EntityRow, EntityRow]:
    polity, _ = await crown(realm, "Velmar")
    town = await settlement(realm, "Velmar Town")
    ruler = await mortal(realm, "Queen Otta", location_id=town.id)
    realm.session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    realm.session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, powers=[]))
    await realm.session.flush()
    return polity, town, ruler


async def ill_will(realm: Realm, holder: int, subject: int) -> MemoryRow | None:
    return await realm.session.scalar(
        select(MemoryRow).where(MemoryRow.holder_node_id == holder, MemoryRow.subject_node_id == subject, MemoryRow.kind == MemoryKind.ILL_WILL)
    )


async def test_a_betraying_curse_turns_its_bearer_against_the_ruler(realm: Realm) -> None:
    _, town, ruler = await realm_town(realm)
    bearer = await mortal(realm, "Sir Halden", location_id=town.id)
    item = await cursed(realm, bearer, CurseKind.BETRAYAL)
    ctx = context(realm.session)
    assert await afflict(ctx, await RealmBook.load(realm.session), item) == CurseKind.BETRAYAL.value
    memory = await ill_will(realm, bearer.id, ruler.id)
    assert memory is not None and memory.magnitude < 0 and item.name in (memory.note or "")


async def test_a_ruler_bearing_a_betraying_curse_turns_against_the_realm_itself(realm: Realm) -> None:
    polity, _, ruler = await realm_town(realm)
    item = await cursed(realm, ruler, CurseKind.BETRAYAL)
    assert await afflict(context(realm.session), await RealmBook.load(realm.session), item) == CurseKind.BETRAYAL.value
    assert await ill_will(realm, ruler.id, polity.id) is not None


async def test_a_betraying_curse_outside_any_realm_does_nothing(realm: Realm) -> None:
    wanderer = await mortal(realm, "Wanderer")
    item = await cursed(realm, wanderer, CurseKind.BETRAYAL)
    assert await afflict(context(realm.session), await RealmBook.load(realm.session), item) is None


async def test_misfortune_drains_the_bearers_home(realm: Realm) -> None:
    town = await settlement(realm, "Lowmere", prosperity=50)
    bearer = await mortal(realm, "Tam", location_id=town.id)
    item = await cursed(realm, bearer, CurseKind.MISFORTUNE)
    ctx = context(realm.session)
    assert await afflict(ctx, await RealmBook.load(realm.session), item) == CurseKind.MISFORTUNE.value
    assert stat(town, "prosperity") == 50 - ctx.rules.item_curses.misfortune_pct


async def test_madness_and_wasting_harm_a_mortal_bearer(realm: Realm) -> None:
    ctx = context(realm.session)
    mad = await mortal(realm, "Ilse")
    sane_before = sanity_of(ctx.rules, mad)
    await afflict(ctx, await RealmBook.load(realm.session), await cursed(realm, mad, CurseKind.MADNESS))
    assert sanity_of(ctx.rules, mad) < sane_before
    wasting = await mortal(realm, "Orm", hp=100)
    await afflict(ctx, await RealmBook.load(realm.session), await cursed(realm, wasting, CurseKind.WASTING))
    assert (stat(wasting, "hp") or 0) < 100


async def test_a_strong_bloodthirst_makes_its_bearer_martial_and_wrathful(realm: Realm) -> None:
    ctx = context(realm.session)
    bearer = await mortal(realm, "Brask")
    await afflict(ctx, await RealmBook.load(realm.session), await cursed(realm, bearer, CurseKind.BLOODTHIRST))
    values = await stored_values(realm.session, ValueHolder.PERSONAL, bearer.id)
    assert values.get(ValueAxis.MARTIAL, 0) > 0 and values.get(ValueAxis.MERCY, 0) < 0
    trait = await realm.session.scalar(select(TraitRow).where(TraitRow.node_id == bearer.id, TraitRow.trait == TraitKind.WRATHFUL))
    assert trait is not None


async def test_a_faint_bloodthirst_stirs_values_without_wrath(realm: Realm) -> None:
    ctx = context(realm.session)
    bearer = await mortal(realm, "Pell")
    await afflict(
        ctx, await RealmBook.load(realm.session), await cursed(realm, bearer, CurseKind.BLOODTHIRST, strength=ctx.rules.item_powers.wrathful_curse - 1)
    )
    trait = await realm.session.scalar(select(TraitRow).where(TraitRow.node_id == bearer.id, TraitRow.trait == TraitKind.WRATHFUL))
    assert trait is None


async def test_an_uncursed_or_unowned_thing_does_nothing(realm: Realm) -> None:
    ctx = context(realm.session)
    bearer = await mortal(realm, "Kell")
    item = await cursed(realm, bearer, CurseKind.NONE)
    assert await afflict(ctx, await RealmBook.load(realm.session), item) is None
    loose = await make(realm.session, "Loose Ring", EntityType.ITEM, ItemStats(damage=0, protection=0, might=0, curse=90), world_id=realm.world.id)
    (await items.profile_of(ctx, loose)).curse = CurseKind.MADNESS
    assert await afflict(ctx, await RealmBook.load(realm.session), loose) is None

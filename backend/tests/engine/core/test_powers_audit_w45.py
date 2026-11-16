from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.collective import MovementRow
from aerona.db.tables.concealment import HiddenTruthRow, PublicKnowledgeRow
from aerona.db.tables.equipment import EquipmentModelRow, EquipmentStoreRow
from aerona.db.tables.folkways import PurityRankRow, PurityRow
from aerona.db.tables.industry import CommunityIndustryRow
from aerona.db.tables.intrigue import IdentityRow
from aerona.db.tables.mind import CultureValueRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.polity import PolityMemberRow, TreatyProfileRow
from aerona.db.tables.powers import GiftedAttitudeRow, PowerRow
from aerona.domain.enums.arcana import SpellForm, SpellTechnique
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.concealment import BreachCause, ConcealScope, HiddenTruthKind, TruthAttitude
from aerona.domain.enums.culture import MagicSource
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.equipment import ArmamentSlot, EquipmentFamily
from aerona.domain.enums.intrigue import IdentityReason
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.minds import MindSeat
from aerona.domain.enums.polity import LawKind, TreatyKind, TreatyStatus
from aerona.domain.enums.powers import GiftedAttitude, PowerDeviceEffect, PowerOrigin, PowerState, PowerVisibility
from aerona.domain.models.entity_stats import FactionStats, PeopleStats, PolityStats, TreatyStats
from aerona.engine.concealment.truths import breach, passing_trade, reveal_or_fade
from aerona.engine.minds.profiles import profile_of
from aerona.engine.polity.laws import enact
from aerona.engine.powers.backfill import built_in_source
from aerona.engine.powers.society import keep_apart, power_castes, train_in_bands
from aerona.engine.powers.sources import density_row, rite_draw
from aerona.engine.powers.use import use
from aerona.engine.primitives.queries import connect
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement
from tests.engine.core.test_minds_w44 import at


def power_for(holder_id: int, technique: SpellTechnique, form: SpellForm, **values: object) -> PowerRow:
    return PowerRow(
        holder_node_id=holder_id,
        technique=technique,
        form=form,
        strength=values.get("strength", 5),
        control=values.get("control", 80),
        origin=PowerOrigin.BORN,
        state=values.get("state", PowerState.ACTIVE),
        visibility=values.get("visibility", PowerVisibility.SUBTLE),
        strain=0,
        strain_cap=30,
        uses=0,
        gained_epoch=1,
        locked=[],
    )


async def test_the_gifted_of_a_hunting_realm_keep_their_names_apart_from_their_powers(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Hushfield", world, world.regions[0])
    realm = await entity(session, "The Watching Realm", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
    gifted = await mortal(session, "Brand Ollo", world, town.id)
    session.add(power_for(gifted.id, SpellTechnique.DESTROY, SpellForm.FIRE, visibility=PowerVisibility.OVERT))
    await session.flush()
    ctx = await at(session, 2)
    await enact(ctx, town, LawKind.POWER_LAW, {"level": "hunted", "mind_powers": "banned"})
    assert await keep_apart(ctx) == 1
    identity = await session.get(IdentityRow, gifted.id)
    assert identity is not None and identity.reason is IdentityReason.HIDDEN_POWER


async def test_a_band_trains_its_members_and_wakes_their_latent_gifts(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Bandmoor", world, world.regions[0])
    member = await mortal(session, "Tess", world, town.id)
    band = await entity(session, "the band of Tess", EntityType.FACTION, FactionStats(), world_id=world.world.id)
    await connect(session, member.id, band.id, BondKind.MEMBER_OF, 1, description="one of the band")
    power = power_for(member.id, SpellTechnique.PERCEIVE, SpellForm.MIND, control=10, state=PowerState.LATENT)
    session.add(power)
    await session.flush()
    assert await train_in_bands(await at(session, 2)) == 1
    assert power.control > 10 and power.state is PowerState.EMERGING


async def test_an_overt_use_breaks_the_accord_that_kept_a_truth(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Pactford", world, world.regions[0])
    hidden = await mortal(session, "Wren", world, town.id)
    accord = await entity(session, "The Quiet Accord", EntityType.TREATY, TreatyStats(), world_id=world.world.id)
    session.add(TreatyProfileRow(treaty_entity_id=accord.id, kind=TreatyKind.PEACE, status=TreatyStatus.IN_FORCE, signed_epoch=1, locked=[]))
    truth = HiddenTruthRow(title="the quiet folk", subject_node_id=hidden.id, kind=HiddenTruthKind.PRESENCE, strength=0, accord_entity_id=accord.id, locked=[])
    session.add(truth)
    await session.flush()
    await breach(await at(session, 2), truth, BreachCause.OVERT_USE, place_id=town.id)
    profile = await session.get(TreatyProfileRow, accord.id)
    assert profile is not None and profile.status is TreatyStatus.BROKEN


async def test_a_feared_revelation_sets_off_panic_and_hardens_the_people_against_the_gifted(session: AsyncSession, world: CoreWorld) -> None:
    folk = await entity(session, "The Fearful", EntityType.PEOPLE, PeopleStats(population=300), world_id=world.world.id)
    town = await settlement(session, "Dreadmarch", world, world.regions[0])
    await connect(session, town.id, folk.id, BondKind.DESCENDS_FROM, 1)
    session.add(CultureValueRow(entity_id=folk.id, axis=ValueAxis.TRADITION, value=60))
    session.add(GiftedAttitudeRow(people_entity_id=folk.id, attitude=GiftedAttitude.ORDINARY, locked=[]))
    hidden = await mortal(session, "Ash", world, town.id)
    truth = HiddenTruthRow(
        title="the gifted among us", subject_node_id=hidden.id, kind=HiddenTruthKind.PRESENCE, hidden_from=ConcealScope.A_PEOPLE, strength=0, locked=[]
    )
    session.add(truth)
    await session.flush()
    known = PublicKnowledgeRow(truth_id=truth.id, population_node_id=town.id, know_pct=90, believe_pct=90, attitude=TruthAttitude.RUMOURED, locked=[])
    session.add(known)
    await session.flush()
    await reveal_or_fade(await at(session, 2), truth, known)
    assert known.attitude is TruthAttitude.FEARED
    assert await session.scalar(select(MovementRow).where(MovementRow.settlement_entity_id == town.id)) is not None
    attitude = await session.get(GiftedAttitudeRow, folk.id)
    assert attitude is not None and attitude.attitude is GiftedAttitude.FEARED


async def test_a_mind_seated_in_a_made_thing_cannot_be_swayed_and_a_dampener_weakens_a_power(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Coilmere", world, world.regions[0])
    user = await mortal(session, "Pell", world, town.id)
    seated = await mortal(session, "Unit", world, town.id)
    ctx = await at(session, 2)
    mind = await profile_of(session, ctx.rules, seated.id, 2)
    mind.seat = MindSeat.NETWORK
    sway = power_for(user.id, SpellTechnique.CONTROL, SpellForm.EMOTION)
    session.add(sway)
    await session.flush()
    outcome = await use(ctx, sway, user, seated)
    assert outcome.resisted and outcome.done is None
    victim = await mortal(session, "Mott", world, town.id)
    model = EquipmentModelRow(
        name="a dampening ring",
        description="",
        world_id=world.world.id,
        slot=ArmamentSlot.HAND_WEAPON,
        family=EquipmentFamily.STAFF,
        quality=50,
        tech_level=0,
        power_effect=PowerDeviceEffect.DAMPEN,
        created_epoch=1,
        locked=[],
    )
    session.add(model)
    await session.flush()
    session.add(EquipmentStoreRow(holder_node_id=victim.id, model_id=model.id, count=1, locked=[]))
    strike = power_for(user.id, SpellTechnique.DESTROY, SpellForm.FORCE, strength=10)
    session.add(strike)
    await session.flush()
    assert (await session.get(MindProfileRow, seated.id)) is not None
    damped = await use(await at(session, 3), strike, user, victim)
    assert damped.done is not None


async def test_where_a_people_honours_the_gifted_those_born_with_powers_form_a_caste(session: AsyncSession, world: CoreWorld) -> None:
    folk = await entity(session, "The Bright Folk", EntityType.PEOPLE, PeopleStats(population=200), world_id=world.world.id)
    town = await settlement(session, "Lumenford", world, world.regions[0])
    await connect(session, town.id, folk.id, BondKind.DESCENDS_FROM, 1)
    born = await mortal(session, "Sola", world, town.id)
    session.add(power_for(born.id, SpellTechnique.CREATE, SpellForm.LIGHT))
    session.add(GiftedAttitudeRow(people_entity_id=folk.id, attitude=GiftedAttitude.HONOURED, locked=[]))
    await session.flush()
    assert await power_castes(await at(session, 2)) == 1
    purity = await session.get(PurityRow, born.id)
    rank = await session.get(PurityRankRow, purity.rank_id) if purity is not None and purity.rank_id is not None else None
    assert rank is not None and rank.standing > 50


async def test_hidden_folk_passing_among_the_rest_feed_a_black_market(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Underlane", world, world.regions[0])
    hidden = await mortal(session, "Moss", world, town.id)
    session.add(CommunityIndustryRow(community_node_id=town.id, spent={}, short={}, epoch=1, black_market=0, locked=[]))
    truth = HiddenTruthRow(title="the quiet ones", subject_node_id=hidden.id, kind=HiddenTruthKind.PRESENCE, strength=100, by_passing=True, locked=[])
    session.add(truth)
    await session.flush()
    assert await passing_trade(await at(session, 2), truth) == 1
    row = await session.get(CommunityIndustryRow, town.id)
    assert row is not None and row.black_market > 0


async def test_a_rite_draws_down_the_density_of_its_source_in_its_land(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Leyhollow", world, world.regions[0])
    caster = await mortal(session, "Oriel", world, town.id)
    ctx = await at(session, 2)
    ley = await built_in_source(session, MagicSource.LEY)
    density = await density_row(ctx, ley, world.regions[0].id)
    before = density.density
    factor = await rite_draw(ctx, caster, MagicSource.LEY, 5)
    assert factor > 0 and density.density < before and density.last_drawn_epoch == 2

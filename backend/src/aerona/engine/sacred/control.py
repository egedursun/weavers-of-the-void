from sqlalchemy import select

from aerona.catalog.sacred import MODEL_STRATA, PLACE_SPIRITS, SACRAMENT_GUARDS
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.culture import ProphecyConditionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.faith import AfterlifeStratumRow, CultTenetRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.sacred import (
    AFTERLIFE_FIELDS,
    CLIMATE_FIELDS,
    DIVINATION_FIELDS,
    DOCTRINE_SACRAMENT_FIELDS,
    FEEDING_FIELDS,
    FORESIGHT_FIELDS,
    GENIUS_FIELDS,
    MILLENARIAN_FIELDS,
    MODEL_FIELDS,
    MYSTIC_FIELDS,
    OFFICE_FIELDS,
    PETITION_FIELDS,
    SACRAMENT_FIELDS,
    SYSTEM_FIELDS,
    THEODICY_FIELDS,
    VISION_FIELDS,
    DivinationRow,
    DivinationSystemRow,
    DoctrineAfterlifeRow,
    DoctrineSacramentRow,
    FaithClimateRow,
    ForecastModelRow,
    ForesightRow,
    GeniusLocusRow,
    GodFeedingRow,
    MillenarianRow,
    MysticRow,
    PetitionRow,
    SacramentRow,
    SpiritOfficeRow,
    TheodicyCrisisRow,
    VisionRow,
)
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.culture import ProphecyPredicate
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import TerrainKind
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.mind import Emotion
from aerona.domain.enums.sacred import (
    AfterlifeModel,
    BureauRank,
    DivinationKind,
    DivinationQuestion,
    ForesightSource,
    GeniusLocusKind,
    OmenVerdict,
    PetitionKind,
    PetitionStatus,
    SacramentKind,
    SacramentProtection,
    TheodicyCause,
    TheodicyResolution,
    VisionKind,
)
from aerona.engine.collective.control import of_type, saved
from aerona.engine.context import TickContext
from aerona.engine.cycles.control import node_exists
from aerona.engine.divine.control import apply, require_god
from aerona.engine.divine.standing import standing_row
from aerona.engine.faith.judgement import new_stratum
from aerona.engine.gatherings.control import Values, allowed, found
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.sacred.bureau import BureauTally, file_petition, settle
from aerona.engine.sacred.foresight import args_for, consult, court_systems, foresee, model_realm, proclaim, take_up, validity_of
from aerona.engine.sacred.guards import perform
from aerona.engine.sacred.mysteries import MysteryTally, become_mystic, begin_millenarian, open_crisis, see_vision
from aerona.engine.sacred.places import church_of, plagued_regions, realm_of_town, ruler_of
from aerona.engine.sacred.rites import climate_of, taught_model
from aerona.engine.sacred.spirits import bind_spirit, town_near

PLACES = frozenset({EntityType.PLACE, EntityType.SETTLEMENT, EntityType.HOUSE, EntityType.REGION})
SPIRITS = frozenset({EntityType.SPIRIT})
MORTALS = frozenset({EntityType.MORTAL})
TOWNS = frozenset({EntityType.SETTLEMENT})
CULTS = frozenset({EntityType.CULT})
PEOPLES = frozenset({EntityType.PEOPLE})
REALMS = frozenset({EntityType.POLITY})
FACTIONS = frozenset({EntityType.FACTION})
FORESEEN = frozenset({ProphecyPredicate.DIES.value, ProphecyPredicate.FALLS.value})


async def kind_for(ctx: TickContext, place: EntityRow, kind: GeniusLocusKind | None) -> GeniusLocusKind:
    if kind is not None:
        return kind
    if place.entity_type is EntityType.SETTLEMENT:
        return GeniusLocusKind.CITY
    if place.entity_type is EntityType.HOUSE:
        return GeniusLocusKind.HEARTH
    if place.entity_type is EntityType.REGION:
        land = await ctx.session.get(RegionEnvironmentRow, place.id)
        return GeniusLocusKind.SEA if land is not None and land.dominant_terrain is TerrainKind.SEA else GeniusLocusKind.WILDS
    profile = await ctx.session.get(PlaceProfileRow, place.id)
    found_kind = PLACE_SPIRITS.get(profile.kind) if profile is not None else None
    return found_kind or GeniusLocusKind.WILDS


async def raise_spirit(ctx: TickContext, place_id: int, kind: GeniusLocusKind | None, community_id: int | None, son_id: int | None) -> GeniusLocusRow:
    place = await of_type(ctx, place_id, PLACES, "a place, land, town or house")
    if await ctx.session.scalar(select(GeniusLocusRow.spirit_entity_id).where(GeniusLocusRow.place_entity_id == place.id).limit(1)) is not None:
        raise ValidationFailedError(f"{place.name} already has a spirit of its own.")
    community = await of_type(ctx, community_id, TOWNS, "a town") if community_id is not None else await town_near(ctx, place)
    return await bind_spirit(ctx, place, await kind_for(ctx, place, kind), community, son_id=son_id)


async def set_office(
    ctx: TickContext, spirit_id: int, rank: BureauRank, *, superior_id: int | None, overseer_id: int | None, jurisdiction_id: int | None
) -> SpiritOfficeRow:
    await of_type(ctx, spirit_id, SPIRITS, "a spirit")
    if superior_id is not None:
        await found(ctx, SpiritOfficeRow, superior_id, "superior office")
        if superior_id == spirit_id:
            raise ValidationFailedError("A spirit cannot answer to itself.")
    if overseer_id is not None:
        await require_god(ctx, overseer_id)
    if jurisdiction_id is not None:
        await node_exists(ctx, jurisdiction_id, "jurisdiction")
    row = await ctx.session.get(SpiritOfficeRow, spirit_id) or await saved(
        ctx, SpiritOfficeRow(spirit_entity_id=spirit_id, appointed_epoch=ctx.epoch, locked=[])
    )
    apply(
        row,
        {"rank": rank, "superior_spirit_id": superior_id, "overseer_node_id": overseer_id, "jurisdiction_entity_id": jurisdiction_id, "dismissed": False},
        [],
    )
    await ctx.session.flush()
    return row


async def appoint(ctx: TickContext, spirit_id: int, rank: BureauRank | None, son_id: int) -> SpiritOfficeRow:
    row = await found(ctx, SpiritOfficeRow, spirit_id, "spirit office")
    values: dict[str, object] = {"overseer_node_id": son_id}
    if rank is None:
        values["dismissed"] = True
    else:
        values["rank"], values["dismissed"] = rank, False
    apply(row, values, [])
    await reward_work(ctx, son_id, row.jurisdiction_entity_id)
    await ctx.session.flush()
    return row


async def reward_work(ctx: TickContext, god_id: int, community_id: int | None) -> None:
    community = await living_entity(ctx.session, community_id)
    if community is None or community.entity_type is not EntityType.SETTLEMENT:
        return
    standing = await standing_row(ctx, community.id, god_id)
    if "love" not in standing.locked:
        standing.love = clamp_int(standing.love + ctx.rules.celestial_bureaucracy.work_standing, 0, PERCENT)


async def lodge_petition(
    ctx: TickContext, petitioner_id: int, office_id: int, kind: PetitionKind, *, defendant_id: int | None, bribe: int, target_id: int | None = None
) -> PetitionRow:
    await node_exists(ctx, petitioner_id, "petitioner")
    if kind is PetitionKind.VENGEANCE:
        if target_id is None:
            raise ValidationFailedError("A petition for vengeance names the wrongdoer.")
        await node_exists(ctx, target_id, "wrongdoer")
    office = await found(ctx, SpiritOfficeRow, office_id, "spirit office")
    if office.dismissed:
        raise ValidationFailedError("That office stands empty.")
    if kind is PetitionKind.SUIT:
        if defendant_id is None:
            raise ValidationFailedError("A suit names the spirit it is brought against.")
        await of_type(ctx, defendant_id, SPIRITS, "a spirit")
    return await file_petition(ctx, petitioner_id, office, kind, defendant_id=defendant_id, bribe=bribe, target_id=target_id)


async def judge(ctx: TickContext, petition_id: int, granted: bool, son_id: int | None) -> PetitionRow:
    petition = await found(ctx, PetitionRow, petition_id, "petition")
    if petition.status not in {PetitionStatus.FILED, PetitionStatus.DELAYED, PetitionStatus.APPEALED}:
        raise ValidationFailedError("That petition is already settled.")
    office = await found(ctx, SpiritOfficeRow, petition.office_spirit_id, "spirit office")
    await settle(ctx, petition, office, granted=granted, tally=BureauTally())
    if petition.status is PetitionStatus.APPEALED and not granted:
        petition.status = PetitionStatus.DENIED
        petition.resolved_epoch = ctx.epoch
    petition.locked = sorted({*petition.locked, "status"})
    if son_id is not None:
        await reward_work(ctx, son_id, office.jurisdiction_entity_id)
    await ctx.session.flush()
    return petition


async def make_mystic(ctx: TickContext, mortal_id: int, sender_id: int | None, kind: VisionKind | None = None) -> MysticRow:
    mortal = await of_type(ctx, mortal_id, MORTALS, "a mortal")
    if sender_id is not None:
        await require_god(ctx, sender_id)
    existing = await ctx.session.get(MysticRow, mortal.id)
    if existing is None:
        existing = await become_mystic(ctx, mortal, sender_id, MysteryTally())
        if kind is None:
            return existing
    await see_vision(ctx, existing, mortal, sender_id, MysteryTally(), chosen=kind)
    return existing


async def send_vision(ctx: TickContext, mystic_id: int, sender_id: int | None, kind: VisionKind | None = None) -> VisionRow:
    row = await found(ctx, MysticRow, mystic_id, "mystic")
    mortal = await of_type(ctx, mystic_id, MORTALS, "a mortal")
    if sender_id is not None:
        await require_god(ctx, sender_id)
    return await see_vision(ctx, row, mortal, sender_id, MysteryTally(), chosen=kind)


async def stir_movement(ctx: TickContext, town_id: int, prophet_id: int | None, prophecy_id: int | None) -> MillenarianRow:
    town = await of_type(ctx, town_id, TOWNS, "a town")
    if prophet_id is not None:
        await of_type(ctx, prophet_id, MORTALS, "a mortal")
    prophecy = await found(ctx, ProphecyConditionRow, prophecy_id, "prophecy") if prophecy_id is not None else None
    return await begin_millenarian(ctx, town, prophet_id=prophet_id, prophecy=prophecy)


async def test_faith(ctx: TickContext, town_id: int, cause: TheodicyCause, suffering: int) -> TheodicyCrisisRow:
    town = await of_type(ctx, town_id, TOWNS, "a town")
    from_town = await church_of(ctx.session, town)
    if from_town is None:
        raise ValidationFailedError(f"No church stands in {town.name}.")
    return await open_crisis(ctx, town, from_town, cause, clamp_int(suffering, 0, PERCENT))


async def answer_crisis(ctx: TickContext, crisis_id: int, god_id: int | None) -> TheodicyCrisisRow:
    row = await found(ctx, TheodicyCrisisRow, crisis_id, "crisis of faith")
    if row.resolution is not TheodicyResolution.PENDING:
        raise ValidationFailedError("That crisis is already resolved.")
    answering = god_id if god_id is not None else row.god_node_id
    apply(row, {"answered": True, "resolution": TheodicyResolution.ANSWERED, "god_node_id": answering}, [])
    row.resolved_epoch = ctx.epoch
    if answering is not None:
        standing = await standing_row(ctx, row.community_entity_id, answering)
        if "love" not in standing.locked:
            standing.love = clamp_int(standing.love + ctx.rules.theodicy.answer_love, 0, PERCENT)
    await ctx.session.flush()
    return row


async def teach(ctx: TickContext, cult_id: int, kind: SacramentKind, protection: SacramentProtection | None, strength: int) -> DoctrineSacramentRow:
    await of_type(ctx, cult_id, CULTS, "a church")
    row = await ctx.session.get(DoctrineSacramentRow, (cult_id, kind))
    if row is None:
        row = await saved(
            ctx,
            DoctrineSacramentRow(cult_entity_id=cult_id, kind=kind, protection=protection or SACRAMENT_GUARDS[kind], since_epoch=ctx.epoch, locked=[]),
        )
    apply(row, {"protection": protection or row.protection, "strength": clamp_int(strength, 0, PERCENT)}, [])
    await ctx.session.flush()
    return row


async def give_sacrament(ctx: TickContext, mortal_id: int, kind: SacramentKind, priest_id: int | None) -> SacramentRow:
    mortal = await of_type(ctx, mortal_id, MORTALS, "a mortal")
    if priest_id is not None:
        await of_type(ctx, priest_id, MORTALS, "a mortal")
    row = await perform(ctx, mortal, kind, await plagued_regions(ctx.session), priest_id=priest_id)
    if row is None:
        raise ValidationFailedError(f"No church near {mortal.name} teaches that sacrament.")
    return row


async def teach_afterlife(ctx: TickContext, cult_id: int, model: AfterlifeModel | None) -> DoctrineAfterlifeRow:
    await of_type(ctx, cult_id, CULTS, "a church")
    row = await ctx.session.get(DoctrineAfterlifeRow, cult_id)
    chosen = model or await taught_model(ctx, cult_id)
    if row is None:
        row = await saved(ctx, DoctrineAfterlifeRow(cult_entity_id=cult_id, model=chosen, updated_epoch=ctx.epoch, locked=[]))
    apply(row, {"model": chosen}, [])
    await ctx.session.flush()
    return row


async def align(ctx: TickContext, cult_id: int, god_id: int, *, charge: bool) -> DoctrineAfterlifeRow:
    row = await found(ctx, DoctrineAfterlifeRow, cult_id, "taught afterlife")
    god = await require_god(ctx, god_id)
    cost = ctx.rules.afterlife_belief.align_cost
    if charge:
        if not isinstance(god, SonRow) or god.essence < cost:
            raise ValidationFailedError(f"Making the afterlife match costs {cost} essence.")
        god.essence -= cost
    stratum = MODEL_STRATA.get(row.model)
    realm = await ctx.session.scalar(select(AfterlifeStratumRow.realm_entity_id).where(AfterlifeStratumRow.son_id == god_id).limit(1))
    if stratum is not None and realm is not None:
        kinds = set(await ctx.session.scalars(select(AfterlifeStratumRow.kind).where(AfterlifeStratumRow.realm_entity_id == realm)))
        holder = await ctx.session.get(EntityRow, realm)
        if stratum not in kinds and holder is not None:
            made = new_stratum(ctx.rules, holder, stratum)
            made.son_id = god_id
            made.cult_entity_id = cult_id
            ctx.session.add(made)
    if row.model is AfterlifeModel.REBIRTH and await ctx.session.get(CultTenetRow, (cult_id, TenetKind.REINCARNATION)) is None:
        ctx.session.add(CultTenetRow(cult_entity_id=cult_id, tenet=TenetKind.REINCARNATION, since_epoch=ctx.epoch))
    apply(row, {"aligned": True, "aligned_by_node_id": god_id}, [])
    await ctx.session.flush()
    return row


async def weigh_climate(ctx: TickContext, town_id: int) -> FaithClimateRow:
    await of_type(ctx, town_id, TOWNS, "a town")
    row = await climate_of(ctx, town_id)
    await ctx.session.flush()
    return row


async def found_system(ctx: TickContext, people_id: int, kind: DivinationKind) -> DivinationSystemRow:
    people = await of_type(ctx, people_id, PEOPLES, "a people")
    if await ctx.session.scalar(
        select(DivinationSystemRow.id).where(DivinationSystemRow.people_entity_id == people.id, DivinationSystemRow.kind == kind).limit(1)
    ):
        raise ValidationFailedError(f"{people.name} already keep that way of reading.")
    return await take_up(ctx, people, kind)


async def read_omens(
    ctx: TickContext, realm_id: int, question: DivinationQuestion, *, verdict: OmenVerdict | None, swayed_by: int | None, system_id: int | None
) -> DivinationRow:
    realm = await of_type(ctx, realm_id, REALMS, "a realm")
    ruler = await living_entity(ctx.session, await ruler_of(ctx.session, realm.id))
    if ruler is None:
        raise ValidationFailedError(f"{realm.name} has no ruler to consult the diviners.")
    if system_id is not None:
        system = await found(ctx, DivinationSystemRow, system_id, "divination system")
    else:
        systems = await court_systems(ctx, realm.id)
        if not systems:
            raise ValidationFailedError(f"{realm.name} keeps no court diviners.")
        system = systems[0]
    if swayed_by is not None:
        await require_god(ctx, swayed_by)
    return await consult(ctx, system, ruler, realm.id, question, swayed_by=swayed_by, verdict=verdict)


async def foretell(
    ctx: TickContext, seer_id: int, predicate: ProphecyPredicate, subject_id: int, *, certainty: int, source: ForesightSource, proclaimed: bool
) -> ForesightRow:
    await node_exists(ctx, seer_id, "seer")
    subject = await ctx.session.get(EntityRow, subject_id)
    if subject is None:
        raise ValidationFailedError("No such subject.")
    if subject.entity_type is EntityType.OUTER_BEING:
        raise ValidationFailedError("No sight reaches an outer being.")
    if predicate.value not in FORESEEN:
        raise ValidationFailedError("A foresight reads whether someone dies or something falls.")
    row = await foresee(ctx, seer_id, source, subject.world_id, sight=certainty, chosen=(predicate, subject.id, certainty))
    if row is None:
        raise ValidationFailedError("Nothing could be foreseen.")
    seer = await living_entity(ctx.session, seer_id)
    if proclaimed and seer is not None and seer.entity_type is EntityType.MORTAL:
        await proclaim(ctx, row, seer)
    return row


async def build_model(ctx: TickContext, order_id: int, realm_id: int | None) -> ForecastModelRow:
    order = await of_type(ctx, order_id, FACTIONS, "a learned order")
    subject = realm_id
    if subject is None:
        home = await ctx.session.scalar(select(EntityRow.location_id).where(EntityRow.id == order.id))
        subject = await realm_of_town(ctx.session, home) if home is not None else None
    if subject is None:
        raise ValidationFailedError(f"{order.name} has no realm to forecast.")
    await of_type(ctx, subject, REALMS, "a realm")
    return await model_realm(ctx, order.id, subject, 0)


async def set_feeding(ctx: TickContext, god_id: int, emotion: Emotion, weight: int) -> GodFeedingRow:
    await require_god(ctx, god_id)
    row = await ctx.session.get(GodFeedingRow, (god_id, emotion)) or await saved(
        ctx, GodFeedingRow(god_node_id=god_id, emotion=emotion, epoch=ctx.epoch, locked=[])
    )
    apply(row, {"weight": clamp_int(weight, 0, PERCENT)}, [])
    await ctx.session.flush()
    return row


async def refresh_validity(ctx: TickContext, system_id: int) -> DivinationSystemRow:
    row = await found(ctx, DivinationSystemRow, system_id, "divination system")
    row.validity = await validity_of(ctx, row)
    await ctx.session.flush()
    return row


EDITABLE: dict[str, tuple[type[Base], tuple[str, ...], str]] = {
    "genius_locus": (GeniusLocusRow, GENIUS_FIELDS, "place spirit"),
    "spirit_office": (SpiritOfficeRow, OFFICE_FIELDS, "spirit office"),
    "petition": (PetitionRow, PETITION_FIELDS, "petition"),
    "mystic": (MysticRow, MYSTIC_FIELDS, "mystic"),
    "vision": (VisionRow, VISION_FIELDS, "vision"),
    "millenarian": (MillenarianRow, MILLENARIAN_FIELDS, "millenarian movement"),
    "theodicy": (TheodicyCrisisRow, THEODICY_FIELDS, "crisis of faith"),
    "doctrine_sacrament": (DoctrineSacramentRow, DOCTRINE_SACRAMENT_FIELDS, "taught sacrament"),
    "sacrament": (SacramentRow, SACRAMENT_FIELDS, "sacrament"),
    "doctrine_afterlife": (DoctrineAfterlifeRow, AFTERLIFE_FIELDS, "taught afterlife"),
    "faith_climate": (FaithClimateRow, CLIMATE_FIELDS, "faith climate"),
    "divination_system": (DivinationSystemRow, SYSTEM_FIELDS, "divination system"),
    "divination": (DivinationRow, DIVINATION_FIELDS, "reading"),
    "foresight": (ForesightRow, FORESIGHT_FIELDS, "foresight"),
    "forecast_model": (ForecastModelRow, MODEL_FIELDS, "forecast model"),
    "god_feeding": (GodFeedingRow, FEEDING_FIELDS, "feeding"),
}


async def edit_record(ctx: TickContext, kind: str, key: object, values: Values, release: list[str]) -> Base:
    table, fields, label = EDITABLE[kind]
    if kind == "foresight" and str(values.get("predicate", ProphecyPredicate.DIES.value)) not in FORESEEN:
        raise ValidationFailedError("A foresight reads whether someone dies or something falls.")
    row = apply(await found(ctx, table, key, label), allowed(values, fields, label), release)
    if isinstance(row, ForesightRow) and row.subject_node_id is not None:
        row.args = args_for(row.predicate, row.subject_node_id)
    await ctx.session.flush()
    return row


async def delete_record(ctx: TickContext, kind: str, key: object) -> None:
    table, _, label = EDITABLE[kind]
    await ctx.session.delete(await found(ctx, table, key, label))
    await ctx.session.flush()

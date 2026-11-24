from dataclasses import fields, replace
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.law_grammar import Grammar
from aerona.constants.units import PERCENT
from aerona.db.kind_concepts.registry import CONCEPTS
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.celestial import StarRow
from aerona.db.tables.culture import HolderTechniqueRow, IdeologyAdherentRow
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.faith import SpiritProfileRow
from aerona.db.tables.geology import RegionStratumRow
from aerona.db.tables.kind_crafts import ColourMeaningRow
from aerona.db.tables.law_grammar import LawExceptionRow
from aerona.db.tables.military import ArmyProfileRow, SpyNetworkRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.warfare import ArmyRow, SiegeRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cosmography import (
    BeingAgenda,
    BeingKind,
    BeingPhase,
    ClusterKind,
    DimensionKind,
    GalacticNucleus,
    GalaxyType,
    PhenomenonCause,
    PhenomenonKind,
    RiftCause,
    StarAge,
)
from aerona.domain.enums.creator import CovenantDuty, CreatorPromise, CreatorSignKind
from aerona.domain.enums.culture import CurseKind, IdeologyTenet, Technique
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.economy import CommodityKind, CurrencyIssuer, GoodsFlow, MoneyBacking, MoneyForm
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.faith import SpiritAlignment
from aerona.domain.enums.geology import DeepPassageOrigin, DeepPassageState, UndergroundStratum
from aerona.domain.enums.intrigue import PlotKind
from aerona.domain.enums.kind_crafts import ColourMeaning
from aerona.domain.enums.kinds import KindConcept, KindSpread, KindStance
from aerona.domain.enums.law_grammar import LawCondition, LawExceptionKind, LawOperator, LawTarget
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.military import Stance
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import (
    ArmyStats,
    BeastStats,
    FactionStats,
    ItemStats,
    NaturalLawStats,
    OuterBeingStats,
    PeopleStats,
    SpeciesStats,
    SpiritStats,
)
from aerona.engine.body.customs import people_id_of
from aerona.engine.context import TickContext
from aerona.engine.cosmos.beings import create_being
from aerona.engine.cosmos.foreign_gods import NewForeignGod, add_foreign_god
from aerona.engine.cosmos.ladder import ClusterDraft, DimensionDraft, GalaxyDraft, create_cluster, create_dimension, create_galaxy, ensure_ladder
from aerona.engine.cosmos.phenomena import form_phenomenon
from aerona.engine.cosmos.rifts import open_rift
from aerona.engine.disease.control import DiseaseDesign, create_disease
from aerona.engine.divine.creator_bonds import WIDER_SIGNS, offer
from aerona.engine.divine.law_grammar import set_grammar
from aerona.engine.ecology.beasts import profile_beast
from aerona.engine.economy.stocks import goods_of
from aerona.engine.environment.cells import make_passage
from aerona.engine.gods.queries import creator_row
from aerona.engine.intrigue.schemes import begin_scheme
from aerona.engine.kinds.acts import hold_kind, make_kind
from aerona.engine.lore import items
from aerona.engine.lore.control import create_lore
from aerona.engine.phases.native_faith import syncretize
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.sides import SideIndex
from aerona.engine.services.war import open_war, raise_army, take_captive
from aerona.engine.services.war_geography import Neighbourhood
from aerona.rules.model import RULE_METADATA_KEY, rule_meta
from aerona.rules.registry import Rules
from tests.engine.core.factories import entity, mortal, settlement
from tests.engine.cosmos.factories import teach
from tests.engine.integration.factories import RichCosmos
from tests.engine.lore.test_every_lore_kind import FIRST_VALUES

CERTAIN = 100
DATACLASS_FIELDS = "__dataclass_fields__"


def eager(rules: Rules) -> Rules:
    changes: dict[str, Any] = {}
    for space in fields(rules):
        table: Any = getattr(rules, space.name)
        if not hasattr(table, DATACLASS_FIELDS):
            continue
        sure = {
            definition.name: min(CERTAIN, rule_meta(definition).maximum)
            for definition in fields(table)
            if RULE_METADATA_KEY in definition.metadata and (definition.name.endswith("_chance") or rule_meta(definition).label.startswith("Chance"))
        }
        if sure:
            changes[space.name] = replace(table, **sure)
    return replace(rules, **changes)


async def stir(session: AsyncSession, cosmos: RichCosmos) -> None:
    home = cosmos.home
    ctx = await manual_context(session, "stir")
    creed = await create_lore(
        ctx,
        EntityType.IDEOLOGY,
        name="Stirring Creed",
        description="",
        world_id=home.world.id,
        location_id=None,
        power=3,
        values={"tenets": [IdeologyTenet.EGALITARIANISM.value]},
    )
    communities = list(await session.scalars(select(EntityRow.id).where(EntityRow.entity_type.in_(list(COMMUNITY_TYPES)), EntityRow.world_id == home.world.id)))
    for community_id in communities[:2]:
        session.add(IdeologyAdherentRow(ideology_entity_id=creed.id, adherent_entity_id=community_id, strength=90))
    god = await add_foreign_god(session, ctx.rules, ctx.rng(), ctx.epoch, NewForeignGod("Stirring Old God", home.world.id, (Domain.EARTH, None), power=40))
    await syncretize(session, ctx.rules, home.people.id, god.id)
    town = await settlement(session, "Stirring Town", home, home.regions[0], population=12000)
    plotter = await mortal(session, "Stirring Plotter", home, town.id)
    mark = await mortal(session, "Stirring Mark", home, town.id)
    await begin_scheme(ctx, plotter, PlotKind.SWAY, mark)
    await take_captive(ctx, plotter, await mortal(session, "Stirring Captive", home, town.id), None, description="held", home_id=town.id)
    session.add(SpyNetworkRow(owner_entity_id=town.id, target_entity_id=home.people.id, intel=90, since_epoch=1, locked=[]))
    spirit = await entity(session, "Stirring Shade", EntityType.SPIRIT, SpiritStats(unrest=95), world_id=home.world.id, location_id=town.id)
    session.add(SpiritProfileRow(spirit_entity_id=spirit.id, alignment=SpiritAlignment.VENGEFUL, imprint={}, traits=[], deeds={}, locked=[]))
    design = DiseaseDesign(name=None, values={"virulence": 60, "lethality": 20, "stigma": 90}, hold=False)
    await create_disease(ctx, home.regions[0].id, design, son_id=None)
    relic = await entity(session, "Stirring Ring", EntityType.ITEM, ItemStats(damage=5, protection=0, might=5, curse=90), world_id=home.world.id)
    await BondRepository(session).connect(BondDraft(plotter.id, relic.id, BondKind.OWNS, 1, None))
    (await items.profile_of(ctx, relic)).curse = CurseKind.BETRAYAL
    company = await entity(session, "Stirring Lances", EntityType.FACTION, FactionStats(strength=60), world_id=home.world.id)
    session.add(FactionProfileRow(faction_entity_id=company.id, kind=FactionKind.MERCENARY_COMPANY, influence_over={}, loyalty=5, locked=[]))
    other = await entity(session, "Stirring Folk", EntityType.PEOPLE, PeopleStats(population=3000), world_id=home.world.id, location_id=home.regions[0].id)
    await change_relation(ctx, home.people.id, other.id, -90, MemoryKind.ILL_WILL)
    for kind, values in FIRST_VALUES.items():
        await create_lore(ctx, kind, name=f"Stirring {kind.value}", description="", world_id=home.world.id, location_id=town.id, power=3, values=dict(values))
    species = await entity(session, "Stirring Wyrm Kin", EntityType.SPECIES, SpeciesStats(danger=90), world_id=home.world.id, location_id=home.regions[0].id)
    beast = await entity(session, "Stirring Wyrm", EntityType.BEAST, BeastStats(danger=90, hp=200), world_id=home.world.id, location_id=home.regions[0].id)
    await profile_beast(ctx, beast, species)
    rival = await settlement(session, "Stirring Rival", home, home.regions[1], population=8000)
    war = await open_war(ctx, town, rival)
    strength = await MilitaryStrength.load(session, ctx.rules)
    await raise_army(ctx, strength, await SideIndex.load(session, await Neighbourhood.load(session, ctx.rules)), town, war)
    session.add(SiegeRow(war_id=war.id, besieged_entity_id=rival.id, besieger_entity_id=town.id, started_epoch=ctx.epoch))
    await stir_laws(ctx, cosmos, town, mark)
    await stir_gods(ctx, cosmos)
    await session.flush()
    await stir_heavens(ctx, cosmos)
    await stir_kinds(ctx, cosmos, town, other)
    await stir_below(ctx, cosmos)


async def stir_below(ctx: TickContext, cosmos: RichCosmos) -> None:
    home = cosmos.home
    first, second = home.regions[0], home.regions[1]
    for region in (first, second):
        for stratum in (UndergroundStratum.CAVERN_UPPER, UndergroundStratum.AQUIFER):
            ctx.session.add(RegionStratumRow(region_entity_id=region.id, stratum=stratum, volume=40, pressure=20, locked=[]))
    await ctx.session.flush()
    folk = await entity(ctx.session, "Stirring Deep Folk", EntityType.PEOPLE, PeopleStats(population=2000), world_id=home.world.id, location_id=first.id)
    folk.stratum = UndergroundStratum.CAVERN_UPPER
    hall = await settlement(ctx.session, "Stirring Deep Hall", home, first, population=1500)
    hall.stratum = UndergroundStratum.CAVERN_UPPER
    far = await settlement(ctx.session, "Stirring Far Hall", home, second, population=1500)
    far.stratum = UndergroundStratum.CAVERN_UPPER
    up = UndergroundStratum.CAVERN_UPPER
    ends = (
        ((first.id, None), (first.id, up), DeepPassageState.OPEN),
        ((first.id, up), (second.id, up), DeepPassageState.OPEN),
        ((second.id, None), (second.id, up), DeepPassageState.FLOODED),
        ((first.id, up), (first.id, UndergroundStratum.AQUIFER), DeepPassageState.DIGGING),
        ((second.id, up), (second.id, UndergroundStratum.AQUIFER), DeepPassageState.COLLAPSED),
        ((first.id, UndergroundStratum.AQUIFER), (second.id, UndergroundStratum.AQUIFER), DeepPassageState.SEALED),
    )
    for one, two, state in ends:
        await make_passage(ctx, home.world.id, one, two, origin=DeepPassageOrigin.NATURAL, state=state)
    army = await entity(ctx.session, "Stirring Deep Host", EntityType.ARMY, ArmyStats(size=300, morale=60), world_id=home.world.id, location_id=first.id)
    army.stratum = up
    ctx.session.add(ArmyRow(entity_id=army.id, owner_entity_id=hall.id, raised_epoch=1))
    ctx.session.add(
        ArmyProfileRow(army_entity_id=army.id, region_entity_id=second.id, stratum=up, stance=Stance.MARCH, doctrine="shieldwall", supply_line=[], locked=[])
    )
    await ctx.session.flush()


async def stir_laws(ctx: TickContext, cosmos: RichCosmos, town: EntityRow, mark: EntityRow) -> None:
    session, home = ctx.session, cosmos.home
    law = await entity(session, "Stirring Measure", EntityType.NATURAL_LAW, NaturalLawStats(), world_id=home.world.id)
    await set_grammar(ctx, law, Grammar(LawTarget.STAT, LawOperator.SET, "prosperity", 70), LawCondition.ALWAYS, None, hold=False)
    session.add(LawExceptionRow(law_entity_id=law.id, kind=LawExceptionKind.PERSON, node_id=mark.id, locked=[]))
    lot = await entity(session, "Stirring Lot", EntityType.ITEM, ItemStats(damage=40, protection=40, might=60, curse=80), world_id=home.world.id)
    await BondRepository(session).connect(BondDraft(home.people.id, lot.id, BondKind.OWNS, 1, None))
    (await items.profile_of(ctx, lot)).curse = CurseKind.MISFORTUNE
    for holder in (home.people.id, town.id):
        session.add(HolderTechniqueRow(holder_entity_id=holder, technique=Technique.WRITTEN_LAW, since_epoch=0))


async def stir_gods(ctx: TickContext, cosmos: RichCosmos) -> None:
    session, home = ctx.session, cosmos.home
    kin_god = NewForeignGod("Stirring Kin God", home.world.id, (home.son.domain_primary, None), power=30)
    kin = await add_foreign_god(session, ctx.rules, ctx.rng(), ctx.epoch, kin_god)
    bonds = BondRepository(session)
    await bonds.connect(BondDraft(home.people.id, home.son.id, BondKind.WORSHIPS, 1, None))
    towns = await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.world_id == home.world.id))
    for town in list(towns):
        if await people_id_of(session, town) == home.people.id:
            await bonds.connect(BondDraft(town.id, kin.id, BondKind.WORSHIPS, 1, None))
    creator = await creator_row(session)
    if creator is not None:
        await WIDER_SIGNS[CreatorSignKind.MARK](ctx, creator, home.people)
        await offer(ctx, home.people.id, CovenantDuty.WORSHIP, CreatorPromise.PROTECTION, None)


async def stir_heavens(ctx: TickContext, cosmos: RichCosmos) -> None:
    session, home = ctx.session, cosmos.home
    await ensure_ladder(session, ctx.rules)
    plane = await create_dimension(session, ctx.rules, DimensionDraft("Stirring Astral", DimensionKind.ASTRAL, ctx.epoch))
    plane.veil = 0
    mirror = await create_dimension(session, ctx.rules, DimensionDraft("Stirring Mirror", DimensionKind.MIRROR, ctx.epoch))
    mirror.stability = 10
    web = await create_cluster(session, ctx.rules, ClusterDraft("Stirring Web", ClusterKind.RICH_CLUSTER, ctx.epoch, dimension_id=plane.id, radius=5000.0))
    far = await create_galaxy(session, ctx.rules, GalaxyDraft("Stirring Far Galaxy", GalaxyType.STARBURST, ctx.epoch, cluster_id=web.id))
    near = await create_galaxy(session, ctx.rules, GalaxyDraft("Stirring Near Galaxy", GalaxyType.LIVING, ctx.epoch, cluster_id=web.id, x=100.0))
    near.merging_with_galaxy_id = far.id
    near.nucleus = GalacticNucleus.QUASAR
    distant = cosmos.frontiers[0].world
    distant.star_id, distant.parent_world_id, distant.dimension_id = None, None, plane.id
    rift = await open_rift(ctx, home.world, home.regions[0], plane, RiftCause.GOD, target_world=distant)
    rift.stability = 20
    await create_being(ctx, BeingKind.STAR_FEEDER, home.world, region=home.regions[0], home_dimension_id=plane.id, phase=BeingPhase.MANIFEST)
    await create_being(
        ctx, BeingKind.RIFT_BORN, home.world, region=home.regions[1], home_dimension_id=plane.id, phase=BeingPhase.MANIFEST, agenda=BeingAgenda.CONQUER
    )
    await form_phenomenon(ctx, PhenomenonKind.OUTSIDE_OPENING, home.regions[1], PhenomenonCause.DIVINE, intensity=90)
    await form_phenomenon(ctx, PhenomenonKind.TIME_DISTORTION, home.regions[0], PhenomenonCause.DIVINE, intensity=60)
    for star in await session.scalars(select(StarRow).order_by(StarRow.id)):
        star.patron_son_id = home.son.id
        star.age_stage, star.lifecycle_clock = StarAge.DYING, 1
    for route in await session.scalars(select(RouteRow).order_by(RouteRow.id)):
        route.toll_controller_entity_id, route.toll_pct, route.piracy = home.people.id, 20, 60
    home.world.leakage = 90
    for name, size in (("Stirring Listener", 60), ("Stirring Hunger", 40)):
        await entity(
            session, name, EntityType.OUTER_BEING, OuterBeingStats(size=size, interest=80, influence=60), world_id=home.world.id, location_id=home.regions[0].id
        )
    await session.flush()


async def stir_kinds(ctx: TickContext, cosmos: RichCosmos, town: EntityRow, neighbour: EntityRow) -> None:
    home = cosmos.home
    made: dict[KindConcept, int] = {}
    for concept, spec in CONCEPTS.items():
        category = next(iter(spec.category))
        values = {"name": f"Stirring {spec.label}", "category": category, "world_id": home.world.id, "origin_node_id": home.people.id}
        kind = await make_kind(ctx, spec, values)
        made[concept] = kind.id
        if hasattr(kind, "prestige"):
            kind.prestige = 90
        for holder, stance, strength in ((home.people.id, KindStance.MAKES, 90), (neighbour.id, KindStance.USES, 60), (town.id, KindStance.USES, 70)):
            await hold_kind(ctx, concept, kind.id, holder, stance=stance, strength=strength, spread=KindSpread.INVENTED)
    colour = made.get(KindConcept.COLOUR_TERM)
    if colour is not None:
        ctx.session.add(ColourMeaningRow(colour_term_id=colour, culture_node_id=home.people.id, meaning=ColourMeaning.RANK, weight=90, since_epoch=ctx.epoch))
    ctx.session.add(
        CurrencyRow(
            issuer_entity_id=town.id,
            name="Stirring Notes",
            metal=None,
            purity=100,
            supply=500,
            trust=60,
            minted_epoch=ctx.epoch,
            form=MoneyForm.PAPER,
            backing=MoneyBacking.DECREE,
            convertible=False,
            issuer_kind=CurrencyIssuer.COMMUNITY,
        )
    )
    rival = await ctx.session.scalar(select(EntityRow).where(EntityRow.name == "Stirring Rival").limit(1))
    if rival is not None:
        await teach(ctx.session, rival, KnowledgeBranch.TRADE)
        await goods_of(ctx.session, ctx.epoch).add(rival.id, CommodityKind.ORE, 40, GoodsFlow.EXTRACTION, material=MaterialKind.SILVER, force=True)
        set_stats(rival, wealth=PERCENT)
    await ctx.session.flush()

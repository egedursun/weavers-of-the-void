import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import PressureRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.culture import LanguageRegister
from aerona.domain.enums.entity import COMMUNITY_TYPES, SOCIETY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.mind import PressureKind
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.war import WarCause
from aerona.domain.models.entity_stats import CultStats
from aerona.engine.context import TickContext
from aerona.engine.economy.routes import link_partners
from aerona.engine.faith.book import FaithBook
from aerona.engine.faith.zealotry import drifted, record_heresy
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore.language import register_barrier
from aerona.engine.lore.traditions import absorb_festivals
from aerona.engine.mind.book import ValueIndex
from aerona.engine.mind.drives import zeal_drive
from aerona.engine.mind.hooks import converted
from aerona.engine.mind.space import DISTANCE_MAX, NEUTRAL_DISTANCE, value_distance
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import FaithIndex, change_religion, faith_dominance, faith_shares
from aerona.engine.primitives.numbers import clamp_float, clamp_int, fraction, round_half_up
from aerona.engine.primitives.queries import canon, flags_by_entity, spoken_language
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.primitives.thresholds import relative_threshold
from aerona.engine.services.community_relations import lend_settlement_values
from aerona.engine.services.war import declare_war
from aerona.rules.registry import Rules

SCHISM_SUFFIX = "Schismatics"
SCHISM_SUBTYPE = "separatist sect"
ROMAN_TAIL = re.compile(r"\s+[IVXLCDM]+$")
GODLESS_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.FACTION})
BLOCKING_GODLESS_FLAGS = (EntityFlag.GODLESS, EntityFlag.SEEKING_GOD, EntityFlag.WORSHIPS_PLANET)


def schism_root(name: str) -> str:
    root = name.strip()
    for _ in range(PERCENT):
        stripped = ROMAN_TAIL.sub("", root).strip()
        if stripped.endswith(SCHISM_SUFFIX):
            stripped = stripped[: -len(SCHISM_SUFFIX)].strip()
        if stripped == root or not stripped:
            break
        root = stripped
    return root


def schism_candidate(sons: Sequence[SonRow], old_patron: int | None, world_id: int) -> SonRow | None:
    active = [son for son in sons if son.status is SonStatus.ACTIVE and son.id != old_patron]
    local = [son for son in active if son.current_world_id == world_id]
    pool = local or active
    return max(pool, key=lambda son: (son.charisma, -son.id)) if pool else None


def schism_eligible(ctx: TickContext, cult: EntityRow, threshold: float) -> bool:
    settings = ctx.rules.religion
    followers = stat_or(cult, "followers", 0)
    age = ctx.epoch - cult.birth_epoch
    if followers < threshold or age < settings.schism_min_age:
        return False
    zealous = stat_or(cult, "zeal", 0) >= settings.schism_zealotry
    return zealous or (followers >= settings.schism_large_followers and age >= settings.schism_large_min_age)


async def split_cult(ctx: TickContext, cult: EntityRow, candidate: SonRow, old_patron: int | None) -> EntityRow:
    settings = ctx.rules.religion
    followers = stat_or(cult, "followers", 0)
    split = round_half_up(followers * fraction(settings.schism_split_pct))
    set_stats(cult, followers=max(1, followers - split))
    unknown = ctx.rules.world_effects.unknown_stat
    sect = await create_record(
        ctx,
        RecordSpec(
            name=f"{schism_root(cult.name)} {SCHISM_SUFFIX}",
            entity_type=EntityType.CULT,
            stats=CultStats(
                followers=max(1, split),
                zeal=clamp_int(stat_or(cult, "zeal", 0) + settings.schism_zealotry_gain, 0, PERCENT),
                influence=clamp_int(stat_or(cult, "influence", unknown) - settings.schism_influence_loss, 0, PERCENT),
            ),
            body=f"A schism occurred within {cult.name}; {split} followers broke away and turned to {candidate.name}.",
            power=max(ctx.rules.world_effects.split_min_power, cult.power_level - 1),
            world_id=cult.world_id,
            location_id=cult.location_id,
            subtype=SCHISM_SUBTYPE,
        ),
    )
    await declare_war(ctx, sect.id, cult.id, "schism", cause=WarCause.SCHISM)
    bonds = BondRepository(ctx.session)
    await bonds.connect(BondDraft(sect.id, candidate.id, BondKind.WORSHIPS, ctx.epoch, "schism"))
    language = await spoken_language(ctx.session, cult.id)
    if language is not None:
        await bonds.connect(BondDraft(sect.id, language.id, BondKind.SPEAKS, ctx.epoch, "the tongue of the old cult"))
    sons = SonRepository(ctx.session)
    if old_patron is not None and await sons.get(old_patron) is not None:
        await sons.change_relation(old_patron, candidate.id, -settings.schism_patron_relation)
    await note(
        ctx,
        f"{cult.name} split: {split} followers turned to {candidate.name}.",
        key="religion.schism",
        ids=[cult.id, sect.id],
        son_id=candidate.id,
        kind=ChronicleKind.WORSHIP,
    )
    return sect


@reads(
    "cult.followers",
    "cult.influence",
    "cult.zeal",
    "table.bonds",
    "table.cult_doctrines",
    "table.epoch_year_cursors",
    "table.name_registry",
    "table.nodes",
    "table.reverences",
    "table.son_relations",
    "table.war_sides",
    "table.wars",
)
@writes(
    "cult.followers",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
    "table.son_relations",
)
async def schisms(ctx: TickContext) -> None:
    settings = ctx.rules.religion
    cults = await canon(ctx.session, [EntityType.CULT])
    threshold = relative_threshold(cults, "followers", fraction(settings.schism_top_pct), settings.schism_min_followers, settings.schism_always_followers)
    faith = await FaithIndex.load(ctx.session)
    sons = list(faith.sons.values())
    rng = ctx.rng("schism")
    split = 0
    for cult in cults:
        if split >= settings.schism_cap:
            break
        heretical = await drifted(ctx, cult.id)
        if not heretical and not schism_eligible(ctx, cult, threshold(cult)):
            continue
        zealous = heretical or stat_or(cult, "zeal", 0) >= settings.schism_zealotry
        if not rng.chance(settings.schism_zealous_chance if zealous else settings.schism_large_chance):
            continue
        old_patron = faith.patron(cult.id)
        candidate = schism_candidate(sons, old_patron, cult.world_id)
        if candidate is None:
            continue
        sect = await split_cult(ctx, cult, candidate, old_patron)
        await record_heresy(ctx, sect, cult.id)
        split += 1
    ctx.count("schisms", split)


@reads("settlement.piety", "table.bonds", "table.entity_flags", "table.nodes", "table.reverences")
async def godlessness(ctx: TickContext) -> None:
    settings = ctx.rules.religion
    faith = await FaithIndex.load(ctx.session)
    blocked: set[int] = set()
    for flag in BLOCKING_GODLESS_FLAGS:
        blocked |= await flags_by_entity(ctx.session, flag)
    rng = ctx.rng("godless")
    repository = EntityRepository(ctx.session)
    turned = 0
    for entity in await canon(ctx.session, GODLESS_TYPES):
        if entity.id in blocked or faith.patron(entity.id) is not None or faith.worships_anything(entity.id):
            continue
        if stat_or(entity, "piety", ctx.rules.world_effects.unknown_piety) >= settings.godlessness_piety:
            continue
        if not rng.chance(settings.godlessness_chance):
            continue
        await repository.add_flag(entity.id, EntityFlag.GODLESS, ctx.epoch)
        turned += 1
        await note(ctx, f"{entity.name} turned its back on the gods; it is godless now.", key="religion.godless", ids=[entity.id], kind=ChronicleKind.WORSHIP)
    ctx.count("godless", turned)


@dataclass
class WorshipShares:
    weights: dict[int, float] = field(default_factory=lambda: defaultdict(float))
    faith: dict[int, float] = field(default_factory=dict)

    @classmethod
    def count(cls, rules: Rules, communities: Sequence[EntityRow], faith: FaithIndex) -> "WorshipShares":
        shares = cls()
        reverence = fraction(rules.religion.reverence_weight_pct)
        for community in communities:
            patron = faith.patron(community.id)
            if patron is not None:
                shares.weights[patron] += 1
            for god in faith.reverences(community.id):
                shares.weights[god] += reverence
        return shares

    def dominance(self, rules: Rules, god_id: int) -> float:
        total = sum(self.weights.values())
        share = self.weights.get(god_id, 0.0) / total * PERCENT if total else 0.0
        return faith_dominance(rules, god_id, self.faith, share)

    def move(self, old: int | None, new: int) -> None:
        self.weights[new] += 1
        if old is not None:
            self.weights[old] = max(0.0, self.weights[old] - 1)


@dataclass(frozen=True)
class ConversionSource:
    god_id: int
    pull: float
    reason: str
    converter_id: int | None = None


@dataclass(frozen=True)
class SpreadWorld:
    faith: FaithIndex
    atlas: RegionAtlas
    cults: Sequence[EntityRow]
    communities: Sequence[EntityRow]
    flags: Mapping[EntityFlag, set[int]]
    values: ValueIndex = field(default_factory=ValueIndex)
    impiety: Mapping[int, int] = field(default_factory=dict)
    zeal: Mapping[int, float] = field(default_factory=dict)
    roads: Mapping[int, Mapping[int, float]] = field(default_factory=dict)
    churches: FaithBook | None = None


def god_kinship(world: SpreadWorld, first: int, second: int) -> float:
    one, other = world.values.of(first), world.values.of(second)
    return (DISTANCE_MAX - value_distance(one, other)) / NEUTRAL_DISTANCE if one and other else 1.0


def doctrine_fit(rules: Rules, world: SpreadWorld, cult: EntityRow, community: EntityRow) -> float:
    doctrine, culture = world.values.of(cult.id), world.values.of(community.id)
    closeness = (DISTANCE_MAX - value_distance(doctrine, culture)) / NEUTRAL_DISTANCE if doctrine and culture else 1.0
    lift = 1 + world.impiety.get(community.id, 0) / DISTANCE_MAX * rules.needs.conversion_impiety_pct / PERCENT
    return closeness * lift


def preaching_pull(rules: Rules, cult: EntityRow, community: EntityRow) -> float:
    settings = rules.religion
    population = stat_or(community, "population", 0)
    follower_pull = stat_or(cult, "followers", 0) / max(settings.preach_follower_min_divisor, population * settings.preach_population_mult)
    return (
        fraction(settings.preach_base_pct)
        + stat_or(cult, "influence", 0) / settings.preach_influence_divisor
        + min(fraction(settings.preach_follower_max_pct), follower_pull)
    )


def conversion_sources(rules: Rules, community: EntityRow, world: SpreadWorld, seeker: bool) -> list[ConversionSource]:
    old = world.faith.patron(community.id)
    sources: list[ConversionSource] = []
    for cult in world.cults:
        god = world.faith.living_patron_son(cult.id)
        if god is None or god.id == old or cult.world_id != community.world_id or not world.atlas.adjacent(cult.id, community.id):
            continue
        church = world.churches.churches.get(cult.id) if world.churches is not None else None
        zealous = rules.doctrine.proselytism_pct / PERCENT if church is not None and church.holds(TenetKind.PROSELYTISM) else 1.0
        sources.append(
            ConversionSource(
                god.id,
                preaching_pull(rules, cult, community) * doctrine_fit(rules, world, cult, community) * world.zeal.get(cult.id, 1.0) * zealous,
                f"through the sermons of {cult.name}",
                cult.id,
            )
        )
    sources.extend(missions(rules, community, world, old))
    if seeker:
        for neighbour in world.communities:
            god = world.faith.living_patron_son(neighbour.id)
            if neighbour.id == community.id or god is None or god.id == old or neighbour.world_id != community.world_id:
                continue
            if world.atlas.adjacent(neighbour.id, community.id):
                sources.append(ConversionSource(god.id, fraction(rules.religion.seeker_pull_chance), f"from its neighbour {neighbour.name}", neighbour.id))
    for partner_id, weight in sorted(world.roads.get(community.id, {}).items()):
        god = world.faith.living_patron_son(partner_id)
        partner = next((item for item in world.communities if item.id == partner_id), None)
        if god is None or god.id == old or partner is None:
            continue
        pull = fraction(rules.trade_routes.missionary_pct) * weight * (1 + fraction(rules.religion.conversion_seeker_bonus_pct) if seeker else 1)
        sources.append(ConversionSource(god.id, pull, f"from missionaries who came with the caravans of {partner.name}", partner.id))
    return sources


def missions(rules: Rules, community: EntityRow, world: SpreadWorld, old: int | None) -> list[ConversionSource]:
    if world.churches is None:
        return []
    table = rules.missions
    rival = world.churches.church_of(community.id) if old is not None else None
    rival_quality = rival.doctrine.clergy_quality if rival is not None and rival.doctrine is not None else 0
    found: list[ConversionSource] = []
    for partner_id in sorted(world.roads.get(community.id, {})):
        church = world.churches.church_of(partner_id)
        if church is None or church.god is None or church.god.id == old or church.doctrine is None or not church.holds(TenetKind.PROSELYTISM):
            continue
        skill = church.doctrine.clergy_quality / PERCENT * table.skill_pct / PERCENT
        miracles = (church.doctrine.zeal_parts.get("miracles of the god", 0) > 0) * table.miracle_pct / PERCENT
        pull = fraction(table.base_pct) * doctrine_fit(rules, world, church.cult, community) * (1 + skill + miracles)
        pull -= rival_quality / PERCENT * table.rival_clergy_pct / PERCENT * fraction(table.base_pct)
        if pull > 0:
            found.append(ConversionSource(church.god.id, pull, f"through the missionaries of {church.cult.name}", church.cult.id))
    return sorted(found, key=lambda item: -item.pull)[: table.cap]


def syncretism_weight(rules: Rules, world: SpreadWorld, community_id: int, god_id: int) -> float:
    if world.churches is None:
        return 1.0
    holder = world.churches.church_of(community_id)
    newcomer = next(iter(world.churches.by_god.get(god_id, [])), None)
    for church in (holder, newcomer):
        if church is not None and church.holds(TenetKind.EXCLUSIVITY):
            return rules.doctrine.exclusive_syncretism_pct / PERCENT
    if any(church is not None and church.holds(TenetKind.SYNCRETIC_OPENNESS) for church in (holder, newcomer)):
        return rules.doctrine.open_syncretism_pct / PERCENT
    return 1.0


def tolerance(ctx: TickContext, laws: LawBook, community_id: int) -> float:
    level = laws.param(community_id, LawKind.RELIGIOUS_TOLERANCE, "level")
    table = ctx.rules.legislation
    if level == "free":
        return table.tolerance_spread_pct / PERCENT
    if level == "persecution":
        return table.persecution_spread_pct / PERCENT
    return 1.0


def best_source(
    rules: Rules, sources: Sequence[ConversionSource], old: int | None, seeker: bool, world: tuple[FaithIndex, WorshipShares]
) -> ConversionSource | None:
    faith, shares = world
    settings = rules.religion
    best: ConversionSource | None = None
    for source in sources:
        bonus = (faith.god_fame(source.god_id) - faith.god_fame(old)) / settings.conversion_renown_divisor
        seeking = fraction(settings.conversion_seeker_bonus_pct) if seeker else 0.0
        pull = clamp_float(source.pull + bonus + seeking, 0.0, fraction(settings.conversion_chance_cap)) * shares.dominance(rules, source.god_id)
        if best is None or pull > best.pull:
            best = ConversionSource(source.god_id, pull, source.reason, source.converter_id)
    return best


def god_name(faith: FaithIndex, god_id: int | None) -> str:
    if god_id is None:
        return "no god"
    son = faith.sons.get(god_id)
    return son.name if son is not None else "the Creator"


async def _announce(ctx: TickContext, community: EntityRow, faith: FaithIndex, old: int | None, chosen: ConversionSource, *, syncretic: bool) -> None:
    new_name = god_name(faith, chosen.god_id)
    if syncretic:
        text = f"{community.name} began making offerings to {new_name} too, without abandoning {god_name(faith, old)}."
        key = "religion.syncretism"
    else:
        cold = f"; the altars of {god_name(faith, old)} grew cold" if old is not None else ""
        text = f"{community.name} converted to the faith of {new_name} {chosen.reason}{cold}."
        key = "religion.conversion"
    son_id = chosen.god_id if chosen.god_id in faith.sons else None
    await note(ctx, text, key=key, ids=[community.id], son_id=son_id, feed=FeedCategory.WORLD, kind=ChronicleKind.WORSHIP)


@reads(
    "cult.followers",
    "cult.influence",
    "people.population",
    "settlement.population",
    "table.bonds",
    "table.cult_doctrines",
    "table.cult_tenets",
    "table.culture_values",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.language_registers",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.memories",
    "table.minds",
    "table.nodes",
    "table.personality_values",
    "table.polity_members",
    "table.pressures",
    "table.reverences",
    "table.speaker_cohorts",
    "table.trade_flows",
    "table.trade_route_profiles",
    "table.trade_route_regions",
    "table.trade_route_tolls",
    "table.traits",
    "table.world_maps",
)
@writes(
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.reverences",
)
async def religion_spread(ctx: TickContext) -> None:
    settings = ctx.rules.religion
    session = ctx.session
    faith = await FaithIndex.load(session)
    communities = await canon(session, COMMUNITY_TYPES)
    flags = {flag: await flags_by_entity(session, flag) for flag in (EntityFlag.GODLESS, EntityFlag.SEEKING_GOD)}
    values = await ValueIndex.load(session)
    await lend_settlement_values(session, values, {community.id for community in communities})
    world = SpreadWorld(
        faith,
        await RegionAtlas.load(session),
        [cult for cult in communities if cult.entity_type is EntityType.CULT and faith.living_patron_son(cult.id) is not None],
        [community for community in communities if community.entity_type in SOCIETY_TYPES],
        flags,
        values,
        {row.entity_id: row.value for row in await session.scalars(select(PressureRow).where(PressureRow.pressure == PressureKind.IMPIETY))},
        {cult.id: await zeal_drive(session, ctx.rules, cult.id) for cult in communities if cult.entity_type is EntityType.CULT},
        await link_partners(ctx),
        await FaithBook.load(session),
    )
    shares = WorshipShares.count(ctx.rules, communities, faith)
    shares.faith = await faith_shares(session)
    creator_id = await NodeRepository(session).creator_id()
    rng = ctx.rng("spread")
    laws = await LawBook.load(session)
    conversions = syncretisms = 0
    for community in world.communities:
        if conversions >= settings.conversion_cap and syncretisms >= settings.syncretism_cap:
            break
        if community.status is not EntityStatus.CANON:
            continue
        old = faith.patron(community.id)
        if old is not None and old == creator_id:
            continue
        seeker = old is None or community.id in flags[EntityFlag.SEEKING_GOD] or community.id in flags[EntityFlag.GODLESS]
        chosen = best_source(ctx.rules, conversion_sources(ctx.rules, community, world, seeker), old, seeker, (faith, shares))
        understood = (
            await register_barrier(session, ctx.rules, chosen.converter_id, community.id, ctx.epoch, ours=LanguageRegister.LITURGICAL)
            if chosen is not None and chosen.converter_id is not None
            else 1.0
        )
        if chosen is None or not rng.probability(min(1.0, chosen.pull * understood * tolerance(ctx, laws, community.id))):
            continue
        weight = syncretism_weight(ctx.rules, world, community.id, chosen.god_id)
        syncretic = old is not None and not seeker and rng.chance(settings.syncretism_pct * god_kinship(world, old, chosen.god_id) * weight)
        if (syncretisms if syncretic else conversions) >= (settings.syncretism_cap if syncretic else settings.conversion_cap):
            continue
        if not await change_religion(ctx.session, community, chosen.god_id, ctx.epoch, chosen.reason, syncretic=syncretic, faith=faith):
            continue
        if syncretic:
            syncretisms += 1
        else:
            conversions += 1
            shares.move(old, chosen.god_id)
        await _announce(ctx, community, faith, old, chosen, syncretic=syncretic)
        if chosen.converter_id is not None:
            await converted(ctx, community.id, chosen.converter_id, note=chosen.reason)
            for festival in await absorb_festivals(ctx, community, chosen.converter_id):
                ctx.count("festivals_absorbed")
                await note(
                    ctx,
                    f"{community.name} kept {festival.name} even under the new faith, and the converters took the festival as their own.",
                    key="lore.festival_absorbed",
                    ids=[community.id, festival.id, chosen.converter_id],
                )
    ctx.count("conversions", conversions)
    ctx.count("syncretisms", syncretisms)


PHASES = (
    Phase("schisms", schisms),
    Phase("godlessness", godlessness),
    Phase("religion_spread", religion_spread),
)

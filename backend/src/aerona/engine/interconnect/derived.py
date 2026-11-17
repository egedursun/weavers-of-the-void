from collections import defaultdict
from collections.abc import Awaitable, Callable, Sequence

from sqlalchemy import select

from aerona.catalog.modifier_effects import (
    BLESSING_COMMUNITY_KEYS,
    BLESSING_MORTAL_KEYS,
    CURSE_KEYS,
    DOCTRINE_EFFECTS,
    FANATICISM_EFFECTS,
    LAW_EFFECTS,
    STRUCTURE_EFFECTS,
    TERRAIN_EFFECTS,
    TRADITION_EFFECT_STATS,
    TREATY_EFFECTS,
)
from aerona.constants.units import PERCENT
from aerona.db.tables.culture import TraditionParticipationRow, TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow, CultTenetRow
from aerona.db.tables.polity import TreatyClauseRow, TreatyPartyRow, TreatyProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityFlag, EntityType
from aerona.domain.enums.environment import WeatherEffect
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.domain.enums.polity import TreatyStatus
from aerona.domain.enums.son import PowerEffect
from aerona.engine.body.derived import body_drafts
from aerona.engine.context import TickContext
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.derivation import Origin, effect_draft, replace_derived, shaped_draft
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import has_unlocked_power, living_patron
from aerona.engine.primitives.modifiers import GROWTH_KEY, NEUTRAL_MULTIPLIER, ModifierDraft
from aerona.engine.primitives.queries import active_bonds, canon, flags_by_entity
from aerona.engine.primitives.stats import stat

S = ModifierSource
TICK_SOURCES = frozenset(
    {
        S.WONDER,
        S.CONDITION,
        S.INJURY,
        S.TRAIT,
        S.LAW,
        S.TRADITION,
        S.ARTWORK,
        S.DOCTRINE,
        S.TREATY,
        S.STRUCTURE,
        S.CURSE,
        S.BLESSING,
        S.GOD_POWER,
        S.GOD_DEATH,
        S.PHENOMENON,
    }
)
ENVIRONMENT_SOURCES = frozenset({S.TERRAIN, S.SEASON, S.WEATHER})
LAW_OF_NATURE_SOURCES = frozenset({S.NATURAL_LAW})
DERIVED_SOURCES = TICK_SOURCES | ENVIRONMENT_SOURCES | LAW_OF_NATURE_SOURCES
WEATHER_SLOT = "modifiers"


async def law_drafts(ctx: TickContext, communities: Sequence[EntityRow]) -> list[ModifierDraft]:
    book = await LawBook.load(ctx.session)
    drafts: list[ModifierDraft] = []
    for community in communities:
        for kind, effects in LAW_EFFECTS.items():
            row = book.in_force(community.id, kind)
            if row is None or not row.enforcement:
                continue
            origin = Origin(S.LAW, f"modifier.law.{kind.value}", ctx.epoch, row.law_entity_id, f"law.{kind.value}")
            drafts.extend(draft for effect in effects if (draft := effect_draft(ctx.rules, community, effect, origin, factor=row.enforcement / PERCENT)))
    return drafts


async def tradition_drafts(ctx: TickContext, by_id: dict[int, EntityRow]) -> list[ModifierDraft]:
    traditions = {row.id for row in await canon(ctx.session, [EntityType.TRADITION])}
    profiles = {row.tradition_entity_id: row for row in await ctx.session.scalars(select(TraditionProfileRow)) if row.tradition_entity_id in traditions}
    scale = ctx.rules.modifiers.tradition_effect_pct / PERCENT
    drafts: list[ModifierDraft] = []
    statement = select(TraditionParticipationRow).order_by(TraditionParticipationRow.tradition_entity_id, TraditionParticipationRow.community_entity_id)
    for share in await ctx.session.scalars(statement):
        profile = profiles.get(share.tradition_entity_id)
        community = by_id.get(share.community_entity_id)
        if profile is None or community is None:
            continue
        origin = Origin(S.TRADITION, f"modifier.tradition.{profile.kind.value}", ctx.epoch, profile.tradition_entity_id, f"tradition.{profile.kind.value}")
        for effect_key, value in sorted(profile.effects.items()):
            key = TRADITION_EFFECT_STATS.get(effect_key)
            if key is not None and (draft := shaped_draft(community, key, ModifierOp.ADD, value, origin, factor=share.participation / PERCENT * scale)):
                drafts.append(draft)
    return drafts


async def artwork_drafts(ctx: TickContext, by_id: dict[int, EntityRow]) -> list[ModifierDraft]:
    drafts: list[ModifierDraft] = []
    for artwork in await canon(ctx.session, [EntityType.ARTWORK]):
        holder = by_id.get(artwork.location_id or 0)
        renown = stat(artwork, "renown") or 0
        if holder is None or not renown:
            continue
        origin = Origin(S.ARTWORK, "modifier.artwork", ctx.epoch, artwork.id, "artwork")
        size = ctx.rules.modifiers.artwork_prosperity * renown / PERCENT
        if (draft := shaped_draft(holder, "prosperity", ModifierOp.ADD, size, origin)) is not None:
            drafts.append(draft)
    return drafts


async def doctrine_drafts(ctx: TickContext, by_id: dict[int, EntityRow]) -> list[ModifierDraft]:
    drafts: list[ModifierDraft] = []
    for tenet in await ctx.session.scalars(select(CultTenetRow).order_by(CultTenetRow.cult_entity_id, CultTenetRow.tenet)):
        cult = by_id.get(tenet.cult_entity_id)
        effects = DOCTRINE_EFFECTS.get(tenet.tenet, ())
        if cult is None or not effects:
            continue
        origin = Origin(S.DOCTRINE, f"modifier.doctrine.{tenet.tenet.value}", ctx.epoch, group=f"doctrine.{tenet.tenet.value}")
        drafts.extend(draft for effect in effects if (draft := effect_draft(ctx.rules, cult, effect, origin)))
    for doctrine in await ctx.session.scalars(select(CultDoctrineRow).where(CultDoctrineRow.fanaticism.is_not(None)).order_by(CultDoctrineRow.cult_entity_id)):
        cult = by_id.get(doctrine.cult_entity_id)
        if cult is None or doctrine.fanaticism is None:
            continue
        origin = Origin(S.DOCTRINE, f"modifier.fanaticism.{doctrine.fanaticism.value}", ctx.epoch, group="fanaticism")
        drafts.extend(draft for effect in FANATICISM_EFFECTS[doctrine.fanaticism] if (draft := effect_draft(ctx.rules, cult, effect, origin)))
    return drafts


async def treaty_drafts(ctx: TickContext, by_id: dict[int, EntityRow]) -> list[ModifierDraft]:
    treaties = {
        row.treaty_entity_id: row
        for row in await ctx.session.scalars(select(TreatyProfileRow).where(TreatyProfileRow.status == TreatyStatus.IN_FORCE))
        if row.treaty_entity_id in by_id
    }
    if not treaties:
        return []
    obligors: dict[int, set[int]] = defaultdict(set)
    for clause in await ctx.session.scalars(select(TreatyClauseRow).where(TreatyClauseRow.treaty_entity_id.in_(list(treaties)))):
        if clause.obligor_node_id is not None:
            obligors[clause.treaty_entity_id].add(clause.obligor_node_id)
    drafts: list[ModifierDraft] = []
    statement = (
        select(TreatyPartyRow)
        .where(TreatyPartyRow.treaty_entity_id.in_(list(treaties)))
        .order_by(TreatyPartyRow.treaty_entity_id, TreatyPartyRow.party_node_id)
    )
    for party in await ctx.session.scalars(statement):
        treaty = treaties[party.treaty_entity_id]
        member = by_id.get(party.party_node_id)
        if member is None:
            continue
        origin = Origin(S.TREATY, f"modifier.treaty.{treaty.kind.value}", ctx.epoch, treaty.treaty_entity_id, f"treaty.{treaty.kind.value}")
        for item in TREATY_EFFECTS.get(treaty.kind, ()):
            if item.obligor_only and party.party_node_id not in obligors[treaty.treaty_entity_id]:
                continue
            if (draft := effect_draft(ctx.rules, member, item.effect, origin)) is not None:
                drafts.append(draft)
    return drafts


async def structure_drafts(ctx: TickContext, by_id: dict[int, EntityRow]) -> list[ModifierDraft]:
    drafts: list[ModifierDraft] = []
    for work in await canon(ctx.session, [EntityType.STRUCTURE]):
        effects = STRUCTURE_EFFECTS.get(work.engine_kind) if work.engine_kind is not None else None
        owner = by_id.get(work.location_id or 0)
        function = stat(work, "function") or 0
        if not effects or owner is None or owner.entity_type not in COMMUNITY_TYPES or not function or work.engine_kind is None:
            continue
        origin = Origin(S.STRUCTURE, f"modifier.structure.{work.engine_kind.value}", ctx.epoch, work.id, f"structure.{work.engine_kind.value}")
        drafts.extend(draft for effect in effects if (draft := effect_draft(ctx.rules, owner, effect, origin, factor=function / PERCENT)))
    return drafts


async def curse_drafts(ctx: TickContext, by_id: dict[int, EntityRow]) -> list[ModifierDraft]:
    cursed = sorted(await flags_by_entity(ctx.session, EntityFlag.CURSED))
    cursers = {bond.target_node_id: bond.source_node_id for bond in await active_bonds(ctx.session, [BondKind.CURSED], targets=cursed)}
    drafts: list[ModifierDraft] = []
    for entity_id in cursed:
        target = by_id.get(entity_id)
        if target is None:
            continue
        origin = Origin(S.CURSE, "modifier.curse", ctx.epoch, cursers.get(entity_id), "curse")
        size = ctx.rules.modifiers.curse_stat_pct / PERCENT
        drafts.extend(draft for key in CURSE_KEYS if (draft := shaped_draft(target, key, ModifierOp.MULTIPLY, size, origin)))
    return drafts


async def blessing_drafts(ctx: TickContext, by_id: dict[int, EntityRow]) -> list[ModifierDraft]:
    drafts: list[ModifierDraft] = []
    rules = ctx.rules.modifiers
    for bond in await active_bonds(ctx.session, [BondKind.BLESSED]):
        target = by_id.get(bond.target_node_id)
        if target is None:
            continue
        mortal = target.entity_type is EntityType.MORTAL
        keys = BLESSING_MORTAL_KEYS if mortal else BLESSING_COMMUNITY_KEYS if target.entity_type in COMMUNITY_TYPES else ()
        size = rules.blessing_mortal if mortal else rules.blessing_community
        origin = Origin(S.BLESSING, "modifier.blessing", ctx.epoch, bond.source_node_id, "blessing")
        drafts.extend(draft for key in keys if (draft := shaped_draft(target, key, ModifierOp.ADD, size, origin)))
    return drafts


async def god_power_drafts(ctx: TickContext, communities: Sequence[EntityRow]) -> list[ModifierDraft]:
    drafts: list[ModifierDraft] = []
    growth = float(ctx.rules.world_epoch_transition.bounty_power_growth_mult)
    for community in communities:
        patron = await living_patron(ctx.session, community)
        if patron is None or not await has_unlocked_power(ctx.session, ctx.rules, patron, PowerEffect.BOUNTY_GIVER):
            continue
        origin = Origin(S.GOD_POWER, "modifier.god_power.bounty_giver", ctx.epoch, patron.id, "god_power.bounty_giver")
        if (draft := shaped_draft(community, GROWTH_KEY, ModifierOp.MULTIPLY, growth, origin)) is not None:
            drafts.append(draft)
    return drafts


async def god_death_drafts(ctx: TickContext, atlas: RegionAtlas, by_id: dict[int, EntityRow]) -> list[ModifierDraft]:
    drafts: list[ModifierDraft] = []
    table = ctx.rules.modifiers
    for corpse in await canon(ctx.session, [EntityType.PLACE]):
        if corpse.engine_kind is not EngineKind.DEAD_GOD:
            continue
        region = by_id.get(atlas.top_region(corpse.id) or 0)
        if region is None:
            continue
        origin = Origin(S.GOD_DEATH, "modifier.god_death", ctx.epoch, corpse.id, "god_death")
        for key, size in (("magic", table.god_corpse_magic), ("fertility", table.god_corpse_fertility)):
            if (draft := shaped_draft(region, key, ModifierOp.ADD, size, origin)) is not None:
                drafts.append(draft)
    return drafts


async def phenomenon_drafts(ctx: TickContext, atlas: RegionAtlas, by_id: dict[int, EntityRow], communities: Sequence[EntityRow]) -> list[ModifierDraft]:
    table = ctx.rules.modifiers
    storms: dict[int, EntityRow] = {}
    for event in await canon(ctx.session, [EntityType.EVENT]):
        if event.engine_kind is EngineKind.MAGIC_STORM and event.birth_epoch >= ctx.epoch - table.phenomenon_epochs and event.location_id is not None:
            storms.setdefault(event.location_id, event)
    drafts: list[ModifierDraft] = []
    for region_id, storm in sorted(storms.items()):
        region = by_id.get(region_id)
        origin = Origin(S.PHENOMENON, "modifier.phenomenon.magic_storm", ctx.epoch, storm.id, "phenomenon")
        if region is not None and (draft := shaped_draft(region, "magic", ModifierOp.ADD, table.phenomenon_region_magic, origin)):
            drafts.append(draft)
    for community in communities:
        storm_here = storms.get(atlas.top_region(community.id) or 0)
        if storm_here is None:
            continue
        origin = Origin(S.PHENOMENON, "modifier.phenomenon.magic_storm", ctx.epoch, storm_here.id, "phenomenon")
        if (draft := shaped_draft(community, "prosperity", ModifierOp.ADD, -table.phenomenon_prosperity, origin)) is not None:
            drafts.append(draft)
    return drafts


Deriver = Callable[[], Awaitable[list[ModifierDraft]]]


async def derive_tick_modifiers(ctx: TickContext) -> int:
    living = await canon(ctx.session)
    by_id = {row.id: row for row in living}
    communities = [row for row in living if row.entity_type in COMMUNITY_TYPES]
    atlas = await RegionAtlas.load(ctx.session)
    derivers: tuple[Deriver, ...] = (
        lambda: body_drafts(ctx.session, ctx.rules, ctx.epoch),
        lambda: law_drafts(ctx, communities),
        lambda: tradition_drafts(ctx, by_id),
        lambda: artwork_drafts(ctx, by_id),
        lambda: doctrine_drafts(ctx, by_id),
        lambda: treaty_drafts(ctx, by_id),
        lambda: structure_drafts(ctx, by_id),
        lambda: curse_drafts(ctx, by_id),
        lambda: blessing_drafts(ctx, by_id),
        lambda: god_power_drafts(ctx, communities),
        lambda: god_death_drafts(ctx, atlas, by_id),
        lambda: phenomenon_drafts(ctx, atlas, by_id, communities),
    )
    drafts: list[ModifierDraft] = []
    for deriver in derivers:
        drafts.extend(await deriver())
    return await replace_derived(ctx.session, TICK_SOURCES - {S.WONDER, S.CONDITION}, drafts)


def environment_drafts(ctx: TickContext, book: EnvironmentBook, holders: Sequence[EntityRow], armies: Sequence[EntityRow]) -> list[ModifierDraft]:
    table = ctx.rules.modifiers
    drafts: list[ModifierDraft] = []
    for holder in holders:
        env = book.region_of(holder.id)
        if env is None:
            continue
        terrain = Origin(S.TERRAIN, f"modifier.terrain.{env.dominant_terrain.value}", ctx.epoch, env.entity_id, "terrain")
        drafts.extend(draft for effect in TERRAIN_EFFECTS.get(env.dominant_terrain, ()) if (draft := effect_draft(ctx.rules, holder, effect, terrain)))
        harsh = NEUTRAL_MULTIPLIER - env.seasonality / PERCENT * table.season_prosperity_pct / PERCENT
        season = Origin(S.SEASON, "modifier.season", ctx.epoch, env.entity_id, "season")
        if (draft := shaped_draft(holder, "prosperity", ModifierOp.MULTIPLY, harsh, season)) is not None:
            drafts.append(draft)
        weather = book.weather(ctx.environment.world_seed, ctx.epoch, env, book.growing_season(env.world_id), WEATHER_SLOT)
        origin = Origin(S.WEATHER, f"modifier.weather.{weather.kind.value}", ctx.epoch, env.entity_id, "weather")
        size = weather.effect(WeatherEffect.GROWTH) * table.weather_prosperity_pct / PERCENT
        if (draft := shaped_draft(holder, "prosperity", ModifierOp.ADD, round(size), origin)) is not None:
            drafts.append(draft)
    for army in armies:
        env = book.region_of(army.id)
        if env is None:
            continue
        weather = book.weather(ctx.environment.world_seed, ctx.epoch, env, book.travel_season(env.world_id), f"{WEATHER_SLOT}.army.{army.id}")
        felt = weather.effect(WeatherEffect.MORALE) - weather.effect(WeatherEffect.COLD) // 2 - weather.effect(WeatherEffect.HEAT) // 2
        origin = Origin(S.WEATHER, f"modifier.weather.{weather.kind.value}", ctx.epoch, env.entity_id, "weather")
        size = felt * table.weather_morale_pct / PERCENT
        if (draft := shaped_draft(army, "morale", ModifierOp.ADD, round(size), origin)) is not None:
            drafts.append(draft)
    return drafts


async def derive_environment_modifiers(ctx: TickContext) -> int:
    living = await canon(ctx.session, [*COMMUNITY_TYPES, EntityType.ARMY])
    book = await EnvironmentBook.load(ctx.session, ctx.rules, ctx.epoch)
    holders = [row for row in living if row.entity_type in COMMUNITY_TYPES]
    armies = [row for row in living if row.entity_type is EntityType.ARMY]
    return await replace_derived(ctx.session, ENVIRONMENT_SOURCES, environment_drafts(ctx, book, holders, armies))

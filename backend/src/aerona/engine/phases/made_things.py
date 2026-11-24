from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.culture import CurseKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.fortune import FortuneSourceKind
from aerona.domain.enums.mind import MemoryKind, TraitKind, TraitSource, ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.hits import Harm
from aerona.engine.body.package_fixups import curse_package
from aerona.engine.context import TickContext
from aerona.engine.cosmos.sanity import shift_sanity
from aerona.engine.economy.materials import MaterialBook
from aerona.engine.fortune.profiles import shift_fortune
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore import art, items, typed_backfill
from aerona.engine.lore.curse_kinds import WIDER_CURSES, Cursed
from aerona.engine.mind.book import add_trait, stored_values, write_values
from aerona.engine.mind.memories import remember
from aerona.engine.polity.book import RealmBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat, stat_or
from aerona.engine.recording.record import record


async def rival_of(ctx: TickContext, bearer: EntityRow) -> EntityRow | None:
    if bearer.location_id is None:
        return None
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(
            await present_among(ctx.session, [bearer.location_id]),
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.id != bearer.id,
        )
        .order_by(EntityRow.id)
    )
    return max(rows, key=lambda mortal: (stat(mortal, "strength") or 0, -mortal.id), default=None)


async def liege_of(ctx: TickContext, realms: RealmBook, bearer: EntityRow) -> int | None:
    seat = bearer.location_id if bearer.entity_type is EntityType.MORTAL else bearer.id
    realm = realms.realm_of(seat)
    if realm is None:
        return None
    ruler = await items.ruler_of(ctx, realm.profile.polity_entity_id)
    return ruler if ruler is not None and ruler != bearer.id else realm.profile.polity_entity_id


async def bloodthirst(ctx: TickContext, item: EntityRow, bearer: EntityRow, strength: int) -> None:
    table = ctx.rules.item_curses
    mortal = bearer.entity_type is EntityType.MORTAL
    holder = ValueHolder.PERSONAL if mortal else ValueHolder.CULTURE
    values = await stored_values(ctx.session, holder, bearer.id)
    values[ValueAxis.MARTIAL] = values.get(ValueAxis.MARTIAL, 0) + round_half_up(strength * table.bloodthirst_pct / PERCENT)
    values[ValueAxis.MERCY] = values.get(ValueAxis.MERCY, 0) - round_half_up(strength * table.bloodthirst_pct / PERCENT)
    await write_values(ctx.session, holder, bearer.id, values)
    if not mortal or strength < ctx.rules.item_powers.wrathful_curse:
        return
    await add_trait(ctx.session, bearer.id, TraitKind.WRATHFUL, TraitSource.CONDITION, ctx.epoch, source_node_id=item.id)
    rival = await rival_of(ctx, bearer)
    if rival is not None:
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=bearer.id,
            subject_id=rival.id,
            kind=MemoryKind.HUMILIATED_ME,
            magnitude=-ctx.rules.item_powers.provocation,
            epoch=ctx.epoch,
            note=f"{item.name} drives its bearer to fight",
        )


async def betrayal(ctx: TickContext, realms: RealmBook, item: EntityRow, bearer: EntityRow, strength: int) -> bool:
    liege = await liege_of(ctx, realms, bearer)
    if liege is None:
        return False
    await remember(
        ctx.session,
        ctx.rules,
        holder_id=bearer.id,
        subject_id=liege,
        kind=MemoryKind.ILL_WILL,
        magnitude=-ctx.rules.item_powers.betrayal_opinion * strength / PERCENT,
        epoch=ctx.epoch,
        note=f"whispers of {item.name}",
    )
    return True


async def afflict(ctx: TickContext, realms: RealmBook, item: EntityRow) -> str | None:
    row = await items.profile_of(ctx, item)
    if row.curse is CurseKind.NONE:
        return None
    bearer = await living_entity(ctx.session, await items.owner_of(ctx, item.id))
    if bearer is None:
        return None
    table = ctx.rules.item_curses
    strength = stat_or(item, "curse", PERCENT // 2)
    mortal = bearer if bearer.entity_type is EntityType.MORTAL else None
    await curse_package(ctx, item, bearer, row.curse, strength)
    if row.curse is CurseKind.WASTING and mortal is not None:
        harm = Harm(
            damage=strength * table.wasting_pct / PERCENT,
            cause=HarmCause.CURSE,
            death_cause=f"wasted away under the curse of {item.name}",
            source_node_id=item.id,
        )
        await apply_hits(ctx, mortal, harm)
    elif row.curse is CurseKind.MADNESS and mortal is not None:
        shift_sanity(ctx.rules, mortal, -strength * table.madness_pct / PERCENT)
    elif row.curse is CurseKind.BLOODTHIRST:
        await bloodthirst(ctx, item, bearer, strength)
    elif row.curse is CurseKind.MISFORTUNE:
        await shift_fortune(ctx, bearer.id, -ctx.rules.fortune.curse_strength, FortuneSourceKind.CURSE, item.id)
        home = await living_entity(ctx.session, bearer.location_id) if mortal is not None else bearer
        if home is not None and stat(home, "prosperity") is not None:
            shift_stat(home, "prosperity", -round_half_up(strength * table.misfortune_pct / PERCENT))
    elif row.curse in WIDER_CURSES:
        await WIDER_CURSES[row.curse](ctx, Cursed(item, bearer, strength))
    elif row.curse is not CurseKind.BETRAYAL or not await betrayal(ctx, realms, item, bearer, strength):
        return None
    return row.curse.value


@reads(
    "artwork.influence",
    "artwork.renown",
    "cult.zeal",
    "item.curse",
    "item.damage",
    "item.might",
    "item.protection",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "settlement.defense",
    "settlement.prosperity",
    "table.afflictions",
    "table.applied_fixups",
    "table.assistive_aids",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.community_stocks",
    "table.conditions",
    "table.cosmos",
    "table.creature_anatomy",
    "table.cult_tenets",
    "table.culture_values",
    "table.custom_kinds",
    "table.deep_passages",
    "table.dimensional_events",
    "table.dimensions",
    "table.divine_wounds",
    "table.doctrine_sacraments",
    "table.entities",
    "table.entity_flags",
    "table.entity_tags",
    "table.foreign_gods",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.genomes",
    "table.holder_levels",
    "table.house_members",
    "table.house_profiles",
    "table.incubating_ideas",
    "table.injuries",
    "table.item_enchantments",
    "table.item_history",
    "table.item_profiles",
    "table.memories",
    "table.mind_attributes",
    "table.minds",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.natural_law_profiles",
    "table.node_births",
    "table.node_materials",
    "table.nodes",
    "table.offices",
    "table.people_culture",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.prostheses",
    "table.region_environment",
    "table.relics",
    "table.sacraments",
    "table.skills",
    "table.sons",
    "table.spirit_profiles",
    "table.spy_networks",
    "table.stars",
    "table.tradition_profiles",
    "table.traits",
    "table.vassalages",
    "table.world_domain_hooks",
    "table.world_maps",
    "table.world_materials",
    "table.worlds",
)
@writes(
    "cult.zeal",
    "mortal.hp",
    "settlement.defense",
    "settlement.prosperity",
    "table.afflictions",
    "table.applied_fixups",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_stocks",
    "table.conditions",
    "table.entities",
    "table.fortune_sources",
    "table.goods_flows",
    "table.house_profiles",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.injuries",
    "table.item_enchantments",
    "table.item_history",
    "table.item_profiles",
    "table.memories",
    "table.mortal_profiles",
    "table.people_culture",
    "table.personality_values",
    "table.prostheses",
    "table.region_environment",
    "table.relics",
    "table.sons",
    "table.spy_networks",
    "table.thread_links",
    "table.threads",
    "table.traits",
)
async def item_cycles(ctx: TickContext) -> None:
    ctx.count("items_typed", await typed_backfill.backfill_items(ctx))
    atlas = await RegionAtlas.load(ctx.session)
    book = await MaterialBook.load(ctx.session)
    realms = await RealmBook.load(ctx.session)
    for item in await items.living_items(ctx):
        for key, value in (await items.item_year(ctx, atlas, item, book)).items():
            ctx.count(f"items_{key}", value)
        cursed = await afflict(ctx, realms, item)
        if cursed:
            ctx.count(f"curse_{cursed}")
    for key, value in (await items.relic_year(ctx, atlas)).items():
        ctx.count(f"relics_{key}", value)


@reads(
    "artwork.influence",
    "artwork.renown",
    "table.applied_fixups",
    "table.artwork_profiles",
    "table.banned_works",
    "table.bonds",
    "table.community_societies",
    "table.culture_values",
    "table.entities",
    "table.holder_techniques",
    "table.language_intelligibility",
    "table.memories",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.people_culture",
    "table.polity_members",
    "table.polity_profiles",
    "table.preferences",
    "table.skills",
    "table.sons",
    "table.speaker_cohorts",
    "table.spirit_profiles",
    "table.traits",
)
@writes(
    "artwork.renown",
    "table.applied_fixups",
    "table.artwork_profiles",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.culture_values",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.name_registry",
    "table.polity_profiles",
    "table.sons",
    "table.spirit_profiles",
    "table.value_profiles",
)
async def artwork_cycles(ctx: TickContext) -> None:
    ctx.count("artworks_typed", await typed_backfill.backfill_artworks(ctx))
    for work in await art.living_artworks(ctx):
        for key, value in (await art.art_year(ctx, work)).items():
            ctx.count(f"art_{key}", value)
    for realm in list(await ctx.session.scalars(select(PolityProfileRow).order_by(PolityProfileRow.polity_entity_id))):
        if held(realm.polity_entity_id):
            continue
        raised = await art.commission(ctx, realm)
        if raised is not None:
            ctx.count("propaganda_works")
            await record(ctx, "lore.propaganda", roles={IncidentRole.SUBJECT: [raised.id, realm.polity_entity_id]})

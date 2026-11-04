from typing import Any

from aerona.catalog.civilization import unlocked
from aerona.catalog.domains import match_domain
from aerona.catalog.mind import CRAFT_SKILLS
from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, TurnCounter
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.civilization import TierCapability
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.economy import CommodityKind, MaterialSlot
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind, SkillKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.war import WarCause
from aerona.engine.economy.materials import armour_protection, curse_bonus, decay_loss, enchantment_cap, sanctity_splendour, set_node_material, weapon_damage
from aerona.engine.economy.resources import ensure_profile, set_resource_yield
from aerona.engine.primitives.mechanics import assign_mechanics
from aerona.engine.primitives.queries import spoken_language
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.engine.primitives.strength import military_strength
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.war import declare_war
from aerona.engine.structures.profiles import ensure_profile as structure_profile
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action, no_cost
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.mortal import lines
from aerona.tools.mortal.inputs import (
    BuildInput,
    ClaimInput,
    CultureInput,
    CultureKind,
    DiscoverInput,
    ProduceInput,
    SettleInput,
)
from aerona.tools.mortal.materials import chosen_material
from aerona.tools.mortal.support import (
    MortalCreation,
    civilization_tier,
    craft_of,
    create_record,
    fail_with_candidates,
    headcount_key,
    home_of,
    is_community,
    my_branch_effect,
    name_free,
    near,
    practised,
    require_craft,
    same_region,
)

PERCENT = 100
LAND = frozenset({EntityType.REGION, EntityType.PLACE})
CARRIER_TYPES = frozenset({*COMMUNITY_TYPES, EntityType.MORTAL})
BUILD_SITES = frozenset({EntityType.REGION, EntityType.PLACE, EntityType.SETTLEMENT})
JOIN = ", "
CULTURE_TYPES = {
    CultureKind.TRADITION: EntityType.TRADITION,
    CultureKind.LEGEND: EntityType.LEGEND,
    CultureKind.ARTWORK: EntityType.ARTWORK,
    CultureKind.LAW: EntityType.LAW,
}
CULTURE_BONDS = {
    CultureKind.TRADITION: BondKind.CELEBRATES,
    CultureKind.LEGEND: BondKind.TELLS_OF,
    CultureKind.ARTWORK: BondKind.PRODUCED,
    CultureKind.LAW: BondKind.RULES,
}
WEAPONS = frozenset({"weapon"})
ARMOUR = frozenset({"armour", "shield"})


def pct(value: float, percent: int) -> float:
    return value * percent / PERCENT


def clamp(value: float) -> int:
    return max(0, min(PERCENT, round(value)))


async def _usable_resource(call: MortalCall, resource_id: int) -> EntityRow:
    tools = call.rules.mortal_tools
    resource = await call.session.get(EntityRow, resource_id)
    if resource is None:
        fail(MortalResult.RESOURCE_MISSING)
    resource = await require_canon(call.session, resource_id)
    require_type(resource, {EntityType.RESOURCE}, MortalResult.NOT_A_RESOURCE_NAMED, name=resource.name)
    owned = await BondRepository(call.session).exists_between(call.me.id, resource.id, BondKind.OWNS)
    if not owned and not await same_region(call, resource):
        fail(MortalResult.NOT_YOUR_RESOURCE, name=resource.name)
    abundance = stat_or(resource, "abundance", 0)
    if abundance < tools.craft_min_abundance:
        fail(MortalResult.RESOURCE_SCARCE, name=resource.name, abundance=abundance)
    return resource


async def produce_item(call: MortalCall, args: ProduceInput) -> str:
    tools = call.rules.mortal_tools
    await name_free(call, args.name)
    resources = [await _usable_resource(call, resource_id) for resource_id in dict.fromkeys(args.resource_ids[: tools.craft_max_resources])]
    await require_craft(call)
    craft = await craft_of(call)
    await practised(call, CRAFT_SKILLS, call.rules.skills.craft_xp)
    might = sum(stat_or(resource, "might", 0) for resource in resources) / max(1, len(resources))
    metallurgy = round(tools.craft_metallurgy_bonus * await my_branch_effect(call, KnowledgeBranch.METALLURGY))
    region = (await call.atlas()).top_region(call.me.id)
    region_row = await call.session.get(EntityRow, region) if region is not None else None
    region_magic = round(stat_or(region_row, "magic", 0) / tools.craft_region_magic_divisor) if region_row is not None else 0
    magic = round(tools.craft_magic_bonus * await my_branch_effect(call, KnowledgeBranch.MAGIC)) + region_magic
    skilled = pct(craft, tools.craft_skill_pct) + pct(might, tools.craft_resource_might_pct)
    category = args.category.value
    damage = max(tools.craft_min_value, clamp(skilled + call.die(tools.craft_die) + metallurgy)) if category in WEAPONS else call.die(tools.craft_side_die)
    protection = max(tools.craft_min_value, clamp(skilled + call.die(tools.craft_die) + metallurgy)) if category in ARMOUR else call.die(tools.craft_side_die)
    material = await chosen_material(call, args.material, resources)
    worked = round(craft)
    if material is not None and category in WEAPONS:
        damage = max(damage, weapon_damage(call.rules, material, worked))
    if material is not None and category in ARMOUR:
        protection = max(protection, armour_protection(call.rules, material, worked))
    enchanted = clamp(pct(might, tools.craft_item_might_pct) + call.die(tools.craft_item_might_die) + magic)
    stats = {
        "damage": damage,
        "protection": protection,
        "might": min(enchanted, enchantment_cap(call.rules, material)) if material is not None else enchanted,
        "curse": clamp(call.die(tools.craft_curse_die) - tools.craft_curse_shift + (curse_bonus(call.rules, material) if material is not None else 0)),
    }
    label = args.category.value.replace("_", " ")
    subtype = lines.ITEM_SUBTYPE.format(label=label, subtype=args.subtype) if args.subtype else label
    home = await home_of(call)
    item = await create_record(
        call,
        MortalCreation(
            args.name,
            EntityType.ITEM,
            args.description,
            subtype=subtype,
            stats=stats,
            location_id=home.id if home is not None else None,
            image_prompt=args.image_prompt,
            tags=(category,),
        ),
    )
    if material is not None:
        await set_node_material(call.session, item.id, MaterialSlot.BODY, material.kind, material.world_material_id)
    bonds = BondRepository(call.session)
    for resource in resources:
        await bonds.connect(BondDraft(item.id, resource.id, BondKind.SOURCE_OF, call.epoch))
        set_stats(resource, abundance=max(0, stat_or(resource, "abundance", 0) - tools.craft_abundance_loss))
    await bonds.connect(BondDraft(call.me.id, item.id, BondKind.PRODUCED, call.epoch))
    owner = await call.session.get(EntityRow, args.owner_id) if args.owner_id is not None else None
    fit = owner is not None and owner.id != call.me.id and owner.status is EntityStatus.CANON and owner.entity_type in CARRIER_TYPES
    carrier = owner if fit and owner is not None and await near(call, owner) else call.me
    await bonds.connect(BondDraft(carrier.id, item.id, BondKind.OWNS, call.epoch))
    quality = "masterwork" if damage + protection >= tools.craft_masterwork else "sturdy" if damage + protection >= tools.craft_sturdy else "crude"
    await call.chronicle(
        ChronicleKind.PRODUCTION,
        lines.PRODUCED,
        entity_ids=[call.me.id, item.id],
        me=call.me.name,
        resources=" and ".join(resource.name for resource in resources),
        name=item.name,
        category=label,
        quality=lines.QUALITY[quality],
    )
    return result(MortalResult.PRODUCED, id=item.id, name=item.name, damage=damage, protection=protection, might=stats["might"])


async def build_structure(call: MortalCall, args: BuildInput) -> str:
    tools = call.rules.mortal_tools
    await name_free(call, args.name)
    location = await call.session.get(EntityRow, args.location_id) if args.location_id is not None else await home_of(call)
    if location is None or location.status is not EntityStatus.CANON or location.entity_type not in BUILD_SITES:
        fail(MortalResult.INVALID_LOCATION)
    if location.id != call.me.id and not await same_region(call, location):
        fail(MortalResult.NOT_YOUR_LAND)
    await require_craft(call)
    craft = await craft_of(call)
    await practised(call, (SkillKind.MASONRY, SkillKind.CARPENTRY, SkillKind.ENGINEERING), call.rules.skills.craft_xp)
    architecture = round(tools.build_architecture_bonus * await my_branch_effect(call, KnowledgeBranch.ARCHITECTURE))
    material = await chosen_material(call, args.material, [])
    lasting = decay_loss(call.rules, material, 0) if material is not None else 0
    holy = sanctity_splendour(call.rules, material) if material is not None else 0
    stats = {
        "splendor": clamp(pct(craft, tools.build_splendor_pct) + call.die(tools.build_splendor_die) + architecture + holy),
        "durability": clamp(pct(craft, tools.build_durability_pct) + call.die(tools.build_durability_die) + architecture - lasting),
        "function": clamp(tools.build_function_base + call.die(tools.build_function_die)),
    }
    work = await create_record(
        call,
        MortalCreation(
            args.name, EntityType.STRUCTURE, args.description, subtype=args.subtype, stats=stats, location_id=location.id, image_prompt=args.image_prompt
        ),
    )
    if material is not None:
        await set_node_material(call.session, work.id, MaterialSlot.BODY, material.kind, material.world_material_id)
    bonds = BondRepository(call.session)
    await bonds.connect(BondDraft(call.me.id, work.id, BondKind.BUILT, call.epoch))
    god = await call.session.get(SonRow, args.dedicated_son_id) if args.dedicated_son_id is not None else None
    living_god = god is not None and god.status is not SonStatus.DEAD
    await structure_profile(
        call.session,
        call.rules,
        call.epoch,
        work,
        args.structure_kind,
        builder=call.me,
        architect_id=call.me.id,
        son_id=god.id if god is not None and living_god else None,
    )
    if god is not None and god.status is not SonStatus.DEAD:
        await bonds.connect(BondDraft(work.id, god.id, BondKind.WORSHIPS, call.epoch, lines.OFFERING))
    for key in ("prosperity", "wealth"):
        value = stat(call.me, key)
        if value is not None:
            set_stats(call.me, **{key: max(0, value - tools.build_cost)})
    await call.chronicle(
        ChronicleKind.CONSTRUCTION,
        lines.BUILT,
        entity_ids=[call.me.id, work.id],
        me=call.me.name,
        name=work.name,
        location=location.name,
        subtype=lines.SUBTYPE_SUFFIX.format(subtype=work.subtype) if work.subtype else "",
        dedication=lines.DEDICATION.format(son=god.name) if god is not None and god.status is not SonStatus.DEAD else "",
    )
    return result(MortalResult.BUILT, id=work.id, name=work.name)


def _culture_stats(call: MortalCall, kind: CultureKind) -> dict[str, int]:
    tools = call.rules.mortal_tools
    if kind is CultureKind.ARTWORK:
        return {"renown": clamp(tools.artwork_base + call.die(tools.artwork_die)), "influence": clamp(tools.artwork_base + call.die(tools.artwork_die))}
    if kind is CultureKind.LAW:
        return {
            "rigidity": clamp(tools.law_rigidity_base + call.die(tools.law_rigidity_die)),
            "justice": clamp(tools.law_justice_base + call.die(tools.law_justice_die)),
        }
    return {"spread": tools.tradition_spread, "rigidity": tools.tradition_rigidity}


async def create_culture(call: MortalCall, args: CultureInput) -> str:
    tools = call.rules.mortal_tools
    await call.within_limit(TurnCounter.CULTURES_CREATED, tools.culture_per_epoch, "mortal_tools.culture_per_epoch", MortalResult.CULTURE_LIMIT)
    await name_free(call, args.name)
    home = await home_of(call) if args.kind in (CultureKind.ARTWORK, CultureKind.LAW) else None
    created = await create_record(
        call,
        MortalCreation(
            args.name,
            CULTURE_TYPES[args.kind],
            args.description,
            subtype=args.subtype,
            stats=_culture_stats(call, args.kind),
            location_id=home.id if home is not None else None,
            image_prompt=args.image_prompt,
            legend_category=args.legend_category,
        ),
    )
    bonds = BondRepository(call.session)
    await bonds.connect(BondDraft(call.me.id, created.id, CULTURE_BONDS[args.kind], call.epoch))
    patron = await bonds.patron(call.me.id)
    if args.kind is CultureKind.ARTWORK and patron is not None:
        await bonds.connect(BondDraft(created.id, patron, BondKind.TELLS_OF, call.epoch, lines.TELLS_OF_GOD))
    kind_label = lines.CULTURE_KINDS[args.kind.value]
    for related_id in (args.related_ids or [])[: tools.culture_max_related]:
        related = await call.session.get(EntityRow, related_id)
        if related is not None and related.status is EntityStatus.CANON and related.id != created.id:
            await bonds.connect(BondDraft(created.id, related.id, BondKind.TELLS_OF, call.epoch, lines.SUBJECT_OF.format(kind=kind_label)))
    await call.chronicle(ChronicleKind.CULTURE, lines.CULTURE, entity_ids=[call.me.id, created.id], kind=kind_label, me=call.me.name, name=created.name)
    await call.bump(TurnCounter.CULTURES_CREATED)
    return result(MortalResult.CULTURE_BORN, id=created.id, name=created.name)


async def discover_resource(call: MortalCall, args: DiscoverInput) -> str:
    tools = call.rules.mortal_tools
    await call.within_limit(
        TurnCounter.DISCOVERIES, tools.discover_resource_per_epoch, "mortal_tools.discover_resource_per_epoch", MortalResult.DISCOVERY_LIMIT
    )
    await name_free(call, args.name)
    location = await require_canon(call.session, args.location_id)
    if location.entity_type not in LAND or not await same_region(call, location):
        await fail_with_candidates(call, MortalResult.DISCOVER_OWN_REGION, LAND, local=True)
    stats = {
        "abundance": clamp(tools.discover_abundance_base + call.die(tools.discover_abundance_die)),
        "value": clamp(tools.discover_value_base + call.die(tools.discover_value_die)),
        "might": clamp(tools.discover_might_base + call.die(tools.discover_might_die)),
    }
    resource = await create_record(
        call,
        MortalCreation(
            args.name, EntityType.RESOURCE, args.description, subtype=args.subtype, stats=stats, location_id=location.id, image_prompt=args.image_prompt
        ),
    )
    resource.domain = match_domain(args.domain or "") or Domain.EARTH
    if args.commodity is not None:
        await set_resource_yield(call.session, call.rules, resource.id, args.commodity, args.material)
    else:
        region_id = (await call.atlas()).top_region(location.id)
        region = await call.session.get(RegionEnvironmentRow, region_id) if region_id is not None else None
        await ensure_profile(
            call.session, call.rules, resource, region, commodity=CommodityKind.ORE if args.material is not None else None, material=args.material
        )
    await BondRepository(call.session).connect(BondDraft(call.me.id, resource.id, BondKind.OWNS, call.epoch, lines.DISCOVERED_BOND))
    await assign_mechanics(call.session, call.rules, resource, resource_choice=args.mechanics or ())
    await call.bump(TurnCounter.DISCOVERIES)
    await call.chronicle(
        ChronicleKind.EXPLORATION,
        lines.DISCOVERED,
        entity_ids=[call.me.id, resource.id],
        me=call.me.name,
        name=resource.name,
        location=location.name,
        subtype=lines.SUBTYPE_SUFFIX.format(subtype=resource.subtype) if resource.subtype else "",
    )
    return result(MortalResult.DISCOVERED, id=resource.id, name=resource.name)


async def _seizure_holds(call: MortalCall, resource: EntityRow, owners: list[EntityRow]) -> tuple[bool, int, int]:
    tools = call.rules.mortal_tools
    mine = round(await military_strength(call.session, call.rules, call.me) + call.die(tools.seize_die, "seize_mine"))
    best = max([await military_strength(call.session, call.rules, owner) for owner in owners])
    theirs = round(best + tools.seize_defense + call.die(tools.seize_die, "seize_theirs"))
    if mine >= theirs:
        return True, mine, theirs
    if is_community(call.me):
        for owner in owners:
            if is_community(owner):
                await change_relation(
                    call.tick,
                    owner.id,
                    call.me.id,
                    -tools.seize_repelled_relation,
                    MemoryKind.HARMED_ME,
                    note=lines.SEIZE_ATTEMPT.format(resource=resource.name),
                )
    names = JOIN.join(owner.name for owner in owners)
    await call.chronicle(
        ChronicleKind.RESOURCE,
        lines.SEIZE_REPELLED,
        entity_ids=[call.me.id, resource.id, *(owner.id for owner in owners)],
        me=call.me.name,
        resource=resource.name,
        owners=names,
    )
    return False, mine, theirs


async def claim_resource(call: MortalCall, args: ClaimInput) -> str:
    tools = call.rules.mortal_tools
    await call.within_limit(TurnCounter.CLAIMS, tools.claim_per_epoch, "mortal_tools.claim_per_epoch", MortalResult.CLAIM_LIMIT)
    resource = await require_canon(call.session, args.resource_id)
    if resource.entity_type is not EntityType.RESOURCE:
        await fail_with_candidates(call, MortalResult.NOT_A_RESOURCE, [EntityType.RESOURCE], local=True)
    if not await same_region(call, resource):
        await fail_with_candidates(call, MortalResult.RESOURCE_NOT_ON_LAND, [EntityType.RESOURCE], local=True)
    bonds = BondRepository(call.session)
    if await bonds.exists_between(call.me.id, resource.id, BondKind.OWNS):
        fail(MortalResult.ALREADY_YOURS)
    if resource.engine_kind is EngineKind.COSMIC_TRAVEL_RESOURCE and not unlocked(
        call.rules, await civilization_tier(call.session, call.me), TierCapability.DEPOSIT_CLAIM
    ):
        fail(MortalResult.DEPOSIT_TIER)
    holders = [await call.session.get(EntityRow, bond.source_node_id) for bond in await bonds.incoming(resource.id, BondKind.OWNS)]
    owners = [owner for owner in holders if owner is not None and owner.status is EntityStatus.CANON and owner.id != call.me.id]
    cost = tools.claim_action_cost + (tools.seize_action_cost if owners else 0)
    if cost > 0 and call.turn.action_points < cost:
        fail(MortalResult.CLAIM_ACTIONS, cost=cost, seizing=bool(owners))
    call.charge_actions(cost)
    if owners:
        holds, mine, theirs = await _seizure_holds(call, resource, owners)
        if not holds:
            return result(MortalResult.SEIZE_REPELLED, mine=mine, theirs=theirs, name=resource.name, owners=JOIN.join(owner.name for owner in owners))
    angered: list[str] = []
    for bond in await bonds.incoming(resource.id, BondKind.OWNS):
        owner = await call.session.get(EntityRow, bond.source_node_id)
        await bonds.deactivate(bond, call.epoch, lines.SEIZED_NOTE.format(me=call.me.name, epoch=call.epoch)[:KEY_MAX_LENGTH])
        if owner is None or owner.status is not EntityStatus.CANON or not is_community(owner):
            continue
        angered.append(owner.name)
        reason = lines.CONFISCATION.format(resource=resource.name)
        grudge = (
            await change_relation(call.tick, owner.id, call.me.id, -tools.seizure_relation_loss, MemoryKind.HARMED_ME, note=reason)
            if is_community(call.me)
            else -tools.seize_war_threshold
        )
        if grudge <= -tools.seize_war_threshold:
            await declare_war(call.tick, owner.id, call.me.id, reason, cause=WarCause.RESOURCE)
    await bonds.connect(BondDraft(call.me.id, resource.id, BondKind.OWNS, call.epoch))
    call.target(resource.id)
    await call.bump(TurnCounter.CLAIMS)
    names = angered[: tools.chronicle_named_communities]
    await call.chronicle(
        ChronicleKind.RESOURCE,
        lines.CLAIMED,
        entity_ids=[call.me.id, resource.id],
        me=call.me.name,
        resource=resource.name,
        angered=lines.ANGERED.format(owners=JOIN.join(names)) if names else "",
    )
    return result(MortalResult.CLAIMED, name=resource.name, angered=JOIN.join(names))


async def found_settlement(call: MortalCall, args: SettleInput) -> str:
    tools = call.rules.mortal_tools
    limits = call.rules.limits
    await name_free(call, args.name)
    location = await require_canon(call.session, args.location_id)
    if location.entity_type not in LAND or not await near(call, location):
        fail(MortalResult.SETTLE_NEAR)
    key = headcount_key(call.me)
    if key is None:
        fail(MortalResult.NO_MIGRANTS)
    current = stat_or(call.me, key, 0)
    floor = (
        tools.cult_min_followers_kept
        if key == "followers"
        else limits.people_population_floor
        if call.me.entity_type is EntityType.PEOPLE
        else limits.population_floor
    )
    available = max(0, current - floor)
    minimum = max(tools.settle_min_migrants, limits.population_floor)
    migrants = min(available, limits.settlement_population_cap, max(minimum, round(pct(current, tools.settle_migration_pct))))
    if migrants < minimum:
        kind = "disciples" if key == "followers" else "people"
        fail(MortalResult.TOO_FEW_MIGRANTS, minimum=minimum, available=available, kind=kind)
    set_stats(call.me, **{key: current - migrants})
    stats = {
        "population": migrants,
        "prosperity": tools.new_settlement_prosperity,
        "defense": tools.new_settlement_defense,
        "piety": tools.new_settlement_piety,
    }
    power = max(1, call.me.power_level - 1)
    settlement = await create_record(
        call,
        MortalCreation(
            args.name,
            EntityType.SETTLEMENT,
            args.description,
            subtype=args.subtype,
            stats=stats,
            location_id=location.id,
            power=power,
            image_prompt=args.image_prompt,
        ),
    )
    bonds = BondRepository(call.session)
    await bonds.connect(BondDraft(call.me.id, settlement.id, BondKind.MIGRATED_TO, call.epoch, lines.MIGRANTS.format(count=migrants)))
    await bonds.connect(BondDraft(settlement.id, call.me.id, BondKind.DESCENDS_FROM, call.epoch))
    language = await spoken_language(call.session, call.me.id)
    if language is not None:
        await bonds.connect(BondDraft(settlement.id, language.id, BondKind.SPEAKS, call.epoch))
    patron = await bonds.patron(call.me.id)
    if patron is not None:
        await bonds.connect(BondDraft(settlement.id, patron, BondKind.WORSHIPS, call.epoch))
    await call.chronicle(
        ChronicleKind.MIGRATION,
        lines.MIGRATED,
        entity_ids=[call.me.id, settlement.id],
        count=migrants,
        me=call.me.name,
        name=settlement.name,
        location=location.name,
    )
    return result(MortalResult.SETTLED, id=settlement.id, name=settlement.name, count=migrants)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    standard = mortal_standard_action
    return [
        ToolSpec(MortalToolId.PRODUCE_ITEM, mortal, ProduceInput, ToolMeta(ActionKind.PRODUCE, standard), produce_item),
        ToolSpec(MortalToolId.BUILD_STRUCTURE, mortal, BuildInput, ToolMeta(ActionKind.BUILD, standard), build_structure),
        ToolSpec(MortalToolId.CREATE_CULTURE, mortal, CultureInput, ToolMeta(ActionKind.CREATE_CULTURE, standard), create_culture),
        ToolSpec(MortalToolId.DISCOVER_RESOURCE, mortal, DiscoverInput, ToolMeta(ActionKind.DISCOVER_RESOURCE, standard), discover_resource),
        ToolSpec(MortalToolId.CLAIM_RESOURCE, mortal, ClaimInput, ToolMeta(ActionKind.CLAIM, no_cost), claim_resource),
        ToolSpec(MortalToolId.FOUND_SETTLEMENT, mortal, SettleInput, ToolMeta(ActionKind.FOUND_SETTLEMENT, standard), found_settlement),
    ]

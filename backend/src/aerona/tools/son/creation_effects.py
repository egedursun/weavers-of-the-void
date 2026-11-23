from dataclasses import dataclass
from typing import Any

from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.catalog.life.tools import VESSEL_ROUTES
from aerona.catalog.tenets import OPPOSED
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import fill, spoken
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.polity import LawProfileRow
from aerona.db.tables.structures import StructureDesignRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import RiteStage, TraditionFunction
from aerona.domain.enums.demography import FuneralCustom
from aerona.domain.enums.economy import MaterialSlot
from aerona.domain.enums.entity import AGENT_TYPES, EntityStatus, EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.polity import LegitimacyBasis
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.travel import VehicleKind
from aerona.engine.cosmos.routes import RouteSpec, method_label, open_route
from aerona.engine.cosmos.vessels import set_vessel_kind
from aerona.engine.economy.materials import set_node_material
from aerona.engine.economy.provenance import ensure_materials
from aerona.engine.economy.resources import set_resource_yield
from aerona.engine.environment.places import write_kind
from aerona.engine.factions.book import new_profile
from aerona.engine.faith.book import FaithBook
from aerona.engine.faith.doctrine import found_doctrine
from aerona.engine.gods.queries import worshippers_of
from aerona.engine.lore import art, items, legends, prophecy, traditions
from aerona.engine.military.shipyard import Commission, commission
from aerona.engine.phases.society_support.knowledge import teach
from aerona.engine.polity.laws import attach_profile
from aerona.engine.primitives.language_profile import language_profile
from aerona.engine.primitives.mechanics import assign_mechanics
from aerona.engine.primitives.stats import set_stats
from aerona.engine.structures.profiles import ensure_profile
from aerona.prompts.tools.results import SonResult, result
from aerona.rules.registry import Rules
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.shared_inputs import add_words
from aerona.tools.framework.validation import fail, state_reason
from aerona.tools.son import lines
from aerona.tools.son.creation_inputs import CreationInput
from aerona.tools.son.support import ensure_in_reach, shift_relation

PERCENT = 100
SEVERITY_KEY = "severity"
MECHANIC_TYPES = frozenset({EntityType.RESOURCE, EntityType.NATURAL_LAW})
HOLDER_BONDS = {EntityType.ITEM: BondKind.OWNS, EntityType.TRADITION: BondKind.CELEBRATES, EntityType.KNOWLEDGE: BondKind.KNOWS}
NONE_AVAILABLE = "none"
LIST_SEPARATOR = ", "


@dataclass(frozen=True)
class PlannedEffect:
    target: EntityRow
    stat: str
    percent: float


@dataclass(frozen=True)
class EffectPlan:
    severity: int
    effects: tuple[PlannedEffect, ...]
    clipped: tuple[str, ...] = ()


def bounded_percent(rules: Rules, percent: float, severity: int, power: int) -> float:
    tools = rules.son_tools
    limit = min(severity, max(1, power) * tools.event_effect_per_power_pct)
    return max(-min(-tools.event_effect_min_pct, limit), min(tools.event_effect_max_pct, limit, percent))


def present_stats(entity: EntityRow) -> list[str]:
    return [field.key for field in ENTITY_TYPES[entity.entity_type].stats if getattr(entity.stats, field.key, None) is not None]


async def check_effects(call: SonCall, args: CreationInput, stats: dict[str, Any], power: int) -> EffectPlan | None:
    requested = args.option("effects") or []
    if not requested:
        return None
    tools = call.rules.son_tools
    given = stats.get(SEVERITY_KEY)
    severity = max(0, min(PERCENT, given if isinstance(given, int) else tools.event_severity_base + power * tools.event_severity_per_power))
    planned: list[PlannedEffect] = []
    clipped: list[str] = []
    seen: set[tuple[int, str]] = set()
    for effect in requested[: tools.event_max_effects]:
        target = await call.session.get(EntityRow, effect.entity_id)
        reason = state_reason(target, effect.entity_id)
        if reason is not None or target is None:
            fail(SonResult.EFFECT_TARGET, reason=reason)
        await ensure_in_reach(call, target)
        available = present_stats(target)
        if effect.stat not in available:
            fail(SonResult.EFFECT_NO_STAT, id=target.id, name=target.name, stat=effect.stat, available=LIST_SEPARATOR.join(available) or NONE_AVAILABLE)
        if (target.id, effect.stat) in seen:
            continue
        seen.add((target.id, effect.stat))
        percent = bounded_percent(call.rules, effect.percent, severity, power)
        if percent != effect.percent:
            clipped.append(result(SonResult.EFFECT_CLIPPED, name=target.name, stat=effect.stat, asked=f"{effect.percent:g}", kept=f"{percent:g}"))
        planned.append(PlannedEffect(target, effect.stat, percent))
    return EffectPlan(severity, tuple(planned), tuple(clipped))


async def apply_effects(call: SonCall, event: EntityRow, plan: EffectPlan | None) -> list[str]:
    if plan is None:
        return []
    notes: list[str] = []
    bonds = BondRepository(call.session)
    angered: set[int] = set()
    for effect in plan.effects:
        maker = effect.target.creator_son_id
        if maker is not None and maker != call.son.id and maker not in angered:
            angered.add(maker)
            await shift_relation(call, maker, -call.rules.son_tools.event_touch_relation)
        field = ENTITY_TYPES[effect.target.entity_type].stat(effect.stat)
        old = getattr(effect.target.stats, effect.stat, None)
        if field is None or not isinstance(old, int):
            continue
        low, high = field.bounds(call.rules)
        new = max(low, round(old * (1 + effect.percent / PERCENT)))
        new = new if high is None else min(high, new)
        set_stats(effect.target, **{effect.stat: new})
        note = lines.EFFECT_NOTE.format(label=field.label, old=old, new=new)
        await bonds.connect(BondDraft(event.id, effect.target.id, BondKind.CAUSED, call.epoch, note))
        notes.append(f"{effect.target.name}: {note}")
    return notes


async def mandatory_holder(call: SonCall, created: EntityRow, linked: list[EntityRow], location: EntityRow | None) -> None:
    kind = HOLDER_BONDS.get(created.entity_type)
    if kind is None:
        return
    if await BondRepository(call.session).incoming(created.id, kind):
        return
    worshippers = sorted(await worshippers_of(call.session, call.son.id), key=lambda entity: -entity.id)
    settlement = [location] if location is not None and location.entity_type is EntityType.SETTLEMENT else []
    for candidate in [*linked, *settlement, *worshippers]:
        if candidate.status is not EntityStatus.CANON or candidate.entity_type not in AGENT_TYPES or candidate.entity_type is EntityType.SPECIES:
            continue
        if candidate.world_id != created.world_id:
            continue
        if kind is BondKind.KNOWS:
            await teach(call.tick, candidate.id, created, lines.TAUGHT_BY.format(son=call.son.name))
        else:
            await BondRepository(call.session).connect(BondDraft(candidate.id, created.id, kind, call.epoch))
        return


async def _vessel_route(call: SonCall, args: CreationInput, created: EntityRow) -> str | None:
    kind = args.option("vessel_kind") or VehicleKind.SHIP
    await set_vessel_kind(call.session, created.id, kind)
    if kind is VehicleKind.SHIP:
        await commission(
            call.session,
            call.rules,
            created,
            Commission(
                frame=args.option("frame"),
                hull_material=args.option("hull_material"),
                fabric_material=args.option("fabric_material"),
                home_port_id=args.option("home_port_id"),
                captain_id=args.option("captain_id"),
            ),
        )
    target_id = args.option("target_world_id")
    target = await call.session.get(WorldRow, target_id) if target_id is not None else None
    if target is None or target.id == created.world_id or kind not in VESSEL_ROUTES:
        return None
    method = VESSEL_ROUTES[kind]
    spec = RouteSpec(
        first_world_id=created.world_id,
        second_world_id=target.id,
        method=method,
        vehicle_id=created.id,
        builder_son_id=call.son.id if kind is VehicleKind.BRIDGE else None,
        description=lines.VESSEL_ROUTE.format(son=call.son.name, vessel=created.name),
    )
    route = await open_route(call.session, call.rules, call.rng("route"), call.epoch, spec)
    return result(SonResult.ROUTE_OPENED, id=route.id, world=target.name, method=method_label(method))


async def _son_materials(call: SonCall, args: CreationInput, created: EntityRow) -> None:
    chosen = {
        MaterialSlot.BODY: (args.option("material"), args.option("world_material_id")),
        MaterialSlot.HULL: (args.option("hull_material"), None),
        MaterialSlot.FABRIC: (args.option("fabric_material"), None),
    }
    for slot, (material, world_material_id) in chosen.items():
        known = world_material_id is not None and await call.session.get(WorldMaterialRow, world_material_id) is not None
        if material is not None or known:
            await set_node_material(call.session, created.id, slot, material, world_material_id if known else None)
    await ensure_materials(call.session, created, rules=call.rules)


async def raise_divine_structure(call: SonCall, args: CreationInput, created: EntityRow, kind: StructureKind) -> str:
    design_id = args.option("design_id")
    design = await call.session.get(StructureDesignRow, design_id) if design_id is not None else None
    if design is not None and (design.retired or design.base_kind is not kind):
        design = None
    profile = await ensure_profile(
        call.session,
        call.rules,
        call.epoch,
        created,
        kind,
        level=args.option("level") or 1,
        design_id=design.id if design is not None else None,
        builder=call.son,
        son_id=call.son.id,
        material=args.option("material"),
    )
    return fill(lines.STRUCTURE_RAISED, kind=spoken(kind), effect=profile.effect_pct)


async def seed_lore_kinds(call: SonCall, args: CreationInput, created: EntityRow) -> None:
    if created.entity_type is EntityType.LEGEND:
        await legends.profile_of(call.tick, created, args.option("archetype"))
    if created.entity_type is EntityType.TRADITION:
        row = await traditions.profile_of(call.tick, created, args.option("tradition_kind") or TraditionFunction.FESTIVAL)
        row.calendar_slot = args.option("calendar_slot")
        taboo_target, taboo_act = args.option("taboo_target"), args.option("taboo_act")
        if taboo_target is not None:
            row.taboo_target = taboo_target.value
        row.taboo_act = taboo_act


async def seed_made_kinds(call: SonCall, args: CreationInput, created: EntityRow) -> None:
    if created.entity_type is EntityType.ITEM:
        row = await items.profile_of(call.tick, created, args.option("item_class"))
        row.secondary_materials = [item.value for item in args.option("secondary_materials") or []]
    if created.entity_type is EntityType.ARTWORK:
        work = await art.profile_of(call.tick, created, args.option("medium"))
        subject = args.option("subject_id")
        if subject is not None and await call.session.get(EntityRow, subject) is not None:
            work.subject_node_id = subject
    if created.entity_type is EntityType.PROPHECY:
        await prophecy.typed_condition(
            call.tick,
            created,
            prophecy.Foretelling(
                predicate=args.option("predicate"),
                subject_id=args.option("subject_id"),
                second_id=args.option("second_id"),
                archetype=args.option("archetype"),
                sky_kind=args.option("sky_kind"),
                event_kind=args.option("event_kind"),
                within_epochs=args.option("within_epochs"),
                consequence=args.option("consequence"),
                consequence_id=args.option("consequence_id"),
            ),
        )


async def teach_cult(call: SonCall, args: CreationInput, created: EntityRow) -> list[str]:
    await call.session.flush()
    church = (await FaithBook.load(call.session)).churches.get(created.id)
    if church is None or church.doctrine is not None:
        return []
    seeded: list[TenetKind] = []
    for tenet in args.option("tenets") or []:
        if tenet not in seeded and not any(frozenset({tenet, other}) in OPPOSED for other in seeded):
            seeded.append(tenet)
    doctrine = await found_doctrine(call.tick, church, seeded=tuple(seeded[: call.rules.doctrine.tenets_max]), judgement=args.option("judgement"))
    path = args.option("rebirth_path")
    if path is not None:
        doctrine.rebirth_path = path
    await call.session.flush()
    return [result(SonResult.CULT_TAUGHT, tenets=", ".join(sorted(spoken(tenet) for tenet in church.tenets)) or "none")]


async def keep_rite(call: SonCall, created: EntityRow, rite: FuneralCustom) -> None:
    profile = await traditions.profile_of(call.tick, created, TraditionFunction.RITE_OF_PASSAGE)
    reseed = profile.kind is not TraditionFunction.RITE_OF_PASSAGE or profile.stage is not RiteStage.DEATH
    profile.kind, profile.stage, profile.funeral_rite = TraditionFunction.RITE_OF_PASSAGE, RiteStage.DEATH, rite
    if reseed:
        await traditions.seed_effects(call.tick, profile, replace=True)
    profile.locked = [*profile.locked, "funeral_rite"] if "funeral_rite" not in profile.locked else profile.locked


async def polity_extras(call: SonCall, args: CreationInput, created: EntityRow) -> list[str]:
    notes: list[str] = []
    faction_kind = args.option("faction_kind")
    if created.entity_type is EntityType.FACTION and faction_kind is not None and await call.session.get(FactionProfileRow, created.id) is None:
        new_profile(call.tick, created, faction_kind)
    law_kind = args.option("law_kind")
    if created.entity_type is EntityType.LAW and law_kind is not None and await call.session.get(LawProfileRow, created.id) is None:
        holder = await call.session.get(EntityRow, created.location_id) if created.location_id is not None else None
        try:
            await attach_profile(
                call.session, created, law_kind, args.option("law_params"), holder=holder, epoch=call.epoch, by_id=None, basis=LegitimacyBasis.DIVINE
            )
        except ValidationFailedError:
            await attach_profile(call.session, created, law_kind, {}, holder=holder, epoch=call.epoch, by_id=None, basis=LegitimacyBasis.DIVINE)
            notes.append(f"Its terms were set to the custom of {spoken(law_kind)}.")
    return notes


async def language_extras(call: SonCall, args: CreationInput, created: EntityRow) -> None:
    words = args.option("words")
    if words:
        await add_words(call.session, created, words[: call.rules.son_tools.coin_word_max_words], actor=(ActorKind.SON, call.son.id), epoch=call.epoch)
    base = args.option("numeral_base")
    if base is not None:
        (await language_profile(call.session, created)).numeral_base = base


async def finish_extras(call: SonCall, args: CreationInput, created: EntityRow) -> list[str]:
    notes: list[str] = []
    await seed_lore_kinds(call, args, created)
    await seed_made_kinds(call, args, created)
    if created.entity_type is EntityType.VESSEL:
        route = await _vessel_route(call, args, created)
        if route is not None:
            notes.append(route)
    await _son_materials(call, args, created)
    kind = args.option("structure_kind")
    if created.entity_type is EntityType.STRUCTURE and kind is not None:
        notes.append(await raise_divine_structure(call, args, created, kind))
    if created.entity_type is EntityType.LANGUAGE:
        await language_extras(call, args, created)
    place_kind = args.option("place_kind")
    if created.entity_type is EntityType.PLACE and place_kind is not None:
        await write_kind(call.session, call.rules, created.id, place_kind)
    if created.entity_type is EntityType.RESOURCE:
        await set_resource_yield(call.session, call.rules, created.id, args.option("commodity"), args.option("material"))
    if created.entity_type in MECHANIC_TYPES:
        await assign_mechanics(call.session, call.rules, created, resource_choice=args.option("mechanics") or (), law_choice=args.option("mechanic"))
    if created.entity_type is EntityType.CULT:
        notes.extend(await teach_cult(call, args, created))
    rite = args.option("funeral_rite")
    if created.entity_type is EntityType.TRADITION and rite is not None:
        await keep_rite(call, created, rite)
    notes.extend(await polity_extras(call, args, created))
    learners = args.option("learner_ids") or []
    if created.entity_type is EntityType.KNOWLEDGE:
        for learner_id in learners[: call.rules.son_tools.knowledge_first_learners]:
            learner = await call.session.get(EntityRow, learner_id)
            if learner is not None and learner.status is EntityStatus.CANON:
                await teach(call.tick, learner.id, created, lines.TAUGHT_BY.format(son=call.son.name))
    return notes

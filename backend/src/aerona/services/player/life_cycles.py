from aerona.core.errors import ValidationFailedError
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.cosmos.pilgrimage import declare_pilgrimage_site
from aerona.engine.phases.casualties import FateWrit, write_fate
from aerona.engine.phases.ecology import set_abundance
from aerona.engine.phases.geography import seed_place_by_hand
from aerona.engine.phases.institutions import RecordEnd, merge_cult_by_hand, order_end, swallow_place_by_hand, unite_peoples
from aerona.engine.phases.life_cycles import dissolve_community, end_cost, raze_structure
from aerona.engine.phases.religion_spread import schism_candidate, split_cult
from aerona.engine.phases.remembrance import MemorialForm, commemorate
from aerona.engine.phases.world_balance import appoint_guardian, revive_world
from aerona.engine.primitives.faith import FaithIndex
from aerona.engine.primitives.stats import stat
from aerona.services.player import guards
from aerona.services.player.chronicle import hand
from aerona.services.player.lines import FATE_CLEARED, FATE_DOOMED, FATE_SHIELDED, MEMORIAL_ORDERED, RECORD_ENDED, WORLD_REVIVED
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

FATE_LINES = {FateWrit.DOOM: FATE_DOOMED, FateWrit.SHIELD: FATE_SHIELDED, FateWrit.CLEAR: FATE_CLEARED}


class CommunityEnd(Command):
    community_id: int
    reason: str = ""


class StructureEnd(Command):
    structure_id: int
    reason: str = ""


class MortalFate(Command):
    mortal_id: int
    fate: FateWrit


class Commemoration(Command):
    target_id: int
    form: MemorialForm


class WorldTarget(Command):
    world_id: int


class WorldGuardian(Command):
    world_id: int
    son_id: int


class SpeciesAbundance(Command):
    species_id: int
    abundance: int


class RegionTarget(Command):
    region_id: int


def _because(creator: str, reason: str) -> str:
    return f"{creator} willed it ({reason})" if reason else f"{creator} willed it"


@player_action("community:collapse", ActionKind.DISSOLVE_COMMUNITY)
async def collapse_community(scope: PlayerScope, command: CommunityEnd) -> Effect:
    community = await guards.canon_entity(scope.session, command.community_id, "The community")
    creator = await scope.creator()
    spent = guards.charge(creator, end_cost(scope.rules, community), "life_cycles.end_cost")
    await dissolve_community(await scope.context("collapse_community"), community.id, _because(creator.name, guards.clip(command.reason, 200)))
    return Effect(f"{community.name} collapsed.", community.id, essence_spent=spent)


@player_action("structure:raze", ActionKind.RAZE_STRUCTURE)
async def raze(scope: PlayerScope, command: StructureEnd) -> Effect:
    structure = guards.of_types(
        await guards.canon_entity(scope.session, command.structure_id, "The structure"), [EntityType.STRUCTURE], "Only a structure can be razed."
    )
    creator = await scope.creator()
    spent = guards.charge(creator, end_cost(scope.rules, structure), "life_cycles.end_cost")
    await raze_structure(await scope.context("raze_structure"), structure.id, _because(creator.name, guards.clip(command.reason, 200)))
    return Effect(f"{structure.name} was razed.", structure.id, essence_spent=spent)


@player_action("mortal:fate", ActionKind.WRITE_FATE)
async def fate(scope: PlayerScope, command: MortalFate) -> Effect:
    creator = await scope.creator()
    spent = 0 if command.fate is FateWrit.CLEAR else guards.charge(creator, scope.rules.casualties.fate_cost, "casualties.fate_cost")
    ctx = await scope.context("write_fate")
    mortal = await write_fate(ctx, command.mortal_id, command.fate)
    text = await hand(ctx, creator, FATE_LINES[command.fate], ids=[mortal.id], mortal=mortal.name)
    return Effect(text, mortal.id, essence_spent=spent)


@player_action("memorial:order", ActionKind.COMMEMORATE)
async def order_memorial(scope: PlayerScope, command: Commemoration) -> Effect:
    subject = await guards.entity(scope.session, command.target_id)
    creator = await scope.creator()
    spent = guards.charge(creator, scope.rules.remembrance.commemorate_cost, "remembrance.commemorate_cost")
    ctx = await scope.context("commemorate")
    created = await commemorate(ctx, subject.id, command.form)
    names = ", ".join(entity.name for entity in [await guards.entity(scope.session, record_id) for record_id in created])
    text = await hand(ctx, creator, MEMORIAL_ORDERED, ids=[subject.id, *created], subject=subject.name, memorials=names)
    return Effect(text, subject.id, essence_spent=spent, created_ids=tuple(created))


@player_action("world:revive", ActionKind.REVIVE_WORLD)
async def revive(scope: PlayerScope, command: WorldTarget) -> Effect:
    world = await guards.open_world(scope.session, command.world_id)
    creator = await scope.creator()
    spent = guards.charge(creator, scope.rules.world_balance.revive_cost, "world_balance.revive_cost")
    ctx = await scope.context("revive_world")
    created = await revive_world(ctx, world.id)
    text = await hand(ctx, creator, WORLD_REVIVED, ids=created, world_id=world.id, world=world.name)
    return Effect(text, world.id, essence_spent=spent, created_ids=tuple(created))


@player_action("world:guardian", ActionKind.APPOINT_GUARDIAN)
async def guardian(scope: PlayerScope, command: WorldGuardian) -> Effect:
    creator = await scope.creator()
    spent = guards.charge(creator, scope.rules.world_balance.guardian_cost, "world_balance.guardian_cost")
    text = await appoint_guardian(await scope.context("appoint_guardian"), command.world_id, command.son_id)
    return Effect(text, command.world_id, essence_spent=spent)


@player_action("species:abundance", ActionKind.SET_ABUNDANCE)
async def abundance(scope: PlayerScope, command: SpeciesAbundance) -> Effect:
    species = await set_abundance(await scope.context("set_abundance"), command.species_id, command.abundance)
    return Effect(f"{species.name} now numbers {stat(species, 'abundance')}.", species.id)


@player_action("region:seed_place", ActionKind.SEED_PLACE)
async def seed(scope: PlayerScope, command: RegionTarget) -> Effect:
    creator = await scope.creator()
    seeded = await seed_place_by_hand(await scope.context("seed_place"), command.region_id, creator.name)
    return Effect(seeded.text, seeded.place.id, created_ids=(seeded.place.id,))


class SiteTarget(Command):
    entity_id: int


@player_action("pilgrimage:declare", ActionKind.DECLARE_PILGRIMAGE_SITE)
async def declare_site(scope: PlayerScope, command: SiteTarget) -> Effect:
    creator = await scope.creator()
    site = await declare_pilgrimage_site(await scope.context("pilgrimage_site"), command.entity_id, creator.name)
    return Effect(f"{site.name} became a pilgrimage site.", site.id)


class RecordEndOrder(Command):
    entity_id: int
    end: RecordEnd
    reason: str = ""


@player_action("record:end", ActionKind.ORDER_END)
async def end_record(scope: PlayerScope, command: RecordEndOrder) -> Effect:
    record = await guards.canon_entity(scope.session, command.entity_id)
    creator = await scope.creator()
    spent = guards.charge(creator, end_cost(scope.rules, record), "life_cycles.end_cost")
    reason = guards.clip(command.reason, 200)
    ctx = await scope.context("order_end")
    await order_end(ctx, record.id, command.end, _because(creator.name, reason))
    text = await hand(ctx, creator, RECORD_ENDED, ids=[record.id], record=record.name, end=command.end.value, reason=f" ({reason})" if reason else "")
    return Effect(text, record.id, essence_spent=spent)


class Union(Command):
    source_id: int
    into_id: int


class PlaceTarget(Command):
    place_id: int


@player_action("cult:merge", ActionKind.ORDER_END)
async def merge_cult(scope: PlayerScope, command: Union) -> Effect:
    into = await merge_cult_by_hand(await scope.context("merge_cult"), command.source_id, command.into_id)
    return Effect(f"The cult merged into {into.name}.", into.id)


@player_action("people:unite", ActionKind.ORDER_END)
async def unite(scope: PlayerScope, command: Union) -> Effect:
    into = await unite_peoples(await scope.context("unite_peoples"), command.source_id, command.into_id)
    return Effect(f"The two peoples became {into.name}.", into.id)


@player_action("place:swallow", ActionKind.ORDER_END)
async def swallow_place(scope: PlayerScope, command: PlaceTarget) -> Effect:
    place = await guards.canon_entity(scope.session, command.place_id, "The place")
    creator = await scope.creator()
    spent = guards.charge(creator, end_cost(scope.rules, place), "life_cycles.end_cost")
    await swallow_place_by_hand(await scope.context("swallow_place"), place.id)
    return Effect(f"{place.name} was unmade by the Creator's hand.", place.id, essence_spent=spent)


class Schism(Command):
    cult_id: int
    son_id: int | None = None


@player_action("cult:schism", ActionKind.CONVERT)
async def schism(scope: PlayerScope, command: Schism) -> Effect:
    cult = await guards.canon_entity(scope.session, command.cult_id, "The cult")
    if cult.entity_type is not EntityType.CULT:
        raise ValidationFailedError(f"{cult.name} is not a cult.")
    faith = await FaithIndex.load(scope.session)
    old_patron = faith.patron(cult.id)
    sons = list(faith.sons.values())
    chosen = next((son for son in sons if son.id == command.son_id), None)
    candidate = chosen if command.son_id is not None else schism_candidate(sons, old_patron, cult.world_id)
    if candidate is None or candidate.id == old_patron:
        raise ValidationFailedError("No son can take the breaking sect.")
    sect = await split_cult(await scope.context("cult_schism"), cult, candidate, old_patron)
    return Effect(f"{cult.name} split; {sect.name} follows {candidate.name}.", sect.id, created_ids=(sect.id,))

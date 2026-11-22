from sqlalchemy import select

from aerona.catalog.life.living import STANCE_SIGN
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.faith import CultDoctrineRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityFlag, EntityStatus
from aerona.domain.enums.living import LivingCraftStance
from aerona.domain.enums.mind import MemoryKind, ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.engine.context import TickContext
from aerona.engine.factions.companies import realm_of
from aerona.engine.made.doctrine import doctrine_here
from aerona.engine.mind.book import values_for
from aerona.engine.minds.continuity import law_for
from aerona.engine.minds.values import liberty_of
from aerona.engine.recording.record import record
from aerona.engine.sacred.places import church_of
from aerona.engine.services.community_relations import change_relation

LEAN = 25
STATUS_STEPS = ("property", "ward", "servant", "citizen", "sovereign")
STANCE_COLUMNS = ("living_craft_stance", "germline_stance", "clone_stance")


def living_stance(values: dict[ValueAxis, int]) -> LivingCraftStance:
    order = values.get(ValueAxis.PURITY, 0) + values.get(ValueAxis.TRADITION, 0)
    craft = values.get(ValueAxis.KNOWLEDGE, 0) + values.get(ValueAxis.CRAFTSMANSHIP, 0)
    if order >= LEAN * 2 and order > craft:
        return LivingCraftStance.ABOMINATION
    if craft >= LEAN * 2:
        return LivingCraftStance.PERMITTED
    if values.get(ValueAxis.PIETY, 0) >= LEAN and values.get(ValueAxis.FAMILY, 0) >= LEAN:
        return LivingCraftStance.SACRED_DUTY
    return LivingCraftStance.SILENT


async def doctrine_stances(ctx: TickContext) -> int:
    set_from = 0
    for doctrine in list(await ctx.session.scalars(select(CultDoctrineRow).order_by(CultDoctrineRow.cult_entity_id))):
        if held(doctrine.cult_entity_id):
            continue
        values = dict(await values_for(ctx.session, doctrine.cult_entity_id))
        kept = set(doctrine.locked or [])
        for column in STANCE_COLUMNS:
            if column not in kept:
                setattr(doctrine, column, living_stance(values))
        set_from += 1
    return set_from


async def faith_on_maker(ctx: TickContext, maker: EntityRow, germline: bool) -> None:
    doctrine = await doctrine_here(ctx.session, maker)
    if doctrine is None:
        return
    stance = doctrine.germline_stance if germline else doctrine.living_craft_stance
    sign = STANCE_SIGN[stance]
    town = await ctx.session.get(EntityRow, maker.location_id) if maker.location_id is not None else None
    church = await church_of(ctx.session, town) if town is not None else None
    if sign and church is not None and not held(church.id):
        memory = MemoryKind.GOODWILL if sign > 0 else MemoryKind.HUMILIATED_ME
        await change_relation(ctx, church.id, maker.id, sign * ctx.rules.clones.stance_regard, memory, note="judged for making life")


async def rise_against(ctx: TickContext, being: EntityRow, law: LawKind, label: str) -> bool:
    table = ctx.rules.clones
    status = await law_for(ctx, being, law, "status") or "property"
    step = STATUS_STEPS.index(status) if status in STATUS_STEPS else 0
    wanted = 3 if await liberty_of(ctx.session, being.id) > 0 else 1
    if wanted - step < table.movement_gap:
        return False
    realm = await realm_of(ctx, being.location_id)
    if realm is None or held(realm) or not ctx.rng(f"living.rising.{being.id}.{ctx.epoch}").chance(table.movement_chance):
        return False
    await change_relation(ctx, being.id, realm, -table.bond_by_status, MemoryKind.HUMILIATED_ME, note=f"held as {status}")
    await record(ctx, "living.rising", roles={IncidentRole.ACTOR: being.id, IncidentRole.AUTHORITY: realm}, facts={"law": law, "wanted": wanted, "step": step})
    return True


async def keep_standing(ctx: TickContext) -> int:
    risen = 0
    clones = select(BondRow.source_node_id).where(BondRow.kind == BondKind.CLONE_OF, BondRow.state == BondState.ACTIVE).distinct()
    for clone_id in list(await ctx.session.scalars(clones)):
        clone = await ctx.session.get(EntityRow, clone_id)
        if clone is None or clone.status is not EntityStatus.CANON or held(clone.id):
            continue
        risen += await rise_against(ctx, clone, LawKind.CLONE_STATUS, "clones")
        doctrine = await doctrine_here(ctx.session, clone)
        town = await ctx.session.get(EntityRow, clone.location_id) if clone.location_id is not None else None
        church = await church_of(ctx.session, town) if town is not None else None
        sign = STANCE_SIGN[doctrine.clone_stance] if doctrine is not None else 0
        if sign and church is not None and not held(church.id):
            memory = MemoryKind.GOODWILL if sign > 0 else MemoryKind.HUMILIATED_ME
            await change_relation(ctx, church.id, clone.id, sign * ctx.rules.clones.stance_regard, memory, note="judged for being a clone")
    designed = select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.DESIGNED_PEOPLE)
    for people_id in list(await ctx.session.scalars(designed)):
        people = await ctx.session.get(EntityRow, people_id)
        if people is not None and people.status is EntityStatus.CANON and not held(people.id):
            risen += await rise_against(ctx, people, LawKind.DESIGNED_STATUS, "designed folk")
    return risen

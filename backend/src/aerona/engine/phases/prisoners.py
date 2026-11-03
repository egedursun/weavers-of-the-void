from sqlalchemy import select

from aerona.core.errors import ConflictError, NotFoundError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES
from aerona.domain.enums.mind import ActKind, MemoryKind
from aerona.domain.enums.war import CaptiveStatus
from aerona.engine.body.book import effective
from aerona.engine.context import TickContext
from aerona.engine.mind.drives import cruelty_drive
from aerona.engine.mind.hooks import witnessed
from aerona.engine.phase import Phase
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.records import death_path
from aerona.engine.services.community_relations import change_relation, relation, start_blood_feud
from aerona.engine.services.war import release_captive

HOME_BOND_KINDS = (BondKind.PROTECTS, BondKind.DESCENDS_FROM)


async def _note(ctx: TickContext, kind: ChronicleKind, text: str, key: str, ids: tuple[int, ...]) -> None:
    await ctx.chronicle(kind, text, template_key=key, entity_ids=ids)


async def home_of(ctx: TickContext, captive: EntityRow, row: CaptiveRow) -> EntityRow | None:
    bonds = BondRepository(ctx.session)
    for kind in HOME_BOND_KINDS:
        for bond in await bonds.outgoing(captive.id, kind):
            target = await living_entity(ctx.session, bond.target_node_id)
            if target is not None and target.entity_type in COMMUNITY_TYPES:
                return target
    return await living_entity(ctx.session, row.home_entity_id)


def _is_rich(ctx: TickContext, home: EntityRow) -> bool:
    campaigns = ctx.rules.campaigns
    return (stat(home, "wealth") or 0) >= campaigns.ransom_min_wealth or (stat(home, "prosperity") or 0) >= campaigns.ransom_min_prosperity


async def pay_ransom(ctx: TickContext, row: CaptiveRow, captive: EntityRow, captor: EntityRow, home: EntityRow) -> None:
    cost = ctx.rules.campaigns.ransom_cost
    shift_stat(home, "wealth", -cost)
    shift_stat(home, "prosperity", -cost)
    shift_stat(captor, "wealth", cost)
    add_prosperity(ctx.rules, captor, cost)
    await change_relation(ctx, home.id, captor.id, ctx.rules.campaigns.ransom_relation, MemoryKind.FREED_US, note="ransom")
    await release_captive(ctx, row, CaptiveStatus.RANSOMED, cost)
    text = f"{home.name} paid {captor.name} a heavy ransom for {captive.name}; the prisoner returned home."
    await _note(ctx, ChronicleKind.RANSOM, text, "prisoner.ransomed", (captor.id, captive.id, home.id))


async def defect(ctx: TickContext, row: CaptiveRow, captive: EntityRow, captor: EntityRow) -> None:
    await release_captive(ctx, row, CaptiveStatus.TURNCOAT)
    bonds = BondRepository(ctx.session)
    for bond in await bonds.outgoing(captive.id, BondKind.PROTECTS):
        if bond.target_node_id != captor.id:
            await bonds.deactivate(bond, ctx.epoch, "turned to the captors")
    await bonds.connect(BondDraft(captive.id, captor.id, BondKind.PROTECTS, ctx.epoch, "from captivity to loyalty"))
    text = f"After years of captivity {captive.name} pledged to {captor.name} and joined their side."
    await _note(ctx, ChronicleKind.WAR, text, "prisoner.turncoat", (captor.id, captive.id))


async def _fate(ctx: TickContext, row: CaptiveRow, captive: EntityRow, captor: EntityRow) -> None:
    campaigns = ctx.rules.campaigns
    rng = ctx.rng("captivity")
    home = await home_of(ctx, captive, row)
    if home is not None and _is_rich(ctx, home) and rng.chance(campaigns.ransom_chance):
        await pay_ransom(ctx, row, captive, captor, home)
        return
    agility = await effective(ctx.session, captive, "agility", campaigns.captive_default_stat, rules=ctx.rules)
    intellect = await effective(ctx.session, captive, "intellect", campaigns.captive_default_stat, rules=ctx.rules)
    if rng.probability(agility / campaigns.escape_agility_divisor + intellect / campaigns.escape_intellect_divisor):
        await release_captive(ctx, row, CaptiveStatus.ESCAPED)
        await _note(ctx, ChronicleKind.ESCAPE, f"{captive.name} escaped from the dungeon of {captor.name}.", "prisoner.escaped", (captor.id, captive.id))
        return
    if (
        home is not None
        and await relation(ctx.session, ctx.rules, home.id, captor.id) <= -campaigns.execution_relation
        and rng.chance(campaigns.execution_chance * await cruelty_drive(ctx.session, ctx.rules, captor.id))
    ):
        await release_captive(ctx, row, CaptiveStatus.EXECUTED)
        await death_path(ctx, captive, f"executed by {captor.name}", captor.id, "execution", forced=True)
        await start_blood_feud(ctx, home.id, captor.id, f"the execution of {captive.name}")
        await witnessed(ctx, home.id, captor.id, ActKind.EXECUTION, base=ctx.rules.memory.outrage_magnitude, note=captive.name)
        text = f"{captor.name} executed its prisoner {captive.name}; {home.name} swore vengeance."
        await _note(ctx, ChronicleKind.WAR, text, "prisoner.executed", (captor.id, captive.id, home.id))
        return
    if ctx.epoch - row.taken_epoch >= campaigns.captive_defection_epochs and rng.chance(campaigns.captive_defection_chance):
        await defect(ctx, row, captive, captor)


async def prisoners(ctx: TickContext) -> None:
    rows = list(await ctx.session.scalars(select(CaptiveRow).where(CaptiveRow.status == CaptiveStatus.HELD).order_by(CaptiveRow.id)))
    for row in rows:
        captive, captor = await living_entity(ctx.session, row.captive_entity_id), await living_entity(ctx.session, row.captor_entity_id)
        if captive is None:
            await release_captive(ctx, row, CaptiveStatus.RELEASED)
            continue
        if captor is None:
            await release_captive(ctx, row, CaptiveStatus.RELEASED)
            text = f"{captive.name} was freed from captivity when the captors scattered."
            await _note(ctx, ChronicleKind.RESCUE, text, "prisoner.freed", (row.captor_entity_id, captive.id))
            continue
        if row.taken_epoch == ctx.epoch:
            continue
        await _fate(ctx, row, captive, captor)
    ctx.count("prisoners_held", len(rows))


async def _held(ctx: TickContext, captive_row_id: int) -> tuple[CaptiveRow, EntityRow, EntityRow]:
    row = await ctx.session.get(CaptiveRow, captive_row_id)
    if row is None:
        raise NotFoundError("No such prisoner.")
    if row.status is not CaptiveStatus.HELD:
        raise ConflictError("That prisoner is no longer held.")
    captive, captor = await living_entity(ctx.session, row.captive_entity_id), await living_entity(ctx.session, row.captor_entity_id)
    if captive is None or captor is None:
        raise ConflictError("The prisoner or the captor is gone.")
    return row, captive, captor


async def free_prisoner(ctx: TickContext, captive_row_id: int) -> CaptiveRow:
    row, captive, captor = await _held(ctx, captive_row_id)
    await release_captive(ctx, row, CaptiveStatus.RESCUED)
    await _note(ctx, ChronicleKind.RESCUE, f"The Creator freed {captive.name} from {captor.name}.", "prisoner.freed_by_decree", (captor.id, captive.id))
    return row


async def order_ransom(ctx: TickContext, captive_row_id: int) -> CaptiveRow:
    row, captive, captor = await _held(ctx, captive_row_id)
    home = await home_of(ctx, captive, row)
    if home is None:
        raise ConflictError(f"{captive.name} has no homeland to pay a ransom.")
    await pay_ransom(ctx, row, captive, captor, home)
    return row


PHASES = (Phase("prisoners", prisoners),)

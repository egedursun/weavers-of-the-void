from sqlalchemy import select

from aerona.core.errors import ConflictError, NotFoundError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.mind import ActKind, MemoryKind, ValueAxis, ValueHolder
from aerona.domain.enums.war import CaptiveStatus
from aerona.engine.body.book import effective
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.taboos import forbidden
from aerona.engine.military.captivity import announce, cohort_fates, ransom_lawful, rich, wring_intel
from aerona.engine.military.ransom import grow_ward, marry_captive, named_ransom, pay_from_treasury, release_by_opinion, ward_returns
from aerona.engine.mind.book import stored_values, values_for, write_values
from aerona.engine.mind.drives import closeness, cruelty_drive
from aerona.engine.mind.hooks import judged, witnessed
from aerona.engine.mind.memories import remember
from aerona.engine.mortal.kin import close_kin_of
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


async def pay_ransom(ctx: TickContext, row: CaptiveRow, captive: EntityRow, captor: EntityRow, home: EntityRow) -> None:
    cost = await pay_from_treasury(ctx, home, await named_ransom(ctx, captive), captive=captive)
    if cost <= 0:
        return
    shift_stat(captor, "wealth", cost)
    add_prosperity(ctx.rules, captor, cost)
    await change_relation(ctx, home.id, captor.id, ctx.rules.campaigns.ransom_relation, MemoryKind.FREED_US, note="ransom")
    await judged(ctx, captor.id, home.id, ActKind.RANSOM, note=captive.name)
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


async def execute(ctx: TickContext, row: CaptiveRow, captive: EntityRow, captor: EntityRow, home: EntityRow) -> None:
    await release_captive(ctx, row, CaptiveStatus.EXECUTED)
    await death_path(ctx, captive, f"executed by {captor.name}", captor.id, "execution", forced=True, harm=HarmCause.PUNISHMENT)
    await start_blood_feud(ctx, home.id, captor.id, f"the execution of {captive.name}")
    await witnessed(ctx, home.id, captor.id, ActKind.EXECUTION, base=ctx.rules.memory.outrage_magnitude, note=captive.name)
    for relative in await kin_of(ctx, captive):
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=relative.id,
            subject_id=captor.id,
            kind=MemoryKind.KILLED_KIN,
            magnitude=-ctx.rules.captivity.execution_memory,
            epoch=ctx.epoch,
            note=captive.name,
        )
    text = f"{captor.name} executed its prisoner {captive.name}; {home.name} swore vengeance."
    await _note(ctx, ChronicleKind.WAR, text, "prisoner.executed", (captor.id, captive.id, home.id))


async def kin_of(ctx: TickContext, mortal: EntityRow) -> list[EntityRow]:
    found: list[EntityRow] = []
    for other in await close_kin_of(ctx.session, mortal.id):
        relative = await living_entity(ctx.session, other)
        if relative is not None and relative.entity_type is EntityType.MORTAL:
            found.append(relative)
    return found


async def torture(ctx: TickContext, captive: EntityRow, captor: EntityRow, home: EntityRow) -> None:
    table = ctx.rules.captivity
    await apply_hits(ctx, captive, Harm(table.torture_hp, HarmCause.TORTURE, f"tortured by {captor.name}", killer_id=captor.id), lethal=False)
    await wring_intel(ctx, captor, home)
    await judged(ctx, captor.id, captive.id, ActKind.MUTILATION, note=captive.name)
    ctx.count("tortured")


async def foster(ctx: TickContext, row: CaptiveRow, captive: EntityRow, captor: EntityRow) -> bool:
    if (stat(captive, "age") or ctx.rules.skills.adult_age) >= ctx.rules.skills.adult_age:
        if row.status is CaptiveStatus.WARD:
            await ward_returns(ctx, row, captive, captor)
            await release_captive(ctx, row, CaptiveStatus.RELEASED)
            text = f"{captive.name}, raised at the court of {captor.name}, came of age and went home."
            await _note(ctx, ChronicleKind.WAR, text, "prisoner.ward_home", (captor.id, captive.id))
            return True
        return False
    if row.status is not CaptiveStatus.WARD:
        if not ctx.rng(f"ward.{row.id}").chance(ctx.rules.captivity.ward_chance):
            return False
        row.status = CaptiveStatus.WARD
    own = await stored_values(ctx.session, ValueHolder.PERSONAL, captive.id)
    theirs = await values_for(ctx.session, captor.id)
    step = ctx.rules.captivity.ward_drift
    drifted = {axis: own.get(axis, 0) + max(-step, min(step, theirs.get(axis, 0) - own.get(axis, 0))) for axis in ValueAxis}
    await write_values(ctx.session, ValueHolder.PERSONAL, captive.id, drifted)
    await grow_ward(ctx, row, captive, captor)
    ctx.count("wards")
    return True


async def _fate(ctx: TickContext, row: CaptiveRow, captive: EntityRow, captor: EntityRow) -> None:
    campaigns = ctx.rules.campaigns
    rng = ctx.rng("captivity")
    home = await home_of(ctx, captive, row)
    if await foster(ctx, row, captive, captor):
        return
    if await marry_captive(ctx, row, captive, captor) is not None:
        await _note(ctx, ChronicleKind.WAR, f"{captive.name} was married into the house of {captor.name}.", "prisoner.married", (captor.id, captive.id))
        return
    if await release_by_opinion(ctx, captor, home):
        await release_captive(ctx, row, CaptiveStatus.RELEASED)
        await _note(
            ctx,
            ChronicleKind.WAR,
            f"{captor.name} thought well of {captive.name}'s people and let the prisoner go.",
            "prisoner.released",
            (captor.id, captive.id),
        )
        return
    if home is not None and rich(ctx, home) and await ransom_lawful(ctx, captor) and rng.chance(campaigns.ransom_chance):
        await pay_ransom(ctx, row, captive, captor, home)
        return
    agility = await effective(ctx.session, captive, "agility", campaigns.captive_default_stat, rules=ctx.rules)
    intellect = await effective(ctx.session, captive, "intellect", campaigns.captive_default_stat, rules=ctx.rules)
    if rng.probability(agility / campaigns.escape_agility_divisor + intellect / campaigns.escape_intellect_divisor):
        await release_captive(ctx, row, CaptiveStatus.ESCAPED)
        await _note(ctx, ChronicleKind.ESCAPE, f"{captive.name} escaped from the dungeon of {captor.name}.", "prisoner.escaped", (captor.id, captive.id))
        return
    cruelty = await cruelty_drive(ctx.session, ctx.rules, captor.id)
    hated = home is not None and await relation(ctx.session, ctx.rules, home.id, captor.id) <= -campaigns.execution_relation
    if home is not None and hated and rng.chance(campaigns.execution_chance * cruelty) and not await forbidden(ctx, captor.id, ActKind.EXECUTION):
        await execute(ctx, row, captive, captor, home)
        return
    if home is not None and rng.chance(ctx.rules.captivity.torture_chance * cruelty):
        await torture(ctx, captive, captor, home)
    kinship = await closeness(ctx.session, captive.id, captor.id)
    if ctx.epoch - row.taken_epoch >= campaigns.captive_defection_epochs and rng.chance(campaigns.captive_defection_chance * kinship):
        await defect(ctx, row, captive, captor)


@reads(
    "people.population",
    "people.wealth",
    "table.bonds",
    "table.captive_cohorts",
    "table.captives",
    "table.culture_values",
    "table.epoch_year_cursors",
    "table.minds",
    "table.polity_members",
    "table.traits",
)
@writes(
    "people.population",
    "people.wealth",
    "table.captive_cohorts",
    "table.captives",
    "table.chronicle",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incidents",
)
@reads(
    "table.applied_fixups",
    "table.army_officers",
    "table.claims",
    "table.community_cohorts",
    "table.community_stocks",
    "table.currencies",
    "table.districts",
    "table.feuds",
    "table.goods",
    "table.house_members",
    "table.house_profiles",
    "table.injuries",
    "table.law_profiles",
    "table.learned_tactics",
    "table.loans",
    "table.memories",
    "table.mercenary_contracts",
    "table.offices",
    "table.peace_terms",
    "table.polity_members",
    "table.polity_profiles",
    "table.routes",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.spy_agents",
    "table.treaty_clauses",
    "table.treaty_profiles",
    "table.unit_designs",
    "table.vessel_profiles",
    "table.workshops",
)
@writes(
    "army.size",
    "people.population",
    "people.wealth",
    "settlement.population",
    "settlement.wealth",
    "table.applied_fixups",
    "table.army_officers",
    "table.battle_casualties",
    "table.battle_stacks",
    "table.bonds",
    "table.captive_cohorts",
    "table.captives",
    "table.claims",
    "table.community_cohorts",
    "table.community_stocks",
    "table.currencies",
    "table.districts",
    "table.entities",
    "table.feuds",
    "table.goods",
    "table.house_members",
    "table.house_profiles",
    "table.learned_tactics",
    "table.loans",
    "table.maimed_cohorts",
    "table.memories",
    "table.mercenary_contracts",
    "table.offices",
    "table.peace_terms",
    "table.polity_profiles",
    "table.region_environment",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.spy_agents",
    "table.spy_networks",
    "table.treaty_breaches",
    "table.vessel_profiles",
)
async def prisoners(ctx: TickContext) -> None:
    held = (CaptiveStatus.HELD, CaptiveStatus.WARD)
    rows = list(await ctx.session.scalars(select(CaptiveRow).where(CaptiveRow.status.in_(held)).order_by(CaptiveRow.id)))
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
    fates = await cohort_fates(ctx)
    for fate, count in fates.items():
        ctx.count(f"captive_cohorts_{fate.value}", count)
    await announce(ctx, fates)


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

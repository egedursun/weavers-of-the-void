from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.endowments import TOWN_EFFECTS
from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import NumberSystemRow
from aerona.db.tables.endowments import EndowmentRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folk_knowledge import FolkKnowledgeRow
from aerona.db.tables.military import CaptiveCohortRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.endowments import EndowmentCapital, EndowmentPurpose, EndowmentState, EndowmentTerms
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.customs import people_id_of
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import realm_of
from aerona.engine.economy.purse import give_coin, receive_coin
from aerona.engine.mortal.kin import children_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term

CAPITAL_YIELD_PCT: dict[EndowmentCapital, int] = {
    EndowmentCapital.LAND: 80,
    EndowmentCapital.COIN: 100,
    EndowmentCapital.SHARES: 130,
    EndowmentCapital.RENTS: 110,
}
CAPTORS = frozenset({EntityType.FACTION, EntityType.POLITY})
LIVE = frozenset({EndowmentState.SERVING, EndowmentState.CAPTURED})


@dataclass
class EndowmentTally:
    seeded: int = 0
    paid: int = 0
    skimmed: int = 0
    captured: int = 0
    confiscated: int = 0
    ended: int = 0
    outlived: int = 0


def parties(row: EndowmentRow, actor: int | None = None) -> dict[IncidentRole, int]:
    return {
        IncidentRole.ACTOR if actor is not None else IncidentRole.MAKER: actor if actor is not None else row.founder_node_id,
        IncidentRole.BENEFICIARY: row.beneficiary_node_id,
    }


def editable(row: EndowmentRow | SettlementProfileRow | MortalProfileRow | FolkKnowledgeRow | NumberSystemRow, field: str) -> bool:
    return field not in (row.locked or [])


async def ransom_kin(ctx: TickContext, town: EntityRow | None, amount: int) -> bool:
    if town is None:
        return False
    row = await ctx.session.scalar(
        select(CaptiveCohortRow).where(CaptiveCohortRow.origin_entity_id == town.id, CaptiveCohortRow.count > 0).order_by(CaptiveCohortRow.id).limit(1)
    )
    captor = await ctx.session.get(EntityRow, row.captor_entity_id) if row is not None else None
    if row is None or captor is None or held(captor.id, town.id) or "count" in (row.locked or []):
        return False
    freed = min(row.count, max(1, amount // max(1, ctx.rules.endowments.ransom_per_captive)))
    await receive_coin(ctx.session, ctx.rules, captor, amount)
    row.count -= freed
    shift_stat(town, "population", freed, low=0)
    await record(ctx, "endowment.ransomed", roles={IncidentRole.TARGET: captor.id, IncidentRole.RECEIVER: town.id}, facts={"freed": freed}, place=town.id)
    return True


async def town_of(session: AsyncSession, node_id: int) -> EntityRow | None:
    node = await session.get(EntityRow, node_id)
    if node is None:
        return None
    if node.entity_type is EntityType.SETTLEMENT:
        return node
    host = await session.get(EntityRow, node.location_id) if node.location_id is not None else None
    return host if host is not None and host.entity_type is EntityType.SETTLEMENT else None


async def endowed(session: AsyncSession, community_id: int) -> bool:
    for row in await session.scalars(select(EndowmentRow).where(EndowmentRow.state == EndowmentState.SERVING).order_by(EndowmentRow.id)):
        town = await town_of(session, row.beneficiary_node_id)
        if town is not None and town.id == community_id:
            return True
    return False


async def raise_renown(ctx: TickContext, node_id: int, amount: int, key: str) -> None:
    profile = await ctx.session.get(MortalProfileRow, node_id)
    if profile is None or held(node_id) or not editable(profile, "renown") or not amount:
        return
    with explaining():
        term(key, amount, source_node_id=node_id)
        profile.renown = clamp_int(profile.renown + amount, 0, PERCENT)


async def nudge_town(ctx: TickContext, town: EntityRow | None, field: str, amount: int, source: int) -> None:
    if town is None or held(town.id) or not amount:
        return
    if field in {"piety", "prosperity"}:
        with explaining():
            term("endowments.effect_per_income", amount, source_node_id=source)
            shift_stat(town, field, amount, low=0, high=PERCENT)
        return
    profile = await ctx.session.get(SettlementProfileRow, town.id)
    if profile is None or not editable(profile, field):
        return
    with explaining():
        term("endowments.effect_per_income", amount, source_node_id=source)
        setattr(profile, field, clamp_int(getattr(profile, field) + amount, 0, PERCENT))


async def teach_people(ctx: TickContext, town: EntityRow | None, points: int, source: int, *, research: bool) -> None:
    people = await people_id_of(ctx.session, town)
    if people is None or held(people) or not points:
        return
    if not research:
        system = await ctx.session.get(NumberSystemRow, people)
        if system is not None and editable(system, "numeracy"):
            with explaining():
                term("endowments.effect_per_income", points, source_node_id=source)
                system.numeracy = clamp_int(system.numeracy + points, 0, PERCENT)
        return
    weakest = await ctx.session.scalar(
        select(FolkKnowledgeRow).where(FolkKnowledgeRow.people_entity_id == people).order_by(FolkKnowledgeRow.accuracy, FolkKnowledgeRow.id).limit(1)
    )
    if weakest is not None and editable(weakest, "accuracy"):
        with explaining():
            term("endowments.effect_per_income", points, source_node_id=source)
            weakest.accuracy = clamp_int(weakest.accuracy + points, 0, PERCENT)


async def serve(ctx: TickContext, row: EndowmentRow, amount: int) -> None:
    points = amount // ctx.rules.endowments.effect_per_income
    town = await town_of(ctx.session, row.beneficiary_node_id)
    source = row.founder_node_id
    if row.purpose in TOWN_EFFECTS:
        field, sign = TOWN_EFFECTS[row.purpose]
        await nudge_town(ctx, town, field, sign * points, source)
    match row.purpose:
        case EndowmentPurpose.ART:
            if await ctx.session.get(MortalProfileRow, row.beneficiary_node_id) is not None:
                await raise_renown(ctx, row.beneficiary_node_id, points, "endowments.effect_per_income")
            else:
                await nudge_town(ctx, town, "prosperity", points, source)
        case EndowmentPurpose.LEARNING:
            await teach_people(ctx, town, points, source, research=False)
        case EndowmentPurpose.RESEARCH:
            await teach_people(ctx, town, points, source, research=True)
        case EndowmentPurpose.KIN:
            heirs = [heir for heir_id in await children_of(ctx.session, row.founder_node_id) if (heir := await ctx.session.get(EntityRow, heir_id)) is not None]
            living = [heir for heir in heirs if heir.status is EntityStatus.CANON and not held(heir.id)]
            for heir in living:
                await give_coin(ctx.session, ctx.rules, heir, amount // len(living))
        case EndowmentPurpose.MEMORY:
            await raise_renown(ctx, row.founder_node_id, points, "endowments.effect_per_income")
        case EndowmentPurpose.RANSOM:
            if await ransom_kin(ctx, town, amount):
                await raise_renown(ctx, row.founder_node_id, points, "endowments.effect_per_income")
    beneficiary = await ctx.session.get(EntityRow, row.beneficiary_node_id)
    if beneficiary is not None and row.purpose is not EndowmentPurpose.KIN and not held(beneficiary.id):
        await give_coin(ctx.session, ctx.rules, beneficiary, amount)


async def end_by_terms(ctx: TickContext, row: EndowmentRow, tally: EndowmentTally) -> bool:
    beneficiary = await ctx.session.get(EntityRow, row.beneficiary_node_id)
    over = (row.terms is EndowmentTerms.FOR_A_TERM and row.ends_epoch is not None and ctx.epoch >= row.ends_epoch) or (
        row.terms is EndowmentTerms.CONDITIONAL and beneficiary is not None and beneficiary.status is not EntityStatus.CANON
    )
    if not over or not editable(row, "state"):
        return False
    row.state = EndowmentState.ENDED
    await record(ctx, "endowment.ended", roles=parties(row), facts={"terms": row.terms})
    tally.ended += 1
    return True


async def confiscate(ctx: TickContext, row: EndowmentRow, tally: EndowmentTally) -> bool:
    if row.sheltered or not editable(row, "state"):
        return False
    town = await town_of(ctx.session, row.beneficiary_node_id)
    realm_id = await realm_of(ctx.session, town.id) if town is not None else None
    realm = await ctx.session.get(PolityProfileRow, realm_id) if realm_id is not None else None
    if realm is None or realm_id is None or held(realm_id) or realm.treasury >= 0 or "treasury" in (realm.locked or []):
        return False
    if not ctx.rng(f"endowment_confiscated.{row.id}.{ctx.epoch}").chance(ctx.rules.endowments.confiscation_risk_pct):
        return False
    realm.treasury += row.capital
    row.state = EndowmentState.CONFISCATED
    await record(
        ctx,
        "endowment.confiscated",
        roles=parties(row, realm_id),
        facts={"capital": row.capital, "purpose": row.purpose},
    )
    tally.confiscated += 1
    return True


async def capture(ctx: TickContext, row: EndowmentRow, tally: EndowmentTally) -> None:
    trustee = await ctx.session.get(EntityRow, row.trustee_node_id) if row.trustee_node_id is not None else None
    if trustee is None or trustee.entity_type not in CAPTORS or row.state is not EndowmentState.SERVING or not editable(row, "state"):
        return
    row.state = EndowmentState.CAPTURED
    await record(ctx, "endowment.captured", roles=parties(row, trustee.id), facts={"purpose": row.purpose})
    tally.captured += 1


async def pay(ctx: TickContext, row: EndowmentRow, tally: EndowmentTally) -> None:
    table = ctx.rules.endowments
    income = round_half_up(row.capital * table.income_pct / PERCENT * CAPITAL_YIELD_PCT[row.capital_kind] / PERCENT)
    if editable(row, "income"):
        row.income = income
    if not income:
        return
    trustee = await ctx.session.get(EntityRow, row.trustee_node_id) if row.trustee_node_id is not None else None
    if row.state is EndowmentState.CAPTURED and trustee is not None:
        await give_coin(ctx.session, ctx.rules, trustee, income)
        return
    kept = 0
    if trustee is not None and trustee.id != row.founder_node_id and ctx.rng(f"endowment_skim.{row.id}.{ctx.epoch}").chance(table.skim_chance_pct):
        kept = round_half_up(income * table.skim_share_pct / PERCENT)
        await give_coin(ctx.session, ctx.rules, trustee, kept)
        if editable(row, "skimmed"):
            row.skimmed += kept
        await record(ctx, "endowment.skimmed", roles=parties(row, trustee.id), facts={"amount": kept})
        tally.skimmed += 1
    await serve(ctx, row, income - kept)
    await raise_renown(ctx, row.founder_node_id, table.renown_per_epoch, "endowments.renown_per_epoch")
    if income - kept > 0:
        await record(
            ctx,
            "endowment.paid",
            roles=parties(row),
            facts={"amount": income - kept, "purpose": row.purpose},
        )
    tally.paid += 1


async def outlive(ctx: TickContext, row: EndowmentRow, tally: EndowmentTally) -> None:
    founder = await ctx.session.get(EntityRow, row.founder_node_id)
    if row.outlived or founder is None or founder.status is EntityStatus.CANON or not editable(row, "outlived"):
        return
    row.outlived = True
    await record(
        ctx,
        "endowment.outlived_founder",
        roles=parties(row),
        facts={"purpose": row.purpose},
    )
    tally.outlived += 1


async def keep_endowments(ctx: TickContext, tally: EndowmentTally) -> None:
    for row in list(await ctx.session.scalars(select(EndowmentRow).where(EndowmentRow.state.in_(sorted(LIVE))).order_by(EndowmentRow.id))):
        if held(row.founder_node_id) or held(row.beneficiary_node_id):
            continue
        if await end_by_terms(ctx, row, tally) or await confiscate(ctx, row, tally):
            continue
        await capture(ctx, row, tally)
        await pay(ctx, row, tally)
        await outlive(ctx, row, tally)
    await ctx.session.flush()

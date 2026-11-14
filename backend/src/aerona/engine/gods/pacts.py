from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog import god_lines
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import TreatyClauseRow, TreatyProfileRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.polity import ClauseKind, PartyRole, TreatyKind, TreatyStatus
from aerona.engine.context import TickContext
from aerona.engine.gods.stats import Trait, add_trait
from aerona.engine.polity.accords import Clause, end_treaty, sign
from aerona.engine.polity.treaties import breach
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity

Payer = Callable[[TickContext, EntityRow, CommodityKind | None, int, int], Awaitable[bool]]
Shifter = Callable[[AsyncSession, EntityRow, int], Awaitable[None]]


@dataclass(frozen=True)
class Terms:
    demand: str
    commodity: CommodityKind | None
    units: int
    cost: int
    every: int

    def params(self, paid_epoch: int) -> dict[str, int | str | bool]:
        return {
            "demand": self.demand,
            "commodity": self.commodity.value if self.commodity is not None else "",
            "units": self.units,
            "cost": self.cost,
            "every": self.every,
            "paid_epoch": paid_epoch,
        }


def terms_of(clause: TreatyClauseRow, every: int) -> Terms:
    params = clause.params or {}
    wanted = str(params.get("commodity") or "")
    return Terms(
        demand=str(params.get("demand") or "its due"),
        commodity=CommodityKind(wanted) if wanted in CommodityKind._value2member_map_ else None,
        units=max(0, int(params.get("units", 0))),
        cost=max(0, int(params.get("cost", 0))),
        every=max(1, int(params.get("every", every))),
    )


async def pact_for(session: AsyncSession, resource_id: int) -> tuple[TreatyProfileRow, TreatyClauseRow] | None:
    statement = (
        select(TreatyProfileRow, TreatyClauseRow)
        .join(TreatyClauseRow, TreatyClauseRow.treaty_entity_id == TreatyProfileRow.treaty_entity_id)
        .where(
            TreatyProfileRow.status == TreatyStatus.IN_FORCE,
            TreatyClauseRow.kind == ClauseKind.RESOURCE_DEMAND,
            TreatyClauseRow.beneficiary_node_id == resource_id,
        )
        .order_by(TreatyProfileRow.treaty_entity_id.desc())
    )
    found = (await session.execute(statement)).first()
    return (found[0], found[1]) if found is not None else None


def bargained(ctx: TickContext, terms: Terms, skill: int) -> Terms:
    discount = clamp_int(skill * ctx.rules.sentient_pacts.discount_pct_per_level, 0, PERCENT)
    keep = (PERCENT - discount) / PERCENT
    return Terms(terms.demand, terms.commodity, round_half_up(terms.units * keep), round_half_up(terms.cost * keep), ctx.rules.sentient_pacts.every_epochs)


async def strike_pact(ctx: TickContext, resource: EntityRow, owner: EntityRow, terms: Terms, *, negotiator: EntityRow | None) -> EntityRow:
    treaty = await sign(
        ctx,
        TreatyKind.TRIBUTE,
        [(owner.id, PartyRole.SIGNATORY), (resource.id, PartyRole.SIGNATORY)],
        clauses=[Clause(ClauseKind.RESOURCE_DEMAND, owner.id, resource.id, terms.params(ctx.epoch - terms.every))],
        until=ctx.epoch + ctx.rules.sentient_pacts.pact_epochs,
    )
    line = god_lines.ECONOMY_SENTIENT_PACT
    await ctx.chronicle(
        ChronicleKind.RESOURCE,
        line.render(resource=resource.name, owner=owner.name, demand=terms.demand, negotiator=negotiator.name if negotiator is not None else owner.name),
        template_key=line.key,
        entity_ids=[resource.id, owner.id, treaty.id, *([negotiator.id] if negotiator is not None else [])],
    )
    return treaty


async def keep_pact(
    ctx: TickContext, resource: EntityRow, pact: tuple[TreatyProfileRow, TreatyClauseRow], owners: list[EntityRow], *, pay: Payer, shift: Shifter
) -> str:
    table = ctx.rules.sentient_pacts
    profile, clause = pact
    terms = terms_of(clause, table.every_epochs)
    paid = int((clause.params or {}).get("paid_epoch", profile.signed_epoch))
    if ctx.epoch - paid < terms.every:
        return "waiting"
    owner = await living_entity(ctx.session, clause.obligor_node_id) if clause.obligor_node_id is not None else None
    if owner is None or all(item.id != owner.id for item in owners):
        await end_treaty(ctx, profile, TreatyStatus.FULFILLED, "the resource passed from its keeper")
        return "ended"
    if await pay(ctx, owner, terms.commodity, terms.units, terms.cost):
        clause.params = {**(clause.params or {}), "paid_epoch": ctx.epoch}
        clause.last_kept_epoch = ctx.epoch
        await shift(ctx.session, resource, table.honour_reserve_pct)
        add_trait(owner, Trait.PROSPERITY, table.honour_prosperity)
        line = god_lines.ECONOMY_SENTIENT_PACT_KEPT
        await ctx.chronicle(
            ChronicleKind.RESOURCE,
            line.render(resource=resource.name, owner=owner.name, demand=terms.demand),
            template_key=line.key,
            entity_ids=[resource.id, owner.id, profile.treaty_entity_id],
        )
        return "kept"
    await breach(ctx, profile, owner.id, clause=clause, reason=f"it did not give {resource.name} {terms.demand}")
    add_trait(owner, Trait.PROSPERITY, -table.wrath_prosperity)
    add_trait(owner, Trait.WEALTH, -table.wrath_prosperity)
    await shift(ctx.session, resource, -table.wrath_reserve_pct)
    line = god_lines.ECONOMY_SENTIENT_PACT_BROKEN
    await ctx.chronicle(
        ChronicleKind.CURSE,
        line.render(resource=resource.name, owner=owner.name, demand=terms.demand),
        template_key=line.key,
        entity_ids=[resource.id, owner.id, profile.treaty_entity_id],
    )
    return "broken"


TERM_KEYS = frozenset({"demand", "commodity", "units", "cost", "every"})


def checked_terms(values: Mapping[str, int | str | None], base: Terms) -> Terms:
    unknown = set(values) - TERM_KEYS
    if unknown:
        raise ValidationFailedError(f"Unknown pact terms: {', '.join(sorted(unknown))}.")
    wanted = values.get("commodity", base.commodity.value if base.commodity is not None else "")
    if wanted and str(wanted) not in CommodityKind._value2member_map_:
        raise ValidationFailedError(f"{wanted} is not a good.")
    numbers: dict[str, int] = {}
    for key, floor in (("units", 0), ("cost", 0), ("every", 1)):
        value = values.get(key, getattr(base, key))
        if not isinstance(value, int) or isinstance(value, bool) or value < floor or (key == "cost" and value > PERCENT):
            raise ValidationFailedError(f"{key.capitalize()} must be a whole number of at least {floor}{' and at most 100' if key == 'cost' else ''}.")
        numbers[key] = value
    demand = str(values.get("demand") or base.demand).strip() or base.demand
    return Terms(demand, CommodityKind(str(wanted)) if wanted else None, numbers["units"], numbers["cost"], numbers["every"])


async def pact_by_hand(ctx: TickContext, resource_id: int, owner_id: int, values: Mapping[str, int | str | None], *, epochs: int | None) -> EntityRow:
    resource = await living_entity(ctx.session, resource_id)
    owner = await living_entity(ctx.session, owner_id)
    if resource is None or resource.entity_type is not EntityType.RESOURCE:
        raise NotFoundError("No such living resource.")
    if owner is None or owner.entity_type not in COMMUNITY_TYPES:
        raise ValidationFailedError("A pact binds a people, settlement, faction or cult to the resource.")
    if await pact_for(ctx.session, resource.id) is not None:
        raise ValidationFailedError(f"{resource.name} is already bound by a pact; change its terms instead.")
    table = ctx.rules.sentient_pacts
    terms = checked_terms(values, Terms("an offering on each term", None, 0, ctx.rules.economy.sentient_demand_cost, table.every_epochs))
    treaty = await strike_pact(ctx, resource, owner, terms, negotiator=None)
    profile = await ctx.session.get(TreatyProfileRow, treaty.id)
    if profile is not None and epochs is not None:
        profile.until_epoch = ctx.epoch + max(1, epochs)
    return treaty


async def pact_terms(ctx: TickContext, treaty_id: int, values: Mapping[str, int | str | None]) -> TreatyClauseRow:
    clause = await ctx.session.scalar(
        select(TreatyClauseRow).where(TreatyClauseRow.treaty_entity_id == treaty_id, TreatyClauseRow.kind == ClauseKind.RESOURCE_DEMAND).limit(1)
    )
    if clause is None:
        raise NotFoundError("No pact with a resource under that treaty.")
    terms = checked_terms(values, terms_of(clause, ctx.rules.sentient_pacts.every_epochs))
    paid = int((clause.params or {}).get("paid_epoch", ctx.epoch))
    clause.params = terms.params(paid)
    await ctx.session.flush()
    return clause


async def end_pact(ctx: TickContext, treaty_id: int) -> TreatyProfileRow:
    profile = await ctx.session.get(TreatyProfileRow, treaty_id)
    if profile is None or profile.status is not TreatyStatus.IN_FORCE:
        raise NotFoundError("No pact in force.")
    await end_treaty(ctx, profile, TreatyStatus.FULFILLED, "released by the Creator")
    await ctx.session.flush()
    return profile

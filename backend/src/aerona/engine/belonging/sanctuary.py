from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.fugitives import FUGITIVES, SANCTUARIES
from aerona.catalog.terrain import terrains
from aerona.constants.units import PERCENT
from aerona.db.tables.belonging import SanctuaryLawRow, SanctuaryRow
from aerona.db.tables.collective import SocialNormRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.faith import CultDoctrineRow, CultHoldingRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.law_depth import DefectionRow, OutlawRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.belonging import FugitiveKind, SanctuaryKind, SanctuaryState
from aerona.domain.enums.collective import NormSituation
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import TerrainTrait
from aerona.domain.enums.intrigue import FavourOrigin
from aerona.domain.enums.justice import CaseStage
from aerona.domain.enums.mind import EthicalStance, MemoryKind, ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.structure import StructureKind
from aerona.engine.belonging.fugitives_w52 import open_fugitives
from aerona.engine.belonging.refuge import OPEN_STATES, refuge_of
from aerona.engine.body.afflictions import desecration_curse
from aerona.engine.body.customs import people_of
from aerona.engine.collective.book import ruler_id
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import realm_of
from aerona.engine.economy.purse import give_coin, receive_coin, take_coin
from aerona.engine.intrigue.favours import owe
from aerona.engine.law.prisons import imprison
from aerona.engine.mind.book import stored_values
from aerona.engine.mind.hooks import desecrated
from aerona.engine.mortal.standing import add_infamy
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import change_relation

HOLY = (StructureKind.TEMPLE, StructureKind.SHRINE, StructureKind.MONASTERY)
HIDING = terrains(TerrainTrait.WOODED) | terrains(TerrainTrait.HIGH) | terrains(TerrainTrait.WET) | terrains(TerrainTrait.RUINED)
WELCOMING = frozenset({EthicalStance.REQUIRED, EthicalStance.ADMIRABLE})


@dataclass
class SanctuaryTally:
    sought: int = 0
    asylums: int = 0
    paid: int = 0
    bargained: int = 0
    besieged: int = 0
    violated: int = 0
    surrendered: int = 0
    laws: int = 0


@dataclass(frozen=True)
class Fugitive:
    mortal: EntityRow
    kind: FugitiveKind
    pursuer: int | None


async def restricted(ctx: TickContext, polity: int | None) -> bool:
    law = await ctx.session.get(SanctuaryLawRow, polity) if polity is not None else None
    return law is not None and law.restricted


async def structure_in(ctx: TickContext, town: int, kind: StructureKind) -> EntityRow | None:
    found = await ctx.session.scalar(
        select(EntityRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(EntityRow.location_id == town, EntityRow.status == EntityStatus.CANON, StructureProfileRow.kind == kind)
        .order_by(EntityRow.id)
        .limit(1)
    )
    return found


async def ship_in(ctx: TickContext, town: int) -> EntityRow | None:
    vessel = await ctx.session.scalar(
        select(VesselProfileRow.entity_id).where(VesselProfileRow.home_port_entity_id == town).order_by(VesselProfileRow.entity_id).limit(1)
    )
    return await living_entity(ctx.session, vessel) if vessel is not None else None


async def temple_in(ctx: TickContext, town: int) -> EntityRow | None:
    found = await ctx.session.scalar(
        select(EntityRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(EntityRow.location_id == town, EntityRow.status == EntityStatus.CANON, StructureProfileRow.kind.in_(list(HOLY)))
        .order_by(EntityRow.id)
        .limit(1)
    )
    return found


async def welcoming(ctx: TickContext, town: EntityRow) -> bool:
    folk = await people_of(ctx.session, town)
    holders = [town.id, *([folk.id] if folk is not None else [])]
    stances = await ctx.session.scalars(
        select(SocialNormRow.stance).where(SocialNormRow.holder_entity_id.in_(holders), SocialNormRow.situation == NormSituation.HOSPITALITY)
    )
    return any(stance in WELCOMING for stance in stances)


async def embassy_in(ctx: TickContext, town: int) -> EntityRow | None:
    found = await ctx.session.scalar(
        select(EntityRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(EntityRow.location_id == town, EntityRow.status == EntityStatus.CANON, StructureProfileRow.kind == StructureKind.EMBASSY)
        .order_by(EntityRow.id)
        .limit(1)
    )
    return found


async def frees_runaways(ctx: TickContext, town: int) -> bool:
    profile = await ctx.session.get(SettlementProfileRow, town)
    return profile is not None and profile.free_city and profile.charter_entity_id is not None


async def wilds_near(ctx: TickContext, town: EntityRow) -> EntityRow | None:
    ground = await ctx.session.get(RegionEnvironmentRow, town.location_id) if town.location_id is not None else None
    if ground is None or ground.dominant_terrain not in HIDING or held(ground.entity_id):
        return None
    return await ctx.session.get(EntityRow, ground.entity_id)


async def host_for(ctx: TickContext, fugitive: Fugitive, wanted: SanctuaryKind | None = None) -> tuple[EntityRow, SanctuaryKind] | None:
    town = await ctx.session.get(EntityRow, fugitive.mortal.location_id) if fugitive.mortal.location_id is not None else None
    if town is None or town.entity_type is not EntityType.SETTLEMENT:
        return None
    found: list[tuple[EntityRow, SanctuaryKind]] = []
    temple = await temple_in(ctx, town.id)
    if temple is not None and not await restricted(ctx, await realm_of(ctx.session, town.id)) and not held(temple.id):
        found.append((temple, SanctuaryKind.TEMPLE))
    embassy = await embassy_in(ctx, town.id)
    if embassy is not None and FUGITIVES[fugitive.kind].embassy and not held(embassy.id):
        found.append((embassy, SanctuaryKind.EMBASSY))
    if FUGITIVES[fugitive.kind].city_frees and await frees_runaways(ctx, town.id) and not held(town.id):
        found.append((town, SanctuaryKind.FREE_CITY))
    if await welcoming(ctx, town) and not held(town.id):
        found.append((town, SanctuaryKind.HOSPITALITY))
    hall = await structure_in(ctx, town.id, StructureKind.GUILDHALL)
    if hall is not None and not held(hall.id):
        found.append((hall, SanctuaryKind.TRADE_HALL))
    ship = await ship_in(ctx, town.id)
    if ship is not None and not held(ship.id):
        found.append((ship, SanctuaryKind.SHIP))
    wilds = await wilds_near(ctx, town)
    if wilds is not None:
        found.append((wilds, SanctuaryKind.WILDS))
    chosen = [item for item in found if wanted is None or item[1] is wanted]
    return chosen[0] if chosen else None


async def fugitives(ctx: TickContext) -> list[Fugitive]:
    found: dict[int, Fugitive] = {}
    for row in await ctx.session.scalars(select(OutlawRow).order_by(OutlawRow.mortal_entity_id)):
        mortal = await living_entity(ctx.session, row.mortal_entity_id)
        if mortal is not None:
            found.setdefault(mortal.id, Fugitive(mortal, FugitiveKind.OUTLAW, row.polity_entity_id))
    for case in await ctx.session.scalars(
        select(CrimeCaseRow).where(CrimeCaseRow.stage != CaseStage.CLOSED, CrimeCaseRow.accused_entity_id.is_not(None)).order_by(CrimeCaseRow.id)
    ):
        mortal = await living_entity(ctx.session, case.accused_entity_id)
        if mortal is not None:
            found.setdefault(mortal.id, Fugitive(mortal, FugitiveKind.ACCUSED, case.polity_entity_id))
    for fled in await open_fugitives(ctx):
        mortal = await living_entity(ctx.session, fled.mortal_entity_id)
        if mortal is not None:
            found.setdefault(mortal.id, Fugitive(mortal, fled.kind, fled.pursuer_entity_id))
    return [item for _, item in sorted(found.items())]


async def shelter(ctx: TickContext, fugitive: Fugitive, host: EntityRow, kind: SanctuaryKind) -> SanctuaryRow:
    row = SanctuaryRow(
        fugitive_entity_id=fugitive.mortal.id,
        host_entity_id=host.id,
        kind=kind,
        fugitive_kind=fugitive.kind,
        pursuer_entity_id=fugitive.pursuer,
        fee=ctx.rules.sanctuary.fee,
        granted_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await owe(ctx, fugitive.mortal.id, host.id, FavourOrigin.HOSPITALITY, ctx.rules.favours.hospitality_favour)
    return row


async def seek(ctx: TickContext, tally: SanctuaryTally) -> None:
    for fugitive in await fugitives(ctx):
        if held(fugitive.mortal.id) or await refuge_of(ctx.session, fugitive.mortal.id) is not None:
            continue
        if not ctx.rng(seed_of("sanctuary.seek", fugitive.mortal.id, ctx.epoch)).chance(ctx.rules.sanctuary.seek_chance):
            continue
        found = await host_for(ctx, fugitive)
        if found is None:
            continue
        await shelter(ctx, fugitive, *found)
        tally.sought += 1
        await record(
            ctx,
            "sanctuary.claimed",
            roles={IncidentRole.ACTOR: fugitive.mortal.id, IncidentRole.HOST: found[0].id, IncidentRole.OPPONENT: fugitive.pursuer},
            facts={"refuge": found[1], "fugitive": fugitive.kind, "chance": ctx.rules.sanctuary.seek_chance},
            place=found[0].id,
        )


async def asylums(ctx: TickContext, tally: SanctuaryTally) -> None:
    for row in await ctx.session.scalars(select(DefectionRow).where(DefectionRow.to_entity_id.is_not(None)).order_by(DefectionRow.id)):
        defector = await living_entity(ctx.session, row.defector_entity_id)
        host = await living_entity(ctx.session, row.to_entity_id)
        if defector is None or host is None or held(defector.id, host.id) or await refuge_of(ctx.session, defector.id) is not None:
            continue
        known = await ctx.session.scalar(select(SanctuaryRow.id).where(SanctuaryRow.fugitive_entity_id == defector.id, SanctuaryRow.host_entity_id == host.id))
        if known is not None:
            continue
        await shelter(ctx, Fugitive(defector, FugitiveKind.DEFECTOR, row.from_entity_id), host, SanctuaryKind.ASYLUM)
        if row.from_entity_id is not None and not held(row.from_entity_id):
            await change_relation(
                ctx, row.from_entity_id, host.id, -ctx.rules.sanctuary.asylum_relation, MemoryKind.ILL_WILL, note=f"gave asylum to {defector.name}"
            )
        tally.asylums += 1


async def hand_over(ctx: TickContext, row: SanctuaryRow, state: SanctuaryState) -> None:
    row.state = state
    fugitive = await living_entity(ctx.session, row.fugitive_entity_id)
    if fugitive is not None:
        await imprison(ctx, fugitive)


async def violate(ctx: TickContext, row: SanctuaryRow, host: EntityRow, pursuer: EntityRow, tally: SanctuaryTally) -> None:
    await hand_over(ctx, row, SanctuaryState.VIOLATED)
    ruler = await ruler_id(ctx, pursuer.id) if pursuer.entity_type is EntityType.POLITY else pursuer.id
    if ruler is not None and not held(ruler):
        await add_infamy(ctx.session, ruler, ctx.rules.sanctuary.infamy, ctx.epoch, rules=ctx.rules)
        if row.kind is SanctuaryKind.TEMPLE:
            await desecration_curse(ctx, host, ruler)
    await desecrated(ctx, host.id, pursuer.id, note="broke the sanctuary")
    if row.kind is SanctuaryKind.EMBASSY and host.affiliated_entity_id is not None and not held(host.affiliated_entity_id):
        await change_relation(
            ctx, pursuer.id, host.affiliated_entity_id, -ctx.rules.sanctuary.embassy_crisis, MemoryKind.ILL_WILL, note="broke into its embassy"
        )
    tally.violated += 1
    await record(
        ctx,
        "sanctuary.violated",
        roles={IncidentRole.ACTOR: pursuer.id, IncidentRole.HOST: host.id, IncidentRole.VICTIM: row.fugitive_entity_id, IncidentRole.LEADER: ruler},
        facts={"refuge": row.kind, "infamy": ctx.rules.sanctuary.infamy},
        place=host.id,
    )


async def pay_host(ctx: TickContext, host: EntityRow, amount: int) -> None:
    keeper = await ctx.session.scalar(select(CultHoldingRow.cult_entity_id).where(CultHoldingRow.holding_entity_id == host.id).limit(1))
    doctrine = await ctx.session.get(CultDoctrineRow, keeper) if keeper is not None else None
    if doctrine is None or "treasury" in doctrine.locked:
        await give_coin(ctx.session, ctx.rules, host, amount)
        return
    doctrine.treasury += amount
    cult = await ctx.session.get(EntityRow, keeper)
    if cult is not None and not held(cult.id):
        shift_stat(cult, "influence", ctx.rules.sanctuary.cult_influence, default=0)


async def split_fee(ctx: TickContext, row: SanctuaryRow, host: EntityRow) -> None:
    realm = await realm_of(ctx.session, host.location_id or host.id)
    law = await ctx.session.get(SanctuaryLawRow, realm) if realm is not None else None
    levy = round_half_up(row.fee * law.fee_pct / PERCENT) if law is not None else 0
    polity = await ctx.session.get(EntityRow, realm) if levy and realm is not None else None
    if polity is not None:
        await receive_coin(ctx.session, ctx.rules, polity, levy)
    await pay_host(ctx, host, row.fee - (levy if polity is not None else 0))


async def pursue(ctx: TickContext, row: SanctuaryRow, tally: SanctuaryTally) -> None:
    table = ctx.rules.sanctuary
    host = await living_entity(ctx.session, row.host_entity_id)
    fugitive = await living_entity(ctx.session, row.fugitive_entity_id)
    if host is None or fugitive is None:
        row.state = SanctuaryState.ENDED
        return
    if row.fee and await take_coin(ctx.session, ctx.rules, fugitive, row.fee):
        await split_fee(ctx, row, host)
        tally.paid += 1
    pursuer = await living_entity(ctx.session, row.pursuer_entity_id) if row.pursuer_entity_id is not None else None
    if pursuer is None or held(pursuer.id) or "state" in row.locked:
        return
    if row.state is SanctuaryState.NEGOTIATING:
        if await take_coin(ctx.session, ctx.rules, pursuer, table.ransom):
            await pay_host(ctx, host, table.ransom)
            await hand_over(ctx, row, SanctuaryState.ENDED)
            tally.bargained += 1
        return
    if row.state is SanctuaryState.BESIEGED:
        row.siege_epochs += 1
        if row.siege_epochs >= table.surrender_epochs:
            await hand_over(ctx, row, SanctuaryState.ENDED)
            tally.surrendered += 1
        return
    roll = ctx.rng(seed_of("sanctuary.pursue", row.id, ctx.epoch))
    hidden = SANCTUARIES[row.kind].hides and roll.chance(table.wilds_hide_pct)
    if hidden:
        return
    if roll.chance(table.violate_chance):
        await violate(ctx, row, host, pursuer, tally)
    elif roll.chance(table.negotiate_chance):
        row.state = SanctuaryState.NEGOTIATING
    elif roll.chance(table.besiege_chance):
        row.state = SanctuaryState.BESIEGED
        tally.besieged += 1


async def legislate(ctx: TickContext, row: SanctuaryRow, tally: SanctuaryTally) -> None:
    table = ctx.rules.sanctuary
    host = await ctx.session.get(EntityRow, row.host_entity_id)
    realm = await realm_of(ctx.session, host.location_id or host.id) if host is not None else None
    if realm is None or realm != row.pursuer_entity_id or held(realm) or await ctx.session.get(SanctuaryLawRow, realm) is not None:
        return
    if not ctx.rng(seed_of("sanctuary.law", realm, ctx.epoch)).chance(table.law_chance):
        return
    ruler = await ruler_id(ctx, realm)
    values = await stored_values(ctx.session, ValueHolder.PERSONAL, ruler) if ruler is not None else {}
    strict = values.get(ValueAxis.LAW, 0) >= table.restrict_from
    ctx.session.add(SanctuaryLawRow(polity_entity_id=realm, restricted=strict, fee_pct=0 if strict else table.levy_pct, locked=[]))
    await ctx.session.flush()
    tally.laws += 1
    await record(
        ctx,
        "sanctuary.law_barred" if strict else "sanctuary.law_levied",
        roles={IncidentRole.AUTHORITY: realm, IncidentRole.LEADER: ruler},
        facts={"law_value": values.get(ValueAxis.LAW, 0), "levy": 0 if strict else table.levy_pct},
    )


async def keep_sanctuaries(ctx: TickContext, tally: SanctuaryTally) -> None:
    await seek(ctx, tally)
    await asylums(ctx, tally)
    for row in list(await ctx.session.scalars(select(SanctuaryRow).where(SanctuaryRow.state.in_(OPEN_STATES)).order_by(SanctuaryRow.id))):
        await legislate(ctx, row, tally)
    for row in list(await ctx.session.scalars(select(SanctuaryRow).where(SanctuaryRow.state.in_(OPEN_STATES)).order_by(SanctuaryRow.id))):
        if held(row.fugitive_entity_id, row.host_entity_id):
            continue
        await pursue(ctx, row, tally)
    await ctx.session.flush()

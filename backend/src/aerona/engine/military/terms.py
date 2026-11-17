from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import OccupationRow
from aerona.db.tables.warfare import ArmyRow, WarRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.military import PeaceTermKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.renown import Currency, ReputationAxis
from aerona.domain.enums.war import WarStatus
from aerona.engine.body.variants import fear_of
from aerona.engine.context import TickContext
from aerona.engine.military.peace import record
from aerona.engine.military.support import realm_of
from aerona.engine.mind.book import values_for
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.regard import shift_regard
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import FactInput
from aerona.engine.recording.record import record as record_incident
from aerona.engine.renown.book import acclaim
from aerona.engine.renown.currencies import bump, purse_of, ruler_of_realm
from aerona.engine.services.war import OngoingWar
from aerona.engine.services.war_resolution import make_peace


async def separate_peace(ctx: TickContext, item: OngoingWar, ally: WarSideRow) -> bool:
    if ally.weariness < ctx.rules.war_conduct.separate_peace_at or held(ally.entity_id) or "left_epoch" in ally.locked:
        return False
    enemy_id = item.foe_of_camp(ally.side)
    ally.left_epoch = ctx.epoch
    await make_peace(ctx, ally.entity_id, enemy_id, "a separate peace")
    leaver, enemy = await living_entity(ctx.session, ally.entity_id), await living_entity(ctx.session, enemy_id)
    leaver_name = leaver.name if leaver is not None else "an ally"
    enemy_name = enemy.name if enemy is not None else "the enemy"
    text = f"{leaver_name} made a separate peace with {enemy_name} and left the war"
    record(ctx, item.war, PeaceTermKind.WHITE_PEACE, victor_id=None, loser_id=None, params={"separate": True, "side_id": ally.entity_id}, note=text)
    await record_incident(
        ctx, "war.separate_peace", roles={IncidentRole.ACTOR: ally.entity_id, IncidentRole.OPPONENT: enemy_id}, facts={"war": item.war.event_entity_id}
    )
    ctx.count("separate_peaces")
    return True


async def fights_on(ctx: TickContext, war: WarRow, loser: EntityRow) -> bool:
    table = ctx.rules.war_conduct
    side = await ctx.session.get(WarSideRow, (war.id, loser.id))
    if side is None or held(loser.id) or side.support < table.fight_on_support or side.weariness >= table.fight_on_weariness:
        return False
    if "weariness" not in side.locked:
        side.weariness = clamp_int(side.weariness + table.refusal_weariness, 0, PERCENT)
    await record_incident(ctx, "war.fought_on", roles={IncidentRole.ACTOR: loser.id}, facts={"war": war.event_entity_id, "weariness": side.weariness})
    ctx.count("peace_refused")
    return True


async def frighten_or_harden(ctx: TickContext, war_id: int, perpetrator: EntityRow, victim: EntityRow) -> bool:
    table = ctx.rules.war_conduct
    fearful = (await values_for(ctx.session, victim.id)).get(ValueAxis.MARTIAL, 0) < 0
    side = await ctx.session.get(WarSideRow, (war_id, victim.id))
    if side is not None and "support" not in side.locked and not held(victim.id):
        side.support = clamp_int(side.support + (-table.dread_support if fearful else table.harden_support), 0, PERCENT)
    if fearful:
        for row in await ctx.session.scalars(select(ArmyRow).where(ArmyRow.owner_entity_id == victim.id, ArmyRow.disbanded_epoch.is_(None))):
            army = await living_entity(ctx.session, row.entity_id)
            if army is not None and not held(army.id):
                shift_stat(army, "morale", -table.dread_morale * await fear_of(ctx.session, army))
        return True
    book = await RealmBook.load(ctx.session)
    homeland = {region for region in [book.atlas.top_region(victim.id)] if region is not None}
    for occupation in await ctx.session.scalars(select(OccupationRow).where(OccupationRow.occupier_entity_id == perpetrator.id)):
        if occupation.region_entity_id in homeland and "resistance" not in occupation.locked and not held(occupation.region_entity_id):
            occupation.resistance = clamp_int(occupation.resistance + table.harden_resistance, 0, PERCENT)
    return False


async def backlash(ctx: TickContext, perpetrator: EntityRow) -> int:
    table = ctx.rules.war_conduct
    book = await RealmBook.load(ctx.session)
    own = await realm_of(ctx, perpetrator.id)
    onlookers = [realm for realm in book.realms.values() if realm.entity.id != own and realm.entity.world_id == perpetrator.world_id]
    for realm in onlookers:
        core = realm.profile.core_entity_id
        mercy = max(0, (await values_for(ctx.session, core)).get(ValueAxis.MERCY, 0)) if core is not None else 0
        outrage = 1 + mercy / PERCENT * table.atrocity_mercy_pct / PERCENT
        await acclaim(ctx.session, perpetrator.id, realm.entity.id, ReputationAxis.CRUELTY, amount=table.atrocity_cruelty * outrage, epoch=ctx.epoch)
        if own is not None:
            await shift_regard(ctx, realm.entity.id, own, threat=round_half_up(table.atrocity_threat * outrage))
    ruler = await ruler_of_realm(ctx.session, own) if own is not None else None
    purse = await purse_of(ctx.session, ruler, ctx.epoch) if ruler is not None else None
    if purse is not None:
        bump(purse, Currency.DREAD, table.atrocity_dread)
    return len(onlookers)


async def war_between(ctx: TickContext, first_id: int, second_id: int) -> int | None:
    ongoing = select(WarRow.id).where(WarRow.status != WarStatus.ENDED)
    mine = select(WarSideRow.war_id).where(WarSideRow.entity_id == first_id, WarSideRow.left_epoch.is_(None), WarSideRow.war_id.in_(ongoing))
    theirs = select(WarSideRow).where(WarSideRow.entity_id == second_id, WarSideRow.war_id.in_(mine), WarSideRow.left_epoch.is_(None))
    row = await ctx.session.scalar(theirs.order_by(WarSideRow.war_id).limit(1))
    return row.war_id if row is not None else None


async def terror(ctx: TickContext, war_id: int, perpetrator: EntityRow, victim: EntityRow, deed: str) -> bool:
    if held(perpetrator.id):
        return False
    fearful = await frighten_or_harden(ctx, war_id, perpetrator, victim)
    await backlash(ctx, perpetrator)
    war = await ctx.session.get(WarRow, war_id)
    facts: dict[str, FactInput] = {"deed": deed}
    if war is not None:
        facts["war"] = war.event_entity_id
    await record_incident(
        ctx, "war.terror" if fearful else "war.terror_hardened", roles={IncidentRole.ACTOR: perpetrator.id, IncidentRole.VICTIM: victim.id}, facts=facts
    )
    ctx.count("terror_fearful" if fearful else "terror_hardened")
    return fearful

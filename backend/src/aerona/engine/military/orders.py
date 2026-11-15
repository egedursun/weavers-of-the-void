from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.constants.warfare import ARMY_NAME_TEMPLATE
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyOfficerRow, WarAimRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import ArmyRow, CaptiveRow, SiegeRow, WarRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import AGENT_TYPES, COMMUNITY_TYPES, EntityFlag, EntityType
from aerona.domain.enums.military import ArmyRole, PeaceTermKind, Stance, WarAimKind
from aerona.domain.enums.war import WarCause, WarEnding
from aerona.domain.models.entity_stats import ArmyStats, VesselStats
from aerona.engine.context import TickContext
from aerona.engine.interconnect.flows import flowing
from aerona.engine.military.causes import declared_war
from aerona.engine.military.peace import PeaceTerm
from aerona.engine.military.shipyard import Commission, commission
from aerona.engine.military.siege import open_siege
from aerona.engine.military.units import muster, profile_of
from aerona.engine.military.vessels import SeaTally, repair
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.levies import levy, levy_category
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import headcount_value
from aerona.engine.services.war import require_ongoing_war, take_captive
from aerona.engine.services.war_resolution import WarSettlement, end_war

ARMY_SUBTYPE = "standing army"


async def class_levy_cap(ctx: TickContext, community: EntityRow) -> int | None:
    society = await ctx.session.get(CommunitySocietyRow, community.id)
    people = headcount_value(community)
    if society is None or people is None:
        return None
    table = ctx.rules.levies
    commoners = society.share_farmer + society.share_artisan + society.share_merchant + society.share_serf_or_slave
    share = society.share_warrior * table.warrior_first_pct + society.share_noble * table.noble_first_pct + commoners * table.commoner_pct
    return max(1, round_half_up(people * share / PERCENT / PERCENT))


async def raise_standing_army(
    ctx: TickContext, community_id: int, size: int, *, commander_id: int | None = None, war_id: int | None = None, name: str | None = None
) -> EntityRow:
    community = await living_entity(ctx.session, community_id)
    if community is None or community.entity_type not in COMMUNITY_TYPES:
        raise ValidationFailedError("Only a living community can raise an army.")
    war = (await require_ongoing_war(ctx.session, war_id)).war if war_id is not None else None
    cap = await class_levy_cap(ctx, community)
    wanted = clamp_int(size, 1, ctx.rules.limits.army_soldier_cap)
    soldiers = levy(ctx.rules, community, min(wanted, cap) if cap is not None else wanted)
    if soldiers <= 0:
        raise ConflictError(f"{community.name} has no one left to levy.")
    from_engine = ctx.rules.campaigns
    with flowing(levy_category(community)):
        army = await create_record(
            ctx,
            RecordSpec(
                name=name or ARMY_NAME_TEMPLATE.format(root=community.name),
                entity_type=EntityType.ARMY,
                stats=ArmyStats(
                    size=soldiers, morale=from_engine.army_morale_base, equipment=from_engine.army_equipment_base, experience=from_engine.army_experience
                ),
                body=f"{community.name} raised an army of {soldiers} by decree.",
                power=clamp_int(community.power_level, from_engine.army_power_min, from_engine.army_power_max),
                world_id=community.world_id,
                location_id=community.id if community.entity_type is EntityType.SETTLEMENT else community.location_id,
                subtype=ARMY_SUBTYPE,
            ),
        )
    commander = await living_entity(ctx.session, commander_id)
    ctx.session.add(
        ArmyRow(
            entity_id=army.id,
            war_id=war.id if war is not None else None,
            owner_entity_id=community.id,
            commander_entity_id=commander.id if commander is not None else None,
            raised_epoch=ctx.epoch,
        )
    )
    await ctx.session.flush()
    await muster(ctx, army, community, await KnowledgeMap.load(ctx.session))
    await profile_of(ctx, army, community)
    bonds = BondRepository(ctx.session)
    await bonds.connect(BondDraft(army.id, community.id, BondKind.PROTECTS, ctx.epoch, "serves"))
    if commander is not None:
        await bonds.connect(BondDraft(commander.id, army.id, BondKind.COMMANDS, ctx.epoch, "commands"))
        ctx.session.add(ArmyOfficerRow(army_entity_id=army.id, mortal_entity_id=commander.id, role=ArmyRole.COMMANDER, since_epoch=ctx.epoch, locked=[]))
    if war is None:
        await EntityRepository(ctx.session).add_flag(army.id, EntityFlag.ON_WATCH, ctx.epoch)
    await ctx.session.flush()
    return army


async def set_commander(ctx: TickContext, army_id: int, mortal_id: int | None, owner_id: int | None = None) -> ArmyRow:
    row = await ctx.session.get(ArmyRow, army_id)
    if row is None:
        raise NotFoundError("No such army.")
    if mortal_id is not None:
        mortal = await living_entity(ctx.session, mortal_id)
        if mortal is None or mortal.entity_type is not EntityType.MORTAL:
            raise ValidationFailedError("A commander must be a living mortal.")
    for officer in await ctx.session.scalars(
        select(ArmyOfficerRow).where(ArmyOfficerRow.army_entity_id == army_id, ArmyOfficerRow.role == ArmyRole.COMMANDER, ArmyOfficerRow.until_epoch.is_(None))
    ):
        officer.until_epoch = ctx.epoch
    row.commander_entity_id = mortal_id
    if mortal_id is not None:
        ctx.session.add(ArmyOfficerRow(army_entity_id=army_id, mortal_entity_id=mortal_id, role=ArmyRole.COMMANDER, since_epoch=ctx.epoch, locked=[]))
    if owner_id is not None:
        owner = await living_entity(ctx.session, owner_id)
        if owner is None or owner.entity_type not in COMMUNITY_TYPES:
            raise ValidationFailedError("An army must serve a living community.")
        row.owner_entity_id = owner.id
    await ctx.session.flush()
    return row


async def start_siege(ctx: TickContext, war_id: int, army_id: int, settlement_id: int) -> SiegeRow:
    item = await require_ongoing_war(ctx.session, war_id)
    army_row = await ctx.session.get(ArmyRow, army_id)
    settlement = await living_entity(ctx.session, settlement_id)
    if army_row is None or settlement is None or settlement.entity_type is not EntityType.SETTLEMENT:
        raise ValidationFailedError("A siege needs a living army and a living settlement.")
    if not item.involves(army_row.owner_entity_id) or not item.involves(settlement.id):
        raise ValidationFailedError("The besiegers and the besieged must be the two sides of the war.")
    besieger = await living_entity(ctx.session, army_row.owner_entity_id)
    siege = await open_siege(ctx, item.war, settlement, besieger or settlement)
    army = await living_entity(ctx.session, army_id)
    if army is not None:
        profile = await profile_of(ctx, army, besieger)
        profile.target_entity_id = profile.region_entity_id
        profile.stance = Stance.BESIEGE
    return siege


async def declare_with_cause(
    ctx: TickContext, attacker_id: int, defender_id: int, cause: WarCause, *, reason: str, aims: list[tuple[WarAimKind, dict[str, int | str | bool]]]
) -> WarRow:
    first = aims[0] if aims else (None, {})
    war = await declared_war(ctx, attacker_id, defender_id, cause, reason, aim=first[0], params=first[1])
    if war is None:
        raise ConflictError("No war could be opened between these two now.")
    for kind, params in aims[1:]:
        ctx.session.add(
            WarAimRow(war_id=war.id, side_entity_id=attacker_id, kind=kind, target_entity_id=defender_id, params=dict(params), achieved=0, locked=[])
        )
    await ctx.session.flush()
    return war


async def build_peace(ctx: TickContext, war_id: int, victor_id: int | None, terms: list[tuple[PeaceTermKind, dict[str, int | str | bool]]]) -> WarSettlement:
    item = await require_ongoing_war(ctx.session, war_id)
    chosen = [PeaceTerm(kind, dict(params)) for kind, params in terms]
    if victor_id is None:
        return await end_war(ctx, item.war, WarEnding.WHITE_PEACE, reason="peace made by decree", chosen=chosen)
    if not item.involves(victor_id):
        raise ValidationFailedError("The victor must be a side of the war.")
    loser_id = item.foe_of(victor_id)
    return await end_war(ctx, item.war, WarEnding.VICTORY, victor_id=victor_id, loser_id=loser_id, reason="peace terms set by decree", chosen=chosen)


async def create_vessel(ctx: TickContext, owner_id: int, name: str, order: Commission) -> EntityRow:
    owner = await living_entity(ctx.session, owner_id)
    if owner is None:
        raise ValidationFailedError("A vessel needs a living owner.")
    if owner.entity_type not in AGENT_TYPES:
        raise ValidationFailedError(f"{owner.name} cannot own a ship; a town, a people, a faction, a cult or a mortal holds one.")
    vessel = await create_record(
        ctx,
        RecordSpec(
            name=name,
            entity_type=EntityType.VESSEL,
            stats=VesselStats(speed=0, range=0, crew=0, armor=100, strangeness=0),
            body=f"{owner.name} laid down a new ship.",
            power=1,
            world_id=owner.world_id,
            location_id=order.home_port_id or (owner.id if owner.entity_type is EntityType.SETTLEMENT else owner.location_id),
            subtype="ship",
        ),
    )
    await BondRepository(ctx.session).connect(BondDraft(owner.id, vessel.id, BondKind.OWNS, ctx.epoch, "laid down by decree"))
    if order.captain_id is not None:
        await BondRepository(ctx.session).connect(BondDraft(order.captain_id, vessel.id, BondKind.CAPTAIN_OF, ctx.epoch, "captain"))
    profile = await commission(ctx.session, ctx.rules, vessel, order)
    profile.crew_community_entity_id = owner.id
    await ctx.session.flush()
    return vessel


async def repair_vessel(ctx: TickContext, vessel_id: int) -> int:
    row = await ctx.session.get(VesselProfileRow, vessel_id)
    if row is None:
        raise NotFoundError("No such vessel.")
    gain = await repair(ctx, row, SeaTally())
    if gain <= 0:
        raise ConflictError("No shipyard at its home port can mend it, or its owners cannot pay.")
    return gain


async def take_named_captive(ctx: TickContext, captor_id: int, mortal_id: int, war_id: int | None = None) -> CaptiveRow:
    captor, mortal = await living_entity(ctx.session, captor_id), await living_entity(ctx.session, mortal_id)
    if captor is None or mortal is None or mortal.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("A living captor takes a living mortal.")
    war = await ctx.session.get(WarRow, war_id) if war_id is not None else None
    return await take_captive(ctx, captor, mortal, war, description="taken by decree", home_id=mortal.location_id)

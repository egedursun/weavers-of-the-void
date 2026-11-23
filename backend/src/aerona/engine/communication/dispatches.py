from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from aerona.catalog.ethics import HONOUR_MODELS
from aerona.catalog.intrigue import BELIEF_ATTRIBUTES
from aerona.catalog.life.communication import COURTESIES_OFFICE_KINDS, EFFECTS_DISPATCH_CONTENTS, WELCOME_SKILL_KINDS
from aerona.catalog.life.domain import OUTLAW_KINDS
from aerona.catalog.pacts import DISPATCH_CONTENTS, TRAVELLING_STATES
from aerona.constants.units import PERCENT
from aerona.db.tables.communication import CipherRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.military import ArmyProfileRow, SpyNetworkRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow, TreatyBreachRow, TreatyClauseRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.communication import DispatchContent, DispatchState, EnvoyFate, Medium
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intrigue import BeliefSource, FavourOrigin
from aerona.domain.enums.mind import ActKind, MemoryKind, PreferenceKind, SkillKind, ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.war import WarCause
from aerona.engine.communication.post import CLAUSES, COMMODITY, FACTS, FORGER, LOCKED_STATE, OVERLAND, SPIED, TREATY, send
from aerona.engine.context import TickContext
from aerona.engine.intrigue.beliefs import believe
from aerona.engine.intrigue.favours import owe
from aerona.engine.mind.book import best_skill, values_for
from aerona.engine.mind.ethics import culture_of, honour_of
from aerona.engine.mind.hooks import judged
from aerona.engine.mind.memories import remember
from aerona.engine.mind.preferences import fit, prefs_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.queries import bond_exists, living_entity, spoken_language
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.recording.record import record
from aerona.engine.relations.book import ensure_relation, relation, shift
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.community_relations import relation as community_relation
from aerona.engine.services.war import declare_war, take_captive
from aerona.engine.tongues.grammar import misread_factor

ARMY = "army"
REGION = "region"


@dataclass
class DispatchTally:
    sent: int = 0
    delivered: int = 0
    intercepted: int = 0
    lost: int = 0
    forged: int = 0
    misread: int = 0
    envoys_harmed: int = 0
    delayed: int = 0
    obeyed: int = 0
    warned: int = 0
    defected: int = 0


async def readable(ctx: TickContext, row: MessageRow, reader_id: int) -> bool:
    if not row.enciphered:
        return True
    cipher = await ctx.session.get(CipherRow, row.sender_node_id)
    return cipher is None or reader_id in cipher.broken_by


async def learn_facts(ctx: TickContext, holder_id: int, facts: dict[str, Any], source: BeliefSource, confidence: int) -> int:
    learned = 0
    for subject, attributes in facts.items():
        if not str(subject).isdigit() or not isinstance(attributes, dict):
            continue
        for attribute, value in attributes.items():
            if isinstance(value, int) and await believe(ctx, holder_id, int(subject), str(attribute), value, source=source, confidence=confidence):
                learned += 1
    return learned


async def spy_networks_on(ctx: TickContext, row: MessageRow) -> list[SpyNetworkRow]:
    ends = [row.sender_node_id, row.recipient_node_id]
    networks = await ctx.session.scalars(select(SpyNetworkRow).where(SpyNetworkRow.target_entity_id.in_(ends)).order_by(SpyNetworkRow.id))
    return [network for network in networks if network.owner_entity_id not in ends and not held(network.owner_entity_id)]


async def outlaws_near(ctx: TickContext, row: MessageRow) -> bool:
    ends = [row.sender_node_id, row.recipient_node_id]
    places = [found.location_id for end in ends if (found := await ctx.session.get(EntityRow, end)) is not None]
    homes = [*ends, *(place for place in places if place is not None)]
    gang = await ctx.session.scalar(
        select(FactionProfileRow.faction_entity_id).where(FactionProfileRow.kind.in_(list(OUTLAW_KINDS)), FactionProfileRow.home_entity_id.in_(homes)).limit(1)
    )
    return gang is not None


async def enemy_army_near(ctx: TickContext, row: MessageRow) -> int | None:
    atlas = await RegionAtlas.load(ctx.session)
    lands = {atlas.top_region(end) for end in (row.sender_node_id, row.recipient_node_id)} - {None}
    if not lands:
        return None
    armies = await ctx.session.execute(
        select(ArmyRow.owner_entity_id)
        .join(ArmyProfileRow, ArmyProfileRow.army_entity_id == ArmyRow.entity_id)
        .where(ArmyRow.disbanded_epoch.is_(None), ArmyRow.war_id.is_not(None), ArmyProfileRow.region_entity_id.in_(list(lands)))
        .order_by(ArmyRow.entity_id)
    )
    for (owner,) in armies:
        if owner in (row.sender_node_id, row.recipient_node_id):
            continue
        if await bond_exists(ctx.session, owner, row.sender_node_id, BondKind.ENEMY) or await bond_exists(
            ctx.session, owner, row.recipient_node_id, BondKind.ENEMY
        ):
            return int(owner)
    return None


async def waylay(ctx: TickContext, row: MessageRow, tally: DispatchTally) -> None:
    table = ctx.rules.communication
    if row.intercepted_by_node_id is None:
        for network in await spy_networks_on(ctx, row):
            if not ctx.rng(seed_of("dispatch.intercept", row.id, network.id, ctx.epoch)).chance(table.spy_intercept_pct * network.depth / PERCENT):
                continue
            row.intercepted_by_node_id = network.owner_entity_id
            tally.intercepted += 1
            if await bond_exists(ctx.session, network.owner_entity_id, row.sender_node_id, BondKind.ENEMY):
                row.state = DispatchState.INTERCEPTED
            if await readable(ctx, row, network.owner_entity_id):
                await learn_facts(ctx, network.owner_entity_id, row.payload.get(FACTS, {}), BeliefSource.SPY, ctx.rules.belief_state.spy_confidence)
                if not row.forged and ctx.rng(seed_of("dispatch.forge", row.id, ctx.epoch)).chance(table.forge_replace_pct):
                    row.forged, row.content = True, DispatchContent.INSULT
                    row.payload = {**row.payload, FORGER: network.owner_entity_id}
                    tally.forged += 1
            break
    if row.intercepted_by_node_id is None and row.medium in OVERLAND:
        seizer = await enemy_army_near(ctx, row)
        if seizer is not None and ctx.rng(seed_of("dispatch.army", row.id, ctx.epoch)).chance(table.army_intercept_pct):
            row.intercepted_by_node_id, row.state = seizer, DispatchState.INTERCEPTED
            tally.intercepted += 1
            if await readable(ctx, row, seizer):
                await learn_facts(ctx, seizer, row.payload.get(FACTS, {}), BeliefSource.SPY, ctx.rules.belief_state.spy_confidence)
    if row.medium in OVERLAND and await outlaws_near(ctx, row) and ctx.rng(seed_of("dispatch.outlaws", row.id, ctx.epoch)).chance(table.outlaw_loss_pct):
        row.state = DispatchState.LOST
        tally.lost += 1


async def misread(ctx: TickContext, row: MessageRow) -> bool:
    recipient_tongue = await spoken_language(ctx.session, row.recipient_node_id)
    if row.language_node_id is None or recipient_tongue is None or recipient_tongue.id == row.language_node_id:
        return False
    table = ctx.rules.communication
    clauses = max(1, len(row.payload.get(CLAUSES, [])) or 1)
    skill = await best_skill(ctx.session, row.recipient_node_id, [SkillKind.LANGUAGES])
    chance = table.misread_pct * clauses * max(0.0, 1 - skill / PERCENT * table.interpreter_pct / PERCENT)
    chance *= await misread_factor(ctx.session, ctx.rules, {row.language_node_id}, {recipient_tongue.id})
    return ctx.rng(seed_of("dispatch.misread", row.id)).chance(chance)


async def welcome(ctx: TickContext, row: MessageRow) -> float:
    table = ctx.rules.communication
    skill = await best_skill(ctx.session, row.envoy_node_id, WELCOME_SKILL_KINDS) if row.envoy_node_id is not None else 0
    hierarchy = max(0, (await values_for(ctx.session, row.recipient_node_id)).get(ValueAxis.HIERARCHY, 0))
    precedence = hierarchy / PERCENT * table.precedence_pct / PERCENT * (1 - skill / PERCENT)
    return max(0.0, 1 + skill / PERCENT * table.etiquette_pct / PERCENT - precedence)


async def warm(ctx: TickContext, holder_id: int, subject_id: int, friendship: float, kind: MemoryKind) -> None:
    holder = await ctx.session.get(EntityRow, holder_id)
    subject = await ctx.session.get(EntityRow, subject_id)
    mortals = holder is not None and subject is not None and holder.entity_type is EntityType.MORTAL and subject.entity_type is EntityType.MORTAL
    if mortals:
        view = await ensure_relation(ctx.session, holder_id, subject_id, ctx.epoch)
        if view is not None:
            shift(ctx.rules, view, ctx.epoch, friendship=round(friendship))
        await remember(ctx.session, ctx.rules, holder_id=holder_id, subject_id=subject_id, kind=kind, magnitude=round(friendship), epoch=ctx.epoch)
    elif holder is not None and subject is not None:
        await change_relation(ctx, holder_id, subject_id, friendship, kind)


async def culture_id(ctx: TickContext, node_id: int) -> int:
    found = await culture_of(ctx.session, node_id)
    return found.id if found is not None else node_id


async def gift_value(ctx: TickContext, recipient_id: int, commodity: str | None) -> int:
    prefs = await prefs_of(ctx.session, await culture_id(ctx, recipient_id))
    return max(fit(prefs, PreferenceKind.MATERIAL, commodity), fit(prefs, PreferenceKind.FOOD, commodity), fit(prefs, PreferenceKind.DRINK, commodity))


async def receive_envoy(ctx: TickContext, row: MessageRow, tally: DispatchTally) -> None:
    table = ctx.rules.communication
    envoy = await living_entity(ctx.session, row.envoy_node_id)
    if envoy is None or held(envoy.id):
        return
    back = await relation(ctx.session, row.recipient_node_id, row.sender_node_id)
    hostile = back is not None and back.friendship <= table.envoy_hostility
    if not hostile or not ctx.rng(seed_of("dispatch.envoy", row.id)).chance(table.envoy_harm_pct):
        row.envoy_fate = EnvoyFate.RECEIVED
        if ctx.rng(seed_of("dispatch.defect", row.id)).chance(ctx.rules.envoys.defect_pct):
            await defect(ctx, row, envoy)
            tally.defected += 1
        return
    recipient = await living_entity(ctx.session, row.recipient_node_id)
    roll = ctx.rng(seed_of("dispatch.envoy_fate", row.id)).integer(0, 3)
    tally.envoys_harmed += 1
    if roll == 3 and recipient is not None:
        await expel(ctx, row, recipient.id)
    elif roll == 0 or recipient is None:
        row.envoy_fate = EnvoyFate.INSULTED
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=row.sender_node_id,
            subject_id=row.recipient_node_id,
            kind=MemoryKind.HUMILIATED_ME,
            magnitude=-table.insult_harm,
            epoch=ctx.epoch,
        )
    elif roll == 1:
        row.envoy_fate = EnvoyFate.IMPRISONED
        await take_captive(ctx, recipient, envoy, None, description="an envoy thrown in chains", home_id=envoy.location_id)
    else:
        row.envoy_fate = EnvoyFate.KILLED
        await judged(ctx, recipient.id, envoy.id, ActKind.GUEST_KILLING)
        await declare_war(ctx, row.sender_node_id, recipient.id, f"{recipient.name} slew the envoy {envoy.name}", cause=WarCause.PUNITIVE, world_cap=False)


async def sting(ctx: TickContext, row: MessageRow, recipient: int) -> float:
    model = await honour_of(ctx.session, await culture_id(ctx, recipient))
    spec = HONOUR_MODELS[model]
    return (spec.herald_sting_pct if row.medium is Medium.HERALD else spec.message_sting_pct) / PERCENT


async def effects(ctx: TickContext, row: MessageRow, tally: DispatchTally) -> None:
    table = ctx.rules.communication
    kindness = await welcome(ctx, row)
    sender, recipient = row.sender_node_id, row.recipient_node_id
    content = row.content
    if content in EFFECTS_DISPATCH_CONTENTS:
        source = BeliefSource.SPY if row.payload.get(SPIED) else BeliefSource.MESSAGE
        confidence = table.misread_confidence if row.misread else table.report_confidence
        await learn_facts(ctx, recipient, row.payload.get(FACTS, {}), source, confidence)
    elif content is DispatchContent.DECLARATION and row.forged:
        named = await living_entity(ctx.session, sender)
        if named is not None:
            await declare_war(ctx, recipient, sender, f"a letter in the name of {named.name} declared war", cause=WarCause.HOSTILITY, world_cap=False)
    elif content is DispatchContent.INSULT:
        harm = table.insult_harm * await sting(ctx, row, recipient)
        await warm(ctx, recipient, sender, -harm, MemoryKind.HUMILIATED_ME)
    elif content is DispatchContent.GIFT_NOTICE:
        taste = await gift_value(ctx, recipient, row.payload.get(COMMODITY))
        await warm(ctx, recipient, sender, table.gift_friendship * (PERCENT + taste) / PERCENT * kindness, MemoryKind.GIFTED_ME)
        await owe(ctx, recipient, sender, FavourOrigin.GIFT, table.gift_favour)
    elif content is DispatchContent.THREAT:
        await warm(ctx, recipient, sender, -table.threat_harm, MemoryKind.ILL_WILL)
    elif content is DispatchContent.PLEA:
        await warm(ctx, recipient, sender, table.plea_mercy * kindness, MemoryKind.GIFTED_ME)
    elif content is DispatchContent.DEMAND:
        await warm(ctx, recipient, sender, (kindness - await sting(ctx, row, recipient)) * table.gift_friendship, MemoryKind.HUMILIATED_ME)
    elif content is DispatchContent.PROPOSAL:
        await warm(ctx, recipient, sender, (kindness - 1) * table.gift_friendship, MemoryKind.GIFTED_ME)
        acted = ctx.rng(seed_of("dispatch.misread_acted", row.id)).chance(ctx.rules.dispatches.misread_pct)
        if row.misread and acted and isinstance(row.payload.get(TREATY), int):
            await misread_clause(ctx, row.payload[TREATY], recipient)
    elif content is not None and DISPATCH_CONTENTS[content].commands:
        tally.obeyed += int(await obey(ctx, row))
    elif content is not None and DISPATCH_CONTENTS[content].warns:
        tally.warned += int(await heed(ctx, row))


async def misread_clause(ctx: TickContext, treaty_id: int, reader_id: int) -> None:
    clause = await ctx.session.scalar(select(TreatyClauseRow).where(TreatyClauseRow.treaty_entity_id == treaty_id).order_by(TreatyClauseRow.id).limit(1))
    if clause is not None:
        ctx.session.add(TreatyBreachRow(treaty_entity_id=treaty_id, clause_id=clause.id, breaker_node_id=reader_id, epoch=ctx.epoch, note="misread"))


async def deliver(ctx: TickContext, row: MessageRow, tally: DispatchTally) -> None:
    row.state = DispatchState.DELIVERED
    if "misread" not in (row.locked or []):
        row.misread = await misread(ctx, row)
    tally.delivered += 1
    tally.misread += int(row.misread)
    await mark_arrival(ctx, row)
    if row.envoy_node_id is not None:
        await receive_envoy(ctx, row, tally)
    if row.envoy_fate is EnvoyFate.KILLED:
        return
    await effects(ctx, row, tally)


async def tend_dispatches(ctx: TickContext, tally: DispatchTally) -> None:
    rows = await ctx.session.scalars(
        select(MessageRow).where(MessageRow.intent == MessageIntent.DISPATCH, MessageRow.state.in_(list(TRAVELLING_STATES))).order_by(MessageRow.id)
    )
    for row in list(rows):
        if LOCKED_STATE in (row.locked or []) or held(row.recipient_node_id) or held(row.sender_node_id):
            continue
        await waylay(ctx, row, tally)
        if row.state in TRAVELLING_STATES and (row.arrival_epoch or 0) <= ctx.epoch:
            if await held_up(ctx, row):
                tally.delayed += 1
                continue
            await deliver(ctx, row, tally)


async def finest_good(ctx: TickContext, realm_id: int) -> str | None:
    profile = await ctx.session.get(PolityProfileRow, realm_id)
    seat = profile.capital_entity_id if profile is not None else None
    found = await ctx.session.scalar(
        select(CommunityStockRow.commodity)
        .where(CommunityStockRow.community_entity_id == seat)
        .order_by(CommunityStockRow.quantity.desc(), CommunityStockRow.commodity)
        .limit(1)
    )
    return found.value if found is not None else None


async def courtesies(ctx: TickContext, atlas: RegionAtlas, tally: DispatchTally) -> None:
    table = ctx.rules.communication
    realms = list(await ctx.session.scalars(select(PolityProfileRow.polity_entity_id).order_by(PolityProfileRow.polity_entity_id)))
    for realm in realms:
        if held(realm):
            continue
        envoy = await ctx.session.scalar(
            select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == realm, OfficeRow.kind.in_(COURTESIES_OFFICE_KINDS)).limit(1)
        )
        for other in realms:
            if other == realm or atlas.world_of(other) != atlas.world_of(realm):
                continue
            warmth = await community_relation(ctx.session, ctx.rules, realm, other)
            rng = ctx.rng(seed_of("dispatch.courtesy", realm, other, ctx.epoch))
            if warmth >= table.warm_at and rng.chance(table.ruler_gift_pct):
                commodity = await finest_good(ctx, realm)
                payload = {COMMODITY: commodity} if commodity is not None else {}
                if await send(
                    ctx, realm, other, DispatchContent.GIFT_NOTICE, Medium.ENVOY if envoy else Medium.LETTER, payload=payload, envoy_id=envoy, atlas=atlas
                ):
                    tally.sent += 1
            elif warmth <= table.cold_at and rng.chance(table.ruler_insult_pct):
                if await send(ctx, realm, other, DispatchContent.INSULT, Medium.LETTER, atlas=atlas):
                    tally.sent += 1


async def held_up(ctx: TickContext, row: MessageRow) -> bool:
    if row.medium not in OVERLAND or row.state is DispatchState.DELAYED or LOCKED_STATE in (row.locked or []):
        return False
    if await enemy_army_near(ctx, row) is None:
        return False
    row.state, row.arrival_epoch = DispatchState.DELAYED, ctx.epoch + 1
    return True


async def mark_arrival(ctx: TickContext, row: MessageRow) -> None:
    if row.forged:
        row.state = DispatchState.FORGED
        forger = row.payload.get(FORGER)
        await record(
            ctx,
            "dispatch.forged",
            roles={
                IncidentRole.ACTOR: forger if isinstance(forger, int) else None,
                IncidentRole.ORIGIN: row.sender_node_id,
                IncidentRole.RECEIVER: row.recipient_node_id,
            },
            facts={"content": row.content},
        )
    elif row.misread:
        row.state = DispatchState.MISREAD
        await record(
            ctx,
            "dispatch.misread",
            roles={IncidentRole.ORIGIN: row.sender_node_id, IncidentRole.RECEIVER: row.recipient_node_id},
            facts={"content": row.content},
        )


async def obey(ctx: TickContext, row: MessageRow) -> bool:
    army_id, region_id = row.payload.get(ARMY), row.payload.get(REGION)
    if not isinstance(army_id, int) or not isinstance(region_id, int):
        return False
    army = await ctx.session.get(ArmyRow, army_id)
    profile = await ctx.session.get(ArmyProfileRow, army_id)
    if army is None or profile is None or army.disbanded_epoch is not None or held(army_id) or "region_entity_id" in (profile.locked or []):
        return False
    if not ctx.rng(seed_of("dispatch.obey", row.id)).chance(ctx.rules.dispatches.order_obedience_pct):
        return False
    profile.region_entity_id = region_id
    await record(
        ctx,
        "dispatch.order_obeyed",
        roles={
            IncidentRole.ACTOR: row.recipient_node_id,
            IncidentRole.AUTHORITY: row.sender_node_id,
            IncidentRole.SUBJECT: army_id,
            IncidentRole.PLACE: region_id,
        },
        facts={"content": row.content},
        place=region_id,
    )
    return True


async def heed(ctx: TickContext, row: MessageRow) -> bool:
    town = await living_entity(ctx.session, row.recipient_node_id)
    if town is None or held(town.id):
        return False
    shift_stat(town, "defense", ctx.rules.dispatches.warning_prepare_pct, high=PERCENT)
    return True


async def defect(ctx: TickContext, row: MessageRow, envoy: EntityRow) -> None:
    host = await living_entity(ctx.session, row.recipient_node_id)
    if host is None:
        return
    row.envoy_fate = EnvoyFate.DEFECTED
    envoy.location_id = host.id if host.entity_type is EntityType.SETTLEMENT else host.location_id
    sender = await living_entity(ctx.session, row.sender_node_id)
    if sender is not None:
        for attribute in BELIEF_ATTRIBUTES:
            value = stat(sender, attribute)
            if value is not None:
                await believe(ctx, host.id, sender.id, attribute, value, source=BeliefSource.SPY, confidence=ctx.rules.belief_state.spy_confidence)
    await record(ctx, "envoy.defected", roles={IncidentRole.ENVOY: envoy.id, IncidentRole.HOST: host.id, IncidentRole.VICTIM: row.sender_node_id})


async def expel(ctx: TickContext, row: MessageRow, by_id: int) -> bool:
    if row.envoy_node_id is None or held(row.envoy_node_id):
        return False
    row.envoy_fate = EnvoyFate.EXPELLED
    await remember(
        ctx.session,
        ctx.rules,
        holder_id=row.sender_node_id,
        subject_id=row.recipient_node_id,
        kind=MemoryKind.HUMILIATED_ME,
        magnitude=-ctx.rules.communication.insult_harm // 2,
        epoch=ctx.epoch,
    )
    await record(ctx, "envoy.expelled", roles={IncidentRole.ENVOY: row.envoy_node_id, IncidentRole.HOST: by_id, IncidentRole.RECEIVER: row.sender_node_id})
    return True


async def commanders_of(ctx: TickContext, realm_id: int) -> list[ArmyRow]:
    return list(
        await ctx.session.scalars(
            select(ArmyRow)
            .where(ArmyRow.owner_entity_id == realm_id, ArmyRow.disbanded_epoch.is_(None), ArmyRow.commander_entity_id.is_not(None))
            .order_by(ArmyRow.entity_id)
        )
    )


async def orders_and_warnings(ctx: TickContext, atlas: RegionAtlas, tally: DispatchTally) -> None:
    for realm in list(await ctx.session.scalars(select(PolityProfileRow).order_by(PolityProfileRow.polity_entity_id))):
        seat = realm.capital_entity_id
        home = atlas.top_region(seat) if seat is not None else None
        if seat is None or home is None or held(realm.polity_entity_id):
            continue
        for army in await commanders_of(ctx, realm.polity_entity_id):
            profile = await ctx.session.get(ArmyProfileRow, army.entity_id)
            if army.war_id is not None or profile is None or profile.region_entity_id in (None, home) or army.commander_entity_id is None:
                continue
            payload = {ARMY: army.entity_id, REGION: home}
            if await send(ctx, seat, army.commander_entity_id, DispatchContent.ORDER, Medium.LETTER, payload=payload, atlas=atlas):
                tally.sent += 1
        for town_id in [member for member in atlas.communities_in(home) if member != seat][:1]:
            danger = await threat_near(ctx, atlas, realm.polity_entity_id, town_id)
            if danger and await send(ctx, seat, town_id, DispatchContent.WARNING, Medium.LETTER, payload={"danger": danger}, atlas=atlas):
                tally.sent += 1


async def threat_near(ctx: TickContext, atlas: RegionAtlas, realm_id: int, town_id: int) -> int | None:
    land = atlas.top_region(town_id)
    if land is None:
        return None
    lands = [land, *atlas.neighbour_regions(land)]
    armies = await ctx.session.execute(
        select(ArmyRow.owner_entity_id)
        .join(ArmyProfileRow, ArmyProfileRow.army_entity_id == ArmyRow.entity_id)
        .where(ArmyRow.disbanded_epoch.is_(None), ArmyRow.war_id.is_not(None), ArmyProfileRow.region_entity_id.in_(lands))
        .order_by(ArmyRow.entity_id)
    )
    for (owner,) in armies:
        if owner != realm_id and await bond_exists(ctx.session, owner, realm_id, BondKind.ENEMY):
            return int(owner)
    return None

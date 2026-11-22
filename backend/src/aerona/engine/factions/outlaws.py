from sqlalchemy import select

from aerona.catalog.life.domain import ROBBER_KINDS
from aerona.catalog.life.factions import SUPPRESS_FACTION_KINDS
from aerona.constants.units import PERCENT
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.polity import TreatyProfileRow
from aerona.db.tables.warfare import WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.faction import FactionActionKind, FactionKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import ClauseKind, OfficePower, PartyRole, TreatyBreach, TreatyKind, TreatyStatus
from aerona.engine.context import TickContext
from aerona.engine.factions.book import FactionBook, log
from aerona.engine.military.support import new_side
from aerona.engine.polity.accords import Clause, end_treaty, sign
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.offices import best_skill
from aerona.engine.polity.treaties import breach
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.primitives.transfers import move_amount
from aerona.engine.recording.record import record as record_incident
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.war import ongoing_wars


async def suppress(ctx: TickContext, factions: FactionBook, realms: RealmBook) -> int:
    table = ctx.rules.banditry
    broken = 0
    for faction_id, profile in list(factions.profiles.items()):
        if profile.kind not in ROBBER_KINDS or profile.chartered_by_entity_id is not None or held(faction_id):
            continue
        realm = realms.realm_of(profile.home_entity_id)
        if realm is None or not (profile.outlawed or profile.kind in SUPPRESS_FACTION_KINDS):
            continue
        if not ctx.rng(f"suppress.{faction_id}.{ctx.epoch}").chance(table.suppress_chance):
            continue
        band = factions.entities[faction_id]
        skill = await best_skill(ctx, realm, OfficePower.COMMAND)
        shift_stat(band, "strength", -round_half_up(table.suppress_strength * (1 + skill)), ctx.rules.society.default_stat)
        log(ctx, faction_id, FactionActionKind.SUPPRESSED, target=realm.entity.id)
        if (stat(band, "strength") or 0) <= table.destroy_strength:
            await retire_in(ctx, band, f"broken by the soldiers of {realm.entity.name}", close_bonds=True)
            await record_incident(
                ctx,
                "faction.suppressed",
                roles={IncidentRole.ACTOR: realm.entity.id, IncidentRole.TARGET: band.id},
                facts={
                    "command_skill": skill,
                },
            )
            broken += 1
    return broken


async def privateers(ctx: TickContext, factions: FactionBook, realms: RealmBook) -> int:
    table = ctx.rules.banditry
    struck = 0
    for faction_id, profile in factions.profiles.items():
        if profile.chartered_by_entity_id is None or profile.kind not in ROBBER_KINDS:
            continue
        lord = realms.realms.get(profile.chartered_by_entity_id)
        core = lord.profile.core_entity_id if lord is not None else None
        if core is None or held(faction_id):
            continue
        for item in await ongoing_wars(ctx.session, core):
            enemy_id = item.foe_id
            enemy = await living_entity(ctx.session, enemy_id)
            if enemy is None or held(enemy.id):
                continue
            shift_stat(enemy, "prosperity", -ctx.rules.banditry.raid_prosperity, ctx.rules.society.default_stat)
            await change_relation(
                ctx, enemy.id, core, -table.privateer_relation, MemoryKind.FOUGHT_US, note=f"the privateers of {factions.entities[faction_id].name}"
            )
            profile.treasury += table.raid_loot
            log(ctx, faction_id, FactionActionKind.RAID, target=enemy.id, amount=table.raid_loot, note="by letter of marque")
            struck += 1
    return struck


async def hire(ctx: TickContext, factions: FactionBook, realms: RealmBook) -> int:
    table = ctx.rules.mercenaries
    hired = 0
    idle = ctx.rng("hire.order").shuffled(
        [
            profile
            for profile in factions.profiles.values()
            if profile.kind is FactionKind.MERCENARY_COMPANY and profile.employer_entity_id is None and not held(profile.faction_entity_id)
        ]
    )
    for realm in realms.realms.values():
        core = realm.profile.core_entity_id
        asked = max(idle[0].pay, table.pay * max(1, len(factions.members[idle[0].faction_entity_id]))) if idle else table.pay
        if not idle or core is None or held(realm.entity.id, core) or not await ongoing_wars(ctx.session, core) or realm.profile.treasury < asked:
            continue
        if not ctx.rng(f"hire.{realm.entity.id}.{ctx.epoch}").chance(table.hire_chance):
            continue
        company = idle.pop(0)
        await contract(ctx, factions, company, realm, pay=asked, epochs=table.contract_epochs)
        hired += 1
    return hired


async def contract(ctx: TickContext, factions: FactionBook, company: FactionProfileRow, realm: Realm, *, pay: int, epochs: int) -> int:
    core = realm.profile.core_entity_id or realm.entity.id
    treaty = await sign(
        ctx,
        TreatyKind.CONDOTTA,
        [(core, PartyRole.SIGNATORY), (company.faction_entity_id, PartyRole.SIGNATORY)],
        clauses=[
            Clause(ClauseKind.CALL_TO_ARMS, company.faction_entity_id, core),
            Clause(ClauseKind.TRIBUTE, core, company.faction_entity_id, {"amount": pay}),
        ],
        until=ctx.epoch + epochs,
        witnessed=False,
    )
    company.employer_entity_id = realm.entity.id
    company.contract_entity_id = treaty.id
    company.pay = pay
    company.unpaid_epochs = 0
    log(ctx, company.faction_entity_id, FactionActionKind.HIRED, target=realm.entity.id, amount=pay)
    await record_incident(
        ctx,
        "faction.hired",
        roles={IncidentRole.BUYER: realm.entity.id, IncidentRole.SELLER: company.faction_entity_id, IncidentRole.INSTRUMENT: treaty.id},
        facts={"pay": pay},
    )
    return treaty.id


async def pay_companies(ctx: TickContext, factions: FactionBook, realms: RealmBook) -> dict[str, int]:
    table = ctx.rules.mercenaries
    counts = {"paid": 0, "unpaid": 0, "defected": 0, "bandits": 0}
    for profile in list(factions.profiles.values()):
        if profile.kind is not FactionKind.MERCENARY_COMPANY or profile.employer_entity_id is None or held(profile.faction_entity_id):
            continue
        treaty = await ctx.session.get(TreatyProfileRow, profile.contract_entity_id) if profile.contract_entity_id is not None else None
        employer = realms.realms.get(profile.employer_entity_id)
        if treaty is None or treaty.status is not TreatyStatus.IN_FORCE or employer is None:
            profile.employer_entity_id, profile.contract_entity_id = None, None
            continue
        if employer.profile.treasury >= profile.pay and move_amount(employer.profile, profile, "treasury", profile.pay):
            profile.unpaid_epochs = 0
            if "loyalty" not in profile.locked:
                profile.loyalty = clamp_int(profile.loyalty + table.loyalty_paid, 0, PERCENT)
            counts["paid"] += 1
            continue
        profile.unpaid_epochs += 1
        if "loyalty" not in profile.locked:
            profile.loyalty = clamp_int(profile.loyalty - table.loyalty_unpaid, 0, PERCENT)
        counts["unpaid"] += 1
        if profile.loyalty >= table.defect_loyalty:
            continue
        await defect(ctx, factions, profile, employer, treaty=treaty, counts=counts)
    return counts


async def defect(
    ctx: TickContext, factions: FactionBook, profile: FactionProfileRow, employer: Realm, *, treaty: TreatyProfileRow, counts: dict[str, int]
) -> None:
    table = ctx.rules.mercenaries
    company = factions.entities[profile.faction_entity_id]
    await breach(ctx, treaty, company.id, clause=None, reason=TreatyBreach.COMPANY_UNPAID)
    profile.employer_entity_id, profile.contract_entity_id = None, None
    core = employer.profile.core_entity_id
    wars = await ongoing_wars(ctx.session, core) if core is not None else []
    if wars and not ctx.rng(f"turncoat.{company.id}.{ctx.epoch}").chance(table.banditry_chance):
        item = wars[0]
        enemy = item.foe_id
        side = await ctx.session.scalar(select(WarSideRow.side).where(WarSideRow.war_id == item.war.id, WarSideRow.entity_id == enemy).limit(1))
        if side is not None and await ctx.session.get(WarSideRow, (item.war.id, company.id)) is None:
            ctx.session.add(new_side(ctx, item.war.id, company.id, side))
        log(ctx, company.id, FactionActionKind.DEFECTED, target=enemy, note="changed sides")
        await record_incident(
            ctx,
            "faction.turncoat",
            roles={
                IncidentRole.ACTOR: company.id,
                IncidentRole.VICTIM: employer.entity.id,
                IncidentRole.ALLY: enemy,
            },
        )
        counts["defected"] += 1
        return
    profile.kind = FactionKind.BANDITS
    profile.outlawed = True
    log(ctx, company.id, FactionActionKind.DEFECTED, target=employer.entity.id, note="turned bandit")
    await record_incident(ctx, "faction.turned_bandit", roles={IncidentRole.ACTOR: company.id, IncidentRole.VICTIM: employer.entity.id})
    counts["bandits"] += 1


async def end_contract(ctx: TickContext, profile: FactionProfileRow) -> None:
    treaty = await ctx.session.get(TreatyProfileRow, profile.contract_entity_id) if profile.contract_entity_id is not None else None
    if treaty is not None and treaty.status is TreatyStatus.IN_FORCE:
        await end_treaty(ctx, treaty, TreatyStatus.FULFILLED, "the condotta was ended")
    profile.employer_entity_id, profile.contract_entity_id = None, None

from sqlalchemy import select

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.military import DuelContext
from aerona.domain.enums.war import WarEnding, WarSide, WarStatus
from aerona.engine.context import TickContext
from aerona.engine.lore.arms import wear_in_duel
from aerona.engine.military.alliance import betrayed_call
from aerona.engine.military.duels import bout, fighter
from aerona.engine.military.support import new_side
from aerona.engine.notes import note
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.subjects import protected_by
from aerona.engine.polity.treaties import allies_called, answer_call, champion_for
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat
from aerona.engine.records import death_path
from aerona.engine.services.war import war_event
from aerona.engine.services.war_resolution import end_war


def comrades(book: RealmBook, entity_id: int) -> list[int]:
    realm = book.realm_of(entity_id)
    found: list[int] = []
    if realm is not None:
        found.extend(member for member in realm.members if member != entity_id)
        protector = protected_by(book, realm)
        if protector is not None and protector.profile.core_entity_id is not None:
            found.append(protector.profile.core_entity_id)
        if realm.profile.core_entity_id == entity_id:
            for vassal in book.vassals.values():
                if vassal.overlord_entity_id == realm.entity.id:
                    vassal_realm = book.realms.get(vassal.vassal_entity_id)
                    if vassal_realm is not None and vassal_realm.profile.core_entity_id is not None:
                        found.append(vassal_realm.profile.core_entity_id)
    return found


async def join_wars(ctx: TickContext, book: RealmBook) -> int:
    joined = 0
    wars = await ctx.session.scalars(select(WarRow).where(WarRow.status == WarStatus.ONGOING).order_by(WarRow.id))
    for war in wars:
        sides = list(await ctx.session.scalars(select(WarSideRow).where(WarSideRow.war_id == war.id, WarSideRow.left_epoch.is_(None))))
        present = {row.entity_id for row in sides}
        event = await war_event(ctx.session, war)
        for row in list(sides):
            called = await allies_called(ctx, row.entity_id, row.side)
            for ally_id in [*comrades(book, row.entity_id), *called]:
                if ally_id in present:
                    continue
                ally = await living_entity(ctx.session, ally_id)
                if (
                    ally is None
                    or held(ally_id, row.entity_id)
                    or ally.status is not EntityStatus.CANON
                    or ally.entity_type not in {EntityType.PEOPLE, EntityType.SETTLEMENT}
                ):
                    continue
                if ally_id in called and not await answer_call(ctx, ally_id, row.entity_id):
                    await betrayed_call(ctx, ally_id, row.entity_id)
                    continue
                ctx.session.add(new_side(ctx, war.id, ally_id, row.side))
                present.add(ally_id)
                await BondRepository(ctx.session).connect(
                    BondDraft(ally_id, event.id, BondKind.PARTY_TO, ctx.epoch, "joined the war", role=BondRole.SIDE, war_id=war.id)
                )
                joined += 1
    return joined


async def champion(ctx: TickContext, side: int) -> EntityRow | None:
    fighters = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [side]))
    )
    return max(fighters, key=lambda mortal: ((stat(mortal, "strength") or 0) + (stat(mortal, "agility") or 0), -mortal.id), default=None)


async def champions(ctx: TickContext) -> int:
    settled = 0
    wars = await ctx.session.scalars(select(WarRow).where(WarRow.status == WarStatus.ONGOING, WarRow.started_epoch >= ctx.epoch - 1))
    for war in list(wars):
        sides = {row.side: row.entity_id for row in await ctx.session.scalars(select(WarSideRow).where(WarSideRow.war_id == war.id))}
        attacker, defender = sides.get(WarSide.ATTACKER), sides.get(WarSide.DEFENDER)
        if attacker is None or defender is None or not await champion_for(ctx, attacker, defender):
            continue
        first, second = await champion(ctx, attacker), await champion(ctx, defender)
        if first is None or second is None:
            continue
        result = bout(ctx.rules, ctx.rng(f"champions.{war.id}"), await fighter(ctx, first, second), await fighter(ctx, second, first), DuelContext.CHAMPION)
        await wear_in_duel(ctx, first.id, result.exchanges)
        await wear_in_duel(ctx, second.id, result.exchanges)
        hero = result.winner.entity
        victor, loser = (attacker, defender) if hero.id == first.id else (defender, attacker)
        if result.killed:
            await death_path(ctx, result.loser.entity, f"fell as champion against {hero.name}", hero.id, "duel of champions", forced=True, harm=HarmCause.DUEL)
        await end_war(ctx, war, WarEnding.VICTORY, victor_id=victor, loser_id=loser, reason=f"{hero.name} won the duel of champions")
        await note(
            ctx, f"The war was decided by champions: {hero.name} won it.", key="treaty.champions", ids=[hero.id, victor, loser], kind=ChronicleKind.DIPLOMACY
        )
        settled += 1
    return settled

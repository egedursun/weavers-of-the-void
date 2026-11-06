from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.bond_texts import BARGAINED, CHOSEN_HEIR, CRAVES, HARVESTED, HIS_REMAINS, SACRED_TO
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.foreign_gods import ForeignGodRow, GodConflictRow, OuterBargainRow
from aerona.db.tables.lifecycle import DesignatedHeirRow
from aerona.db.tables.routes import JourneyRow
from aerona.db.tables.society import AddictionRow, ArchiveHoldingRow, ResurrectionOrderRow, ReverenceRow, SoulRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import ArmyRow, BattleRow, HeroQuestRow, WarRow
from aerona.domain.enums.bond import VISIBLE_BOND_STATES, BondKind, BondRole
from aerona.domain.enums.entity import LIVING_STATUSES
from aerona.services.integrity.pair_index import PairIndex

DIED_THERE = "died there"
PARENT_TONGUE = "its parent tongue"
FACTION_WITHIN = "a faction within it"
PRODUCED = "produced"
CREATED = "created"
COMMANDS_IT = "commands it"
ITS_ARMY = "its army"
FOUGHT_IN = "fought in the war"
WON_BATTLE = "won the battle"
LOST_BATTLE = "lost the battle"
BATTLE_OF = "a battle of the war"
WON_WAR = "won the war"
INCITED = "incited it"
DUELED = "dueled"
REVERES = "reveres this god"
AWAITS_RETURN = "awaits their return"
SOUL_DESCENDED = "its soul descended there"
ITS_SOUL = "the soul it was"
BOUND_HERE = "bound here"
KEPT_IN_ARCHIVE = "kept in its archive"
READ_IN_ARCHIVE = "read it in the archive"
TRAVELLED_ABOARD = "travelled aboard"
FOUNDED_ON_VOYAGE = "founded on the voyage"
ON_A_QUEST = "on a quest"
FATHER = "their creator"
HIS_ANCHOR = "their anchor"
FOUGHT_GOD = "fought it"

Link = Callable[..., Awaitable[bool]]


@dataclass
class StructuralCounters:
    added: int = 0


class StructuralLinks:
    def __init__(self, session: AsyncSession, single: Link, index: PairIndex) -> None:
        self.session = session
        self.single = single
        self.index = index
        self.counters = StructuralCounters()
        self.nodes: set[int] = set()

    async def _load_nodes(self) -> None:
        living = select(EntityRow.id).where(EntityRow.status.in_(list(LIVING_STATUSES)), EntityRow.pending_name.is_(False))
        self.nodes = set(await self.session.scalars(living))
        self.nodes |= set(await self.session.scalars(select(SonRow.id)))
        self.nodes |= set(await self.session.scalars(select(ForeignGodRow.id)))
        creator = await CosmosRepository(self.session).creator()
        if creator is not None:
            self.nodes.add(creator.id)

    def _kind_between(self, first: int, second: int, kind: BondKind) -> bool:
        return self.index.kind_between(first, second, kind)

    def _any_between(self, first: int, second: int) -> bool:
        return self.index.visible_between(first, second)

    async def link(
        self,
        source: int | None,
        target: int | None,
        kind: BondKind,
        description: str,
        *,
        role: BondRole | None = None,
        epoch: int | None = None,
        only_if_unlinked: bool = False,
    ) -> None:
        if source is None or target is None or source == target or source not in self.nodes or target not in self.nodes:
            return
        if only_if_unlinked and self._any_between(source, target):
            return
        if self._kind_between(source, target, kind):
            return
        self.counters.added += await self.single(source, target, kind, description, epoch=epoch, role=role)

    async def run(self) -> int:
        await self._load_nodes()
        await self.records()
        await self.languages()
        await self.warfare()
        await self.society()
        await self.travel()
        await self.gods()
        return self.counters.added

    async def records(self) -> None:
        statement = select(EntityRow).where(EntityRow.status.in_(list(LIVING_STATUSES)), EntityRow.pending_name.is_(False))
        for entity in list(await self.session.scalars(statement)):
            if entity.death_event_entity_id is not None:
                await self.link(entity.death_event_entity_id, entity.id, BondKind.CAUSED, DIED_THERE, epoch=entity.end_epoch)
            if entity.affiliated_entity_id is not None:
                await self.link(entity.id, entity.affiliated_entity_id, BondKind.PART_OF, FACTION_WITHIN)
            if entity.sacred_to_son_id is not None:
                await self.link(entity.id, entity.sacred_to_son_id, BondKind.RELATED, SACRED_TO)
            if entity.maker_entity_id is not None:
                await self.link(entity.maker_entity_id, entity.id, BondKind.PRODUCED, PRODUCED, epoch=entity.birth_epoch, only_if_unlinked=True)
            elif entity.creator_son_id is not None:
                await self.link(entity.creator_son_id, entity.id, BondKind.PRODUCED, CREATED, epoch=entity.birth_epoch, only_if_unlinked=True)

    async def languages(self) -> None:
        for profile in await self.session.scalars(select(LanguageProfileRow).where(LanguageProfileRow.parent_language_id.is_not(None))):
            await self.link(profile.entity_id, profile.parent_language_id, BondKind.DESCENDS_FROM, PARENT_TONGUE)

    async def warfare(self) -> None:
        events = {war.id: war for war in await self.session.scalars(select(WarRow))}
        for war in events.values():
            await self.link(war.victor_entity_id, war.loser_entity_id, BondKind.BEAT, WON_WAR)
            await self.link(war.incited_by_son_id, war.event_entity_id, BondKind.CAUSED, INCITED)
            if war.event_entity_id is not None:
                event = await self.session.get(EntityRow, war.event_entity_id)
                if event is not None:
                    rivals = select(BondRow).where(
                        BondRow.kind == BondKind.RIVAL, BondRow.description == event.name, BondRow.state.in_(list(VISIBLE_BOND_STATES))
                    )
                    for rival in await self.session.scalars(rivals):
                        for hero in (rival.source_node_id, rival.target_node_id):
                            await self.link(event.id, hero, BondKind.PARTY_TO, DUELED, role=BondRole.DUELED)
        for army in await self.session.scalars(select(ArmyRow)):
            await self.link(army.commander_entity_id, army.entity_id, BondKind.COMMANDS, COMMANDS_IT)
            await self.link(army.entity_id, army.owner_entity_id, BondKind.PART_OF, ITS_ARMY)
            army_war = events.get(army.war_id) if army.war_id is not None else None
            if army_war is not None:
                await self.link(army.entity_id, army_war.event_entity_id, BondKind.PARTY_TO, FOUGHT_IN, role=BondRole.SIDE)
        for battle in await self.session.scalars(select(BattleRow)):
            await self.link(battle.winner_entity_id, battle.loser_entity_id, BondKind.BEAT, WON_BATTLE, epoch=battle.epoch)
            if battle.record_entity_id is None:
                continue
            battle_war = events.get(battle.war_id)
            if battle_war is not None:
                await self.link(battle.record_entity_id, battle_war.event_entity_id, BondKind.PART_OF, BATTLE_OF, epoch=battle.epoch)
            await self.link(battle.winner_entity_id, battle.record_entity_id, BondKind.PARTY_TO, WON_BATTLE, role=BondRole.VICTOR, epoch=battle.epoch)
            await self.link(battle.loser_entity_id, battle.record_entity_id, BondKind.PARTY_TO, LOST_BATTLE, role=BondRole.LOSER, epoch=battle.epoch)
        for quest in await self.session.scalars(select(HeroQuestRow)):
            await self.link(quest.hero_entity_id, quest.target_node_id, BondKind.PURSUES, ON_A_QUEST, epoch=quest.started_epoch)

    async def society(self) -> None:
        for heir in await self.session.scalars(select(DesignatedHeirRow)):
            await self.link(heir.ruler_entity_id, heir.heir_entity_id, BondKind.RELATED, CHOSEN_HEIR, epoch=heir.epoch)
        for reverence in await self.session.scalars(select(ReverenceRow)):
            await self.link(reverence.entity_id, reverence.god_node_id, BondKind.WORSHIPS, REVERES, epoch=reverence.since_epoch)
        for order in await self.session.scalars(select(ResurrectionOrderRow)):
            await self.link(order.cult_entity_id, order.son_id, BondKind.WORSHIPS, AWAITS_RETURN)
        for soul in await self.session.scalars(select(SoulRow)):
            await self.link(soul.mortal_entity_id, soul.realm_entity_id, BondKind.SOUL_DESCENDED_TO, SOUL_DESCENDED, epoch=soul.descended_epoch)
            await self.link(soul.spirit_entity_id, soul.mortal_entity_id, BondKind.DESCENDS_FROM, ITS_SOUL, epoch=soul.descended_epoch)
            await self.link(soul.spirit_entity_id, soul.bound_to_entity_id, BondKind.INSIDE, BOUND_HERE, role=BondRole.SPIRIT_BINDING)
            await self.link(soul.harvested_by_entity_id, soul.spirit_entity_id, BondKind.RELATED, HARVESTED)
        for holding in await self.session.scalars(select(ArchiveHoldingRow)):
            await self.link(holding.archive_entity_id, holding.knowledge_entity_id, BondKind.SOURCE_OF, KEPT_IN_ARCHIVE, epoch=holding.epoch)
            await self.link(holding.reader_entity_id, holding.knowledge_entity_id, BondKind.KNOWS, READ_IN_ARCHIVE, epoch=holding.epoch)
        for addiction in await self.session.scalars(select(AddictionRow).where(AddictionRow.addicted_since_epoch.is_not(None))):
            await self.link(addiction.community_entity_id, addiction.resource_entity_id, BondKind.RELATED, CRAVES, epoch=addiction.addicted_since_epoch)

    async def travel(self) -> None:
        for journey in await self.session.scalars(select(JourneyRow)):
            await self.link(journey.traveller_entity_id, journey.vehicle_entity_id, BondKind.PASSENGER_OF, TRAVELLED_ABOARD, epoch=journey.start_epoch)
            await self.link(journey.traveller_entity_id, journey.result_entity_id, BondKind.PRODUCED, FOUNDED_ON_VOYAGE, epoch=journey.end_epoch)

    async def gods(self) -> None:
        for son in await self.session.scalars(select(SonRow)):
            await self.link(son.id, son.parent_son_id, BondKind.DESCENDS_FROM, FATHER)
            await self.link(son.id, son.co_parent_son_id, BondKind.DESCENDS_FROM, FATHER)
            await self.link(son.id, son.anchor_entity_id, BondKind.LIVES_IN, HIS_ANCHOR)
            await self.link(son.corpse_entity_id, son.id, BondKind.RELATED, HIS_REMAINS)
        for bargain in await self.session.scalars(select(OuterBargainRow)):
            await self.link(bargain.son_id, bargain.outer_entity_id, BondKind.RELATED, BARGAINED, epoch=bargain.epoch)
        for conflict in await self.session.scalars(select(GodConflictRow)):
            await self.link(conflict.attacker_node_id, conflict.defender_node_id, BondKind.ENEMY, FOUGHT_GOD, epoch=conflict.epoch)

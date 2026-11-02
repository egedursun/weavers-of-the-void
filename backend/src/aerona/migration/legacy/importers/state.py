from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmic_state import AddictionImmunityRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import OuterBargainRow
from aerona.db.tables.society import AddictionRow, ResurrectionOrderRow, ReverenceRow
from aerona.db.tables.warfare import ArmyRow, BattleRow, CaptiveRow, SiegeRow, TributeRow, WarRow, WarSideRow
from aerona.domain.enums.bond import BondKind, BondRole, BondState
from aerona.domain.enums.entity import COMMUNITY_TYPES, ENDED_STATUSES, EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.war import BattleOutcome, CaptiveStatus, SiegeStatus, TributeStatus, WarCause, WarEnding, WarSide, WarStatus
from aerona.migration.legacy.context import MigrationContext
from aerona.migration.legacy.idmap import LegacyKind
from aerona.migration.legacy.importers.cosmos import DEFAULTED
from aerona.migration.legacy.tags import TagReading

SIDES = (WarSide.ATTACKER, WarSide.DEFENDER)
WAR_ASSUMED = "war assumption"
EPOCH_ASSUMED = "epoch assumed"


class StateConverter:
    def __init__(self, context: MigrationContext) -> None:
        self.context = context
        self.report = context.report
        self.reverse = context.ids.reverse_entities()
        self.wars_by_event: dict[int, WarRow] = {}
        self.bonds: list[BondRow] = []

    def reading(self, entity: EntityRow) -> TagReading:
        return self.context.readings.get(self.reverse.get(entity.id, 0)) or TagReading()

    def mapped(self, legacy_ids: list[int]) -> list[int]:
        found: list[int] = []
        for legacy in legacy_ids:
            new_id = self.context.entity(legacy)
            if new_id is not None and new_id not in found:
                found.append(new_id)
        return found

    async def run(self) -> None:
        await self.context.flush()
        self.bonds = list(await self.context.session.scalars(select(BondRow).order_by(BondRow.id)))
        entities = sorted(self.context.rows.values(), key=lambda entity: entity.id)
        for entity in entities:
            if entity.entity_type is EntityType.EVENT and entity.engine_kind is EngineKind.WAR:
                await self.war(entity)
        await self.context.session.flush()
        self.link_war_bonds()
        await self.battles(entities)
        for entity in entities:
            if entity.entity_type is EntityType.ARMY:
                self.army(entity)
        self.tributes()
        self.captives(entities)
        for entity in entities:
            self.faith_and_bonds(entity)
        await self.context.flush()

    def side_bonds(self, event: EntityRow) -> list[BondRow]:
        return [bond for bond in self.bonds if bond.source_node_id == event.id and bond.kind is BondKind.PARTY_TO]

    async def war(self, event: EntityRow) -> None:
        reading = self.reading(event)
        reference = f"entity:{self.reverse.get(event.id)}"
        bonds = self.side_bonds(event)
        sides = self.mapped(reading.sides)
        for bond in bonds:
            if bond.role is BondRole.SIDE and bond.target_node_id not in sides and self.context.facts(bond.target_node_id) is not None:
                sides.append(bond.target_node_id)
        if len(sides) < len(SIDES):
            self.report.place_failed("war", reference, "a war event without two known sides stays a lore event")
            return
        stats = self.context.war_stats.get(self.reverse.get(event.id, 0), {})
        ongoing = reading.war_ongoing and event.status is EntityStatus.CANON
        start = stats.get("war_start", event.birth_epoch)
        ending = reading.outcome
        if not ongoing and ending is None:
            ending = WarEnding.PEACE
            self.report.warn(WAR_ASSUMED, reference, "an ended war without a recorded outcome is read as peace")
        end = None
        if not ongoing:
            end = stats.get("war_end") or event.end_epoch or max(start, self.context.epoch - 1)
            end = max(start, end)
        victor = next((bond.target_node_id for bond in bonds if bond.role is BondRole.VICTOR), None)
        loser = next((bond.target_node_id for bond in bonds if bond.role is BondRole.LOSER and bond.target_node_id != victor), None)
        severity = getattr(event.stats, "severity", None)
        war = WarRow(
            event_entity_id=event.id,
            world_id=event.world_id,
            status=WarStatus.ONGOING if ongoing else WarStatus.ENDED,
            cause=WarCause.HOSTILITY,
            started_epoch=start,
            ended_epoch=end,
            last_clash_epoch=stats.get("war_last_clash"),
            battles=max(0, stats.get("war_battles", 0)),
            score=stats.get("war_score", 0),
            violence=severity,
            ending=None if ongoing else ending,
            victor_entity_id=victor,
            loser_entity_id=loser,
        )
        self.context.session.add(war)
        await self.context.session.flush()
        self.wars_by_event[event.id] = war
        for index, entity_id in enumerate(sides):
            side = SIDES[min(index, len(SIDES) - 1)]
            if index >= len(SIDES):
                self.report.warn(WAR_ASSUMED, reference, f"extra side {entity_id} joined the defenders")
            self.context.add(WarSideRow(war_id=war.id, entity_id=entity_id, side=side, joined_epoch=start, left_epoch=end))
        self.report.convert("wars_ongoing" if ongoing else "wars_ended")
        self.report.convert("war_sides", len(sides))

    def bond_target(self, event: EntityRow, kind: BondKind, role: BondRole | None = None) -> int | None:
        return next(
            (bond.target_node_id for bond in self.bonds if bond.source_node_id == event.id and bond.kind is kind and (role is None or bond.role is role)),
            None,
        )

    async def battles(self, entities: list[EntityRow]) -> None:
        clashes = [entity for entity in entities if entity.entity_type is EntityType.EVENT and entity.engine_kind in (EngineKind.BATTLE, EngineKind.SIEGE)]
        clashes.sort(key=lambda entity: (entity.birth_epoch, entity.id))
        sequence: dict[int, int] = {}
        for clash in clashes:
            reference = f"entity:{self.reverse.get(clash.id)}"
            war_event = self.bond_target(clash, BondKind.PART_OF)
            war = self.wars_by_event.get(war_event) if war_event is not None else None
            winner = self.bond_target(clash, BondKind.PARTY_TO, BondRole.VICTOR)
            loser = self.bond_target(clash, BondKind.PARTY_TO, BondRole.LOSER)
            if war is None or winner is None or loser is None or winner == loser:
                self.report.place_failed("battle", reference, "a battle without its war, winner and loser stays a lore event")
                continue
            place = self.bond_target(clash, BondKind.INSIDE)
            sequence[war.id] = sequence.get(war.id, 0) + 1
            siege: SiegeRow | None = None
            outcome = BattleOutcome.FIELD_VICTORY
            if clash.engine_kind is EngineKind.SIEGE:
                besieged = place if place in (winner, loser) else loser
                besieger = loser if besieged == winner else winner
                repulsed = besieged == winner
                siege = SiegeRow(
                    war_id=war.id,
                    besieged_entity_id=besieged,
                    besieger_entity_id=besieger,
                    status=SiegeStatus.REPULSED if repulsed else SiegeStatus.BREACHED,
                    started_epoch=clash.birth_epoch,
                    ended_epoch=clash.birth_epoch,
                    rounds=1,
                )
                self.context.session.add(siege)
                await self.context.session.flush()
                outcome = BattleOutcome.SIEGE_REPULSED if repulsed else BattleOutcome.SIEGE_BREACHED
                self.report.convert("sieges")
            self.context.session.add(
                BattleRow(
                    war_id=war.id,
                    epoch=clash.birth_epoch,
                    sequence=sequence[war.id],
                    record_entity_id=clash.id,
                    place_entity_id=place,
                    winner_entity_id=winner,
                    loser_entity_id=loser,
                    outcome=outcome,
                    gap=0.0,
                    siege_id=siege.id if siege is not None else None,
                )
            )
            self.report.convert("battles")

    def link_war_bonds(self) -> None:
        for bond in self.bonds:
            war = self.wars_by_event.get(bond.source_node_id) if bond.kind is BondKind.PARTY_TO else None
            if war is None and bond.kind is BondKind.PART_OF:
                war = self.wars_by_event.get(bond.target_node_id)
            if war is not None:
                bond.war_id = war.id
                self.report.convert("war_bonds_linked")

    def army(self, army: EntityRow) -> None:
        reading = self.reading(army)
        reference = f"entity:{self.reverse.get(army.id)}"
        owners = self.mapped(reading.sides)
        if not owners:
            owners = [bond.target_node_id for bond in self.bonds if bond.source_node_id == army.id and bond.kind is BondKind.PROTECTS]
        owner = next((candidate for candidate in owners if (facts := self.context.facts(candidate)) is not None and facts.entity_type in COMMUNITY_TYPES), None)
        if owner is None:
            self.report.place_failed("army", reference, "no owning community")
            return
        war = None
        for legacy_war in reading.wars:
            event = self.context.entity(legacy_war)
            war = self.wars_by_event.get(event) if event is not None else None
            if war is not None:
                break
        commander = next(
            (
                bond.source_node_id
                for bond in self.bonds
                if bond.target_node_id == army.id and bond.kind is BondKind.COMMANDS and bond.state is BondState.ACTIVE
            ),
            None,
        )
        self.context.add(
            ArmyRow(
                entity_id=army.id,
                war_id=war.id if war is not None and not reading.standby else None,
                owner_entity_id=owner,
                commander_entity_id=commander,
                raised_epoch=army.birth_epoch,
                disbanded_epoch=army.end_epoch if army.status in ENDED_STATUSES else None,
            )
        )
        self.report.convert("armies")

    def tributes(self) -> None:
        for bond in self.bonds:
            if bond.kind is not BondKind.PAYS_TRIBUTE:
                continue
            if self.context.facts(bond.source_node_id) is None or self.context.facts(bond.target_node_id) is None:
                self.report.place_failed("tribute", f"bond:{bond.id}", "payer or receiver is not a record")
                continue
            active = bond.state is BondState.ACTIVE
            self.context.add(
                TributeRow(
                    payer_entity_id=bond.source_node_id,
                    receiver_entity_id=bond.target_node_id,
                    bond_id=bond.id,
                    status=TributeStatus.ACTIVE if active else TributeStatus.ENDED,
                    since_epoch=bond.epoch,
                )
            )
            self.report.convert("tributes_active" if active else "tributes_ended")

    def captives(self, entities: list[EntityRow]) -> None:
        wars_by_name = {self.context.rows[event].name: war for event, war in self.wars_by_event.items()}
        held: set[int] = set()
        for bond in self.bonds:
            if bond.kind is not BondKind.HOLDS_CAPTIVE:
                continue
            if self.context.facts(bond.source_node_id) is None or self.context.facts(bond.target_node_id) is None:
                self.report.place_failed("captive", f"bond:{bond.id}", "captor or captive is not a record")
                continue
            active = bond.state is BondState.ACTIVE
            war = wars_by_name.get((bond.description or "").strip())
            self.context.add(
                CaptiveRow(
                    captive_entity_id=bond.target_node_id,
                    captor_entity_id=bond.source_node_id,
                    war_id=war.id if war is not None else None,
                    bond_id=bond.id,
                    status=CaptiveStatus.HELD if active else CaptiveStatus.RELEASED,
                    taken_epoch=bond.epoch,
                )
            )
            if active:
                held.add(bond.target_node_id)
            self.report.convert("captives_held" if active else "captives_released")
        for entity in entities:
            if self.reading(entity).captive and entity.id not in held:
                self.report.place_failed("captive", f"entity:{self.reverse.get(entity.id)}", "tagged captive but no captor bond")

    def patron(self, entity: EntityRow) -> int | None:
        return next(
            (
                bond.target_node_id
                for bond in self.bonds
                if bond.source_node_id == entity.id and bond.kind is BondKind.WORSHIPS and bond.state is BondState.ACTIVE
            ),
            None,
        )

    def faith_and_bonds(self, entity: EntityRow) -> None:
        reading = self.reading(entity)
        reference = f"entity:{self.reverse.get(entity.id)}"
        patron = self.patron(entity) if reading.syncretic else None
        for legacy_son in reading.syncretic:
            son = self.context.son(legacy_son)
            if son is None:
                self.report.place_failed("syncretism", reference, f"son {legacy_son} is missing")
                continue
            if son == patron:
                self.report.convert("syncretism_to_own_patron_dropped")
                continue
            self.context.add(ReverenceRow(entity_id=entity.id, god_node_id=son, since_epoch=self.context.epoch))
            self.report.convert("reverences")
            self.report.warn(EPOCH_ASSUMED, reference, "syncretic reverence dated to the migration epoch")
        for legacy_god in reading.old_gods:
            god = self.context.ids.get(LegacyKind.FOREIGN_GOD, legacy_god)
            if god is None:
                self.report.place_failed("syncretism", reference, f"old god {legacy_god} is missing")
                continue
            self.context.add(ReverenceRow(entity_id=entity.id, god_node_id=god, since_epoch=self.context.epoch))
            self.report.convert("old_god_reverences")
        self.addictions(entity, reading, reference)
        self.orders(entity, reading, reference)

    def addictions(self, entity: EntityRow, reading: TagReading, reference: str) -> None:
        for legacy_resource in reading.addicted:
            resource = self.context.entity(legacy_resource)
            if resource is None:
                self.report.place_failed("addiction", reference, f"resource {legacy_resource} is missing")
                continue
            self.context.add(AddictionRow(community_entity_id=entity.id, resource_entity_id=resource, addicted_since_epoch=self.context.epoch))
            self.report.convert("addictions")
        for legacy_resource, recovered in reading.purified:
            resource = self.context.entity(legacy_resource)
            if resource is None:
                self.report.place_failed("purification", reference, f"resource {legacy_resource} is missing")
                continue
            self.context.add(AddictionImmunityRow(community_entity_id=entity.id, resource_entity_id=resource, recovered_epoch=max(0, recovered)))
            self.report.convert("addiction_immunities")

    def orders(self, entity: EntityRow, reading: TagReading, reference: str) -> None:
        if reading.resurrection_son is not None:
            son = self.context.son(reading.resurrection_son)
            if son is None or entity.entity_type is not EntityType.CULT:
                self.report.place_failed("resurrection order", reference, "the cult or its son is missing")
            else:
                done = self.context.epoch if EntityFlag.RESURRECTION_COMPLETE in reading.flags else None
                self.context.add(ResurrectionOrderRow(cult_entity_id=entity.id, son_id=son, completed_epoch=done))
                if entity.engine_kind is None:
                    entity.engine_kind = EngineKind.RESURRECTION_ORDER
                self.report.convert("resurrection_orders")
        for legacy_son in reading.bargains:
            son = self.context.son(legacy_son)
            if son is None or entity.entity_type is not EntityType.OUTER_BEING:
                self.report.place_failed("outer bargain", reference, f"son {legacy_son} or the outer being is missing")
                continue
            self.context.add(OuterBargainRow(outer_entity_id=entity.id, son_id=son, epoch=entity.birth_epoch))
            self.report.warn(DEFAULTED, reference, "outer bargain dated to the outer being's birth")
            self.report.convert("outer_bargains")


async def convert_state(context: MigrationContext) -> None:
    await StateConverter(context).run()

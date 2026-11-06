from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.demography import LabourRow
from aerona.db.tables.economy import ResourceProfileRow, ResourceWorkerRow, WorkshopDesignRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.industry import CommunityIndustryRow, CommunityMethodRow, RegionPollutionRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.polity import TreatyClauseRow, TreatyPartyRow, TreatyProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.demography import Job
from aerona.domain.enums.economy import WorkshopKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, SOCIETY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.industry import ProcessKind
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.polity import ClauseKind, TreatyStatus
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.economy.materials import MaterialBook
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import canon

HOME_BONDS = (BondKind.LIVES_IN, BondKind.MEMBER_OF)


@dataclass
class EconomyBook:
    entities: dict[int, EntityRow]
    communities: list[EntityRow]
    societies: dict[int, CommunitySocietyRow]
    workshops: dict[int, dict[WorkshopKind, WorkshopRow]]
    profiles: dict[int, ResourceProfileRow]
    workers: dict[int, dict[int, ResourceWorkerRow]]
    owners: dict[int, list[int]]
    skills: dict[int, dict[SkillKind, int]]
    knowledge: KnowledgeMap
    ground: EnvironmentBook
    materials: MaterialBook
    affiliated: dict[int, int] = field(default_factory=dict)
    labour: dict[int, dict[Job, LabourRow]] = field(default_factory=dict)
    waived: set[frozenset[int]] = field(default_factory=set)
    blockaded: set[int] = field(default_factory=set)
    techniques: dict[int, set[Technique]] = field(default_factory=dict)
    designs: dict[int, WorkshopDesignRow] = field(default_factory=dict)
    merchant_danger: dict[int, int] = field(default_factory=dict)
    robbers: frozenset[int] = frozenset()
    methods: dict[int, dict[ProcessKind, CommunityMethodRow]] = field(default_factory=dict)
    industry: dict[int, CommunityIndustryRow] = field(default_factory=dict)
    pollution: dict[int, RegionPollutionRow] = field(default_factory=dict)

    @classmethod
    async def load(cls, ctx: TickContext) -> "EconomyBook":
        session = ctx.session
        entities = {entity.id: entity for entity in await canon(session)}
        communities = sorted((entity for entity in entities.values() if entity.entity_type in SOCIETY_TYPES), key=lambda entity: entity.id)
        societies = {row.entity_id: row for row in await session.scalars(select(CommunitySocietyRow))}
        workshops: dict[int, dict[WorkshopKind, WorkshopRow]] = defaultdict(dict)
        for row in await session.scalars(select(WorkshopRow).order_by(WorkshopRow.id)):
            workshops[row.community_entity_id][row.kind] = row
        profiles = {row.resource_entity_id: row for row in await session.scalars(select(ResourceProfileRow))}
        workers: dict[int, dict[int, ResourceWorkerRow]] = defaultdict(dict)
        for worker in await session.scalars(select(ResourceWorkerRow)):
            workers[worker.resource_entity_id][worker.community_entity_id] = worker
        owners: dict[int, list[int]] = defaultdict(list)
        homes: dict[int, int] = {}
        statement = select(BondRow).where(BondRow.kind.in_([BondKind.OWNS, *HOME_BONDS]), BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
        for bond in await session.scalars(statement):
            if bond.kind is BondKind.OWNS and bond.source_node_id in entities:
                owners[bond.target_node_id].append(bond.source_node_id)
            elif bond.kind in HOME_BONDS and bond.target_node_id in entities and entities[bond.target_node_id].entity_type in COMMUNITY_TYPES:
                homes.setdefault(bond.source_node_id, bond.target_node_id)
        book = cls(
            entities=entities,
            communities=communities,
            societies=societies,
            workshops=workshops,
            profiles=profiles,
            workers=workers,
            owners=owners,
            skills=defaultdict(dict),
            knowledge=await KnowledgeMap.load(session),
            ground=await EnvironmentBook.load(session, ctx.rules, ctx.epoch),
            materials=await MaterialBook.load(session),
        )
        for entity in entities.values():
            home = book.home_of(entity, homes)
            if home is not None:
                book.affiliated[entity.id] = home
        for skill in await session.scalars(select(SkillRow).where(SkillRow.subject_node_id.is_(None))):
            community = book.affiliated.get(skill.holder_node_id)
            if community is not None:
                held = book.skills[community]
                held[skill.skill] = max(held.get(skill.skill, 0), skill.level)
        for labour in await session.scalars(select(LabourRow)):
            book.labour.setdefault(labour.community_entity_id, {})[labour.job] = labour
        live = select(TreatyProfileRow.treaty_entity_id).where(TreatyProfileRow.status == TreatyStatus.IN_FORCE)
        waivers = select(TreatyClauseRow.treaty_entity_id).where(TreatyClauseRow.kind == ClauseKind.TOLLS_WAIVED, TreatyClauseRow.treaty_entity_id.in_(live))
        signers: dict[int, set[int]] = defaultdict(set)
        for party in await session.scalars(select(TreatyPartyRow).where(TreatyPartyRow.treaty_entity_id.in_(waivers))):
            signers[party.treaty_entity_id].add(party.party_node_id)
        book.waived = {frozenset(pair) for parties in signers.values() for pair in combinations(sorted(parties), 2)}
        for known in await session.scalars(select(HolderTechniqueRow)):
            book.techniques.setdefault(known.holder_entity_id, set()).add(known.technique)
        book.designs = {row.id: row for row in await session.scalars(select(WorkshopDesignRow).order_by(WorkshopDesignRow.id))}
        await book.load_industry(ctx)
        book.blockaded = set(await session.scalars(select(ArmyProfileRow.blockade_entity_id).where(ArmyProfileRow.blockade_entity_id.is_not(None))))
        return book

    async def load_industry(self, ctx: TickContext) -> None:
        for method in await ctx.session.scalars(select(CommunityMethodRow).order_by(CommunityMethodRow.id)):
            self.methods.setdefault(method.community_node_id, {})[method.process] = method
        self.industry = {row.community_node_id: row for row in await ctx.session.scalars(select(CommunityIndustryRow))}
        self.pollution = {row.region_node_id: row for row in await ctx.session.scalars(select(RegionPollutionRow))}

    def home_of(self, entity: EntityRow, homes: dict[int, int]) -> int | None:
        if entity.entity_type in SOCIETY_TYPES:
            return entity.id
        if entity.affiliated_entity_id is not None and entity.affiliated_entity_id in self.entities:
            target = self.entities[entity.affiliated_entity_id]
            if target.entity_type in SOCIETY_TYPES:
                return target.id
        location = self.entities.get(entity.location_id) if entity.location_id is not None else None
        if location is not None and location.entity_type in SOCIETY_TYPES:
            return location.id
        home = homes.get(entity.id)
        if home is not None and self.entities[home].entity_type in SOCIETY_TYPES:
            return home
        return None

    def lacks(self, community_id: int, technique: Technique) -> bool:
        held = self.techniques.get(community_id, set())
        return bool(held) and technique not in held

    def hands(self, community_id: int, *jobs: Job) -> int | None:
        rows = self.labour.get(community_id)
        if not rows:
            return None
        return sum(round_half_up(rows[job].workers * rows[job].output_pct / PERCENT) for job in jobs if job in rows)

    def community_of(self, entity_id: int) -> EntityRow | None:
        home = self.affiliated.get(entity_id)
        return self.entities.get(home) if home is not None else None

    def skill(self, community_id: int, skill: SkillKind) -> int:
        return self.skills.get(community_id, {}).get(skill, 0)

    def level(self, community_id: int, branch: KnowledgeBranch) -> int:
        return self.knowledge.level(community_id, branch)

    def levels(self, community_id: int) -> dict[KnowledgeBranch, int]:
        return {branch: self.knowledge.level(community_id, branch) for branch in self.knowledge.branches(community_id)}

    def workshop(self, community_id: int, kind: WorkshopKind) -> WorkshopRow | None:
        return self.workshops.get(community_id, {}).get(kind)

    def design_of(self, workshop: WorkshopRow | None) -> WorkshopDesignRow | None:
        return self.designs.get(workshop.design_id) if workshop is not None and workshop.design_id is not None else None

    def resources(self) -> list[EntityRow]:
        return sorted(
            (entity for entity in self.entities.values() if entity.entity_type is EntityType.RESOURCE and entity.status is EntityStatus.CANON),
            key=lambda entity: entity.id,
        )

    def temperature(self, entity_id: int) -> int:
        region = self.ground.region_of(entity_id)
        return region.temperature if region is not None else 0

    def magic_density(self, entity_id: int) -> int:
        region = self.ground.region_of(entity_id)
        return region.magic_density if region is not None else 0

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.realms import (
    BalanceSlice,
    BreachView,
    ClaimView,
    ClauseView,
    HeirloomView,
    HouseMemberView,
    HouseView,
    LawKindSpec,
    LawParamSpec,
    LawView,
    LoanView,
    MemberView,
    NamedNode,
    OathsView,
    OathView,
    OfficeView,
    PartyView,
    RealmLink,
    RealmView,
    ReputeView,
    SentenceView,
    TerritoryView,
    TreasuryLineView,
    TreatyBrief,
    TreatyView,
    VassalView,
    WhyPart,
)
from aerona.catalog.laws import LAW_PARAMS, law_effect
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.economy import LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.polity import (
    ClaimRow,
    HeirloomRow,
    HouseMemberRow,
    HouseProfileRow,
    MortalReputeRow,
    OathRow,
    OfficeRow,
    PolityMemberRow,
    PolityTreasuryRow,
    SentenceRow,
    TreatyBreachRow,
    TreatyClauseRow,
    TreatyPartyRow,
    TreatyProfileRow,
    VassalageRow,
)
from aerona.domain.enums.body import LASTING_INJURY_STATES
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.polity import LAW_AREAS
from aerona.engine.factions.balance import power_balance
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.laws import LawBook
from aerona.engine.polity.offices import powers_of, succession_line
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat

router = APIRouter(tags=["realms"])


async def names_of(session: AsyncSession, ids: set[int]) -> dict[int, str]:
    clean = {item for item in ids if item is not None}
    if not clean:
        return {}
    return {entity_id: name for entity_id, name in await session.execute(select(EntityRow.id, EntityRow.name).where(EntityRow.id.in_(list(clean))))}


def node(names: dict[int, str], entity_id: int | None) -> NamedNode | None:
    return NamedNode(id=entity_id, name=names.get(entity_id, "")) if entity_id is not None else None


def claim_view(row: ClaimRow, names: dict[int, str]) -> ClaimView:
    return ClaimView(
        id=row.id,
        claimant_id=row.claimant_entity_id,
        claimant=names.get(row.claimant_entity_id, ""),
        house_id=row.house_entity_id,
        polity_id=row.polity_entity_id,
        strength=row.strength,
        basis=row.basis,
        pressed=row.pressed,
        since_epoch=row.since_epoch,
        office=row.office,
        backer_id=row.backer_entity_id,
        locked=list(row.locked),
    )


def vassal_view(row: VassalageRow, names: dict[int, str]) -> VassalView:
    return VassalView(
        id=row.vassal_entity_id,
        name=names.get(row.vassal_entity_id, ""),
        overlord_id=row.overlord_entity_id,
        tribute_pct=row.tribute_pct,
        levy_pct=row.levy_pct,
        loyalty=row.loyalty,
        treaty_id=row.treaty_entity_id,
        locked=list(row.locked),
    )


@router.get("/entities/{entity_id}/realm", response_model=RealmLink)
async def realm_link(services: ServicesDep, entity_id: int = Path(ge=1)) -> RealmLink:
    async with reader(services) as session:
        entity = await session.get(EntityRow, entity_id)
        if entity is None:
            raise NotFoundError("No such record.")
        if entity.entity_type is EntityType.POLITY:
            return RealmLink(polity_id=entity.id)
        lookup = entity.location_id if entity.entity_type is EntityType.MORTAL else entity.id
        found = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == lookup).limit(1))
        return RealmLink(polity_id=found)


@router.get("/polities/{polity_id}", response_model=RealmView)
async def realm(services: ServicesDep, polity_id: int = Path(ge=1)) -> RealmView:
    async with reader(services) as session:
        cosmos = await CosmosRepository(session).require_cosmos()
        rules = rules_from_snapshot(cosmos.rules_snapshot)
        book = await RealmBook.load(session)
        found = book.realms.get(polity_id)
        if found is None:
            raise NotFoundError("No such realm.")
        laws = await LawBook.load(session)
        ctx = await manual_context(session, "realm_view", rules)
        line = await succession_line(ctx, found, laws)
        profile = found.profile
        law_ids = [*laws.by_node.get(polity_id, []), *(law for member in found.members for law in laws.by_node.get(member, []))]
        claims = list(await session.scalars(select(ClaimRow).where(ClaimRow.polity_entity_id == polity_id, ClaimRow.ended_epoch.is_(None))))
        ledger = list(
            await session.scalars(
                select(PolityTreasuryRow).where(PolityTreasuryRow.polity_entity_id == polity_id).order_by(PolityTreasuryRow.epoch, PolityTreasuryRow.id)
            )
        )
        cores = [profile.core_entity_id] if profile.core_entity_id is not None else []
        party_treaties = set(await session.scalars(select(TreatyPartyRow.treaty_entity_id).where(TreatyPartyRow.party_node_id.in_([polity_id, *cores]))))
        treaties = list(await session.scalars(select(TreatyProfileRow).where(TreatyProfileRow.treaty_entity_id.in_(list(party_treaties)))))
        overlord = await session.get(VassalageRow, polity_id)
        vassals = list(await session.scalars(select(VassalageRow).where(VassalageRow.overlord_entity_id == polity_id)))
        ids = {
            *found.members,
            *found.territory,
            *(office.holder_entity_id for office in found.offices if office.holder_entity_id),
            *(office.region_entity_id for office in found.offices if office.region_entity_id),
            *(item.id for item in line),
            *law_ids,
            *(row.claimant_entity_id for row in claims),
            *(row.treaty_entity_id for row in treaties),
            *(row.vassal_entity_id for row in vassals),
            *([overlord.overlord_entity_id] if overlord else []),
            *(item for item in (profile.core_entity_id, profile.capital_entity_id, profile.state_religion_id, found.ruler_id) if item),
        }
        loans = list(await session.scalars(select(LoanRow).where(LoanRow.borrower_entity_id == polity_id).order_by(LoanRow.id)))
        balance = await power_balance(ctx, found)
        sentences = list(
            await session.scalars(
                select(SentenceRow).where(SentenceRow.settlement_entity_id.in_(list(found.members) or [-1])).order_by(SentenceRow.epoch, SentenceRow.id)
            )
        )
        repute = await session.get(MortalReputeRow, found.ruler_id) if found.ruler_id is not None else None
        ids |= {*(row.lender_entity_id for row in loans), *balance, *(row.mortal_entity_id for row in sentences)}
        ids |= {office.target_entity_id for office in found.offices if office.target_entity_id}
        names = await names_of(session, ids)
        whole = sum(balance.values()) or 1
        kinds = {
            row.faction_entity_id: row.kind.value
            for row in await session.scalars(select(FactionProfileRow).where(FactionProfileRow.faction_entity_id.in_(list(balance) or [-1])))
        }
        return RealmView(
            tier_strain=profile.tier_strain,
            power_balance=[
                BalanceSlice(id=key, name=names.get(key, ""), kind=kinds.get(key, ""), share=round(value * 100 / whole))
                for key, value in sorted(balance.items())
            ],
            loans=[
                LoanView(
                    id=row.id,
                    lender_id=row.lender_entity_id,
                    lender=names.get(row.lender_entity_id, ""),
                    principal=row.principal,
                    interest_pct=row.interest_pct,
                    repaid=row.repaid,
                    due_epoch=row.due_epoch,
                    status=row.status.value,
                )
                for row in loans
            ],
            vassal_terms=[vassal_view(row, names) for row in vassals],
            overlord_terms=vassal_view(overlord, names) if overlord is not None else None,
            ruler_repute=ReputeView(mortal_id=repute.mortal_entity_id, honour=repute.honour, infamy=repute.infamy, locked=list(repute.locked))
            if repute is not None
            else None,
            sentences=[
                SentenceView(
                    id=row.id,
                    mortal_id=row.mortal_entity_id,
                    mortal=names.get(row.mortal_entity_id, ""),
                    settlement_id=row.settlement_entity_id,
                    crime=row.crime.value,
                    penalty=row.penalty,
                    epoch=row.epoch,
                )
                for row in sentences
            ],
            id=found.entity.id,
            name=found.entity.name,
            government=profile.government,
            decision_rule=profile.decision_rule,
            legitimacy=profile.legitimacy,
            stability=profile.stability,
            treasury=profile.treasury,
            debt=profile.debt,
            war_chest=profile.war_chest,
            administration=profile.administration,
            overextension=profile.overextension,
            war_weariness=profile.war_weariness,
            tier=profile.tier,
            standing=profile.standing,
            core=node(names, profile.core_entity_id),
            capital=node(names, profile.capital_entity_id),
            state_religion=node(names, profile.state_religion_id),
            ruler=node(names, found.ruler_id),
            patron_son_id=profile.patron_son_id,
            emblem=dict(profile.emblem),
            locked=list(profile.locked),
            members=[
                MemberView(
                    id=member_id,
                    name=names.get(member_id, ""),
                    entity_type=book.entities[member_id].entity_type,
                    autonomy=row.autonomy,
                    population=stat(book.entities[member_id], "population") or 0,
                    locked=list(row.locked),
                )
                for member_id, row in sorted(found.members.items())
                if member_id in book.entities
            ],
            territory=[
                TerritoryView(region_id=region, name=names.get(region, ""), control=row.control, province=row.province, locked=list(row.locked))
                for region, row in sorted(found.territory.items())
            ],
            offices=[
                OfficeView(
                    id=office.id,
                    kind=office.kind,
                    holder_id=office.holder_entity_id,
                    holder=names.get(office.holder_entity_id) if office.holder_entity_id else None,
                    region_id=office.region_entity_id,
                    region=names.get(office.region_entity_id) if office.region_entity_id else None,
                    since_epoch=office.since_epoch,
                    title=office.title,
                    powers=sorted(power.value for power in powers_of(office)),
                    target_id=office.target_entity_id,
                    target=names.get(office.target_entity_id) if office.target_entity_id else None,
                    locked=list(office.locked),
                )
                for office in found.offices
            ],
            why=[WhyPart(label=key, value=value) for key, value in profile.legitimacy_parts.items() if key != "usurper"],
            succession=[NamedNode(id=item.id, name=item.name) for item in line],
            laws=[
                LawView(
                    id=law_id,
                    name=names.get(law_id, ""),
                    kind=laws.profiles[law_id].kind,
                    area=laws.profiles[law_id].area,
                    params=dict(laws.profiles[law_id].params),
                    effect=law_effect(laws.profiles[law_id].kind, dict(laws.profiles[law_id].params)),
                    enforcement=laws.profiles[law_id].enforcement,
                    conflict=laws.profiles[law_id].conflict,
                    legitimacy_basis=laws.profiles[law_id].legitimacy_basis,
                    justice=stat(laws.laws[law_id], "justice") or 0,
                    enacted_epoch=laws.profiles[law_id].enacted_epoch,
                    holder_id=next((holder for holder, items in laws.by_node.items() if law_id in items), polity_id),
                    locked=list(laws.profiles[law_id].locked),
                )
                for law_id in law_ids
                if law_id in laws.profiles and law_id in laws.laws
            ],
            claims=[claim_view(row, names) for row in claims],
            treasury_ledger=[TreasuryLineView(epoch=row.epoch, entry=row.entry, amount=row.amount, balance=row.balance, note=row.note) for row in ledger],
            treaties=[
                TreatyBrief(id=row.treaty_entity_id, name=names.get(row.treaty_entity_id, ""), kind=row.kind, status=row.status, until_epoch=row.until_epoch)
                for row in treaties
            ],
            overlord=node(names, overlord.overlord_entity_id) if overlord else None,
            vassals=[NamedNode(id=row.vassal_entity_id, name=names.get(row.vassal_entity_id, "")) for row in vassals],
        )


@router.get("/houses/{house_id}", response_model=HouseView)
async def house(services: ServicesDep, house_id: int = Path(ge=1)) -> HouseView:
    async with reader(services) as session:
        entity = await session.get(EntityRow, house_id)
        profile = await session.get(HouseProfileRow, house_id)
        if entity is None or profile is None:
            raise NotFoundError("No such house.")
        members = list(await session.scalars(select(HouseMemberRow).where(HouseMemberRow.house_entity_id == house_id)))
        ids = [row.mortal_entity_id for row in members]
        mortals = {row.id: row for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_(ids)))} if ids else {}
        parents: dict[int, list[int]] = {}
        for bond in await session.scalars(
            select(BondRow).where(
                BondRow.kind == BondKind.DESCENDS_FROM, BondRow.source_node_id.in_(ids), BondRow.state.in_([BondState.ACTIVE, BondState.PAST])
            )
        ):
            parents.setdefault(bond.source_node_id, []).append(bond.target_node_id)
        wounds: dict[int, int] = {}
        for bearer in await session.scalars(
            select(InjuryRow.bearer_node_id).where(InjuryRow.bearer_node_id.in_(ids), InjuryRow.state.in_(list(LASTING_INJURY_STATES)))
        ):
            wounds[bearer] = wounds.get(bearer, 0) + 1
        offices = {row.holder_entity_id: row.kind for row in await session.scalars(select(OfficeRow).where(OfficeRow.holder_entity_id.in_(ids)))}
        claims = list(
            await session.scalars(
                select(ClaimRow).where(or_(ClaimRow.house_entity_id == house_id, ClaimRow.claimant_entity_id.in_(ids)), ClaimRow.ended_epoch.is_(None))
            )
        )
        heirlooms = list(await session.scalars(select(HeirloomRow).where(HeirloomRow.house_entity_id == house_id)))
        branches = list(await session.scalars(select(HouseProfileRow.house_entity_id).where(HouseProfileRow.parent_house_id == house_id)))
        names = await names_of(
            session,
            {
                *ids,
                *(row.claimant_entity_id for row in claims),
                *(row.polity_entity_id for row in claims),
                *(row.item_entity_id for row in heirlooms),
                *branches,
                *(item for item in (profile.founder_entity_id, profile.head_entity_id, profile.parent_house_id, profile.polity_entity_id) if item),
            },
        )
        return HouseView(
            id=entity.id,
            name=entity.name,
            prestige=profile.prestige,
            wealth=profile.wealth,
            motto=profile.motto,
            emblem=dict(profile.emblem),
            traits=[str(item) for item in profile.traits],
            founder=node(names, profile.founder_entity_id),
            head=node(names, profile.head_entity_id),
            parent=node(names, profile.parent_house_id),
            polity=node(names, profile.polity_entity_id),
            divine_son_id=profile.divine_son_id,
            branches=[NamedNode(id=item, name=names.get(item, "")) for item in branches],
            members=[
                HouseMemberView(
                    id=row.mortal_entity_id,
                    name=names.get(row.mortal_entity_id, ""),
                    alive=mortals[row.mortal_entity_id].status is EntityStatus.CANON if row.mortal_entity_id in mortals else False,
                    sex=getattr(mortals[row.mortal_entity_id].stats, "sex", None) if row.mortal_entity_id in mortals else None,
                    age=stat(mortals[row.mortal_entity_id], "age") if row.mortal_entity_id in mortals else None,
                    parents=[parent for parent in parents.get(row.mortal_entity_id, []) if parent in mortals],
                    by_marriage=row.by_marriage,
                    lasting_injuries=wounds.get(row.mortal_entity_id, 0),
                    fate=mortals[row.mortal_entity_id].fate_note if row.mortal_entity_id in mortals else None,
                    office=offices.get(row.mortal_entity_id),
                )
                for row in members
            ],
            claims=[claim_view(row, names) for row in claims],
            heirlooms=[HeirloomView(id=row.item_entity_id, name=names.get(row.item_entity_id, ""), since_epoch=row.since_epoch) for row in heirlooms],
            locked=list(profile.locked),
        )


@router.get("/treaties/{treaty_id}", response_model=TreatyView)
async def treaty(services: ServicesDep, treaty_id: int = Path(ge=1)) -> TreatyView:
    async with reader(services) as session:
        entity = await session.get(EntityRow, treaty_id)
        profile = await session.get(TreatyProfileRow, treaty_id)
        if entity is None or profile is None:
            raise NotFoundError("No such treaty.")
        parties = list(await session.scalars(select(TreatyPartyRow).where(TreatyPartyRow.treaty_entity_id == treaty_id)))
        clauses = list(await session.scalars(select(TreatyClauseRow).where(TreatyClauseRow.treaty_entity_id == treaty_id).order_by(TreatyClauseRow.id)))
        breaches = list(await session.scalars(select(TreatyBreachRow).where(TreatyBreachRow.treaty_entity_id == treaty_id).order_by(TreatyBreachRow.epoch)))
        names = await names_of(
            session,
            {
                *(row.party_node_id for row in parties),
                *(row.obligor_node_id for row in clauses if row.obligor_node_id),
                *(row.beneficiary_node_id for row in clauses if row.beneficiary_node_id),
                *(row.breaker_node_id for row in breaches if row.breaker_node_id),
            },
        )
        return TreatyView(
            id=entity.id,
            name=entity.name,
            kind=profile.kind,
            status=profile.status,
            signed_epoch=profile.signed_epoch,
            until_epoch=profile.until_epoch,
            ended_epoch=profile.ended_epoch,
            witness_son_id=profile.witness_son_id,
            renewals=profile.renewals,
            parties=[PartyView(id=row.party_node_id, name=names.get(row.party_node_id, ""), role=row.role) for row in parties],
            clauses=[
                ClauseView(
                    id=row.id,
                    kind=row.kind,
                    obligor_id=row.obligor_node_id,
                    obligor=names.get(row.obligor_node_id) if row.obligor_node_id else None,
                    beneficiary_id=row.beneficiary_node_id,
                    beneficiary=names.get(row.beneficiary_node_id) if row.beneficiary_node_id else None,
                    params=dict(row.params),
                    last_kept_epoch=row.last_kept_epoch,
                )
                for row in clauses
            ],
            breaches=[
                BreachView(
                    epoch=row.epoch, breaker_id=row.breaker_node_id, breaker=names.get(row.breaker_node_id) if row.breaker_node_id else None, note=row.note
                )
                for row in breaches
            ],
            locked=list(profile.locked),
        )


def oath_view(row: OathRow, names: dict[int, str]) -> OathView:
    return OathView(
        id=row.id,
        kind=row.kind,
        status=row.status,
        swearer_id=row.swearer_entity_id,
        swearer=names.get(row.swearer_entity_id, ""),
        recipient_id=row.recipient_node_id,
        recipient=names.get(row.recipient_node_id) if row.recipient_node_id else None,
        witness_son_id=row.witness_son_id,
        sworn_epoch=row.sworn_epoch,
        deadline_epoch=row.deadline_epoch,
        ended_epoch=row.ended_epoch,
        note=row.note,
    )


@router.get("/entities/{entity_id}/oaths", response_model=OathsView)
async def oaths(services: ServicesDep, entity_id: int = Path(ge=1)) -> OathsView:
    async with reader(services) as session:
        sworn = list(await session.scalars(select(OathRow).where(OathRow.swearer_entity_id == entity_id).order_by(OathRow.sworn_epoch, OathRow.id)))
        received = list(await session.scalars(select(OathRow).where(OathRow.recipient_node_id == entity_id).order_by(OathRow.sworn_epoch, OathRow.id)))
        names = await names_of(
            session, {*(row.swearer_entity_id for row in [*sworn, *received]), *(row.recipient_node_id for row in [*sworn, *received] if row.recipient_node_id)}
        )
        return OathsView(entity_id=entity_id, sworn=[oath_view(row, names) for row in sworn], received=[oath_view(row, names) for row in received])


@router.get("/laws/kinds", response_model=list[LawKindSpec])
async def law_kinds() -> list[LawKindSpec]:
    return [
        LawKindSpec(
            kind=kind,
            area=LAW_AREAS[kind],
            params=[
                LawParamSpec(
                    key=key,
                    kind="bool" if isinstance(param.default, bool) else "choice" if param.choices else "int",
                    default=param.default,
                    low=param.low,
                    high=param.high,
                    choices=list(param.choices),
                )
                for key, param in specs.items()
            ],
        )
        for kind, specs in LAW_PARAMS.items()
    ]

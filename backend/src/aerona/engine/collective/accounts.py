from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.life.collective import MEDIUM_FADE
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.total import total
from aerona.db.record_context import Term
from aerona.db.tables.collective import AccountRow, AccountStanceRow, CommemorationRow, FoundingMythRow, LostLandRow, MemoryStrikeRow
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import CollectionIncidentRow, CollectionMemberRow, CollectionPlaceRow, CollectionRow
from aerona.db.tables.made import DataStoreRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import HouseMemberRow, OfficeRow, PolityMemberRow, PolityProfileRow, PolityTerritoryRow
from aerona.db.tables.renown import DeedClaimRow, DeedRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.warfare import CasusBelliRow
from aerona.db.write_guard import held
from aerona.domain.enums.collective import AccountKind, AccountMedium, AccountStance, CollectiveActKind, CollectiveTrigger, CommemorationFeeling
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.gathering import CollectionKind, CollectionRole
from aerona.domain.enums.intrigue import IntrigueSecret
from aerona.domain.enums.made import Authenticity
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.minds import MindSeat
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import ClaimBasis, OfficeKind
from aerona.domain.enums.renown import ClaimKind, ClaimStatus
from aerona.domain.enums.war import CasusBelliKind
from aerona.engine.belonging.effects import GROUP_LAYERS, identities_of, same_value
from aerona.engine.body.customs import people_of
from aerona.engine.collective.book import realm_of_town, ruler_id, shift
from aerona.engine.collective.crowds import begin_movement
from aerona.engine.context import TickContext
from aerona.engine.intrigue.secrets import keep_secret
from aerona.engine.mind.book import stored_values
from aerona.engine.mind.ethics import holder_kind
from aerona.engine.polity.control import grant_claim
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record as record_incident

C = CollectionKind
R = CollectionRole
RECORDED = frozenset(
    {
        C.WAR,
        C.BATTLE,
        C.SIEGE,
        C.COUP,
        C.INSURRECTION,
        C.SUCCESSION_CRISIS,
        C.OCCUPATION,
        C.FOUNDING,
        C.PLAGUE,
        C.FAMINE,
        C.PERSECUTION,
        C.PURGE,
        C.CORONATION,
        C.HEROQUEST,
        C.CONVERSION_WAVE,
        C.SCHISM,
        C.MIGRATION,
        C.RIOT,
        C.PANIC,
        C.MOVEMENT,
    }
)
FAITH_KINDS = frozenset({C.CONVERSION_WAVE, C.SCHISM, C.PERSECUTION, C.PILGRIMAGE, C.HEROQUEST, C.MOVEMENT})
EPIC_KINDS = frozenset({C.BATTLE, C.SIEGE, C.HEROQUEST, C.DUEL})
STAGED_KINDS = frozenset({C.PERFORMANCE, C.FEAST, C.CEREMONY, C.TOURNAMENT, C.CORONATION})
SWORN_KINDS = frozenset({C.TRIAL, C.INVESTIGATION})
PRIDE_KINDS = frozenset({C.FOUNDING, C.CORONATION})
GRIEF_KINDS = frozenset({C.PERSECUTION, C.PURGE, C.PLAGUE, C.FAMINE, C.OCCUPATION, C.RIOT})
GREAT_KINDS = frozenset({C.WAR, C.SIEGE, C.FOUNDING, C.PERSECUTION, C.PURGE, C.CORONATION, C.INSURRECTION})
TRIUMPH = frozenset({R.WINNER, R.FOUNDER, R.LEADER, R.HOST, R.FINDER})
DEFEAT = frozenset({R.LOSER, R.VICTIM, R.ACCUSED})
SLANT = {AccountStance.GLORIFY: 8, AccountStance.VILIFY: 8, AccountStance.OMIT: 15, AccountStance.NEUTRAL: 0}
REVISION_LOSS = 20
SCANDAL_CREDENCE = 30
MYTH_FIDELITY = 30
MYTH_CREDENCE = 70
DEBUNKED_CREDENCE = 10
KEPT_FLOOR = 30


@dataclass
class HistoryTally:
    accounts: int = 0
    revisions: int = 0
    scandals: int = 0
    struck: int = 0
    faded: int = 0
    myths: int = 0
    debunked: int = 0
    anniversaries: int = 0
    neglected: int = 0
    claims: int = 0


def distance_from_truth(account: AccountRow, stances: list[AccountStance]) -> int:
    return clamp_int(PERCENT - account.fidelity + sum(SLANT[stance] for stance in stances), 0, PERCENT)


async def stances_of(ctx: TickContext, account_id: int) -> dict[int, AccountStance]:
    rows = await ctx.session.scalars(select(AccountStanceRow).where(AccountStanceRow.account_id == account_id))
    return {row.node_id: row.stance for row in rows}


async def realm_id_of(ctx: TickContext, node_id: int) -> int | None:
    if await ctx.session.get(PolityProfileRow, node_id) is not None:
        return node_id
    profile = await ctx.session.get(MortalProfileRow, node_id)
    if profile is not None and profile.polity_id is not None:
        return profile.polity_id
    return await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == node_id).limit(1))


async def truthful(ctx: TickContext, holder: EntityRow) -> int:
    values = await stored_values(ctx.session, holder_kind(holder), holder.id) if holder.entity_type in {EntityType.PEOPLE, EntityType.CULT} else {}
    return values.get(ValueAxis.TRUTH, 0)


async def record(
    ctx: TickContext,
    holder: EntityRow,
    kind: AccountKind,
    *,
    fidelity: int,
    stances: dict[int, AccountStance],
    collection_id: int | None = None,
    subject_id: int | None = None,
    medium: AccountMedium = AccountMedium.ORAL,
    author_id: int | None = None,
    structure_id: int | None = None,
    artwork_id: int | None = None,
    revised_from: int | None = None,
    credence: int = 60,
) -> AccountRow | None:
    if held(holder.id):
        return None
    row = AccountRow(
        holder_entity_id=holder.id,
        author_node_id=author_id,
        kind=kind,
        medium=medium,
        collection_id=collection_id,
        subject_node_id=subject_id,
        structure_entity_id=structure_id,
        artwork_entity_id=artwork_id,
        fidelity=clamp_int(fidelity, 0, PERCENT),
        credence=clamp_int(credence, 0, PERCENT),
        revised_from_id=revised_from,
        defaced=False,
        authenticity=Authenticity.UNKNOWN if medium is AccountMedium.ORAL else Authenticity.GENUINE,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    for node_id, stance in sorted(stances.items()):
        ctx.session.add(AccountStanceRow(account_id=row.id, node_id=node_id, stance=stance))
    await ctx.session.flush()
    return row


def slant(side: int | None, own: int, role: CollectionRole) -> AccountStance:
    mine = side == own
    if mine and role in TRIUMPH:
        return AccountStance.GLORIFY
    if mine and role in DEFEAT:
        return AccountStance.OMIT
    if not mine and role in TRIUMPH:
        return AccountStance.VILIFY
    return AccountStance.NEUTRAL


async def monument_of(ctx: TickContext, realm: PolityProfileRow) -> int | None:
    if realm.capital_entity_id is None:
        return None
    return await ctx.session.scalar(
        select(EntityRow.id)
        .where(EntityRow.entity_type == EntityType.STRUCTURE, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == realm.capital_entity_id)
        .order_by(EntityRow.id)
        .limit(1)
    )


Members = list[tuple[int, CollectionRole]]


async def false_credits(ctx: TickContext, collection_id: int) -> list[tuple[int, int]]:
    rows = await ctx.session.execute(
        select(DeedClaimRow.claimant_node_id, DeedRow.doer_node_id)
        .join(DeedRow, DeedRow.id == DeedClaimRow.deed_id)
        .join(CollectionIncidentRow, CollectionIncidentRow.incident_id == DeedRow.incident_id)
        .where(CollectionIncidentRow.collection_id == collection_id, DeedClaimRow.kind == ClaimKind.FALSE, DeedClaimRow.status == ClaimStatus.STANDING)
        .order_by(DeedClaimRow.id)
    )
    return [(claimant, doer) for claimant, doer in rows if claimant != doer]


async def realm_accounts(ctx: TickContext, collection: CollectionRow, members: Members, places: list[int], tally: HistoryTally) -> None:
    table = ctx.rules.historiography
    sides = {node: await realm_id_of(ctx, node) for node, _ in members}
    taking_part = {side for side in sides.values() if side is not None}
    realms: list[int] = sorted(taking_part)
    for place in places:
        local = await realm_of_town(ctx, place)
        if local is not None and local.polity_entity_id not in realms:
            realms.append(local.polity_entity_id)
    for index, realm_id in enumerate(realms):
        realm = await ctx.session.get(EntityRow, realm_id)
        profile = await ctx.session.get(PolityProfileRow, realm_id)
        if realm is None or profile is None:
            continue
        stances = {node: slant(sides[node], realm_id, role) for node, role in members}
        own = realm_id in taking_part or index == 0
        if own:
            for claimant, doer in await false_credits(ctx, collection.id):
                if await realm_id_of(ctx, claimant) == realm_id:
                    stances[claimant], stances[doer] = AccountStance.GLORIFY, AccountStance.OMIT
        boasts = own and any(stance is AccountStance.GLORIFY for stance in stances.values())
        monument = await monument_of(ctx, profile) if boasts else None
        artwork = await artwork_of(ctx, realm_id, [node for node, _ in members]) if boasts and monument is None else None
        slanted = sum(1 for stance in stances.values() if stance is not AccountStance.NEUTRAL)
        kept = await keeps_records(ctx, realm_id)
        written = await record(
            ctx,
            realm,
            official_kind(own, monument, kept),
            fidelity=(table.official_fidelity if own else table.foreign_fidelity) - slanted * 3,
            stances=stances,
            collection_id=collection.id,
            medium=await official_medium(ctx, realm_id, monument, artwork, kept),
            author_id=await ruler_id(ctx, realm_id),
            structure_id=monument,
            artwork_id=artwork,
        )
        tally.accounts += written is not None


async def folk_accounts(ctx: TickContext, collection: CollectionRow, members: Members, places: list[int], tally: HistoryTally) -> None:
    table = ctx.rules.historiography
    place_row = await ctx.session.get(EntityRow, places[0]) if places else None
    people = await people_of(ctx.session, place_row) if place_row is not None else None
    if people is None:
        return
    folk = {node: AccountStance.GLORIFY if role in DEFEAT else AccountStance.NEUTRAL for node, role in members}
    kind = AccountKind.EPIC if collection.kind in EPIC_KINDS else AccountKind.TESTIMONY if collection.kind in SWORN_KINDS else AccountKind.FOLK_MEMORY
    medium = AccountMedium.PERFORMANCE if collection.kind in STAGED_KINDS else AccountMedium.ORAL
    fidelity = table.folk_fidelity + await truthful(ctx, people) // 5
    written = await record(ctx, people, kind, fidelity=fidelity, stances=folk, collection_id=collection.id, medium=medium)
    tally.accounts += written is not None


async def gospels(ctx: TickContext, collection: CollectionRow, members: Members, tally: HistoryTally) -> None:
    if collection.kind not in FAITH_KINDS:
        return
    for node, role in members:
        cult = await ctx.session.get(EntityRow, node)
        if cult is None or cult.entity_type is not EntityType.CULT:
            continue
        gospel = {other: AccountStance.GLORIFY if other == node else slant(node, node, given) for other, given in members}
        fidelity = ctx.rules.historiography.folk_fidelity
        written = await record(ctx, cult, AccountKind.GOSPEL, fidelity=fidelity, stances=gospel, collection_id=collection.id, medium=AccountMedium.BOOK)
        tally.accounts += written is not None
        if role in TRIUMPH:
            return


async def artwork_of(ctx: TickContext, realm_id: int, subjects: list[int]) -> int | None:
    if not subjects:
        return None
    return await ctx.session.scalar(
        select(ArtworkProfileRow.artwork_entity_id)
        .join(EntityRow, EntityRow.id == ArtworkProfileRow.artwork_entity_id)
        .where(ArtworkProfileRow.patron_entity_id == realm_id, ArtworkProfileRow.subject_node_id.in_(subjects), EntityRow.status == EntityStatus.CANON)
        .order_by(ArtworkProfileRow.artwork_entity_id.desc())
        .limit(1)
    )


async def identity_accounts(ctx: TickContext, collection: CollectionRow, members: Members, places: list[int], tally: HistoryTally) -> None:
    for place in places:
        rows = await identities_of(ctx.session, place)
        keepers = [
            row for row in rows.values() if row.layer in GROUP_LAYERS and row.value_node_id is not None and row.salience >= ctx.rules.identities.memory_at
        ]
        if not keepers:
            continue
        keeper = max(keepers, key=lambda row: (row.salience, row.layer.value))
        group = await living_entity(ctx.session, keeper.value_node_id)
        if group is None:
            continue
        stances = {}
        for node, _role in members:
            mine = (await identities_of(ctx.session, node)).get(keeper.layer)
            stances[node] = AccountStance.GLORIFY if mine is not None and same_value(mine, keeper) else AccountStance.NEUTRAL
        written = await record(
            ctx, group, AccountKind.FOLK_MEMORY, fidelity=ctx.rules.historiography.folk_fidelity, stances=stances, collection_id=collection.id
        )
        tally.accounts += written is not None


async def chronicle_collection(ctx: TickContext, collection: CollectionRow, tally: HistoryTally) -> None:
    query = select(CollectionMemberRow.node_id, CollectionMemberRow.role).where(CollectionMemberRow.collection_id == collection.id)
    members: Members = [(node, role) for node, role in await ctx.session.execute(query)]
    places = list(await ctx.session.scalars(select(CollectionPlaceRow.place_entity_id).where(CollectionPlaceRow.collection_id == collection.id)))
    await realm_accounts(ctx, collection, members, places, tally)
    await folk_accounts(ctx, collection, members, places, tally)
    await gospels(ctx, collection, members, tally)
    await identity_accounts(ctx, collection, members, places, tally)


async def write_accounts(ctx: TickContext, tally: HistoryTally) -> None:
    told = select(AccountRow.collection_id).where(AccountRow.collection_id.is_not(None))
    rows = await ctx.session.scalars(
        select(CollectionRow)
        .where(CollectionRow.kind.in_(sorted(RECORDED)), CollectionRow.id.not_in(told), CollectionRow.start_epoch >= ctx.epoch - 1)
        .order_by(CollectionRow.id)
    )
    for collection in list(rows):
        if not held(collection.world_id):
            await chronicle_collection(ctx, collection, tally)


KIND_DECAY: Mapping[AccountKind, int] = total(
    AccountKind,
    {
        AccountKind.OFFICIAL_CHRONICLE: 100,
        AccountKind.FOLK_MEMORY: 120,
        AccountKind.FOREIGN_ACCOUNT: 100,
        AccountKind.GOSPEL: 60,
        AccountKind.EPIC: 80,
        AccountKind.INSCRIPTION: 30,
        AccountKind.FOUNDING_MYTH: 50,
        AccountKind.ELDER_MEMORY: 140,
        AccountKind.RECORD: 20,
        AccountKind.TESTIMONY: 110,
    },
)


async def keeps_records(ctx: TickContext, realm_id: int) -> bool:
    return await ctx.session.scalar(select(DataStoreRow.id).where(DataStoreRow.holder_node_id == realm_id).limit(1)) is not None


def official_kind(own: bool, monument: int | None, kept: bool) -> AccountKind:
    if not own:
        return AccountKind.FOREIGN_ACCOUNT
    if monument is not None:
        return AccountKind.INSCRIPTION
    return AccountKind.RECORD if kept else AccountKind.OFFICIAL_CHRONICLE


async def official_medium(ctx: TickContext, realm_id: int, monument: int | None, artwork: int | None, kept: bool) -> AccountMedium:
    if monument is not None:
        return AccountMedium.INSCRIPTION
    if artwork is not None:
        return AccountMedium.ARTWORK
    ruler = await ruler_id(ctx, realm_id)
    mind = await ctx.session.get(MindProfileRow, ruler) if ruler is not None else None
    if mind is not None and mind.seat is not MindSeat.BODY:
        return AccountMedium.MIND_STATE
    return AccountMedium.RECORD if kept else AccountMedium.BOOK


async def age_accounts(ctx: TickContext, tally: HistoryTally) -> None:
    table = ctx.rules.historiography
    for account in list(await ctx.session.scalars(select(AccountRow).where(AccountRow.credence > 0).order_by(AccountRow.id))):
        if held(account.holder_entity_id):
            continue
        shift(account, "fidelity", -table.fidelity_decay * MEDIUM_FADE[account.medium] // PERCENT)
        shift(account, "credence", -table.credence_decay * KIND_DECAY[account.kind] // PERCENT)
        tally.faded += 1


async def house_of(ctx: TickContext, mortal_id: int | None) -> int | None:
    if mortal_id is None:
        return None
    return await ctx.session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == mortal_id).limit(1))


async def revise(ctx: TickContext, account: AccountRow, ousted: list[int], new_ruler: int | None) -> AccountRow | None:
    holder = await ctx.session.get(EntityRow, account.holder_entity_id)
    if holder is None:
        return None
    stances = await stances_of(ctx, account.id)
    for node in ousted:
        stances[node] = AccountStance.VILIFY
    if new_ruler is not None:
        stances[new_ruler] = AccountStance.GLORIFY
    revision = await record(
        ctx,
        holder,
        account.kind,
        fidelity=account.fidelity - REVISION_LOSS,
        stances=stances,
        collection_id=account.collection_id,
        subject_id=account.subject_node_id,
        medium=account.medium,
        author_id=new_ruler,
        structure_id=account.structure_entity_id,
        artwork_id=account.artwork_entity_id,
        revised_from=account.id,
        credence=max(account.credence, PERCENT // 2),
    )
    if revision is not None:
        shift(account, "credence", -account.credence // 2)
    return revision


async def rewrite_reigns(ctx: TickContext, tally: HistoryTally) -> None:
    table = ctx.rules.historiography
    fresh = await ctx.session.scalars(
        select(OfficeRow)
        .where(OfficeRow.kind == OfficeKind.RULER, OfficeRow.since_epoch >= ctx.epoch - 1, OfficeRow.holder_entity_id.is_not(None))
        .order_by(OfficeRow.id)
    )
    for office in list(fresh):
        if held(office.polity_entity_id):
            continue
        dynasty = await house_of(ctx, office.holder_entity_id)
        accounts = list(
            await ctx.session.scalars(
                select(AccountRow)
                .where(AccountRow.holder_entity_id == office.polity_entity_id, AccountRow.kind == AccountKind.OFFICIAL_CHRONICLE, AccountRow.credence > 0)
                .order_by(AccountRow.id)
            )
        )
        revised = set(await ctx.session.scalars(select(AccountRow.revised_from_id).where(AccountRow.revised_from_id.is_not(None))))
        for account in accounts:
            if account.id in revised or "credence" in account.locked:
                continue
            glorified = [node for node, stance in (await stances_of(ctx, account.id)).items() if stance is AccountStance.GLORIFY]
            ousted = [node for node in glorified if node != office.holder_entity_id and (await house_of(ctx, node)) not in {None, dynasty}]
            if not ousted or not ctx.rng(f"revise.{account.id}.{ctx.epoch}").chance(table.revise_pct):
                continue
            if await revise(ctx, account, ousted, office.holder_entity_id) is not None:
                tally.revisions += 1
                for node in ousted:
                    await strike(ctx, office.polity_entity_id, node, tally)


async def scholar_in(ctx: TickContext, realm_id: int) -> int | None:
    rows = await ctx.session.scalars(
        select(MortalProfileRow.entity_id)
        .join(EntityRow, EntityRow.id == MortalProfileRow.entity_id)
        .where(MortalProfileRow.polity_id == realm_id, EntityRow.status == EntityStatus.CANON)
        .order_by(MortalProfileRow.education.desc(), MortalProfileRow.entity_id)
        .limit(1)
    )
    found = rows.first()
    return found if found is not None and not held(found) else None


async def expose(ctx: TickContext, revision: AccountRow, original: AccountRow, scholar: int | None) -> None:
    table = ctx.rules.historiography
    shift(revision, "credence", -SCANDAL_CREDENCE)
    shift(original, "credence", SCANDAL_CREDENCE)
    realm = await ctx.session.get(PolityProfileRow, revision.holder_entity_id)
    if realm is not None:
        shift(realm, "legitimacy", -table.debunk_cost / 2)
    if scholar is not None:
        await keep_secret(ctx, scholar, IntrigueSecret.TRUE_HISTORY, about_id=revision.holder_entity_id, source="historiography")
    await record_incident(
        ctx,
        "history.scandal",
        roles={IncidentRole.SUBJECT: revision.holder_entity_id, **({IncidentRole.ACCUSER: scholar} if scholar is not None else {})},
        facts={"credence_shift": SCANDAL_CREDENCE, **({"legitimacy_lost": table.debunk_cost / 2} if realm is not None else {})},
        terms=[
            Term("historiography.scandal_credence", SCANDAL_CREDENCE),
            *([Term("rules.historiography.debunk_cost", table.debunk_cost / 2)] if realm is not None else []),
        ],
    )
    if realm is not None:
        await rally_true_line(ctx, realm, revision, original)


async def rally_true_line(ctx: TickContext, realm: PolityProfileRow, revision: AccountRow, original: AccountRow) -> None:
    table = ctx.rules.historiography
    capital = await ctx.session.get(EntityRow, realm.capital_entity_id) if realm.capital_entity_id is not None else None
    if capital is not None and not held(capital.id) and await ctx.session.get(SettlementProfileRow, capital.id) is not None:
        members = round_half_up(stat_or(capital, "population", 0) * table.debunk_cost / PERCENT)
        await begin_movement(ctx, capital, CollectiveActKind.RIOT, CollectiveTrigger.RUMOUR, members=members, share=table.debunk_cost * 2)
    now = await stances_of(ctx, revision.id)
    wronged = [
        node for node, stance in (await stances_of(ctx, original.id)).items() if stance is AccountStance.GLORIFY and now.get(node) is not AccountStance.GLORIFY
    ]
    ruler = await ruler_id(ctx, realm.polity_entity_id)
    for node in wronged:
        dynasty = await house_of(ctx, node)
        if dynasty is None:
            continue
        heir = await ctx.session.scalar(
            select(HouseMemberRow.mortal_entity_id)
            .join(EntityRow, EntityRow.id == HouseMemberRow.mortal_entity_id)
            .where(HouseMemberRow.house_entity_id == dynasty, EntityRow.status == EntityStatus.CANON, HouseMemberRow.mortal_entity_id != ruler)
            .order_by(HouseMemberRow.mortal_entity_id)
            .limit(1)
        )
        if heir is None or held(heir):
            continue
        try:
            await grant_claim(ctx, heir, realm.polity_entity_id, strength=table.irredentist_claim_at, basis=ClaimBasis.INHERITANCE)
        except (NotFoundError, ValidationFailedError):
            continue
        await record_incident(
            ctx,
            "history.true_line",
            roles={IncidentRole.ACTOR: heir, IncidentRole.TARGET: realm.polity_entity_id},
            facts={"claim_strength": table.irredentist_claim_at, "basis": ClaimBasis.INHERITANCE},
            terms=[Term("rules.historiography.irredentist_claim_at", table.irredentist_claim_at)],
        )
        return


async def excavated(ctx: TickContext, realm_id: int) -> bool:
    towns = select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == realm_id)
    found = await ctx.session.scalar(
        select(CollectionRow.id)
        .join(CollectionPlaceRow, CollectionPlaceRow.collection_id == CollectionRow.id)
        .where(CollectionRow.kind == C.EXCAVATION, CollectionRow.start_epoch >= ctx.epoch - 1, CollectionPlaceRow.place_entity_id.in_(towns))
        .limit(1)
    )
    return found is not None


async def find_scandals(ctx: TickContext, tally: HistoryTally) -> None:
    table = ctx.rules.historiography
    rows = await ctx.session.scalars(select(AccountRow).where(AccountRow.revised_from_id.is_not(None), AccountRow.credence > 0).order_by(AccountRow.id))
    for revision in list(rows):
        original = await ctx.session.get(AccountRow, revision.revised_from_id)
        if original is None or held(revision.holder_entity_id) or original.credence <= 0:
            continue
        scholar = await scholar_in(ctx, revision.holder_entity_id)
        chance = table.scandal_pct * (2 if await excavated(ctx, revision.holder_entity_id) else 1)
        if scholar is None or not ctx.rng(f"scandal.{revision.id}.{ctx.epoch}").chance(chance):
            continue
        await expose(ctx, revision, original, scholar)
        tally.scandals += 1


async def strike(ctx: TickContext, by_id: int, node_id: int, tally: HistoryTally) -> MemoryStrikeRow | None:
    if held(by_id) or held(node_id):
        return None
    row = await ctx.session.get(MemoryStrikeRow, (node_id, by_id))
    if row is None:
        row = MemoryStrikeRow(node_id=node_id, by_entity_id=by_id, active=True, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    row.active = True
    surviving = select(AccountRow.revised_from_id).where(AccountRow.revised_from_id.is_not(None))
    for account in await ctx.session.scalars(select(AccountRow).where(AccountRow.holder_entity_id == by_id, AccountRow.id.not_in(surviving))):
        stance = await ctx.session.get(AccountStanceRow, (account.id, node_id))
        if stance is not None:
            stance.stance = AccountStance.OMIT
            if account.medium is AccountMedium.INSCRIPTION and "defaced" not in account.locked:
                account.defaced = True
    for artwork in await ctx.session.scalars(
        select(ArtworkProfileRow).where(ArtworkProfileRow.subject_node_id == node_id, ArtworkProfileRow.patron_entity_id == by_id)
    ):
        work = await ctx.session.get(EntityRow, artwork.artwork_entity_id)
        if work is not None and work.status is EntityStatus.CANON and not held(work.id):
            await retire_in(ctx, work, "destroyed to erase the memory of its subject", EntityStatus.DESTROYED)
    await ctx.session.flush()
    tally.struck += 1
    await record_incident(ctx, "history.struck", roles={IncidentRole.ACTOR: by_id, IncidentRole.TARGET: node_id})
    return row


async def fade_struck(ctx: TickContext, tally: HistoryTally) -> None:
    table = ctx.rules.historiography
    for row in list(await ctx.session.scalars(select(MemoryStrikeRow).where(MemoryStrikeRow.active.is_(True)).order_by(MemoryStrikeRow.node_id))):
        if held(row.node_id):
            continue
        kept = await ctx.session.scalar(
            select(func.count())
            .select_from(AccountStanceRow)
            .join(AccountRow, AccountRow.id == AccountStanceRow.account_id)
            .where(
                AccountStanceRow.node_id == row.node_id,
                AccountStanceRow.stance != AccountStance.OMIT,
                AccountRow.kind.in_([AccountKind.FOLK_MEMORY, AccountKind.FOREIGN_ACCOUNT, AccountKind.EPIC]),
                AccountRow.credence > 0,
            )
        )
        profile = await ctx.session.get(MortalProfileRow, row.node_id)
        if kept or profile is None:
            continue
        shift(profile, "renown", -table.strike_fade)
        tally.faded += 1


async def myth_holders(ctx: TickContext) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type.in_([EntityType.PEOPLE, EntityType.POLITY]), EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return [row for row in rows if not held(row.id)]


async def found_myth(ctx: TickContext, holder: EntityRow, tally: HistoryTally) -> FoundingMythRow | None:
    origin = await ctx.session.scalar(
        select(CollectionRow.id)
        .join(CollectionMemberRow, CollectionMemberRow.collection_id == CollectionRow.id)
        .where(CollectionRow.kind == C.FOUNDING, CollectionMemberRow.node_id == holder.id)
        .order_by(CollectionRow.id)
        .limit(1)
    )
    account = await record(
        ctx,
        holder,
        AccountKind.FOUNDING_MYTH,
        fidelity=MYTH_FIDELITY,
        stances={holder.id: AccountStance.GLORIFY},
        collection_id=origin,
        subject_id=holder.id,
        credence=MYTH_CREDENCE,
    )
    row = FoundingMythRow(
        holder_entity_id=holder.id, account_id=account.id if account is not None else None, credence=MYTH_CREDENCE, since_epoch=ctx.epoch, locked=[]
    )
    ctx.session.add(row)
    await ctx.session.flush()
    tally.myths += 1
    return row


async def believe_myths(ctx: TickContext, tally: HistoryTally) -> None:
    table = ctx.rules.historiography
    known = {row.holder_entity_id: row for row in await ctx.session.scalars(select(FoundingMythRow))}
    for holder in await myth_holders(ctx):
        myth = known.get(holder.id) or await found_myth(ctx, holder, tally)
        if myth is None or myth.debunked_epoch is not None:
            continue
        lean = (myth.credence - PERCENT // 2) / PERCENT
        realm = await ctx.session.get(PolityProfileRow, holder.id)
        if realm is not None:
            shift(realm, "legitimacy", table.myth_legitimacy * lean)
            shift(realm, "stability", table.myth_cohesion * lean)
            doubted = myth.credence > KEPT_FLOOR and await scholar_in(ctx, holder.id) is not None
            if doubted and ctx.rng(f"debunk.{holder.id}.{ctx.epoch}").chance(table.scandal_pct / 4):
                await debunk(ctx, myth, holder, tally)
        else:
            for town in await town_profiles_of(ctx, holder.id):
                shift(town, "unrest", -table.myth_cohesion * lean)


async def town_profiles_of(ctx: TickContext, people_id: int) -> list[SettlementProfileRow]:
    rows = await ctx.session.scalars(
        select(SettlementProfileRow)
        .where(SettlementProfileRow.settlement_entity_id.in_(await towns_of_people(ctx.session, people_id)))
        .order_by(SettlementProfileRow.settlement_entity_id)
    )
    return [row for row in rows if not held(row.settlement_entity_id)]


async def debunk(ctx: TickContext, myth: FoundingMythRow, holder: EntityRow, tally: HistoryTally) -> None:
    table = ctx.rules.historiography
    myth.credence, myth.debunked_epoch = DEBUNKED_CREDENCE, ctx.epoch
    realm = await ctx.session.get(PolityProfileRow, holder.id)
    if realm is not None:
        shift(realm, "legitimacy", -table.debunk_cost)
        shift(realm, "stability", -table.debunk_cost)
    for town in await town_profiles_of(ctx, holder.id):
        shift(town, "unrest", table.debunk_cost)
    tally.debunked += 1
    await record_incident(
        ctx,
        "history.myth_debunked",
        roles={IncidentRole.SUBJECT: holder.id},
        facts={"credence": DEBUNKED_CREDENCE, **({"standing_lost": table.debunk_cost} if realm is not None else {})},
        terms=[Term("rules.historiography.debunk_cost", table.debunk_cost)],
    )


async def mark_anniversaries(ctx: TickContext, tally: HistoryTally) -> None:
    kept = select(CommemorationRow.collection_id)
    rows = await ctx.session.scalars(
        select(CollectionRow).where(CollectionRow.kind.in_(sorted(GREAT_KINDS)), CollectionRow.id.not_in(kept)).order_by(CollectionRow.id)
    )
    for collection in list(rows):
        members = list(
            await ctx.session.execute(select(CollectionMemberRow.node_id, CollectionMemberRow.role).where(CollectionMemberRow.collection_id == collection.id))
        )
        for node, role in members:
            realm = await realm_id_of(ctx, node)
            if realm is None or held(realm) or await ctx.session.get(CommemorationRow, (realm, collection.id)) is not None:
                continue
            pride = collection.kind in PRIDE_KINDS or (role in TRIUMPH and collection.kind not in GRIEF_KINDS)
            ctx.session.add(
                CommemorationRow(holder_entity_id=realm, collection_id=collection.id, pride=pride, strength=PERCENT * 3 // 5, since_epoch=ctx.epoch, locked=[])
            )
    await ctx.session.flush()


async def keep_anniversary(ctx: TickContext, row: CommemorationRow, collection: CollectionRow, tally: HistoryTally, *, forced: bool = False) -> bool:
    table = ctx.rules.historiography
    realm = await ctx.session.get(PolityProfileRow, row.holder_entity_id)
    capital = await ctx.session.get(SettlementProfileRow, realm.capital_entity_id) if realm is not None and realm.capital_entity_id else None
    if not forced and not ctx.rng(f"relive.{row.holder_entity_id}.{row.collection_id}.{ctx.epoch}").chance(row.strength):
        shift(row, "strength", -table.commemoration_fade)
        tally.neglected += 1
        return False
    if capital is not None:
        if row.pride:
            shift(capital, "public_order", table.pride_order)
        else:
            shift(capital, "unrest", table.grievance_unrest)
    if "last_observed_epoch" not in row.locked:
        row.last_observed_epoch = ctx.epoch
    tally.anniversaries += 1
    if await ctx.session.get(EntityRow, row.holder_entity_id) is not None:
        change = table.pride_order if row.pride else table.grievance_unrest
        await record_incident(
            ctx,
            "history.anniversary",
            roles={IncidentRole.SUBJECT: row.holder_entity_id},
            facts={
                "feeling": CommemorationFeeling.PRIDE if row.pride else CommemorationFeeling.GRIEF,
                "happening": collection.name,
                "years": ctx.epoch - collection.start_epoch,
                **({"shift": change} if capital is not None else {}),
            },
            place=realm.capital_entity_id if realm is not None and realm.capital_entity_id else None,
            terms=[Term("rules.historiography.pride_order" if row.pride else "rules.historiography.grievance_unrest", change)] if capital is not None else [],
        )
    return True


async def relive(ctx: TickContext, tally: HistoryTally) -> None:
    table = ctx.rules.historiography
    for row in list(await ctx.session.scalars(select(CommemorationRow).where(CommemorationRow.strength > 0).order_by(CommemorationRow.holder_entity_id))):
        collection = await ctx.session.get(CollectionRow, row.collection_id)
        age = ctx.epoch - collection.start_epoch if collection is not None else 0
        if collection is None or held(row.holder_entity_id) or age <= 0 or age % table.commemorate_every:
            continue
        await keep_anniversary(ctx, row, collection, tally)


async def remember_loss(ctx: TickContext, polity_id: int, region_id: int) -> LostLandRow | None:
    if held(polity_id):
        return None
    row = await ctx.session.get(LostLandRow, (polity_id, region_id))
    if row is None:
        row = LostLandRow(claimant_entity_id=polity_id, region_entity_id=region_id, strength=PERCENT * 7 // 10, lost_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    elif "strength" not in row.locked:
        row.strength, row.lost_epoch = max(row.strength, PERCENT * 7 // 10), ctx.epoch
    await ctx.session.flush()
    return row


async def press_lost_lands(ctx: TickContext, tally: HistoryTally) -> None:
    table = ctx.rules.historiography
    for row in list(await ctx.session.scalars(select(LostLandRow).where(LostLandRow.strength > 0).order_by(LostLandRow.claimant_entity_id))):
        if held(row.claimant_entity_id):
            continue
        holder = await ctx.session.scalar(
            select(PolityTerritoryRow.polity_entity_id).where(PolityTerritoryRow.region_entity_id == row.region_entity_id).limit(1)
        )
        if holder == row.claimant_entity_id:
            await ctx.session.delete(row)
            continue
        kept = await ctx.session.scalar(
            select(func.count()).select_from(CommemorationRow).where(CommemorationRow.holder_entity_id == row.claimant_entity_id, CommemorationRow.strength > 0)
        )
        shift(row, "strength", -table.lost_land_fade + (1 if kept else 0))
        if holder is None or row.strength < table.irredentist_claim_at or row.claimed_epoch is not None:
            continue
        ctx.session.add(
            CasusBelliRow(
                holder_entity_id=row.claimant_entity_id,
                target_entity_id=holder,
                kind=CasusBelliKind.CLAIM,
                source_node_id=row.region_entity_id,
                justification=row.strength,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        row.claimed_epoch = ctx.epoch
        tally.claims += 1
        await record_incident(
            ctx,
            "history.irredentism",
            roles={IncidentRole.ACTOR: row.claimant_entity_id, IncidentRole.TARGET: holder, IncidentRole.PLACE: row.region_entity_id},
            facts={"claim_strength": row.strength},
            place=row.region_entity_id,
            terms=[Term("rules.historiography.irredentist_claim_at", table.irredentist_claim_at)],
        )
    await ctx.session.flush()

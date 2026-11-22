from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.polity import RANK_ORDER
from aerona.catalog.titles import CHARGES, RANK_WORDS, SEAT_RANKS, TIER_RANKS, TINCTURES
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import ClaimRow, VassalageRow
from aerona.db.tables.titles import DeJureLinkRow, TitleHolderRow, TitleProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import ClaimBasis, LawKind, OfficeKind
from aerona.domain.enums.renown import Currency
from aerona.domain.enums.statecraft import SubjectKind
from aerona.domain.enums.titles import TitleTenure, TitleTier
from aerona.domain.enums.transform import TransformKind
from aerona.domain.models.entity_stats import TitleStats
from aerona.engine.context import TickContext
from aerona.engine.environment.knowledge import charted_share
from aerona.engine.mortal.kin import children_of
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.formation import found_polity
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats
from aerona.engine.recording.record import record
from aerona.engine.renown.currencies import bump, purse_of
from aerona.engine.transform.record import blocked, record_transformation

HOLDER = "holder_node_id"
OFFICE_HOLDER = "holder_entity_id"
LIEGE = "de_jure_liege_entity_id"
DRIFT = "drift"
RANK = "rank"
EQUAL_SPLIT = "equal"
POWER = 3


@dataclass
class TitleTally:
    founded: int = 0
    passed: int = 0
    drifted: int = 0
    claimed: int = 0
    usurped: int = 0
    created: int = 0
    dormant: int = 0
    restored: int = 0
    unions: int = 0
    partitioned: int = 0


def rank_of(tier: int) -> TitleTier:
    return TIER_RANKS[min(max(tier, 0), len(TIER_RANKS) - 1)]


def rank_index(rank: TitleTier) -> int:
    return RANK_ORDER.index(rank) if rank in RANK_ORDER else 0


@memoized(TitleProfileRow)
async def first_title(session: AsyncSession, realm_id: int) -> TitleProfileRow | None:
    found: TitleProfileRow | None = await session.scalar(
        select(TitleProfileRow)
        .where(TitleProfileRow.polity_entity_id == realm_id, TitleProfileRow.destroyed_epoch.is_(None))
        .order_by(TitleProfileRow.title_entity_id)
        .limit(1)
    )
    return found


async def primary_title(ctx: TickContext, realm_id: int) -> TitleProfileRow | None:
    return await first_title(ctx.session, realm_id)


@memoized(DeJureLinkRow)
async def lands_by_title(session: AsyncSession) -> dict[int, frozenset[int]]:
    found: dict[int, set[int]] = {}
    for title_id, member_id in await session.execute(select(DeJureLinkRow.title_entity_id, DeJureLinkRow.member_entity_id)):
        found.setdefault(title_id, set()).add(member_id)
    return {title_id: frozenset(members) for title_id, members in found.items()}


async def de_jure_lands(ctx: TickContext, title_id: int) -> set[int]:
    return set((await lands_by_title(ctx.session)).get(title_id, frozenset()))


def emblem_of(ctx: TickContext, seed: str) -> str:
    rng = ctx.rng(seed)
    return f"{rng.pick(TINCTURES)} {rng.pick(CHARGES)} on {rng.pick(TINCTURES)}"


async def record_holder(ctx: TickContext, title: TitleProfileRow, holder_id: int | None, tenure: TitleTenure) -> None:
    previous = await ctx.session.scalar(
        select(TitleHolderRow)
        .where(TitleHolderRow.title_entity_id == title.title_entity_id, TitleHolderRow.until_epoch.is_(None))
        .order_by(TitleHolderRow.id.desc())
        .limit(1)
    )
    if previous is not None:
        previous.until_epoch = ctx.epoch
    title.holder_node_id = holder_id
    if holder_id is not None:
        ctx.session.add(TitleHolderRow(title_entity_id=title.title_entity_id, holder_node_id=holder_id, tenure=tenure, since_epoch=ctx.epoch))


async def regalia_of(ctx: TickContext, realm_id: int) -> list[int]:
    return list(
        await ctx.session.scalars(
            select(ItemProfileRow.item_entity_id).where(ItemProfileRow.regalia_of_entity_id == realm_id).order_by(ItemProfileRow.item_entity_id)
        )
    )


async def found_title(ctx: TickContext, realm: Realm, rank: TitleTier, tenure: TitleTenure, lands: set[int]) -> TitleProfileRow:
    entity = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.TITLE,
            name=f"the {RANK_WORDS[rank]} of {realm.entity.name}",
            body=f"The {RANK_WORDS[rank].lower()} held by the rulers of {realm.entity.name}.",
            stats=TitleStats(prestige=ctx.rules.titles.rank_prestige * (rank_index(rank) + 1), territory=len(lands)),
            power=POWER,
            world_id=realm.entity.world_id,
            subtype=RANK_WORDS[rank].lower(),
        ),
    )
    row = TitleProfileRow(
        title_entity_id=entity.id,
        rank=rank,
        polity_entity_id=realm.entity.id,
        capital_entity_id=realm.profile.capital_entity_id,
        emblem=emblem_of(ctx, seed_of("title.emblem", entity.id)),
        prestige=min(PERCENT, ctx.rules.titles.rank_prestige * (rank_index(rank) + 1)),
        regalia=await regalia_of(ctx, realm.entity.id),
        drift={},
        created_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    for land in sorted(lands):
        ctx.session.add(DeJureLinkRow(title_entity_id=entity.id, member_entity_id=land, since_epoch=ctx.epoch))
    await record_holder(ctx, row, realm.ruler_id, tenure)
    await ctx.session.flush()
    await record_transformation(ctx, TransformKind.TITLE_RAISED, realm.entity.id, entity.id)
    return row


async def seed_titles(ctx: TickContext, book: RealmBook, tally: TitleTally) -> None:
    linked = set(await ctx.session.scalars(select(DeJureLinkRow.member_entity_id)))
    for realm in book.realms.values():
        if held(realm.entity.id) or await primary_title(ctx, realm.entity.id) is not None or await blocked(ctx, TransformKind.TITLE_RAISED, realm.entity.id):
            continue
        lands = set(realm.territory) - linked
        await found_title(ctx, realm, rank_of(realm.profile.tier), TitleTenure.FOUNDED, lands)
        linked |= lands
        tally.founded += 1


async def follow_rulers(ctx: TickContext, book: RealmBook, tally: TitleTally) -> None:
    for realm in book.realms.values():
        title = await primary_title(ctx, realm.entity.id)
        if title is None or held(title.title_entity_id):
            continue
        office = realm.office(OfficeKind.RULER)
        if HOLDER in (title.locked or []) and title.holder_node_id is not None:
            if office is not None and office.holder_entity_id != title.holder_node_id and OFFICE_HOLDER not in (office.locked or []):
                office.holder_entity_id, office.since_epoch = title.holder_node_id, ctx.epoch
            continue
        if realm.ruler_id != title.holder_node_id:
            if title.holder_node_id is not None:
                tally.partitioned += await partition(ctx, book, realm, title.holder_node_id, realm.ruler_id)
            await record_holder(ctx, title, realm.ruler_id, TitleTenure.INHERITED)
            tally.passed += 1


async def partition(ctx: TickContext, book: RealmBook, realm: Realm, late_id: int, heir_id: int | None) -> int:
    split = await law_param(ctx.session, realm.entity.id, LawKind.INHERITANCE_SPLIT, "split")
    if split != EQUAL_SPLIT:
        return 0
    heirs = [
        child
        for child in await children_of(ctx.session, late_id)
        if child != heir_id and await living_entity(ctx.session, child) is not None and not held(child)
    ]
    lesser = list(
        await ctx.session.scalars(
            select(TitleProfileRow)
            .where(TitleProfileRow.holder_node_id == late_id, TitleProfileRow.polity_entity_id.is_(None), TitleProfileRow.destroyed_epoch.is_(None))
            .order_by(TitleProfileRow.title_entity_id)
        )
    )
    split_off = 0
    for title, heir in zip(lesser, heirs, strict=False):
        if HOLDER in (title.locked or []):
            continue
        lands = await de_jure_lands(ctx, title.title_entity_id)
        towns = [book.entities[member] for member in realm.members if member in book.entities and book.entities[member].location_id in lands]
        await record_holder(ctx, title, heir, TitleTenure.INHERITED)
        if not towns:
            continue
        share = await found_polity(ctx, book, towns[0])
        for town in towns:
            row = realm.members.pop(town.id, None)
            if row is not None:
                row.polity_entity_id = share.entity.id
                share.members[town.id] = row
        for land in lands & set(realm.territory):
            place = realm.territory.pop(land)
            place.polity_entity_id = share.entity.id
            share.territory[land] = place
        office = share.office(OfficeKind.RULER)
        if office is not None:
            office.holder_entity_id = heir
        title.polity_entity_id = share.entity.id
        await record(
            ctx,
            "titles.partition",
            roles={IncidentRole.PREDECESSOR: realm.entity.id, IncidentRole.PRODUCT: share.entity.id, IncidentRole.HEIR: heir},
            facts={"title": title.title_entity_id, "towns": len(towns), "lands": len(lands & set(share.territory))},
            place=towns[0].id,
        )
        split_off += 1
    return split_off


async def bind_lieges(ctx: TickContext, book: RealmBook) -> None:
    for vassal_id, bond in book.vassals.items():
        title = await primary_title(ctx, vassal_id)
        lord = await primary_title(ctx, bond.overlord_entity_id)
        if title is None or lord is None or LIEGE in (title.locked or []) or rank_index(lord.rank) <= rank_index(title.rank):
            continue
        title.de_jure_liege_entity_id = lord.title_entity_id


async def rightful_holds(ctx: TickContext, book: RealmBook, title_id: int, land: int) -> bool:
    owner = await ctx.session.get(TitleProfileRow, title_id)
    rightful = book.realms.get(owner.polity_entity_id) if owner is not None and owner.polity_entity_id is not None else None
    return rightful is not None and land in rightful.territory


async def drift_lands(ctx: TickContext, book: RealmBook, tally: TitleTally) -> None:
    table = ctx.rules.titles
    for realm in book.realms.values():
        title = await primary_title(ctx, realm.entity.id)
        if title is None or DRIFT in (title.locked or []) or held(title.title_entity_id):
            continue
        mine = await de_jure_lands(ctx, title.title_entity_id)
        drift = dict(title.drift or {})
        for land in realm.territory:
            if land in mine:
                continue
            link = await ctx.session.scalar(select(DeJureLinkRow).where(DeJureLinkRow.member_entity_id == land).limit(1))
            if link is not None and (link.locked or await rightful_holds(ctx, book, link.title_entity_id, land)):
                continue
            drift[str(land)] = drift.get(str(land), 0) + 1
            if drift[str(land)] < table.drift_epochs:
                continue
            if link is not None:
                await ctx.session.delete(link)
            ctx.session.add(DeJureLinkRow(title_entity_id=title.title_entity_id, member_entity_id=land, since_epoch=ctx.epoch))
            drift.pop(str(land))
            tally.drifted += 1
        title.drift = {key: value for key, value in drift.items() if int(key) in realm.territory}


async def press_claims(ctx: TickContext, book: RealmBook, tally: TitleTally) -> None:
    table = ctx.rules.titles
    titles = list(await ctx.session.scalars(select(TitleProfileRow).where(TitleProfileRow.destroyed_epoch.is_(None)).order_by(TitleProfileRow.title_entity_id)))
    for realm in book.realms.values():
        ruler = realm.ruler_id
        if ruler is None or held(ruler):
            continue
        for title in titles:
            if title.holder_node_id == ruler or title.polity_entity_id is None or title.polity_entity_id == realm.entity.id:
                continue
            if not set(realm.territory) & await de_jure_lands(ctx, title.title_entity_id):
                continue
            exists = await ctx.session.scalar(
                select(ClaimRow.id).where(ClaimRow.claimant_entity_id == ruler, ClaimRow.title_entity_id == title.title_entity_id).limit(1)
            )
            if exists is None:
                charted = await charted_share(ctx.session, ctx.rules, realm.entity.id, await de_jure_lands(ctx, title.title_entity_id))
                drawn = 1 + ctx.rules.discovery.charted_claim_pct / PERCENT if charted * 2 >= 1 else 1
                ctx.session.add(
                    ClaimRow(
                        claimant_entity_id=ruler,
                        polity_entity_id=title.polity_entity_id,
                        title_entity_id=title.title_entity_id,
                        basis=ClaimBasis.DE_JURE,
                        strength=min(PERCENT, round_half_up(table.claim_strength * drawn)),
                        since_epoch=ctx.epoch,
                        locked=[],
                    )
                )
                tally.claimed += 1


async def share_of(ctx: TickContext, realm: Realm, title_id: int) -> float:
    lands = await de_jure_lands(ctx, title_id)
    return len(lands & set(realm.territory)) * PERCENT / len(lands) if lands else 0.0


async def usurp_and_create(ctx: TickContext, book: RealmBook, tally: TitleTally) -> None:
    table = ctx.rules.titles
    for realm in book.realms.values():
        ruler = realm.ruler_id
        own = await primary_title(ctx, realm.entity.id)
        if ruler is None or own is None or held(ruler) or held(own.title_entity_id):
            continue
        wanted = rank_of(realm.profile.tier)
        if rank_index(wanted) > rank_index(own.rank) and RANK not in (own.locked or []) and not await blocked(ctx, TransformKind.TITLE_RAISED, realm.entity.id):
            lands = await de_jure_lands(ctx, own.title_entity_id) | set(realm.territory)
            higher = await found_title(ctx, realm, wanted, TitleTenure.CREATED, lands - await de_jure_lands(ctx, own.title_entity_id))
            purse = await purse_of(ctx.session, ruler, ctx.epoch)
            if purse is not None:
                bump(purse, Currency.PRESTIGE, -table.creation_prestige)
            own.polity_entity_id, own.de_jure_liege_entity_id = None, higher.title_entity_id
            await record(
                ctx,
                "titles.created",
                roles={IncidentRole.SUBJECT: realm.entity.id, IncidentRole.LEADER: ruler, IncidentRole.PRODUCT: higher.title_entity_id},
                facts={"rank": wanted, "prestige": table.creation_prestige},
                place=realm.profile.capital_entity_id,
            )
            tally.created += 1
            continue
        lieges = await ctx.session.scalars(
            select(TitleProfileRow).where(TitleProfileRow.title_entity_id == own.de_jure_liege_entity_id, TitleProfileRow.destroyed_epoch.is_(None))
        )
        for liege in list(lieges):
            if liege.holder_node_id == ruler or HOLDER in (liege.locked or []) or held(liege.title_entity_id):
                continue
            if liege.capital_entity_id is not None and liege.capital_entity_id not in realm.members:
                continue
            if await share_of(ctx, realm, liege.title_entity_id) < table.creation_share_pct:
                continue
            previous = liege.holder_node_id
            await record_holder(ctx, liege, ruler, TitleTenure.USURPED)
            realm.profile.legitimacy = max(0, realm.profile.legitimacy - table.usurp_legitimacy)
            await record(
                ctx,
                "titles.usurped",
                roles={IncidentRole.ACTOR: realm.entity.id, IncidentRole.LEADER: ruler, IncidentRole.PREDECESSOR: previous},
                facts={"title": liege.title_entity_id, "legitimacy_lost": table.usurp_legitimacy},
                place=realm.profile.capital_entity_id,
            )
            tally.usurped += 1


async def dormancy(ctx: TickContext, book: RealmBook, tally: TitleTally) -> None:
    table = ctx.rules.titles
    for title in list(
        await ctx.session.scalars(select(TitleProfileRow).where(TitleProfileRow.destroyed_epoch.is_(None)).order_by(TitleProfileRow.title_entity_id))
    ):
        if held(title.title_entity_id) or title.rank in SEAT_RANKS:
            continue
        realm = await living_entity(ctx.session, title.polity_entity_id) if title.polity_entity_id is not None else None
        if title.polity_entity_id is not None and realm is None and HOLDER not in (title.locked or []):
            title.polity_entity_id = None
            await record_holder(ctx, title, None, TitleTenure.INHERITED)
            tally.dormant += 1
            continue
        if title.holder_node_id is not None or title.polity_entity_id is not None:
            continue
        for candidate in book.realms.values():
            if candidate.ruler_id is None or held(candidate.entity.id):
                continue
            if await share_of(ctx, candidate, title.title_entity_id) < table.creation_share_pct:
                continue
            if not ctx.rng(seed_of("title.restore", title.title_entity_id, candidate.entity.id, ctx.epoch)).chance(table.restore_pct):
                continue
            await record_holder(ctx, title, candidate.ruler_id, TitleTenure.RESTORED)
            await record(
                ctx,
                "titles.restored",
                roles={IncidentRole.ACTOR: candidate.entity.id, IncidentRole.LEADER: candidate.ruler_id},
                facts={"title": title.title_entity_id, "chance": table.restore_pct},
                place=candidate.profile.capital_entity_id,
            )
            tally.restored += 1
            break


async def join_crowns(ctx: TickContext, book: RealmBook, realms: list[Realm]) -> None:
    senior = max(realms, key=lambda realm: (realm.profile.tier, len(realm.territory), -realm.entity.id))
    for realm in realms:
        if realm.entity.id == senior.entity.id or realm.entity.id in book.vassals or held(realm.entity.id):
            continue
        row = VassalageRow(
            vassal_entity_id=realm.entity.id,
            overlord_entity_id=senior.entity.id,
            since_epoch=ctx.epoch,
            kind=SubjectKind.PERSONAL_UNION,
            tribute_pct=0,
            levy_pct=0,
            locked=[],
        )
        ctx.session.add(row)
        book.vassals[realm.entity.id] = row
    await ctx.session.flush()


async def unions(ctx: TickContext, book: RealmBook, tally: TitleTally) -> None:
    holders: dict[int, list[Realm]] = {}
    for realm in book.realms.values():
        title = await primary_title(ctx, realm.entity.id)
        if title is not None and title.holder_node_id is not None:
            holders.setdefault(title.holder_node_id, []).append(realm)
    for mortal_id, realms in holders.items():
        if len(realms) < 2 or held(mortal_id) or not ctx.rng(seed_of("title.union", mortal_id, ctx.epoch)).chance(ctx.rules.titles.union_pct):
            continue
        for realm in realms:
            office = realm.office(OfficeKind.RULER)
            if office is not None and office.holder_entity_id != mortal_id and OFFICE_HOLDER not in (office.locked or []):
                office.holder_entity_id, office.since_epoch = mortal_id, ctx.epoch
                tally.unions += 1
        await join_crowns(ctx, book, realms)


async def tally_territory(ctx: TickContext) -> None:
    for title in list(await ctx.session.scalars(select(TitleProfileRow).order_by(TitleProfileRow.title_entity_id))):
        entity = await ctx.session.get(EntityRow, title.title_entity_id)
        if entity is not None and entity.status is EntityStatus.CANON and not held(entity.id):
            set_stats(entity, prestige=title.prestige, territory=len(await de_jure_lands(ctx, title.title_entity_id)))


async def tend_titles(ctx: TickContext, tally: TitleTally) -> None:
    book = await RealmBook.load(ctx.session)
    await seed_titles(ctx, book, tally)
    await follow_rulers(ctx, book, tally)
    await bind_lieges(ctx, book)
    await drift_lands(ctx, book, tally)
    await press_claims(ctx, book, tally)
    await usurp_and_create(ctx, book, tally)
    await dormancy(ctx, book, tally)
    await unions(ctx, book, tally)
    await tally_territory(ctx)

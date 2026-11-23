from sqlalchemy import func, select

from aerona.catalog.catch import grounds_in
from aerona.catalog.life.couplings import FACTION_SPEECH
from aerona.catalog.tongues import SIGN_CAUSES, SOCIOLECTS
from aerona.constants.units import PERCENT
from aerona.db.repositories.lexicon import add_lexeme
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.belonging import HeldIdentityRow
from aerona.db.tables.body import MaimedCohortRow
from aerona.db.tables.couplings import SignOriginRow, SociolectRow
from aerona.db.tables.crafts import CatchGroundRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.faith import CultHoldingRow, CultTenetRow
from aerona.db.tables.folkways import PurityRankRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.youth import YouthGroupRow
from aerona.db.write_guard import held
from aerona.domain.enums.belonging import IdentityLayer
from aerona.domain.enums.body import MaimedKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import PartOfSpeech
from aerona.domain.enums.couplings import SignCause, SociolectKind
from aerona.domain.enums.crafts import CatchGround, CatchMedium
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faith import HoldingKind, TenetKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.tongues import LanguageModality, WordRegister
from aerona.domain.models.entity_stats import LanguageStats
from aerona.engine.context import TickContext
from aerona.engine.economy.routes import link_partners
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore.language import learn_second
from aerona.engine.lore.research import has_technique
from aerona.engine.primitives.language_profile import language_profile
from aerona.engine.primitives.numbers import clamp_percent, scaled_cap
from aerona.engine.primitives.queries import canon, connect, spoken_language
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import record as record_incident

SEA_GROUNDS = grounds_in(CatchMedium.WATER)
HUNT_GROUNDS = grounds_in(CatchMedium.LAND)


async def cohort_share(ctx: TickContext, community: EntityRow, kind: MaimedKind) -> int:
    count = await ctx.session.scalar(select(MaimedCohortRow.count).where(MaimedCohortRow.community_entity_id == community.id, MaimedCohortRow.kind == kind))
    population = stat(community, "population") or 0
    return (count or 0) * PERCENT // population if population > 0 else 0


async def grounds_owned(ctx: TickContext, owner_id: int, grounds: tuple[CatchGround, ...]) -> int:
    found = await ctx.session.scalar(
        select(func.count()).select_from(CatchGroundRow).where(CatchGroundRow.owner_node_id == owner_id, CatchGroundRow.ground.in_(grounds))
    )
    return int(found or 0)


async def silent_cults(ctx: TickContext) -> set[int]:
    monks = select(CultHoldingRow.cult_entity_id).where(CultHoldingRow.kind == HoldingKind.MONASTERY)
    learning = select(CultTenetRow.cult_entity_id).where(CultTenetRow.tenet == TenetKind.MONASTIC_LEARNING)
    return set(await ctx.session.scalars(select(EntityRow.id).where(EntityRow.id.in_(monks), EntityRow.id.in_(learning))))


async def crossing_tongues(ctx: TickContext) -> dict[int, set[int]]:
    partners = await link_partners(ctx)
    found: dict[int, set[int]] = {}
    for here in sorted(partners):
        tongues = {tongue.id for there in [here, *sorted(partners[here])] if (tongue := await spoken_language(ctx.session, there)) is not None}
        found[here] = tongues
    return found


async def sign_cause(ctx: TickContext, community: EntityRow, silent: set[int], crossings: dict[int, set[int]] | None = None) -> SignCause | None:
    table = ctx.rules.couplings
    if community.id in silent:
        return SignCause.SILENCE_VOW
    met = (crossings or {}).get(community.id, set())
    if len(met) >= ctx.rules.tongues.trade_sign_tongues and ctx.rng(f"sign.trade.{community.id}.{ctx.epoch}").chance(ctx.rules.tongues.trade_sign_pct):
        return SignCause.TRADE
    if community.entity_type in (EntityType.PEOPLE, EntityType.SETTLEMENT):
        if await cohort_share(ctx, community, MaimedKind.DEAF) >= table.sign_share_pct:
            return SignCause.DEAFNESS
        if await cohort_share(ctx, community, MaimedKind.MUTE) >= table.sign_share_pct:
            return SignCause.MUTILATION
        if await grounds_owned(ctx, community.id, HUNT_GROUNDS) >= table.sign_hunting_grounds:
            return SignCause.HUNTING_SILENCE
    return None


async def signers(ctx: TickContext) -> set[int]:
    return set(await ctx.session.scalars(select(SignOriginRow.community_entity_id).where(SignOriginRow.community_entity_id.is_not(None))))


async def make_sign_language(ctx: TickContext, community: EntityRow, cause: SignCause) -> EntityRow:
    spoken = await spoken_language(ctx.session, community.id)
    language = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.LANGUAGE,
            name=await NameRepository(ctx.session).unique_name(f"{community.name} Signing"),
            body=f"The signed language of {community.name}, made by signs instead of voices.",
            stats=LanguageStats(spread=0, complexity=PERCENT // 2, sacredness=PERCENT // 2 if cause is SignCause.SILENCE_VOW else 0),
            power=max(1, community.power_level // 2),
            world_id=community.world_id,
        ),
    )
    profile = await language_profile(ctx.session, language, spoken.id if spoken is not None else None)
    profile.modality = LanguageModality.SIGN
    ctx.session.add(SignOriginRow(language_entity_id=language.id, community_entity_id=community.id, cause=cause, since_epoch=ctx.epoch, locked=[]))
    await connect(ctx.session, community.id, language.id, BondKind.SPEAKS, ctx.epoch, description="signs it")
    await ctx.session.flush()
    return language


@reads(
    "people.population",
    "settlement.population",
    "table.bonds",
    "table.catch_grounds",
    "table.cult_holdings",
    "table.cult_tenets",
    "table.entities",
    "table.maimed_cohorts",
    "table.nodes",
    "table.sign_origins",
    "table.trade_flows",
    "table.trade_route_profiles",
    "table.trade_route_regions",
    "table.trade_route_tolls",
    "trade_route.culture",
)
@writes("table.bonds", "table.entities", "table.language_profiles", "table.sign_origins")
async def sign_languages(ctx: TickContext) -> None:
    known = await signers(ctx)
    silent = await silent_cults(ctx)
    crossings = await crossing_tongues(ctx)
    made = 0
    communities = ctx.rng("sign_languages.order").shuffled(await canon(ctx.session, [EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.CULT]))
    limit = scaled_cap(ctx.rules.couplings.sign_per_epoch, ctx.rules.couplings.sign_community_divisor, len(communities))
    for community in communities:
        if community.id in known or held(community.id) or made >= limit:
            continue
        cause = await sign_cause(ctx, community, silent, crossings)
        if cause is None:
            continue
        language = await make_sign_language(ctx, community, cause)
        made += 1
        await record_incident(ctx, "language.signed", roles={IncidentRole.SUBJECT: community.id, IncidentRole.PRODUCT: language.id}, facts={"cause": cause})
        if SIGN_CAUSES[cause].spreads_on_routes:
            await spread_on_routes(ctx, community, language)
    ctx.count("sign_languages", made)


async def spread_on_routes(ctx: TickContext, community: EntityRow, language: EntityRow) -> int:
    partners = (await link_partners(ctx)).get(community.id, {})
    taught = 0
    for partner in sorted(partners):
        if held(partner):
            continue
        await learn_second(ctx, partner, language.id, ctx.rules.tongues.trade_sign_pct)
        taught += 1
    await record_incident(ctx, "language.sign_born", roles={IncidentRole.SUBJECT: community.id, IncidentRole.PRODUCT: language.id}, facts={"reach": taught})
    return taught


async def speech_groups(ctx: TickContext) -> list[tuple[EntityRow, SociolectKind]]:
    found: list[tuple[EntityRow, SociolectKind]] = []
    for profile, faction in await ctx.session.execute(
        select(FactionProfileRow, EntityRow)
        .join(EntityRow, EntityRow.id == FactionProfileRow.faction_entity_id)
        .where(EntityRow.status == EntityStatus.CANON, FactionProfileRow.kind.in_(tuple(FACTION_SPEECH)))
        .order_by(EntityRow.id)
    ):
        found.append((faction, FACTION_SPEECH[profile.kind]))
    for polity in await canon(ctx.session, [EntityType.POLITY]):
        found.append((polity, SociolectKind.COURT))
    table = ctx.rules.couplings
    classed = select(HeldIdentityRow.holder_entity_id).where(HeldIdentityRow.layer == IdentityLayer.CLASS, HeldIdentityRow.salience >= table.sociolect_salience)
    castes = select(PurityRankRow.people_entity_id).where(PurityRankRow.endogamous.is_(True))
    for town in await canon(ctx.session, [EntityType.SETTLEMENT]):
        if await grounds_owned(ctx, town.id, SEA_GROUNDS) >= table.sign_hunting_grounds:
            found.append((town, SociolectKind.SAILORS))
    for community in await ctx.session.scalars(
        select(EntityRow).where(EntityRow.id.in_(classed), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    ):
        found.append((community, SociolectKind.CLASS))
    for people in await ctx.session.scalars(select(EntityRow).where(EntityRow.id.in_(castes), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)):
        found.append((people, SociolectKind.CASTE))
    young = select(YouthGroupRow.settlement_entity_id)
    for town in await ctx.session.scalars(select(EntityRow).where(EntityRow.id.in_(young), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)):
        found.append((town, SociolectKind.YOUTH))
    for army in await canon(ctx.session, [EntityType.ARMY]):
        found.append((army, SociolectKind.SOLDIERS))
    return found


async def speech_of(ctx: TickContext, group: EntityRow) -> EntityRow | None:
    holders = (group.location_id, group.id) if group.entity_type is EntityType.FACTION else (group.id, group.affiliated_entity_id, group.location_id)
    for holder in holders:
        found = await spoken_language(ctx.session, holder) if holder is not None else None
        if found is not None:
            return found
    return None


async def lift_identity(ctx: TickContext, row: SociolectRow) -> None:
    layer = SOCIOLECTS[row.kind].layer
    identity = await ctx.session.get(HeldIdentityRow, (row.holder_entity_id, layer))
    if identity is None or "salience" in identity.locked:
        return
    floor = row.salience * ctx.rules.couplings.sociolect_identity_pct // PERCENT
    identity.salience = clamp_percent(max(identity.salience, floor))


async def keep_secrecy(ctx: TickContext, row: SociolectRow) -> None:
    profile = await ctx.session.get(FactionProfileRow, row.holder_entity_id)
    if profile is not None and "secrecy" not in profile.locked:
        profile.secrecy = clamp_percent(max(profile.secrecy, row.salience * ctx.rules.couplings.cant_secrecy_pct // PERCENT))


@reads(
    "table.army_profiles",
    "table.bonds",
    "table.catch_grounds",
    "table.entities",
    "table.faction_profiles",
    "table.held_identities",
    "table.holder_techniques",
    "table.lexemes",
    "table.nodes",
    "table.purity_ranks",
    "table.sociolects",
)
@writes("table.faction_profiles", "table.held_identities", "table.lexemes", "table.sociolects")
async def sociolects(ctx: TickContext) -> None:
    table = ctx.rules.couplings
    rows = {(row.holder_entity_id, row.kind): row for row in await ctx.session.scalars(select(SociolectRow).where(SociolectRow.faded_epoch.is_(None)))}
    groups = await speech_groups(ctx)
    present = {(group.id, kind) for group, kind in groups}
    for group, kind in groups:
        if held(group.id) or (group.id, kind) in rows:
            continue
        language = await speech_of(ctx, group)
        if language is None:
            continue
        row = SociolectRow(
            language_entity_id=language.id,
            holder_entity_id=group.id,
            kind=kind,
            prestige=SOCIOLECTS[kind].prestige,
            secret=kind is SociolectKind.CANT,
            salience=table.sociolect_start,
            since_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(row)
        rows[(group.id, kind)] = row
        ctx.count("sociolects_formed")
    for key, row in sorted(rows.items()):
        if held(row.holder_entity_id) or (row.id is None and key not in present):
            continue
        if key not in present and "faded_epoch" not in row.locked:
            row.faded_epoch = ctx.epoch
            ctx.count("sociolects_faded")
            continue
        levelled = await has_technique(ctx.session, row.holder_entity_id, Technique.PRINTING)
        if "salience" not in row.locked:
            row.salience = clamp_percent(row.salience + (-table.sociolect_levelling if levelled else table.sociolect_growth))
        if row.salience == 0 and "faded_epoch" not in row.locked:
            row.faded_epoch = ctx.epoch
            ctx.count("sociolects_faded")
            continue
        await lift_identity(ctx, row)
        if row.secret:
            await keep_secrecy(ctx, row)
        if SOCIOLECTS[row.kind].coins_technical:
            await coin_technical(ctx, row)
        if SOCIOLECTS[row.kind].carries_words:
            await carry_words(ctx, row)
    await ctx.session.flush()


async def coin_technical(ctx: TickContext, row: SociolectRow) -> LexemeRow | None:
    if not ctx.rng(f"sociolect.technical.{row.holder_entity_id}.{row.kind.value}.{ctx.epoch}").chance(ctx.rules.tongues.technical_pct):
        return None
    words = list(
        await ctx.session.scalars(
            select(LexemeRow)
            .where(
                LexemeRow.language_entity_id == row.language_entity_id, LexemeRow.register == WordRegister.COMMON, LexemeRow.part_of_speech == PartOfSpeech.NOUN
            )
            .order_by(LexemeRow.id)
        )
    )
    if not words:
        return None
    word = ctx.rng(f"sociolect.technical.word.{row.holder_entity_id}.{row.kind.value}.{ctx.epoch}").pick(words)
    word.register = WordRegister.TECHNICAL
    ctx.count("technical_words")
    return word


async def carry_words(ctx: TickContext, row: SociolectRow) -> int:
    army = await ctx.session.get(ArmyProfileRow, row.holder_entity_id)
    foe = await ctx.session.get(EntityRow, army.target_entity_id) if army is not None and army.target_entity_id is not None else None
    met = await speech_of(ctx, foe) if foe is not None else None
    if met is None or met.id == row.language_entity_id:
        return 0
    known = set(await ctx.session.scalars(select(LexemeRow.word_key).where(LexemeRow.language_entity_id == row.language_entity_id)))
    offered = [
        word
        for word in await ctx.session.scalars(
            select(LexemeRow).where(LexemeRow.language_entity_id == met.id, LexemeRow.register == WordRegister.COMMON).order_by(LexemeRow.id)
        )
        if word.word_key not in known
    ]
    carried = ctx.rng(f"sociolect.carry.{row.holder_entity_id}.{row.kind.value}.{ctx.epoch}").sample(
        offered, min(len(offered), ctx.rules.tongues.carried_words)
    )
    for word in carried:
        await add_lexeme(
            ctx.session,
            LexemeRow(
                language_entity_id=row.language_entity_id,
                word=word.word,
                meaning=word.meaning,
                part_of_speech=word.part_of_speech,
                etymology=f"carried back by soldiers from {met.name}",
                added_by_kind=ActorKind.ENGINE,
                added_by_node_id=None,
                epoch=ctx.epoch,
                register=WordRegister.COMMON,
            ),
        )
    ctx.count("words_carried", len(carried))
    return len(carried)

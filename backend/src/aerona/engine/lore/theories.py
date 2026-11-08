from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.theories import DOMAINS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import HolderLevelRow, InstitutionRow
from aerona.db.tables.discovery import ParadigmShiftRow, TheoryAdherentRow, TheoryAnomalyRow, TheoryProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import CultureValueRow, SkillRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.discovery import AnomalyKind, TheoryDomain
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind, ValueAxis
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.renown import ReputationAxis
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import TheoryStats
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.lore.blueprints import books_of
from aerona.engine.lore.research_depth import RESEARCHERS, living_researchers, trade_partners
from aerona.engine.lore.truth import CONTRARY, ruling
from aerona.engine.mind.ethics import church_of
from aerona.engine.notes import note
from aerona.engine.polity.trials import report_crime
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats
from aerona.engine.renown.book import acclaim
from aerona.rules.registry import Rules


async def adhere(ctx: TickContext, theory_id: int, holder_id: int, strength: int, domain: TheoryDomain) -> TheoryAdherentRow:
    row = await ctx.session.get(TheoryAdherentRow, (theory_id, holder_id))
    if row is None:
        orthodox = await ruling(ctx.session, holder_id, domain) is None
        row = TheoryAdherentRow(
            theory_entity_id=theory_id, adherent_entity_id=holder_id, strength=strength, orthodox=orthodox, since_epoch=ctx.epoch, locked=[]
        )
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def create_theory(
    ctx: TickContext, founder: EntityRow, domain: TheoryDomain, name: str, claim: str, *, correctness: int, son_id: int | None = None
) -> EntityRow:
    theory = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.THEORY,
            name=name,
            body=claim,
            stats=TheoryStats(adherents=1, explanatory=ctx.rules.theories.found_strength),
            power=3,
            world_id=founder.world_id,
            subtype=DOMAINS[domain].label.lower(),
            creator_son_id=son_id,
        ),
    )
    rival = await ruling(ctx.session, founder.id, domain)
    shelf = sorted(await books_of(ctx.session, founder.id))
    ctx.session.add(
        TheoryProfileRow(
            theory_entity_id=theory.id,
            domain=domain,
            claim=claim,
            correctness=clamp_int(correctness, 0, PERCENT),
            explanatory_power=ctx.rules.theories.found_strength,
            founder_entity_id=founder.id,
            founding_book_id=shelf[0] if shelf else None,
            rival_entity_id=rival.theory_entity_id if rival is not None else None,
            endorsed_by=[],
            condemned_by=[],
            revealed_by_son_id=son_id,
            updated_epoch=ctx.epoch,
            locked=[],
        )
    )
    await ctx.session.flush()
    await adhere(ctx, theory.id, founder.id, ctx.rules.theories.found_strength, domain)
    return theory


async def found_theories(ctx: TickContext) -> int:
    table = ctx.rules.theories
    levels: dict[int, dict[KnowledgeBranch, int]] = defaultdict(dict)
    for row in await ctx.session.scalars(select(HolderLevelRow)):
        levels[row.holder_entity_id][row.branch] = row.level
    founded = 0
    for community in await living_researchers(ctx.session):
        if held(community.id):
            continue
        for domain, spec in DOMAINS.items():
            if max((levels[community.id].get(branch, 0) for branch in spec.branches), default=0) < table.found_level:
                continue
            if await ruling(ctx.session, community.id, domain) is not None:
                continue
            rng = ctx.rng(f"theory.found.{community.id}.{domain.value}.{ctx.epoch}")
            if not rng.chance(table.found_pct):
                continue
            theory = await create_theory(
                ctx,
                community,
                domain,
                f"The {spec.label.lower()} of {community.name}",
                f"The scholars of {community.name} give their own account of {spec.subject}.",
                correctness=rng.integer(0, PERCENT),
            )
            founded += 1
            await note(
                ctx,
                f"The scholars of {community.name} set out {theory.name}.",
                key="theories.founded",
                ids=[community.id, theory.id],
                kind=ChronicleKind.KNOWLEDGE,
            )
    return founded


async def spread_theories(ctx: TickContext) -> int:
    table = ctx.rules.theories
    spread = 0
    for row in list(await ctx.session.scalars(select(TheoryAdherentRow).order_by(TheoryAdherentRow.theory_entity_id, TheoryAdherentRow.adherent_entity_id))):
        profile = await ctx.session.get(TheoryProfileRow, row.theory_entity_id)
        if profile is None:
            continue
        for partner in sorted(await trade_partners(ctx.session, row.adherent_entity_id)):
            target = await ctx.session.get(EntityRow, partner)
            if target is None or target.entity_type not in RESEARCHERS or target.status is not EntityStatus.CANON or held(partner):
                continue
            if await ctx.session.get(TheoryAdherentRow, (row.theory_entity_id, partner)) is not None:
                continue
            if ctx.rng(f"theory.spread.{row.theory_entity_id}.{partner}.{ctx.epoch}").chance(table.spread_pct):
                await adhere(ctx, row.theory_entity_id, partner, max(1, row.strength // 2), profile.domain)
                spread += 1
    return spread


async def read_theories(ctx: TickContext) -> int:
    taught = 0
    written = await ctx.session.scalars(select(TheoryProfileRow).where(TheoryProfileRow.founding_book_id.is_not(None)))
    for profile in list(written):
        owners = await ctx.session.scalars(
            select(BondRow.source_node_id).where(
                BondRow.target_node_id == profile.founding_book_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE
            )
        )
        for owner_id in list(owners):
            owner = await ctx.session.get(EntityRow, owner_id)
            reader = owner.location_id if owner is not None and owner.entity_type is EntityType.MORTAL else owner_id
            home = await ctx.session.get(EntityRow, reader) if reader is not None else None
            if home is None or home.entity_type not in RESEARCHERS or held(home.id):
                continue
            if await ctx.session.get(TheoryAdherentRow, (profile.theory_entity_id, home.id)) is None:
                await adhere(ctx, profile.theory_entity_id, home.id, ctx.rules.theories.found_strength // 2, profile.domain)
                taught += 1
    return taught


async def abandon(ctx: TickContext) -> int:
    dropped = 0
    for row in list(await ctx.session.scalars(select(TheoryAdherentRow).where(TheoryAdherentRow.strength <= 0))):
        if "strength" not in row.locked and not held(row.adherent_entity_id):
            await ctx.session.delete(row)
            dropped += 1
    await ctx.session.flush()
    return dropped


async def faiths_of(session: AsyncSession, community: EntityRow) -> list[int]:
    people = await people_of(session, community)
    return await church_of(session, people or community)


async def meet_anomalies(ctx: TickContext) -> int:
    table = ctx.rules.theories
    met = 0
    rows = await ctx.session.scalars(select(TheoryAdherentRow).where(TheoryAdherentRow.orthodox.is_(True)).order_by(TheoryAdherentRow.theory_entity_id))
    clean: set[int] = set()
    struck: set[int] = set()
    for row in list(rows):
        profile = await ctx.session.get(TheoryProfileRow, row.theory_entity_id)
        community = await ctx.session.get(EntityRow, row.adherent_entity_id)
        if profile is None or community is None or held(profile.theory_entity_id):
            continue
        chance = table.anomaly_pct * (PERCENT - profile.correctness) / PERCENT
        if set(profile.endorsed_by) & set(await faiths_of(ctx.session, community)):
            chance *= 1 - table.endorsed_anomaly_pct / PERCENT
        rng = ctx.rng(f"theory.anomaly.{profile.theory_entity_id}.{community.id}.{ctx.epoch}")
        if rng.chance(chance):
            kinds = [AnomalyKind.FAILED_PREDICTION, AnomalyKind.OBSERVATION, *([AnomalyKind.CONTRARY_CURE] if profile.domain in CONTRARY else [])]
            ctx.session.add(
                TheoryAnomalyRow(theory_entity_id=profile.theory_entity_id, kind=rng.pick(kinds), weight=1, witness_entity_id=community.id, epoch=ctx.epoch)
            )
            struck.add(profile.theory_entity_id)
            met += 1
        else:
            clean.add(profile.theory_entity_id)
    for theory_id in sorted(clean - struck):
        profile = await ctx.session.get(TheoryProfileRow, theory_id)
        if profile is not None and "explanatory_power" not in profile.locked:
            profile.explanatory_power = clamp_int(profile.explanatory_power + table.explanatory_gain, 0, PERCENT)
    await ctx.session.flush()
    return met


async def weight_against(session: AsyncSession, rules: Rules, theory_id: int, epoch: int) -> int:
    total = await session.scalar(
        select(func.sum(TheoryAnomalyRow.weight)).where(
            TheoryAnomalyRow.theory_entity_id == theory_id, TheoryAnomalyRow.epoch > epoch - rules.theories.anomaly_window
        )
    )
    return int(total or 0)


async def contest_score(ctx: TickContext, community: EntityRow, profile: TheoryProfileRow, *, ruling_now: bool) -> float:
    table = ctx.rules.theories
    knowledge = await ctx.session.get(CultureValueRow, (community.id, ValueAxis.KNOWLEDGE))
    tradition = await ctx.session.get(CultureValueRow, (community.id, ValueAxis.TRADITION))
    evidence = profile.correctness * (1 + (knowledge.value if knowledge is not None else 0) / PERCENT)
    embraced = await ctx.session.scalar(
        select(InstitutionRow.technique).where(InstitutionRow.community_entity_id == community.id, InstitutionRow.embraced.is_(True)).limit(1)
    )
    support = table.institution_bonus * (embraced is not None) + table.institution_bonus * bool(
        set(profile.endorsed_by) & set(await faiths_of(ctx.session, community))
    )
    habit = max(0, tradition.value if tradition is not None else 0) * table.tradition_weight_pct / PERCENT if ruling_now else 0
    return evidence + support + habit + ctx.rng(f"theory.contest.{profile.theory_entity_id}.{community.id}.{ctx.epoch}").integer(0, table.contest_margin)


async def shift_paradigm(ctx: TickContext, community: EntityRow, old: TheoryAdherentRow, new: TheoryAdherentRow, domain: TheoryDomain) -> None:
    old.orthodox, new.orthodox = False, True
    ctx.session.add(
        ParadigmShiftRow(
            community_entity_id=community.id, domain=domain, old_theory_id=old.theory_entity_id, new_theory_id=new.theory_entity_id, epoch=ctx.epoch
        )
    )
    fallen = await ctx.session.get(EntityRow, old.theory_entity_id)
    risen = await ctx.session.get(EntityRow, new.theory_entity_id)
    await note(
        ctx,
        f"The scholars of {community.name} turned from {fallen.name if fallen else 'an old account'} to {risen.name if risen else 'a new one'}.",
        key="theories.paradigm_shift",
        ids=[community.id, new.theory_entity_id],
        kind=ChronicleKind.KNOWLEDGE,
    )


async def contests(ctx: TickContext) -> int:
    table = ctx.rules.theories
    shifted = 0
    rows = await ctx.session.scalars(select(TheoryAdherentRow).where(TheoryAdherentRow.orthodox.is_(True)).order_by(TheoryAdherentRow.adherent_entity_id))
    for row in list(rows):
        profile = await ctx.session.get(TheoryProfileRow, row.theory_entity_id)
        community = await ctx.session.get(EntityRow, row.adherent_entity_id)
        if profile is None or community is None or "orthodox" in row.locked or held(community.id):
            continue
        if await weight_against(ctx.session, ctx.rules, profile.theory_entity_id, ctx.epoch) <= profile.explanatory_power:
            continue
        rivals = await ctx.session.execute(
            select(TheoryAdherentRow, TheoryProfileRow)
            .join(TheoryProfileRow, TheoryProfileRow.theory_entity_id == TheoryAdherentRow.theory_entity_id)
            .where(TheoryAdherentRow.adherent_entity_id == community.id, TheoryAdherentRow.orthodox.is_(False), TheoryProfileRow.domain == profile.domain)
        )
        named = await ctx.session.get(TheoryProfileRow, profile.rival_entity_id) if profile.rival_entity_id is not None else None
        if named is not None and await ctx.session.get(TheoryAdherentRow, (named.theory_entity_id, community.id)) is None:
            heard = await ctx.session.scalar(
                select(TheoryAdherentRow.adherent_entity_id).where(TheoryAdherentRow.theory_entity_id == named.theory_entity_id).limit(1)
            )
            if heard is not None:
                await adhere(ctx, named.theory_entity_id, community.id, 1, named.domain)
        incumbent = await contest_score(ctx, community, profile, ruling_now=True)
        best: tuple[float, TheoryAdherentRow] | None = None
        for rival_row, rival_profile in rivals.all():
            score = await contest_score(ctx, community, rival_profile, ruling_now=False)
            if best is None or score > best[0]:
                best = (score, rival_row)
        if best is not None and best[0] > incumbent + table.contest_margin and "orthodox" not in best[1].locked:
            await shift_paradigm(ctx, community, row, best[1], profile.domain)
            shifted += 1
    return shifted


async def entangle(ctx: TickContext) -> int:
    table = ctx.rules.theories
    faithful: dict[int, set[int]] = defaultdict(set)
    for community in await living_researchers(ctx.session):
        for cult in await faiths_of(ctx.session, community):
            faithful[cult].add(community.id)
    persecuted = 0
    profiles = {row.theory_entity_id: row for row in await ctx.session.scalars(select(TheoryProfileRow))}
    adherents = list(await ctx.session.scalars(select(TheoryAdherentRow)))
    for cult, members in sorted(faithful.items()):
        if held(cult):
            continue
        ruling_ids = {row.theory_entity_id for row in adherents if row.orthodox and row.adherent_entity_id in members}
        endorsed_domains = {profiles[theory].domain for theory in ruling_ids if theory in profiles}
        for theory_id, profile in profiles.items():
            if "endorsed_by" not in profile.locked and theory_id in ruling_ids and cult not in profile.endorsed_by:
                profile.endorsed_by = [*profile.endorsed_by, cult]
            rival = theory_id not in ruling_ids and profile.domain in endorsed_domains
            if "condemned_by" not in profile.locked and rival and cult not in profile.condemned_by:
                profile.condemned_by = [*profile.condemned_by, cult]
        for row in adherents:
            condemned = profiles.get(row.theory_entity_id)
            if condemned is None or cult not in condemned.condemned_by or row.adherent_entity_id not in members or "strength" in row.locked:
                continue
            row.strength = clamp_int(row.strength - table.persecution_blow, 0, PERCENT)
            persecuted += 1
            if condemned.correctness >= PERCENT // 2:
                await try_heretic(ctx, row.adherent_entity_id, condemned.theory_entity_id)
    return persecuted


async def try_heretic(ctx: TickContext, community_id: int, theory_id: int) -> bool:
    if not ctx.rng(f"theory.heresy.{theory_id}.{community_id}.{ctx.epoch}").chance(ctx.rules.theories.heresy_trial_pct):
        return False
    scholar = await ctx.session.scalar(
        select(EntityRow.id)
        .join(SkillRow, SkillRow.holder_node_id == EntityRow.id)
        .where(
            await present_among(ctx.session, [community_id]),
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            SkillRow.skill == SkillKind.LORE,
        )
        .order_by(SkillRow.level.desc(), EntityRow.id)
        .limit(1)
    )
    if scholar is None or held(scholar):
        return False
    return await report_crime(ctx, community_id, scholar, CrimeKind.BLASPHEMY) is not None


async def tally_adherents(ctx: TickContext) -> None:
    counts = dict((await ctx.session.execute(select(TheoryAdherentRow.theory_entity_id, func.count()).group_by(TheoryAdherentRow.theory_entity_id))).all())
    for profile in list(await ctx.session.scalars(select(TheoryProfileRow))):
        theory = await ctx.session.get(EntityRow, profile.theory_entity_id)
        if theory is not None and not held(theory.id):
            set_stats(theory, adherents=int(counts.get(profile.theory_entity_id, 0)), explanatory=profile.explanatory_power)


@dataclass(frozen=True)
class Revelation:
    son_id: int
    theory_id: int | None
    domain: TheoryDomain
    name: str
    claim: str


async def reveal(ctx: TickContext, community: EntityRow, told: Revelation) -> TheoryProfileRow:
    table = ctx.rules.theories
    son_id, theory_id, domain, name, claim = told.son_id, told.theory_id, told.domain, told.name, told.claim
    profile = await ctx.session.get(TheoryProfileRow, theory_id) if theory_id is not None else None
    if profile is None:
        theory = await create_theory(ctx, community, domain, name, claim, correctness=PERCENT, son_id=son_id)
        profile = await ctx.session.get_one(TheoryProfileRow, theory.id)
    elif "correctness" not in profile.locked:
        profile.correctness, profile.revealed_by_son_id = PERCENT, son_id
    old = await ruling(ctx.session, community.id, profile.domain)
    mine = await adhere(ctx, profile.theory_entity_id, community.id, table.found_strength, profile.domain)
    if old is not None and old.theory_entity_id != profile.theory_entity_id:
        previous = await ctx.session.get(TheoryAdherentRow, (old.theory_entity_id, community.id))
        if previous is not None:
            await shift_paradigm(ctx, community, previous, mine, profile.domain)
        for cult in old.endorsed_by:
            await acclaim(ctx.session, son_id, cult, ReputationAxis.PIETY, amount=-table.reveal_anger, epoch=ctx.epoch)
    mine.orthodox = True
    ctx.session.add(
        TheoryAnomalyRow(
            theory_entity_id=old.theory_entity_id if old is not None else profile.theory_entity_id,
            kind=AnomalyKind.DIVINE_SIGN,
            weight=1,
            witness_entity_id=community.id,
            epoch=ctx.epoch,
        )
    )
    await acclaim(ctx.session, son_id, community.id, ReputationAxis.WISDOM, amount=table.reveal_standing, epoch=ctx.epoch)
    await ctx.session.flush()
    return profile


async def theories(ctx: TickContext) -> dict[str, int]:
    counts = {
        "theories_founded": await found_theories(ctx),
        "theories_spread": await spread_theories(ctx),
        "anomalies": await meet_anomalies(ctx),
        "paradigm_shifts": await contests(ctx),
        "theories_persecuted": await entangle(ctx),
        "theories_read": await read_theories(ctx),
        "theories_abandoned": await abandon(ctx),
    }
    await tally_adherents(ctx)
    return counts

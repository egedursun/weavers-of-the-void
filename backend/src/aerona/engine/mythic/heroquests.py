from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.mythic import ARCHETYPE_REALMS, ARCHETYPE_SKILLS, REALM_PHRASES, REALM_STEPS, trial_at
from aerona.constants.units import PERCENT
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.culture import LegendProfileRow, RiteProfileRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.dominion import DominionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import TrueNameRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.mythic import HeroquestMemberRow, HeroquestRow, ServitorRow
from aerona.db.tables.relations import PassionRow
from aerona.db.tables.renown import ReputationRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import CureKind, PackageKind, Transmission
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.gathering import CollectionKind, CollectionRole
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.enums.mythic import HeroquestBoon, HeroquestState, MythicRealm, QuestTrial
from aerona.domain.models.entity_stats import ItemStats
from aerona.engine.body.afflictions import active, afflict, cure
from aerona.engine.body.customs import people_of
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.divine.standing import standing_row
from aerona.engine.faith.book import patron_node
from aerona.engine.gods.queries import community_of
from aerona.engine.history.collections import open_collection
from aerona.engine.lifecycle.wounds import apply_hits, slay
from aerona.engine.lore.names import entitle
from aerona.engine.mind.book import skill_level
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import canon, connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import stat

QUEST_SKILLS = (SkillKind.RITUAL, SkillKind.LORE, SkillKind.PROPHECY, SkillKind.SPELLCRAFT, SkillKind.LEADERSHIP)
ITEM_POWER = 4
CURSED = frozenset({Transmission.CURSE, Transmission.RITE})


@dataclass
class QuestTally:
    begun: int = 0
    succeeded: int = 0
    failed: int = 0


async def renown_of(ctx: TickContext, mortal_id: int) -> int:
    return int(await ctx.session.scalar(select(func.max(ReputationRow.value)).where(ReputationRow.subject_node_id == mortal_id)) or 0)


async def fitting_legend(ctx: TickContext, mortal: EntityRow, community: EntityRow | None) -> LegendProfileRow | None:
    god = await patron_node(ctx.session, community.id) if community is not None else None
    people = await people_of(ctx.session, community) if community is not None else None
    tellers = {item for item in (community.id if community else None, people.id if people else None) if item is not None}
    for legend in await ctx.session.scalars(select(LegendProfileRow).order_by(LegendProfileRow.credence.desc(), LegendProfileRow.legend_entity_id)):
        if god is not None and legend.subject_node_id == god:
            return legend
        if tellers & set(legend.tellers or []):
            return legend
    return None


def realm_of(legend: LegendProfileRow) -> MythicRealm:
    if legend.fixed_in_entity_id is not None:
        return MythicRealm.SACRED_SITE
    realm = ARCHETYPE_REALMS[legend.archetype]
    return MythicRealm.DREAM if realm is MythicRealm.PALACE and legend.subject_node_id is None else realm


async def trial_of(ctx: TickContext, row: HeroquestRow) -> QuestTrial:
    legend = await ctx.session.get(LegendProfileRow, row.legend_entity_id) if row.legend_entity_id is not None else None
    return trial_at(legend.archetype if legend is not None else None, row.step)


async def trial_value(ctx: TickContext, row: HeroquestRow, quester: EntityRow, trial: QuestTrial, piety: int) -> int:
    if trial is QuestTrial.FAITH:
        return piety
    if trial is QuestTrial.CONVICTION:
        profile = await ctx.session.get(MortalProfileRow, quester.id)
        return profile.conviction if profile is not None else 0
    if trial is QuestTrial.PASSION:
        return int(await ctx.session.scalar(select(func.max(PassionRow.strength)).where(PassionRow.holder_node_id == quester.id)) or 0)
    legend = await ctx.session.get(LegendProfileRow, row.legend_entity_id) if row.legend_entity_id is not None else None
    skills = ARCHETYPE_SKILLS[legend.archetype] if legend is not None else frozenset(QUEST_SKILLS)
    return max([await skill_level(ctx.session, quester.id, kind) for kind in sorted(skills)])


async def begin_quest(ctx: TickContext, quester: EntityRow, legend: LegendProfileRow, members: list[int]) -> HeroquestRow:
    table = ctx.rules.heroquests
    realm = realm_of(legend)
    rng = ctx.rng(f"heroquest.{quester.id}.{ctx.epoch}")
    steps = rng.integer(table.steps_min, max(table.steps_min, table.steps_max)) + REALM_STEPS[realm]
    collection = await open_collection(
        ctx,
        CollectionKind.HEROQUEST,
        world_id=quester.world_id,
        members={quester.id: CollectionRole.LEADER, **dict.fromkeys(members, CollectionRole.MEMBER)},
        places=[legend.fixed_in_entity_id] if legend.fixed_in_entity_id is not None else [],
    )
    row = HeroquestRow(
        quester_entity_id=quester.id,
        legend_entity_id=legend.legend_entity_id,
        god_node_id=legend.subject_node_id,
        realm=realm,
        place_entity_id=legend.fixed_in_entity_id,
        steps=steps,
        step=0,
        fidelity=PERCENT,
        deviated=False,
        state=HeroquestState.QUESTING,
        interference=0,
        collection_id=collection.id if collection is not None else None,
        start_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    ctx.session.add_all(HeroquestMemberRow(heroquest_id=row.id, entity_id=member) for member in members if member != quester.id)
    await note(ctx, f"{quester.name} set out on a heroquest into {REALM_PHRASES[realm]}.", key="mythic.heroquest_begun", ids=[quester.id, *members])
    return row


async def interference_of(ctx: TickContext, row: HeroquestRow, world_id: int | None) -> int:
    rivals = await ctx.session.scalar(
        select(func.count()).select_from(ServitorRow).where(ServitorRow.god_node_id != (row.god_node_id or 0), ServitorRow.fallen_to_node_id.is_not(None))
    )
    outer = len([being for being in await canon(ctx.session, [EntityType.OUTER_BEING]) if being.world_id in {None, world_id}])
    return clamp_int((int(rivals or 0) + outer) * ctx.rules.heroquests.interference, 0, PERCENT)


async def party_of(ctx: TickContext, row: HeroquestRow) -> list[EntityRow]:
    ids = await ctx.session.scalars(
        select(HeroquestMemberRow.entity_id).where(HeroquestMemberRow.heroquest_id == row.id).order_by(HeroquestMemberRow.entity_id)
    )
    found = [await ctx.session.get(EntityRow, member) for member in ids]
    return [member for member in found if member is not None and member.status is EntityStatus.CANON and not held(member.id)]


async def score_of(ctx: TickContext, row: HeroquestRow, quester: EntityRow, piety: int) -> int:
    table = ctx.rules.heroquests
    trial = await trial_of(ctx, row)
    value = await trial_value(ctx, row, quester, trial, piety)
    members = len(await party_of(ctx, row))
    following = table.fidelity_bonus * row.fidelity // PERCENT
    roll = ctx.rng(f"heroquest.step.{row.id}.{row.step}.{ctx.epoch}").integer(1, PERCENT)
    return roll + value + following + members * table.member_bonus - row.interference


async def grant_rite(ctx: TickContext, quester: EntityRow) -> None:
    rite = await ctx.session.scalar(select(RiteProfileRow.rite_entity_id).order_by(RiteProfileRow.power.desc(), RiteProfileRow.rite_entity_id).limit(1))
    if rite is None:
        return
    found = await ctx.session.scalar(
        select(SkillRow).where(SkillRow.holder_node_id == quester.id, SkillRow.skill == SkillKind.SPELLCRAFT, SkillRow.subject_node_id == rite)
    )
    level = ctx.rules.spell_grammar.lab_skill
    if found is None:
        ctx.session.add(
            SkillRow(
                holder_node_id=quester.id,
                skill=SkillKind.SPELLCRAFT,
                subject_node_id=rite,
                level=level,
                peak=level,
                last_used_epoch=ctx.epoch,
                source=SkillSource.TEACHING,
            )
        )
    else:
        found.level = max(found.level, level)
        found.peak = max(found.peak, found.level)


async def grant(ctx: TickContext, row: HeroquestRow, quester: EntityRow) -> None:
    for hero in [quester, *await party_of(ctx, row)]:
        await bestow(ctx, row, hero)
    await renew(ctx, row, quester)


async def bestow(ctx: TickContext, row: HeroquestRow, quester: EntityRow) -> None:
    boon = row.boon or HeroquestBoon.FAVOUR
    if boon is HeroquestBoon.BLESSING:
        await afflict(ctx, quester, PackageKind.DIVINE_BLESSING, Transmission.RITE, source_node_id=row.god_node_id)
    elif boon is HeroquestBoon.ITEM:
        item = await create_record(
            ctx,
            RecordSpec(
                name=f"Boon of {quester.name}",
                entity_type=EntityType.ITEM,
                stats=ItemStats(might=PERCENT // 4),
                body=f"Brought back by {quester.name} from a heroquest.",
                power=ITEM_POWER,
                world_id=quester.world_id,
                location_id=quester.location_id,
                pending=False,
            ),
        )
        await connect(ctx.session, quester.id, item.id, BondKind.OWNS, ctx.epoch, description="won on a heroquest")
    elif boon is HeroquestBoon.RITE:
        await grant_rite(ctx, quester)
    elif boon is HeroquestBoon.LIFTED_CURSE:
        for affliction in await active(ctx.session, quester.id):
            if affliction.transmission in CURSED:
                await cure(ctx, quester, affliction, None)
    elif boon is HeroquestBoon.TITLE:
        legend = await ctx.session.get(LegendProfileRow, row.legend_entity_id) if row.legend_entity_id is not None else None
        await entitle(ctx, quester, legend.archetype.value.replace("_", " ") if legend is not None else row.realm.value.replace("_", " "))
    elif boon is HeroquestBoon.TRUE_NAME and row.god_node_id is not None:
        name = await ctx.session.get(TrueNameRow, row.god_node_id)
        if name is not None and quester.id not in name.known_by and "known_by" not in name.locked:
            name.known_by = [*name.known_by, quester.id]


async def renew(ctx: TickContext, row: HeroquestRow, quester: EntityRow) -> None:
    table = ctx.rules.heroquests
    community = await community_of(ctx.session, quester)
    if row.boon is HeroquestBoon.RENEWED_LAND and row.god_node_id is not None:
        region = (await RegionAtlas.load(ctx.session)).top_region(quester.id)
        claim = await ctx.session.get(DominionRow, (row.god_node_id, region)) if region is not None else None
        if claim is not None and "strength" not in claim.locked:
            claim.strength = clamp_int(claim.strength + table.boon_dominion, 0, PERCENT)
    if community is not None and row.god_node_id is not None and not held(community.id, row.god_node_id):
        standing = await standing_row(ctx, community.id, row.god_node_id)
        if "awe" not in standing.locked:
            standing.awe = clamp_int(standing.awe + table.boon_standing, 0, PERCENT)


async def rewrite(ctx: TickContext, row: HeroquestRow) -> None:
    legend = await ctx.session.get(LegendProfileRow, row.legend_entity_id) if row.legend_entity_id is not None else None
    if legend is None or held(legend.legend_entity_id):
        return
    if row.deviated and "distortion" not in legend.locked:
        legend.distortion = clamp_int(legend.distortion + ctx.rules.heroquests.rewrite_distortion, 0, PERCENT)
    legend.updated_epoch = ctx.epoch


async def free_trapped(ctx: TickContext, row: HeroquestRow) -> None:
    trapped = await ctx.session.scalars(
        select(HeroquestRow).where(HeroquestRow.state == HeroquestState.TRAPPED, HeroquestRow.realm == row.realm, HeroquestRow.id != row.id)
    )
    for other in list(trapped):
        if "state" not in other.locked:
            other.state = HeroquestState.FAILED
    await settle_souls(ctx)


async def lost_souls(ctx: TickContext) -> set[int]:
    trapped = list(await ctx.session.scalars(select(HeroquestRow).where(HeroquestRow.state == HeroquestState.TRAPPED)))
    souls = {row.quester_entity_id for row in trapped}
    if trapped:
        members = select(HeroquestMemberRow.entity_id).where(HeroquestMemberRow.heroquest_id.in_([row.id for row in trapped]))
        souls |= set(await ctx.session.scalars(members))
    return souls


async def settle_souls(ctx: TickContext) -> None:
    souls = await lost_souls(ctx)
    bearing = {
        row.bearer_node_id: row
        for row in await ctx.session.scalars(
            select(AfflictionRow).where(AfflictionRow.package == PackageKind.SOUL_TRAPPED, AfflictionRow.cured_epoch.is_(None))
        )
    }
    for soul in sorted(souls - set(bearing)):
        mortal = await ctx.session.get(EntityRow, soul)
        if mortal is not None and mortal.status is EntityStatus.CANON and not held(soul):
            await afflict(ctx, mortal, PackageKind.SOUL_TRAPPED, Transmission.EXPERIENCE)
    for bearer_id, affliction in sorted(bearing.items()):
        mortal = await ctx.session.get(EntityRow, bearer_id)
        if bearer_id not in souls and mortal is not None and not held(bearer_id):
            await cure(ctx, mortal, affliction, CureKind.QUEST)


async def succeed(ctx: TickContext, row: HeroquestRow, quester: EntityRow, tally: QuestTally) -> None:
    if row.boon is None and "boon" not in row.locked:
        boons = list(HeroquestBoon)
        row.boon = ctx.rng(f"heroquest.boon.{row.id}").pick(boons) if row.deviated else HeroquestBoon.FAVOUR
    row.state, row.end_epoch = HeroquestState.SUCCEEDED, ctx.epoch
    await grant(ctx, row, quester)
    await rewrite(ctx, row)
    await free_trapped(ctx, row)
    tally.succeeded += 1
    await note(ctx, f"{quester.name} returned from a heroquest with a boon.", key="mythic.heroquest_won", ids=[quester.id], kind=ChronicleKind.WORLD)


async def break_myth(ctx: TickContext, row: HeroquestRow, quester: EntityRow) -> None:
    table = ctx.rules.heroquests
    legend = await ctx.session.get(LegendProfileRow, row.legend_entity_id) if row.legend_entity_id is not None else None
    if legend is not None and "credence" not in legend.locked:
        legend.credence = clamp_int(legend.credence - table.break_credence, 0, PERCENT)
    community = await community_of(ctx.session, quester)
    people = await people_of(ctx.session, community) if community is not None else None
    culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
    if culture is not None and "cohesion" not in culture.locked:
        culture.cohesion = clamp_int(culture.cohesion - table.break_cohesion, 0, PERCENT)


async def fail(ctx: TickContext, row: HeroquestRow, quester: EntityRow, tally: QuestTally) -> None:
    table = ctx.rules.heroquests
    rng = ctx.rng(f"heroquest.fall.{row.id}")
    row.end_epoch = ctx.epoch
    party = [quester, *await party_of(ctx, row)]
    if rng.chance(table.trap_pct):
        row.state = HeroquestState.TRAPPED
        await settle_souls(ctx)
        outcome = "the soul is held in the myth while the body sleeps"
    elif rng.chance(table.break_pct):
        row.state = HeroquestState.BROKEN
        await break_myth(ctx, row, quester)
        outcome = "the myth itself broke"
    elif rng.chance(table.madness_pct):
        row.state = HeroquestState.FAILED
        for hero in party:
            await afflict(ctx, hero, PackageKind.TRAUMA, Transmission.EXPERIENCE, source_node_id=row.god_node_id)
        outcome = "the questers came back mad"
    else:
        row.state = HeroquestState.FAILED
        doomed = rng.chance(table.death_pct)
        for hero in party:
            harm = Harm(damage=table.injury_hp, cause=HarmCause.CURSE, death_cause="lost on a heroquest", source_node_id=row.god_node_id)
            if doomed:
                await slay(ctx, hero, harm)
            else:
                await apply_hits(ctx, hero, harm, lethal=False)
        outcome = "the questers did not come back" if doomed else "the questers came back hurt"
    tally.failed += 1
    await note(ctx, f"{quester.name} fell on a heroquest: {outcome}.", key="mythic.heroquest_lost", ids=[hero.id for hero in party], kind=ChronicleKind.WORLD)


async def advance(ctx: TickContext, row: HeroquestRow, tally: QuestTally) -> None:
    table = ctx.rules.heroquests
    quester = await ctx.session.get(EntityRow, row.quester_entity_id)
    if quester is None or quester.status is not EntityStatus.CANON:
        row.state, row.end_epoch = HeroquestState.FAILED, ctx.epoch
        return
    community = await community_of(ctx.session, quester)
    if "interference" not in row.locked:
        row.interference = await interference_of(ctx, row, quester.world_id)
    piety = (stat(community, "piety") or 0) if community is not None else 0
    if await score_of(ctx, row, quester, piety) >= table.step_pass:
        row.step += 1
    elif ctx.rng(f"heroquest.deviate.{row.id}.{row.step}").chance(table.deviation_pct):
        row.deviated = True
        row.fidelity = clamp_int(row.fidelity - table.deviation_fidelity, 0, PERCENT)
        row.step += 1
    else:
        await fail(ctx, row, quester, tally)
        return
    if row.step >= row.steps:
        await succeed(ctx, row, quester, tally)


async def fellows(ctx: TickContext, quester: EntityRow, ids: list[int]) -> list[int] | str:
    party: list[int] = []
    for mate_id in dict.fromkeys(ids):
        mate = await ctx.session.get(EntityRow, mate_id)
        if mate is None or mate.status is not EntityStatus.CANON or mate.entity_type is not EntityType.MORTAL or mate.id == quester.id:
            return f"#{mate_id} cannot walk beside {quester.name}"
        if mate.location_id != quester.location_id:
            return f"{mate.name} is not where {quester.name} is"
        party.append(mate.id)
    return party


async def eligible(ctx: TickContext, mortal: EntityRow) -> tuple[LegendProfileRow, EntityRow | None] | None:
    table = ctx.rules.heroquests
    if held(mortal.id) or await renown_of(ctx, mortal.id) < table.renown_min:
        return None
    community = await community_of(ctx.session, mortal)
    if community is None or (stat(community, "piety") or 0) < table.piety_min:
        return None
    legend = await fitting_legend(ctx, mortal, community)
    return (legend, community) if legend is not None else None


async def quest_world(ctx: TickContext, tally: QuestTally) -> None:
    table = ctx.rules.heroquests
    questing = set(
        await ctx.session.scalars(select(HeroquestRow.quester_entity_id).where(HeroquestRow.state.in_([HeroquestState.QUESTING, HeroquestState.TRAPPED])))
    )
    for row in list(await ctx.session.scalars(select(HeroquestRow).where(HeroquestRow.state == HeroquestState.QUESTING).order_by(HeroquestRow.id))):
        if not held(row.quester_entity_id) and "step" not in row.locked:
            await advance(ctx, row, tally)
    for mortal in await canon(ctx.session, [EntityType.MORTAL]):
        if tally.begun >= table.per_epoch:
            break
        if mortal.id in questing or not ctx.rng(f"heroquest.call.{mortal.id}.{ctx.epoch}").chance(table.chance_pct):
            continue
        found = await eligible(ctx, mortal)
        if found is not None:
            party = await companions(ctx, mortal, questing) if ctx.rng(f"heroquest.party.{mortal.id}.{ctx.epoch}").chance(table.party_pct) else []
            await begin_quest(ctx, mortal, found[0], party)
            questing |= {mortal.id, *party}
            tally.begun += 1
    await settle_souls(ctx)
    await ctx.session.flush()


async def companions(ctx: TickContext, quester: EntityRow, questing: set[int]) -> list[int]:
    table = ctx.rules.heroquests
    if quester.location_id is None or table.party_max <= 0:
        return []
    near = await ctx.session.scalars(
        select(EntityRow)
        .where(
            await present_among(ctx.session, [quester.location_id]),
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.id != quester.id,
        )
        .order_by(EntityRow.id)
    )
    party: list[int] = []
    for mortal in near:
        if len(party) >= table.party_max:
            break
        if mortal.id not in questing and not held(mortal.id) and await renown_of(ctx, mortal.id) >= table.renown_min // 2:
            party.append(mortal.id)
    return party

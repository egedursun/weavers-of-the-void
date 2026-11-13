from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from sqlalchemy import or_, select

from aerona.catalog.norms import GATHERING_SITUATIONS, INTERACTION_BEHAVIOUR
from aerona.catalog.relations import INTERACTIONS
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow
from aerona.db.tables.gatherings import CollectionPlaceRow, CollectionRow
from aerona.db.tables.mind import GriefRow, SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.relations import RelationshipRow, SocialCircleRow
from aerona.db.write_guard import write_blocked
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.collective import NormSituation
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ActKind, EthicalStance, Facet, GriefStage, MemoryKind, NeedKind, SkillKind, ThoughtKind, ValueAxis, ValueHolder, WantKind
from aerona.domain.enums.relations import AppealKind, InteractionKind, PersuasionAim, RelationType
from aerona.domain.enums.renown import ReputationAxis
from aerona.engine.body.decline import too_forgetful
from aerona.engine.body.hits import Harm
from aerona.engine.collective.book import shift as shift_field
from aerona.engine.collective.norms import Norms, breach, norms_of, stance_in, volition
from aerona.engine.context import TickContext
from aerona.engine.intrigue.talk import affair_secret, ask_back, confide_own, gift_earns, gossip_secret
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.aspirations import open_wants
from aerona.engine.mind.book import Values, needs_of, stored_values
from aerona.engine.mind.ethics import at_war, conscience, culture_of
from aerona.engine.mind.memories import remember
from aerona.engine.mind.skills import practise
from aerona.engine.mind.split import facets_of
from aerona.engine.mind.thoughts import think
from aerona.engine.mortal.attraction import drawn, pull
from aerona.engine.mortal.kin import children_of, parents_of, partners_of, siblings_of
from aerona.engine.mortal.kinship import betroth, marriage_between
from aerona.engine.mortal.life import adult
from aerona.engine.mortal.standing import add_stress
from aerona.engine.polity.book import sex_of
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.queries import spoken_language
from aerona.engine.relations.book import RELATIONS_KEY, ensure_relation, mood_of, relation, shift
from aerona.engine.relations.persuasion import persuade
from aerona.engine.renown.deeds import acclaim_deed
from aerona.engine.renown.lore import confide

K = InteractionKind
FACET_SPAN = 50
VALUE_SPAN = 100
TALK_FREE = frozenset({K.BRAWL, K.GIFT})
FRIENDLY_TALK = frozenset({K.CONVERSE, K.BEFRIEND, K.JOKE, K.CONFIDE_SECRET})
LIGHT_WEIGHT = 0.05
MIN_TEACH_GAP = 20
HUNGRY_BELOW = 30
BRAWL_BELOW = -20
CONFIDE_AT = 40
FAVOUR_AT = 20
SUPERIOR_GAP = 30
CONFORMING = (Facet.COOPERATION, Facet.POLITENESS, Facet.SENSE_OF_DUTY)


@dataclass
class Scene:
    ctx: TickContext
    place_id: int
    mortals: dict[int, EntityRow]
    profiles: dict[int, MortalProfileRow] = field(default_factory=dict)
    facets: dict[int, dict[Facet, int]] = field(default_factory=dict)
    values: dict[int, Values] = field(default_factory=dict)
    tongues: dict[int, int | None] = field(default_factory=dict)
    wants: dict[int, set[WantKind]] = field(default_factory=dict)
    kin: dict[int, set[int]] = field(default_factory=dict)
    spouses: dict[int, set[int]] = field(default_factory=dict)
    circles: dict[int, set[int]] = field(default_factory=dict)
    skills: dict[int, dict[str, int]] = field(default_factory=dict)
    hungry: set[int] = field(default_factory=set)
    grieving: set[int] = field(default_factory=set)
    war: bool = False
    met: set[tuple[int, int]] = field(default_factory=set)
    norms: dict[int, Norms] = field(default_factory=dict)
    gathering: NormSituation | None = None
    forgetful: set[int] = field(default_factory=set)


@dataclass
class SocialTally:
    interactions: int = 0
    pairs: int = 0
    proposals: int = 0
    affairs: int = 0
    brawls: int = 0
    gifts: int = 0
    lessons: int = 0
    persuaded: int = 0
    breaches: int = 0
    by_kind: dict[str, int] = field(default_factory=lambda: defaultdict(int))


async def load_scene(ctx: TickContext, place_id: int, mortals: list[EntityRow]) -> Scene:
    scene = Scene(ctx, place_id, {mortal.id: mortal for mortal in mortals})
    ids = list(scene.mortals)
    for profile in await ctx.session.scalars(select(MortalProfileRow).where(MortalProfileRow.entity_id.in_(ids))):
        scene.profiles[profile.entity_id] = profile
    for row in await ctx.session.scalars(select(SkillRow).where(SkillRow.holder_node_id.in_(ids))):
        scene.skills.setdefault(row.holder_node_id, {})[row.skill.value] = row.level
    for mortal_id in ids:
        scene.facets[mortal_id] = await facets_of(ctx.session, mortal_id)
        scene.values[mortal_id] = await stored_values(ctx.session, ValueHolder.PERSONAL, mortal_id)
        tongue = await spoken_language(ctx.session, mortal_id)
        scene.tongues[mortal_id] = tongue.id if tongue is not None else None
        scene.wants[mortal_id] = await open_wants(ctx.session, mortal_id)
        scene.spouses[mortal_id] = set(await partners_of(ctx.session, mortal_id))
        scene.kin[mortal_id] = {
            *await parents_of(ctx.session, mortal_id),
            *await children_of(ctx.session, mortal_id),
            *await siblings_of(ctx.session, mortal_id),
        }
        if (await needs_of(ctx.session, mortal_id)).get(NeedKind.SUSTENANCE, PERCENT) < HUNGRY_BELOW:
            scene.hungry.add(mortal_id)
    scene.grieving = set(
        await ctx.session.scalars(select(GriefRow.mourner_node_id).where(GriefRow.mourner_node_id.in_(ids), GriefRow.stage != GriefStage.ACCEPTANCE))
    )
    scene.forgetful = {mortal_id for mortal_id in ids if await too_forgetful(ctx.session, mortal_id, ctx.rules.decline.teach_block)}
    circles = select(SocialCircleRow.faction_entity_id)
    for faction_id, mortal_id in await ctx.session.execute(
        select(FactionMembershipRow.faction_entity_id, FactionMembershipRow.mortal_entity_id).where(
            FactionMembershipRow.mortal_entity_id.in_(ids), FactionMembershipRow.faction_entity_id.in_(circles)
        )
    ):
        scene.circles.setdefault(mortal_id, set()).add(faction_id)
    scene.war = await at_war(ctx.session, [place_id])
    held_norms: dict[int, Norms] = {}
    for mortal_id in ids:
        culture = await culture_of(ctx.session, mortal_id)
        if culture is not None and culture.id not in held_norms:
            held_norms[culture.id] = await norms_of(ctx.session, culture.id)
        scene.norms[mortal_id] = held_norms[culture.id] if culture is not None else {}
    kinds = await ctx.session.scalars(
        select(CollectionRow.kind)
        .join(CollectionPlaceRow, CollectionPlaceRow.collection_id == CollectionRow.id)
        .where(CollectionPlaceRow.place_entity_id == place_id, or_(CollectionRow.end_epoch.is_(None), CollectionRow.end_epoch >= ctx.epoch))
        .order_by(CollectionRow.start_epoch.desc(), CollectionRow.id.desc())
    )
    scene.gathering = next((GATHERING_SITUATIONS[kind] for kind in kinds if kind in GATHERING_SITUATIONS), None)
    return scene


def alignment(first: Values, second: Values) -> float:
    axes = set(first) & set(second)
    if not axes:
        return 0.0
    return sum(first[axis] * second[axis] for axis in axes) / (len(axes) * VALUE_SPAN * VALUE_SPAN)


async def pairs_for(scene: Scene, rng: SeededRandom) -> list[tuple[int, int]]:
    table = scene.ctx.rules.social
    ids = sorted(scene.mortals)
    found: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()

    def add(first: int, second: int) -> None:
        pair = (min(first, second), max(first, second))
        if first != second and second in scene.mortals and pair not in seen:
            seen.add(pair)
            found.append(pair)

    rows = await scene.ctx.session.scalars(
        select(RelationshipRow)
        .where(RelationshipRow.holder_node_id.in_(ids), RelationshipRow.subject_node_id.in_(ids))
        .order_by(RelationshipRow.familiarity.desc(), RelationshipRow.id)
    )
    known: dict[int, list[int]] = defaultdict(list)
    for row in rows:
        known[row.holder_node_id].append(row.subject_node_id)
    for mortal_id in ids:
        for other in known[mortal_id][: table.partners_per_mortal]:
            add(mortal_id, other)
        for other in sorted(scene.kin[mortal_id] | scene.spouses[mortal_id]):
            add(mortal_id, other)
        for other in ids:
            if scene.circles.get(mortal_id, set()) & scene.circles.get(other, set()):
                add(mortal_id, other)
        strangers = [other for other in ids if other != mortal_id and other not in known[mortal_id]]
        for _ in range(min(table.new_acquaintances, len(strangers))):
            add(mortal_id, rng.pick(strangers))
    return found[: table.pairs_per_place]


def grown(scene: Scene, mortal_id: int) -> bool:
    profile = scene.profiles.get(mortal_id)
    return profile is None or adult(profile.life_stage)


def skill_of(scene: Scene, mortal_id: int, skill: str | None) -> int:
    if skill is None:
        return max(scene.skills.get(mortal_id, {}).values(), default=0)
    return scene.skills.get(mortal_id, {}).get(skill, 0)


def single(scene: Scene, mortal_id: int) -> bool:
    return not scene.spouses.get(mortal_id)


def allowed(scene: Scene, actor: int, target: int, kind: InteractionKind, *, row: RelationshipRow | None, back: RelationshipRow | None) -> bool:
    spec = INTERACTIONS[kind]
    friendship = row.friendship if row is not None else 0
    familiarity = row.familiarity if row is not None else 0
    romance = row.romance if row is not None else 0
    if spec.romantic and (not grown(scene, actor) or not grown(scene, target) or target in scene.kin[actor]):
        return False
    if spec.romantic and not drawn(scene.profiles.get(actor), sex_of(scene.mortals[target])):
        return False
    if familiarity < spec.min_familiarity or romance < spec.min_romance:
        return False
    rival = (row.rivalry if row is not None else 0) >= scene.ctx.rules.social.rival_at
    checks = {
        K.PROPOSE: single(scene, actor) and single(scene, target) and (back.romance if back is not None else 0) >= spec.min_romance,
        K.RECONCILE: friendship < 0,
        K.COMFORT: mood_of(scene.profiles.get(target)) < 0 or target in scene.grieving,
        K.TEACH: skill_of(scene, actor, None) - skill_of(scene, target, None) >= MIN_TEACH_GAP and actor not in scene.forgetful,
        K.BRAWL: grown(scene, actor) and grown(scene, target) and (friendship <= BRAWL_BELOW or rival),
        K.CONFIDE_SECRET: friendship >= CONFIDE_AT,
        K.ASK_FAVOUR: friendship >= FAVOUR_AT,
        K.GIFT: (scene.profiles[actor].wealth if actor in scene.profiles else 0) >= scene.ctx.rules.social.gift_wealth,
    }
    return checks.get(kind, True)


def weight(scene: Scene, actor: int, target: int, kind: InteractionKind, row: RelationshipRow | None) -> float:
    table = scene.ctx.rules.social
    spec = INTERACTIONS[kind]
    facets = scene.facets.get(actor, {})
    lean = sum(facets.get(facet, 0) * value for facet, value in spec.facets.items()) / (FACET_SPAN * PERCENT)
    result = max(LIGHT_WEIGHT, 1 + lean * table.facet_weight_pct / PERCENT)
    result *= max(LIGHT_WEIGHT, 1 + spec.mood * mood_of(scene.profiles.get(actor)) * table.mood_weight_pct / (4 * PERCENT))
    friendship = row.friendship if row is not None else 0
    result *= max(LIGHT_WEIGHT, 1 + spec.warmth * friendship * table.warmth_weight_pct / (VALUE_SPAN * PERCENT * 10))
    fit = alignment(scene.values.get(actor, {}), scene.values.get(target, {})) * table.belief_weight_pct / PERCENT
    if spec.hostile or kind is K.ARGUE:
        result *= max(LIGHT_WEIGHT, 1 - fit)
    elif kind in FRIENDLY_TALK:
        result *= max(LIGHT_WEIGHT, 1 + fit)
    if kind not in TALK_FREE and scene.tongues.get(actor) != scene.tongues.get(target):
        result *= table.foreign_tongue_pct / PERCENT
    if spec.wants & scene.wants.get(actor, set()):
        result *= 1 + table.want_weight_pct / PERCENT
    events = table.event_weight_pct / PERCENT
    if scene.war and kind in {K.COMFORT, K.ARGUE}:
        result *= 1 + events
    if actor in scene.hungry and kind in {K.QUARREL, K.BRAWL}:
        result *= 1 + events
    return result


def situation_of(scene: Scene, actor: int, target: int) -> NormSituation:
    if actor in scene.grieving or target in scene.grieving:
        return NormSituation.MOURNING
    mine, theirs = scene.profiles.get(actor), scene.profiles.get(target)
    if mine is not None and theirs is not None and theirs.renown - mine.renown >= SUPERIOR_GAP:
        return NormSituation.SUPERIOR
    if scene.gathering is not None:
        return scene.gathering
    if scene.tongues.get(actor) != scene.tongues.get(target):
        return NormSituation.STRANGER
    return NormSituation.MARKET


def conformity(scene: Scene, mortal_id: int) -> float:
    facets = scene.facets.get(mortal_id, {})
    return max(-1.0, min(1.0, sum(facets.get(facet, 0) for facet in CONFORMING) / (len(CONFORMING) * FACET_SPAN)))


def rebellion(scene: Scene, mortal_id: int) -> float:
    return max(0.0, -scene.values.get(mortal_id, {}).get(ValueAxis.TRADITION, 0) / VALUE_SPAN)


def norm_for(scene: Scene, actor: int, target: int, kind: InteractionKind) -> EthicalStance:
    behaviour = INTERACTION_BEHAVIOUR.get(kind)
    if behaviour is None:
        return EthicalStance.ACCEPTABLE
    return stance_in(scene.norms.get(actor, {}), situation_of(scene, actor, target), behaviour)


def score(scene: Scene, actor: int, target: int, kind: InteractionKind, row: RelationshipRow | None) -> float:
    stance = norm_for(scene, actor, target, kind)
    rule = volition(scene.ctx.rules, stance, conformity=conformity(scene, actor), rebel=rebellion(scene, actor))
    return weight(scene, actor, target, kind, row) * max(LIGHT_WEIGHT, rule)


async def choose(scene: Scene, actor: int, target: int, rng: SeededRandom) -> InteractionKind | None:
    row = await relation(scene.ctx.session, actor, target)
    back = await relation(scene.ctx.session, target, actor)
    options = [kind for kind in InteractionKind if allowed(scene, actor, target, kind, row=row, back=back)]
    if not options:
        return None
    scores = [score(scene, actor, target, kind, row) for kind in options]
    if sum(scores) <= 0:
        return None
    if rng.chance(scene.ctx.rules.volition.whim_pct):
        return rng.weighted(options, scores)
    return max(zip(scores, options, strict=True), key=lambda pair: pair[0])[1]


async def shamed(scene: Scene, actor: int, target: int, kind: InteractionKind, tally: SocialTally) -> None:
    if not breach(norm_for(scene, actor, target, kind)) or len(scene.mortals) < 3 or write_blocked(actor, RELATIONS_KEY):
        return
    profile = scene.profiles.get(actor)
    if profile is not None:
        shift_field(profile, "honour", -scene.ctx.rules.volition.breach_shame)
    tally.breaches += 1
    await think(scene.ctx.session, scene.ctx.rules, actor, ThoughtKind.WAS_SHAMED, scene.ctx.epoch, subject_id=target)


async def gossip(scene: Scene, actor: int, target: int) -> None:
    session, rules = scene.ctx.session, scene.ctx.rules
    worst = await session.scalar(
        select(RelationshipRow)
        .where(RelationshipRow.holder_node_id == actor, RelationshipRow.subject_node_id != target, RelationshipRow.friendship < 0)
        .order_by(RelationshipRow.friendship, RelationshipRow.id)
        .limit(1)
    )
    if worst is None:
        return
    heard = await ensure_relation(session, target, worst.subject_node_id, scene.ctx.epoch)
    if heard is not None:
        shift(rules, heard, scene.ctx.epoch, friendship=-rules.social.gossip_spread, familiarity=1)
    await gossip_secret(scene.ctx, actor, target)


async def comfort(scene: Scene, actor: int, target: int) -> None:
    await add_stress(scene.ctx.session, target, -scene.ctx.rules.social.comfort_stress, scene.ctx.epoch)


async def threaten(scene: Scene, actor: int, target: int) -> None:
    await add_stress(scene.ctx.session, target, scene.ctx.rules.social.threat_stress, scene.ctx.epoch)


async def pass_wealth(scene: Scene, giver: int, taker: int, amount: int) -> bool:
    given, taken = scene.profiles.get(giver), scene.profiles.get(taker)
    if given is None or taken is None or "wealth" in given.locked or "wealth" in taken.locked or given.wealth < amount:
        return False
    given.wealth -= amount
    taken.wealth = min(PERCENT, taken.wealth + amount)
    return True


async def gift(scene: Scene, actor: int, target: int) -> None:
    if await pass_wealth(scene, actor, target, scene.ctx.rules.social.gift_wealth):
        ctx = scene.ctx
        await remember(ctx.session, ctx.rules, holder_id=target, subject_id=actor, kind=MemoryKind.GIFTED_ME, magnitude=10, epoch=ctx.epoch)
        await gift_earns(ctx, actor, target)


async def favour(scene: Scene, actor: int, target: int) -> None:
    if await ask_back(scene.ctx, actor, target) is False:
        return
    await pass_wealth(scene, target, actor, scene.ctx.rules.social.favour_wealth)


async def teach(scene: Scene, actor: int, target: int) -> None:
    mine, theirs = scene.skills.get(actor, {}), scene.skills.get(target, {})
    gaps = sorted(((level - theirs.get(skill, 0), skill) for skill, level in mine.items()), reverse=True)
    if gaps and gaps[0][0] >= MIN_TEACH_GAP:
        await practise(scene.ctx.session, scene.ctx.rules, target, SkillKind(gaps[0][1]), scene.ctx.rules.skills.teach_xp, epoch=scene.ctx.epoch)


async def propose(scene: Scene, actor: int, target: int) -> None:
    ctx = scene.ctx
    back = await relation(ctx.session, target, actor)
    chance = ctx.rules.social.proposal_accept_pct * (back.romance if back is not None else 0) / PERCENT
    if await marriage_between(ctx.session, actor, target) is None and ctx.rng(seed_of("proposal", actor, target, ctx.epoch)).chance(chance):
        await betroth(ctx.session, scene.mortals[actor], scene.mortals[target], ctx.epoch, description="promised for love")
    else:
        await think(ctx.session, ctx.rules, actor, ThoughtKind.HEARTBROKEN, ctx.epoch, subject_id=target)


async def seduce(scene: Scene, actor: int, target: int) -> None:
    ctx = scene.ctx
    spouses = (scene.spouses.get(actor, set()) | scene.spouses.get(target, set())) - {actor, target}
    if not spouses:
        return
    for holder, subject in ((actor, target), (target, actor)):
        row = await ensure_relation(ctx.session, holder, subject, ctx.epoch)
        if row is not None and "affair" not in row.locked:
            row.affair = True
    await affair_secret(ctx, actor, target)
    await conscience(ctx, actor, ActKind.ADULTERY, min(spouses))


async def insult(scene: Scene, actor: int, target: int) -> None:
    ctx = scene.ctx
    await remember(ctx.session, ctx.rules, holder_id=target, subject_id=actor, kind=MemoryKind.HUMILIATED_ME, magnitude=-10, epoch=ctx.epoch)


async def brawl(scene: Scene, actor: int, target: int) -> None:
    ctx = scene.ctx
    first, second = scene.mortals[actor], scene.mortals[target]
    rng = ctx.rng(seed_of("brawl", actor, target, ctx.epoch))
    loser = second if rng.chance(PERCENT // 2) else first
    winner = first if loser is second else second
    for side in (first, second):
        await acclaim_deed(ctx, side.id, ReputationAxis.TROUBLEMAKER, ctx.rules.local_renown.brawl_magnitude, place_id=scene.place_id)
    if not write_blocked(loser.id, RELATIONS_KEY):
        await apply_hits(ctx, loser, Harm(ctx.rules.social.brawl_hp, HarmCause.ACCIDENT, "hurt in a brawl", severity=1), lethal=False)
        await remember(ctx.session, ctx.rules, holder_id=loser.id, subject_id=winner.id, kind=MemoryKind.HARMED_ME, magnitude=-8, epoch=ctx.epoch)


async def argue(scene: Scene, actor: int, target: int) -> None:
    ctx = scene.ctx
    if not ctx.rng(seed_of("argue", actor, target, ctx.epoch)).chance(ctx.rules.persuasion.argue_pct):
        return
    mine, theirs = scene.values.get(actor, {}), scene.values.get(target, {})
    axes = sorted(set(mine) & set(theirs), key=lambda axis: (-abs(mine[axis] - theirs[axis]), axis.value))
    if axes:
        await persuade(ctx, actor, target, AppealKind.BELIEF, PersuasionAim.BELIEF, axis=axes[0], toward=mine[axes[0]])


async def confide_lore(scene: Scene, actor: int, target: int) -> None:
    if await confide(scene.ctx, scene.mortals[actor], scene.mortals[target]):
        scene.ctx.count("lore_confided")
    if await confide_own(scene.ctx, actor, target):
        scene.ctx.count("secrets_confided")


EFFECTS: dict[InteractionKind, Callable[[Scene, int, int], Awaitable[None]]] = {
    K.GOSSIP: gossip,
    K.COMFORT: comfort,
    K.THREATEN: threaten,
    K.GIFT: gift,
    K.ASK_FAVOUR: favour,
    K.TEACH: teach,
    K.PROPOSE: propose,
    K.SEDUCE: seduce,
    K.INSULT: insult,
    K.BRAWL: brawl,
    K.ARGUE: argue,
    K.CONFIDE_SECRET: confide_lore,
}


async def lands(scene: Scene, actor: int, target: int, kind: InteractionKind, rng: SeededRandom) -> bool:
    spec = INTERACTIONS[kind]
    if spec.hostile:
        return True
    table = scene.ctx.rules.social
    chance = table.success_base + (skill_of(scene, actor, spec.skill.value if spec.skill else None) - PERCENT // 2) * table.skill_success_pct / PERCENT
    if spec.romantic:
        back = await relation(scene.ctx.session, target, actor)
        chance += (back.romance if back is not None else 0) / 2 - PERCENT // 4
    return rng.chance(max(0.0, min(float(PERCENT), chance)))


async def interact(scene: Scene, actor: int, target: int, kind: InteractionKind, *, rng: SeededRandom, tally: SocialTally) -> bool:
    ctx = scene.ctx
    spec = INTERACTIONS[kind]
    heard = await ensure_relation(ctx.session, target, actor, ctx.epoch)
    spoke = await ensure_relation(ctx.session, actor, target, ctx.epoch)
    success = await lands(scene, actor, target, kind, rng)
    if success:
        if heard is not None:
            kindled = spec.romance * await ctx.hook_factor(target, DomainHook.KINDLING_LOVE) if spec.romance > 0 else spec.romance
            if kindled > 0:
                kindled *= pull(scene.profiles.get(target), sex_of(scene.mortals[actor])) if actor in scene.mortals else 0.0
            shift(ctx.rules, heard, ctx.epoch, friendship=spec.friendship, romance=kindled, familiarity=spec.familiarity, rivalry=spec.rivalry)
        if spoke is not None:
            share = 1 if spec.mutual else 0.5
            shift(ctx.rules, spoke, ctx.epoch, friendship=spec.friendship * share, familiarity=spec.familiarity, rivalry=spec.rivalry * share)
        if spec.thought is not None:
            await think(ctx.session, ctx.rules, target, spec.thought, ctx.epoch, subject_id=actor)
            if spec.mutual:
                await think(ctx.session, ctx.rules, actor, spec.thought, ctx.epoch, subject_id=target)
        effect = EFFECTS.get(kind)
        if effect is not None:
            await effect(scene, actor, target)
    elif heard is not None:
        shift(ctx.rules, heard, ctx.epoch, friendship=-abs(spec.friendship) / 2, familiarity=1)
    if spec.skill is not None:
        await practise(ctx.session, ctx.rules, actor, spec.skill, ctx.rules.skills.spar_xp, epoch=ctx.epoch)
    await shamed(scene, actor, target, kind, tally)
    tally.interactions += 1
    tally.by_kind[kind.value] += 1
    tally.proposals += kind is K.PROPOSE and success
    tally.affairs += kind is K.SEDUCE and success
    tally.brawls += kind is K.BRAWL
    tally.gifts += kind is K.GIFT and success
    tally.lessons += kind is K.TEACH and success
    return success


async def socialise(ctx: TickContext, place_id: int, mortals: list[EntityRow], tally: SocialTally) -> Scene | None:
    if len(mortals) < 2:
        return None
    scene = await load_scene(ctx, place_id, mortals)
    rng = ctx.rng(seed_of("social", place_id, ctx.epoch))
    for first, second in await pairs_for(scene, rng):
        tally.pairs += 1
        scene.met.add((first, second))
        for sample in range(ctx.rules.social.interactions_per_epoch):
            actor, target = (first, second) if rng.chance(PERCENT // 2) else (second, first)
            kind = await choose(scene, actor, target, ctx.rng(seed_of("pick", actor, target, ctx.epoch, sample)))
            if kind is not None:
                await interact(scene, actor, target, kind, rng=rng, tally=tally)
    return scene


async def fade(ctx: TickContext, ids: list[int], met: set[tuple[int, int]]) -> int:
    table = ctx.rules.social
    faded = 0
    for row in await ctx.session.scalars(select(RelationshipRow).where(RelationshipRow.holder_node_id.in_(ids)).order_by(RelationshipRow.id)):
        pair = (min(row.holder_node_id, row.subject_node_id), max(row.holder_node_id, row.subject_node_id))
        if pair in met or row.last_epoch >= ctx.epoch or write_blocked(row.holder_node_id, RELATIONS_KEY):
            continue
        toward = -1 if row.friendship > 0 else 1 if row.friendship < 0 else 0
        if "familiarity" not in row.locked:
            row.familiarity = max(0, row.familiarity - table.familiarity_fade)
        if "friendship" not in row.locked and toward:
            step = min(abs(row.friendship), table.friendship_fade)
            row.friendship += toward * step
        faded += 1
    return faded


async def living_mortals_by_place(ctx: TickContext, mortals: list[EntityRow]) -> dict[int, list[EntityRow]]:
    places: dict[int, list[EntityRow]] = defaultdict(list)
    for mortal in mortals:
        if mortal.location_id is not None and mortal.status is EntityStatus.CANON and mortal.entity_type is EntityType.MORTAL:
            places[mortal.location_id].append(mortal)
    return places


GAIN_THOUGHTS = {RelationType.FRIEND: ThoughtKind.MADE_A_FRIEND, RelationType.LOVER: ThoughtKind.FELL_IN_LOVE, RelationType.CRUSH: ThoughtKind.FELL_IN_LOVE}
LOSS_THOUGHTS = {RelationType.FRIEND: ThoughtKind.LOST_A_FRIEND, RelationType.LOVER: ThoughtKind.HEARTBROKEN}


async def feel_changes(ctx: TickContext, row: RelationshipRow, before: set[RelationType], after: set[RelationType]) -> None:
    for kind, thought in GAIN_THOUGHTS.items():
        if kind in after - before:
            await think(ctx.session, ctx.rules, row.holder_node_id, thought, ctx.epoch, subject_id=row.subject_node_id)
    for kind, thought in LOSS_THOUGHTS.items():
        if kind in before - after:
            await think(ctx.session, ctx.rules, row.holder_node_id, thought, ctx.epoch, subject_id=row.subject_node_id)

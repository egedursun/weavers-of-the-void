from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.tenets import STRATUM_NAMES
from aerona.constants.units import PERCENT
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import AfterlifeStratumRow, CultDoctrineRow, SoulJudgementRow, SpiritProfileRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import TraditionKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.faith import AfterlifeState, FuneralRite, JudgementDoctrine, SpiritAlignment, StratumKind, TenetKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import LawKind
from aerona.engine.context import TickContext
from aerona.engine.faith.book import faith_tenets, patron_node
from aerona.engine.mind.book import traits_of, values_for
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry.doctrine import AfterlifeRules

HALF = 2
TEN = 10
NEUTRAL = 50
FAVOURED = 70
FORSAKEN = 20
RITE_SCORE = 75
NO_RITE_SCORE = 10
VALUE_SPAN = 200


def as_percent(value: int) -> int:
    return clamp_int((value + PERCENT) * PERCENT / VALUE_SPAN, 0, PERCENT)


async def ledger(ctx: TickContext, mortal: EntityRow) -> dict[str, int]:
    values = await values_for(ctx.session, mortal.id)
    kills = await ctx.session.scalar(select(func.count(BondRow.id)).where(BondRow.source_node_id == mortal.id, BondRow.kind == BondKind.KILLED))
    grudges = await ctx.session.scalar(
        select(func.coalesce(func.sum(MemoryRow.magnitude), 0)).where(MemoryRow.subject_node_id == mortal.id, MemoryRow.magnitude < 0)
    )
    return {
        "renown": clamp_int(stat(mortal, "charisma") or 0, 0, PERCENT),
        "honour": as_percent(values.get(ValueAxis.HONOUR, 0)),
        "faith": as_percent(values.get(ValueAxis.PIETY, 0)),
        "violence": clamp_int(int(kills or 0) * TEN, 0, PERCENT),
        "infamy": clamp_int(-int(grudges or 0) // TEN, 0, PERCENT),
    }


FUNERAL_WORDS = ((("burn", "pyre", "fire", "ash"), FuneralRite.BURNING), (("sky", "tower", "vulture", "expos", "wind"), FuneralRite.EXPOSURE))


async def funeral_custom(ctx: TickContext, community_id: int) -> FuneralRite | None:
    kept = select(BondRow.target_node_id).where(BondRow.source_node_id == community_id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE)
    rites = select(TraditionProfileRow.tradition_entity_id).where(
        TraditionProfileRow.tradition_entity_id.in_(kept), TraditionProfileRow.kind == TraditionKind.FUNERAL_RITE
    )
    tradition = await ctx.session.scalar(
        select(EntityRow).where(EntityRow.id.in_(rites), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id).limit(1)
    )
    if tradition is None:
        return None
    text = f"{tradition.name} {tradition.subtype or ''}".lower()
    return next((rite for words, rite in FUNERAL_WORDS if any(word in text for word in words)), FuneralRite.BURIAL)


async def rite_for(ctx: TickContext, mortal: EntityRow) -> FuneralRite:
    table = ctx.rules.afterlife
    fell = await ctx.session.scalar(
        select(InjuryRow.id).where(InjuryRow.bearer_node_id == mortal.id, InjuryRow.cause_kind.in_([HarmCause.BATTLE, HarmCause.DUEL])).limit(1)
    )
    chance = table.battle_no_rite_chance if fell is not None else table.no_rite_chance
    if ctx.rng(f"rite.{mortal.id}").chance(chance):
        return FuneralRite.NONE
    home = mortal.location_id
    custom = await law_param(ctx.session, home, LawKind.BURIAL_LAW, "rite") if home is not None else None
    if custom in {rite.value for rite in FuneralRite}:
        return FuneralRite(str(custom))
    kept = await funeral_custom(ctx, home) if home is not None else None
    return kept or FuneralRite.BURIAL


async def judgement_for(ctx: TickContext, mortal: EntityRow) -> tuple[SonRow | None, JudgementDoctrine, set[TenetKind]]:
    god_id = await patron_node(ctx.session, mortal.id)
    son = await ctx.session.get(SonRow, god_id) if god_id is not None else None
    home = mortal.location_id
    tenets = await faith_tenets(ctx.session, home) if home is not None else set()
    if son is None:
        return None, JudgementDoctrine.NONE, tenets
    cults = select(BondRow.source_node_id).where(BondRow.target_node_id == son.id, BondRow.kind == BondKind.WORSHIPS)
    doctrine = await ctx.session.scalar(
        select(CultDoctrineRow).where(CultDoctrineRow.cult_entity_id.in_(cults)).order_by(CultDoctrineRow.cult_entity_id).limit(1)
    )
    return son, doctrine.judgement if doctrine is not None else JudgementDoctrine.DEEDS, tenets


def score_of(deeds: dict[str, int], doctrine: JudgementDoctrine, *, rite: FuneralRite, favoured: bool, tenets: set[TenetKind]) -> int:
    if doctrine is JudgementDoctrine.DEEDS:
        violence = deeds["violence"] if TenetKind.MARTYRDOM_GLORY in tenets or TenetKind.HOLY_WAR in tenets else -deeds["violence"]
        return clamp_int((deeds["renown"] + deeds["honour"] + (PERCENT - deeds["infamy"])) / 3 + violence / 4, 0, PERCENT)
    if doctrine is JudgementDoctrine.FAITH:
        return deeds["faith"]
    if doctrine is JudgementDoctrine.RITE:
        return RITE_SCORE if rite is not FuneralRite.NONE else NO_RITE_SCORE
    if doctrine is JudgementDoctrine.FAVOUR:
        return FAVOURED if favoured else FORSAKEN
    return NEUTRAL


async def strata_of(ctx: TickContext, realm: EntityRow, tenets: set[TenetKind]) -> dict[StratumKind, AfterlifeStratumRow]:
    rows = {row.kind: row for row in await ctx.session.scalars(select(AfterlifeStratumRow).where(AfterlifeStratumRow.realm_entity_id == realm.id))}
    wanted = [StratumKind.PARADISE, StratumKind.PLAIN, StratumKind.TORMENT, StratumKind.OBLIVION]
    if tenets & {TenetKind.MARTYRDOM_GLORY, TenetKind.HOLY_WAR}:
        wanted.append(StratumKind.WARRIOR_HALL)
    if TenetKind.ANCESTOR_VENERATION in tenets:
        wanted.append(StratumKind.ANCESTOR_HALL)
    table = ctx.rules.afterlife
    criteria: dict[StratumKind, dict[str, int | str]] = {
        StratumKind.PARADISE: {"score_at_least": table.paradise_score},
        StratumKind.PLAIN: {"score_between": f"{table.torment_score}-{table.paradise_score}"},
        StratumKind.TORMENT: {"score_below": table.torment_score},
        StratumKind.OBLIVION: {"no_god": 1},
        StratumKind.WARRIOR_HALL: {"violence_at_least": table.warrior_violence},
        StratumKind.ANCESTOR_HALL: {"rite": "any"},
    }
    for kind in wanted:
        if kind not in rows:
            row = AfterlifeStratumRow(
                realm_entity_id=realm.id, kind=kind, name=f"{STRATUM_NAMES[kind]} of {realm.name}"[:200], criteria=criteria[kind], population=0
            )
            ctx.session.add(row)
            rows[kind] = row
    await ctx.session.flush()
    return rows


def stratum_for(table: AfterlifeRules, *, score: int, deeds: dict[str, int], god: SonRow | None, rite: FuneralRite, tenets: set[TenetKind]) -> StratumKind:
    paradise, torment, warrior = table.paradise_score, table.torment_score, table.warrior_violence
    if god is None:
        return StratumKind.OBLIVION
    if deeds["violence"] >= warrior and tenets & {TenetKind.MARTYRDOM_GLORY, TenetKind.HOLY_WAR}:
        return StratumKind.WARRIOR_HALL
    if score >= paradise:
        return StratumKind.PARADISE
    if score < torment:
        return StratumKind.TORMENT
    if TenetKind.ANCESTOR_VENERATION in tenets and rite is not FuneralRite.NONE:
        return StratumKind.ANCESTOR_HALL
    return StratumKind.PLAIN


@dataclass
class Verdict:
    stratum: AfterlifeStratumRow | None
    score: int
    reason: str


async def profile_for(ctx: TickContext, spirit: EntityRow, mortal: EntityRow) -> SpiritProfileRow:
    profile = await ctx.session.get(SpiritProfileRow, spirit.id)
    if profile is not None:
        return profile
    values = await values_for(ctx.session, mortal.id)
    profile = SpiritProfileRow(
        spirit_entity_id=spirit.id,
        origin_mortal_id=mortal.id,
        imprint={axis.value: value for axis, value in values.items()},
        traits=sorted(trait.value for trait in await traits_of(ctx.session, mortal.id)),
        deeds=await ledger(ctx, mortal),
        memory_strength=PERCENT,
        veneration=0,
        alignment=SpiritAlignment.NEUTRAL,
        state=AfterlifeState.WANDERING,
        rite=await rite_for(ctx, mortal),
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(profile)
    return profile


async def judge(ctx: TickContext, spirit: EntityRow, mortal: EntityRow, realm: EntityRow | None) -> Verdict:
    profile = await profile_for(ctx, spirit, mortal)
    son, doctrine, tenets = await judgement_for(ctx, mortal)
    profile.patron_son_id = son.id if son is not None else None
    if TenetKind.SOULS_REST in tenets:
        profile.sealed = True
    if profile.rite is FuneralRite.NONE and doctrine is not JudgementDoctrine.RITE:
        profile.state = AfterlifeState.WANDERING
        set_stats(spirit, unrest=max(stat(spirit, "unrest") or 0, ctx.rules.afterlife.restless_unrest))
        reason = "no rites were said; the soul wanders restless"
        ctx.session.add(
            SoulJudgementRow(
                spirit_entity_id=spirit.id, son_id=profile.patron_son_id, doctrine=doctrine, score=0, rite=profile.rite, reason=reason, epoch=ctx.epoch
            )
        )
        return Verdict(None, 0, reason)
    devotion = await ctx.session.scalar(
        select(func.coalesce(func.sum(MemoryRow.magnitude), 0)).where(
            MemoryRow.holder_node_id == mortal.id, MemoryRow.subject_node_id == (son.id if son is not None else -1)
        )
    )
    favoured = son is not None and (mortal.creator_son_id == son.id or int(devotion or 0) >= ctx.rules.afterlife.favour_relation)
    score = score_of(profile.deeds, doctrine, rite=profile.rite, favoured=favoured, tenets=tenets)
    kind = stratum_for(ctx.rules.afterlife, score=score, deeds=profile.deeds, god=son, rite=profile.rite, tenets=tenets)
    stratum = (await strata_of(ctx, realm, tenets))[kind] if realm is not None else None
    if stratum is not None:
        stratum.population += 1
        profile.stratum_id = stratum.id
        profile.state = AfterlifeState.IN_REALM
    else:
        profile.state = AfterlifeState.JUDGED
    if kind is StratumKind.TORMENT:
        profile.alignment = SpiritAlignment.VENGEFUL
    elif kind in {StratumKind.ANCESTOR_HALL, StratumKind.PARADISE}:
        profile.alignment = SpiritAlignment.GUARDIAN
    reason = f"judged by {doctrine.value.replace('_', ' ')}: score {score}, sent to {kind.value.replace('_', ' ')}"
    ctx.session.add(
        SoulJudgementRow(
            spirit_entity_id=spirit.id,
            son_id=profile.patron_son_id,
            doctrine=doctrine,
            stratum_id=stratum.id if stratum is not None else None,
            score=score,
            rite=profile.rite,
            reason=reason,
            epoch=ctx.epoch,
        )
    )
    return Verdict(stratum, score, reason)


def ledger_score(deeds: dict[str, int]) -> int:
    return max(deeds.get("renown", 0), deeds.get("faith", 0), round_half_up((deeds.get("honour", 0) + deeds.get("violence", 0)) / HALF))

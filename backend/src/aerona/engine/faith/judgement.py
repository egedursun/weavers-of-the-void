from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.afterlife import STRATUM_VALENCES
from aerona.catalog.peoples import FUNERALS
from aerona.catalog.strata import ADMISSION_PRIORITY, STRATUM_AXES, StratumAxes
from aerona.catalog.tenets import STRATUM_NAMES
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmography import DimensionRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import AfterlifeStratumRow, CultDoctrineRow, SoulJudgementRow, SpiritProfileRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import RiteStage, TraditionFunction
from aerona.domain.enums.demography import FuneralCustom
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.faith import (
    AfterlifeState,
    JudgementDoctrine,
    SpiritAlignment,
    StratumActivity,
    StratumAdmission,
    StratumContact,
    StratumKind,
    StratumValence,
    TenetKind,
)
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import LawKind
from aerona.domain.models.faith import StratumCriteria
from aerona.engine.context import TickContext
from aerona.engine.cosmos.strata import drawing_dimensions, host_for
from aerona.engine.demography.rites import rite_of
from aerona.engine.faith.book import faith_tenets, patron_node
from aerona.engine.mind.book import traits_of, values_for
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.sacred.guards import rite_chance
from aerona.engine.structures.readers import rite_keeping
from aerona.rules.registry import Rules
from aerona.rules.registry.doctrine import AfterlifeRules

HALF = 2
VALUE_SPAN = 200
DEEDS_PARTS = 3
VIOLENCE_SHARE = 4
WARLIKE = frozenset({TenetKind.MARTYRDOM_GLORY, TenetKind.HOLY_WAR})
EXECUTIONS = (HarmCause.PUNISHMENT, HarmCause.SACRIFICE)


def as_percent(value: int) -> int:
    return clamp_int((value + PERCENT) * PERCENT / VALUE_SPAN, 0, PERCENT)


async def ledger(ctx: TickContext, mortal: EntityRow) -> dict[str, int]:
    table = ctx.rules.afterlife
    values = await values_for(ctx.session, mortal.id)
    kills = await ctx.session.scalar(select(func.count(BondRow.id)).where(BondRow.source_node_id == mortal.id, BondRow.kind == BondKind.KILLED))
    grudges = await ctx.session.scalar(
        select(func.coalesce(func.sum(MemoryRow.magnitude), 0)).where(MemoryRow.subject_node_id == mortal.id, MemoryRow.magnitude < 0)
    )
    return {
        "renown": clamp_int(stat(mortal, "charisma") or 0, 0, PERCENT),
        "honour": as_percent(values.get(ValueAxis.HONOUR, 0)),
        "faith": as_percent(values.get(ValueAxis.PIETY, 0)),
        "violence": clamp_int(int(kills or 0) * table.violence_per_kill, 0, PERCENT),
        "infamy": clamp_int(-int(grudges or 0) // table.grudge_divisor, 0, PERCENT),
    }


def custom_from_values(table: AfterlifeRules, values: dict[ValueAxis, int]) -> FuneralCustom:
    purity, nature = values.get(ValueAxis.PURITY, 0), values.get(ValueAxis.NATURE, 0)
    if purity >= table.custom_value and purity >= nature:
        return FuneralCustom.CREMATION
    if nature >= table.custom_value:
        return FuneralCustom.SKY_BURIAL
    return FuneralCustom.BURIAL


async def funeral_custom(ctx: TickContext, community_id: int) -> FuneralCustom | None:
    community = await ctx.session.get(EntityRow, community_id)
    custom = await rite_of(ctx.session, community) if community is not None else None
    if custom is not None:
        return custom
    kept = select(BondRow.target_node_id).where(BondRow.source_node_id == community_id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE)
    living = select(EntityRow.id).where(EntityRow.id.in_(kept), EntityRow.status == EntityStatus.CANON)
    profile = await ctx.session.scalar(
        select(TraditionProfileRow)
        .where(
            TraditionProfileRow.tradition_entity_id.in_(living),
            TraditionProfileRow.kind == TraditionFunction.RITE_OF_PASSAGE,
            TraditionProfileRow.stage == RiteStage.DEATH,
        )
        .order_by(TraditionProfileRow.tradition_entity_id)
        .limit(1)
    )
    if profile is None:
        return None
    return profile.funeral_rite or custom_from_values(ctx.rules.afterlife, await values_for(ctx.session, community_id))


async def rite_for(ctx: TickContext, mortal: EntityRow) -> FuneralCustom:
    table = ctx.rules.afterlife
    causes = set(await ctx.session.scalars(select(InjuryRow.cause_kind).where(InjuryRow.bearer_node_id == mortal.id)))
    if causes & set(EXECUTIONS) and ctx.rng(f"nameless.{mortal.id}").chance(table.nameless_execution_pct):
        return FuneralCustom.NAMELESS
    base = table.battle_no_rite_chance if causes & {HarmCause.BATTLE, HarmCause.DUEL} else table.no_rite_chance
    chance = await rite_chance(ctx, mortal, base * (1 - await rite_keeping(ctx.session, ctx.rules, mortal.location_id)))
    if ctx.rng(f"rite.{mortal.id}").chance(chance):
        return FuneralCustom.NONE
    home = mortal.location_id
    custom = await law_param(ctx.session, home, LawKind.BURIAL_LAW, "rite") if home is not None else None
    if custom in {rite.value for rite in FuneralCustom}:
        return FuneralCustom(str(custom))
    kept = await funeral_custom(ctx, home) if home is not None else None
    return kept or FuneralCustom.BURIAL


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


def score_of(table: AfterlifeRules, deeds: dict[str, int], doctrine: JudgementDoctrine, *, rite: FuneralCustom, favoured: bool, tenets: set[TenetKind]) -> int:
    if doctrine is JudgementDoctrine.DEEDS:
        violence = deeds.get("violence", 0) if tenets & WARLIKE else -deeds.get("violence", 0)
        merit = deeds.get("renown", 0) + deeds.get("honour", 0) + (PERCENT - deeds.get("infamy", 0))
        return clamp_int(merit / DEEDS_PARTS + violence / VIOLENCE_SHARE, 0, PERCENT)
    if doctrine is JudgementDoctrine.FAITH:
        return deeds.get("faith", 0)
    if doctrine is JudgementDoctrine.RITE:
        return table.rite_score if FUNERALS[rite].counts_as_rite else table.no_rite_score
    if doctrine is JudgementDoctrine.FAVOUR:
        return table.favoured_score if favoured else table.forsaken_score
    return table.neutral_score


def valence_bounds(table: AfterlifeRules, valence: StratumValence) -> dict[str, int]:
    spec = STRATUM_VALENCES[valence]
    bounds: dict[str, int] = {}
    if spec.floor_rule is not None:
        bounds["score_at_least"] = int(getattr(table, spec.floor_rule))
    if spec.ceiling_rule is not None:
        bounds["score_below"] = int(getattr(table, spec.ceiling_rule))
    return bounds


def admission_bounds(table: AfterlifeRules, axes: StratumAxes) -> dict[str, int | bool]:
    if axes.admission is StratumAdmission.BY_FAITH:
        return {"faith_at_least": table.paradise_score}
    if axes.admission is StratumAdmission.BY_RITES:
        return {"needs_rite": True}
    if axes.admission is StratumAdmission.BY_DEEDS:
        return {**valence_bounds(table, axes.valence)}
    return {}


def axes_criteria(table: AfterlifeRules, axes: StratumAxes) -> StratumCriteria:
    priority = ADMISSION_PRIORITY[axes.admission]
    if axes.activity is StratumActivity.DISSOLUTION:
        return StratumCriteria(priority=priority // 10, no_god=True)
    if axes.admission is StratumAdmission.BY_MANNER_OF_DEATH:
        return StratumCriteria(priority=priority, violence_at_least=table.warrior_violence, tenets_any=tuple(sorted(WARLIKE)))
    if axes.admission is StratumAdmission.BY_LINE:
        return StratumCriteria(
            priority=priority,
            needs_rite=True,
            score_at_least=table.torment_score,
            score_below=table.paradise_score,
            tenets_any=(TenetKind.ANCESTOR_VENERATION,),
        )
    return StratumCriteria(priority=priority, **admission_bounds(table, axes))


def default_criteria(table: AfterlifeRules, kind: StratumKind) -> StratumCriteria:
    return axes_criteria(table, STRATUM_AXES[kind])


def axes_of(row: AfterlifeStratumRow) -> StratumAxes:
    return StratumAxes(row.valence, row.permanence, row.admission, row.activity, row.contact)


def wanted_strata(tenets: set[TenetKind]) -> list[StratumKind]:
    wanted = [StratumKind.REWARD, StratumKind.COMMON, StratumKind.PUNISHMENT, StratumKind.DISSOLUTION]
    if tenets & WARLIKE:
        wanted.append(StratumKind.BY_MANNER_OF_DEATH)
    if TenetKind.ANCESTOR_VENERATION in tenets:
        wanted.append(StratumKind.BY_LINE)
    return wanted


def new_stratum(rules: Rules, realm: EntityRow, kind: StratumKind) -> AfterlifeStratumRow:
    axes = STRATUM_AXES[kind]
    return AfterlifeStratumRow(
        realm_entity_id=realm.id,
        kind=kind,
        valence=axes.valence,
        permanence=axes.permanence,
        admission=axes.admission,
        activity=axes.activity,
        contact=axes.contact,
        name=f"{STRATUM_NAMES[kind]} of {realm.name}",
        criteria=default_criteria(rules.afterlife, kind).stored(),
        population=0,
        closed=False,
    )


async def strata_of(ctx: TickContext, realm: EntityRow, tenets: set[TenetKind]) -> list[AfterlifeStratumRow]:
    rows = list(await ctx.session.scalars(select(AfterlifeStratumRow).where(AfterlifeStratumRow.realm_entity_id == realm.id).order_by(AfterlifeStratumRow.id)))
    present = {row.kind for row in rows}
    missing = [kind for kind in wanted_strata(tenets) if kind not in present]
    dimensions = list(await ctx.session.scalars(select(DimensionRow).order_by(DimensionRow.id))) if missing else []
    for kind in missing:
        row = new_stratum(ctx.rules, realm, kind)
        host = host_for(dimensions, row.valence, row.activity)
        row.dimension_id = host.id if host is not None else None
        ctx.session.add(row)
        rows.append(row)
    await ctx.session.flush()
    return rows


def admits(row: AfterlifeStratumRow, god: SonRow | None, cults: set[int]) -> bool:
    if row.closed:
        return False
    if row.son_id is not None and (god is None or god.id != row.son_id):
        return False
    return row.cult_entity_id is None or row.cult_entity_id in cults


def route(
    strata: list[AfterlifeStratumRow],
    *,
    score: int,
    deeds: dict[str, int],
    god: SonRow | None,
    rite: FuneralCustom,
    tenets: set[TenetKind],
    cults: set[int] | None = None,
) -> AfterlifeStratumRow | None:
    chosen = [(StratumCriteria.read(row.criteria), row) for row in strata if admits(row, god, cults or set())]
    for criteria, row in sorted(chosen, key=lambda item: (item[0].priority, item[1].id)):
        if criteria.matches(score=score, deeds=deeds, has_god=god is not None, rite=rite, rite_kept=FUNERALS[rite].counts_as_rite, tenets=tenets):
            return row
    return None


async def cults_of(ctx: TickContext, god: SonRow | None) -> set[int]:
    if god is None:
        return set()
    return set(await ctx.session.scalars(select(BondRow.source_node_id).where(BondRow.target_node_id == god.id, BondRow.kind == BondKind.WORSHIPS)))


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
    rite = await rite_for(ctx, mortal)
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
        rite=rite,
        sealed=FUNERALS[rite].seals,
        seal_strength=ctx.rules.afterlife.nameless_seal if FUNERALS[rite].seals else 0,
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(profile)
    return profile


def seal(profile: SpiritProfileRow, strength: int) -> None:
    if "sealed" in profile.locked:
        return
    profile.sealed = True
    profile.seal_strength = clamp_int(max(profile.seal_strength, strength), 0, PERCENT)


def unseal(profile: SpiritProfileRow) -> None:
    if "sealed" in profile.locked:
        return
    profile.sealed, profile.seal_strength = False, 0


async def recount(ctx: TickContext, stratum_ids: set[int] | None = None) -> None:
    statement = select(AfterlifeStratumRow)
    if stratum_ids is not None:
        statement = statement.where(AfterlifeStratumRow.id.in_(list(stratum_ids)))
    strata = list(await ctx.session.scalars(statement))
    if not strata:
        return
    await ctx.session.flush()
    counts = dict(
        (
            await ctx.session.execute(
                select(SpiritProfileRow.stratum_id, func.count(SpiritProfileRow.spirit_entity_id))
                .join(EntityRow, EntityRow.id == SpiritProfileRow.spirit_entity_id)
                .where(
                    SpiritProfileRow.stratum_id.in_([row.id for row in strata]),
                    SpiritProfileRow.state == AfterlifeState.IN_REALM,
                    EntityRow.status == EntityStatus.CANON,
                )
                .group_by(SpiritProfileRow.stratum_id)
            )
        ).all()
    )
    for row in strata:
        row.population = int(counts.get(row.id, 0))


async def reaches_living(session: AsyncSession, profile: SpiritProfileRow) -> bool:
    stratum = await session.get(AfterlifeStratumRow, profile.stratum_id) if profile.stratum_id is not None else None
    if stratum is None or stratum.contact is StratumContact.OPEN:
        return True
    return stratum.contact is StratumContact.BY_RITE and FUNERALS[profile.rite].counts_as_rite


async def leave_realm(ctx: TickContext, profile: SpiritProfileRow, state: AfterlifeState) -> None:
    old = profile.stratum_id
    profile.state = state
    if old is not None:
        await recount(ctx, {old})


async def place(ctx: TickContext, profile: SpiritProfileRow, stratum: AfterlifeStratumRow | None) -> None:
    old = profile.stratum_id
    if stratum is None:
        profile.stratum_id, profile.state = None, AfterlifeState.JUDGED
    else:
        profile.stratum_id, profile.state = stratum.id, AfterlifeState.IN_REALM
    await recount(ctx, {item for item in (old, profile.stratum_id) if item is not None})


async def judge(ctx: TickContext, spirit: EntityRow, mortal: EntityRow, realm: EntityRow | None) -> Verdict:
    profile = await profile_for(ctx, spirit, mortal)
    son, doctrine, tenets = await judgement_for(ctx, mortal)
    if "patron_son_id" in profile.locked:
        son = await ctx.session.get(SonRow, profile.patron_son_id) if profile.patron_son_id is not None else None
    else:
        profile.patron_son_id = son.id if son is not None else None
    if TenetKind.SOULS_REST in tenets:
        seal(profile, PERCENT)
    if not FUNERALS[profile.rite].counts_as_rite and doctrine is not JudgementDoctrine.RITE:
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
    score = score_of(ctx.rules.afterlife, profile.deeds, doctrine, rite=profile.rite, favoured=favoured, tenets=tenets)
    strata = await strata_of(ctx, realm, tenets) if realm is not None else []
    cults = await cults_of(ctx, son)
    drawing = await drawing_dimensions(ctx.session) if strata else set()
    drawn = [row for row in strata if row.dimension_id in drawing]
    stratum = None
    if drawn and ctx.rng(f"soul_draw.{spirit.id}").chance(ctx.rules.dimensions.soul_draw_chance):
        stratum = route(drawn, score=score, deeds=profile.deeds, god=son, rite=profile.rite, tenets=tenets, cults=cults)
    if stratum is None:
        stratum = route(strata, score=score, deeds=profile.deeds, god=son, rite=profile.rite, tenets=tenets, cults=cults)
    await place(ctx, profile, stratum)
    valence = stratum.valence if stratum is not None else None
    if "alignment" not in profile.locked:
        if valence is StratumValence.PUNISHMENT:
            profile.alignment = SpiritAlignment.VENGEFUL
        elif valence is StratumValence.REWARD:
            profile.alignment = SpiritAlignment.GUARDIAN
    where = stratum.name if stratum is not None else "no stratum that would take it"
    reason = f"judged by {spoken(doctrine)}: score {score}, sent to {where}"
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

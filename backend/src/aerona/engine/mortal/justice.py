from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.ethics import CRIME_ACTS, HONOUR_MODELS
from aerona.catalog.laws import PENALTY_CRUELTY
from aerona.catalog.thoughts import THOUGHTS
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import BodyPart, DamageType, HarmCause, InjuryKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.mind import ActKind, ThoughtKind
from aerona.domain.enums.mortal import CrimeKind, DeathCause, PunishmentKind
from aerona.domain.enums.polity import LawKind
from aerona.engine.body.hits import Harm
from aerona.engine.constructs.remaking import may_remake, remake
from aerona.engine.context import TickContext
from aerona.engine.factions.estates import immune
from aerona.engine.law.prisons import imprison
from aerona.engine.lifecycle.mortal_death import die
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.ethics import culture_of, honour_of
from aerona.engine.mind.hooks import judged
from aerona.engine.mind.thoughts import think
from aerona.engine.mortal.standing import add_infamy, add_wealth
from aerona.engine.notes import note
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.queries import active_bonds, add_flag, living_entity

JUDGED_CRIMES = frozenset({CrimeKind.THEFT, CrimeKind.BLASPHEMY, CrimeKind.TREASON})
CODE_PUNISHMENTS: dict[str, PunishmentKind] = {
    "fine": PunishmentKind.FINE,
    "pillory": PunishmentKind.PUBLIC_SHAMING,
    "wergild": PunishmentKind.FINE,
    "flogging": PunishmentKind.FLOGGING,
    "prison": PunishmentKind.IMPRISONMENT,
    "hand": PunishmentKind.HAND,
    "blinding": PunishmentKind.EYES,
    "tongue": PunishmentKind.TONGUE,
    "exile": PunishmentKind.EXILE,
    "death": PunishmentKind.DEATH,
    "remaking": PunishmentKind.REMAKING,
}
MUTILATIONS: dict[PunishmentKind, tuple[BodyPart, ...]] = {
    PunishmentKind.HAND: (BodyPart.RIGHT_HAND,),
    PunishmentKind.TONGUE: (BodyPart.TONGUE,),
    PunishmentKind.EYES: (BodyPart.LEFT_EYE, BodyPart.RIGHT_EYE),
}
MUTILATION_KINDS: dict[PunishmentKind, InjuryKind] = {
    PunishmentKind.HAND: InjuryKind.SEVERED,
    PunishmentKind.TONGUE: InjuryKind.SEVERED,
    PunishmentKind.EYES: InjuryKind.GOUGED,
}
SENTENCE_TEXT = total(
    PunishmentKind,
    {
        PunishmentKind.FINE: "was fined",
        PunishmentKind.PUBLIC_SHAMING: "was shamed in public",
        PunishmentKind.FLOGGING: "was flogged",
        PunishmentKind.EXILE: "was sent into exile",
        PunishmentKind.BRANDING: "was branded",
        PunishmentKind.HAND: "lost a hand to the law",
        PunishmentKind.TONGUE: "had their tongue cut out by the law",
        PunishmentKind.EYES: "was blinded by the law",
        PunishmentKind.DEATH: "was put to death",
        PunishmentKind.IMPRISONMENT: "was sent to prison",
        PunishmentKind.REMAKING: "was remade in body by the law",
    },
)
CRIME_TEXT = total(
    CrimeKind,
    {
        CrimeKind.THEFT: "theft",
        CrimeKind.BLASPHEMY: "blasphemy",
        CrimeKind.TREASON: "treason",
        CrimeKind.MURDER: "murder",
        CrimeKind.DESERTION: "desertion",
    },
)


def cruelty_of(punishment: PunishmentKind) -> int:
    name = next((name for name, kind in CODE_PUNISHMENTS.items() if kind is punishment), None)
    return PENALTY_CRUELTY.get(name, 0) if name is not None else 0


async def community_ruler(session: AsyncSession, community_id: int | None) -> EntityRow | None:
    if community_id is None:
        return None
    for bond in await active_bonds(session, [BondKind.RULES], targets=[community_id]):
        ruler = await living_entity(session, bond.source_node_id)
        if ruler is not None and ruler.entity_type is EntityType.MORTAL:
            return ruler
    return None


async def code_punishment(ctx: TickContext, community_id: int | None, crime: CrimeKind) -> PunishmentKind:
    value = await law_param(ctx.session, community_id, LawKind.PENAL_CODE, crime.value) if community_id is not None else None
    chosen = CODE_PUNISHMENTS.get(str(value), PunishmentKind.FINE) if value is not None else PunishmentKind.FINE
    table = ctx.rules.punishment
    if chosen in MUTILATIONS and community_id is not None and ctx.rng(f"mercy.{community_id}.{crime.value}").chance(table.exile_chance):
        return PunishmentKind.EXILE
    if chosen is PunishmentKind.DEATH and crime is CrimeKind.TREASON and not table.death_for_treason:
        return PunishmentKind.EXILE
    if chosen is PunishmentKind.DEATH and crime is CrimeKind.BLASPHEMY and not table.death_for_blasphemy:
        return PunishmentKind.TONGUE
    cruel = chosen in MUTILATIONS or chosen is PunishmentKind.DEATH
    if cruel and await may_remake(ctx, community_id) and ctx.rng(f"remake.{community_id}.{crime.value}").chance(ctx.rules.punitive_remaking.remake_chance):
        return PunishmentKind.REMAKING
    return chosen


async def shame_publicly(ctx: TickContext, culprit: EntityRow, judge: EntityRow | None) -> None:
    culture = await culture_of(ctx.session, culprit.id)
    spec = HONOUR_MODELS[await honour_of(ctx.session, culture.id if culture is not None else None)]
    await add_infamy(ctx.session, culprit.id, ctx.rules.ethics.pillory_infamy * spec.public_shame_pct / PERCENT, ctx.epoch, rules=ctx.rules)
    size = THOUGHTS[ThoughtKind.WAS_SHAMED].intensity * spec.public_shame_pct / PERCENT
    await think(ctx.session, ctx.rules, culprit.id, ThoughtKind.WAS_SHAMED, ctx.epoch, subject_id=judge.id if judge is not None else None, intensity=size)


async def jailed_or_fined(ctx: TickContext, culprit: EntityRow, punishment: PunishmentKind, case_id: int | None) -> PunishmentKind:
    if punishment is PunishmentKind.IMPRISONMENT and await imprison(ctx, culprit, case_id=case_id) is None:
        return PunishmentKind.FINE
    if punishment is PunishmentKind.REMAKING:
        await remake(ctx, culprit, case_id)
    return punishment


async def sentence(
    ctx: TickContext, culprit: EntityRow, crime: CrimeKind, punishment: PunishmentKind, *, judge: EntityRow | None = None, case_id: int | None = None
) -> bool:
    table = ctx.rules.punishment
    reason = f"punished for {CRIME_TEXT[crime]}"
    if await immune(ctx, culprit):
        return False
    await think(ctx.session, ctx.rules, culprit.id, ThoughtKind.WAS_PUNISHED, ctx.epoch, subject_id=judge.id if judge is not None else None)
    if crime in JUDGED_CRIMES:
        await judged(ctx, culprit.id, culprit.id, CRIME_ACTS[crime])
    if punishment is PunishmentKind.PUBLIC_SHAMING:
        await shame_publicly(ctx, culprit, judge)
    punishment = await jailed_or_fined(ctx, culprit, punishment, case_id)
    if punishment is PunishmentKind.FINE:
        await add_wealth(ctx.session, culprit.id, -table.fine_wealth, ctx.epoch)
    elif punishment is PunishmentKind.FLOGGING:
        await apply_hits(
            ctx, culprit, Harm(ctx.rules.crime.punishment_hp, HarmCause.PUNISHMENT, reason, damage_type=DamageType.BLUNT, severity=2), lethal=False
        )
    elif punishment is PunishmentKind.EXILE:
        culprit.location_id = None
        await add_flag(ctx.session, culprit.id, EntityFlag.EXILE, ctx.epoch)
    elif punishment is PunishmentKind.BRANDING:
        await apply_hits(
            ctx,
            culprit,
            Harm(ctx.rules.crime.punishment_hp, HarmCause.PUNISHMENT, reason, damage_type=DamageType.FIRE, part=BodyPart.FACE, severity=1),
            lethal=False,
        )
        await add_infamy(ctx.session, culprit.id, table.branding_infamy, ctx.epoch, rules=ctx.rules)
    elif punishment in MUTILATIONS:
        for part in MUTILATIONS[punishment]:
            harm = Harm(
                ctx.rules.crime.punishment_hp,
                HarmCause.PUNISHMENT,
                reason,
                damage_type=DamageType.CUT,
                part=part,
                kind=MUTILATION_KINDS[punishment],
                severity=table.mutilation_severity,
                killer_id=judge.id if judge is not None else None,
            )
            await apply_hits(ctx, culprit, harm, lethal=False)
        if judge is not None:
            await add_infamy(ctx.session, judge.id, table.cruelty_infamy, ctx.epoch, rules=ctx.rules)
            await judged(ctx, judge.id, culprit.id, ActKind.MUTILATION)
    elif punishment is PunishmentKind.DEATH:
        if judge is not None:
            await judged(ctx, judge.id, culprit.id, ActKind.EXECUTION)
        await die(
            ctx, culprit, cause=f"executed for {CRIME_TEXT[crime]}", manner=DeathCause.EXECUTION, killer_id=judge.id if judge is not None else None, forced=True
        )
    text = f"{culprit.name} {SENTENCE_TEXT[punishment]} for {CRIME_TEXT[crime]}."
    await note(ctx, text, key=f"justice.{punishment.value}", ids=[culprit.id, *([judge.id] if judge is not None else [])])
    return True

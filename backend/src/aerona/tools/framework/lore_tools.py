from aerona.catalog.arcana import SCHOOL_GRAMMAR
from aerona.core.errors import AeronaError
from aerona.db.tables.culture import RiteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.arcana.grammar import Shape
from aerona.engine.context import TickContext
from aerona.engine.lore import art, ideology, rites
from aerona.engine.polity.book import RealmBook
from aerona.engine.primitives.queries import living_entity
from aerona.prompts.tools.results import result
from aerona.tools.framework.lore_inputs import CommissionInput, DesignRiteInput, FoundSchoolInput, LoreToolResult
from aerona.tools.framework.validation import fail

PAYING = frozenset({EntityType.POLITY, EntityType.SETTLEMENT})


async def commission(tick: TickContext, patron: EntityRow, args: CommissionInput) -> str:
    try:
        work = await art.commission_work(
            tick,
            patron.id,
            name=args.name,
            medium=args.medium,
            author_id=args.author_id,
            subject_id=args.subject_id,
            message=None,
            paid=patron.entity_type in PAYING,
        )
    except AeronaError as error:
        fail(LoreToolResult.UNABLE, reason=str(error))
    return result(LoreToolResult.COMMISSIONED, id=work.id, name=work.name)


async def design(tick: TickContext, holder: EntityRow, args: DesignRiteInput) -> str:
    technique, form = SCHOOL_GRAMMAR[args.school]
    shape = Shape(args.technique or technique, args.form or form, args.range, args.duration, args.target)
    plan = rites.Design(
        name=args.name,
        school=args.school,
        source=args.source,
        power=args.power,
        workings=tuple((item.effect, item.magnitude, item.damage_type, item.summon_form) for item in args.workings),
        shape=shape,
        paradigm_id=await known(tick, args.paradigm_id, EntityType.THEORY),
        myth_id=await known(tick, args.myth_id, EntityType.LEGEND),
    )
    rite, _ = await rites.design(tick, plan, holder)
    names = ", ".join(item.effect.value.replace("_", " ") for item in args.workings)
    return result(LoreToolResult.DESIGNED, id=rite.id, name=rite.name, workings=names)


async def known(tick: TickContext, entity_id: int | None, kind: EntityType) -> int | None:
    found = await living_entity(tick.session, entity_id) if entity_id is not None else None
    return found.id if found is not None and found.entity_type is kind else None


async def rite_of(tick: TickContext, rite_id: int) -> tuple[EntityRow, RiteProfileRow]:
    rite = await living_entity(tick.session, rite_id)
    row = await tick.session.get(RiteProfileRow, rite_id) if rite is not None else None
    if rite is None or row is None:
        fail(LoreToolResult.NOT_A_RITE, id=rite_id)
    return rite, row


async def cast(tick: TickContext, caster: EntityRow, rite_id: int, target_id: int | None) -> str:
    rite, row = await rite_of(tick, rite_id)
    target = await living_entity(tick.session, target_id) if target_id is not None else None
    realms = await RealmBook.load(tick.session)
    reason = await rites.lawful(tick, caster, row, realms) or await rites.unmet(tick, caster, row) or await rites.beyond_reach(tick, caster, row, target)
    if reason is not None:
        fail(LoreToolResult.REFUSED, name=rite.name, reason=reason)
    casting = await rites.cast(tick, caster, rite, row, target=target, realms=realms)
    if casting is None:
        fail(LoreToolResult.REFUSED, name=rite.name, reason="its price could not be paid")
    return result(LoreToolResult.CAST, name=rite.name, effect=casting.effect)


async def found(tick: TickContext, founder: EntityRow, args: FoundSchoolInput) -> str:
    creed = await ideology.found_school(tick, founder, list(args.tenets), args.name)
    return result(LoreToolResult.FOUNDED, id=creed.id, name=creed.name, tenets=", ".join(item.value.replace("_", " ") for item in args.tenets))

from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import LegendProfileRow, TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import LegendArchetype, RiteStage, TraditionFunction
from aerona.domain.enums.entity import EntityType
from aerona.engine.context import TickContext
from aerona.engine.lore import legends, traditions
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.words import names_word

TYPED_KINDS_FIXUP = "lore.typed_kinds_backfill"
A = LegendArchetype
K = TraditionFunction
LEGEND_WORDS = (
    (("flood", "deluge"), A.WORLD_DISASTER),
    (("king", "return", "throne"), A.RETURN_OF_A_RULER),
    (("betray", "traitor"), A.BETRAYAL),
    (("curse", "doom"), A.CURSED_LINE),
    (("ghost", "haunt", "shade"), A.HAUNTED_PLACE),
    (("chosen", "prophet"), A.CHOSEN_ONE),
    (("trick", "fox", "thief"), A.TRICKSTER),
    (("beginning", "creation", "first"), A.CREATION),
    (("paradise", "golden", "lost"), A.LOST_GOLDEN_AGE),
    (("beast", "dragon", "monster", "serpent"), A.MONSTER),
)
STAGE_WORDS = (
    (("funeral", "burial"), RiteStage.DEATH),
    (("wedding", "marriage"), RiteStage.UNION),
    (("naming",), RiteStage.NAMING),
    (("birth",), RiteStage.BIRTH),
    (("elder",), RiteStage.ELDERHOOD),
    (("initiation", "coming of age"), RiteStage.COMING_OF_AGE),
)
TRADITION_WORDS = (
    (("mourning", "lament", "wake"), K.MOURNING),
    (("funeral", "burial"), K.RITE_OF_PASSAGE),
    (("plague",), K.FAST),
    (("remembrance", "memorial", "commemoration"), K.COMMEMORATION),
    (("victory", "festival", "feast day", "carnival"), K.FESTIVAL),
    (("ancestor",), K.ANCESTRAL_RITE),
    (("harvest", "sowing"), K.SEASONAL_RITE),
    (("fast", "lent"), K.FAST),
    (("initiation", "wedding", "marriage", "coming of age", "naming", "birth", "elder"), K.RITE_OF_PASSAGE),
    (("taboo", "forbidden"), K.TABOO),
    (("offering", "sacrifice"), K.OFFERING),
    (("pilgrimage",), K.PILGRIMAGE),
    (("hospitality", "guest"), K.HOSPITALITY),
    (("duel", "honour"), K.DUEL_CUSTOM),
    (("war dance", "war-dance", "dance"), K.MARTIAL_DISPLAY),
    (("scar",), K.BODY_MARKING),
    (("oath", "peace"), K.FESTIVAL),
    (("gift", "giving"), K.GIFT_CUSTOM),
    (("purification", "cleansing"), K.PURIFICATION),
    (("games", "contest", "tournament"), K.COMPETITION),
)


def read_once[E](entity: EntityRow, table: tuple[tuple[tuple[str, ...], E], ...]) -> E | None:
    text = f"{entity.name} {entity.subtype or ''}".lower()
    return next((found for words, found in table if names_word(text, words)), None)


async def backfill_legends(ctx: TickContext) -> dict[str, int]:
    counts = {"legends_typed": 0, "legends_credence": 0, "legends_sourced": 0}
    for legend in await canon(ctx.session, [EntityType.LEGEND]):
        existing = await ctx.session.get(LegendProfileRow, legend.id)
        if existing is None:
            await legends.profile_of(ctx, legend, read_once(legend, LEGEND_WORDS))
            counts["legends_typed"] += 1
            continue
        if held(legend.id):
            continue
        if "credence" not in existing.locked and existing.credence == getattr(LegendProfileRow.__table__.c.credence.default, "arg", None):
            existing.credence = legends.credence_from(ctx, legend)
            counts["legends_credence"] += 1
        if existing.source_incident_id is None:
            subject = await ctx.session.get(EntityRow, existing.subject_node_id) if existing.subject_node_id is not None else None
            existing.source_incident_id = await legends.source_of(ctx, subject)
            counts["legends_sourced"] += int(existing.source_incident_id is not None)
    return counts


async def backfill_traditions(ctx: TickContext) -> dict[str, int]:
    counts = {"traditions_typed": 0, "traditions_effects": 0, "traditions_origins": 0}
    for tradition in await canon(ctx.session, [EntityType.TRADITION]):
        row = await ctx.session.get(TraditionProfileRow, tradition.id)
        if row is None:
            row = await traditions.profile_of(ctx, tradition, read_once(tradition, TRADITION_WORDS) or K.FESTIVAL)
            if row.kind is K.RITE_OF_PASSAGE and row.stage is None:
                row.stage = read_once(tradition, STAGE_WORDS)
            counts["traditions_typed"] += 1
        counts["traditions_effects"] += await traditions.seed_effects(ctx, row)
        if row.origin_incident_id is None and row.origin_entity_id is not None:
            row.origin_incident_id = await traditions.founding_incident(ctx, row.origin_entity_id)
            counts["traditions_origins"] += int(row.origin_incident_id is not None)
    return counts


async def backfill_typed_kinds(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, TYPED_KINDS_FIXUP):
        return 0
    result = {**await backfill_legends(ctx), **await backfill_traditions(ctx)}
    ctx.session.add(AppliedFixupRow(key=TYPED_KINDS_FIXUP, result=result))
    await ctx.session.flush()
    return sum(result.values())

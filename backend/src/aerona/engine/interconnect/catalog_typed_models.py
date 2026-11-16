from aerona.db.tables.anatomy import CreatureAttackRow
from aerona.db.tables.dimension_aspects import DimensionAspectRow
from aerona.db.tables.faith import AfterlifeStratumRow
from aerona.db.tables.horror import HorrorEventRow
from aerona.db.tables.lore import LegendaryQuestRow
from aerona.db.tables.storyteller import StorytellerRow
from aerona.db.tables.warfare import HeroQuestRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

S = Subsystem
E = EdgeKind
TYPED = "section-typed-models"

TYPED_MODEL_MECHANICS: tuple[Mechanic, ...] = (
    Mechanic(
        key="horror_model",
        spec_item="S47.6",
        title="Horrors typed by what they touch, what they do, how far they reach, how they are perceived and where they come from",
        subsystem=S.COSMOS,
        phases=("horror",),
        surface=Surface(drawer=TYPED),
        backfill="none: horrors are typed from their first occurrence; the seven old scenes are presets of the model",
        templates=("horror.",),
        tables=(HorrorEventRow.__tablename__,),
        exposure=Exposure.NONE,
        tools=(),
        targets=("world", "mortal", "people", "settlement", "region"),
        couplings=(
            Coupling(S.MIND, "those who perceive a horror lose sanity while it lingers", E.FLOW, "cosmic_horror.horror_sanity_cost"),
            Coupling(S.LANGUAGE, "a horror that takes from language removes words", E.FLOW, "cosmic_horror.language_loss_pct"),
            Coupling(S.COSMOS, "a horror on light moves its world's star", E.MODIFIER, "cosmic_horror.light_loss"),
        ),
    ),
    Mechanic(
        key="quest_model",
        spec_item="S47.6",
        title="Quests typed by aim, what they seek, what stands in the way, their reward and their scale, for heroes and for the cosmos alike",
        subsystem=S.SOCIAL,
        phases=("heroes", "beyond"),
        surface=Surface(drawer=TYPED),
        backfill="none: old hero and legendary quests are mapped to aims and targets by the migration",
        templates=("heroes.quest_", "beyond.quest_"),
        tables=(HeroQuestRow.__tablename__, LegendaryQuestRow.__tablename__),
        exposure=Exposure.NONE,
        tools=(),
        targets=("mortal", "star", "route", "outer_being"),
        couplings=(
            Coupling(S.WAR, "an obstacle makes a hero's quest harder", E.MODIFIER, "heroes.quest_success_min_pct"),
            Coupling(S.GODS, "a legendary quest's reward sets what the gods and the Creator gain", E.FLOW, "beyond.expedition_renown"),
        ),
    ),
    Mechanic(
        key="creature_attacks",
        spec_item="S47.6",
        title="Creature attacks typed by delivery, effect, range and recharge, and tissues typed by hardness, flexibility, heat resistance and conductivity",
        subsystem=S.ECOLOGY,
        phases=("beast_cycles", "monster_raids"),
        surface=Surface(drawer=TYPED),
        backfill="beast_cycles: every kind and beast is given attacks from its traits; old breaths and gazes become attack rows by the migration",
        templates=("monsters.raid",),
        tables=(CreatureAttackRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("raise_beast",),
        targets=("species", "beast"),
        couplings=(
            Coupling(S.WAR, "each attack adds to the harm of a raid", E.MODIFIER, "creature_anatomy.attack_harm_pct"),
            Coupling(S.BODY, "tissue properties change the harm of each kind of hit", E.MODIFIER, "creature_anatomy.skin_damage_pct"),
        ),
    ),
    Mechanic(
        key="stratum_axes",
        spec_item="S47.6",
        title=(
            "Realms of the dead typed by what they give, how long souls stay, who they take, what souls do there, their ruler and whether the living reach them"
        ),
        subsystem=S.FAITH,
        phases=("soul_cycles",),
        surface=Surface(drawer="section-afterlife"),
        backfill="none: old strata take their axes from their kind by the migration",
        templates=("afterlife.",),
        tables=(AfterlifeStratumRow.__tablename__,),
        exposure=Exposure.NONE,
        tools=(),
        targets=("region", "son"),
        couplings=(
            Coupling(S.FAITH, "souls fade from a realm where souls fade", E.FLOW, "afterlife.stratum_fade"),
            Coupling(S.FAITH, "souls leave a realm that holds them until rebirth", E.TRIGGER, "afterlife.rebirth_wait"),
            Coupling(S.SOCIAL, "a guardian reaches the living only from a realm the living can reach", E.MODIFIER, "spirits.house_luck"),
        ),
    ),
    Mechanic(
        key="storyteller_palette",
        spec_item="S47.6",
        title="Every subsystem registers its disruptions and recoveries; the storyteller weighs only those whose causes hold in each world",
        subsystem=S.CORE,
        phases=("storyteller",),
        surface=Surface(drawer="section-storyteller"),
        backfill="storyteller: the palette is weighed on the first epoch",
        templates=(),
        tables=(StorytellerRow.__tablename__,),
        exposure=Exposure.NONE,
        tools=(),
        targets=("world",),
        couplings=(
            Coupling(S.CORE, "subsystems that have not acted lately weigh more", E.MODIFIER, "storyteller.palette_rest_pct"),
            Coupling(S.CORE, "a quiet world leans toward disruptions and a heated one toward recoveries", E.MODIFIER, "storyteller.palette_lean_pct"),
        ),
    ),
    Mechanic(
        key="dimension_aspects",
        spec_item="S47.6",
        title="Dimensions described by aspects of form and matter, each pulling the dimension's values its own way every epoch",
        subsystem=S.COSMOS,
        phases=("scale_ladder", "dimension_cycles"),
        surface=Surface(drawer=TYPED),
        backfill="scale_ladder: every dimension is given aspects from its kind once; old elements become aspects by the migration",
        templates=(),
        tables=(DimensionAspectRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("create_dimension",),
        targets=("dimension",),
        couplings=(
            Coupling(S.COSMOS, "each aspect pulls a dimension's veil, stability, magic, hostility, sanity drain or leak", E.MODIFIER, "dimensions.aspect_step"),
            Coupling(S.COSMOS, "aspects of time or cold move a dimension's time", E.MODIFIER, "dimensions.aspect_time_pct"),
        ),
    ),
)

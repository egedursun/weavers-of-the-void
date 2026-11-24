from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

M = RuleGroup.DEATH_AND_RESURRECTION
A = RuleGroup.HEROES_AND_MORTALS
MIND = RuleGroup.MIND


@dataclass(frozen=True)
class DeathReadingRules:
    martial_glory_pct: int = rule(50, 0, 100, M, "How far a people's love of war turns a death in a fight toward glory (%)")
    honour_shame_pct: int = rule(50, 0, 100, M, "How far a people's sense of honour turns a judged or self-sought death toward shame (%)")
    piety_offering_pct: int = rule(50, 0, 100, M, "How far a people's piety turns a death offered to a god toward glory (%)")
    death_rest_pct: int = rule(30, 0, 100, M, "How far a people's regard for death honours a quiet death (%)")
    dread_curse_pct: int = rule(50, 0, 100, M, "How far a people's dread of the uncanny turns a death by curse or power toward a curse (%)")
    glorious_at: int = rule(60, 0, 100, M, "Reading above which a people holds a death glorious")
    honourable_at: int = rule(25, 0, 100, M, "Reading above which a people holds a death honourable")
    shameful_at: int = rule(25, 0, 100, M, "Reading below the negative of which a people holds a death shameful")
    cursed_at: int = rule(60, 0, 100, M, "Reading below the negative of which a people holds a death cursed")
    glorious_renown: int = rule(5, 0, 100, M, "Renown a mortal's name keeps after a death their people hold glorious")
    lament_pct: int = rule(150, 0, 500, M, "How much more kin lament a death their people hold glorious or cursed (%)")
    pity_mercy: int = rule(30, -100, 100, M, "Mercy a culture must hold before a plain death that no one chose is read with pity")


@dataclass(frozen=True)
class FuneralRules(Spanned):
    mummification_cost: int = rule(30, 0, 500, M, "Treasury a people spends on preserving each of its dead")
    secondary_rite_years: int = span(3, 0, 50, M, "Years between laying the dead to rest and gathering the bones in a second rite")
    second_rite_cohesion: int = rule(2, 0, 50, M, "Cohesion a people gains from each gathering of its dead in a second rite")
    preserved_draw_pct: int = rule(50, 0, 300, M, "How much more a preserved body draws grave robbers (%)")


@dataclass(frozen=True)
class PackageRules:
    fortune_roll_pct: int = rule(15, 0, 100, A, "How far a fortune shifts every chance rolled for its holder, at full strength (%)")
    fortune_line_pct: int = rule(50, 0, 100, A, "Chance a line's fortune passes to each child (%)")
    fortune_strength: int = rule(60, 0, 100, A, "Strength a fortune is laid with when no other strength is set")
    transform_recur_pct: int = rule(100, 0, 100, A, "Chance a changed body changes again when its sign comes (%)")
    charm_strength: int = rule(60, 0, 100, A, "Strength a charm is laid with")
    charm_fade: int = rule(5, 0, 50, A, "Strength a charm loses each epoch it is not renewed")
    charm_renew_cost: int = rule(10, 0, 500, A, "Treasury the charmer pays each epoch to keep a fading charm at full strength")
    charm_pull: int = rule(10, 0, 100, A, "Warmth toward its target a charm stirs in the charmed each epoch, at full strength")
    unkept_mind_pct: int = rule(20, 0, 100, A, "Intellect and charisma a changed body loses while it does not keep its own mind")
    ageing_rate_pct: int = rule(200, 0, 1000, A, "Rate at which an affliction of ageing moves its holder through its years against the usual (%)")
    epochs_years: int = rule(50, 1, 200, A, "Years of life an affliction of ageing weighs against the usual pace when it takes hold")
    forget_share_pct: int = rule(50, 0, 100, A, "Share of its memories an affliction of forgetting takes from its holder (%)")
    sleep_care_cost: int = rule(3, 0, 50, A, "Wealth a household spends each epoch tending one of its own held in a sleep")
    marked_read_pct: int = rule(70, 0, 100, A, "Chance one who knows the sign reads a marked affliction on its holder (%)")
    site_cure_pct: int = rule(40, 0, 100, A, "Chance a holy place cures an affliction that a place can lift (%)")


@dataclass(frozen=True)
class EmotionRules:
    joy_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of joy that fades each epoch (%)")
    contentment_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of contentment that fades each epoch (%)")
    pride_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of pride that fades each epoch (%)")
    love_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of love that fades each epoch (%)")
    gratitude_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of gratitude that fades each epoch (%)")
    relief_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of relief that fades each epoch (%)")
    hope_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of hope that fades each epoch (%)")
    awe_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of awe that fades each epoch (%)")
    amusement_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of amusement that fades each epoch (%)")
    fear_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of fear that fades each epoch (%)")
    anxiety_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of anxiety that fades each epoch (%)")
    anger_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of anger that fades each epoch (%)")
    rage_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of rage that fades each epoch (%)")
    grief_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of grief that fades each epoch (%)")
    sadness_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of sadness that fades each epoch (%)")
    shame_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of shame that fades each epoch (%)")
    guilt_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of guilt that fades each epoch (%)")
    envy_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of envy that fades each epoch (%)")
    jealousy_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of jealousy that fades each epoch (%)")
    disgust_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of disgust that fades each epoch (%)")
    loneliness_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of loneliness that fades each epoch (%)")
    boredom_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of boredom that fades each epoch (%)")
    despair_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of despair that fades each epoch (%)")
    longing_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of longing that fades each epoch (%)")
    surprise_decay: int = rule(50, 0, 50, MIND, "Share of a feeling of surprise that fades each epoch (%)")
    curiosity_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of curiosity that fades each epoch (%)")
    compassion_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of compassion that fades each epoch (%)")
    contempt_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of contempt that fades each epoch (%)")
    surprise_act_weight: int = rule(30, 0, 100, MIND, "How much a surprise sharpens the next feeling of the same epoch (%)")
    curiosity_act_weight: int = rule(30, 0, 100, MIND, "Chance a strong curiosity sends its holder to study, explore or seek out strangers (%)")
    compassion_act_weight: int = rule(30, 0, 100, MIND, "Chance a strong compassion moves its holder to give to the one who suffers (%)")
    contempt_act_weight: int = rule(30, 0, 100, MIND, "Chance a strong contempt moves its holder to insult or shut out the one held low (%)")
    felt_intensity: int = rule(40, 0, 100, MIND, "Strength a feeling of one of these four must reach before it moves its holder to act")
    surprise_share_pct: int = rule(60, 0, 100, MIND, "Strength of a surprise against the unexpected happening that stirred it (%)")
    compassion_gift: int = rule(3, 0, 100, MIND, "Wealth a moved holder gives to the one who suffers")
    contempt_insult: int = rule(10, 0, 100, MIND, "Ill will an insult from contempt leaves in the one held low")
    curiosity_xp: int = rule(20, 0, 500, MIND, "Practice a strong curiosity gives in study")
    trust_decay: int = rule(15, 0, 100, M, "Share of trust that fades each epoch (%)")
    anticipation_decay: int = rule(50, 0, 100, M, "Share of anticipation that fades each epoch (%)")
    admiration_decay: int = rule(30, 0, 100, M, "Share of admiration that fades each epoch (%)")
    embarrassment_decay: int = rule(70, 0, 100, M, "Share of embarrassment that fades each epoch (%)")


@dataclass(frozen=True)
class BreakRules(Spanned):
    withdrawal_years: int = span(5, 0, 100, MIND, "Years one who withdraws stops acting, leaving office and duties")
    withdrawal_care_cut: int = rule(30, 0, 100, MIND, "How much care from a healer shortens a withdrawal (%)")
    withdrawal_ease: int = rule(10, 0, 100, MIND, "Stress a withdrawn mortal sheds each epoch of rest")


P = RuleGroup.POLITY
CIV = RuleGroup.CIVILIZATION
WAR = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class MandatesRules:
    ration_death_cut_pct: int = rule(30, 0, 100, P, "How far a ration mandate cuts the deaths of hunger in its town (%)")
    corvee_grievance: int = rule(10, 0, 100, P, "Unrest a town gains each epoch its people are called out to forced labour")
    corvee_progress_pct: int = rule(15, 0, 100, P, "Share of a work's cost that called-out labour raises each epoch (%)")
    ration_grievance_pct: int = rule(100, 0, 300, P, "How much of the unrest of rationing a town feels, scaled by how corrupt its realm is (%)")
    quarantine_health: int = rule(8, 0, 100, P, "Sanitation a quarantine adds to a town each epoch while it holds")
    quarantine_trade_cost: int = rule(3, 0, 100, P, "Prosperity a town loses each epoch its quarantine closes its gates and ports")
    conscript_share_pct: int = rule(20, 0, 100, P, "Share of a town's people a levy of soldiers calls, in tenths (%)")


@dataclass(frozen=True)
class CrisisRules(Spanned):
    cede_region_weight: int = rule(100, 0, 100, WAR, "How readily a realm turns a quarrel into a demand that a land be ceded (%)")
    release_vassal_weight: int = rule(100, 0, 100, WAR, "How readily a realm turns a quarrel into a demand that a vassal be released (%)")
    convert_weight: int = rule(100, 0, 100, WAR, "How readily a realm turns a quarrel into a demand of conversion (%)")
    pay_weight: int = rule(100, 0, 100, WAR, "How readily a realm turns a quarrel into a demand of payment (%)")
    hand_over_weight: int = rule(80, 0, 100, WAR, "How readily a realm turns a quarrel into a demand that a person be handed over (%)")
    disarm_weight: int = rule(60, 0, 100, WAR, "How readily a realm turns a quarrel into a demand that forces be cut (%)")
    open_trade_weight: int = rule(80, 0, 100, WAR, "How readily a realm turns a quarrel into a demand that roads and ports be opened (%)")
    disarm_share_pct: int = rule(30, 0, 100, WAR, "Share of its armies a realm that gives way to a demand to disarm sends home (%)")
    hand_over_shame: int = rule(10, 0, 100, WAR, "Legitimacy a realm loses besides when it hands over one who sheltered with it")
    mediation_chance_pct: int = rule(15, 0, 100, WAR, "Chance each season a crisis with a third power trusted by both sides is settled by its mediation (%)")
    apology_weight: int = rule(30, 0, 100, WAR, "Weight of a demand for a public apology, paid in face (%)")
    release_captives_weight: int = rule(50, 0, 100, WAR, "Weight of a demand to release captives (%)")
    apology_shame: int = rule(8, 0, 100, WAR, "Legitimacy a realm loses when it gives way to a demand for a public apology")
    frozen_after_years: int = span(60, 1, 1000, WAR, "Years a crisis stays open before it freezes, neither side moving")


@dataclass(frozen=True)
class CourtRules:
    jester_calm: int = rule(5, 0, 50, P, "Unrest a jester's tolerated mockery takes from the seat of the realm each epoch")
    seer_sway_pct: int = rule(15, 0, 100, P, "How far a court seer's readings sway the realm's standing by the seer's renown (%)")
    jester_grudge: int = rule(20, 0, 100, P, "Ill will a jester bears a ruler who silences their mockery")
    taster_guard: int = rule(25, 0, 100, P, "Progress a court food taster takes from each plot to poison the ruler each epoch")
    interpreter_trust: int = rule(5, 0, 100, P, "Trust a court interpreter wins each epoch from each realm of another tongue")


@dataclass(frozen=True)
class PatronageRules:
    broker_share_pct: int = rule(10, 0, 100, P, "Share of the favours passing through a broker that the broker keeps (%)")
    artist_renown: int = rule(5, 0, 50, P, "Renown an artist client's works and praise bring a patron each epoch")
    scholar_renown: int = rule(6, 0, 100, P, "Renown a patron gains each epoch from a scholar it keeps, at full strength of the tie")


@dataclass(frozen=True)
class MembershipRules:
    office_grievance: int = rule(10, 0, 100, P, "Unrest a membership barred from office adds where it lives")
    marriage_grievance: int = rule(10, 0, 100, P, "Unrest a membership barred from marrying freely adds where it lives")
    arms_grievance: int = rule(5, 0, 100, P, "Unrest a membership barred from bearing arms adds where it lives")
    courts_grievance: int = rule(10, 0, 100, P, "Unrest a membership barred from the courts adds where it lives")
    property_grievance: int = rule(15, 0, 100, P, "Unrest a membership barred from holding property adds where it lives")
    movement_grievance: int = rule(10, 0, 100, P, "Unrest a membership barred from moving and settling adds where it lives")
    vote_grievance: int = rule(10, 0, 100, P, "Unrest a membership barred from voting adds where it lives")
    worship_grievance: int = rule(15, 0, 100, P, "Unrest a membership barred from worshipping openly adds where it lives")
    assembly_grievance: int = rule(10, 0, 100, P, "Grievance of members denied the right to gather")
    education_grievance: int = rule(8, 0, 100, P, "Grievance of members denied schooling")


@dataclass(frozen=True)
class LawAreaRules:
    succession_clash_weight: int = rule(60, 0, 100, P, "How hard a law of succession that clashes with a people's values stirs unrest (%)")
    property_clash_weight: int = rule(70, 0, 100, P, "How hard a law of property that clashes with a people's values stirs unrest (%)")
    fiscal_clash_weight: int = rule(80, 0, 100, P, "How hard a law of taxes and coin that clashes with a people's values stirs unrest (%)")
    penal_clash_weight: int = rule(70, 0, 100, P, "How hard a law of crime and punishment that clashes with a people's values stirs unrest (%)")
    military_clash_weight: int = rule(50, 0, 100, P, "How hard a law of arms and service that clashes with a people's values stirs unrest (%)")
    social_clash_weight: int = rule(80, 0, 100, P, "How hard a law of standing and custom that clashes with a people's values stirs unrest (%)")
    public_health_clash_weight: int = rule(40, 0, 100, P, "How hard a law of health that clashes with a people's values stirs unrest (%)")
    magic_clash_weight: int = rule(60, 0, 100, P, "How hard a law of powers that clashes with a people's values stirs unrest (%)")
    constitutional_clash_weight: int = rule(70, 0, 100, P, "How hard a law of the realm's frame that clashes with a people's values stirs unrest (%)")
    commerce_clash_weight: int = rule(60, 0, 100, P, "How hard a law of trade, contracts and guilds that clashes with a people's values stirs unrest (%)")
    faith_clash_weight: int = rule(90, 0, 100, P, "How hard a law of faith, tithes and rites that clashes with a people's values stirs unrest (%)")
    labour_clash_weight: int = rule(70, 0, 100, P, "How hard a law of work, wages and bondage that clashes with a people's values stirs unrest (%)")
    family_clash_weight: int = rule(35, 0, 100, P, "Weight of a clash over family law between a law and the people's values")
    environment_clash_weight: int = rule(30, 0, 100, P, "Weight of a clash over environment law between a law and the people's values")


@dataclass(frozen=True)
class CourtLevelRules:
    local_bias: int = rule(0, -100, 100, P, "How far a local court leans toward its own people over strangers")
    provincial_bias: int = rule(0, -100, 100, P, "How far a provincial court leans toward its own people over strangers")
    high_bias: int = rule(0, -100, 100, P, "How far a high court leans toward its own people over strangers")
    religious_bias: int = rule(20, -100, 100, P, "How far a court of faith leans toward the faithful over others")
    guild_bias: int = rule(25, -100, 100, P, "How far a guild court leans toward the guild's members over outsiders")
    military_bias: int = rule(30, -100, 100, P, "How far a military court leans toward soldiers over civilians")
    consular_bias: int = rule(40, -100, 100, P, "How far a court of foreigners leans toward its own nation's people")
    dispute_pct: int = rule(25, 0, 100, P, "Chance a case two courts both claim becomes a dispute of jurisdiction (%)")
    appellate_bias: int = rule(5, -50, 50, P, "Bias of a court of appeal toward the stronger party, small since it hears the case again")


@dataclass(frozen=True)
class CoopRules:
    mill_gain: int = rule(10, 0, 100, CIV, "How strongly a milling cooperative lifts its town's prosperity (tenths of the usual)")
    boats_gain: int = rule(10, 0, 100, CIV, "How strongly a boat cooperative lifts its town's prosperity (tenths of the usual)")
    irrigation_gain: int = rule(10, 0, 100, CIV, "How strongly an irrigation cooperative lifts its town's prosperity (tenths of the usual)")
    insurance_gain: int = rule(10, 0, 100, CIV, "How much an insurance cooperative pays each member out of its pool (tenths of the usual)")
    burial_gain: int = rule(10, 0, 100, CIV, "How much a burial society pays each member out of its pool (tenths of the usual)")
    credit_gain: int = rule(10, 0, 100, CIV, "How much a credit cooperative lends each member out of its pool (tenths of the usual)")
    granary_gain: int = rule(10, 0, 100, CIV, "Grain a granary cooperative gives out from its stores for each member in a hungry epoch, in tenths")
    herding_gain: int = rule(10, 0, 100, CIV, "Beasts a herding cooperative's shared herders add for each member each epoch, in tenths")
    school_gain: int = rule(10, 0, 100, CIV, "Learning a cooperative school gives its members' young")
    housing_gain: int = rule(10, 0, 100, CIV, "Share of their dwelling costs a housing cooperative saves its members (%)")


ARC = RuleGroup.HEROES_AND_MORTALS
DIV = RuleGroup.THE_DIVINE


@dataclass(frozen=True)
class ArcanaRules:
    linked_strength_pct: int = rule(70, 0, 100, ARC, "Strength a rite cast through a link keeps of the link's own strength (%)")
    cosmos_cost_pct: int = rule(300, 100, 1000, ARC, "Price of a rite that reaches beyond its world, against the same rite cast at home (%)")
    world_rite_power: int = rule(9, 1, 10, ARC, "Power a rite needs to touch a whole world")
    line_reach: int = rule(8, 1, 50, ARC, "Most living descendants a rite cast on a line of descent reaches with its holder")
    site_fill: int = rule(1, 0, 100, ARC, "Charges an item bound to a site regains each epoch at a found magic site")
    vis_fill: int = rule(1, 0, 100, ARC, "Charges an item bound to vis regains each epoch its holder pays the vis")
    moon_fill: int = rule(1, 0, 100, ARC, "Charges an item bound to the moon regains each epoch its world's first moon is full")
    none_fill: int = rule(0, 0, 100, ARC, "Charges an item that never refills regains each epoch")
    sky_event_fill: int = rule(2, 0, 100, ARC, "Charges an item bound to the sky regains in an epoch that brings an eclipse, alignment or comet to its world")
    bodily_offering_fill: int = rule(2, 0, 100, ARC, "Charges an item fed of a body regains each epoch its holder gives of a body")
    bodily_offering_harm: int = rule(5, 0, 100, ARC, "Hit points a holder gives of its body to fill an item fed so")
    sustained_struck_pct: int = rule(50, 0, 100, ARC, "Chance a fresh wound on the caster breaks a rite it sustains (%)")
    create_cost: int = rule(3, 0, 100, ARC, "Steps of difficulty a rite that brings a thing into being adds to its working")
    perceive_cost: int = rule(1, 0, 100, ARC, "Steps of difficulty a rite that perceives adds to its working")
    transform_cost: int = rule(3, 0, 100, ARC, "Steps of difficulty a rite that changes a thing adds to its working")
    destroy_cost: int = rule(2, 0, 100, ARC, "Steps of difficulty a rite that destroys adds to its working")
    control_cost: int = rule(3, 0, 100, ARC, "Steps of difficulty a rite that controls adds to its working")
    bind_cost: int = rule(4, 0, 100, ARC, "Steps of difficulty a rite that binds adds to its working")
    summon_cost: int = rule(4, 0, 100, ARC, "Steps of difficulty a rite that summons adds to its working")
    ward_cost: int = rule(2, 0, 100, ARC, "Steps of difficulty a rite that wards adds to its working")
    drain_cost: int = rule(3, 0, 100, ARC, "Steps of difficulty a rite that drains adds to its working")
    mimic_cost: int = rule(4, 0, 100, ARC, "Steps of difficulty a rite that copies a working adds to its working")
    heal_cost: int = rule(3, 0, 100, ARC, "Steps of difficulty a rite that heals injuries and conditions adds to its working")
    move_cost: int = rule(3, 0, 100, ARC, "Steps of difficulty a rite that moves beings and goods between places adds to its working")
    speak_cost: int = rule(2, 0, 100, ARC, "Steps of difficulty a rite that sends words across distance adds to its working")
    communal_power_per_worker: int = rule(10, 0, 50, ARC, "Power a rite that needs several workers gains for each worker beyond the first (%)")
    rest_fill: int = rule(1, 0, 100, ARC, "Charges an item that refills by rest regains in each epoch its holder works no rite")
    worship_fill: int = rule(1, 0, 100, ARC, "Charges an item that refills by worship regains each epoch for each hundred followers who pray to its holder")
    dimension_cost_pct: int = rule(500, 100, 2000, ARC, "Price of a rite that reaches across dimensions, against the same rite cast at home (%)")
    member_cost_per_100: int = rule(1, 0, 100, ARC, "Steps of difficulty a rite aimed at a whole species or people adds for each hundred members it reaches")


@dataclass(frozen=True)
class LinkRules:
    hair_strength: int = rule(50, 0, 100, ARC, "Strength of a link made with a target's hair")
    blood_strength: int = rule(65, 0, 100, ARC, "Strength of a link made with a target's blood")
    name_strength: int = rule(90, 0, 100, ARC, "Strength of a link made with a target's name")
    portrait_strength: int = rule(40, 0, 100, ARC, "Strength of a link made with a likeness of the target")
    fragment_strength: int = rule(55, 0, 100, ARC, "Strength of a link made with a thing the target once held")
    true_name_strength: int = rule(100, 0, 100, ARC, "Strength of a link made with a target's true name")
    possession_strength: int = rule(30, 0, 100, ARC, "Strength of a link made with a thing the target wears or keeps")
    true_name_command_pct: int = rule(150, 100, 400, ARC, "Strength a rite that commands or binds draws from a true name it is cast through (%)")
    footprint_strength: int = rule(35, 0, 100, ARC, "Strength of a link made with a target's footprint")
    voice_strength: int = rule(60, 0, 100, ARC, "Strength of a link made with a target's voice")
    birth_record_strength: int = rule(80, 0, 100, ARC, "Strength of a link made with the record of a target's birth")
    guarded_tokens_cut: int = rule(
        50,
        0,
        100,
        ARC,
        "Share of the strength of a link through a voice, a footprint or a birth record lost where the target's people guard them by custom (%)",
    )


@dataclass(frozen=True)
class InstructionRules:
    guard_literalness: int = rule(70, 0, 100, MIND, "How literally a made thing reads an order to guard")
    serve_literalness: int = rule(60, 0, 100, MIND, "How literally a made thing reads an order to serve")
    obey_holder_literalness: int = rule(80, 0, 100, MIND, "How literally a made thing reads an order to obey whoever holds it")
    build_literalness: int = rule(75, 0, 100, MIND, "How literally a made thing reads an order to build")
    gather_literalness: int = rule(75, 0, 100, MIND, "How literally a made thing reads an order to gather")
    protect_literalness: int = rule(65, 0, 100, MIND, "How literally a made thing reads an order to protect")
    destroy_literalness: int = rule(85, 0, 100, MIND, "How literally a made thing reads an order to destroy")
    report_literalness: int = rule(70, 0, 100, MIND, "How literally a made thing reads an order to report")
    maintain_literalness: int = rule(75, 0, 100, MIND, "How literally a made thing reads an order to maintain")
    replicate_literalness: int = rule(90, 0, 100, MIND, "How literally a made thing reads an order to make more of itself")
    hold_still_literalness: int = rule(95, 0, 100, MIND, "How literally a made thing reads an order to hold still")
    follow_literalness: int = rule(70, 0, 100, MIND, "How literally a made thing reads an order to follow")
    forbid_literalness: int = rule(85, 0, 100, MIND, "How literally a made thing reads an order that forbids")
    carry_literalness: int = rule(80, 0, 100, MIND, "How literally a made thing reads an order to carry")
    tend_literalness: int = rule(60, 0, 100, MIND, "How literally a made thing reads an order to tend")
    true_name_override: int = rule(1, 0, 1, MIND, "Whether one who knows a made thing's true name commands it over any other token (1 yes, 0 no)")
    carry_goods: int = rule(4, 0, 100, MIND, "Goods a made thing set to carry brings to the stores of its town each epoch")
    tend_food: int = rule(4, 0, 100, MIND, "Food a made thing set to tend keeps for its town each epoch")
    teach_literalness: int = rule(40, 0, 100, MIND, "How literally a made thing reads an order to teach")
    heal_literalness: int = rule(55, 0, 100, MIND, "How literally a made thing reads an order to heal")
    hunt_literalness: int = rule(70, 0, 100, MIND, "How literally a made thing reads an order to hunt")
    teach_literacy: int = rule(1, 0, 20, MIND, "Literacy a made thing ordered to teach gives the people of its town each epoch")
    heal_hp: int = rule(10, 0, 100, MIND, "Hit points a made thing ordered to heal gives back to the one it tends each epoch")
    hunt_food: int = rule(4, 0, 100, MIND, "Food a made thing ordered to hunt brings its town each epoch (supply index)")


@dataclass(frozen=True)
class WorshipRules:
    bargain_neglect_pct: int = rule(150, 0, 500, DIV, "How much faster a people that bargains with a god turns to neglect when its bargain goes unanswered (%)")
    bargain_offering_pct: int = rule(60, 0, 400, DIV, "Faith a bargaining people offers for its named return, against what an appeasing people offers (%)")
    bargain_trust: int = rule(5, 0, 100, DIV, "Love a bargaining people gains when its god answers the bargain")
    thanks_essence: int = rule(2, 0, 100, DIV, "Essence a prayer of thanks gives its god")
    mercy_essence: int = rule(1, 0, 100, DIV, "Essence a prayer for mercy gives its god")
    request_essence: int = rule(1, 0, 100, DIV, "Essence a prayer that asks a boon gives its god")
    praise_essence: int = rule(3, 0, 100, DIV, "Essence a prayer of praise gives its god")
    praise_renown: int = rule(1, 0, 100, DIV, "Awe a people gains of its god for each epoch its prayers praise it")
    lament_essence: int = rule(1, 0, 100, DIV, "Essence a prayer of lament gives its god")
    confession_essence: int = rule(2, 0, 100, DIV, "Essence a prayer of confession gives its god")
    lament_notice: int = rule(5, 0, 100, DIV, "Attention a god gives a world for each people whose prayers lament there")
    confession_guilt: int = rule(10, 0, 100, DIV, "Guilt a people sheds in an epoch its prayers confess")
    union_mystic_pct: int = rule(150, 0, 500, DIV, "How often mystics rise among a people that seeks union with its god, against other peoples (%)")
    kinship_ancestor: int = rule(5, 0, 100, DIV, "Ancestral rites a people that holds its god as kin keeps more each epoch")

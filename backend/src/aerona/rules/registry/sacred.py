from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

R = RuleGroup.RELIGION_AND_LANGUAGE
D = RuleGroup.THE_DIVINE


@dataclass(frozen=True)
class GeniusLociRules:
    bind_chance: int = rule(20, 0, 100, R, "Chance each epoch that a notable place, town or house without a spirit of its own gains one (%)")
    binds_per_epoch: int = rule(12, 0, 1000, R, "Place spirits that may arise across the cosmos in one epoch")
    city_population: int = rule(800, 0, 1000000, R, "People a town needs before a spirit of the town arises in it")
    hunger: int = rule(2, 0, 100, R, "Offerings a place spirit expects from its community each epoch")
    touchy_hunger_pct: int = rule(150, 0, 500, R, "What a touchy place spirit expects against an even-tempered one (%)")
    offering_piety: int = rule(30, 0, 100, R, "Piety a community needs before it brings offerings to its place spirits")
    offering_per_thousand: int = rule(5, 0, 100, R, "Offerings a pious community brings each epoch for every thousand of its people")
    offering_food: int = rule(2, 0, 1000, R, "Food a community gives up for each offering it brings")
    unpaid_epochs: int = rule(2, 1, 50, R, "Epochs a place spirit goes short before it takes offence")
    pollution_offence: int = rule(45, 0, 100, R, "Pollution of a land that offends the spirits of its places")
    clearing_offence: int = rule(30, 0, 100, R, "Forest cover below which the spirits of groves and forests take offence at the clearing")
    content_at: int = rule(60, 0, 100, R, "Contentment from which a place spirit grants favour")
    favour_gain: int = rule(8, 0, 100, R, "Favour a contented place spirit grows each epoch")
    contentment_step: int = rule(10, 0, 100, R, "Contentment a place spirit gains when paid in full, or loses when short or offended")
    favour_food: int = rule(6, 0, 1000, R, "Food a community gains each epoch for every ten points of its place spirit's favour")
    favour_prosperity: int = rule(1, 0, 100, R, "Prosperity a community gains each epoch for every twenty points of its place spirit's favour")
    misfortune_per_mille: int = rule(4, 0, 1000, R, "People in a thousand an offended place spirit's floods and illness take each epoch")
    misfortune_health: int = rule(5, 0, 100, R, "Health the mortals of a community lose each epoch to an offended place spirit")


@dataclass(frozen=True)
class CelestialBureaucracyRules:
    petition_chance: int = rule(30, 0, 100, R, "Chance each epoch that a community petitions the spirit office over it (%)")
    petitions_per_epoch: int = rule(40, 0, 10000, R, "Petitions that may be filed across the cosmos in one epoch")
    delay: int = rule(1, 0, 20, R, "Epochs an office takes to read a petition")
    bribe_per_epoch: int = rule(3, 1, 100, R, "Offerings slipped with a petition that save an epoch of waiting")
    bribe_share: int = rule(2, 0, 100, R, "Offerings a petitioner slips to the office for every ten points of its corruption")
    grant_base: int = rule(55, 0, 100, R, "Chance a petition is granted before merit, corruption and gifts (%)")
    merit_grant_pct: int = rule(20, 0, 100, R, "Most chance a petition gains from the merit of its office, reached at the merit of promotion (%)")
    corruption_deny_pct: int = rule(5, 0, 100, R, "Chance a petition loses for every ten points of the office's corruption (%)")
    bribe_grant: int = rule(2, 0, 100, R, "Chance a petition gains for every offering slipped with it (%)")
    appeal_chance: int = rule(50, 0, 100, R, "Chance a denied petitioner appeals to the office above (%)")
    neglect_epochs: int = rule(3, 1, 50, R, "Epochs past its due a petition may lie unread before the office is marked for neglect")
    merit_per_grant: int = rule(3, 0, 100, R, "Merit an office earns for each petition it settles")
    promote_merit: int = rule(30, 1, 1000, R, "Merit at which a spirit office is promoted one rank")
    demote_neglect: int = rule(3, 1, 100, R, "Neglected petitions after which a spirit office is demoted one rank, or dismissed from the lowest")
    corruption_rate: int = rule(6, 0, 100, R, "Corruption an office gains in an epoch its overseeing god does not watch its world")
    corruption_mend: int = rule(4, 0, 100, R, "Corruption an office sheds in an epoch its overseeing god watches its world")
    rogue_at: int = rule(70, 0, 100, R, "Corruption at which an office goes rogue, answering to no one")
    rogue_neglect: int = rule(5, 0, 100, R, "Neglect a rogue office breeds each epoch in its community toward the god meant to oversee it")
    grant_love: int = rule(2, 0, 100, R, "Love a granted petition earns the overseeing god in the petitioner's community")
    healing: int = rule(15, 0, 100, R, "Health a granted petition for healing restores")
    harvest_food: int = rule(40, 0, 100000, R, "Food a granted petition for the harvest brings its community")
    fertility: int = rule(10, 0, 100, R, "Fertility a granted petition for children grants")
    passage_safety: int = rule(5, 0, 100, R, "Stress a granted petition for safe passage lifts from the petitioner")
    prosperity: int = rule(3, 0, 100, R, "Prosperity a granted petition for prosperity grants its community")
    suit_merit: int = rule(10, 0, 1000, R, "Merit a spirit loses when a suit against it is granted")
    work_standing: int = rule(3, 0, 100, D, "Love a god earns in a community when it judges a petition or appoints a spirit there")


@dataclass(frozen=True)
class MysticismRules:
    vision_chance: int = rule(4, 0, 100, R, "Chance each epoch that a mortal open to the divine has a first direct experience (%)")
    mystics_per_epoch: int = rule(6, 0, 1000, R, "New mystics that may arise across the cosmos in one epoch")
    wisdom_floor: int = rule(60, 0, 100, R, "Wisdom a mortal needs before visions come to it")
    piety_floor: int = rule(65, 0, 100, R, "Piety a mortal holds dear before visions come to it")
    again_chance: int = rule(35, 0, 100, R, "Chance each epoch that a mystic has another vision (%)")
    answer_chance: int = rule(15, 0, 100, D, "Chance a mystic's patron god answers a vision itself, making it real contact (%)")
    awe: int = rule(40, 0, 100, R, "Awe a vision leaves in the mystic")
    followers_per_vision: int = rule(12, 0, 10000, R, "Followers a vision draws to a mystic of middling charisma")
    visionary_at: int = rule(3, 1, 100, R, "Visions after which a seeker is called a visionary")
    orthodoxy_persecutes: int = rule(60, 0, 100, R, "Orthodoxy of a church from which it persecutes mystics outside its clergy")
    persecution_step: int = rule(15, 0, 100, R, "Persecution or reverence a mystic gains each epoch from the church's orthodoxy")
    persecuted_at: int = rule(50, 0, 100, R, "Persecution at which a mystic is persecuted")
    revered_at: int = rule(50, 0, 100, R, "Reverence at which a mystic is revered")
    persecution_stress: int = rule(10, 0, 200, R, "Stress a persecuted mystic gains each epoch")
    found_at: int = rule(120, 1, 100000, R, "Followers at which a mystic founds an order or a heresy")
    lapse_epochs: int = rule(6, 1, 100, R, "Epochs without a vision after which a mystic lapses")


@dataclass(frozen=True)
class MillenarianRules:
    stir_chance: int = rule(10, 0, 100, R, "Chance each epoch that a town under an end-time sign stirs into a millenarian movement (%)")
    movements_per_epoch: int = rule(3, 0, 1000, R, "Millenarian movements that may begin across the cosmos in one epoch")
    psi_floor: int = rule(55, 0, 100, R, "Political stress of a realm from which immiseration alone stirs its towns")
    horizon: int = rule(3, 1, 50, R, "Epochs from a movement's start to the end it awaits")
    gather_pct: int = rule(8, 0, 100, R, "Share of a town that first joins a millenarian movement (%)")
    recruit_pct: int = rule(25, 0, 500, R, "Growth of a gathering movement each epoch (%)")
    vigil_epochs: int = rule(1, 0, 50, R, "Epochs before the awaited end at which the faithful stop working and give up their goods")
    give_up_pct: int = rule(15, 0, 100, R, "Wealth of its town a movement in vigil gives away each epoch (%)")
    idle_pct: int = rule(40, 0, 100, R, "Share of a movement that stops working in vigil (%)")
    idle_food: int = rule(10, 0, 1000, R, "Food a town loses each epoch for every ten points of its idle share")
    march_at: int = rule(75, 0, 100, R, "Conviction from which a movement marches against those it calls unclean")
    attack_per_mille: int = rule(6, 0, 1000, R, "People in a thousand a marching movement's attacks kill each epoch")
    redate_chance: int = rule(55, 0, 100, R, "Chance a movement whose date passes reads the prophecy anew and sets a new date (%)")
    redate_decay: int = rule(15, 0, 100, R, "Chance of a new date lost for every date already set (%)")
    sect_chance: int = rule(45, 0, 100, R, "Chance a disappointed movement that does not set a new date becomes a sect (%)")
    conviction_loss: int = rule(20, 0, 100, R, "Conviction a movement loses when its date passes")


@dataclass(frozen=True)
class TheodicyRules:
    suffering_at: int = rule(40, 0, 100, R, "Suffering of a faithful community that tests its doctrine")
    plague_suffering: int = rule(60, 0, 100, R, "Suffering a plague in a town brings")
    famine_suffering: int = rule(55, 0, 100, R, "Suffering hunger in a town brings")
    defeat_suffering: int = rule(45, 0, 100, R, "Suffering a lost battle brings the towns of the losing realm")
    disaster_suffering: int = rule(50, 0, 100, R, "Suffering a disaster in a land brings its towns")
    window: int = rule(2, 1, 50, R, "Epochs a crisis waits for the patron god to answer visibly before the faithful seek another way")
    argue_base: int = rule(25, 0, 100, R, "Chance theologians' arguments settle the crisis before their intellect (%)")
    doctrine_chance: int = rule(30, 0, 100, R, "Chance the crisis yields a new doctrine of suffering as a trial (%)")
    conversion_chance: int = rule(40, 0, 100, R, "Chance the faithful turn away from the silent god (%)")
    conversion_neglect: int = rule(20, 0, 100, D, "Neglect a crisis that ends in conversion leaves toward the silent god")
    drift_piety: int = rule(8, 0, 100, R, "Piety a crisis that ends in secular drift costs its community")
    answer_love: int = rule(10, 0, 100, D, "Love a god earns when it answers a crisis visibly")


@dataclass(frozen=True)
class SacramentRules:
    strength: int = rule(60, 0, 100, R, "Strength a church's sacrament has when first taught")
    coverage: int = rule(70, 0, 100, R, "Chance a priest is at hand for a sacrament in a town of the church at peace and in health (%)")
    hardship_pct: int = rule(50, 0, 100, R, "Chance of a priest lost in a town at war, in plague or far from the church (%)")
    initiation_age: int = rule(14, 1, 200, R, "Age at which a mortal is initiated")
    rites_per_epoch: int = rule(300, 0, 100000, R, "Sacraments that may be given across the cosmos in one epoch, births and weddings first")
    missed_anxiety: int = rule(35, 0, 100, R, "Unease a mortal feels for a sacrament it missed")
    routing_pct: int = rule(60, 0, 100, R, "Share of a routing sacrament's strength that keeps a soul from dying without rites (%)")
    unrest_relief: int = rule(25, 0, 100, R, "Unrest at death a sacrament against unrest lifts at full strength")
    missed_unrest: int = rule(15, 0, 100, R, "Unrest at death a missed sacrament against unrest adds")
    missed_rite_pct: int = rule(20, 0, 100, R, "Chance of dying without rites a missed routing sacrament adds (%)")


@dataclass(frozen=True)
class AfterlifeBeliefRules:
    shock_unrest: int = rule(25, 0, 100, R, "Unrest a soul gains when the afterlife it meets is not the one it was taught")
    testimony_doubt: int = rule(6, 0, 100, R, "Doubt each testimony of the dead brings the doctrine it contradicts")
    doubt_decay: int = rule(4, 0, 100, R, "Doubt a doctrine sheds each epoch")
    doubt_at: int = rule(50, 0, 100, R, "Doubt from which a doctrine's orthodoxy weakens")
    doubt_orthodoxy: int = rule(5, 0, 100, R, "Orthodoxy a doubted doctrine loses each epoch")
    align_cost: int = rule(40, 0, 100000, D, "Essence a god spends to make the afterlife match its church's teaching")


@dataclass(frozen=True)
class SecularisationRules:
    literacy_pct: int = rule(30, 0, 100, R, "Pull away from faith for every hundred points of a people's literacy (%)")
    science_per_theory: int = rule(4, 0, 100, R, "Pull away from faith for every sound theory held in a world")
    science_cap: int = rule(30, 0, 100, R, "Most pull away from faith sound theories can bring")
    prosperity_pct: int = rule(40, 0, 100, R, "Pull away from faith for prosperity above the middle (%)")
    city_scale: int = rule(4000, 1, 10000000, R, "People of a town for each point of pull away from faith, capped at twenty")
    silence_per_epoch: int = rule(3, 0, 100, R, "Pull away from faith for each epoch its gods stay silent")
    silence_cap: int = rule(30, 0, 100, R, "Most pull away from faith divine silence can bring")
    disaster_push: int = rule(20, 0, 100, R, "Push toward faith a disaster brings")
    miracle_push: int = rule(15, 0, 100, R, "Push toward faith each miracle brings")
    war_push: int = rule(10, 0, 100, R, "Push toward faith a war brings")
    dominion_pct: int = rule(30, 0, 100, R, "Push toward faith for every hundred points of a god's dominion over the land (%)")
    drift_pct: int = rule(10, 0, 100, R, "Share of the net pull that moves a community's piety each epoch (%)")
    godless_piety: int = rule(10, 0, 100, R, "Piety below which a community with no god of its own becomes godless")
    faithful_piety: int = rule(25, 0, 100, R, "Piety from which a godless community is godless no longer")


@dataclass(frozen=True)
class DivinationRules:
    found_chance: int = rule(8, 0, 100, R, "Chance each epoch that a people without a divination system takes one up (%)")
    systems_per_people: int = rule(2, 0, 20, R, "Divination systems a people may keep")
    consult_chance: int = rule(50, 0, 100, R, "Chance each epoch that a ruler with court diviners consults them (%)")
    valid_truth: int = rule(85, 0, 100, R, "Chance a valid system reads the true omen (%)")
    heed_superstition: int = rule(50, 0, 100, R, "Superstition a ruler holds dear before heeding the diviners")
    trust_step: int = rule(8, 0, 100, R, "Trust a system gains or loses when a heeded reading proves true or false")
    battle_edge_pct: int = rule(6, 0, 100, R, "Edge a heeded omen gives or takes from an army in battle (%)")
    legitimacy: int = rule(5, 0, 100, R, "Legitimacy a heeded coronation omen gives or takes")
    wedding_stress: int = rule(8, 0, 200, R, "Stress a heeded wedding omen lifts or lays on a ruler")
    harvest_food: int = rule(30, 0, 100000, R, "Food a realm's towns lose when sowing waits on an ill harvest omen")


@dataclass(frozen=True)
class PrescienceRules:
    foresee_chance: int = rule(30, 0, 100, R, "Chance each epoch that a seer foresees a likely future (%)")
    foresights_per_epoch: int = rule(20, 0, 10000, R, "Foresights that may be made across the cosmos in one epoch")
    horizon_years: int = rule(10, 1, 1000, R, "Years ahead a seer looks")
    god_sight: int = rule(25, 0, 100, D, "Certainty a god with the seer's power adds to what it foresees")
    rival_cloud: int = rule(15, 0, 100, R, "Certainty lost for every rival seer in the same world")
    cloud_floor: int = rule(20, 0, 100, R, "Certainty below which a foresight is clouded")
    likely_at: int = rule(45, 0, 100, R, "Chance from which the forecast counts a future as likely")
    renown_step: int = rule(4, 0, 100, R, "Renown a seer gains when a foresight comes true or loses when it fails")
    proclaim_at: int = rule(70, 0, 100, R, "Certainty from which a mortal seer proclaims a foresight as prophecy")


@dataclass(frozen=True)
class PsychohistoryRules:
    archive_min: int = rule(5, 0, 10000, R, "Works an order's archive must hold before it can model a realm")
    build_chance: int = rule(20, 0, 100, R, "Chance each epoch that a learned order able to model its realm does so (%)")
    accuracy_per_work: int = rule(3, 0, 100, R, "Accuracy each archived work adds to a forecast model")
    accuracy_cap: int = rule(85, 0, 100, R, "Most accuracy a forecast model can reach")
    learn_step: int = rule(4, 0, 100, R, "Accuracy a model gains when its forecast lands near the realm's real stress")
    near_at: int = rule(10, 0, 100, R, "Stress error within which a forecast counts as near")
    plan_at: int = rule(55, 0, 100, R, "Accuracy from which an order steers its realm by a long plan")
    plan_steps: int = rule(5, 1, 100, R, "Steps of a long plan that steers a forecast")
    psi_shift: int = rule(15, 0, 100, R, "Political stress a fulfilled steering plan lifts from its realm at no disruption")
    mule_pct: int = rule(20, 0, 100, R, "Disruption each great intervention in a modelled realm brings")


@dataclass(frozen=True)
class EmotionFeedingRules:
    weight: int = rule(50, 0, 100, D, "Weight a god's feeding on an emotion has when first drawn from its domains")
    essence_max: int = rule(30, 0, 10000, D, "Most essence a god can draw from the feelings of its faithful in one epoch")
    half: int = rule(400, 1, 1000000, D, "Felt intensity at which a god draws half its most essence from feelings")

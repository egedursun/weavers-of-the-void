from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.faith import BindingKind, HoldingKind, JudgementDoctrine, RebirthPath, ReincarnationGate, SpiritAlignment, StratumContact

BINDING_KIND = total(
    BindingKind,
    {
        BindingKind.NONE: Defined(
            "None",
            checked_by=(
                "engine.constructs.making.bind_soul",
                "engine.faith.control.bind_spirit",
                "engine.lore.rites.pay_souls",
                "engine.lore.rites.wandering_near",
                "engine.sacred.foresight.restless_dead_among",
                "services.player.faith.bind_spirit",
            ),
            used_by=(
                "db.tables.faith.SpiritProfileRow",
                "engine.constructs.control.ensoul",
                "engine.faith.control.bind_spirit",
                "engine.faith.souls.release_host",
                "engine.lore.rites.backlash",
                "engine.sacred.rites.follow_namers",
            ),
        ),
        BindingKind.PLACE: Defined(
            "Place",
            checked_by=("engine.faith.souls.ancestral_site",),
            used_by=("engine.lore.rites.bind_wandering", "engine.sites.digs.raise_spirit", "services.player.faith.BindSpirit"),
        ),
        BindingKind.ITEM: Defined("Item", checked_by=("engine.lore.arms.ward_magic", "engine.lore.items.spirit_year"), used_by=()),
        BindingKind.STRUCTURE: Defined("Structure", checked_by=("engine.settlement.life.warded",), used_by=("engine.lore.rites.bind_wandering",)),
        BindingKind.BEAST: Defined("Beast", checked_by=(), used_by=("engine.constructs.control.ensoul", "engine.constructs.making.bind_soul")),
        BindingKind.PERSON: Defined(
            "Person",
            checked_by=("engine.faith.souls.possess",),
            used_by=("engine.faith.souls.take_host", "engine.lore.rites.do_raise", "engine.lore.rites.do_summon"),
        ),
        BindingKind.REALM: Defined("Realm", checked_by=(), used_by=("engine.faith.spirit_bonds.keep_realm", "engine.faith.spirit_bonds.wider_binding")),
        BindingKind.NETWORK: Defined("Network", checked_by=(), used_by=("engine.faith.spirit_bonds.keep_network", "engine.faith.spirit_bonds.wider_binding")),
        BindingKind.LINE: Defined("Line", checked_by=(), used_by=("engine.faith.spirit_bonds.keep_line", "engine.faith.spirit_bonds.wider_binding")),
        BindingKind.NAME: Defined("Name", checked_by=("engine.sacred.rites.follow_namers",), used_by=("engine.lore.rites.bind_wandering",)),
    },
)

HOLDING_KIND = total(
    HoldingKind,
    {
        HoldingKind.TEMPLE: Defined(
            "Temple", checked_by=("engine.divine.wounds.worship_wounds",), used_by=("engine.faith.works.spend", "engine.faith.works.survey_holdings")
        ),
        HoldingKind.LAND: Defined(
            "Land",
            checked_by=("api.routers.faith.doctrine", "api.routers.map.holy_marks", "engine.faith.works.land_holders"),
            used_by=("engine.faith.works.survey_holdings", "engine.faith.works.tithe_base", "services.player.faith.SetHolding"),
        ),
        HoldingKind.RELIC: Defined("Relic", checked_by=(), used_by=("engine.faith.backfill.relic_bones", "engine.faith.works.canonise")),
        HoldingKind.HOLY_PLACE: Defined(
            "Holy place", checked_by=("engine.faith.zealotry.holy_place",), used_by=("engine.dominion.sites.reveal", "engine.faith.works.survey_holdings")
        ),
        HoldingKind.MONASTERY: Defined(
            "Monastery", checked_by=("engine.couplings.registers.silent_cults", "engine.faith.zealotry.monastery_keeps"), used_by=("engine.faith.works.spend",)
        ),
        HoldingKind.NETWORK: Defined("Network", checked_by=("engine.faith.works.holding_income",), used_by=("engine.faith.works.wider_holdings",)),
        HoldingKind.SHARES: Defined("Shares", checked_by=("engine.faith.works.holding_income",), used_by=("engine.faith.works.wider_holdings",)),
        HoldingKind.LINES: Defined("Lines", checked_by=("engine.faith.works.holding_income",), used_by=("engine.faith.works.wider_holdings",)),
        HoldingKind.SCHOOL: Defined("School", checked_by=(), used_by=("catalog.life.faith.CHURCH_WORKS", "engine.faith.works.tend_works")),
        HoldingKind.HOSPITAL: Defined("Hospital", checked_by=(), used_by=("catalog.life.faith.CHURCH_WORKS", "engine.faith.works.tend_works")),
    },
)

JUDGEMENT_DOCTRINE = total(
    JudgementDoctrine,
    {
        JudgementDoctrine.DEEDS: Defined(
            "Deeds",
            checked_by=("engine.faith.judgement.score_of", "engine.faith.souls.fear_of_torment"),
            used_by=(
                "api.routers.faith.doctrine",
                "catalog.life.faith.REBIRTH_PATH_OF_JUDGEMENT_DOCTRINES",
                "catalog.tenets.DOMAIN_JUDGEMENT",
                "db.tables.faith.CultDoctrineRow",
                "engine.divine.foreign.old_god_doctrine",
                "engine.faith.doctrine.judgement_of",
                "engine.faith.judgement.judgement_for",
            ),
        ),
        JudgementDoctrine.FAITH: Defined(
            "Faith",
            checked_by=("engine.faith.judgement.score_of",),
            used_by=("catalog.life.faith.REBIRTH_PATH_OF_JUDGEMENT_DOCTRINES", "engine.faith.doctrine.judgement_of"),
        ),
        JudgementDoctrine.RITE: Defined("Rite", checked_by=("engine.faith.judgement.judge", "engine.faith.judgement.score_of"), used_by=()),
        JudgementDoctrine.FAVOUR: Defined("Favour", checked_by=("engine.faith.judgement.score_of",), used_by=("engine.faith.control.judge_soul",)),
        JudgementDoctrine.NONE: Defined(
            "None",
            checked_by=("agents.context.son_faith.church_line", "engine.sacred.rites.taught_model"),
            used_by=("catalog.tenets.DOMAIN_JUDGEMENT", "engine.faith.doctrine.judgement_of", "engine.faith.judgement.judgement_for"),
        ),
        JudgementDoctrine.REMEMBRANCE: Defined(
            "Remembrance", checked_by=("engine.faith.judgement.score_of", "engine.sacred.rites.taught_model"), used_by=("engine.faith.doctrine.judgement_of",)
        ),
    },
)

REBIRTH_PATH = total(
    RebirthPath,
    {
        RebirthPath.PEOPLE: Defined(
            "People",
            checked_by=("engine.faith.backfill.doctrine_fields",),
            used_by=(
                "api.routers.faith.doctrine",
                "db.tables.faith.CultDoctrineRow",
                "db.tables.faith.ReincarnationRow",
                "engine.faith.doctrine.rebirth_path_of",
                "engine.faith.souls.cradle",
                "services.integrity.w52_agent_g.rebirth_by_people",
            ),
        ),
        RebirthPath.HOUSE: Defined("House", checked_by=("engine.faith.souls.cradle",), used_by=("engine.faith.doctrine.rebirth_path_of",)),
        RebirthPath.MERIT: Defined("Merit", checked_by=("engine.faith.souls.cradle",), used_by=("engine.faith.doctrine.rebirth_path_of",)),
        RebirthPath.KIND: Defined(
            "Kind",
            checked_by=("engine.faith.souls.rebirth", "services.integrity.w52_agent_g.kindless_rebirths"),
            used_by=("engine.faith.doctrine.rebirth_path_of", "engine.faith.souls.reborn_as_kind"),
        ),
        RebirthPath.PLACE: Defined("Place", checked_by=("engine.faith.souls.cradle",), used_by=("engine.faith.doctrine.rebirth_path_of",)),
    },
)

REINCARNATION_GATE = total(
    ReincarnationGate,
    {
        ReincarnationGate.TENET: Defined("Tenet", checked_by=(), used_by=("engine.faith.souls.gates",)),
        ReincarnationGate.NATURAL_LAW: Defined("Natural law", checked_by=(), used_by=("engine.faith.souls.gates",)),
        ReincarnationGate.RITE: Defined("Rite", checked_by=(), used_by=("engine.faith.souls.gates",)),
        ReincarnationGate.GOD: Defined("God", checked_by=(), used_by=("engine.faith.control.reincarnate_soul", "tools.son.faith.open_rebirth_gate")),
    },
)

SPIRIT_ALIGNMENT = total(
    SpiritAlignment,
    {
        SpiritAlignment.GUARDIAN: Defined(
            "Guardian",
            checked_by=("engine.faith.souls.ancestral_site", "engine.faith.souls.guardians_of", "engine.faith.souls.house_luck", "engine.faith.souls.tend"),
            used_by=(
                "engine.faith.backfill.temper",
                "engine.faith.judgement.judge",
                "engine.faith.souls.tend",
                "engine.lifecycle.mortal_death._leave_spirit",
                "engine.lore.rites.bind_wandering",
                "engine.lore.rites.do_summon",
                "engine.mythic.servitors.make_servitor",
            ),
        ),
        SpiritAlignment.NEUTRAL: Defined(
            "Neutral",
            checked_by=(),
            used_by=(
                "db.tables.faith.SpiritProfileRow",
                "engine.faith.backfill.temper",
                "engine.faith.judgement.profile_for",
                "engine.lore.traditions.placate",
                "services.player.faith.RaiseSoul",
                "tools.son.world_works.CallUpSoulInput",
            ),
        ),
        SpiritAlignment.VENGEFUL: Defined(
            "Vengeful",
            checked_by=(
                "engine.faith.souls.restless",
                "engine.faith.spirit_bonds.sign_of",
                "engine.lore.arms.ward_magic",
                "engine.lore.items.spirit_year",
                "engine.lore.traditions.placate",
                "engine.settlement.life.warded",
            ),
            used_by=(
                "engine.faith.backfill.temper",
                "engine.faith.judgement.judge",
                "engine.faith.souls.tend",
                "engine.lifecycle.mortal_death._leave_spirit",
                "engine.lore.rites.backlash",
                "engine.lore.rites.do_raise",
                "engine.mythic.servitors.fall",
                "engine.sites.digs.raise_spirit",
            ),
        ),
    },
)

STRATUM_CONTACT = total(
    StratumContact,
    {
        StratumContact.OPEN: Defined(
            "The living can reach it", checked_by=("engine.faith.judgement.reaches_living",), used_by=("catalog.strata.STRATUM_AXES",)
        ),
        StratumContact.BY_RITE: Defined(
            "Only by rite",
            checked_by=("engine.faith.judgement.reaches_living",),
            used_by=("catalog.strata.STRATUM_AXES", "db.tables.faith.AfterlifeStratumRow"),
        ),
        StratumContact.CLOSED: Defined("Closed to the living", checked_by=(), used_by=("catalog.strata.STRATUM_AXES",)),
    },
)

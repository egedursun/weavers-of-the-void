from aerona.db.tables.genetics import AllelePoolRow, GenomeRow, HouseResemblanceRow
from aerona.db.tables.households import DwellingFurnishingRow, DwellingRow, HouseholdAggregateRow, HouseholdMemberRow, HouseholdRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

LINEAGE = "section-lineage"
HOME = "section-home"
S = Subsystem
E = EdgeKind

LINEAGE_MECHANICS: tuple[Mechanic, ...] = (
    Mechanic(
        key="genetics",
        spec_item="F26",
        title=(
            "Every mortal carries a genome of typed loci; children inherit one allele from each parent, the stronger shows, and kin unions raise harmful pairs"
        ),
        subsystem=S.BODY,
        phases=("genetics_survey", "couple_births", "bloodlines", "house_cycles"),
        surface=Surface(drawer=LINEAGE),
        backfill="genetics_survey: writes a genome for every living mortal and a pool for every people",
        templates=("genetics.resemblance",),
        fields=("genes", "potential", "divine_son_id", "inbreeding", "beauty", "recognisability", "likeness", "marks"),
        tables=(GenomeRow.__tablename__, AllelePoolRow.__tablename__, HouseResemblanceRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("shape_blood",),
        targets=("mortal", "people", "house"),
        couplings=(
            Coupling(S.DEMOGRAPHY, "fertile or barren blood moves the chance of children", E.MODIFIER, "genetics.fertility_pct"),
            Coupling(S.BODY, "long-lived, brief-lived and cursed blood lengthen or shorten a life", E.MODIFIER, "genetics.longevity_pct"),
            Coupling(S.BODY, "hardy or frail blood moves the chance of catching a sickness", E.MODIFIER, "genetics.disease_pct"),
            Coupling(S.MIND, "blood prone to madness breaks a mind sooner under strain", E.MODIFIER, "genetics.madness_pct"),
            Coupling(S.SOCIAL, "beauty, read by the people's tastes in looks, feeds presence", E.MODIFIER, "genetics.presence_beauty_pct"),
            Coupling(S.POLITY, "a house is known by the look most of its blood shares, and houses weigh kin matches by their ethics", E.TRIGGER),
            Coupling(S.CULTURE, "portraits keep the same face, drawn from the looks, scars and marks of afflictions", E.FLOW),
        ),
    ),
    Mechanic(
        key="magical_gift",
        spec_item="F26/RP8",
        title=(
            "Aptitude for each form of magic is carried in the blood; peoples read the gift by their ethics and law, "
            "persecution thins it, natural laws move it and mage orders test children"
        ),
        subsystem=S.MAGIC,
        phases=("bloodlines",),
        surface=Surface(drawer=LINEAGE),
        backfill="none: shares and stances are reckoned from the next epoch",
        templates=("genetics.order_recruits",),
        fields=("gift_stance", "gifted_share", "cohort_shares", "frequencies"),
        tables=(AllelePoolRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("people", "mortal", "faction"),
        couplings=(
            Coupling(S.LAW, "a ban on magic makes the gift persecuted, a licence makes it taxed", E.RULE_SWITCH),
            Coupling(S.SOCIAL, "the honoured gifted gain renown, the feared and persecuted bear stress", E.MODIFIER, "gift.fear_stress"),
            Coupling(S.ECONOMY, "the taxed gifted pay into the town's treasury", E.FLOW, "gift.tax_wealth"),
            Coupling(S.GODS, "natural laws of the gift raise or wither it in every bloodline", E.MODIFIER, "gift.law_shift_pct"),
        ),
    ),
    Mechanic(
        key="households",
        spec_item="F29",
        title=(
            "Every named mortal belongs to a household that pools its income, pays for food, upkeep, tithes and taxes, "
            "cares for its weak and decides whom to marry, apprentice or where to move"
        ),
        subsystem=S.HOUSEHOLD,
        phases=("household_survey", "households"),
        surface=Surface(drawer=HOME),
        backfill="household_survey: houses every living named mortal",
        templates=("households.marry", "households.apprentice", "households.migrate", "households.usury", "households.abandon"),
        fields=("wealth", "income", "expenses", "servants", "dependents", "burden", "debts", "role", "last_decision"),
        tables=(HouseholdRow.__tablename__, HouseholdMemberRow.__tablename__, HouseholdAggregateRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("tend_home",),
        targets=("mortal", "settlement", "people"),
        couplings=(
            Coupling(S.MIND, "a burdened household strains its head, spouse and carers", E.MODIFIER, "households.burden_stress"),
            Coupling(S.FAITH, "the faithful pay a tithe", E.FLOW, "households.tithe_pct"),
            Coupling(S.POLITY, "households pay tax, and a ruling household draws from the realm's treasury", E.FLOW, "households.ruler_draw"),
            Coupling(S.LAW, "destitute households may lend at usury, give up an infant or leave an elder, judged by their people's ethics", E.TRIGGER),
            Coupling(S.DEMOGRAPHY, "the wealth and home of the household raising a child lift its abilities", E.MODIFIER, "genetics.upbringing_pct"),
        ),
    ),
    Mechanic(
        key="dwellings",
        spec_item="F29",
        title=(
            "Each household lives in a dwelling of a kind, quality and rooms, furnished with its items; quality feeds comfort, "
            "beauty, status and rest, squalor breeds sickness and a noble home must be grand"
        ),
        subsystem=S.HOUSEHOLD,
        phases=("household_survey", "households", "mind_needs", "natural_disasters"),
        surface=Surface(drawer=HOME),
        backfill="household_survey: builds a dwelling for every new household",
        fields=("kind", "quality", "rooms", "district_id"),
        tables=(DwellingRow.__tablename__, DwellingFurnishingRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=("mortal", "settlement"),
        couplings=(
            Coupling(
                S.MIND, "home quality feeds the needs for comfort, beauty and status, and spare rooms give rest", E.MODIFIER, "households.comfort_home_pct"
            ),
            Coupling(S.BODY, "squalor raises the chance of catching a sickness", E.MODIFIER, "households.squalor_disease_pct"),
            Coupling(S.POLITY, "the home of a house's head raises or lowers its prestige", E.MODIFIER, "households.prestige_quality"),
            Coupling(S.MIND, "a home above or below its class's expectation brings pride or shame", E.TRIGGER, "households.proud_at"),
        ),
    ),
)

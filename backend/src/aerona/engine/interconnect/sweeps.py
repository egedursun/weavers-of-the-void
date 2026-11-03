from dataclasses import dataclass

from aerona.engine.interconnect.registry import Subsystem

S = Subsystem


@dataclass(frozen=True)
class SweepClass:
    code: str
    name: str
    subsystems: tuple[S, ...]
    words: tuple[str, ...] = ()


SWEEPS: dict[str, tuple[SweepClass, ...]] = {
    "S-E Biology": (
        SweepClass("tree", "tree of life: domains and kingdoms", (S.ECOLOGY,), ("species", "creature", "beast")),
        SweepClass("life-history", "life-history theory", (S.DEMOGRAPHY, S.ECOLOGY), ("birth", "aging", "growth")),
        SweepClass("symbiosis", "symbiosis types", (S.ECOLOGY,), ("tame", "hunt", "prey")),
        SweepClass("ethology", "ethology", (S.ECOLOGY, S.MIND), ("monster", "raid", "migration")),
        SweepClass("physiology", "physiology and the senses", (S.BODY,), ("body", "capacit", "condition")),
        SweepClass("biogeography", "biogeography", (S.ECOLOGY, S.ENVIRONMENT), ("region", "land", "terrain")),
    ),
    "S-F Technology (IPC)": (
        SweepClass("A", "human necessities", (S.ECONOMY, S.BODY), ("food", "harvest", "healing")),
        SweepClass("B", "performing operations and transporting", (S.ECONOMY, S.COSMOS), ("trade", "travel", "route")),
        SweepClass("C", "chemistry and metallurgy", (S.KNOWLEDGE, S.ECONOMY), ("knowledge", "resource", "metallurg")),
        SweepClass("D", "textiles and paper", (S.ECONOMY, S.CULTURE), ("craft", "work", "artwork")),
        SweepClass("E", "fixed constructions", (S.ECONOMY,), ("structure", "work", "wonder", "settlement")),
        SweepClass("F", "mechanical engineering, lighting, heating, weapons", (S.WAR, S.KNOWLEDGE), ("army", "weapon", "campaign")),
        SweepClass("G", "physics and instruments", (S.KNOWLEDGE, S.COSMOS), ("calendar", "sky", "star")),
        SweepClass("H", "electricity", (S.KNOWLEDGE,), ("knowledge",)),
    ),
    "S-G Economics (JEL)": tuple(
        SweepClass(code, name, subsystems, words)
        for code, name, subsystems, words in (
            ("A", "general economics", (S.ECONOMY,), ("economy",)),
            ("B", "history of economic thought", (S.KNOWLEDGE,), ("knowledge",)),
            ("C", "mathematical and quantitative methods", (S.CORE,), ("statistics",)),
            ("D", "microeconomics", (S.ECONOMY, S.MIND), ("need", "market", "barter")),
            ("E", "macroeconomics and money", (S.ECONOMY,), ("currency", "market", "debt")),
            ("F", "international economics", (S.ECONOMY,), ("trade", "tribute")),
            ("G", "financial economics", (S.ECONOMY,), ("debt", "lend")),
            ("H", "public economics", (S.POLITY, S.ECONOMY), ("tribute", "tax")),
            ("I", "health, education and welfare", (S.BODY, S.KNOWLEDGE), ("healing", "knowledge", "famine")),
            ("J", "labour and demographic economics", (S.DEMOGRAPHY,), ("population", "cohort", "career")),
            ("K", "law and economics", (S.LAW,), ("law",)),
            ("L", "industrial organisation", (S.ECONOMY,), ("resource", "production", "work")),
            ("M", "business administration", (S.ECONOMY,), ("market",)),
            ("N", "economic history", (S.CULTURE,), ("remembrance", "legend")),
            ("O", "development, innovation and growth", (S.KNOWLEDGE, S.ECONOMY), ("tier", "knowledge", "growth")),
            ("P", "economic systems", (S.ECONOMY, S.POLITY), ("society", "economy")),
            ("Q", "agricultural, natural resource and environmental economics", (S.ENVIRONMENT, S.ECONOMY), ("harvest", "land", "resource")),
            ("R", "urban, rural and regional economics", (S.ECONOMY, S.DEMOGRAPHY), ("settlement", "migration")),
            ("Y", "miscellaneous categories", (S.CORE,), ()),
            ("Z", "other special topics: cultural economics", (S.CULTURE,), ("tradition", "artwork")),
        )
    ),
    "S-H Narrative (Thompson and Propp)": tuple(
        SweepClass(code, name, (S.CULTURE, S.GODS), words)
        for code, name, words in (
            ("A", "mythological motifs", ("god", "myth", "pantheon")),
            ("B", "animals", ("species", "creature", "beast")),
            ("C", "tabu", ("taboo", "law")),
            ("D", "magic", ("magic", "curse", "ley")),
            ("E", "the dead", ("death", "spirit", "soul", "afterlife")),
            ("F", "marvels", ("wonder", "sky", "horror")),
            ("G", "ogres", ("monster",)),
            ("H", "tests", ("duel", "quest")),
            ("J", "the wise and the foolish", ("knowledge", "sage")),
            ("K", "deceptions", ("betray", "espionage", "sabotage")),
            ("L", "reversal of fortune", ("dark_age", "golden")),
            ("M", "ordaining the future", ("prophec", "fate", "thread")),
            ("N", "chance and fate", ("fate", "omen")),
            ("P", "society", ("society", "faction", "institution")),
            ("Q", "rewards and punishments", ("reward", "punish", "curse")),
            ("R", "captives and fugitives", ("captive", "prisoner", "refugee")),
            ("S", "unnatural cruelty", ("execution", "sacrifice")),
            ("T", "sex", ("marriage", "birth", "love")),
            ("U", "the nature of life", ("aging", "life")),
            ("V", "religion", ("religion", "cult", "faith")),
            ("W", "traits of character", ("trait", "mind")),
            ("X", "humour", ("legend", "tale")),
            ("Z", "miscellaneous groups of motifs", ("legend", "remembrance")),
        )
    ),
    "S-I Human universals (Brown)": tuple(
        SweepClass(code, name, subsystems, words)
        for code, name, subsystems, words in (
            ("language", "language, naming and metaphor", (S.LANGUAGE,), ("language", "dialect")),
            ("kinship", "kinship, marriage and family", (S.DEMOGRAPHY, S.SOCIAL), ("birth", "marriage", "lineage")),
            ("status", "status, rank and leadership", (S.POLITY, S.SOCIAL), ("ruler", "faction", "career")),
            ("law", "rules, sanctions and property", (S.LAW,), ("law", "prisoner", "theft")),
            ("conflict", "conflict, violence and its mediation", (S.WAR,), ("war", "feud", "diplomacy")),
            ("religion", "religion, magic and ritual", (S.FAITH, S.MAGIC), ("religion", "cult", "magic")),
            ("death", "mourning and death practices", (S.CULTURE,), ("remembrance", "death", "spirit")),
            ("art", "art, music and adornment", (S.CULTURE,), ("artwork", "work", "tradition")),
            ("exchange", "reciprocity, gifts and trade", (S.ECONOMY,), ("trade", "barter", "famine_aid")),
            ("identity", "self-image and in-group identity", (S.MIND, S.CULTURE), ("value", "culture")),
            ("emotion", "emotions and their display", (S.MIND,), ("mind", "memory", "need")),
            ("tools", "tools, fire and shelter", (S.ECONOMY, S.KNOWLEDGE), ("craft", "structure", "knowledge")),
            ("worldview", "worldview, time and cosmology", (S.COSMOS, S.KNOWLEDGE), ("calendar", "sky", "star")),
        )
    ),
    "S-J Warfare": tuple(
        SweepClass(code, name, (S.WAR, *extra), words)
        for code, name, extra, words in (
            ("command", "command and control", (), ("commander", "campaign")),
            ("intelligence", "intelligence", (S.INTRIGUE,), ("espionage", "spy")),
            ("fires", "fires", (), ("battle", "casualt")),
            ("manoeuvre", "movement and manoeuvre", (S.ENVIRONMENT,), ("campaign", "passab", "travel")),
            ("protection", "protection", (S.BODY,), ("armour", "siege", "wall")),
            ("sustainment", "sustainment", (S.ECONOMY,), ("supply", "levy", "upkeep")),
            ("engineering", "engineering", (S.ECONOMY,), ("siege", "structure")),
            ("medical", "medical", (S.BODY,), ("healing", "injur")),
            ("civil", "civil affairs", (S.POLITY,), ("tribute", "conquest")),
            ("culture", "military culture", (S.CULTURE,), ("duel", "hero", "glory")),
        )
    ),
}

from typing import Any

from aerona.prompts.ids import PromptId

IMAGE = "A white salt cave lit by blue lamps, wide lens."
POWER = {"name": "Salt Memory", "description": "Remembers every tide.", "effect": "essence_spring", "param": ""}
EXISTENCE = {"nature": "brine", "state": "concrete", "manifestation": "a wet shadow", "true_name": "Oz"}
NAMING_RULE = {"vowels": "aeo", "consonants": "kshrv", "syllable_patterns": ["CV"], "sample_names": ["Vesh", "Karo"]}
SON = {
    "name": "Ozzeh",
    "title": "the Weeper",
    "domain_1": "salt",
    "domain_2": "sea",
    "appearance": "Tall.",
    "temperament": "Cold.",
    "obsession": "The moon.",
    "fear": "Fire.",
    "speech_style": "Short.",
    "secret": "A drowned brother.",
    "strengths": ["strength", "will"],
    "weakness": "charisma",
    "passions": {"loyalty": 40, "ambition": 70, "wrath": 30, "mercy": 10},
    "powers": [POWER, {**POWER, "effect": "tireless"}, {**POWER, "effect": "cheap_creation", "param": "place"}],
    "existence": EXISTENCE,
    "image_prompt": IMAGE,
}
GOD = {"title": "the Salt", "appearance": "A white tide.", "temperament": "Distant.", "image_prompt": IMAGE}
RECORD = {"name": "Kael", "subtype": "tide folk", "description": "A people of the shore.", "image_prompt": IMAGE}
NAMING_ITEM = {"id": 13, "name": "Battle of Salt", "subtype": "battle", "description": "A long fight.", "image_prompt": IMAGE, "motifs": ["salt"]}
VERDICT = {"id": 12, "decision": "fix", "rationale": "It fits.", "fixed_description": "A cave.", "motifs": ["salt", "bone_bell"]}
SECTION = {"world_id": 1, "narrative": "Things happened.", "summary": "Kael raised a wall and lost their elders to the tide."}
SAYING = {"kind": "proverb", "text": "Salt remembers."}
NODE = {"name": "Vel", "subtype": "sea", "description": "Deep.", "danger": 10, "fertility": 50, "magic": 20, "image_prompt": IMAGE}

PAYLOADS: dict[PromptId, dict[str, Any]] = {
    PromptId.LOCALISE_USER: {"lines": [{"id": 4, "text": "Nehir Velar'in uzerine yukseldi."}]},
    PromptId.GENESIS_USER: {
        "world_name": "Aerona",
        "cosmology": "A salt lake.",
        "naming": NAMING_RULE,
        "tone": "Grim.",
        "god": GOD,
        "regions": [NODE],
        "first_celestial": {"name": "Ka", "subtype": "star", "description": "Bright.", "domain": "star", "image_prompt": IMAGE},
        "cosmic_resource": {
            "name": "Veilsalt",
            "description": "A pale crystal.",
            "rule": "Dissolved in a gate.",
            "side_effect": "Memory loss.",
            "region_index": 0,
            "image_prompt": IMAGE,
        },
        "sons": [SON, SON, SON],
        "relations": [{"i": 0, "j": 1, "value": -20, "note": "Old feud."}],
    },
    PromptId.SON_POWERS_USER: {"powers": SON["powers"], "existence": EXISTENCE, "image_prompt": IMAGE},
    PromptId.CREATOR_PORTRAIT_USER: GOD,
    PromptId.SUMMON_SON_USER: SON,
    PromptId.AWAKEN_PEOPLES_USER: {
        "peoples": [
            {
                "region_id": 9,
                "people": {**RECORD, "population": 2000, "martiality": 40, "craft": 30, "magic": 20},
                "language": {**RECORD, "words": [{"word": "vesh", "meaning": "salt", "kind": "noun", "origin": "the shore"}]},
                "settlement": {**RECORD, "population": 300},
                "resource": {**RECORD, "domain": "salt"},
                "knowledge": {**RECORD, "branch": "astronomy"},
                "tradition": RECORD,
                "worshipped_son_id": 2,
            }
        ]
    },
    PromptId.REVELATION_USER: {
        "type": "celestial",
        "name": "Ka",
        "subtype": "star",
        "description": "Bright.",
        "domain": "star",
        "power_level": 5,
        "location_id": 0,
        "stats": {"brightness": 80},
        "links": [{"target_kind": "son", "target_id": 2, "kind": "tells_of", "description": "named for him"}],
        "image_prompt": IMAGE,
        "mechanic": None,
    },
    PromptId.FATE_JUDGMENT_USER: {
        "verdicts": [VERDICT],
        "namings": [NAMING_ITEM],
        "fulfilled_prophecies": [{"id": 90, "how": "The sea rose.", "reading": "misread"}],
        "resolved_thread": {"id": 3, "how": "The salt fell silent."},
        "closed_threads": [{"id": 4, "how": "Forgotten."}],
        "advanced_threads": [{"id": 5, "record_id": 13, "how": "A step."}],
        "new_threads": [{"text": "Who burned the bell?", "related_ids": [12]}],
        "rewards": [{"son_id": 2, "fame": 3, "reason": "He ended the salt song."}],
        "facts": [{"subject_id": 12, "relation": "is made of", "object": "salt"}],
        "words": [{"language_id": 20, "word": "vesh", "meaning": "salt", "origin": "the war"}],
    },
    PromptId.FATE_EXTRA_JUDGMENT_USER: {"verdicts": [VERDICT]},
    PromptId.CHRONICLER_USER: {
        "age_name": "Age of Brine",
        "narrative": "Things happened.",
        "summary": SECTION["summary"],
        "chronicler": {"name": "Ehmel", "who": "scribe of the Kael"},
        "worlds": [SECTION],
    },
    PromptId.CHRONICLER_FIX_OPENING_USER: {"first_sentence": "A bell rang under the salt."},
    PromptId.CHRONICLER_AUDIT_FIX_USER: {
        "narrative": "x",
        "coverage": {
            "covered": ["son-2"],
            "entity_ids": [5],
            "outcomes": [{"ref": "war-1", "winner_id": 5}],
            "credits": [],
            "idle_actor_ids": [],
            "counts": [],
        },
    },
    PromptId.CHRONICLER_MISSING_WORLDS_USER: {"worlds": [SECTION]},
    PromptId.CHRONICLER_LOST_AGE_USER: {"age_name": "Age of Brine", "narrative": "x", "summary": "y", "chronicler": {"name": "Ehmel", "who": "scribe"}},
    PromptId.CHRONICLER_LOST_WORLD_SECTIONS_USER: {"worlds": [SECTION]},
    PromptId.NAMING_USER: {"namings": [NAMING_ITEM]},
    PromptId.VOICES_USER: {
        "views": [{"people_id": 30, "historian": "Ehmel", "text": "We won."}],
        "beliefs": [{"people_id": 30, "son_id": 2, "name": "Salt Mother", "story": "She weeps.", "wrong": "She is a he."}],
    },
    PromptId.DEEPEN_ENTITY_USER: {
        "history": "Long ago.",
        "rumours": ["It sings."],
        "sayings": [SAYING],
        "details": ["Cold walls."],
        "special": {"temperament": "Calm"},
    },
    PromptId.DEEPEN_CELESTIAL_USER: {
        "history": "The sea came first.",
        "rumours": ["The tide speaks."],
        "sayings": [SAYING],
        "details": ["Salt rain."],
    },
    PromptId.CREATOR_EPIC_USER: {
        "title": "The Brine",
        "sections": [{"title": "Dawn", "text": "Salt.", "age_start": 1, "age_end": 2}],
        "line": "Salt remembers.",
    },
    PromptId.CREATOR_DEEPEN_USER: {
        "history": "He changed.",
        "names": [{"name": "Old Tide", "who": "the Kael", "meaning": "the sleeper"}],
        "prohibitions": ["No bone may burn."],
        "desire": "To be remembered.",
        "sayings": [{"kind": "hymn", "text": "O tide."}],
    },
    PromptId.FOREIGN_GOD_DEEPEN_USER: {
        "personality": {"appearance": "a", "temperament": "b", "obsession": "c", "fear": "d", "speech": "e", "secret": "f"},
        "existence": EXISTENCE,
        "powers": [{"name": "Ash Wall", "effect": "shield", "description": "A wall."}],
        "history": "Old.",
        "desire": "Fire.",
        "image_prompt": IMAGE,
    },
    PromptId.SON_EPIC_USER: {"title": "The Weeper", "epic": "He wept.", "line": "Salt."},
    PromptId.ENTITY_IMAGE_PROMPTS_USER: {"prompts": [{"id": 12, "prompt": IMAGE}]},
    PromptId.COSMOS_IMAGE_PROMPTS_USER: {"prompts": [{"number": 1, "prompt": IMAGE}]},
    PromptId.COUNCIL_SESSION_USER: {
        "speeches": [{"son_id": 2, "words": "Enough."}],
        "motion": "Make peace.",
        "votes": [{"son_id": 2, "vote": "yes", "reason": "Tired."}],
        "alliances": [{"a": 2, "b": 3, "kind": "covenant", "reason": "Fear."}],
        "decision": "call_for_peace",
        "minutes": "They spoke.",
        "agenda": "the salt war",
    },
    PromptId.SON_CHAT_USER: {"reply": "Always, father.", "attitude": "loyal", "loyalty_change": 3},
    PromptId.TRANSLATE_USER: {
        "translation": "Vesh ka.",
        "pronunciation": "vesh-ka",
        "word_by_word": [{"word": "vesh", "meaning": "salt"}],
        "new_words": [{"word": "ka", "meaning": "remembers", "kind": "verb", "origin": "old root"}],
        "note": "Verbs come last.",
    },
    PromptId.NEW_WORLD_USER: {
        "placement": "existing_star",
        "type": "ocean",
        "dialect": NAMING_RULE,
        "name": "Vel",
        "language": {
            "name": "Veli",
            "subtype": "spoken",
            "description": "Wet.",
            "words": [{"word": "vel", "meaning": "water", "kind": "noun", "origin": "rain"}],
        },
        "description": "Water.",
        "cosmology": "Water above.",
        "gravity": "low",
        "atmosphere": "dense",
        "time_factor": 1.5,
        "day": "Long days.",
        "star_id": 1,
        "regions": [NODE],
        "sky": {"name": "Ring", "subtype": "ring", "description": "A ring.", "image_prompt": IMAGE},
        "unique_resource": {
            "name": "Tear Pearl",
            "subtype": "pearl",
            "description": "Weeps.",
            "rule": "Decays.",
            "mechanics": ["decaying"],
            "region_index": 0,
            "image_prompt": IMAGE,
        },
        "natives": [{"kind": "species", "name": "Ray", "subtype": "fish", "description": "Wide.", "region_index": 0, "image_prompt": IMAGE}],
        "image_prompt": IMAGE,
    },
    PromptId.BOND_SUGGEST_USER: {
        "bonds": [{"record": "e12", "other": "s2", "direction": "from_record", "type": "tells_of", "reason": "The cave sings of him.", "shared_theme": False}]
    },
    PromptId.BOND_NAME_RELATED_USER: {"decisions": [{"number": 1, "decision": "close", "reason": "No link.", "denies_bond": True}]},
}

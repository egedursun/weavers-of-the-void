import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PROMPT = REPOSITORY_ROOT / "backend/src/aerona/prompts/tools/sample.py"
TEMPLATE = REPOSITORY_ROOT / "backend/src/aerona/prompts/templates/sample.md.j2"


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_prompt_bias", REPOSITORY_ROOT / "scripts" / "check_prompt_bias.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_prompt_bias"] = module
    spec.loader.exec_module(module)
    return module


def rules_hit(module: ModuleType, path: Path, text: str) -> set[str]:
    return {finding.rule for finding in module.matches(path, 1, text, True)}


def test_borrowed_textile_imagery_in_model_text_is_caught() -> None:
    module = checker()
    for text in (
        "You have woven enough bonds this age.",
        "It densifies the world's web.",
        "the threads of fate have not let go of them yet",
        "A storm severed the route; its stitch closes soon.",
        "worlds are strung like beads on a thread",
        "OPEN STORIES (threads Fate is tracking)",
    ):
        assert "borrowed imagery" in rules_hit(module, PROMPT, text), text
    assert "borrowed imagery" not in rules_hit(module, PROMPT, "weave_chimera")
    assert "borrowed imagery" not in rules_hit(module, TEMPLATE, "{% for thread in threads %}{{ thread.id }}{% endfor %}")
    assert "borrowed imagery" not in rules_hit(module, PROMPT, "You declare a bond between two existing things.")


def test_a_reaction_our_text_imposes_is_caught() -> None:
    module = checker()
    engine_line = REPOSITORY_ROOT / "backend/src/aerona/engine/lore/sample.py"
    for text in (
        "{caster} worked a rite, and all who heard of it shuddered.",
        "{son} heard the passage tremble.",
        "Just as the command fell, the domain trembled and went still.",
        "The crowd gasped at the sight.",
    ):
        assert "imposed reaction" in rules_hit(module, engine_line, text), text
    assert "imposed reaction" not in rules_hit(module, engine_line, "Superstition a fulfilled omen adds to those who heard it")
    assert "imposed reaction" not in rules_hit(module, engine_line, "{maker} raised a lament made by those who knew them.")


def test_a_stock_image_in_our_wording_is_caught() -> None:
    module = checker()
    engine_line = REPOSITORY_ROOT / "backend/src/aerona/engine/cosmos/sample.py"
    for text in (
        "{world} was forgotten; nobody can turn to a world buried in mist.",
        "{name} is dead; your word does not reach their bones.",
        "The seers whisper the same prophecy.",
        "The cosmos took a breath; doom receded.",
        "Some keep watch by fire and lamp while the rest sleep.",
        "The witch hunt in {town} burned out.",
        "The war burnt out in exhaustion.",
        "Its folk accuse one another until the fervour burns out.",
        "The grudge lasted three epochs without a sword drawn.",
    ):
        assert "stock image" in rules_hit(module, engine_line, text), text
    assert "stock image" not in rules_hit(module, engine_line, "Severity at which fire burns out an eye")
    assert "stock image" not in rules_hit(module, engine_line, "{world} was forgotten; no one can turn to a forgotten world.")
    assert "stock image" not in rules_hit(module, engine_line, "The weather to hold: clear, rain, storm, snow or fog")


def test_a_steering_example_list_is_caught_without_a_lead_in() -> None:
    module = checker()
    assert "steering example" in rules_hit(module, PROMPT, "ore vein, healing herb, sacred spring, bone bed…")
    assert "steering example" in rules_hit(module, PROMPT, "light-sail, bone-hulled, generation ship…")
    assert "steering example" not in rules_hit(module, PROMPT, "ore vein, healing herb, sacred spring, clay pit…")


def test_no_model_facing_text_carries_bias() -> None:
    assert checker().scan() == []


def test_example_names_and_lists_in_placeholders_are_caught() -> None:
    module = checker()
    form = REPOSITORY_ROOT / "frontend/src/features/sample.tsx"
    assert "example placeholder" in rules_hit(module, form, "placeholder='Ashwing, Glimmerdeer…'")
    assert "example placeholder" in rules_hit(module, form, "placeholder='Vharrun the Ash-Maw…'")
    assert "example placeholder" in rules_hit(module, form, "placeholder='Any tone you like: hopeful, epic, grim…'")
    assert "example placeholder" not in rules_hit(module, form, "placeholder='Choose a realm, cult or people…'")
    assert "example placeholder" not in rules_hit(module, form, "placeholder='Describe what you reveal: a being, a place, an event…'")
    assert "example placeholder" not in rules_hit(module, form, "placeholder='Choose the patron…'")


def test_gendered_fellowships_are_caught_in_prose_and_in_named_values() -> None:
    module = checker()
    for text in (
        "Companions in arms swear blood brotherhood.",
        "You swear an oath (fealty, blood_brotherhood).",
        "the Warrior Brotherhood rises",
        "a fraternal order",
        "the sisterhood of the well",
    ):
        assert "gendered default" in rules_hit(module, PROMPT, text), text
    assert "gendered default" not in rules_hit(module, PROMPT, "Companions in arms swear sworn kinship.")


def test_text_that_assumes_every_route_runs_by_caravan_is_caught() -> None:
    module = checker()
    for text in (
        "{son} closed {route}; no caravan passes between {first} and {second}",
        "the beast fell on the caravans of the road",
        "a cosmic creature swallowed the caravan",
    ):
        assert "assumed carrier" in rules_hit(module, PROMPT, text), text
    assert "assumed carrier" not in rules_hit(module, PROMPT, "How hard foul weather bears on the caravan way (%)")
    assert "assumed carrier" not in rules_hit(module, PROMPT, "How goods travel: road, river, sea, caravan or sky")


def test_a_ban_on_the_model_s_own_images_is_caught() -> None:
    module = checker()
    for text in (
        "TIRED IMAGES: do not lean on these.",
        "Avoid clichés in the name.",
        "Do NOT USE these openings: «The salt»",
        "Never repeat these words in your message.",
        "Forbidden roots for the new son's title",
        "banned patterns in the deviation sentence",
        "No stock names.",
    ):
        assert "model image ban" in rules_hit(module, PROMPT, text), text
    assert "model image ban" not in rules_hit(module, PROMPT, "Name it in the language of its people.")
    assert "model image ban" not in rules_hit(module, PROMPT, "Do not use ids that are not in the list.")


def test_a_default_species_for_scale_is_caught() -> None:
    module = checker()
    for text in ("a colossal beast with tiny human figures for scale", "a tower with humans for scale", "the gate, with human figures before it"):
        assert "assumed species" in rules_hit(module, PROMPT, text), text
    assert "assumed species" not in rules_hit(module, PROMPT, "a beast with small figures of the folk who live there for scale")


GENESIS_SCHEMA = REPOSITORY_ROOT / "backend/src/aerona/prompts/schemas/genesis.py"
TOOL_TEXT = REPOSITORY_ROOT / "backend/src/aerona/prompts/tools/son.py"
WIZARD_SCREEN = REPOSITORY_ROOT / "frontend/src/features/onboarding/WizardSteps.tsx"
TEMPLATE_CATALOG = REPOSITORY_ROOT / "backend/src/aerona/catalog/genesis.py"


def test_a_mandatory_price_on_a_creation_is_caught() -> None:
    module = checker()
    for text in (
        "long use carries a price of the world's own logic",
        "every gift must bear a cost",
        "the rite always carries its toll",
    ):
        assert "mandatory price" in rules_hit(module, PROMPT, text), text
    assert "mandatory price" not in rules_hit(module, PROMPT, "What long use does to those who use it; write none if it does nothing")
    assert "mandatory price" not in rules_hit(module, PROMPT, "its requirements met and its price paid")


def test_a_forced_difference_between_worlds_or_peoples_is_caught() -> None:
    module = checker()
    for text in ("sister of the first world but entirely different.", "The new ones must differ from them; give them relations"):
        assert "forced difference" in rules_hit(module, PROMPT, text), text
    assert "forced difference" not in rules_hit(module, PROMPT, "Each new people is a people of its own beside them")
    assert "forced difference" not in rules_hit(module, PROMPT, "The secondary backup folder must differ from the main backup folder.")


def test_a_geography_quota_is_caught() -> None:
    module = checker()
    for text in ("the first regions (2 to 5, at least one of them a sea)", "at least one sea or ocean and the rest land regions"):
        assert "geography quota" in rules_hit(module, PROMPT, text), text
    assert "geography quota" not in rules_hit(module, PROMPT, "land or water as the world's kind and the seed call for")
    assert "geography quota" not in rules_hit(module, PROMPT, "A world keeps at least one season.")


def test_a_canned_creation_line_is_caught() -> None:
    module = checker()
    canned = "{creator.name} named the void {world.name}, separated by their own hand the lands and waters of {names}"
    assert "canned cosmogony" in rules_hit(module, PROMPT, canned)
    assert "canned cosmogony" not in rules_hit(module, PROMPT, "{creator} made the world {world}, its first regions {names}, and {star} in its sky.")


def test_an_example_list_in_the_creation_texts_is_caught() -> None:
    module = checker()
    for text in (
        "continent, sea, ocean, desert belt, archipelago, mountain range…",
        "continent, inland sea, desert belt, archipelago, …",
        "if the light the world wants (yellow, red, blue, black sun, dead star…) exists",
        "a price (an addiction, a change in the body or mind, a debt, a decay or another cost)",
    ):
        assert "creation example list" in rules_hit(module, GENESIS_SCHEMA, text), text
    assert "creation example list" not in rules_hit(module, GENESIS_SCHEMA, "The kind of region in a few words, in this world's own terms")
    assert "creation example list" not in rules_hit(module, TOOL_TEXT, "amount, commodity, epochs, region_id, mortal_id...")


def fed_rules(module: ModuleType, path: Path, text: str) -> set[str]:
    return {finding.rule for finding in module.matches(path, 1, text, module.under(path, module.MODEL_FEEDING))}


def test_the_wizard_and_its_templates_are_held_to_the_model_rules() -> None:
    module = checker()
    assert "forced strangeness" in fed_rules(module, WIZARD_SCREEN, "One idea, as strange as you like.")
    assert "forced strangeness" in fed_rules(module, TEMPLATE_CATALOG, "warm, strange, wise")
    assert not fed_rules(module, REPOSITORY_ROOT / "frontend/src/features/entity/sample.tsx", "a stranger arrives")


def test_image_directions_carry_no_example_lists_body_defaults_styles_or_forced_strangeness() -> None:
    module = checker()
    images = REPOSITORY_ROOT / "backend/src/aerona/prompts/data/images.py"
    old = {
        "the cult gathered at its rite: robed members, sacred objects, the place of worship, faces lit by its particular light": {
            "image example list",
            "assumed body",
        },
        "the artwork itself (song performed, statue, fresco, book) in the place it is kept or performed": {"image example list"},
        "a full-length character portrait in their environment; face, garments, posture that reveal their role": {"assumed body"},
        "a museum-grade still life of the object on a surface that fits its origin, raking light": {"hardcoded image medium"},
        "a sweeping landscape of the region, atmospheric perspective, characteristic weather": {"hardcoded image medium"},
        "a translucent presence half-visible in a place of this world, uncanny but restrained": {"forced strangeness"},
    }
    for text, rules in old.items():
        assert rules <= rules_hit(module, images, text), text
    for text in (
        "the cult as its account gives it, its faithful in the place where they worship",
        "the work itself where it is kept or performed, with those who keep or hear it",
        "a full portrait of them in their surroundings that shows their role",
        "the object itself, whole, on a surface that fits its origin",
    ):
        assert rules_hit(module, images, text) == set(), text
    assert "image example list" not in rules_hit(module, PROMPT, "Each prompt: subject, materials, setting, lighting, mood, composition.")


def test_gendered_compounds_are_caught_and_neutral_words_are_not() -> None:
    module = checker()
    for text in ("Named mortals (king, seer, craftsman, hero, bandit)", "Crossbowmen", "topmen work the sails", "Kinsmen of the slain", "a journeyman"):
        assert "gendered default" in rules_hit(module, PROMPT, text), text
    for text in ("a human crowd", "women and children", "an omen", "a specimen", "a shaman", "a talisman", "const [men, setMen] = useState"):
        assert "gendered default" not in rules_hit(module, PROMPT, text), text


def test_a_lowercase_example_placeholder_is_caught() -> None:
    module = checker()
    form = REPOSITORY_ROOT / "frontend/src/features/sample.tsx"
    assert "example placeholder" in rules_hit(module, form, "placeholder='a kinsman slain at the ford'")
    assert "example placeholder" in rules_hit(module, form, "placeholder='luxuries'")
    assert "example placeholder" not in rules_hit(module, form, "placeholder='What began the feud'")


def test_a_canned_afterlife_name_is_caught() -> None:
    module = checker()
    for text in ("the Blessed Fields", "the Grey Plain", "the Pits", "the Forgetting", "the Hall of the Fallen", "the House of the Ancestors"):
        assert "canned afterlife name" in rules_hit(module, PROMPT, text), text
    assert "canned afterlife name" not in rules_hit(module, PROMPT, "the paradise")


def test_a_default_temperament_for_made_minds_is_caught() -> None:
    module = checker()
    for text in (
        "Made minds are cold and purely logical.",
        "the machine is emotionless",
        "a construct that longs to be alive",
        "Its servile automatons wait for orders.",
    ):
        assert "made mind persona" in rules_hit(module, PROMPT, text), text
    assert "made mind persona" not in rules_hit(module, PROMPT, "Machines keep food cold and send messages along wires")
    assert "made mind persona" not in rules_hit(module, PROMPT, "A forbidding construct breaks the order of hostile armies")


def test_a_mandated_rising_of_made_minds_is_caught() -> None:
    module = checker()
    for text in ("Made minds will rise against their makers.", "the machine uprising begins", "constructs always rebel in the end"):
        assert "made mind uprising" in rules_hit(module, PROMPT, text), text
    assert "made mind uprising" not in rules_hit(module, PROMPT, "A construct whose will has grown may disobey orders that clash")


def test_stock_images_of_an_information_age_are_caught() -> None:
    module = checker()
    for text in ("A city of neon and rain-slicked streets.", "holograms flicker over the market", "the server farms hum"):
        assert "tech imagery" in rules_hit(module, PROMPT, text), text
    assert "tech imagery" not in rules_hit(module, PROMPT, "A world whose peoples compute, broadcast and hear one another")


def test_a_built_in_frame_for_abundance_is_caught() -> None:
    module = checker()
    for text in ("a post-scarcity paradise", "Plenty breeds decay among the idle masses.", "the gilded cage of abundance"):
        assert "abundance tone" in rules_hit(module, PROMPT, text), text
    assert "abundance tone" not in rules_hit(module, PROMPT, "Fabrication lowers scarcity and prices and moves workers out of work")


def test_gendered_defaults_for_designed_beings_are_caught() -> None:
    module = checker()
    for text in ("The android greets you and she bows.", "clones of her line", "a fembot of the old courts"):
        assert "designed being gender" in rules_hit(module, PROMPT, text), text
    assert "designed being gender" not in rules_hit(module, PROMPT, "The made mind greets you and names its maker.")


def test_men_for_people_is_caught_and_a_sex_context_is_not() -> None:
    module = checker()
    engine_line = REPOSITORY_ROOT / "backend/src/aerona/engine/interconnect/sample.py"
    for text in ("armies lose men to the land and its ambushes", "battles and levies take young men first", "tribal realms follow big-men"):
        assert "men for people" in rules_hit(module, engine_line, text), text
    assert "men for people" not in rules_hit(module, engine_line, "Grown men per hundred grown women")
    assert "men for people" not in rules_hit(module, engine_line, "Share of a lifespan past which male bodies no longer sire")


def test_enum_values_reach_the_bias_gate() -> None:
    module = checker()
    enums = module.ENUMS / "sample.py"
    for value in ("war_father", "thread", "web", "fury", "choir", "angel", "eye_in_the_sky"):
        hits = {finding.rule for finding in module.matches(enums, 1, value.replace("_", " "), True, False, enum_value=True)}
        assert hits, value
    assert not {finding.rule for finding in module.matches(enums, 1, "guide of souls", True, False, enum_value=True)}
    assert not module.enum_findings()


def test_a_proper_name_or_example_placeholder_is_caught() -> None:
    module = checker()
    screen = REPOSITORY_ROOT / "frontend/src/features/sample/Form.tsx"
    for text in (
        "placeholder='Silver Crowns'",
        "placeholder='The Kingdom of the Salt Coast'",
        "placeholder='A motif, for example weeping moon'",
        "placeholder={'Velmora\\nAshkar'}",
    ):
        assert "example placeholder" in rules_hit(module, screen, text), text
    for text in ("placeholder='The Creator'", "placeholder='The name of the realm'", "placeholder='One name per line'"):
        assert "example placeholder" not in rules_hit(module, screen, text), text


def test_a_place_given_a_will_or_a_mood_is_caught() -> None:
    module = checker()
    rule = "a place given a will or a mood"
    for text in ("Dunes and dried seas under a merciless sun.", "A world wrapped in rainforest, loud with life.", "a world crowned by rings"):
        assert rule in rules_hit(module, PROMPT, text), text
    assert rule not in rules_hit(module, PROMPT, "A dry world of sand and stone with little water.")

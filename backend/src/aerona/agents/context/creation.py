from aerona.catalog.climate import CLIMATES
from aerona.catalog.cosmography import DIMENSION_KINDS, WORLD_AGE_LABELS
from aerona.catalog.genesis import COSMOS_LABELS, SHAPE_LINES, TECHNOLOGY_LABELS, TEMPLATES, TEXTURE_LABELS
from aerona.catalog.worlds import WORLD_TYPES
from aerona.core.grammar import an, several
from aerona.domain.enums.world import CosmosSize
from aerona.domain.models.genesis import GenesisSettings
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.genesis import GenesisWizardContext
from aerona.rules.registry import Rules


def cosmos_label(rules: Rules, size: CosmosSize) -> str:
    worlds = {CosmosSize.SMALL: rules.setup_wizard.small_cosmos_worlds, CosmosSize.LARGE: rules.setup_wizard.large_cosmos_worlds}
    if size not in worlds:
        return "a single world"
    return f"{an(COSMOS_LABELS[size].lower())} ({several(1 + worlds[size], 'world', 'worlds')})"


def shape_line(settings: GenesisSettings) -> str | None:
    if settings.cosmos_size is CosmosSize.SINGLE:
        return None
    return SHAPE_LINES[settings.cosmos_shape]


def creation_text(rules: Rules, settings: GenesisSettings, *, for_genesis: bool) -> str:
    context = GenesisWizardContext(
        rules=rules,
        for_genesis=for_genesis,
        template_name=TEMPLATES[settings.template].name if settings.template is not None else None,
        magic=settings.magic,
        danger=settings.danger,
        technology_label=TECHNOLOGY_LABELS[settings.technology].lower(),
        language_label=TEXTURE_LABELS[settings.language_texture].lower(),
        cosmos_label=cosmos_label(rules, settings.cosmos_size),
        shape_line=shape_line(settings),
        layer_label=DIMENSION_KINDS[settings.layer_kind].label if settings.layer_kind is not None else None,
        world_type_label=WORLD_TYPES[settings.world_type].label if settings.world_type is not None else None,
        world_type_key=settings.world_type.value if settings.world_type is not None else None,
        sea=settings.sea_pct,
        mountains=settings.mountains_pct,
        moisture=settings.moisture_pct,
        climate_label=CLIMATES[settings.climate_era].label if settings.climate_era is not None else None,
        age_label=WORLD_AGE_LABELS[settings.world_age] if settings.world_age is not None else None,
    )
    return render(PromptId.GENESIS_WIZARD_SETTINGS, context)

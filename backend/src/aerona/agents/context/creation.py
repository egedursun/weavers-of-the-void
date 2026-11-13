from aerona.catalog.climate import CLIMATES
from aerona.catalog.cosmography import DIMENSION_KINDS, WORLD_AGE_LABELS
from aerona.catalog.genesis import SHAPE_LINES, TEMPLATES
from aerona.catalog.worlds import WORLD_TYPES
from aerona.domain.enums.world import CosmosSize
from aerona.domain.models.genesis import GenesisSettings
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.genesis import GenesisWizardContext
from aerona.rules.registry import Rules


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
        technology=settings.technology,
        language=settings.language_texture,
        cosmos=settings.cosmos_size,
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

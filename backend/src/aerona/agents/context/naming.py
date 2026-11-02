from aerona.db.tables.celestial import WorldRow
from aerona.domain.models.phonology import Phonology
from aerona.prompts.contexts.blocks import WorldNaming
from aerona.prompts.contexts.common import NamingRuleItem


def naming_item(phonology: Phonology | None, samples: list[str] | None = None) -> NamingRuleItem:
    if phonology is None:
        return NamingRuleItem(sample_names=samples or [])
    return NamingRuleItem(
        vowels="".join(phonology.vowels),
        consonants="".join(phonology.consonants),
        forbidden_sounds=list(phonology.forbidden_sounds),
        syllable_patterns=list(phonology.syllable_patterns),
        endings=list(phonology.preferred_endings),
        sample_names=samples or [],
    )


def world_naming(world: WorldRow, fallback: Phonology | None) -> WorldNaming:
    return WorldNaming(id=world.id, name=world.name, naming=naming_item(world.phonology or fallback))

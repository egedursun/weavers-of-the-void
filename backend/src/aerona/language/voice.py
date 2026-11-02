from aerona.language.corpus import CorpusSources, assemble_corpus
from aerona.language.generator import NamingVoice
from aerona.language.phonology import Phonology, build_phonology
from aerona.language.signature import LanguageSignature, derive_signature
from aerona.rules.registry import Rules


def phonology_for(sources: CorpusSources, alphabet: frozenset[str] | None, rules: Rules) -> Phonology:
    return build_phonology(assemble_corpus(sources, rules), alphabet, rules)


def build_voice(
    language_key: str,
    phonology: Phonology,
    rules: Rules,
    stored_signature: LanguageSignature | None = None,
    parent_signature: LanguageSignature | None = None,
) -> NamingVoice:
    signature = stored_signature or derive_signature(language_key, phonology, parent_signature, rules)
    return NamingVoice(language_key=language_key, phonology=phonology, signature=signature)

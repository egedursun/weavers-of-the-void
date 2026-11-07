import re
from dataclasses import dataclass

from aerona.core.total import partial
from aerona.domain.enums.world import ImageStyle

CUSTOM_STYLE_MAX_LENGTH = 300


@dataclass(frozen=True)
class StyleLook:
    label: str
    lead: str
    tail: str


STYLE_LOOKS = partial(
    ImageStyle,
    {
        ImageStyle.PHOTOREAL: StyleLook(
            "Photoreal",
            "Photorealistic photograph of",
            "Natural light, true-to-life texture and detail, considered lens and depth of field",
        ),
        ImageStyle.PAINTING: StyleLook(
            "Classical painting",
            "Classical oil painting of",
            "Visible brushstrokes on canvas, rich glazed colours, dramatic chiaroscuro, old master style",
        ),
        ImageStyle.INK: StyleLook(
            "Book illustration",
            "Pen and ink book illustration of",
            "Fine cross-hatching, engraved linework, ink on cream paper",
        ),
        ImageStyle.WATERCOLOR: StyleLook(
            "Watercolour",
            "Soft watercolour painting of",
            "Loose translucent washes, bleeding pigment edges, visible paper grain",
        ),
        ImageStyle.ANIME: StyleLook(
            "Anime",
            "Anime illustration of",
            "Clean bold line art, cel shading, vibrant flat colours",
        ),
    },
    without={ImageStyle.CUSTOM},
)

PHOTO_TERMS = re.compile(
    r"\b(hyper-?realistic|photo-?realistic|photoreal|photograph(y|ic|ed)?|photo|astrophotography|DSLR|bokeh|"
    r"\d+\s?mm( lens)?|f/\d+(\.\d+)?|(wide-angle|telephoto|macro|prime) lens|lens|long exposure|shallow depth of field|"
    r"documentary style|cinematic still|camera)\b",
    re.IGNORECASE,
)
LEADING_MEDIUM = re.compile(r"^\s*(an? )?(english,? )?(photo-?realistic|photoreal|cinematic)( image| photo(graph)?| portrait)?( of)?[,:]?\s*", re.IGNORECASE)
LOOSE_PUNCTUATION = re.compile(r"\s*,\s*(,\s*)+|\(\s*\)|\s{2,}")


def style_signature(style: ImageStyle, custom: str) -> str:
    if style is ImageStyle.CUSTOM:
        return f"{ImageStyle.CUSTOM.value}: {custom.strip()}"
    return style.value


def style_label(style: ImageStyle, custom: str) -> str:
    if style is ImageStyle.CUSTOM:
        return custom.strip() or "Custom"
    return STYLE_LOOKS[style].label


def _subject(prompt: str, keep_photo_terms: bool) -> str:
    body = LEADING_MEDIUM.sub("", prompt.strip())
    if not keep_photo_terms:
        body = PHOTO_TERMS.sub("", body)
        body = LOOSE_PUNCTUATION.sub(lambda match: ", " if "," in match.group(0) else " ", body)
    return body.strip(" ,.;")


def styled_prompt(prompt: str, style: ImageStyle, custom: str) -> str:
    if style is ImageStyle.CUSTOM:
        look = custom.strip()
        subject = _subject(prompt, keep_photo_terms=False)
        return f"{subject}. In this visual style: {look}." if look else f"{subject}."
    look_of = STYLE_LOOKS[style]
    subject = _subject(prompt, keep_photo_terms=style is ImageStyle.PHOTOREAL)
    if subject:
        subject = subject[0].lower() + subject[1:] if subject[1:2].islower() else subject
    return f"{look_of.lead} {subject}. {look_of.tail}."

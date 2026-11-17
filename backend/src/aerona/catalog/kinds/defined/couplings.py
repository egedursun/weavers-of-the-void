from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.couplings import CarrionRest, FieldAgreementKind, SealKind, TeachingKind

CARRION_REST = total(
    CarrionRest,
    {
        CarrionRest.ROTTING: Defined(
            "Rotting where they lie",
            checked_by=("engine.couplings.carrion.lie_unscavenged",),
            used_by=(
                "db.tables.couplings.CarrionPulseRow",
                "engine.couplings.carrion.carrion",
                "engine.couplings.carrion.rest_of",
                "engine.couplings.control.keep_dead",
            ),
        ),
        CarrionRest.MUMMIFIED: Defined(
            "Dried out by the land",
            checked_by=(),
            used_by=("catalog.couplings.KEEPING_RESTS", "catalog.couplings.WORLD_RESTS", "engine.couplings.carrion.rest_of"),
        ),
        CarrionRest.FROZEN: Defined(
            "Frozen where they fell",
            checked_by=(),
            used_by=("catalog.couplings.KEEPING_RESTS", "catalog.couplings.WORLD_RESTS", "engine.couplings.carrion.rest_of"),
        ),
        CarrionRest.DRIFTING: Defined(
            "Fallen to the depths", checked_by=("engine.couplings.carrion.lie_unscavenged",), used_by=("catalog.couplings.WORLD_RESTS",)
        ),
        CarrionRest.FLOATING: Defined(
            "Floating where they died",
            checked_by=("engine.couplings.carrion.lie_unscavenged",),
            used_by=("catalog.couplings.KEEPING_RESTS", "catalog.couplings.WORLD_RESTS"),
        ),
    },
)

FIELD_AGREEMENT_KIND = total(
    FieldAgreementKind,
    {
        FieldAgreementKind.PARLEY: Defined("Parley", checked_by=(), used_by=("engine.couplings.field.parley", "tools.mortal.couplings.parley")),
        FieldAgreementKind.TRUCE: Defined("Truce", checked_by=(), used_by=("engine.couplings.field.parley", "tools.mortal.couplings.parley")),
        FieldAgreementKind.SURRENDER: Defined(
            "Surrender terms",
            checked_by=("engine.couplings.field.lapse", "engine.couplings.field.under_terms"),
            used_by=("engine.couplings.field.offer_terms",),
        ),
        FieldAgreementKind.EXCHANGE: Defined("Exchange of captives and the dead", checked_by=(), used_by=("engine.couplings.field.exchanges",)),
        FieldAgreementKind.SAFE_CONDUCT: Defined("Safe conduct", checked_by=(), used_by=("engine.couplings.field.offer_terms",)),
        FieldAgreementKind.FRATERNISATION: Defined("Fraternisation", checked_by=(), used_by=("engine.couplings.field.fraternise",)),
    },
)

SEAL_KIND = total(
    SealKind,
    {
        SealKind.STRUCTURE: Defined("Walls and gates", checked_by=(), used_by=("engine.couplings.deep.seal_after_breach",)),
        SealKind.RITE: Defined(
            "A warding rite",
            checked_by=("engine.couplings.deep.seal_deep", "engine.couplings.deep.test_seal"),
            used_by=("engine.couplings.deep.seal_after_breach",),
        ),
        SealKind.DIVINE: Defined("A god's hand", checked_by=(), used_by=("services.player.couplings.SealDraft", "tools.son.couplings.seal_breach")),
    },
)

TEACHING_KIND = total(
    TeachingKind,
    {
        TeachingKind.SONG: Defined("A song", checked_by=("engine.couplings.teachers.teach",), used_by=("engine.couplings.teachers.SPIRIT_LESSONS",)),
        TeachingKind.ART_FORM: Defined("An art form", checked_by=("engine.couplings.teachers.teach",), used_by=("engine.couplings.teachers.SPIRIT_LESSONS",)),
        TeachingKind.RITE: Defined(
            "A rite",
            checked_by=("engine.couplings.teachers.teach",),
            used_by=("engine.couplings.teachers.BEAST_LESSONS", "engine.couplings.teachers.SPIRIT_LESSONS"),
        ),
        TeachingKind.TECHNIQUE: Defined("A craft", checked_by=("engine.couplings.teachers.teach",), used_by=("engine.couplings.teachers.SPIRIT_LESSONS",)),
        TeachingKind.TRUE_NAME: Defined(
            "A true name",
            checked_by=("engine.couplings.teachers.teach",),
            used_by=("engine.couplings.teachers.BEAST_LESSONS", "engine.couplings.teachers.SPIRIT_LESSONS"),
        ),
        TeachingKind.PROPHECY: Defined("A prophecy", checked_by=(), used_by=("engine.couplings.teachers.SPIRIT_LESSONS",)),
        TeachingKind.TREASURE: Defined(
            "Where a treasure lies", checked_by=("engine.couplings.teachers.teach",), used_by=("engine.couplings.teachers.SPIRIT_LESSONS",)
        ),
        TeachingKind.LANGUAGE: Defined(
            "A language",
            checked_by=("engine.couplings.teachers.teach",),
            used_by=("engine.couplings.teachers.BEAST_LESSONS", "engine.couplings.teachers.SPIRIT_LESSONS"),
        ),
        TeachingKind.ACCOUNT: Defined(
            "The memory of an age",
            checked_by=("engine.couplings.teachers.teach",),
            used_by=("engine.couplings.control.block_teaching", "engine.couplings.teachers.BEAST_LESSONS"),
        ),
    },
)

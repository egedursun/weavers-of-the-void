from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.customs import EvidenceKind
from aerona.domain.enums.justice import TrialKind
from aerona.domain.enums.mortal import CrimeKind, PunishmentKind
from aerona.domain.enums.polity import LawArea

K = CrimeKind
A = LawArea
V = EvidenceKind
P = PunishmentKind


@dataclass(frozen=True)
class CrimeSpec:
    area: LawArea
    severity: int
    evidence: tuple[EvidenceKind, ...]
    detection: int
    punishment: PunishmentKind
    text: str


CRIMES: Mapping[CrimeKind, CrimeSpec] = total(
    CrimeKind,
    {
        K.THEFT: CrimeSpec(
            A.PROPERTY,
            20,
            (
                V.TRACE,
                V.WITNESS,
            ),
            50,
            P.FINE,
            "theft",
        ),
        K.BURGLARY: CrimeSpec(
            A.PROPERTY,
            30,
            (
                V.TRACE,
                V.WITNESS,
            ),
            40,
            P.FLOGGING,
            "burglary",
        ),
        K.ROBBERY: CrimeSpec(A.PROPERTY, 45, (V.WITNESS,), 55, P.IMPRISONMENT, "robbery"),
        K.FRAUD: CrimeSpec(A.PROPERTY, 30, (V.DOCUMENT,), 35, P.FINE, "fraud"),
        K.EMBEZZLEMENT: CrimeSpec(A.PROPERTY, 40, (V.DOCUMENT,), 30, P.CONFISCATION, "embezzlement"),
        K.COUNTERFEITING: CrimeSpec(
            A.FISCAL,
            50,
            (
                V.DOCUMENT,
                V.TRACE,
            ),
            30,
            P.BRANDING,
            "counterfeiting",
        ),
        K.SMUGGLING: CrimeSpec(A.FISCAL, 30, (V.TRACE,), 30, P.CONFISCATION, "smuggling"),
        K.POACHING: CrimeSpec(
            A.PROPERTY,
            15,
            (
                V.TRACE,
                V.WITNESS,
            ),
            40,
            P.FINE,
            "poaching",
        ),
        K.ARSON: CrimeSpec(
            A.PROPERTY,
            60,
            (
                V.TRACE,
                V.WITNESS,
            ),
            45,
            P.DEATH,
            "arson",
        ),
        K.VANDALISM: CrimeSpec(A.PROPERTY, 15, (V.WITNESS,), 50, P.COMMUNITY_WORK, "vandalism"),
        K.TRESPASS: CrimeSpec(A.PROPERTY, 5, (V.WITNESS,), 60, P.FINE, "trespass"),
        K.RECEIVING: CrimeSpec(A.PROPERTY, 20, (V.TRACE,), 30, P.FINE, "receiving stolen goods"),
        K.MURDER: CrimeSpec(
            A.PENAL,
            90,
            (
                V.WITNESS,
                V.TRACE,
                V.CONFESSION,
            ),
            60,
            P.DEATH,
            "murder",
        ),
        K.MANSLAUGHTER: CrimeSpec(A.PENAL, 60, (V.WITNESS,), 60, P.COMPENSATION, "manslaughter"),
        K.ASSAULT: CrimeSpec(A.PENAL, 35, (V.WITNESS,), 65, P.FLOGGING, "assault"),
        K.KIDNAPPING: CrimeSpec(
            A.PENAL,
            70,
            (
                V.WITNESS,
                V.TRACE,
            ),
            45,
            P.IMPRISONMENT,
            "kidnapping",
        ),
        K.TRAFFICKING: CrimeSpec(
            A.PENAL,
            80,
            (
                V.DOCUMENT,
                V.WITNESS,
            ),
            30,
            P.PENAL_LABOUR,
            "enslavement and trafficking",
        ),
        K.SEXUAL_VIOLENCE: CrimeSpec(
            A.PENAL,
            85,
            (
                V.WITNESS,
                V.CONFESSION,
            ),
            40,
            P.IMPRISONMENT,
            "violence against a person's body",
        ),
        K.THREATS: CrimeSpec(A.PENAL, 15, (V.WITNESS,), 50, P.FINE, "threats"),
        K.DUELLING: CrimeSpec(A.PENAL, 30, (V.WITNESS,), 70, P.FINE, "duelling where it is banned"),
        K.RIOT: CrimeSpec(A.SOCIAL, 40, (V.WITNESS,), 70, P.FLOGGING, "riot"),
        K.SEDITION: CrimeSpec(
            A.CONSTITUTIONAL,
            55,
            (
                V.DOCUMENT,
                V.WITNESS,
            ),
            35,
            P.EXILE,
            "sedition",
        ),
        K.BANDITRY: CrimeSpec(A.PENAL, 55, (V.WITNESS,), 50, P.OUTLAWRY, "banditry"),
        K.PIRACY: CrimeSpec(A.PENAL, 60, (V.WITNESS,), 40, P.DEATH, "piracy"),
        K.REBELLION: CrimeSpec(A.CONSTITUTIONAL, 85, (V.WITNESS,), 60, P.DEATH, "rebellion"),
        K.VAGRANCY: CrimeSpec(A.SOCIAL, 5, (V.WITNESS,), 60, P.COMMUNITY_WORK, "vagrancy where it is banned"),
        K.UNLAWFUL_ASSEMBLY: CrimeSpec(A.SOCIAL, 20, (V.WITNESS,), 60, P.FINE, "unlawful assembly"),
        K.DESERTION: CrimeSpec(A.MILITARY, 50, (V.WITNESS,), 60, P.FLOGGING, "desertion"),
        K.MUTINY: CrimeSpec(A.MILITARY, 75, (V.WITNESS,), 65, P.DEATH, "mutiny"),
        K.COWARDICE: CrimeSpec(A.MILITARY, 30, (V.WITNESS,), 70, P.PUBLIC_SHAMING, "cowardice"),
        K.LOOTING: CrimeSpec(
            A.MILITARY,
            30,
            (
                V.WITNESS,
                V.TRACE,
            ),
            50,
            P.FLOGGING,
            "looting against orders",
        ),
        K.WAR_CRIMES: CrimeSpec(
            A.MILITARY,
            90,
            (
                V.WITNESS,
                V.DOCUMENT,
            ),
            30,
            P.DEATH,
            "crimes of war under treaty",
        ),
        K.TREASON: CrimeSpec(
            A.CONSTITUTIONAL,
            95,
            (
                V.DOCUMENT,
                V.WITNESS,
                V.CONFESSION,
            ),
            40,
            P.DEATH,
            "treason",
        ),
        K.ESPIONAGE: CrimeSpec(
            A.CONSTITUTIONAL,
            70,
            (
                V.DOCUMENT,
                V.TRACE,
            ),
            30,
            P.IMPRISONMENT,
            "espionage",
        ),
        K.BRIBERY: CrimeSpec(
            A.CONSTITUTIONAL,
            35,
            (
                V.DOCUMENT,
                V.WITNESS,
            ),
            30,
            P.FINE,
            "bribery",
        ),
        K.CORRUPTION: CrimeSpec(A.CONSTITUTIONAL, 45, (V.DOCUMENT,), 25, P.LOSS_OF_RANK, "corruption"),
        K.USURPATION: CrimeSpec(A.SUCCESSION, 95, (V.WITNESS,), 70, P.DEATH, "usurpation"),
        K.CONTEMPT_OF_COURT: CrimeSpec(A.CONSTITUTIONAL, 15, (V.WITNESS,), 80, P.FINE, "contempt of court"),
        K.PERJURY: CrimeSpec(
            A.CONSTITUTIONAL,
            35,
            (
                V.WITNESS,
                V.DOCUMENT,
            ),
            35,
            P.FLOGGING,
            "perjury",
        ),
        K.ELECTION_FRAUD: CrimeSpec(A.CONSTITUTIONAL, 50, (V.DOCUMENT,), 30, P.LOSS_OF_RANK, "fraud in an election"),
        K.TAX_EVASION: CrimeSpec(A.FISCAL, 25, (V.DOCUMENT,), 35, P.FINE, "evading taxes"),
        K.CUSTOMS_FRAUD: CrimeSpec(
            A.FISCAL,
            30,
            (
                V.DOCUMENT,
                V.TRACE,
            ),
            35,
            P.CONFISCATION,
            "customs fraud",
        ),
        K.DEBASEMENT: CrimeSpec(A.FISCAL, 55, (V.TRACE,), 30, P.CONFISCATION, "debasing the coin"),
        K.UNLICENSED_TRADE: CrimeSpec(A.FISCAL, 15, (V.DOCUMENT,), 40, P.FINE, "trading without a licence"),
        K.QUARANTINE_BREACH: CrimeSpec(A.PUBLIC_HEALTH, 35, (V.WITNESS,), 55, P.FINE, "breaking quarantine"),
        K.WELL_POISONING: CrimeSpec(
            A.PUBLIC_HEALTH,
            90,
            (
                V.TRACE,
                V.WITNESS,
            ),
            35,
            P.DEATH,
            "poisoning the wells",
        ),
        K.TAINTED_GOODS: CrimeSpec(A.PUBLIC_HEALTH, 30, (V.TRACE,), 40, P.FINE, "selling tainted goods"),
        K.UNLAWFUL_POLLUTION: CrimeSpec(A.PUBLIC_HEALTH, 25, (V.TRACE,), 40, P.FINE, "polluting against the law"),
        K.UNION_OFFENCE: CrimeSpec(A.SOCIAL, 25, (V.WITNESS,), 40, P.PUBLIC_SHAMING, "an offence against a union the culture names"),
        K.SUMPTUARY_BREACH: CrimeSpec(A.SOCIAL, 10, (V.WITNESS,), 70, P.FINE, "dressing above one's station"),
        K.FORBIDDEN_FOOD: CrimeSpec(A.SOCIAL, 10, (V.WITNESS,), 50, P.PENANCE, "eating what is forbidden"),
        K.INTOXICATION: CrimeSpec(A.SOCIAL, 10, (V.WITNESS,), 60, P.FINE, "intoxication where it is banned"),
        K.TABOO_BREACH: CrimeSpec(A.SOCIAL, 30, (V.WITNESS,), 50, P.PENANCE, "breaking a taboo"),
        K.PURITY_BREACH: CrimeSpec(A.SOCIAL, 20, (V.WITNESS,), 50, P.PENANCE, "breaching purity"),
        K.BLASPHEMY: CrimeSpec(A.MAGIC, 40, (V.WITNESS,), 60, P.FINE, "blasphemy"),
        K.HERESY: CrimeSpec(
            A.MAGIC,
            50,
            (
                V.WITNESS,
                V.DOCUMENT,
            ),
            45,
            P.EXCOMMUNICATION,
            "heresy",
        ),
        K.SACRILEGE: CrimeSpec(
            A.MAGIC,
            60,
            (
                V.WITNESS,
                V.TRACE,
            ),
            50,
            P.FLOGGING,
            "sacrilege",
        ),
        K.DESECRATION: CrimeSpec(
            A.MAGIC,
            65,
            (
                V.WITNESS,
                V.TRACE,
            ),
            55,
            P.BANISHMENT_FROM_PLACE,
            "desecration",
        ),
        K.FORBIDDEN_RITE: CrimeSpec(
            A.MAGIC,
            55,
            (
                V.MAGIC,
                V.WITNESS,
            ),
            40,
            P.IMPRISONMENT,
            "working a forbidden rite",
        ),
        K.WITCHCRAFT: CrimeSpec(
            A.MAGIC,
            50,
            (
                V.WITNESS,
                V.DIVINATION,
                V.MAGIC,
            ),
            45,
            P.EXILE,
            "witchcraft",
        ),
        K.OATHBREAKING: CrimeSpec(A.MAGIC, 45, (V.WITNESS,), 60, P.PUBLIC_SHAMING, "oathbreaking"),
        K.UNLICENSED_POWER: CrimeSpec(
            A.MAGIC,
            35,
            (
                V.MAGIC,
                V.WITNESS,
            ),
            40,
            P.DAMPENING,
            "using a power without a licence",
        ),
        K.FALSE_CLAIM: CrimeSpec(A.SUCCESSION, 50, (V.DOCUMENT,), 40, P.EXILE, "pressing a false claim"),
        K.FORGED_LINE: CrimeSpec(A.SUCCESSION, 55, (V.DOCUMENT,), 30, P.BRANDING, "forging a line of descent"),
        K.HEIR_MURDER: CrimeSpec(
            A.SUCCESSION,
            95,
            (
                V.WITNESS,
                V.TRACE,
            ),
            50,
            P.DEATH,
            "murder of an heir",
        ),
        K.MIND_THEFT: CrimeSpec(
            A.PROPERTY,
            70,
            (
                V.TRACE,
                V.DOCUMENT,
            ),
            30,
            P.IMPRISONMENT,
            "theft of a mind",
        ),
        K.UNLICENSED_COPYING: CrimeSpec(A.PROPERTY, 40, (V.DOCUMENT,), 30, P.FINE, "copying a mind without leave"),
        K.FORCED_EDIT: CrimeSpec(A.PENAL, 75, (V.TRACE,), 25, P.IMPRISONMENT, "editing a mind by force"),
        K.ERASURE: CrimeSpec(A.PENAL, 85, (V.TRACE,), 30, P.IMPRISONMENT, "ending a mind"),
        K.MACHINE_SEIZURE: CrimeSpec(A.PROPERTY, 50, (V.TRACE,), 35, P.IMPRISONMENT, "seizing a made thing"),
        K.IMPERSONATION: CrimeSpec(A.CONSTITUTIONAL, 45, (V.DOCUMENT,), 30, P.FINE, "passing as another by a copy"),
        K.MIND_COMPULSION: CrimeSpec(A.PENAL, 70, (V.MAGIC,), 25, P.IMPRISONMENT, "bending a mind by a power"),
    },
)


@dataclass(frozen=True)
class PunishmentSpec:
    word: str
    deterrence: int
    recidivism: int
    cost: int
    labour: int
    mercy: int
    tradition: int
    order: int
    harm: int
    text: str


PUNISHMENTS: Mapping[PunishmentKind, PunishmentSpec] = total(
    PunishmentKind,
    {
        P.FINE: PunishmentSpec("fine", 20, 40, 0, 0, 10, 0, 10, 0, "was fined"),
        P.PUBLIC_SHAMING: PunishmentSpec("pillory", 25, 35, 0, 0, 0, 20, 10, 15, "was shamed in public"),
        P.FLOGGING: PunishmentSpec("flogging", 40, 30, 0, -5, -20, 15, 20, 35, "was flogged"),
        P.IMPRISONMENT: PunishmentSpec("prison", 45, 35, 20, -10, 0, 0, 25, 30, "was sent to prison"),
        P.HAND: PunishmentSpec("hand", 60, 20, 0, -20, -40, 20, 15, 60, "lost a hand to the law"),
        P.EYES: PunishmentSpec("blinding", 65, 15, 0, -30, -50, 10, 10, 80, "was blinded by the law"),
        P.TONGUE: PunishmentSpec("tongue", 55, 20, 0, -10, -45, 15, 10, 65, "had their tongue cut out by the law"),
        P.EXILE: PunishmentSpec("exile", 50, 10, 0, -10, 0, 10, 15, 25, "was sent into exile"),
        P.BRANDING: PunishmentSpec("branding", 45, 25, 0, -5, -25, 15, 15, 40, "was branded"),
        P.DEATH: PunishmentSpec("death", 70, 0, 5, -15, -60, 20, 25, 100, "was put to death"),
        P.REMAKING: PunishmentSpec("remaking", 60, 5, 30, -10, -50, -20, 15, 90, "was remade in body by the law"),
        P.FORCED_DORMANCY: PunishmentSpec("dormancy", 40, 10, 15, -15, -10, -15, 15, 30, "was put to sleep by the law"),
        P.FORCED_EDIT: PunishmentSpec("edit", 50, 5, 25, 0, -35, -20, 15, 70, "had their mind edited by the law"),
        P.SEAT_CONFINEMENT: PunishmentSpec("confinement", 35, 20, 10, -10, -5, -10, 15, 20, "was confined to one seat by the law"),
        P.STATE_SEIZURE: PunishmentSpec("seizure", 40, 15, 5, 5, -15, -10, 15, 25, "was seized by the state"),
        P.ERASURE: PunishmentSpec("erasure", 70, 0, 10, -15, -60, -20, 20, 100, "was ended by the law"),
        P.RESTITUTION: PunishmentSpec("restitution", 25, 30, 0, 0, 30, 10, 10, 0, "was made to restore what was taken"),
        P.COMPENSATION: PunishmentSpec("wergild", 30, 30, 0, 0, 25, 25, 10, 5, "paid a price to the wronged and their kin"),
        P.PENAL_LABOUR: PunishmentSpec("penal_labour", 45, 30, 10, 25, -10, 0, 25, 30, "was sent to labour under sentence"),
        P.SERVITUDE: PunishmentSpec("servitude", 50, 25, 0, 30, -35, 10, 15, 40, "was bound into servitude"),
        P.OUTLAWRY: PunishmentSpec("outlawry", 45, 30, 0, -5, -20, 25, 10, 35, "was declared outside the law"),
        P.CONFISCATION: PunishmentSpec("confiscation", 35, 25, 0, 5, 5, 0, 15, 5, "had their goods taken by the law"),
        P.LOSS_OF_RANK: PunishmentSpec("loss_of_rank", 35, 20, 0, 0, 10, 10, 15, 5, "was stripped of rank"),
        P.EXCOMMUNICATION: PunishmentSpec("excommunication", 35, 25, 0, 0, 0, 25, 5, 10, "was cast out of the faith"),
        P.PENANCE: PunishmentSpec("penance", 20, 35, 0, 0, 30, 25, 5, 5, "was set a penance"),
        P.BANISHMENT_FROM_PLACE: PunishmentSpec("banishment", 40, 20, 0, -5, 10, 10, 15, 15, "was banished from the place"),
        P.HOUSE_ARREST: PunishmentSpec("house_arrest", 30, 30, 5, -10, 20, 0, 15, 5, "was kept under arrest at home"),
        P.PROBATION: PunishmentSpec("probation", 15, 45, 5, 0, 35, -5, 10, 0, "was set free under watch"),
        P.REEDUCATION: PunishmentSpec("reeducation", 35, 25, 20, -5, 5, -25, 20, 30, "was sent to be taught anew"),
        P.TRANSPORTATION: PunishmentSpec("transportation", 50, 5, 25, 10, -5, 0, 15, 30, "was carried off to a far settlement"),
        P.COMMUNITY_WORK: PunishmentSpec("community_work", 20, 35, 0, 15, 30, 5, 10, 5, "was set to work for the community"),
        P.DAMPENING: PunishmentSpec("dampening", 40, 20, 15, 0, 0, -10, 20, 25, "had their powers dampened by the law"),
    },
)
PENALTY_WORDS: Mapping[str, PunishmentKind] = {spec.word: kind for kind, spec in PUNISHMENTS.items()}
CRIME_PENALTY_DEFAULTS: Mapping[CrimeKind, str] = {crime: PUNISHMENTS[spec.punishment].word for crime, spec in CRIMES.items()}


@dataclass(frozen=True)
class TrialSpec:
    fairness: int
    delay: int
    cost: int
    error: int
    mercy: int
    tradition: int
    order: int
    appeal: int
    sentence: PunishmentKind | None
    text: str


TRIALS: Mapping[TrialKind, TrialSpec] = total(
    TrialKind,
    {
        TrialKind.JUDGE: TrialSpec(60, 0, 5, 5, 0, 10, 20, 100, None, "before a judge"),
        TrialKind.JURY: TrialSpec(70, 1, 10, 8, 10, 0, 15, 90, None, "before a jury"),
        TrialKind.COMBAT: TrialSpec(20, 0, 0, 0, -10, 25, 0, 20, None, "by combat"),
        TrialKind.ORDEAL: TrialSpec(15, 0, 0, 0, -15, 25, 0, 20, None, "by ordeal"),
        TrialKind.COUNCIL: TrialSpec(65, 1, 10, 6, 5, 15, 15, 80, None, "before a council"),
        TrialKind.ARBITRATION: TrialSpec(60, 0, 5, 10, 20, 5, 5, 30, P.COMPENSATION, "by arbitration"),
        TrialKind.ORACLE: TrialSpec(30, 0, 5, 25, 0, 20, 0, 20, None, "by an oracle"),
        TrialKind.DIVINE_JUDGEMENT: TrialSpec(50, 0, 0, 10, 0, 25, 5, 5, None, "before a god"),
        TrialKind.ASSEMBLY: TrialSpec(45, 1, 5, 15, 10, 5, 5, 40, None, "before the assembled people"),
        TrialKind.INQUISITION: TrialSpec(25, 1, 15, 12, -25, 0, 25, 30, None, "by inquisition"),
        TrialKind.MEDIATION: TrialSpec(70, 1, 5, 8, 30, 5, 0, 15, P.RESTITUTION, "by mediation"),
        TrialKind.MADE_JUDGE: TrialSpec(80, 0, 20, 3, 0, -20, 25, 90, None, "before a made judge"),
    },
)

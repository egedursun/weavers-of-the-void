from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.military import DuelEnd
from aerona.domain.enums.mind import ActKind, EthicalStance, HonourModel
from aerona.domain.enums.mortal import CrimeKind

A = ActKind
S = EthicalStance

STANCE_ORDER: tuple[EthicalStance, ...] = (S.REQUIRED, S.ADMIRABLE, S.ACCEPTABLE, S.FROWNED_UPON, S.SHAMEFUL, S.UNTHINKABLE)

STANCE_LABELS: MappingProxyType[EthicalStance, str] = MappingProxyType(
    {
        S.REQUIRED: "Required",
        S.ADMIRABLE: "Admirable",
        S.ACCEPTABLE: "Acceptable",
        S.FROWNED_UPON: "Frowned upon",
        S.SHAMEFUL: "Shameful",
        S.UNTHINKABLE: "Unthinkable",
    }
)

STANCE_READINGS: MappingProxyType[EthicalStance, int] = MappingProxyType(
    {S.REQUIRED: 70, S.ADMIRABLE: 40, S.ACCEPTABLE: 0, S.FROWNED_UPON: -25, S.SHAMEFUL: -55, S.UNTHINKABLE: -85}
)

ACT_LABELS: Mapping[ActKind, str] = total(
    ActKind,
    {
        A.EXECUTION: "Execution",
        A.MUTILATION: "Mutilation as punishment",
        A.BETRAYAL: "Betrayal",
        A.MERCY_TO_ENEMY: "Mercy to an enemy",
        A.SACRIFICE_OF_PEOPLE: "Sacrifice of people",
        A.TRADE_WITH_OUTSIDERS: "Trade with outsiders",
        A.BUILDING_TEMPLES: "Building temples",
        A.BURNING_BOOKS: "Burning books",
        A.CONQUEST: "Conquest",
        A.RAIDING: "Raiding",
        A.DUELLING: "Duelling",
        A.RANSOM: "Ransoming captives",
        A.TAKING_CAPTIVES: "Taking captives",
        A.OATHBREAKING: "Breaking an oath",
        A.LEARNING: "Learning",
        A.HOSPITALITY: "Hospitality",
        A.WINTER_FIGHTING: "Fighting in winter",
        A.GUEST_KILLING: "Killing a guest",
        A.RITUAL_SCARRING: "Ritual scarring",
        A.KILLING_KIN: "Killing kin",
        A.KILLING_OUTSIDER: "Killing an outsider",
        A.KILLING_IN_WAR: "Killing in war",
        A.KILLING_CAPTIVE: "Killing a captive",
        A.REGICIDE: "Killing a ruler",
        A.DUEL_TO_DEATH: "A duel to the death",
        A.REVENGE_KILLING: "Killing for revenge",
        A.THEFT: "Theft",
        A.TREASON: "Treason",
        A.COWARDICE: "Cowardice",
        A.DESECRATION: "Desecration",
        A.BRIBERY: "Bribery",
        A.SUICIDE: "Taking one's own life",
        A.TORTURE: "Torture",
        A.EATING_SAPIENTS: "Eating thinking beings",
        A.ICONOCLASM: "Breaking images",
        A.CONVERSION_BY_FORCE: "Conversion by force",
        A.POLYGAMY: "Several spouses",
        A.INCEST: "Marrying close kin",
        A.MAGIC_USE: "Using magic",
        A.BLOOD_MAGIC: "Blood magic",
        A.VOID_MAGIC: "Void magic",
        A.NECROMANCY: "Necromancy",
        A.HOARDING_IN_FAMINE: "Hoarding in famine",
        A.SLAVERY: "Keeping slaves",
        A.ADULTERY: "Love outside a marriage",
        A.USURY: "Lending at interest",
        A.INFANTICIDE: "Killing an infant",
        A.ABANDONING_ELDERS: "Leaving the old to fend alone",
        A.FORCED_LABOUR: "Forcing folk to labour unpaid",
        A.SELLING_OFFICES: "Selling the offices of the realm",
        A.POACHING: "Poaching game reserved for another",
        A.ENCLOSING: "Enclosing the common land of the folk",
        A.LYING: "Lying",
        A.DRUNKENNESS: "Drunkenness",
        A.TOMB_ROBBING: "Robbing graves and hoards",
        A.USING_CHARMS: "Using charms",
        A.FEEDING_ON_HOSTS: "Feeding on a living host",
        A.KILLING_SACRED_ANIMAL: "Killing a sacred animal",
        A.FIXING_CONTESTS: "Fixing a contest",
        A.ABANDONING_THE_SICK: "Abandoning the sick",
        A.BREAKING_HOSPITALITY: "Breaking hospitality",
        A.CRUELTY_TO_ANIMALS: "Cruelty to animals",
        A.APOLOGISING: "Apologising",
        A.SHELTERING_STRANGERS: "Sheltering strangers",
        A.LAYING_CURSES: "Laying curses",
        A.ENHANCING_CONTESTANTS: "Enhancing contestants",
        A.POISON_WELLS: "Poisoning wells and water",
    },
)

CRIME_ACTS: MappingProxyType[CrimeKind, ActKind] = MappingProxyType(
    {
        CrimeKind.THEFT: A.THEFT,
        CrimeKind.BLASPHEMY: A.DESECRATION,
        CrimeKind.TREASON: A.TREASON,
        CrimeKind.MURDER: A.KILLING_OUTSIDER,
        CrimeKind.DESERTION: A.COWARDICE,
        CrimeKind.WITCHCRAFT: A.MAGIC_USE,
    }
)

ACT_CRIMES: MappingProxyType[ActKind, str] = MappingProxyType({act: crime.value for crime, act in CRIME_ACTS.items()})


@dataclass(frozen=True)
class HonourSpec:
    label: str
    insult_pct: int
    shame_spread_pct: int
    public_shame_pct: int
    guilt_pct: int
    law_pct: int
    oath_pct: int
    face_loss_pct: int = 100
    restores: bool = False
    grievance_kept_pct: int = 50
    message_sting_pct: int = 100
    herald_sting_pct: int = 100
    affairs_end_in_duels: bool = False
    duel_end: DuelEnd = DuelEnd.YIELD


HONOUR_MODELS: MappingProxyType[HonourModel, HonourSpec] = MappingProxyType(
    {
        HonourModel.DIGNITY: HonourSpec("Dignity: law over insult", 50, 0, 100, 100, 150, 60, duel_end=DuelEnd.FIRST_WOUND),
        HonourModel.HONOUR: HonourSpec(
            "Honour: a shame to one is a shame to the house",
            150,
            60,
            120,
            100,
            100,
            150,
            restores=True,
            message_sting_pct=200,
            herald_sting_pct=200,
            affairs_end_in_duels=True,
        ),
        HonourModel.FACE: HonourSpec(
            "Face: public shame weighs more than private guilt",
            100,
            30,
            160,
            50,
            100,
            120,
            face_loss_pct=200,
            restores=True,
            grievance_kept_pct=0,
            message_sting_pct=50,
            herald_sting_pct=200,
            duel_end=DuelEnd.RING_OUT,
        ),
        HonourModel.NONE: HonourSpec("None: neither word nor standing is weighed beyond the act", 0, 0, 0, 100, 150, 0),
        HonourModel.PURITY: HonourSpec(
            "Purity: one member's wrong counts against the whole group", 100, 80, 120, 150, 100, 130, restores=True, grievance_kept_pct=70
        ),
    }
)


DUEL_END_LABELS: Mapping[DuelEnd, str] = total(
    DuelEnd,
    {
        DuelEnd.YIELD: "When one yields",
        DuelEnd.DISARM: "When one is disarmed",
        DuelEnd.CRIPPLED: "When one is crippled",
        DuelEnd.DEATH: "To the death",
        DuelEnd.EXHAUSTION: "When both are spent",
        DuelEnd.UNCONSCIOUS: "When one falls senseless",
        DuelEnd.FIRST_WOUND: "At the first wound",
        DuelEnd.RING_OUT: "When one is driven out of the bounds",
        DuelEnd.STOPPED: "When an authority, a god or a crowd stops it",
    },
)

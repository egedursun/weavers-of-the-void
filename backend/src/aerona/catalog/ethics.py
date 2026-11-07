from dataclasses import dataclass
from types import MappingProxyType

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

ACT_LABELS: MappingProxyType[ActKind, str] = MappingProxyType(
    {
        A.EXECUTION: "Execution",
        A.MUTILATION: "Mutilation as punishment",
        A.BETRAYAL: "Betrayal",
        A.MERCY_TO_ENEMY: "Mercy to an enemy",
        A.HUMAN_SACRIFICE: "Human sacrifice",
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
    }
)

CRIME_ACTS: MappingProxyType[CrimeKind, ActKind] = MappingProxyType(
    {
        CrimeKind.THEFT: A.THEFT,
        CrimeKind.BLASPHEMY: A.DESECRATION,
        CrimeKind.TREASON: A.TREASON,
        CrimeKind.MURDER: A.KILLING_OUTSIDER,
        CrimeKind.DESERTION: A.COWARDICE,
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


HONOUR_MODELS: MappingProxyType[HonourModel, HonourSpec] = MappingProxyType(
    {
        HonourModel.DIGNITY: HonourSpec("Dignity: law over insult", 50, 0, 100, 100, 150),
        HonourModel.HONOUR: HonourSpec("Honour: a shame to one is a shame to the house", 150, 60, 120, 100, 100),
        HonourModel.FACE: HonourSpec("Face: public shame weighs more than private guilt", 100, 30, 160, 50, 100),
    }
)

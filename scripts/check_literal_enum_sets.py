import argparse
import ast
import builtins
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
MIGRATIONS = SOURCE / "db" / "alembic"
META_CATALOGUE = SOURCE / "catalog" / "kinds"


@dataclass(frozen=True)
class Family:
    name: str
    enums: tuple[str, ...]
    homes: tuple[str, ...]
    mapping_min: int


@dataclass(frozen=True)
class Literal:
    path: Path
    line: int
    family: str
    enum: str
    shape: str
    text: str


FAMILIES = (
    Family(
        "weather",
        ("WeatherKind",),
        ("catalog/weather.py",),
        1,
    ),
    Family(
        "terrain",
        ("TerrainKind",),
        ("catalog/terrain.py",),
        1,
    ),
    Family(
        "movement",
        ("MovementMode",),
        (
            "catalog/movement.py",
            "catalog/terrain.py",
            "engine/environment/profile.py",
        ),
        2,
    ),
    Family(
        "deep",
        (
            "RockKind",
            "UndergroundStratum",
            "SedimentKind",
            "CoastForm",
            "SealKind",
        ),
        ("catalog/",),
        2,
    ),
    Family(
        "catch",
        (
            "CatchGround",
            "Gear",
            "CentralityRank",
        ),
        ("catalog/",),
        2,
    ),
    Family(
        "species",
        (
            "Diet",
            "Sociality",
            "Biochemistry",
            "DomesticationStage",
            "SpeciesRole",
            "PlantForm",
            "PlantPart",
            "PlantProduct",
            "EvolvedTrait",
            "TrophicLevel",
            "KeystoneRole",
            "SenseKind",
            "Dormancy",
            "Thermoregulation",
            "PlantDefence",
            "CarrionRest",
        ),
        ("catalog/",),
        2,
    ),
    Family(
        "body",
        (
            "BodyPlan",
            "BodyPart",
            "DamageType",
            "InjuryKind",
            "InjuryState",
            "HarmCause",
            "ConditionKind",
            "MaimedKind",
            "TreatmentStep",
            "Capacity",
        ),
        ("catalog/",),
        2,
    ),
    Family(
        "life",
        (
            "AccountKind",
            "AccountMedium",
            "AccountStance",
            "AccusationOutcome",
            "ActKind",
            "AfterlifeModel",
            "AgeBand",
            "AgeCycle",
            "AgeGrade",
            "AgeKind",
            "AgentStatus",
            "AidKind",
            "AirNeed",
            "AllocationMode",
            "AnomalyKind",
            "AppealKind",
            "ArcRole",
            "ArcTemplate",
            "ArmyRole",
            "ArtMarketRole",
            "ArtMode",
            "AssistiveAid",
            "Atmosphere",
            "AttackDelivery",
            "AttackRange",
            "AugmentKind",
            "AugmentMake",
            "BargainGain",
            "BattlePhase",
            "BattlefieldFeature",
            "BeingAgenda",
            "BeingScale",
            "BeliefSource",
            "BeliefStance",
            "BindingKind",
            "BindingNeed",
            "BiologyVariant",
            "BirthComplication",
            "BloodlineRule",
            "BlueprintKind",
            "BlueprintSource",
            "BodyFunction",
            "BodySystem",
            "BreachCause",
            "BuilderKind",
            "BuildingForm",
            "CaptiveFate",
            "CaptiveStatus",
            "CareerPath",
            "CargoClass",
            "CarrierKind",
            "CasualtyFate",
            "CasusBelli",
            "ChallengeKind",
            "ChallengeResponse",
            "CharmPower",
            "CircleKind",
            "ClaimBasis",
            "ClaimKind",
            "ClaimStatus",
            "ClauseKind",
            "ClientRole",
            "ClimateEra",
            "ClockKind",
            "ClubKind",
            "CohortCondition",
            "CollectiveActKind",
            "CollectiveTrigger",
            "CommandArea",
            "CommandToken",
            "CommanderTrait",
            "CommonsKind",
            "CompanyCharter",
            "CompanyHoldingKind",
            "ConcealScope",
            "ConstructionState",
            "ContainerKind",
            "ContestKind",
            "ContestStake",
            "ContractStatus",
            "ConvoyStatus",
            "CookingMethod",
            "CoopPurpose",
            "CosmicFeatureKind",
            "CouncilMotion",
            "CouncilTask",
            "CourtLevel",
            "CourtPosition",
            "CreatorMoodAxis",
            "CreatorPassion",
            "CreatorSignKind",
            "CreatureDeed",
            "CreatureLesson",
            "CreditState",
            "CrewStation",
            "CrimeStance",
            "CrisisDemand",
            "CrisisState",
            "CrowdFeeling",
            "CultivationMethod",
            "CureKind",
            "Currency",
            "CurseKind",
            "DataContent",
            "DeathCause",
            "DeathRole",
            "DefenderAction",
            "DimensionElement",
            "DiseaseAgent",
            "DishCourse",
            "DispatchContent",
            "DispatchState",
            "DistrictKind",
            "DivinationKind",
            "DivinationQuestion",
            "DivineScale",
            "DivineWoundKind",
            "DreamKind",
            "DrinkCategory",
            "DuelContext",
            "DuelEnd",
            "DwellingKind",
            "Echelon",
            "EchelonOrder",
            "EffectTarget",
            "Emotion",
            "EndowmentPurpose",
            "EnvoyFate",
            "EraChannel",
            "EraDeed",
            "EstatePrivilege",
            "EvidenceKind",
            "ExcavationFind",
            "ExcavationRisk",
            "ExpeditionEvent",
            "ExpeditionGround",
            "ExpeditionRole",
            "ExtractionKind",
            "Facet",
            "FactionActionKind",
            "FactionGoalKind",
            "FactionKind",
            "FavourOrigin",
            "FermentKind",
            "Fertility",
            "FeudAction",
            "FeudStatus",
            "FieldAgreementKind",
            "ForesightSource",
            "ForgeryKind",
            "Formation",
            "FormativeKind",
            "FugitiveKind",
            "FuneralCustom",
            "FurnishingCategory",
            "GameCategory",
            "GardenKind",
            "GarmentCategory",
            "GatheringKind",
            "GeasLayer",
            "GeasMode",
            "GeniusLocusKind",
            "GiftOccasion",
            "GiftState",
            "GiftedAttitude",
            "GiftedStance",
            "GoodCategory",
            "Gravity",
            "GreatField",
            "GriefStage",
            "GroupKind",
            "HazardKind",
            "HeroquestBoon",
            "HiddenTruthKind",
            "HoardKind",
            "HoldingKind",
            "HonourModel",
            "HookDemand",
            "HookSource",
            "HostPlacement",
            "HouseDuty",
            "HouseholdForm",
            "HousingLevel",
            "HumourForm",
            "IdentityLayer",
            "IdentityReason",
            "ImpactBody",
            "ImpactOutcome",
            "IngredientRole",
            "InheritanceCustom",
            "InspirationKind",
            "InstructionBinding",
            "InstrumentCategory",
            "InstrumentKind",
            "InsuranceCover",
            "InteractionKind",
            "IntimacyStance",
            "Intoxicant",
            "IntoxicantUse",
            "IntrigueSecret",
            "IntrusionAim",
            "IntrusionOutcome",
            "IntrusionTarget",
            "Job",
            "JourneyIntent",
            "JudgementDoctrine",
            "KeeperResponse",
            "KeeperRole",
            "KinRole",
            "KinshipDescent",
            "KnowledgeBranch",
            "LabourReason",
            "LandAct",
            "LandUseRing",
            "LanguageModality",
            "LanguagePolicy",
            "LanguageStage",
            "LawArea",
            "LawScope",
            "LegitimacyType",
            "LeisureKind",
            "LifeEnvironment",
            "LifeStage",
            "LineOutcome",
            "LineTrait",
            "LinkToken",
            "LivingCraftStance",
            "LoanStatus",
            "LocalClimateCause",
            "LockKind",
            "Locus",
            "LongPlanKind",
            "LongSeasonReach",
            "LorePrice",
            "LuckReach",
            "LuckSign",
            "MadeMindStance",
            "MagicSiteKind",
            "MakingOutcome",
            "MandateKind",
            "Manifestation",
            "MantlingState",
            "MarkKind",
            "MarkMeaning",
            "MarketPlay",
            "MasteryKind",
            "MaterialOrigin",
            "MealSlot",
            "MediaItemKind",
            "MedicineTier",
            "Medium",
            "MemberRight",
            "Membership",
            "MemoryKind",
            "Metabolism",
            "MindPurpose",
            "MindUpkeep",
            "MishapAttribution",
            "MishapKind",
            "MishapResponse",
            "MobilityEvent",
            "MoneyForm",
            "MoodArousal",
            "MovementCause",
            "MutinyOutcome",
            "MysticState",
            "NameForm",
            "NamingPattern",
            "Naturalisation",
            "NavigationAid",
            "NeedGroup",
            "NeedKind",
            "NetworkCarrier",
            "NetworkRole",
            "Notation",
            "NumeralBase",
            "OathKind",
            "ObservationMethod",
            "OfficeDuty",
            "OfficeKind",
            "OfficePower",
            "OpinionSubject",
            "OrderCondition",
            "OrderKind",
            "OscillationPhase",
            "OutageCause",
            "OuterHunger",
            "PackageKind",
            "PackageVisibility",
            "PartyRole",
            "PassionKind",
            "PeaceTermKind",
            "PedagogyTheory",
            "PerennialKind",
            "PersonalityTrait",
            "PersuasionAim",
            "PetitionKind",
            "PhenomenonRhythm",
            "PieceKind",
            "PlanetaryCycle",
            "PlotKind",
            "PopulationInstrument",
            "PostnatalCustom",
            "PowerCost",
            "PowerDeviceEffect",
            "PowerHazard",
            "PowerOrigin",
            "PowerState",
            "PowerTrigger",
            "PrayerTone",
            "PrehistoryKind",
            "PreparednessKind",
            "PressureKind",
            "ProgrammeStage",
            "Propulsion",
            "PunishmentKind",
            "QuestTrial",
            "QuirkKind",
            "RacketKind",
            "RealmEntry",
            "RealmPurpose",
            "RebirthPath",
            "RebuildCause",
            "RebuildPlan",
            "RechargeRule",
            "RecordForm",
            "RecruitMotive",
            "RegionalStanding",
            "RegistryKind",
            "RelationContext",
            "RelationType",
            "RelicStance",
            "RelicState",
            "RelicUse",
            "ReliefKind",
            "ReplicatorOutput",
            "ReputationAxis",
            "ResearchIncident",
            "ResistanceKind",
            "ResolutionKind",
            "ResolveKind",
            "RestrictionKind",
            "RevivalGoal",
            "RevivalWay",
            "RiftCause",
            "RightAcquired",
            "RightKind",
            "RiteComponent",
            "RoomContentKind",
            "RouteState",
            "RumourDistortion",
            "SabotageKind",
            "SackChoice",
            "SacramentKind",
            "SacramentProtection",
            "SalienceDriver",
            "SanctuaryKind",
            "SatireSource",
            "SavingForm",
            "ScriptChangeCause",
            "SeasonOnset",
            "SeasonWater",
            "SeekerAim",
            "SenseShift",
            "ServitorOrigin",
            "ServitorRole",
            "SettleMode",
            "SetupKind",
            "ShortfallEffect",
            "ShotKind",
            "SiegeAction",
            "SiegeStatus",
            "SiegeWork",
            "SignCause",
            "SignalKind",
            "SignalState",
            "SiteChallenge",
            "SiteRoomKind",
            "SizeClass",
            "SkillKind",
            "SocializationTechnique",
            "SociolectKind",
            "SonPunishment",
            "SourceAccess",
            "SourceLawLevel",
            "SourceLocus",
            "SourceRenewal",
            "SpaceWeatherKind",
            "SpeciesClass",
            "SpeculationStatus",
            "SpeechVenue",
            "SpellDuration",
            "SpellForm",
            "SpellRange",
            "SpellTarget",
            "SpellTechnique",
            "SpiritOffence",
            "SpyOperation",
            "Stance",
            "StarvationStage",
            "StepLocus",
            "StepState",
            "StorytellerProfile",
            "StressBreak",
            "StructureSection",
            "SuccessionRule",
            "SurveillanceFocus",
            "SurveyLevel",
            "SymbiosisKind",
            "Tactic",
            "TaxKind",
            "TechFamily",
            "Technique",
            "TechnologyEra",
            "TerraformAim",
            "TheodicyCause",
            "TheoryDomain",
            "ThoughtKind",
            "TimeShare",
            "TissueMaterial",
            "TitleRank",
            "TitleTier",
            "TradeLoss",
            "TradeMode",
            "TradePolicyKind",
            "TradeRouteStatus",
            "TraditionFunction",
            "TraditionKind",
            "TransformTrigger",
            "TreatyKind",
            "TreatyStatus",
            "TruthAttitude",
            "UnitHonourKind",
            "UrbanService",
            "ValueAxis",
            "VehicleFamily",
            "VehicleKind",
            "VehicleSection",
            "VeteranGrant",
            "VisionKind",
            "WarAim",
            "WarCause",
            "WarEnding",
            "WarTerrain",
            "WaterLift",
            "WeatherEffect",
            "WeatherWorkMethod",
            "WillCause",
            "WitnessMode",
            "WordRegister",
            "WorksKind",
            "WorldEnd",
            "WorldEndCause",
            "WorldLight",
            "WorldType",
            "WorshipMode",
            "WoundCause",
            "WritingMedium",
            "YouthPurpose",
            "ZealKind",
            "ZoneKind",
        ),
        ("catalog/",),
        2,
    ),
    Family(
        "goods",
        (
            "MaterialKind",
            "MaterialOrigin",
            "CommodityKind",
            "WorkshopKind",
            "ProcessKind",
            "Pollutant",
            "ChemicalProduct",
        ),
        ("catalog/",),
        2,
    ),
)


def aliases_of(tree: ast.Module, owners: dict[str, str]) -> dict[str, str]:
    names = {enum: enum for enum in owners}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(
                {
                    alias.asname or alias.name: alias.name
                    for alias in node.names
                    if alias.name in owners
                }
            )
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Name)
            and node.value.id in names
        ):
            names.update(
                {
                    target.id: names[node.value.id]
                    for target in node.targets
                    if isinstance(target, ast.Name)
                }
            )
    return names


def unwrapped(item: ast.expr | None) -> ast.expr | None:
    if isinstance(item, ast.Attribute) and item.attr == "value" and isinstance(item.value, ast.Attribute):
        return item.value
    return item


def members(items: list[ast.expr | None], names: dict[str, str]) -> Counter[str]:
    return Counter(
        names[item.value.id]
        for item in map(unwrapped, items)
        if isinstance(item, ast.Attribute)
        and isinstance(item.value, ast.Name)
        and item.value.id in names
        and item.attr.isupper()
    )


def module_names(tree: ast.Module) -> set[str]:
    found: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import | ast.ImportFrom):
            found.update(
                (alias.asname or alias.name).split(".")[0] for alias in node.names
            )
        elif isinstance(node, ast.Assign):
            found.update(
                target.id for target in node.targets if isinstance(target, ast.Name)
            )
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            found.add(node.target.id)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            found.add(node.name)
    return found


def computed(value: ast.expr, known: set[str]) -> bool:
    bound = {
        arg.arg
        for node in ast.walk(value)
        if isinstance(node, ast.Lambda)
        for arg in node.args.args
    }
    bound |= {
        name.id
        for node in ast.walk(value)
        if isinstance(node, ast.comprehension)
        for name in ast.walk(node.target)
        if isinstance(name, ast.Name)
    }
    return any(
        isinstance(node, ast.Name)
        and node.id not in known
        and node.id not in bound
        and not hasattr(builtins, node.id)
        for node in ast.walk(value)
    )


CATALOGUE_CALLS = frozenset({"total", "partial"})


def functions_of(tree: ast.Module) -> set[str]:
    found = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    found |= {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if (alias.asname or alias.name)[0].islower()
    }
    return found


def handler(value: ast.expr, functions: set[str]) -> bool:
    if isinstance(value, ast.Tuple) and value.elts:
        return handler(value.elts[0], functions)
    if isinstance(value, ast.Lambda):
        return True
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
        return value.func.id in functions
    return isinstance(value, ast.Name) and value.id in functions


def catalogued(tree: ast.Module) -> set[int]:
    found: set[int] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in CATALOGUE_CALLS
        ):
            for part in [*node.args[1:], *(word.value for word in node.keywords)]:
                found.update(id(inner) for inner in ast.walk(part))
    return found


def at_home(relative: str, family: Family) -> bool:
    return any(
        relative == home or (home.endswith("/") and relative.startswith(home))
        for home in family.homes
    )


def literals_in(
    relative: str, text: str, families: tuple[Family, ...]
) -> list[Literal]:
    owners = {enum: family for family in families for enum in family.enums}
    tree = ast.parse(text)
    names = aliases_of(tree, {enum: family.name for enum, family in owners.items()})
    known = module_names(tree)
    functions = functions_of(tree)
    tables = catalogued(tree)
    found: list[Literal] = []
    for node in ast.walk(tree):
        counted: Counter[str] = Counter()
        shape = ""
        if isinstance(node, ast.Set | ast.List | ast.Tuple) and id(node) not in tables:
            counted, shape = members(list(node.elts), names), "collection"
        elif (
            isinstance(node, ast.Dict)
            and id(node) not in tables
            and not all(
                handler(value, functions)
                for key, value in zip(node.keys, node.values, strict=True)
                if key is not None
            )
            and not any(computed(value, known) for value in node.values)
        ):
            counted, shape = members(list(node.keys), names), "mapping"
        for enum, count in counted.items():
            family = owners[enum]
            least = family.mapping_min if shape == "mapping" else 2
            if count >= least and not at_home(relative, family):
                found.append(
                    Literal(
                        Path(relative),
                        node.lineno,
                        family.name,
                        enum,
                        shape,
                        ast.unparse(node)[:140],
                    )
                )
    return found


def literal_sets(families: tuple[Family, ...]) -> list[Literal]:
    words = {enum for family in families for enum in family.enums}
    found: list[Literal] = []
    for path in sorted(SOURCE.rglob("*.py")):
        if path.is_relative_to(MIGRATIONS) or path.is_relative_to(META_CATALOGUE):
            continue
        text = path.read_text(encoding="utf-8")
        if any(word in text for word in words):
            found.extend(literals_in(str(path.relative_to(SOURCE)), text, families))
    return sorted(set(found), key=lambda item: (item.family, str(item.path), item.line))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--family")
    parser.add_argument("--summary", action="store_true")
    options = parser.parse_args(argv)
    families = tuple(
        family for family in FAMILIES if options.family in (None, family.name)
    )
    found = literal_sets(families)
    if options.summary:
        for name, count in sorted(Counter(item.family for item in found).items()):
            print(f"{name}: {count}")
    else:
        for item in found:
            print(
                f"backend/src/aerona/{item.path}:{item.line}: a {item.shape} of {item.enum} members outside the {item.family} catalogues: "
                f"{item.text}; read a field or trait of the catalogue instead"
            )
    print(f"literal enum sets outside their catalogues: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.arts import ArtMarketRole, ClubKind, ForgeryKind
from aerona.domain.enums.crafts import RightAcquired
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.mortal import CrimeKind
from aerona.rules.registry import Rules

A = ArtMarketRole
F = ForgeryKind
W = RightAcquired
K = ClubKind


@dataclass(frozen=True)
class RoleSpec:
    label: str
    keeps: bool
    judges: bool
    fakes: bool


ROLES: Mapping[ArtMarketRole, RoleSpec] = total(
    ArtMarketRole,
    {
        A.COLLECTOR: RoleSpec("Collector", keeps=True, judges=False, fakes=False),
        A.DEALER: RoleSpec("Dealer", keeps=False, judges=False, fakes=False),
        A.PATRON: RoleSpec("Patron", keeps=True, judges=False, fakes=False),
        A.CONNOISSEUR: RoleSpec("Connoisseur", keeps=True, judges=True, fakes=False),
        A.CURATOR: RoleSpec("Curator", keeps=True, judges=True, fakes=False),
        A.CRITIC: RoleSpec("Critic", keeps=False, judges=True, fakes=False),
        A.FORGER: RoleSpec("Forger", keeps=False, judges=False, fakes=True),
    },
)
JUDGES = frozenset(role for role, spec in ROLES.items() if spec.judges)


@dataclass(frozen=True)
class ForgerySpec:
    label: str
    crime: CrimeKind
    detect: Callable[[Rules], int]
    expert: SkillKind | None
    against: str = "work"


FORGERIES: Mapping[ForgeryKind, ForgerySpec] = total(
    ForgeryKind,
    {
        F.ARTWORK: ForgerySpec("A forged work of art", CrimeKind.FRAUD, lambda rules: rules.forgery.artwork_detect_pct, None),
        F.RELIC: ForgerySpec("A forged relic", CrimeKind.SACRILEGE, lambda rules: rules.forgery.relic_detect_pct, SkillKind.THEOLOGY),
        F.DOCUMENT: ForgerySpec("A forged document", CrimeKind.FRAUD, lambda rules: rules.forgery.document_detect_pct, SkillKind.LAW),
        F.BRAND: ForgerySpec("Goods under a false mark", CrimeKind.UNLICENSED_COPYING, lambda rules: rules.forgery.brand_detect_pct, None),
        F.COIN: ForgerySpec("False coin", CrimeKind.COUNTERFEITING, lambda rules: rules.forgery.coin_detect_pct, SkillKind.SMITHING, against="realm"),
        F.LINEAGE: ForgerySpec("A forged lineage", CrimeKind.FORGED_LINE, lambda rules: rules.forgery.lineage_detect_pct, SkillKind.LORE, against="title"),
        F.SEAL: ForgerySpec("A forged seal", CrimeKind.IMPERSONATION, lambda rules: rules.forgery.seal_detect_pct, SkillKind.LAW, against="realm"),
    },
)
FORGERY_CRIMES = frozenset(spec.crime for spec in FORGERIES.values())


@dataclass(frozen=True)
class WaySpec:
    label: str
    needs_contest: bool
    needs_union: bool


WAYS: Mapping[RightAcquired, WaySpec] = total(
    RightAcquired,
    {
        W.CREATED: WaySpec("Made", needs_contest=False, needs_union=False),
        W.INHERITED: WaySpec("Inherited", needs_contest=False, needs_union=False),
        W.BOUGHT: WaySpec("Bought", needs_contest=False, needs_union=False),
        W.LICENSED: WaySpec("Licensed", needs_contest=False, needs_union=False),
        W.STOLEN: WaySpec("Stolen", needs_contest=False, needs_union=False),
        W.GRANTED: WaySpec("Granted", needs_contest=False, needs_union=False),
        W.WON: WaySpec("Won in a contest", needs_contest=True, needs_union=False),
        W.WED: WaySpec("Passed with a union", needs_contest=False, needs_union=True),
    },
)


@dataclass(frozen=True)
class ClubSpec:
    label: str
    fan_draw: Callable[[Rules], int]
    keeps_animals: bool
    trains_minds: bool


CLUBS: Mapping[ClubKind, ClubSpec] = total(
    ClubKind,
    {
        K.TEAM_GAME: ClubSpec("Team game", lambda rules: rules.clubs.team_game_fan_draw, keeps_animals=False, trains_minds=False),
        K.RACING: ClubSpec("Racing", lambda rules: rules.clubs.racing_fan_draw, keeps_animals=False, trains_minds=False),
        K.COMBAT: ClubSpec("Combat", lambda rules: rules.clubs.combat_fan_draw, keeps_animals=False, trains_minds=False),
        K.ATHLETICS: ClubSpec("Athletics", lambda rules: rules.clubs.athletics_fan_draw, keeps_animals=False, trains_minds=False),
        K.ANIMAL_CONTEST: ClubSpec("Animal contests", lambda rules: rules.clubs.animal_contest_fan_draw, keeps_animals=True, trains_minds=False),
        K.MIND_GAMES: ClubSpec("Games of the mind", lambda rules: rules.clubs.mind_games_fan_draw, keeps_animals=False, trains_minds=True),
    },
)
ANIMAL_CLUBS = frozenset(kind for kind, spec in CLUBS.items() if spec.keeps_animals)
MIND_CLUBS = frozenset(kind for kind, spec in CLUBS.items() if spec.trains_minds)

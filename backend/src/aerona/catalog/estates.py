from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.faction import EstatePrivilege, MovementCause
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import SocialClass

ESTATE_CLASSES: tuple[SocialClass, ...] = (
    SocialClass.NOBLE,
    SocialClass.PRIEST,
    SocialClass.MERCHANT,
    SocialClass.ARTISAN,
    SocialClass.FARMER,
    SocialClass.WARRIOR,
)
ESTATE_NAMES = total(
    SocialClass,
    {
        SocialClass.NOBLE: "Nobility",
        SocialClass.PRIEST: "Clergy",
        SocialClass.MERCHANT: "Merchants",
        SocialClass.ARTISAN: "Craftsfolk",
        SocialClass.FARMER: "Farmers",
        SocialClass.WARRIOR: "Warrior Estate",
        SocialClass.SCRIBE: "Clerks",
        SocialClass.SERF_OR_SLAVE: "Bonded Folk",
        SocialClass.OUTCAST: "Outcasts",
        SocialClass.MONASTIC: "Cloistered",
        SocialClass.WORKER: "Workers",
        SocialClass.PROFESSIONAL: "Professions",
        SocialClass.OFFICIAL: "Officialdom",
        SocialClass.CITIZEN: "Citizenry",
        SocialClass.UNEMPLOYED: "Workless",
    },
)
PRIVILEGE_WISHES = total(
    SocialClass,
    {
        SocialClass.NOBLE: (EstatePrivilege.TAX_EXEMPTION, EstatePrivilege.JUDICIAL_IMMUNITY, EstatePrivilege.COUNCIL_SEAT, EstatePrivilege.ARMS),
        SocialClass.PRIEST: (EstatePrivilege.JUDICIAL_IMMUNITY, EstatePrivilege.TAX_EXEMPTION, EstatePrivilege.COUNCIL_SEAT),
        SocialClass.MERCHANT: (EstatePrivilege.MONOPOLY, EstatePrivilege.COUNCIL_SEAT, EstatePrivilege.TAX_EXEMPTION),
        SocialClass.ARTISAN: (EstatePrivilege.MONOPOLY, EstatePrivilege.COUNCIL_SEAT),
        SocialClass.FARMER: (EstatePrivilege.COUNCIL_SEAT, EstatePrivilege.ARMS),
        SocialClass.WARRIOR: (EstatePrivilege.ARMS, EstatePrivilege.TAX_EXEMPTION, EstatePrivilege.COUNCIL_SEAT),
        SocialClass.SCRIBE: (EstatePrivilege.COUNCIL_SEAT, EstatePrivilege.TAX_EXEMPTION),
        SocialClass.SERF_OR_SLAVE: (EstatePrivilege.COUNCIL_SEAT, EstatePrivilege.ARMS),
        SocialClass.OUTCAST: (EstatePrivilege.COUNCIL_SEAT, EstatePrivilege.JUDICIAL_IMMUNITY),
        SocialClass.MONASTIC: (EstatePrivilege.TAX_EXEMPTION, EstatePrivilege.JUDICIAL_IMMUNITY),
        SocialClass.WORKER: (EstatePrivilege.COUNCIL_SEAT, EstatePrivilege.MONOPOLY),
        SocialClass.PROFESSIONAL: (EstatePrivilege.MONOPOLY, EstatePrivilege.COUNCIL_SEAT),
        SocialClass.OFFICIAL: (EstatePrivilege.JUDICIAL_IMMUNITY, EstatePrivilege.COUNCIL_SEAT, EstatePrivilege.TAX_EXEMPTION),
        SocialClass.CITIZEN: (EstatePrivilege.COUNCIL_SEAT, EstatePrivilege.ARMS),
        SocialClass.UNEMPLOYED: (EstatePrivilege.COUNCIL_SEAT,),
    },
)
ESTATE_LAWS: Mapping[SocialClass, tuple[LawKind, dict[str, int | str | bool]]] = total(
    SocialClass,
    {
        SocialClass.NOBLE: (LawKind.SERFDOM, {"allowed": True}),
        SocialClass.PRIEST: (LawKind.TITHE, {"rate": 10, "enforced": True}),
        SocialClass.MERCHANT: (LawKind.TOLLS, {"rate": 0}),
        SocialClass.ARTISAN: (LawKind.GUILD_CHARTER, {}),
        SocialClass.FARMER: (LawKind.TAX_RATE, {"rate": 5}),
        SocialClass.WARRIOR: (LawKind.VETERAN_PENSION, {}),
        SocialClass.SCRIBE: (LawKind.CENSORSHIP, {"strictness": 0}),
        SocialClass.SERF_OR_SLAVE: (LawKind.SERFDOM, {"allowed": False}),
        SocialClass.OUTCAST: (LawKind.FRANCHISE, {"voters": "all"}),
        SocialClass.MONASTIC: (LawKind.RELIGIOUS_TOLERANCE, {"level": "free"}),
        SocialClass.WORKER: (LawKind.LABOUR_LAW, {"max_hours": 48, "child_labour": False, "unions": True}),
        SocialClass.PROFESSIONAL: (LawKind.FAIR_MARKET, {"strength": 70}),
        SocialClass.OFFICIAL: (LawKind.TAX_RATE, {"rate": 15}),
        SocialClass.CITIZEN: (LawKind.FRANCHISE, {"voters": "citizens"}),
        SocialClass.UNEMPLOYED: (LawKind.LABOUR_LAW, {"max_hours": 40, "child_labour": False, "unions": True}),
    },
)
PRIVILEGE_LABELS: dict[EstatePrivilege, str] = {
    EstatePrivilege.TAX_EXEMPTION: "Freedom from taxes",
    EstatePrivilege.MONOPOLY: "A monopoly",
    EstatePrivilege.COUNCIL_SEAT: "A seat in council",
    EstatePrivilege.ARMS: "The right to bear arms",
    EstatePrivilege.JUDICIAL_IMMUNITY: "Immunity from the courts",
}
CAUSE_LABELS: dict[MovementCause, str] = {
    MovementCause.ABOLITION: "Abolition of slavery",
    MovementCause.INDEPENDENCE: "Independence",
    MovementCause.REVIVAL: "A revival of faith",
    MovementCause.LAND_REFORM: "Land reform",
    MovementCause.FRANCHISE: "A wider franchise",
    MovementCause.PEACE: "Peace",
    MovementCause.CONSERVATION: "Protection of the wild",
}

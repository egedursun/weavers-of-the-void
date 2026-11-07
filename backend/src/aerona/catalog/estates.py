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
ESTATE_NAMES: dict[SocialClass, str] = {
    SocialClass.NOBLE: "Nobility",
    SocialClass.PRIEST: "Clergy",
    SocialClass.MERCHANT: "Burghers",
    SocialClass.ARTISAN: "Craftsfolk",
    SocialClass.FARMER: "Peasantry",
    SocialClass.WARRIOR: "Warrior Estate",
}
PRIVILEGE_WISHES: dict[SocialClass, tuple[EstatePrivilege, ...]] = {
    SocialClass.NOBLE: (EstatePrivilege.TAX_EXEMPTION, EstatePrivilege.JUDICIAL_IMMUNITY, EstatePrivilege.COUNCIL_SEAT, EstatePrivilege.ARMS),
    SocialClass.PRIEST: (EstatePrivilege.JUDICIAL_IMMUNITY, EstatePrivilege.TAX_EXEMPTION, EstatePrivilege.COUNCIL_SEAT),
    SocialClass.MERCHANT: (EstatePrivilege.MONOPOLY, EstatePrivilege.COUNCIL_SEAT, EstatePrivilege.TAX_EXEMPTION),
    SocialClass.ARTISAN: (EstatePrivilege.MONOPOLY, EstatePrivilege.COUNCIL_SEAT),
    SocialClass.FARMER: (EstatePrivilege.COUNCIL_SEAT, EstatePrivilege.ARMS),
    SocialClass.WARRIOR: (EstatePrivilege.ARMS, EstatePrivilege.TAX_EXEMPTION, EstatePrivilege.COUNCIL_SEAT),
}
ESTATE_LAWS: dict[SocialClass, tuple[LawKind, dict[str, int | str | bool]]] = {
    SocialClass.NOBLE: (LawKind.SERFDOM, {"allowed": True}),
    SocialClass.PRIEST: (LawKind.TITHE, {"rate": 10, "enforced": True}),
    SocialClass.MERCHANT: (LawKind.TOLLS, {"rate": 0}),
    SocialClass.ARTISAN: (LawKind.GUILD_CHARTER, {}),
    SocialClass.FARMER: (LawKind.TAX_RATE, {"rate": 5}),
    SocialClass.WARRIOR: (LawKind.VETERAN_PENSION, {}),
}
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
}

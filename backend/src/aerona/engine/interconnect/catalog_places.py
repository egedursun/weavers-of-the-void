from aerona.catalog.place_terrain import PLACE_KINDS
from aerona.core.grammar import an, spoken
from aerona.db.tables.place import PlaceProfileRow, PlaceSecretRow
from aerona.domain.enums.place import SacredClass, SecretKind
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

PLACE_SECTION = "section-place"
S = Subsystem
PLACE = ("place",)
SACRED_RULES: dict[SacredClass, str] = {
    SacredClass.HOLY: "places.sacred_holy_base",
    SacredClass.NOTABLE: "places.sacred_notable_base",
    SacredClass.PROFANE: "places.sacred_profane_base",
}
SECRET_CARRIERS: dict[SecretKind, tuple[Subsystem, str]] = {
    SecretKind.HIDDEN_RESOURCE: (S.ECONOMY, "a found seam becomes a resource and a mineral layer of the region"),
    SecretKind.BURIED_RELIC: (S.CULTURE, "a dug relic becomes an item, sometimes cursed"),
    SecretKind.SEALED_SPIRIT: (S.FAITH, "a broken seal frees a spirit and haunts the region"),
    SecretKind.LOST_KNOWLEDGE: (S.KNOWLEDGE, "found lore is taught to the finder's people"),
    SecretKind.LOST_RITE: (S.MAGIC, "a found rite is devised or learned by the finder"),
    SecretKind.UNDERWORLD_ENTRANCE: (S.COSMOS, "a way down links the place to the underworld; opened, it haunts and deepens the place"),
    SecretKind.HIDDEN_PEOPLE: (S.SOCIAL, "a found people comes into the knowledge of the finder"),
    SecretKind.DORMANT_MIND: (S.MIND, "a found mind wakes steadier"),
    SecretKind.SEALED_REALM: (S.COSMOS, "a found realm is unsealed"),
}

PLACE_MECHANICS = (
    Mechanic(
        key="place_profiles",
        spec_item="S6.2",
        title="Place kinds, sacredness and pilgrims; valleys and crossroads worn into battlefields",
        subsystem=S.ENVIRONMENT,
        phases=("environment_survey", "place_profiles"),
        surface=Surface(drawer=PLACE_SECTION),
        backfill="places.kind_backfill: every existing place gets a typed kind read once from its recorded subtype; untouched ground takes the kind's profile",
        templates=("place.became_battlefield", "tools.son.sanctify_place", "tools.son.raise_nexus"),
        fields=("piety", "prosperity", "mystery"),
        tables=(PlaceProfileRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("sanctify_place", "raise_nexus", "create_place"),
        targets=("place", "settlement", "people"),
        couplings=(
            Coupling(S.FAITH, "sacred places draw pilgrims and count as holy sites of cults and pilgrimage duties", EdgeKind.MODIFIER, "places.pilgrim_piety"),
            Coupling(S.ECONOMY, "pilgrims bring prosperity to the community at the place", EdgeKind.MODIFIER, "places.pilgrim_prosperity"),
            Coupling(
                S.WAR, "the kind sets cover, height, water and chokepoint; repeated battles make a battlefield", EdgeKind.TRIGGER, "places.battlefield_battles"
            ),
        ),
    ),
    Mechanic(
        key="place_secrets",
        spec_item="S6.2",
        title="Place secrets: hidden seams, relics, sealed spirits, lost lore and rites, ways below; found by explorers, seers, miners and solved mysteries",
        subsystem=S.ENVIRONMENT,
        phases=("place_profiles", "place_secrets", "living_stats"),
        surface=Surface(drawer=PLACE_SECTION),
        backfill="place_profiles: every place not yet seeded rolls once for a secret by its mystery and kind on the first run",
        templates=("place.secret_", "place.secret_released", "place.secret_opened", "tools.son.hide_secret"),
        fields=("mystery", "danger"),
        tables=(PlaceSecretRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("hide_secret",),
        targets=PLACE,
        couplings=(
            Coupling(S.KNOWLEDGE, "explorers, seers and solved mysteries reveal secrets", EdgeKind.TRIGGER, "places.discover_skill_pct"),
            Coupling(S.ECONOMY, "deep mining strikes secrets and breaks seals", EdgeKind.TRIGGER, "places.miner_pct"),
            Coupling(S.FAITH, "released spirits haunt the region", EdgeKind.FLOW, "places.haunted_depth"),
        ),
    ),
    Mechanic(
        key="battle_sites",
        spec_item="S6.2",
        title="Chokepoints and passes draw battles; cover shelters defenders from missiles and hides ambushes",
        subsystem=S.WAR,
        phases=("campaigns",),
        surface=Surface(drawer=PLACE_SECTION),
        backfill="none: battles already fought keep their ground; sites are chosen from the next campaign season",
        fields=("cover", "chokepoint", "height_advantage"),
        targets=PLACE,
        couplings=(
            Coupling(
                S.WAR, "a campaign season's battle may be drawn to a chokepoint of the defender's region", EdgeKind.TRIGGER, "places.chokepoint_battle_pct"
            ),
            Coupling(S.WAR, "heavy cover cuts missile harm on defenders and opens ambushes", EdgeKind.MODIFIER, "places.cover_missile_heavy_pct"),
        ),
    ),
)


def kind_behaviours() -> tuple[Mechanic, ...]:
    return tuple(
        Mechanic(
            key=f"place_kind_{kind.value}",
            spec_item="S6.2",
            title=f"{spec.label}: {spoken(spec.cover)} cover, {spoken(spec.water)} water, {spoken(spec.height)} ground"
            + (", a chokepoint" if spec.chokepoint else "")
            + f", {spoken(spec.sacred)} sanctity"
            + (", deep enough for miners" if spec.deep else ""),
            subsystem=S.ENVIRONMENT,
            phases=("environment_survey", "place_profiles", "place_secrets"),
            surface=Surface(drawer=PLACE_SECTION),
            backfill="none: the kind acts from the next epoch",
            fields=("kind",),
            targets=PLACE,
            couplings=(Coupling(S.FAITH, f"the sanctity {an(spec.label.lower())} tends toward", EdgeKind.MODIFIER, SACRED_RULES[spec.sacred]),),
        )
        for kind, spec in PLACE_KINDS.items()
    )


def secret_behaviours() -> tuple[Mechanic, ...]:
    return tuple(
        Mechanic(
            key=f"place_secret_{kind.value}",
            spec_item="S6.2",
            title=f"Secret: {kind.value.replace('_', ' ')}",
            subsystem=S.ENVIRONMENT,
            phases=("place_secrets",),
            surface=Surface(drawer=PLACE_SECTION),
            backfill="none: the secret acts when found",
            fields=("kind",),
            targets=PLACE,
            couplings=(Coupling(subsystem, carrier, EdgeKind.TRIGGER),),
        )
        for kind, (subsystem, carrier) in SECRET_CARRIERS.items()
    )


PLACE_BEHAVIOURS = (*kind_behaviours(), *secret_behaviours())

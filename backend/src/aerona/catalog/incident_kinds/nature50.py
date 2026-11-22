from aerona.catalog.incident_kinds.record_builders import amount, chosen, happening, maybe, named, one, some
from aerona.catalog.incident_kinds.spec import IncidentKindSpec
from aerona.domain.enums.body_systems import BodySystem, Sensitivity
from aerona.domain.enums.chronicle import ChronicleKind as K
from aerona.domain.enums.chronicle import FeedCategory as F
from aerona.domain.enums.disease_agents import CureClass, DiseaseAgent
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.forecasting import ObservationMethod, WeatherAim, WeatherWorkMethod
from aerona.domain.enums.fossil import Preservation
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.modifier import IncidentRole as R
from aerona.domain.enums.node import NodeKind as N
from aerona.domain.enums.records import FactUnit as U
from aerona.domain.enums.records import PlaceRule as P
from aerona.domain.enums.records import ProcessClock as C
from aerona.domain.enums.records import ProcessGroup as G
from aerona.domain.enums.records import StepAction as A

SPACE_WEATHER_TEMPLATES: dict[str, str] = {
    "particle_storm": "A storm of particles from its star reached {subject}, at strength {strength}; {dose} of it came through to the ground.",
    "field_storm": "A storm shook the magnetic field of {subject}, at strength {strength}; {dose} of it came through to the ground.",
    "field_reversal": "The magnetic field of {subject} turned over; while it turns its shield is weaker, and {dose} came through to the ground.",
    "cosmic_ray_burst": "A burst of rays from far away reached {subject}, at strength {strength}; {dose} of it came through to the ground.",
    "wind_surge": "The wind of its star surged against {subject}, at strength {strength}; {dose} of it came through to the ground.",
}

LAND_STEPS: dict[str, A] = {
    "ice_closed": A.FREEZE,
    "ice_opened": A.EASE,
    "ice_road": A.FREEZE,
    "thaw_collapse": A.COLLAPSE,
    "thaw_release": A.REVEAL,
    "snow_drought": A.DRY,
    "silted": A.CLOSE,
    "coast_lost": A.FLOOD_LAND,
    "delta_grew": A.SPREAD,
    "glacier_advanced": A.FREEZE,
    "glacier_retreated": A.WANE,
}
LAND_TEMPLATES: dict[str, tuple[str, str, U]] = {
    "ice_closed": ("Ice closed the waters of {place}, for {months:month|months} of the year.", "months", U.COUNT),
    "ice_opened": ("The ice gave up the waters of {place}; it holds only {months:month|months} of the year now.", "months", U.COUNT),
    "ice_road": ("The ice over {place} grew thick enough to walk on, for {months:month|months} of the year.", "months", U.COUNT),
    "thaw_collapse": ("The frozen ground of {place} thawed by {fall} and the works on it gave way.", "fall", U.PERCENT),
    "thaw_release": ("The thaw of {place} gave up what the ice had kept, a bed of remains of richness {richness}.", "richness", U.PERCENT),
    "snow_drought": ("Little snow lay on {place}, only {snowpack} of it, and the lands below went dry in summer.", "snowpack", U.PERCENT),
    "silted": ("Sediment filled the harbour of {place} until ships could no longer come in.", "silting", U.PERCENT),
    "coast_lost": ("The sea took the fields of {place}, and its towns lost {loss} of their prosperity.", "loss", U.PERCENT),
    "delta_grew": ("The delta of {place} grew out into the water, and its soil rose to {fertility}.", "fertility", U.PERCENT),
    "glacier_advanced": ("The glacier of {place} advanced, covering {extent} of the land.", "extent", U.PERCENT),
    "glacier_retreated": ("The glacier of {place} drew back, covering {extent} of the land.", "extent", U.PERCENT),
}

DREDGED = happening(
    "land.dredged",
    G.NATURE,
    "{actor} paid {cost} to dredge the harbour of {place}, and its silting fell to {silting}.",
    roles=(one(R.ACTOR), one(R.PLACE)),
    facts=(amount("cost", U.COIN), amount("silting", U.PERCENT)),
    steps=(A.OPEN,),
    place=P.REQUIRED,
    clock=C.SEASON,
    kind=K.CLIMATE,
    direct=True,
)

LAND: tuple[IncidentKindSpec, ...] = tuple(
    happening(
        f"land.{key}",
        G.NATURE,
        template,
        roles=(one(R.PLACE),),
        facts=(amount(fact, unit),),
        steps=(LAND_STEPS[key],),
        place=P.REQUIRED,
        clock=C.SEASON,
        kind=K.CLIMATE,
    )
    for key, (template, fact, unit) in LAND_TEMPLATES.items()
)

DISEASE: tuple[IncidentKindSpec, ...] = (
    happening(
        "disease.resistance_rose",
        G.NATURE,
        "{subject} grew used to the {cure} cure that was used too often against it; its resistance rose to {resistance}.",
        roles=(one(R.SUBJECT),),
        facts=(chosen("cure", CureClass), amount("resistance", U.PERCENT)),
        steps=(A.WORSEN,),
        place=P.NONE,
        clock=C.SEASON,
        kind=K.DISASTER,
    ),
    happening(
        "disease.wrong_cure",
        G.NATURE,
        "{actor} treated {subject} with the {cure} cure, which does nothing against a sickness that is {agent:an}.",
        roles=(one(R.SUBJECT), one(R.ACTOR)),
        facts=(chosen("cure", CureClass), chosen("agent", DiseaseAgent)),
        steps=(A.TREAT,),
        place=P.WHEN_KNOWN,
        clock=C.SEASON,
        kind=K.DISASTER,
    ),
    happening(
        "disease.right_cure",
        G.NATURE,
        "{actor} treated {subject} with the {cure} cure, which works on it; its outbreak eased to {severity}.",
        roles=(one(R.SUBJECT), one(R.ACTOR)),
        facts=(chosen("cure", CureClass), amount("severity", U.PERCENT)),
        steps=(A.TREAT, A.EASE),
        place=P.WHEN_KNOWN,
        clock=C.SEASON,
        kind=K.DISASTER,
    ),
    happening(
        "disease.reservoir_found",
        G.NATURE,
        "{subject} lives on in the beasts of {place} between its outbreaks, at a load of {load}.",
        roles=(one(R.SUBJECT), one(R.PLACE)),
        facts=(amount("load", U.PERCENT),),
        steps=(A.DISCOVER,),
        place=P.REQUIRED,
        clock=C.SEASON,
        kind=K.DISASTER,
    ),
    happening(
        "disease.agent_identified",
        G.NATURE,
        "The healers of {actor} learned what {subject} is: {agent:an}.",
        roles=(one(R.SUBJECT), one(R.ACTOR)),
        facts=(chosen("agent", DiseaseAgent),),
        steps=(A.DISCOVER,),
        place=P.NONE,
        clock=C.SEASON,
        kind=K.DISASTER,
    ),
)

BODY_TEMPLATES: dict[str, tuple[str, A]] = {
    "tolerance_exceeded": ("The world of {place} weighs on the {system} of {subject} past what it bears, by {excess}.", A.WORSEN),
    "system_failed": ("The {system} of {subject} gave way in {place}, strained past bearing by {excess}.", A.COLLAPSE_BODY),
    "system_recovered": ("The {system} of {subject} came back in {place} once the strain eased.", A.RECOVER),
    "adapted": ("The {system} of {subject} grew used to the world of {place}.", A.EASE),
}

BODY: tuple[IncidentKindSpec, ...] = (
    *(
        happening(
            f"body.{key}",
            G.BODY,
            template,
            roles=(one(R.SUBJECT), one(R.PLACE)),
            facts=(chosen("system", BodySystem), amount("excess", U.PERCENT)),
            steps=(step,),
            place=P.REQUIRED,
            clock=C.SEASON,
            kind=K.LINEAGE,
        )
        for key, (template, step) in BODY_TEMPLATES.items()
    ),
    happening(
        "body.sensitivity_reaction",
        G.BODY,
        "{subject} met what its body cannot bear ({sensitivity}) and fell ill, at a severity of {severity}.",
        roles=(one(R.SUBJECT),),
        facts=(chosen("sensitivity", Sensitivity), amount("severity", U.PERCENT)),
        steps=(A.FALL_ILL,),
        place=P.WHEN_KNOWN,
        clock=C.SEASON,
        kind=K.LINEAGE,
    ),
)

PLANTS: tuple[IncidentKindSpec, ...] = (
    happening(
        "life.plant_spread",
        G.NATURE,
        "{subject} took root in {place}, carried there by wind or beast, at an abundance of {abundance}.",
        roles=(one(R.SUBJECT), one(R.PLACE)),
        facts=(amount("abundance", U.PERCENT),),
        steps=(A.SPREAD,),
        place=P.REQUIRED,
        clock=C.SEASON,
        kind=K.WORLD,
    ),
    happening(
        "life.plant_invaded",
        G.NATURE,
        "{subject} crowded the other {kinds:kind|kinds} of life in {place}.",
        roles=(one(R.SUBJECT), one(R.PLACE)),
        facts=(amount("kinds", U.COUNT),),
        steps=(A.SPREAD,),
        place=P.REQUIRED,
        clock=C.SEASON,
        kind=K.WORLD,
    ),
    happening(
        "life.plant_domesticated",
        G.NATURE,
        "{subject} grows on {share} of the fields of a land and is tamed.",
        roles=(one(R.SUBJECT),),
        facts=(amount("share", U.PERCENT),),
        steps=(A.SETTLE,),
        place=P.NONE,
        clock=C.SEASON,
        kind=K.DOMESTICATION,
    ),
)

FOSSILS: tuple[IncidentKindSpec, ...] = (
    happening(
        "land.fossil_read",
        G.KNOWLEDGE,
        "{actor} studied a bed of remains in {place}, kept in {preservation} at a richness of {richness}, as the record of deep time.",
        roles=(one(R.ACTOR), one(R.PLACE)),
        facts=(chosen("preservation", Preservation), amount("richness", U.PERCENT)),
        steps=(A.EXAMINE,),
        place=P.REQUIRED,
        clock=C.SEASON,
        kind=K.KNOWLEDGE,
    ),
    happening(
        "land.fossil_traded",
        G.EXCHANGE,
        "{actor} took {units} of remains from a bed in {place} to trade as luxuries.",
        roles=(one(R.ACTOR), one(R.PLACE)),
        facts=(amount("units", U.COUNT),),
        steps=(A.GATHER,),
        place=P.REQUIRED,
        clock=C.SEASON,
        kind=K.TRADE,
    ),
    happening(
        "life.revived",
        G.NATURE,
        "{actor} raised {subject} again from its remains in {place}, a bed of richness {richness}.",
        roles=(one(R.ACTOR), one(R.SUBJECT), one(R.PLACE)),
        facts=(amount("richness", U.PERCENT),),
        steps=(A.RETURN_TO_LIFE,),
        place=P.REQUIRED,
        clock=C.SEASON,
        kind=K.CREATION,
        direct=True,
    ),
)

FORECASTS: dict[str, tuple[str, A]] = {
    "forecast_kept": ("{subject} foresaw the hard season by {method}, at an accuracy of {accuracy}, and made ready.", A.FORESEE),
    "forecast_failed": ("{subject} did not see the hard season coming; its {method} reads the weather at an accuracy of only {accuracy}.", A.LOSE_WAY),
    "forecast_ignored": ("{subject} was told of the hard season by {method}, at an accuracy of {accuracy}, and did not believe it.", A.DENY),
}

WEATHER: tuple[IncidentKindSpec, ...] = (
    *(
        happening(
            f"weather.{key}",
            G.NATURE,
            template,
            roles=(one(R.SUBJECT),),
            facts=(chosen("method", ObservationMethod), amount("accuracy", U.PERCENT)),
            steps=(step,),
            place=P.NONE,
            clock=C.SEASON,
            kind=K.CLIMATE,
        )
        for key, (template, step) in FORECASTS.items()
    ),
    happening(
        "tools.mortal.forecast",
        G.NATURE,
        "{actor} read the weather of {place} by {method}, at an accuracy of {accuracy}, and foresaw {told}.",
        roles=(one(R.ACTOR), one(R.PLACE)),
        facts=(chosen("method", ObservationMethod), amount("accuracy", U.PERCENT), named("told")),
        steps=(A.FORESEE,),
        place=P.REQUIRED,
        clock=C.INSTANT,
        kind=K.CLIMATE,
    ),
    happening(
        "tools.mortal.work_weather",
        G.NATURE,
        "{actor} set to work the weather of {place} toward {aim}, at a strength of {strength}, for {cost} coin.",
        roles=(one(R.ACTOR), one(R.PLACE)),
        facts=(chosen("aim", WeatherAim), amount("strength", U.PERCENT), amount("cost", U.COIN)),
        steps=(A.PERFORM_RITE,),
        place=P.REQUIRED,
        clock=C.INSTANT,
        kind=K.CLIMATE,
        direct=True,
    ),
    happening(
        "weather.work_raised",
        G.NATURE,
        "{actor} began to work the weather of {place} toward {aim} by {method}, at a strength of {strength}.",
        roles=(one(R.ACTOR), one(R.PLACE)),
        facts=(chosen("aim", WeatherAim), chosen("method", WeatherWorkMethod), amount("strength", U.PERCENT)),
        steps=(A.PERFORM_RITE,),
        place=P.REQUIRED,
        clock=C.SEASON,
        kind=K.CLIMATE,
    ),
    happening(
        "weather.worked",
        G.NATURE,
        "{actor} worked the weather of {place} toward {aim}, at a strength of {strength}.",
        roles=(one(R.ACTOR), one(R.PLACE)),
        facts=(chosen("aim", WeatherAim), amount("strength", U.PERCENT)),
        steps=(A.PERFORM_RITE,),
        place=P.REQUIRED,
        clock=C.SEASON,
        kind=K.CLIMATE,
    ),
    happening(
        "weather.side_effect",
        G.NATURE,
        "The weather worked by {actor} turned {place}, downwind, toward {aim}, at a strength of {strength}.",
        roles=(one(R.ACTOR), one(R.PLACE)),
        facts=(chosen("aim", WeatherAim), amount("strength", U.PERCENT)),
        steps=(A.BLOW,),
        place=P.REQUIRED,
        clock=C.SEASON,
        kind=K.CLIMATE,
    ),
    happening(
        "weather.work_banned",
        G.NATURE,
        "{actor}, harmed downwind, made {target} stop working the weather of {place}; their relation stands at {relation}.",
        roles=(one(R.ACTOR), one(R.TARGET), one(R.PLACE)),
        facts=(amount("relation", U.COUNT),),
        steps=(A.REFUSE,),
        place=P.REQUIRED,
        clock=C.SEASON,
        kind=K.CLIMATE,
    ),
)

STANDING: tuple[IncidentKindSpec, ...] = (
    happening(
        "standing.hypocrisy_exposed",
        G.SOCIAL,
        "It came out that {subject} professes {axis} and acts against it, by a gap of {gap} over {acts:deed|deeds}.",
        roles=(one(R.SUBJECT), maybe(R.ACTOR)),
        facts=(chosen("axis", ValueAxis), amount("gap", U.PERCENT), amount("acts", U.COUNT)),
        steps=(A.REVEAL, A.SHAME),
        place=P.NONE,
        clock=C.SEASON,
        kind=K.INTRIGUE,
    ),
    happening(
        "standing.hypocrisy_forgiven",
        G.SOCIAL,
        "The gap between what {subject} professes of {axis} and what it does closed to {gap}, and the world forgave it.",
        roles=(one(R.SUBJECT),),
        facts=(chosen("axis", ValueAxis), amount("gap", U.PERCENT)),
        steps=(A.RECONCILE,),
        place=P.NONE,
        clock=C.SEASON,
        kind=K.INTRIGUE,
    ),
    happening(
        "tools.mortal.expose_hypocrisy",
        G.SOCIAL,
        "{actor} showed that {target} professes {axis} and acts against it, by a gap of {gap}.",
        roles=(one(R.ACTOR), one(R.TARGET)),
        facts=(chosen("axis", ValueAxis), amount("gap", U.PERCENT)),
        steps=(A.REVEAL,),
        place=P.NONE,
        clock=C.INSTANT,
        kind=K.INTRIGUE,
        direct=True,
    ),
)

KINDS: tuple[IncidentKindSpec, ...] = (
    *STANDING,
    *WEATHER,
    *FOSSILS,
    *PLANTS,
    *BODY,
    *DISEASE,
    DREDGED,
    *LAND,
    *(
        happening(
            f"sky.{key}",
            G.COSMOS,
            template,
            roles=(one(R.SUBJECT, N.WORLD),),
            facts=(amount("strength", U.PERCENT), amount("dose", U.PERCENT)),
            steps=(A.APPEAR,),
            place=P.NONE,
            clock=C.SEASON,
            kind=K.SKY,
            feed=F.SKY,
        )
        for key, template in SPACE_WEATHER_TEMPLATES.items()
    ),
    happening(
        "sky.outage",
        G.COSMOS,
        "The storm from the sky silenced the signals of {subject}: {networks:network|networks} went down under a dose of {dose}.",
        roles=(one(R.SUBJECT, N.WORLD), some(R.VICTIM, required=False)),
        facts=(amount("dose", U.PERCENT), amount("networks", U.COUNT)),
        steps=(A.END,),
        place=P.NONE,
        clock=C.SEASON,
        kind=K.SKY,
        feed=F.SKY,
    ),
    happening(
        "sky.aurora_spread",
        G.COSMOS,
        "Lights in the sky spread far over {subject}, reaching {reach} of the way from its poles to its middle.",
        roles=(one(R.SUBJECT, N.WORLD),),
        facts=(amount("reach", U.PERCENT),),
        steps=(A.APPEAR,),
        place=P.NONE,
        clock=C.SEASON,
        kind=K.SKY,
        feed=F.SKY,
    ),
    happening(
        "media.market_alarmed",
        G.EXCHANGE,
        "News from {outlet} sent the folk of {place} to hoard {commodity}, at strength {strength}.",
        roles=(one(R.PLACE),),
        facts=(named("outlet"), chosen("commodity", CommodityKind), amount("strength", U.PERCENT)),
        steps=(A.RISE,),
        place=P.REQUIRED,
        clock=C.SEASON,
        kind=K.TRADE,
    ),
    happening(
        "daily.help_taken",
        G.SOCIAL,
        "The household of {actor} took on help, its housework grown to {load} of 100.",
        roles=(one(R.ACTOR),),
        facts=(amount("load", U.PERCENT),),
        steps=(A.HIRE,),
        place=P.WHEN_KNOWN,
        clock=C.SEASON,
        kind=K.CIVILIZATION,
    ),
    happening(
        "tools.son.move_ice",
        G.GODS,
        "{actor} moved the ice of {place} by {change:month|months} a year: {reason}",
        roles=(one(R.ACTOR), one(R.PLACE)),
        facts=(amount("change", U.COUNT), named("reason", required=False)),
        place=P.REQUIRED,
        clock=C.INSTANT,
        kind=K.CLIMATE,
        direct=True,
    ),
    happening(
        "tools.son.shield_world",
        G.GODS,
        "{actor} changed the magnetic field of {subject} by {change} for {epochs:epoch|epochs}: {reason}",
        roles=(one(R.ACTOR), one(R.SUBJECT, N.WORLD), maybe(R.PLACE)),
        facts=(amount("change", U.PERCENT), amount("epochs", U.COUNT), named("reason", required=False)),
        place=P.NONE,
        clock=C.INSTANT,
        kind=K.COSMIC,
        direct=True,
    ),
)

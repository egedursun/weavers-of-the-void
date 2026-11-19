from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.intimacy.norms import NormTally, keep_norms, lover_pairs
from aerona.engine.intimacy.restraint import RestraintTally, break_vows, vow_customs
from aerona.engine.intimacy.seed import seed_intimacy
from aerona.engine.phase import Phase


@reads(
    "table.bonds",
    "table.culture_ethics",
    "table.culture_values",
    "table.entities",
    "table.intimacy_norms",
    "table.kin_group_members",
    "table.kin_role_duties",
    "table.legitimacy_rules",
    "table.marriages",
    "table.mind_profiles",
    "table.mortal_profiles",
    "table.nodes",
    "table.oaths",
    "table.people_reproduction",
    "table.polity_members",
    "table.relationships",
    "table.reproductive_courses",
    "table.restraint_customs",
    "table.war_sides",
    "table.wars",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.intimacy_norms",
    "table.legitimacy_rules",
    "table.mortal_profiles",
    "table.oaths",
    "table.relationships",
    "table.reproductive_courses",
    "table.secrets",
)
async def unions_and_birth(ctx: TickContext) -> None:
    seeded = await seed_intimacy(ctx)
    ctx.count("intimacy_seeded_norms", seeded.norms)
    ctx.count("intimacy_seeded_courses", seeded.courses)
    ctx.count("intimacy_seeded_legitimacy", seeded.legitimacy)
    pairs = await lover_pairs(ctx)
    restraint = RestraintTally()
    await vow_customs(ctx, restraint)
    await break_vows(ctx, pairs, restraint)
    ctx.count("restraint_vowed", restraint.vowed)
    ctx.count("restraint_broken", restraint.broken)
    norms = NormTally()
    await keep_norms(ctx, norms)
    ctx.count("union_scandals", norms.scandals)
    ctx.count("union_sanctions", norms.sanctions)
    ctx.count("union_flights", norms.fled)
    ctx.count("union_hidden", norms.hidden)
    ctx.count("union_norms_changed", norms.changed)


PHASES = (Phase("unions_and_birth", unions_and_birth),)

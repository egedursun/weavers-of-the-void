from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.youth.groups import keep_youth
from aerona.engine.youth.seed import seed_youth


@reads(
    "mortal.age",
    "settlement.prosperity",
    "table.age_set_members",
    "table.age_sets",
    "table.bonds",
    "table.child_standing",
    "table.culture_values",
    "table.districts",
    "table.entities",
    "table.faction_memberships",
    "table.faction_profiles",
    "table.mortal_profiles",
    "table.nodes",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.settlement_profiles",
    "table.turf",
    "table.youth_group_members",
    "table.youth_groups",
    "table.youth_standing",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.faction_memberships",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.personality_values",
    "table.settlement_profiles",
    "table.youth_group_members",
    "table.youth_groups",
    "table.youth_standing",
)
async def youth(ctx: TickContext) -> None:
    seeded = await seed_youth(ctx)
    ctx.count("youth_seeded_standing", seeded.standing)
    ctx.count("youth_seeded_groups", seeded.groups)
    tally = await keep_youth(ctx)
    ctx.count("youth_formed", tally.formed)
    ctx.count("youth_joined", tally.joined)
    ctx.count("youth_came_of_age", tally.came_of_age)
    ctx.count("youth_delinquent", tally.delinquent)
    ctx.count("youth_recruited", tally.recruited)
    ctx.count("youth_coopted", tally.coopted)
    ctx.count("youth_disbanded", tally.disbanded)


PHASES = (Phase("youth", youth),)

from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.leagues import LeagueMemberRow, PolityLeagueRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.leagues import LeagueAim, LeagueOrgan, LeagueStanding, LeagueVoteBasis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.entity_stats import LeagueStats
from aerona.engine.context import TickContext
from aerona.engine.leagues.book import LeagueTally, membership
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.recording.record import record

COUNCIL_AT = 5
ORGANS_OF_AIMS = total(
    LeagueAim,
    {
        LeagueAim.DEFENCE: LeagueOrgan.FORCE,
        LeagueAim.TRADE: LeagueOrgan.SECRETARIAT,
        LeagueAim.CUSTOMS_UNION: LeagueOrgan.SECRETARIAT,
        LeagueAim.CURRENCY_UNION: LeagueOrgan.SECRETARIAT,
        LeagueAim.LAW: LeagueOrgan.COURT,
        LeagueAim.FAITH: LeagueOrgan.COUNCIL,
        LeagueAim.PEACE: LeagueOrgan.COURT,
        LeagueAim.RESEARCH: LeagueOrgan.SECRETARIAT,
        LeagueAim.MIGRATION: LeagueOrgan.SECRETARIAT,
    },
)


def organs_for(aims: list[LeagueAim], members: int) -> list[str]:
    organs = {LeagueOrgan.ASSEMBLY, *(ORGANS_OF_AIMS[aim] for aim in aims)}
    if members >= COUNCIL_AT:
        organs.add(LeagueOrgan.COUNCIL)
    return sorted(organ.value for organ in organs)


async def join(ctx: TickContext, league: EntityRow, polity: EntityRow, standing: LeagueStanding, *, veto: bool = False) -> LeagueMemberRow:
    found = await membership(ctx.session, league.id, polity.id)
    if found is not None:
        found.standing = standing
        return found
    member = LeagueMemberRow(league_entity_id=league.id, polity_entity_id=polity.id, standing=standing, veto=veto, joined_epoch=ctx.epoch, locked=[])
    ctx.session.add(member)
    await ctx.session.flush()
    return member


async def found_league(
    ctx: TickContext, polities: list[EntityRow], aims: list[LeagueAim], vote_basis: LeagueVoteBasis, tally: LeagueTally, *, seat: int | None = None
) -> EntityRow:
    first = polities[0]
    league = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.LEAGUE,
            name=f"the league of {first.name.removeprefix('the ')}",
            body=f"A league of {', '.join(polity.name for polity in polities)}.",
            stats=LeagueStats(strength=ctx.rules.leagues.strength_per_member * len(polities), cohesion=50, members=len(polities)),
            power=max(polity.power_level for polity in polities),
            world_id=first.world_id,
            subtype="league",
            pending=False,
        ),
    )
    ctx.session.add(
        PolityLeagueRow(
            league_entity_id=league.id,
            aims=sorted({aim.value for aim in aims}),
            seat_entity_id=seat,
            dues_pct=ctx.rules.leagues.dues_pct,
            vote_basis=vote_basis,
            organs=organs_for(aims, len(polities)),
            common_tariff_pct=ctx.rules.leagues.common_tariff_pct if LeagueAim.CUSTOMS_UNION in aims else 0,
            founded_epoch=ctx.epoch,
            locked=[],
        )
    )
    for index, polity in enumerate(polities):
        await join(ctx, league, polity, LeagueStanding.FOUNDER, veto=vote_basis is LeagueVoteBasis.BY_VETO_HOLDERS and index == 0)
    tally.founded += 1
    await record(
        ctx,
        "league.founded",
        roles={IncidentRole.PRODUCT: league.id, IncidentRole.MEMBER: [polity.id for polity in polities]},
        facts={"aims": ", ".join(aim.value.replace("_", " ") for aim in aims), "basis": vote_basis},
    )
    return league

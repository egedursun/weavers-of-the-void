from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.speech_shapes import HUMOUR_BITE_PCT
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.media import MediaOutletRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.speech import HumourStyleRow, SpeechRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.folk_knowledge import FolkDomain
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.speech import HumourForm, SpeechAim, SpeechVenue
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import realm_of
from aerona.engine.folk_knowledge.factor import folk_factor
from aerona.engine.mortal.kin import children_of, parents_of
from aerona.engine.polity.laws import ruling_law
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term
from aerona.engine.sacred.places import ruler_of

TEN = 10
CROWD_VENUES = frozenset({SpeechVenue.SQUARE, SpeechVenue.CAMP, SpeechVenue.OUTLET})
RAISING = frozenset({SpeechAim.RALLY, SpeechAim.DEFEND, SpeechAim.PERSUADE, SpeechAim.TEACH, SpeechAim.MOURN})
GOD_KINDS = frozenset({EntityType.CULT})


@dataclass
class SpeechTally:
    heard: int = 0
    votes: int = 0
    crowds: int = 0
    offended: int = 0
    punished: int = 0
    satire: int = 0
    rallied: int = 0


def skill_of(speaker: EntityRow) -> int:
    return clamp_int(stat_or(speaker, "charisma", PERCENT // 2), 0, PERCENT)


async def style_for(session: AsyncSession, place: EntityRow) -> HumourStyleRow | None:
    folk = await people_of(session, place)
    return await session.get(HumourStyleRow, folk.id) if folk is not None else None


async def mockable(session: AsyncSession, style: HumourStyleRow | None, speaker: EntityRow, target: EntityRow | None, place_id: int) -> tuple[bool, bool]:
    if target is None:
        return True, False
    realm = await realm_of(session, place_id)
    is_ruler = realm is not None and await ruler_of(session, realm) == target.id
    if style is None:
        return not is_ruler, is_ruler
    if is_ruler:
        return style.mock_rulers, True
    if target.entity_type in GOD_KINDS:
        return style.mock_gods, False
    if target.id in {*await parents_of(session, speaker.id), *await children_of(session, speaker.id)}:
        return style.mock_kin, False
    return style.mock_strangers, False


async def lose_honour(ctx: TickContext, being_id: int, amount: int, key: str) -> None:
    profile = await ctx.session.get(MortalProfileRow, being_id)
    if profile is None or held(being_id) or "honour" in (profile.locked or []):
        return
    with explaining():
        term(key, -amount, source_node_id=being_id)
        profile.honour = clamp_int(profile.honour - amount, 0, PERCENT)


async def shift_realm(ctx: TickContext, place_id: int, amount: int, source: int) -> bool:
    realm = await realm_of(ctx.session, place_id)
    profile = await ctx.session.get(PolityProfileRow, realm) if realm is not None else None
    if profile is None or realm is None or held(realm) or "legitimacy" in (profile.locked or []) or not amount:
        return False
    with explaining():
        term("speech.persuasion_pct", amount, source_node_id=source)
        profile.legitimacy = clamp_int(profile.legitimacy + amount, 0, PERCENT)
    return True


async def stir_town(ctx: TickContext, place_id: int, amount: int, source: int) -> bool:
    profile = await ctx.session.get(SettlementProfileRow, place_id)
    if profile is None or held(place_id) or "unrest" in (profile.locked or []) or not amount:
        return False
    with explaining():
        term("speech.persuasion_pct", amount, source_node_id=source)
        profile.unrest = clamp_int(profile.unrest + amount, 0, PERCENT)
    return True


async def mock(ctx: TickContext, speech: SpeechRow, speaker: EntityRow, place: EntityRow, *, power: int, tally: SpeechTally) -> int:
    table = ctx.rules.speech
    target = await ctx.session.get(EntityRow, speech.audience_node_id) if speech.audience_node_id is not None else None
    style = await style_for(ctx.session, place)
    allowed, at_ruler = await mockable(ctx.session, style, speaker, target, place.id)
    threshold = style.offence_threshold if style is not None else table.offence_threshold
    if allowed or power < threshold // TEN:
        if target is not None:
            bite = HUMOUR_BITE_PCT[style.form] if style is not None else PERCENT
            await lose_honour(ctx, target.id, round_half_up(power * bite / PERCENT), "speech.persuasion_pct")
        gain = round_half_up(table.humour_ease_pct * power / TEN)
        await lose_honour(ctx, speaker.id, -gain, "speech.humour_ease_pct")
        if at_ruler:
            await shift_realm(ctx, place.id, -power, speaker.id)
        return -power
    if at_ruler and await ruling_law(ctx.session, place.id, LawKind.CENSORSHIP) is not None:
        await lose_honour(ctx, speaker.id, table.punishment_honour, "speech.punishment_honour")
        await record(ctx, "speech.satire_punished", roles={IncidentRole.ACTOR: speaker.id, IncidentRole.PLACE: place.id}, facts={"venue": speech.venue})
        tally.punished += 1
        return 0
    await lose_honour(ctx, speaker.id, power, "speech.offence_threshold")
    await record(
        ctx,
        "speech.offence_taken",
        roles={IncidentRole.ACTOR: speaker.id, IncidentRole.PLACE: place.id, **({IncidentRole.TARGET: target.id} if target is not None else {})},
        facts={"venue": speech.venue},
    )
    tally.offended += 1
    return 0


async def hear(ctx: TickContext, speech: SpeechRow, tally: SpeechTally) -> None:
    speaker = await ctx.session.get(EntityRow, speech.speaker_node_id)
    place = await ctx.session.get(EntityRow, speech.place_entity_id)
    speech.heard = True
    if speaker is None or place is None:
        return
    lore = await folk_factor(ctx.session, ctx.rules, speaker, FolkDomain.SOCIETY if speech.venue is SpeechVenue.ASSEMBLY else FolkDomain.MIND)
    power = round_half_up(ctx.rules.speech.persuasion_pct * speech.skill / PERCENT * speech.reach / PERCENT * lore)
    effect = 0
    if speech.aim is SpeechAim.MOCK:
        effect = await mock(ctx, speech, speaker, place, power=power, tally=tally)
    elif speech.venue is SpeechVenue.ASSEMBLY:
        effect = power if speech.aim in RAISING else -power
        if await shift_realm(ctx, place.id, effect, speaker.id):
            await record(
                ctx, "speech.moved_vote", roles={IncidentRole.ACTOR: speaker.id, IncidentRole.PLACE: place.id}, facts={"aim": speech.aim, "effect": effect}
            )
            tally.votes += 1
    elif speech.venue in CROWD_VENUES:
        effect = power if speech.aim in {SpeechAim.RALLY, SpeechAim.ACCUSE} else -power
        if await stir_town(ctx, place.id, effect if speech.aim is SpeechAim.ACCUSE else -effect, speaker.id):
            await record(
                ctx, "speech.moved_crowd", roles={IncidentRole.ACTOR: speaker.id, IncidentRole.PLACE: place.id}, facts={"aim": speech.aim, "effect": effect}
            )
            tally.crowds += 1
    elif speech.venue is SpeechVenue.TEMPLE and not held(place.id):
        effect = power
        with explaining():
            term("speech.persuasion_pct", power / TEN, source_node_id=speaker.id)
            shift_stat(place, "piety", power / TEN, low=0, high=PERCENT)
    else:
        effect = power
        await lose_honour(ctx, speaker.id, -round_half_up(power / 2), "speech.persuasion_pct")
    if "effect" not in (speech.locked or []):
        speech.effect = clamp_int(effect, -PERCENT, PERCENT)
    tally.heard += 1


async def satire_of_rulers(ctx: TickContext, tally: SpeechTally) -> None:
    loss = ctx.rules.speech.satire_legitimacy_loss
    seats = await ctx.session.scalars(select(MediaOutletRow.seat_entity_id).order_by(MediaOutletRow.seat_entity_id).distinct())
    for seat_id in list(seats):
        place = await ctx.session.get(EntityRow, seat_id)
        style = await style_for(ctx.session, place) if place is not None else None
        if style is None or style.form is not HumourForm.SATIRE or not style.mock_rulers:
            continue
        if await shift_realm(ctx, seat_id, -loss, seat_id):
            tally.satire += 1


async def rulers_rally(ctx: TickContext, tally: SpeechTally) -> None:
    table = ctx.rules.speech
    for profile in list(
        await ctx.session.scalars(
            select(SettlementProfileRow).where(SettlementProfileRow.unrest >= table.restless_at).order_by(SettlementProfileRow.settlement_entity_id)
        )
    ):
        realm = await realm_of(ctx.session, profile.settlement_entity_id)
        ruler_id = await ruler_of(ctx.session, realm) if realm is not None else None
        ruler = await ctx.session.get(EntityRow, ruler_id) if ruler_id is not None else None
        if ruler is None or held(ruler.id) or held(profile.settlement_entity_id):
            continue
        if not ctx.rng(f"ruler_speech.{ruler.id}.{profile.settlement_entity_id}.{ctx.epoch}").chance(table.ruler_speech_pct):
            continue
        ctx.session.add(
            SpeechRow(
                speaker_node_id=ruler.id,
                place_entity_id=profile.settlement_entity_id,
                venue=SpeechVenue.SQUARE,
                aim=SpeechAim.RALLY,
                skill=skill_of(ruler),
                reach=PERCENT // 2,
                epoch=ctx.epoch,
                locked=[],
            )
        )
        await record(
            ctx,
            "speech.given",
            roles={IncidentRole.ACTOR: ruler.id, IncidentRole.PLACE: profile.settlement_entity_id},
            facts={"venue": SpeechVenue.SQUARE, "aim": SpeechAim.RALLY},
        )
        tally.rallied += 1
    await ctx.session.flush()


async def keep_speech(ctx: TickContext) -> SpeechTally:
    tally = SpeechTally()
    await rulers_rally(ctx, tally)
    for speech in list(await ctx.session.scalars(select(SpeechRow).where(SpeechRow.heard.is_(False)).order_by(SpeechRow.id))):
        if not held(speech.speaker_node_id) and not held(speech.place_entity_id):
            await hear(ctx, speech, tally)
    await satire_of_rulers(ctx, tally)
    await ctx.session.flush()
    return tally

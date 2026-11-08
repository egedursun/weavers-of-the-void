from aerona.db.tables.body import InjuryRow, ProsthesisRow
from aerona.domain.enums.body import DamageType, HarmCause, InjuryKind, InjuryState
from aerona.domain.enums.material import MaterialKind
from aerona.engine.body.book import ensure_body
from aerona.engine.body.describe import body_lines
from tests.engine.society.factories import Realm, context, mortal


async def test_a_lost_limb_shows_the_prosthesis_its_bearer_wears(realm: Realm) -> None:
    ctx = context(realm.session)
    veteran = await mortal(realm, "Brann")
    await ensure_body(realm.session, ctx.rules, veteran, ctx.epoch)
    lost = InjuryRow(
        bearer_node_id=veteran.id,
        part="left_arm",
        kind=InjuryKind.SEVERED,
        damage_type=next(iter(DamageType)),
        severity=5,
        state=InjuryState.PERMANENT,
        function_loss=100,
        cause_kind=HarmCause.BATTLE,
        epoch=ctx.epoch,
    )
    realm.session.add(lost)
    await realm.session.flush()
    bare = await body_lines(realm.session, ctx.rules, veteran)
    assert any(line.startswith("Missing: ") and "lost" in line and "wears" not in line for line in bare)
    material = next(iter(MaterialKind))
    realm.session.add(
        ProsthesisRow(bearer_node_id=veteran.id, injury_id=lost.id, part=lost.part, material=material, quality=60, restored_pct=40, epoch=ctx.epoch)
    )
    await realm.session.flush()
    fitted = await body_lines(realm.session, ctx.rules, veteran)
    assert any(line.startswith("Missing: ") and f"{material.value.replace('_', ' ')} one)" in line for line in fitted)

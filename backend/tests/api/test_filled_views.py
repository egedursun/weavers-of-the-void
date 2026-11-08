from aerona.db.tables.intrigue import TrueNameRow
from aerona.domain.enums.communication import DispatchContent, Medium
from aerona.domain.enums.culture import CustomCatalog
from aerona.domain.enums.intrigue import FavourOrigin, HookSource, IntrigueSecret, PlotKind
from aerona.domain.enums.mortal import CrimeKind
from aerona.engine.communication.post import send
from aerona.engine.intrigue.favours import owe
from aerona.engine.intrigue.schemes import begin_scheme
from aerona.engine.intrigue.secrets import grant_hook, keep_secret
from aerona.engine.lore.control import create_lore
from aerona.engine.polity.trials import report_crime
from aerona.engine.primitives.manual import manual_context
from tests.api.conftest import ApiWorld, seeded
from tests.engine.core.factories import mortal, settlement
from tests.engine.lore.test_every_lore_kind import FIRST_VALUES


async def test_intrigue_correspondence_and_justice_views_read_filled_records(api: ApiWorld) -> None:
    core = seeded(api).core
    async with api.services.database.write() as session:
        ctx = await manual_context(session, "views", api.services.rules.current)
        plotter = await mortal(session, "Plotter", core, core.regions[0].id)
        mark = await mortal(session, "Mark", core, core.regions[0].id)
        secret = await keep_secret(ctx, mark.id, IntrigueSecret.AFFAIR, about_id=plotter.id, known_by=(plotter.id,), source="test")
        await grant_hook(ctx, plotter.id, mark.id, HookSource.SECRET, strong=True, secret_id=secret.id if secret else None)
        await owe(ctx, mark.id, plotter.id, FavourOrigin.GIFT, 10)
        await begin_scheme(ctx, plotter, PlotKind.SWAY, mark)
        session.add(TrueNameRow(bearer_node_id=mark.id, name="Ithar", known_by=[plotter.id], since_epoch=1, locked=[]))
        await send(ctx, core.people.id, core.son.id, DispatchContent.PLEA, Medium.LETTER)
        town = await settlement(session, "Lawford", core, core.regions[0], population=8000)
        await report_crime(ctx, town.id, mark.id, CrimeKind.THEFT)
        plotter_id, mark_id = plotter.id, mark.id
    for node in (plotter_id, mark_id):
        view = await api.http.get(f"/api/intrigue/{node}")
        assert view.status_code == 200, view.text
    body = (await api.http.get(f"/api/intrigue/{mark_id}")).json()
    assert body["secrets"] and body["hooks_on"] and body["favours_owed"] and body["schemes_against"]
    letters = await api.http.get(f"/api/correspondence/{core.people.id}")
    assert letters.status_code == 200, letters.text
    assert letters.json()["sent"]
    assert (await api.http.get(f"/api/justice/{mark_id}")).status_code == 200


async def test_every_kind_of_lore_card_reads_a_record_a_god_made(api: ApiWorld) -> None:
    core = seeded(api).core
    made: list[int] = []
    async with api.services.database.write() as session:
        ctx = await manual_context(session, "lore", api.services.rules.current)
        for kind, values in FIRST_VALUES.items():
            entity = await create_lore(
                ctx, kind, name=f"Card {kind.value}", description="", world_id=core.world.id, location_id=core.regions[0].id, power=3, values=dict(values)
            )
            made.append(entity.id)
    for entity_id in made:
        card = await api.http.get(f"/api/entities/{entity_id}/lore")
        assert card.status_code == 200, card.text
    for catalog in CustomCatalog:
        listed = await api.http.get("/api/custom-kinds", params={"catalog": catalog.value, "world_id": core.world.id})
        assert listed.status_code == 200, listed.text

from aerona.db.tables.routes import HorizonIntuitionRow, JourneyRow, RouteRow
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.travel import HorizonStatus, JourneyIntent, JourneyStatus, RouteClosure, TravelMethod
from aerona.migration.legacy import blobs
from aerona.migration.legacy.context import MigrationContext
from aerona.migration.legacy.idmap import LegacyKind
from aerona.migration.legacy.importers.cosmos import UNKNOWN_VALUE
from aerona.migration.legacy.patterns import LegacyPatterns

ROUTE_CLOSURE_UNKNOWN = "route closure unknown"


async def import_routes(context: MigrationContext) -> None:
    created: list[tuple[int, RouteRow]] = []
    for row in context.source.iterate("routes", ("id",)):
        legacy_id = row.integer("id") or 0
        reference = f"route:{legacy_id}"
        first, second = context.world(row.integer("world_a")), context.world(row.integer("world_b"))
        method = context.vocabulary.decode_as("travel_method", row.text("method"), TravelMethod)
        if first is None or second is None or first == second or method is None:
            context.report.place_failed("route", reference, f"worlds or method {row.text('method')!r} could not be read")
            continue
        active = row.flag("active")
        forgetting = context.world(row.integer("closed_by_forgetting"))
        closure = None
        if not active:
            closure = RouteClosure.FORGOTTEN if forgetting is not None else RouteClosure.SEALED
            if forgetting is None:
                context.report.warn(ROUTE_CLOSURE_UNKNOWN, reference, "a closed route was marked sealed")
        route = RouteRow(
            world_a_id=first,
            world_b_id=second,
            method=method,
            duration_epochs=max(1, row.integer("duration") or 1),
            danger=max(PERCENT_MIN, min(PERCENT_MAX, row.integer("danger") or 0)),
            known=row.flag("known"),
            controller_entity_id=context.entity(row.integer("controller_id")),
            vehicle_entity_id=context.entity(row.integer("vehicle_id")),
            builder_son_id=context.son(row.integer("builder_son_id")),
            description=row.text("description"),
            created_epoch=max(0, row.integer("created_epoch") or 0),
            active=active,
            closure=closure,
            temp_open_until_epoch=row.integer("temp_open_until"),
            temp_closed_until_epoch=row.integer("temp_closed_until"),
            closed_by_forgetting_world_id=forgetting,
        )
        created.append((legacy_id, route))
    context.session.add_all([route for _, route in created])
    await context.session.flush()
    for legacy_id, route in created:
        context.ids.put(LegacyKind.ROUTE, legacy_id, route.id)


async def import_journeys(context: MigrationContext) -> None:
    patterns = LegacyPatterns(context.vocabulary)
    for row in context.source.iterate("journeys", ("id",)):
        reference = f"journey:{row.integer('id')}"
        traveller = context.entity(row.integer("traveller_id"))
        route_id = context.ids.get(LegacyKind.ROUTE, row.integer("route_id"))
        destination = context.world(row.integer("destination_world"))
        route = await context.session.get(RouteRow, route_id) if route_id is not None else None
        intent = context.vocabulary.decode_as("journey_intent", row.text("intent"), JourneyIntent)
        if traveller is None or route is None or destination is None or intent is None:
            context.report.place_failed("journey", reference, "traveller, route, destination or intent is missing")
            continue
        origin = route.world_b_id if route.world_a_id == destination else route.world_a_id
        status = context.vocabulary.decode_as("journey_status", row.text("status"), JourneyStatus)
        if status is None:
            context.report.warn(UNKNOWN_VALUE, reference, f"status {row.text('status')!r} read as underway")
            status = JourneyStatus.UNDERWAY
        start = max(0, row.integer("start_epoch") or 0)
        context.add(
            JourneyRow(
                traveller_entity_id=traveller,
                route_id=route.id,
                vehicle_entity_id=context.entity(row.integer("vehicle_id")),
                origin_world_id=origin,
                destination_world_id=destination,
                intent=intent,
                population=max(0, row.integer("population") or 0),
                epochs_left=max(0, row.integer("epochs_left") or 0),
                status=status,
                events=blobs.journey_events(context.vocabulary, row.json("events"), max(1, start), patterns.journey_event),
                start_epoch=start,
                result_entity_id=context.entity(row.integer("result_id")),
            )
        )
        context.report.convert("journeys_origin_from_route")
    for row in context.source.iterate("horizon_intuitions", ("id",)):
        mortal = context.entity(row.integer("mortal_id"))
        if mortal is None:
            context.report.place_failed("horizon intuition", f"intuition:{row.integer('id')}", "the mortal is missing")
            continue
        context.add(
            HorizonIntuitionRow(
                mortal_entity_id=mortal,
                world_id=context.world(row.integer("world_id")),
                epoch=max(0, row.integer("epoch") or 0),
                how=row.text("how"),
                method=context.vocabulary.decode_as("travel_method", row.text("method"), TravelMethod),
                status=context.vocabulary.decode_as("horizon_status", row.text("status"), HorizonStatus) or HorizonStatus.PENDING,
                result_world_id=context.world(row.integer("result_world")),
            )
        )
    await context.flush()

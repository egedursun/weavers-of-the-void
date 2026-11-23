from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.biology import BiologyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.body.variants import BiologyView, folk_biology, holder_of, view_from

SHARES = (
    ("food_need_pct", "food needed"),
    ("fertility_pct", "births"),
    ("death_pct", "deaths"),
    ("disease_pct", "sickness"),
    ("morale_loss_pct", "fear in battle"),
    ("fire_harm_pct", "harm from fire"),
    ("storm_harm_pct", "harm from storms"),
)


def biology_lines(view: BiologyView) -> list[str]:
    found = []
    if view.variants:
        found.append(f"in body {', '.join(spoken(variant) for variant in view.variants)}")
    found.extend(f"{label} at {getattr(view, key)}% of an ordinary body" for key, label in SHARES if getattr(view, key) != PERCENT)
    found.extend(text for flag, text in ((view.breathes, "needs no air"), (view.drinks, "needs no water"), (view.ages, "does not age")) if not flag)
    return found


async def mortal_biology_lines(scope: Scope, me: EntityRow) -> list[str]:
    found = biology_lines(await folk_biology(scope.session, me))
    holder = await holder_of(scope.session, me)
    row = await scope.session.get(BiologyRow, holder.id) if holder is not None else None
    partner = await scope.session.get(EntityRow, row.partner_species_id) if row is not None and row.partner_species_id is not None else None
    if partner is not None:
        found.append(f"your kind lives joined to {partner.name}, and their fate binds yours")
    return found


async def son_biology_lines(scope: Scope, son: SonRow) -> list[str]:
    if son.current_world_id is None:
        return []
    rows = (
        await scope.session.execute(
            select(EntityRow, BiologyRow)
            .join(BiologyRow, BiologyRow.holder_entity_id == EntityRow.id)
            .where(EntityRow.world_id == son.current_world_id, EntityRow.status == EntityStatus.CANON)
            .order_by(EntityRow.id)
        )
    ).all()
    shown = [f"{entity.name} ({'; '.join(told)})" for entity, row in rows if (told := biology_lines(view_from(row)))]
    return [f"The bodies of the kinds of life of the world you walk: {', '.join(shown)}."] if shown else []

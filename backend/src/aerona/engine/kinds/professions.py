from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.kind_concepts.society import BUILT_IN_PROFESSIONS
from aerona.db.tables.kinds import KindHoldingRow
from aerona.db.tables.society_kinds import OrganisationKindRow, ProfessionKindRow, RankKindRow
from aerona.domain.enums.kinds import KindConcept, KindStance
from aerona.domain.enums.mind import Profession

CARRIED = frozenset({KindStance.MAKES, KindStance.USES, KindStance.FAVOURS})


async def held_kinds[T: (ProfessionKindRow, RankKindRow, OrganisationKindRow)](
    session: AsyncSession, holder_id: int, concept: KindConcept, table: type[T]
) -> list[tuple[KindHoldingRow, T]]:
    rows = await session.execute(
        select(KindHoldingRow, table)
        .join(table, table.id == KindHoldingRow.kind_id)
        .where(
            KindHoldingRow.holder_node_id == holder_id,
            KindHoldingRow.concept == concept,
            KindHoldingRow.stance.in_(sorted(CARRIED)),
            table.retired.is_(False),
        )
        .order_by(KindHoldingRow.strength.desc(), KindHoldingRow.id)
    )
    return [(holding, kind) for holding, kind in rows.all()]


async def profession_kind(session: AsyncSession, people_id: int | None, profession: Profession) -> ProfessionKindRow | None:
    if people_id is not None:
        for _, kind in await held_kinds(session, people_id, KindConcept.PROFESSION, ProfessionKindRow):
            if kind.base is profession:
                return kind
    found: ProfessionKindRow | None = await session.scalar(
        select(ProfessionKindRow).where(ProfessionKindRow.built_in.is_(True), ProfessionKindRow.base == profession).limit(1)
    )
    return found


async def profession_purity(session: AsyncSession, people_id: int | None, profession: Profession) -> int:
    kind = await profession_kind(session, people_id, profession)
    return kind.purity if kind is not None else BUILT_IN_PROFESSIONS[profession].purity


async def professions_by_purity(session: AsyncSession, people_id: int | None) -> list[Profession]:
    scored = [(await profession_purity(session, people_id, profession), profession.value, profession) for profession in Profession]
    return [profession for _, _, profession in sorted(scored, key=lambda item: (-item[0], item[1]))]

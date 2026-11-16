from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.concealment import HiddenTruthRow, TruthKeeperRow
from aerona.db.tables.powers import PowerRow
from aerona.domain.enums.arcana import SpellForm, SpellTechnique
from aerona.domain.enums.concealment import ConcealScope, HiddenTruthKind, KeeperRole
from aerona.domain.enums.powers import PowerOrigin, PowerState, PowerVisibility
from tests.tools.every_setup import ruled_realm, second_mortal
from tests.tools.factories import Realm

EPOCH = 1


def power_of(holder_id: int, form: SpellForm = SpellForm.MIND, granted_by: int | None = None) -> PowerRow:
    return PowerRow(
        holder_node_id=holder_id,
        technique=SpellTechnique.PERCEIVE,
        form=form,
        strength=4,
        control=60,
        origin=PowerOrigin.GRANTED if granted_by is not None else PowerOrigin.BORN,
        state=PowerState.ACTIVE,
        visibility=PowerVisibility.SUBTLE,
        strain=0,
        strain_cap=30,
        granted_by_node_id=granted_by,
        uses=0,
        gained_epoch=EPOCH,
        locked=[],
    )


async def powered(session: AsyncSession, realm: Realm) -> dict[str, int]:
    row = power_of(realm.mortal_id)
    session.add(row)
    await session.flush()
    return {"power": row.id}


async def seer(session: AsyncSession, realm: Realm) -> dict[str, int]:
    row = power_of(realm.mortal_id, SpellForm.TIME)
    session.add(row)
    await session.flush()
    return {"power": row.id}


async def linked_pair(session: AsyncSession, realm: Realm) -> dict[str, int]:
    found = await second_mortal(session, realm)
    partner = found["mortal"]
    session.add_all([power_of(realm.mortal_id), power_of(partner)])
    await session.flush()
    return {"partner": partner}


async def kept_truth(session: AsyncSession, realm: Realm) -> dict[str, int]:
    truth = HiddenTruthRow(
        title="those who walk unseen",
        description="",
        subject_node_id=realm.people_id,
        kind=HiddenTruthKind.PRESENCE,
        hidden_from=ConcealScope.EVERYONE,
        strength=60,
        by_oath=True,
        founded_epoch=EPOCH,
        tended_epoch=EPOCH,
        locked=[],
    )
    session.add(truth)
    await session.flush()
    session.add(TruthKeeperRow(truth_id=truth.id, keeper_node_id=realm.mortal_id, role=KeeperRole.MEMBER, locked=[]))
    await session.flush()
    return {"truth": truth.id}


async def heard_truth(session: AsyncSession, realm: Realm) -> dict[str, int]:
    truth = HiddenTruthRow(
        title="what the river keeps",
        description="",
        subject_node_id=realm.mortal_id,
        kind=HiddenTruthKind.ORIGIN,
        hidden_from=ConcealScope.A_PEOPLE,
        scope_node_id=realm.people_id,
        strength=40,
        by_neglect=True,
        founded_epoch=EPOCH,
        tended_epoch=EPOCH,
        locked=[],
    )
    session.add(truth)
    await session.flush()
    return {"truth": truth.id}


async def tested_realm(session: AsyncSession, realm: Realm) -> dict[str, int]:
    found = await ruled_realm(session, realm)
    other = await second_mortal(session, realm)
    row = power_of(other["mortal"])
    row.state = PowerState.LATENT
    session.add(row)
    await session.flush()
    return found


async def son_granted(session: AsyncSession, realm: Realm) -> dict[str, int]:
    row = power_of(realm.mortal_id, granted_by=realm.son_id)
    session.add(row)
    await session.flush()
    return {"power": row.id}

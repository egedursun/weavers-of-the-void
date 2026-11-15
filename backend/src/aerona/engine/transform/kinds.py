from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from types import MappingProxyType

from aerona.domain.enums.transform import TransformKind, TransformTrigger
from aerona.engine.context import TickContext
from aerona.engine.transform import beings, cosmos, creatures, faiths, gods, lore, peoples, realms
from aerona.engine.transform.ledger import Ledger
from aerona.rules.registry import Rules

K = TransformKind
Push = tuple[int, TransformTrigger]
Pressures = Callable[[TickContext], Awaitable[dict[int, Push]]]


def engine_pushes(found: Callable[[TickContext], Awaitable[dict[int, int]]], trigger: TransformTrigger) -> Pressures:
    async def pushes(ctx: TickContext) -> dict[int, Push]:
        return {subject: (value, trigger) for subject, value in (await found(ctx)).items()}

    return pushes


@dataclass(frozen=True)
class Kind:
    pressures: Pressures
    check: Callable[[TickContext, int], Awaitable[str | None]]
    perform: Callable[[TickContext, int, Ledger], Awaitable[int]]
    epochs: Callable[[Rules], int]
    direct: bool = False
    forced_trigger: TransformTrigger = TransformTrigger.FORCED

    def step(self, rules: Rules, pressure: int) -> int:
        return pressure if self.direct else -(-pressure // max(1, self.epochs(rules)))


KINDS = MappingProxyType(
    {
        K.FALL: Kind(
            engine_pushes(gods.fall_pressures, TransformTrigger.FADING),
            gods.fall_check,
            gods.cast_down,
            lambda rules: rules.transform.fall_epochs,
            forced_trigger=TransformTrigger.CREATOR,
        ),
        K.RESTORATION: Kind(
            engine_pushes(gods.restoration_pressures, TransformTrigger.ENGINE),
            gods.restoration_check,
            gods.restore,
            lambda rules: 1,
            direct=True,
        ),
        K.CORRUPTION: Kind(
            engine_pushes(gods.corruption_pressures, TransformTrigger.VOID),
            gods.corruption_check,
            gods.corrupt,
            lambda rules: 1,
            direct=True,
        ),
        K.LOSS_OF_SAPIENCE: Kind(
            peoples.sapience_pressures,
            peoples.people_check,
            peoples.lose_sapience,
            lambda rules: rules.transform.sapience_epochs,
            forced_trigger=TransformTrigger.PUNISHMENT,
        ),
        K.ETHNORELIGIOUS: Kind(
            peoples.ethnoreligious_pressures, peoples.cult_check, peoples.faith_to_people, lambda rules: rules.transform.ethnoreligious_epochs
        ),
        K.NATION_BUILDING: Kind(peoples.nation_pressures, peoples.polity_check, peoples.realm_to_people, lambda rules: rules.transform.nation_epochs),
        K.HOUSE_PEOPLE: Kind(peoples.house_pressures, peoples.house_check, peoples.house_to_people, lambda rules: rules.transform.house_epochs),
        K.POCKET_WORLD: Kind(
            engine_pushes(cosmos.pocket_pressures, TransformTrigger.ENGINE), cosmos.pocket_check, cosmos.detach, lambda rules: rules.transform.pocket_epochs
        ),
        K.WORLD_SOUL: Kind(
            engine_pushes(cosmos.world_soul_pressures, TransformTrigger.ENGINE),
            cosmos.world_soul_check,
            cosmos.ascend_world,
            lambda rules: rules.transform.world_soul_epochs,
        ),
        K.STAR_GOD: Kind(
            engine_pushes(cosmos.star_god_pressures, TransformTrigger.ENGINE),
            cosmos.star_god_check,
            cosmos.raise_star,
            lambda rules: rules.transform.star_god_epochs,
        ),
        K.OUTER_ENTRY: Kind(
            engine_pushes(cosmos.outer_entry_pressures, TransformTrigger.ENGINE),
            cosmos.outer_entry_check,
            cosmos.enter_cosmos,
            lambda rules: rules.transform.outer_entry_epochs,
        ),
        K.SACRALISATION: Kind(faiths.sacralisation_pressures, faiths.ideology_check, faiths.sacralise, lambda rules: rules.transform.sacralisation_epochs),
        K.SECULARISATION: Kind(faiths.secularisation_pressures, faiths.cult_check, faiths.secularise, lambda rules: rules.transform.secularisation_epochs),
        K.PROGENITOR: Kind(creatures.progenitor_pressures, creatures.beast_check, creatures.found_line, lambda rules: rules.transform.progenitor_epochs),
        K.LOCAL_GOD: Kind(
            engine_pushes(beings.local_god_pressures, TransformTrigger.ENGINE),
            beings.spirit_check,
            beings.raise_spirit,
            lambda rules: rules.transform.local_god_epochs,
        ),
        K.BEAST_CURSE: Kind(
            engine_pushes(beings.beast_curse_pressures, TransformTrigger.CURSE),
            beings.mortal_check,
            beings.curse_into_beast,
            lambda rules: 1,
            direct=True,
        ),
        K.CURSE_LIFTED: Kind(
            engine_pushes(beings.curse_lifted_pressures, TransformTrigger.ENGINE),
            beings.lifted_check,
            beings.lift_curse,
            lambda rules: 1,
            direct=True,
        ),
        K.REALM_FROM_TITLE: Kind(
            engine_pushes(realms.realm_title_pressures, TransformTrigger.ENGINE),
            realms.title_check,
            realms.title_to_realm,
            lambda rules: rules.transform.realm_title_epochs,
        ),
        K.TRADITION_CODIFIED: Kind(
            engine_pushes(realms.codified_pressures, TransformTrigger.ENGINE),
            realms.tradition_check,
            realms.codify,
            lambda rules: rules.transform.codified_epochs,
        ),
        K.THEORY_SETTLED: Kind(lore.theory_pressures, lore.theory_check, lore.settle, lambda rules: rules.transform.theory_epochs),
    }
)

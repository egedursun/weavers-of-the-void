from aerona.catalog.identity import SALIENCE_DRIVERS, VOTE_LAYERS
from aerona.domain.enums.belonging import IdentityLayer, SalienceDriver
from aerona.domain.enums.referendums import ReferendumSubject


def test_thirteen_drivers_each_reach_their_own_layers() -> None:
    assert len(SALIENCE_DRIVERS) == len(SalienceDriver) == 13
    assert IdentityLayer.KIND in SALIENCE_DRIVERS[SalienceDriver.PERSECUTION].layers
    assert SALIENCE_DRIVERS[SalienceDriver.CONTEST].layers == {IdentityLayer.LOCALITY, IdentityLayer.CIRCLE}
    assert set(VOTE_LAYERS) == set(ReferendumSubject)
    assert all(spec.layers <= set(IdentityLayer) for spec in SALIENCE_DRIVERS.values())

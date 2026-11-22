from aerona.domain.enums.world import Atmosphere

AIR_SHIELDING: dict[Atmosphere, int] = {Atmosphere.NONE: 0, Atmosphere.THIN: 25, Atmosphere.NORMAL: 50, Atmosphere.DENSE: 75, Atmosphere.TOXIC: 60}

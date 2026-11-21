from dataclasses import dataclass


@dataclass
class CityTally:
    rules_set: int = 0
    evaded: int = 0
    services: int = 0
    failed: int = 0
    joined: int = 0
    split: int = 0
    rebuilt: int = 0

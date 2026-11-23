from types import MappingProxyType

from aerona.catalog.transmission import ROUTES

VECTOR_LABELS = MappingProxyType({route: spec.label for route, spec in ROUTES.items()})
VECTOR_FUNCTIONS = MappingProxyType({route: spec.functions for route, spec in ROUTES.items()})
VECTOR_STIGMA = MappingProxyType({route: spec.stigma for route, spec in ROUTES.items()})

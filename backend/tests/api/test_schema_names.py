from aerona.main import create_app
from aerona.settings import Settings

QUALIFIED = "__"


def test_no_two_api_models_share_a_name(settings: Settings) -> None:
    schemas = create_app(settings).openapi()["components"]["schemas"]
    assert sorted(name for name in schemas if QUALIFIED in name) == []

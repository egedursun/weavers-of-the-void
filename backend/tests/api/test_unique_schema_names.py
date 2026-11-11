from aerona.main import create_app


def test_every_api_schema_has_a_name_of_its_own() -> None:
    names = create_app().openapi()["components"]["schemas"]
    assert sorted(name for name in names if "__" in name) == []

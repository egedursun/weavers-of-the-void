from tests.api.conftest import ApiWorld, seeded


async def test_codex_and_book(api: ApiWorld) -> None:
    codex = await api.http.get("/api/codex.md")
    assert codex.status_code == 200
    assert "attachment" in codex.headers["content-disposition"]
    book = await api.http.get("/api/book")
    assert book.status_code == 200
    assert "nonce-" in book.headers["content-security-policy"]
    entry = await api.http.get("/api/book", params={"son_id": seeded(api).core.son.id})
    assert entry.status_code == 200
    assert (await api.http.get("/api/book", params={"entity_id": 999999})).status_code == 404

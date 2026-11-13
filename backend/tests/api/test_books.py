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


async def test_the_book_serves_its_fonts_logo_and_print_status(api: ApiWorld) -> None:
    font = await api.http.get("/api/book/fonts/alegreya-regular.ttf")
    assert font.status_code == 200 and "immutable" in font.headers["cache-control"]
    assert (await api.http.get("/api/book/fonts/no-such-font.ttf")).status_code == 404
    assert (await api.http.get("/api/book/fonts/..%2Fsecret.ttf")).status_code in (404, 422)
    logo = await api.http.get("/api/book/brand/logo.png")
    assert logo.status_code == 200 and logo.headers["content-type"] == "image/png"
    status = await api.http.get("/api/book/pdf")
    assert status.status_code == 200 and status.json()["ready"] is False and status.json()["size"] is None


async def test_the_book_offers_no_download_before_a_pdf_is_generated(api: ApiWorld) -> None:
    page = (await api.http.get("/api/book")).text
    toolbar = page[page.index('<header class="toolbar">') : page.index("</header>")]
    download = toolbar[toolbar.index('id="pdf-download"') : toolbar.index("</a>", toolbar.index('id="pdf-download"'))]
    assert 'aria-disabled="true"' in download and "href=" not in download
    assert "Generate PDF" in toolbar and "Create PDF" not in toolbar
    assert toolbar.index('id="pdf-make"') < toolbar.index('id="pdf-download"') < toolbar.index('id="print-book"')
    assert "[hidden]{display:none!important}" in page


async def test_a_language_previews_names_without_keeping_them(api: ApiWorld) -> None:
    language = seeded(api).core.language
    first = await api.http.post(f"/api/languages/{language.id}/sample-names", json={"count": 4, "salt": "a"})
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["language_id"] == language.id and len(body["names"]) == 4
    again = await api.http.post(f"/api/languages/{language.id}/sample-names", json={"count": 4, "salt": "a"})
    assert again.json()["names"] == body["names"]
    assert (await api.http.post("/api/languages/999999/sample-names", json={})).status_code == 404

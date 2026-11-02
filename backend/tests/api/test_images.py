import io

from PIL import Image

from tests.api.conftest import ApiWorld, seeded


def png(width: int = 400, height: int = 200) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (200, 120, 40)).save(buffer, format="PNG")
    return buffer.getvalue()


async def test_image_upload_cover_caption_thumbnail_and_delete(api: ApiWorld) -> None:
    town = seeded(api).core.extra["town"].id
    uploaded = await api.http.post("/api/images", params={"node_id": town, "caption": "The harbour"}, content=png(), headers={"content-type": "image/png"})
    assert uploaded.status_code == 200, uploaded.text
    image = uploaded.json()
    assert image["is_cover"] is True
    listed = (await api.http.get("/api/images", params={"node_id": town})).json()
    assert [item["image"]["id"] for item in listed] == [image["id"]]
    original = await api.http.get(f"/api/media/{image['file_name']}")
    assert original.status_code == 200
    assert "immutable" in original.headers["cache-control"]
    assert original.headers["content-type"] == "image/png"
    assert original.content == png()
    assert original.headers["content-length"] == str(len(png()))
    etag = original.headers["etag"]
    assert (await api.http.get(f"/api/media/{image['file_name']}", headers={"if-none-match": etag})).status_code == 304
    head = await api.http.head(f"/api/media/{image['file_name']}")
    assert head.status_code == 200
    assert head.headers["content-length"] == str(len(png()))
    thumbnail = await api.http.get(f"/api/media/{image['file_name']}", params={"w": 160})
    assert thumbnail.status_code == 200
    assert thumbnail.headers["content-type"] == "image/webp"
    assert thumbnail.headers["etag"] != etag
    assert Image.open(io.BytesIO(thumbnail.content)).width == 160
    store = api.services.application.media
    stem = image["file_name"].rsplit(".", 1)[0]
    assert await store.exists(f"thumbnails/160/{stem}.webp")
    assert (await api.http.get(f"/api/media/{image['file_name']}", params={"w": 640})).headers["content-type"] == "image/png"
    assert (await api.http.get(f"/api/media/{image['file_name']}", params={"w": 161})).status_code == 400
    assert (await api.http.put(f"/api/images/{image['id']}/caption", json={"caption": "Harbour at dusk"})).status_code == 200
    assert (await api.http.put(f"/api/images/{image['id']}/cover")).status_code == 200
    assert (await api.http.delete(f"/api/images/{image['id']}")).status_code == 200
    assert (await api.http.get(f"/api/media/{image['file_name']}")).status_code == 404
    assert not await store.exists(f"originals/{image['file_name']}")
    assert not await store.exists(f"thumbnails/160/{stem}.webp")


async def test_same_upload_twice_is_stored_once(api: ApiWorld) -> None:
    town = seeded(api).core.extra["town"].id
    headers = {"content-type": "image/png"}
    first = (await api.http.post("/api/images", params={"node_id": town}, content=png(300, 100), headers=headers)).json()
    again = (await api.http.post("/api/images", params={"node_id": town}, content=png(300, 100), headers=headers)).json()
    assert again["id"] == first["id"]
    listed = (await api.http.get("/api/images", params={"node_id": town})).json()
    assert len(listed) == 1


async def test_unknown_media_is_not_found(api: ApiWorld) -> None:
    assert (await api.http.get("/api/media/nothing.png")).status_code == 404
    assert (await api.http.get("/api/media/..%2Fsecret.png")).status_code in (404, 422)


async def test_export_and_replace_import_carry_images(api: ApiWorld) -> None:
    town = seeded(api).core.extra["town"].id
    image = (await api.http.post("/api/images", params={"node_id": town}, content=png(), headers={"content-type": "image/png"})).json()
    package = (await api.http.get("/api/world/export")).content
    assert (await api.http.delete(f"/api/images/{image['id']}")).status_code == 200
    assert (await api.http.get(f"/api/media/{image['file_name']}")).status_code == 404
    imported = await api.http.post(
        "/api/world/import", params={"mode": "replace", "confirm": "REPLACE"}, content=package, headers={"content-type": "application/octet-stream"}
    )
    assert imported.status_code == 200, imported.text
    await api.settle()
    served = await api.http.get(f"/api/media/{image['file_name']}")
    assert served.status_code == 200
    assert served.content == png()


async def test_image_upload_refuses_lies_and_forms(api: ApiWorld) -> None:
    town = seeded(api).core.extra["town"].id
    lie = await api.http.post("/api/images", params={"node_id": town}, content=b"not an image", headers={"content-type": "image/png"})
    assert lie.status_code == 400
    form = await api.http.post("/api/images", params={"node_id": town}, content=png(), headers={"content-type": "multipart/form-data"})
    assert form.status_code == 415


async def test_gallery_and_generation_status(api: ApiWorld) -> None:
    missing = (await api.http.get("/api/gallery/missing", params={"limit": 3})).json()
    assert len(missing) <= 3
    status = (await api.http.get("/api/image-gen")).json()
    assert status["status"]["available"] is False
    generate = await api.http.post("/api/image-gen", json={"node_id": seeded(api).core.extra["town"].id})
    assert generate.status_code in (409, 503)
    assert (await api.http.post("/api/image-gen/batch/stop")).status_code == 409
    assert (await api.http.post("/api/entities/prompts/write-missing")).status_code == 409

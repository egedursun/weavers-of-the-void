from fastapi import APIRouter

from aerona.api.actions import Alias, mount_all

router = APIRouter(tags=["player"])

ALIASES = (
    Alias("POST", "/peoples/awaken", "awaken_peoples"),
    Alias("POST", "/federations", "federation"),
    Alias("POST", "/cheats/essence", "cheat:essence"),
)

mount_all(router, ALIASES, tag="player")

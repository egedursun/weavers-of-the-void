from fastapi import APIRouter, Request, Response

from aerona.api.dependencies import AccountsDep, SignedDep
from aerona.api.schemas.accounts import AccountProfileView, AuthState, PasswordChange, ProfilePatch, SessionsEnded, SessionView, SetupRequest, SignInRequest
from aerona.api.schemas.common import Done
from aerona.constants.accounts import SECONDS_PER_DAY, SESSION_COOKIE
from aerona.services.accounts.service import AccountService, Resolved, SignedIn
from aerona.services.accounts.store import AccountRecord

router = APIRouter(prefix="/auth", tags=["auth"])

SIGNED_OUT = "Signed out."


def account_view(account: AccountRecord) -> AccountProfileView:
    return AccountProfileView(
        id=account.id,
        username=account.username,
        email=account.email,
        display_name=account.display_name,
        status=account.status,
        server_role=account.server_role,
        avatar_tone=account.avatar_tone,
        must_change_password=account.must_change_password,
        created_at=account.created_at,
        last_sign_in_at=account.last_sign_in_at,
        password_changed_at=account.password_changed_at,
        locked_until=account.locked_until,
    )


def client_address(request: Request) -> str:
    return request.client.host if request.client is not None else ""


def set_cookie(response: Response, accounts: AccountService, signed: SignedIn) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        signed.token,
        max_age=int(accounts.settings.accounts_session_max_days * SECONDS_PER_DAY),
        httponly=True,
        samesite="lax",
        secure=accounts.settings.cookie_secure,
        path="/",
    )


def clear_cookie(response: Response, accounts: AccountService) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax", secure=accounts.settings.cookie_secure)


async def state_of(accounts: AccountService, signed: Resolved | None) -> AuthState:
    ready = await accounts.ready()
    return AuthState(
        setup_required=not ready,
        account=account_view(signed.account) if signed is not None else None,
        must_change_password=signed.account.must_change_password if signed is not None else False,
        password_min_length=accounts.settings.accounts_password_min_length,
    )


@router.get("/state", response_model=AuthState)
async def auth_state(request: Request, accounts: AccountsDep) -> AuthState:
    return await state_of(accounts, getattr(request.state, "signed", None))


@router.post("/setup", response_model=AuthState)
async def setup(body: SetupRequest, request: Request, response: Response, accounts: AccountsDep) -> AuthState:
    signed = await accounts.setup(
        username=body.username,
        email=body.email,
        display_name=body.display_name,
        password=body.password,
        user_agent=request.headers.get("user-agent", ""),
        address=client_address(request),
    )
    set_cookie(response, accounts, signed)
    return await state_of(accounts, Resolved(signed.account, signed.session))


@router.post("/sign-in", response_model=AuthState)
async def sign_in(body: SignInRequest, request: Request, response: Response, accounts: AccountsDep) -> AuthState:
    signed = await accounts.sign_in(body.login, body.password, user_agent=request.headers.get("user-agent", ""), address=client_address(request))
    set_cookie(response, accounts, signed)
    return await state_of(accounts, Resolved(signed.account, signed.session))


@router.post("/sign-out", response_model=Done)
async def sign_out(signed: SignedDep, response: Response, accounts: AccountsDep) -> Done:
    await accounts.sign_out(signed.session.id)
    clear_cookie(response, accounts)
    return Done(message=SIGNED_OUT)


@router.post("/password", response_model=AuthState)
async def change_password(body: PasswordChange, signed: SignedDep, accounts: AccountsDep) -> AuthState:
    account = await accounts.change_password(signed.account, body.current, body.new, signed.session.id)
    return await state_of(accounts, Resolved(account, signed.session))


@router.patch("/profile", response_model=AccountProfileView)
async def update_profile(body: ProfilePatch, signed: SignedDep, accounts: AccountsDep) -> AccountProfileView:
    return account_view(await accounts.update_profile(signed.account, display_name=body.display_name, email=body.email, avatar_tone=body.avatar_tone))


@router.get("/sessions", response_model=list[SessionView])
async def sessions(signed: SignedDep, accounts: AccountsDep) -> list[SessionView]:
    return [
        SessionView(
            id=session.id,
            created_at=session.created_at,
            last_used_at=session.last_used_at,
            expires_at=session.expires_at,
            user_agent=session.user_agent,
            address=session.address,
            current=session.id == signed.session.id,
        )
        for session in await accounts.sessions_of(signed.account)
    ]


@router.delete("/sessions/{session_id}", response_model=Done)
async def end_session(session_id: int, signed: SignedDep, response: Response, accounts: AccountsDep) -> Done:
    await accounts.end_session(signed.account, session_id)
    if session_id == signed.session.id:
        clear_cookie(response, accounts)
    return Done()


@router.delete("/sessions", response_model=SessionsEnded)
async def end_other_sessions(signed: SignedDep, accounts: AccountsDep) -> SessionsEnded:
    return SessionsEnded(ended=await accounts.end_other_sessions(signed.account, signed.session.id))

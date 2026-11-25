from fastapi import APIRouter, Path

from aerona.api.dependencies import AccountsDep, SignedDep
from aerona.api.routers.auth import account_view
from aerona.api.schemas.accounts import AccountCreate, AccountPatch, AccountProfileView, IssuedPassword
from aerona.api.schemas.common import Done

router = APIRouter(prefix="/accounts", tags=["accounts"])

ACCOUNT_DELETED = "The account is deleted; everything it made keeps its name."


@router.get("", response_model=list[AccountProfileView])
async def list_accounts(accounts: AccountsDep) -> list[AccountProfileView]:
    return [account_view(account) for account in await accounts.accounts()]


@router.post("", response_model=IssuedPassword, status_code=201)
async def create_account(body: AccountCreate, signed: SignedDep, accounts: AccountsDep) -> IssuedPassword:
    issued = await accounts.create_account(
        signed.account, username=body.username, email=body.email, display_name=body.display_name, server_role=body.server_role
    )
    return IssuedPassword(account=account_view(issued.account), temporary_password=issued.temporary_password)


@router.patch("/{account_id}", response_model=AccountProfileView)
async def edit_account(body: AccountPatch, signed: SignedDep, accounts: AccountsDep, account_id: int = Path(ge=1)) -> AccountProfileView:
    return account_view(await accounts.edit_account(signed.account, account_id, status=body.status, server_role=body.server_role))


@router.delete("/{account_id}", response_model=Done)
async def delete_account(signed: SignedDep, accounts: AccountsDep, account_id: int = Path(ge=1)) -> Done:
    await accounts.delete_account(signed.account, account_id)
    return Done(message=ACCOUNT_DELETED)


@router.post("/{account_id}/reset-password", response_model=IssuedPassword)
async def reset_password(signed: SignedDep, accounts: AccountsDep, account_id: int = Path(ge=1)) -> IssuedPassword:
    issued = await accounts.admin_reset(signed.account, account_id)
    return IssuedPassword(account=account_view(issued.account), temporary_password=issued.temporary_password)


@router.post("/{account_id}/ownership", response_model=AccountProfileView)
async def transfer_ownership(signed: SignedDep, accounts: AccountsDep, account_id: int = Path(ge=1)) -> AccountProfileView:
    return account_view(await accounts.transfer_ownership(signed.account, account_id))

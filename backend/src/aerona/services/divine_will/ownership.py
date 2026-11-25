from aerona.db.authorship import owns
from aerona.tools.divine_will.library_ports import Ownership


def ownership_of(author_account_id: int | None, author_name: str | None, shared: bool) -> Ownership:
    return Ownership(author_account_id, author_name, shared, owns(author_account_id))

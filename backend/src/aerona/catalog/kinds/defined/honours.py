from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.honours import HonourPrivilege, VeteranGrant

HONOUR_PRIVILEGE = total(
    HonourPrivilege,
    {
        HonourPrivilege.PRECEDENCE: Defined("Precedence", checked_by=("engine.honours.persons.confer",), used_by=("tools.son.person_honours.own_honour",)),
        HonourPrivilege.PENSION: Defined("Pension", checked_by=("engine.honours.persons.pay_pensions",), used_by=()),
        HonourPrivilege.LAND: Defined("Land", checked_by=("engine.honours.persons.grant_privileges",), used_by=()),
        HonourPrivilege.SEAT: Defined("Seat", checked_by=("engine.honours.persons.grant_privileges",), used_by=()),
        HonourPrivilege.IMMUNITY: Defined("Immunity", checked_by=("engine.honours.persons.immune",), used_by=()),
        HonourPrivilege.TITLE: Defined("Title", checked_by=("engine.honours.persons.grant_privileges",), used_by=()),
        HonourPrivilege.NONE: Defined("None", checked_by=(), used_by=()),
    },
)

VETERAN_GRANT = total(
    VeteranGrant,
    {
        VeteranGrant.LAND: Defined("Land in a colony", checked_by=(), used_by=("engine.honours.veterans.grant",)),
        VeteranGrant.PENSION: Defined(
            "Pensions",
            checked_by=("engine.honours.veterans.pay_pensions",),
            used_by=("engine.honours.veterans.grant", "services.player.honours.VeteranGrantDraft"),
        ),
        VeteranGrant.NONE: Defined("Nothing", checked_by=("engine.honours.veterans.bitter_veterans",), used_by=("engine.honours.veterans.grant",)),
    },
)

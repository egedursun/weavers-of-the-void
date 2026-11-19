from aerona.domain.enums.works import EnterpriseForm, EnterpriseManagement, WorksKind

WORKS_PROSPERITY_PCT: dict[WorksKind, int] = {
    WorksKind.POWER_LINE: 150,
    WorksKind.NETWORK_LINE: 150,
    WorksKind.TERRAFORMING_STAGE: 200,
    WorksKind.MEGASTRUCTURE_STAGE: 300,
    WorksKind.GROWN_WORKS: 120,
}

ENTERPRISE_REVENUE_PCT: dict[EnterpriseForm, int] = {
    EnterpriseForm.MONOPOLY: 100,
    EnterpriseForm.ROYAL_WORKS: 80,
    EnterpriseForm.STATE_COMPANY: 110,
    EnterpriseForm.LICENCE_HOLDER: 60,
    EnterpriseForm.ARSENAL: 50,
    EnterpriseForm.MINT: 100,
}

MANAGEMENT_SKIM_PCT: dict[EnterpriseManagement, int] = {
    EnterpriseManagement.OFFICIAL: 100,
    EnterpriseManagement.COMPANY: 60,
    EnterpriseManagement.MADE_MIND: 0,
}

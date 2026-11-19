from aerona.domain.enums.daily_life import ServiceEnd, ServiceTerms

SERVICE_COST_PCT: dict[ServiceTerms, int] = {
    ServiceTerms.WAGE: 100,
    ServiceTerms.BOARD: 50,
    ServiceTerms.BOUND: 0,
}

SERVICE_ENDING: dict[ServiceTerms, ServiceEnd] = {
    ServiceTerms.WAGE: ServiceEnd.UNPAID,
    ServiceTerms.BOARD: ServiceEnd.DISMISSED,
    ServiceTerms.BOUND: ServiceEnd.CHOSE,
}

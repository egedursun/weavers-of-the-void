export const CITY_VIEWS = ['city', 'land'] as const

export type CityView = (typeof CITY_VIEWS)[number]

export type CitiesSearch = {
  view?: CityView
  town?: number
  region?: number
}

function positiveInteger(value: unknown): number | undefined {
  const number = typeof value === 'string' ? Number(value) : value
  return typeof number === 'number' && Number.isInteger(number) && number > 0
    ? number
    : undefined
}

export function validateCitiesSearch(
  search: Record<string, unknown>
): CitiesSearch {
  return {
    view: CITY_VIEWS.find((item) => item === search.view),
    town: positiveInteger(search.town),
    region: positiveInteger(search.region),
  }
}

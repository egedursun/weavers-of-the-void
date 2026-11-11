import { createFileRoute } from '@tanstack/react-router'
import { CitiesScreen } from '@/features/city/CitiesScreen'
import { validateCitiesSearch } from '@/features/city/citiesSearch'

export const Route = createFileRoute('/_app/cities')({
  staticData: { layout: 'canvas' },
  validateSearch: validateCitiesSearch,
  component: CitiesScreen,
})

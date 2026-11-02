import { getRouteApi } from '@tanstack/react-router'
import { PromptsPage } from './PromptsPage'

const route = getRouteApi('/_app/settings/prompts')

export function PromptsRouteScreen() {
  const search = route.useSearch()
  return <PromptsPage key={search.son ?? 'none'} search={search} />
}

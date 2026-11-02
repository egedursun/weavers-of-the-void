import { createFileRoute } from '@tanstack/react-router'
import { WorldRulesScreen } from '@/features/world-rules/WorldRulesScreen'

type WorldRulesSearch = {
  q?: string
}

export const Route = createFileRoute('/_app/settings/world-rules')({
  validateSearch: (search: Record<string, unknown>): WorldRulesSearch =>
    typeof search.q === 'string' && search.q !== '' ? { q: search.q } : {},
  component: WorldRulesScreen,
})

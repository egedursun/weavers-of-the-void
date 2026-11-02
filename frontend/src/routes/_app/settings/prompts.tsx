import { createFileRoute } from '@tanstack/react-router'
import { PromptsRouteScreen } from '@/features/prompts/PromptsRouteScreen'
import { validatePromptsSearch } from '@/features/prompts/promptsSearch'

export const Route = createFileRoute('/_app/settings/prompts')({
  validateSearch: validatePromptsSearch,
  component: PromptsRouteScreen,
})

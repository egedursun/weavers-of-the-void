import { createFileRoute } from '@tanstack/react-router'
import { WarsScreen } from '@/features/wars/WarsScreen'
import { validateWarsSearch } from '@/features/wars/warsTabs'

export const Route = createFileRoute('/_app/wars')({
  validateSearch: validateWarsSearch,
  component: WarsScreen,
})

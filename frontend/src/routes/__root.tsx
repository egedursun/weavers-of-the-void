import { type QueryClient } from '@tanstack/react-query'
import { createRootRouteWithContext } from '@tanstack/react-router'
import { RootLayout } from '@/components/layout/RootLayout'
import { validateEntrySearch } from '@/components/layout/entry/entryStack'
import { GeneralError } from '@/features/errors/GeneralError'
import { NotFoundError } from '@/features/errors/NotFoundError'

export const Route = createRootRouteWithContext<{
  queryClient: QueryClient
}>()({
  validateSearch: validateEntrySearch,
  component: RootLayout,
  notFoundComponent: NotFoundError,
  errorComponent: GeneralError,
})

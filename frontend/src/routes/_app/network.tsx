import { createFileRoute, lazyRouteComponent } from '@tanstack/react-router'
import { validateGraphSearch } from '@/features/graph/graphRouteSearch'

export const Route = createFileRoute('/_app/network')({
  staticData: { layout: 'canvas' },
  validateSearch: validateGraphSearch,
  component: lazyRouteComponent(
    () => import('@/features/graph/GraphScreen'),
    'GraphScreen'
  ),
})

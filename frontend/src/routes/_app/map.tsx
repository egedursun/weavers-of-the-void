import { createFileRoute, lazyRouteComponent } from '@tanstack/react-router'
import { validateMapSearch } from '@/features/map/mapRouteSearch'

export const Route = createFileRoute('/_app/map')({
  staticData: { layout: 'canvas' },
  validateSearch: validateMapSearch,
  component: lazyRouteComponent(
    () => import('@/features/map/MapView'),
    'MapView'
  ),
})

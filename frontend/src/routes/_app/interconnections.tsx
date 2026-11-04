import { createFileRoute, lazyRouteComponent } from '@tanstack/react-router'

export const Route = createFileRoute('/_app/interconnections')({
  component: lazyRouteComponent(
    () => import('@/features/interconnect/InterconnectionExplorer'),
    'InterconnectionExplorer'
  ),
})

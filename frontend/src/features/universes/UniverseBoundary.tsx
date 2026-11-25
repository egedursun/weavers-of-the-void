import { type ReactNode, useEffect } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { Navigate, useRouterState } from '@tanstack/react-router'
import { RealtimeProvider } from '@/realtime'
import { type EventSourceLike } from '@/realtime/eventStream'
import { toast } from 'sonner'
import { queryClientFor } from '@/api/queryClients'
import {
  chooseUniverse,
  holdsDocument,
  onUniverseRefused,
  universeFromSearch,
  useUniverseId,
  wasRefused,
} from '@/api/universeStore'
import { EnteringUniverse } from './EnteringUniverse'

const REFUSAL_TOAST = 'universe-refused'

type UniverseBoundaryProps = {
  children: ReactNode
  createSource?: (url: string) => EventSourceLike
}

export function UniverseBoundary({
  children,
  createSource,
}: UniverseBoundaryProps) {
  const universe = useUniverseId()
  const named = useRouterState({
    select: (state) => universeFromSearch(state.location.searchStr),
  })
  const fromUrl = named !== null && !wasRefused(named) ? named : null
  const target = fromUrl ?? universe
  const switching = target !== null && target !== universe
  const held = target !== null && !switching && holdsDocument(target)
  const foreign = target !== null && !switching && !held

  useEffect(
    () =>
      onUniverseRefused((message) =>
        toast.error(message, { id: REFUSAL_TOAST })
      ),
    []
  )
  useEffect(() => {
    if (switching) chooseUniverse(target)
  }, [switching, target])
  useEffect(() => {
    if (foreign) window.location.reload()
  }, [foreign])

  if (target === null) return <Navigate to='/' replace />
  if (!held) return <EnteringUniverse />
  return (
    <QueryClientProvider key={target} client={queryClientFor(target)}>
      <RealtimeProvider createSource={createSource}>
        {children}
      </RealtimeProvider>
    </QueryClientProvider>
  )
}

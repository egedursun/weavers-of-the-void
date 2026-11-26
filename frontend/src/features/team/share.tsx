import { useId } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Share2 } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { useMutation } from '@/api/mutation'
import { queryKeys } from '@/api/queryKeys'
import { Switch } from '@/components/ui/switch'
import { FieldTile } from '@/components/domain/FieldTile'
import { Label } from '@/components/typography'
import { AuthorMark } from './AuthorMark'

export type ShareKind = 'session' | 'plan' | 'forecast' | 'writing' | 'presence'

const NOUN: Record<ShareKind, string> = {
  session: 'session',
  plan: 'plan',
  forecast: 'forecast',
  writing: 'writing',
  presence: 'conversation',
}

function send(kind: ShareKind, id: number, shared: boolean) {
  const body = { shared }
  switch (kind) {
    case 'session':
      return unwrap(
        api.PATCH('/api/divine-will/sessions/{session_id}', {
          params: { path: { session_id: id } },
          body,
        })
      )
    case 'plan':
      return unwrap(
        api.PATCH('/api/divine-will/plans/{plan_id}', {
          params: { path: { plan_id: id } },
          body,
        })
      )
    case 'forecast':
      return unwrap(
        api.PATCH('/api/divine-will/forecasts/{forecast_id}', {
          params: { path: { forecast_id: id } },
          body,
        })
      )
    case 'writing':
      return unwrap(
        api.PATCH('/api/divine-will/artifacts/{artifact_id}', {
          params: { path: { artifact_id: id } },
          body,
        })
      )
    case 'presence':
      return unwrap(
        api.PATCH('/api/presence/sessions/{session_id}', {
          params: { path: { session_id: id } },
          body,
        })
      )
  }
}

function useShare(kind: ShareKind) {
  const client = useQueryClient()
  return useMutation({
    writes: [
      { method: 'PATCH', path: '/api/divine-will/sessions/{session_id}' },
      { method: 'PATCH', path: '/api/divine-will/plans/{plan_id}' },
      { method: 'PATCH', path: '/api/divine-will/forecasts/{forecast_id}' },
      { method: 'PATCH', path: '/api/divine-will/artifacts/{artifact_id}' },
      { method: 'PATCH', path: '/api/presence/sessions/{session_id}' },
    ],
    mutationFn: async ({ id, shared }: { id: number; shared: boolean }) => {
      await send(kind, id, shared)
    },
    onSuccess: (_result, { shared }) => {
      toast.success(
        shared
          ? `The ${NOUN[kind]} is shared with the team`
          : `The ${NOUN[kind]} is yours alone again`
      )
      void client.invalidateQueries({
        queryKey:
          kind === 'presence'
            ? queryKeys.presence.all
            : queryKeys.divineWill.all,
      })
    },
    onError: (error) => toast.error(error.message),
  })
}

export function ShareToggle({
  kind,
  id,
  shared,
  mine,
  author,
  inline = false,
}: {
  kind: ShareKind
  id: number
  shared: boolean
  mine: boolean
  author: string | null | undefined
  inline?: boolean
}) {
  const share = useShare(kind)
  const switchId = useId()
  if (!mine) return <AuthorMark name={author} verb='Shared by' />
  if (inline)
    return (
      <div data-presence='free' className='shrink-0'>
        <FieldTile
          id={switchId}
          label={shared ? 'Shared' : 'Only you'}
          icon={Share2}
        >
          <Switch
            id={switchId}
            act={share}
            checked={shared}
            disabled={share.isPending}
            onCheckedChange={(next) => share.mutate({ id, shared: next })}
            aria-label={`Share this ${NOUN[kind]} with the team`}
          />
        </FieldTile>
      </div>
    )
  return (
    <div
      data-presence='free'
      className='flex shrink-0 items-center gap-2 rounded-md surface-sheen px-2 py-1'
    >
      <Share2 aria-hidden='true' className='size-icon-sm text-primary' />
      <Label htmlFor={switchId}>Shared with the team</Label>
      <Switch
        id={switchId}
        act={share}
        checked={shared}
        disabled={share.isPending}
        onCheckedChange={(next) => share.mutate({ id, shared: next })}
        aria-label={`Share this ${NOUN[kind]} with the team`}
      />
    </div>
  )
}

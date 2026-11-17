import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type FateControls = components['schemas']['FateControlsView']
export type LimboRecord = components['schemas']['LimboRecord']
export type StepState = components['schemas']['FateStepState']
export type HistorianView = components['schemas']['HistorianViewItem']
export type VerdictChoice = components['schemas']['VerdictChoice']
export type ActionResponse = components['schemas']['ActionResponse']

export const fateKeys = {
  controls: [...queryKeys.world.all, 'fate', 'controls'] as const,
}

export function useFateControls() {
  return useQuery({
    queryKey: fateKeys.controls,
    queryFn: () => unwrap(api.GET('/api/fate/controls')),
  })
}

export type FateJobAction =
  | 'fate:retry'
  | 'fate:rejudge_debt'
  | 'fate:rejudge_limbo'
  | 'voices:retry'
  | 'births:retry'

export const FATE_JOB_RUNNERS: Record<
  FateJobAction,
  () => Promise<ActionResponse>
> = {
  'fate:retry': () => unwrap(api.POST('/api/actions/fate:retry')),
  'fate:rejudge_debt': () => unwrap(api.POST('/api/actions/fate:rejudge_debt')),
  'fate:rejudge_limbo': () =>
    unwrap(api.POST('/api/actions/fate:rejudge_limbo')),
  'voices:retry': () => unwrap(api.POST('/api/actions/voices:retry')),
  'births:retry': () => unwrap(api.POST('/api/actions/births:retry')),
}

export type OverrideRequest = {
  entityId: number
  choice: VerdictChoice
  rationale: string
}

export function overrideVerdict(request: OverrideRequest) {
  return unwrap(
    api.POST('/api/actions/fate:override_verdict', {
      body: {
        entity_id: request.entityId,
        choice: request.choice,
        rationale: request.rationale.trim() === '' ? null : request.rationale,
      },
    })
  )
}

export function editHistorianView(change: { viewId: number; text: string }) {
  return unwrap(
    api.POST('/api/actions/voices:edit_view', {
      body: { view_id: change.viewId, text: change.text },
    })
  )
}

export function deleteHistorianView(viewId: number) {
  return unwrap(
    api.POST('/api/actions/voices:delete_view', { body: { view_id: viewId } })
  )
}

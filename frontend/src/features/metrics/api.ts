import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type ModelMetricsView = components['schemas']['ModelMetricsView']
export type StepMetrics = components['schemas']['StepMetrics']
export type LlmCall = components['schemas']['LlmCall']

export const metricsKeys = {
  models: (epochs: number | null) =>
    [...queryKeys.metrics.all, 'models', epochs ?? 'default'] as const,
}

export function useModelMetrics(epochs: number | null) {
  return useQuery({
    queryKey: metricsKeys.models(epochs),
    placeholderData: keepPreviousData,
    queryFn: () =>
      unwrap(
        api.GET('/api/metrics/models', {
          params: { query: epochs === null ? {} : { epochs } },
        })
      ),
  })
}

export function stepAverageMs(
  metrics: ModelMetricsView | undefined,
  needle: string
): number | null {
  const step = metrics?.steps.find((item) =>
    item.step.toLowerCase().includes(needle)
  )
  return step && step.calls > 0 ? step.average_ms : null
}

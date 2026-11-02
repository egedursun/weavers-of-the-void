import { api } from './client'
import { unwrap } from './errors'
import { type components } from './generated/schema'

export type Health = components['schemas']['HealthResponse']
export type Job = components['schemas']['JobResponse']

export function fetchHealth(): Promise<Health> {
  return unwrap(api.GET('/api/health'))
}

export function fetchJobs(limit: number): Promise<Job[]> {
  return unwrap(api.GET('/api/jobs', { params: { query: { limit } } }))
}

export function fetchJob(jobId: string): Promise<Job> {
  return unwrap(
    api.GET('/api/jobs/{job_id}', { params: { path: { job_id: jobId } } })
  )
}

export function cancelJob(jobId: string): Promise<unknown> {
  return unwrap(
    api.POST('/api/jobs/{job_id}/cancel', {
      params: { path: { job_id: jobId } },
    })
  )
}

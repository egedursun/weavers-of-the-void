import { APP_VERSION } from './appVersion'
import { mechanicsResponse } from './mechanicsMocks'
import { type Page, type Route } from '@playwright/test'
import { controlsResponse } from './controlsMocks'
import { cosmosResponse } from './cosmosMocks'
import { fateResponse } from './fateMocks'
import { godResponse } from './godMocks'
import { LORE_PIXEL, loreResponse } from './loreMocks'
import { maintenanceResponse } from './maintenanceMocks'
import { mapGraphResponse } from './mapGraphMocks'
import { promptResponse } from './promptMocks'
import { warsResponse } from './warsMocks'
import { type RunWorldVariant, runWorldResponse } from './runWorldMocks'

const NOW = '2026-01-01T12:00:00+00:00'

export const HEALTH = {
  status: 'ok',
  version: APP_VERSION,
  database_ok: true,
  llm_enabled: false,
  gateway_ready: false,
  running_jobs: 1,
}

export const JOBS = [
  {
    id: 'job-epoch',
    kind: 'epoch',
    status: 'running',
    progress: 0.42,
    stage: 'Sons are acting',
    params: {},
    result: null,
    error: null,
    created_at: NOW,
    started_at: NOW,
    finished_at: null,
  },
  {
    id: 'job-backup',
    kind: 'backup',
    status: 'failed',
    progress: 0.6,
    stage: null,
    params: {},
    result: null,
    error: 'The disk is full.',
    created_at: NOW,
    started_at: NOW,
    finished_at: NOW,
  },
]

const EVENTS = [
  { id: 1, kind: 'job.queued', payload: { job_id: 'job-epoch', kind: 'epoch' }, at: NOW },
  { id: 2, kind: 'job.started', payload: { job_id: 'job-epoch', kind: 'epoch' }, at: NOW },
  {
    id: 3,
    kind: 'job.failed',
    payload: { job_id: 'job-backup', kind: 'backup', error: 'The disk is full.' },
    at: NOW,
  },
]

const RETRY_MS = 3_600_000

function eventStreamBody(): string {
  const frames = EVENTS.map(
    (event) => `id: ${event.id}\nevent: ${event.kind}\ndata: ${JSON.stringify(event)}\n\n`
  )
  return [`retry: ${RETRY_MS}\n\n`, ...frames].join('')
}

export const MOCK_VARIANT_COOKIE = 'aerona-mock'

function mockVariant(route: Route): RunWorldVariant {
  const cookie = route.request().headers()['cookie'] ?? ''
  const match = new RegExp(`${MOCK_VARIANT_COOKIE}=([a-z-]+)`).exec(cookie)
  const value = match?.[1]
  return value === 'empty' || value === 'llm-off' || value === 'discovery' ? value : 'default'
}

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
}

export async function mockApi(page: Page): Promise<void> {
  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    if (path === '/api/health') return json(route, HEALTH)
    if (path === '/api/jobs') return json(route, JOBS)
    if (path === '/api/events') {
      return route.fulfill({
        status: 200,
        headers: { 'content-type': 'text/event-stream', 'cache-control': 'no-cache' },
        body: eventStreamBody(),
      })
    }
    const job = JOBS.find((item) => path === `/api/jobs/${item.id}`)
    if (job) return json(route, job)
    if (path.startsWith('/api/media/'))
      return route.fulfill({ status: 200, contentType: 'image/png', body: LORE_PIXEL })
    const operator = fateResponse(route.request().method(), url, route.request().headers().referer) ?? promptResponse(route.request().method(), url) ?? maintenanceResponse(route.request().method(), url)
    if (operator !== undefined) return json(route, operator)
    const wars = warsResponse(route.request().method(), url)
    if (wars !== undefined) return json(route, wars)
    const controls = controlsResponse(route.request().method(), url)
    if (controls !== undefined) return json(route, controls)
    const lore = loreResponse(route.request().method(), url, route.request().headers().referer)
    if (lore !== undefined) return json(route, lore)
    const cosmos = cosmosResponse(route.request().method(), url, route.request().headers().referer)
    if (cosmos !== undefined) return json(route, cosmos)
    const runWorld = runWorldResponse(route.request().method(), url, mockVariant(route))
    if (runWorld !== undefined) return json(route, runWorld)
    const god = godResponse(route.request().method(), url)
    if (god !== undefined) return json(route, god)
    const mechanics = mechanicsResponse(route.request().method(), url)
    if (mechanics !== undefined) return json(route, mechanics)
    const mapGraph = mapGraphResponse(route.request().method(), url)
    if (mapGraph !== undefined) return json(route, mapGraph)
    return json(route, { detail: 'Not found' }, 404)
  })
}

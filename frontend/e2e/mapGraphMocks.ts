import { readFileSync } from 'node:fs'
import path from 'node:path'

type Fixture = Record<string, unknown> & {
  map: Record<string, unknown> & { time: Record<string, unknown> }
}

const FIXTURE: Fixture = JSON.parse(
  readFileSync(path.resolve(import.meta.dirname, 'fixtures/mapGraph.json'), 'utf8')
)

const ACCEPTED = {
  action: 'world:map',
  message: 'The map was redrawn.',
  essence_spent: 0,
  essence_gained: 0,
}

export function mapGraphResponse(method: string, url: URL): unknown {
  const route = url.pathname
  if (method !== 'GET') {
    if (route.startsWith('/api/map-notes') || route.startsWith('/api/actions/world:map'))
      return ACCEPTED
    if (route === '/api/graph/repair') return { counters: { total: 0 }, ledger_entry_id: null }
    if (route === '/api/graph/fate-link') return { job_id: null, message: 'Fate is looking at the network.' }
    if (route === '/api/graph/fate-link/stop') return { stopped: true }
    return undefined
  }
  if (/^\/api\/worlds\/\d+\/map$/.test(route)) {
    const epoch = Number(url.searchParams.get('epoch'))
    if (!epoch) return FIXTURE.map
    return { ...FIXTURE.map, time: { ...FIXTURE.map.time, shown: epoch } }
  }
  const direct: Record<string, string> = {
    '/api/cosmos': 'cosmos',
    '/api/graph': 'graph',
    '/api/graph/health': 'health',
    '/api/graph/path': 'path',
    '/api/catalogue': 'catalogue',
    '/api/sons': 'sons',
    '/api/languages': 'languages',
    '/api/rules': 'rules',
  }
  const key = direct[route]
  return key ? FIXTURE[key] : undefined
}

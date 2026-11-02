import { readFileSync } from 'node:fs'
import path from 'node:path'

type CosmosFixture = {
  cosmos: unknown
  discovery: unknown
  guide: unknown
  rules: unknown
}

const FIXTURE: CosmosFixture = JSON.parse(
  readFileSync(path.resolve(import.meta.dirname, 'fixtures/cosmos.json'), 'utf8')
)

const ACCEPTED = {
  action: 'cosmic',
  message: 'The sky obeyed.',
  essence_spent: 0,
  essence_gained: 0,
  target_node_id: null,
  created_ids: [],
  ledger_entry_id: null,
  values: {},
  job_id: null,
}

const COSMIC_WRITES = /^\/api\/(worlds|stars|routes|voyages|climate|cosmic|cosmic-resource|federations)(\/|$)/

function onCosmosScreen(referer: string | undefined): boolean {
  if (!referer) return false
  return new URL(referer).pathname.startsWith('/cosmos')
}

export function cosmosResponse(method: string, url: URL, referer: string | undefined): unknown {
  const route = url.pathname
  if (method !== 'GET') return COSMIC_WRITES.test(route) ? ACCEPTED : undefined
  if (route === '/api/discovery-summary') return FIXTURE.discovery
  if (/^\/api\/worlds\/\d+\/guide$/.test(route)) return FIXTURE.guide
  if (route === '/api/cosmos') return FIXTURE.cosmos
  if (!onCosmosScreen(referer)) return undefined
  if (route === '/api/rules') return FIXTURE.rules
  return undefined
}

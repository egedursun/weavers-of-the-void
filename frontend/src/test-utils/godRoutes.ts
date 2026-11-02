import { godResponse } from '../../e2e/godMocks'
import { type MockRequest, type MockRoutes, failure } from './mockServer'

const METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'] as const
const DEPTHS = ['{a}', '{a}/{b}', '{a}/{b}/{c}', '{a}/{b}/{c}/{d}']

function fromGodMocks(request: MockRequest) {
  const url = new URL(`http://mock${request.path}?${request.query.toString()}`)
  const reply = godResponse(request.method, url)
  return reply === undefined ? failure(404, 'Not found') : reply
}

export function godRoutes(overrides: MockRoutes = {}): MockRoutes {
  const routes: MockRoutes = {
    'GET /api/jobs': [],
    'GET /api/health': { status: 'ok', llm_enabled: true },
    ...overrides,
  }
  for (const method of METHODS)
    for (const depth of DEPTHS) routes[`${method} /api/${depth}`] = fromGodMocks
  return routes
}

export function godData(path: string): Record<string, unknown> {
  return godResponse('GET', new URL(`http://mock${path}`)) as Record<string, unknown>
}

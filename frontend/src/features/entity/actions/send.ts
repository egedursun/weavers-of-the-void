import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type ActionResponse } from '../api/types'
import { type ActionRoute } from './registry'
import { type FieldValue } from './schema'

const ENTITY_PREFIX = '/api/entities/{entity_id}/'

export function usesPathParam(route: ActionRoute): boolean {
  return route.path.startsWith(ENTITY_PREFIX)
}

export async function sendAction(
  route: ActionRoute,
  entityId: number,
  self: string | null,
  body: Record<string, FieldValue>
): Promise<ActionResponse> {
  if (usesPathParam(route)) {
    const init = {
      params: { path: { entity_id: entityId } },
      body,
    } as never
    const path = route.path as never
    if (route.method === 'PUT') return unwrap(api.PUT(path, init))
    if (route.method === 'PATCH') return unwrap(api.PATCH(path, init))
    return unwrap(api.POST(path, init))
  }
  return unwrap(
    api.POST(
      route.path as never,
      {
        body: self === null ? body : { ...body, [self]: entityId },
      } as never
    )
  )
}

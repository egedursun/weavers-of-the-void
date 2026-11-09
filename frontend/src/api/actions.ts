import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { paths } from '@/api/generated/schema'

type ActionPath = Extract<keyof paths, `/api/actions/${string}`>

export type ActionName = ActionPath extends `/api/actions/${infer Name}`
  ? Name
  : never

type BodyOf<Operation> = Operation extends {
  requestBody?: { content: { 'application/json': infer Body } }
}
  ? { [Key in keyof Body]?: Body[Key] }
  : never

export type ActionBody<Name extends ActionName> = Name extends ActionName
  ? BodyOf<paths[`/api/actions/${Name}`]['post']>
  : never

export type EditValues = Record<string, string | number | boolean | null>

export function postAction<Name extends ActionName>(
  name: Name,
  body: ActionBody<Name>
) {
  return unwrap(
    api.POST(`/api/actions/${name}` as '/api/actions/galaxy:create', {
      body: body as never,
    })
  )
}

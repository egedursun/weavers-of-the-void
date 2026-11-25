import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type CustomsNodeView = Schema['CustomsNodeView']

export const customsKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'customs-of', nodeId] as const,
}

export function useNodeCustoms(nodeId: number) {
  return useQuery({
    queryKey: customsKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/customs/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type CustomsAction =
  | 'revival:create'
  | 'revival:edit'
  | 'revival:delete'
  | 'intoxicant_custom:set'
  | 'intoxicant_custom:edit'
  | 'intoxicant_custom:delete'
  | 'mark_custom:set'
  | 'mark_custom:edit'
  | 'mark_custom:delete'
  | 'body_mark:create'
  | 'body_mark:edit'
  | 'body_mark:delete'
  | 'time_budget:set'
  | 'time_budget:edit'
  | 'time_budget:delete'
  | 'naming_custom:set'
  | 'naming_custom:edit'
  | 'naming_custom:delete'
  | 'name_form:set'
  | 'name_form:edit'
  | 'name_form:delete'
  | 'grade_duty:set'
  | 'grade_duty:edit'
  | 'grade_duty:delete'
  | 'age_set:create'
  | 'age_set:edit'
  | 'age_set:delete'
  | 'age_set_member:set'
  | 'age_set_member:edit'
  | 'age_set_member:delete'
  | 'tavern:set'
  | 'tavern:edit'
  | 'tavern:delete'
  | 'welfare_house:set'
  | 'welfare_house:edit'
  | 'welfare_house:delete'
  | 'commute:set'
  | 'commute:edit'
  | 'commute:delete'
  | 'cooperative:set'
  | 'cooperative:edit'
  | 'cooperative:delete'
  | 'evidence:create'
  | 'evidence:edit'
  | 'evidence:delete'
  | 'membership_category:set'
  | 'membership_category:edit'
  | 'membership_category:delete'
  | 'membership:set'
  | 'membership:edit'
  | 'membership:delete'
  | 'border_control:set'
  | 'border_control:edit'
  | 'border_control:delete'
  | 'poor_relief:set'
  | 'poor_relief:edit'
  | 'poor_relief:delete'
  | 'measure_standard:set'
  | 'measure_standard:edit'
  | 'measure_standard:delete'
  | 'membership_category:right'
  | 'town_life:run'
  | 'civics:run'
  | 'age_set:run'

export function useCustomsAction<Name extends CustomsAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    writes: [{ lever: name }],
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}

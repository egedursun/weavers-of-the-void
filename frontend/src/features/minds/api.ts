import { useQuery } from '@tanstack/react-query'
import {
  type ActionBody,
  type ActionName,
  type EditValues,
  postAction,
} from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type MindNodeView = Schema['MindNodeView']
export type MindStateView = Schema['MindStateView']
export type NetworkNodeView = Schema['NetworkNodeView']
export type NetworkMemberView = Schema['NetworkMemberView']
export type AugmentsNodeView = Schema['AugmentsNodeView']
export type AugmentView = Schema['AugmentView']
export type MadeWorldNodeView = Schema['MadeWorldNodeView']
export type ReplicatorLineView = Schema['ReplicatorLineView']
export type MadeRealmView = Schema['MadeRealmView']
export type DataStoreView = Schema['DataStoreView']

const keys = {
  mind: (nodeId: number) =>
    [...queryKeys.world.all, 'mind-of', nodeId] as const,
  networks: (nodeId: number) =>
    [...queryKeys.world.all, 'networks-of', nodeId] as const,
  augments: (nodeId: number) =>
    [...queryKeys.world.all, 'augments-of', nodeId] as const,
  madeWorld: (nodeId: number) =>
    [...queryKeys.world.all, 'made-world-of', nodeId] as const,
}

export function useNodeMind(nodeId: number) {
  return useQuery({
    queryKey: keys.mind(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/minds/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useNodeNetworks(nodeId: number) {
  return useQuery({
    queryKey: keys.networks(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/networks/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useNodeAugments(nodeId: number) {
  return useQuery({
    queryKey: keys.augments(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/augments/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useNodeMadeWorld(nodeId: number) {
  return useQuery({
    queryKey: keys.madeWorld(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/made-world/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useMadeAction<Name extends ActionName, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}

export type RowKey = Record<string, number | string>

export function useProfileEdit(nodeId: number, table: string) {
  return useGodAction<{ values: EditValues; release: string[] }>({
    run: async ({ values, release }) => {
      const sets = Object.entries(values).map(
        ([column, value]) =>
          () =>
            postAction('profile:set', {
              node_id: nodeId,
              table,
              column,
              value,
              hold: true,
            })
      )
      const releases = release.map(
        (column) => () =>
          postAction('profile:release', { node_id: nodeId, table, column })
      )
      const steps = [...sets, ...releases]
      if (!steps.length) throw new Error('Nothing was changed')
      let last = await steps[0]()
      for (const step of steps.slice(1)) last = await step()
      return last
    },
    success: 'The values are set and held',
  })
}

export function useRowEdit(table: string, key: RowKey) {
  return useGodAction<{ values: EditValues; release: string[] }>({
    run: ({ values, release }) =>
      postAction('record_row:edit', {
        table,
        key,
        values,
        hold: Object.keys(values).length > 0,
        release,
      }),
    success: 'The row keeps its new values and is held',
  })
}

export function useRowDelete(table: string, key: RowKey) {
  return useGodAction<void>({
    run: () => postAction('record_row:delete', { table, key }),
    success: 'The row is struck out',
  })
}

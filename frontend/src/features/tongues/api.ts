import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type NodeTonguesView = Schema['NodeTonguesView']
export type TongueMechanicsView = Schema['TongueMechanicsView']
export type SoundChangeView = Schema['SoundChangeView']
export type TongueGrammarView = Schema['TongueGrammarView']
export type ScriptView = Schema['ScriptView']
export type DecipherView = Schema['DecipherView']
export type PolicyView = Schema['PolicyView']
export type ShiftView = Schema['MeaningShiftView']
export type DivineTongueView = Schema['DivineTongueView']
export type SoundChangeKind = Schema['SoundChangeKind']
export type SoundEnvironment = Schema['SoundEnvironment']
export type LanguagePolicy = Schema['LanguagePolicy']
export type WritingSystem = Schema['WritingSystem']
export type ScriptChangeCause = Schema['ScriptChangeCause']

export const tongueKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'tongues-of', nodeId] as const,
  scripts: () => [...queryKeys.world.all, 'scripts'] as const,
}

export function useNodeTongues(nodeId: number) {
  return useQuery({
    queryKey: tongueKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/tongues/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useScripts() {
  return useQuery({
    queryKey: tongueKeys.scripts(),
    queryFn: () => unwrap(api.GET('/api/tongues/scripts')),
  })
}

export type TongueAction =
  | 'sound_change:add'
  | 'sound_change:edit'
  | 'sound_change:delete'
  | 'grammar:edit'
  | 'grammar:reset'
  | 'tongue:edit'
  | 'word:register'
  | 'word:veil'
  | 'meaning_shift:edit'
  | 'meaning_shift:delete'
  | 'script:create'
  | 'script:edit'
  | 'script:delete'
  | 'script:assign'
  | 'decipherment:start'
  | 'decipherment:edit'
  | 'decipherment:delete'
  | 'language_policy:set'
  | 'language_policy:edit'
  | 'language_policy:delete'
  | 'divine_tongue:set'
  | 'divine_tongue:edit'
  | 'divine_tongue:delete'
  | 'divine_tongue:teach'
  | 'pidgin:make'

export function useTongueAction<Name extends TongueAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}

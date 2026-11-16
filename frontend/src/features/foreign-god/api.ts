import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type ForeignGodDetail = components['schemas']['ForeignGodDetail']
export type ForeignGodRecord = components['schemas']['ForeignGodRecord']
export type ForeignEditBody = components['schemas']['PatchForeignGodsGodIdBody']
export type ForeignPowerEffect = components['schemas']['ForeignGodPowerEffect']

export const foreignKeys = {
  detail: (godId: number) =>
    [...queryKeys.world.all, 'foreign-god', godId] as const,
}

export function useForeignGod(godId: number) {
  return useQuery({
    queryKey: foreignKeys.detail(godId),
    queryFn: () =>
      unwrap(
        api.GET('/api/foreign-gods/{god_id}', {
          params: { path: { god_id: godId } },
        })
      ),
    enabled: Number.isInteger(godId) && godId > 0,
  })
}

export function editForeignGod(godId: number, body: ForeignEditBody) {
  return unwrap(
    api.PATCH('/api/foreign-gods/{god_id}', {
      params: { path: { god_id: godId } },
      body,
    })
  )
}

export const FOREIGN_EFFECT_LABEL: Record<ForeignPowerEffect, string> = {
  shield: 'Shield: harder to defeat in war',
  caller: 'Caller: draws worshippers',
  thief: 'Thief: steals worshippers',
  destroyer: 'Destroyer: strikes more often',
  fertile: 'Fertile: worshippers prosper',
  reviving: 'Reviving: wakes sooner after defeat',
  deathless: 'Deathless: costs twice as much to kill',
  persuasion: 'Persuasive: hard to talk down',
}

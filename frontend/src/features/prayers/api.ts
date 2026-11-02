import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type PrayerView = components['schemas']['PrayerView']
export type PrayerRequest = components['schemas']['PrayerRequest']

export const prayerKeys = {
  list: [...queryKeys.world.all, 'prayers'] as const,
}

export function usePrayers() {
  return useQuery({
    queryKey: prayerKeys.list,
    queryFn: () => unwrap(api.GET('/api/prayers')),
  })
}

export const WISH_LABEL: Record<PrayerRequest, string | null> = {
  essence: 'Essence',
  blessing: 'Blessing',
  permission: 'Permission',
  vengeance: 'Revenge',
  forgiveness: 'Forgiveness',
  wish: 'A wish',
  none: null,
}

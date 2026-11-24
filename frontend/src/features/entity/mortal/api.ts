import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '../api/keys'

export type MortalProfile = components['schemas']['MortalProfileView']
export type FamilyTree = components['schemas']['FamilyTreeView']
export type TreePerson = components['schemas']['TreePerson']
export type TreeUnion = components['schemas']['TreeUnion']
export type TreeTie = components['schemas']['TreeTie']
export type TreeHouse = components['schemas']['TreeHouse']
export type ArmsInk = components['schemas']['ArmsInk']
export type KinLink = components['schemas']['KinLink']
export type Marriage = components['schemas']['MarriageView']
export type Slot = components['schemas']['SlotView']
export type EquipmentSlot = components['schemas']['EquipmentSlot']
export type CrimeKind = components['schemas']['CrimeKind']
export type PunishmentKind = components['schemas']['PunishmentKind']
export type UnionForm = components['schemas']['UnionForm']
export type UnionPurpose = components['schemas']['UnionPurpose']
export type MarriageEnd = components['schemas']['MarriageEnd']
export type MortalSex = components['schemas']['SexKind']

export function profileKey(mortalId: number) {
  return [...loreKeys.entity(mortalId), 'mortal-profile'] as const
}

export function familyKey(mortalId: number) {
  return [...loreKeys.entity(mortalId), 'family'] as const
}

export function useMortalProfile(mortalId: number) {
  return useQuery({
    queryKey: profileKey(mortalId),
    queryFn: () =>
      unwrap(
        api.GET('/api/mortals/{mortal_id}/profile', {
          params: { path: { mortal_id: mortalId } },
        })
      ),
    retry: false,
  })
}

export type FamilyReach = { up: number; down: number }
export type CareBond = 'fostered_by' | 'godparent_of' | 'sworn_kin'

export function useFamilyTree(
  mortalId: number,
  reach: FamilyReach,
  hide: CareBond[] = []
) {
  return useQuery({
    queryKey: [...familyKey(mortalId), reach.up, reach.down, ...hide],
    queryFn: () =>
      unwrap(
        api.GET('/api/mortals/{mortal_id}/family', {
          params: {
            path: { mortal_id: mortalId },
            query: { up: reach.up, down: reach.down, hide },
          },
        })
      ),
    placeholderData: (previous) => previous,
    retry: false,
  })
}

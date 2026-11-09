import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '../api/keys'

export type MortalProfile = components['schemas']['MortalProfileView']
export type FamilyTree = components['schemas']['FamilyTreeView']
export type TreePerson = components['schemas']['TreePerson']
export type KinLink = components['schemas']['KinLink']
export type Marriage = components['schemas']['MarriageView']
export type Slot = components['schemas']['SlotView']
export type Ability = components['schemas']['Ability']
export type EquipmentSlot = components['schemas']['EquipmentSlot']
export type CrimeKind = components['schemas']['CrimeKind']
export type PunishmentKind = components['schemas']['PunishmentKind']
export type MarriageKind = components['schemas']['MarriageKind']
export type MarriageEnd = components['schemas']['MarriageEnd']
export type MortalSex = components['schemas']['MortalSex']

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

export function useFamilyTree(mortalId: number) {
  return useQuery({
    queryKey: familyKey(mortalId),
    queryFn: () =>
      unwrap(
        api.GET('/api/mortals/{mortal_id}/family', {
          params: { path: { mortal_id: mortalId } },
        })
      ),
    retry: false,
  })
}

export function generationsOf(people: TreePerson[]): TreePerson[][] {
  const levels = [...new Set(people.map((person) => person.generation))].sort(
    (first, second) => first - second
  )
  return levels.map((level) =>
    people
      .filter((person) => person.generation === level)
      .sort((first, second) => first.id - second.id)
  )
}

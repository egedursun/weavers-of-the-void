import { Swords } from 'lucide-react'
import { useUnitKinds } from './api'
import { FAMILY, UNIT_ICON } from './labels'

export function useKindTable() {
  const kinds = useUnitKinds()
  const table = Object.fromEntries(
    (kinds.data ?? []).map((spec) => [
      spec.kind,
      {
        label: spec.label,
        icon: UNIT_ICON[spec.kind] ?? Swords,
        tone: FAMILY[spec.family]?.tone ?? ('muted' as const),
      },
    ])
  )
  return { table, specs: kinds.data ?? [] }
}

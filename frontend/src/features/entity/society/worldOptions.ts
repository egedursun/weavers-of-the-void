import { useMemo } from 'react'
import { useNames } from '../api/queries'
import { fieldLabel } from './labels'

export function useWorldOptions(anchorId: number) {
  const names = useNames()
  return useMemo(() => {
    const entries = names.data ?? []
    const world =
      entries.find((entry) => entry.id === anchorId)?.world_id ?? null
    const local = entries.filter(
      (entry) =>
        entry.kind === 'entity' && (world === null || entry.world_id === world)
    )
    const pick = (types: string[]) =>
      local
        .filter((entry) => types.includes(entry.type ?? ''))
        .map((entry) => ({
          value: String(entry.id),
          label: entry.name,
          hint: fieldLabel(entry.type ?? ''),
        }))
    return {
      lands: pick(['region']),
      species: pick(['species']),
      communities: pick(['people', 'settlement', 'faction', 'cult']),
      targets: pick(['region', 'people', 'settlement', 'faction', 'cult']),
    }
  }, [names.data, anchorId])
}

import { useMemo } from 'react'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { type NameEntry, useNames } from './api'
import { humanize } from './labels'

type NamePickerProps = {
  id?: string
  value: string | null
  onChange: (value: string | null, entry: NameEntry | null) => void
  placeholder?: string
  kinds?: NameEntry['kind'][]
  exclude?: number[]
  worldId?: number | null
  types?: string[]
}

export function NamePicker({
  id,
  value,
  onChange,
  placeholder = 'Pick a record',
  kinds,
  exclude = [],
  worldId,
  types,
}: NamePickerProps) {
  const names = useNames()
  const entries = useMemo(
    () =>
      (names.data ?? []).filter(
        (entry) =>
          (!kinds || kinds.includes(entry.kind)) &&
          (!types || types.includes(entry.type)) &&
          (worldId === undefined ||
            worldId === null ||
            entry.world_id === worldId) &&
          !exclude.includes(entry.id)
      ),
    [names.data, kinds, exclude, worldId, types]
  )
  const options = useMemo(
    () =>
      entries.map((entry) => ({
        value: String(entry.id),
        label: entry.name,
        hint: humanize(entry.type || entry.kind),
      })),
    [entries]
  )
  return (
    <RecordCombobox
      id={id}
      options={options}
      value={value}
      placeholder={names.isPending ? 'Loading names...' : placeholder}
      disabled={names.isPending}
      disabledReason='Names are loading.'
      onChange={(next) =>
        onChange(
          next,
          entries.find((entry) => String(entry.id) === next) ?? null
        )
      }
    />
  )
}

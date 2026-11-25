import { useMemo, useState } from 'react'
import { Check, ChevronsUpDown } from 'lucide-react'
import { type ActProp } from '@/api/mutation'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { type NameEntry, useNames } from './api'
import { humanize } from './model/labels'

const LIST_LIMIT = 200
const LIVING_STATUS = 'canon'

type EntityPickerProps = {
  id?: string
  types: readonly string[]
  value: number | null
  onChange: (id: number | null) => void
  placeholder: string
  worldId?: number
  worldName?: (id: number | null | undefined) => string
  includeDead?: boolean
}

export function EntityPicker({
  id,
  types,
  value,
  onChange,
  placeholder,
  worldId,
  worldName,
  includeDead = false,
  act,
}: EntityPickerProps & { act?: ActProp }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const { data, isLoading } = useNames()
  const options = useMemo(() => {
    const wanted = new Set(types)
    return (data ?? []).filter(
      (entry: NameEntry) =>
        entry.kind === 'entity' &&
        wanted.has(entry.type) &&
        (includeDead || !entry.status || entry.status === LIVING_STATUS) &&
        (worldId === undefined || entry.world_id === worldId)
    )
  }, [data, types, worldId, includeDead])
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase()
    const matching = needle
      ? options.filter((entry) => entry.name.toLowerCase().includes(needle))
      : options
    return matching.slice(0, LIST_LIMIT)
  }, [options, query])
  const selected = options.find((entry) => entry.id === value)
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id={id}
          variant='field'
          role='combobox'
          aria-expanded={open}
          className='w-full justify-between'
        >
          {selected
            ? selected.name
            : isLoading
              ? 'Loading names…'
              : placeholder}
          <ChevronsUpDown className='opacity-50' />
        </Button>
      </PopoverTrigger>
      <PopoverContent align='start' className='p-0'>
        <Command shouldFilter={false}>
          <CommandInput
            placeholder='Search…'
            value={query}
            onValueChange={setQuery}
          />
          <CommandList>
            <CommandEmpty>Nothing matches.</CommandEmpty>
            <CommandGroup>
              {filtered.map((entry) => (
                <CommandItem
                  act={act}
                  key={entry.id}
                  value={String(entry.id)}
                  onSelect={() => {
                    onChange(entry.id === value ? null : entry.id)
                    setOpen(false)
                  }}
                >
                  <Check
                    className={entry.id === value ? 'opacity-100' : 'opacity-0'}
                  />
                  <span className='min-w-0 flex-1 truncate'>{entry.name}</span>
                  <span className='shrink-0 text-muted-foreground'>
                    {worldName &&
                    entry.world_id != null &&
                    worldId === undefined
                      ? `${humanize(entry.type)} · ${worldName(entry.world_id)}`
                      : humanize(entry.type)}
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}

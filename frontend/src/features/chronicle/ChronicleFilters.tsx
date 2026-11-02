import { useEffect, useState } from 'react'
import { Filter, FolderOpen, Search, X } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ChronicleKindIcon } from '@/components/domain/ChronicleKindIcon'
import { MultiSelect } from '@/components/domain/MultiSelect'
import { Muted } from '@/components/typography'
import { DEFAULT_HIDDEN_KINDS } from './chronicleKinds'
import { type ChronicleSearch, kindSet } from './chronicleSearch'

const DEBOUNCE_MS = 250
const EVERY_WORLD = '__every__'

type ChronicleFiltersProps = {
  search: ChronicleSearch
  onChange: (patch: Partial<ChronicleSearch>) => void
  kinds: { key: string; label: string }[]
  worlds: { id: number; name: string }[]
  loaded: number
  epochs: number
  shown: number
}

export function ChronicleFilters({
  search,
  onChange,
  kinds,
  worlds,
  loaded,
  epochs,
  shown,
}: ChronicleFiltersProps) {
  const [text, setText] = useState(search.q ?? '')
  const [seen, setSeen] = useState(search.q ?? '')
  if ((search.q ?? '') !== seen) {
    setSeen(search.q ?? '')
    setText(search.q ?? '')
  }
  useEffect(() => {
    if (text === (search.q ?? '')) return
    const timer = window.setTimeout(
      () => onChange({ q: text || undefined }),
      DEBOUNCE_MS
    )
    return () => window.clearTimeout(timer)
  }, [text, search.q, onChange])
  const chosen = kindSet(search.kinds)
  const isOn = (key: string) =>
    chosen ? chosen.has(key) : !DEFAULT_HIDDEN_KINDS.has(key)
  return (
    <div data-chronicle-filters className='flex min-w-0 flex-col gap-3'>
      <div className='flex min-w-0 flex-col gap-2 sm:flex-row'>
        <Input
          type='search'
          leadingIcon={Search}
          placeholder='Search the chronicle'
          aria-label='Search the chronicle'
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
        {worlds.length > 1 && (
          <Select
            value={search.world ? String(search.world) : EVERY_WORLD}
            onValueChange={(value) =>
              onChange({
                world: value === EVERY_WORLD ? undefined : Number(value),
              })
            }
          >
            <SelectTrigger aria-label='World' className='w-full sm:w-56'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={EVERY_WORLD}>Every world</SelectItem>
              {worlds.map((world) => (
                <SelectItem key={world.id} value={String(world.id)}>
                  {world.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <MultiSelect
          label='Kinds'
          size='sm'
          icon={<Filter />}
          options={kinds.map((kind) => ({
            value: kind.key,
            label: kind.label,
            icon: <ChronicleKindIcon kind={kind.key} size='sm' />,
          }))}
          value={kinds.map((kind) => kind.key).filter(isOn)}
          onChange={(next) =>
            onChange({ kinds: [...next].sort().join(',') || undefined })
          }
          searchPlaceholder='Filter kinds'
          emptyText='No kind matches.'
        />
        {(search.q || search.kinds || search.world) && (
          <Button
            variant='ghost'
            size='sm'
            onClick={() => {
              setText('')
              onChange({ q: undefined, kinds: undefined, world: undefined })
            }}
          >
            <X />
            Clear
          </Button>
        )}
        <Button
          variant='outline'
          size='sm'
          disabled={search.all === true || loaded >= epochs}
          disabledReason='Every epoch is already open.'
          onClick={() => onChange({ all: true })}
        >
          <FolderOpen />
          Open every epoch
        </Button>
        <Muted as='span' variant='caption' aria-live='polite'>
          {`${formatInteger(shown)} records shown · ${formatInteger(loaded)} of ${formatInteger(epochs)} epochs read`}
        </Muted>
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import {
  ArrowDownWideNarrow,
  ArrowUpNarrowWide,
  History,
  ListTree,
  List,
  Search,
  Star,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Toggle } from '@/components/ui/toggle'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { Muted } from '@/components/typography'
import { type EntityTypeInfo } from '@/features/entity/api/types'
import {
  ATLAS_SORTS,
  ATLAS_STATUSES,
  type AtlasSearch,
  type AtlasSort,
  type AtlasStatus,
  type AtlasView,
} from './atlasSearch'

const SEARCH_DEBOUNCE_MS = 250
const ALL = '__all__'

const STATUS_LABEL: Record<AtlasStatus, string> = {
  visible: 'In the world',
  canon: 'Living canon',
  dead: 'Dead',
  destroyed: 'Destroyed',
  fulfilled: 'Fulfilled',
  rejected: 'Rejected by Fate',
}

const SORT_LABEL: Record<AtlasSort, string> = {
  name: 'Name',
  type: 'Kind',
  epoch: 'Epoch',
  power: 'Power',
  importance: 'Importance',
}

type AtlasFiltersProps = {
  search: AtlasSearch
  onChange: (patch: Partial<AtlasSearch>) => void
  types: EntityTypeInfo[]
  typeCounts: Map<string, number>
  matches: number
  view: AtlasView
}

export function AtlasFilters({
  search,
  onChange,
  types,
  typeCounts,
  matches,
  view,
}: AtlasFiltersProps) {
  const [text, setText] = useState(search.q ?? '')
  const [lastSeen, setLastSeen] = useState(search.q ?? '')
  if ((search.q ?? '') !== lastSeen) {
    setLastSeen(search.q ?? '')
    setText(search.q ?? '')
  }
  useEffect(() => {
    if (text === (search.q ?? '')) return
    const timer = window.setTimeout(
      () => onChange({ q: text || undefined, page: undefined }),
      SEARCH_DEBOUNCE_MS
    )
    return () => window.clearTimeout(timer)
  }, [text, search.q, onChange])
  return (
    <div data-atlas-filters className='flex min-w-0 flex-col gap-3'>
      <Input
        type='search'
        leadingIcon={Search}
        placeholder='Search names, kinds and titles'
        aria-label='Search the atlas'
        value={text}
        onChange={(event) => setText(event.target.value)}
      />
      <div className='grid min-w-0 grid-cols-1 gap-2 @xs/pane:grid-cols-2'>
        <Select
          value={search.type ?? ALL}
          onValueChange={(value) =>
            onChange({
              type: value === ALL ? undefined : value,
              page: undefined,
            })
          }
        >
          <SelectTrigger aria-label='Kind' className='w-full'>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Every kind</SelectItem>
            {types.map((type) => (
              <SelectItem key={type.key} value={type.key}>
                {`${type.plural} · ${formatInteger(typeCounts.get(type.key) ?? 0)}`}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={search.status ?? 'visible'}
          onValueChange={(value) =>
            onChange({
              status: value === 'visible' ? undefined : (value as AtlasStatus),
              page: undefined,
            })
          }
        >
          <SelectTrigger aria-label='Status' className='w-full'>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ATLAS_STATUSES.map((status) => (
              <SelectItem key={status} value={status}>
                {STATUS_LABEL[status]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <ToggleGroup
          type='single'
          variant='outline'
          size='sm'
          value={view}
          onValueChange={(value) =>
            value &&
            onChange({
              view: value === 'tree' ? undefined : (value as AtlasView),
              page: undefined,
            })
          }
          aria-label='Show as'
        >
          <ToggleGroupItem value='tree' aria-label='Tree'>
            <ListTree />
            Tree
          </ToggleGroupItem>
          <ToggleGroupItem value='list' aria-label='List'>
            <List />
            List
          </ToggleGroupItem>
        </ToggleGroup>
        <Toggle
          variant='outline'
          size='sm'
          pressed={search.favorites ?? false}
          onPressedChange={(pressed) =>
            onChange({ favorites: pressed || undefined, page: undefined })
          }
          aria-label='Favourites only'
        >
          <Star />
          Favourites
        </Toggle>
        <Toggle
          variant='outline'
          size='sm'
          pressed={search.history ?? false}
          onPressedChange={(pressed) =>
            onChange({ history: pressed || undefined, page: undefined })
          }
          aria-label='Include records sunk into history'
        >
          <History />
          History
        </Toggle>
      </div>
      {view === 'list' && (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Select
            value={search.sort ?? 'name'}
            onValueChange={(value) =>
              onChange({
                sort: value === 'name' ? undefined : (value as AtlasSort),
              })
            }
          >
            <SelectTrigger aria-label='Sort by' size='sm'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ATLAS_SORTS.map((sort) => (
                <SelectItem key={sort} value={sort}>
                  {`Sort by ${SORT_LABEL[sort].toLowerCase()}`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant='outline'
            size='sm'
            aria-label={search.desc ? 'Descending' : 'Ascending'}
            onClick={() => onChange({ desc: search.desc ? undefined : true })}
          >
            {search.desc ? <ArrowDownWideNarrow /> : <ArrowUpNarrowWide />}
            {search.desc ? 'Descending' : 'Ascending'}
          </Button>
        </div>
      )}
      <Muted variant='caption' aria-live='polite'>
        {`${plural(matches, 'record', 'records')} match`}
      </Muted>
    </div>
  )
}

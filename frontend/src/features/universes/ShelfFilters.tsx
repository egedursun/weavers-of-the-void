import { FilterX, Search, SlidersHorizontal } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { FormRow } from '@/components/domain'
import { NO_UNIVERSE_FILTERS } from './api'
import {
  type FacetCount,
  type UniverseFacets,
  type UniverseFilters,
  universeOriginValues,
  universeSortValues,
  universeStatusValues,
} from './types'
import { ORIGIN_LOOK, SORT_LOOK, STATUS_LOOK } from './universeLook'
import { narrowedCount } from './universeModel'

const ANY = '__any'

function counted<K extends string>(
  label: string,
  counts: FacetCount<K>[],
  value: K
): string {
  const found = counts.find((item) => item.value === value)
  return found ? `${label} (${formatInteger(found.count)})` : label
}

export function ShelfFilters({
  filters,
  text,
  facets,
  onText,
  onChange,
}: {
  filters: UniverseFilters
  text: string
  facets: UniverseFacets
  onText: (text: string) => void
  onChange: (filters: UniverseFilters) => void
}) {
  const narrowed = narrowedCount(filters)
  const set = (change: Partial<UniverseFilters>) =>
    onChange({ ...filters, ...change })
  const tags = facets.tags
  const tagKnown = tags.some((item) => item.value === filters.tag)
  return (
    <Collapsible
      defaultOpen={narrowed > 0}
      className='flex min-w-0 flex-col gap-3'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <div className='min-w-0 flex-1 basis-56'>
          <Input
            type='search'
            leadingIcon={Search}
            value={text}
            placeholder='Search names, summaries and notes'
            aria-label='Search the universes'
            onChange={(event) => onText(event.target.value)}
          />
        </div>
        <div className='min-w-0 basis-48'>
          <Select
            value={filters.sort}
            onValueChange={(value) => {
              const sort = universeSortValues.find((item) => item === value)
              if (sort) set({ sort })
            }}
          >
            <SelectTrigger aria-label='Order of the shelves' className='w-full'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {universeSortValues.map((sort) => {
                const Icon = SORT_LOOK[sort].icon
                return (
                  <SelectItem key={sort} value={sort}>
                    <Icon aria-hidden='true' />
                    {SORT_LOOK[sort].label}
                  </SelectItem>
                )
              })}
            </SelectContent>
          </Select>
        </div>
        <CollapsibleTrigger asChild>
          <Button type='button' variant='outline'>
            <SlidersHorizontal />
            {narrowed > 0 ? `Filters · ${plural(narrowed, 'set')}` : 'Filters'}
          </Button>
        </CollapsibleTrigger>
        <Button
          type='button'
          variant='ghost'
          disabled={narrowed === 0 && text.trim() === ''}
          disabledReason='No search or filter is set.'
          onClick={() => {
            onText('')
            onChange({ ...NO_UNIVERSE_FILTERS, sort: filters.sort })
          }}
        >
          <FilterX />
          Clear
        </Button>
      </div>
      <CollapsibleContent className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
        <FormRow label='Shelf'>
          {(id) => (
            <Select
              value={filters.status ?? ANY}
              onValueChange={(value) =>
                set({
                  status:
                    universeStatusValues.find((item) => item === value) ?? null,
                })
              }
            >
              <SelectTrigger id={id} size='sm' className='w-full'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {universeStatusValues.map((status) => (
                  <SelectItem key={status} value={status}>
                    {counted(
                      STATUS_LOOK[status].label,
                      facets.statuses,
                      status
                    )}
                  </SelectItem>
                ))}
                <SelectItem value={ANY}>On the shelf or archived</SelectItem>
              </SelectContent>
            </Select>
          )}
        </FormRow>
        <FormRow label='Origin'>
          {(id) => (
            <Select
              value={filters.origin ?? ANY}
              onValueChange={(value) =>
                set({
                  origin:
                    universeOriginValues.find((item) => item === value) ?? null,
                })
              }
            >
              <SelectTrigger id={id} size='sm' className='w-full'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ANY}>Every origin</SelectItem>
                {universeOriginValues.map((origin) => (
                  <SelectItem key={origin} value={origin}>
                    {counted(ORIGIN_LOOK[origin].label, facets.origins, origin)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </FormRow>
        <FormRow
          label='Tag'
          description={
            tags.length === 0 ? 'No universe has a tag yet.' : undefined
          }
        >
          {(id) => (
            <Select
              value={filters.tag !== null && tagKnown ? filters.tag : ANY}
              onValueChange={(value) =>
                set({ tag: value === ANY ? null : value })
              }
            >
              <SelectTrigger
                id={id}
                size='sm'
                className='w-full'
                disabled={tags.length === 0}
                title={
                  tags.length === 0 ? 'No universe has a tag yet.' : undefined
                }
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ANY}>Every tag</SelectItem>
                {tags.map((tag) => (
                  <SelectItem key={tag.value} value={tag.value}>
                    {counted(tag.value, tags, tag.value)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </FormRow>
      </CollapsibleContent>
    </Collapsible>
  )
}

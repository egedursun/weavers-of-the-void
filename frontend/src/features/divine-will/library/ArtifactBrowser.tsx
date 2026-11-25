import { useEffect, useMemo, useState } from 'react'
import {
  ChevronDown,
  FilterX,
  LibraryBig,
  Loader2,
  RefreshCw,
  Search,
  SearchX,
  SlidersHorizontal,
} from 'lucide-react'
import { librarySortValues } from '@/api/generated/schema'
import { formatDateTime, formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
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
import { EmptyState, FormRow, LoadingBlock } from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Muted, Text } from '@/components/typography'
import { NODE_KIND_WORDS } from '@/features/entity/affairs/labels'
import { useNames } from '@/features/entity/api/queries'
import { type ArtifactFilters, NO_ARTIFACT_FILTERS, useArtifacts } from '../api'
import { MODE_LOOK, MODE_ORDER } from '../modes'
import { type LibrarySort, type WillArtifactSummary } from '../types'
import { KindSelectItems } from './ArtifactMeta'
import {
  CATEGORY_LOOK,
  FORMAT_LOOK,
  FORMAT_ORDER,
  KIND_LOOK,
  KIND_ORDER,
  STATUS_LOOK,
  STATUS_ORDER,
} from './artifactLook'

const ANY = '__any'
const SEARCH_DEBOUNCE_MS = 220

const SORT_LABEL: Record<LibrarySort, string> = {
  relevance: 'Best match first',
  updated: 'Last revised first',
  created: 'Newest first',
  title: 'By title',
  length: 'Longest first',
}

const DEFAULT_SORT: LibrarySort = 'updated'

function useDebounced(value: string): string {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const handle = window.setTimeout(
      () => setDebounced(value),
      SEARCH_DEBOUNCE_MS
    )
    return () => window.clearTimeout(handle)
  }, [value])
  return debounced
}

function activeFilters(filters: ArtifactFilters): number {
  return [
    filters.q.trim(),
    filters.kind,
    filters.status,
    filters.format,
    filters.language,
    filters.mode,
    filters.tag,
    filters.nodeId,
  ].filter((value) => value !== null && value !== '').length
}

function OptionSelect<T extends string>({
  label,
  value,
  options,
  labelOf,
  onChange,
  anyLabel,
}: {
  label: string
  value: T | null
  options: readonly T[]
  labelOf: (value: T) => string
  onChange: (value: T | null) => void
  anyLabel: string
}) {
  return (
    <FormRow label={label}>
      {(id) => (
        <Select
          value={value ?? ANY}
          onValueChange={(next) =>
            onChange(
              next === ANY
                ? null
                : (options.find((item) => item === next) ?? null)
            )
          }
        >
          <SelectTrigger id={id} size='sm' className='w-full'>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ANY}>{anyLabel}</SelectItem>
            {options.map((option) => (
              <SelectItem key={option} value={option}>
                {labelOf(option)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
    </FormRow>
  )
}

function ArtifactRow({
  artifact,
  selected,
  onSelect,
}: {
  artifact: WillArtifactSummary
  selected: boolean
  onSelect: () => void
}) {
  const kind = KIND_LOOK[artifact.kind]
  const Icon = kind.icon
  const status = STATUS_LOOK[artifact.status]
  const mode = MODE_LOOK[artifact.mode]
  const ModeIcon = mode.icon
  return (
    <li>
      <Button
        variant='outline'
        size='card'
        aria-pressed={selected}
        aria-label={`${artifact.title}, ${kind.label}, ${status.label}`}
        onClick={onSelect}
        className={cn(selected && 'border-primary bg-accent')}
      >
        <span className='flex min-w-0 items-start gap-2.5'>
          <Icon
            aria-hidden='true'
            className='size-icon-md shrink-0 text-primary'
          />
          <span className='flex min-w-0 flex-1 flex-col gap-0.5'>
            <Text as='span' weight='semibold' truncate={2}>
              {artifact.title}
            </Text>
            <Muted as='span' variant='caption' truncate>
              {`${kind.label} · ${CATEGORY_LOOK[kind.category].label}`}
            </Muted>
          </span>
          <Badge size='sm' variant={status.badge}>
            {status.label}
          </Badge>
        </span>
        <span className='flex min-w-0 flex-wrap items-center gap-1'>
          <Badge size='sm' variant='secondary'>
            <ModeIcon aria-hidden='true' />
            {`Written in ${mode.label}`}
          </Badge>
          {artifact.language && (
            <Badge size='sm' variant='outline'>
              {artifact.language}
            </Badge>
          )}
          {artifact.subjects.length > 0 && (
            <Badge size='sm' variant='outline'>
              {artifact.subjects.length === 1
                ? artifact.subjects[0].name
                : plural(artifact.subjects.length, 'subject')}
            </Badge>
          )}
          {artifact.tags.length > 0 && (
            <Badge size='sm' variant='outline'>
              {artifact.tags.join(', ')}
            </Badge>
          )}
        </span>
        <Muted as='span' variant='caption'>
          {[
            `Version ${String(artifact.current_version)}`,
            plural(artifact.characters, 'character'),
            `revised ${formatDateTime(artifact.updated_at)}`,
          ].join(' · ')}
        </Muted>
      </Button>
    </li>
  )
}

type BrowserProps = {
  selected: number | null
  onSelect: (id: number) => void
  compact?: boolean
  initialNodeId?: number | null
  actions?: React.ReactNode
}

export function ArtifactBrowser({
  selected,
  onSelect,
  compact = false,
  initialNodeId = null,
  actions = null,
}: BrowserProps) {
  const [filters, setFilters] = useState<ArtifactFilters>({
    ...NO_ARTIFACT_FILTERS,
    nodeId: initialNodeId,
  })
  const [text, setText] = useState('')
  const q = useDebounced(text)
  const effective = useMemo(() => ({ ...filters, q }), [filters, q])
  const query = useArtifacts(effective)
  const names = useNames(!compact)
  const set = (change: Partial<ArtifactFilters>) =>
    setFilters((current) => ({ ...current, ...change }))
  const pages = query.data?.pages ?? []
  const shown = pages.flatMap((page) => page.items)
  const total = pages[0]?.total ?? 0
  const languages = pages[0]?.languages ?? []
  const tags = pages[0]?.tags ?? []
  const pageSize = pages[0]?.limit ?? 0
  const filtered = activeFilters({ ...filters, q: text })
  const narrowed = activeFilters({ ...filters, q: '' })
  const subjectOptions = useMemo(
    () =>
      (names.data ?? []).map((entry) => ({
        value: String(entry.id),
        label: entry.name,
        hint: NODE_KIND_WORDS[entry.kind],
      })),
    [names.data]
  )
  const clear = () => {
    setText('')
    setFilters({ ...NO_ARTIFACT_FILTERS })
  }
  return (
    <div
      data-domain='artifact-browser'
      className='@container/browser flex min-w-0 flex-col gap-3'
    >
      <Collapsible
        defaultOpen={narrowed > 0}
        className='flex min-w-0 flex-col gap-3'
      >
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <div className='min-w-0 flex-1 basis-48'>
            <Input
              type='search'
              leadingIcon={Search}
              value={text}
              placeholder='Search titles and text'
              aria-label='Search the writings'
              onChange={(event) => setText(event.target.value)}
            />
          </div>
          <div className='min-w-0 basis-44'>
            <Select
              value={filters.sort ?? DEFAULT_SORT}
              onValueChange={(value) => {
                const sort = librarySortValues.find((item) => item === value)
                if (sort) set({ sort })
              }}
            >
              <SelectTrigger
                aria-label='Order of the writings'
                className='w-full'
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {librarySortValues.map((sort) => (
                  <SelectItem key={sort} value={sort}>
                    {SORT_LABEL[sort]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <CollapsibleTrigger asChild>
            <Button variant='outline'>
              <SlidersHorizontal />
              {narrowed > 0
                ? `Filters · ${plural(narrowed, 'set')}`
                : 'Filters'}
            </Button>
          </CollapsibleTrigger>
          {actions}
        </div>
        <CollapsibleContent className='grid min-w-0 grid-cols-1 gap-3 @md/browser:grid-cols-2 @4xl/browser:grid-cols-4'>
          <FormRow label='Kind'>
            {(id) => (
              <Select
                value={filters.kind ?? ANY}
                onValueChange={(value) =>
                  set({
                    kind: KIND_ORDER.find((item) => item === value) ?? null,
                  })
                }
              >
                <SelectTrigger id={id} size='sm' className='w-full'>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ANY}>Every kind</SelectItem>
                  <KindSelectItems />
                </SelectContent>
              </Select>
            )}
          </FormRow>
          <OptionSelect
            label='Status'
            value={filters.status}
            options={STATUS_ORDER}
            labelOf={(value) => STATUS_LOOK[value].label}
            onChange={(status) => set({ status })}
            anyLabel='Draft or final'
          />
          {!compact && (
            <>
              <OptionSelect
                label='Format'
                value={filters.format}
                options={FORMAT_ORDER}
                labelOf={(value) => FORMAT_LOOK[value].label}
                onChange={(format) => set({ format })}
                anyLabel='Every format'
              />
              <OptionSelect
                label='Mode'
                value={filters.mode}
                options={MODE_ORDER}
                labelOf={(value) => MODE_LOOK[value].label}
                onChange={(mode) => set({ mode })}
                anyLabel='Every mode'
              />
              <OptionSelect
                label='Language'
                value={filters.language}
                options={languages}
                labelOf={(value) => value}
                onChange={(language) => set({ language })}
                anyLabel='Every language'
              />
              <OptionSelect
                label='Tag'
                value={filters.tag}
                options={tags}
                labelOf={(value) => value}
                onChange={(tag) => set({ tag })}
                anyLabel='Every tag'
              />
              <FormRow label='Subject'>
                {(id) => (
                  <RecordCombobox
                    id={id}
                    size='sm'
                    options={subjectOptions}
                    value={
                      filters.nodeId === null ? null : String(filters.nodeId)
                    }
                    placeholder={
                      names.isPending ? 'Loading the names' : 'Any subject'
                    }
                    searchPlaceholder='Type a name'
                    clearable
                    disabled={names.isPending}
                    disabledReason='The names of the world are still loading.'
                    onChange={(value) =>
                      set({ nodeId: value === null ? null : Number(value) })
                    }
                  />
                )}
              </FormRow>
            </>
          )}
        </CollapsibleContent>
      </Collapsible>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
        <Muted as='span' variant='caption' role='status'>
          {query.isPending
            ? 'Searching the Library…'
            : total === 1
              ? 'One writing'
              : plural(total, 'writing')}
        </Muted>
        <span className='flex min-w-0 flex-wrap items-center gap-2'>
          <Button
            variant='ghost'
            size='sm'
            disabled={filtered === 0}
            disabledReason='No filter is set.'
            onClick={clear}
          >
            <FilterX />
            {filtered > 0
              ? `Clear ${plural(filtered, 'filter')}`
              : 'Clear filters'}
          </Button>
          {actions}
        </span>
      </div>
      {query.isPending ? (
        <LoadingBlock label='Loading the writings' />
      ) : query.isError ? (
        <EmptyState
          icon={LibraryBig}
          title='The Library could not be opened'
          description={query.error.message}
          action={
            <Button
              variant='outline'
              size='sm'
              onClick={() => void query.refetch()}
            >
              <RefreshCw />
              Try again
            </Button>
          }
        />
      ) : total === 0 ? (
        filtered > 0 ? (
          <EmptyState
            size='compact'
            icon={SearchX}
            title='Nothing matches'
            description='No writing fits these filters. Loosen one or clear them all.'
          />
        ) : (
          <EmptyState
            size={compact ? 'compact' : 'default'}
            icon={LibraryBig}
            title='The Library is empty'
            description='Ask the Divine Will in Creative Work for a story, a chronicle, a screenplay or any other writing, and it is kept here with every version.'
          />
        )
      ) : (
        <>
          <ul
            aria-label='Writings'
            className='grid min-w-0 grid-cols-1 gap-2 @3xl/browser:grid-cols-2'
          >
            {shown.map((artifact) => (
              <ArtifactRow
                key={artifact.id}
                artifact={artifact}
                selected={artifact.id === selected}
                onSelect={() => onSelect(artifact.id)}
              />
            ))}
          </ul>
          {total > shown.length && (
            <div className='flex min-w-0 flex-wrap items-center justify-between gap-2 rounded-md px-3 py-1.5 sealed-well'>
              <Muted as='span' variant='caption'>
                {`Showing ${formatInteger(shown.length)} of ${plural(total, 'writing')}, ${String(pageSize)} at a time`}
              </Muted>
              <Button
                variant='ghost'
                size='sm'
                disabled={query.isFetchingNextPage}
                disabledReason='Loading more writings.'
                onClick={() => void query.fetchNextPage()}
              >
                {query.isFetchingNextPage ? (
                  <Loader2 className='animate-spin' />
                ) : (
                  <ChevronDown />
                )}
                Show more
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

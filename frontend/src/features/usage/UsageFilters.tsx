import { useEffect, useState } from 'react'
import {
  Boxes,
  CalendarRange,
  Cpu,
  FilterX,
  Hash,
  Search,
  ShieldCheck,
  UserRound,
  Workflow,
  X,
} from 'lucide-react'
import { llmCallKindValues, llmCallStatusValues } from '@/api/generated/schema'
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
import { MultiSelect } from '@/components/domain/MultiSelect'
import { Label, Muted } from '@/components/typography'
import {
  EMPTY_FILTER,
  type LlmCallKind,
  type LlmCallStatus,
  type UsageFilter,
  type UsageReport,
} from './api'
import { KIND_LOOK, RANGES, type RangeKey, STATUS_LOOK } from './usageVisuals'

const SEARCH_DELAY_MS = 300

type Chip = { key: string; label: string; clear: () => void }

type UsageFiltersProps = {
  filter: UsageFilter
  onChange: (next: UsageFilter) => void
  range: RangeKey
  onRange: (next: RangeKey) => void
  facets: UsageReport['facets'] | undefined
  matching: number | undefined
}

function epochValue(text: string): number | null {
  if (text.trim() === '') return null
  const value = Number(text)
  return Number.isInteger(value) && value >= 0 ? value : null
}

function isKind(value: string): value is LlmCallKind {
  return llmCallKindValues.some((kind) => kind === value)
}

function isStatus(value: string): value is LlmCallStatus {
  return llmCallStatusValues.some((status) => status === value)
}

export function UsageFilters({
  filter,
  onChange,
  range,
  onRange,
  facets,
  matching,
}: UsageFiltersProps) {
  const [search, setSearch] = useState(filter.search)
  const [seen, setSeen] = useState(filter.search)
  if (seen !== filter.search) {
    setSeen(filter.search)
    setSearch(filter.search)
  }
  useEffect(() => {
    if (search === filter.search) return
    const timer = window.setTimeout(
      () => onChange({ ...filter, search }),
      SEARCH_DELAY_MS
    )
    return () => window.clearTimeout(timer)
  }, [search, filter, onChange])
  const patch = (next: Partial<UsageFilter>) => onChange({ ...filter, ...next })
  const rangeLabel = RANGES.find((item) => item.key === range)?.label ?? ''
  const chips: Chip[] = [
    ...(filter.search.trim()
      ? [
          {
            key: 'search',
            label: `Matching “${filter.search.trim()}”`,
            clear: () => {
              setSearch('')
              patch({ search: '' })
            },
          },
        ]
      : []),
    ...(range !== 'all'
      ? [{ key: 'range', label: rangeLabel, clear: () => onRange('all') }]
      : []),
    ...(filter.epochFrom !== null || filter.epochTo !== null
      ? [
          {
            key: 'epochs',
            label: `Epochs ${filter.epochFrom ?? 'first'}–${filter.epochTo ?? 'latest'}`,
            clear: () => patch({ epochFrom: null, epochTo: null }),
          },
        ]
      : []),
    ...filter.models.map((model) => ({
      key: `model-${model}`,
      label: `Model ${model}`,
      clear: () =>
        patch({ models: filter.models.filter((item) => item !== model) }),
    })),
    ...filter.steps.map((step) => ({
      key: `step-${step}`,
      label: `Step ${step}`,
      clear: () =>
        patch({ steps: filter.steps.filter((item) => item !== step) }),
    })),
    ...filter.roles.map((role) => ({
      key: `role-${role}`,
      label: `Role ${role}`,
      clear: () =>
        patch({ roles: filter.roles.filter((item) => item !== role) }),
    })),
    ...filter.kinds.map((kind) => ({
      key: `kind-${kind}`,
      label: KIND_LOOK[kind].label,
      clear: () =>
        patch({ kinds: filter.kinds.filter((item) => item !== kind) }),
    })),
    ...filter.statuses.map((status) => ({
      key: `status-${status}`,
      label: STATUS_LOOK[status].label,
      clear: () =>
        patch({
          statuses: filter.statuses.filter((item) => item !== status),
        }),
    })),
  ]
  const noFacets = facets === undefined || facets.calls === 0
  const facetReason = 'No calls have been measured yet.'
  return (
    <div
      role='search'
      aria-label='Filter token usage'
      className='flex min-w-0 flex-col gap-3'
    >
      <div className='grid min-w-0 grid-cols-1 gap-2 @xl/usage:grid-cols-2 @4xl/usage:grid-cols-4'>
        <Input
          leadingIcon={Search}
          aria-label='Search calls by step, role, model or error'
          placeholder='Search step, role, model or error'
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className='@xl/usage:col-span-2'
        />
        <Select
          value={range}
          onValueChange={(next) =>
            onRange(RANGES.find((item) => item.key === next)?.key ?? 'all')
          }
        >
          <SelectTrigger aria-label='Time range' className='w-full'>
            <CalendarRange />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {RANGES.map((item) => (
              <SelectItem key={item.key} value={item.key}>
                {item.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className='grid min-w-0 grid-cols-2 gap-2'>
          <Input
            type='number'
            inputMode='numeric'
            min={0}
            leadingIcon={Hash}
            aria-label='From epoch'
            placeholder={
              facets?.epoch_low != null
                ? `From ${facets.epoch_low}`
                : 'From epoch'
            }
            value={filter.epochFrom ?? ''}
            onChange={(event) =>
              patch({ epochFrom: epochValue(event.target.value) })
            }
          />
          <Input
            type='number'
            inputMode='numeric'
            min={0}
            leadingIcon={Hash}
            aria-label='To epoch'
            placeholder={
              facets?.epoch_high != null
                ? `To ${facets.epoch_high}`
                : 'To epoch'
            }
            value={filter.epochTo ?? ''}
            onChange={(event) =>
              patch({ epochTo: epochValue(event.target.value) })
            }
          />
        </div>
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 @md/usage:grid-cols-2 @5xl/usage:grid-cols-5'>
        <MultiSelect
          label='Models'
          icon={<Cpu aria-hidden='true' />}
          options={(facets?.models ?? []).map((model) => ({
            value: model,
            label: model,
          }))}
          value={filter.models}
          onChange={(models) => patch({ models })}
          emptyText={noFacets ? facetReason : 'No model matches.'}
        />
        <MultiSelect
          label='Steps'
          icon={<Workflow aria-hidden='true' />}
          options={(facets?.steps ?? []).map((step) => ({
            value: step,
            label: step,
          }))}
          value={filter.steps}
          onChange={(steps) => patch({ steps })}
          emptyText={noFacets ? facetReason : 'No step matches.'}
        />
        <MultiSelect
          label='Roles'
          icon={<UserRound aria-hidden='true' />}
          options={(facets?.roles ?? []).map((role) => ({
            value: role,
            label: role,
          }))}
          value={filter.roles}
          onChange={(roles) => patch({ roles })}
          emptyText={noFacets ? facetReason : 'No role matches.'}
        />
        <MultiSelect
          label='Call kinds'
          icon={<Boxes aria-hidden='true' />}
          options={llmCallKindValues.map((kind) => ({
            value: kind,
            label: KIND_LOOK[kind].label,
          }))}
          value={filter.kinds}
          onChange={(kinds) => patch({ kinds: kinds.filter(isKind) })}
        />
        <MultiSelect
          label='Outcomes'
          icon={<ShieldCheck aria-hidden='true' />}
          options={llmCallStatusValues.map((status) => ({
            value: status,
            label: STATUS_LOOK[status].label,
          }))}
          value={filter.statuses}
          onChange={(statuses) =>
            patch({ statuses: statuses.filter(isStatus) })
          }
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Label>
          {matching === undefined || facets === undefined
            ? 'Counting calls'
            : `${formatInteger(matching)} of ${plural(facets.calls, 'call', 'calls')} match`}
        </Label>
        {chips.map((chip) => (
          <Button
            key={chip.key}
            variant='outline'
            size='sm'
            aria-label={`Remove filter: ${chip.label}`}
            onClick={chip.clear}
          >
            {chip.label}
            <X />
          </Button>
        ))}
        <Button
          variant='ghost'
          size='sm'
          disabled={chips.length === 0}
          disabledReason='No filter is set.'
          onClick={() => {
            setSearch('')
            onRange('all')
            onChange(EMPTY_FILTER)
          }}
        >
          <FilterX />
          Clear filters
        </Button>
        {chips.length === 0 && (
          <Muted variant='caption'>Showing every measured call.</Muted>
        )}
      </div>
    </div>
  )
}

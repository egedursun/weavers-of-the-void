import { useId, useState } from 'react'
import { ChevronDown, Search, SearchX, ScrollText } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, EntityLink, Paged, Section } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { Chip, RecordRow } from '@/features/cosmography/parts'
import { type Named, named } from '@/features/entity/environment/labels'
import { amountText, spokenKey } from '@/features/records/format'
import { INSTRUMENT_KIND, STEP_ACTION } from '@/features/records/labels'
import { NodeRef } from '@/features/records/parts'
import { ChoiceField } from '@/features/wars/military/parts'
import {
  type FactSearchHit,
  type InstrumentKind,
  type RecordQuery,
  type StepAction,
  recordQueryEmpty,
  useRecordSearch,
} from './api'

const ANY = 'any'
const EMPTY: RecordQuery = {
  fact: null,
  enumValue: null,
  kind: null,
  action: null,
  instrumentKind: null,
}

function withAny(table: Record<string, Named>, label: string) {
  return { [ANY]: { label, icon: Search }, ...table }
}

function TextInput({
  label,
  value,
  placeholder,
  onChange,
}: {
  label: string
  value: string
  placeholder: string
  onChange: (value: string) => void
}) {
  const id = useId()
  return (
    <div className='flex min-w-0 flex-col gap-1.5'>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Input
        id={id}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  )
}

function HitValue({ hit }: { hit: FactSearchHit }) {
  if (hit.node_id !== null)
    return <NodeRef id={hit.node_id} name={hit.node_name} />
  if (hit.number !== null)
    return <span>{amountText(hit.number, hit.unit)}</span>
  if (hit.enum_value !== null)
    return (
      <span>
        {hit.enum_name
          ? `${spokenKey(hit.enum_name)}: ${spokenKey(hit.enum_value)}`
          : spokenKey(hit.enum_value)}
      </span>
    )
  if (hit.name !== null) return <span>{hit.name}</span>
  return <Muted as='span'>No value</Muted>
}

function HitRow({ hit }: { hit: FactSearchHit }) {
  const action = hit.step_action ? named(STEP_ACTION, hit.step_action) : null
  const instrument = hit.instrument_kind
    ? named(INSTRUMENT_KIND, hit.instrument_kind)
    : null
  return (
    <RecordRow
      icon={action?.icon ?? ScrollText}
      tone='verdigris'
      title={
        <EntityLink kind='incident' id={String(hit.incident_id)} showIcon>
          {hit.line ?? spokenKey(hit.kind)}
        </EntityLink>
      }
      caption={`${spokenKey(hit.kind)} · epoch ${formatInteger(hit.epoch)}${hit.year !== null ? ` · year ${formatInteger(hit.year)}` : ''}`}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-1'>
        {hit.fact_key && (
          <Chip icon={ScrollText}>{spokenKey(hit.fact_key)}</Chip>
        )}
        {action && <Chip icon={action.icon}>{action.label}</Chip>}
        {instrument && <Chip icon={instrument.icon}>{instrument.label}</Chip>}
        <Text as='span' variant='caption'>
          <HitValue hit={hit} />
        </Text>
      </div>
    </RecordRow>
  )
}

export function RecordSearch() {
  const [draft, setDraft] = useState<RecordQuery>(EMPTY)
  const [query, setQuery] = useState<RecordQuery>(EMPTY)
  const search = useRecordSearch(query)
  const hits = (search.data?.pages ?? []).flatMap((page) => page.hits)
  const total = search.data?.pages[0]?.total ?? 0
  const blank = recordQueryEmpty(draft)
  const patch = (change: Partial<RecordQuery>) =>
    setDraft((current) => ({ ...current, ...change }))
  const text = (value: string) => (value.trim() ? value.trim() : null)
  return (
    <Section
      id='record-search'
      title='Search the record'
      description='Find every happening by what it holds: a fact, a value, a kind, a step or the instrument used.'
      level={3}
    >
      <form
        className='flex min-w-0 flex-col gap-3'
        onSubmit={(event) => {
          event.preventDefault()
          setQuery(draft)
        }}
      >
        <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'>
          <TextInput
            label='Fact'
            value={draft.fact ?? ''}
            placeholder='The key of a fact'
            onChange={(value) => patch({ fact: text(value) })}
          />
          <TextInput
            label='Value'
            value={draft.enumValue ?? ''}
            placeholder='A typed value'
            onChange={(value) => patch({ enumValue: text(value) })}
          />
          <TextInput
            label='Kind or family'
            value={draft.kind ?? ''}
            placeholder='A kind of happening or its family'
            onChange={(value) => patch({ kind: text(value) })}
          />
        </div>
        <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
          <ChoiceField
            label='Step taken'
            value={draft.action ?? ANY}
            table={withAny(STEP_ACTION, 'Any step')}
            blocked={null}
            onPick={(value) =>
              patch({ action: value === ANY ? null : (value as StepAction) })
            }
          />
          <ChoiceField
            label='Instrument used'
            value={draft.instrumentKind ?? ANY}
            table={withAny(INSTRUMENT_KIND, 'Any instrument')}
            blocked={null}
            onPick={(value) =>
              patch({
                instrumentKind:
                  value === ANY ? null : (value as InstrumentKind),
              })
            }
          />
        </div>
        <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
          <Muted variant='caption'>
            A step or an instrument searches the steps of every happening;
            otherwise the facts are searched.
          </Muted>
          <Button
            type='submit'
            size='sm'
            disabled={blank}
            disabledReason='Name a fact, a value, a kind, a step or an instrument to search for.'
          >
            <Search />
            Search the record
          </Button>
        </div>
      </form>
      {!recordQueryEmpty(query) && (
        <div className='flex min-w-0 flex-col gap-2'>
          {search.isPending && <Skeleton className='h-textarea w-full' />}
          {search.isError && (
            <Text tone='destructive'>{search.error.message}</Text>
          )}
          {search.isSuccess && hits.length === 0 && (
            <EmptyState
              size='compact'
              icon={SearchX}
              title='Nothing recorded'
              description='No happening holds what you searched for.'
            />
          )}
          {hits.length > 0 && (
            <>
              <Muted variant='caption'>
                {`${plural(total, 'record', 'records')} found, ${formatInteger(hits.length)} read so far`}
              </Muted>
              <ul className='flex min-w-0 flex-col gap-2'>
                <Paged items={hits} as='li' noun={['record', 'records']}>
                  {(hit, index) => (
                    <HitRow key={`${hit.incident_id}-${index}`} hit={hit} />
                  )}
                </Paged>
              </ul>
            </>
          )}
          {search.hasNextPage && (
            <Button
              variant='outline'
              size='sm'
              className='self-center'
              onClick={() => void search.fetchNextPage()}
              disabled={search.isFetchingNextPage}
              disabledReason='The next records are being read.'
            >
              <ChevronDown />
              {search.isFetchingNextPage
                ? 'Reading more records'
                : 'Show more records'}
            </Button>
          )}
        </div>
      )}
    </Section>
  )
}

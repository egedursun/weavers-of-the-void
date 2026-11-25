import { useId, useMemo } from 'react'
import { actionKindValues } from '@/api/generated/schema'
import { useUniverseId } from '@/api/universeStore'
import { Input } from '@/components/ui/input'
import { FieldTile } from '@/components/domain/FieldTile'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { wordOf } from '@/features/entity/affairs/labels'
import { useUniverseAccess } from '@/features/workspaces/api'
import { useActiveWorkspace } from '@/features/workspaces/useActiveWorkspace'
import { type LedgerQuery } from './api'

const DAY_END = 'T23:59:59.999Z'
const DAY_START = 'T00:00:00.000Z'

function dayOf(value: string | null): string {
  return value === null ? '' : value.slice(0, 10)
}

function usePeople() {
  const universeId = useUniverseId()
  const { active } = useActiveWorkspace()
  const access = useUniverseAccess(
    active === null || universeId === null
      ? null
      : { id: active.id, universeId }
  )
  return access.data?.people ?? []
}

export function LedgerFilters({
  query,
  onChange,
}: {
  query: LedgerQuery
  onChange: (next: Partial<LedgerQuery>) => void
}) {
  const sinceId = useId()
  const personId = useId()
  const kindId = useId()
  const untilId = useId()
  const people = usePeople()
  const personOptions = useMemo(
    () =>
      people.map((person) => ({
        value: String(person.account.id),
        label: person.account.display_name,
        hint: `@${person.account.username}`,
      })),
    [people]
  )
  const kindOptions = useMemo(
    () =>
      actionKindValues.map((kind) => ({
        value: kind,
        label: wordOf(actionKindValues, kind),
      })),
    []
  )
  return (
    <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4'>
      <FieldTile id={personId} label='Made by'>
        <RecordCombobox
          id={personId}
          options={personOptions}
          value={query.authorId === null ? null : String(query.authorId)}
          onChange={(value) =>
            onChange({ authorId: value === null ? null : Number(value) })
          }
          placeholder='Anyone on the team'
          searchPlaceholder='Type a name'
          emptyText='Nobody on the team has this name.'
          clearable
          size='sm'
          aria-label='Made by'
        />
      </FieldTile>
      <FieldTile id={kindId} label='Kind of act'>
        <RecordCombobox
          id={kindId}
          options={kindOptions}
          value={query.actionKind}
          onChange={(value) =>
            onChange({
              actionKind:
                actionKindValues.find((kind) => kind === value) ?? null,
            })
          }
          placeholder='Any kind of act'
          searchPlaceholder='Type a kind of act'
          emptyText='No kind of act has this name.'
          clearable
          size='sm'
          aria-label='Kind of act'
        />
      </FieldTile>
      <FieldTile id={sinceId} label='From'>
        <Input
          id={sinceId}
          type='date'
          size='sm'
          value={dayOf(query.since)}
          max={dayOf(query.until) || undefined}
          onChange={(event) =>
            onChange({
              since: event.target.value
                ? `${event.target.value}${DAY_START}`
                : null,
            })
          }
        />
      </FieldTile>
      <FieldTile id={untilId} label='To'>
        <Input
          id={untilId}
          type='date'
          size='sm'
          value={dayOf(query.until)}
          min={dayOf(query.since) || undefined}
          onChange={(event) =>
            onChange({
              until: event.target.value
                ? `${event.target.value}${DAY_END}`
                : null,
            })
          }
        />
      </FieldTile>
    </div>
  )
}

import { type ReactNode, useId, useMemo, useState } from 'react'
import { Lock, LockOpen, Plus, Save, Trash2 } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { EmptyState, EntityLink, type KpiTone } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  type RecordColumn,
  type RecordRow,
  type RecordValues,
  RECORD_ICON,
  depthKeys,
  useRecords,
} from './depth'
import { type Named, busyOf, fieldLabel } from './labels'
import { Adjust, FieldGrid, Panel } from './parts'

type Choices = Record<string, Record<string, Named>>

function Field({
  column,
  value,
  held,
  choices,
  onChange,
}: {
  column: RecordColumn
  value: unknown
  held: boolean
  choices: Choices
  onChange: (value: unknown) => void
}) {
  const id = useId()
  const label = fieldLabel(column.name)
  const table = choices[column.name]
  return (
    <div className='flex min-w-0 flex-col gap-1.5 rounded-lg border bg-background p-2.5'>
      <div className='flex min-w-0 items-center gap-1.5'>
        {held ? (
          <Lock
            aria-label='held'
            className='size-icon-xs shrink-0 text-primary'
          />
        ) : null}
        <Label as='label' htmlFor={id} truncate>
          {label}
          {column.required ? ' *' : ''}
        </Label>
      </div>
      {column.kind === 'choice' ? (
        <Select
          value={value === null || value === undefined ? '' : String(value)}
          onValueChange={onChange}
        >
          <SelectTrigger id={id} aria-label={label} className='w-full'>
            <SelectValue placeholder='Choose…' />
          </SelectTrigger>
          <SelectContent>
            {column.options.map((option) => (
              <SelectItem key={option} value={option}>
                {table?.[option]?.label ?? option.replaceAll('_', ' ')}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ) : column.kind === 'flag' ? (
        <Switch
          id={id}
          aria-label={label}
          checked={Boolean(value)}
          onCheckedChange={onChange}
        />
      ) : column.kind === 'words' ? (
        <Input
          id={id}
          value={Array.isArray(value) ? value.join(', ') : ''}
          onChange={(event) =>
            onChange(
              event.target.value
                .split(',')
                .map((item) => item.trim())
                .filter(Boolean)
                .map((item) => (/^\d+$/.test(item) ? Number(item) : item))
            )
          }
        />
      ) : (
        <Input
          id={id}
          type={column.kind === 'text' ? 'text' : 'number'}
          inputMode={column.kind === 'text' ? undefined : 'numeric'}
          value={value === null || value === undefined ? '' : String(value)}
          onChange={(event) =>
            onChange(
              column.kind === 'text'
                ? event.target.value
                : event.target.value === ''
                  ? null
                  : Number(event.target.value)
            )
          }
        />
      )}
    </div>
  )
}

function valueText(
  column: RecordColumn,
  value: unknown,
  choices: Choices
): string {
  if (value === null || value === undefined) return '—'
  if (column.kind === 'choice')
    return (
      choices[column.name]?.[String(value)]?.label ??
      String(value).replaceAll('_', ' ')
    )
  if (column.kind === 'flag') return value ? 'Yes' : 'No'
  if (Array.isArray(value)) return value.length ? value.join(', ') : '—'
  if (typeof value === 'object')
    return Object.keys(value as object).join(', ') || '—'
  return String(value)
}

function RowCard({
  kind,
  row,
  columns,
  deletable,
  choices,
  blocked,
  hidden,
  summary,
  invalidate,
}: {
  kind: string
  row: RecordRow
  columns: RecordColumn[]
  deletable: boolean
  choices: Choices
  blocked: string | null
  hidden: string[]
  summary?: (row: RecordRow) => ReactNode
  invalidate: readonly unknown[]
}) {
  const editable = columns.filter((column) => !hidden.includes(column.name))
  const [draft, setDraft] = useState<RecordValues>({})
  const changed = Object.keys(draft)
  const save = useGodAction<boolean>({
    run: (hold) =>
      unwrap(
        api.POST('/api/actions/military:edit', {
          body: { kind, record_id: row.id, values: draft, hold },
        })
      ),
    invalidate: [invalidate as unknown[]],
    onDone: () => setDraft({}),
  })
  const release = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/military:release', {
          body: { kind, record_id: row.id, columns: [] },
        })
      ),
    invalidate: [invalidate as unknown[]],
  })
  const remove = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/military:delete', {
          body: { kind, record_id: row.id },
        })
      ),
    invalidate: [invalidate as unknown[]],
  })
  const busy = busyOf(
    blocked,
    save.isPending,
    release.isPending,
    remove.isPending
  )
  const shown = editable
    .filter(
      (column) =>
        row.values[column.name] !== null &&
        row.values[column.name] !== undefined
    )
    .slice(0, 6)
  return (
    <div className='flex min-w-0 flex-col gap-2.5 rounded-lg border bg-background p-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        {summary ? summary(row) : null}
        {row.locked.length > 0 && (
          <Badge size='sm' variant='outline'>
            <Lock aria-hidden='true' />
            {row.locked.length} held
          </Badge>
        )}
      </div>
      {!summary && (
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          {shown.map((column) => {
            const ref = row.refs[column.name]
            return (
              <Badge key={column.name} size='sm' variant='secondary'>
                <span className='text-muted-foreground'>
                  {fieldLabel(column.name)}
                </span>
                {ref
                  ? ref.name
                  : valueText(column, row.values[column.name], choices)}
              </Badge>
            )
          })}
        </div>
      )}
      <Adjust
        title='Every value'
        note='Set any value; held values stay as you set them until released.'
      >
        <FieldGrid>
          {editable.map((column) => (
            <Field
              key={column.name}
              column={column}
              value={
                column.name in draft
                  ? draft[column.name]
                  : row.values[column.name]
              }
              held={row.locked.includes(column.name)}
              choices={choices}
              onChange={(value) =>
                setDraft((current) => ({ ...current, [column.name]: value }))
              }
            />
          ))}
        </FieldGrid>
        <div className='flex flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={busy !== null || changed.length === 0}

            disabledReason={
              busy !== null || changed.length === 0
                ? (blocked ?? 'Fill in what is needed first')
                : undefined
            }
            onClick={() => save.mutate(true)}
          >
            <Lock />
            Set and hold
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null || changed.length === 0}

            disabledReason={
              busy !== null || changed.length === 0
                ? (blocked ?? 'Fill in what is needed first')
                : undefined
            }
            onClick={() => save.mutate(false)}
          >
            <Save />
            Set once
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null || row.locked.length === 0}

            disabledReason={
              busy !== null || row.locked.length === 0
                ? (blocked ?? 'Fill in what is needed first')
                : undefined
            }
            onClick={() => release.mutate()}
          >
            <LockOpen />
            Release holds
          </Button>
          {deletable && (
            <Button
              size='sm'
              variant='destructive'
              disabled={busy !== null}

              disabledReason={
                busy !== null
                  ? (blocked ?? 'Fill in what is needed first')
                  : undefined
              }
              onClick={() => remove.mutate()}
            >
              <Trash2 />
              Strike out
            </Button>
          )}
        </div>
      </Adjust>
    </div>
  )
}

function CreateForm({
  kind,
  columns,
  presets,
  choices,
  blocked,
  invalidate,
  label,
}: {
  kind: string
  columns: RecordColumn[]
  presets: RecordValues
  choices: Choices
  blocked: string | null
  invalidate: readonly unknown[]
  label: string
}) {
  const [values, setValues] = useState<RecordValues>({})
  const create = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/military:create', {
          body: { kind, values: { ...values, ...presets } },
        })
      ),
    invalidate: [invalidate as unknown[]],
    onDone: () => setValues({}),
  })
  const shown = columns.filter((column) => !(column.name in presets))
  const ordered = [
    ...shown.filter((column) => column.required),
    ...shown.filter((column) => !column.required),
  ]
  const missing = ordered.filter(
    (column) =>
      column.required &&
      (values[column.name] === undefined || values[column.name] === null)
  )
  return (
    <Adjust
      title={`Create a ${label.toLowerCase()}`}
      note='Required values are marked with a star.'
      label={`Create ${label.toLowerCase()}`}
    >
      <FieldGrid>
        {ordered.map((column) => (
          <Field
            key={column.name}
            column={column}
            value={values[column.name]}
            held={false}
            choices={choices}
            onChange={(value) =>
              setValues((current) => ({ ...current, [column.name]: value }))
            }
          />
        ))}
      </FieldGrid>
      <Button
        size='sm'
        className='self-start'
        disabled={
          busyOf(blocked, create.isPending) !== null || missing.length > 0
        }

        disabledReason={
          busyOf(blocked, create.isPending) !== null || missing.length > 0
            ? (blocked ?? 'Fill in what is needed first')
            : undefined
        }
        onClick={() => create.mutate()}
      >
        <Plus />
        Create
      </Button>
    </Adjust>
  )
}

export function RecordPanel({
  kind,
  scope,
  title,
  hint,
  tone = 'gold',
  blocked,
  presets = {},
  choices = {},
  hidden = [],
  summary,
  empty,
}: {
  kind: string
  scope: number | null
  title: string
  hint?: string
  tone?: KpiTone
  blocked: string | null
  presets?: RecordValues
  choices?: Choices
  hidden?: string[]
  summary?: (row: RecordRow) => ReactNode
  empty?: string
}) {
  const query = useRecords(kind, scope)
  const invalidate = useMemo(
    () => depthKeys.records(kind, scope),
    [kind, scope]
  )
  const table = query.data
  const icon = RECORD_ICON[kind] ?? Plus
  if (!table)
    return <Muted variant='caption'>Loading {title.toLowerCase()}…</Muted>
  return (
    <Panel
      title={title}
      icon={icon}
      tone={tone}
      count={table.rows.length}
      hint={hint}
    >
      {table.rows.length === 0 ? (
        <EmptyState
          icon={icon}
          title={empty ?? `No ${title.toLowerCase()} yet`}
          description='Create one below, or let the world make its own.'
        />
      ) : (
        <div className='flex min-w-0 flex-col gap-2'>
          {table.rows.map((row) => (
            <RowCard
              key={row.id}
              kind={kind}
              row={row}
              columns={table.columns}
              deletable={table.deletable}
              choices={choices}
              blocked={blocked}
              hidden={[...hidden, ...Object.keys(presets)]}
              summary={summary}
              invalidate={invalidate}
            />
          ))}
        </div>
      )}
      {table.creatable && (
        <CreateForm
          kind={kind}
          columns={table.columns}
          presets={presets}
          choices={choices}
          blocked={blocked}
          invalidate={invalidate}
          label={table.label}
        />
      )}
    </Panel>
  )
}

export function RefLink({
  refValue,
}: {
  refValue: RecordRow['refs'][string] | undefined
}) {
  if (!refValue) return null
  return (
    <EntityLink kind='entity' id={String(refValue.id)}>
      <Text as='span' variant='caption'>
        {refValue.name}
      </Text>
    </EntityLink>
  )
}

export function Hint({ children }: { children: ReactNode }) {
  return <Muted variant='caption'>{children}</Muted>
}

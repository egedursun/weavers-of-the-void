import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ChevronDown,
  Database,
  Lock,
  Pencil,
  Plus,
  Trash2,
  TriangleAlert,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import {
  ConfirmDialog,
  EmptyState,
  FormRow,
  Medallion,
  Paged,
  Section,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { loreKeys } from '../api/keys'

type TableView = components['schemas']['ThingRecordTableView']
type ColumnView = components['schemas']['ThingRecordColumnView']
type RowView = components['schemas']['ThingRecordRowView']
type Value =
  string | number | boolean | null | unknown[] | Record<string, unknown>
type Draft = Record<string, Value>

const WORKING = 'Working on it.'
const NONE = '__none__'

function words(name: string) {
  return name.replaceAll('_', ' ')
}

function shown(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? 'yes' : 'no'
  if (typeof value === 'object') return JSON.stringify(value)
  return words(String(value))
}

function jsonText(value: Value) {
  return value === null ? '' : JSON.stringify(value, null, 2)
}

function parsed(column: ColumnView, raw: string): Value | undefined {
  if (raw.trim() === '') return column.nullable ? null : undefined
  try {
    return JSON.parse(raw) as Value
  } catch {
    return undefined
  }
}

function RowField({
  column,
  value,
  onChange,
  disabled,
}: {
  column: ColumnView
  value: Value
  onChange: (value: Value | undefined) => void
  disabled: boolean
}) {
  const [raw, setRaw] = useState(jsonText(value))
  return (
    <FormRow
      label={words(column.name)}
      description={column.required ? 'Required' : undefined}
    >
      {(id) => {
        if (column.kind === 'flag')
          return (
            <Switch
              id={id}
              checked={value === true}
              disabled={disabled}
              onCheckedChange={onChange}
              aria-label={words(column.name)}
            />
          )
        if (column.kind === 'choice')
          return (
            <Select
              value={
                value === null || value === undefined ? NONE : String(value)
              }
              disabled={disabled}
              onValueChange={(next) => onChange(next === NONE ? null : next)}
            >
              <SelectTrigger id={id} aria-label={words(column.name)}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {column.nullable && <SelectItem value={NONE}>None</SelectItem>}
                {column.options.map((option) => (
                  <SelectItem key={option} value={option}>
                    {words(option)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )
        if (column.kind === 'json')
          return (
            <Textarea
              id={id}
              value={raw}
              disabled={disabled}
              rows={3}
              onChange={(event) => {
                setRaw(event.target.value)
                onChange(parsed(column, event.target.value))
              }}
            />
          )
        const numeric = column.kind === 'integer' || column.kind === 'number'
        return (
          <Input
            id={id}
            type={numeric ? 'number' : 'text'}
            step={column.kind === 'integer' ? 1 : 'any'}
            value={value === null || value === undefined ? '' : String(value)}
            disabled={disabled}
            onChange={(event) => {
              const text = event.target.value
              if (text === '') onChange(column.nullable ? null : undefined)
              else onChange(numeric ? Number(text) : text)
            }}
          />
        )
      }}
    </FormRow>
  )
}

function RowEditor({
  table,
  row,
  nodeId,
  open,
  onOpenChange,
  blocked,
}: {
  table: TableView
  row: RowView | null
  nodeId: number
  open: boolean
  onOpenChange: (open: boolean) => void
  blocked: string | null
}) {
  const editing = row !== null
  const fields = table.columns.filter((column) =>
    editing
      ? column.editable
      : column.kind !== '' &&
        !(column.primary && !column.required && !column.owner)
  )
  const owner = table.columns.find((column) => column.owner)
  const start: Draft = editing
    ? Object.fromEntries(
        fields.map((column) => [
          column.name,
          (row.values[column.name] ?? null) as Value,
        ])
      )
    : Object.fromEntries(
        fields.map((column) => [
          column.name,
          column.name === owner?.name ? nodeId : null,
        ])
      )
  const [draft, setDraft] = useState<Draft>(start)
  const [invalid, setInvalid] = useState<string[]>([])
  const [hold, setHold] = useState(false)
  const save = useGodAction({
    run: () => {
      const changed = editing
        ? Object.fromEntries(
            Object.entries(draft).filter(
              ([name, value]) =>
                JSON.stringify(value) !==
                JSON.stringify(row.values[name] ?? null)
            )
          )
        : Object.fromEntries(
            Object.entries(draft).filter(([, value]) => value !== null)
          )
      return editing
        ? unwrap(
            api.POST('/api/actions/record_row:edit', {
              body: {
                table: table.table,
                key: row.key as Record<string, string | number | null>,
                values: changed,
                hold,
              },
            })
          )
        : unwrap(
            api.POST('/api/actions/record_row:create', {
              body: { table: table.table, values: changed },
            })
          )
    },
    onDone: () => onOpenChange(false),
  })
  const missing = fields.find(
    (column) =>
      column.required &&
      !editing &&
      (draft[column.name] === null || draft[column.name] === undefined)
  )
  const reason =
    blocked ??
    (save.isPending ? WORKING : null) ??
    (invalid.length > 0 ? `Fix ${invalid.map(words).join(', ')}.` : null) ??
    (missing ? `Fill in ${words(missing.name)}.` : null)
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {editing
              ? `Reshape a row of ${table.label.toLowerCase()}`
              : `Make a row of ${table.label.toLowerCase()}`}
          </DialogTitle>
          <DialogDescription>
            Every change goes into the ledger and can be undone.
          </DialogDescription>
        </DialogHeader>
        <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
          {fields.map((column) => (
            <RowField
              key={column.name}
              column={column}
              value={draft[column.name] ?? null}
              disabled={save.isPending}
              onChange={(value) => {
                setInvalid((items) =>
                  value === undefined
                    ? [...new Set([...items, column.name])]
                    : items.filter((item) => item !== column.name)
                )
                if (value !== undefined)
                  setDraft({ ...draft, [column.name]: value })
              }}
            />
          ))}
        </div>
        {editing && (
          <label className='flex items-center gap-2'>
            <Switch
              checked={hold}
              onCheckedChange={setHold}
              aria-label='Hold what I set'
            />
            <Text as='span'>Hold what I set against the world</Text>
          </label>
        )}
        <DialogFooter>
          <Button
            size='sm'
            disabled={reason !== null}
            disabledReason={reason ?? undefined}
            onClick={() => save.mutate()}
          >
            {editing ? <Pencil /> : <Plus />}
            {editing ? 'Reshape it' : 'Make it'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function RowCard({
  table,
  row,
  nodeId,
  blocked,
}: {
  table: TableView
  row: RowView
  nodeId: number
  blocked: string | null
}) {
  const [editing, setEditing] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const remove = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/record_row:delete', {
          body: {
            table: table.table,
            key: row.key as Record<string, string | number | null>,
          },
        })
      ),
  })
  const reason = blocked ?? (remove.isPending ? WORKING : null)
  const values = table.columns.filter(
    (column) =>
      !column.owner ||
      column.name !== table.columns.find((item) => item.owner)?.name
  )
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-md border bg-background p-2'>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        {values.map((column) => (
          <Badge
            key={column.name}
            size='sm'
            variant={row.held.includes(column.name) ? 'warning' : 'secondary'}
          >
            {row.held.includes(column.name) && <Lock />}
            {`${words(column.name)}: ${shown(row.values[column.name])}`}
          </Badge>
        ))}
      </div>
      <div className='flex min-w-0 justify-end gap-1'>
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Reshape this row of ${table.label.toLowerCase()}`}
          disabled={reason !== null}
          disabledReason={reason ?? undefined}
          onClick={() => setEditing(true)}
        >
          <Pencil />
        </Button>
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Unmake this row of ${table.label.toLowerCase()}`}
          disabled={reason !== null}
          disabledReason={reason ?? undefined}
          onClick={() => setConfirming(true)}
        >
          <Trash2 />
        </Button>
      </div>
      {editing && (
        <RowEditor
          table={table}
          row={row}
          nodeId={nodeId}
          open={editing}
          onOpenChange={setEditing}
          blocked={blocked}
        />
      )}
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title={`Unmake this row of ${table.label.toLowerCase()}?`}
        desc='It is removed from the world; the ledger can bring it back.'
        destructive
        confirmText='Unmake it'
        isLoading={remove.isPending}
        handleConfirm={() => {
          setConfirming(false)
          remove.mutate()
        }}
      />
    </li>
  )
}

function TableGroup({
  table,
  nodeId,
  blocked,
}: {
  table: TableView
  nodeId: number
  blocked: string | null
}) {
  const [making, setMaking] = useState(false)
  return (
    <Collapsible className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/20 p-2'>
      <div className='flex min-w-0 items-center justify-between gap-2'>
        <CollapsibleTrigger asChild>
          <Button size='sm' variant='ghost' className='min-w-0 justify-start'>
            <ChevronDown />
            <Text as='span' weight='medium' truncate>
              {table.label}
            </Text>
            <Badge size='sm' variant='outline'>
              {table.rows.length}
            </Badge>
          </Button>
        </CollapsibleTrigger>
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Make a row of ${table.label.toLowerCase()}`}
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={() => setMaking(true)}
        >
          <Plus />
        </Button>
      </div>
      <CollapsibleContent>
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={table.rows} as='li'>
            {(row) => (
              <RowCard
                key={JSON.stringify(row.key)}
                table={table}
                row={row}
                nodeId={nodeId}
                blocked={blocked}
              />
            )}
          </Paged>
        </ul>
      </CollapsibleContent>
      {making && (
        <RowEditor
          table={table}
          row={null}
          nodeId={nodeId}
          open={making}
          onOpenChange={setMaking}
          blocked={blocked}
        />
      )}
    </Collapsible>
  )
}

function MakeAnyRow({
  tables,
  nodeId,
  blocked,
}: {
  tables: TableView[]
  nodeId: number
  blocked: string | null
}) {
  const [picked, setPicked] = useState('')
  const [open, setOpen] = useState(false)
  const table = tables.find((item) => item.table === picked)
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-lg border border-dashed p-3'>
      <Label variant='overline'>
        Make a record this thing does not have yet
      </Label>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <div className='flex min-w-0 flex-1 basis-60 flex-col gap-1'>
          <Select
            value={picked}
            onValueChange={setPicked}
            disabled={blocked !== null}
          >
            <SelectTrigger aria-label='Kind of record'>
              <SelectValue placeholder='Choose a kind of record' />
            </SelectTrigger>
            <SelectContent>
              {tables.map((item) => (
                <SelectItem key={item.table} value={item.table}>
                  {item.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button
          size='sm'
          disabled={blocked !== null || !table}
          disabledReason={
            blocked ?? (table ? undefined : 'Choose a kind of record first.')
          }
          onClick={() => setOpen(true)}
        >
          <Plus />
          Make it
        </Button>
      </div>
      {table && open && (
        <RowEditor
          table={table}
          row={null}
          nodeId={nodeId}
          open={open}
          onOpenChange={setOpen}
          blocked={blocked}
        />
      )}
    </div>
  )
}

export function RecordRowsSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const view = useQuery({
    queryKey: [...loreKeys.entity(nodeId), 'record-rows'],
    queryFn: () =>
      unwrap(
        api.GET('/api/records/{node_id}/rows', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
  const data = view.data
  const present = new Set((data?.tables ?? []).map((table) => table.table))
  const rows = (data?.tables ?? []).reduce(
    (total, table) => total + table.rows.length,
    0
  )
  return (
    <Section
      id='section-records'
      title='Every record'
      description='Every typed record that belongs to this thing, straight from the world. Change or hold any value, unmake a row or make a new one.'
      icon={Database}
      tone='info'
    >
      {view.isError ? (
        <EmptyState
          icon={TriangleAlert}
          title='The records could not be read'
          description={view.error.message}
        />
      ) : !data ? (
        <Muted>Reading the records.</Muted>
      ) : (
        <div className='flex min-w-0 flex-col gap-3'>
          <div className='flex min-w-0 items-center gap-2'>
            <Medallion icon={Database} tone='info' size='sm' />
            <Muted variant='caption'>{`${rows} rows in ${data.tables.length} kinds of record`}</Muted>
          </div>
          {data.tables.length === 0 ? (
            <EmptyState
              icon={Database}
              title='No records yet'
              description='The world has written nothing about this thing yet.'
            />
          ) : (
            <Paged items={data.tables}>
              {(table) => (
                <TableGroup
                  key={table.table}
                  table={table}
                  nodeId={nodeId}
                  blocked={reason()}
                />
              )}
            </Paged>
          )}
          <MakeAnyRow
            tables={data.creatable.filter((table) => !present.has(table.table))}
            nodeId={nodeId}
            blocked={reason()}
          />
        </div>
      )}
    </Section>
  )
}

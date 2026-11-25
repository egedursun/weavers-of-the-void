import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Check, Hand, Lock, Pin, Table2, Unlock } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { plural } from '@/lib/units'
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
import { EmptyState, Medallion, Paged } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { humanize } from '../actions/schema'
import { loreKeys } from '../api/keys'
import { AdjustPanel } from '../realm/parts'

type Table = components['schemas']['ProfileTableRecord']
type Column = components['schemas']['ProfileColumnRecord']
type Scalar = string | number | boolean | null

const NONE = '__none__'

export function profilesKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'profiles'] as const
}

export function parseColumn(column: Column, raw: string): Scalar {
  if (raw === '' && column.nullable) return null
  if (column.kind === 'integer') return Number.parseInt(raw, 10)
  if (column.kind === 'number') return Number(raw)
  return raw
}

function shown(value: Scalar | undefined): string {
  if (value === null || value === undefined) return 'none'
  if (typeof value === 'boolean') return value ? 'yes' : 'no'
  return typeof value === 'string' ? humanize(value) : String(value)
}

function ColumnRow({
  nodeId,
  table,
  column,
  blocked,
}: {
  nodeId: number
  table: string
  column: Column
  blocked: string | undefined
}) {
  const [draft, setDraft] = useState(
    column.value === null ? '' : String(column.value)
  )
  const set = useGodAction({
    writes: [{ lever: 'profile:set' }],
    run: (value: Scalar) =>
      unwrap(
        api.POST('/api/actions/profile:set', {
          body: {
            node_id: nodeId,
            table,
            column: column.name,
            value,
            hold: true,
          },
        })
      ),
    success: `${humanize(column.name)} is set and held`,
    invalidate: [profilesKey(nodeId)],
  })
  const release = useGodAction({
    writes: [{ lever: 'profile:release' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/profile:release', {
          body: { node_id: nodeId, table, column: column.name },
        })
      ),
    success: `${humanize(column.name)} follows the world again`,
    invalidate: [profilesKey(nodeId)],
  })
  const busy =
    blocked ??
    (set.isPending || release.isPending
      ? 'Another change is being applied.'
      : undefined)
  const kept = column.held || column.pinned
  const control =
    column.kind === 'flag' ? (
      <Switch
        act={set}
        checked={column.value === true}
        aria-label={humanize(column.name)}
        disabled={busy !== undefined}
        onCheckedChange={(value) => set.mutate(value)}
      />
    ) : column.kind === 'choice' ? (
      <Select
        act={set}
        value={column.value === null ? NONE : String(column.value)}
        disabled={busy !== undefined}
        onValueChange={(value) => set.mutate(value === NONE ? null : value)}
      >
        <SelectTrigger aria-label={humanize(column.name)} className='w-48'>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {column.nullable && <SelectItem value={NONE}>None</SelectItem>}
          {column.options.map((option) => (
            <SelectItem key={option} value={option}>
              {humanize(option)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    ) : (
      <div className='flex min-w-0 items-center gap-1'>
        <Input
          aria-label={humanize(column.name)}
          inputMode={column.kind === 'text' ? 'text' : 'decimal'}
          className='w-32'
          value={draft}
          disabled={busy !== undefined}
          onChange={(event) => setDraft(event.target.value)}
        />
        <Button
          act={set}
          size='sm'
          variant='outline'
          aria-label={`Set ${humanize(column.name)}`}
          disabled={busy !== undefined}
          disabledReason={busy}
          onClick={() => set.mutate(parseColumn(column, draft))}
        >
          <Check />
        </Button>
      </div>
    )
  return (
    <li className='flex min-w-0 flex-wrap items-center gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
      <div className='flex min-w-0 flex-1 flex-col'>
        <Text weight='medium' truncate>
          {humanize(column.name)}
        </Text>
        <Muted variant='caption' truncate>
          {`Now ${shown(column.value)}`}
        </Muted>
      </div>
      {column.pinned && (
        <Badge size='sm' variant='info'>
          <Pin aria-hidden='true' />
          Pinned
        </Badge>
      )}
      {control}
      {kept ? (
        <Button
          act={release}
          size='sm'
          variant='ghost'
          disabled={busy !== undefined}
          disabledReason={busy}
          onClick={() => release.mutate()}
        >
          <Unlock />
          Release
        </Button>
      ) : (
        <Button
          act={set}
          size='sm'
          variant='ghost'
          disabled={busy !== undefined}
          disabledReason={busy}
          onClick={() => set.mutate(column.value as Scalar)}
        >
          <Lock />
          Hold
        </Button>
      )}
    </li>
  )
}

function TableCard({
  nodeId,
  table,
  blocked,
}: {
  nodeId: number
  table: Table
  blocked: string | undefined
}) {
  const held = table.columns.filter(
    (column) => column.held || column.pinned
  ).length
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={Table2} tone='verdigris' size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text weight='semibold' truncate>
            {humanize(table.table)}
          </Text>
          <Muted variant='caption'>{`${plural(table.columns.length, 'value', 'values')}${held ? `, ${held} held by your hand` : ''}`}</Muted>
        </div>
      </div>
      <AdjustPanel
        writes={[{ lever: 'profile:release' }, { lever: 'profile:set' }]}
        title={`Set ${humanize(table.table).toLowerCase()}`}
        note='Every change is held so the engine keeps it; release a value to let the world move it again.'
        trigger='Adjust values'
      >
        <ul className='flex min-w-0 flex-col gap-1.5'>
          <Paged items={table.columns} as='li'>
            {(column) => (
              <ColumnRow
                key={column.name}
                nodeId={nodeId}
                table={table.table}
                column={column}
                blocked={blocked}
              />
            )}
          </Paged>
        </ul>
      </AdjustPanel>
    </div>
  )
}

export function ProfileValues({
  nodeId,
  blocked,
}: {
  nodeId: number
  blocked: string | undefined
}) {
  const query = useQuery({
    queryKey: profilesKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/nodes/{node_id}/profiles', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
  const tables = query.data ?? []
  return (
    <div data-surface='ProfileValues' className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={Hand} tone='gold' size='sm' />
        <div className='flex min-w-0 flex-col'>
          <Label variant='overline'>Hold the world's hand</Label>
          <Muted variant='caption'>
            Every value the engine keeps for this record, table by table.
          </Muted>
        </div>
      </div>
      {query.data && tables.length === 0 ? (
        <EmptyState
          size='compact'
          icon={Table2}
          title='No profile tables'
          description='This record keeps no values beyond its stats.'
        />
      ) : (
        <div className='grid min-w-0 grid-cols-1 gap-2'>
          <Paged items={tables}>
            {(table) => (
              <TableCard
                key={table.table}
                nodeId={nodeId}
                table={table}
                blocked={blocked}
              />
            )}
          </Paged>
        </div>
      )}
    </div>
  )
}

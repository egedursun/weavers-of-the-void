import { useState } from 'react'
import { Eraser, Save } from 'lucide-react'
import { type ActProp } from '@/api/mutation'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EntityLink, Medallion, Paged } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { ALIGNMENTS, WORSHIP_MODES, table } from '@/features/dominion/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { AdjustPanel, Held, NumberField } from '@/features/entity/wilds/parts'
import type { StandingView } from './api'
import { AXIS_LABELS, STANDING_AXES, heldLabel } from './labels'
import { heat } from './model'

type Ref = { id: number; name: string; kind?: string } | null | undefined

const LINK_KINDS: Record<
  string,
  | 'son'
  | 'foreign-god'
  | 'world'
  | 'star'
  | 'galaxy'
  | 'cluster'
  | 'dimension'
  | 'creator'
  | 'entity'
> = {
  son: 'son',
  foreign_god: 'foreign-god',
  world: 'world',
  star: 'star',
  creator: 'creator',
  entity: 'entity',
  galaxy: 'galaxy',
  cluster: 'cluster',
  dimension: 'dimension',
}

export function NodeName({ item }: { item: Ref }) {
  if (!item) return <Muted as='span'>Unknown</Muted>
  const kind = item.kind ? (LINK_KINDS[item.kind] ?? 'entity') : 'entity'
  return (
    <EntityLink kind={kind} id={String(item.id)} showIcon>
      {item.name}
    </EntityLink>
  )
}

export function StandingRow({
  row,
  focus,
  busy,
  onSave,
  onClear,
  act,
}: {
  row: StandingView
  focus: 'god' | 'community'
  busy: string | null
  onSave: (values: Record<string, number | string>, release: string[]) => void
  onClear: () => void
  act?: ActProp
}) {
  const [draft, setDraft] = useState<Record<string, string>>({})
  const value = (axis: (typeof STANDING_AXES)[number]) =>
    draft[axis] ?? String(row[axis])
  const changed = Object.fromEntries(
    Object.entries(draft)
      .filter(([, text]) => text !== '' && !Number.isNaN(Number(text)))
      .map(([key, text]) => [key, Number(text)])
  )
  const nothing =
    Object.keys(changed).length === 0 ? 'Change a value first' : null
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <NodeName item={focus === 'god' ? row.community : row.god} />
        <Muted variant='caption'>{`since epoch ${row.epoch}`}</Muted>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        {row.perceived ? (
          <Badge variant='outline'>
            {`Seen as ${ALIGNMENTS[row.perceived].label.toLowerCase()}`}
          </Badge>
        ) : (
          <Muted variant='caption'>Not yet judged good or ill</Muted>
        )}
        {row.mode && (
          <Badge variant='outline'>
            {`Worshipped in ${WORSHIP_MODES[row.mode].label.toLowerCase()}`}
          </Badge>
        )}
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
        <MindPicker
          act={act}
          label='Seen as'
          value={row.perceived ?? ''}
          table={table(ALIGNMENTS)}
          blocked={busy}
          onPick={(picked) => onSave({ perceived: picked }, [])}
        />
        <MindPicker
          act={act}
          label='Worshipped in'
          value={row.mode ?? ''}
          table={table(WORSHIP_MODES)}
          blocked={busy}
          onPick={(picked) => onSave({ mode: picked }, [])}
        />
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-4'>
        {STANDING_AXES.map((axis) => {
          const spec = AXIS_LABELS[axis]
          return (
            <div
              key={axis}
              className={cn(
                'flex min-w-0 items-center gap-2 rounded-md p-2',
                heat(row[axis])
              )}
            >
              <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
              <div className='flex min-w-0 flex-col'>
                <Label variant='overline' truncate>
                  {spec.label}
                </Label>
                <Text weight='semibold'>{row[axis]}</Text>
              </div>
            </div>
          )
        })}
      </div>
      <Held
        act={act}
        keys={row.locked}
        label={heldLabel}
        busy={busy}
        onRelease={() => onSave({}, row.locked)}
      />
      <AdjustPanel
        acts={[{ blockedReason: busy }]}
        title='Set this regard'
        note='Values you set are held against the world until you let it decide again.'
      >
        <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-4'>
          {STANDING_AXES.map((axis) => (
            <NumberField
              key={axis}
              label={AXIS_LABELS[axis].label}
              value={value(axis)}
              min={0}
              max={100}
              disabled={busy !== null}
              onChange={(text) => setDraft((old) => ({ ...old, [axis]: text }))}
            />
          ))}
        </div>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            act={act}
            size='sm'
            disabled={busy !== null || nothing !== null}
            disabledReason={busy ?? nothing ?? undefined}
            onClick={() => {
              onSave(changed, [])
              setDraft({})
            }}
          >
            <Save />
            Hold these values
          </Button>
          <Button
            act={act}
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={onClear}
          >
            <Eraser />
            Forget this regard
          </Button>
        </div>
      </AdjustPanel>
    </li>
  )
}

export function StandingList({
  rows,
  focus,
  busy,
  onSave,
  onClear,
  act,
}: {
  rows: StandingView[]
  focus: 'god' | 'community'
  busy: string | null
  onSave: (
    row: StandingView,
    values: Record<string, number | string>,
    release: string[]
  ) => void
  onClear: (row: StandingView) => void
  act?: ActProp
}) {
  return (
    <ul className='flex min-w-0 flex-col gap-2'>
      <Paged items={rows} as='li'>
        {(row) => (
          <StandingRow
            act={act}
            key={`${row.community.id}-${row.god.id}`}
            row={row}
            focus={focus}
            busy={busy}
            onSave={(values, release) => onSave(row, values, release)}
            onClear={() => onClear(row)}
          />
        )}
      </Paged>
    </ul>
  )
}

export function PickRow({
  label,
  table,
  value,
  blocked,
  onPick,
}: {
  label: string
  table: Record<string, string>
  value: string
  blocked: string | null
  onPick: (value: string) => void
}) {
  const empty =
    Object.keys(table).length === 0
      ? `No ${label.toLowerCase()} to choose from yet`
      : null
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <MindPicker
        label={label}
        value={value}
        table={table}
        blocked={blocked ?? empty}
        onPick={onPick}
      />
      {empty && (
        <Badge size='sm' variant='outline'>
          {empty}
        </Badge>
      )}
    </div>
  )
}

const COMMUNITY_TYPES = [
  'people',
  'settlement',
  'cult',
  'faction',
  'polity',
] as const

export function RegardForm({
  busy,
  onSave,
  act,
}: {
  busy: string | null
  onSave: (community: number, values: Record<string, number>) => void
  act?: ActProp
}) {
  const [community, setCommunity] = useState<number | null>(null)
  const [draft, setDraft] = useState<Record<string, string>>({})
  const values = Object.fromEntries(
    Object.entries(draft)
      .filter(([, text]) => text !== '')
      .map(([key, text]) => [key, Number(text)])
  )
  const problem =
    community === null
      ? 'Choose a community'
      : Object.keys(values).length === 0
        ? 'Set at least one value'
        : null
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md p-3 sealed-well'>
      <Label variant='overline'>Set a community’s regard</Label>
      <EntityPicker
        types={COMMUNITY_TYPES}
        value={community}
        onChange={setCommunity}
        placeholder='The community whose regard you set'
      />
      <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-4'>
        {STANDING_AXES.map((axis) => (
          <NumberField
            key={axis}
            label={AXIS_LABELS[axis].label}
            value={draft[axis] ?? ''}
            min={0}
            max={100}
            disabled={busy !== null}
            onChange={(text) => setDraft((old) => ({ ...old, [axis]: text }))}
          />
        ))}
      </div>
      <Button
        act={act}
        size='sm'
        disabled={busy !== null || problem !== null}
        disabledReason={busy ?? problem ?? undefined}
        onClick={() => {
          if (community !== null) onSave(community, values)
          setDraft({})
        }}
      >
        <Save />
        Hold this regard
      </Button>
    </div>
  )
}

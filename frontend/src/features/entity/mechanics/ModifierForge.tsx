import { useState } from 'react'
import {
  Anvil,
  Hourglass,
  Layers,
  Lock,
  Pencil,
  Plus,
  Sigma,
  Trash2,
  Unlock,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
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
import { Medallion } from '@/components/domain'
import { ChoiceTiles } from '@/components/domain/SettingsKit'
import { Label, Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { humanize } from '../actions/schema'
import { named } from '../environment/labels'
import { badgeVariant } from '../realm/labels'
import { NumberField, RecordField } from '../realm/parts'
import {
  DERIVED_SOURCES,
  FORGEABLE_SOURCES,
  MODIFIER_SOURCE,
  VIRTUAL_KEYS,
} from './labels'

type Modifier = components['schemas']['ModifierRecord']
type Op = 'add' | 'multiply'
type Source = components['schemas']['ModifierSource']

const OPS = [
  { value: 'add', label: 'Add', hint: 'Shift the value', icon: Plus },
  {
    value: 'multiply',
    label: 'Multiply',
    hint: 'Scale the value',
    icon: Sigma,
  },
] as const

function whole(value: string): number | null {
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

function percent(value: string): number | null {
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) && parsed >= 0 && parsed <= 100 ? parsed : null
}

export function shiftText(op: string, magnitude: number): string {
  if (op === 'multiply') return `× ${magnitude}`
  return `${magnitude > 0 ? '+' : ''}${magnitude}`
}

export function ModifierCard({
  modifier,
  blocked,
}: {
  modifier: Modifier
  blocked: string | undefined
}) {
  const spec = named(MODIFIER_SOURCE, modifier.source_kind)
  const [editing, setEditing] = useState(false)
  const [magnitude, setMagnitude] = useState(String(modifier.magnitude))
  const [epochs, setEpochs] = useState('')
  const [group, setGroup] = useState(modifier.stacking_group ?? '')
  const edit = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/modifier:edit', {
          body: {
            modifier_id: modifier.id,
            magnitude: Number(magnitude),
            epochs: whole(epochs),
            stacking_group: group === '' ? null : group,
            clear_stacking_group: group === '',
            clear_source_node: false,
            endless: false,
            clear_decay: false,
          },
        })
      ),
    success: 'The modifier is reshaped',
    onDone: () => setEditing(false),
  })
  const hold = useGodAction({
    run: (held: boolean) =>
      unwrap(
        api.POST(
          held ? '/api/actions/modifier:hold' : '/api/actions/modifier:release',
          { body: { modifier_id: modifier.id } }
        )
      ),
  })
  const remove = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/modifier:remove', {
          body: { modifier_id: modifier.id },
        })
      ),
    success: 'Modifier removed',
  })
  const busy =
    blocked ??
    ([edit, hold, remove].some((item) => item.isPending)
      ? 'Another change is being applied.'
      : undefined)
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={spec.icon} tone={spec.tone ?? 'gold'} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text weight='medium' truncate>
            {`${humanize(modifier.key)} ${shiftText(modifier.op, modifier.magnitude)}`}
          </Text>
          <Muted variant='caption' truncate>
            {`${modifier.reason} · ${humanize(modifier.source_subsystem)}`}
          </Muted>
        </div>
        <Badge size='sm' variant={badgeVariant(spec.tone)}>
          {spec.label}
        </Badge>
        {modifier.held && (
          <Badge size='sm' variant='warning'>
            <Lock aria-hidden='true' />
            Held
          </Badge>
        )}
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Badge size='sm' variant='outline'>
          <Hourglass aria-hidden='true' />
          {modifier.end_epoch !== null
            ? `Until epoch ${modifier.end_epoch}`
            : 'No end'}
        </Badge>
        {modifier.decay_pct !== null && (
          <Badge size='sm' variant='outline'>
            {`Fades ${modifier.decay_pct}% an epoch`}
          </Badge>
        )}
        {modifier.stacking_group && (
          <Badge size='sm' variant='outline'>
            <Layers aria-hidden='true' />
            {humanize(modifier.stacking_group)}
          </Badge>
        )}
        <div className='ml-auto flex shrink-0 items-center gap-1'>
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== undefined}
            disabledReason={busy}
            onClick={() => setEditing((value) => !value)}
          >
            <Pencil />
            Edit
          </Button>
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== undefined}
            disabledReason={busy}
            onClick={() => hold.mutate(!modifier.held)}
          >
            {modifier.held ? <Unlock /> : <Lock />}
            {modifier.held ? 'Release' : 'Hold'}
          </Button>
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== undefined}
            disabledReason={busy}
            onClick={() => remove.mutate()}
          >
            <Trash2 />
            Remove
          </Button>
        </div>
      </div>
      {editing && (
        <div className='@container/edit grid min-w-0 grid-cols-1 gap-2 rounded-lg border border-dashed bg-muted/20 p-2 @md/edit:grid-cols-3'>
          <NumberField
            label={modifier.op === 'multiply' ? 'Factor' : 'Amount'}
            value={magnitude}
            blocked={busy ?? null}
            onChange={setMagnitude}
          />
          <NumberField
            label='Epochs from now'
            value={epochs}
            min={1}
            placeholder='Keep the end'
            blocked={busy ?? null}
            onChange={setEpochs}
          />
          <div className='flex min-w-0 flex-col gap-1'>
            <Label as='label' htmlFor={`group-${modifier.id}`}>
              Stacking group
            </Label>
            <Input
              id={`group-${modifier.id}`}
              value={group}
              placeholder='Stacks freely'
              onChange={(event) => setGroup(event.target.value)}
            />
          </div>
          <Button
            size='sm'
            className='self-start'
            disabled={busy !== undefined || magnitude === ''}
            disabledReason={busy}
            onClick={() => edit.mutate()}
          >
            Save
          </Button>
        </div>
      )}
    </li>
  )
}

export function ModifierForge({
  nodeId,
  statKeys,
  blocked,
}: {
  nodeId: number
  statKeys: string[]
  blocked: string | undefined
}) {
  const keys = [...statKeys, ...VIRTUAL_KEYS]
  const [source, setSource] = useState<Source>('player')
  const [key, setKey] = useState(keys[0] ?? '')
  const [op, setOp] = useState<Op>('add')
  const [magnitude, setMagnitude] = useState('')
  const [epochs, setEpochs] = useState('')
  const [decay, setDecay] = useState('')
  const [group, setGroup] = useState('')
  const [origin, setOrigin] = useState<number | null>(null)
  const forge = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/modifier:create', {
          body: {
            node_id: nodeId,
            key,
            op,
            magnitude: Number(magnitude),
            source_kind: source,
            source_node_id: origin,
            stacking_group: group === '' ? null : group,
            epochs: whole(epochs),
            decay_pct: percent(decay),
          },
        })
      ),
    success: 'A new modifier bends the record',
  })
  const missing = !key
    ? 'Pick a value first.'
    : magnitude === ''
      ? 'Enter a size first.'
      : null
  const busy =
    blocked ?? (forge.isPending ? 'Forging the modifier.' : undefined)
  return (
    <div
      data-surface='ModifierForge'
      className='@container/forge flex min-w-0 flex-col gap-3 rounded-lg border border-dashed bg-muted/20 p-3'
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={Anvil} tone='gold' size='sm' />
        <div className='flex min-w-0 flex-col'>
          <Text weight='semibold'>Forge a modifier</Text>
          <Muted variant='caption'>
            Any source, any value. A modifier you forge from an engine source is
            held, so the engine keeps it until you release it.
          </Muted>
        </div>
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 @lg/forge:grid-cols-2'>
        <div className='flex min-w-0 flex-col gap-1'>
          <Label>Source</Label>
          <Select
            value={source}
            onValueChange={(value) => setSource(value as Source)}
          >
            <SelectTrigger aria-label='Source'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {FORGEABLE_SOURCES.map((item) => {
                const spec = named(MODIFIER_SOURCE, item)
                const Icon = spec.icon
                return (
                  <SelectItem key={item} value={item}>
                    <Icon aria-hidden='true' />
                    {spec.label}
                    {DERIVED_SOURCES.has(item) ? ' · engine source' : ''}
                  </SelectItem>
                )
              })}
            </SelectContent>
          </Select>
        </div>
        <div className='flex min-w-0 flex-col gap-1'>
          <Label>Value</Label>
          <Select value={key} onValueChange={setKey}>
            <SelectTrigger aria-label='Value to bend'>
              <SelectValue placeholder='Value' />
            </SelectTrigger>
            <SelectContent>
              {keys.map((item) => (
                <SelectItem key={item} value={item}>
                  {humanize(item)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <ChoiceTiles
        label='Operation'
        value={op}
        options={OPS}
        onChange={setOp}
        columns={2}
      />
      <div className='grid min-w-0 grid-cols-1 gap-3 @lg/forge:grid-cols-4'>
        <NumberField
          label={op === 'multiply' ? 'Factor' : 'Amount'}
          value={magnitude}
          blocked={busy ?? null}
          onChange={setMagnitude}
        />
        <NumberField
          label='Epochs'
          value={epochs}
          min={1}
          placeholder='No end'
          blocked={busy ?? null}
          onChange={setEpochs}
        />
        <NumberField
          label='Fades each epoch (%)'
          value={decay}
          min={0}
          max={100}
          placeholder='Never'
          blocked={busy ?? null}
          onChange={setDecay}
        />
        <div className='flex min-w-0 flex-col gap-1'>
          <Label as='label' htmlFor={`forge-group-${nodeId}`}>
            Stacking group
          </Label>
          <Input
            id={`forge-group-${nodeId}`}
            value={group}
            placeholder='Stacks freely'
            onChange={(event) => setGroup(event.target.value)}
          />
        </div>
      </div>
      <RecordField
        label='Coming from (optional)'
        types={null}
        value={origin}
        onChange={setOrigin}
        blocked={busy ?? null}
        placeholder='No source record'
      />
      <Button
        className='self-start'
        disabled={(busy ?? missing) !== null && (busy ?? missing) !== undefined}
        disabledReason={busy ?? missing ?? undefined}
        onClick={() => forge.mutate()}
      >
        <Anvil />
        Forge it
      </Button>
    </div>
  )
}

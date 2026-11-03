import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Cog,
  Lock,
  Pause,
  Play,
  Plus,
  ScrollText,
  Sigma,
  Sparkles,
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
import {
  ChangeChip,
  Medallion,
  Section,
  Timeline,
  TimelineItem,
} from '@/components/domain'
import { ChoiceTiles } from '@/components/domain/SettingsKit'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { humanize } from '../actions/schema'
import { loreKeys } from '../api/keys'

type Modifier = components['schemas']['ModifierRecord']
type Incident = components['schemas']['IncidentRecord']
type Op = 'add' | 'multiply'

const DEFAULT_SUPPRESS_EPOCHS = 1
const WORKING = 'Another change is being applied.'
const PICK_FIELD = 'Pick a field first.'
const PICK_MECHANIC = 'Pick a mechanic first.'
const ENTER_MAGNITUDE = 'Enter a magnitude first.'
const SUPPRESSION_PREFIX = 'mechanic:'
const OPS = [
  {
    value: 'add',
    label: 'Add',
    hint: 'Shift the value by an amount',
    icon: Plus,
  },
  {
    value: 'multiply',
    label: 'Multiply',
    hint: 'Scale the value by a factor',
    icon: Sigma,
  },
] as const
const ROLE_TONE = {
  subject: 'primary',
  actor: 'success',
  target: 'destructive',
  witness: 'default',
  place: 'default',
} as const
const ROLE_LABEL: Record<string, string> = {
  subject: 'About it',
  actor: 'It acted',
  target: 'It was struck',
  witness: 'It witnessed',
  place: 'It happened here',
}

function mechanicsKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'mechanics'] as const
}

function positive(value: string): number | null {
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

function incidentTitle(kind: string): { title: string; area: string | null } {
  const parts = kind.split('.').filter((part) => part !== 'folded')
  if (parts.length === 1) return { title: humanize(parts[0]), area: null }
  return { title: humanize(parts[parts.length - 1]), area: humanize(parts[0]) }
}

function modifierText(modifier: Modifier): string {
  if (modifier.op === 'multiply') return `× ${modifier.magnitude}`
  return `${modifier.magnitude > 0 ? '+' : ''}${modifier.magnitude}`
}

function ModifierRow({
  modifier,
  blocked,
  onRemove,
}: {
  modifier: Modifier
  blocked: string | undefined
  onRemove: () => void
}) {
  return (
    <li className='flex min-w-0 flex-wrap items-center gap-3 rounded-lg border bg-muted/30 p-2'>
      <Medallion
        icon={Sparkles}
        tone={modifier.op === 'multiply' ? 'verdigris' : 'gold'}
        size='sm'
      />
      <div className='flex min-w-0 flex-1 flex-col'>
        <Text weight='medium' truncate>
          {`${humanize(modifier.key)} ${modifierText(modifier)}`}
        </Text>
        <Muted variant='caption' truncate>
          {modifier.end_epoch !== null
            ? `Until epoch ${modifier.end_epoch}`
            : 'Lasts until removed'}
          {modifier.decay_pct !== null &&
            ` · fades ${modifier.decay_pct}% each epoch`}
        </Muted>
      </div>
      <Badge size='sm' variant='info'>
        {humanize(modifier.source_kind)}
      </Badge>
      <Button
        size='sm'
        variant='ghost'
        disabled={blocked !== undefined}
        disabledReason={blocked}
        onClick={onRemove}
      >
        <Trash2 />
        Remove
      </Button>
    </li>
  )
}

function IncidentItem({
  incident,
  last,
}: {
  incident: Incident
  last: boolean
}) {
  const { title, area } = incidentTitle(incident.kind)
  return (
    <TimelineItem
      icon={ScrollText}
      tone={ROLE_TONE[incident.role]}
      title={title}
      timestamp={
        incident.year !== null
          ? `Year ${incident.year} · epoch ${incident.epoch}`
          : `Epoch ${incident.epoch}`
      }
      last={last}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        {area && (
          <Badge size='sm' variant='secondary'>
            {area}
          </Badge>
        )}
        <Badge size='sm' variant='outline'>
          {ROLE_LABEL[incident.role] ?? humanize(incident.role)}
        </Badge>
        {incident.magnitude > 0 && (
          <Badge size='sm' variant='warning'>
            {`Weight ${incident.magnitude}`}
          </Badge>
        )}
      </div>
    </TimelineItem>
  )
}

export function EntityMechanics({
  nodeId,
  statKeys,
  readOnlyReason,
}: {
  nodeId: number
  statKeys: string[]
  readOnlyReason: string | null
}) {
  const view = useQuery({
    queryKey: mechanicsKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/nodes/{node_id}/mechanics', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
  const mechanics = useQuery({
    queryKey: [...loreKeys.catalogue, 'mechanics'] as const,
    queryFn: () => unwrap(api.GET('/api/mechanics')),
  })
  const [field, setField] = useState(statKeys[0] ?? '')
  const [op, setOp] = useState<Op>('add')
  const [magnitude, setMagnitude] = useState('')
  const [epochs, setEpochs] = useState('')
  const [mechanic, setMechanic] = useState('')
  const pin = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/lever:pin', {
          body: { node_id: nodeId, key: field, epochs: positive(epochs) },
        })
      ),
    success: `${humanize(field)} is pinned`,
  })
  const unpin = useGodAction({
    run: (key: string) =>
      unwrap(
        api.POST('/api/actions/lever:unpin', { body: { node_id: nodeId, key } })
      ),
    success: 'The field is free again',
  })
  const suppress = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/lever:suppress', {
          body: {
            node_id: nodeId,
            mechanic,
            epochs: positive(epochs) ?? DEFAULT_SUPPRESS_EPOCHS,
          },
        })
      ),
    success: 'The mechanic is held back here',
  })
  const unsuppress = useGodAction({
    run: (key: string) =>
      unwrap(
        api.POST('/api/actions/lever:unsuppress', {
          body: { node_id: nodeId, mechanic: key },
        })
      ),
    success: 'The mechanic acts here again',
  })
  const runNow = useGodAction({
    run: () =>
      unwrap(api.POST('/api/actions/lever:run', { body: { mechanic } })),
  })
  const add = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/modifier:add', {
          body: {
            node_id: nodeId,
            key: field,
            op,
            magnitude: Number(magnitude),
            epochs: positive(epochs),
          },
        })
      ),
    success: 'Modifier added',
  })
  const remove = useGodAction({
    run: (modifierId: number) =>
      unwrap(
        api.POST('/api/actions/modifier:remove', {
          body: { modifier_id: modifierId },
        })
      ),
    success: 'Modifier removed',
  })
  const data = view.data
  const pending = [pin, unpin, suppress, unsuppress, runNow, add, remove].some(
    (item) => item.isPending
  )
  const blocked = readOnlyReason ?? (pending ? WORKING : undefined)
  const needs = (missing: string | null) => blocked ?? missing ?? undefined
  const titles = new Map(
    (mechanics.data ?? []).map((item) => [item.key, item.title])
  )
  const mechanicName = (key: string) =>
    titles.get(key.replace(SUPPRESSION_PREFIX, '')) ??
    humanize(key.replace(SUPPRESSION_PREFIX, ''))
  return (
    <Section
      id='section-mechanics'
      title='Mechanics'
      description='What bends this record right now: modifiers on its values, fields you pinned, mechanics you held back, and the incidents it took part in.'
      icon={Cog}
    >
      {data && (
        <div className='@container/mech flex min-w-0 flex-col gap-4'>
          {data.effective.length > 0 && (
            <div className='grid min-w-0 grid-cols-1 gap-2 @md/mech:grid-cols-2 @xl/mech:grid-cols-3'>
              {data.effective.map((value) => (
                <div
                  key={value.key}
                  className='flex min-w-0 items-center gap-2 rounded-lg border bg-background p-2'
                >
                  <div className='flex min-w-0 flex-1 flex-col'>
                    <Stat value={Number(value.value.toFixed(1))} />
                    <Label truncate>{humanize(value.key)}</Label>
                  </div>
                  <ChangeChip
                    value={Number((value.value - value.base).toFixed(1))}
                    label={`from ${value.base}`}
                  />
                </div>
              ))}
            </div>
          )}
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>Modifiers</Label>
            {data.modifiers.length === 0 ? (
              <Muted>Nothing is bending this record's values.</Muted>
            ) : (
              <ul className='flex min-w-0 flex-col gap-2'>
                {data.modifiers.map((modifier) => (
                  <ModifierRow
                    key={modifier.id}
                    modifier={modifier}
                    blocked={needs(null)}
                    onRemove={() => remove.mutate(modifier.id)}
                  />
                ))}
              </ul>
            )}
          </div>
          {(data.pins.length > 0 || data.suppressions.length > 0) && (
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              {data.pins.map((guard) => (
                <Button
                  key={`pin-${guard.id}`}
                  size='sm'
                  variant='outline'
                  disabled={needs(null) !== undefined}
                  disabledReason={needs(null)}
                  onClick={() => unpin.mutate(guard.key)}
                >
                  <Unlock />
                  {`Release ${humanize(guard.key).toLowerCase()}${guard.end_epoch !== null ? ` (pinned to epoch ${guard.end_epoch})` : ''}`}
                </Button>
              ))}
              {data.suppressions.map((guard) => (
                <Button
                  key={`suppression-${guard.id}`}
                  size='sm'
                  variant='outline'
                  disabled={needs(null) !== undefined}
                  disabledReason={needs(null)}
                  onClick={() =>
                    unsuppress.mutate(guard.key.replace(SUPPRESSION_PREFIX, ''))
                  }
                >
                  <Play />
                  {`Let ${mechanicName(guard.key)} act`}
                </Button>
              ))}
            </div>
          )}
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>Recent incidents</Label>
            {data.incidents.length === 0 ? (
              <Muted>It has not taken part in anything yet.</Muted>
            ) : (
              <Timeline label='Recent incidents'>
                {data.incidents.map((incident, index) => (
                  <IncidentItem
                    key={incident.id}
                    incident={incident}
                    last={index === data.incidents.length - 1}
                  />
                ))}
              </Timeline>
            )}
          </div>
        </div>
      )}
      <div className='@container/mech flex min-w-0 flex-col gap-4 rounded-lg border border-dashed bg-muted/20 p-3'>
        <div className='flex min-w-0 flex-col gap-0.5'>
          <Text weight='semibold'>Bend the mechanics</Text>
          <Muted variant='caption'>
            Add a modifier, pin a field so nothing can change it, or hold a
            mechanic back on this record. Leave epochs empty for no end; every
            change goes into the ledger and can be undone.
          </Muted>
        </div>
        <ChoiceTiles
          label='Operation'
          value={op}
          options={OPS}
          onChange={setOp}
          columns={2}
        />
        <div className='grid min-w-0 grid-cols-1 gap-3 @lg/mech:grid-cols-3'>
          <div className='flex min-w-0 flex-col gap-1'>
            <Label>Field</Label>
            <Select value={field} onValueChange={setField}>
              <SelectTrigger aria-label='Field'>
                <SelectValue placeholder='Field' />
              </SelectTrigger>
              <SelectContent>
                {statKeys.map((key) => (
                  <SelectItem key={key} value={key}>
                    {humanize(key)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className='flex min-w-0 flex-col gap-1'>
            <Label as='label' htmlFor={`modifier-magnitude-${nodeId}`}>
              {op === 'multiply' ? 'Factor' : 'Amount'}
            </Label>
            <Input
              id={`modifier-magnitude-${nodeId}`}
              inputMode='decimal'
              value={magnitude}
              onChange={(event) => setMagnitude(event.target.value)}
            />
          </div>
          <div className='flex min-w-0 flex-col gap-1'>
            <Label as='label' htmlFor={`modifier-epochs-${nodeId}`}>
              Epochs
            </Label>
            <Input
              id={`modifier-epochs-${nodeId}`}
              inputMode='numeric'
              placeholder='No end'
              value={epochs}
              onChange={(event) => setEpochs(event.target.value)}
            />
          </div>
        </div>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Button
            disabled={
              needs(
                !field ? PICK_FIELD : magnitude === '' ? ENTER_MAGNITUDE : null
              ) !== undefined
            }
            disabledReason={needs(
              !field ? PICK_FIELD : magnitude === '' ? ENTER_MAGNITUDE : null
            )}
            onClick={() => add.mutate()}
          >
            <Plus />
            Add modifier
          </Button>
          <Button
            variant='outline'
            disabled={needs(!field ? PICK_FIELD : null) !== undefined}
            disabledReason={needs(!field ? PICK_FIELD : null)}
            onClick={() => pin.mutate()}
          >
            <Lock />
            Pin this field
          </Button>
        </div>
        <div className='flex min-w-0 flex-wrap items-end gap-2'>
          <div className='flex min-w-0 flex-1 flex-col gap-1'>
            <Label>Mechanic</Label>
            <Select value={mechanic} onValueChange={setMechanic}>
              <SelectTrigger aria-label='Mechanic'>
                <SelectValue placeholder='Pick a mechanic' />
              </SelectTrigger>
              <SelectContent>
                {(mechanics.data ?? []).map((item) => (
                  <SelectItem key={item.key} value={item.key}>
                    {item.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button
            variant='outline'
            disabled={needs(!mechanic ? PICK_MECHANIC : null) !== undefined}
            disabledReason={needs(!mechanic ? PICK_MECHANIC : null)}
            onClick={() => suppress.mutate()}
          >
            <Pause />
            Hold it back here
          </Button>
          <Button
            variant='outline'
            disabled={needs(!mechanic ? PICK_MECHANIC : null) !== undefined}
            disabledReason={needs(!mechanic ? PICK_MECHANIC : null)}
            onClick={() => runNow.mutate()}
          >
            <Play />
            Run it now
          </Button>
        </div>
        {readOnlyReason && <Muted variant='caption'>{readOnlyReason}</Muted>}
      </div>
    </Section>
  )
}

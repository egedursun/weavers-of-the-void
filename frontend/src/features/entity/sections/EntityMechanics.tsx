import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Cog, Lock, Pause, Play, Plus, Trash2, Unlock } from 'lucide-react'
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
import { Section } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { loreKeys } from '../api/keys'
import { useLoreMutation } from '../api/mutations'

const OPS = ['add', 'multiply'] as const
type Op = (typeof OPS)[number]
const DEFAULT_SUPPRESS_EPOCHS = 1
const BUSY_REASON = 'Another change is being applied.'
const PICK_FIELD = 'Pick a field first.'
const PICK_MECHANIC = 'Pick a mechanic first.'
const ENTER_MAGNITUDE = 'Enter a magnitude first.'

function mechanicsKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'mechanics'] as const
}

function useNodeMechanics(nodeId: number) {
  return useQuery({
    queryKey: mechanicsKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/nodes/{node_id}/mechanics', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

function useMechanicList() {
  return useQuery({
    queryKey: [...loreKeys.catalogue, 'mechanics'] as const,
    queryFn: () => unwrap(api.GET('/api/mechanics')),
  })
}

function positive(value: string): number | null {
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
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
  const view = useNodeMechanics(nodeId)
  const mechanics = useMechanicList()
  const invalidate = [mechanicsKey(nodeId)]
  const [field, setField] = useState(statKeys[0] ?? '')
  const [op, setOp] = useState<Op>('add')
  const [magnitude, setMagnitude] = useState('')
  const [epochs, setEpochs] = useState('')
  const [mechanic, setMechanic] = useState('')
  const pin = useLoreMutation({
    run: () =>
      unwrap(
        api.POST('/api/actions/lever:pin', {
          body: { node_id: nodeId, key: field, epochs: positive(epochs) },
        })
      ),
    invalidate,
  })
  const unpin = useLoreMutation({
    run: (key: string) =>
      unwrap(
        api.POST('/api/actions/lever:unpin', { body: { node_id: nodeId, key } })
      ),
    invalidate,
  })
  const suppress = useLoreMutation({
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
    invalidate,
  })
  const unsuppress = useLoreMutation({
    run: (key: string) =>
      unwrap(
        api.POST('/api/actions/lever:unsuppress', {
          body: { node_id: nodeId, mechanic: key },
        })
      ),
    invalidate,
  })
  const run = useLoreMutation({
    run: () =>
      unwrap(api.POST('/api/actions/lever:run', { body: { mechanic } })),
    invalidate,
  })
  const add = useLoreMutation({
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
    invalidate,
  })
  const remove = useLoreMutation({
    run: (modifierId: number) =>
      unwrap(
        api.POST('/api/actions/modifier:remove', {
          body: { modifier_id: modifierId },
        })
      ),
    invalidate,
  })
  const data = view.data
  const busyNow =
    pin.isPending ||
    suppress.isPending ||
    run.isPending ||
    add.isPending ||
    remove.isPending
  const blocked = readOnlyReason ?? (busyNow ? BUSY_REASON : undefined)
  const needs = (missing: string | null) => blocked ?? missing ?? undefined
  return (
    <Section
      id='section-mechanics'
      title='Mechanics'
      description='Modifiers acting on this record, pinned fields, suppressed mechanics and the incidents it took part in.'
      icon={Cog}
    >
      {data && (
        <div className='flex min-w-0 flex-col gap-4'>
          {data.effective.length > 0 && (
            <div className='flex min-w-0 flex-col gap-2'>
              <Label variant='overline'>Effective values</Label>
              {data.effective.map((value) => (
                <Text key={value.key}>
                  {value.key}: {value.base} → {value.value.toFixed(1)}
                </Text>
              ))}
            </div>
          )}
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>Modifiers</Label>
            {data.modifiers.length === 0 && <Muted>No modifiers.</Muted>}
            {data.modifiers.map((modifier) => (
              <div
                key={modifier.id}
                className='flex min-w-0 flex-wrap items-center gap-2'
              >
                <Badge size='sm' variant='info'>
                  {modifier.source_kind}
                </Badge>
                <Text>
                  {modifier.key}{' '}
                  {modifier.op === 'multiply'
                    ? `times ${modifier.magnitude}`
                    : modifier.magnitude}
                  {modifier.end_epoch !== null &&
                    ` until epoch ${modifier.end_epoch}`}
                </Text>
                <Button
                  size='sm'
                  variant='ghost'
                  disabled={needs(null) !== undefined}
                  disabledReason={needs(null)}
                  onClick={() => remove.mutate(modifier.id)}
                >
                  <Trash2 />
                  Remove
                </Button>
              </div>
            ))}
          </div>
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
                Unpin {guard.key}
              </Button>
            ))}
            {data.suppressions.map((guard) => (
              <Button
                key={`suppression-${guard.id}`}
                size='sm'
                variant='outline'
                disabled={needs(null) !== undefined}
                disabledReason={needs(null)}
                onClick={() => unsuppress.mutate(guard.key)}
              >
                <Play />
                Let {guard.key} act
              </Button>
            ))}
          </div>
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>Recent incidents</Label>
            {data.incidents.length === 0 && <Muted>No incidents yet.</Muted>}
            {data.incidents.map((incident) => (
              <Text key={incident.id}>
                Epoch {incident.epoch}: {incident.kind} ({incident.role})
              </Text>
            ))}
          </div>
        </div>
      )}
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Select value={field} onValueChange={setField}>
          <SelectTrigger aria-label='Field'>
            <SelectValue placeholder='Field' />
          </SelectTrigger>
          <SelectContent>
            {statKeys.map((key) => (
              <SelectItem key={key} value={key}>
                {key}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={op} onValueChange={(value) => setOp(value as Op)}>
          <SelectTrigger aria-label='Operation'>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {OPS.map((item) => (
              <SelectItem key={item} value={item}>
                {item}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          aria-label='Magnitude'
          inputMode='decimal'
          placeholder='Magnitude'
          value={magnitude}
          onChange={(event) => setMagnitude(event.target.value)}
        />
        <Input
          aria-label='Epochs'
          inputMode='numeric'
          placeholder='Epochs'
          value={epochs}
          onChange={(event) => setEpochs(event.target.value)}
        />
        <Button
          size='sm'
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
          size='sm'
          variant='outline'
          disabled={needs(!field ? PICK_FIELD : null) !== undefined}
          disabledReason={needs(!field ? PICK_FIELD : null)}
          onClick={() => pin.mutate()}
        >
          <Lock />
          Pin field
        </Button>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Select value={mechanic} onValueChange={setMechanic}>
          <SelectTrigger aria-label='Mechanic'>
            <SelectValue placeholder='Mechanic' />
          </SelectTrigger>
          <SelectContent>
            {(mechanics.data ?? []).map((item) => (
              <SelectItem key={item.key} value={item.key}>
                {item.title}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          size='sm'
          variant='outline'
          disabled={needs(!mechanic ? PICK_MECHANIC : null) !== undefined}
          disabledReason={needs(!mechanic ? PICK_MECHANIC : null)}
          onClick={() => suppress.mutate()}
        >
          <Pause />
          Suppress here
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={needs(!mechanic ? PICK_MECHANIC : null) !== undefined}
          disabledReason={needs(!mechanic ? PICK_MECHANIC : null)}
          onClick={() => run.mutate()}
        >
          <Play />
          Run now
        </Button>
      </div>
      {readOnlyReason && <Muted variant='caption'>{readOnlyReason}</Muted>}
    </Section>
  )
}

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Anchor,
  DoorOpen,
  Hammer,
  Leaf,
  ShieldCheck,
  Sprout,
  Trash2,
} from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { type Named } from '@/features/entity/environment/labels'
import { ThingPicker } from '@/features/gatherings/parts'
import { useMadeAction } from '@/features/minds/api'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import { Chip, type Field, ForgeCard, RecordEditor } from './parts'

type RiftControlView = components['schemas']['RiftControlView']
type Edit = { values: EditValues; release: string[] }

const HOLD =
  'Values you set are held against the engine until you release them.'
const REALMS = ['polity'] as const

const RIFT_WORKS: Record<components['schemas']['RiftWork'], Named> = {
  none: { label: 'Left alone', icon: Sprout, tone: 'muted' },
  sealing: { label: 'Being sealed', icon: ShieldCheck, tone: 'success' },
  stabilising: { label: 'Being steadied', icon: Anchor, tone: 'info' },
  gate: { label: 'Gated for a toll', icon: DoorOpen, tone: 'gold' },
}

const CONTROL_FIELDS: readonly Field[] = [
  {
    key: 'work',
    label: 'Work on it',
    kind: 'pick',
    table: Object.fromEntries(
      Object.entries(RIFT_WORKS).map(([key, value]) => [key, value.label])
    ),
  },
  { key: 'toll', label: 'Toll per crossing', kind: 'number', min: 0 },
  {
    key: 'adapted',
    label: 'Life adapted to it',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'claimant_entity_id',
    label: 'Claimed by',
    kind: 'node',
    types: ['polity'],
  },
]

export function useRiftControls() {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'rift-controls'] as const,
    queryFn: () => unwrap(api.GET('/api/rifts/controls')),
  })
}

export function RiftControl({
  riftId,
  control,
  blocked,
}: {
  riftId: number
  control: RiftControlView | undefined
  blocked: string | null
}) {
  const [work, setWork] = useState<string>(control?.work ?? 'stabilising')
  const [claimant, setClaimant] = useState<number | null>(
    control?.claimant?.id ?? null
  )
  const [toll, setToll] = useState(String(control?.toll ?? 0))
  const setting = useMadeAction(
    'rift_control:set',
    (_: void) => ({
      rift_id: riftId,
      work: work as RiftControlView['work'],
      claimant_id: claimant,
      toll: Math.max(0, Number(toll) || 0),
    }),
    'The hold on the rift is set'
  )
  const editing = useMadeAction(
    'rift_control:edit',
    (vars: Edit) => ({
      rift_id: riftId,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The hold on the rift is set'
  )
  const removing = useMadeAction(
    'rift_control:delete',
    (_: void) => ({ rift_id: riftId }),
    'The rift is held by no one'
  )
  const named = control ? RIFT_WORKS[control.work] : null
  return (
    <>
      {control && named ? (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Chip icon={named.icon}>{named.label}</Chip>
          <Chip icon={Hammer}>
            {control.claimant
              ? `Claimed by ${control.claimant.name}${control.claimed_epoch !== null ? ` in epoch ${control.claimed_epoch}` : ''}`
              : 'Claimed by no realm'}
          </Chip>
          <Chip icon={DoorOpen}>Toll {control.toll}</Chip>
          <Chip icon={Leaf}>Life adapted {control.adapted}/100</Chip>
        </div>
      ) : null}
      {control ? (
        <>
          <RecordEditor
            act={editing}
            title='Set the hold on this rift'
            note={HOLD}
            fields={CONTROL_FIELDS}
            locked={control.locked}
            busy={why(blocked, editing.isPending)}
            onSave={(values) => editing.mutate({ values, release: [] })}
            onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
          />
          <StepButton
            act={removing}
            icon={Trash2}
            label='Free it from its holder'
            busy={why(blocked, removing.isPending)}
            onClick={() => removing.mutate()}
          />
        </>
      ) : (
        <ForgeCard
          icon={Hammer}
          tone='gold'
          title='Hold this rift'
          note='A realm claims it and works on it: sealing shrinks it, steadying keeps it from collapse, every party crossing a gate pays its keeper a toll from its own purse.'
          columns={3}
          action={
            <StepButton
              act={setting}
              icon={Hammer}
              label='Hold it'
              variant='default'
              busy={why(blocked, setting.isPending)}
              onClick={() => setting.mutate()}
            />
          }
        >
          <ChoiceField
            label='Work on it'
            value={work}
            table={RIFT_WORKS}
            blocked={blocked}
            onPick={setWork}
          />
          <ThingPicker
            label='Claimed by'
            value={claimant}
            onChange={setClaimant}
            blocked={blocked}
            types={REALMS}
          />
          <NumberField
            label='Toll per crossing'
            value={toll}
            min={0}
            onChange={setToll}
          />
        </ForgeCard>
      )}
    </>
  )
}

import { useState } from 'react'
import {
  Anchor,
  Crown,
  Gauge,
  Hammer,
  Package,
  Ship,
  Sparkles,
  Users,
  Waves,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EntityLink, IconStat, Section, StatBar } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { RecordPanel } from './RecordPanel'
import {
  ARMAMENT,
  HULL,
  VESSEL_STATUS,
  depthKeys,
  nameOf,
  useHulls,
  useVessel,
} from './depth'
import { busyOf } from './labels'
import {
  Adjust,
  ChoiceField,
  FieldGrid,
  Panel,
  Tag,
  ToggleField,
} from './parts'

type Hull = components['schemas']['HullClass']
type Arm = components['schemas']['VesselArmament']

function Arms({
  value,
  onChange,
  blocked,
}: {
  value: string[]
  onChange: (next: string[]) => void
  blocked: string | null
}) {
  return (
    <FieldGrid>
      {Object.entries(ARMAMENT).map(([key, item]) => (
        <ToggleField
          key={key}
          item={item}
          checked={value.includes(key)}
          disabled={blocked !== null}
          onChange={(next) =>
            onChange(
              next ? [...value, key] : value.filter((entry) => entry !== key)
            )
          }
        />
      ))}
    </FieldGrid>
  )
}

export function VesselCard({
  vesselId,
  blocked,
}: {
  vesselId: number
  blocked: string | null
}) {
  const query = useVessel(vesselId)
  const [hull, setHull] = useState<string>('')
  const [arms, setArms] = useState<string[] | null>(null)
  const vessel = query.data
  const invalidate = [depthKeys.vessel(vesselId) as unknown as unknown[]]
  const refit = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/vessel:refit', {
          body: {
            vessel_id: vesselId,
            hull_class: (hull || vessel?.hull.hull) as Hull,
            armament: (arms ?? vessel?.armament ?? []) as Arm[],
          },
        })
      ),
    invalidate,
  })
  const repair = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/vessel:repair', {
          body: { vessel_id: vesselId },
        })
      ),
    invalidate,
  })
  if (!vessel) return <Muted variant='caption'>Reading the ship's log…</Muted>
  const status = nameOf(VESSEL_STATUS, vessel.status)
  const busy = busyOf(blocked, refit.isPending, repair.isPending)
  return (
    <Panel
      title='Vessel'
      icon={Ship}
      tone='info'
      hint={`${vessel.hull.label} · ${status.label}`}
    >
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Tag item={nameOf(HULL, vessel.hull.hull)} />
        <Tag item={status} />
        {vessel.armament.map((arm) => (
          <Tag key={arm} item={nameOf(ARMAMENT, arm)} />
        ))}
      </div>
      <StatBar
        label='Hull'
        value={vessel.condition}
        max={100}
        icon={Hammer}
        tone={
          vessel.condition < 40
            ? 'destructive'
            : vessel.condition < 70
              ? 'warning'
              : 'success'
        }
      />
      <StatBar
        label='Seaworthiness'
        value={vessel.seaworthiness}
        max={100}
        icon={Waves}
        tone='info'
      />
      <StatBar
        label='Seamanship'
        value={vessel.seamanship}
        max={100}
        icon={Anchor}
        tone='verdigris'
      />
      <div className='grid min-w-0 grid-cols-2 gap-2 @lg/mil:grid-cols-4'>
        <IconStat icon={Users} label='Crew' value={vessel.crew} tone='info' />
        <IconStat
          icon={Package}
          label='Cargo'
          value={vessel.cargo_capacity}
          tone='gold'
        />
        <IconStat
          icon={Crown}
          label='Renown'
          value={vessel.renown}
          tone='warning'
          hint={vessel.legend ? 'Sung of in a legend' : undefined}
        />
        <IconStat
          icon={Sparkles}
          label='Strangeness'
          value={vessel.strangeness}
          tone='verdigris'
        />
      </div>
      <div className='flex min-w-0 flex-wrap gap-x-3 gap-y-1'>
        {(
          [
            ['Owner', vessel.owner],
            ['Captain', vessel.captain],
            ['Home port', vessel.home_port],
            ['Waters', vessel.region],
            ['Fleet', vessel.fleet],
            ['Legend', vessel.legend],
          ] as const
        ).map(([label, ref]) =>
          ref ? (
            <Text key={label} as='span' variant='caption'>
              {label}:{' '}
              <EntityLink kind='entity' id={String(ref.id)}>
                {ref.name}
              </EntityLink>
            </Text>
          ) : null
        )}
        {vessel.hull_material && (
          <Muted variant='caption'>
            Hull of {vessel.hull_material.replaceAll('_', ' ')}
          </Muted>
        )}
        {vessel.fabric_material && (
          <Muted variant='caption'>
            Sails of {vessel.fabric_material.replaceAll('_', ' ')}
          </Muted>
        )}
      </div>
      <div className='flex flex-wrap gap-2'>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || vessel.condition >= 100}

          disabledReason={
            busy !== null || vessel.condition >= 100
              ? (blocked ?? 'Fill in what is needed first')
              : undefined
          }
          onClick={() => repair.mutate()}
        >
          <Hammer />
          Repair at the yard
        </Button>
      </div>
      <Adjust
        title='Refit'
        note='Rebuild the ship to another hull and arms.'
        label='Refit'
      >
        <FieldGrid>
          <ChoiceField
            label='Hull'
            icon={Gauge}
            value={hull || vessel.hull.hull}
            table={HULL}
            blocked={blocked}
            onPick={setHull}
          />
        </FieldGrid>
        <Arms
          value={arms ?? vessel.armament}
          onChange={setArms}
          blocked={blocked}
        />
        <Button
          size='sm'
          className='self-start'
          disabled={busy !== null}

          disabledReason={
            busy !== null
              ? (blocked ?? 'Fill in what is needed first')
              : undefined
          }
          onClick={() => refit.mutate()}
        >
          <Ship />
          Refit
        </Button>
      </Adjust>
      <RecordPanel
        kind='vessel'
        scope={vesselId}
        title='Every value'
        blocked={blocked}
        choices={{ hull_class: HULL, status: VESSEL_STATUS }}
        tone='info'
      />
    </Panel>
  )
}

export function LayDownVessel({
  ownerId,
  blocked,
}: {
  ownerId: number
  blocked: string | null
}) {
  const hulls = useHulls()
  const [name, setName] = useState('')
  const [hull, setHull] = useState('boat')
  const [arms, setArms] = useState<string[]>([])
  const create = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/vessel:create', {
          body: {
            owner_id: ownerId,
            name: name.trim(),
            hull_class: hull as Hull,
            armament: arms as Arm[],
          },
        })
      ),
    onDone: () => setName(''),
  })
  const spec = hulls.data?.find((item) => item.hull === hull)
  return (
    <Adjust
      title='Lay down a vessel'
      note='Choose a hull and its arms; the shipwrights do the rest.'
      label='Lay down a vessel'
    >
      <FieldGrid>
        <label className='flex min-w-0 flex-col gap-1'>
          <Text as='span' variant='caption'>
            Name
          </Text>
          <Input
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <ChoiceField
          label='Hull'
          icon={Ship}
          value={hull}
          table={HULL}
          blocked={blocked}
          onPick={setHull}
        />
      </FieldGrid>
      {spec && (
        <Muted variant='caption'>
          {spec.label}: speed {spec.speed}, cargo {spec.cargo}, crew {spec.crew}
          , seaworthiness {spec.seaworthiness}, {spec.slots} arms
        </Muted>
      )}
      <Arms value={arms} onChange={setArms} blocked={blocked} />
      <Button
        size='sm'
        className='self-start'
        disabled={busyOf(blocked, create.isPending) !== null || !name.trim()}

        disabledReason={
          busyOf(blocked, create.isPending) !== null || !name.trim()
            ? (blocked ?? 'Fill in what is needed first')
            : undefined
        }
        onClick={() => create.mutate()}
      >
        <Anchor />
        Lay down
      </Button>
    </Adjust>
  )
}

export function VesselSection({
  vesselId,
  readOnlyReason,
}: {
  vesselId: number
  readOnlyReason?: string | null
}) {
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  return (
    <Section
      id='section-vessel'
      title='Vessel'
      description='Hull, arms, crew, renown and the sea.'
      icon={Ship}
    >
      <div className='@container/mil min-w-0'>
        <VesselCard vesselId={vesselId} blocked={blocked} />
      </div>
    </Section>
  )
}

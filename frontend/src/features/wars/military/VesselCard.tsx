import { useState } from 'react'
import {
  Anchor,
  Compass,
  Crown,
  Flag,
  Gauge,
  Hammer,
  MapPin,
  Package,
  Ship,
  ShipWheel,
  Sparkles,
  Users,
  Waves,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  EntityLink,
  MiniStat,
  Section,
  StatBar,
  Paged,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { EntityPicker, Held, RecordButtons, TextField } from './controls'
import {
  ARMAMENT,
  HULL,
  MATERIAL,
  type Vessel,
  VESSEL_STATUS,
  depthKeys,
  nameOf,
  useHulls,
  useVessel,
} from './depth'
import { PERCENT, busyOf } from './labels'
import {
  Adjust,
  ChoiceField,
  FieldGrid,
  NumberField,
  Panel,
  Tag,
  ToggleField,
} from './parts'
import { type Values, numbersOf, useRecordActions } from './recordHooks'

const BERTH_NUMBERS = [
  'condition',
  'seaworthiness',
  'seamanship',
  'crew',
  'cargo_capacity',
  'renown',
  'voyages',
] as const
const BERTH_LABEL: Record<string, string> = {
  condition: 'Hull',
  seaworthiness: 'Seaworthiness',
  seamanship: 'Seamanship',
  crew: 'Crew',
  cargo_capacity: 'Cargo',
  renown: 'Renown',
  voyages: 'Voyages',
}
const BERTH_ICON: Record<string, typeof Ship> = {
  condition: Hammer,
  seaworthiness: Waves,
  seamanship: Anchor,
  crew: Users,
  cargo_capacity: Package,
  renown: Crown,
  voyages: Compass,
}
const PERCENT_BERTH = new Set(['condition', 'seaworthiness', 'seamanship'])
const COMMUNITIES = ['people', 'settlement', 'faction', 'cult', 'polity']

function idOf(ref: { id: number } | null): number | null {
  return ref ? ref.id : null
}

function Berth({
  vessel,
  vesselId,
  blocked,
}: {
  vessel: Vessel
  vesselId: number
  blocked: string | null
}) {
  const actions = useRecordActions('vessel', vesselId, vesselId, [
    depthKeys.vessel(vesselId) as unknown as unknown[],
  ])
  const [draft, setDraft] = useState<Values>({})
  const current: Record<string, unknown> = {
    ...vessel,
    status: vessel.status,
    captain_entity_id: idOf(vessel.captain),
    home_port_entity_id: idOf(vessel.home_port),
    region_entity_id: idOf(vessel.region),
    fleet_army_entity_id: idOf(vessel.fleet),
  }
  const value = (key: string) => (key in draft ? draft[key] : current[key])
  const pick = (key: string) =>
    typeof value(key) === 'number' ? (value(key) as number) : null
  return (
    <Adjust
      title='Crew, berth and wear'
      note='Every value of the ship: its wear, its crew and their craft, its cargo, fame and voyages, who captains it, where it berths and sails.'
      label='Crew and berth'
    >
      <FieldGrid>
        <ChoiceField
          label='State'
          icon={Ship}
          value={String(value('status'))}
          table={VESSEL_STATUS}
          blocked={blocked}
          onPick={(next) => setDraft({ ...draft, status: next })}
        />
        <ChoiceField
          label='Hull of'
          icon={Hammer}
          value={String(value('hull_material') ?? 'wood')}
          table={MATERIAL}
          blocked={blocked}
          onPick={(next) => setDraft({ ...draft, hull_material: next })}
        />
        <ChoiceField
          label='Sails of'
          icon={Flag}
          value={String(value('fabric_material') ?? 'cloth')}
          table={MATERIAL}
          blocked={blocked}
          onPick={(next) => setDraft({ ...draft, fabric_material: next })}
        />
        {BERTH_NUMBERS.map((key) => (
          <NumberField
            key={key}
            label={BERTH_LABEL[key]}
            icon={BERTH_ICON[key]}
            value={String(value(key) ?? 0)}
            max={PERCENT_BERTH.has(key) ? PERCENT : undefined}
            onChange={(next) => setDraft({ ...draft, [key]: next })}
          />
        ))}
        <EntityPicker
          label='Captain'
          icon={ShipWheel}
          types={['mortal']}
          value={pick('captain_entity_id')}
          onChange={(next) => setDraft({ ...draft, captain_entity_id: next })}
          blocked={blocked}
        />
        <EntityPicker
          label='Home port'
          icon={Anchor}
          types={['settlement']}
          value={pick('home_port_entity_id')}
          onChange={(next) => setDraft({ ...draft, home_port_entity_id: next })}
          blocked={blocked}
        />
        <EntityPicker
          label='Waters'
          icon={MapPin}
          types={['region']}
          value={pick('region_entity_id')}
          onChange={(next) => setDraft({ ...draft, region_entity_id: next })}
          blocked={blocked}
        />
        <EntityPicker
          label='Sails with'
          icon={Flag}
          types={['army']}
          value={pick('fleet_army_entity_id')}
          onChange={(next) =>
            setDraft({ ...draft, fleet_army_entity_id: next })
          }
          blocked={blocked}
        />
        <EntityPicker
          label='Crewed by'
          icon={Users}
          types={COMMUNITIES}
          value={pick('crew_community_entity_id')}
          onChange={(next) =>
            setDraft({ ...draft, crew_community_entity_id: next })
          }
          blocked={blocked}
        />
      </FieldGrid>
      <RecordButtons
        actions={actions}
        values={numbersOf(draft, BERTH_NUMBERS)}
        locked={vessel.locked}
        blocked={blocked}
        deletable={false}
      />
    </Adjust>
  )
}

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
            hull_class: (hull || vessel?.hull.hull || 'boat') as Hull,
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
  if (query.isError)
    return (
      <Panel title='Vessel' icon={Ship} tone='info'>
        <EmptyState
          icon={Anchor}
          title='Not a ship'
          description='This vessel is a gate, mount or bridge; it keeps no hull, crew or sea log.'
        />
        <Adjust
          title='Fit it out as a ship'
          note='Give it a hull and arms; the shipwrights make it seaworthy.'
          label='Fit out as a ship'
        >
          <FieldGrid>
            <ChoiceField
              label='Hull'
              icon={Gauge}
              value={hull || 'boat'}
              table={HULL}
              blocked={blocked}
              onPick={setHull}
            />
          </FieldGrid>
          <Arms value={arms ?? []} onChange={setArms} blocked={blocked} />
          <Button
            size='sm'
            className='self-start'
            disabled={busyOf(blocked, refit.isPending) !== null}
            disabledReason={busyOf(blocked, refit.isPending) ?? undefined}
            onClick={() => refit.mutate()}
          >
            <Ship />
            Fit out
          </Button>
        </Adjust>
      </Panel>
    )
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
        <Held locked={vessel.locked} />
        <Paged items={vessel.armament}>
          {(arm) => <Tag key={arm} item={nameOf(ARMAMENT, arm)} />}
        </Paged>
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
        <MiniStat icon={Users} label='Crew' value={vessel.crew} tone='info' />
        <MiniStat
          icon={Package}
          label='Cargo'
          value={vessel.cargo_capacity}
          tone='gold'
        />
        <MiniStat
          icon={Crown}
          label='Renown'
          value={vessel.renown}
          tone='warning'
          hint={vessel.legend ? 'Sung of in a legend' : undefined}
        />
        <MiniStat
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
      <div className='flex min-w-0 flex-col gap-2'>
        <Button
          size='sm'
          variant='outline'
          className='self-start'
          disabled={busy !== null || vessel.condition >= 100}

          disabledReason={
            busy !== null || vessel.condition >= 100
              ? (busy ?? 'The hull is whole')
              : undefined
          }
          onClick={() => repair.mutate()}
        >
          <Hammer />
          Repair at the yard
        </Button>
        <Berth vessel={vessel} vesselId={vesselId} blocked={blocked} />
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
            disabledReason={busy ?? undefined}
            onClick={() => refit.mutate()}
          >
            <Ship />
            Refit
          </Button>
        </Adjust>
      </div>
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
        <TextField
          label='Name'
          icon={Ship}
          value={name}
          onChange={setName}
          placeholder='The Saltwind'
        />
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
        <div className='grid min-w-0 grid-cols-2 gap-2 @lg/mil:grid-cols-5'>
          <MiniStat icon={Gauge} label='Speed' value={spec.speed} tone='info' />
          <MiniStat
            icon={Package}
            label='Cargo'
            value={spec.cargo}
            tone='gold'
          />
          <MiniStat icon={Users} label='Crew' value={spec.crew} tone='muted' />
          <MiniStat
            icon={Waves}
            label='Seaworthy'
            value={spec.seaworthiness}
            tone='verdigris'
          />
          <MiniStat
            icon={Anchor}
            label='Arms'
            value={spec.slots}
            tone='warning'
          />
        </div>
      )}
      <Arms value={arms} onChange={setArms} blocked={blocked} />
      <Button
        size='sm'
        className='self-start'
        disabled={busyOf(blocked, create.isPending) !== null || !name.trim()}
        disabledReason={
          busyOf(blocked, create.isPending) ??
          (!name.trim() ? 'Name the ship first' : undefined)
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

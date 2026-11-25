import { useState } from 'react'
import {
  Anchor,
  Compass,
  Crosshair,
  Crown,
  Flag,
  Gauge,
  Hammer,
  MapPin,
  Package,
  Ship,
  ShipWheel,
  Sparkles,
  Swords,
  Users,
  Waves,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  equipmentFamilyValues,
  vehicleSectionValues,
  type components,
} from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  EntityLink,
  MiniStat,
  Section,
  StatBar,
  Paged,
  LoadingBlock,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { humanize } from '@/features/entity/actions/schema'
import { wordOf } from '@/features/entity/affairs/labels'
import { DAMAGE } from '@/features/entity/body/labels'
import { useFrames } from '@/features/madeKinds/api'
import { MOUNT, frameTable } from '@/features/madeKinds/labels'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { ReportSteps } from '@/features/records/ReportSteps'
import { EntityPicker, Held, RecordButtons, TextField } from './controls'
import {
  MATERIAL,
  type Vessel,
  VESSEL_STATUS,
  depthKeys,
  nameOf,
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
      acts={[actions.save, actions.release, actions.remove]}
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

type Frame = components['schemas']['VehicleFrame']
type Weapon = components['schemas']['VesselWeaponView']

function Weapons({ weapons }: { weapons: Weapon[] }) {
  if (weapons.length === 0)
    return (
      <Muted variant='caption'>
        No weapons are mounted; the type of this frame carries none yet.
      </Muted>
    )
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Paged items={weapons}>
        {(weapon) => (
          <div
            key={`${weapon.mount}-${weapon.model_id}-${weapon.section ?? ''}`}
            className='flex min-w-0 flex-wrap items-center gap-1.5'
          >
            <Tag item={nameOf(MOUNT, weapon.mount)} />
            <Text as='span' variant='caption'>
              {`${weapon.count} × ${weapon.model_name} (${wordOf(equipmentFamilyValues, weapon.family)}, ${DAMAGE[weapon.damage_type]})`}
            </Text>
            {weapon.section && (
              <Muted variant='caption'>
                on the {wordOf(vehicleSectionValues, weapon.section)}
              </Muted>
            )}
          </div>
        )}
      </Paged>
    </div>
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
  const frames = useFrames()
  const FRAMES = frameTable(frames.data ?? [])
  const [hull, setHull] = useState<string>('')
  const vessel = query.data
  const invalidate = [depthKeys.vessel(vesselId) as unknown as unknown[]]
  const refit = useGodAction({
    writes: [{ lever: 'vessel:refit' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/vessel:refit', {
          body: {
            vessel_id: vesselId,
            frame: (hull || vessel?.frame.frame || 'boat') as Frame,
          },
        })
      ),
    invalidate,
  })
  const [foe, setFoe] = useState<number | null>(null)
  const engage = useGodAction({
    writes: [{ lever: 'engagement:force' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/engagement:force', {
          body: { vessel_id: vesselId, foe_vessel_id: foe ?? 0 },
        })
      ),
    invalidate,
    onDone: () => setFoe(null),
  })
  const repair = useGodAction({
    writes: [{ lever: 'vessel:repair' }],
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
          acts={[refit]}
          title='Fit it out as a ship'
          note='Give it a hull; the shipwrights make it seaworthy and mount the weapons of its type.'
          label='Fit out as a ship'
        >
          <FieldGrid>
            <ChoiceField
              label='Frame'
              icon={Gauge}
              value={hull || 'boat'}
              table={FRAMES}
              blocked={blocked}
              onPick={setHull}
            />
          </FieldGrid>
          <Button
            act={refit}
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
  if (!vessel) return <LoadingBlock label='Reading the ship’s log' />
  const status = nameOf(VESSEL_STATUS, vessel.status)
  const busy = busyOf(
    blocked,
    refit.isPending,
    repair.isPending,
    engage.isPending
  )
  const engageReason =
    busy ??
    (foe === null
      ? 'Choose the vessel it engages'
      : foe === vesselId
        ? 'A vessel cannot engage itself'
        : null)
  return (
    <Panel
      title='Vessel'
      icon={Ship}
      tone='info'
      hint={`${vessel.frame.label} · ${status.label}`}
    >
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Tag item={nameOf(FRAMES, vessel.frame.frame)} />
        <Tag item={status} />
        <Held locked={vessel.locked} />
      </div>
      <Weapons weapons={vessel.weapons} />
      <StatBar
        framed
        label='Frame'
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
        framed
        label='Seaworthiness'
        value={vessel.seaworthiness}
        max={100}
        icon={Waves}
        tone='info'
      />
      <StatBar
        framed
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
            Hull of {humanize(vessel.hull_material)}
          </Muted>
        )}
        {vessel.fabric_material && (
          <Muted variant='caption'>
            Sails of {humanize(vessel.fabric_material)}
          </Muted>
        )}
      </div>
      <div className='flex min-w-0 flex-col gap-2'>
        <Button
          act={repair}
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
          acts={[engage]}
          title='Force an engagement'
          note='Set this vessel on another in their own domain; every round, hit and loss is written into its history.'
          label='Force an engagement'
        >
          <FieldGrid>
            <EntityPicker
              label='Vessel it engages'
              icon={Crosshair}
              types={['vessel']}
              value={foe}
              onChange={setFoe}
              blocked={blocked}
            />
          </FieldGrid>
          <Button
            act={engage}
            size='sm'
            className='self-start'
            disabled={engageReason !== null}
            disabledReason={engageReason ?? undefined}
            onClick={() => engage.mutate()}
          >
            <Swords />
            Engage
          </Button>
        </Adjust>
        <Adjust
          acts={[refit]}
          title='Refit'
          note='Rebuild the ship to another hull; its weapons follow the type of that frame, edited on the vehicle type.'
          label='Refit'
        >
          <FieldGrid>
            <ChoiceField
              label='Frame'
              icon={Gauge}
              value={hull || vessel.frame.frame}
              table={FRAMES}
              blocked={blocked}
              onPick={setHull}
            />
          </FieldGrid>
          <Button
            act={refit}
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
      <ReportSteps
        nodeId={vesselId}
        kind='seafaring'
        label='How its last engagement unfolded'
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
  const frames = useFrames()
  const FRAMES = frameTable(frames.data ?? [])
  const [name, setName] = useState('')
  const [hull, setHull] = useState('boat')
  const create = useGodAction({
    writes: [{ lever: 'vessel:create' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/vessel:create', {
          body: {
            owner_id: ownerId,
            name: name.trim(),
            frame: hull as Frame,
          },
        })
      ),
    onDone: () => setName(''),
  })
  const spec = frames.data?.find((item) => item.frame === hull)
  return (
    <Adjust
      acts={[create]}
      title='Lay down a vessel'
      note='Choose a hull; the shipwrights build it to its type and mount its weapons.'
      label='Lay down a vessel'
    >
      <FieldGrid>
        <TextField
          label='Name'
          icon={Ship}
          value={name}
          onChange={setName}
          placeholder='A name of your choosing'
        />
        <ChoiceField
          label='Frame'
          icon={Ship}
          value={hull}
          table={FRAMES}
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
            label='Endurance'
            value={spec.endurance}
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
      <Button
        act={create}
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
      description='Hull, mounted weapons, crew, renown and the waters it sails.'
      icon={Ship}
    >
      <div className='@container/mil min-w-0'>
        <VesselCard vesselId={vesselId} blocked={blocked} />
      </div>
    </Section>
  )
}

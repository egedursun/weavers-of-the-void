import { useState } from 'react'
import {
  Anchor,
  Bomb,
  Coins,
  Compass,
  Droplets,
  Flag,
  Flame,
  Landmark,
  Scale,
  Ship,
  Target,
  Users,
  Wind,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { KpiTile, PagedList } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { clamp } from '@/features/cycles/model'
import { why } from '@/features/dominion/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { SECTION_STATE, sectionLabel } from '@/features/madeKinds/labels'
import { Tag } from '@/features/wars/military/parts'
import { type OperationsNodeView, useOperationsAction } from './api'
import { COMPASS, POINTS_OF_SAIL, SHOTS, STATIONS } from './labels'
import {
  MANY,
  MORTAL_TYPES,
  OWNER_TYPES,
  SPAN,
  heading,
  useOpsRow,
} from './model'

type ShipState = NonNullable<OperationsNodeView['ship']>
type Crew = OperationsNodeView['crews'][number]
type Admiralty = NonNullable<OperationsNodeView['admiralty']>

const NOT_VESSEL = 'Only a ship sails, fights and takes prizes'
const NOT_REALM = 'Only a realm keeps an admiralty'
const COMPASS_TABLE = Object.fromEntries(
  COMPASS.map((name, index) => [String(index), name])
)

function WindRose({
  heading: course,
  wind,
}: {
  heading: number
  wind: number
}) {
  const point = (octant: number, radius: number) => {
    const angle = (octant * Math.PI) / 4
    return [50 + Math.sin(angle) * radius, 50 - Math.cos(angle) * radius]
  }
  const [courseX, courseY] = point(course, 30)
  const [windX, windY] = point(wind, 44)
  const [windInX, windInY] = point(wind, 18)
  return (
    <svg
      viewBox='0 0 100 100'
      className='size-portrait-xl shrink-0'
      role='img'
      aria-label={`Heading ${heading(course, COMPASS)}, the wind from the ${heading(wind, COMPASS)}`}
    >
      <circle
        cx='50'
        cy='50'
        r='46'
        className='fill-background stroke-border'
        strokeWidth='1.5'
      />
      {COMPASS.map((name, index) => {
        const [x, y] = point(index, 40)
        return index % 2 === 0 ? (
          <text
            key={name}
            x={x}
            y={y + 2}
            textAnchor='middle'
            className='fill-muted-foreground'
            fontSize='7'
          >
            {name[0].toUpperCase()}
          </text>
        ) : null
      })}

      <line
        x1='50'
        y1='50'
        x2={courseX}
        y2={courseY}
        className='stroke-primary'
        strokeWidth='4'
        strokeLinecap='round'
      />
      <line
        x1={windX}
        y1={windY}
        x2={windInX}
        y2={windInY}
        className='stroke-info'
        strokeWidth='3'
        strokeDasharray='4 3'
      />
      <circle cx='50' cy='50' r='4' className='fill-primary' />
    </svg>
  )
}

function ShipCard({
  row,
  blocked,
}: {
  row: ShipState
  blocked: string | null
}) {
  const action = useOpsRow(
    'ship_state:edit',
    'ship_state:delete',
    { vessel_id: row.vessel.id },
    blocked
  )
  const point = POINTS_OF_SAIL[row.point_of_sail]
  const shot = SHOTS[row.shot]
  return (
    <Held
      icon={Ship}
      tone={row.struck ? 'danger' : row.fire > 0 ? 'warning' : 'info'}
      title={row.vessel.name}
      caption={`${point.label}, heading ${heading(row.heading, COMPASS)} with the wind from the ${heading(row.wind_from, COMPASS)} · read in epoch ${row.updated_epoch}`}
      removeLabel='Read the ship anew'
      editTitle='Set the ship'
      note='A ship’s speed follows its angle to the wind: close-hauled is slow, a reach is fastest, and heading straight into the wind it must tack or lie in irons, where it is raked along its length. Galleys row whatever the wind, and their rowers tire. Round shot holes the hull and lets in water the pumps fight; chain shot tears the rigging; grape thins the crew; fire spreads fastest on a wooden deck, and fire at the magazine may destroy the ship. A ship whose crew or hull is broken strikes its colours and is taken as a prize.'
      fields={[
        {
          key: 'heading',
          label: 'Heading',
          kind: 'pick',
          table: COMPASS_TABLE,
        },
        {
          key: 'wind_from',
          label: 'Wind from',
          kind: 'pick',
          table: COMPASS_TABLE,
        },
        {
          key: 'point_of_sail',
          label: 'Point of sail',
          kind: 'pick',
          table: table(POINTS_OF_SAIL),
        },
        {
          key: 'tacks',
          label: 'Tacks made',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'shot', label: 'Shot', kind: 'pick', table: table(SHOTS) },
        {
          key: 'leak',
          label: 'Water in the hold',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'fire',
          label: 'Fire on board',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'magazine',
          label: 'Magazine intact',
          kind: 'pick',
          table: YES_NO,
        },
        {
          key: 'rate_of_fire',
          label: 'Rate of fire',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'rower_fatigue',
          label: 'Rowers’ fatigue',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'raked',
          label: 'Times raked',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'struck', label: 'Colours struck', kind: 'pick', table: YES_NO },
        {
          key: 'prize_of_entity_id',
          label: 'Prize of',
          kind: 'node',
          types: OWNER_TYPES,
        },
        {
          key: 'prize_crew',
          label: 'Prize crew',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'prize_money',
          label: 'Prize money',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <Tag item={point} />
          <Tag item={shot} text={`Firing ${shot.label.toLowerCase()}`} />
          {!row.magazine && (
            <Badge size='sm' variant='destructive'>
              <Bomb aria-hidden='true' />
              Magazine gone
            </Badge>
          )}
          {row.struck && (
            <Badge size='sm' variant='destructive'>
              <Flag aria-hidden='true' />
              Colours struck
            </Badge>
          )}
        </div>
      }
    >
      <div className='flex min-w-0 flex-wrap items-center gap-3'>
        <WindRose heading={row.heading} wind={row.wind_from} />
        <Muted variant='caption'>
          The gold line is the ship&apos;s heading, the dashed blue line the
          wind blowing in from the {heading(row.wind_from, COMPASS)}.
        </Muted>
      </div>
      <div data-chart='chart-ship-damage' className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2 @lg/tiles:grid-cols-4'>
          <KpiTile
            label='Hull'
            value={row.hull_condition}
            icon={Anchor}
            tone='info'
          />
          <KpiTile
            label='Crew aboard'
            value={row.crew_total}
            icon={Users}
            tone='verdigris'
          />
          <KpiTile
            label='Water in the hold'
            value={row.leak}
            icon={Droplets}
            tone='warning'
          />
          <KpiTile
            label='Fire on board'
            value={row.fire}
            icon={Flame}
            tone='danger'
          />
        </div>
      </div>
      <Meter
        label='Rate of fire'
        value={row.rate_of_fire}
        tone='destructive'
        icon={Target}
      />
      <Meter
        label='Rowers’ fatigue'
        value={row.rower_fatigue}
        tone='warning'
        icon={Wind}
      />
      {row.sections.length > 0 ? (
        <div className='flex min-w-0 flex-col gap-1.5'>
          <Label>Damage by section</Label>
          <PagedList
            items={row.sections}
            initial={12}
            noun={['section', 'sections']}
            as='div'
            className='flex min-w-0 flex-wrap gap-1.5'
            itemKey={(item) => item.section}
          >
            {(item) => (
              <Tag
                key={item.section}
                item={SECTION_STATE[item.state]}
                text={`${sectionLabel(item.section)} · ${SECTION_STATE[item.state].label.toLowerCase()} · ${item.condition}`}
              />
            )}
          </PagedList>
        </div>
      ) : (
        <Muted variant='caption'>
          No section of this ship has been struck yet.
        </Muted>
      )}
      <Facts
        items={[
          ['Tacks made', String(row.tacks)],
          ['Times raked', String(row.raked)],
          ['Prize of', <Ref key='prize' node={row.prize_of} empty='its own' />],
          ['Prize crew', String(row.prize_crew)],
          ['Prize money', String(row.prize_money)],
        ]}
      />
    </Held>
  )
}

function CrewCard({
  row,
  vesselId,
  blocked,
}: {
  row: Crew
  vesselId: number
  blocked: string | null
}) {
  const action = useOpsRow(
    'ship_crew:edit',
    'ship_crew:delete',
    { vessel_id: vesselId, station: row.station },
    blocked
  )
  const look = STATIONS[row.station]
  return (
    <Held
      icon={look.icon}
      tone={look.tone}
      title={look.label}
      caption={`${row.count} at the station`}
      removeLabel='Man the station anew'
      editTitle='Set the station'
      note='Gunners set the rate of fire by their skill and how many still serve the guns; officers keep the guns loading under fire; topmen work the sails and the pumps; marines board; rowers drive a galley against the wind.'
      fields={[
        {
          key: 'count',
          label: 'Crew at the station',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'skill', label: 'Skill', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter label='Skill' value={row.skill} tone='info' icon={look.icon} />
    </Held>
  )
}

function ShipForge({
  nodeId,
  kind,
  blocked,
}: {
  nodeId: number
  kind: string | null
  blocked: string | null
}) {
  const gate = kind === 'vessel' ? blocked : NOT_VESSEL
  const [shot, setShot] = useState<keyof typeof SHOTS>('round')
  const [point, setPoint] = useState<keyof typeof POINTS_OF_SAIL>('reaching')
  const [station, setStation] = useState<keyof typeof STATIONS>('gunners')
  const [count, setCount] = useState('20')
  const [skill, setSkill] = useState('40')
  const sailing = useOperationsAction(
    'ship_state:set',
    (_: void) => ({ vessel_id: nodeId, shot, point_of_sail: point }),
    'The ship’s sailing and gunnery are set'
  )
  const manning = useOperationsAction(
    'ship_crew:set',
    (_: void) => ({
      vessel_id: nodeId,
      station,
      count: clamp(count, MANY),
      skill: clamp(skill),
    }),
    'The station is manned'
  )
  const sailBusy = why(gate, sailing.isPending)
  const crewBusy = why(gate, manning.isPending)
  return (
    <ForgeCard
      icon={Compass}
      tone='info'
      title='Trim the sails, load the guns, man the stations'
      note='Choose the shot the guns fire and the point of sail the ship holds, or man a station with a crew and their skill.'
      columns={3}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={sailBusy !== null}
            disabledReason={sailBusy ?? undefined}
            onClick={() => sailing.mutate()}
          >
            <Compass />
            Set the sailing
          </Button>
          <Button
            size='sm'
            variant='secondary'
            disabled={crewBusy !== null}
            disabledReason={crewBusy ?? undefined}
            onClick={() => manning.mutate()}
          >
            <Users />
            Man the station
          </Button>
        </div>
      }
    >
      <MindPicker
        label='Shot'
        value={shot}
        table={table(SHOTS)}
        blocked={gate}
        onPick={(value) => setShot(value as keyof typeof SHOTS)}
      />
      <MindPicker
        label='Point of sail'
        value={point}
        table={table(POINTS_OF_SAIL)}
        blocked={gate}
        onPick={(value) => setPoint(value as keyof typeof POINTS_OF_SAIL)}
      />
      <MindPicker
        label='Station'
        value={station}
        table={table(STATIONS)}
        blocked={gate}
        onPick={(value) => setStation(value as keyof typeof STATIONS)}
      />
      <NumberField
        label='Crew'
        value={count}
        min={0}
        max={MANY}
        blocked={gate}
        onChange={setCount}
      />
      <NumberField
        label='Skill'
        value={skill}
        min={0}
        max={SPAN}
        blocked={gate}
        onChange={setSkill}
      />
    </ForgeCard>
  )
}

export function ShipPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: OperationsNodeView
  blocked: string | null
}) {
  return (
    <div data-surface='ShipPanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Sailing, damage and prizes'
        items={data.ship ? [data.ship] : []}
        empty='This ship has not yet sailed or fought since the age of sail came to the world.'
        noun={['ship', 'ships']}
        itemKey={(item) => item.vessel.id}
      >
        {(item) => <ShipCard row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='Crew stations'
        items={data.crews}
        empty='No station is manned here.'
        noun={['station', 'stations']}
        itemKey={(item) => item.station}
      >
        {(item) => <CrewCard row={item} vesselId={nodeId} blocked={blocked} />}
      </Listed>
      <ShipForge nodeId={nodeId} kind={kind} blocked={blocked} />
    </div>
  )
}

function AdmiraltyCard({
  row,
  blocked,
}: {
  row: Admiralty
  blocked: string | null
}) {
  const action = useOpsRow(
    'admiralty:edit',
    'admiralty:delete',
    { polity_id: row.polity.id },
    blocked
  )
  const over = row.limit_tonnage !== null && row.tonnage > row.limit_tonnage
  return (
    <Held
      icon={Landmark}
      tone={over ? 'danger' : 'info'}
      title={`Admiralty of ${row.polity.name}`}
      caption={`${plural(row.commissioned, 'ship', 'ships')} laid down · read in epoch ${row.updated_epoch}`}
      removeLabel='Draw the admiralty anew'
      editTitle='Set the admiralty'
      note='The admiralty asks the council for a share of the war budget and contends with the marshal for it, winning by its admiral’s skill; its share pays for new ships. A naval treaty caps the fleet’s tonnage: an admiralty past its limit stops building, or, if its admiral scorns the law, hides ships in secret until the other side finds them out and the treaty breaks.'
      fields={[
        {
          key: 'admiral_entity_id',
          label: 'Admiral',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        {
          key: 'budget_share',
          label: 'Share of the war budget',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'requested',
          label: 'Share asked for',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'influence',
          label: 'Sway in council',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'tonnage',
          label: 'Fleet tonnage',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'limit_tonnage',
          label: 'Treaty limit',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'concealed',
          label: 'Hidden tonnage',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'commissioned',
          label: 'Ships laid down',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        row.concealed > 0 ? (
          <Badge size='sm' variant='warning'>
            {row.concealed} tons hidden
          </Badge>
        ) : undefined
      }
    >
      <Meter
        label='Share of the war budget'
        value={row.budget_share}
        tone='legendary'
        icon={Coins}
      />
      <Meter
        label='Sway in council'
        value={row.influence}
        tone='info'
        icon={Scale}
      />
      <Facts
        items={[
          [
            'Admiral',
            <Ref key='admiral' node={row.admiral} empty='no admiral' />,
          ],
          ['Share asked for', `${row.requested}%`],
          ['Fleet tonnage', String(row.tonnage)],
          [
            'Treaty limit',
            row.limit_tonnage !== null ? String(row.limit_tonnage) : 'unbound',
          ],
        ]}
      />
    </Held>
  )
}

export function AdmiraltyPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: OperationsNodeView
  blocked: string | null
}) {
  const gate = kind === 'polity' ? blocked : NOT_REALM
  const [budget, setBudget] = useState('25')
  const setting = useOperationsAction(
    'admiralty:set',
    (_: void) => ({ polity_id: nodeId, budget_share: clamp(budget) }),
    'The admiralty’s share is set'
  )
  const busy = why(gate, setting.isPending)
  return (
    <div data-surface='AdmiraltyPanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Admiralty'
        items={data.admiralty ? [data.admiralty] : []}
        empty='No admiralty sits here.'
        noun={['admiralty', 'admiralties']}
        itemKey={(item) => item.polity.id}
      >
        {(item) => <AdmiraltyCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Landmark}
        tone='info'
        title='Fund the admiralty'
        note='Set the share of the realm’s war budget its admiralty holds. A naval treaty capping the fleet is bound through the treaty records of the realm.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => setting.mutate()}
          >
            <Coins />
            Set the share
          </Button>
        }
      >
        <NumberField
          label='Share of the war budget'
          value={budget}
          min={0}
          max={SPAN}
          blocked={gate}
          onChange={setBudget}
        />
      </ForgeCard>
    </div>
  )
}

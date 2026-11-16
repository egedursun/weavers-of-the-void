import { useState } from 'react'
import {
  CirclePlus,
  Flame,
  MapPinned,
  Target,
  Trash2,
  Waypoints,
} from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { EmptyState, ShowMore, useShowMore } from '@/components/domain'
import {
  Chip,
  type Field,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { useMadeAction } from '@/features/minds/api'
import { NumberField } from '@/features/wars/military/parts'
import { type StorytellerView } from './api'
import { ThingPicker } from './parts'

const SPAN = 100
const SHOWN = 5
const HOLD =
  'Values you set are held against the engine until you release them.'
const REGIONS = ['region'] as const
const TENSION_FIELDS: readonly Field[] = [
  { key: 'tension', label: 'Tension', kind: 'number', min: 0, max: SPAN },
]

type Edit = { values: EditValues; release: string[] }
type Region = StorytellerView['regions'][number]
type Part = StorytellerView['subsystems'][number]
type Point = { epoch: number; target: number }

function words(key: string) {
  return key.replaceAll('_', ' ')
}

function RegionRow({ row, blocked }: { row: Region; blocked: string | null }) {
  const editing = useMadeAction(
    'regional_tension:edit',
    (vars: Edit) => ({
      region_id: row.region.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The region’s tension is set'
  )
  const removing = useMadeAction(
    'regional_tension:delete',
    (_: void) => ({ region_id: row.region.id }),
    'The region is measured afresh'
  )
  return (
    <RecordRow
      icon={row.crisis ? Flame : MapPinned}
      tone={row.crisis ? 'danger' : 'info'}
      title={`${row.region.name}: tension ${row.tension}${row.crisis ? ', in crisis' : ''}`}
      caption={`measured in epoch ${row.updated_epoch}`}
    >
      <RecordEditor
        title='Set the region’s tension'
        note={HOLD}
        fields={TENSION_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Measure afresh'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function PartRow({
  row,
  worldId,
  blocked,
}: {
  row: Part
  worldId: number
  blocked: string | null
}) {
  const editing = useMadeAction(
    'subsystem_tension:edit',
    (vars: Edit) => ({
      world_id: worldId,
      subsystem: row.subsystem,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The tension is set'
  )
  const removing = useMadeAction(
    'subsystem_tension:delete',
    (_: void) => ({ world_id: worldId, subsystem: row.subsystem }),
    'Measured afresh'
  )
  return (
    <RecordRow
      icon={Waypoints}
      tone={row.tension >= SPAN / 2 ? 'warning' : 'muted'}
      title={`${words(row.subsystem)}: tension ${row.tension}`}
      caption={`measured in epoch ${row.updated_epoch}`}
    >
      <RecordEditor
        title='Set this part’s tension'
        note={HOLD}
        fields={TENSION_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Measure afresh'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function TargetPoints({
  view,
  blocked,
}: {
  view: StorytellerView
  blocked: string | null
}) {
  const [epoch, setEpoch] = useState('10')
  const [target, setTarget] = useState('50')
  const saving = useMadeAction(
    'storyteller_points:set',
    (points: Point[]) => ({ world_id: view.world_id, points }),
    'The storyteller follows the set points'
  )
  const points = view.target_points
  const adding = {
    epoch: Math.max(0, Number(epoch) || 0),
    target: Math.min(SPAN, Math.max(0, Number(target) || 0)),
  }
  return (
    <ForgeCard
      icon={Target}
      tone='info'
      title='Shape the aim by points'
      note='Set points of tension by epoch; the aim runs straight between them and overrides the profile. With no points the profile shapes the aim.'
      columns={2}
      action={
        <StepButton
          icon={CirclePlus}
          label='Add the point'
          variant='default'
          busy={why(blocked, saving.isPending)}
          onClick={() =>
            saving.mutate([
              ...points.filter((point) => point.epoch !== adding.epoch),
              adding,
            ])
          }
        />
      }
    >
      <NumberField label='Epoch' value={epoch} min={0} onChange={setEpoch} />
      <NumberField
        label='Aim at that epoch'
        value={target}
        min={0}
        max={SPAN}
        onChange={setTarget}
      />
      <div className='flex min-w-0 flex-wrap gap-2 sm:col-span-2'>
        {points.length ? (
          points.map((point) => (
            <Chip key={point.epoch} icon={Target}>
              Epoch {point.epoch}: aim {point.target}
            </Chip>
          ))
        ) : (
          <Chip icon={Target}>No points set; the profile shapes the aim</Chip>
        )}
      </div>
      <StepButton
        icon={Trash2}
        label='Clear the points'
        busy={why(
          blocked ?? (points.length ? null : 'There are no points to clear'),
          saving.isPending
        )}
        onClick={() => saving.mutate([])}
      />
    </ForgeCard>
  )
}

function RegionForge({ blocked }: { blocked: string | null }) {
  const [region, setRegion] = useState<number | null>(null)
  const [tension, setTension] = useState('70')
  const setting = useMadeAction(
    'regional_tension:set',
    (_: void) => ({
      region_id: region ?? 0,
      tension: Math.min(SPAN, Math.max(0, Number(tension) || 0)),
      hold: true,
    }),
    'The region’s tension is set'
  )
  const missing = region === null ? 'Pick a region first' : null
  return (
    <ForgeCard
      icon={Flame}
      tone='warning'
      title='Set a region’s tension'
      note='A region can burn while its world is calm; a region in crisis keeps the storyteller from hurrying the rest.'
      columns={2}
      action={
        <StepButton
          icon={Flame}
          label='Set it'
          busy={why(blocked ?? missing, setting.isPending)}
          onClick={() => setting.mutate()}
        />
      }
    >
      <ThingPicker
        label='Region'
        value={region}
        onChange={setRegion}
        blocked={blocked}
        types={REGIONS}
      />
      <NumberField
        label='Tension'
        value={tension}
        min={0}
        max={SPAN}
        onChange={setTension}
      />
    </ForgeCard>
  )
}

export function StorytellerDepth({
  view,
  blocked,
}: {
  view: StorytellerView
  blocked: string | null
}) {
  const regions = useShowMore(view.regions, SHOWN, SHOWN)
  const parts = useShowMore(view.subsystems, SHOWN, SHOWN)
  return (
    <>
      <TargetPoints view={view} blocked={blocked} />
      {view.regions.length ? (
        <>
          <ul className='flex min-w-0 flex-col gap-2'>
            {regions.visible.map((row) => (
              <RegionRow key={row.region.id} row={row} blocked={blocked} />
            ))}
          </ul>
          <ShowMore state={regions} />
        </>
      ) : (
        <EmptyState
          icon={MapPinned}
          size='inline'
          title='No region measured yet'
          description='Regions are measured as things happen in them.'
        />
      )}
      <RegionForge blocked={blocked} />
      {view.subsystems.length ? (
        <>
          <ul className='flex min-w-0 flex-col gap-2'>
            {parts.visible.map((row) => (
              <PartRow
                key={row.subsystem}
                row={row}
                worldId={view.world_id}
                blocked={blocked}
              />
            ))}
          </ul>
          <ShowMore state={parts} />
        </>
      ) : null}
    </>
  )
}

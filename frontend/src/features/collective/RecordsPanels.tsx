import { useState } from 'react'
import {
  Anchor,
  CalendarDays,
  Gauge,
  Hammer,
  Package,
  RefreshCw,
  Ship,
  Sparkles,
  Sword,
  Wrench,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { KpiTile, PagedList } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Chip, Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { useFrames } from '@/features/madeKinds/api'
import { frameTable } from '@/features/madeKinds/labels'
import { ArmsCard, ArmsForge } from './ArmsPanels'
import {
  type CollectiveView,
  type DesignView,
  useCollectiveAction,
} from './api'
import { DATING, DESIGN_KINDS, PARTS } from './labels'
import { clamp, SPAN, useRemove, useRow } from './model'
import { Held, Listed } from './parts'

type Dating = NonNullable<CollectiveView['dating']>
type Part = DesignView['components'][number]

const CALENDARS = ['polity', 'cult', 'people']
const NO_MATERIAL = 'none'

function DatingCard({
  holderId,
  row,
  blocked,
}: {
  holderId: number
  row: Dating
  blocked: string | null
}) {
  const action = useRow(
    'dating_system:edit',
    'dating_system:delete',
    { holder_id: holderId },
    blocked
  )
  const kind = DATING[row.kind]
  return (
    <Held
      icon={kind.icon}
      tone={kind.tone}
      title={`It is ${row.today}`}
      caption={`${kind.label}${row.reformed_epoch !== null ? ` · reformed in epoch ${row.reformed_epoch}` : ''} · counted so since epoch ${row.since_epoch}`}
      removeLabel='Let the era be chosen anew'
      editTitle='Set the reckoning'
      note='Dates in accounts and in what mortals say are given in the holder’s own era.'
      fields={[
        { key: 'kind', label: 'Counted', kind: 'pick', table: table(DATING) },
        {
          key: 'anchor_year',
          label: 'Year it counts from',
          kind: 'number',
          min: 0,
        },
        {
          key: 'cycle_years',
          label: 'Years in a cycle',
          kind: 'number',
          min: 0,
        },
        {
          key: 'anchor_node_id',
          label: 'Counted from the life of',
          kind: 'node',
          types: ['mortal', 'polity', 'cult', 'people', 'settlement'],
          kinds: ['son', 'foreign_god'],
        },
        {
          key: 'label_node_id',
          label: 'Era named for',
          kind: 'node',
          types: ['mortal', 'polity', 'cult', 'people', 'settlement'],
          kinds: ['son', 'foreign_god'],
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          ['Counts from year', row.anchor_year],
          [
            'Named for',
            <Ref key='label' node={row.label} empty='the era itself' />,
          ],
          [
            'Counted from the life of',
            <Ref key='anchor' node={row.anchor} empty='no one' />,
          ],
          ['Years in a cycle', row.cycle_years],
        ]}
      />
    </Held>
  )
}

function DatingForge({
  holderId,
  type,
  blocked,
}: {
  holderId: number
  type: string | null
  blocked: string | null
}) {
  const [kind, setKind] = useState<keyof typeof DATING>('founding')
  const [anchor, setAnchor] = useState('0')
  const [cycle, setCycle] = useState('60')
  const setting = useCollectiveAction(
    'dating_system:set',
    (_: void) => ({
      holder_id: holderId,
      kind,
      anchor_year: clamp(anchor, 100_000),
      cycle_years: clamp(cycle, 100_000),
    }),
    'The years are counted so'
  )
  const busy = why(
    type !== null && CALENDARS.includes(type)
      ? blocked
      : 'Only a realm, cult or people counts its years',
    setting.isPending
  )
  return (
    <ForgeCard
      icon={CalendarDays}
      tone='verdigris'
      title='Set how the years are counted'
      note='By reign, from a founding, by a holy era or by the cycles of the sky.'
      columns={3}
      action={
        <Button
          act={setting}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <CalendarDays />
          Count so
        </Button>
      }
    >
      <MindPicker
        label='Counted'
        value={kind}
        table={table(DATING)}
        blocked={busy}
        onPick={(value) => setKind(value as keyof typeof DATING)}
      />
      <NumberField
        label='From year'
        value={anchor}
        min={0}
        blocked={busy}
        onChange={setAnchor}
      />
      <NumberField
        label='Years in a cycle'
        value={cycle}
        min={0}
        blocked={busy}
        onChange={setCycle}
      />
    </ForgeCard>
  )
}

export function DatingPanel({
  nodeId,
  type,
  data,
  blocked,
}: {
  nodeId: number
  type: string | null
  data: CollectiveView
  blocked: string | null
}) {
  return (
    <div
      id='section-dating'
      data-surface='DatingPanel'
      className='flex min-w-0 flex-col gap-3'
    >
      <Label variant='overline'>Reckoning of years</Label>
      {data.dating ? (
        <DatingCard holderId={nodeId} row={data.dating} blocked={blocked} />
      ) : (
        <DatingForge holderId={nodeId} type={type} blocked={blocked} />
      )}
    </div>
  )
}

export function HeraldryPanel({
  nodeId,
  name,
  type,
  data,
  blocked,
}: {
  nodeId: number
  name: string
  type: string | null
  data: CollectiveView
  blocked: string | null
}) {
  return (
    <div
      id='section-heraldry'
      data-surface='HeraldryPanel'
      className='flex min-w-0 flex-col gap-3'
    >
      <Label variant='overline'>Arms</Label>
      {data.arms ? (
        <ArmsCard
          holderId={nodeId}
          row={data.arms}
          label={name}
          blocked={blocked}
        />
      ) : (
        <ArmsForge holderId={nodeId} type={type} blocked={blocked} />
      )}
    </div>
  )
}

function WearControl({
  vesselId,
  part,
  blocked,
}: {
  vesselId: number
  part: Part
  blocked: string | null
}) {
  const [wear, setWear] = useState(String(part.wear ?? 0))
  const keys = { vessel_id: vesselId, component: part.component }
  const setting = useCollectiveAction(
    'component_wear:set',
    (_: void) => ({ ...keys, wear: clamp(wear) }),
    'The part wears so'
  )
  const editing = useCollectiveAction(
    'component_wear:edit',
    (_: void) => ({ ...keys, values: { wear: clamp(wear) }, release: [] }),
    'The part wears so'
  )
  const mending = useRemove('component_wear:delete', keys, blocked)
  const busy = why(mending.busy, setting.isPending, editing.isPending)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Meter
        label='Wear on this vessel'
        value={part.wear ?? 0}
        max={SPAN}
        tone='warning'
        icon={Wrench}
      />
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <NumberField
          label='Wear'
          value={wear}
          min={0}
          max={SPAN}
          blocked={busy}
          onChange={setWear}
        />
        <Button
          act={[setting, editing]}
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() =>
            part.wear === null ? setting.mutate() : editing.mutate()
          }
        >
          <Wrench />
          Set the wear
        </Button>
        <Button
          size='sm'
          variant='ghost'
          disabled={
            (busy ??
              (part.wear === null ? 'This part is as good as new' : null)) !==
            null
          }
          disabledReason={
            busy ??
            (part.wear === null ? 'This part is as good as new' : undefined)
          }
          onClick={mending.onRemove}
        >
          <Sparkles />
          Make it as good as new
        </Button>
      </div>
    </div>
  )
}

function PartRow({
  designId,
  vesselId,
  part,
  materials,
  blocked,
}: {
  designId: number
  vesselId: number | null
  part: Part
  materials: Record<string, string>
  blocked: string | null
}) {
  const [size, setSize] = useState(String(part.size))
  const [quality, setQuality] = useState(String(part.quality))
  const [material, setMaterial] = useState(
    part.material_id !== null ? String(part.material_id) : NO_MATERIAL
  )
  const setting = useCollectiveAction(
    'design_component:set',
    (_: void) => ({
      design_id: designId,
      component: part.component,
      size: clamp(size, 10),
      quality: clamp(quality),
      material_id: material === NO_MATERIAL ? null : Number(material),
    }),
    'The part is set so'
  )
  const removing = useRemove(
    'design_component:delete',
    { design_id: designId, component: part.component },
    blocked
  )
  const busy = why(removing.busy, setting.isPending)
  const spec = PARTS[part.component]
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Chip icon={spec.icon}>{spec.label}</Chip>
        <Muted variant='caption'>{part.material_name ?? 'common stuff'}</Muted>
      </div>
      {vesselId !== null ? (
        <WearControl vesselId={vesselId} part={part} blocked={busy} />
      ) : (
        part.wear !== null && (
          <Meter
            label='Wear on this vessel'
            value={part.wear}
            max={SPAN}
            tone='warning'
            icon={Wrench}
          />
        )
      )}
      <div className='grid min-w-0 gap-2 sm:grid-cols-4'>
        <NumberField
          label='Size'
          value={size}
          min={0}
          max={10}
          blocked={busy}
          onChange={setSize}
        />
        <NumberField
          label='Quality'
          value={quality}
          min={0}
          max={SPAN}
          blocked={busy}
          onChange={setQuality}
        />
        <MindPicker
          label='Material'
          value={material}
          table={{ [NO_MATERIAL]: 'Common stuff', ...materials }}
          blocked={busy}
          onPick={setMaterial}
        />
        <div className='flex min-w-0 flex-wrap items-end gap-2'>
          <Button
            act={setting}
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => setting.mutate()}
          >
            <Hammer />
            Rework
          </Button>
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={removing.onRemove}
          >
            Take out
          </Button>
        </div>
      </div>
    </div>
  )
}

function DesignCard({
  row,
  vesselId,
  fitted,
  materials,
  blocked,
}: {
  row: DesignView
  vesselId: number | null
  fitted: boolean
  materials: Record<string, string>
  blocked: string | null
}) {
  const action = useRow(
    'design:edit',
    'design:delete',
    { design_id: row.id },
    blocked
  )
  const refitting = useCollectiveAction(
    'design:refit',
    (_: void) => ({ design_id: row.id }),
    'A new mark is drawn'
  )
  const fitting = useCollectiveAction(
    'design:fit',
    (_: void) => ({ vessel_id: vesselId ?? 0, design_id: row.id }),
    'The vessel is refitted'
  )
  const kind = DESIGN_KINDS[row.kind]
  const frames = frameTable(useFrames().data ?? [])
  const busy = why(action.busy, refitting.isPending, fitting.isPending)
  const unfit =
    vesselId === null
      ? 'Only a vessel can be refitted to a design'
      : fitted
        ? 'This vessel is built to it already'
        : null
  return (
    <Held
      icon={kind.icon}
      tone={row.obsolete ? 'muted' : kind.tone}
      title={
        row.name.endsWith(`mark ${row.mark}`)
          ? row.name
          : `${row.name} · mark ${row.mark}`
      }
      caption={`${kind.label}${row.frame ? ` · ${frames[row.frame]?.label ?? row.frame}` : ''} · drawn in epoch ${row.epoch}${row.obsolete ? ' · superseded' : ''}`}
      removeLabel='Strike the design'
      editTitle='Set the design'
      note='Speed, reach, cargo, arms and crew follow from its parts; set them here to hold them against the parts.'
      fields={[
        { key: 'name', label: 'Design name', kind: 'text' },
        {
          key: 'designer_entity_id',
          label: 'Drawn by',
          kind: 'node',
          types: ['mortal'],
        },
        { key: 'frame', label: 'Frame', kind: 'pick', table: table(frames) },
        { key: 'speed', label: 'Speed', kind: 'number', min: 0, max: SPAN },
        { key: 'range', label: 'Reach', kind: 'number', min: 0, max: SPAN },
        {
          key: 'seaworthiness',
          label: 'Seaworthiness',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'cargo', label: 'Cargo', kind: 'number', min: 0 },
        { key: 'armament', label: 'Arms', kind: 'number', min: 0, max: SPAN },
        { key: 'crew', label: 'Crew', kind: 'number', min: 0 },
        {
          key: 'obsolete',
          label: 'Superseded',
          kind: 'pick',
          table: { true: 'Yes', false: 'No' },
        },
      ]}
      locked={row.locked}
      blocked={busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <>
          <Chip icon={Ship}>{`${row.vessels} built to it`}</Chip>
          {fitted && (
            <Chip icon={Anchor} variant='success'>
              This vessel
            </Chip>
          )}
        </>
      }
    >
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2 @2xl/tiles:grid-cols-4'>
          <KpiTile
            label='Speed'
            value={row.speed}
            icon={Gauge}
            tone='info'
            meter={{ value: row.speed, max: SPAN, label: 'Speed' }}
          />
          <KpiTile
            label='Seaworthiness'
            value={row.seaworthiness}
            icon={Anchor}
            tone='success'
            meter={{
              value: row.seaworthiness,
              max: SPAN,
              label: 'Seaworthiness',
            }}
          />
          <KpiTile
            label='Arms'
            value={row.armament}
            icon={Sword}
            tone='danger'
            meter={{ value: row.armament, max: SPAN, label: 'Arms' }}
          />
          <KpiTile label='Cargo' value={row.cargo} icon={Package} tone='gold' />
        </div>
      </div>
      <Facts
        items={[
          ['Reach', row.range],
          ['Crew', row.crew],
          ['Mass of its parts', row.mass],
          ['Owned by', <Ref key='owner' node={row.owner} />],
          [
            'Drawn by',
            <Ref key='designer' node={row.designer} empty='its owner' />,
          ],
          [
            'Improves on',
            row.parent_design_id !== null
              ? `design ${row.parent_design_id}`
              : 'nothing; a first mark',
          ],
        ]}
      />
      <Label variant='overline'>{`Parts (${row.components.length})`}</Label>
      <PagedList
        items={row.components}
        initial={3}
        noun={['part', 'parts']}
        className='flex min-w-0 flex-col gap-2'
        itemKey={(part) => part.component}
      >
        {(part) => (
          <PartRow
            designId={row.id}
            vesselId={fitted ? vesselId : null}
            part={part}
            materials={materials}
            blocked={busy}
          />
        )}
      </PagedList>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          act={refitting}
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => refitting.mutate()}
        >
          <RefreshCw />
          Draw a new mark
        </Button>
        <Button
          act={fitting}
          size='sm'
          variant='outline'
          disabled={(unfit ?? busy) !== null}
          disabledReason={unfit ?? busy ?? undefined}
          onClick={() => fitting.mutate()}
        >
          <Wrench />
          Refit this vessel to it
        </Button>
      </div>
    </Held>
  )
}

function DesignForge({
  ownerId,
  blocked,
}: {
  ownerId: number
  blocked: string | null
}) {
  const [frame, setFrame] = useState('boat')
  const [quality, setQuality] = useState('50')
  const frames = frameTable(useFrames().data ?? [])
  const drawing = useCollectiveAction(
    'design:draw',
    (_: void) => ({
      owner_id: ownerId,
      frame: frame as NonNullable<DesignView['frame']>,
      quality: clamp(quality),
    }),
    'The design is drawn'
  )
  const busy = why(blocked, drawing.isPending)
  return (
    <ForgeCard
      icon={Ship}
      tone='info'
      title='Draw a design'
      note='Draw a vehicle type on any frame for this owner; its yards build new vehicles to it.'
      columns={3}
      action={
        <Button
          act={drawing}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => drawing.mutate()}
        >
          <Hammer />
          Draw it
        </Button>
      }
    >
      <MindPicker
        label='Frame'
        value={frame}
        table={table(frames)}
        blocked={busy}
        onPick={setFrame}
      />
      <NumberField
        label='Quality'
        value={quality}
        min={0}
        max={SPAN}
        blocked={busy}
        onChange={setQuality}
      />
    </ForgeCard>
  )
}

export function DesignPanel({
  nodeId,
  type,
  data,
  blocked,
}: {
  nodeId: number
  type: string | null
  data: CollectiveView
  blocked: string | null
}) {
  const materials = Object.fromEntries(
    data.materials.map((item) => [String(item.id), item.name])
  )
  const vesselId = type === 'vessel' ? nodeId : null
  return (
    <div
      id='section-designs'
      data-surface='DesignPanel'
      className='flex min-w-0 flex-col gap-3'
    >
      <Label variant='overline'>Designs</Label>
      <Listed
        title='Designs'
        items={data.designs}
        empty='No design is drawn here.'
        noun={['design', 'designs']}
        itemKey={(row) => row.id}
      >
        {(row) => (
          <DesignCard
            row={row}
            vesselId={vesselId}
            fitted={data.vessel_design_id === row.id}
            materials={materials}
            blocked={blocked}
          />
        )}
      </Listed>
      <DesignForge ownerId={nodeId} blocked={blocked} />
    </div>
  )
}

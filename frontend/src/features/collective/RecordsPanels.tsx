import { useState } from 'react'
import {
  Anchor,
  CalendarDays,
  Copy,
  Gauge,
  Hammer,
  Package,
  Quote,
  RefreshCw,
  Shield,
  Ship,
  Sword,
  Wrench,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Chip, Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { HULL } from '@/features/wars/military/depth'
import { ArmsShield } from './ArmsShield'
import {
  type ArmsView,
  type CollectiveView,
  type DesignView,
  useCollectiveAction,
} from './api'
import {
  BEARERS,
  CHARGES,
  DATING,
  DESIGN_KINDS,
  DIVISIONS,
  PARTS,
  TINCTURES,
} from './labels'
import { clamp, SPAN, useRemove, useRow } from './model'
import { Held, Listed } from './parts'

type Dating = NonNullable<CollectiveView['dating']>
type Part = DesignView['components'][number]
type Tincture = keyof typeof TINCTURES

const CALENDARS = ['polity', 'cult', 'people']
const BEARER_TYPES: Record<string, keyof typeof BEARERS> = {
  house: 'house',
  polity: 'polity',
  title: 'title',
  army: 'army',
  faction: 'guild',
}
const NO_TINCTURE = 'none'
const TINCTURE_PICK = { [NO_TINCTURE]: 'None', ...TINCTURES }
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

function ArmsCard({
  holderId,
  row,
  label,
  blocked,
}: {
  holderId: number
  row: ArmsView
  label: string
  blocked: string | null
}) {
  const action = useRow(
    'arms:edit',
    'arms:delete',
    { holder_id: holderId },
    blocked
  )
  const [other, setOther] = useState<number | null>(null)
  const quartering = useCollectiveAction(
    'arms:quarter',
    (_: void) => ({ holder_id: holderId, other_id: other ?? 0 }),
    'The arms are quartered'
  )
  const busy = why(action.busy, quartering.isPending)
  const bearer = BEARERS[row.holder_kind]
  return (
    <Held
      icon={Shield}
      tone='gold'
      title={row.blazon}
      caption={`${bearer.label} has borne these arms since epoch ${row.since_epoch}`}
      removeLabel='Grant them anew'
      editTitle='Set the arms'
      note='A cadet bears its parent’s arms within a border; a marriage of two armigerous houses may quarter them.'
      fields={[
        { key: 'field', label: 'Field', kind: 'pick', table: TINCTURES },
        { key: 'division', label: 'Division', kind: 'pick', table: DIVISIONS },
        {
          key: 'second',
          label: 'Second tincture',
          kind: 'pick',
          table: TINCTURE_PICK,
        },
        { key: 'charge', label: 'Charge', kind: 'pick', table: CHARGES },
        {
          key: 'charge_tincture',
          label: 'Charge tincture',
          kind: 'pick',
          table: TINCTURE_PICK,
        },
        { key: 'motto', label: 'Motto', kind: 'text' },
      ]}
      locked={row.locked}
      blocked={busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Chip icon={bearer.icon}>{bearer.label}</Chip>}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-4'>
        <ArmsShield
          field={row.field}
          division={row.division}
          second={row.second}
          charge={row.charge}
          chargeTincture={row.charge_tincture}
          label={`Arms of ${label}`}
          size='lg'
        />
        <div className='flex min-w-0 flex-1 flex-col gap-2'>
          {row.motto && (
            <Text>
              <Quote className='size-icon-sm' aria-hidden='true' /> {row.motto}
            </Text>
          )}
          <Facts
            items={[
              ['Field', TINCTURES[row.field]],
              ['Division', DIVISIONS[row.division]],
              ['Second tincture', row.second ? TINCTURES[row.second] : 'none'],
              ['Charge', CHARGES[row.charge]],
              [
                'Charge tincture',
                row.charge_tincture ? TINCTURES[row.charge_tincture] : 'none',
              ],
              [
                'Differenced from',
                <Ref key='parent' node={row.parent} empty='no parent' />,
              ],
              [
                'Quartered with',
                <Ref key='quartered' node={row.quartered} empty='no one' />,
              ],
            ]}
          />
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <NodePicker
          label='Quarter with'
          value={other}
          onChange={setOther}
          blocked={busy}
          types={['house', 'polity']}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={
            (other === null ? 'Choose whose arms to quarter with' : busy) !==
            null
          }
          disabledReason={
            other === null
              ? 'Choose whose arms to quarter with'
              : (busy ?? undefined)
          }
          onClick={() => quartering.mutate()}
        >
          <Copy />
          Quarter them
        </Button>
      </div>
    </Held>
  )
}

function ArmsForge({
  holderId,
  type,
  blocked,
}: {
  holderId: number
  type: string | null
  blocked: string | null
}) {
  const [field, setField] = useState<Tincture>('blue')
  const [division, setDivision] = useState<keyof typeof DIVISIONS>('plain')
  const [second, setSecond] = useState<string>('silver')
  const [charge, setCharge] = useState<keyof typeof CHARGES>('star')
  const [chargeTincture, setChargeTincture] = useState<string>('gold')
  const [parent, setParent] = useState<number | null>(null)
  const bearer = type ? BEARER_TYPES[type] : undefined
  const granting = useCollectiveAction(
    'arms:set',
    (_: void) => ({
      holder_id: holderId,
      holder_kind: bearer ?? 'house',
      field,
      division,
      second: second === NO_TINCTURE ? null : (second as Tincture),
      charge,
      charge_tincture:
        chargeTincture === NO_TINCTURE ? null : (chargeTincture as Tincture),
    }),
    'The arms are granted'
  )
  const differencing = useCollectiveAction(
    'arms:difference',
    (_: void) => ({
      holder_id: holderId,
      parent_id: parent ?? 0,
      border: second === NO_TINCTURE ? 'silver' : (second as Tincture),
    }),
    'The cadet arms are drawn'
  )
  const wrong =
    bearer === undefined
      ? 'Only houses, realms, titles, armies and guilds bear arms'
      : null
  const busy = why(wrong ?? blocked, granting.isPending, differencing.isPending)
  return (
    <ForgeCard
      icon={Shield}
      tone='gold'
      title='Grant arms'
      note='Choose the field, its division, a charge and their tinctures, or bear a parent’s arms within a border.'
      columns={3}
      meta={
        <ArmsShield
          field={field}
          division={division}
          second={second === NO_TINCTURE ? null : (second as Tincture)}
          charge={charge}
          chargeTincture={
            chargeTincture === NO_TINCTURE ? null : (chargeTincture as Tincture)
          }
          label='The arms as drawn'
          size='md'
        />
      }
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => granting.mutate()}
          >
            <Shield />
            Grant them
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={
              (parent === null
                ? 'Choose the parent whose arms to bear'
                : busy) !== null
            }
            disabledReason={
              parent === null
                ? 'Choose the parent whose arms to bear'
                : (busy ?? undefined)
            }
            onClick={() => differencing.mutate()}
          >
            <Copy />
            Bear the parent’s within a border
          </Button>
        </div>
      }
    >
      <MindPicker
        label='Field'
        value={field}
        table={TINCTURES}
        blocked={busy}
        onPick={(value) => setField(value as Tincture)}
      />
      <MindPicker
        label='Division'
        value={division}
        table={DIVISIONS}
        blocked={busy}
        onPick={(value) => setDivision(value as keyof typeof DIVISIONS)}
      />
      <MindPicker
        label='Second tincture'
        value={second}
        table={TINCTURE_PICK}
        blocked={busy}
        onPick={setSecond}
      />
      <MindPicker
        label='Charge'
        value={charge}
        table={CHARGES}
        blocked={busy}
        onPick={(value) => setCharge(value as keyof typeof CHARGES)}
      />
      <MindPicker
        label='Charge tincture'
        value={chargeTincture}
        table={TINCTURE_PICK}
        blocked={busy}
        onPick={setChargeTincture}
      />
      <NodePicker
        label='Parent'
        value={parent}
        onChange={setParent}
        blocked={busy}
        types={['house', 'polity']}
      />
    </ForgeCard>
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

function PartRow({
  designId,
  part,
  materials,
  blocked,
}: {
  designId: number
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
    <div className='flex min-w-0 flex-col gap-2 rounded-lg border p-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Chip icon={spec.icon}>{spec.label}</Chip>
        <Muted variant='caption'>{part.material_name ?? 'common stuff'}</Muted>
      </div>
      {part.wear !== null && (
        <Meter
          label='Wear on this vessel'
          value={part.wear}
          max={SPAN}
          tone='warning'
          icon={Wrench}
        />
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
      title={`${row.name} · mark ${row.mark}`}
      caption={`${kind.label}${row.hull ? ` · ${HULL[row.hull]?.label ?? row.hull}` : ''} · drawn in epoch ${row.epoch}${row.obsolete ? ' · superseded' : ''}`}
      removeLabel='Strike the design'
      editTitle='Set the design'
      note='Speed, reach, cargo, arms and crew follow from its parts; set them here to hold them against the parts.'
      fields={[
        { key: 'name', label: 'Name', kind: 'text' },
        { key: 'hull', label: 'Hull', kind: 'pick', table: table(HULL) },
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
      <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
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
      {row.components.map((part) => (
        <PartRow
          key={part.component}
          designId={row.id}
          part={part}
          materials={materials}
          blocked={busy}
        />
      ))}
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
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
  const [kind, setKind] = useState<keyof typeof DESIGN_KINDS>('vessel')
  const [hull, setHull] = useState('carrack')
  const [quality, setQuality] = useState('50')
  const drawing = useCollectiveAction(
    'design:draw',
    (_: void) => ({
      owner_id: ownerId,
      kind,
      hull:
        kind === 'siege_engine'
          ? null
          : (hull as NonNullable<DesignView['hull']>),
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
      note='Draw a vessel, skyship or siege engine for this owner; new hulls and engines are built to it.'
      columns={3}
      action={
        <Button
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
        label='What'
        value={kind}
        table={table(DESIGN_KINDS)}
        blocked={busy}
        onPick={(value) => setKind(value as keyof typeof DESIGN_KINDS)}
      />
      <MindPicker
        label='Hull'
        value={hull}
        table={table(HULL)}
        blocked={kind === 'siege_engine' ? 'A siege engine has no hull' : busy}
        onPick={setHull}
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

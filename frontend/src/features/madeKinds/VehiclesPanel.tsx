import { useState } from 'react'
import {
  ArrowLeftRight,
  Fuel,
  Gauge,
  Hammer,
  Package,
  Plus,
  Sword,
  Users,
  Wrench,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { Held, Listed } from '@/features/collective/parts'
import { Chip, ForgeCard } from '@/features/cosmography/parts'
import { SPAN } from '@/features/cycles/model'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { IntegrityDiagram } from './IntegrityDiagram'
import {
  type ThingKinds,
  type VehicleGroup,
  type VehicleType,
  useLever,
} from './api'
import {
  CRITICALITY,
  VEHICLE_FAMILY,
  VEHICLE_STATUS,
  namedTable,
  sectionLabel,
} from './labels'
import { HOLDER_TYPES, useKindRow, worst } from './model'
import { vehicleZone } from './zones'

type GroupSection = VehicleGroup['sections'][number]

const LANDS = ['region'] as const
const LOTS = 1_000_000

function GroupSectionCard({
  row,
  group,
  blocked,
}: {
  row: GroupSection
  group: VehicleGroup
  blocked: string | null
}) {
  const action = useKindRow(
    'vehicle_group_section:set',
    'vehicle_group_section:delete',
    { group_id: group.id, section: row.section },
    blocked
  )
  const state = worst(group.count, row.damaged, row.disabled, row.destroyed)
  return (
    <Held
      icon={CRITICALITY[row.criticality].icon}
      tone={
        state === 'sound'
          ? 'success'
          : state === 'damaged'
            ? 'warning'
            : 'danger'
      }
      title={sectionLabel(row.section)}
      caption={`${row.damaged} damaged · ${row.disabled} disabled · ${row.destroyed} destroyed of ${group.count}`}
      removeLabel='Make it whole'
      editTitle='Set the damage of this section'
      note='How many vehicles of the group carry a damaged, disabled or destroyed section here. A destroyed critical section loses the vehicle; a disabled one cripples what it serves.'
      fields={[
        { key: 'damaged', label: 'Damaged', kind: 'number', min: 0, max: LOTS },
        {
          key: 'disabled',
          label: 'Disabled',
          kind: 'number',
          min: 0,
          max: LOTS,
        },
        {
          key: 'destroyed',
          label: 'Destroyed',
          kind: 'number',
          min: 0,
          max: LOTS,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function GroupCard({
  row,
  design,
  types,
  blocked,
}: {
  row: VehicleGroup
  design: VehicleType | undefined
  types: Record<string, string>
  blocked: string | null
}) {
  const action = useKindRow(
    'vehicle_group:edit',
    'vehicle_group:delete',
    { record_id: row.id },
    blocked
  )
  const [target, setTarget] = useState<number | null>(null)
  const [count, setCount] = useState('1')
  const [section, setSection] = useState('')
  const move = useLever(
    'vehicle_group:move',
    (_: void) => ({
      group_id: row.id,
      holder_id: target ?? 0,
      count: Number(count),
    }),
    'The vehicles change hands'
  )
  const repair = useLever(
    'vehicle_group:repair',
    (_: void) => ({ group_id: row.id, points: SPAN }),
    'The vehicles are mended'
  )
  const strike = useLever(
    'vehicle_group_section:set',
    (_: void) => ({
      group_id: row.id,
      section: section as never,
      values: { damaged: 1 },
    }),
    'The section is marked'
  )
  const busy = why(
    action.busy,
    move.isPending,
    repair.isPending,
    strike.isPending
  )
  const family = row.family ? VEHICLE_FAMILY[row.family] : VEHICLE_FAMILY.cart
  const status = VEHICLE_STATUS[row.status]
  const damage = new Map(row.sections.map((item) => [item.section, item]))
  const parts = (design?.sections ?? []).map((item) => {
    const hit = damage.get(item.section)
    return {
      key: item.section,
      state: hit
        ? worst(row.count, hit.damaged, hit.disabled, hit.destroyed)
        : ('sound' as const),
      criticality: item.criticality,
      share: item.share,
      hazard: item.hazard,
      detail: hit
        ? `${hit.damaged} damaged, ${hit.disabled} disabled, ${hit.destroyed} destroyed`
        : 'all whole',
    }
  })
  const sections = Object.fromEntries(
    (design?.sections ?? [])
      .filter((item) => !damage.has(item.section))
      .map((item) => [item.section, sectionLabel(item.section)])
  )
  return (
    <Held
      icon={family.icon}
      tone={row.status === 'wrecked' ? 'danger' : family.tone}
      title={`${row.count} × ${row.design_name}`}
      caption={`${status.label} · ${row.crewed} crewed · condition ${row.condition}${row.region ? ` · in ${row.region.name}` : ''}`}
      removeLabel='Strike the group'
      editTitle='Set the group'
      note='How many vehicles of the type are held, how many are crewed, their condition, fuel and what they are doing. Damage to their sections is set below.'
      fields={[
        {
          key: 'holder_node_id',
          label: 'Held by',
          kind: 'node',
          types: HOLDER_TYPES,
        },
        { key: 'design_id', label: 'Vehicle type', kind: 'pick', table: types },
        { key: 'count', label: 'How many', kind: 'number', min: 0, max: LOTS },
        { key: 'crewed', label: 'Crewed', kind: 'number', min: 0, max: LOTS },
        {
          key: 'condition',
          label: 'Condition',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'fuel', label: 'Fuel', kind: 'number', min: 0, max: SPAN },
        {
          key: 'status',
          label: 'What they do',
          kind: 'pick',
          table: namedTable(VEHICLE_STATUS),
        },
        {
          key: 'region_entity_id',
          label: 'Where they are',
          kind: 'node',
          types: LANDS,
        },
      ]}
      locked={row.locked}
      blocked={busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <>
          <Chip icon={status.icon}>{status.label}</Chip>
          <Chip icon={Users}>{`Needs ${row.crew_needed} crew`}</Chip>
          <Chip>{`Built in epoch ${row.built_epoch}`}</Chip>
          <Chip>
            Held by <Ref node={row.holder} />
          </Chip>
        </>
      }
    >
      <IntegrityDiagram
        title={`Damage across ${row.design_name}`}
        parts={parts}
        zoneOf={vehicleZone}
      />
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2 @2xl/tiles:grid-cols-4'>
          <KpiTile
            label='Firepower'
            value={row.firepower}
            icon={Sword}
            tone='danger'
          />
          <KpiTile label='Pace' value={row.pace} icon={Gauge} tone='info' />
          <KpiTile
            label='Troops carried'
            value={row.troops}
            icon={Users}
            tone='gold'
          />
          {design?.fuel ? (
            <KpiTile
              label='Fuel'
              value={row.fuel}
              icon={Fuel}
              tone='warning'
              meter={{ value: row.fuel, max: SPAN, label: 'Fuel' }}
            />
          ) : (
            <KpiTile
              label='Cargo'
              value={row.cargo}
              icon={Package}
              tone='gold'
            />
          )}
        </div>
      </div>
      <Listed
        title='Damaged sections'
        items={row.sections}
        empty='Every section of every vehicle is whole.'
        noun={['section', 'sections']}
        itemKey={(item) => item.section}
      >
        {(item) => (
          <GroupSectionCard row={item} group={row} blocked={blocked} />
        )}
      </Listed>
      <ForgeCard
        icon={Wrench}
        tone='info'
        title='Move, mend or strike'
        note='Hand some of the vehicles to another holder, mend the group at a yard, or mark a section as hit.'
        columns={4}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Button
              size='sm'
              disabled={(busy ?? (target ? null : 'Pick a holder')) !== null}
              disabledReason={busy ?? (target ? undefined : 'Pick a holder')}
              onClick={() => move.mutate()}
            >
              <ArrowLeftRight />
              Hand them over
            </Button>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => repair.mutate()}
            >
              <Hammer />
              Mend at a yard
            </Button>
            <Button
              size='sm'
              variant='outline'
              disabled={(busy ?? (section ? null : 'Pick a section')) !== null}
              disabledReason={busy ?? (section ? undefined : 'Pick a section')}
              onClick={() => strike.mutate()}
            >
              Mark it hit
            </Button>
          </div>
        }
      >
        <NodePicker
          label='New holder'
          value={target}
          onChange={setTarget}
          blocked={busy}
          types={HOLDER_TYPES}
        />
        <NumberField
          label='How many'
          value={count}
          min={1}
          max={row.count}
          blocked={busy}
          onChange={setCount}
        />
        <MindPicker
          label='Section hit'
          value={section}
          table={sections}
          blocked={
            Object.keys(sections).length
              ? busy
              : 'Every section already carries damage'
          }
          onPick={setSection}
        />
      </ForgeCard>
    </Held>
  )
}

export function VehiclesPanel({
  nodeId,
  data,
  types,
  blocked,
}: {
  nodeId: number
  data: ThingKinds
  types: VehicleType[]
  blocked: string | null
}) {
  const [design, setDesign] = useState('')
  const [count, setCount] = useState('1')
  const give = useLever(
    'vehicle_group:create',
    (_: void) => ({
      holder_id: nodeId,
      design_id: Number(design),
      count: Number(count),
      crewed: Number(count),
    }),
    'The vehicles are given'
  )
  const busy = why(blocked, give.isPending)
  const table = Object.fromEntries(
    types.map((item) => [
      String(item.id),
      `${item.name} (${item.frame_label ?? 'vehicle'})`,
    ])
  )
  const byId = new Map(types.map((item) => [item.id, item]))
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      {data.pace !== null && (
        <KpiTile
          label='Pace its vehicles set'
          value={data.pace}
          icon={Gauge}
          tone='info'
        />
      )}
      <Listed
        title='Vehicles held'
        items={data.vehicle_groups}
        empty='It holds no vehicles.'
        noun={['group', 'groups']}
        itemKey={(item) => item.id}
      >
        {(item) => (
          <GroupCard
            row={item}
            design={byId.get(item.design_id)}
            types={table}
            blocked={blocked}
          />
        )}
      </Listed>
      <ForgeCard
        icon={Plus}
        tone='gold'
        title='Give vehicles'
        note='Give it vehicles of a type known in its world; they arrive crewed and whole.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={
              (busy ?? (design ? null : 'Pick a vehicle type')) !== null
            }
            disabledReason={
              busy ?? (design ? undefined : 'Pick a vehicle type')
            }
            onClick={() => give.mutate()}
          >
            <Plus />
            Give them
          </Button>
        }
      >
        <MindPicker
          label='Vehicle type'
          value={design}
          table={table}
          blocked={
            Object.keys(table).length
              ? busy
              : 'No vehicle type is known in this world yet; draw one under its kinds'
          }
          onPick={setDesign}
        />
        <NumberField
          label='How many'
          value={count}
          min={1}
          max={LOTS}
          blocked={busy}
          onChange={setCount}
        />
      </ForgeCard>
    </div>
  )
}

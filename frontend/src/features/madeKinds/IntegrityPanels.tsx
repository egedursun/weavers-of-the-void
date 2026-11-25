import { useState } from 'react'
import { Gauge, Hammer, Orbit, Zap } from 'lucide-react'
import {
  structureSectionValues,
  vehicleSectionValues,
} from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { Held, Listed } from '@/features/collective/parts'
import { ForgeCard } from '@/features/cosmography/parts'
import { SPAN } from '@/features/cycles/model'
import { why } from '@/features/dominion/model'
import { wordOf } from '@/features/entity/affairs/labels'
import { useWorldMaterials } from '@/features/entity/economy/api'
import { MATERIAL_LABEL } from '@/features/entity/economy/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { KIND_SPEC } from '@/features/entity/society/structureLabels'
import { IntegrityDiagram } from './IntegrityDiagram'
import { type ThingKinds, useLever } from './api'
import { buildingShape, vehicleShape } from './blueprints'
import {
  CRITICALITY,
  HAZARD,
  ROLE,
  SECTION_STATE,
  STRUCTURE_SECTIONS,
  namedTable,
  wordTable,
} from './labels'
import { useKindRow, useKindStep } from './model'
import { ListEditor } from './parts'
import { structureZone, vehicleZone } from './zones'

type VesselPart = ThingKinds['vessel_sections'][number]
type StructurePart = ThingKinds['sections'][number]
type Mega = NonNullable<ThingKinds['megastructure']>

const SECTIONS = wordTable(STRUCTURE_SECTIONS)
const ALL_SECTIONS = wordTable(structureSectionValues)

function VesselPartCard({
  row,
  vesselId,
  blocked,
}: {
  row: VesselPart
  vesselId: number
  blocked: string | null
}) {
  const action = useKindRow(
    'vessel_section:set',
    'vessel_section:delete',
    { vessel_id: vesselId, section: row.section },
    blocked
  )
  const state = SECTION_STATE[row.state]
  return (
    <Held
      icon={state.icon}
      tone={state.tone ?? 'muted'}
      title={wordOf(vehicleSectionValues, row.section)}
      caption={`${CRITICALITY[row.criticality].label} · ${state.label} · condition ${row.condition}${row.laid ? '' : ' · never struck'}`}
      removeLabel='Make it whole'
      editTitle='Set the section'
      note='A struck section loses condition; a disabled one cripples what it serves and a destroyed critical one loses the vessel.'
      fields={[
        {
          key: 'state',
          label: 'State',
          kind: 'pick',
          table: namedTable(SECTION_STATE),
        },
        {
          key: 'condition',
          label: 'Condition',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

export function VesselSectionsPanel({
  nodeId,
  data,
  blocked,
}: {
  nodeId: number
  data: ThingKinds
  blocked: string | null
}) {
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Muted variant='caption'>
        Only a vessel carries its own sections; vehicles held in groups keep
        their damage on the group.
      </Muted>
      <IntegrityDiagram
        title={`Sections of ${data.node.name}`}
        shape={vehicleShape(data.vessel_frame, data.vessel_family)}
        parts={data.vessel_sections.map((item) => ({
          key: item.section,
          state: item.state,
          criticality: item.criticality,
          share: 10,
          hazard: 'none',
          detail: `condition ${item.condition}`,
        }))}
        zoneOf={vehicleZone}
      />
      <Listed
        title='Sections'
        items={data.vessel_sections}
        empty='Its frame has no sections.'
        noun={['section', 'sections']}
        itemKey={(item) => item.section}
      >
        {(item) => (
          <VesselPartCard row={item} vesselId={nodeId} blocked={blocked} />
        )}
      </Listed>
    </div>
  )
}

function StructurePartCard({
  row,
  structureId,
  blow,
  materials,
  blocked,
}: {
  row: StructurePart
  structureId: number
  blow: number
  materials: Record<string, string>
  blocked: string | null
}) {
  const action = useKindRow(
    'structure_section:edit',
    'structure_section:delete',
    { structure_id: structureId, section: row.section },
    blocked
  )
  const repair = useKindStep(
    'structure_section:repair',
    { structure_id: structureId, section: row.section },
    blocked,
    'The section is whole'
  )
  const strike = useLever(
    'structure_section:strike',
    (_: void) => ({
      structure_id: structureId,
      section: row.section,
      damage: blow,
    }),
    'The section is struck'
  )
  const busy = why(action.busy ?? repair.busy, strike.isPending)
  const state = SECTION_STATE[row.state]
  const role = ROLE[row.role]
  return (
    <Held
      icon={
        row.criticality === 'critical' ? CRITICALITY.critical.icon : role.icon
      }
      tone={state.tone ?? 'muted'}
      title={wordOf(structureSectionValues, row.section)}
      caption={`${role.label} · ${CRITICALITY[row.criticality].label} · ${state.label} · condition ${row.condition}`}
      removeLabel='Take it away'
      editTitle='Set the section'
      note='Fire spreads to neighbours by how readily they burn; a collapsing foundation brings down what stands on it. A fallen gate breaches the walls, a fallen keep lets the siege in, a ruined sanctum shames its faithful.'
      fields={[
        {
          key: 'role',
          label: 'What it does',
          kind: 'pick',
          table: namedTable(ROLE),
        },
        {
          key: 'criticality',
          label: 'Criticality',
          kind: 'pick',
          table: namedTable(CRITICALITY),
        },
        {
          key: 'share',
          label: 'Share of the whole (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'exposure',
          label: 'Exposure (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'hazard',
          label: 'When it fails',
          kind: 'pick',
          table: namedTable(HAZARD),
        },
        {
          key: 'condition',
          label: 'Condition',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'state',
          label: 'State',
          kind: 'pick',
          table: namedTable(SECTION_STATE),
        },
        {
          key: 'material',
          label: 'Material',
          kind: 'pick',
          table: MATERIAL_LABEL,
        },
        {
          key: 'world_material_id',
          label: 'Material of this world',
          kind: 'pick',
          table: materials,
        },
        {
          key: 'flammability',
          label: 'How readily it burns',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <>
          <Button
            act={strike}
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => strike.mutate()}
          >
            <Zap />
            Strike it
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={
              (busy ?? (row.condition >= SPAN ? 'It is whole' : null)) !== null
            }
            disabledReason={
              busy ?? (row.condition >= SPAN ? 'It is whole' : undefined)
            }
            onClick={repair.run}
          >
            <Hammer />
            Make it whole
          </Button>
        </>
      }
    >
      <ListEditor
        field={{
          key: 'neighbours',
          label: 'Spreads to',
          note: 'Fire and collapse pass from this section to these.',
        }}
        options={SECTIONS}
        value={row.neighbours}
        held={row.locked.includes('neighbours')}
        blocked={busy}
        onSet={(next) =>
          action.onEdit({ values: { neighbours: next as never }, release: [] })
        }
      />
    </Held>
  )
}

function MegaCard({
  row,
  structureId,
  blocked,
}: {
  row: Mega
  structureId: number
  blocked: string | null
}) {
  const action = useKindRow(
    'megastructure:edit',
    'megastructure:delete',
    { structure_id: structureId },
    blocked
  )
  const kind = KIND_SPEC[row.kind]
  return (
    <ul className='flex min-w-0 flex-col gap-2'>
      <Held
        icon={Orbit}
        tone='verdigris'
        title={`${kind.label} at work`}
        caption={`Output ${row.output}${row.target_orbit !== null ? ` · steering toward orbit ${row.target_orbit}` : ''} · last turned in epoch ${row.updated_epoch}`}
        removeLabel='Start it afresh'
        editTitle='Set the megastructure'
        note={`${kind.hint ?? kind.label}. Its control core is critical: if it fails the whole work fails with it, and its town suffers.`}
        fields={[
          { key: 'output', label: 'Output', kind: 'number', min: 0, max: SPAN },
          {
            key: 'target_orbit',
            label: 'Orbit it steers toward',
            kind: 'decimal',
            min: 0,
          },
        ]}
        locked={row.locked}
        blocked={action.busy}
        onEdit={action.onEdit}
        onRemove={action.onRemove}
      >
        <KpiTile
          label='Output'
          value={row.output}
          icon={Gauge}
          tone='verdigris'
          meter={{ value: row.output, max: SPAN, label: 'Output' }}
        />
      </Held>
    </ul>
  )
}

export function StructureSectionsPanel({
  nodeId,
  data,
  blocked,
}: {
  nodeId: number
  data: ThingKinds
  blocked: string | null
}) {
  const [section, setSection] = useState('')
  const [damage, setDamage] = useState('40')
  const worldMaterials = useWorldMaterials(data.world_id)
  const materials = Object.fromEntries(
    (worldMaterials.data?.materials ?? []).flatMap((item) =>
      item.world_material_id === null
        ? []
        : [[String(item.world_material_id), item.label]]
    )
  )
  const add = useLever(
    'structure_section:edit',
    (_: void) => ({
      structure_id: nodeId,
      section: section as never,
      values: {},
      release: [],
    }),
    'The section is laid'
  )
  const busy = why(blocked, add.isPending)
  const have = new Set(
    data.sections
      .filter((item) => item.laid)
      .map((item) => item.section as string)
  )
  const free = Object.fromEntries(
    Object.entries(ALL_SECTIONS).filter(([key]) => !have.has(key))
  )
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Muted variant='caption'>
        Only a structure stands in sections; other things carry their integrity
        in their bodies or hulls.
      </Muted>
      <IntegrityDiagram
        title={`Sections of ${data.node.name}`}
        parts={data.sections.map((item) => ({
          key: item.section,
          state: item.state,
          criticality: item.criticality,
          share: item.share,
          hazard: item.hazard,
          detail: `condition ${item.condition}, burns at ${item.flammability}`,
        }))}
        zoneOf={structureZone}
        shape={data.megastructure ? 'ring' : buildingShape(data.structure_form)}
      />
      {data.megastructure && (
        <>
          <Label variant='overline'>Megastructure</Label>
          <MegaCard
            row={data.megastructure}
            structureId={nodeId}
            blocked={blocked}
          />
        </>
      )}
      <Listed
        title='Sections'
        items={data.sections}
        empty='It has no sections.'
        noun={['section', 'sections']}
        itemKey={(item) => item.section}
      >
        {(item) => (
          <StructurePartCard
            row={item}
            structureId={nodeId}
            blow={Math.max(1, Math.min(SPAN, Number(damage) || 1))}
            materials={materials}
            blocked={blocked}
          />
        )}
      </Listed>
      <ForgeCard
        icon={Hammer}
        tone='info'
        title='Lay a section, set the blow'
        note='Add a section the common layout of its kind does not have; it starts whole. The blow sets how hard each strike above hits.'
        columns={2}
        action={
          <Button
            act={add}
            size='sm'
            disabled={(busy ?? (section ? null : 'Pick a section')) !== null}
            disabledReason={busy ?? (section ? undefined : 'Pick a section')}
            onClick={() => add.mutate()}
          >
            Lay it
          </Button>
        }
      >
        <MindPicker
          label='Section'
          value={section}
          table={free}
          blocked={Object.keys(free).length ? busy : 'Every section is laid'}
          onPick={setSection}
        />
        <NumberField
          label='Blow of each strike'
          value={damage}
          min={1}
          max={SPAN}
          blocked={busy}
          onChange={setDamage}
        />
      </ForgeCard>
    </div>
  )
}

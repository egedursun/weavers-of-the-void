import { useState } from 'react'
import {
  Anchor,
  Gauge,
  Hammer,
  Package,
  Plus,
  RefreshCw,
  Shield,
  Sword,
  Trash2,
  Users,
  Wrench,
} from 'lucide-react'
import { techniqueValues } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { KpiTile, PagedList } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { PARTS } from '@/features/collective/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Chip, Facts, ForgeCard } from '@/features/cosmography/parts'
import { SPAN } from '@/features/cycles/model'
import { why } from '@/features/dominion/model'
import { useWorldMaterials } from '@/features/entity/economy/api'
import { COMMODITY } from '@/features/entity/economy/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { Ref } from '@/features/gatherings/parts'
import { IntegrityDiagram } from './IntegrityDiagram'
import { type EquipmentModel, type VehicleType, useLever } from './api'
import { vehicleShape } from './blueprints'
import {
  ARC,
  CRITICALITY,
  FIRE_CONTROL,
  FRAME_OPTIONS,
  HAZARD,
  MOUNT,
  PROPULSION,
  VEHICLE_DOMAIN,
  VEHICLE_FAMILY,
  VEHICLE_SECTIONS,
  VEHICLE_SIZE,
  namedTable,
  sectionLabel,
  wordTable,
} from './labels'
import { OWNER_TYPES, useKindRow, useKindStep } from './model'
import { KindHeader, ListEditor } from './parts'
import { vehicleZone } from './zones'

type Section = VehicleType['sections'][number]
type Mount = VehicleType['mounts'][number]

const FRAMES = wordTable(FRAME_OPTIONS)
const SECTIONS = wordTable(VEHICLE_SECTIONS)
const TECHNIQUES = wordTable(techniqueValues)
const GODS = ['son', 'creator', 'foreign_god'] as const
const WORLDS = ['world'] as const
const DESIGNERS = ['mortal'] as const
const YES_NO = { true: 'Yes', false: 'No' }
const SIZE_MAX = 10
const SEAGOING = new Set(['water', 'underwater', 'amphibious'])

function SectionCard({
  row,
  designId,
  materials,
  blocked,
}: {
  row: Section
  designId: number
  materials: Record<string, string>
  blocked: string | null
}) {
  const action = useKindRow(
    'design_section:set',
    'design_section:delete',
    { design_id: designId, section: row.section },
    blocked
  )
  const crit = CRITICALITY[row.criticality]
  return (
    <Held
      icon={crit.icon}
      tone={crit.tone}
      title={sectionLabel(row.section)}
      caption={`${crit.label} section · ${PARTS[row.function].label} · ${row.share}% of the whole · ${HAZARD[row.hazard].label.toLowerCase()}`}
      removeLabel='Take it out'
      editTitle='Set the section'
      note='How much of the whole it is, how exposed it is to blows, how well armoured, what happens when it fails and which sections it spreads to. Critical sections lose the vehicle when destroyed; major ones cripple a function; minor ones only wear.'
      fields={[
        {
          key: 'function',
          label: 'What it serves',
          kind: 'pick',
          table: namedTable(PARTS),
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
          label: 'Exposure to blows (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'armour', label: 'Armour', kind: 'number', min: 0, max: SPAN },
        {
          key: 'hazard',
          label: 'When it fails',
          kind: 'pick',
          table: namedTable(HAZARD),
        },
        {
          key: 'material_id',
          label: 'Material',
          kind: 'pick',
          table: materials,
        },
        { key: 'size', label: 'Size', kind: 'number', min: 0, max: SIZE_MAX },
        { key: 'quality', label: 'Quality', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <>
          <Chip icon={Shield}>{`Armour ${row.armour}`}</Chip>
          <Chip>{`Exposure ${row.exposure}%`}</Chip>
          <Chip>{`Quality ${row.quality}`}</Chip>
          <Chip>{row.material_name ?? 'Common material'}</Chip>
        </>
      }
    >
      <ListEditor
        field={{
          key: 'neighbours',
          label: 'Spreads to',
          note: 'Fire, floods and explosions pass from this section to these.',
        }}
        options={SECTIONS}
        value={row.neighbours}
        held={row.locked.includes('neighbours')}
        blocked={action.busy}
        onSet={(next) =>
          action.onEdit({ values: { neighbours: next as never }, release: [] })
        }
      />
    </Held>
  )
}

function MountCard({
  row,
  sections,
  models,
  blocked,
}: {
  row: Mount
  sections: Record<string, string>
  models: Record<string, string>
  blocked: string | null
}) {
  const action = useKindRow(
    'design_mount:edit',
    'design_mount:delete',
    { record_id: row.id },
    blocked
  )
  const mount = MOUNT[row.mount]
  return (
    <Held
      icon={mount.icon}
      tone={mount.tone}
      title={`${mount.label} × ${row.count}`}
      caption={`${ARC[row.arc].label} · on ${row.section ? sectionLabel(row.section).toLowerCase() : 'no section'} · ${row.model_name ?? 'no weapon fitted'}`}
      removeLabel='Take it off'
      editTitle='Set the mount'
      note='Each mount carries the weapon model fitted to it; its arc sets which foes it can bear on, and it is lost when its section is destroyed.'
      fields={[
        { key: 'slot', label: 'Slot', kind: 'number', min: 0, max: SPAN },
        {
          key: 'mount',
          label: 'Mount',
          kind: 'pick',
          table: namedTable(MOUNT),
        },
        {
          key: 'section',
          label: 'On the section',
          kind: 'pick',
          table: sections,
        },
        {
          key: 'model_id',
          label: 'Weapon fitted',
          kind: 'pick',
          table: models,
        },
        { key: 'count', label: 'How many', kind: 'number', min: 1, max: SPAN },
        { key: 'arc', label: 'Arc', kind: 'pick', table: namedTable(ARC) },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function TechniqueChip({
  designId,
  technique,
  blocked,
}: {
  designId: number
  technique: string
  blocked: string | null
}) {
  const remove = useKindStep(
    'design_technique:delete',
    { design_id: designId, technique: technique as never },
    blocked,
    'The technique is no longer needed'
  )
  return (
    <Button
      size='sm'
      variant='outline'
      disabled={remove.busy !== null}
      disabledReason={remove.busy ?? undefined}
      onClick={remove.run}
    >
      {sectionLabel(technique)}
      <Trash2 />
    </Button>
  )
}

function Additions({
  row,
  blocked,
}: {
  row: VehicleType
  blocked: string | null
}) {
  const [section, setSection] = useState('')
  const [mount, setMount] = useState('')
  const [technique, setTechnique] = useState('')
  const addSection = useLever(
    'design_section:set',
    (_: void) => ({ design_id: row.id, section: section as never, values: {} }),
    'The section is added'
  )
  const addMount = useLever(
    'design_mount:add',
    (_: void) => ({ design_id: row.id, mount: mount as never, values: {} }),
    'The mount is added'
  )
  const addTechnique = useLever(
    'design_technique:add',
    (_: void) => ({ design_id: row.id, technique: technique as never }),
    'The technique is now needed'
  )
  const busy = why(
    blocked,
    addSection.isPending,
    addMount.isPending,
    addTechnique.isPending
  )
  const have = new Set(row.sections.map((item) => item.section))
  const free = Object.fromEntries(
    Object.entries(SECTIONS).filter(([key]) => !have.has(key as never))
  )
  const needed = Object.fromEntries(
    Object.entries(TECHNIQUES).filter(
      ([key]) => !row.techniques.includes(key as never)
    )
  )
  return (
    <ForgeCard
      icon={Wrench}
      tone='info'
      title='Add to the type'
      note='Add a section, a weapon mount or a technique its builders must know. Speed, reach, cargo, arms and crew follow from its sections and mounts.'
      columns={3}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={(busy ?? (section ? null : 'Pick a section')) !== null}
            disabledReason={busy ?? (section ? undefined : 'Pick a section')}
            onClick={() => addSection.mutate()}
          >
            <Plus />
            Add the section
          </Button>
          <Button
            size='sm'
            disabled={(busy ?? (mount ? null : 'Pick a mount')) !== null}
            disabledReason={busy ?? (mount ? undefined : 'Pick a mount')}
            onClick={() => addMount.mutate()}
          >
            <Plus />
            Add the mount
          </Button>
          <Button
            size='sm'
            disabled={
              (busy ?? (technique ? null : 'Pick a technique')) !== null
            }
            disabledReason={
              busy ?? (technique ? undefined : 'Pick a technique')
            }
            onClick={() => addTechnique.mutate()}
          >
            <Plus />
            Require the technique
          </Button>
        </div>
      }
    >
      <MindPicker
        label='Section'
        value={section}
        table={free}
        blocked={
          Object.keys(free).length ? busy : 'It has every section already'
        }
        onPick={setSection}
      />
      <MindPicker
        label='Mount'
        value={mount}
        table={namedTable(MOUNT)}
        blocked={busy}
        onPick={setMount}
      />
      <MindPicker
        label='Technique'
        value={technique}
        table={needed}
        blocked={busy}
        onPick={setTechnique}
      />
    </ForgeCard>
  )
}

export function VehicleTypePage({
  row,
  models,
  blocked = null,
}: {
  row: VehicleType
  models: EquipmentModel[]
  blocked?: string | null
}) {
  const action = useKindRow(
    'design:edit',
    'design:delete',
    { design_id: row.id },
    blocked
  )
  const refit = useKindStep(
    'design:refit',
    { design_id: row.id },
    blocked,
    'A new mark is drawn'
  )
  const worldMaterials = useWorldMaterials(row.world_id)
  const materials = Object.fromEntries(
    (worldMaterials.data?.materials ?? []).flatMap((item) =>
      item.world_material_id === null
        ? []
        : [[String(item.world_material_id), item.label]]
    )
  )
  const family = row.family ? VEHICLE_FAMILY[row.family] : VEHICLE_FAMILY.cart
  const seagoing = row.domain !== null && SEAGOING.has(row.domain)
  const sections = Object.fromEntries(
    row.sections.map((item) => [item.section, sectionLabel(item.section)])
  )

  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <KindHeader
        icon={family.icon}
        tone={row.obsolete ? 'muted' : family.tone}
        overline='Vehicle type'
        title={row.name}
        caption={`${row.frame_label ?? 'No frame'} of ${row.origin?.name ?? 'no maker'} · drawn in epoch ${row.epoch}${row.obsolete ? ' · superseded' : ''}`}
        chips={
          <>
            <Chip icon={family.icon}>{family.label}</Chip>
            {row.domain && (
              <Chip icon={VEHICLE_DOMAIN[row.domain].icon}>
                {VEHICLE_DOMAIN[row.domain].label}
              </Chip>
            )}
            {row.propulsion && (
              <Chip icon={PROPULSION[row.propulsion].icon}>
                {PROPULSION[row.propulsion].label}
              </Chip>
            )}
            <Chip>{VEHICLE_SIZE[row.size_class].label}</Chip>
            <Chip icon={FIRE_CONTROL[row.fire_control].icon}>
              {FIRE_CONTROL[row.fire_control].label}
            </Chip>
            <Chip icon={Package}>{`${row.built} built`}</Chip>
          </>
        }
      />
      {row.description && <Muted variant='caption'>{row.description}</Muted>}
      <IntegrityDiagram
        title={`Sections of ${row.name}`}
        parts={row.sections.map((item) => ({
          key: item.section,
          state: 'sound',
          criticality: item.criticality,
          share: item.share,
          hazard: item.hazard,
          detail: `armour ${item.armour}`,
        }))}
        mounts={row.mounts.map((item) => ({
          key: String(item.id),
          section: item.section,
          label: `${MOUNT[item.mount].label}${item.model_name ? ` with ${item.model_name}` : ''}, ${ARC[item.arc].label.toLowerCase()}`,
          count: item.count,
          arc: item.arc,
        }))}
        zoneOf={vehicleZone}
        shape={vehicleShape(row.frame, row.family)}
      />
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
            label='Arms'
            value={row.armament}
            icon={Sword}
            tone='danger'
            meter={{ value: row.armament, max: SPAN, label: 'Arms' }}
          />
          <KpiTile
            label='Armour'
            value={row.armour}
            icon={Shield}
            tone='gold'
            meter={{ value: row.armour, max: SPAN, label: 'Armour' }}
          />
          {seagoing ? (
            <KpiTile
              label='Seaworthiness'
              value={row.seaworthiness}
              icon={Anchor}
              tone='verdigris'
              meter={{
                value: row.seaworthiness,
                max: SPAN,
                label: 'Seaworthiness',
              }}
            />
          ) : (
            <KpiTile
              label='Cargo'
              value={row.cargo}
              icon={Package}
              tone='verdigris'
            />
          )}
        </div>
      </div>
      <Facts
        items={[
          ['Reach', row.range],
          ...(seagoing ? [['Cargo', row.cargo] as [string, number]] : []),
          ['Crew', row.crew],
          ['Troops carried', row.troops],
          ['Structure', row.structure],
          ['Mass of its parts', row.mass],
          [
            'Fuel',
            row.fuel
              ? `${COMMODITY[row.fuel].label}, ${row.fuel_use} an epoch`
              : 'none',
          ],
          ['Cost and upkeep', `${row.cost} · ${row.upkeep}`],
          ['Knowledge', `level ${row.tech_level}`],
          ['Strangeness', row.strangeness],
          ['Made by', <Ref key='origin' node={row.origin} empty='no maker' />],
          ['Held by', <Ref key='owner' node={row.owner} empty='no holder' />],
          [
            'Drawn by',
            <Ref key='designer' node={row.designer} empty='its makers' />,
          ],
          [
            'Improves on',
            row.parent_design_id !== null ? 'an earlier mark' : 'none',
          ],
        ]}
      />
      <ul className='flex min-w-0 flex-col gap-2'>
        <Held
          icon={Hammer}
          tone='gold'
          title='The whole type'
          caption='Every value of the type, held as you set it'
          removeLabel='Strike the type'
          editTitle='Set the type'
          note='Speed, reach, cargo, arms and crew follow from its sections and mounts; set them here to hold them against the engine.'
          fields={[
            { key: 'name', label: 'Name of the type', kind: 'text' },
            {
              key: 'description',
              label: 'What sets it apart',
              kind: 'text',
              long: true,
            },
            { key: 'frame', label: 'Frame', kind: 'pick', table: FRAMES },
            {
              key: 'world_id',
              label: 'World',
              kind: 'node',
              types: [],
              kinds: WORLDS,
            },
            {
              key: 'origin_node_id',
              label: 'Made by',
              kind: 'node',
              types: OWNER_TYPES,
              kinds: GODS,
            },
            {
              key: 'owner_entity_id',
              label: 'Held by',
              kind: 'node',
              types: OWNER_TYPES,
            },
            {
              key: 'designer_entity_id',
              label: 'Drawn by',
              kind: 'node',
              types: DESIGNERS,
            },
            {
              key: 'domain',
              label: 'Where it goes',
              kind: 'pick',
              table: namedTable(VEHICLE_DOMAIN),
            },
            {
              key: 'family',
              label: 'Family',
              kind: 'pick',
              table: namedTable(VEHICLE_FAMILY),
            },
            {
              key: 'propulsion',
              label: 'Moved by',
              kind: 'pick',
              table: namedTable(PROPULSION),
            },
            {
              key: 'size_class',
              label: 'Size',
              kind: 'pick',
              table: namedTable(VEHICLE_SIZE),
            },
            {
              key: 'fire_control',
              label: 'How its weapons aim',
              kind: 'pick',
              table: namedTable(FIRE_CONTROL),
            },
            {
              key: 'obsolete',
              label: 'Superseded',
              kind: 'pick',
              table: YES_NO,
            },
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
            {
              key: 'armament',
              label: 'Arms',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
            { key: 'crew', label: 'Crew', kind: 'number', min: 0 },
            { key: 'troops', label: 'Troops carried', kind: 'number', min: 0 },
            {
              key: 'armour',
              label: 'Armour',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
            { key: 'structure', label: 'Structure', kind: 'number', min: 0 },
            {
              key: 'fuel',
              label: 'Fuel',
              kind: 'pick',
              table: namedTable(COMMODITY),
            },
            { key: 'fuel_use', label: 'Fuel an epoch', kind: 'number', min: 0 },
            { key: 'cost', label: 'Cost', kind: 'number', min: 0 },
            { key: 'upkeep', label: 'Upkeep', kind: 'number', min: 0 },
            {
              key: 'tech_level',
              label: 'Knowledge it needs',
              kind: 'number',
              min: 0,
              max: SIZE_MAX,
            },
            {
              key: 'strangeness',
              label: 'Strangeness',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
          ]}
          locked={row.locked}
          blocked={action.busy}
          onEdit={action.onEdit}
          onRemove={action.onRemove}
          extra={
            <Button
              size='sm'
              variant='outline'
              disabled={refit.busy !== null}
              disabledReason={refit.busy ?? undefined}
              onClick={refit.run}
            >
              <RefreshCw />
              Draw a new mark
            </Button>
          }
        />
      </ul>
      <Listed
        title='Sections'
        items={row.sections}
        empty='It has no sections; add one below.'
        noun={['section', 'sections']}
        itemKey={(item) => item.section}
      >
        {(item) => (
          <SectionCard
            row={item}
            designId={row.id}
            materials={materials}
            blocked={blocked}
          />
        )}
      </Listed>
      <Listed
        title='Weapon mounts'
        items={row.mounts}
        empty='It carries no weapon mounts.'
        noun={['mount', 'mounts']}
        itemKey={(item) => item.id}
      >
        {(item) => (
          <MountCard
            row={item}
            sections={sections}
            models={Object.fromEntries(
              models
                .filter((model) => item.families.includes(model.family))
                .map((model) => [
                  String(model.id),
                  `${model.name} (${model.family_label})`,
                ])
            )}
            blocked={blocked}
          />
        )}
      </Listed>
      <Label variant='overline'>{`Techniques its builders must know (${row.techniques.length})`}</Label>
      {row.techniques.length === 0 ? (
        <Muted variant='caption'>It needs no technique beyond its frame.</Muted>
      ) : (
        <PagedList
          items={row.techniques}
          initial={6}
          noun={['technique', 'techniques']}
          className='flex min-w-0 flex-wrap gap-1.5'
          itemKey={(item) => item}
        >
          {(item) => (
            <TechniqueChip
              designId={row.id}
              technique={item}
              blocked={blocked}
            />
          )}
        </PagedList>
      )}
      <Additions row={row} blocked={blocked} />
      <Muted variant='caption'>
        <Users aria-hidden='true' className='size-icon-xs' /> Instances are not
        entered in the atlas; they live with the realms, towns and armies that
        hold them.
      </Muted>
    </div>
  )
}

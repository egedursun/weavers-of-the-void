import { useState } from 'react'
import { Building2, Plus, Ruler } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Muted } from '@/components/typography'
import { Preview } from '@/features/city/TypePages'
import { typedLook } from '@/features/city/models'
import { Held, Listed } from '@/features/collective/parts'
import { Chip, Facts, ForgeCard } from '@/features/cosmography/parts'
import { SPAN } from '@/features/cycles/model'
import { why } from '@/features/dominion/model'
import { COMMODITY, MATERIAL_LABEL } from '@/features/entity/economy/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { CLASS_SPEC, SIZE_SPEC } from '@/features/entity/society/labels'
import {
  KIND_SPEC,
  SCALE_SPEC,
  STAFF_SCALE_SPEC,
} from '@/features/entity/society/structureLabels'
import { Ref } from '@/features/gatherings/parts'
import { IntegrityDiagram } from './IntegrityDiagram'
import { type BuildingType, useLever } from './api'
import {
  CRITICALITY,
  FORM,
  STRUCTURE_SECTIONS,
  namedTable,
  sectionLabel,
  wordTable,
} from './labels'
import { OWNER_TYPES, useKindRow, useKindStep } from './model'
import { KindHeader } from './parts'
import { buildingShape } from './silhouettes'
import { structureZone } from './zones'

type Part = BuildingType['sections'][number]

const SECTIONS = wordTable(STRUCTURE_SECTIONS)
const GODS = ['son', 'creator', 'foreign_god'] as const
const YES_NO = { true: 'Yes', false: 'No' }
const PCT_MAX = 1000
const STOREYS_MAX = 200
const AS_KIND = 'as its kind'

function PartCard({
  row,
  designId,
  blocked,
}: {
  row: Part
  designId: number
  blocked: string | null
}) {
  const action = useKindRow(
    'structure_design_section:set',
    'structure_design_section:delete',
    { design_id: designId, section: row.section },
    blocked
  )
  const crit = CRITICALITY[row.criticality]
  return (
    <Held
      icon={crit.icon}
      tone={crit.tone}
      title={sectionLabel(row.section)}
      caption={`${crit.label} · ${row.share}% of the whole · ${row.material ? MATERIAL_LABEL[row.material] : 'the type’s material'}`}
      removeLabel='Follow the common layout'
      editTitle='Set the section of the type'
      note='Works built to this type lay this section with these values instead of the common layout of their kind.'
      fields={[
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
          key: 'material',
          label: 'Material',
          kind: 'pick',
          table: MATERIAL_LABEL,
        },
      ]}
      locked={[]}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function AddPart({
  row,
  blocked,
}: {
  row: BuildingType
  blocked: string | null
}) {
  const [section, setSection] = useState('')
  const add = useLever(
    'structure_design_section:set',
    (_: void) => ({
      design_id: row.id,
      section: section as never,
      values: { share: 10 },
    }),
    'The section is set'
  )
  const busy = why(blocked, add.isPending)
  const have = new Set(row.sections.map((item) => item.section as string))
  const free = Object.fromEntries(
    Object.entries(SECTIONS).filter(([key]) => !have.has(key))
  )
  return (
    <ForgeCard
      icon={Ruler}
      tone='info'
      title='Set a section of the type'
      note='Give the type its own value for one section: how vital it is, how much of the whole and what it is built of.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={(busy ?? (section ? null : 'Pick a section')) !== null}
          disabledReason={busy ?? (section ? undefined : 'Pick a section')}
          onClick={() => add.mutate()}
        >
          <Plus />
          Set the section
        </Button>
      }
    >
      <MindPicker
        label='Section'
        value={section}
        table={free}
        blocked={
          Object.keys(free).length ? busy : 'Every section is set already'
        }
        onPick={setSection}
      />
    </ForgeCard>
  )
}

export function BuildingTypePage({
  row,
  blocked = null,
}: {
  row: BuildingType
  blocked?: string | null
}) {
  const action = useKindRow(
    'structure_design:edit',
    'structure_design:retire',
    { design_id: row.id },
    blocked
  )
  const retire = useKindStep(
    'structure_design:retire',
    { design_id: row.id, retired: !row.retired },
    blocked,
    row.retired ? 'The type is restored' : 'The type is retired'
  )
  const kind = KIND_SPEC[row.base_kind]
  const form = row.form ? FORM[row.form] : null
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <KindHeader
        icon={form?.icon ?? kind.icon}
        tone={row.retired ? 'muted' : kind.tone}
        overline='Building type'
        title={row.name}
        caption={`${row.kind_label} of ${row.origin?.name ?? 'no maker'} · drawn in epoch ${row.created_epoch}${row.retired ? ' · retired' : ''}`}
        chips={
          <>
            <Chip icon={kind.icon}>{kind.label}</Chip>
            {form && <Chip icon={form.icon}>{form.label}</Chip>}
            {row.storeys !== null && <Chip>{`${row.storeys} storeys`}</Chip>}
            {row.material && <Chip>{MATERIAL_LABEL[row.material]}</Chip>}
            <Chip icon={Building2}>{`${row.used_by} built`}</Chip>
          </>
        }
      />
      {row.description && <Muted variant='caption'>{row.description}</Muted>}
      <Preview
        look={typedLook(row.base_kind, row.form, row.storeys)}
        label={`${row.name}, ${row.kind_label.toLowerCase()}`}
        icon={kind.icon}
      />
      {row.sections.length > 0 && (
        <IntegrityDiagram
          title={`Sections set by ${row.name}`}
          parts={row.sections.map((item) => ({
            key: item.section,
            state: 'sound',
            criticality: item.criticality,
            share: item.share,
            hazard: 'none',
          }))}
          shape={buildingShape(row.form)}
          zoneOf={structureZone}
        />
      )}
      <Facts
        items={[
          ['Made by', <Ref key='origin' node={row.origin} empty='no maker' />],
          ['Capacity', `${row.capacity_pct}%`],
          ['Cost', `${row.cost_pct}%`],
          ['Upkeep', `${row.upkeep_pct}%`],
          ['Function', `${row.function_pct}%`],
          ['Staff', `${row.staff_pct}%`],
          [
            'Staffed by',
            row.staff_class ? CLASS_SPEC[row.staff_class].label : AS_KIND,
          ],
          [
            'Upkeep in',
            row.upkeep_commodity
              ? COMMODITY[row.upkeep_commodity].label
              : AS_KIND,
          ],
          [
            'Smallest place',
            row.min_tier ? SIZE_SPEC[row.min_tier].label : AS_KIND,
          ],
          ['Scale', row.scale ? SCALE_SPEC[row.scale].label : AS_KIND],
          [
            'Hands',
            row.staff_scale ? STAFF_SCALE_SPEC[row.staff_scale].label : AS_KIND,
          ],
          [
            'Ley lines',
            row.ley === null
              ? AS_KIND
              : row.ley
                ? 'draws on them'
                : 'ignores them',
          ],
        ]}
      />
      <ul className='flex min-w-0 flex-col gap-2'>
        <Held
          icon={kind.icon}
          tone={kind.tone ?? 'gold'}
          title='The whole type'
          caption='Every value of the type, held as you set it'
          removeLabel={row.retired ? 'Restore the type' : 'Retire the type'}
          editTitle='Set the type'
          note='Builders of its makers raise its kind to this type; its form and storeys set how it looks, its numbers how it works.'
          fields={[
            { key: 'name', label: 'Name of the type', kind: 'text' },
            {
              key: 'description',
              label: 'What sets it apart',
              kind: 'text',
              long: true,
            },
            {
              key: 'origin_node_id',
              label: 'Made by',
              kind: 'node',
              types: OWNER_TYPES,
              kinds: GODS,
            },
            {
              key: 'base_kind',
              label: 'Kind of structure',
              kind: 'pick',
              table: namedTable(KIND_SPEC),
            },
            {
              key: 'form',
              label: 'Building form',
              kind: 'pick',
              table: namedTable(FORM),
            },
            {
              key: 'storeys',
              label: 'Storeys',
              kind: 'number',
              min: 1,
              max: STOREYS_MAX,
            },
            {
              key: 'material',
              label: 'Material',
              kind: 'pick',
              table: MATERIAL_LABEL,
            },
            {
              key: 'staff_class',
              label: 'Staffed by',
              kind: 'pick',
              table: namedTable(CLASS_SPEC),
            },
            {
              key: 'staff_scale',
              label: 'Hands it needs',
              kind: 'pick',
              table: namedTable(STAFF_SCALE_SPEC),
            },
            {
              key: 'scale',
              label: 'Scale',
              kind: 'pick',
              table: namedTable(SCALE_SPEC),
            },
            {
              key: 'upkeep_commodity',
              label: 'Upkeep paid in',
              kind: 'pick',
              table: namedTable(COMMODITY),
            },
            {
              key: 'min_tier',
              label: 'Smallest place',
              kind: 'pick',
              table: namedTable(SIZE_SPEC),
            },
            {
              key: 'ley',
              label: 'Draws on ley lines',
              kind: 'pick',
              table: YES_NO,
            },
            {
              key: 'capacity_pct',
              label: 'Capacity (%)',
              kind: 'number',
              min: 0,
              max: PCT_MAX,
            },
            {
              key: 'cost_pct',
              label: 'Cost (%)',
              kind: 'number',
              min: 1,
              max: PCT_MAX,
            },
            {
              key: 'upkeep_pct',
              label: 'Upkeep (%)',
              kind: 'number',
              min: 0,
              max: PCT_MAX,
            },
            {
              key: 'function_pct',
              label: 'Function (%)',
              kind: 'number',
              min: 0,
              max: 300,
            },
            {
              key: 'staff_pct',
              label: 'Staff (%)',
              kind: 'number',
              min: 0,
              max: PCT_MAX,
            },
          ]}
          locked={row.locked}
          blocked={action.busy}
          onEdit={action.onEdit}
          onRemove={retire.run}
        />
      </ul>
      <Listed
        title='Sections of its own'
        items={row.sections}
        empty='It follows the common layout of its kind.'
        noun={['section', 'sections']}
        itemKey={(item) => item.section}
      >
        {(item) => <PartCard row={item} designId={row.id} blocked={blocked} />}
      </Listed>
      <AddPart row={row} blocked={blocked} />
    </div>
  )
}

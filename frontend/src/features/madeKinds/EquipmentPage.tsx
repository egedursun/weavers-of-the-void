import { Crosshair, Gem, Package, Shield, Sword, Swords } from 'lucide-react'
import { damageTypeValues, techniqueValues } from '@/api/generated/schema'
import { KpiTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held } from '@/features/collective/parts'
import { Chip, Facts } from '@/features/cosmography/parts'
import { SPAN } from '@/features/cycles/model'
import { useWorldMaterials } from '@/features/entity/economy/api'
import { COMMODITY, MATERIAL_LABEL } from '@/features/entity/economy/labels'
import { Ref } from '@/features/gatherings/parts'
import { DEVICE_EFFECTS } from '@/features/powers/labels'
import { type EquipmentModel } from './api'
import {
  EQUIPMENT_FAMILIES,
  SLOT,
  namedTable,
  sectionLabel,
  wordTable,
} from './labels'
import { OWNER_TYPES, useKindRow } from './model'
import { KindHeader } from './parts'

const FAMILIES = wordTable(EQUIPMENT_FAMILIES)
const TECHNIQUES = wordTable(techniqueValues)
const DAMAGE = wordTable(damageTypeValues)
const WORLDS = ['world'] as const
const GODS = ['son', 'creator', 'foreign_god'] as const
const YES_NO = { true: 'Yes', false: 'No' }
const LEVEL_MAX = 10
const REACH_MAX = 5

export function EquipmentPage({
  row,
  blocked = null,
}: {
  row: EquipmentModel
  blocked?: string | null
}) {
  const action = useKindRow(
    'equipment_model:edit',
    'equipment_model:delete',
    { record_id: row.id },
    blocked
  )
  const worldMaterials = useWorldMaterials(row.world_id)
  const materials = Object.fromEntries(
    (worldMaterials.data?.materials ?? []).flatMap((item) =>
      item.world_material_id === null
        ? []
        : [[String(item.world_material_id), item.label]]
    )
  )
  const slot = SLOT[row.slot]
  const armour =
    row.slot === 'armour' ||
    row.slot === 'shield' ||
    row.slot === 'helmet' ||
    row.slot === 'barding'
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <KindHeader
        icon={slot.icon}
        tone={row.retired ? 'muted' : slot.tone}
        overline='Equipment model'
        title={row.name}
        caption={`${row.family_label} of ${row.origin?.name ?? 'no maker'} · made since epoch ${row.created_epoch}${row.retired ? ' · retired' : ''}`}
        chips={
          <>
            <Chip icon={slot.icon}>{slot.label}</Chip>
            <Chip>
              {row.material_name ??
                (row.material
                  ? MATERIAL_LABEL[row.material]
                  : 'Common material')}
            </Chip>
            <Chip icon={Package}>{`${row.stored} in store`}</Chip>
            <Chip icon={Swords}>{`${row.carried} carried`}</Chip>
            <Chip icon={Gem}>{`Renown ${row.renown}`}</Chip>
          </>
        }
      />
      {row.description && <Muted variant='caption'>{row.description}</Muted>}
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2 @2xl/tiles:grid-cols-4'>
          <KpiTile
            label='Quality'
            value={row.quality}
            icon={Gem}
            tone='gold'
            meter={{ value: row.quality, max: SPAN, label: 'Quality' }}
          />
          {armour ? (
            <KpiTile
              label='Protection'
              value={row.protection}
              icon={Shield}
              tone='info'
              meter={{ value: row.protection, max: SPAN, label: 'Protection' }}
            />
          ) : (
            <KpiTile
              label='Damage'
              value={row.damage}
              icon={Sword}
              tone='danger'
              meter={{ value: row.damage, max: SPAN, label: 'Damage' }}
            />
          )}
          <KpiTile
            label='Piercing'
            value={row.piercing}
            icon={Crosshair}
            tone='warning'
            meter={{ value: row.piercing, max: SPAN, label: 'Piercing' }}
          />
          <KpiTile
            label='Coverage'
            value={row.coverage}
            icon={Shield}
            tone='verdigris'
            meter={{ value: row.coverage, max: SPAN, label: 'Coverage' }}
          />
        </div>
      </div>
      <Facts
        items={[
          [
            'Damage and kind',
            `${row.damage} · ${sectionLabel(row.damage_type).toLowerCase()}`,
          ],
          [
            'Reach, rate and accuracy',
            `${row.reach} · ${row.rate} · ${row.accuracy}`,
          ],
          [
            'Ammunition',
            row.ammunition ? COMMODITY[row.ammunition].label : 'none',
          ],
          ['Crew to work it', row.crew],
          ['Weight and cost', `${row.weight} · ${row.cost}`],
          [
            'Knowledge it needs',
            `level ${row.tech_level}${row.technique ? `, ${sectionLabel(row.technique).toLowerCase()}` : ''}${row.power_effect ? `, ${DEVICE_EFFECTS[row.power_effect].label.toLowerCase()}` : ''}`,
          ],
          ['Made by', <Ref key='origin' node={row.origin} empty='no maker' />],
          [
            'Improves on',
            row.parent_model_id !== null ? 'an earlier model' : 'none',
          ],
        ]}
      />
      <ul className='flex min-w-0 flex-col gap-2'>
        <Held
          icon={slot.icon}
          tone={slot.tone}
          title='The whole model'
          caption='Every value of the model, held as you set it'
          removeLabel='Forget the model'
          editTitle='Set the model'
          note='Its family and material set what it does; its makers produce it for its soldiers and vehicles.'
          fields={[
            { key: 'name', label: 'Name of the model', kind: 'text' },
            {
              key: 'description',
              label: 'What sets it apart',
              kind: 'text',
              long: true,
            },
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
              key: 'slot',
              label: 'Where it is carried',
              kind: 'pick',
              table: namedTable(SLOT),
            },
            { key: 'family', label: 'Family', kind: 'pick', table: FAMILIES },
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
              key: 'quality',
              label: 'Quality',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
            {
              key: 'technique',
              label: 'Technique it needs',
              kind: 'pick',
              table: TECHNIQUES,
            },
            {
              key: 'tech_level',
              label: 'Knowledge it needs',
              kind: 'number',
              min: 0,
              max: LEVEL_MAX,
            },
            {
              key: 'power_effect',
              label: 'What it does to powers',
              kind: 'pick',
              table: table(DEVICE_EFFECTS),
            },
            {
              key: 'damage',
              label: 'Damage',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
            {
              key: 'piercing',
              label: 'Piercing',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
            {
              key: 'reach',
              label: 'Reach',
              kind: 'number',
              min: 0,
              max: REACH_MAX,
            },
            { key: 'rate', label: 'Rate', kind: 'number', min: 0, max: SPAN },
            {
              key: 'accuracy',
              label: 'Accuracy',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
            {
              key: 'damage_type',
              label: 'Kind of damage',
              kind: 'pick',
              table: DAMAGE,
            },
            {
              key: 'ammunition',
              label: 'Ammunition',
              kind: 'pick',
              table: namedTable(COMMODITY),
            },
            {
              key: 'crew',
              label: 'Crew to work it',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
            {
              key: 'protection',
              label: 'Protection',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
            {
              key: 'coverage',
              label: 'Coverage',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
            {
              key: 'weight',
              label: 'Weight',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
            { key: 'cost', label: 'Cost', kind: 'number', min: 0 },
            {
              key: 'renown',
              label: 'Renown',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
            { key: 'retired', label: 'Retired', kind: 'pick', table: YES_NO },
          ]}
          locked={row.locked}
          blocked={action.busy}
          onEdit={action.onEdit}
          onRemove={action.onRemove}
        />
      </ul>
    </div>
  )
}

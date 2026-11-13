import { useState } from 'react'
import {
  Gauge,
  Plus,
  Shield,
  Sword,
  Swords,
  Target,
  Trash2,
  Users,
} from 'lucide-react'
import { techniqueValues, unitKindValues } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { KpiTile, PagedList } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { Held, Listed } from '@/features/collective/parts'
import { Chip, Facts, ForgeCard } from '@/features/cosmography/parts'
import { SPAN } from '@/features/cycles/model'
import { why } from '@/features/dominion/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { CLASS_SPEC } from '@/features/entity/society/labels'
import { Ref } from '@/features/gatherings/parts'
import {
  ARMOUR,
  DOCTRINE,
  FAMILY,
  FORMATION,
  SHIELD,
  unitIcon,
} from '@/features/wars/military/labels'
import {
  type EquipmentModel,
  type UnitType,
  type VehicleType,
  useLever,
} from './api'
import {
  SLOT,
  familyLabel,
  namedTable,
  sectionLabel,
  wordTable,
} from './labels'
import { OWNER_TYPES, useKindRow, useKindStep } from './model'
import { KindHeader } from './parts'

type Loadout = UnitType['loadout'][number]

const TECHNIQUES = wordTable(techniqueValues)
const ROLES = wordTable(unitKindValues)
const WORLDS = ['world'] as const
const GODS = ['son', 'creator', 'foreign_god'] as const
const MOUNTS = ['species'] as const
const YES_NO = { true: 'Yes', false: 'No' }
const PIECES_MAX = 10
const REACH_MAX = 5
const VOLLEYS_MAX = 6
const EPOCHS_MAX = 20

function LoadoutRow({
  row,
  designId,
  blocked,
}: {
  row: Loadout
  designId: number
  blocked: string | null
}) {
  const remove = useKindStep(
    'unit_loadout:delete',
    { design_id: designId, model_id: row.model_id },
    blocked,
    'The piece is taken from the loadout'
  )
  const [count, setCount] = useState(String(row.count))
  const set = useLever(
    'unit_loadout:set',
    (_: void) => ({
      design_id: designId,
      model_id: row.model_id,
      count: Number(count),
    }),
    'The loadout is set'
  )
  const busy = why(remove.busy, set.isPending)
  const slot = SLOT[row.slot]
  return (
    <li className='flex min-w-0 flex-wrap items-end gap-2 rounded-lg border bg-muted/30 p-2'>
      <Chip icon={slot.icon}>{slot.label}</Chip>
      <Muted
        as='span'
        variant='caption'
      >{`${row.model_name}, ${familyLabel(row.family).toLowerCase()}`}</Muted>
      <NumberField
        label='Pieces each'
        value={count}
        min={1}
        max={PIECES_MAX}
        blocked={busy}
        onChange={setCount}
      />
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => set.mutate()}
      >
        Set
      </Button>
      <Button
        size='sm'
        variant='ghost'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={remove.run}
      >
        <Trash2 />
        Take it away
      </Button>
    </li>
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
    'unit_technique:delete',
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
  models,
  blocked,
}: {
  row: UnitType
  models: EquipmentModel[]
  blocked: string | null
}) {
  const [model, setModel] = useState('')
  const [technique, setTechnique] = useState('')
  const addPiece = useLever(
    'unit_loadout:set',
    (_: void) => ({ design_id: row.id, model_id: Number(model), count: 1 }),
    'The piece joins the loadout'
  )
  const addTechnique = useLever(
    'unit_technique:add',
    (_: void) => ({ design_id: row.id, technique: technique as never }),
    'The technique is now needed'
  )
  const busy = why(blocked, addPiece.isPending, addTechnique.isPending)
  const carried = new Set(row.loadout.map((item) => item.model_id))
  const pieces = Object.fromEntries(
    models
      .filter((item) => item.slot !== 'vehicle_weapon' && !carried.has(item.id))
      .map((item) => [String(item.id), `${item.name} (${item.family_label})`])
  )
  const needed = Object.fromEntries(
    Object.entries(TECHNIQUES).filter(
      ([key]) => !row.techniques.includes(key as never)
    )
  )
  return (
    <ForgeCard
      icon={Swords}
      tone='danger'
      title='Equip and train'
      note='Add a weapon, armour or shield model its soldiers carry, or a technique their makers must know before raising them.'
      columns={2}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={(busy ?? (model ? null : 'Pick a model')) !== null}
            disabledReason={busy ?? (model ? undefined : 'Pick a model')}
            onClick={() => addPiece.mutate()}
          >
            <Plus />
            Add to the loadout
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
        label='Model'
        value={model}
        table={pieces}
        blocked={
          Object.keys(pieces).length
            ? busy
            : 'No other model of this world can be carried'
        }
        onPick={setModel}
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

export function UnitTypePage({
  row,
  models,
  vehicles,
  blocked = null,
}: {
  row: UnitType
  models: EquipmentModel[]
  vehicles: VehicleType[]
  blocked?: string | null
}) {
  const action = useKindRow(
    'unit_type:edit',
    'unit_type:delete',
    { record_id: row.id },
    blocked
  )
  const family = FAMILY[row.family]
  const icon = unitIcon(row.base_kind, family.icon)
  const vehicleTable = Object.fromEntries(
    vehicles.map((item) => [String(item.id), item.name])
  )
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <KindHeader
        icon={icon}
        tone={row.retired ? 'muted' : family.tone}
        overline='Kind of soldier'
        title={row.name}
        caption={`${row.role_label} of ${row.origin?.name ?? 'no maker'} · raised since epoch ${row.created_epoch}${row.retired ? ' · retired' : ''}`}
        chips={
          <>
            <Chip icon={family.icon}>{family.label}</Chip>
            {row.doctrine && (
              <Chip icon={DOCTRINE[row.doctrine].icon}>
                {DOCTRINE[row.doctrine].label}
              </Chip>
            )}
            {row.formation && (
              <Chip icon={FORMATION[row.formation].icon}>
                {FORMATION[row.formation].label}
              </Chip>
            )}
            <Chip icon={Users}>{`${row.fielded} in the field`}</Chip>
            {row.flying && <Chip>Flies</Chip>}
            {row.counters_charge && <Chip>Stands against charges</Chip>}
          </>
        }
      />
      {row.description && <Muted variant='caption'>{row.description}</Muted>}
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2 @2xl/tiles:grid-cols-4'>
          <KpiTile
            label='Melee'
            value={row.melee}
            icon={Sword}
            tone='danger'
            meter={{ value: row.melee, max: SPAN, label: 'Melee' }}
          />
          <KpiTile
            label='Missile'
            value={row.missile}
            icon={Target}
            tone='info'
            meter={{ value: row.missile, max: SPAN, label: 'Missile' }}
          />
          <KpiTile
            label='Defence'
            value={row.defence}
            icon={Shield}
            tone='gold'
            meter={{ value: row.defence, max: SPAN, label: 'Defence' }}
          />
          <KpiTile
            label='Speed'
            value={row.speed}
            icon={Gauge}
            tone='verdigris'
            meter={{ value: row.speed, max: SPAN, label: 'Speed' }}
          />
        </div>
      </div>
      <Facts
        items={[
          [
            'Armour and shield',
            `${ARMOUR[row.armour]?.label ?? row.armour} · ${SHIELD[row.shield]?.label ?? row.shield}`,
          ],
          ['Reach and volleys', `${row.reach} · ${row.volleys}`],
          ['Accuracy and piercing', `${row.accuracy} · ${row.piercing}`],
          ['Discipline', row.discipline],
          ['Terror it strikes', row.terror],
          ['Mass', row.mass],
          ['Cost and upkeep', `${row.cost} · ${row.upkeep}`],
          ['Epochs of training', row.training_epochs],
          [
            'Drawn from',
            row.social_class ? CLASS_SPEC[row.social_class].label : 'any class',
          ],
          [
            'Rides',
            <Ref key='mount' node={row.mount_species} empty='nothing' />,
          ],
          [
            'Crews',
            row.vehicle_design_name
              ? `${row.vehicle_design_name}, ${row.crew_per_vehicle} to a vehicle`
              : 'no vehicle',
          ],
          ['Made by', <Ref key='origin' node={row.origin} empty='no maker' />],
          ['Fielded by', <Ref key='owner' node={row.owner} empty='no realm' />],
          [
            'Grew from',
            row.parent_design_id !== null ? 'an earlier kind' : 'its role',
          ],
        ]}
      />
      <ul className='flex min-w-0 flex-col gap-2'>
        <Held
          icon={icon}
          tone='danger'
          title='The whole kind'
          caption='Every value of the kind, held as you set it'
          removeLabel='Strike the kind'
          editTitle='Set the kind of soldier'
          note='Its role sets its place in battle; its loadout, doctrine, formation and discipline set how it fights.'
          fields={[
            { key: 'name', label: 'Name of the kind', kind: 'text' },
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
              key: 'owner_entity_id',
              label: 'Fielded by',
              kind: 'node',
              types: OWNER_TYPES,
            },
            {
              key: 'base_kind',
              label: 'Battlefield role',
              kind: 'pick',
              table: ROLES,
            },
            {
              key: 'family',
              label: 'Family',
              kind: 'pick',
              table: namedTable(FAMILY),
            },
            { key: 'melee', label: 'Melee', kind: 'number', min: 0, max: SPAN },
            {
              key: 'missile',
              label: 'Missile',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
            {
              key: 'defence',
              label: 'Defence',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
            { key: 'speed', label: 'Speed', kind: 'number', min: 0, max: SPAN },
            { key: 'mass', label: 'Mass', kind: 'number', min: 0, max: SPAN },
            { key: 'cost', label: 'Cost', kind: 'number', min: 0 },
            { key: 'upkeep', label: 'Upkeep', kind: 'number', min: 0 },
            {
              key: 'armour',
              label: 'Armour',
              kind: 'pick',
              table: namedTable(ARMOUR),
            },
            {
              key: 'shield',
              label: 'Shield',
              kind: 'pick',
              table: namedTable(SHIELD),
            },
            {
              key: 'terror',
              label: 'Terror',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
            {
              key: 'counters_charge',
              label: 'Stands against charges',
              kind: 'pick',
              table: YES_NO,
            },
            { key: 'flying', label: 'Flies', kind: 'pick', table: YES_NO },
            {
              key: 'social_class',
              label: 'Drawn from',
              kind: 'pick',
              table: namedTable(CLASS_SPEC),
            },
            { key: 'retired', label: 'Retired', kind: 'pick', table: YES_NO },
            {
              key: 'reach',
              label: 'Reach',
              kind: 'number',
              min: 0,
              max: REACH_MAX,
            },
            {
              key: 'volleys',
              label: 'Volleys',
              kind: 'number',
              min: 0,
              max: VOLLEYS_MAX,
            },
            {
              key: 'accuracy',
              label: 'Accuracy',
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
              key: 'doctrine',
              label: 'Doctrine',
              kind: 'pick',
              table: namedTable(DOCTRINE),
            },
            {
              key: 'formation',
              label: 'Formation',
              kind: 'pick',
              table: namedTable(FORMATION),
            },
            {
              key: 'discipline',
              label: 'Discipline',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
            {
              key: 'training_epochs',
              label: 'Epochs of training',
              kind: 'number',
              min: 0,
              max: EPOCHS_MAX,
            },
            {
              key: 'mount_species_id',
              label: 'Rides',
              kind: 'node',
              types: MOUNTS,
            },
            {
              key: 'vehicle_design_id',
              label: 'Crews the vehicle type',
              kind: 'pick',
              table: vehicleTable,
            },
            {
              key: 'crew_per_vehicle',
              label: 'Crew to a vehicle',
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
      </ul>
      <Listed
        title='Loadout'
        items={row.loadout}
        empty='Its soldiers carry no model of their own; they fight with what their role gives them.'
        noun={['piece', 'pieces']}
        itemKey={(item) => item.model_id}
      >
        {(item) => (
          <LoadoutRow row={item} designId={row.id} blocked={blocked} />
        )}
      </Listed>
      <Label variant='overline'>{`Techniques its makers must know (${row.techniques.length})`}</Label>
      {row.techniques.length === 0 ? (
        <Muted variant='caption'>It needs no technique to raise.</Muted>
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
      <Additions row={row} models={models} blocked={blocked} />
    </div>
  )
}

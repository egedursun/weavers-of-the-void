import { useState } from 'react'
import {
  Archive,
  Coins,
  Crosshair,
  Drama,
  Feather,
  Footprints,
  Hammer,
  PencilRuler,
  Shield,
  Swords,
  Weight,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EmptyState, Medallion, StatBar } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useUnitKinds } from './api'
import { Held, RecordButtons, TextField } from './controls'
import { SOCIAL_CLASS, type RecordRow, nameOf, useRecords } from './depth'
import {
  ARMOUR,
  FAMILY,
  PERCENT,
  SHIELD,
  UNIT_ICON,
  busyOf,
  cardGrid,
} from './labels'
import {
  Adjust,
  ChoiceField,
  FieldGrid,
  NumberField,
  Panel,
  Plain,
  Tag,
  ToggleField,
} from './parts'
import {
  type Values,
  numbersOf,
  useRecordActions,
  useRecordCreate,
} from './recordHooks'

const NUMBERS = [
  'melee',
  'missile',
  'defence',
  'speed',
  'mass',
  'cost',
  'upkeep',
  'terror',
] as const
const PERCENT_NUMBERS = new Set(['melee', 'missile', 'defence', 'terror'])
const NUMBER_ICON: Record<string, typeof Swords> = {
  melee: Swords,
  missile: Crosshair,
  defence: Shield,
  speed: Footprints,
  mass: Weight,
  cost: Coins,
  upkeep: Coins,
  terror: Drama,
}
const NUMBER_LABEL: Record<string, string> = {
  melee: 'Hand to hand',
  missile: 'At range',
  defence: 'Holding',
  speed: 'Speed',
  mass: 'Weight of charge',
  cost: 'Cost to raise',
  upkeep: 'Upkeep',
  terror: 'Terror',
}
const COUNTERS = {
  label: 'Breaks charges',
  icon: Shield,
  tone: 'info' as const,
}
const FLYING = {
  label: 'Takes wing',
  icon: Feather,
  tone: 'verdigris' as const,
}

function useKindTable() {
  const kinds = useUnitKinds()
  const table = Object.fromEntries(
    (kinds.data ?? []).map((spec) => [
      spec.kind,
      {
        label: spec.label,
        icon: UNIT_ICON[spec.kind] ?? Swords,
        tone: FAMILY[spec.family]?.tone ?? ('muted' as const),
      },
    ])
  )
  return { table, specs: kinds.data ?? [] }
}

function DesignFields({
  value,
  onChange,
  blocked,
}: {
  value: (key: string) => unknown
  onChange: (key: string, next: unknown) => void
  blocked: string | null
}) {
  const { table } = useKindTable()
  return (
    <>
      <FieldGrid>
        <TextField
          label='Name'
          icon={PencilRuler}
          value={String(value('name') ?? '')}
          onChange={(next) => onChange('name', next)}
        />
        <ChoiceField
          label='Grown from'
          icon={Swords}
          value={String(value('base_kind') ?? 'levy')}
          table={table}
          blocked={blocked}
          onPick={(next) => onChange('base_kind', next)}
        />
        <ChoiceField
          label='Family'
          icon={Swords}
          value={String(value('family') ?? 'infantry')}
          table={FAMILY}
          blocked={blocked}
          onPick={(next) => onChange('family', next)}
        />
        <ChoiceField
          label='Armour'
          icon={Shield}
          value={String(value('armour') ?? 'none')}
          table={ARMOUR}
          blocked={blocked}
          onPick={(next) => onChange('armour', next)}
        />
        <ChoiceField
          label='Shield'
          icon={Shield}
          value={String(value('shield') ?? 'none')}
          table={SHIELD}
          blocked={blocked}
          onPick={(next) => onChange('shield', next)}
        />
        <ChoiceField
          label='Drawn from'
          icon={Hammer}
          value={String(value('social_class') ?? 'warrior')}
          table={SOCIAL_CLASS}
          blocked={blocked}
          onPick={(next) => onChange('social_class', next)}
        />
        {NUMBERS.map((key) => (
          <NumberField
            key={key}
            label={NUMBER_LABEL[key]}
            icon={NUMBER_ICON[key]}
            value={String(value(key) ?? 0)}
            max={PERCENT_NUMBERS.has(key) ? PERCENT : undefined}
            onChange={(next) => onChange(key, next)}
          />
        ))}
      </FieldGrid>
      <FieldGrid>
        <ToggleField
          item={COUNTERS}
          checked={Boolean(value('counters_charge'))}
          disabled={blocked !== null}
          onChange={(next) => onChange('counters_charge', next)}
        />
        <ToggleField
          item={FLYING}
          checked={Boolean(value('flying'))}
          disabled={blocked !== null}
          onChange={(next) => onChange('flying', next)}
        />
      </FieldGrid>
    </>
  )
}

function DesignCard({
  row,
  ownerId,
  blocked,
}: {
  row: RecordRow
  ownerId: number
  blocked: string | null
}) {
  const actions = useRecordActions('unit_design', row.id, ownerId)
  const [draft, setDraft] = useState<Values>({})
  const value = (key: string) => (key in draft ? draft[key] : row.values[key])
  const kind = String(row.values.base_kind)
  const family = nameOf(FAMILY, String(row.values.family))
  const retired = Boolean(row.values.retired)
  return (
    <li
      data-surface='UnitDesign'
      className='flex min-w-0 flex-col gap-3 rounded-xl border bg-background p-3'
    >
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion
          icon={UNIT_ICON[kind] ?? family.icon}
          tone={retired ? 'muted' : family.tone}
        />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <Text as='span' weight='semibold' truncate>
            {String(row.values.name)}
          </Text>
          <Muted as='span' variant='caption' truncate>
            {`${kind.replaceAll('_', ' ')} reforged · since epoch ${String(row.values.created_epoch)}`}
          </Muted>
        </div>
        <Held locked={row.locked} />
      </div>
      <div className='flex min-w-0 flex-wrap gap-1'>
        <Tag item={family} />
        <Tag item={nameOf(ARMOUR, String(row.values.armour))} />
        <Tag item={nameOf(SHIELD, String(row.values.shield))} />
        {Boolean(row.values.counters_charge) && <Tag item={COUNTERS} />}
        {Boolean(row.values.flying) && <Tag item={FLYING} />}
        {retired && <Plain icon={Archive}>Retired</Plain>}
        <Plain
          icon={Coins}
        >{`${String(row.values.cost)} to raise · ${String(row.values.upkeep)} upkeep`}</Plain>
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-1.5 @sm/mil:grid-cols-2'>
        {(['melee', 'missile', 'defence', 'terror'] as const).map((key) => (
          <StatBar
            key={key}
            label={NUMBER_LABEL[key]}
            icon={NUMBER_ICON[key]}
            value={Number(row.values[key] ?? 0)}
            max={PERCENT}
            tone={key === 'terror' ? 'warning' : 'info'}
          />
        ))}
      </div>
      <div className='mt-auto flex min-w-0 flex-col gap-2'>
        <Adjust
          title='Reshape the design'
          note='Every stat, gear and calling of this kind of soldier; armies muster it where their doctrine and stores allow.'
        >
          <DesignFields
            value={value}
            onChange={(key, next) => setDraft({ ...draft, [key]: next })}
            blocked={blocked}
          />
          <FieldGrid>
            <ToggleField
              item={{
                label: 'Retired from the musters',
                icon: Archive,
                tone: 'muted',
              }}
              checked={Boolean(value('retired'))}
              disabled={blocked !== null}
              onChange={(next) => setDraft({ ...draft, retired: next })}
            />
          </FieldGrid>
          <RecordButtons
            actions={actions}
            values={numbersOf(draft, NUMBERS)}
            locked={row.locked}
            blocked={blocked}
            removeLabel='Forget the design'
          />
        </Adjust>
      </div>
    </li>
  )
}

function NewDesign({
  ownerId,
  blocked,
}: {
  ownerId: number
  blocked: string | null
}) {
  const create = useRecordCreate('unit_design', ownerId)
  const { specs } = useKindTable()
  const [draft, setDraft] = useState<Values>({
    base_kind: 'spearmen',
    armour: 'none',
    shield: 'none',
    social_class: 'warrior',
  })
  const base = specs.find((spec) => spec.kind === draft.base_kind)
  const value = (key: string) =>
    key in draft
      ? draft[key]
      : base
        ? (base as Record<string, unknown>)[key]
        : undefined
  const busy = busyOf(blocked, create.isPending)
  const name = String(draft.name ?? '').trim()
  const seeded = Object.fromEntries(
    NUMBERS.map((key) => [key, value(key) ?? 0])
  )
  return (
    <Adjust
      title='Devise a new kind of soldier'
      note='Grow it from a known unit and change what you will; its stats start from that unit.'
      label='Devise a unit'
    >
      <DesignFields
        value={value}
        onChange={(key, next) => setDraft({ ...draft, [key]: next })}
        blocked={blocked}
      />
      <Button
        size='sm'
        className='self-start'
        disabled={busy !== null || !name}
        disabledReason={busy ?? (!name ? 'Name the soldiers first' : undefined)}
        onClick={() =>
          create.mutate(
            numbersOf(
              {
                ...seeded,
                family: base?.family ?? 'infantry',
                ...draft,
                name,
                owner_entity_id: ownerId,
              },
              NUMBERS
            )
          )
        }
      >
        <PencilRuler />
        Devise
      </Button>
    </Adjust>
  )
}

export function UnitDesigns({
  ownerId,
  blocked,
}: {
  ownerId: number
  blocked: string | null
}) {
  const designs = useRecords('unit_design', ownerId)
  const rows = designs.data?.rows ?? []
  return (
    <Panel
      title='Unit designs'
      icon={PencilRuler}
      tone='gold'
      count={rows.length}
      hint='Its own kinds of soldier; musters field them by doctrine and stores'
    >
      <div data-surface='UnitDesigns' className='flex min-w-0 flex-col gap-3'>
        {rows.length === 0 ? (
          <EmptyState
            icon={PencilRuler}
            title='No designs of its own'
            description='Its armies muster the common kinds until it devises its own.'
          />
        ) : (
          <ul className={cardGrid(rows.length)}>
            {rows.map((row) => (
              <DesignCard
                key={row.id}
                row={row}
                ownerId={ownerId}
                blocked={blocked}
              />
            ))}
          </ul>
        )}
        <NewDesign ownerId={ownerId} blocked={blocked} />
      </div>
    </Panel>
  )
}

import { useId, useMemo, useState } from 'react'
import {
  Anchor,
  Building,
  Coins,
  Compass,
  Construction,
  Flame,
  HardHat,
  HeartPulse,
  Landmark,
  Layers,
  Lock,
  PenTool,
  Plus,
  RotateCcw,
  Ruler,
  Shield,
  Sparkles,
  Trash2,
  TriangleAlert,
  Users,
  Wrench,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  EmptyState,
  KpiTile,
  Medallion,
  MiniStat,
  Section,
  StatBar,
  Paged,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useSons } from '@/features/pantheon/api'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  MATERIAL_KINDS,
  MATERIAL_LABEL,
  type MaterialKind,
} from '../economy/labels'
import { AESTHETIC_SPEC, CLASS_SPEC, SIZE_SPEC, type Spec } from './labels'
import {
  AdjustPanel,
  ChoiceEditor,
  EditorGroup,
  FlagEditor,
  HeldStrip,
  IconPicker,
  type NumberField,
  NumberEditor,
  Panel,
} from './parts'
import { structureKeys, useHostStructures, useStructure } from './structureApi'
import {
  BUILDER_SPEC,
  type DesignView,
  DESIGN_FIELD,
  GROUP_ORDER,
  GROUP_SPEC,
  KIND_SPEC,
  type KindOption,
  SCALE_SPEC,
  STAFF_SCALE_SPEC,
  STATE_SPEC,
  type StructureKind,
  type StructureView,
  structureField,
} from './structureLabels'
import { capacityText, raising, standing } from './structureModel'
import {
  AmountForm,
  FunctionBreakdown,
  GroupHeader,
  StaffLine,
  StructureCard,
  UpkeepLine,
} from './structureParts'
import { METER_TONE, WORKING, goodTone } from './tones'

type Value = number | string | boolean | null
const PERCENT = 100
const LEVEL_MAX = 5
const HUGE = 1000000000
const NONE = 'none'
const DESIGN_PCT = [
  { key: 'capacity_pct', icon: Layers, max: 1000 },
  { key: 'cost_pct', icon: HardHat, max: 1000 },
  { key: 'upkeep_pct', icon: Coins, max: 1000 },
  { key: 'function_pct', icon: HeartPulse, max: 300 },
  { key: 'staff_pct', icon: Users, max: 1000 },
] as const

function kindTable(options: KindOption[]): Record<string, Spec> {
  return Object.fromEntries(
    options.map((option) => [
      option.kind,
      {
        ...KIND_SPEC[option.kind],
        label: option.allowed
          ? `${KIND_SPEC[option.kind].label} (${formatInteger(option.cost)} labour)`
          : `${KIND_SPEC[option.kind].label} (needs a ${SIZE_SPEC[option.min_tier].label.toLowerCase()})`,
      },
    ])
  )
}

const MATERIAL_TABLE: Record<string, Spec> = Object.fromEntries(
  MATERIAL_KINDS.map((kind) => [
    kind,
    { label: MATERIAL_LABEL[kind], icon: Building, tone: 'muted' as const },
  ])
)

function designTable(
  designs: DesignView[],
  kind: StructureKind
): Record<string, Spec> {
  return {
    [NONE]: { label: 'The common plan', icon: Ruler, tone: 'muted' },
    ...Object.fromEntries(
      designs
        .filter((design) => design.base_kind === kind && !design.retired)
        .map((design) => [
          String(design.id),
          { label: design.name, icon: PenTool, tone: 'gold' as const },
        ])
    ),
  }
}

function SonSelect({
  value,
  onChange,
  blocked,
}: {
  value: number | null
  onChange: (value: number | null) => void
  blocked: string | null
}) {
  const sons = useSons()
  const id = useId()
  return (
    <div className='flex min-w-0 flex-col gap-1.5'>
      <FieldLabel htmlFor={id}>Dedicated to</FieldLabel>
      <Select
        value={value === null ? NONE : String(value)}
        onValueChange={(next) => onChange(next === NONE ? null : Number(next))}
        disabled={blocked !== null}
      >
        <SelectTrigger id={id} aria-label='Dedicated to' className='w-full'>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={NONE}>No god</SelectItem>
          {(sons.data ?? []).map((entry) => (
            <SelectItem key={entry.son.id} value={String(entry.son.id)}>
              {entry.son.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

function CommissionPanel({
  hostId,
  options,
  designs,
  full,
  blocked,
}: {
  hostId: number
  options: KindOption[]
  designs: DesignView[]
  full: boolean
  blocked: string | null
}) {
  const [kind, setKind] = useState<StructureKind>(
    options.find((option) => option.allowed)?.kind ?? 'shrine'
  )
  const [level, setLevel] = useState('1')
  const [material, setMaterial] = useState<string>('stone')
  const [design, setDesign] = useState<string>(NONE)
  const [name, setName] = useState('')
  const [architect, setArchitect] = useState<number | null>(null)
  const [son, setSon] = useState<number | null>(null)
  const [funds, setFunds] = useState('0')
  const option = options.find((item) => item.kind === kind)
  const commission = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/structure:commission', {
          body: {
            site_id: hostId,
            kind,
            level: Number(level),
            material: material as MaterialKind,
            design_id: design === NONE ? null : Number(design),
            name: name.trim() || null,
            architect_id: architect,
            dedicated_son_id: son,
            funds: Number(funds) || 0,
          },
        })
      ),
    success: 'The builders set to work',
  })
  const levelValue = Number(level)
  const problem = full
    ? 'Every slot is taken; raze or let one fall first.'
    : option && !option.allowed
      ? `It needs a ${SIZE_SPEC[option.min_tier].label.toLowerCase()} or larger.`
      : !Number.isInteger(levelValue) ||
          levelValue < 1 ||
          levelValue > LEVEL_MAX
        ? `Level runs from 1 to ${LEVEL_MAX}.`
        : null
  const reason = blocked ?? problem ?? (commission.isPending ? WORKING : null)
  return (
    <Panel
      title='Commission a structure'
      icon={Construction}
      tone='gold'
      hint='Choose what to raise; its builders, stone and coin raise it over the coming ages'
      wide
    >
      <div
        data-surface='CommissionStructure'
        className='grid min-w-0 grid-cols-1 gap-3 @md:grid-cols-2 @xl:grid-cols-3'
      >
        <IconPicker
          label='Kind'
          value={kind}
          table={kindTable(options)}
          blocked={blocked}
          onPick={(next) => {
            setKind(next as StructureKind)
            setDesign(NONE)
          }}
        />
        <IconPicker
          label='Design'
          value={design}
          table={designTable(designs, kind)}
          blocked={blocked}
          onPick={setDesign}
        />
        <IconPicker
          label='Material'
          value={material}
          table={MATERIAL_TABLE}
          blocked={blocked}
          onPick={setMaterial}
        />
        <div className='flex min-w-0 flex-col gap-1.5'>
          <FieldLabel htmlFor={`level-${hostId}`}>Level</FieldLabel>
          <Input
            id={`level-${hostId}`}
            type='number'
            min={1}
            max={LEVEL_MAX}
            value={level}
            onChange={(event) => setLevel(event.target.value)}
          />
        </div>
        <div className='flex min-w-0 flex-col gap-1.5'>
          <FieldLabel htmlFor={`name-${hostId}`}>Name</FieldLabel>
          <Input
            id={`name-${hostId}`}
            placeholder='Leave empty to let its builders name it'
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </div>
        <div className='flex min-w-0 flex-col gap-1.5'>
          <FieldLabel htmlFor={`funds-${hostId}`}>Gift of coin</FieldLabel>
          <Input
            id={`funds-${hostId}`}
            type='number'
            min={0}
            value={funds}
            onChange={(event) => setFunds(event.target.value)}
          />
        </div>
        <div className='flex min-w-0 flex-col gap-1.5'>
          <FieldLabel>Architect</FieldLabel>
          <EntityPicker
            types={['mortal']}
            value={architect}
            onChange={setArchitect}
            placeholder='The best engineer at hand'
          />
        </div>
        <SonSelect value={son} onChange={setSon} blocked={blocked} />
      </div>
      {option && (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Badge size='sm' variant='secondary'>
            <SCALE_SPEC_ICON scale={option.scale} />
            {SCALE_SPEC[option.scale].label}
          </Badge>
          <Badge size='sm' variant='secondary'>
            {option.staff_class
              ? `${STAFF_SCALE_SPEC[option.staff_scale].label} of ${CLASS_SPEC[option.staff_class].label.toLowerCase()}`
              : 'No staff'}
          </Badge>
          <Muted as='span' variant='caption'>
            {KIND_SPEC[kind].hint}
          </Muted>
        </div>
      )}
      <div className='flex min-w-0 justify-end'>
        <Button
          disabled={reason !== null}
          disabledReason={reason ?? undefined}
          onClick={() => commission.mutate(undefined)}
        >
          <Plus />
          Commission it
        </Button>
      </div>
    </Panel>
  )
}

function SCALE_SPEC_ICON({ scale }: { scale: KindOption['scale'] }) {
  const Icon = SCALE_SPEC[scale].icon
  return <Icon aria-hidden='true' />
}

function DesignCard({
  design,
  blocked,
}: {
  design: DesignView
  blocked: string | null
}) {
  const kind = KIND_SPEC[design.base_kind]
  const invalidate = [structureKeys.designs(design.world_id)]
  const edit = useGodAction({
    run: ({
      values,
      release,
    }: {
      values: Record<string, Value>
      release: string[]
    }) =>
      unwrap(
        api.POST('/api/actions/structure_design:edit', {
          body: { design_id: design.id, values, release },
        })
      ),
    invalidate,
  })
  const retire = useGodAction({
    run: (retired: boolean) =>
      unwrap(
        api.POST('/api/actions/structure_design:retire', {
          body: { design_id: design.id, retired },
        })
      ),
    invalidate,
  })
  const busy = blocked ?? (edit.isPending || retire.isPending ? WORKING : null)
  const id = useId()
  return (
    <li className='flex min-w-0 flex-col gap-3 rounded-lg border bg-card p-3'>
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion
          icon={PenTool}
          tone={design.retired ? 'muted' : 'gold'}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='medium' truncate>
            {design.name}
          </Text>
          <Muted as='span' variant='caption' truncate>
            {`A kind of ${kind.label.toLowerCase()}; ${design.used_by} built to it`}
          </Muted>
        </div>
        {design.retired && (
          <Badge size='sm' variant='secondary'>
            Retired
          </Badge>
        )}
      </div>
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        {DESIGN_PCT.map((item) => (
          <Badge key={item.key} size='sm' variant='outline'>
            {`${DESIGN_FIELD[item.key]} ${design[item.key]}%`}
          </Badge>
        ))}
      </div>
      <AdjustPanel
        title='Redraw the design'
        note='Every number is held as you set it until you release it.'
      >
        <EditorGroup title='Proportions' icon={Ruler}>
          {DESIGN_PCT.map((item) => (
            <NumberEditor
              key={`${item.key}-${design[item.key]}`}
              id={id}
              field={{
                key: item.key,
                label: DESIGN_FIELD[item.key],
                icon: item.icon,
                value: design[item.key],
                min: item.key === 'cost_pct' ? 1 : 0,
                max: item.max,
                unit: '% of the common plan',
              }}
              held={design.locked.includes(item.key)}
              blocked={busy}
              pending={edit.isPending}
              onSet={(value) =>
                edit.mutate({ values: { [item.key]: value }, release: [] })
              }
            />
          ))}
        </EditorGroup>
        <EditorGroup title='Its nature' icon={Compass}>
          <ChoiceEditor
            label={DESIGN_FIELD.staff_class}
            value={design.staff_class ?? 'priest'}
            table={CLASS_SPEC}
            held={design.locked.includes('staff_class')}
            blocked={busy}
            hint='The class that mans it'
            onPick={(value) =>
              edit.mutate({ values: { staff_class: value }, release: [] })
            }
          />
          <ChoiceEditor
            label={DESIGN_FIELD.staff_scale}
            value={design.staff_scale ?? 'some'}
            table={STAFF_SCALE_SPEC}
            held={design.locked.includes('staff_scale')}
            blocked={busy}
            hint='How many hands it needs per level'
            onPick={(value) =>
              edit.mutate({ values: { staff_scale: value }, release: [] })
            }
          />
          <ChoiceEditor
            label={DESIGN_FIELD.scale}
            value={design.scale ?? 'major'}
            table={SCALE_SPEC}
            held={design.locked.includes('scale')}
            blocked={busy}
            hint='Sets its labour and upkeep'
            onPick={(value) =>
              edit.mutate({ values: { scale: value }, release: [] })
            }
          />
          <ChoiceEditor
            label={DESIGN_FIELD.min_tier}
            value={design.min_tier ?? 'hamlet'}
            table={SIZE_SPEC}
            held={design.locked.includes('min_tier')}
            blocked={busy}
            hint='The smallest place that can raise it'
            onPick={(value) =>
              edit.mutate({ values: { min_tier: value }, release: [] })
            }
          />
          <FlagEditor
            label={DESIGN_FIELD.ley}
            hint='Draws strength from ley lines'
            icon={Sparkles}
            tone='verdigris'
            checked={design.ley ?? false}
            held={design.locked.includes('ley')}
            blocked={busy}
            onToggle={(value) =>
              edit.mutate({ values: { ley: value }, release: [] })
            }
          />
        </EditorGroup>
        <HeldStrip
          keys={design.locked}
          labelOf={(key) => DESIGN_FIELD[key] ?? key}
          blocked={busy}
          onRelease={(keys) => edit.mutate({ values: {}, release: keys })}
        />
      </AdjustPanel>
      <div className='flex min-w-0 justify-end'>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => retire.mutate(!design.retired)}
        >
          {design.retired ? <RotateCcw /> : <Trash2 />}
          {design.retired ? 'Restore the design' : 'Retire the design'}
        </Button>
      </div>
    </li>
  )
}

function DesignsPanel({
  worldId,
  designs,
  blocked,
}: {
  worldId: number | null
  designs: DesignView[]
  blocked: string | null
}) {
  const [name, setName] = useState('')
  const [base, setBase] = useState<StructureKind>('temple')
  const create = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/structure_design:create', {
          body: {
            world_id: worldId,
            values: { name: name.trim(), base_kind: base },
          },
        })
      ),
    invalidate: [structureKeys.designs(worldId)],
    success: 'The design was drawn up',
  })
  const reason =
    blocked ??
    (name.trim() === ''
      ? 'Give the design a name.'
      : create.isPending
        ? WORKING
        : null)
  return (
    <Panel
      title='Structure designs'
      icon={PenTool}
      tone='verdigris'
      hint='Your own kinds of building: a base kind with its own proportions, staff and scale'
      wide
    >
      <div
        data-surface='StructureDesigns'
        className='flex min-w-0 flex-col gap-3'
      >
        <div className='grid min-w-0 grid-cols-1 items-end gap-3 @md:grid-cols-3'>
          <div className='flex min-w-0 flex-col gap-1.5'>
            <FieldLabel htmlFor={`design-name-${worldId ?? 0}`}>
              Name of the design
            </FieldLabel>
            <Input
              id={`design-name-${worldId ?? 0}`}
              placeholder='The Seven-Domed Temple'
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <IconPicker
            label='Base kind'
            value={base}
            table={KIND_SPEC}
            blocked={blocked}
            onPick={(next) => setBase(next as StructureKind)}
          />
          <Button
            disabled={reason !== null}
            disabledReason={reason ?? undefined}
            onClick={() => {
              create.mutate(undefined)
              setName('')
            }}
          >
            <Plus />
            Draw up a design
          </Button>
        </div>
        {designs.length === 0 ? (
          <Muted variant='caption'>
            No designs yet; every work follows the common plan of its kind.
          </Muted>
        ) : (
          <ul className='grid min-w-0 grid-cols-1 gap-3 @xl:grid-cols-2'>
            <Paged items={designs} as='li'>
              {(design) => (
                <DesignCard key={design.id} design={design} blocked={blocked} />
              )}
            </Paged>
          </ul>
        )}
      </div>
    </Panel>
  )
}

export function SettlementStructures({
  hostId,
  blocked,
}: {
  hostId: number
  blocked: string | null
}) {
  const view = useHostStructures(hostId)
  const data = view.data
  const groups = useMemo(() => {
    const found = new Map<string, StructureView[]>()
    for (const item of data?.structures ?? []) {
      found.set(item.group, [...(found.get(item.group) ?? []), item])
    }
    return GROUP_ORDER.filter((group) => found.has(group)).map((group) => ({
      group,
      items: found.get(group) ?? [],
    }))
  }, [data])
  if (view.isPending) return <Muted>Counting the works…</Muted>
  if (view.isError || !data)
    return (
      <EmptyState
        icon={TriangleAlert}
        title='No works surveyed'
        description={
          view.error?.message ?? 'The works are counted at the next epoch.'
        }
      />
    )
  const raisingCount = data.structures.filter(raising).length
  const working = data.structures.filter(standing)
  const strength = working.length
    ? Math.round(
        working.reduce((sum, item) => sum + item.effect_pct, 0) / working.length
      )
    : 0
  return (
    <div
      id='section-structures'
      data-surface='SettlementStructures'
      className='@container flex min-w-0 flex-col gap-4'
    >
      <div className='grid min-w-0 grid-cols-2 gap-3 @xl:grid-cols-4'>
        <KpiTile
          label='Works'
          value={`${data.slots_used} of ${data.slots_total}`}
          icon={Building}
          tone='verdigris'
          hint='Slots taken, out of all its size allows'
          meter={{
            value: data.slots_used,
            max: data.slots_total,
            label: 'Works',
          }}
        />
        <KpiTile
          label='Being raised'
          value={formatInteger(raisingCount)}
          icon={Construction}
          tone='warning'
          hint='Works its builders are still raising'
        />
        <KpiTile
          label='Standing'
          value={formatInteger(working.length)}
          icon={Landmark}
          tone='success'
          hint='Works that stand and serve'
        />
        <KpiTile
          label='Working strength'
          value={`${strength}%`}
          icon={HeartPulse}
          tone={goodTone(strength)}
          hint='How well the standing works serve, on average'
        />
      </div>
      {groups.length === 0 ? (
        <EmptyState
          icon={Building}
          title='No works yet'
          description='Commission the first one below, or wait for its people to raise one.'
        />
      ) : (
        <Paged items={groups}>
          {({ group, items }) => (
            <div key={group} className='flex min-w-0 flex-col gap-2'>
              <GroupHeader
                group={group as StructureView['group']}
                count={items.length}
              />
              <ul className='grid min-w-0 grid-cols-1 gap-3 @md:grid-cols-2 @3xl:grid-cols-3'>
                <Paged items={items} as='li'>
                  {(item) => (
                    <StructureCard
                      key={item.id}
                      view={item}
                      blocked={blocked}
                    />
                  )}
                </Paged>
              </ul>
            </div>
          )}
        </Paged>
      )}
      <CommissionPanel
        key={data.kinds.map((item) => `${item.kind}${item.allowed}`).join()}
        hostId={hostId}
        options={data.kinds}
        designs={data.designs}
        full={data.slots_used >= data.slots_total}
        blocked={blocked}
      />
      <DesignsPanel
        worldId={data.world_id ?? null}
        designs={data.designs}
        blocked={blocked}
      />
    </div>
  )
}

export function PeopleStructuresSection({
  peopleId,
  readOnlyReason,
}: {
  peopleId: number
  readOnlyReason?: string | null
}) {
  const { reason } = useGodGate()
  return (
    <Section
      id='section-people-structures'
      title='Works'
      description='The temples, walls, workshops and wonders this people raises and keeps.'
      icon={Landmark}
    >
      <SettlementStructures
        hostId={peopleId}
        blocked={readOnlyReason ?? reason()}
      />
    </Section>
  )
}

const NUMBERS: {
  key: string
  icon: NumberField['icon']
  min: number
  max: number
}[] = [
  { key: 'level', icon: Layers, min: 1, max: LEVEL_MAX },
  { key: 'capacity', icon: Building, min: 0, max: HUGE },
  { key: 'condition', icon: Wrench, min: 0, max: PERCENT },
  { key: 'fire_resistance', icon: Flame, min: 0, max: PERCENT },
  { key: 'effect_pct', icon: HeartPulse, min: 0, max: PERCENT },
  { key: 'staff_pct', icon: Users, min: 0, max: PERCENT },
  { key: 'upkeep_coin', icon: Coins, min: 0, max: HUGE },
  { key: 'upkeep_goods', icon: Coins, min: 0, max: HUGE },
  { key: 'unpaid_epochs', icon: RotateCcw, min: 0, max: HUGE },
  { key: 'progress', icon: HardHat, min: 0, max: PERCENT },
]
const STATS = [
  { key: 'splendor', icon: Sparkles },
  { key: 'durability', icon: Shield },
  { key: 'function', icon: HeartPulse },
] as const

function StructureAdjust({
  view,
  blocked,
}: {
  view: StructureView
  blocked: string | null
}) {
  const id = useId()
  const edit = useGodAction({
    run: ({
      values,
      release,
    }: {
      values: Record<string, Value>
      release: string[]
    }) =>
      unwrap(
        api.POST('/api/actions/structure:edit', {
          body: { structure_id: view.id, values, release },
        })
      ),
    success: (_result, change) =>
      change.release.length
        ? 'The structure follows the world again'
        : 'Held as you set it',
  })
  const staff = useGodAction({
    run: ({ allocated, hold }: { allocated: number | null; hold: boolean }) =>
      unwrap(
        api.POST('/api/actions/structure:staff', {
          body: { structure_id: view.id, allocated, hold },
        })
      ),
  })
  const abandon = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/structure:abandon', {
          body: { structure_id: view.id, reason: '' },
        })
      ),
  })
  const fund = useGodAction({
    run: (amount: number) =>
      unwrap(
        api.POST('/api/actions/structure:fund', {
          body: { structure_id: view.id, amount },
        })
      ),
  })
  const damage = useGodAction({
    run: (amount: number) =>
      unwrap(
        api.POST('/api/actions/structure:damage', {
          body: { structure_id: view.id, amount, cause: '' },
        })
      ),
  })
  const pending =
    edit.isPending ||
    staff.isPending ||
    abandon.isPending ||
    fund.isPending ||
    damage.isPending
  const busy = blocked ?? (pending ? WORKING : null)
  const set = (key: string, value: Value) =>
    edit.mutate({ values: { [key]: value }, release: [] })
  const current: Record<string, number> = {
    level: view.level,
    capacity: view.capacity,
    condition: view.condition,
    fire_resistance: view.fire_resistance,
    effect_pct: view.effect_pct,
    staff_pct: view.staff_pct,
    upkeep_coin: view.upkeep_coin,
    upkeep_goods: view.upkeep_goods,
    unpaid_epochs: view.unpaid_epochs,
    progress: view.progress,
    splendor: view.splendor,
    durability: view.durability,
    function: view.function,
  }
  const held = [
    ...view.locked,
    ...(view.construction?.locked ?? []),
    ...(view.staff_held ? ['staff'] : []),
  ]
  return (
    <AdjustPanel
      title='Adjust this work'
      note='Every value you set is held against the world until you release it.'
    >
      <EditorGroup title='Its nature' icon={Compass}>
        <ChoiceEditor
          label={structureField('kind')}
          value={view.kind}
          table={KIND_SPEC}
          held={view.locked.includes('kind')}
          blocked={busy}
          hint='What it is and what it does'
          onPick={(value) => set('kind', value)}
        />
        <ChoiceEditor
          label={structureField('construction_state')}
          value={view.construction_state}
          table={STATE_SPEC}
          held={view.locked.includes('construction_state')}
          blocked={busy}
          hint='Raised, standing, damaged or ruined'
          onPick={(value) => set('construction_state', value)}
        />
        <ChoiceEditor
          label={structureField('material')}
          value={view.material ?? 'stone'}
          table={MATERIAL_TABLE}
          held={view.locked.includes('material')}
          blocked={busy}
          hint='Sets its durability and how well it resists fire'
          onPick={(value) => set('material', value)}
        />
        <ChoiceEditor
          label={structureField('aesthetic')}
          value={view.aesthetic ?? 'austere'}
          table={AESTHETIC_SPEC}
          held={view.locked.includes('aesthetic')}
          blocked={busy}
          hint='Its style; fitting the people who see it adds splendour'
          onPick={(value) => set('aesthetic', value)}
        />
        <ChoiceEditor
          label={structureField('builder_kind')}
          value={view.builder_kind ?? 'community'}
          table={BUILDER_SPEC}
          held={view.locked.includes('builder_kind')}
          blocked={busy}
          hint='Who raised it'
          onPick={(value) => set('builder_kind', value)}
        />
        <FlagEditor
          label={structureField('on_ley_line')}
          hint={
            view.attuned
              ? 'Attuned: a ley line strengthens it'
              : 'Not attuned to ley lines'
          }
          icon={Sparkles}
          tone='verdigris'
          checked={view.on_ley_line}
          held={view.locked.includes('on_ley_line')}
          blocked={busy}
          onToggle={(value) => set('on_ley_line', value)}
        />
        <FlagEditor
          label={structureField('anchor')}
          hint='Binds its dedicated god to the world'
          icon={Anchor}
          tone='gold'
          checked={view.anchor}
          held={view.locked.includes('anchor')}
          blocked={busy}
          onToggle={(value) => set('anchor', value)}
        />
      </EditorGroup>
      <EditorGroup title='Numbers' icon={Ruler}>
        {[
          ...NUMBERS,
          ...STATS.map((item) => ({ ...item, min: 0, max: PERCENT })),
        ].map((item) => (
          <NumberEditor
            key={`${item.key}-${current[item.key]}`}
            id={id}
            field={{
              key: item.key,
              label: structureField(item.key),
              icon: item.icon,
              value: current[item.key],
              min: item.min,
              max: item.max,
            }}
            held={view.locked.includes(item.key)}
            blocked={busy}
            pending={edit.isPending}
            onSet={(value) => set(item.key, value)}
          />
        ))}
      </EditorGroup>
      <EditorGroup title='People' icon={Users} pairs>
        <div className='flex min-w-0 flex-col gap-1.5 rounded-lg border bg-card p-3'>
          <FieldLabel>Architect</FieldLabel>
          <EntityPicker
            types={['mortal']}
            value={view.architect_id}
            onChange={(value) => set('architect_entity_id', value)}
            placeholder='No architect'
          />
        </div>
        <div className='flex min-w-0 flex-col gap-1.5 rounded-lg border bg-card p-3'>
          <SonSelect
            value={view.dedicated_son_id}
            onChange={(value) => set('dedicated_son_id', value)}
            blocked={busy}
          />
        </div>
        <div className='flex min-w-0 flex-col gap-1.5 rounded-lg border bg-card p-3'>
          <FieldLabel>Serves</FieldLabel>
          <EntityPicker
            types={['settlement', 'people']}
            value={view.host_id}
            onChange={(value) => set('host_entity_id', value)}
            placeholder='No one'
          />
        </div>
        <div className='flex min-w-0 flex-col gap-2 rounded-lg border bg-card p-3'>
          <FieldLabel>Staff at their posts</FieldLabel>
          <AmountForm
            label='Post staff'
            icon={Users}
            blocked={busy}
            pending={staff.isPending}
            max={HUGE}
            onSubmit={(value) => staff.mutate({ allocated: value, hold: true })}
          />
        </div>
      </EditorGroup>
      {view.construction && view.construction.status === 'active' && (
        <EditorGroup title='The building site' icon={HardHat} pairs>
          {(['cost', 'work', 'funds'] as const).map((key) => (
            <NumberEditor
              key={`${key}-${view.construction?.[key === 'work' ? 'work' : key]}`}
              id={id}
              field={{
                key,
                label: structureField(key),
                icon: key === 'funds' ? Coins : HardHat,
                value: view.construction ? view.construction[key] : 0,
                min: key === 'cost' ? 1 : 0,
                max: HUGE,
              }}
              held={
                view.construction?.locked.includes(
                  key === 'work' ? 'progress' : key
                ) ?? false
              }
              blocked={busy}
              pending={edit.isPending}
              onSet={(value) => set(key, value)}
            />
          ))}
          <div className='flex min-w-0 flex-col gap-2 rounded-lg border bg-card p-3'>
            <FieldLabel>Give coin to the builders</FieldLabel>
            <AmountForm
              label='Fund'
              icon={Coins}
              blocked={busy}
              pending={fund.isPending}
              max={HUGE}
              onSubmit={(value) => fund.mutate(value)}
            />
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => abandon.mutate(undefined)}
            >
              <Trash2 />
              Abandon the work
            </Button>
          </div>
        </EditorGroup>
      )}
      {standing(view) && (
        <EditorGroup title='Harm' icon={Flame} pairs>
          <div className='flex min-w-0 flex-col gap-2 rounded-lg border bg-card p-3'>
            <FieldLabel>Strike it</FieldLabel>
            <AmountForm
              label='Damage'
              icon={Flame}
              blocked={busy}
              pending={damage.isPending}
              max={PERCENT}
              onSubmit={(value) => damage.mutate(value)}
            />
          </div>
        </EditorGroup>
      )}
      <HeldStrip
        keys={held}
        labelOf={structureField}
        blocked={busy}
        onRelease={(keys) => {
          const rest = keys.filter((key) => key !== 'staff')
          if (keys.includes('staff'))
            staff.mutate({ allocated: null, hold: false })
          if (rest.length)
            edit.mutate({
              values: {},
              release: rest.map((key) => (key === 'progress' ? 'work' : key)),
            })
        }}
      />
    </AdjustPanel>
  )
}

function StructureHero({ view }: { view: StructureView }) {
  const kind = KIND_SPEC[view.kind]
  const state = STATE_SPEC[view.construction_state]
  const group = GROUP_SPEC[view.group]
  return (
    <div className='flex min-w-0 items-center gap-3 rounded-lg border bg-background p-3'>
      <Medallion icon={kind.icon} tone={kind.tone} />
      <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Text weight='semibold'>{view.design_name ?? kind.label}</Text>
          <Badge size='sm' variant='secondary'>
            <group.icon />
            {group.label}
          </Badge>
          <Badge
            size='sm'
            variant={
              view.construction_state === 'ruined' ? 'destructive' : 'secondary'
            }
          >
            <state.icon />
            {state.label}
          </Badge>
          {view.on_ley_line && (
            <Badge size='sm' variant='info'>
              <Sparkles />
              On a ley line
            </Badge>
          )}
          {view.locked.length > 0 && (
            <Badge size='sm' variant='default'>
              <Lock />
              {`${view.locked.length} held`}
            </Badge>
          )}
        </div>
        <Muted variant='caption'>{kind.hint}</Muted>
      </div>
    </div>
  )
}

export function StructureSection({
  structureId,
  readOnlyReason,
}: {
  structureId: number
  readOnlyReason?: string | null
}) {
  const view = useStructure(structureId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const data = view.data
  return (
    <Section
      id='section-structure'
      title='The work'
      description='What it is, how well it serves, who keeps it and what it costs.'
      icon={Landmark}
    >
      {view.isPending && <Muted>Surveying the work…</Muted>}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Not surveyed yet'
          description={view.error.message}
        />
      )}
      {data && (
        <div
          data-surface='StructureSection'
          className='@container flex min-w-0 flex-col gap-4'
        >
          <StructureHero view={data} />
          <div className='grid min-w-0 grid-cols-2 gap-3 @xl:grid-cols-4'>
            <KpiTile
              label='Working strength'
              value={`${data.effect_pct}%`}
              icon={HeartPulse}
              tone={goodTone(data.effect_pct)}
              hint='Base function times design, condition, staff and ley line'
            />
            <KpiTile
              label='Condition'
              value={`${data.condition} of ${data.durability}`}
              icon={Wrench}
              tone={goodTone(data.condition, 80, 40)}
              hint='Its durability is the most it can be'
            />
            <KpiTile
              label='Capacity'
              value={capacityText(data)}
              icon={Building}
              tone='verdigris'
              hint={`Level ${data.level} of ${LEVEL_MAX}`}
            />
            <KpiTile
              label='Splendour'
              value={formatInteger(data.splendor)}
              icon={Sparkles}
              tone='gold'
              hint='Feeds prestige, legitimacy and wonder status'
            />
          </div>
          {raising(data) && data.construction && (
            <Panel
              title='The building site'
              icon={HardHat}
              tone='warning'
              hint='Builders times engineering times materials, against the labour it needs'
            >
              <StatBar
                label='Raised'
                icon={Construction}
                value={data.construction.percent}
                max={PERCENT}
                tone='warning'
              />
              <div className='grid min-w-0 grid-cols-2 gap-2 @xl:grid-cols-4'>
                <MiniStat
                  icon={Users}
                  label='Builders'
                  value={formatInteger(data.construction.workers)}
                />
                <MiniStat
                  icon={HardHat}
                  label='Labour'
                  value={`${formatInteger(data.construction.work)} of ${formatInteger(data.construction.cost)}`}
                  tone='gold'
                />
                <MiniStat
                  icon={Building}
                  label='Materials delivered'
                  value={`${data.construction.materials_pct}%`}
                  tone={goodTone(data.construction.materials_pct)}
                />
                <MiniStat
                  icon={TriangleAlert}
                  label='Idle ages'
                  value={`${data.construction.stalled_epochs} of ${data.construction.stall_limit}`}
                  tone={
                    data.construction.stalled_epochs > 0 ? 'warning' : 'muted'
                  }
                />
              </div>
              {data.construction.generations > 0 && (
                <Muted variant='caption'>{`${data.construction.generations} generations have worked on it.`}</Muted>
              )}
            </Panel>
          )}
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl:grid-cols-2'>
            <Panel
              title='What it does'
              icon={HeartPulse}
              tone='success'
              hint='Its function by kind, times condition and staff'
            >
              <FunctionBreakdown view={data} />
              <StatBar
                label='Working strength'
                icon={HeartPulse}
                value={data.effect_pct}
                max={PERCENT}
                tone={METER_TONE[goodTone(data.effect_pct)]}
              />
            </Panel>
            <Panel
              title='Who keeps it'
              icon={Users}
              tone='info'
              hint='Staff from the cohorts of the place it serves'
            >
              <StaffLine view={data} />
              <UpkeepLine view={data} />
            </Panel>
          </div>
          <Panel
            title='Its making'
            icon={Compass}
            tone='gold'
            hint='Who raised it, of what, and for whom'
          >
            <div className='grid min-w-0 grid-cols-1 gap-2 @md:grid-cols-2 @xl:grid-cols-3'>
              <MiniStat
                icon={Landmark}
                label='Serves'
                value={data.host_name ?? 'No one'}
              />
              <MiniStat
                icon={BUILDER_SPEC[data.builder_kind ?? 'community'].icon}
                label={
                  data.builder_kind
                    ? BUILDER_SPEC[data.builder_kind].label
                    : 'Builder'
                }
                value={data.builder_name ?? 'Unknown'}
              />
              <MiniStat
                icon={Compass}
                label='Architect'
                value={data.architect_name ?? 'None remembered'}
              />
              <MiniStat
                icon={Sparkles}
                label='Dedicated to'
                value={data.dedicated_son_name ?? 'No god'}
                tone={data.dedicated_son_id ? 'verdigris' : 'muted'}
              />
              <MiniStat
                icon={Building}
                label='Material'
                value={data.material_label ?? 'Unknown'}
              />
              <MiniStat
                icon={Flame}
                label='Fire resistance'
                value={`${data.fire_resistance}%`}
                tone={goodTone(data.fire_resistance)}
              />
              <MiniStat
                icon={PenTool}
                label='Style'
                value={
                  data.aesthetic
                    ? AESTHETIC_SPEC[data.aesthetic].label
                    : 'Plain'
                }
              />
              <MiniStat
                icon={Wrench}
                label='Workshop'
                value={
                  data.workshop ? data.workshop.replaceAll('_', ' ') : 'None'
                }
              />
              <MiniStat
                icon={HardHat}
                label='Built in'
                value={
                  data.built_epoch !== null
                    ? `epoch ${data.built_epoch}`
                    : 'not yet'
                }
              />
            </div>
          </Panel>
          <StructureAdjust
            key={JSON.stringify([
              data.locked,
              data.construction?.locked,
              data.staff_held,
            ])}
            view={data}
            blocked={blocked}
          />
        </div>
      )}
    </Section>
  )
}

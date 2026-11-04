import { useState } from 'react'
import {
  ArrowDownRight,
  ArrowUpRight,
  Biohazard,
  BrickWall,
  Building,
  Castle,
  Coins,
  DoorOpen,
  Droplets,
  Flame,
  Gavel,
  Hammer,
  House,
  Landmark,
  LandPlot,
  Package,
  Percent,
  Plus,
  Route,
  ScrollText,
  Shield,
  ShieldAlert,
  Ship,
  Siren,
  Sparkles,
  Star,
  Trash2,
  TriangleAlert,
  Truck,
  Users,
  Utensils,
  Warehouse,
  Wheat,
  Wrench,
  Lock,
  LockOpen,
  Swords,
  Compass,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Medallion,
  MiniStat,
  RangeField,
  Section,
  StatBar,
  Paged,
} from '@/components/domain'
import { LineChart } from '@/components/domain/LineChart'
import { Muted, Stat, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { CityWorkings, DesignEditor, DistrictDesigns } from './CityWorks'
import { SettlementStructures } from './Structures'
import { useSettlementPlan } from './api'
import { DESIGN_FIELDS, signed } from './cityFields'
import {
  DISTRICT_MAX_LEVEL,
  DISTRICT_SPEC,
  MATERIAL_SPEC,
  SIZE_ORDER,
  SIZE_SPEC,
  TREASURY_SPEC,
  WATER_SPEC,
  type BuildMaterial,
  type DistrictKind,
  type Spec,
  fieldLabel,
} from './labels'
import {
  AdjustPanel,
  ChoiceEditor,
  EditorGroup,
  EditorTile,
  FlagEditor,
  HeldStrip,
  IconPicker,
  type NumberField,
  NumberEditor,
  Panel,
  Pips,
} from './parts'
import { METER_TONE, WORKING, badTone, goodTone } from './tones'

type Plan = components['schemas']['SettlementPlanView']
type District = components['schemas']['DistrictView']
type Change = { key: string; value: number | string | boolean }

const PERCENT = 100
const HUGE = 1000000000000
const STORE_MAX = 100000000
const WALL_MAX = 5
const ROAD_MAX = 5
const GATE_MAX = 20
const PLOT_PIPS = 12
const ADMIN_MAX = 300
const NO_GARRISON = '0'
const DISTRICT_LOCK_LABEL: Record<string, string> = {
  level: 'Level',
  condition: 'Repair',
  material: 'Material',
}

const CIVIC = [
  { key: 'public_order', icon: Gavel, harmful: false },
  { key: 'crime', icon: Siren, harmful: true },
  { key: 'unrest', icon: ShieldAlert, harmful: true },
  { key: 'sanitation', icon: Droplets, harmful: false },
  { key: 'fire_risk', icon: Flame, harmful: true },
  { key: 'prestige', icon: Star, harmful: false },
] as const
const COFFERS = [
  { key: 'treasury', icon: Coins, max: HUGE, unit: 'coin' },
  { key: 'militia', icon: Shield, max: HUGE, unit: 'men' },
  { key: 'investment_pool', icon: Sparkles, max: HUGE, unit: 'coin' },
  { key: 'construction_capacity', icon: Hammer, max: HUGE, unit: 'work' },
  { key: 'hauling_capacity', icon: Truck, max: HUGE, unit: 'loads' },
  { key: 'admin_capacity', icon: ScrollText, max: ADMIN_MAX, unit: '%' },
] as const
const SIEGE = [
  { key: 'siege_supplies', icon: Utensils, max: HUGE, unit: 'days' },
  { key: 'siege_water', icon: Droplets, max: HUGE, unit: 'days' },
  { key: 'siege_disease', icon: Biohazard, max: HUGE, unit: '' },
] as const
const WORKS = [
  { key: 'walls_level', icon: BrickWall, max: WALL_MAX, unit: '' },
  { key: 'walls_condition', icon: Wrench, max: PERCENT, unit: '' },
  { key: 'gates', icon: DoorOpen, max: GATE_MAX, unit: '' },
  { key: 'towers', icon: Castle, max: GATE_MAX, unit: '' },
] as const
const STORES = [
  { key: 'roads', icon: Route, max: ROAD_MAX, unit: '' },
  { key: 'granary_capacity', icon: Wheat, max: STORE_MAX, unit: 'measures' },
  { key: 'warehouse_capacity', icon: Warehouse, max: STORE_MAX, unit: 'loads' },
  { key: 'harbour_capacity', icon: Ship, max: STORE_MAX, unit: 'ships' },
] as const

function taxLevel(rate: number): string {
  if (rate === 0) return 'Untaxed'
  if (rate <= 10) return 'Light'
  if (rate <= 25) return 'Fair'
  if (rate <= 45) return 'Heavy'
  return 'Crushing'
}

function DistrictTile({
  district,
  design,
  blocked,
}: {
  district: District
  design: string | null
  blocked: string | null
}) {
  const spec = DISTRICT_SPEC[district.kind]
  const material = MATERIAL_SPEC[district.material]
  const raze = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/district:raze', {
          body: { district_id: district.id },
        })
      ),
  })
  const edit = useGodAction({
    run: (change: { level?: number; condition?: number; release?: string[] }) =>
      unwrap(
        api.POST('/api/actions/district:edit', {
          body: { district_id: district.id, clear_design: false, ...change },
        })
      ),
  })
  const busy = blocked ?? (raze.isPending || edit.isPending ? WORKING : null)
  const conditionTone = goodTone(district.condition, 80, 40)
  return (
    <li className='flex h-full min-w-0 flex-col gap-3 rounded-lg border bg-muted/30 p-3'>
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='medium' truncate>
            {design ?? spec.label}
          </Text>
          <Muted as='span' variant='caption' truncate>
            {design
              ? `A ${spec.label.toLowerCase()} · built in epoch ${district.built_epoch}`
              : `Built in epoch ${district.built_epoch}`}
          </Muted>
        </div>
        <Badge size='sm' variant='secondary'>
          <material.icon />
          {material.label}
        </Badge>
      </div>
      <div className='flex min-w-0 items-center justify-between gap-2'>
        <Muted as='span' variant='caption'>
          {`Level ${district.level} of ${DISTRICT_MAX_LEVEL}`}
        </Muted>
        <Pips
          value={district.level}
          max={DISTRICT_MAX_LEVEL}
          tone={spec.tone}
          label='Level'
        />
      </div>
      <StatBar
        label='Repair'
        icon={Wrench}
        value={district.condition}
        max={PERCENT}
        tone={METER_TONE[conditionTone]}
      />
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        {DESIGN_FIELDS.filter((item) => district.effects[item.key]).map(
          (item) => (
            <Badge key={item.key} size='sm' variant='outline'>
              <item.icon />
              {`${fieldLabel(item.key)} ${item.unit === '%' ? `${signed(district.effects[item.key])}%` : signed(district.effects[item.key])}`}
            </Badge>
          )
        )}
      </div>
      {district.locked.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          {district.locked.map((key) => (
            <Badge key={key} size='sm' variant='warning'>
              <Lock />
              {`${DISTRICT_LOCK_LABEL[key] ?? fieldLabel(key)} held`}
            </Badge>
          ))}
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => edit.mutate({ release: district.locked })}
          >
            <LockOpen />
            Release
          </Button>
        </div>
      )}
      <div className='mt-auto grid min-w-0 grid-cols-3 gap-1.5'>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || district.level >= DISTRICT_MAX_LEVEL}
          disabledReason={busy ?? 'Already at the highest level'}
          onClick={() =>
            edit.mutate({ level: district.level + 1, condition: PERCENT })
          }
        >
          <Hammer />
          Enlarge
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || district.condition >= PERCENT}
          disabledReason={busy ?? 'It stands whole'}
          onClick={() => edit.mutate({ condition: PERCENT })}
        >
          <Wrench />
          Repair
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => raze.mutate(undefined)}
        >
          <Trash2 />
          Raze
        </Button>
      </div>
    </li>
  )
}

function OpenPlots({ count }: { count: number }) {
  return (
    <li className='flex h-full min-h-32 min-w-0 flex-col items-center justify-center gap-2 rounded-lg border border-dashed bg-background p-3 text-center'>
      <Medallion icon={LandPlot} tone='muted' size='sm' />
      <Text as='span' weight='medium'>
        {count === 1 ? 'One open plot' : `${count} open plots`}
      </Text>
      {count <= PLOT_PIPS && (
        <Pips value={0} max={count} tone='muted' label='Open plots' />
      )}
      <Muted as='span' variant='caption'>
        Raise a district on them from the controls below
      </Muted>
    </li>
  )
}

function CityHero({ plan }: { plan: Plan }) {
  const size = SIZE_SPEC[plan.size_tier]
  const water = WATER_SPEC[plan.infrastructure.water]
  return (
    <div className='flex min-w-0 items-center gap-3 rounded-lg border bg-background p-3'>
      <Medallion icon={size.icon} tone={size.tone} />
      <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Text weight='semibold'>{size.label}</Text>
          <Pips
            value={size.rank}
            max={SIZE_ORDER.length}
            tone={size.tone}
            label='Size'
          />
        </div>
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Badge size='sm' variant={plan.free_city ? 'success' : 'secondary'}>
            <Shield />
            {plan.free_city ? 'Free city' : 'Under an overlord'}
          </Badge>
          {plan.charter_id !== null && (
            <Badge size='sm' variant='default'>
              <ScrollText />
              <EntityLink kind='entity' id={String(plan.charter_id)}>
                Chartered
              </EntityLink>
            </Badge>
          )}
          <Badge size='sm' variant='info'>
            <water.icon />
            {water.label}
          </Badge>
          <Badge
            size='sm'
            variant={plan.infrastructure.sewers ? 'info' : 'secondary'}
          >
            <Droplets />
            {plan.infrastructure.sewers ? 'Sewers' : 'No sewers'}
          </Badge>
          {plan.rationing && (
            <Badge size='sm' variant='warning'>
              <Utensils />
              Rationing
            </Badge>
          )}
          <Paged items={plan.foreigners}>
            {(item) => (
              <Badge key={item.people_id} size='sm' variant='outline'>
                <Users />
                {`${item.name} ${item.share}%`}
              </Badge>
            )}
          </Paged>
        </div>
      </div>
    </div>
  )
}

function Defences({ plan }: { plan: Plan }) {
  const works = plan.infrastructure
  const material = MATERIAL_SPEC[works.walls_material]
  return (
    <Panel
      title='Walls and stores'
      icon={BrickWall}
      tone='info'
      hint='What keeps enemies out and the city fed'
      aside={
        <Badge size='sm' variant='secondary'>
          <material.icon />
          {material.label}
        </Badge>
      }
    >
      <div className='flex min-w-0 items-center justify-between gap-2'>
        <Text as='span' variant='caption' weight='medium'>
          {works.walls_level === 0
            ? 'No walls'
            : `Walls, height ${works.walls_level} of ${WALL_MAX}`}
        </Text>
        <Pips
          value={works.walls_level}
          max={WALL_MAX}
          tone='info'
          label='Wall height'
        />
      </div>
      <StatBar
        label='Wall repair'
        icon={Wrench}
        value={works.walls_condition}
        max={PERCENT}
        tone={METER_TONE[goodTone(works.walls_condition, 80, 40)]}
      />
      <div className='grid min-w-0 grid-cols-2 gap-2'>
        <MiniStat icon={DoorOpen} label='Gates' value={works.gates} />
        <MiniStat icon={Castle} label='Towers' value={works.towers} />
        <MiniStat
          icon={Route}
          label='Roads'
          value={`${works.roads} of ${ROAD_MAX}`}
        />
        <MiniStat
          icon={Wheat}
          label='Granaries'
          value={formatInteger(works.granary_capacity)}
          tone='success'
        />
        <MiniStat
          icon={Warehouse}
          label='Warehouses'
          value={formatInteger(works.warehouse_capacity)}
          tone='gold'
        />
        <MiniStat
          icon={Ship}
          label='Harbour'
          value={formatInteger(works.harbour_capacity)}
          tone={works.harbour_capacity > 0 ? 'info' : 'muted'}
        />
      </div>
    </Panel>
  )
}

function Streets({ plan }: { plan: Plan }) {
  return (
    <Panel
      title='Life in the streets'
      icon={Users}
      hint='Order and standing, each out of 100'
    >
      <div className='flex min-w-0 flex-col gap-3'>
        {CIVIC.map((item) => {
          const value = plan[item.key]
          return (
            <StatBar
              key={item.key}
              label={fieldLabel(item.key)}
              icon={item.icon}
              value={value}
              max={PERCENT}
              tone={METER_TONE[item.harmful ? badTone(value) : goodTone(value)]}
            />
          )
        })}
        <StatBar
          label='Wealth'
          icon={Coins}
          value={plan.wealth}
          max={PERCENT}
          tone={METER_TONE[goodTone(plan.wealth)]}
        />
      </div>
    </Panel>
  )
}

function PlanControls({
  plan,
  blocked,
}: {
  plan: Plan
  blocked: string | null
}) {
  const [tax, setTax] = useState(plan.tax_rate)
  const [kind, setKind] = useState<string>('market')
  const [material, setMaterial] = useState<string>('stone')
  const [design, setDesign] = useState<string>('')
  const [target, setTarget] = useState<string>(
    plan.districts[0] ? String(plan.districts[0].id) : ''
  )
  const [retype, setRetype] = useState<string>('kind:market')
  const designTable = Object.fromEntries(
    plan.designs.map((item) => [
      String(item.id),
      {
        label: item.name,
        icon: DISTRICT_SPEC[item.base_kind].icon,
        tone: DISTRICT_SPEC[item.base_kind].tone,
      },
    ])
  )
  const districtTable = Object.fromEntries(
    plan.districts.map((item) => [
      String(item.id),
      {
        label: `${plan.designs.find((entry) => entry.id === item.design_id)?.name ?? DISTRICT_SPEC[item.kind].label} ${item.level}`,
        icon: DISTRICT_SPEC[item.kind].icon,
        tone: DISTRICT_SPEC[item.kind].tone,
      },
    ])
  )
  const garrisonTable: Record<string, Spec> = {
    [NO_GARRISON]: { label: 'No garrison', icon: Shield, tone: 'muted' },
    ...Object.fromEntries(
      plan.armies.map((army) => [
        String(army.id),
        {
          label: `${army.name} (${formatInteger(army.size)})`,
          icon: Swords,
          tone: 'danger' as const,
        },
      ])
    ),
  }
  const locked = [...plan.locked, ...plan.infrastructure.locked]
  const edit = useGodAction({
    run: ({ key, value }: Change) =>
      unwrap(
        api.POST('/api/actions/settlement:edit', {
          body: {
            settlement_id: plan.entity_id,
            values: { [key]: value },
            release: [],
          },
        })
      ),
    success: (_result, change) => `${fieldLabel(change.key)} set`,
  })
  const release = useGodAction({
    run: (keys: string[]) =>
      unwrap(
        api.POST('/api/actions/settlement:edit', {
          body: { settlement_id: plan.entity_id, values: {}, release: keys },
        })
      ),
    success: 'The city follows the world again',
  })
  const setRate = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/settlement:tax', {
          body: { settlement_id: plan.entity_id, rate: tax },
        })
      ),
  })
  const build = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/district:build', {
          body: {
            settlement_id: plan.entity_id,
            kind: design === '' ? (kind as DistrictKind) : null,
            design_id: design === '' ? null : Number(design),
            material: material as BuildMaterial,
          },
        })
      ),
  })
  const free = useGodAction({
    run: (value: boolean) =>
      unwrap(
        api.POST('/api/actions/settlement:free_city', {
          body: { settlement_id: plan.entity_id, free: value },
        })
      ),
  })
  const rework = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/district:edit', {
          body: {
            district_id: Number(target),
            kind: retype.startsWith('kind:')
              ? (retype.slice(5) as DistrictKind)
              : null,
            design_id: retype.startsWith('design:')
              ? Number(retype.slice(7))
              : null,
            clear_design: false,
          },
        })
      ),
    success: 'The district was reworked',
  })
  const foreign = useGodAction({
    run: (shares: Record<string, number>) =>
      unwrap(
        api.POST('/api/actions/settlement:foreigners', {
          body: { settlement_id: plan.entity_id, shares },
        })
      ),
    success: 'The foreign quarters were counted anew',
  })
  const charter = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/settlement:charter', {
          body: { settlement_id: plan.entity_id },
        })
      ),
  })
  const pending =
    edit.isPending ||
    release.isPending ||
    setRate.isPending ||
    build.isPending ||
    free.isPending ||
    rework.isPending ||
    foreign.isPending ||
    charter.isPending
  const busy = blocked ?? (pending ? WORKING : null)
  const current: Record<string, number> = {
    public_order: plan.public_order,
    crime: plan.crime,
    unrest: plan.unrest,
    sanitation: plan.sanitation,
    fire_risk: plan.fire_risk,
    prestige: plan.prestige,
    treasury: plan.treasury,
    militia: plan.militia,
    investment_pool: plan.investment_pool,
    construction_capacity: plan.construction_capacity,
    hauling_capacity: plan.hauling_capacity,
    admin_capacity: plan.admin_capacity,
    siege_supplies: plan.siege_supplies,
    siege_water: plan.siege_water,
    siege_disease: plan.siege_disease,
    walls_level: plan.infrastructure.walls_level,
    walls_condition: plan.infrastructure.walls_condition,
    gates: plan.infrastructure.gates,
    towers: plan.infrastructure.towers,
    roads: plan.infrastructure.roads,
    granary_capacity: plan.infrastructure.granary_capacity,
    warehouse_capacity: plan.infrastructure.warehouse_capacity,
    harbour_capacity: plan.infrastructure.harbour_capacity,
  }
  const editor = (item: {
    key: string
    icon: NumberField['icon']
    max: number
    unit?: string
  }) => {
    const field: NumberField = {
      key: item.key,
      label: fieldLabel(item.key),
      icon: item.icon,
      value: current[item.key],
      min: 0,
      max: item.max,
      unit: item.unit || undefined,
    }
    return (
      <NumberEditor
        key={`${field.key}-${field.value}`}
        id={`settlement-${plan.entity_id}`}
        field={field}
        held={locked.includes(field.key)}
        blocked={blocked}
        pending={edit.isPending && edit.variables?.key === field.key}
        onSet={(value) => edit.mutate({ key: field.key, value })}
      />
    )
  }
  const full = plan.districts.length >= plan.district_slots
  return (
    <AdjustPanel
      title='Govern the city'
      note='Tax, build, free or charter it, and set any value. What you set is held against the world until you release it; every change goes into the ledger and can be undone.'
    >
      <HeldStrip
        keys={locked}
        labelOf={fieldLabel}
        blocked={busy}
        onRelease={(keys) => release.mutate(keys)}
      />
      <EditorGroup title='Tax' icon={Percent} pairs>
        <div className='flex min-w-0 flex-col gap-2 @md:col-span-2'>
          <RangeField
            label='Tax'
            icon={Percent}
            value={tax}
            min={0}
            max={PERCENT}
            level={taxLevel(tax)}
            hint='Share of trade and harvest taken'
            lowLabel='Untaxed'
            highLabel='Crushing'
            onChange={setTax}
          />
          <Button
            size='sm'
            variant='outline'
            className='self-end'
            disabled={busy !== null || tax === plan.tax_rate}
            disabledReason={busy ?? 'This is the present rate.'}
            onClick={() => setRate.mutate(undefined)}
          >
            <Percent />
            {`Set the tax to ${tax}%`}
          </Button>
        </div>
      </EditorGroup>
      <EditorGroup title='Decrees' icon={ScrollText} pairs>
        <FlagEditor
          label='Free city'
          hint='Rules itself, owing no overlord'
          icon={Shield}
          tone='success'
          checked={plan.free_city}
          held={locked.includes('free_city')}
          blocked={busy}
          onToggle={(value) => free.mutate(value)}
        />
        <FlagEditor
          label='Rationing'
          hint='Food is doled out; hunger eases, mood sours'
          icon={Utensils}
          tone='warning'
          checked={plan.rationing}
          held={locked.includes('rationing')}
          blocked={busy}
          onToggle={(value) => edit.mutate({ key: 'rationing', value })}
        />
        <FlagEditor
          label='Sewers'
          hint='Carry filth away; sanitation rises'
          icon={Droplets}
          tone='info'
          checked={plan.infrastructure.sewers}
          held={locked.includes('sewers')}
          blocked={busy}
          onToggle={(value) => edit.mutate({ key: 'sewers', value })}
        />
        <EditorTile
          icon={ScrollText}
          tone={plan.charter_id !== null ? 'gold' : 'muted'}
          label='Charter'
          hint={
            plan.charter_id !== null
              ? 'It holds its own courts, markets and walls'
              : 'Grant it its own courts, markets and walls'
          }
          held={false}
          control={
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || plan.charter_id !== null}
              disabledReason={busy ?? 'It already holds a charter'}
              onClick={() => charter.mutate(undefined)}
            >
              <ScrollText />
              Grant
            </Button>
          }
        />
      </EditorGroup>
      <EditorGroup title='Raise a district' icon={Building}>
        <IconPicker
          label='District'
          value={kind}
          table={DISTRICT_SPEC}
          blocked={
            busy !== null ? busy : design !== '' ? 'A design is chosen' : null
          }
          onPick={setKind}
        />
        {plan.designs.length > 0 && (
          <IconPicker
            label='Or a design'
            value={design}
            table={{
              '': { label: 'No design', icon: Compass, tone: 'muted' },
              ...designTable,
            }}
            blocked={busy}
            onPick={setDesign}
          />
        )}
        <IconPicker
          label='Built of'
          value={material}
          table={MATERIAL_SPEC}
          blocked={busy}
          onPick={setMaterial}
        />
        <div className='flex min-w-0 flex-col justify-end gap-1.5'>
          <Muted variant='caption'>
            {full
              ? 'Every plot is taken; a new district crowds in beyond them.'
              : `${plan.district_slots - plan.districts.length} open plots`}
          </Muted>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => build.mutate(undefined)}
          >
            <Plus />
            Build it
          </Button>
        </div>
      </EditorGroup>
      {plan.districts.length > 0 && (
        <EditorGroup title='Rework a district' icon={Wrench}>
          <IconPicker
            label='District'
            value={target}
            table={districtTable}
            blocked={busy}
            onPick={setTarget}
          />
          <IconPicker
            label='Turn it into'
            value={retype}
            table={{
              ...Object.fromEntries(
                Object.entries(DISTRICT_SPEC).map(([key, spec]) => [
                  `kind:${key}`,
                  spec,
                ])
              ),
              ...Object.fromEntries(
                Object.entries(designTable).map(([key, spec]) => [
                  `design:${key}`,
                  spec,
                ])
              ),
            }}
            blocked={busy}
            onPick={setRetype}
          />
          <div className='flex min-w-0 flex-col justify-end gap-1.5'>
            <Muted variant='caption'>
              Its level, repair and material stay; its effects follow the new
              kind.
            </Muted>
            <Button
              size='sm'
              disabled={busy !== null || retype === '' || target === ''}
              disabledReason={busy ?? 'Choose a district and what it becomes'}
              onClick={() => rework.mutate(undefined)}
            >
              <Wrench />
              Rework it
            </Button>
          </div>
        </EditorGroup>
      )}
      <EditorGroup title='Garrison and foreigners' icon={Users}>
        <ChoiceEditor
          label='Garrison'
          hint='The standing army that watches the walls'
          value={String(plan.garrison_id ?? NO_GARRISON)}
          table={garrisonTable}
          held={locked.includes('garrison_entity_id')}
          blocked={busy}
          onPick={(value) =>
            edit.mutate({ key: 'garrison_entity_id', value: Number(value) })
          }
        />
        <Paged items={plan.foreigners}>
          {(item) => (
            <NumberEditor
              key={`foreign-${item.people_id}-${item.share}`}
              id={`settlement-${plan.entity_id}-foreign`}
              field={{
                key: `foreign-${item.people_id}`,
                label: item.name || 'Foreign people',
                icon: Users,
                value: item.share,
                min: 0,
                max: PERCENT,
                unit: '% of the city',
              }}
              held={locked.includes('foreigners')}
              blocked={busy}
              pending={foreign.isPending}
              onSet={(value) =>
                foreign.mutate(
                  Object.fromEntries(
                    plan.foreigners.map((entry) => [
                      String(entry.people_id),
                      entry.people_id === item.people_id ? value : entry.share,
                    ])
                  )
                )
              }
            />
          )}
        </Paged>
        {plan.foreigners.length === 0 && (
          <Muted variant='caption'>
            No foreign people lives here; they arrive as migrants and traders.
          </Muted>
        )}
      </EditorGroup>
      <EditorGroup title='Design a new district' icon={Compass}>
        <div className='flex min-w-0 flex-col gap-2 @md:col-span-2 @3xl:col-span-3'>
          <Muted variant='caption'>
            Pick the base kind it builds on and replace any of its effects per
            level; blank fields keep the base value. Every city of the world may
            then raise it.
          </Muted>
          <DesignEditor design={null} plan={plan} blocked={busy} />
        </div>
      </EditorGroup>
      <EditorGroup title='The city' icon={Landmark}>
        <ChoiceEditor
          label='Size'
          hint='How large the city counts as'
          value={plan.size_tier}
          table={SIZE_SPEC}
          held={locked.includes('size_tier')}
          blocked={busy}
          onPick={(value) => edit.mutate({ key: 'size_tier', value })}
        />
        <ChoiceEditor
          label='Water'
          hint='Where its water comes from'
          value={plan.infrastructure.water}
          table={WATER_SPEC}
          held={locked.includes('water')}
          blocked={busy}
          onPick={(value) => edit.mutate({ key: 'water', value })}
        />
        <ChoiceEditor
          label='Walls of'
          hint='What its walls are built of'
          value={plan.infrastructure.walls_material}
          table={MATERIAL_SPEC}
          held={locked.includes('walls_material')}
          blocked={busy}
          onPick={(value) => edit.mutate({ key: 'walls_material', value })}
        />
      </EditorGroup>
      <EditorGroup title='Order and standing' icon={Gavel}>
        {CIVIC.map((item) => editor({ ...item, max: PERCENT }))}
      </EditorGroup>
      <EditorGroup title='Coffers and men' icon={Coins}>
        {COFFERS.map(editor)}
      </EditorGroup>
      <EditorGroup title='Siege stores' icon={Castle}>
        {SIEGE.map(editor)}
      </EditorGroup>
      <EditorGroup title='Walls' icon={BrickWall} pairs>
        {WORKS.map(editor)}
      </EditorGroup>
      <EditorGroup title='Roads and stores' icon={Package} pairs>
        {STORES.map(editor)}
      </EditorGroup>
    </AdjustPanel>
  )
}

export function SettlementPlanSection({
  settlementId,
  readOnlyReason,
}: {
  settlementId: number
  readOnlyReason?: string | null
}) {
  const view = useSettlementPlan(settlementId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const plan = view.data
  const living = plan?.history[plan.history.length - 1]?.population ?? null
  return (
    <Section
      id='section-settlement-plan'
      title='The city'
      description='Its size, districts, walls, water and sewers; order, crime and unrest; how it stands a siege.'
      icon={Landmark}
    >
      {view.isPending && <Muted>Walking the streets…</Muted>}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Not surveyed yet'
          description={view.error.message}
        />
      )}
      {plan && (
        <div
          data-surface='SettlementPlan'
          className='@container/city flex min-w-0 flex-col gap-4'
        >
          <CityHero plan={plan} />
          <div className='grid min-w-0 grid-cols-2 gap-3 @xl/city:grid-cols-4'>
            <KpiTile
              label='Treasury'
              value={formatInteger(plan.treasury)}
              icon={Coins}
              tone='gold'
              hint={`Taxed at ${plan.tax_rate}%, ${taxLevel(plan.tax_rate).toLowerCase()}`}
            />
            <KpiTile
              label='Districts'
              value={`${plan.districts.length} of ${plan.district_slots}`}
              icon={Building}
              tone='verdigris'
              hint='Plots built on, out of all the city can hold'
              meter={{
                value: plan.districts.length,
                max: plan.district_slots,
                label: 'Districts',
              }}
            />
            <KpiTile
              label='Housing'
              value={formatInteger(plan.housing)}
              icon={House}
              tone={
                living !== null && living > plan.housing ? 'warning' : 'info'
              }
              hint={
                living !== null
                  ? `${formatInteger(living)} live here`
                  : 'Roofs for this many'
              }
            />
            <KpiTile
              label='Militia'
              value={formatInteger(plan.militia)}
              icon={Shield}
              tone='danger'
              hint='Citizens who take up arms in need'
            />
          </div>
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl/city:grid-cols-2'>
            <Streets plan={plan} />
            <Defences plan={plan} />
          </div>
          <CityWorkings plan={plan} />
          <Panel
            title='Under siege'
            icon={Castle}
            tone='warning'
            hint='How long it holds out, and how fast it builds and hauls'
          >
            <div className='grid min-w-0 grid-cols-1 gap-2 @md/city:grid-cols-2 @xl/city:grid-cols-3'>
              <MiniStat
                icon={Utensils}
                label='Food'
                value={`${formatInteger(plan.siege_supplies)} days`}
                tone='success'
              />
              <MiniStat
                icon={Droplets}
                label='Water'
                value={`${formatInteger(plan.siege_water)} days`}
                tone='info'
              />
              <MiniStat
                icon={Biohazard}
                label='Camp sickness'
                value={formatInteger(plan.siege_disease)}
                tone={plan.siege_disease > 0 ? 'danger' : 'muted'}
              />
              <MiniStat
                icon={Hammer}
                label='Builders raise'
                value={formatInteger(plan.construction_capacity)}
                tone='gold'
                hint='Building work done each epoch'
              />
              <MiniStat
                icon={Truck}
                label='Porters haul'
                value={formatInteger(plan.hauling_capacity)}
                tone='gold'
                hint='Loads carried each epoch'
              />
              <MiniStat
                icon={Sparkles}
                label='Investment'
                value={formatInteger(plan.investment_pool)}
                tone='verdigris'
                hint='Coin the owners have put in, waiting to be spent'
              />
            </div>
          </Panel>
          <Panel
            title='Districts'
            icon={Building}
            hint='Each quarter of the city, its size and its repair'
            aside={
              <Badge size='sm' variant='secondary'>
                {`${plan.districts.length} of ${plan.district_slots} plots`}
              </Badge>
            }
          >
            <ul
              data-surface='SettlementPlanTiles'
              className='grid min-w-0 grid-cols-1 gap-3 @md/city:grid-cols-2 @3xl/city:grid-cols-3'
            >
              <Paged items={plan.districts} as='li'>
                {(district) => (
                  <DistrictTile
                    key={district.id}
                    district={district}
                    design={
                      plan.designs.find(
                        (item) => item.id === district.design_id
                      )?.name ?? null
                    }
                    blocked={blocked}
                  />
                )}
              </Paged>
              {plan.district_slots > plan.districts.length && (
                <OpenPlots
                  count={plan.district_slots - plan.districts.length}
                />
              )}
            </ul>
          </Panel>
          <DistrictDesigns plan={plan} blocked={blocked} />
          <Panel
            title='Works and buildings'
            icon={Landmark}
            tone='verdigris'
            hint='Temples, walls, granaries, workshops and wonders: what each does, how well, and what it costs'
          >
            <SettlementStructures hostId={settlementId} blocked={blocked} />
          </Panel>
          <PlanControls
            key={JSON.stringify([
              plan.locked,
              plan.infrastructure.locked,
              plan.tax_rate,
            ])}
            plan={plan}
            blocked={blocked}
          />
        </div>
      )}
    </Section>
  )
}

export function TreasurySection({ settlementId }: { settlementId: number }) {
  const view = useSettlementPlan(settlementId)
  if (!view.data) return null
  const plan = view.data
  const history = plan.history
  const income = plan.treasury_ledger
    .filter((line) => line.amount > 0)
    .reduce((total, line) => total + line.amount, 0)
  const spending = plan.treasury_ledger
    .filter((line) => line.amount < 0)
    .reduce((total, line) => total - line.amount, 0)
  return (
    <>
      <Section
        id='section-treasury'
        title='Treasury'
        description='Every coin in and out: taxes, tolls, the owners’ investment, garrisons, walls, festivals, alms, building and fires.'
        icon={Coins}
      >
        <div className='@container/coin flex min-w-0 flex-col gap-4'>
          <div className='grid min-w-0 grid-cols-3 gap-3'>
            <KpiTile
              label='In the coffers'
              value={formatInteger(plan.treasury)}
              icon={Coins}
              tone='gold'
              hint={`Taxed at ${plan.tax_rate}%`}
            />
            <KpiTile
              label='Came in'
              value={formatInteger(income)}
              icon={ArrowUpRight}
              tone='success'
              hint='All income on the ledger'
            />
            <KpiTile
              label='Went out'
              value={formatInteger(spending)}
              icon={ArrowDownRight}
              tone='danger'
              hint='All spending on the ledger'
            />
          </div>
          {plan.treasury_ledger.length === 0 ? (
            <EmptyState
              icon={Coins}
              title='No coin has moved yet'
              description='Taxes and costs are booked at the end of each epoch.'
            />
          ) : (
            <Panel title='Ledger' icon={ScrollText} hint='Newest last'>
              <ul
                data-surface='TreasuryLedger'
                className='flex min-w-0 flex-col divide-y'
              >
                <Paged items={plan.treasury_ledger} as='li'>
                  {(line, index) => {
                    const spec = TREASURY_SPEC[line.entry]
                    return (
                      <li
                        key={`${line.epoch}-${index}`}
                        className='flex min-w-0 items-center gap-3 py-2 first:pt-0 last:pb-0'
                      >
                        <Medallion
                          icon={spec.icon}
                          tone={line.amount < 0 ? 'danger' : spec.tone}
                          size='sm'
                        />
                        <div className='flex min-w-0 flex-1 flex-col'>
                          <Text as='span' weight='medium' truncate>
                            {spec.label}
                          </Text>
                          <Muted as='span' variant='caption' truncate>
                            {line.note &&
                            line.note.toLowerCase() !== spec.label.toLowerCase()
                              ? `Epoch ${line.epoch} · ${line.note}`
                              : `Epoch ${line.epoch}`}
                          </Muted>
                        </div>
                        <div className='flex shrink-0 flex-col items-end'>
                          <Stat
                            value={`${line.amount > 0 ? '+' : ''}${formatInteger(line.amount)}`}
                            tone={line.amount < 0 ? 'destructive' : 'success'}
                          />
                          <Muted as='span' variant='caption'>
                            {`Balance ${formatInteger(line.balance)}`}
                          </Muted>
                        </div>
                      </li>
                    )
                  }}
                </Paged>
              </ul>
            </Panel>
          )}
        </div>
      </Section>
      {history.length > 1 && (
        <Section
          id='chart-order-timeline'
          title='Order, crime and unrest'
          description='How the city has fared, epoch by epoch.'
          icon={Landmark}
        >
          <LineChart
            label='Order, crime and unrest'
            height={160}
            series={[
              {
                key: 'order',
                label: 'Order',
                color: 'var(--chart-2)',
                points: history.map((point) => ({
                  x: point.epoch,
                  y: point.public_order,
                })),
              },
              {
                key: 'crime',
                label: 'Crime',
                color: 'var(--color-destructive)',
                points: history.map((point) => ({
                  x: point.epoch,
                  y: point.crime,
                })),
              },
              {
                key: 'unrest',
                label: 'Unrest',
                color: 'var(--color-warning)',
                points: history.map((point) => ({
                  x: point.epoch,
                  y: point.unrest,
                })),
              },
              {
                key: 'sanitation',
                label: 'Sanitation',
                color: 'var(--color-info)',
                points: history.map((point) => ({
                  x: point.epoch,
                  y: point.sanitation,
                })),
              },
            ]}
          />
        </Section>
      )}
    </>
  )
}

import { useState } from 'react'
import {
  Activity,
  Bandage,
  Biohazard,
  ChevronRight,
  Coins,
  Crosshair,
  Crown,
  Flag,
  Flame,
  Footprints,
  Gauge,
  HandCoins,
  HardHat,
  Hourglass,
  Lock,
  MapPin,
  Medal,
  Network,
  Package,
  Plus,
  Repeat,
  Route,
  Rows3,
  Ruler,
  Save,
  Shield,
  Shovel,
  Swords,
  Target,
  Telescope,
  Trash2,
  Unlock,
  UserMinus,
  Users,
  Wheat,
  Wrench,
  Zap,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { unitKindValues } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  EntityLink,
  Medallion,
  MiniStat,
  Paged,
  PagedList,
  StatBar,
  Timeline,
  TimelineItem,
} from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { StackArms } from './ArmyDepth'
import { ArmyWorks, CommanderAreas } from './ArmyWorks'
import { type ArmyCard, type Stack, soldiersOf, useUnitKinds } from './api'
import { EntityPicker } from './controls'
import {
  ARMOUR,
  DOCTRINE,
  FAMILY,
  FORMATION,
  MORALE_STATE,
  PERCENT,
  SHIELD,
  STANCE,
  TARGET_CLASS,
  TRAIT,
  UNIT_ICON,
  WEAPON,
  fieldLabel,
  named,
  percentTone,
  busyOf,
  whole,
} from './labels'
import {
  Adjust,
  ChoiceField,
  FieldGrid,
  NumberField,
  Pips,
  Plain,
  Tag,
  TableTag,
  ToggleField,
} from './parts'

const SUPPLY_COMFORT = 90
const SUPPLY_LOW = 20
const PROFILE_NUMBERS = [
  'supply_days',
  'war_chest',
  'cohesion',
  'disease',
  'entrenchment',
  'loot',
  'baggage',
  'contact_seasons',
] as const
const PERCENT_PROFILE = new Set(['cohesion', 'disease', 'entrenchment'])
const STACK_NUMBERS = [
  'count',
  'quality',
  'experience',
  'morale',
  'fatigue',
  'wounded',
  'condition',
  'organisation',
  'discipline',
  'ammunition',
  'missing',
] as const
const UNBOUNDED_STACK = new Set(['count', 'wounded', 'ammunition', 'missing'])
const NUMBER_ICON: Record<string, typeof Users> = {
  supply_days: Wheat,
  war_chest: Coins,
  cohesion: Activity,
  disease: Biohazard,
  entrenchment: Shovel,
  loot: HandCoins,
  baggage: Package,
  count: Users,
  quality: Gauge,
  experience: Medal,
  morale: Flame,
  fatigue: Hourglass,
  wounded: Bandage,
  condition: Wrench,
  organisation: Network,
  discipline: Swords,
  ammunition: Crosshair,
  missing: UserMinus,
  contact_seasons: Telescope,
}
const ARMOUR_MAX = 6
const SHIELD_MAX = 3

type ProfileNumber = (typeof PROFILE_NUMBERS)[number]
type StackNumber = (typeof STACK_NUMBERS)[number]

function unitOf(stack: { kind: string; family: string }) {
  const family = named(FAMILY, stack.family)
  return { icon: UNIT_ICON[stack.kind] ?? family.icon, family }
}

function StackEditor({
  stack,
  armyId,
  blocked,
}: {
  stack: Stack
  armyId: number
  blocked: string | null
}) {
  const [values, setValues] = useState<Record<StackNumber, string>>(
    () =>
      Object.fromEntries(
        STACK_NUMBERS.map((key) => [key, String(stack[key])])
      ) as Record<StackNumber, string>
  )
  const [armour, setArmour] = useState<string>(stack.armour)
  const [shield, setShield] = useState<string>(stack.shield)
  const [helmet, setHelmet] = useState(stack.helmet)
  const [formation, setFormation] = useState<string>(stack.formation)
  const [moraleState, setMoraleState] = useState<string>(stack.morale_state)
  const release = useGodAction({
    run: (key: string) =>
      unwrap(
        api.POST('/api/actions/army:edit_stack', {
          body: { unit_id: stack.id, values: {}, release: [key] },
        })
      ),
  })
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/army:edit_stack', {
          body: {
            unit_id: stack.id,
            values: {
              ...Object.fromEntries(
                STACK_NUMBERS.map((key) => [
                  key,
                  whole(
                    values[key],
                    UNBOUNDED_STACK.has(key) ? undefined : PERCENT
                  ),
                ])
              ),
              armour,
              shield,
              helmet,
              formation,
              morale_state: moraleState,
            },
          },
        })
      ),
  })
  const remove = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/army:remove_stack', {
          body: { unit_id: stack.id },
        })
      ),
  })
  const busy = busyOf(
    blocked,
    save.isPending,
    remove.isPending,
    release.isPending
  )
  return (
    <Adjust
      title={`Shape the ${stack.label.toLowerCase()}`}
      note='Set numbers, morale, order and gear. Every value you set is held against battles and marches until you release it.'
    >
      <div className='grid min-w-0 grid-cols-1 gap-2 @sm/stack:grid-cols-2'>
        {STACK_NUMBERS.map((key) => (
          <NumberField
            key={key}
            label={fieldLabel(key)}
            icon={NUMBER_ICON[key]}
            value={values[key]}
            max={UNBOUNDED_STACK.has(key) ? undefined : PERCENT}
            onChange={(value) =>
              setValues((current) => ({ ...current, [key]: value }))
            }
          />
        ))}
        <ChoiceField
          label='Armour'
          icon={ARMOUR.plate.icon}
          value={armour}
          table={ARMOUR}
          blocked={busy}
          onPick={setArmour}
        />
        <ChoiceField
          label='Shield'
          icon={Shield}
          value={shield}
          table={SHIELD}
          blocked={busy}
          onPick={setShield}
        />
        <ChoiceField
          label='Formation'
          icon={Rows3}
          value={formation}
          table={FORMATION}
          blocked={busy}
          onPick={setFormation}
        />
        <ChoiceField
          label='Morale state'
          icon={Flame}
          value={moraleState}
          table={MORALE_STATE}
          blocked={busy}
          onPick={setMoraleState}
        />
        <ToggleField
          item={{ label: 'Helmets', icon: HardHat, tone: 'gold' }}
          checked={helmet}
          disabled={busy !== null}
          onChange={setHelmet}
        />
      </div>
      {stack.locked.length > 0 ? (
        <div className='flex min-w-0 flex-col gap-1'>
          <Label>Held against the world</Label>
          <PagedList
            items={stack.locked}
            initial={12}
            noun={['entry', 'entries']}
            as='div'
            className='flex min-w-0 flex-wrap gap-1'
            itemKey={(key) => key}
          >
            {(key) => (
              <Button
                key={key}
                size='sm'
                variant='outline'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => release.mutate(key)}
              >
                <Unlock />
                {`Release ${fieldLabel(key).toLowerCase()}`}
              </Button>
            )}
          </PagedList>
        </div>
      ) : (
        <Muted variant='caption'>
          Nothing is held yet: battles and marches change every value freely.
        </Muted>
      )}
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => save.mutate(undefined)}
        >
          <Save />
          Save the stack
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => remove.mutate(undefined)}
        >
          <Trash2 />
          Strike it
        </Button>
      </div>
      <StackArms
        armyId={armyId}
        stackId={stack.id}
        kind={stack.kind}
        blocked={blocked}
      />
    </Adjust>
  )
}

function StackCard({
  stack,
  armyId,
  blocked,
}: {
  stack: Stack
  armyId: number
  blocked: string | null
}) {
  const { icon, family } = unitOf(stack)
  const armour = named(ARMOUR, stack.armour) as (typeof ARMOUR)[string]
  const shield = named(SHIELD, stack.shield) as (typeof SHIELD)[string]
  const broken = stack.count === 0
  return (
    <li
      data-surface='ArmyStack'
      className={cn(
        '@container/stack flex min-w-0 flex-col gap-3 rounded-xl border bg-background p-3',
        broken && 'border-dashed'
      )}
    >
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion
          icon={icon}
          tone={broken ? 'muted' : (family.tone ?? 'gold')}
        />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Text as='span' weight='semibold' truncate>
            {stack.label}
          </Text>
          <div className='flex min-w-0 flex-wrap gap-1'>
            <Tag item={family} />
            {broken && (
              <Badge size='sm' variant='destructive'>
                <Flag />
                Broken
              </Badge>
            )}
          </div>
        </div>
        <div className='flex shrink-0 flex-col items-end'>
          <Stat value={formatInteger(stack.count)} size='kpi' />
          <Label>Soldiers</Label>
        </div>
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 @xs/stack:grid-cols-2'>
        <StatBar
          label='Morale'
          icon={Flame}
          value={stack.morale}
          max={PERCENT}
          tone={percentTone(stack.morale)}
        />
        <StatBar
          label='Gear condition'
          icon={Wrench}
          value={stack.condition}
          max={PERCENT}
          tone={percentTone(stack.condition)}
        />
        <StatBar
          label='Experience'
          icon={Medal}
          value={stack.experience}
          max={PERCENT}
          tone='info'
        />
        <StatBar
          label='Fatigue'
          icon={Hourglass}
          value={stack.fatigue}
          max={PERCENT}
          tone={percentTone(stack.fatigue, true)}
        />
        <StatBar
          label='Organisation'
          icon={Network}
          value={stack.organisation}
          max={PERCENT}
          tone={percentTone(stack.organisation)}
        />
        <StatBar
          label='Discipline'
          icon={Swords}
          value={stack.discipline}
          max={PERCENT}
          tone='info'
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-1'>
        <TableTag table={MORALE_STATE} value={stack.morale_state} />
        <TableTag table={FORMATION} value={stack.formation} />
        <TableTag table={TARGET_CLASS} value={stack.target_class} />
        {stack.volleys > 0 && (
          <Plain icon={Crosshair}>
            {`${formatInteger(stack.ammunition)} volleys left`}
          </Plain>
        )}
        {stack.missing > 0 && (
          <Badge size='sm' variant='warning'>
            <UserMinus />
            {`${formatInteger(stack.missing)} stragglers`}
          </Badge>
        )}
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2 @xs/stack:grid-cols-4'>
        <MiniStat label='Reach' value={stack.reach} icon={Ruler} />
        <MiniStat label='Volleys' value={stack.volleys} icon={Repeat} />
        <MiniStat label='Accuracy' value={stack.accuracy} icon={Target} />
        <MiniStat label='Piercing' value={stack.piercing} icon={Zap} />
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 rounded-lg border bg-muted/20 p-2 @xs/stack:grid-cols-2'>
        <div className='flex min-w-0 items-center gap-2'>
          <TableTag table={ARMOUR} value={stack.armour} />
          <Pips
            value={armour.rank ?? 0}
            max={ARMOUR_MAX}
            tone={armour.tone}
            label={`Armour ${armour.label}`}
          />
        </div>
        <div className='flex min-w-0 items-center gap-2'>
          <TableTag table={SHIELD} value={stack.shield} />
          <Pips
            value={shield.rank ?? 0}
            max={SHIELD_MAX}
            tone={shield.tone}
            label={`Shield ${shield.label}`}
          />
        </div>
        <div className='flex min-w-0 flex-wrap items-center gap-1 @xs/stack:col-span-2'>
          <Badge size='sm' variant={stack.helmet ? 'default' : 'outline'}>
            <HardHat />
            {stack.helmet ? 'Helmets' : 'Bare heads'}
          </Badge>
          {stack.weapons.map((weapon) => (
            <TableTag key={weapon} table={WEAPON} value={weapon} />
          ))}
          <Plain icon={Gauge}>{`Quality ${stack.quality}`}</Plain>
          {stack.wounded > 0 && (
            <Badge size='sm' variant='warning'>
              <Bandage />
              {`${formatInteger(stack.wounded)} wounded`}
            </Badge>
          )}
        </div>
      </div>
      <div className='mt-auto flex min-w-0 flex-col'>
        <StackEditor stack={stack} armyId={armyId} blocked={blocked} />
      </div>
    </li>
  )
}

function AddStack({
  armyId,
  blocked,
}: {
  armyId: number
  blocked: string | null
}) {
  const kinds = useUnitKinds()
  const [kind, setKind] = useState<string>('spearmen')
  const [count, setCount] = useState('100')
  const add = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/army:add_stack', {
          body: {
            army_id: armyId,
            kind: kind as (typeof unitKindValues)[number],
            count: whole(count, undefined, 1),
          },
        })
      ),
  })
  const families = Object.fromEntries(
    (kinds.data ?? []).map((spec) => [spec.kind, spec])
  )
  const table = Object.fromEntries(
    unitKindValues.map((value) => {
      const spec = families[value]
      const family = named(FAMILY, spec?.family ?? 'infantry')
      return [
        value,
        {
          label: spec?.label ?? named({}, value).label,
          icon: UNIT_ICON[value] ?? family.icon,
          tone: family.tone,
        },
      ]
    })
  )
  const busy = busyOf(blocked, add.isPending)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>Raise a stack</Label>
      <FieldGrid>
        <ChoiceField
          label='Unit'
          icon={Users}
          value={kind}
          table={table}
          blocked={busy}
          onPick={setKind}
        />
        <NumberField
          label='Soldiers'
          icon={Users}
          value={count}
          min={1}
          onChange={setCount}
        />
      </FieldGrid>
      <div>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => add.mutate(undefined)}
        >
          <Plus />
          Add the stack
        </Button>
      </div>
    </div>
  )
}

function ArmyOrders({
  army,
  blocked,
}: {
  army: ArmyCard
  blocked: string | null
}) {
  const id = army.army?.id ?? 0
  const [stance, setStance] = useState<string>(army.stance)
  const [doctrine, setDoctrine] = useState(army.doctrine)
  const [forced, setForced] = useState(army.forced_march)
  const [target, setTarget] = useState<number | null>(
    army.target ? army.target.id : null
  )
  const [numbers, setNumbers] = useState<Record<ProfileNumber, string>>(
    () =>
      Object.fromEntries(
        PROFILE_NUMBERS.map((key) => [key, String(army[key])])
      ) as Record<ProfileNumber, string>
  )
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/army:edit', {
          body: {
            army_id: id,
            values: {
              ...Object.fromEntries(
                PROFILE_NUMBERS.map((key) => [
                  key,
                  whole(
                    numbers[key],
                    PERCENT_PROFILE.has(key) ? PERCENT : undefined
                  ),
                ])
              ),
              stance,
              doctrine,
              forced_march: forced,
              target_id: target,
            },
          },
        })
      ),
  })
  const release = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/army:edit', {
          body: { army_id: id, values: {}, release: army.locked },
        })
      ),
  })
  const busy = busyOf(blocked, save.isPending, release.isPending)
  return (
    <Adjust
      label='Command the army'
      title='Orders and stores'
      note='Orders you give are held: the army keeps them until you let it decide again. Every change goes into the ledger.'
    >
      <div data-surface='ArmyOrders' className='flex min-w-0 flex-col gap-3'>
        <FieldGrid>
          <ChoiceField
            label='Stance'
            icon={Footprints}
            value={stance}
            table={STANCE}
            blocked={busy}
            onPick={setStance}
          />
          <ChoiceField
            label='Way of war'
            icon={Shield}
            value={doctrine}
            table={DOCTRINE}
            blocked={busy}
            onPick={setDoctrine}
          />
          <EntityPicker
            label='March on'
            icon={Target}
            types={['region']}
            value={target}
            onChange={setTarget}
            blocked={busy}
          />
          <ToggleField
            item={{ label: 'Forced march', icon: Footprints, tone: 'warning' }}
            checked={forced}
            disabled={busy !== null}
            onChange={setForced}
          />
          {PROFILE_NUMBERS.map((key) => (
            <NumberField
              key={key}
              label={fieldLabel(key)}
              icon={NUMBER_ICON[key]}
              value={numbers[key]}
              max={PERCENT_PROFILE.has(key) ? PERCENT : undefined}
              onChange={(value) =>
                setNumbers((current) => ({ ...current, [key]: value }))
              }
            />
          ))}
        </FieldGrid>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => save.mutate(undefined)}
          >
            <Save />
            Give the orders
          </Button>
          {army.locked.length > 0 && (
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => release.mutate(undefined)}
            >
              <Unlock />
              Let the army decide again
            </Button>
          )}
          {army.locked.map((key) => (
            <Badge key={key} size='sm' variant='default'>
              <Lock />
              {`Held: ${fieldLabel(key)}`}
            </Badge>
          ))}
        </div>
        <AddStack armyId={id} blocked={blocked} />
      </div>
    </Adjust>
  )
}

function Marches({ army }: { army: ArmyCard }) {
  return (
    <Timeline label='Marches by season'>
      <Paged items={army.movements} as='li'>
        {(move, index) => {
          const stance = named(STANCE, move.stance)
          const from = move.from_region?.name ?? '—'
          const to = move.to_region?.name ?? '—'
          return (
            <TimelineItem
              key={`${move.epoch}.${move.season}`}
              icon={stance.icon}
              tone={move.attrition > 0 ? 'warning' : 'default'}
              title={from === to ? `Held ${to}` : `${from} → ${to}`}
              timestamp={`Epoch ${move.epoch} · season ${move.season + 1}`}
              last={index === army.movements.length - 1}
            >
              <div className='flex min-w-0 flex-wrap gap-1'>
                <Tag item={stance} />
                <Plain icon={Wheat}>{`${move.supply_days} days of food`}</Plain>
                <Badge
                  size='sm'
                  variant={move.attrition > 0 ? 'destructive' : 'outline'}
                >
                  <Users />
                  {`${formatInteger(move.attrition)} lost`}
                </Badge>
                {move.note && <Plain icon={Flag}>{move.note}</Plain>}
              </div>
            </TimelineItem>
          )
        }}
      </Paged>
    </Timeline>
  )
}

export function ArmyPanel({
  army,
  blocked,
}: {
  army: ArmyCard
  blocked: string | null
}) {
  const stance = named(STANCE, army.stance)
  const soldiers = soldiersOf(army)
  const supplyTone =
    army.supply_days <= 0
      ? 'danger'
      : army.supply_days < SUPPLY_LOW
        ? 'warning'
        : 'success'
  return (
    <div
      data-surface='ArmyCard'
      className='@container/mil flex min-w-0 flex-col gap-4 rounded-xl border bg-card p-4'
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={stance.icon} tone={stance.tone ?? 'gold'} />
        <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
          <div className='flex min-w-0 flex-wrap items-baseline gap-x-1.5'>
            {army.army ? (
              <EntityLink kind='entity' id={String(army.army.id)}>
                {army.army.name}
              </EntityLink>
            ) : (
              <Text as='span' weight='semibold'>
                An army
              </Text>
            )}
            {army.owner && (
              <Muted as='span' variant='caption'>
                {`of ${army.owner.name}`}
              </Muted>
            )}
          </div>
          <div className='flex min-w-0 flex-wrap gap-1'>
            <Tag item={stance} />
            <TableTag table={DOCTRINE} value={army.doctrine} />
            {army.region && (
              <Plain icon={MapPin}>{`In ${army.region.name}`}</Plain>
            )}
            {army.target && (
              <Plain icon={Target}>{`Bound for ${army.target.name}`}</Plain>
            )}
            {army.blockade && (
              <Badge size='sm' variant='warning'>
                <Flag />
                {`Blockading ${army.blockade.name}`}
              </Badge>
            )}
            {army.forced_march && (
              <Badge size='sm' variant='warning'>
                <Footprints />
                Forced march
              </Badge>
            )}
          </div>
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2 rounded-lg border bg-muted/20 p-2'>
        <Crown
          aria-hidden='true'
          className='size-icon-sm shrink-0 text-primary'
        />
        {army.commander ? (
          <EntityLink kind='entity' id={String(army.commander.id)}>
            {army.commander.name}
          </EntityLink>
        ) : (
          <Muted as='span'>No commander leads it</Muted>
        )}
        {army.commander_traits.length === 0
          ? army.commander && (
              <Muted as='span' variant='caption'>
                No battle traits
              </Muted>
            )
          : army.commander_traits.map((trait) => (
              <TableTag key={trait} table={TRAIT} value={trait} />
            ))}
      </div>
      <CommanderAreas army={army} />
      <div className='grid min-w-0 grid-cols-2 gap-2 @2xl/mil:grid-cols-4'>
        <MiniStat
          icon={Users}
          label='Soldiers'
          value={formatInteger(soldiers)}
          tone='gold'
          hint={`Across ${army.stacks.length} ${army.stacks.length === 1 ? 'stack' : 'stacks'}`}
        />
        <MiniStat
          icon={Wheat}
          label='Supplies'
          value={`${army.supply_days} days`}
          tone={supplyTone}
          hint={
            army.supply_days >= SUPPLY_COMFORT
              ? 'Well fed for the season'
              : 'Days of food carried and foraged'
          }
        />
        <MiniStat
          icon={Coins}
          label='War chest'
          value={formatInteger(army.war_chest)}
          tone='gold'
        />
        <MiniStat
          icon={HandCoins}
          label='Loot and baggage'
          value={`${formatInteger(army.loot)} / ${formatInteger(army.baggage)}`}
          tone='warning'
          hint='Loot carried, then baggage weighing the march'
        />
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 @lg/mil:grid-cols-3'>
        <StatBar
          label='Cohesion'
          icon={Activity}
          value={army.cohesion}
          max={PERCENT}
          tone={percentTone(army.cohesion)}
        />
        <StatBar
          label='Earthworks'
          icon={Shovel}
          value={army.entrenchment}
          max={PERCENT}
          tone='verdigris'
        />
        <StatBar
          label='Camp sickness'
          icon={Biohazard}
          value={army.disease}
          max={PERCENT}
          tone={percentTone(army.disease, true)}
        />
      </div>
      <ArmyWorks army={army} />
      {army.supply_line.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Route
            aria-hidden='true'
            className='size-icon-sm shrink-0 text-muted-foreground'
          />
          <Label>Supply line</Label>
          <Paged items={army.supply_line}>
            {(item, index) => (
              <span
                key={`${item.id}.${index}`}
                className='flex items-center gap-1.5'
              >
                {index > 0 && (
                  <ChevronRight
                    aria-hidden='true'
                    className='size-icon-xs text-muted-foreground'
                  />
                )}
                <Plain icon={MapPin}>{item.name}</Plain>
              </span>
            )}
          </Paged>
        </div>
      )}
      <div className='flex min-w-0 flex-col gap-2'>
        <div className='flex min-w-0 items-center gap-2'>
          <Label variant='overline'>Unit stacks</Label>
          <Badge size='sm' variant='secondary'>
            {army.stacks.length}
          </Badge>
        </div>
        {army.stacks.length === 0 ? (
          <EmptyState
            size='compact'
            icon={Shield}
            title='No stacks'
            description='This army has no units on its rolls. Raise one from Command the army.'
          />
        ) : (
          <ul className='grid min-w-0 grid-cols-1 gap-3 @xl/mil:grid-cols-2 @6xl/mil:grid-cols-3'>
            <Paged items={army.stacks} as='li'>
              {(stack) => (
                <StackCard
                  key={stack.id}
                  stack={stack}
                  armyId={army.army?.id ?? 0}
                  blocked={blocked}
                />
              )}
            </Paged>
          </ul>
        )}
      </div>
      {army.movements.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <div className='flex min-w-0 items-center gap-2'>
            <Label variant='overline'>Marches</Label>
            <Badge size='sm' variant='secondary'>
              {army.movements.length}
            </Badge>
          </div>
          <Marches army={army} />
        </div>
      )}
      <ArmyOrders army={army} blocked={blocked} />
    </div>
  )
}

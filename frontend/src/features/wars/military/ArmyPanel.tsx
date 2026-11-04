import { useState } from 'react'
import {
  Footprints,
  Flag,
  Plus,
  Save,
  Shield,
  Swords,
  Tent,
  Trash2,
  Wheat,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  armourTypeValues,
  shieldTypeValues,
  stanceValues,
  unitKindValues,
} from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  StatBar,
  Timeline,
  TimelineItem,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { MindPicker } from '@/features/entity/mind/parts'
import { useGodAction } from '@/features/pantheon/godAction'
import { type ArmyCard, type Stack, table, useUnitKinds, words } from './api'

const PERCENT = 100
const WORKING = 'Working…'
const DOCTRINES = [
  'shieldwall',
  'horse_archer',
  'skirmisher',
  'chariot',
  'phalanx',
  'berserker',
  'naval_raider',
  'siege_engineer',
  'war_magic',
  'beast_war',
] as const
const PROFILE_NUMBERS = [
  'supply_days',
  'war_chest',
  'cohesion',
  'disease',
  'entrenchment',
  'loot',
  'baggage',
] as const
const STACK_NUMBERS = [
  'count',
  'quality',
  'experience',
  'morale',
  'fatigue',
  'wounded',
  'condition',
] as const

type ProfileNumber = (typeof PROFILE_NUMBERS)[number]
type StackNumber = (typeof STACK_NUMBERS)[number]

export function NumberBox({
  label,
  value,
  onChange,
  max,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  max?: number
}) {
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label>{label}</Label>
      <Input
        type='number'
        min={0}
        max={max}
        value={value}
        aria-label={label}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  )
}

function StackRow({
  stack,
  blocked,
}: {
  stack: Stack
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
                  Math.max(0, Math.round(Number(values[key]) || 0)),
                ])
              ),
              armour,
              shield,
              helmet,
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
  const busy = blocked ?? (save.isPending || remove.isPending ? WORKING : null)
  return (
    <li
      data-surface='ArmyStack'
      className='flex min-w-0 flex-col gap-3 rounded-lg border bg-muted/30 p-3'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Text as='span' weight='semibold'>
          {stack.label}
        </Text>
        <Badge variant='outline'>{words(stack.family)}</Badge>
        <Badge variant='outline'>{formatInteger(stack.count)}</Badge>
        {stack.weapons.map((weapon) => (
          <Badge key={weapon} variant='outline'>
            {weapon}
          </Badge>
        ))}
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-3'>
        <StatBar label='Morale' value={stack.morale} max={PERCENT} />
        <StatBar label='Experience' value={stack.experience} max={PERCENT} />
        <StatBar
          label='Fatigue'
          value={stack.fatigue}
          max={PERCENT}
          tone={stack.fatigue > PERCENT / 2 ? 'warning' : 'default'}
        />
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
        {STACK_NUMBERS.map((key) => (
          <NumberBox
            key={key}
            label={words(key)}
            value={values[key]}
            max={key === 'count' || key === 'wounded' ? undefined : PERCENT}
            onChange={(value) =>
              setValues((current) => ({ ...current, [key]: value }))
            }
          />
        ))}
        <MindPicker
          label='Armour'
          value={armour}
          table={table(armourTypeValues)}
          blocked={busy}
          onPick={setArmour}
        />
        <MindPicker
          label='Shield'
          value={shield}
          table={table(shieldTypeValues)}
          blocked={busy}
          onPick={setShield}
        />
        <label className='flex items-center gap-2'>
          <Switch
            checked={helmet}
            disabled={busy !== null}
            onCheckedChange={setHelmet}
            aria-label='Helmet'
          />
          <Text as='span'>Helmet</Text>
        </label>
      </div>
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
            count: Math.max(1, Math.round(Number(count) || 1)),
          },
        })
      ),
  })
  const labels = Object.fromEntries(
    (kinds.data ?? []).map((spec) => [spec.kind, spec.label])
  )
  const busy = blocked ?? (add.isPending ? WORKING : null)
  return (
    <div className='flex min-w-0 flex-wrap items-end gap-2'>
      <MindPicker
        label='Unit'
        value={kind}
        table={Object.keys(labels).length ? labels : table(unitKindValues)}
        blocked={busy}
        onPick={setKind}
      />
      <NumberBox label='Soldiers' value={count} onChange={setCount} />
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
  const [target, setTarget] = useState(
    army.target ? String(army.target.id) : ''
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
                  Math.max(0, Math.round(Number(numbers[key]) || 0)),
                ])
              ),
              stance,
              doctrine,
              forced_march: forced,
              target_id: target ? Math.round(Number(target)) : null,
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
  const busy = blocked ?? (save.isPending || release.isPending ? WORKING : null)
  return (
    <div data-surface='ArmyOrders' className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
        <MindPicker
          label='Stance'
          value={stance}
          table={table(stanceValues)}
          blocked={busy}
          onPick={setStance}
        />
        <MindPicker
          label='Way of war'
          value={doctrine}
          table={table(DOCTRINES)}
          blocked={busy}
          onPick={setDoctrine}
        />
        <NumberBox
          label='March on region'
          value={target}
          onChange={setTarget}
        />
        <label className='flex items-center gap-2'>
          <Switch
            checked={forced}
            disabled={busy !== null}
            onCheckedChange={setForced}
            aria-label='Forced march'
          />
          <Text as='span'>Forced march</Text>
        </label>
        {PROFILE_NUMBERS.map((key) => (
          <NumberBox
            key={key}
            label={words(key)}
            value={numbers[key]}
            max={
              ['cohesion', 'disease', 'entrenchment'].includes(key)
                ? PERCENT
                : undefined
            }
            onChange={(value) =>
              setNumbers((current) => ({ ...current, [key]: value }))
            }
          />
        ))}
      </div>
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
            Let the army decide again
          </Button>
        )}
        {army.locked.map((key) => (
          <Badge key={key} variant='outline'>{`held: ${words(key)}`}</Badge>
        ))}
      </div>
    </div>
  )
}

export function ArmyPanel({
  army,
  blocked,
}: {
  army: ArmyCard
  blocked: string | null
}) {
  const id = army.army?.id ?? 0
  return (
    <div data-surface='ArmyCard' className='flex min-w-0 flex-col gap-4'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        {army.army && (
          <EntityLink kind='entity' id={String(army.army.id)}>
            {army.army.name}
          </EntityLink>
        )}
        <Badge variant='info'>{words(army.stance)}</Badge>
        <Badge variant='outline'>{words(army.doctrine)}</Badge>
        {army.region && (
          <Badge variant='outline'>{`In ${army.region.name}`}</Badge>
        )}
        {army.blockade && (
          <Badge variant='warning'>{`Blockading ${army.blockade.name}`}</Badge>
        )}
        {army.commander && (
          <Badge variant='outline'>{`Led by ${army.commander.name}`}</Badge>
        )}
        {army.commander_traits.map((trait) => (
          <Badge key={trait} variant='outline'>
            {words(trait)}
          </Badge>
        ))}
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
        <KpiTile
          label='Soldiers'
          value={formatInteger(army.size)}
          icon={Swords}
        />
        <KpiTile
          label='Supplies'
          value={`${army.supply_days} days`}
          icon={Wheat}
          tone={army.supply_days <= 0 ? 'danger' : 'muted'}
        />
        <KpiTile
          label='War chest'
          value={formatInteger(army.war_chest)}
          icon={Flag}
        />
        <KpiTile
          label='Earthworks'
          value={`${army.entrenchment}%`}
          icon={Tent}
          hint={`Camp sickness ${army.disease}%`}
        />
      </div>
      {army.supply_line.length > 0 && (
        <Muted>{`Supply line: ${army.supply_line.map((item) => item.name).join(' → ')}`}</Muted>
      )}
      <ArmyOrders army={army} blocked={blocked} />
      <Label variant='overline'>Stacks</Label>
      {army.stacks.length === 0 ? (
        <EmptyState
          icon={Shield}
          title='No stacks'
          description='This army has no units on its rolls.'
        />
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          {army.stacks.map((stack) => (
            <StackRow key={stack.id} stack={stack} blocked={blocked} />
          ))}
        </ul>
      )}
      <AddStack armyId={id} blocked={blocked} />
      {army.movements.length > 0 && (
        <>
          <Label variant='overline'>Marches</Label>
          <Timeline label='Marches by season'>
            {army.movements.map((move, index) => (
              <TimelineItem
                key={`${move.epoch}.${move.season}`}
                icon={Footprints}
                tone={move.attrition > 0 ? 'warning' : 'default'}
                title={`${move.from_region?.name ?? '—'} → ${move.to_region?.name ?? '—'} (${words(move.stance)})`}
                timestamp={`Epoch ${move.epoch}, season ${move.season + 1}`}
                last={index === army.movements.length - 1}
              >
                <Muted variant='caption'>
                  {`${move.supply_days} days of food, ${formatInteger(move.attrition)} lost${move.note ? `, ${move.note}` : ''}`}
                </Muted>
              </TimelineItem>
            ))}
          </Timeline>
        </>
      )}
    </div>
  )
}

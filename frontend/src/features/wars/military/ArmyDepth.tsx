import { useState } from 'react'
import {
  Award,
  CalendarDays,
  Crown,
  Dumbbell,
  Flag,
  MapPin,
  Route,
  ShieldAlert,
  Swords,
  Users,
  Wheat,
  X,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  EntityLink,
  Medallion,
  StatBar,
  Paged,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { EntityPicker, Held, RecordButtons } from './controls'
import {
  MATERIAL,
  ROLE,
  SOCIAL_CLASS,
  type RecordRow,
  nameOf,
  useRecords,
} from './depth'
import { PERCENT, TACTIC, WEAPON, busyOf } from './labels'
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
  useNameMap,
  useRecordActions,
  useRecordCreate,
} from './recordHooks'

const COMMUNITIES = ['people', 'settlement', 'faction', 'cult', 'polity']
const PROFILE_NUMBERS = ['drill', 'fodder_days', 'mutiny'] as const
const MUTINY_WARN = 50

function supplyLine(value: unknown): number[] {
  return Array.isArray(value)
    ? value.filter((item): item is number => typeof item === 'number')
    : []
}

function SupplyLine({
  line,
  onChange,
  blocked,
}: {
  line: number[]
  onChange: (next: number[]) => void
  blocked: string | null
}) {
  const names = useNameMap()
  const [next, setNext] = useState<number | null>(null)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>Supply line</Label>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        {line.length === 0 && (
          <Muted variant='caption'>The army lives off the land.</Muted>
        )}
        {line.map((region, index) => (
          <Badge key={`${region}.${index}`} size='sm' variant='outline'>
            <Route />
            {names[region] ?? `Region ${region}`}
            <Button
              size='icon-sm'
              variant='ghost'
              aria-label={`Drop ${names[region] ?? 'this region'}`}
              disabled={blocked !== null}
              disabledReason={blocked ?? undefined}
              onClick={() => onChange(line.filter((_, at) => at !== index))}
            >
              <X />
            </Button>
          </Badge>
        ))}
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <div className='min-w-0 flex-1 basis-56'>
          <EntityPicker
            label='Add a waystation'
            icon={MapPin}
            types={['region']}
            value={next}
            onChange={setNext}
            blocked={blocked}
          />
        </div>
        <Button
          size='sm'
          variant='outline'
          disabled={blocked !== null || next === null}
          disabledReason={
            blocked ?? (next === null ? 'Choose a region first' : undefined)
          }
          onClick={() => {
            if (next !== null) onChange([...line, next])
            setNext(null)
          }}
        >
          <Route />
          Extend the line
        </Button>
      </div>
    </div>
  )
}

function BattlePlan({
  row,
  armyId,
  blocked,
}: {
  row: RecordRow
  armyId: number
  blocked: string | null
}) {
  const actions = useRecordActions('army_profile', row.id, armyId)
  const [draft, setDraft] = useState<Values>({})
  const value = (key: string) => (key in draft ? draft[key] : row.values[key])
  const region = value('battle_region_id')
  return (
    <Adjust
      acts={[actions.save, actions.release, actions.remove]}
      title='Battle plan and camp'
      note='The tactic it opens with, how hard it drills, its fodder, its temper and where it means to fight. Held values bind the army.'
      label='Battle plan'
    >
      <FieldGrid>
        <ChoiceField
          label='Opening tactic'
          icon={Swords}
          value={String(value('tactic') ?? 'hold_line')}
          table={TACTIC}
          blocked={blocked}
          onPick={(next) => setDraft({ ...draft, tactic: next })}
        />
        <NumberField
          label='Drill'
          icon={Dumbbell}
          value={String(value('drill') ?? 0)}
          max={PERCENT}
          onChange={(next) => setDraft({ ...draft, drill: next })}
        />
        <NumberField
          label='Fodder (days)'
          icon={Wheat}
          value={String(value('fodder_days') ?? 0)}
          onChange={(next) => setDraft({ ...draft, fodder_days: next })}
        />
        <NumberField
          label='Mutiny'
          icon={ShieldAlert}
          value={String(value('mutiny') ?? 0)}
          max={PERCENT}
          onChange={(next) => setDraft({ ...draft, mutiny: next })}
        />
        <EntityPicker
          label='Seek battle in'
          icon={MapPin}
          types={['region']}
          value={typeof region === 'number' ? region : null}
          onChange={(next) => setDraft({ ...draft, battle_region_id: next })}
          blocked={blocked}
        />
      </FieldGrid>
      <SupplyLine
        line={supplyLine(value('supply_line'))}
        onChange={(next) => setDraft({ ...draft, supply_line: next })}
        blocked={blocked}
      />
      <RecordButtons
        actions={actions}
        values={numbersOf(draft, PROFILE_NUMBERS)}
        locked={row.locked}
        blocked={blocked}
        deletable={false}
      />
    </Adjust>
  )
}

function Leadership({
  armyId,
  blocked,
}: {
  armyId: number
  blocked: string | null
}) {
  const [commander, setCommander] = useState<number | null>(null)
  const [owner, setOwner] = useState<number | null>(null)
  const assign = useGodAction({
    writes: [{ lever: 'army:assign' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/army:assign', {
          body: { army_id: armyId, commander_id: commander, owner_id: owner },
        })
      ),
    invalidate: [['entities'], ['military']],
  })
  const busy = busyOf(blocked, assign.isPending)
  return (
    <Adjust
      acts={[assign]}
      title='Command and allegiance'
      note='Hand the army to a new commander, or have it swear to another community.'
      label='Change command'
    >
      <FieldGrid>
        <EntityPicker
          label='Commander'
          icon={Crown}
          types={['mortal']}
          value={commander}
          onChange={setCommander}
          blocked={blocked}
        />
        <EntityPicker
          label='Serves'
          icon={Flag}
          types={COMMUNITIES}
          value={owner}
          onChange={setOwner}
          blocked={blocked}
        />
      </FieldGrid>
      <Button
        act={assign}
        size='sm'
        className='self-start'
        disabled={busy !== null || (commander === null && owner === null)}
        disabledReason={
          busy ??
          (commander === null && owner === null
            ? 'Choose a commander or a community'
            : undefined)
        }
        onClick={() => assign.mutate()}
      >
        <Crown />
        Hand over
      </Button>
    </Adjust>
  )
}

function OfficerCard({
  row,
  armyId,
  blocked,
}: {
  row: RecordRow
  armyId: number
  blocked: string | null
}) {
  const actions = useRecordActions('officer', row.id, armyId)
  const [role, setRole] = useState(String(row.values.role))
  const mortal = row.refs.mortal_entity_id
  const post = nameOf(ROLE, String(row.values.role))
  const ended =
    row.values.until_epoch !== null && row.values.until_epoch !== undefined
  return (
    <li className='@container/mil flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-2.5'>
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion
          icon={post.icon}
          tone={ended ? 'muted' : post.tone}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          {mortal ? (
            <EntityLink kind='entity' id={String(mortal.id)}>
              {mortal.name}
            </EntityLink>
          ) : (
            <Text as='span'>An officer</Text>
          )}
          <Muted as='span' variant='caption' truncate>
            {ended
              ? `${post.label}, until epoch ${String(row.values.until_epoch)}`
              : `${post.label} since epoch ${String(row.values.since_epoch)}`}
          </Muted>
        </div>
        <Held locked={row.locked} />
      </div>
      <Adjust
        acts={[actions.save, actions.release, actions.remove]}
        title='Officer'
        note='Give the officer another post, or strike the appointment.'
      >
        <FieldGrid>
          <ChoiceField
            label='Post'
            icon={Award}
            value={role}
            table={ROLE}
            blocked={blocked}
            onPick={setRole}
          />
        </FieldGrid>
        <RecordButtons
          actions={actions}
          values={role !== String(row.values.role) ? { role } : {}}
          locked={row.locked}
          blocked={blocked}
          removeLabel='Dismiss'
        />
      </Adjust>
    </li>
  )
}

function Officers({
  armyId,
  blocked,
}: {
  armyId: number
  blocked: string | null
}) {
  const officers = useRecords('officer', armyId)
  const create = useRecordCreate('officer', armyId)
  const [mortal, setMortal] = useState<number | null>(null)
  const [role, setRole] = useState('sub_commander')
  const rows = officers.data?.rows ?? []
  const serving = rows.filter(
    (row) =>
      row.values.until_epoch === null || row.values.until_epoch === undefined
  )
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Label variant='overline'>Officers</Label>
        <Plain icon={Users}>{`${serving.length} serving`}</Plain>
      </div>
      {rows.length === 0 ? (
        <EmptyState
          icon={Award}
          title='No officers'
          description='Appoint a commander, quartermaster, standard bearer or surgeon.'
        />
      ) : (
        <ul className='grid min-w-0 grid-cols-1 gap-2 @xl/mil:grid-cols-2 @5xl/mil:grid-cols-3'>
          <Paged items={rows} as='li'>
            {(row) => (
              <OfficerCard
                key={row.id}
                row={row}
                armyId={armyId}
                blocked={blocked}
              />
            )}
          </Paged>
        </ul>
      )}
      <Adjust
        acts={[create]}
        title='Appoint an officer'
        note='A living mortal takes a post in this army.'
        label='Appoint'
      >
        <FieldGrid>
          <EntityPicker
            label='Mortal'
            icon={Users}
            types={['mortal']}
            value={mortal}
            onChange={setMortal}
            blocked={blocked}
          />
          <ChoiceField
            label='Post'
            icon={Award}
            value={role}
            table={ROLE}
            blocked={blocked}
            onPick={setRole}
          />
        </FieldGrid>
        <Button
          act={create}
          size='sm'
          className='self-start'
          disabled={
            busyOf(blocked, create.isPending) !== null || mortal === null
          }
          disabledReason={
            busyOf(blocked, create.isPending) ??
            (mortal === null ? 'Choose a mortal' : undefined)
          }
          onClick={() =>
            create.mutate({
              army_entity_id: armyId,
              mortal_entity_id: mortal,
              role,
            })
          }
        >
          <Award />
          Appoint
        </Button>
      </Adjust>
    </div>
  )
}

export function ArmyOrders({
  armyId,
  blocked,
}: {
  armyId: number
  blocked: string | null
}) {
  const profile = useRecords('army_profile', armyId)
  const row = profile.data?.rows[0]
  const tactic = row
    ? nameOf(TACTIC, String(row.values.tactic ?? 'hold_line'))
    : null
  const mutiny = Number(row?.values.mutiny ?? 0)
  const region = row?.refs.battle_region_id
  return (
    <Panel
      title='Command'
      icon={Crown}
      tone='gold'
      hint='Battle plan, camp, officers and allegiance'
    >
      <div data-surface='ArmyDepth' className='flex min-w-0 flex-col gap-3'>
        {row && tactic && (
          <>
            <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
              <Tag
                item={tactic}
                text={`Opens with ${tactic.label.toLowerCase()}`}
              />
              {region && (
                <Tag
                  item={{
                    label: `Seeks battle in ${region.name}`,
                    icon: MapPin,
                    tone: 'danger',
                  }}
                />
              )}
              <Plain
                icon={Route}
              >{`${supplyLine(row.values.supply_line).length} ${supplyLine(row.values.supply_line).length === 1 ? 'waystation' : 'waystations'}`}</Plain>
              <Plain
                icon={CalendarDays}
              >{`Orders of epoch ${String(row.values.updated_epoch ?? '—')}`}</Plain>
              <Held locked={row.locked} />
            </div>
            <div className='grid min-w-0 grid-cols-1 gap-2 @lg/mil:grid-cols-3'>
              <StatBar
                label='Drill'
                icon={Dumbbell}
                value={Number(row.values.drill ?? 0)}
                max={PERCENT}
                tone='info'
              />
              <StatBar
                label='Fodder (days)'
                icon={Wheat}
                value={Math.min(PERCENT, Number(row.values.fodder_days ?? 0))}
                max={PERCENT}
                tone='success'
              />
              <StatBar
                label='Mutiny'
                icon={ShieldAlert}
                value={mutiny}
                max={PERCENT}
                tone={mutiny >= MUTINY_WARN ? 'destructive' : 'warning'}
              />
            </div>
            <div className='flex min-w-0 flex-col gap-2'>
              <BattlePlan row={row} armyId={armyId} blocked={blocked} />
              <Leadership armyId={armyId} blocked={blocked} />
            </div>
          </>
        )}
        <Officers armyId={armyId} blocked={blocked} />
      </div>
    </Panel>
  )
}

export function StackArms({
  armyId,
  stackId,
  kind,
  blocked,
}: {
  armyId: number
  stackId: number
  kind: string
  blocked: string | null
}) {
  const stacks = useRecords('stack', armyId)
  const designs = useRecords('unit_design', null)
  const row = stacks.data?.rows.find((item) => item.id === stackId)
  const actions = useRecordActions('stack', stackId, armyId)
  const [draft, setDraft] = useState<Values>({})
  if (!row) return null
  const value = (key: string) => (key in draft ? draft[key] : row.values[key])
  const weapons = Array.isArray(value('weapons'))
    ? (value('weapons') as string[])
    : []
  const origin = value('origin_entity_id')
  const fitting = (designs.data?.rows ?? []).filter(
    (design) => design.values.base_kind === kind && !design.values.retired
  )
  const designTable = {
    none: { label: 'The common kind', icon: Swords, tone: 'muted' as const },
    ...Object.fromEntries(
      fitting.map((design) => [
        String(design.id),
        {
          label: String(design.values.name),
          icon: Award,
          tone: 'gold' as const,
        },
      ])
    ),
  }
  const design = value('design_id')
  return (
    <div className='flex min-w-0 flex-col gap-2 border-t pt-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Label variant='overline'>Arms, origin and design</Label>
        <Held locked={row.locked} />
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 @sm/stack:grid-cols-2'>
        {Object.entries(WEAPON).map(([key, item]) => (
          <ToggleField
            key={key}
            item={item}
            checked={weapons.includes(key)}
            disabled={blocked !== null}
            onChange={(on) =>
              setDraft({
                ...draft,
                weapons: on
                  ? [...weapons, key]
                  : weapons.filter((entry) => entry !== key),
              })
            }
          />
        ))}
        <ChoiceField
          label='Forged of'
          icon={Award}
          value={String(value('material') ?? 'wood')}
          table={MATERIAL}
          blocked={blocked}
          onPick={(next) => setDraft({ ...draft, material: next })}
        />
        <ChoiceField
          label='Drawn from'
          icon={Users}
          value={String(value('social_class') ?? 'farmer')}
          table={SOCIAL_CLASS}
          blocked={blocked}
          onPick={(next) => setDraft({ ...draft, social_class: next })}
        />
        <ChoiceField
          label='Design'
          icon={Award}
          value={
            design === null || design === undefined ? 'none' : String(design)
          }
          table={designTable}
          blocked={blocked}
          onPick={(next) =>
            setDraft({
              ...draft,
              design_id: next === 'none' ? null : Number(next),
            })
          }
        />
        <EntityPicker
          label='Levied from'
          icon={Flag}
          types={COMMUNITIES}
          value={typeof origin === 'number' ? origin : null}
          onChange={(next) => setDraft({ ...draft, origin_entity_id: next })}
          blocked={blocked}
        />
      </div>
      <RecordButtons
        actions={actions}
        values={draft}
        locked={row.locked}
        blocked={blocked}
        deletable={false}
      />
    </div>
  )
}

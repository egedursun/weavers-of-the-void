import { useState } from 'react'
import {
  Castle,
  Flag,
  Handshake,
  Map as MapIcon,
  Megaphone,
  Moon,
  Save,
  Skull,
  Swords,
  Target,
  Trash2,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  captiveFateValues,
  siegeStatusValues,
  starvationStageValues,
  warAimKindValues,
} from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import {
  EmptyState,
  EntityLink,
  StatBar,
  Timeline,
  TimelineItem,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { MindPicker } from '@/features/entity/mind/parts'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { ArmyPanel, NumberBox } from './ArmyPanel'
import {
  type BattleReport,
  type CaptiveCohort,
  type Occupation,
  type SiegeTracker,
  type WarAimKind,
  type WarRoom as Room,
  table,
  useWarRoom,
  words,
} from './api'

const PERCENT = 100
const WORKING = 'Working…'
const SIEGE_NUMBERS = [
  'supplies',
  'water',
  'breaches',
  'walls_level',
  'disease_inside',
  'disease_outside',
  'sallies',
] as const
type SiegeNumber = (typeof SIEGE_NUMBERS)[number]

function busyOf(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

function Weariness({ room, blocked }: { room: Room; blocked: string | null }) {
  return (
    <div
      data-surface='WarWeariness'
      className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'
    >
      {room.weariness.map((side) => (
        <WearinessRow
          key={side.entity?.id ?? side.side}
          warId={room.war.id}
          side={side}
          blocked={blocked}
        />
      ))}
    </div>
  )
}

function WearinessRow({
  warId,
  side,
  blocked,
}: {
  warId: number
  side: Room['weariness'][number]
  blocked: string | null
}) {
  const [value, setValue] = useState(String(side.weariness))
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/war:weariness', {
          body: {
            war_id: warId,
            side_id: side.entity?.id ?? 0,
            weariness: Math.max(
              0,
              Math.min(PERCENT, Math.round(Number(value) || 0))
            ),
          },
        })
      ),
  })
  const allies = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/war:call_allies', {
          body: { war_id: warId, side_id: side.entity?.id ?? 0 },
        })
      ),
  })
  const busy = busyOf(blocked, save.isPending, allies.isPending)
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'>
      <StatBar
        label={`${side.entity?.name ?? 'A side'} (${side.side})`}
        value={side.weariness}
        max={PERCENT}
        tone={
          side.weariness >= 70
            ? 'destructive'
            : side.weariness >= 40
              ? 'warning'
              : 'default'
        }
      />
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <NumberBox
          label='Weariness'
          value={value}
          max={PERCENT}
          onChange={setValue}
        />
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => save.mutate(undefined)}
        >
          <Save />
          Set
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => allies.mutate(undefined)}
        >
          <Megaphone />
          Call the allies
        </Button>
      </div>
    </div>
  )
}

function AimRow({
  warId,
  aim,
  blocked,
}: {
  warId: number
  aim: Room['aims'][number]
  blocked: string | null
}) {
  const [achieved, setAchieved] = useState(String(aim.achieved))
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/war:aim', {
          body: {
            war_id: warId,
            side_id: aim.side?.id ?? 0,
            kind: aim.kind,
            target_id: aim.target?.id ?? null,
            achieved: Math.max(
              0,
              Math.min(PERCENT, Math.round(Number(achieved) || 0))
            ),
          },
        })
      ),
  })
  const drop = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/war:drop_aim', { body: { aim_id: aim.id } })
      ),
  })
  const busy = busyOf(blocked, save.isPending, drop.isPending)
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Badge variant='info'>{words(aim.kind)}</Badge>
        <Text as='span'>{aim.side?.name ?? ''}</Text>
        {aim.target && <Muted as='span'>{`→ ${aim.target.name}`}</Muted>}
      </div>
      <StatBar
        label='Achieved'
        value={aim.achieved}
        max={PERCENT}
        tone='success'
      />
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <NumberBox
          label='Achieved'
          value={achieved}
          max={PERCENT}
          onChange={setAchieved}
        />
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => save.mutate(undefined)}
        >
          <Save />
          Set
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => drop.mutate(undefined)}
        >
          <Trash2 />
          Abandon
        </Button>
      </div>
    </li>
  )
}

function Aims({ room, blocked }: { room: Room; blocked: string | null }) {
  const sides = Object.fromEntries(
    room.weariness.map((side) => [
      String(side.entity?.id ?? 0),
      side.entity?.name ?? side.side,
    ])
  )
  const [side, setSide] = useState(Object.keys(sides)[0] ?? '0')
  const [kind, setKind] = useState<string>('conquer_region')
  const add = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/war:aim', {
          body: {
            war_id: room.war.id,
            side_id: Number(side),
            kind: kind as WarAimKind,
            target_id: null,
            achieved: 0,
          },
        })
      ),
  })
  const busy = busyOf(blocked, add.isPending)
  return (
    <div data-surface='WarAims' className='flex min-w-0 flex-col gap-2'>
      {room.aims.length === 0 ? (
        <Muted>No side has named its aims yet.</Muted>
      ) : (
        <ul className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2'>
          {room.aims.map((aim) => (
            <AimRow
              key={aim.id}
              warId={room.war.id}
              aim={aim}
              blocked={blocked}
            />
          ))}
        </ul>
      )}
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <MindPicker
          label='Side'
          value={side}
          table={sides}
          blocked={busy}
          onPick={setSide}
        />
        <MindPicker
          label='Aim'
          value={kind}
          table={table(warAimKindValues)}
          blocked={busy}
          onPick={setKind}
        />
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => add.mutate(undefined)}
        >
          <Target />
          Add the aim
        </Button>
      </div>
    </div>
  )
}

function PeaceBuilder({
  room,
  blocked,
}: {
  room: Room
  blocked: string | null
}) {
  const sides = Object.fromEntries(
    room.weariness.map((side) => [
      String(side.entity?.id ?? 0),
      side.entity?.name ?? side.side,
    ])
  )
  const [victor, setVictor] = useState(Object.keys(sides)[0] ?? '0')
  const [terms, setTerms] = useState<WarAimKind[]>([])
  const impose = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/war:impose_peace', {
          body: { war_id: room.war.id, victor_id: Number(victor), terms },
        })
      ),
  })
  const busy =
    busyOf(blocked, impose.isPending) ??
    (room.war.status === 'ended' ? 'This war is over.' : null)
  return (
    <div data-surface='PeaceBuilder' className='flex min-w-0 flex-col gap-3'>
      <MindPicker
        label='The victor'
        value={victor}
        table={sides}
        blocked={busy}
        onPick={setVictor}
      />
      <div className='grid min-w-0 grid-cols-2 gap-2 md:grid-cols-4'>
        {warAimKindValues.map((kind) => (
          <label key={kind} className='flex items-center gap-2'>
            <Switch
              checked={terms.includes(kind)}
              disabled={busy !== null}
              aria-label={words(kind)}
              onCheckedChange={(checked) =>
                setTerms((current) =>
                  checked
                    ? [...current, kind]
                    : current.filter((item) => item !== kind)
                )
              }
            />
            <Text as='span'>{words(kind)}</Text>
          </label>
        ))}
      </div>
      <div>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => impose.mutate(undefined)}
        >
          <Handshake />
          Impose the peace
        </Button>
      </div>
    </div>
  )
}

function SiegeCard({
  siege,
  blocked,
}: {
  siege: SiegeTracker
  blocked: string | null
}) {
  const [numbers, setNumbers] = useState<Record<SiegeNumber, string>>(
    () =>
      Object.fromEntries(
        SIEGE_NUMBERS.map((key) => [key, String(siege[key])])
      ) as Record<SiegeNumber, string>
  )
  const [starvation, setStarvation] = useState<string>(siege.starvation)
  const [status, setStatus] = useState<string>(siege.status)
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/siege:edit', {
          body: {
            siege_id: siege.id,
            values: {
              ...Object.fromEntries(
                SIEGE_NUMBERS.map((key) => [
                  key,
                  Math.max(0, Math.round(Number(numbers[key]) || 0)),
                ])
              ),
              starvation,
              status,
            },
          },
        })
      ),
  })
  const busy = busyOf(blocked, save.isPending)
  return (
    <li
      data-surface='SiegeTracker'
      className='flex min-w-0 flex-col gap-3 rounded-lg border bg-muted/30 p-3'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Castle
          aria-hidden='true'
          className='size-icon-sm text-muted-foreground'
        />
        <Text as='span' weight='semibold'>
          {siege.besieged?.name ?? 'A city'}
        </Text>
        <Muted as='span'>{`besieged by ${siege.besieger?.name ?? 'an enemy'}`}</Muted>
        <Badge variant={siege.status === 'ongoing' ? 'warning' : 'outline'}>
          {words(siege.status)}
        </Badge>
        <Badge variant='outline'>{`${siege.rounds} seasons`}</Badge>
        {siege.starvation !== 'none' && (
          <Badge variant='destructive'>{words(siege.starvation)}</Badge>
        )}
        {siege.last_action && (
          <Badge variant='outline'>{`Besiegers: ${words(siege.last_action)}`}</Badge>
        )}
        {siege.last_defence && (
          <Badge variant='outline'>{`Defenders: ${words(siege.last_defence)}`}</Badge>
        )}
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-4'>
        <StatBar
          label='Food (days)'
          value={siege.supplies}
          max={Math.max(siege.supplies, 180)}
          tone={siege.supplies <= 0 ? 'destructive' : 'default'}
        />
        <StatBar
          label='Water (days)'
          value={siege.water}
          max={Math.max(siege.water, 120)}
          tone={siege.water <= 0 ? 'destructive' : 'info'}
        />
        <StatBar
          label='Sickness inside'
          value={siege.disease_inside}
          max={PERCENT}
          tone='warning'
        />
        <StatBar
          label='Sickness outside'
          value={siege.disease_outside}
          max={PERCENT}
          tone='warning'
        />
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
        {SIEGE_NUMBERS.map((key) => (
          <NumberBox
            key={key}
            label={words(key)}
            value={numbers[key]}
            onChange={(value) =>
              setNumbers((current) => ({ ...current, [key]: value }))
            }
          />
        ))}
        <MindPicker
          label='Hunger'
          value={starvation}
          table={table(starvationStageValues)}
          blocked={busy}
          onPick={setStarvation}
        />
        <MindPicker
          label='Standing'
          value={status}
          table={table(siegeStatusValues)}
          blocked={busy}
          onPick={setStatus}
        />
      </div>
      <div>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => save.mutate(undefined)}
        >
          <Save />
          Save the siege
        </Button>
      </div>
    </li>
  )
}

export function OccupationRow({
  occupation,
  blocked,
}: {
  occupation: Occupation
  blocked: string | null
}) {
  const [control, setControl] = useState(String(occupation.control))
  const [resistance, setResistance] = useState(String(occupation.resistance))
  const region = occupation.region?.id ?? 0
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/occupation:edit', {
          body: {
            region_id: region,
            control: Math.max(
              0,
              Math.min(PERCENT, Math.round(Number(control) || 0))
            ),
            resistance: Math.max(
              0,
              Math.min(PERCENT, Math.round(Number(resistance) || 0))
            ),
            end: false,
          },
        })
      ),
  })
  const end = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/occupation:edit', {
          body: { region_id: region, end: true },
        })
      ),
  })
  const busy = busyOf(blocked, save.isPending, end.isPending)
  return (
    <li
      data-surface='Occupation'
      className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'
    >
      <Text as='span'>{`${occupation.region?.name ?? 'A land'} held by ${occupation.occupier?.name ?? 'an enemy'} since epoch ${occupation.since_epoch}`}</Text>
      <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
        <StatBar label='Control' value={occupation.control} max={PERCENT} />
        <StatBar
          label='Resistance'
          value={occupation.resistance}
          max={PERCENT}
          tone='destructive'
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <NumberBox
          label='Control'
          value={control}
          max={PERCENT}
          onChange={setControl}
        />
        <NumberBox
          label='Resistance'
          value={resistance}
          max={PERCENT}
          onChange={setResistance}
        />
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => save.mutate(undefined)}
        >
          <Save />
          Set
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => end.mutate(undefined)}
        >
          <Flag />
          End the occupation
        </Button>
      </div>
    </li>
  )
}

export function CohortRow({
  cohort,
  blocked,
}: {
  cohort: CaptiveCohort
  blocked: string | null
}) {
  const [fate, setFate] = useState<string>(cohort.fate)
  const [count, setCount] = useState(String(cohort.count))
  const settle = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/captives:settle', {
          body: {
            cohort_id: cohort.id,
            fate: fate as CaptiveCohort['fate'],
            count: Math.max(0, Math.round(Number(count) || 0)),
          },
        })
      ),
  })
  const busy = busyOf(blocked, settle.isPending)
  return (
    <li
      data-surface='CaptiveCohort'
      className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Users
          aria-hidden='true'
          className='size-icon-sm text-muted-foreground'
        />
        <Text as='span'>{`${formatInteger(cohort.count)} ${words(cohort.social_class)} of ${cohort.origin?.name ?? 'the enemy'}`}</Text>
        <Muted as='span'>{`held by ${cohort.captor?.name ?? ''}`}</Muted>
        <Badge variant={cohort.fate === 'held' ? 'warning' : 'outline'}>
          {words(cohort.fate)}
        </Badge>
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <MindPicker
          label='Fate'
          value={fate}
          table={table(captiveFateValues)}
          blocked={busy}
          onPick={setFate}
        />
        <NumberBox label='Captives' value={count} onChange={setCount} />
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => settle.mutate(undefined)}
        >
          <Save />
          Decide
        </Button>
      </div>
    </li>
  )
}

export function BattleReportView({ battle }: { battle: BattleReport }) {
  const kinds = Object.entries(battle.casualties_by_kind).sort(
    (first, second) => second[1] - first[1]
  )
  const worst = Math.max(1, ...kinds.map(([, value]) => value))
  return (
    <article
      data-surface='BattleReport'
      className='flex min-w-0 flex-col gap-3 rounded-lg border bg-card p-4'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Swords
          aria-hidden='true'
          className='size-icon-sm text-muted-foreground'
        />
        {battle.record ? (
          <EntityLink kind='entity' id={String(battle.record.id)}>
            {battle.record.name}
          </EntityLink>
        ) : (
          <Text as='span' weight='semibold'>{`Clash #${battle.sequence}`}</Text>
        )}
        {battle.outcome_class && (
          <Badge variant='info'>{words(battle.outcome_class)}</Badge>
        )}
        <Badge variant='outline'>{words(battle.outcome)}</Badge>
        {battle.terrain && (
          <Badge variant='outline'>{words(battle.terrain)}</Badge>
        )}
        {battle.weather && (
          <Badge variant='outline'>{words(battle.weather)}</Badge>
        )}
        {battle.night && (
          <Badge variant='outline'>
            <Moon />
            Night
          </Badge>
        )}
      </div>
      <Muted>
        {`${battle.winner?.name ?? 'One side'} beat ${battle.loser?.name ?? 'the other'}: ${formatInteger(battle.winner_losses)} against ${formatInteger(battle.loser_losses)} fallen.`}
        {battle.tactics_attacker && battle.tactics_defender
          ? ` ${words(battle.tactics_attacker)} against ${words(battle.tactics_defender)}.`
          : ''}
      </Muted>
      {battle.phases.length > 0 && (
        <Timeline label='Phases of the battle'>
          {battle.phases.map((phase, index) => (
            <TimelineItem
              key={phase.position}
              icon={phase.phase === 'aftermath' ? Skull : Swords}
              tone={
                phase.attacker_losses + phase.defender_losses > 0
                  ? 'destructive'
                  : 'default'
              }
              title={`${words(phase.phase)}: ${phase.summary ?? ''}`}
              timestamp={`${formatInteger(phase.attacker_losses)} / ${formatInteger(phase.defender_losses)}`}
              last={index === battle.phases.length - 1}
            />
          ))}
        </Timeline>
      )}
      {kinds.length > 0 && (
        <div className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-3'>
          {kinds.map(([kind, value]) => (
            <StatBar
              key={kind}
              label={words(kind)}
              value={value}
              max={worst}
              tone='destructive'
              showMax={false}
            />
          ))}
        </div>
      )}
    </article>
  )
}

function Block({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>{title}</Label>
      {children}
    </div>
  )
}

export function WarRoom({ warId }: { warId: number }) {
  const room = useWarRoom(warId)
  const { reason } = useGodGate()
  const blocked = reason()
  if (room.isPending) return <Skeleton className='h-textarea w-full' />
  if (room.isError)
    return (
      <EmptyState
        icon={Swords}
        title='No war room'
        description={room.error.message}
      />
    )
  const data = room.data
  return (
    <div data-surface='WarRoom' className='flex min-w-0 flex-col gap-5'>
      <Block title='War weariness'>
        <Weariness room={data} blocked={blocked} />
      </Block>
      <Block title='War aims'>
        <Aims room={data} blocked={blocked} />
      </Block>
      <Block title='Peace terms'>
        <PeaceBuilder room={data} blocked={blocked} />
      </Block>
      <Block title='Fronts'>
        {data.fronts.length === 0 ? (
          <Muted>The armies have not met yet.</Muted>
        ) : (
          <ul className='flex min-w-0 flex-wrap gap-2'>
            {data.fronts.map((front) => (
              <li key={`${front.first_region?.id}.${front.second_region?.id}`}>
                <Badge variant='outline'>
                  <MapIcon />
                  {`${front.first_region?.name ?? '?'} – ${front.second_region?.name ?? '?'} (${front.since_epoch}–${front.last_epoch})`}
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </Block>
      <Block title='Armies'>
        {data.armies.length === 0 ? (
          <Muted>No army marches in this war.</Muted>
        ) : (
          data.armies.map((army) => (
            <ArmyPanel key={army.army?.id} army={army} blocked={blocked} />
          ))
        )}
      </Block>
      <Block title='Sieges'>
        {data.sieges.length === 0 ? (
          <Muted>No walls are under siege.</Muted>
        ) : (
          <ul className='flex min-w-0 flex-col gap-2'>
            {data.sieges.map((siege) => (
              <SiegeCard key={siege.id} siege={siege} blocked={blocked} />
            ))}
          </ul>
        )}
      </Block>
      <Block title='Occupied lands'>
        {data.occupations.length === 0 ? (
          <Muted>No land is occupied.</Muted>
        ) : (
          <ul className='flex min-w-0 flex-col gap-2'>
            {data.occupations.map((item) => (
              <OccupationRow
                key={item.region?.id}
                occupation={item}
                blocked={blocked}
              />
            ))}
          </ul>
        )}
      </Block>
      <Block title='Captives'>
        {data.captives.length === 0 ? (
          <Muted>No one was led away.</Muted>
        ) : (
          <ul className='flex min-w-0 flex-col gap-2'>
            {data.captives.map((cohort) => (
              <CohortRow key={cohort.id} cohort={cohort} blocked={blocked} />
            ))}
          </ul>
        )}
      </Block>
      <Block title='Battle reports'>
        {data.battles.length === 0 ? (
          <Muted>No battle has been fought.</Muted>
        ) : (
          data.battles.map((battle) => (
            <BattleReportView key={battle.id} battle={battle} />
          ))
        )}
      </Block>
    </div>
  )
}

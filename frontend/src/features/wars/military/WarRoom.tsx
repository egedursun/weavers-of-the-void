import { useState } from 'react'
import {
  Biohazard,
  BrickWall,
  CalendarDays,
  ChevronDown,
  ChevronUp,
  Crown,
  Droplets,
  Flag,
  Crosshair,
  Lock,
  Map as MapIcon,
  MapPin,
  Megaphone,
  Moon,
  Save,
  Shield,
  Skull,
  Swords,
  Target,
  Trash2,
  Users,
  Wheat,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  EmptyState,
  EntityLink,
  type KpiTone,
  Medallion,
  MiniStat,
  StatBar,
  Timeline,
  TimelineItem,
  type TimelineTone,
  Paged,
} from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { TERRAIN, WEATHER } from '@/features/entity/environment/labels'
import { CLASS_SPEC } from '@/features/entity/society/labels'
import { IncitementCard } from '@/features/foundations/IncitementCard'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { ArmyPanel } from './ArmyPanel'
import { BattleDepthPanel } from './BattleDepth'
import { AimParams, SiegeDepth, WarLedger, WarOrders } from './Orders'
import { PeaceTreaty } from './PeaceBuilder'
import { WarMap } from './WarMap'
import {
  type BattleReport,
  type CaptiveCohort,
  type Occupation,
  type SiegeTracker,
  type WarAimKind,
  type WarRoom as Room,
  soldiersOf,
  useWarRoom,
} from './api'
import { EntityPicker } from './controls'
import { aimParamText } from './depth'
import {
  AIM,
  DEFENCE,
  FATE,
  OUTCOME,
  OUTCOME_CLASS,
  PERCENT,
  PHASE,
  PHASE_DETAIL,
  PROGRESS_TONE,
  SIDE,
  SIEGE_ACTION,
  SIEGE_STATUS,
  STARVATION,
  TACTIC,
  UNIT_ICON,
  WORKS,
  fieldLabel,
  named,
  percentTone,
  wearinessLevel,
  busyOf,
  cardGrid,
  frameTone,
  iconTone,
  whole,
} from './labels'
import {
  Adjust,
  ChoiceField,
  FieldGrid,
  NumberField,
  Panel,
  Pips,
  Plain,
  Quiet,
  Steps,
  TableTag,
  Tag,
  TugBar,
} from './parts'
import { useNameMap } from './recordHooks'

const SCORE_SCALE_MIN = 5
const FOOD_SCALE = 180
const WATER_SCALE = 120
const WALLS_MAX = 5
const SIEGE_NUMBERS = [
  'supplies',
  'water',
  'breaches',
  'walls_level',
  'disease_inside',
  'disease_outside',
  'sallies',
] as const
const SIEGE_MAX: Partial<Record<SiegeNumber, number>> = {
  walls_level: WALLS_MAX,
  disease_inside: PERCENT,
  disease_outside: PERCENT,
}
const SIEGE_ICON: Record<SiegeNumber, typeof Wheat> = {
  supplies: Wheat,
  water: Droplets,
  breaches: BrickWall,
  walls_level: BrickWall,
  disease_inside: Biohazard,
  disease_outside: Biohazard,
  sallies: Swords,
}
const TIMELINE_TONE: Record<KpiTone, TimelineTone> = {
  gold: 'primary',
  verdigris: 'success',
  info: 'default',
  success: 'success',
  warning: 'warning',
  danger: 'destructive',
  muted: 'default',
}
type SiegeNumber = (typeof SIEGE_NUMBERS)[number]
type SideEntry = {
  id: number
  name: string
  side: string
  weariness: number
  left: number | null
}

const AIM_TARGETS = [
  'region',
  'settlement',
  'place',
  'resource',
  'cult',
  'polity',
  'people',
  'faction',
  'house',
]

function sideEntries(room: Room): SideEntry[] {
  const weariness = new Map(
    room.weariness.map((item) => [item.entity?.id ?? 0, item.weariness])
  )
  return room.war.sides.map((side) => ({
    id: side.entity?.id ?? 0,
    name: side.entity?.name ?? 'A people',
    side: side.side,
    weariness: weariness.get(side.entity?.id ?? 0) ?? 0,
    left: side.left_epoch,
  }))
}

function sideTable(room: Room) {
  return Object.fromEntries(
    sideEntries(room).map((entry) => [
      String(entry.id),
      { ...named(SIDE, entry.side), label: entry.name },
    ])
  )
}

function WearinessEditor({
  warId,
  entry,
  blocked,
}: {
  warId: number
  entry: SideEntry
  blocked: string | null
}) {
  const [value, setValue] = useState(String(entry.weariness))
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/war:weariness', {
          body: {
            war_id: warId,
            side_id: entry.id,
            weariness: whole(value, PERCENT),
          },
        })
      ),
  })
  const allies = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/war:call_allies', {
          body: { war_id: warId, side_id: entry.id },
        })
      ),
  })
  const busy = busyOf(blocked, save.isPending, allies.isPending)
  const side = named(SIDE, entry.side)
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-2.5'>
      <div className='flex min-w-0 items-center gap-2'>
        <side.icon
          aria-hidden='true'
          className={cn('size-icon-sm shrink-0', iconTone(side.tone))}
        />
        <Text as='span' weight='medium' truncate className='min-w-0 flex-1'>
          {entry.name}
        </Text>
        <Tag item={side} />
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <div className='min-w-0 flex-1 basis-32'>
          <NumberField
            label='Weariness'
            icon={wearinessLevel(entry.weariness).icon}
            value={value}
            max={PERCENT}
            framed={false}
            onChange={setValue}
          />
        </div>
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

function AimEditor({
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
            achieved: whole(achieved, PERCENT),
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
  const item = named(AIM, aim.kind)
  return (
    <li className='@container/mil flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-2.5'>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Tag item={item} />
        <Muted as='span' variant='caption' truncate>
          {`${aim.side?.name ?? ''}${aim.target ? ` → ${aim.target.name}` : ''}`}
        </Muted>
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <div className='min-w-0 flex-1 basis-32'>
          <NumberField
            label='Achieved'
            icon={Target}
            value={achieved}
            max={PERCENT}
            framed={false}
            onChange={setAchieved}
          />
        </div>
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
      <AimParams
        aimId={aim.id}
        kind={aim.kind}
        params={aim.params ?? {}}
        locked={aim.locked ?? []}
        warId={warId}
        blocked={blocked}
      />
    </li>
  )
}

function AddAim({ room, blocked }: { room: Room; blocked: string | null }) {
  const sides = sideTable(room)
  const [side, setSide] = useState(Object.keys(sides)[0] ?? '0')
  const [kind, setKind] = useState<string>('conquer_region')
  const [target, setTarget] = useState<number | null>(null)
  const add = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/war:aim', {
          body: {
            war_id: room.war.id,
            side_id: Number(side),
            kind: kind as WarAimKind,
            target_id: target,
            achieved: 0,
          },
        })
      ),
  })
  const busy = busyOf(blocked, add.isPending)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <FieldGrid>
        <ChoiceField
          label='Side'
          icon={Flag}
          value={side}
          table={sides}
          blocked={busy}
          onPick={setSide}
        />
        <ChoiceField
          label='Aim'
          icon={Target}
          value={kind}
          table={AIM}
          blocked={busy}
          onPick={setKind}
        />
        <EntityPicker
          label='Against'
          icon={Crosshair}
          types={AIM_TARGETS}
          value={target}
          onChange={setTarget}
          blocked={busy}
        />
      </FieldGrid>
      <div>
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

function WarControls({
  room,
  blocked,
}: {
  room: Room
  blocked: string | null
}) {
  return (
    <Adjust
      label='Command the war'
      title='Weariness and aims'
      note='How weary each side is, what each fights for and what winning will demand. Every change goes into the ledger and can be undone.'
    >
      <div className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>War weariness</Label>
        <div
          data-surface='WarWeariness'
          className='grid min-w-0 grid-cols-1 gap-2 @xl/mil:grid-cols-2'
        >
          {sideEntries(room).map((entry) => (
            <WearinessEditor
              key={entry.id}
              warId={room.war.id}
              entry={entry}
              blocked={blocked}
            />
          ))}
        </div>
      </div>
      <div data-surface='WarAims' className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>War aims</Label>
        {room.aims.length > 0 && (
          <ul className='grid min-w-0 grid-cols-1 gap-2 @xl/mil:grid-cols-2 @5xl/mil:grid-cols-4'>
            <Paged items={room.aims} as='li'>
              {(aim) => (
                <AimEditor
                  key={aim.id}
                  warId={room.war.id}
                  aim={aim}
                  blocked={blocked}
                />
              )}
            </Paged>
          </ul>
        )}
        <AddAim room={room} blocked={blocked} />
      </div>
    </Adjust>
  )
}

function AimLine({ aim }: { aim: Room['aims'][number] }) {
  const item = named(AIM, aim.kind)
  const done = aim.achieved >= PERCENT
  const names = useNameMap()
  const terms = aimParamText(aim.kind, aim.params ?? {}, names)
  return (
    <li className='flex min-w-0 items-center gap-2.5 rounded-lg border bg-background/70 p-2'>
      <Medallion icon={item.icon} tone={item.tone} size='sm' />
      <div className='flex min-w-0 flex-1 flex-col gap-1'>
        <div className='flex min-w-0 items-center gap-2'>
          <Text as='span' weight='medium' truncate className='min-w-0 flex-1'>
            {item.label}
          </Text>
          <Stat value={aim.achieved} unit='%' className='shrink-0' />
        </div>
        <Progress
          size='sm'
          value={aim.achieved}
          tone={done ? 'success' : 'default'}
          aria-label={`${item.label} achieved`}
        />
        {terms && (
          <Text as='span' variant='caption' weight='medium' truncate>
            {terms}
          </Text>
        )}
        {aim.target && (
          <Muted as='span' variant='caption' truncate>
            {`Against ${aim.target.name}`}
          </Muted>
        )}
      </div>
    </li>
  )
}

function SideCard({
  room,
  side,
}: {
  room: Room
  side: 'attacker' | 'defender'
}) {
  const item = named(SIDE, side)
  const entries = sideEntries(room).filter((entry) => entry.side === side)
  const ids = new Set(entries.map((entry) => entry.id))
  const aims = room.aims.filter((aim) => ids.has(aim.side?.id ?? 0))
  const victor = room.war.victor?.id ?? null
  return (
    <div
      className={cn(
        'flex min-w-0 flex-1 flex-col gap-3 rounded-xl border p-3',
        frameTone(item.tone)
      )}
    >
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion icon={item.icon} tone={item.tone} />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Label variant='overline'>{item.label}</Label>
          <Muted as='span' variant='caption'>
            {`${entries.length} ${entries.length === 1 ? 'member' : 'members'} · ${aims.length} ${aims.length === 1 ? 'aim' : 'aims'}`}
          </Muted>
        </div>
        {entries.some((entry) => entry.id === victor) && (
          <Badge variant='default'>
            <Crown />
            Victor
          </Badge>
        )}
      </div>
      {entries.length === 0 ? (
        <Muted variant='caption'>No one stands here.</Muted>
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={entries} as='li'>
            {(entry) => {
              const level = wearinessLevel(entry.weariness)
              return (
                <li
                  key={entry.id}
                  className='flex min-w-0 flex-col gap-1.5 rounded-lg border bg-background/70 p-2'
                >
                  <div className='flex min-w-0 items-center gap-2'>
                    {entry.id === victor && (
                      <Crown
                        aria-label='Victor'
                        className='size-icon-sm shrink-0 text-primary'
                      />
                    )}
                    <span className='min-w-0 flex-1 truncate'>
                      <EntityLink kind='entity' id={String(entry.id)}>
                        {entry.name}
                      </EntityLink>
                    </span>
                    {entry.left !== null && (
                      <Plain icon={Flag}>{`Left ${entry.left}`}</Plain>
                    )}
                    <Tag item={level} />
                  </div>
                  <div className='flex min-w-0 items-center gap-2'>
                    <Label className='shrink-0'>Weariness</Label>
                    <Progress
                      size='sm'
                      value={entry.weariness}
                      tone={PROGRESS_TONE[level.tone ?? 'muted']}
                      aria-label={`${entry.name} weariness`}
                      className='flex-1'
                    />
                    <Stat
                      value={entry.weariness}
                      unit='%'
                      className='shrink-0'
                    />
                  </div>
                </li>
              )
            }}
          </Paged>
        </ul>
      )}
      {aims.length > 0 && (
        <div className='flex min-w-0 flex-col gap-1.5'>
          <Label>War aims</Label>
          <ul className='grid min-w-0 grid-cols-1 gap-1.5 @5xl/mil:grid-cols-2'>
            <Paged items={aims} as='li'>
              {(aim) => <AimLine key={aim.id} aim={aim} />}
            </Paged>
          </ul>
        </div>
      )}
    </div>
  )
}

function Versus({ room }: { room: Room }) {
  const score = room.war.score
  return (
    <div
      data-surface='WarVersus'
      className='flex min-w-0 flex-col gap-3 rounded-xl border bg-card p-3'
    >
      <div className='flex min-w-0 flex-col items-stretch gap-2 @xl/mil:flex-row'>
        <SideCard room={room} side='attacker' />
        <span className='flex shrink-0 items-center justify-center'>
          <Medallion icon={Swords} tone='gold' />
        </span>
        <SideCard room={room} side='defender' />
      </div>
      <TugBar
        left='Attackers push'
        right='Defenders push'
        value={score}
        scale={Math.max(SCORE_SCALE_MIN, Math.abs(score))}
        label={
          score === 0
            ? 'momentum, even'
            : `momentum, ${score > 0 ? 'attackers' : 'defenders'} ahead`
        }
      />
    </div>
  )
}

function RoomStats({ room }: { room: Room }) {
  const fallen = room.battles.reduce(
    (sum, battle) => sum + battle.winner_losses + battle.loser_losses,
    0
  )
  const soldiers = room.armies.reduce((sum, army) => sum + soldiersOf(army), 0)
  const ongoing = room.sieges.filter((siege) => siege.status === 'ongoing')
  const captives = room.captives.reduce((sum, cohort) => sum + cohort.count, 0)
  return (
    <div className='grid min-w-0 grid-cols-2 gap-2 @xl/mil:grid-cols-3 @5xl/mil:grid-cols-6'>
      <MiniStat
        icon={Swords}
        label='Battles fought'
        value={formatInteger(room.war.battles)}
        tone='danger'
      />
      <MiniStat
        icon={Skull}
        label='Fallen in battle'
        value={formatInteger(fallen)}
        tone='danger'
        hint='Both sides, every reported battle'
      />
      <MiniStat
        icon={Users}
        label='Soldiers in the field'
        value={formatInteger(soldiers)}
        tone='gold'
        hint={`${room.armies.length} ${room.armies.length === 1 ? 'army' : 'armies'}`}
      />
      <MiniStat
        icon={SIEGE_STATUS.ongoing.icon}
        label='Sieges'
        value={`${ongoing.length} / ${room.sieges.length}`}
        tone='warning'
        hint='Still under siege, then all sieges'
      />
      <MiniStat
        icon={Flag}
        label='Lands occupied'
        value={formatInteger(room.occupations.length)}
        tone='warning'
      />
      <MiniStat
        icon={Lock}
        label='Captives taken'
        value={formatInteger(captives)}
        tone='muted'
      />
    </div>
  )
}

function SiegeEditor({
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
                  whole(numbers[key], SIEGE_MAX[key]),
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
    <Adjust
      title='Shape the siege'
      note='Stores, walls and sickness on both sides of the walls. The next season goes on from what you set.'
    >
      <div className='grid min-w-0 grid-cols-1 gap-2 @sm/siege:grid-cols-2'>
        {SIEGE_NUMBERS.map((key) => (
          <NumberField
            key={key}
            label={fieldLabel(key)}
            icon={SIEGE_ICON[key]}
            value={numbers[key]}
            max={SIEGE_MAX[key]}
            onChange={(value) =>
              setNumbers((current) => ({ ...current, [key]: value }))
            }
          />
        ))}
        <ChoiceField
          label='Hunger'
          icon={Wheat}
          value={starvation}
          table={STARVATION}
          blocked={busy}
          onPick={setStarvation}
        />
        <ChoiceField
          label='Standing'
          icon={Flag}
          value={status}
          table={SIEGE_STATUS}
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
    </Adjust>
  )
}

function SiegeCard({
  siege,
  blocked,
}: {
  siege: SiegeTracker
  blocked: string | null
}) {
  const status = named(SIEGE_STATUS, siege.status)
  const works = Object.entries(siege.works).filter(([, value]) => value > 0)
  return (
    <li
      data-surface='SiegeTracker'
      className='@container/siege flex min-w-0 flex-col gap-3 rounded-xl border bg-background p-3'
    >
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion icon={status.icon} tone={status.tone} />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          {siege.besieged ? (
            <EntityLink kind='entity' id={String(siege.besieged.id)}>
              {siege.besieged.name}
            </EntityLink>
          ) : (
            <Text as='span' weight='semibold'>
              A city
            </Text>
          )}
          <Muted as='span' variant='caption' truncate>
            {`Besieged by ${siege.besieger?.name ?? 'an enemy'}`}
          </Muted>
        </div>
        <div className='flex shrink-0 flex-col items-end'>
          <Stat value={siege.rounds} size='kpi' />
          <Label>{siege.rounds === 1 ? 'Season' : 'Seasons'}</Label>
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap gap-1'>
        <Tag item={status} />
        <Plain icon={CalendarDays}>
          {siege.ended_epoch !== null
            ? `Epoch ${siege.started_epoch}–${siege.ended_epoch}`
            : `Since epoch ${siege.started_epoch}`}
        </Plain>
        {siege.last_action && (
          <TableTag
            table={SIEGE_ACTION}
            value={siege.last_action}
            text={`Besiegers: ${named(SIEGE_ACTION, siege.last_action).label}`}
          />
        )}
        {siege.last_defence && (
          <TableTag
            table={DEFENCE}
            value={siege.last_defence}
            text={`Defenders: ${named(DEFENCE, siege.last_defence).label}`}
          />
        )}
      </div>
      <div className='flex min-w-0 flex-col gap-1.5'>
        <Label>Hunger inside the walls</Label>
        <Steps table={STARVATION} value={siege.starvation} label='Hunger' />
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 @sm/siege:grid-cols-2'>
        <StatBar
          label='Food (days)'
          icon={Wheat}
          value={siege.supplies}
          max={Math.max(siege.supplies, FOOD_SCALE)}
          tone={siege.supplies <= 0 ? 'destructive' : 'success'}
        />
        <StatBar
          label='Water (days)'
          icon={Droplets}
          value={siege.water}
          max={Math.max(siege.water, WATER_SCALE)}
          tone={siege.water <= 0 ? 'destructive' : 'info'}
        />
        <StatBar
          label='Sickness inside'
          icon={Biohazard}
          value={siege.disease_inside}
          max={PERCENT}
          tone={percentTone(siege.disease_inside, true)}
        />
        <StatBar
          label='Sickness outside'
          icon={Biohazard}
          value={siege.disease_outside}
          max={PERCENT}
          tone={percentTone(siege.disease_outside, true)}
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2 rounded-lg border bg-muted/20 p-2'>
        <Label>Walls</Label>
        <Pips
          value={siege.walls_level}
          max={WALLS_MAX}
          tone='info'
          label='Wall strength'
        />
        <Stat value={siege.walls_level} unit={`/ ${WALLS_MAX}`} />
        <Badge
          size='sm'
          variant={siege.breaches > 0 ? 'destructive' : 'outline'}
        >
          <BrickWall />
          {`${siege.breaches} ${siege.breaches === 1 ? 'breach' : 'breaches'}`}
        </Badge>
        <Plain icon={Swords}>
          {`${siege.sallies} ${siege.sallies === 1 ? 'sally' : 'sallies'}`}
        </Plain>
        <Paged items={works}>
          {([key, value]) => (
            <TableTag
              key={key}
              table={WORKS}
              value={key}
              text={`${named(WORKS, key).label} ${value}`}
            />
          )}
        </Paged>
      </div>
      <div className='mt-auto flex min-w-0 flex-col'>
        <SiegeEditor siege={siege} blocked={blocked} />
      </div>
    </li>
  )
}

export function OccupationCard({
  occupation,
  blocked,
  perspective,
}: {
  occupation: Occupation
  blocked: string | null
  perspective?: string
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
            control: whole(control, PERCENT),
            resistance: whole(resistance, PERCENT),
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
      className='@container/occ flex min-w-0 flex-col gap-3 rounded-xl border bg-background p-3'
    >
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion icon={Flag} tone='warning' />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          {occupation.region ? (
            <EntityLink kind='entity' id={String(occupation.region.id)}>
              {occupation.region.name}
            </EntityLink>
          ) : (
            <Text as='span' weight='semibold'>
              A land
            </Text>
          )}
          <Muted as='span' variant='caption' truncate>
            {`Held by ${occupation.occupier?.name ?? 'an enemy'}`}
          </Muted>
        </div>
        <Plain icon={CalendarDays}>{`Since ${occupation.since_epoch}`}</Plain>
      </div>
      {perspective && (
        <div className='flex min-w-0 flex-wrap gap-1'>
          <Plain icon={MapPin}>{perspective}</Plain>
        </div>
      )}
      <div className='grid min-w-0 grid-cols-1 gap-2 @xs/occ:grid-cols-2'>
        <StatBar
          label='Control'
          icon={Crown}
          value={occupation.control}
          max={PERCENT}
          tone='success'
        />
        <StatBar
          label='Resistance'
          icon={Swords}
          value={occupation.resistance}
          max={PERCENT}
          tone='destructive'
        />
      </div>
      <div className='mt-auto flex min-w-0 flex-col'>
        <Adjust
          title='Shape the occupation'
          note='Control and resistance decide whether the land rises, submits or is given back.'
        >
          <div className='grid min-w-0 grid-cols-1 gap-2 @sm/occ:grid-cols-2'>
            <NumberField
              label='Control'
              icon={Crown}
              value={control}
              max={PERCENT}
              onChange={setControl}
            />
            <NumberField
              label='Resistance'
              icon={Swords}
              value={resistance}
              max={PERCENT}
              onChange={setResistance}
            />
          </div>
          <div className='flex min-w-0 flex-wrap gap-2'>
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
        </Adjust>
      </div>
    </li>
  )
}

export function CohortCard({
  cohort,
  blocked,
  perspective,
}: {
  cohort: CaptiveCohort
  blocked: string | null
  perspective?: string
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
            count: whole(count),
          },
        })
      ),
  })
  const busy = busyOf(blocked, settle.isPending)
  const item = named(FATE, cohort.fate)
  const people = CLASS_SPEC[cohort.social_class] ?? {
    label: named({}, cohort.social_class).label,
    icon: Users,
  }
  return (
    <li
      data-surface='CaptiveCohort'
      className='@container/cohort flex min-w-0 flex-col gap-3 rounded-xl border bg-background p-3'
    >
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion icon={item.icon} tone={item.tone} />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <Text as='span' weight='semibold' truncate>
            {`${people.label} of ${cohort.origin?.name ?? 'the enemy'}`}
          </Text>
          <Muted as='span' variant='caption' truncate>
            {`Captured by ${cohort.captor?.name ?? 'an enemy'}`}
          </Muted>
        </div>
        <div className='flex shrink-0 flex-col items-end'>
          <Stat value={formatInteger(cohort.count)} size='kpi' />
          <Label>Captives</Label>
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap gap-1'>
        <Tag item={item} />
        <Plain icon={people.icon}>{people.label}</Plain>
        <Plain icon={CalendarDays}>
          {cohort.settled_epoch !== null
            ? `Epoch ${cohort.since_epoch}–${cohort.settled_epoch}`
            : `Since epoch ${cohort.since_epoch}`}
        </Plain>
        {perspective && <Plain icon={Lock}>{perspective}</Plain>}
      </div>
      <div className='mt-auto flex min-w-0 flex-col'>
        <Adjust
          label='Decide their fate'
          title='Their fate'
          note='Ransom, enslave, sacrifice, set to labour, exchange or release any number of them.'
        >
          <div className='grid min-w-0 grid-cols-1 gap-2 @sm/cohort:grid-cols-2'>
            <ChoiceField
              label='Fate'
              icon={item.icon}
              value={fate}
              table={FATE}
              blocked={busy}
              onPick={setFate}
            />
            <NumberField
              label='Captives'
              icon={Users}
              value={count}
              onChange={setCount}
            />
          </div>
          <div>
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
        </Adjust>
      </div>
    </li>
  )
}

function PhaseChip({ phase }: { phase: BattleReport['phases'][number] }) {
  const item = named(PHASE, phase.phase)
  const fallen = phase.attacker_losses + phase.defender_losses
  return (
    <li>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            tabIndex={0}
            className={cn(
              'flex h-badge-md min-w-0 items-center gap-1 rounded-md border px-2',
              fallen > 0 ? frameTone(item.tone) : 'bg-muted/30'
            )}
          >
            <item.icon
              aria-hidden='true'
              className={cn('size-icon-xs shrink-0', iconTone(item.tone))}
            />
            <Text as='span' variant='caption' weight='medium'>
              {item.label}
            </Text>
            {fallen > 0 && (
              <Text as='span' variant='caption' tone='destructive'>
                {`${formatInteger(fallen)} fell`}
              </Text>
            )}
          </span>
        </TooltipTrigger>
        <TooltipContent className='flex flex-col gap-0.5'>
          <Text as='span' weight='medium'>
            {phase.summary ?? item.label}
          </Text>
          <Muted variant='caption'>
            {`Attackers lost ${formatInteger(phase.attacker_losses)}, defenders lost ${formatInteger(phase.defender_losses)}`}
          </Muted>
        </TooltipContent>
      </Tooltip>
    </li>
  )
}

function detailText(key: string, value: number | string): string {
  const label = PHASE_DETAIL[key] ?? named({}, key).label
  const text =
    typeof value === 'number'
      ? formatInteger(value)
      : (TACTIC[value]?.label ?? named({}, value).label)
  return `${label}: ${text}`
}

function PhaseTimeline({ battle }: { battle: BattleReport }) {
  const [open, setOpen] = useState(false)
  return (
    <Collapsible
      open={open}
      onOpenChange={setOpen}
      className='flex min-w-0 flex-col gap-2'
    >
      <CollapsibleTrigger asChild>
        <Button variant='ghost' size='sm' className='self-start'>
          {open ? <ChevronUp /> : <ChevronDown />}
          {open ? 'Hide the phases' : 'Phase by phase'}
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='min-w-0'>
        <Timeline label='Phases of the battle'>
          <Paged items={battle.phases} as='li'>
            {(phase, index) => {
              const item = named(PHASE, phase.phase)
              const fallen = phase.attacker_losses + phase.defender_losses
              return (
                <TimelineItem
                  key={phase.position}
                  icon={item.icon}
                  tone={fallen > 0 ? 'destructive' : 'default'}
                  title={item.label}
                  last={index === battle.phases.length - 1}
                >
                  {phase.summary && (
                    <Muted variant='caption'>
                      {phase.summary.charAt(0).toUpperCase() +
                        phase.summary.slice(1)}
                    </Muted>
                  )}
                  <div className='flex min-w-0 flex-wrap gap-1'>
                    <Plain icon={Swords}>
                      {`Attackers lost ${formatInteger(phase.attacker_losses)}`}
                    </Plain>
                    <Plain icon={Shield}>
                      {`Defenders lost ${formatInteger(phase.defender_losses)}`}
                    </Plain>
                    {Object.entries(phase.details).map(([key, value]) => (
                      <Badge key={key} size='sm' variant='secondary'>
                        {detailText(key, value)}
                      </Badge>
                    ))}
                  </div>
                </TimelineItem>
              )
            }}
          </Paged>
        </Timeline>
      </CollapsibleContent>
    </Collapsible>
  )
}

function BattleItem({ battle, last }: { battle: BattleReport; last: boolean }) {
  const outcome = named(OUTCOME, battle.outcome)
  const kinds = Object.entries(battle.casualties_by_kind)
    .filter(([, value]) => value > 0)
    .sort((first, second) => second[1] - first[1])
  const when = [
    `Epoch ${battle.epoch}`,
    battle.season_name,
    battle.year !== null ? String(battle.year) : null,
  ]
    .filter(Boolean)
    .join(' · ')
  return (
    <TimelineItem
      icon={outcome.icon}
      tone={TIMELINE_TONE[outcome.tone ?? 'muted']}
      framed
      last={last}
      timestamp={when}
      title={
        battle.record ? (
          <EntityLink kind='entity' id={String(battle.record.id)}>
            {battle.record.name}
          </EntityLink>
        ) : (
          `Clash #${battle.sequence}`
        )
      }
    >
      <div
        data-surface='BattleReport'
        className='flex min-w-0 flex-col gap-2.5'
      >
        <div className='flex min-w-0 flex-wrap gap-1'>
          <Tag item={outcome} />
          {battle.outcome_class && (
            <TableTag table={OUTCOME_CLASS} value={battle.outcome_class} />
          )}
          {battle.place && <Plain icon={MapPin}>{battle.place.name}</Plain>}
          {battle.terrain && (
            <TableTag table={TERRAIN} value={battle.terrain} />
          )}
          {battle.weather && (
            <TableTag table={WEATHER} value={battle.weather} />
          )}
          {battle.night && (
            <Badge size='sm' variant='info'>
              <Moon />
              At night
            </Badge>
          )}
        </div>
        <div className='grid min-w-0 grid-cols-1 gap-2 @lg/mil:grid-cols-2'>
          <MiniStat
            icon={Crown}
            label={`${battle.winner?.name ?? 'The victor'} lost`}
            value={formatInteger(battle.winner_losses)}
            tone='success'
          />
          <MiniStat
            icon={Skull}
            label={`${battle.loser?.name ?? 'The beaten'} lost`}
            value={formatInteger(battle.loser_losses)}
            tone='danger'
          />
        </div>
        {battle.tactics_attacker && battle.tactics_defender && (
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Label>Plans</Label>
            <TableTag table={TACTIC} value={battle.tactics_attacker} />
            <Muted as='span' variant='caption'>
              against
            </Muted>
            <TableTag table={TACTIC} value={battle.tactics_defender} />
          </div>
        )}
        {battle.phases.length > 0 && (
          <ol
            aria-label='Phases'
            className='flex min-w-0 flex-wrap items-center gap-1'
          >
            <Paged items={battle.phases} as='li'>
              {(phase) => <PhaseChip key={phase.position} phase={phase} />}
            </Paged>
          </ol>
        )}
        {kinds.length > 0 && (
          <div className='flex min-w-0 flex-wrap items-center gap-1'>
            <Label>Fallen by unit</Label>
            {kinds.map(([kind, value]) => (
              <Plain key={kind} icon={UNIT_ICON[kind] ?? Users}>
                {`${named({}, kind).label} ${formatInteger(value)}`}
              </Plain>
            ))}
          </div>
        )}
        {battle.phases.length > 0 && <PhaseTimeline battle={battle} />}
        <BattleDepthPanel
          battleId={battle.id}
          sides={Object.fromEntries(
            [battle.winner, battle.loser]
              .filter((side): side is NonNullable<typeof side> => side !== null)
              .map((side) => [String(side.id), side.name])
          )}
        />
      </div>
    </TimelineItem>
  )
}

function Fronts({ room }: { room: Room }) {
  return (
    <ul className='flex min-w-0 flex-wrap gap-1.5'>
      <Paged items={room.fronts} as='li'>
        {(front) => {
          const first = front.first_region?.name ?? '?'
          const second = front.second_region?.name ?? '?'
          return (
            <li key={`${front.first_region?.id}.${front.second_region?.id}`}>
              <Plain icon={MapIcon}>
                {`${first === second ? first : `${first} – ${second}`} · epoch ${front.since_epoch === front.last_epoch ? front.since_epoch : `${front.since_epoch}–${front.last_epoch}`}`}
              </Plain>
            </li>
          )
        }}
      </Paged>
    </ul>
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
  const quiet = [
    data.battles.length === 0 && { icon: Swords, text: 'No battle fought' },
    data.armies.length === 0 && { icon: Users, text: 'No army marches' },
    data.sieges.length === 0 && {
      icon: SIEGE_STATUS.ongoing.icon,
      text: 'No walls besieged',
    },
    data.occupations.length === 0 && { icon: Flag, text: 'No land occupied' },
    data.captives.length === 0 && { icon: Lock, text: 'No one led away' },
    data.fronts.length === 0 && { icon: MapIcon, text: 'No front yet' },
  ].filter(
    (item): item is { icon: typeof Swords; text: string } => item !== false
  )
  return (
    <div
      data-surface='WarRoom'
      className='@container/mil flex min-w-0 flex-col gap-4'
    >
      <Versus room={data} />
      <RoomStats room={data} />
      <IncitementCard war={data.war} blocked={blocked} />
      <WarLedger warId={warId} blocked={blocked} />
      <WarControls room={data} blocked={blocked} />
      <WarMap room={data} />
      <WarOrders
        warId={warId}
        sides={sideEntries(data).map((entry) => ({
          id: entry.id,
          name: entry.name,
        }))}
        blocked={blocked}
      />
      <SiegeDepth warId={warId} blocked={blocked} />
      <PeaceTreaty
        warId={warId}
        sides={sideEntries(data).map((entry) => ({
          id: entry.id,
          name: entry.name,
        }))}
        blocked={blocked}
      />
      {data.fronts.length > 0 && (
        <Panel
          title='Fronts'
          icon={MapIcon}
          tone='warning'
          count={data.fronts.length}
          hint='Regions where the armies have met'
        >
          <Fronts room={data} />
        </Panel>
      )}
      {data.battles.length > 0 && (
        <Panel
          title='Battles'
          icon={Swords}
          tone='danger'
          count={data.battles.length}
          hint='Every clash with its ground, plans, phases and dead'
        >
          <Timeline label='Battle reports'>
            <Paged items={data.battles} as='li'>
              {(battle, index) => (
                <BattleItem
                  key={battle.id}
                  battle={battle}
                  last={index === data.battles.length - 1}
                />
              )}
            </Paged>
          </Timeline>
        </Panel>
      )}
      {data.sieges.length > 0 && (
        <Panel
          title='Sieges'
          icon={SIEGE_STATUS.ongoing.icon}
          tone='warning'
          count={data.sieges.length}
          hint='Stores, water, walls and hunger behind them'
        >
          <ul className={cardGrid(data.sieges.length)}>
            <Paged items={data.sieges} as='li'>
              {(siege) => (
                <SiegeCard key={siege.id} siege={siege} blocked={blocked} />
              )}
            </Paged>
          </ul>
        </Panel>
      )}
      {data.armies.length > 0 && (
        <Panel
          title='Armies'
          icon={Shield}
          tone='gold'
          count={data.armies.length}
          hint='Stacks, stores and marches of every army in this war'
        >
          <div className='flex min-w-0 flex-col gap-3'>
            <Paged items={data.armies}>
              {(army) => (
                <ArmyPanel key={army.army?.id} army={army} blocked={blocked} />
              )}
            </Paged>
          </div>
        </Panel>
      )}
      {data.occupations.length > 0 && (
        <Panel
          title='Occupied lands'
          icon={Flag}
          tone='warning'
          count={data.occupations.length}
          hint='Held by the sword, resisting or submitting'
        >
          <ul className={cardGrid(data.occupations.length)}>
            <Paged items={data.occupations} as='li'>
              {(item) => (
                <OccupationCard
                  key={item.region?.id}
                  occupation={item}
                  blocked={blocked}
                />
              )}
            </Paged>
          </ul>
        </Panel>
      )}
      {data.captives.length > 0 && (
        <Panel
          title='Captives'
          icon={Lock}
          tone='muted'
          count={data.captives.length}
          hint='Cohorts led away and what became of them'
        >
          <ul className={cardGrid(data.captives.length)}>
            <Paged items={data.captives} as='li'>
              {(cohort) => (
                <CohortCard key={cohort.id} cohort={cohort} blocked={blocked} />
              )}
            </Paged>
          </ul>
        </Panel>
      )}
      <Quiet items={quiet} />
    </div>
  )
}

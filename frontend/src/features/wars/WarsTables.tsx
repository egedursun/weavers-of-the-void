import { type ReactNode, useState } from 'react'
import {
  CalendarDays,
  Castle,
  Coins,
  Crown,
  Hourglass,
  Lock,
  type LucideIcon,
  MapPin,
  Shield,
  ShieldCheck,
  Swords,
  Trophy,
  User,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  EmptyState,
  EntityLink,
  type KpiTone,
  Medallion,
} from '@/components/domain'
import { PageControls } from '@/components/domain/PageControls'
import { Muted, Text } from '@/components/typography'
import { NodeAvatar } from '@/features/images/NodeAvatar'
import {
  WAR_PAGE_SIZE,
  type ArmyView,
  type BattleView,
  type CaptiveView,
  type NodeRef,
  type SiegeView,
  type TributeView,
  useArmies,
  useBattles,
  useCaptives,
  useSieges,
  useTributes,
} from './api'

type BattleOutcome = components['schemas']['BattleOutcome']
type SiegeStatus = components['schemas']['SiegeStatus']

const OUTCOME: Record<
  BattleOutcome,
  {
    label: string
    icon: LucideIcon
    tone: KpiTone
    badge: 'default' | 'success' | 'destructive' | 'info' | 'warning'
  }
> = {
  field_victory: {
    label: 'Field victory',
    icon: Swords,
    tone: 'danger',
    badge: 'destructive',
  },
  great_victory: {
    label: 'Great victory',
    icon: Trophy,
    tone: 'gold',
    badge: 'default',
  },
  siege_repulsed: {
    label: 'Siege repulsed',
    icon: ShieldCheck,
    tone: 'info',
    badge: 'info',
  },
  siege_breached: {
    label: 'Walls breached',
    icon: Castle,
    tone: 'danger',
    badge: 'destructive',
  },
  siege_starvation: {
    label: 'Starved out',
    icon: Hourglass,
    tone: 'warning',
    badge: 'warning',
  },
  refused: {
    label: 'Battle refused',
    icon: Shield,
    tone: 'muted',
    badge: 'info',
  },
}

const SIEGE_STATUS: Record<
  SiegeStatus,
  { label: string; badge: 'destructive' | 'info' | 'success' | 'outline' }
> = {
  ongoing: { label: 'Under siege', badge: 'destructive' },
  breached: { label: 'Breached', badge: 'destructive' },
  repulsed: { label: 'Repulsed', badge: 'info' },
  lifted: { label: 'Lifted', badge: 'outline' },
}

export function Ref({ node }: { node: NodeRef | null }) {
  if (!node) return <Text as='span'>Unknown</Text>
  return (
    <span className='inline-flex max-w-full min-w-0 items-center gap-1.5 align-middle'>
      <NodeAvatar id={node.id} name={node.name} />
      {node.kind === 'entity' ? (
        <EntityLink kind='entity' id={String(node.id)}>
          {node.name}
        </EntityLink>
      ) : (
        <Text as='span' truncate>
          {node.name}
        </Text>
      )}
    </span>
  )
}

function EpochBadge({ from, to }: { from: number; to?: number | null }) {
  return (
    <Badge size='sm' variant='outline'>
      <CalendarDays />
      {to !== undefined && to !== null && to !== from
        ? `Epoch ${from}–${to}`
        : `Epoch ${from}`}
    </Badge>
  )
}

type PageShape<T> = { items: T[]; total: number; offset: number }
type Query<T> = {
  isPending: boolean
  isError: boolean
  error: Error | null
  data: PageShape<T> | undefined
}

type ListProps<T> = {
  query: Query<T>
  offset: number
  onOffset: (offset: number) => void
  label: string
  empty: string
  emptyIcon: LucideIcon
  row: (item: T) => ReactNode
  keyOf: (item: T) => string | number
}

function PagedList<T>({
  query,
  offset,
  onOffset,
  label,
  empty,
  emptyIcon,
  row,
  keyOf,
}: ListProps<T>) {
  if (query.isPending) return <Skeleton className='h-control-lg w-full' />
  if (query.isError)
    return <Text tone='destructive'>{query.error?.message}</Text>
  const data = query.data
  if (!data || data.items.length === 0)
    return (
      <EmptyState
        icon={emptyIcon}
        size='compact'
        title={empty}
        description='Nothing is recorded here yet.'
      />
    )
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <ul aria-label={label} className='flex min-w-0 flex-col gap-2'>
        {data.items.map((item) => (
          <li
            key={keyOf(item)}
            className='flex min-w-0 items-start gap-3 rounded-lg border bg-background p-3'
          >
            {row(item)}
          </li>
        ))}
      </ul>
      <PageControls
        offset={offset}
        limit={WAR_PAGE_SIZE}
        total={data.total}
        onChange={onOffset}
        label={label}
      />
    </div>
  )
}

function Line({ children }: { children: ReactNode }) {
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-1'>
      {children}
    </div>
  )
}

export function ArmiesList({ warId }: { warId: number }) {
  const [offset, setOffset] = useState(0)
  return (
    <PagedList<ArmyView>
      query={useArmies(warId, offset, true)}
      offset={offset}
      onOffset={setOffset}
      label='Armies'
      empty='No armies'
      emptyIcon={Shield}
      keyOf={(item) => item.army?.id ?? item.raised_epoch}
      row={(item) => (
        <>
          <Medallion
            icon={Shield}
            tone={item.disbanded_epoch !== null ? 'muted' : 'danger'}
            size='sm'
          />
          <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
            <Line>
              <Ref node={item.army} />
              <Muted as='span' variant='caption'>
                of
              </Muted>
              <Ref node={item.owner} />
            </Line>
            <div className='flex min-w-0 flex-wrap gap-1.5'>
              {item.commander && (
                <Badge size='sm' variant='outline'>
                  <User />
                  <Ref node={item.commander} />
                </Badge>
              )}
              <EpochBadge from={item.raised_epoch} to={item.disbanded_epoch} />
              {item.disbanded_epoch !== null && (
                <Badge size='sm' variant='outline'>
                  Disbanded
                </Badge>
              )}
            </div>
          </div>
        </>
      )}
    />
  )
}

export function BattlesList({ warId }: { warId: number }) {
  const [offset, setOffset] = useState(0)
  return (
    <PagedList<BattleView>
      query={useBattles(warId, offset, true)}
      offset={offset}
      onOffset={setOffset}
      label='Battles'
      empty='No battles'
      emptyIcon={Swords}
      keyOf={(item) => item.id}
      row={(item) => {
        const look = OUTCOME[item.outcome]
        return (
          <>
            <Medallion icon={look.icon} tone={look.tone} size='sm' />
            <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
              <Line>
                <Badge size='sm' variant='outline'>{`#${item.sequence}`}</Badge>
                {item.record ? (
                  <Ref node={item.record} />
                ) : (
                  <Text
                    as='span'
                    weight='medium'
                  >{`Battle ${item.sequence}`}</Text>
                )}
              </Line>
              <Line>
                <Crown
                  aria-hidden='true'
                  className='size-icon-xs shrink-0 text-primary'
                />
                <Ref node={item.winner} />
                <Muted as='span' variant='caption'>
                  defeated
                </Muted>
                <Ref node={item.loser} />
              </Line>
              <div className='flex min-w-0 flex-wrap gap-1.5'>
                <Badge size='sm' variant={look.badge}>
                  {look.label}
                </Badge>
                <EpochBadge from={item.epoch} />
                {item.place && (
                  <Badge size='sm' variant='outline'>
                    <MapPin />
                    <Ref node={item.place} />
                  </Badge>
                )}
              </div>
            </div>
          </>
        )
      }}
    />
  )
}

export function SiegesList({ warId }: { warId: number }) {
  const [offset, setOffset] = useState(0)
  return (
    <PagedList<SiegeView>
      query={useSieges(warId, offset, true)}
      offset={offset}
      onOffset={setOffset}
      label='Sieges'
      empty='No sieges'
      emptyIcon={Castle}
      keyOf={(item) => item.id}
      row={(item) => {
        const look = SIEGE_STATUS[item.status]
        return (
          <>
            <Medallion
              icon={Castle}
              tone={item.status === 'repulsed' ? 'info' : 'danger'}
              size='sm'
            />
            <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
              <Line>
                <Ref node={item.besieger} />
                <Muted as='span' variant='caption'>
                  besieged
                </Muted>
                <Ref node={item.besieged} />
              </Line>
              <div className='flex min-w-0 flex-wrap gap-1.5'>
                <Badge size='sm' variant={look.badge}>
                  {look.label}
                </Badge>
                <EpochBadge from={item.started_epoch} to={item.ended_epoch} />
                <Badge size='sm' variant='outline'>
                  {`${item.rounds} ${item.rounds === 1 ? 'round' : 'rounds'}`}
                </Badge>
              </div>
            </div>
          </>
        )
      }}
    />
  )
}

export function CaptivesList({ communityId }: { communityId: number | null }) {
  const [offset, setOffset] = useState(0)
  return (
    <PagedList<CaptiveView>
      query={useCaptives(communityId, null, offset)}
      offset={offset}
      onOffset={setOffset}
      label='Captives'
      empty='No captives'
      emptyIcon={Lock}
      keyOf={(item) => item.id}
      row={(item) => (
        <>
          <Medallion
            icon={Lock}
            tone={item.status === 'held' ? 'warning' : 'muted'}
            size='sm'
          />
          <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
            <Line>
              <Ref node={item.captive} />
              <Muted as='span' variant='caption'>
                held by
              </Muted>
              <Ref node={item.captor} />
            </Line>
            <div className='flex min-w-0 flex-wrap gap-1.5'>
              <Badge
                size='sm'
                variant={item.status === 'held' ? 'warning' : 'outline'}
              >
                {item.status.replaceAll('_', ' ')}
              </Badge>
              <EpochBadge from={item.taken_epoch} to={item.released_epoch} />
              {item.home && (
                <Badge size='sm' variant='outline'>
                  <MapPin />
                  <Ref node={item.home} />
                </Badge>
              )}
              {item.ransom_paid !== null && (
                <Badge size='sm' variant='success'>
                  <Coins />
                  {`Ransom ${item.ransom_paid}`}
                </Badge>
              )}
            </div>
          </div>
        </>
      )}
    />
  )
}

export function TributesList({ communityId }: { communityId: number | null }) {
  const [offset, setOffset] = useState(0)
  return (
    <PagedList<TributeView>
      query={useTributes(communityId, null, offset)}
      offset={offset}
      onOffset={setOffset}
      label='Tributes'
      empty='No tributes'
      emptyIcon={Coins}
      keyOf={(item) => item.id}
      row={(item) => (
        <>
          <Medallion
            icon={Coins}
            tone={item.status === 'active' ? 'gold' : 'muted'}
            size='sm'
          />
          <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
            <Line>
              <Ref node={item.payer} />
              <Muted as='span' variant='caption'>
                pays tribute to
              </Muted>
              <Ref node={item.receiver} />
            </Line>
            <div className='flex min-w-0 flex-wrap gap-1.5'>
              <Badge
                size='sm'
                variant={item.status === 'active' ? 'warning' : 'outline'}
              >
                {item.status.replaceAll('_', ' ')}
              </Badge>
              <EpochBadge from={item.since_epoch} to={item.ended_epoch} />
            </div>
          </div>
        </>
      )}
    />
  )
}

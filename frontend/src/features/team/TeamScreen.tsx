import { useState } from 'react'
import { navItem } from '@/config/navigation'
import { BookLock, Hourglass, Radio, UsersRound } from 'lucide-react'
import { useUniverseId } from '@/api/universeStore'
import { Badge } from '@/components/ui/badge'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  EmptyState,
  LoadingBlock,
  MiniStat,
  PageHeader,
  Paged,
  PanelGrid,
  Section,
} from '@/components/domain'
import { screenTitle } from '@/components/layout/screenTitle'
import { Muted, Text } from '@/components/typography'
import { AccountAvatar } from '@/features/accounts/AccountAvatar'
import { useNodeIndex } from '@/features/feed/nodes'
import { AccessOf } from '@/features/workspaces/UniverseAccessPanel'
import { useActiveWorkspace } from '@/features/workspaces/useActiveWorkspace'
import { seenText } from './Presence'
import { ProposalList } from './Proposals'
import { QueueList } from './Queue'
import { ROLE_LOOK } from './permissions'
import { useTeamContext } from './teamContext'
import { personTone } from './teamLook'
import { type ProposalStatus, type QueuedActStatus } from './types'

const ITEM = navItem('team')

type QueueFilter = 'queued' | 'all'
type ProposalFilter = 'pending' | 'all'

function HereNow() {
  const team = useTeamContext()
  const names = useNodeIndex()
  const present = team?.team?.present ?? []
  if (present.length === 0)
    return (
      <EmptyState
        size='compact'
        icon={Radio}
        title='Nobody is here right now'
        description='Everyone who opens this universe shows here with the screen or entry they are on.'
      />
    )
  return (
    <ul aria-label='People here now' className='flex min-w-0 flex-col gap-2'>
      <Paged items={present} as='li' noun={['person', 'people']}>
        {(person) => {
          const node =
            person.node_id === null ? null : names.get(person.node_id)
          const where = node
            ? `${person.editing ? 'Editing' : 'Reading'} ${node.name}`
            : `On ${screenTitle(person.screen) ?? 'a screen of the universe'}`
          return (
            <li
              key={person.account_id}
              className='flex min-w-0 items-center gap-3 rounded-md surface-sheen p-2.5'
            >
              <AccountAvatar
                name={person.name}
                tone={personTone(person.name)}
              />
              <span className='flex min-w-0 flex-1 flex-col'>
                <Text as='span' weight='semibold' truncate>
                  {person.account_id === team?.me
                    ? `${person.name} (you)`
                    : person.name}
                </Text>
                <Muted as='span' variant='caption' truncate>
                  {`${where} · ${seenText(person)}`}
                </Muted>
              </span>
              {person.editing && (
                <Badge variant='warning' size='sm'>
                  Editing
                </Badge>
              )}
            </li>
          )
        }}
      </Paged>
    </ul>
  )
}

function Access() {
  const universeId = useUniverseId()
  const { active, workspaces } = useActiveWorkspace()
  if (workspaces.isPending)
    return <LoadingBlock label='Reading who shares this universe' />
  if (active === null || universeId === null)
    return (
      <EmptyState
        size='compact'
        icon={UsersRound}
        title='No workspace is chosen'
        description='Open this universe from its workspace to see who shares it.'
      />
    )
  return <AccessOf workspace={active} universeId={universeId} />
}

export function TeamScreen() {
  const team = useTeamContext()
  const [queue, setQueue] = useState<QueueFilter>('queued')
  const [proposals, setProposals] = useState<ProposalFilter>('pending')
  const view = team?.team
  const role = team?.role ?? null
  const queueStatus: QueuedActStatus | null =
    queue === 'queued' ? 'queued' : null
  const proposalStatus: ProposalStatus | null =
    proposals === 'pending' ? 'pending' : null
  return (
    <>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
        actions={
          role && (
            <Badge variant='default'>
              {`You are ${role === 'viewer' ? 'a' : 'an'} ${ROLE_LOOK[role].label} of ${team?.universe}`}
            </Badge>
          )
        }
      />
      <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
        <MiniStat
          icon={Radio}
          label='Here now'
          value={view?.present.length ?? 0}
          tone='success'
        />
        <MiniStat
          icon={Hourglass}
          label='Waiting for the age'
          value={view?.queued ?? 0}
          tone='warning'
        />
        <MiniStat
          icon={BookLock}
          label='Proposals to review'
          value={view?.proposals ?? 0}
          tone='info'
        />
        <MiniStat
          icon={UsersRound}
          label='Canon approval'
          value={view?.canon_approval ? 'On' : 'Off'}
          tone={view?.canon_approval ? 'gold' : 'muted'}
          hint={
            view?.canon_approval
              ? 'An Editor’s act on locked canon waits for an administrator.'
              : 'Every act on locked canon runs at once.'
          }
        />
      </div>
      <PanelGrid>
        <Section title='Here now' icon={Radio} surface='card' level={3}>
          <HereNow />
        </Section>
        <Section
          title='The queue'
          icon={Hourglass}
          surface='card'
          level={3}
          actions={
            <ToggleGroup
              type='single'
              size='sm'
              value={queue}
              onValueChange={(value) => {
                if (value === 'queued' || value === 'all') setQueue(value)
              }}
              aria-label='Which queued acts'
            >
              <ToggleGroupItem value='queued'>Waiting</ToggleGroupItem>
              <ToggleGroupItem value='all'>All</ToggleGroupItem>
            </ToggleGroup>
          }
        >
          <QueueList status={queueStatus} />
        </Section>
      </PanelGrid>
      <Section
        title='Canon proposals'
        icon={BookLock}
        surface='card'
        actions={
          <ToggleGroup
            type='single'
            size='sm'
            value={proposals}
            onValueChange={(value) => {
              if (value === 'pending' || value === 'all') setProposals(value)
            }}
            aria-label='Which proposals'
          >
            <ToggleGroupItem value='pending'>To review</ToggleGroupItem>
            <ToggleGroupItem value='all'>All</ToggleGroupItem>
          </ToggleGroup>
        }
      >
        <ProposalList status={proposalStatus} />
      </Section>
      <Access />
    </>
  )
}

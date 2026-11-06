import { Link } from '@tanstack/react-router'
import { navItem } from '@/config/navigation'
import { Crown, LibraryBig } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  DomainIcon,
  EmptyState,
  ExpandableText,
  PageHeader,
  Section,
} from '@/components/domain'
import { Label, Muted, Stat } from '@/components/typography'
import { CouncilBlock } from '@/features/council/CouncilBlock'
import { ForeignGodsSection } from '@/features/foreign-god/ForeignGodsSection'
import { GoalsBlock } from '@/features/goals/GoalsBlock'
import { sonHints } from '@/features/son/hints'
import { BrotherhoodMatrix } from './BrotherhoodMatrix'
import { CompareToggle } from './CompareCards'
import { CompareSons } from './CompareSons'
import { DistributionControl } from './DistributionControl'
import { GodPanel } from './GodPanel'
import { SonCard } from './SonCard'
import { StoryThreads } from './StoryThreads'
import { SummonButton } from './SummonButton'
import { ThisEpochBox } from './ThisEpochBox'
import {
  type WorldState,
  useOpportunities,
  useSons,
  useWorldState,
} from './api'
import { useLabels } from './labels'
import { sortSons } from './sonFacts'
import { useActingSons } from './useActingSons'

const ITEM = navItem('pantheon')

function SonGrid({ state }: { state: WorldState }) {
  const hints = useOpportunities()
  const acting = useActingSons()
  const list = useSons()
  const sons = sortSons(list.data ?? state.sons)
  const worldName = (worldId: number | null) =>
    state.worlds.length > 1
      ? (state.worlds.find((world) => world.id === worldId)?.name ?? null)
      : null
  return (
    <Section
      title={`Pantheon · ${sons.length} sons`}
      description='Open a card to give orders, bless, add a star or ascend.'
      actions={<SummonButton />}
    >
      <DistributionControl />
      {sons.length === 0 ? (
        <EmptyState
          icon={Crown}
          title='No sons yet'
          description='Summon your first son; they arrive with a rarity, domains and powers of their own.'
        />
      ) : (
        <div className='grid min-w-0 grid-cols-1 gap-4 md:grid-cols-2 2xl:grid-cols-3'>
          {sons.map((view) => (
            <SonCard
              key={view.son.id}
              view={view}
              ready={state.pending_son_ids.includes(view.son.id)}
              acting={acting.has(view.son.id)}
              worldName={worldName(view.son.current_world_id)}
              hints={sonHints(hints.data, view.son.name)}
              actions={
                <CompareToggle sonId={view.son.id} name={view.son.name} />
              }
            />
          ))}
        </div>
      )}
    </Section>
  )
}

function InTheWorld({ state }: { state: WorldState }) {
  const { entityType } = useLabels()
  const counts = Object.entries(state.counts).filter(([, value]) => value > 0)
  if (counts.length === 0 && !state.world?.cosmology) return null
  return (
    <Section
      title='In the world'
      description='Every kind of living record, by count. Open one to see it in the atlas.'
      icon={LibraryBig}
    >
      {counts.length > 0 && (
        <ul className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-6'>
          {[...counts]
            .sort((left, right) => right[1] - left[1])
            .map(([type, value]) => (
              <li key={type} className='min-w-0'>
                <Button variant='outline' size='tile' asChild>
                  <Link to='/atlas' search={{ type }}>
                    <span className='flex size-control-sm shrink-0 items-center justify-center rounded-md border border-primary/25 bg-primary/10 text-primary'>
                      <DomainIcon vocabulary='entity-type' value={type} />
                    </span>
                    <span className='flex min-w-0 flex-1 flex-col'>
                      <Stat value={value} />
                      <Muted as='span' variant='caption' truncate>
                        {entityType(type)}
                      </Muted>
                    </span>
                  </Link>
                </Button>
              </li>
            ))}
        </ul>
      )}
      {state.world?.cosmology && (
        <div className='flex min-w-0 flex-col gap-1.5 rounded-lg border bg-card p-4'>
          <Label variant='overline'>Cosmology</Label>
          <ExpandableText variant='prose' lines={6}>
            {state.world.cosmology}
          </ExpandableText>
          {state.world?.tone && (
            <Muted variant='caption'>{`Tone: ${state.world.tone}`}</Muted>
          )}
        </div>
      )}
    </Section>
  )
}

export function PantheonScreen() {
  const state = useWorldState()
  return (
    <div className='flex min-w-0 flex-col gap-8'>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
      />
      {state.isPending ? (
        <div className='flex flex-col gap-4'>
          <Skeleton className='h-textarea w-full' />
          <Skeleton className='h-textarea w-full' />
        </div>
      ) : state.isError ? (
        <Alert variant='destructive'>
          <Crown />
          <AlertTitle>The pantheon could not be read</AlertTitle>
          <AlertDescription>{state.error.message}</AlertDescription>
        </Alert>
      ) : !state.data.creator ? (
        <EmptyState
          icon={Crown}
          title='No world yet'
          description='Create the world in the genesis wizard; your sons appear here once they answer your call.'
          action={
            <Button className='self-start' asChild>
              <Link to='/genesis'>Begin genesis</Link>
            </Button>
          }
        />
      ) : (
        <>
          <GodPanel state={state.data} />
          <ThisEpochBox state={state.data} />
          <SonGrid state={state.data} />
          <CompareSons />
          <GoalsBlock summary />
          <CouncilBlock />
          <StoryThreads />
          <BrotherhoodMatrix state={state.data} />
          <ForeignGodsSection />
          <InTheWorld state={state.data} />
        </>
      )}
    </div>
  )
}

import { Link } from '@tanstack/react-router'
import { navItem } from '@/config/navigation'
import { Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, PageHeader, PanelGrid, Section } from '@/components/domain'
import { Text } from '@/components/typography'
import { CompleteEpochButton } from '@/features/epoch/CompleteEpochButton'
import { EpochProgress } from '@/features/epoch/EpochProgress'
import { StopEpochButton } from '@/features/epoch/StopEpochButton'
import { LiveFeedPanel } from '@/features/feed/LiveFeedPanel'
import { FirstEpochsGuide } from '@/features/onboarding/FirstEpochsGuide'
import { ChangeDigestPanel } from './ChangeDigestPanel'
import { EpochBreakdownPanel } from './EpochBreakdownPanel'
import { StatsCharts } from './StatsCharts'
import { WorldSummary } from './WorldSummary'
import { useWorldState } from './api'

const ITEM = navItem('overview')

function NoWorld() {
  return (
    <EmptyState
      icon={Sparkles}
      title='No world yet'
      description='Begin genesis to create a world, its Creator and the first sons.'
      action={
        <Button asChild>
          <Link to='/genesis'>
            <Sparkles />
            Begin genesis
          </Link>
        </Button>
      }
    />
  )
}

export function OverviewScreen() {
  const state = useWorldState()
  const world = state.data?.world ?? null
  return (
    <>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
        actions={
          <>
            <StopEpochButton />
            <CompleteEpochButton />
          </>
        }
      />
      {state.isPending && <Skeleton className='h-48 w-full' />}
      {state.isError && (
        <Section title='The world cannot be read' surface='card'>
          <Text tone='destructive'>{state.error.message}</Text>
        </Section>
      )}
      {state.isSuccess && !world && <NoWorld />}
      {state.data && world && (
        <>
          <FirstEpochsGuide epoch={world.epoch} />
          <WorldSummary state={state.data} />
          <EpochProgress framed />
        </>
      )}
      <PanelGrid>
        <LiveFeedPanel showHeader />
        {state.data && world && <ChangeDigestPanel />}
      </PanelGrid>
      {state.data && world && <EpochBreakdownPanel state={state.data} />}
      <StatsCharts hasWorld={Boolean(world)} />
    </>
  )
}

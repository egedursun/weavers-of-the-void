import { CircleCheck, CircleX, Compass, Rocket } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, MiniStat, Section } from '@/components/domain'
import { Text } from '@/components/typography'
import { ExpeditionCard } from './ExpeditionCard'
import { SendVoyageForm } from './SendVoyageForm'
import { VoyageCard } from './VoyageCard'
import { useExpeditions } from './expeditionsApi'
import {
  type CosmosIndex,
  isUnderway,
  routeState,
  sortJourneys,
} from './model/cosmosModel'
import { type RuleBook, ruleText } from './model/rules'

type VoyagesPanelProps = {
  index: CosmosIndex
  rules: RuleBook
  worldId: number | undefined
}

export function VoyagesPanel({ index, rules, worldId }: VoyagesPanelProps) {
  const journeys = sortJourneys(index.data.journeys)
  const openRoute = index.data.routes.some(
    (route) => route.known && routeState(route).open
  )
  const population = rules.get('expeditionMinPopulation')
  const expeditions = useExpeditions()
  const great = expeditions.data ?? []
  const counted = (test: (journey: (typeof journeys)[number]) => boolean) =>
    journeys.filter(test).length
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      {journeys.length > 0 && (
        <div className='grid min-w-0 grid-cols-2 gap-2'>
          <MiniStat
            icon={Rocket}
            tone='gold'
            label='Underway'
            value={counted(isUnderway)}
          />
          <MiniStat
            icon={CircleCheck}
            tone='success'
            label='Arrived'
            value={counted((journey) => journey.status === 'arrived')}
          />
          <MiniStat
            icon={CircleX}
            tone='danger'
            label='Lost'
            value={counted((journey) => journey.status === 'lost')}
          />
          <MiniStat
            icon={Compass}
            tone='info'
            label='Great expeditions'
            value={great.length}
          />
        </div>
      )}
      <Section title='Voyages' level={3}>
        {journeys.length === 0 ? (
          <EmptyState
            icon={Rocket}
            size='compact'
            title='No community has set out yet'
            description={
              openRoute
                ? `Open routes exist: communities of at least ${population === undefined ? '…' : formatInteger(population)} souls may set out on their own (${ruleText(rules.get('expeditionBase'))}% per epoch, World rules › Cosmos and travel), or you can send one below.`
                : 'There is no open, known route between worlds. Open one in Command › Open a route, or reveal a hidden one from a world card.'
            }
          />
        ) : (
          <div className='flex min-w-0 flex-col gap-3'>
            {journeys.map((journey) => (
              <VoyageCard key={journey.id} journey={journey} index={index} />
            ))}
          </div>
        )}
      </Section>
      <Section
        title='Great expeditions'
        description='Quests of the whole cosmos, each with a deadline in epochs.'
        level={3}
      >
        {expeditions.isPending ? (
          <Skeleton className='h-24 w-full' />
        ) : expeditions.isError ? (
          <Text tone='destructive'>{expeditions.error.message}</Text>
        ) : great.length === 0 ? (
          <EmptyState
            icon={Compass}
            size='compact'
            title='No great expedition'
            description='Proclaim one in Command › Proclaim a legendary quest, or wait for Fate to open one.'
          />
        ) : (
          <div className='flex min-w-0 flex-col gap-3'>
            {great.map((expedition) => (
              <ExpeditionCard
                key={expedition.thread_id}
                expedition={expedition}
              />
            ))}
          </div>
        )}
      </Section>
      <Section title='Send on a voyage' level={3} surface='card'>
        <SendVoyageForm index={index} rules={rules} defaultWorldId={worldId} />
      </Section>
    </div>
  )
}

import { useNavigate, useSearch } from '@tanstack/react-router'
import { navItem } from '@/config/navigation'
import {
  CircleAlert,
  MicOff,
  RefreshCw,
  Speech,
  UsersRound,
} from 'lucide-react'
import { useIsMobile } from '@/hooks/useIsMobile'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  AsideLayout,
  EmptyState,
  LoadingBlock,
  PageHeader,
  Section,
} from '@/components/domain'
import { ModelNeeded } from '@/features/providers/ModelNeeded'
import { AudiencePanel } from './AudiencePanel'
import { PastAudiences } from './PastAudiences'
import { PresenceStage, STAGE_ID } from './PresenceStage'
import { SpeakerRail } from './SpeakerRail'
import { SummonForm } from './SummonForm'
import { isNotSpeaker, useSpeaker } from './api'
import { validatePresenceSearch } from './presenceSearch'
import { usePresenceStream } from './usePresenceStream'

const ITEM = navItem('presence')
const STACKED = '(max-width: 79.99rem)'

function Chosen({ nodeId }: { nodeId: number }) {
  const speaker = useSpeaker(nodeId)
  if (speaker.isPending)
    return (
      <Section title='Summoning' icon={Speech} surface='card'>
        <LoadingBlock label='Calling the speaker before you' />
      </Section>
    )
  if (speaker.isError)
    return (
      <Section title='Summon to Presence' icon={Speech} surface='card'>
        {isNotSpeaker(speaker.error) ? (
          <EmptyState
            icon={MicOff}
            title='This one cannot be summoned'
            description='Only a son, a foreign god, or a mortal, spirit, being or beast with a mind of its own can speak. The Creator, places, peoples and other collectives cannot; their members can.'
          />
        ) : (
          <EmptyState
            icon={CircleAlert}
            title='The speaker could not be called'
            description={speaker.error.message}
            action={
              <Button
                variant='outline'
                size='sm'
                onClick={() => void speaker.refetch()}
              >
                <RefreshCw />
                Try again
              </Button>
            }
          />
        )}
      </Section>
    )
  const view = speaker.data
  const card = view.card
  return (
    <>
      <PresenceStage view={view} />
      <ModelNeeded role='conversation' what='An audience' />
      {view.open_session ? (
        <AudiencePanel
          key={view.open_session.id}
          speaker={card}
          session={view.open_session}
          modelEnabled={view.model_enabled}
        />
      ) : (
        <SummonForm
          key={card.node_id}
          speaker={card}
          modelEnabled={view.model_enabled}
        />
      )}
      <PastAudiences key={`past-${String(card.node_id)}`} view={view} />
    </>
  )
}

export function PresenceScreen() {
  usePresenceStream()
  const search = validatePresenceSearch(useSearch({ strict: false }))
  const navigate = useNavigate()
  const selected = search.node ?? null
  const phone = useIsMobile()
  const select = (node: number) => {
    void navigate({
      to: '.',
      search: (previous: Record<string, unknown>) => ({ ...previous, node }),
    })
    if (!window.matchMedia(STACKED).matches) return
    window.requestAnimationFrame(() =>
      document
        .getElementById(STAGE_ID)
        ?.scrollIntoView({ block: 'start', behavior: 'smooth' })
    )
  }
  const folded = phone && selected !== null
  return (
    <>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
      />
      <AsideLayout
        side='start'
        aside={
          <Section
            title='Who can speak'
            icon={UsersRound}
            surface='card'
            level={3}
          >
            {folded ? (
              <Collapsible className='flex min-w-0 flex-col gap-3'>
                <CollapsibleTrigger asChild>
                  <Button variant='outline' className='w-full'>
                    <UsersRound />
                    Summon someone else
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent className='flex min-w-0 flex-col gap-3'>
                  <SpeakerRail selected={selected} onSelect={select} />
                </CollapsibleContent>
              </Collapsible>
            ) : (
              <SpeakerRail selected={selected} onSelect={select} />
            )}
          </Section>
        }
      >
        {selected === null ? (
          <Section title='Summon to Presence' icon={Speech} surface='card'>
            <EmptyState
              icon={Speech}
              title='Choose who to summon'
              description='Pick a son, a foreign god, a mortal, a spirit, a being or a beast from the list. It answers as itself, from its own mind and memories, and may act through its own tools when the audience is on the record.'
            />
          </Section>
        ) : (
          <Chosen key={selected} nodeId={selected} />
        )}
      </AsideLayout>
    </>
  )
}

import { useState } from 'react'
import { ArrowLeft, CircleAlert, History, RefreshCw } from 'lucide-react'
import { formatDateTime } from '@/lib/format'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EmptyState, LoadingBlock, Paged, Section } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { SessionBadges } from './AudiencePanel'
import { ExchangeList } from './AudienceTranscript'
import { DeadSeal } from './DeadSeal'
import { useSession } from './api'
import { GUISE_LOOK, audienceSpeaker, deathText } from './looks'
import {
  type PresenceSessionSummary,
  type SpeakerCard,
  type SpeakerView,
} from './types'

const AUDIENCES_SHOWN = 6

function audienceTitle(session: PresenceSessionSummary): string {
  return session.title || `Audience of epoch ${String(session.opened_epoch)}`
}

function PastAudience({
  speaker,
  summary,
  onBack,
}: {
  speaker: SpeakerCard
  summary: PresenceSessionSummary
  onBack: () => void
}) {
  const view = useSession(summary.id)
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <Button variant='ghost' size='sm' className='w-fit' onClick={onBack}>
        <ArrowLeft />
        Every past audience
      </Button>
      <div className='flex min-w-0 flex-col gap-1.5 rounded-md surface-sheen px-3 py-2.5'>
        <Text weight='semibold' className='text-gilded font-display'>
          {audienceTitle(summary)}
        </Text>
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <SessionBadges session={summary} />
          {summary.dead_when_summoned && (
            <DeadSeal size='sm' death={deathText(speaker)} />
          )}
        </div>
        <Muted variant='caption'>
          {[
            `Opened in epoch ${String(summary.opened_epoch)}, ${formatDateTime(summary.opened_at)}`,
            summary.closed_at
              ? `ended ${formatDateTime(summary.closed_at)}`
              : '',
            plural(summary.exchange_count, 'exchange'),
          ]
            .filter(Boolean)
            .join(' · ')}
        </Muted>
      </div>
      {view.isPending ? (
        <LoadingBlock label='Opening the audience' />
      ) : view.isError ? (
        <EmptyState
          size='compact'
          icon={CircleAlert}
          title='The audience could not be opened'
          description={view.error.message}
          action={
            <Button
              variant='outline'
              size='sm'
              onClick={() => void view.refetch()}
            >
              <RefreshCw />
              Try again
            </Button>
          }
        />
      ) : view.data.exchanges.length === 0 ? (
        <Muted variant='caption'>
          This audience ended before a word was said.
        </Muted>
      ) : (
        <div
          role='log'
          aria-label={`${audienceTitle(summary)}, read only`}
          className='flex min-w-0 flex-col gap-5'
        >
          <ExchangeList
            exchanges={view.data.exchanges}
            boundary={0}
            speaker={audienceSpeaker(speaker)}
            session={view.data.session}
          />
        </div>
      )}
    </div>
  )
}

export function PastAudiences({ view }: { view: SpeakerView }) {
  const [open, setOpen] = useState<number | null>(null)
  const speaker = view.card
  const sessions = view.past_sessions
  const chosen = sessions.find((session) => session.id === open) ?? null
  return (
    <Section
      id='presence-past'
      title='Past audiences'
      icon={History}
      level={3}
      description={`Every audience with ${speaker.name} kept on the record. Off-the-record audiences leave nothing here.`}
    >
      {chosen ? (
        <PastAudience
          speaker={speaker}
          summary={chosen}
          onBack={() => setOpen(null)}
        />
      ) : sessions.length === 0 ? (
        <EmptyState
          size='compact'
          icon={History}
          title='No audience kept yet'
          description={`When an audience on the record ends, it is kept here, in ${speaker.name}'s entry, the lore book and the Codex.`}
        />
      ) : (
        <ul
          aria-label={`Past audiences with ${speaker.name}`}
          className='flex min-w-0 flex-col gap-2'
        >
          <Paged
            items={sessions}
            initial={AUDIENCES_SHOWN}
            as='li'
            noun={['audience', 'audiences']}
          >
            {(item) => {
              const guise = GUISE_LOOK[item.guise]
              const Icon = guise.icon
              return (
                <li key={item.id}>
                  <Button
                    variant='outline'
                    size='tile'
                    onClick={() => setOpen(item.id)}
                  >
                    <Icon />
                    <span className='flex min-w-0 flex-1 flex-col'>
                      <Text as='span' weight='semibold' truncate>
                        {audienceTitle(item)}
                      </Text>
                      <Muted as='span' variant='caption' truncate={2}>
                        {[
                          `As ${guise.label}`,
                          `epoch ${String(item.opened_epoch)}`,
                          formatDateTime(item.opened_at),
                          item.dead_when_summoned ? 'summoned from death' : '',
                        ]
                          .filter(Boolean)
                          .join(' · ')}
                      </Muted>
                    </span>
                    <Badge size='sm' variant='outline'>
                      {plural(item.exchange_count, 'exchange')}
                    </Badge>
                  </Button>
                </li>
              )
            }}
          </Paged>
        </ul>
      )}
    </Section>
  )
}

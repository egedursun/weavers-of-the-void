import { useState } from 'react'
import {
  CalendarClock,
  CircleCheck,
  CircleX,
  Gavel,
  UsersRound,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import {
  EmptyState,
  KpiTile,
  Medallion,
  Portrait,
  Section,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { ActionJob } from '@/features/pantheon/ActionJob'
import { useSons, useWorldState } from '@/features/pantheon/api'
import { COUNCILS_SHOWN } from '@/features/pantheon/constants'
import { useGodGate, useRuleLookup } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { mediaUrl } from '@/features/pantheon/media'
import { CouncilRecord } from './CouncilRecord'
import { useCouncils } from './api'
import { councilFrequencyText } from './frequency'

const TOPIC_MAX = 400
const PERCENT = 100

export function CouncilBlock({ showAll = false }: { showAll?: boolean }) {
  const councils = useCouncils()
  const sons = useSons()
  const state = useWorldState()
  const rule = useRuleLookup()
  const { reason } = useGodGate()
  const [topic, setTopic] = useState('')
  const [expanded, setExpanded] = useState(showAll)
  const cost = rule('balance.council')
  const minimum = rule('council.min_members')
  const attending = (sons.data ?? []).filter(
    (view) => view.son.status === 'active' || view.son.status === 'asleep'
  )
  const awake = attending.length
  const convene = useGodAction({
    run: () =>
      unwrap(api.POST('/api/councils', { body: { topic: topic.trim() } })),
    success: 'The council is convening; the debate is in the live feed',
    onDone: () => setTopic(''),
  })
  const blocked =
    reason({ cost, world: true, llm: true }) ??
    (minimum !== undefined && awake < minimum
      ? `The council needs at least ${minimum} awake sons.`
      : null)
  const list = councils.data ?? []
  const shown = expanded ? list : list.slice(0, COUNCILS_SHOWN)
  const accepted = list.filter((council) => council.passed).length
  const interval =
    state.data?.world?.council_every_epochs ?? rule('council.default_interval')
  const last = list.reduce((top, council) => Math.max(top, council.epoch), 0)
  return (
    <Section
      title='Council of the Gods'
      description={councilFrequencyText(
        state.data?.world?.council_every_epochs,
        rule('council.default_interval')
      )}
    >
      {showAll && list.length > 0 && (
        <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4'>
          <KpiTile
            label='Sessions'
            icon={Gavel}
            value={list.length}
            hint={last > 0 ? `Last in Epoch ${last}` : undefined}
          />
          <KpiTile
            label='Accepted'
            icon={CircleCheck}
            tone='success'
            value={accepted}
            meter={{
              value: accepted,
              max: list.length,
              label: 'Accepted share',
            }}
            hint={`${Math.round((accepted / list.length) * PERCENT)}% of motions pass`}
          />
          <KpiTile
            label='Rejected'
            icon={CircleX}
            tone='danger'
            value={list.length - accepted}
          />
          <KpiTile
            label='Rhythm'
            icon={CalendarClock}
            tone='info'
            value={
              interval === undefined
                ? '—'
                : interval <= 0
                  ? 'On call'
                  : `Every ${interval}`
            }
            hint={
              interval !== undefined && interval > 0 && last > 0
                ? `Next on its own around Epoch ${last + interval}`
                : 'Convenes only when you call it'
            }
          />
        </div>
      )}
      <form
        className='flex min-w-0 flex-col gap-3 rounded-xl border bg-card p-4'
        onSubmit={(event) => {
          event.preventDefault()
          if (!blocked) convene.mutate()
        }}
      >
        <div className='flex min-w-0 flex-wrap items-center gap-3'>
          <Medallion icon={UsersRound} />
          <div className='flex min-w-0 flex-1 flex-col'>
            <Text as='span' weight='semibold'>
              Convene the council
            </Text>
            <Label>{`${awake} sons would attend${minimum !== undefined ? ` · at least ${minimum} needed` : ''}`}</Label>
          </div>
          <ul
            aria-label='Sons who would attend'
            className='flex min-w-0 flex-wrap items-center gap-1'
          >
            {attending.map((view) => (
              <li key={view.son.id}>
                <Portrait
                  name={view.son.name}
                  src={mediaUrl(view.cover)}
                  size='xs'
                  rarity={view.son.rarity}
                />
              </li>
            ))}
          </ul>
        </div>
        <FieldLabel htmlFor='council-topic'>Agenda (optional)</FieldLabel>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Input
            id='council-topic'
            className='flex-1 basis-60'
            value={topic}
            maxLength={TOPIC_MAX}
            placeholder='How can the doom clock be stopped?'
            aria-describedby='council-topic-hint'
            onChange={(event) => setTopic(event.target.value)}
          />
          <ActionButton
            label='Convene the council'
            icon={UsersRound}
            variant='default'
            cost={cost}
            rule='balance.council'
            blocked={blocked}
            pending={convene.isPending}
            onRun={() => convene.mutate()}
          />
        </div>
        <Muted id='council-topic-hint' variant='caption'>
          {topic.trim()
            ? 'The brothers will debate this agenda.'
            : 'Leave it empty and the agent will choose the topic.'}
        </Muted>
      </form>
      <ActionJob
        jobId={convene.jobId}
        title='Council'
        onDismiss={convene.clearJob}
      />
      {councils.isPending ? (
        <Skeleton className='h-textarea w-full' />
      ) : councils.isError ? (
        <Text tone='destructive'>{councils.error.message}</Text>
      ) : list.length === 0 ? (
        <EmptyState
          icon={UsersRound}
          size='compact'
          title='The council has never convened'
          description='Call the brothers together, with an agenda or without one.'
        />
      ) : (
        <div className='flex min-w-0 flex-col gap-3'>
          {shown.map((council, index) => (
            <CouncilRecord
              key={council.id}
              council={council}
              defaultOpen={index === 0}
            />
          ))}
          {list.length > COUNCILS_SHOWN && (
            <Button
              variant='ghost'
              size='sm'
              className='self-start'
              onClick={() => setExpanded(!expanded)}
            >
              {expanded
                ? 'Show less'
                : `Show all councils (${list.length - COUNCILS_SHOWN} more)`}
            </Button>
          )}
        </div>
      )}
    </Section>
  )
}

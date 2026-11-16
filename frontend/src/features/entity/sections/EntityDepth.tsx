import { BookOpenText, EyeOff, Feather } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatInteger } from '@/lib/format'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  EmptyState,
  ExpandableText,
  JobProgress,
  KeyValueList,
  PagedList,
  Section,
} from '@/components/domain'
import { type LinkTarget, MentionText } from '@/components/domain/MentionText'
import { Label, Muted, Text } from '@/components/typography'
import { useLoreGate } from '../actions/gate'
import { humanize } from '../actions/schema'
import { useJob, useLoreMutation, useRunningJob } from '../api/mutations'
import { type EntityRecord } from '../api/types'

type EntityDepthProps = { entity: EntityRecord; targets?: LinkTarget[] }

export function EntityDepth({ entity, targets }: EntityDepthProps) {
  const depth = entity.depth
  const gate = useLoreGate()
  const running = useRunningJob('deepen', 'entity_id', entity.id)
  const deepen = useLoreMutation({
    run: () =>
      unwrap(
        api.POST('/api/entities/{entity_id}/deepen', {
          params: { path: { entity_id: entity.id } },
        })
      ),
    success: 'Deepening…',
    quiet: false,
  })
  const ownJob = useJob(
    running?.id ?? (deepen.data ? deepen.data.job_id : null)
  )
  const reason =
    gate.reason({ llm: true }) ??
    (running ? 'The deepening is under way.' : null) ??
    (deepen.isPending ? 'Working on it.' : null)
  const specifics = Object.entries(depth?.specifics ?? {})
  return (
    <Section
      id='section-depth'
      title='Depth'
      description={
        depth
          ? `Written in epoch ${formatInteger(depth.epoch)}`
          : "History, rumours and mortals' sayings"
      }
      actions={
        <Button
          variant='outline'
          disabled={reason !== null}
          disabledReason={reason ?? undefined}
          onClick={() => deepen.mutate()}
        >
          <Feather />
          {depth ? 'Deepen again' : 'Deepen'}
        </Button>
      }
    >
      {ownJob.data && (
        <JobProgress job={ownJob.data} title={`Deepening of ${entity.name}`} />
      )}
      {!depth ? (
        <EmptyState
          size='compact'
          icon={BookOpenText}
          title='Not deepened yet'
          description='Its history, rumours and sayings are not written. It also happens by itself at the end of an epoch.'
        />
      ) : (
        <div className='flex min-w-0 flex-col gap-4'>
          {depth.history && (
            <ExpandableText variant='prose' lines={6}>
              <MentionText
                text={depth.history}
                targets={targets}
                selfId={entity.id}
              />
            </ExpandableText>
          )}
          {specifics.length > 0 && (
            <KeyValueList
              items={specifics.map(([key, value]) => ({
                key,
                label: humanize(key),
                value,
              }))}
            />
          )}
          {depth.sayings.length > 0 && (
            <div className='flex min-w-0 flex-col gap-2'>
              <Label variant='overline'>{`Sayings · ${depth.sayings.length}`}</Label>
              <PagedList
                items={depth.sayings}
                initial={4}
                noun={['saying', 'sayings']}
                className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'
                itemKey={(_, index) => index}
              >
                {(saying) => (
                  <li className='flex min-w-0 flex-col gap-1 rounded-md border surface-sheen border-gild/60 bg-card px-3 py-2'>
                    <Label>{humanize(saying.form)}</Label>
                    <ExpandableText italic lines={3}>
                      <MentionText
                        text={`“${saying.text}”`}
                        targets={targets}
                        selfId={entity.id}
                      />
                    </ExpandableText>
                  </li>
                )}
              </PagedList>
            </div>
          )}
          {depth.details.length > 0 && (
            <div className='flex min-w-0 flex-col gap-2'>
              <Label variant='overline'>{`Details · ${depth.details.length}`}</Label>
              <PagedList
                items={depth.details}
                initial={6}
                noun={['detail', 'details']}
                className='flex min-w-0 list-disc flex-col gap-1 ps-5'
                itemKey={(_, index) => index}
              >
                {(detail) => (
                  <Text as='li'>
                    <MentionText
                      text={detail}
                      targets={targets}
                      selfId={entity.id}
                    />
                  </Text>
                )}
              </PagedList>
            </div>
          )}
          {depth.rumours.length > 0 && (
            <div className='flex min-w-0 flex-col gap-2'>
              <Label variant='overline'>{`Rumours · ${depth.rumours.length}`}</Label>
              <PagedList
                items={depth.rumours}
                initial={5}
                noun={['rumour', 'rumours']}
                className='flex min-w-0 flex-col gap-1'
                itemKey={(_, index) => index}
              >
                {(rumour) => (
                  <Muted as='li' italic>
                    <MentionText
                      text={rumour}
                      targets={targets}
                      selfId={entity.id}
                    />
                  </Muted>
                )}
              </PagedList>
            </div>
          )}
          {depth.hidden_truth && (
            <Collapsible className='flex min-w-0 flex-col gap-2'>
              <CollapsibleTrigger asChild>
                <Button variant='ghost' size='sm' className='self-start'>
                  <EyeOff />
                  The hidden truth
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <Text>
                  <MentionText
                    text={depth.hidden_truth}
                    targets={targets}
                    selfId={entity.id}
                  />
                </Text>
              </CollapsibleContent>
            </Collapsible>
          )}
        </div>
      )}
    </Section>
  )
}

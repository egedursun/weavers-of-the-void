import { useState } from 'react'
import {
  Eye,
  EyeOff,
  Feather,
  MessageCircle,
  PenLine,
  Quote,
  ScrollText,
  Sparkle,
  Wand,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Textarea } from '@/components/ui/textarea'
import {
  EmptyState,
  FormRow,
  KeyValueList,
  Medallion,
  PagedList,
  Section,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { ActionJob } from '@/features/pantheon/ActionJob'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { humanize } from '@/features/pantheon/labels'
import { useWriteRefusal } from '@/features/team/writeGate'
import { type CelestialDepth } from './api'

export type CelestialKind =
  'world' | 'star' | 'galaxy' | 'cluster' | 'dimension'

const SAYING_SEPARATOR = ': '

type DepthDraft = {
  history: string
  rumours: string
  sayings: string
  details: string
  hidden_truth: string
}

function draftOf(depth: CelestialDepth | null): DepthDraft {
  return {
    history: depth?.history ?? '',
    rumours: (depth?.rumours ?? []).join('\n'),
    sayings: (depth?.sayings ?? [])
      .map((item) => `${item.form}${SAYING_SEPARATOR}${item.text}`)
      .join('\n'),
    details: (depth?.details ?? []).join('\n'),
    hidden_truth: depth?.hidden_truth ?? '',
  }
}

function lines(text: string): string[] {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
}

function sayingsOf(text: string): { form: string; text: string }[] {
  return lines(text).map((line) => {
    const at = line.indexOf(SAYING_SEPARATOR)
    return at > 0
      ? {
          form: line.slice(0, at).trim(),
          text: line.slice(at + SAYING_SEPARATOR.length).trim(),
        }
      : { form: 'saying', text: line }
  })
}

function DepthEditForm({
  kind,
  id,
  depth,
}: {
  kind: CelestialKind
  id: number
  depth: CelestialDepth | null
}) {
  const [draft, setDraft] = useState(() => draftOf(depth))
  const { reason } = useGodGate()
  const save = useGodAction({
    writes: [
      { lever: 'scale:depth' },
      { lever: 'star:depth' },
      { lever: 'world:depth' },
    ],
    run: () => {
      const body = {
        history: draft.history,
        rumours: lines(draft.rumours),
        sayings: sayingsOf(draft.sayings),
        details: lines(draft.details),
        hidden_truth: draft.hidden_truth,
      }
      if (kind === 'world')
        return unwrap(
          api.POST('/api/actions/world:depth', {
            body: { world_id: id, ...body },
          })
        )
      if (kind === 'star')
        return unwrap(
          api.POST('/api/actions/star:depth', {
            body: { star_id: id, ...body },
          })
        )
      return unwrap(
        api.POST('/api/actions/scale:depth', {
          body: { node_id: id, ...body },
        })
      )
    },
    success: 'The lore was rewritten',
  })
  const field = (key: keyof DepthDraft) => (value: string) =>
    setDraft({ ...draft, [key]: value })
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-4'>
      <FormRow label='History'>
        {(fieldId) => (
          <Textarea
            id={fieldId}
            value={draft.history}
            onChange={(event) => field('history')(event.target.value)}
          />
        )}
      </FormRow>
      <FormRow label='Rumours' description='One rumour per line.'>
        {(fieldId) => (
          <Textarea
            id={fieldId}
            value={draft.rumours}
            onChange={(event) => field('rumours')(event.target.value)}
          />
        )}
      </FormRow>
      <FormRow
        label='Sayings'
        description='One per line, as "form: text", for example "proverb: Salt remembers."'
      >
        {(fieldId) => (
          <Textarea
            id={fieldId}
            value={draft.sayings}
            onChange={(event) => field('sayings')(event.target.value)}
          />
        )}
      </FormRow>
      <FormRow label='Details' description='One concrete detail per line.'>
        {(fieldId) => (
          <Textarea
            id={fieldId}
            value={draft.details}
            onChange={(event) => field('details')(event.target.value)}
          />
        )}
      </FormRow>
      <FormRow label='Hidden truth'>
        {(fieldId) => (
          <Textarea
            id={fieldId}
            value={draft.hidden_truth}
            onChange={(event) => field('hidden_truth')(event.target.value)}
          />
        )}
      </FormRow>
      <div>
        <ActionButton
          act={save}
          label='Save the lore'
          variant='default'
          blocked={reason()}
          pending={save.isPending}
          onRun={() => save.mutate()}
        />
      </div>
    </div>
  )
}

export function CelestialDepthSection({
  kind,
  id,
  name,
  depth,
}: {
  kind: CelestialKind
  id: number
  name: string
  depth: CelestialDepth | null
}) {
  const formGate = {
    blockedReason: useWriteRefusal([
      { lever: 'scale:depth' },
      { lever: 'star:depth' },
      { lever: 'world:depth' },
    ]),
  }
  const { reason } = useGodGate()
  const [truthShown, setTruthShown] = useState(false)
  const deepen = useGodAction({
    writes: [
      { method: 'POST', path: '/api/cosmography/nodes/{node_id}/deepen' },
      { method: 'POST', path: '/api/stars/{star_id}/deepen' },
      { method: 'POST', path: '/api/worlds/{world_id}/deepen' },
    ],
    run: () => {
      if (kind === 'world')
        return unwrap(
          api.POST('/api/worlds/{world_id}/deepen', {
            params: { path: { world_id: id } },
          })
        )
      if (kind === 'star')
        return unwrap(
          api.POST('/api/stars/{star_id}/deepen', {
            params: { path: { star_id: id } },
          })
        )
      return unwrap(
        api.POST('/api/cosmography/nodes/{node_id}/deepen', {
          params: { path: { node_id: id } },
        })
      )
    },
    success: `The lore of ${name} is being written`,
  })
  const written = Boolean(
    depth &&
    (depth.history ||
      depth.rumours.length ||
      depth.sayings.length ||
      depth.details.length ||
      depth.hidden_truth)
  )
  const specifics = Object.entries(depth?.specifics ?? {})
  return (
    <Section
      id='section-celestial-depth'
      title='Lore and depth'
      description={
        written && depth
          ? `Written in epoch ${depth.epoch}.`
          : `What the peoples and the gods tell of ${name}.`
      }
      actions={
        <ActionButton
          act={deepen}
          label={written ? 'Deepen again' : 'Deepen'}
          icon={Wand}
          blocked={reason({ llm: true })}
          pending={deepen.isPending}
          onRun={() => deepen.mutate()}
        />
      }
    >
      <ActionJob
        jobId={deepen.jobId}
        title='Deepening'
        onDismiss={deepen.clearJob}
      />
      {!written ? (
        <EmptyState
          icon={ScrollText}
          size='compact'
          title={`The lore of ${name} is not written yet`}
          description='Deepen it with the lore writer, or write it yourself below.'
        />
      ) : (
        depth && (
          <div className='flex min-w-0 flex-col gap-5'>
            {depth.history && (
              <div className='flex min-w-0 flex-col gap-3'>
                <Label variant='overline'>History</Label>
                {depth.history.split(/\n{2,}/).map((paragraph, index) => (
                  <Text key={index} variant='prose'>
                    {paragraph}
                  </Text>
                ))}
              </div>
            )}
            {depth.rumours.length > 0 && (
              <div className='flex min-w-0 flex-col gap-2'>
                <Label variant='overline'>Rumours</Label>
                <PagedList
                  items={depth.rumours}
                  initial={5}
                  noun={['rumour', 'rumours']}
                  className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2'
                  itemKey={(_, index) => index}
                >
                  {(rumour) => (
                    <li className='flex min-w-0 items-start gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
                      <Medallion icon={MessageCircle} tone='info' size='sm' />
                      <Text variant='caption'>{rumour}</Text>
                    </li>
                  )}
                </PagedList>
              </div>
            )}
            {depth.sayings.length > 0 && (
              <div className='flex min-w-0 flex-col gap-2'>
                <Label variant='overline'>Sayings</Label>
                <PagedList
                  items={depth.sayings}
                  initial={4}
                  noun={['saying', 'sayings']}
                  className='flex min-w-0 flex-col gap-2'
                  itemKey={(_, index) => index}
                >
                  {(saying) => (
                    <li className='flex min-w-0 items-start gap-3 rounded-md rounded-tl-sm border surface-framed border-primary/30 bg-primary/5 p-3'>
                      <Quote
                        aria-hidden='true'
                        className='size-icon-sm shrink-0 text-primary'
                      />
                      <div className='flex min-w-0 flex-1 flex-col gap-1'>
                        <Text italic>{saying.text}</Text>
                        <Badge
                          size='sm'
                          variant='outline'
                          className='self-start'
                        >
                          <Feather />
                          {humanize(saying.form)}
                        </Badge>
                      </div>
                    </li>
                  )}
                </PagedList>
              </div>
            )}
            {depth.details.length > 0 && (
              <div className='flex min-w-0 flex-col gap-2'>
                <Label variant='overline'>Details</Label>
                <PagedList
                  items={depth.details}
                  initial={6}
                  noun={['detail', 'details']}
                  className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2'
                  itemKey={(_, index) => index}
                >
                  {(detail) => (
                    <li className='flex min-w-0 items-start gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2.5'>
                      <Sparkle
                        aria-hidden='true'
                        className='size-icon-sm shrink-0 text-brand-verdigris'
                      />
                      <Text variant='caption'>{detail}</Text>
                    </li>
                  )}
                </PagedList>
              </div>
            )}
            {specifics.length > 0 && (
              <KeyValueList
                items={specifics.map(([key, value]) => ({
                  label: humanize(key),
                  value,
                }))}
              />
            )}
            {depth.hidden_truth && (
              <div className='flex min-w-0 flex-col gap-2 rounded-md border-warning/50 p-3 sealed-well'>
                <div className='flex min-w-0 items-center gap-3'>
                  <Medallion
                    icon={truthShown ? Eye : EyeOff}
                    tone='warning'
                    size='sm'
                  />
                  <Text as='span' weight='medium' className='flex-1'>
                    Hidden truth
                  </Text>
                  <Button
                    variant='ghost'
                    size='sm'
                    aria-expanded={truthShown}
                    onClick={() => setTruthShown(!truthShown)}
                  >
                    {truthShown ? <EyeOff /> : <Eye />}
                    {truthShown ? 'Hide' : 'Reveal'}
                  </Button>
                </div>
                {truthShown ? (
                  <Text variant='prose'>{depth.hidden_truth}</Text>
                ) : (
                  <Muted variant='caption'>
                    Only the gods know it; the mortals never will.
                  </Muted>
                )}
              </div>
            )}
          </div>
        )
      )}
      <Collapsible className='flex min-w-0 flex-col gap-3'>
        <CollapsibleTrigger asChild>
          <Button
            act={formGate}
            variant='ghost'
            size='sm'
            className='self-start'
          >
            <PenLine />
            Write the lore yourself
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <DepthEditForm
            key={JSON.stringify(depth)}
            kind={kind}
            id={id}
            depth={depth}
          />
        </CollapsibleContent>
      </Collapsible>
    </Section>
  )
}

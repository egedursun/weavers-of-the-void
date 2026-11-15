import { Ban, Eye, Gauge, ShieldCheck, Undo2 } from 'lucide-react'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Muted } from '@/components/typography'
import { Chip, RecordRow } from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import {
  type KindChangeView,
  type TransformProspectView,
  useTransformAction,
  useTransformTimeline,
} from './api'
import {
  PROSPECT_STANCES,
  TRANSFORM_ENDS,
  TRANSFORM_ICON,
  TRANSFORM_KINDS,
  TRANSFORM_STATES,
  TRANSFORM_TRIGGERS,
} from './labels'

const SHOWN = 8

type Timeline = NonNullable<ReturnType<typeof useTransformTimeline>['data']>

function Happened({
  row,
  blocked,
}: {
  row: KindChangeView
  blocked: string | null
}) {
  const kind = TRANSFORM_KINDS[row.kind]
  const state = TRANSFORM_STATES[row.state]
  const trigger = TRANSFORM_TRIGGERS[row.trigger]
  const reverting = useTransformAction(
    'transform:revert',
    (_: void) => ({ transformation_id: row.id }),
    'The transformation is undone'
  )
  return (
    <RecordRow
      icon={kind.icon}
      tone={kind.tone}
      title={kind.label}
      caption={`Epoch ${row.epoch}: ${row.text ?? `${row.subject_name || 'a thing'} became ${row.result_name ?? 'another thing'}`}`}
      aside={
        <div className='flex min-w-0 flex-wrap gap-1'>
          <Chip icon={state.icon}>{state.label}</Chip>
          <Chip icon={trigger.icon}>{trigger.label}</Chip>
        </div>
      }
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Ref
          node={row.subject}
          empty={row.subject_name || 'a thing no longer kept'}
        />
        <Muted variant='caption'>became</Muted>
        <Ref
          node={row.result}
          empty={row.result_name ?? 'a thing no longer kept'}
        />
      </div>
      <StepButton
        icon={Undo2}
        label='Undo it'
        busy={why(
          blocked ??
            (row.revertible
              ? null
              : row.state === 'reverted'
                ? 'It is already undone'
                : 'Only a change of this epoch that kept a ledger can be undone'),
          reverting.isPending
        )}
        onClick={() => reverting.mutate()}
      />
    </RecordRow>
  )
}

function Coming({
  row,
  data,
  blocked,
}: {
  row: TransformProspectView
  data: Timeline
  blocked: string | null
}) {
  const kind = TRANSFORM_KINDS[row.kind]
  const stance = PROSPECT_STANCES[row.stance]
  const subject =
    data.subjects.find((node) => node.id === row.subject_id) ?? null
  const blocking = useTransformAction(
    row.stance === 'blocked' ? 'transform:release' : 'transform:block',
    (_: void) => ({ kind: row.kind, subject_id: row.subject_id }),
    row.stance === 'blocked' ? 'It may come again' : 'It is blocked'
  )
  return (
    <RecordRow
      icon={kind.icon}
      tone={kind.tone}
      title={kind.label}
      caption={`${row.progress} of 100${row.warned_epoch !== null ? `, warned in epoch ${row.warned_epoch}` : ''}`}
      aside={<Chip icon={stance.icon}>{stance.label}</Chip>}
    >
      <Ref node={subject} empty='a thing no longer kept' />
      <StepButton
        icon={row.stance === 'blocked' ? ShieldCheck : Ban}
        label={row.stance === 'blocked' ? 'Let it come' : 'Block it'}
        busy={why(blocked, blocking.isPending)}
        onClick={() => blocking.mutate()}
      />
    </RecordRow>
  )
}

export function TransformTimelinePanel({
  readOnlyReason = null,
}: {
  readOnlyReason?: string | null
}) {
  const query = useTransformTimeline()
  const happened = useShowMore(
    query.data?.transformations ?? [],
    SHOWN,
    SHOWN * 2
  )
  const coming = useShowMore(query.data?.prospects ?? [], SHOWN, SHOWN * 2)
  const kinds = useShowMore(query.data?.kinds ?? [], SHOWN, SHOWN * 2)
  return (
    <Section
      id='section-transformation-timeline'
      title='Transformations across the cosmos'
      description='Every change of kind that has happened, every one under way, and every way one kind of thing can become another.'
      icon={TRANSFORM_ICON}
      tone='gold'
    >
      <div
        data-surface='TransformTimelinePanel'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the changes of kind' />
        ) : query.isError ? (
          <EmptyState
            icon={TRANSFORM_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
              <KpiTile
                label='Changes of kind so far'
                value={String(query.data.transformations.length)}
                icon={TRANSFORM_ICON}
                tone='gold'
              />
              <KpiTile
                label='Under way'
                value={String(query.data.prospects.length)}
                icon={Gauge}
                tone='warning'
              />
              <KpiTile
                label='Epoch'
                value={String(query.data.epoch)}
                icon={Eye}
                tone='muted'
              />
            </div>
            <Bars
              chart='chart-transformations-cosmos'
              title='The nearest changes'
              legend={[{ text: 'Progress', variant: 'warning' }]}
              rows={coming.visible.map((row) => ({
                key: String(row.id),
                caption: TRANSFORM_KINDS[row.kind].label,
                segments: [{ value: row.progress, fill: 'fill-warning' }],
              }))}
              max={100}
              noun={['change', 'changes']}
              empty='No change of kind is under way.'
            />
            {query.data.prospects.length ? (
              <ul className='flex min-w-0 flex-col gap-2'>
                {coming.visible.map((row) => (
                  <Coming
                    key={row.id}
                    row={row}
                    data={query.data}
                    blocked={readOnlyReason}
                  />
                ))}
              </ul>
            ) : null}
            <ShowMore state={coming} />
            {query.data.transformations.length ? (
              <ul className='flex min-w-0 flex-col gap-2'>
                {happened.visible.map((row) => (
                  <Happened key={row.id} row={row} blocked={readOnlyReason} />
                ))}
              </ul>
            ) : (
              <EmptyState
                icon={TRANSFORM_ICON}
                size='inline'
                title='Nothing has changed its kind yet'
                description='When a son falls, a people forgets itself or a star gains a god, it is set down here.'
              />
            )}
            <ShowMore state={happened} />
            <ul className='flex min-w-0 flex-col gap-2'>
              {kinds.visible.map((row) => {
                const kind = TRANSFORM_KINDS[row.kind]
                const source = TRANSFORM_ENDS[row.source]
                const target = TRANSFORM_ENDS[row.target]
                return (
                  <RecordRow
                    key={row.kind}
                    icon={kind.icon}
                    tone={kind.tone}
                    title={kind.label}
                    caption={`${source.label} into ${target.label.toLowerCase()}`}
                    aside={
                      <div className='flex min-w-0 flex-wrap gap-1'>
                        <Chip icon={row.watched ? Eye : Gauge}>
                          {row.watched
                            ? 'Watched each epoch'
                            : 'Comes at its own moment'}
                        </Chip>
                        {row.warned ? (
                          <Chip icon={Ban}>Announced ahead</Chip>
                        ) : null}
                        <Chip icon={TRANSFORM_ICON}>
                          {row.existing
                            ? 'Older than the registry'
                            : 'New with the registry'}
                        </Chip>
                      </div>
                    }
                  />
                )
              })}
            </ul>
            <ShowMore state={kinds} />
          </>
        )}
      </div>
    </Section>
  )
}

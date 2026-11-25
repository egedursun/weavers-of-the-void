import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import {
  Ban,
  Check,
  FileText,
  ListChecks,
  Pause,
  PencilLine,
  RefreshCw,
  Play,
  SkipForward,
  TriangleAlert,
  Sparkles,
  StepForward,
  Undo2,
} from 'lucide-react'
import { toast } from 'sonner'
import { isReadOnly, READ_ONLY_MESSAGE } from '@/api/readOnly'
import { formatDateTime, formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { OrnateFrame } from '@/components/ui/ornate'
import { Progress } from '@/components/ui/progress'
import {
  ConfirmDialog,
  EmptyState,
  LoadingBlock,
  Medallion,
  MiniStat,
  Paged,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { ShareToggle } from '@/features/team/share'
import { PlanStepEditor } from './PlanStepEditor'
import { type PlanVerb, usePlan, usePlanCommand, useStepCommand } from './api'
import { IMPACT_LOOK, PLAN_STATUS_LOOK, STEP_STATUS_LOOK } from './planLook'
import { EDITABLE_PLANS, draftOf } from './planModel'
import { argumentSummary } from './toolLook'
import { type WillPlan, type WillPlanStep } from './types'
import { useNameOf } from './useNameOf'

const PERCENT = 100
const STEPS_SHOWN = 8

const VERB_DONE: Record<PlanVerb, string> = {
  approve: 'The plan is approved.',
  execute: 'The plan is under way.',
  pause: 'The plan is paused.',
  resume: 'The plan goes on.',
  abandon: 'The plan is abandoned.',
}

function StepRow({
  step,
  planId,
  planStatus,
  block,
}: {
  step: WillPlanStep
  planId: number
  planStatus: WillPlan['status']
  block: string | null
}) {
  const command = useStepCommand(planId)
  const look = STEP_STATUS_LOOK[step.status]
  const impact = IMPACT_LOOK[step.declared_impact]
  const StatusIcon = look.icon
  const ImpactIcon = impact.icon
  const nameOf = useNameOf()
  const inputs = argumentSummary(step.input, nameOf)
  const skipBlock =
    block ??
    (step.status !== 'pending' && step.status !== 'failed'
      ? 'Only a waiting or failed step can be skipped.'
      : planStatus === 'running'
        ? 'Pause the plan before skipping a step.'
        : command.isPending
          ? 'Your word is on its way.'
          : null)
  const undoBlock =
    block ??
    (step.ledger_entry_id === null
      ? 'This step left nothing in the ledger to undo; undo what its job made from the ledger.'
      : planStatus === 'running'
        ? 'Pause the plan before undoing a step.'
        : command.isPending
          ? 'Your word is on its way.'
          : null)
  const run = (verb: 'skip' | 'undo') =>
    command.mutate(
      { ordinal: step.ordinal, verb },
      {
        onSuccess: () =>
          toast.success(
            verb === 'skip' ? 'The step is skipped.' : 'The step is undone.'
          ),
        onError: (error) => toast.error(error.message),
      }
    )
  return (
    <li
      data-step-status={step.status}
      className={cn(
        'flex min-w-0 flex-col gap-2 rounded-md surface-sheen px-3 py-2.5',
        step.status === 'running' && 'border-primary/60',
        step.status === 'failed' && 'border-destructive/50'
      )}
    >
      <div className='flex min-w-0 items-start gap-2.5'>
        <Medallion icon={StatusIcon} tone={look.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='semibold'>
            {`${String(step.ordinal)}. ${step.title}`}
          </Text>
          <Muted as='span' variant='caption' truncate={2}>
            {[step.action_title || step.action_id, inputs]
              .filter(Boolean)
              .join(' · ')}
          </Muted>
        </div>
        <Badge size='sm' variant={look.badge}>
          <StatusIcon
            className={step.status === 'running' ? 'animate-spin' : undefined}
          />
          {look.label}
        </Badge>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Badge size='sm' variant={impact.badge}>
          <ImpactIcon />
          {impact.label}
        </Badge>
        {step.estimated_essence > 0 && (
          <Badge size='sm' variant='default'>
            <Sparkles />
            {formatInteger(step.estimated_essence)}
          </Badge>
        )}
        {step.depends_on.length > 0 && (
          <Badge size='sm' variant='outline'>
            {`Waits on ${step.depends_on.map(String).join(', ')}`}
          </Badge>
        )}
        <span aria-hidden='true' className='flex-1' />
        {step.job_id && (
          <Badge size='sm' variant='outline'>
            Ran as a job
          </Badge>
        )}
        {(step.status === 'pending' || step.status === 'failed') && (
          <Button
            act={command}
            variant='ghost'
            size='sm'
            disabled={skipBlock !== null}
            disabledReason={skipBlock ?? undefined}
            onClick={() => run('skip')}
          >
            <SkipForward />
            Skip
          </Button>
        )}
        {step.status === 'done' && (
          <Button
            act={command}
            variant='outline'
            size='sm'
            disabled={undoBlock !== null}
            disabledReason={undoBlock ?? undefined}
            onClick={() => run('undo')}
          >
            <Undo2 />
            Undo
          </Button>
        )}
      </div>
      {step.result_text && <Text variant='caption'>{step.result_text}</Text>}
      {step.error && (
        <Text variant='caption' tone='destructive' role='alert'>
          {step.error}
        </Text>
      )}
    </li>
  )
}

export function PlanCard({ planId }: { planId: number }) {
  const query = usePlan(planId)
  if (query.isPending) return <LoadingBlock label='Opening the plan' />
  if (query.isError)
    return (
      <EmptyState
        size='inline'
        icon={ListChecks}
        title='The plan could not be opened'
        description={query.error.message}
        action={
          <Button
            variant='outline'
            size='sm'
            onClick={() => void query.refetch()}
          >
            <RefreshCw />
            Try again
          </Button>
        }
      />
    )
  return <PlanBody plan={query.data} />
}

function PlanBody({ plan }: { plan: WillPlan }) {
  const command = usePlanCommand(plan.id)
  const [editing, setEditing] = useState(false)
  const [abandoning, setAbandoning] = useState(false)
  const look = PLAN_STATUS_LOOK[plan.status]
  const StatusIcon = look.icon
  const total = plan.steps.length
  const finished = plan.steps.filter(
    (step) => step.status === 'done' || step.status === 'skipped'
  ).length
  const essence = plan.steps.reduce(
    (sum, step) => sum + step.estimated_essence,
    0
  )
  const risky = plan.steps.filter(
    (step) => step.declared_impact !== 'safe'
  ).length
  const block = isReadOnly()
    ? READ_ONLY_MESSAGE
    : command.isPending
      ? 'Your word is on its way.'
      : null
  const editable = EDITABLE_PLANS.has(plan.status)
  const run = (verb: PlanVerb) =>
    command.mutate(verb, {
      onSuccess: () => toast.success(VERB_DONE[verb]),
      onError: (error) => toast.error(error.message),
    })
  const ended = plan.status === 'done' || plan.status === 'abandoned'
  const waiting =
    plan.steps.find((step) => step.ordinal === plan.waiting_step) ?? null
  return (
    <OrnateFrame
      frame='card'
      tone={look.tone}
      role='group'
      aria-label={`Plan: ${plan.title}`}
      data-domain='will-plan'
      data-status={plan.status}
      className='flex min-w-0 flex-col gap-3 p-4'
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={ListChecks} tone={look.tone} />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <Label variant='overline'>A plan of the Divine Will</Label>
          <Text weight='semibold' className='text-gilded font-display'>
            {plan.title}
          </Text>
        </div>
        <Badge size='sm' variant={look.badge}>
          <StatusIcon
            className={plan.status === 'running' ? 'animate-spin' : undefined}
          />
          {look.label}
        </Badge>
      </div>
      <ShareToggle
        kind='plan'
        id={plan.id}
        shared={plan.owner.shared}
        mine={plan.owner.mine}
        author={plan.owner.author_name}
      />
      <div className='grid min-w-0 grid-cols-1 gap-2 @md/will:grid-cols-3'>
        <MiniStat
          icon={StepForward}
          label='Steps done'
          value={`${String(finished)} / ${String(total)}`}
          tone='info'
        />
        <MiniStat
          icon={Sparkles}
          label='Essence foreseen'
          value={formatInteger(essence)}
          tone='gold'
        />
        <MiniStat
          icon={IMPACT_LOOK.destructive.icon}
          label='Steps that ask care'
          value={formatInteger(risky)}
          tone={risky > 0 ? 'warning' : 'success'}
          hint='Costly or destructive steps; approving the plan approves what each declares.'
        />
      </div>
      {plan.status !== 'draft' && (
        <Progress
          value={total > 0 ? (finished / total) * PERCENT : 0}
          tone={plan.status === 'failed' ? 'destructive' : 'default'}
          aria-label={`Plan progress, ${String(finished)} of ${String(total)} steps`}
        />
      )}
      {waiting && !editing && (
        <div
          role='status'
          className='flex min-w-0 items-start gap-2.5 rounded-md surface-well border-warning/50 px-3 py-2'
        >
          <TriangleAlert
            aria-hidden='true'
            className='size-icon-sm shrink-0 text-warning'
          />
          <div className='flex min-w-0 flex-col gap-0.5'>
            <Text as='span' variant='caption' weight='medium'>
              {`Step ${String(waiting.ordinal)} waits for your word`}
            </Text>
            <Muted as='span' variant='caption'>
              {waiting.error || 'Its rehearsal does more than it declared.'}{' '}
              Edit the plan to declare its true impact and approve it again, or
              skip the step.
            </Muted>
          </div>
        </div>
      )}
      {editing ? (
        <PlanStepEditor
          planId={plan.id}
          title={plan.title}
          initial={draftOf(plan)}
          onDone={() => setEditing(false)}
        />
      ) : (
        <ol className='flex min-w-0 flex-col gap-2'>
          <Paged
            items={plan.steps}
            initial={STEPS_SHOWN}
            as='li'
            noun={['step', 'steps']}
          >
            {(step) => (
              <StepRow
                key={step.ordinal}
                step={step}
                planId={plan.id}
                planStatus={plan.status}
                block={block}
              />
            )}
          </Paged>
        </ol>
      )}
      {!editing && (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          {plan.artifact_id !== null && (
            <Button variant='ghost' size='sm' asChild>
              <Link to='/library' search={{ artifact: plan.artifact_id }}>
                <FileText />
                In the Library
              </Link>
            </Button>
          )}
          <span aria-hidden='true' className='flex-1' />
          {!ended && (
            <Button
              act={command}
              variant='ghost'
              size='sm'
              disabled={block !== null || plan.status === 'running'}
              disabledReason={block ?? 'Pause the plan before abandoning it.'}
              onClick={() => setAbandoning(true)}
            >
              <Ban />
              Abandon
            </Button>
          )}
          {editable && (
            <Button
              act={command}
              variant='outline'
              size='sm'
              disabled={block !== null}
              disabledReason={block ?? undefined}
              onClick={() => setEditing(true)}
            >
              <PencilLine />
              Edit steps
            </Button>
          )}
          {plan.status === 'draft' && (
            <Button
              act={command}
              size='sm'
              disabled={block !== null || total === 0}
              disabledReason={block ?? 'Add a step before approving.'}
              onClick={() => run('approve')}
            >
              <Check />
              Approve
            </Button>
          )}
          {plan.status === 'approved' && (
            <Button
              act={command}
              size='sm'
              disabled={block !== null}
              disabledReason={block ?? undefined}
              onClick={() => run('execute')}
            >
              <Play />
              Execute
            </Button>
          )}
          {plan.status === 'running' && (
            <Button
              act={command}
              variant='outline'
              size='sm'
              disabled={block !== null}
              disabledReason={block ?? undefined}
              onClick={() => run('pause')}
            >
              <Pause />
              Pause
            </Button>
          )}
          {plan.status === 'failed' && (
            <Button
              act={command}
              size='sm'
              disabled={block !== null}
              disabledReason={block ?? undefined}
              onClick={() => run('execute')}
            >
              <Play />
              Run again
            </Button>
          )}
          {plan.status === 'paused' && (
            <Button
              act={command}
              size='sm'
              disabled={block !== null}
              disabledReason={block ?? undefined}
              onClick={() => run('resume')}
            >
              <Play />
              Resume
            </Button>
          )}
        </div>
      )}
      <Muted variant='caption'>
        {[
          plan.status === 'draft'
            ? 'Nothing in the world changes until you approve the plan and execute it.'
            : '',
          `Drafted ${formatDateTime(plan.created_at)}`,
          plan.approved_at
            ? `approved ${formatDateTime(plan.approved_at)}`
            : '',
          plan.finished_at
            ? `finished ${formatDateTime(plan.finished_at)}`
            : '',
          plan.job_id && plan.status === 'running'
            ? 'runs as a background work of the world'
            : '',
        ]
          .filter(Boolean)
          .join(' · ')}
      </Muted>
      <ConfirmDialog
        act={command}
        open={abandoning}
        onOpenChange={setAbandoning}
        title='Abandon this plan?'
        desc='The steps that have not run are dropped. Steps already done keep their acts, and each can still be undone from your ledger. The plan stays in the Library and the record.'
        confirmText='Abandon the plan'
        destructive
        isLoading={command.isPending}
        handleConfirm={() => {
          setAbandoning(false)
          run('abandon')
        }}
      />
    </OrnateFrame>
  )
}

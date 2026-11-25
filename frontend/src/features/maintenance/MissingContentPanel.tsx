import { type ReactNode, useMemo, useState } from 'react'
import {
  CircleAlert,
  CircleCheck,
  Crown,
  Ghost,
  ImagePlus,
  ListChecks,
  type LucideIcon,
  ScrollText,
  Sparkles,
  Star,
  Sun,
  Tags,
  Users,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import {
  EntityLink,
  Medallion,
  Paged,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useNames } from '@/features/pantheon/api'
import { useGodGate } from '@/features/pantheon/gate'
import { JobOutcome } from './JobOutcome'
import {
  type MissingContent,
  useMissingContent,
  useRunMaintenanceTask,
} from './api'

const NONE = 'Nothing missing'
const PERCENT = 100

function count(value: number, one: string, many: string): string {
  if (value === 0) return NONE
  return `${formatInteger(value)} ${value === 1 ? one : many}`
}

function epochList(epochs: number[]): string {
  if (epochs.length === 0) return NONE
  return `Epoch ${epochs.map(formatInteger).join(', ')}`
}

function useNameLookup() {
  const names = useNames()
  return useMemo(() => {
    const table = new Map<string, string>()
    for (const entry of names.data ?? [])
      table.set(`${entry.kind}:${entry.id}`, entry.name)
    return (kind: string, id: number) => table.get(`${kind}:${id}`)
  }, [names.data])
}

function RecordLinks({
  ids,
  kind,
  linkKind,
  fallback,
}: {
  ids: number[]
  kind: string
  linkKind: 'son' | 'foreign-god'
  fallback: string
}) {
  const nameOf = useNameLookup()
  const more = useShowMore(ids, ID_PAGE)
  if (ids.length === 0) return <>{NONE}</>
  return (
    <span className='flex min-w-0 flex-col gap-1'>
      <span className='flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1'>
        {more.visible.map((id) => (
          <EntityLink key={id} kind={linkKind} id={String(id)}>
            {nameOf(kind, id) ?? `${fallback} ${id}`}
          </EntityLink>
        ))}
      </span>
      <ShowMore state={more} noun={['record', 'records']} />
    </span>
  )
}

const ID_PAGE = 12

type Check = {
  key: string
  label: string
  icon: LucideIcon
  missing: boolean
  detail: ReactNode
}

function checksOf(missing: MissingContent): Check[] {
  return [
    {
      key: 'portrait',
      label: 'Creator portrait',
      icon: Sun,
      missing: missing.portrait,
      detail: missing.portrait ? 'Not written yet' : 'In place',
    },
    {
      key: 'powers',
      label: 'Son powers',
      icon: Crown,
      missing: missing.son_powers.length > 0,
      detail: (
        <RecordLinks
          ids={missing.son_powers}
          kind='son'
          linkKind='son'
          fallback='Son'
        />
      ),
    },
    {
      key: 'sky',
      label: 'First sky body',
      icon: Star,
      missing: missing.sky_body,
      detail: missing.sky_body ? 'Not placed yet' : 'In place',
    },
    {
      key: 'peoples',
      label: 'First peoples',
      icon: Users,
      missing: missing.first_people,
      detail: missing.first_people ? 'Not awakened yet' : 'In place',
    },
    {
      key: 'prompts',
      label: 'Image prompts',
      icon: ImagePlus,
      missing: missing.image_prompts > 0,
      detail: count(missing.image_prompts, 'record', 'records'),
    },
    {
      key: 'gods',
      label: 'Foreign gods',
      icon: Ghost,
      missing: missing.undeepened_gods.length > 0,
      detail: (
        <RecordLinks
          ids={missing.undeepened_gods}
          kind='foreign_god'
          linkKind='foreign-god'
          fallback='Foreign god'
        />
      ),
    },
    {
      key: 'names',
      label: 'Pending names',
      icon: Tags,
      missing: missing.pending_names > 0,
      detail: count(missing.pending_names, 'record', 'records'),
    },
    {
      key: 'narratives',
      label: 'Epoch narratives',
      icon: ScrollText,
      missing: missing.past_narratives.length > 0,
      detail: epochList(missing.past_narratives),
    },
  ]
}

function Checklist({ missing }: { missing: MissingContent }) {
  const checks = checksOf(missing)
  const done = checks.filter((check) => !check.missing).length
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='flex min-w-0 flex-col gap-1.5'>
        <div className='flex min-w-0 items-center justify-between gap-2'>
          <Text as='span' weight='semibold'>
            {`${done} of ${checks.length} in place`}
          </Text>
          <Muted as='span' variant='caption'>
            {done === checks.length ? 'Complete' : 'Some parts wait'}
          </Muted>
        </div>
        <Progress
          tone={done === checks.length ? 'success' : 'warning'}
          value={(done / checks.length) * PERCENT}
          aria-label='Completed content'
        />
      </div>
      <ul className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-4'>
        <Paged items={checks} as='li'>
          {(check) => (
            <li
              key={check.key}
              className={cn(
                'flex min-w-0 items-start gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3',
                check.missing ? 'border-warning/40 bg-warning/5' : 'bg-card'
              )}
            >
              <Medallion
                icon={check.icon}
                tone={check.missing ? 'warning' : 'success'}
                size='sm'
              />
              <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
                <div className='flex min-w-0 items-center gap-1.5'>
                  <Text
                    as='span'
                    weight='semibold'
                    truncate
                    className='min-w-0 flex-1'
                  >
                    {check.label}
                  </Text>
                  {check.missing ? (
                    <CircleAlert
                      aria-label='Missing'
                      className='size-icon-sm shrink-0 text-warning'
                    />
                  ) : (
                    <CircleCheck
                      aria-label='In place'
                      className='size-icon-sm shrink-0 text-success'
                    />
                  )}
                </div>
                <Muted as='span' variant='caption'>
                  {check.detail}
                </Muted>
              </div>
            </li>
          )}
        </Paged>
      </ul>
    </div>
  )
}

export function MissingContentPanel() {
  const missing = useMissingContent()
  const run = useRunMaintenanceTask()
  const { reason } = useGodGate()
  const [jobId, setJobId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const start = () => {
    setError(null)
    run.mutate('completion', {
      onSuccess: (accepted) => setJobId(accepted.job_id),
      onError: (failure) => setError(failure.message),
    })
  }
  return (
    <Section
      title='Missing content'
      description='What the completion job would write now. It runs by itself before every epoch and after startup.'
      surface='card'
      level={3}
      icon={ListChecks}
      tone='success'
      actions={
        <ActionButton
          act={run}
          label='Complete now'
          icon={Sparkles}
          size='sm'
          blocked={
            reason({ llm: true }) ??
            (missing.data && !missing.data.anything_missing
              ? 'Nothing is missing.'
              : null)
          }
          pending={run.isPending}
          onRun={start}
        />
      }
    >
      {missing.isPending && <Skeleton className='h-textarea w-full' />}
      {missing.isError && (
        <Text tone='destructive'>{missing.error.message}</Text>
      )}
      {missing.data && <Checklist missing={missing.data} />}
      {error && (
        <Text variant='caption' tone='destructive'>
          {error}
        </Text>
      )}
      {jobId && (
        <JobOutcome
          jobId={jobId}
          title='Complete missing content'
          onDismiss={() => setJobId(null)}
        />
      )}
      {!jobId && missing.data?.anything_missing && (
        <Muted variant='caption'>
          Completion needs the language model; each part is retried on the next
          pass if it fails.
        </Muted>
      )}
    </Section>
  )
}

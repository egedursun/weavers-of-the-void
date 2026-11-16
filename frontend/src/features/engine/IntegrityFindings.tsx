import {
  CircleCheck,
  Hash,
  KeyRound,
  ListChecks,
  Lock,
  type LucideIcon,
  Network,
  Ruler,
  ShieldAlert,
  Users,
  Wrench,
  Clock,
  Coins,
} from 'lucide-react'
import { toast } from 'sonner'
import type { components } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  EmptyState,
  Medallion,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import {
  type IntegrityFinding,
  useIntegrityFindings,
  useResolveFinding,
} from './api'

type Named = { label: string; icon: LucideIcon }

const SHOWN = 6

const CHECKS: Record<components['schemas']['GenericCheck'], Named> = {
  bounded: { label: 'A number out of its range', icon: Ruler },
  enum_values: { label: 'A value outside its list', icon: ListChecks },
  references: { label: 'A reference to a missing row', icon: Network },
  locked_names: {
    label: 'A hold on something that is not a column',
    icon: Lock,
  },
  one_row_per_thing: {
    label: 'More than one profile for a thing',
    icon: Users,
  },
  past_epochs: { label: 'A past moment set in the future', icon: Clock },
  node_id_lists: { label: 'A list naming nodes that are gone', icon: Hash },
  treasury: { label: 'Coin moved outside the purse', icon: Coins },
}

const REMEDIES: Record<components['schemas']['Remedy'], Named> = {
  repair: { label: 'Mended by itself', icon: Wrench },
  report: { label: 'Waits for your word', icon: ShieldAlert },
}

function title(finding: IntegrityFinding): string {
  return finding.check ? CHECKS[finding.check].label : finding.problem
}

function Row({
  finding,
  readOnlyReason,
}: {
  finding: IntegrityFinding
  readOnlyReason: string | null
}) {
  const resolving = useResolveFinding()
  const remedy = REMEDIES[finding.remedy]
  const where = `${finding.table.replaceAll('_', ' ')}${finding.column ? `, ${finding.column.replaceAll('_', ' ')}` : ''}`
  return (
    <li className='flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2 rounded-md border surface-sheen border-gild/60 bg-card p-3'>
      <Medallion
        icon={finding.check ? CHECKS[finding.check].icon : KeyRound}
        tone='warning'
        size='sm'
      />
      <div className='flex min-w-0 flex-1 basis-60 flex-col gap-0.5'>
        <Text weight='medium'>{title(finding)}</Text>
        <Muted variant='caption'>
          {`In ${where} (${finding.key.replaceAll('_', ' ')}): ${finding.problem}. ${remedy.label}; resolving it means it is ${finding.resolution}.`}
        </Muted>
      </div>
      <Button
        variant='outline'
        size='sm'
        disabled={resolving.isPending || readOnlyReason !== null}
        disabledReason={readOnlyReason ?? 'Working'}
        onClick={() =>
          resolving.mutate(finding, {
            onSuccess: () => toast.success('The finding is resolved'),
            onError: (error) => toast.error(error.message),
          })
        }
      >
        <remedy.icon />
        Resolve
      </Button>
    </li>
  )
}

export function IntegrityFindings({
  readOnlyReason,
}: {
  readOnlyReason: string | null
}) {
  const query = useIntegrityFindings()
  const list = useShowMore(query.data?.findings ?? [], SHOWN, SHOWN)
  return (
    <Section
      title='Findings that wait for your word'
      description='Checks that cannot mend a record by themselves list it here, with what resolving it does.'
      surface='card'
      level={3}
      icon={ShieldAlert}
      tone='warning'
    >
      {query.isPending ? (
        <Skeleton className='h-control-lg w-full' />
      ) : query.isError ? (
        <Text tone='destructive'>{query.error.message}</Text>
      ) : query.data.findings.length ? (
        <>
          <ul className='flex min-w-0 flex-col gap-2'>
            {list.visible.map((finding) => (
              <Row
                key={`${finding.check ?? finding.invariant}-${finding.table}-${finding.column}-${finding.key}`}
                finding={finding}
                readOnlyReason={readOnlyReason}
              />
            ))}
          </ul>
          <ShowMore state={list} />
        </>
      ) : (
        <EmptyState
          icon={CircleCheck}
          size='inline'
          title='Every table holds to its rules'
          description='Nothing waits for your word.'
        />
      )}
    </Section>
  )
}

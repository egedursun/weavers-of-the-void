import { type ReactNode } from 'react'
import {
  ChevronDown,
  ScanSearch,
  ShieldCheck,
  TriangleAlert,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Medallion, Paged } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { NamedRecord } from '@/features/entity/NamedRecord'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'

type AuditReport = components['schemas']['ChronicleAuditReport']
type AuditKind = components['schemas']['ChronicleAuditKind']
type Coverage = components['schemas']['ChronicleCoverage']

const KIND_LABEL: Record<AuditKind, string> = {
  rejected_mentioned: 'Names a rejected record',
  son_skipped: 'Skips a son',
  event_skipped: 'Skips an event',
  verdict_skipped: "Skips a Fate's verdict",
  winner_as_loser: 'Shows a winner as the loser',
  active_as_silent: 'Shows an active god as silent',
  deed_miscredited: 'Credits a deed to the wrong god',
  number_contradiction: 'States a wrong number',
}

function CoverageRow({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <li className='flex min-w-0 flex-wrap items-center gap-1.5 rounded-lg border bg-muted/30 px-2 py-1'>
      <Badge size='sm' variant='outline'>
        {label}
      </Badge>
      {children}
    </li>
  )
}

function CoverageList({ coverage }: { coverage: Coverage }) {
  const empty =
    coverage.covered.length === 0 &&
    coverage.entity_ids.length === 0 &&
    coverage.outcomes.length === 0 &&
    coverage.credits.length === 0 &&
    coverage.idle_actor_ids.length === 0 &&
    coverage.counts.length === 0
  return (
    <div className='flex min-w-0 flex-col gap-1.5'>
      <Label>What the chronicle tells</Label>
      {empty ? (
        <Muted variant='caption'>
          The audit found nothing of the fact sheet in the text.
        </Muted>
      ) : (
        <ul className='flex min-w-0 flex-col gap-1'>
          {coverage.covered.length > 0 && (
            <CoverageRow label='Facts told'>
              <Muted variant='caption'>{`${coverage.covered.length} of the epoch's facts`}</Muted>
            </CoverageRow>
          )}
          <Paged
            items={coverage.entity_ids}
            initial={6}
            noun={['record', 'records']}
            as='li'
          >
            {(id) => (
              <CoverageRow key={`named-${id}`} label='Names'>
                <NamedRecord id={id} />
              </CoverageRow>
            )}
          </Paged>
          <Paged
            items={coverage.outcomes}
            initial={6}
            noun={['contest', 'contests']}
            as='li'
          >
            {(claim) => (
              <CoverageRow key={`won-${claim.ref}`} label='Winner'>
                <NamedRecord id={claim.winner_id} />
                <Muted variant='caption'>{`wins ${claim.ref}`}</Muted>
              </CoverageRow>
            )}
          </Paged>
          <Paged
            items={coverage.credits}
            initial={6}
            noun={['credit', 'credits']}
            as='li'
          >
            {(claim) => (
              <CoverageRow
                key={`credit-${claim.entity_id}-${claim.actor_id}`}
                label='Made by'
              >
                <NamedRecord id={claim.entity_id} />
                <Muted variant='caption'>credited to</Muted>
                <NamedRecord id={claim.actor_id} />
              </CoverageRow>
            )}
          </Paged>
          <Paged
            items={coverage.idle_actor_ids}
            initial={6}
            noun={['god', 'gods']}
            as='li'
          >
            {(id) => (
              <CoverageRow key={`idle-${id}`} label='Told as silent'>
                <NamedRecord id={id} />
              </CoverageRow>
            )}
          </Paged>
          <Paged
            items={coverage.counts}
            initial={6}
            noun={['number', 'numbers']}
            as='li'
          >
            {(claim) => (
              <CoverageRow key={`count-${claim.ref}`} label='Number'>
                <Muted variant='caption'>{`${claim.ref}: ${claim.value}`}</Muted>
              </CoverageRow>
            )}
          </Paged>
        </ul>
      )}
    </div>
  )
}

export function ChronicleAudit({
  epoch,
  audit,
}: {
  epoch: number
  audit: AuditReport | null | undefined
}) {
  const { reason } = useGodGate()
  const run = useGodAction({
    run: () =>
      unwrap(api.POST('/api/actions/chronicle:audit', { body: { epoch } })),
    success: 'The chronicle is being audited again',
  })
  const remaining = audit?.remaining ?? []
  const clean = audit !== null && audit !== undefined && remaining.length === 0
  return (
    <Collapsible className='flex min-w-0 flex-col gap-3 rounded-xl border bg-background p-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-3'>
        <Medallion
          icon={!audit ? ScanSearch : clean ? ShieldCheck : TriangleAlert}
          tone={!audit ? 'muted' : clean ? 'success' : 'warning'}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='medium'>
            Chronicle audit
          </Text>
          <Muted variant='caption'>
            {!audit
              ? 'This chronicle has not been checked against the facts.'
              : clean
                ? 'Matches the facts of the epoch.'
                : `${remaining.length} contradictions remain.`}
          </Muted>
        </div>
        {audit && (
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Badge size='sm' variant='outline'>{`${audit.found} found`}</Badge>
            {audit.rewritten && (
              <Badge size='sm' variant='info'>
                Rewritten
              </Badge>
            )}
            {audit.repaired_sentences > 0 && (
              <Badge
                size='sm'
                variant='success'
              >{`${audit.repaired_sentences} sentences repaired`}</Badge>
            )}
          </div>
        )}
        {audit && (
          <CollapsibleTrigger asChild>
            <Button variant='ghost' size='sm'>
              <ChevronDown />
              {remaining.length > 0 ? 'Findings' : 'What it tells'}
            </Button>
          </CollapsibleTrigger>
        )}
        <ActionButton
          label='Audit again'
          icon={ScanSearch}
          size='sm'
          variant='outline'
          blocked={reason({ llm: true })}
          pending={run.isPending}
          onRun={() => run.mutate()}
        />
      </div>
      <CollapsibleContent className='flex min-w-0 flex-col gap-3'>
        <ul className='flex min-w-0 flex-col gap-1.5'>
          {remaining.map((finding, index) => (
            <li
              key={`${finding.kind}-${finding.ref ?? index}`}
              className='flex min-w-0 flex-col gap-1 rounded-lg border bg-muted/30 p-2'
            >
              <div className='flex min-w-0 flex-wrap items-center gap-2'>
                <Badge size='sm' variant='warning'>
                  {KIND_LABEL[finding.kind]}
                </Badge>
                {finding.name && <Label>{finding.name}</Label>}
              </div>
              {(finding.stated || finding.actual) && (
                <Muted variant='caption'>
                  {`Stated ${finding.stated ?? '—'} · actually ${finding.actual ?? '—'}`}
                </Muted>
              )}
              {finding.sentence && (
                <Text variant='caption' italic truncate={3}>
                  {finding.sentence}
                </Text>
              )}
              {finding.detail && (
                <Muted variant='caption'>{finding.detail}</Muted>
              )}
            </li>
          ))}
        </ul>
        {audit?.coverage && <CoverageList coverage={audit.coverage} />}
      </CollapsibleContent>
    </Collapsible>
  )
}

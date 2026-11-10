import { useState } from 'react'
import { format } from 'date-fns'
import {
  CircleCheck,
  Link2Off,
  RefreshCw,
  Sparkles,
  Waypoints,
} from 'lucide-react'
import { toast } from 'sonner'
import { formatDecimal, formatNumber } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ConfirmDialog, EntityLink, JobProgress } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { ruleValue, useRules } from '@/features/map/api'
import {
  useFateLink,
  useFateLinkJob,
  useNetworkHealth,
  useRepairNetwork,
  useStopFateLink,
} from './api'

const FALLBACK = { healthy: 95, proposals: 3, revisit: 10 }
const RECENT_LIMIT = 8

function counted(counters: Record<string, number>): string {
  const total = counters.total ?? 0
  const named = counters.related_converted ?? 0
  if (total === 0 && named === 0) return 'No loose ends to repair.'
  return named > 0
    ? `${formatNumber(total)} loose ends connected, ${formatNumber(named)} vague links named.`
    : `${formatNumber(total)} loose ends connected.`
}

export function NetworkHealthPanel({ intro = false }: { intro?: boolean }) {
  const health = useNetworkHealth()
  const rules = useRules()
  const job = useFateLinkJob()
  const repair = useRepairNetwork()
  const fate = useFateLink()
  const stop = useStopFateLink()
  const [confirmFull, setConfirmFull] = useState(false)
  const healthyPct = ruleValue(
    rules.data,
    'link_graph',
    'main_cluster_healthy_pct',
    FALLBACK.healthy
  )
  const proposals = ruleValue(
    rules.data,
    'link_graph',
    'proposal_cap',
    FALLBACK.proposals
  )
  const revisit = ruleValue(
    rules.data,
    'link_graph',
    'revisit_epochs',
    FALLBACK.revisit
  )
  const running = job.data ?? null

  const runFate = (full: boolean) =>
    fate.mutate(
      { related: true, full, entity_ids: [] },
      {
        onSuccess: () =>
          toast.success(
            full
              ? 'Fate started repairing the whole network; progress in the feed.'
              : 'Fate is looking at the network; the links it creates and their reasons will appear in the feed.'
          ),
        onError: (error) => toast.error(error.message),
      }
    )

  return (
    <div data-network-health className='flex min-w-0 flex-col gap-3'>
      {intro && (
        <Muted>
          The knowledge network grows without forcing. Repairing loose ends only
          creates links the data itself states. Letting Fate propose links adds
          justified links for weakly connected records, names or closes vague
          ones and reviews older reasoned links: a link that rests only on a
          shared theme, or whose reason admits no real tie, is closed, never
          deleted. Both also run at the end of every epoch.
        </Muted>
      )}
      {health.isPending && (
        <div className='flex flex-col gap-2'>
          <Skeleton className='h-6 w-full' />
          <Skeleton className='h-6 w-3/4' />
        </div>
      )}
      {health.error && (
        <Text tone='destructive' variant='caption'>
          {health.error.message}
        </Text>
      )}
      {health.data && (
        <>
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            <Badge variant='outline'>
              {`${formatNumber(health.data.nodes)} nodes · ${formatNumber(health.data.edges)} links (${formatNumber(health.data.active_edges)} active, ${formatNumber(health.data.past_edges)} past)`}
            </Badge>
            <Badge variant='outline'>
              {`avg. ${formatDecimal(health.data.mean_degree, 1)} links (median ${formatDecimal(health.data.median_degree, 1)})`}
            </Badge>
            <Badge
              variant={
                health.data.largest_share_pct >= healthyPct
                  ? 'success'
                  : 'warning'
              }
            >
              {`main cluster ${formatNumber(health.data.largest_component)} nodes (${Math.round(health.data.largest_share_pct)}%) · ${formatNumber(health.data.components)} clusters`}
            </Badge>
            <Badge variant={health.data.isolated > 0 ? 'warning' : 'outline'}>
              {`${formatNumber(health.data.isolated)} isolated`}
            </Badge>
            <Badge variant='outline'>{`${formatNumber(health.data.single_link)} single-link`}</Badge>
            <Badge
              variant={
                health.data.related_undescribed > 0 ? 'warning' : 'outline'
              }
            >
              {`${formatNumber(health.data.related)} related · ${formatNumber(health.data.related_undescribed)} without description`}
            </Badge>
            {health.data.related_to_review > 0 && (
              <Badge variant='warning'>
                {`${formatNumber(health.data.related_to_review)} reasoned links await Fate's review`}
              </Badge>
            )}
          </div>
          {health.data.weakest.length > 0 && (
            <div className='flex min-w-0 flex-wrap items-baseline gap-x-2 gap-y-1'>
              <Label>Weakest</Label>
              {health.data.weakest.map((node) => (
                <span
                  key={node.id}
                  className='inline-flex min-w-0 items-baseline gap-1'
                >
                  {node.kind === 'creator' ? (
                    <EntityLink kind='creator'>{node.name}</EntityLink>
                  ) : node.kind === 'son' ? (
                    <EntityLink kind='son' id={String(node.id)}>
                      {node.name}
                    </EntityLink>
                  ) : node.kind === 'foreign_god' ? (
                    <EntityLink kind='foreign-god' id={String(node.id)}>
                      {node.name}
                    </EntityLink>
                  ) : (
                    <EntityLink kind='entity' id={String(node.id)}>
                      {node.name}
                    </EntityLink>
                  )}
                  <Muted
                    as='span'
                    variant='caption'
                  >{`(${node.degree})`}</Muted>
                </span>
              ))}
            </div>
          )}
          {health.data.priority > 0 && (
            <Text variant='caption'>
              {`${formatNumber(health.data.priority)} events, legends or traditions mentioned in the chronicle with unlinked participants are waiting for Fate.`}
            </Text>
          )}
        </>
      )}
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          size='sm'
          variant='outline'
          disabled={repair.isPending}
          disabledReason='Repairing loose ends…'
          onClick={() =>
            repair.mutate(undefined, {
              onSuccess: (result) => toast.success(counted(result.counters)),
              onError: (error) => toast.error(error.message),
            })
          }
        >
          <CircleCheck />
          Repair loose ends
        </Button>
        {running ? (
          <Button
            size='sm'
            variant='destructive'
            disabled={stop.isPending}
            disabledReason='Fate is finishing its current batch'
            onClick={() =>
              stop.mutate(undefined, {
                onSuccess: () =>
                  toast.success('Fate will finish its current batch and stop.'),
                onError: (error) => toast.error(error.message),
              })
            }
          >
            <Link2Off />
            Stop
          </Button>
        ) : (
          <>
            <Button
              size='sm'
              disabled={fate.isPending}
              disabledReason='Fate is looking at the network…'
              onClick={() => runFate(false)}
            >
              <Sparkles />
              Let Fate propose links
            </Button>
            <Button
              size='sm'
              variant='outline'
              disabled={fate.isPending}
              disabledReason='Fate is looking at the network…'
              onClick={() => setConfirmFull(true)}
            >
              <Waypoints />
              Full repair
            </Button>
          </>
        )}
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Measure again'
          onClick={() => void health.refetch()}
        >
          <RefreshCw />
        </Button>
      </div>
      {running && (
        <JobProgress job={running} title='Fate is looking at the network' />
      )}
      <Muted variant='caption'>
        {`If Fate finds no evidence it creates no link: at most ${proposals} links per record per pass, each with a reason. It will not revisit a record for ${revisit} epochs.`}
      </Muted>
      <div className='flex min-w-0 flex-col gap-1.5'>
        <Label variant='overline'>Recent repairs</Label>
        {health.data && health.data.log.length === 0 && (
          <Muted variant='caption'>
            No repair yet in this session; it happens automatically at the end
            of an epoch.
          </Muted>
        )}
        <ul className='flex min-w-0 flex-col gap-1'>
          {health.data?.log.slice(0, RECENT_LIMIT).map((entry, index) => (
            <li
              key={`${entry.at}-${index}`}
              className='flex min-w-0 items-baseline gap-2'
            >
              <Muted
                as='span'
                variant='caption'
                className='shrink-0 tabular-nums'
              >
                {format(new Date(entry.at), 'HH:mm')}
              </Muted>
              <Text as='span' variant='caption' truncate={2}>
                {entry.text}
              </Text>
            </li>
          ))}
        </ul>
      </div>
      <ConfirmDialog
        open={confirmFull}
        onOpenChange={setConfirmFull}
        title='Repair the whole network?'
        desc='Fate examines every weakly connected record in batches. It may take a while and uses the model; you can stop it after any batch.'
        confirmText='Repair the whole network'
        handleConfirm={() => {
          setConfirmFull(false)
          runFate(true)
        }}
      />
    </div>
  )
}

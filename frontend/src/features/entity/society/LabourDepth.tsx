import { useState } from 'react'
import { Coins, HardHat, Lock, Network, TrendingUp } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { IconStat, Medallion, MiniStat, Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { NodePicker } from '@/features/dominion/parts'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { COMMODITY, WORKSHOP, type CommodityKind } from '../economy/labels'
import { useSocietyDepth } from './depthApi'
import { REASON_SPEC, type SocietyDepth } from './depthLabels'
import { JOB_ORDER, JOB_SPEC, type Job } from './labels'
import {
  AdjustPanel,
  EditorGroup,
  HeldStrip,
  IconPicker,
  NumberEditor,
  Panel,
} from './parts'
import { WORKING } from './tones'

type Reason = SocietyDepth['labour_reasons'][number]

const PERCENT = 100
const DEAR = 130
const CHEAP = 80
const MOST_WORKERS = 1000000000

function priceTone(pct: number) {
  if (pct >= DEAR) return 'danger' as const
  if (pct <= CHEAP) return 'success' as const
  return 'muted' as const
}

function reasonDetail(reason: Reason): string {
  const parts: string[] = []
  if (reason.commodity) {
    const good = COMMODITY[reason.commodity as CommodityKind]
    parts.push(
      `${good?.label ?? reason.commodity} at ${reason.price_pct}% of its usual price`
    )
  }
  if (reason.workshop) parts.push(WORKSHOP[reason.workshop].label)
  return parts.join('; ')
}

function JobReasons({
  job,
  reasons,
  held,
}: {
  job: Job
  reasons: Reason[]
  held: boolean
}) {
  const spec = JOB_SPEC[job]
  const shifts = reasons.filter((reason) => reason.reason !== 'class')
  const base = reasons.find((reason) => reason.reason === 'class')?.workers ?? 0
  const total = base + shifts.reduce((sum, reason) => sum + reason.workers, 0)
  return (
    <div className='flex h-full min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-2.5'>
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion
          icon={spec.icon}
          tone={held ? 'gold' : (spec.tone ?? 'muted')}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='medium' truncate>
            {spec.label}
          </Text>
          <Muted as='span' variant='caption'>
            {`${formatInteger(base)} by custom, ${formatInteger(Math.max(0, total))} at work`}
          </Muted>
        </div>
        {held && (
          <Badge size='sm'>
            <Lock />
            Held
          </Badge>
        )}
      </div>
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        {shifts.length === 0 && (
          <Muted variant='caption'>Nothing pulls workers in or out.</Muted>
        )}
        <Paged items={shifts}>
          {(reason) => {
            const why = REASON_SPEC[reason.reason]
            const detail = reasonDetail(reason)
            return (
              <Tooltip key={reason.reason}>
                <TooltipTrigger asChild>
                  <span tabIndex={0} className='inline-flex min-w-0'>
                    <Badge
                      size='sm'
                      variant={reason.workers >= 0 ? 'success' : 'destructive'}
                    >
                      <why.icon />
                      {`${why.label} ${reason.workers >= 0 ? '+' : ''}${formatInteger(reason.workers)}`}
                    </Badge>
                  </span>
                </TooltipTrigger>
                <TooltipContent>
                  {detail ? `${why.hint}. ${detail}` : why.hint}
                </TooltipContent>
              </Tooltip>
            )
          }}
        </Paged>
      </div>
    </div>
  )
}

function LabourControls({
  view,
  blocked,
}: {
  view: SocietyDepth
  blocked: string | null
}) {
  const [job, setJob] = useState<string>('farming')
  const [share, setShare] = useState(String(view.corvee?.share_pct ?? 20))
  const hold = useGodAction({
    run: ({ target, workers }: { target: Job; workers: number | null }) =>
      unwrap(
        api.POST('/api/actions/labour:set', {
          body: { community_id: view.entity_id, job: target, workers },
        })
      ),
  })
  const [work, setWork] = useState<number | null>(view.corvee?.work_id ?? null)
  const corvee = useGodAction({
    run: (pct: number) =>
      unwrap(
        api.POST('/api/actions/labour:corvee', {
          body: {
            community_id: view.entity_id,
            share_pct: pct,
            polity_id: view.corvee?.polity_id ?? null,
            work_id: pct > 0 ? work : null,
          },
        })
      ),
  })
  const busy = blocked ?? (hold.isPending || corvee.isPending ? WORKING : null)
  const workers = view.labour_reasons
    .filter((reason) => reason.job === job)
    .reduce((sum, reason) => sum + reason.workers, 0)
  const parsed = Number(share)
  const invalid = !Number.isInteger(parsed) || parsed < 1 || parsed > PERCENT
  return (
    <>
      <EditorGroup title='Workers of a trade' icon={Network} pairs>
        <div className='col-span-full'>
          <HeldStrip
            keys={view.held_jobs}
            labelOf={(key) => JOB_SPEC[key as Job].label}
            blocked={busy}
            onRelease={(keys) =>
              keys.forEach((key) =>
                hold.mutate({ target: key as Job, workers: null })
              )
            }
          />
        </div>
        <IconPicker
          label='Trade'
          value={job}
          table={JOB_SPEC}
          blocked={busy}
          onPick={setJob}
        />
        <NumberEditor
          key={`${job}-${workers}`}
          id={`labour-${view.entity_id}`}
          field={{
            key: job,
            label: `Workers at ${JOB_SPEC[job as Job].label.toLowerCase()}`,
            icon: JOB_SPEC[job as Job].icon,
            value: Math.max(0, workers),
            min: 0,
            max: MOST_WORKERS,
          }}
          held={view.held_jobs.includes(job as Job)}
          blocked={blocked}
          pending={hold.isPending}
          onSet={(value) => hold.mutate({ target: job as Job, workers: value })}
        />
      </EditorGroup>
      <EditorGroup title='Corvee' icon={HardHat} pairs>
        <div className='flex min-w-0 flex-col gap-1.5'>
          <FieldLabel htmlFor={`corvee-${view.entity_id}`}>
            Share of the farmhands taken
          </FieldLabel>
          <Input
            id={`corvee-${view.entity_id}`}
            type='number'
            min={1}
            max={PERCENT}
            value={share}
            disabled={busy !== null}
            onChange={(event) => setShare(event.target.value)}
          />
        </div>
        <div className='flex min-w-0 items-end gap-2'>
          <Button
            size='sm'
            className='flex-1'
            disabled={busy !== null || invalid}
            disabledReason={busy ?? 'Give a share from 1 to 100.'}
            onClick={() => corvee.mutate(parsed)}
          >
            <HardHat />
            {view.corvee ? 'Change the corvee' : 'Impose a corvee'}
          </Button>
          {view.corvee && (
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => corvee.mutate(0)}
            >
              Lift it
            </Button>
          )}
        </div>
        <NodePicker
          label='Great work they labour on'
          value={work}
          onChange={setWork}
          blocked={busy}
          types={['structure']}
        />
        <Muted variant='caption'>
          {view.corvee?.work_name
            ? `Labouring on ${view.corvee.work_name} for ${view.corvee.laboured_epochs} epochs; the town will remember it.`
            : 'No great work is named; the farmhands labour on whatever the town raises.'}
        </Muted>
      </EditorGroup>
    </>
  )
}

export function LabourDepth({
  communityId,
  readOnlyReason,
}: {
  communityId: number
  readOnlyReason?: string | null
}) {
  const view = useSocietyDepth(communityId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const data = view.data
  if (!data) return null
  const jobs = JOB_ORDER.filter((job) =>
    data.labour_reasons.some((item) => item.job === job)
  )
  const dear = [...data.prices].sort(
    (left, right) => right.price_pct - left.price_pct
  )
  const moved = data.labour_reasons
    .filter((item) => item.reason !== 'class' && item.workers > 0)
    .reduce((sum, item) => sum + item.workers, 0)
  return (
    <div
      data-surface='LabourReasons'
      className='@container/why flex min-w-0 flex-col gap-4'
    >
      <div className='grid min-w-0 grid-cols-2 gap-2 @xl/why:grid-cols-4'>
        <MiniStat
          icon={TrendingUp}
          label='Moved by prices, works and need'
          value={formatInteger(moved)}
          tone='gold'
        />
        <MiniStat
          icon={HardHat}
          label='Corvee'
          value={data.corvee ? `${data.corvee.share_pct}%` : 'None'}
          tone={data.corvee ? 'warning' : 'muted'}
        />
        {dear[0] && (
          <MiniStat
            icon={COMMODITY[dear[0].commodity as CommodityKind]?.icon ?? Coins}
            label='Dearest good'
            value={`${COMMODITY[dear[0].commodity as CommodityKind]?.label ?? dear[0].commodity} ${dear[0].price_pct}%`}
            tone={priceTone(dear[0].price_pct)}
          />
        )}
        {dear[dear.length - 1] && (
          <MiniStat
            icon={
              COMMODITY[dear[dear.length - 1].commodity as CommodityKind]
                ?.icon ?? Coins
            }
            label='Cheapest good'
            value={`${COMMODITY[dear[dear.length - 1].commodity as CommodityKind]?.label ?? ''} ${dear[dear.length - 1].price_pct}%`}
            tone={priceTone(dear[dear.length - 1].price_pct)}
          />
        )}
      </div>
      <Panel
        title='Why they work where they work'
        icon={Network}
        hint='Class custom, then mines and coasts, workshops, resources, prices, corvee and your holds'
      >
        <div className='grid min-w-0 grid-cols-1 gap-2 @md/why:grid-cols-2 @3xl/why:grid-cols-3'>
          <Paged items={jobs}>
            {(job) => (
              <JobReasons
                key={job}
                job={job}
                reasons={data.labour_reasons.filter((item) => item.job === job)}
                held={data.held_jobs.includes(job)}
              />
            )}
          </Paged>
        </div>
      </Panel>
      <Panel
        title='Prices that pull workers'
        icon={Coins}
        hint='Against each good’s usual price; dear goods draw hands to their trade'
      >
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <Paged items={dear}>
            {(price) => {
              const good = COMMODITY[price.commodity as CommodityKind]
              return (
                <IconStat
                  key={price.commodity}
                  icon={good?.icon ?? Coins}
                  label={good?.label ?? price.commodity}
                  value={`${price.price_pct}%`}
                  tone={priceTone(price.price_pct)}
                  hint={good?.label}
                />
              )
            }}
          </Paged>
        </div>
      </Panel>
      <AdjustPanel
        title='Set the work'
        note='Hold how many work a trade, or lay a corvee on the farmhands for great works (it raises unrest and bitterness). Holds stay until you release them; every change can be undone from the ledger.'
      >
        <LabourControls view={data} blocked={blocked} />
      </AdjustPanel>
    </div>
  )
}

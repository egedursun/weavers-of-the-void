import { Ruler } from 'lucide-react'
import { formatDateTime, formatTokens } from '@/lib/format'
import { agree, plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { RARITY_LABEL, type Rarity } from '@/constants/rarity'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { HeroFrame, Paged, RarityIcon } from '@/components/domain'
import {
  RARITY_BORDER_CLASS,
  RARITY_FRAME_CLASS,
  RARITY_TEXT_CLASS,
} from '@/components/domain/rarityClasses'
import { Label, Muted, SectionTitle, Stat, Text } from '@/components/typography'
import { type UsageReport } from './api'
import { rankOf, type UsageRank } from './usageVisuals'

const PERCENT = 100

function Track({ lit, hidden }: { lit: boolean; hidden: boolean }) {
  return (
    <span
      aria-hidden='true'
      className={cn(
        'hidden h-0.5 min-w-0 flex-1 rounded-full transition-colors duration-500 sm:block',
        hidden ? 'bg-transparent' : lit ? 'bg-primary' : 'bg-border'
      )}
    />
  )
}

function Emblem({
  rarity,
  size,
  dim = false,
}: {
  rarity: Rarity
  size: 'hero' | 'step'
  dim?: boolean
}) {
  return (
    <span
      className={cn(
        'flex shrink-0 items-center justify-center rounded-full border-2 surface-well transition-shadow duration-500',
        size === 'hero' ? 'size-portrait-xl' : 'size-control-lg',
        dim ? 'border-border' : RARITY_BORDER_CLASS[rarity],
        !dim && RARITY_FRAME_CLASS[rarity]
      )}
    >
      <RarityIcon
        rarity={rarity}
        className={cn(
          size === 'hero' ? 'size-portrait-md drop-shadow-md' : 'size-icon-md',
          dim ? 'text-muted-foreground' : RARITY_TEXT_CLASS[rarity]
        )}
      />
    </span>
  )
}

function RankLadder({
  ranks,
  current,
}: {
  ranks: UsageRank[]
  current: number
}) {
  const last = ranks.length - 1
  return (
    <ol
      aria-label='Usage ranks'
      className='grid min-w-0 grid-cols-3 gap-y-3 sm:grid-cols-6'
    >
      <Paged items={ranks} as='li'>
        {(rank, index) => {
          const reached = index <= current
          const here = index === current
          const next = index === current + 1
          return (
            <li
              key={rank.rarity}
              aria-current={here ? 'step' : undefined}
              aria-label={`${RARITY_LABEL[rank.rarity]} from ${formatTokens(rank.floor)} tokens${here ? ', your rank' : reached ? ', reached' : ''}`}
              className='flex min-w-0 flex-col items-center gap-1.5 text-center'
            >
              <span className='flex w-full min-w-0 items-center'>
                <Track lit={index <= current} hidden={index === 0} />
                <span
                  className={cn(
                    'rounded-full',
                    here &&
                      'shadow-lg ring-2 shadow-primary/40 ring-primary ring-offset-2 ring-offset-card'
                  )}
                >
                  <Emblem rarity={rank.rarity} size='step' dim={!reached} />
                </span>
                <Track lit={index < current} hidden={index === last} />
              </span>
              <Text
                as='span'
                variant='caption'
                weight='semibold'
                className={reached ? RARITY_TEXT_CLASS[rank.rarity] : undefined}
                tone={reached ? undefined : 'muted'}
              >
                {RARITY_LABEL[rank.rarity]}
              </Text>
              <Muted as='span' variant='caption'>
                {here ? 'Your rank' : next ? 'Next' : formatTokens(rank.floor)}
              </Muted>
            </li>
          )
        }}
      </Paged>
    </ol>
  )
}

function paceLine(
  report: UsageReport,
  missing: number,
  next: UsageRank | null
): string | null {
  const { pace_tokens: pace, pace_epochs: epochs } = report.lifetime
  if (!next || pace <= 0) return null
  const away = Math.max(1, Math.ceil(missing / pace))
  return `At your recent pace of ${formatTokens(pace)} ${agree(pace, 'token')} an epoch over the last ${plural(epochs, 'epoch', 'epochs')}, ${RARITY_LABEL[next.rarity]} is about ${plural(away, 'epoch', 'epochs')} away.`
}

export function UsageRankHero({ report }: { report: UsageReport }) {
  const { tokens, calls, since, ranks } = report.lifetime
  const rank = rankOf(ranks, tokens)
  const current = ranks.indexOf(rank.current)
  const missing = rank.next ? rank.next.floor - tokens : 0
  const pace = paceLine(report, missing, rank.next)
  return (
    <HeroFrame>
      <div className='flex min-w-0 flex-col items-center gap-4 text-center sm:flex-row sm:items-center sm:text-start'>
        <Emblem rarity={rank.current.rarity} size='hero' />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Label variant='overline'>Lifetime usage rank</Label>
          <SectionTitle
            level={2}
            className={cn('uppercase', RARITY_TEXT_CLASS[rank.current.rarity])}
          >
            {RARITY_LABEL[rank.current.rarity]}
          </SectionTitle>
          <div className='flex min-w-0 flex-wrap items-baseline justify-center gap-x-2 sm:justify-start'>
            <Stat
              value={formatTokens(tokens)}
              size='kpi'
              className='text-gilded font-display'
            />
            <Muted as='span'>
              {`${agree(tokens, 'token')} over ${plural(calls, 'call', 'calls')}${since ? `, counted since ${formatDateTime(since)}` : ''}`}
            </Muted>
          </div>
        </div>
      </div>
      <div className='flex min-w-0 flex-col gap-2 rounded-md border surface-sheen border-gild/40 bg-card p-3'>
        <div className='flex min-w-0 flex-wrap items-baseline justify-between gap-2'>
          <Text as='span' weight='semibold'>
            {rank.next
              ? `Progress to ${RARITY_LABEL[rank.next.rarity]}`
              : 'The highest rank is reached'}
          </Text>
          <Text as='span' variant='caption' className='font-mono'>
            {rank.next
              ? `${formatTokens(tokens)} / ${formatTokens(rank.next.floor)}`
              : formatTokens(tokens)}
          </Text>
        </div>
        <Progress
          value={rank.progress * PERCENT}
          tone={rank.next ? rank.next.rarity : rank.current.rarity}
          aria-label={
            rank.next
              ? `Progress to ${RARITY_LABEL[rank.next.rarity]}`
              : 'Highest rank reached'
          }
        />
        <Muted variant='caption'>
          {rank.next
            ? `${formatTokens(missing)} more ${agree(missing, 'token')} to ${RARITY_LABEL[rank.next.rarity]}.`
            : 'No rank lies beyond this one.'}
        </Muted>
        {pace && <Muted variant='caption'>{pace}</Muted>}
      </div>
      <RankLadder ranks={ranks} current={current} />
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge variant='outline' tabIndex={0}>
              <Ruler />
              {`Counted with ${report.tokenizer}`}
            </Badge>
          </TooltipTrigger>
          <TooltipContent className='max-w-xs'>
            Every call is counted on this server with the same tokenizer,
            whatever model or provider answered it. The counts are close
            estimates, not the provider&apos;s own figures.
          </TooltipContent>
        </Tooltip>
        <Muted as='span' variant='caption'>
          The rank keeps counting when old calls leave the record; the filters
          below do not change it. Its thresholds are world rules under
          Achievements.
        </Muted>
      </div>
    </HeroFrame>
  )
}

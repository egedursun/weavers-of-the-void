import {
  BookOpenText,
  Crown,
  Globe,
  Hourglass,
  type LucideIcon,
  Radio,
  ScrollText,
  Skull,
  Swords,
  Users,
  UsersRound,
  Waypoints,
} from 'lucide-react'
import { formatCompact, formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Label, Text } from '@/components/typography'
import { useLoreTotals, useWorldState } from '@/features/overview/api'
import { useRuleLookup } from '@/features/pantheon/gate'
import { mediaUrl } from '@/features/pantheon/media'
import { SectionHeading } from './aboutParts'

const COVER_WIDTH = 1280
const PERCENT = 100

type CosmosStat = {
  label: string
  value: string
  icon: LucideIcon
}

export function AboutCosmos() {
  const state = useWorldState()
  const totals = useLoreTotals().data
  const rule = useRuleLookup()
  const data = state.data
  const world = data?.world
  if (!data || !world) return null
  const doomLimit = rule('balance.apocalypse_threshold')
  const cover = mediaUrl(data.world_cover, COVER_WIDTH)
  const pulse = data.pulse
  const stats: CosmosStat[] = [
    { label: 'Sons', value: formatInteger(data.sons.length), icon: Crown },
    {
      label: 'Population',
      value: formatCompact(pulse?.population ?? 0),
      icon: Users,
    },
    {
      label: 'Followers',
      value: formatCompact(pulse?.followers ?? 0),
      icon: UsersRound,
    },
    {
      label: 'Worlds',
      value: formatInteger(data.worlds.length),
      icon: Globe,
    },
    {
      label: 'Records woven',
      value: totals ? formatCompact(totals.records) : '-',
      icon: BookOpenText,
    },
    {
      label: 'Threads',
      value: totals ? formatCompact(totals.bonds) : '-',
      icon: Waypoints,
    },
    {
      label: 'Wars waged',
      value: totals ? formatCompact(totals.wars) : '-',
      icon: Swords,
    },
    {
      label: 'Chronicle entries',
      value: totals ? formatCompact(totals.chronicle) : '-',
      icon: ScrollText,
    },
  ]
  return (
    <section aria-labelledby='about-cosmos' className='flex flex-col gap-5'>
      <SectionHeading
        id='about-cosmos'
        icon={Radio}
        eyebrow='Your run so far'
        title='Your Cosmos'
        aside={
          <Badge className='gap-1.5 border-success/50 bg-success/15 text-success'>
            <span className='relative flex size-2'>
              <span className='absolute inline-flex size-full animate-ping rounded-full bg-success opacity-75' />
              <span className='relative inline-flex size-2 rounded-full bg-success' />
            </span>
            Live
          </Badge>
        }
      />
      <div className='relative isolate overflow-hidden rounded-2xl border border-brand-gold/30 shadow-xl shadow-brand-violet/20'>
        {cover && (
          <img
            src={cover}
            alt=''
            aria-hidden
            className='absolute inset-0 -z-10 size-full object-cover opacity-45'
          />
        )}
        <div className='absolute inset-0 -z-10 bg-linear-to-t from-brand-night via-brand-night/85 to-brand-night/30' />
        <div className='flex flex-col gap-6 p-6 sm:p-8'>
          <div className='flex flex-wrap items-end justify-between gap-4'>
            <div className='flex min-w-0 flex-col gap-1'>
              <Label variant='overline' className='text-brand-gold'>
                {data.creator ? `Shaped by ${data.creator.name}` : 'A world'}
              </Label>
              <Text
                as='span'
                weight='semibold'
                className='font-brand text-display text-primary drop-shadow-lg'
              >
                {world.name}
              </Text>
              {data.last_epoch && (
                <Text variant='caption' tone='muted' italic>
                  {`Last age: ${data.last_epoch.name}`}
                </Text>
              )}
            </div>
            <div className='flex flex-col items-center rounded-xl border border-brand-gold/50 bg-brand-gold/10 px-5 py-3 text-brand-gold backdrop-blur-sm'>
              <Hourglass className='size-icon-md' aria-hidden />
              <span className='font-brand text-display'>{world.epoch}</span>
              <Label className='text-brand-gold'>Epoch</Label>
            </div>
          </div>

          <dl className='grid grid-cols-2 gap-2 sm:grid-cols-4'>
            {stats.map(({ label, value, icon: Icon }) => (
              <div
                key={label}
                className='flex items-center gap-3 rounded-lg border border-border/60 bg-background/50 px-3 py-2.5 backdrop-blur-sm'
              >
                <Icon
                  className='size-icon-md shrink-0 text-brand-gold'
                  aria-hidden
                />
                <div className='flex min-w-0 flex-col'>
                  <dd className='font-brand text-title text-foreground'>
                    {value}
                  </dd>
                  <dt>
                    <Label>{label}</Label>
                  </dt>
                </div>
              </div>
            ))}
          </dl>

          {doomLimit ? (
            <div className='flex flex-col gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 backdrop-blur-sm'>
              <div className='flex items-center gap-2'>
                <Skull className='size-icon-sm text-destructive' aria-hidden />
                <Label className='flex-1 text-destructive'>Doom clock</Label>
                <Label className='font-mono text-destructive'>
                  {`${world.doom_clock} / ${doomLimit}`}
                </Label>
              </div>
              <Progress
                value={Math.min(
                  PERCENT,
                  (world.doom_clock / doomLimit) * PERCENT
                )}
                size='sm'
                tone='destructive'
                aria-label={`Doom clock ${world.doom_clock} of ${doomLimit}`}
              />
            </div>
          ) : null}
        </div>
      </div>
    </section>
  )
}

import {
  Brain,
  Brush,
  Heart,
  HandHeart,
  PersonStanding,
  Sparkles,
  Star,
  Orbit,
  TrendingUp,
  CloudFog,
  type LucideIcon,
} from 'lucide-react'
import { formatDecimal } from '@/lib/format'
import { Medallion, MiniStat, Section, StatBar } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { type SonPublic } from '@/features/pantheon/api'
import { STAT_SCALE } from '@/features/pantheon/constants'
import { useRuleLookup } from '@/features/pantheon/gate'
import {
  BAND_LABEL,
  BAND_TONE,
  SON_PASSIONS,
  STATS,
  STAT_GROUPS,
  type StatGroup,
} from '@/features/pantheon/labels'
import { statValue, xpNeeded } from '@/features/pantheon/sonFacts'

const GROUP_ICON: Record<StatGroup, LucideIcon> = {
  Body: PersonStanding,
  Mind: Brain,
  Soul: Brush,
}

export function SonStats({ view, faith }: { view: SonPublic; faith: number }) {
  const son = view.son
  const rule = useRuleLookup()
  const needed = xpNeeded(son.level, rule('core_rules.xp_per_level'))
  return (
    <>
      <Section title='Stats' level={3}>
        <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
          {STAT_GROUPS.map((group) => (
            <div
              key={group}
              className='flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3'
            >
              <div className='flex min-w-0 items-center gap-2'>
                <Medallion icon={GROUP_ICON[group]} size='sm' />
                <Label variant='overline'>{group}</Label>
              </div>
              <ul className='flex min-w-0 flex-col gap-3'>
                {STATS.filter((stat) => stat.group === group).map((stat) => (
                  <li key={stat.key} className='flex min-w-0 flex-col gap-1'>
                    <StatBar
                      label={stat.label}
                      icon={stat.icon}
                      value={statValue(son, stat.key)}
                      max={STAT_SCALE}
                      tone={son.rarity}
                      showMax={false}
                    />
                    <Muted variant='caption' truncate={2}>
                      {stat.effect}
                    </Muted>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Section>
      <Section
        title='Passions'
        description='They shape his actions and his obedience.'
        level={3}
      >
        <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
          {SON_PASSIONS.map((passion) => (
            <StatBar
              key={passion.key}
              label={passion.label}
              icon={passion.icon}
              value={son[passion.key]}
              max={STAT_SCALE}
              tone='warning'
            />
          ))}
        </div>
      </Section>
      <Section title='Resources' level={3}>
        <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
          <StatBar
            label='Life'
            icon={Heart}
            value={son.hp}
            max={view.max_hp}
            tone='destructive'
          />
          <StatBar
            label='Essence'
            icon={Sparkles}
            value={son.essence}
            max={view.max_essence}
          />
          <StatBar label='Fame' icon={Star} value={son.fame} max={STAT_SCALE} />
          {needed !== null && (
            <StatBar
              label='Experience'
              icon={TrendingUp}
              value={son.xp}
              max={needed}
              tone='epic'
            />
          )}
          {son.sanity !== null && (
            <StatBar
              label='Sanity'
              icon={CloudFog}
              value={son.sanity}
              max={STAT_SCALE}
              tone='muted'
            />
          )}
        </div>
        <div className='flex min-w-0'>
          <MiniStat
            icon={HandHeart}
            tone='gold'
            label='Faith'
            value={formatDecimal(faith, 1)}
          />
        </div>
        <div className='flex min-w-0 flex-col gap-1'>
          <StatBar
            label={`Existence · ${BAND_LABEL[view.band]}`}
            icon={Orbit}
            value={son.existence}
            max={STAT_SCALE}
            tone={BAND_TONE[view.band]}
          />
          <Muted variant='caption'>
            Being worshipped, remembered and his anchor living feed existence.
          </Muted>
        </div>
      </Section>
    </>
  )
}

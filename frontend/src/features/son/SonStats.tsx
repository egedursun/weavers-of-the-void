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
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { formatDecimal } from '@/lib/format'
import { Medallion, MiniStat, Section, StatBar } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { type AdjustGroup, AdjustStats } from '@/features/pantheon/AdjustStats'
import { type SonPublic } from '@/features/pantheon/api'
import {
  STARS_MAX,
  STARS_MIN,
  STAT_MIN,
  STAT_SCALE,
} from '@/features/pantheon/constants'
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

type Body = components['schemas']['PatchSonsSonIdBody']

const GROUP_ICON: Record<StatGroup, LucideIcon> = {
  Body: PersonStanding,
  Mind: Brain,
  Soul: Brush,
}

const STAT_KEYS = new Set<string>(STATS.map((stat) => stat.key))
const PASSION_KEYS = new Set<string>(SON_PASSIONS.map((passion) => passion.key))

function editBody(key: string, value: number): Body {
  if (STAT_KEYS.has(key)) return { stats: { [key]: value } }
  if (PASSION_KEYS.has(key)) return { passions: { [key]: value } }
  return { resources: { [key]: value } }
}

function adjustGroups(view: SonPublic): AdjustGroup[] {
  const son = view.son
  return [
    {
      title: 'Stats',
      fields: STATS.map((stat) => ({
        key: stat.key,
        label: stat.label,
        value: statValue(son, stat.key),
        min: STAT_MIN,
        max: STAT_SCALE,
      })),
    },
    {
      title: 'Passions',
      fields: SON_PASSIONS.map((passion) => ({
        key: passion.key,
        label: passion.label,
        value: son[passion.key],
        min: 0,
        max: STAT_SCALE,
      })),
    },
    {
      title: 'Resources',
      fields: [
        { key: 'hp', label: 'Life', value: son.hp, min: 0, max: view.max_hp },
        {
          key: 'essence',
          label: 'Essence',
          value: son.essence,
          min: 0,
          max: view.max_essence,
        },
        { key: 'fame', label: 'Fame', value: son.fame, min: 0 },
        { key: 'xp', label: 'Experience', value: son.xp, min: 0 },
        ...(son.sanity !== null
          ? [
              {
                key: 'sanity',
                label: 'Sanity',
                value: son.sanity,
                min: 0,
                max: STAT_SCALE,
              },
            ]
          : []),
        {
          key: 'existence',
          label: 'Existence',
          value: son.existence,
          min: 0,
          max: STAT_SCALE,
        },
      ],
    },
    {
      title: 'Rank',
      fields: [
        { key: 'level', label: 'Level', value: son.level, min: 1 },
        {
          key: 'stars',
          label: 'Stars',
          value: son.stars,
          min: STARS_MIN,
          max: STARS_MAX,
        },
      ],
    },
  ]
}

export function SonStats({ view, faith }: { view: SonPublic; faith: number }) {
  const son = view.son
  const rule = useRuleLookup()
  const needed = xpNeeded(son.level, rule('core_rules.xp_per_level'))
  return (
    <>
      <Section id='section-son-stats' title='Stats' level={3}>
        <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
          {STAT_GROUPS.map((group) => (
            <div
              key={group}
              className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'
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
        <AdjustStats
          id={`son-${son.id}-stat`}
          groups={adjustGroups(view)}
          note='Life and essence clamp to the new caps; every change goes into the ledger and can be undone.'
          run={({ key, value }) =>
            unwrap(
              api.PATCH('/api/sons/{son_id}', {
                params: { path: { son_id: son.id } },
                body: editBody(key, value),
              })
            )
          }
        />
      </Section>
      <Section
        id='section-son-passions'
        title='Passions'
        description='They shape their actions and their obedience.'
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
      <Section id='section-son-resources' title='Resources' level={3}>
        <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
          <StatBar
            framed
            label='Life'
            icon={Heart}
            value={son.hp}
            max={view.max_hp}
            tone='destructive'
          />
          <StatBar
            framed
            label='Essence'
            icon={Sparkles}
            value={son.essence}
            max={view.max_essence}
          />
          <StatBar
            framed
            label='Fame'
            icon={Star}
            value={son.fame}
            max={STAT_SCALE}
          />
          {needed !== null && (
            <StatBar
              framed
              label='Experience'
              icon={TrendingUp}
              value={son.xp}
              max={needed}
              tone='epic'
            />
          )}
          {son.sanity !== null && (
            <StatBar
              framed
              label='Sanity'
              icon={CloudFog}
              value={son.sanity}
              max={STAT_SCALE}
              tone='muted'
            />
          )}
          <MiniStat
            icon={HandHeart}
            tone='gold'
            label='Faith'
            value={formatDecimal(faith, 1)}
          />
        </div>
        <div className='flex min-w-0 flex-col gap-1'>
          <StatBar
            framed
            label={`Existence · ${BAND_LABEL[view.band]}`}
            icon={Orbit}
            value={son.existence}
            max={STAT_SCALE}
            tone={BAND_TONE[view.band]}
          />
          <Muted variant='caption'>
            Being worshipped, remembered and a living anchor feed existence.
          </Muted>
        </div>
      </Section>
    </>
  )
}

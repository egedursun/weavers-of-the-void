import { useState } from 'react'
import { ChevronDown, Lock, Trophy } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Progress } from '@/components/ui/progress'
import { EmptyState, Medallion, PagedList } from '@/components/domain'
import { Label, Muted, SectionTitle, Stat, Text } from '@/components/typography'
import { CategoryFilter } from './CategoryFilter'
import {
  type AchievementView,
  type GoalCategory,
  type GoalsOverview,
  roman,
} from './api'
import { ACHIEVEMENT_ICON, CATEGORY_TONE } from './goalIcons'

const PERCENT = 100
const SHOWN = 12
const TIER_SLOTS = [0, 1, 2]

function nextTier(item: AchievementView) {
  return item.tiers.find((tier) => tier.epoch === null) ?? null
}

function TierPips({ item }: { item: AchievementView }) {
  return (
    <div
      className='flex min-w-0 flex-wrap items-center gap-1.5'
      aria-label={`Tier ${item.tier} of ${item.tiers.length}`}
    >
      {TIER_SLOTS.map((slot) => {
        const tier = item.tiers.at(slot)
        if (!tier) return null
        return (
          <Badge
            key={tier.tier}
            size='sm'
            variant={tier.epoch !== null ? 'default' : 'outline'}
            title={`${tier.name}: ${tier.description}`}
          >
            {tier.epoch !== null ? <Trophy /> : <Lock />}
            {tier.epoch !== null
              ? `${roman(tier.tier)} · Epoch ${tier.epoch}`
              : `${roman(tier.tier)} · +${tier.points}`}
          </Badge>
        )
      })}
    </div>
  )
}

function AchievementTile({
  item,
  metricLabel,
}: {
  item: AchievementView
  metricLabel: string
}) {
  const upcoming = nextTier(item)
  const complete = upcoming === null
  const begun = item.tier > 0
  const name = begun ? `${item.title} ${roman(item.tier)}` : item.title
  return (
    <li
      data-achievement={item.key}
      data-tier={item.tier}
      className={cn(
        'flex min-w-0 flex-col gap-2.5 rounded-xl border p-3 transition-colors',
        complete && 'border-primary/50 bg-primary/10',
        begun && !complete && 'border-primary/30 bg-primary/5',
        !begun && 'border-dashed bg-background'
      )}
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion
          icon={begun ? ACHIEVEMENT_ICON[item.key] : Lock}
          tone={begun ? CATEGORY_TONE[item.category] : 'muted'}
        />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Text
            as='span'
            weight='semibold'
            tone={begun ? 'inherit' : 'muted'}
            truncate
          >
            {name}
          </Text>
          <Muted variant='caption' truncate={2}>
            {upcoming ? upcoming.description : item.tiers.at(-1)?.description}
          </Muted>
        </div>
      </div>
      <TierPips item={item} />
      <div className='flex min-w-0 flex-col gap-1'>
        <Progress
          size='sm'
          value={item.percent}
          tone={complete ? 'success' : 'default'}
          aria-label={`${item.title} progress`}
        />
        <div className='flex min-w-0 flex-wrap items-center justify-between gap-x-2'>
          <Label truncate>{metricLabel}</Label>
          <Text as='span' variant='caption' weight='medium'>
            {complete
              ? `${formatInteger(item.value)} · every tier earned`
              : `${formatInteger(item.value)} / ${formatInteger(upcoming.threshold)}`}
          </Text>
        </div>
      </div>
    </li>
  )
}

export function AchievementsGrid({
  data,
  defaultOpen = false,
}: {
  data: GoalsOverview
  defaultOpen?: boolean
}) {
  const [category, setCategory] = useState<GoalCategory | null>(null)
  const achievements = data.achievements
  const metricLabels = new Map(
    data.metrics.map((metric) => [metric.metric, metric.label])
  )
  const earnedTiers = achievements.reduce((sum, item) => sum + item.tier, 0)
  const totalTiers = achievements.reduce(
    (sum, item) => sum + item.tiers.length,
    0
  )
  const points = achievements.reduce(
    (sum, item) =>
      sum +
      item.tiers
        .filter((tier) => tier.epoch !== null)
        .reduce((tierSum, tier) => tierSum + tier.points, 0),
    0
  )
  const counts = data.categories.map((entry) => {
    const inside = achievements.filter(
      (item) => item.category === entry.category
    )
    return {
      category: entry.category,
      label: entry.label,
      done: inside.reduce((sum, item) => sum + item.tier, 0),
      total: inside.reduce((sum, item) => sum + item.tiers.length, 0),
    }
  })
  const shown = achievements
    .filter((item) => category === null || item.category === category)
    .sort((first, second) => {
      const firstDone = nextTier(first) === null
      const secondDone = nextTier(second) === null
      if (firstDone !== secondDone) return firstDone ? 1 : -1
      return second.percent - first.percent
    })
  return (
    <Collapsible
      defaultOpen={defaultOpen}
      className='flex min-w-0 flex-col gap-4 rounded-xl border bg-card p-4'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-3'>
        <Medallion icon={Trophy} />
        <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
          <div className='flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1'>
            <SectionTitle>Achievements</SectionTitle>
            <Stat
              value={earnedTiers}
              unit={`of ${plural(totalTiers, 'tier', 'tiers')} · ${plural(points, 'point', 'points')}`}
            />
          </div>
          <Progress
            size='sm'
            value={totalTiers > 0 ? (earnedTiers / totalTiers) * PERCENT : 0}
            aria-label='Achievement tiers earned'
          />
        </div>
        <CollapsibleTrigger asChild>
          <Button variant='outline' size='sm'>
            <ChevronDown />
            {`Achievements · ${earnedTiers}/${totalTiers}`}
          </Button>
        </CollapsibleTrigger>
      </div>
      <CollapsibleContent className='flex min-w-0 flex-col gap-3'>
        <CategoryFilter
          title='Fields of achievement'
          counts={counts}
          value={category}
          onChange={setCategory}
        />
        {shown.length === 0 ? (
          <EmptyState
            icon={Trophy}
            size='compact'
            title='No achievement in this field'
            description='Choose another field to see its achievements.'
          />
        ) : (
          <PagedList
            items={shown}
            initial={SHOWN}
            noun={['achievement', 'achievements']}
            className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3'
            itemKey={(item) => item.key}
          >
            {(item) => (
              <AchievementTile
                item={item}
                metricLabel={metricLabels.get(item.metric) ?? item.title}
              />
            )}
          </PagedList>
        )}
      </CollapsibleContent>
    </Collapsible>
  )
}

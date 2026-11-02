import { ChevronDown, Lock, Trophy } from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Progress } from '@/components/ui/progress'
import { Medallion } from '@/components/domain'
import { Label, Muted, SectionTitle, Stat, Text } from '@/components/typography'
import { ACHIEVEMENT_ICON } from './goalIcons'

type Achievement = components['schemas']['AchievementView']

const PERCENT = 100

function AchievementTile({ item }: { item: Achievement }) {
  return (
    <li
      data-achievement={item.key}
      data-earned={item.earned || undefined}
      className={cn(
        'flex min-w-0 items-start gap-3 rounded-xl border p-3',
        item.earned
          ? 'border-primary/40 bg-primary/5'
          : 'border-dashed bg-background'
      )}
    >
      <Medallion
        icon={item.earned ? ACHIEVEMENT_ICON[item.key] : Lock}
        tone={item.earned ? 'gold' : 'muted'}
      />
      <div className='flex min-w-0 flex-1 flex-col gap-1'>
        <Text
          as='span'
          weight='semibold'
          tone={item.earned ? 'inherit' : 'muted'}
          truncate
        >
          {item.name}
        </Text>
        <Muted variant='caption' truncate={2}>
          {item.description}
        </Muted>
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Badge size='sm' variant={item.earned ? 'default' : 'outline'}>
            <Trophy />
            {`+${item.points}`}
          </Badge>
          {item.earned && item.epoch !== null && (
            <Badge size='sm' variant='success'>{`Epoch ${item.epoch}`}</Badge>
          )}
        </div>
      </div>
    </li>
  )
}

export function AchievementsGrid({
  achievements,
  defaultOpen = false,
}: {
  achievements: Achievement[]
  defaultOpen?: boolean
}) {
  const earned = achievements.filter((item) => item.earned)
  const locked = achievements.filter((item) => !item.earned)
  const sorted = [
    ...earned.sort((first, second) => (second.epoch ?? 0) - (first.epoch ?? 0)),
    ...locked,
  ]
  const points = earned.reduce((sum, item) => sum + item.points, 0)
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
              value={earned.length}
              unit={`/ ${achievements.length} earned · ${points} points`}
            />
          </div>
          <Progress
            size='sm'
            value={
              achievements.length > 0
                ? (earned.length / achievements.length) * PERCENT
                : 0
            }
            aria-label='Achievements earned'
          />
        </div>
        <CollapsibleTrigger asChild>
          <Button variant='outline' size='sm'>
            <ChevronDown />
            {`Achievements · ${earned.length}/${achievements.length}`}
          </Button>
        </CollapsibleTrigger>
      </div>
      <CollapsibleContent className='flex min-w-0 flex-col gap-2'>
        {locked.length > 0 && earned.length > 0 && (
          <Label variant='overline'>{`${earned.length} earned · ${locked.length} still locked`}</Label>
        )}
        <ul className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3'>
          {sorted.map((item) => (
            <AchievementTile key={item.key} item={item} />
          ))}
        </ul>
      </CollapsibleContent>
    </Collapsible>
  )
}

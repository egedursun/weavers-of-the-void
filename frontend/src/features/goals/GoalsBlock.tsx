import { Link } from '@tanstack/react-router'
import { ArrowRight, Target } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Section } from '@/components/domain'
import { Text } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { AchievementsGrid } from './AchievementsGrid'
import { CustomGoalForm } from './CustomGoalForm'
import { GoalBoard } from './GoalBoard'
import { GoalHistory } from './GoalHistory'
import { RunningGoals } from './RunningGoals'
import { ScorePanel } from './ScorePanel'
import { useGoals } from './api'

export function GoalsBlock({
  achievementsOpen = false,
  summary = false,
}: {
  achievementsOpen?: boolean
  summary?: boolean
}) {
  const goals = useGoals()
  const { reason } = useGodGate()
  const evaluate = useGodAction({
    run: () => unwrap(api.POST('/api/actions/goals:evaluate')),
  })
  if (goals.isPending) return <Skeleton className='h-textarea w-full' />
  if (goals.isError)
    return <Text tone='destructive'>{goals.error.message}</Text>
  const data = goals.data
  return (
    <Section
      title='Your goals'
      description='Set yourself goals, earn achievements tier by tier and watch the score; everything is measured at the end of each epoch.'
      actions={
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          {summary && (
            <Button variant='outline' asChild>
              <Link to='/goals'>
                <ArrowRight />
                Goal board
              </Link>
            </Button>
          )}
          <ActionButton
            label='Measure now'
            icon={Target}
            blocked={reason()}
            pending={evaluate.isPending}
            onRun={() => evaluate.mutate()}
          />
        </div>
      }
    >
      <ScorePanel data={data} />
      <RunningGoals data={data} />
      {!summary && <GoalBoard data={data} />}
      {!summary && <CustomGoalForm data={data} />}
      {!summary && <GoalHistory data={data} />}
      <AchievementsGrid data={data} defaultOpen={achievementsOpen} />
    </Section>
  )
}

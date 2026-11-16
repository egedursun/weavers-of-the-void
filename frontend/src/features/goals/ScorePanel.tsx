import { Flag, Medal, Trophy } from 'lucide-react'
import { plural } from '@/lib/units'
import { OrnateFrame } from '@/components/ui/ornate'
import { KpiTile, MiniStat } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { ScoreSparkline } from './ScoreSparkline'
import {
  type GoalsOverview,
  SCORE_PART_LABEL,
  type ScoreComponent,
} from './api'
import { SCORE_PART_ICON, SCORE_PART_TONE } from './goalIcons'

const TIERS_PER_ACHIEVEMENT = 3

function signed(value: number): string {
  return value > 0 ? `+${value}` : String(value)
}

export function ScorePanel({ data }: { data: GoalsOverview }) {
  const parts = Object.entries(data.score.parts ?? {}) as [
    ScoreComponent,
    number,
  ][]
  const total = parts.reduce((sum, [, value]) => sum + value, 0)
  const completed = data.scenarios.reduce(
    (sum, scenario) =>
      sum +
      scenario.history.filter((entry) => entry.status === 'completed').length,
    0
  )
  const tiers = data.achievements.reduce((sum, item) => sum + item.tier, 0)
  const tierTotal = data.achievements.length * TIERS_PER_ACHIEVEMENT
  const previous = data.score_history.at(-2)?.[1]
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3 xl:grid-cols-4'>
        <KpiTile
          label='Score'
          icon={Trophy}
          value={total}
          change={previous === undefined ? undefined : total - previous}
          hint={`Measured at the end of epoch ${data.epoch}`}
        />
        <KpiTile
          label='Achievement tiers'
          icon={Medal}
          tone='verdigris'
          value={`${tiers}/${tierTotal}`}
          meter={{
            value: tiers,
            max: Math.max(1, tierTotal),
            label: 'Achievement tiers earned',
          }}
          hint={plural(
            data.achievements.filter((item) => item.tier > 0).length,
            'achievement begun',
            'achievements begun'
          )}
        />
        <KpiTile
          label='Goals completed'
          icon={Flag}
          tone='success'
          value={completed}
          hint={plural(data.running.length, 'goal running', 'goals running')}
        />
        <OrnateFrame
          frame='tile'
          crest
          tone='gold'
          bayClassName='sm:col-span-3 xl:col-span-1'
          className='flex min-w-0 flex-col gap-2 p-4'
        >
          <Label variant='gilded'>Score over the epochs</Label>
          {data.score_history.length < 2 ? (
            <Muted variant='caption'>
              The score is measured at the end of each epoch.
            </Muted>
          ) : (
            <ScoreSparkline history={data.score_history} />
          )}
        </OrnateFrame>
      </div>
      {parts.length > 0 && (
        <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5'>
          {parts.map(([key, value]) => (
            <MiniStat
              key={key}
              icon={SCORE_PART_ICON[key]}
              tone={value < 0 ? 'danger' : SCORE_PART_TONE[key]}
              label={SCORE_PART_LABEL[key]}
              value={signed(value)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

import { useState } from 'react'
import { SlidersHorizontal } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatDecimal } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { FormRow, Section, StatBar } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { STAT_SCALE } from '@/features/pantheon/constants'
import { useGodGate, useRuleLookup } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  MOOD_BADGE,
  MOOD_EXPLANATION,
  MOOD_LABEL,
} from '@/features/pantheon/labels'
import { type MoodAxis } from './api'
import { GAUGES, MOOD_AXES } from './mood'

type MoodValues = Record<MoodAxis, number>

export function MoodGauges({
  values,
  short = false,
  breakdown = [],
}: {
  values: MoodValues
  short?: boolean
  breakdown?: { axis: MoodAxis; item: string; delta: number; epoch: number }[]
}) {
  const rule = useRuleLookup()
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
      {GAUGES.map((gauge) => {
        const threshold = rule(gauge.rule)
        const value = values[gauge.axis]
        const active =
          threshold !== undefined &&
          (gauge.downward ? value <= threshold : value >= threshold)
        const inputs = breakdown.filter((entry) => entry.axis === gauge.axis)
        return (
          <div
            key={gauge.axis}
            data-mood-active={active || undefined}
            className={cn(
              'flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-3',
              active && 'border-warning/50 bg-warning/5'
            )}
          >
            <StatBar
              label={gauge.label}
              icon={gauge.icon}
              value={value}
              max={STAT_SCALE}
              tone={gauge.tone}
            />
            <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
              {threshold !== undefined && (
                <Label>
                  {gauge.downward
                    ? `Acts at or below ${threshold}`
                    : `Acts at ${threshold}`}
                </Label>
              )}
              {active && (
                <Badge size='sm' variant='warning'>
                  Active
                </Badge>
              )}
            </div>
            {!short && <Muted variant='caption'>{gauge.effect}</Muted>}
            {!short && inputs.length > 0 && (
              <Muted variant='caption' truncate={3}>
                {`Last epoch: ${inputs
                  .map(
                    (entry) =>
                      `${entry.item} ${entry.delta >= 0 ? '+' : ''}${formatDecimal(entry.delta, 1)}`
                  )
                  .join(' · ')}`}
              </Muted>
            )}
          </div>
        )
      })}
    </div>
  )
}

export function MoodSetForm({ values }: { values: MoodValues }) {
  const [draft, setDraft] = useState<MoodValues>(values)
  const { reason } = useGodGate()
  const action = useGodAction({
    run: (body: MoodValues) => unwrap(api.PUT('/api/creator/mood', { body })),
    success: "The Creator's mood changed",
  })
  return (
    <Collapsible className='flex min-w-0 flex-col gap-3'>
      <CollapsibleTrigger asChild>
        <Button variant='ghost' size='sm' className='self-start'>
          <SlidersHorizontal />
          Set the mood yourself
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='flex min-w-0 flex-col gap-3'>
        {GAUGES.map((gauge) => (
          <FormRow key={gauge.axis} label={gauge.label}>
            {(id) => (
              <Input
                id={id}
                type='number'
                min={0}
                max={STAT_SCALE}
                value={draft[gauge.axis]}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    [gauge.axis]: Number(event.target.value),
                  })
                }
              />
            )}
          </FormRow>
        ))}
        <Muted variant='caption'>
          These become this epoch's starting point; the mood drifts on from
          there.
        </Muted>
        <div>
          <ActionButton
            label='Set the mood'
            variant='default'
            blocked={reason()}
            pending={action.isPending}
            onRun={() => action.mutate(draft)}
          />
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

type MoodPanelProps = {
  label: keyof typeof MOOD_LABEL
  values: MoodValues
  breakdown: { axis: MoodAxis; item: string; delta: number; epoch: number }[]
}

export function MoodPanel({ label, values, breakdown }: MoodPanelProps) {
  return (
    <Section
      title='Mood'
      description='Changes at each epoch end by faith, prayers and silence in the world.'
      surface='card'
      level={3}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Badge variant={MOOD_BADGE[label]}>{MOOD_LABEL[label]}</Badge>
        <Text variant='caption'>{MOOD_EXPLANATION[label]}</Text>
      </div>
      <MoodGauges values={values} breakdown={breakdown} />
      <MoodSetForm
        key={MOOD_AXES.map((axis) => values[axis]).join(':')}
        values={values}
      />
    </Section>
  )
}

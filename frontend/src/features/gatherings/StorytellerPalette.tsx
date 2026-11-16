import { useState } from 'react'
import { Scale, Unlock } from 'lucide-react'
import { ShowMore, useShowMore } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { Chip, ForgeCard, Meter } from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { useMadeAction } from '@/features/minds/api'
import { DIRECTIONS, PALETTE_SUBSYSTEMS } from '@/features/typedModels/labels'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import { type StorytellerView } from './api'

const SHOWN = 6
const WEIGHT_MAX = 1000
const PERCENT = 100

function words(key: string) {
  return key.replaceAll('_', ' ')
}

export function StorytellerPalette({
  view,
  blocked,
}: {
  view: StorytellerView
  blocked: string | null
}) {
  const rows = useShowMore(view.palette, SHOWN, SHOWN)
  const [key, setKey] = useState<string>(view.palette.at(0)?.key ?? '')
  const [weight, setWeight] = useState(String(PERCENT))
  const weighing = useMadeAction(
    'storyteller:palette',
    (_: void) => ({
      world_id: view.world_id,
      key,
      weight_pct: Math.min(WEIGHT_MAX, Math.max(0, Number(weight) || 0)),
    }),
    'The storyteller weighs it so'
  )
  const releasing = useMadeAction(
    'storyteller:palette',
    (_: void) => ({
      world_id: view.world_id,
      key: key || (view.palette.at(0)?.key ?? ''),
      release: true,
    }),
    'The storyteller weighs its palette again'
  )
  const held = view.locked.includes('palette')
  const choices = Object.fromEntries(
    view.palette.map((row) => [
      row.key,
      {
        label: words(row.key),
        icon: PALETTE_SUBSYSTEMS[row.subsystem].icon,
        tone: DIRECTIONS[row.direction].tone,
      },
    ])
  )
  const empty = view.palette.length
    ? null
    : 'No event in the palette has its causes in this world yet'
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>Events whose causes hold here</Label>
      <Muted variant='caption'>
        The storyteller only changes the chances of events whose causes already
        hold in this world. Subsystems that have not acted lately weigh more; a
        quiet world leans toward disruptions and a heated one toward recoveries.
      </Muted>
      {view.palette.length ? (
        <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
          {rows.visible.map((row) => (
            <Meter
              key={row.key}
              label={`${words(row.key)} · ${PALETTE_SUBSYSTEMS[row.subsystem].label} · ${DIRECTIONS[row.direction].label}`}
              icon={PALETTE_SUBSYSTEMS[row.subsystem].icon}
              value={row.weight_pct}
              max={Math.max(row.weight_pct, PERCENT * 2)}
              tone={row.direction === 'recovery' ? 'success' : 'warning'}
            />
          ))}
        </div>
      ) : (
        <Chip icon={Scale}>{empty}</Chip>
      )}
      <ShowMore state={rows} />
      <ForgeCard
        icon={Scale}
        tone='info'
        title='Weigh an event'
        note={
          held
            ? 'You hold the palette; the storyteller keeps your weights until you release it.'
            : 'A weight you set holds the palette against the storyteller.'
        }
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <StepButton
              icon={Scale}
              label='Weigh it'
              variant='default'
              busy={why(blocked ?? empty, weighing.isPending)}
              onClick={() => weighing.mutate()}
            />
            <StepButton
              icon={Unlock}
              label='Release the palette'
              busy={why(
                blocked ?? (held ? null : 'The palette is not held'),
                releasing.isPending
              )}
              onClick={() => releasing.mutate()}
            />
          </div>
        }
      >
        <ChoiceField
          label='Event'
          value={key}
          table={choices}
          blocked={blocked ?? empty}
          onPick={setKey}
        />
        <NumberField
          label='Weight (%)'
          value={weight}
          min={0}
          max={WEIGHT_MAX}
          onChange={setWeight}
        />
      </ForgeCard>
    </div>
  )
}

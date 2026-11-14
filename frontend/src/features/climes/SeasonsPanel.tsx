import { useState } from 'react'
import { CloudRain, Plus, Waves } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { why } from '@/features/dominion/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/wilds/parts'
import { Bars } from '@/features/sacred/parts'
import { type ClimesNodeView, useClimesAction } from './api'
import { PHASES } from './labels'
import { DOUBLE_SPAN, SPAN, SYNODIC_MAX, useClimesRow } from './model'

type View = ClimesNodeView
type Season = View['monsoons'][number]
type Swing = NonNullable<View['oscillation']>

function SeasonCard({
  row,
  worldId,
  blocked,
}: {
  row: Season
  worldId: number
  blocked: string | null
}) {
  const action = useClimesRow(
    'monsoon_season:edit',
    'monsoon_season:delete',
    { world_id: worldId, epoch: row.epoch },
    blocked
  )
  return (
    <Held
      icon={CloudRain}
      tone={row.failed ? 'danger' : row.strength > SPAN ? 'success' : 'info'}
      title={`The monsoon of epoch ${row.epoch}`}
      caption={`${row.strength}% of its usual strength${row.failed ? ' · failed' : ''}`}
      removeLabel='Forget this monsoon'
      editTitle='Set the monsoon'
      note='The monsoon brings rain to its coasts in proportion to its strength. A failed one is a hungry year for the towns of its coasts and makes their sea roads more dangerous; a strong one eases them.'
      fields={[
        {
          key: 'strength',
          label: 'Strength (% of the usual)',
          kind: 'number',
          min: 0,
          max: DOUBLE_SPAN,
        },
        { key: 'failed', label: 'Failed', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Strength (${row.strength} of ${DOUBLE_SPAN})`}
        value={row.strength}
        max={DOUBLE_SPAN}
        tone={row.failed ? 'destructive' : 'success'}
        icon={CloudRain}
      />
    </Held>
  )
}

function SwingCard({
  row,
  worldId,
  blocked,
}: {
  row: Swing
  worldId: number
  blocked: string | null
}) {
  const action = useClimesRow(
    'climate_oscillation:edit',
    'climate_oscillation:delete',
    { world_id: worldId },
    blocked
  )
  const phase = PHASES[row.phase]
  return (
    <Held
      icon={phase.icon}
      tone={phase.tone}
      title={`Climate swing: ${phase.label.toLowerCase()}`}
      caption={`Epoch ${row.step + 1} of a ${row.period}-epoch cycle · shifts rain and heat by up to ${row.strength}`}
      removeLabel='End the swing'
      editTitle='Set the swing'
      note='The seas swing through a warm third, a neutral third and a cold third of the cycle. A warm swing dries the warm coasts and wets the land behind them, a cold one the reverse, and seers of a people that reads the sky foresee more surely while it runs.'
      fields={[
        { key: 'phase', label: 'Phase', kind: 'pick', table: table(PHASES) },
        {
          key: 'period',
          label: 'Epochs in a cycle',
          kind: 'number',
          min: 2,
          max: SYNODIC_MAX,
        },
        {
          key: 'step',
          label: 'Epoch of the cycle',
          kind: 'number',
          min: 0,
          max: SYNODIC_MAX,
        },
        {
          key: 'strength',
          label: 'Shift of rain and heat',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          ['Phase', phase.label],
          ['Cycle', `${row.period} epochs`],
        ]}
      />
      <Meter
        label={`Through the cycle (${row.step + 1} of ${row.period})`}
        value={row.step + 1}
        max={Math.max(1, row.period)}
        tone='info'
        icon={Waves}
      />
    </Held>
  )
}

export function SeasonsPanel({
  data,
  blocked,
}: {
  data: View
  blocked: string | null
}) {
  const worldId = data.world?.id ?? null
  const [strength, setStrength] = useState(SPAN)
  const [phase, setPhase] = useState('warm')
  const stirring = useClimesAction(
    'monsoon_season:set',
    (_: void) => ({
      world_id: worldId ?? 0,
      epoch: data.epoch,
      strength,
      failed: strength < SPAN / 2,
    }),
    'The monsoon is set'
  )
  const swinging = useClimesAction(
    'climate_oscillation:set',
    (_: void) => ({
      world_id: worldId ?? 0,
      phase: phase as Swing['phase'],
    }),
    'The seas begin to swing'
  )
  const noWorld =
    worldId === null ? 'Only a thing on a world has seasons' : null
  const stirBusy = why(blocked ?? noWorld, stirring.isPending)
  const swingBusy = why(
    blocked ??
      noWorld ??
      (data.oscillation ? 'The world swings already; adjust it above' : null),
    swinging.isPending
  )
  return (
    <div data-surface='SeasonsPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-monsoons'
        title='Monsoons by year'
        legend={[
          { text: 'Came', variant: 'success' },
          { text: 'Failed', variant: 'destructive' },
        ]}
        rows={data.monsoons.map((row) => ({
          key: String(row.epoch),
          caption: `Epoch ${row.epoch}: ${row.strength}%${row.failed ? ', failed' : ''}`,
          segments: [
            {
              value: Math.min(DOUBLE_SPAN, row.strength),
              fill: row.failed ? 'fill-destructive' : 'fill-success',
            },
          ],
        }))}
        max={DOUBLE_SPAN}
        noun={['monsoon', 'monsoons']}
        empty='No monsoon has come to this world yet.'
      />
      <Listed
        title='Monsoons'
        items={data.monsoons}
        empty='No monsoon has come to this world yet.'
        noun={['monsoon', 'monsoons']}
        itemKey={(item) => item.epoch}
      >
        {(item) =>
          worldId !== null && (
            <SeasonCard row={item} worldId={worldId} blocked={blocked} />
          )
        }
      </Listed>
      <Bars
        chart='chart-oscillation'
        title='The swing of the seas'
        legend={[{ text: 'Through the cycle', variant: 'secondary' }]}
        rows={
          data.oscillation
            ? [
                {
                  key: 'swing',
                  caption: `${PHASES[data.oscillation.phase].label}: epoch ${data.oscillation.step + 1} of ${data.oscillation.period}`,
                  segments: [
                    {
                      value: data.oscillation.step + 1,
                      fill: 'fill-info',
                    },
                  ],
                },
              ]
            : []
        }
        max={data.oscillation?.period ?? 1}
        noun={['swing', 'swings']}
        empty='The seas of this world do not swing.'
      />
      {data.oscillation && worldId !== null && (
        <SwingCard row={data.oscillation} worldId={worldId} blocked={blocked} />
      )}
      <ForgeCard
        icon={CloudRain}
        tone='info'
        title={`Set the monsoon of epoch ${data.epoch}`}
        note='Below half its usual strength the monsoon fails; above its usual strength it is a strong year.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={stirBusy !== null}
            disabledReason={stirBusy ?? undefined}
            onClick={() => stirring.mutate()}
          >
            <Plus />
            Set the monsoon
          </Button>
        }
      >
        <NumberField
          label='Strength (% of the usual)'
          value={String(strength)}
          min={0}
          max={DOUBLE_SPAN}
          disabled={blocked !== null}
          onChange={(text) =>
            setStrength(Math.max(0, Math.min(DOUBLE_SPAN, Number(text) || 0)))
          }
        />
      </ForgeCard>
      <ForgeCard
        icon={Waves}
        tone='verdigris'
        title='Begin a climate swing'
        note='Let the seas of this world swing between warm and cold years.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={swingBusy !== null}
            disabledReason={swingBusy ?? undefined}
            onClick={() => swinging.mutate()}
          >
            <Plus />
            Begin it
          </Button>
        }
      >
        <MindPicker
          label='Starting phase'
          value={phase}
          table={table(PHASES)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setPhase}
        />
      </ForgeCard>
    </div>
  )
}

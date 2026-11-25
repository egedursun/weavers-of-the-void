import { useState } from 'react'
import { ArrowDown, Plus, Wind } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { Bars } from '@/features/sacred/parts'
import { type ClimesNodeView, useClimesAction } from './api'
import {
  BANDS,
  COMPASS_ICON,
  DIRECTIONS,
  DIRECTION_TABLE,
  ROTATIONS,
  SHADOW_ICON,
} from './labels'
import {
  OCTANT_MAX,
  REGION_TYPES,
  SPAN,
  useClimesRow,
  useClimesStep,
} from './model'

type View = ClimesNodeView
type Wind = View['winds'][number]

function Arrow({ from, label }: { from: number; label: string }) {
  return (
    <span
      role='img'
      aria-label={label}
      className='flex size-control-sm shrink-0 items-center justify-center rounded-full border surface-well border-gild/45 bg-muted/70'
    >
      <ArrowDown
        className={cn(
          'size-icon-sm transition-transform motion-reduce:transition-none',
          ROTATIONS[from]
        )}
      />
    </span>
  )
}

function WindCard({ row, blocked }: { row: Wind; blocked: string | null }) {
  const action = useClimesRow(
    'region_wind:edit',
    'region_wind:delete',
    { region_id: row.region.id },
    blocked
  )
  const band = BANDS[row.band]
  const from = DIRECTIONS[row.wind_from].toLowerCase()
  const marks = [
    row.windward ? 'windward' : null,
    row.shadow > 0 ? `rain shadow ${row.shadow}` : null,
    row.monsoon > 0 ? `monsoon ${row.monsoon}` : null,
    row.upwelling ? 'cold water rises' : null,
  ].filter((item): item is string => item !== null)
  return (
    <Held
      icon={band.icon}
      tone={band.tone}
      title={`${band.label} over ${row.region.name}`}
      caption={`From the ${from} · strength ${row.strength} · in summer ${BANDS[row.summer_band].label.toLowerCase()} · read in epoch ${row.read_epoch}`}
      removeLabel='Still the wind'
      editTitle='Set the wind'
      note='The band and its direction come from the turning and light of the world; highlands upwind cast a rain shadow, moist sea wind rains on windward highlands, and the wind carries foul air, ships and fire. A held field keeps the value you give it.'
      fields={[
        {
          key: 'band',
          label: 'Band of winds',
          kind: 'pick',
          table: table(BANDS),
        },
        {
          key: 'summer_band',
          label: 'Band in the warm half of the year',
          kind: 'pick',
          table: table(BANDS),
        },
        {
          key: 'wind_from',
          label: 'Blows from',
          kind: 'pick',
          table: DIRECTION_TABLE,
        },
        {
          key: 'strength',
          label: 'Strength',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'windward', label: 'Windward', kind: 'pick', table: YES_NO },
        {
          key: 'shadow',
          label: 'Rain lost in the shadow',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'monsoon',
          label: 'Monsoon strength',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'upwelling',
          label: 'Cold water rises',
          kind: 'pick',
          table: YES_NO,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <>
          <Arrow from={row.wind_from} label={`Blows from the ${from}`} />
          {marks.map((mark) => (
            <Badge key={mark} size='sm' variant='secondary'>
              {mark}
            </Badge>
          ))}
        </>
      }
    >
      <Facts
        items={[
          ['Band', band.label],
          ['Blows from', DIRECTIONS[row.wind_from]],
          ['Windward', row.windward ? 'Yes' : 'No'],
        ]}
      />
      <Meter
        label={`Strength (${row.strength} of ${SPAN})`}
        value={row.strength}
        tone='info'
        icon={Wind}
      />
      <Meter
        label={`Rain lost in the shadow (${row.shadow} of ${SPAN})`}
        value={row.shadow}
        tone='warning'
        icon={SHADOW_ICON}
      />
    </Held>
  )
}

export function WindsPanel({
  data,
  blocked,
}: {
  data: View
  blocked: string | null
}) {
  const [land, setLand] = useState<number | null>(data.region?.id ?? null)
  const [band, setBand] = useState('trade')
  const [summer, setSummer] = useState('trade')
  const [from, setFrom] = useState('2')
  const setting = useClimesAction(
    'region_wind:set',
    (_: void) => ({
      region_id: land ?? 0,
      band: band as Wind['band'],
      summer_band: summer as Wind['summer_band'],
      wind_from: Math.min(OCTANT_MAX, Number(from)),
    }),
    'The wind turns'
  )
  const reading = useClimesStep('climes:run', blocked, 'The winds are read')
  const setBusy = why(
    blocked ?? (land === null ? 'Choose the land the wind blows over' : null),
    setting.isPending
  )
  return (
    <div data-surface='WindsPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-winds'
        title='Winds and their rain shadows'
        legend={[
          { text: 'Strength', variant: 'secondary' },
          { text: 'Rain shadow', variant: 'warning' },
        ]}
        rows={data.winds.map((row) => ({
          key: String(row.region.id),
          caption: `${row.region.name}: ${BANDS[row.band].label.toLowerCase()} from the ${DIRECTIONS[row.wind_from].toLowerCase()}, strength ${row.strength}, shadow ${row.shadow}`,
          segments: [
            { value: Math.min(SPAN, row.strength), fill: 'fill-info' },
            { value: Math.min(SPAN, row.shadow), fill: 'fill-warning' },
          ],
        }))}
        max={SPAN * 2}
        noun={['wind', 'winds']}
        empty='No wind has been read over this yet.'
      />
      <Listed
        title='Prevailing winds'
        items={data.winds}
        empty='No wind has been read over this yet.'
        noun={['wind', 'winds']}
        itemKey={(item) => item.region.id}
      >
        {(item) => <WindCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={COMPASS_ICON}
        tone='info'
        title='Turn a wind'
        note='Set the band and direction of the prevailing wind over a land; rain, ships, fire and foul air follow it.'
        columns={3}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <StepButton
              icon={Wind}
              label='Read the winds now'
              busy={reading.busy}
              onClick={reading.run}
            />
            <Button
              act={setting}
              size='sm'
              disabled={setBusy !== null}
              disabledReason={setBusy ?? undefined}
              onClick={() => setting.mutate()}
            >
              <Plus />
              Set the wind
            </Button>
          </div>
        }
      >
        <NodePicker
          label='Land'
          value={land}
          onChange={setLand}
          blocked={blocked}
          types={REGION_TYPES}
        />
        <MindPicker
          label='Band of winds'
          value={band}
          table={table(BANDS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setBand}
        />
        <MindPicker
          label='Band in summer'
          value={summer}
          table={table(BANDS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setSummer}
        />
        <MindPicker
          label='Blows from'
          value={from}
          table={DIRECTION_TABLE}
          placeholder='Choose'
          blocked={blocked}
          onPick={setFrom}
        />
      </ForgeCard>
    </div>
  )
}

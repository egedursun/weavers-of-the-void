import { useState } from 'react'
import { Activity, Crosshair, Gauge, Sparkles, Target } from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { Button } from '@/components/ui/button'
import { EmptyState, KpiTile, LoadingBlock, Section } from '@/components/domain'
import { LineChart } from '@/components/domain/LineChart'
import { ChoiceTiles } from '@/components/domain/SettingsKit'
import { Label, Muted } from '@/components/typography'
import { Chip, Facts, Meter, RecordEditor } from '@/features/cosmography/parts'
import { StorytellerDepth } from './StorytellerDepth'
import { StorytellerPalette } from './StorytellerPalette'
import { type StorytellerView, useGatheringAction, useStoryteller } from './api'
import { why } from './history'
import {
  SPONTANEOUS_KINDS,
  STORYTELLER_PROFILES,
  TENSION_BANDS,
  table,
} from './labels'
import { Ref, ThingPicker } from './parts'

const SPAN = 100

type Order = {
  profile?: StorytellerView['profile']
  values: EditValues
  release: string[]
}

function Spotlight({
  view,
  busy,
  onSet,
}: {
  view: StorytellerView
  busy: string | null
  onSet: (order: Order) => void
}) {
  const [node, setNode] = useState<number | null>(null)
  return (
    <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
      <ThingPicker
        label='Put in the spotlight'
        value={node}
        onChange={setNode}
        blocked={busy}
      />
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null || node === null}
        disabledReason={
          busy ??
          (node === null
            ? 'Choose who stands in the spotlight first'
            : undefined)
        }
        onClick={() => {
          onSet({ values: { spotlight_entity_id: node }, release: [] })
          setNode(null)
        }}
      >
        <Crosshair />
        {view.spotlight ? 'Move the spotlight' : 'Set the spotlight'}
      </Button>
    </div>
  )
}

export function StorytellerSection({
  worldId,
  readOnlyReason = null,
}: {
  worldId: number
  readOnlyReason?: string | null
}) {
  const query = useStoryteller(worldId)
  const set = useGatheringAction(
    'storyteller:set',
    (order: Order) => ({
      world_id: worldId,
      profile: order.profile ?? null,
      values: order.values,
      release: order.release,
    }),
    'The storyteller is set'
  )
  const busy = why(readOnlyReason, set.isPending)
  const view = query.data
  return (
    <Section
      id='section-storyteller'
      title='Storyteller'
      description='The tension of this world against its aim, and how it paces beasts, raids, plagues, comets, claimants and the years of recovery that follow. Only a world has a storyteller: it paces everything on that world at once.'
      icon={Activity}
      tone='warning'
    >
      <div
        data-surface='StorytellerSection'
        className='flex min-w-0 flex-col gap-3'
      >
        {query.isPending ? (
          <LoadingBlock label='Listening to the storyteller' />
        ) : query.isError ? (
          <EmptyState
            icon={Activity}
            size='inline'
            title='The storyteller could not be read'
            description={query.error.message}
          />
        ) : view ? (
          <>
            <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
              <KpiTile
                label='Tension'
                value={view.tension}
                icon={Gauge}
                tone={TENSION_BANDS[view.band].tone}
                meter={{ value: view.tension, max: SPAN, label: 'Tension' }}
              />
              <KpiTile
                label='Aim'
                value={view.target}
                icon={Target}
                tone='info'
                meter={{ value: view.target, max: SPAN, label: 'Aim' }}
              />
              <KpiTile
                label='Pace of events'
                value={`${view.boost_pct > 0 ? '+' : ''}${view.boost_pct}%`}
                icon={Sparkles}
                tone={view.boost_pct >= 0 ? 'warning' : 'success'}
              />
              <KpiTile
                label='Mood'
                value={TENSION_BANDS[view.band].label}
                icon={TENSION_BANDS[view.band].icon}
                tone={TENSION_BANDS[view.band].tone}
              />
            </div>
            <Facts
              items={[
                ['Storyteller', STORYTELLER_PROFILES[view.profile].label],
                ['Cycle offset', String(view.cycle_offset)],
                [
                  'In the spotlight',
                  <Ref key='spotlight' node={view.spotlight} />,
                ],
                [
                  'Last weighed',
                  view.updated_epoch === 0
                    ? 'Not yet'
                    : `Epoch ${view.updated_epoch}`,
                ],
              ]}
            />
            {view.curve.length > 1 ? (
              <LineChart
                title='Tension over the epochs'
                xLabel={(epoch) => `E${epoch}`}
                tooltipLabel={(epoch) => `Epoch ${epoch}`}
                max={SPAN}
                series={[
                  {
                    key: 'tension',
                    label: 'Tension',
                    color: 'var(--color-warning)',
                    points: view.curve.map((point) => ({
                      x: point.epoch,
                      y: point.tension,
                    })),
                  },
                  {
                    key: 'target',
                    label: 'Aim',
                    color: 'var(--color-info)',
                    points: view.curve.map((point) => ({
                      x: point.epoch,
                      y: point.target,
                    })),
                  },
                ]}
              />
            ) : (
              <Muted variant='caption'>
                The curve draws itself once two epochs have been weighed.
              </Muted>
            )}
            {view.curve.length > 0 && (
              <div className='flex min-w-0 flex-wrap gap-1.5'>
                {view.curve.slice(-6).map((point) => {
                  const band = TENSION_BANDS[point.band]
                  return (
                    <Chip
                      key={point.epoch}
                      icon={band.icon}
                    >{`E${point.epoch} ${band.label}`}</Chip>
                  )
                })}
              </div>
            )}
            <div className='flex min-w-0 flex-col gap-2'>
              <Label variant='overline'>What struck of late</Label>
              {Object.keys(view.recent_kinds).length === 0 ? (
                <Muted variant='caption'>
                  Nothing has struck of late, so every kind of event is fresh.
                </Muted>
              ) : (
                <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
                  {(
                    Object.entries(view.recent_kinds) as [
                      keyof typeof SPONTANEOUS_KINDS,
                      number,
                    ][]
                  ).map(([kind, count]) => (
                    <Meter
                      key={kind}
                      label={SPONTANEOUS_KINDS[kind].label}
                      icon={SPONTANEOUS_KINDS[kind].icon}
                      value={count}
                      max={Math.max(count, 5)}
                      tone='warning'
                    />
                  ))}
                </div>
              )}
            </div>
            <StorytellerPalette view={view} blocked={busy} />
            <Label variant='overline'>Choose the storyteller</Label>
            <ChoiceTiles
              label='Storyteller'
              value={view.profile}
              columns={4}
              blocked={busy}
              options={(
                Object.keys(
                  STORYTELLER_PROFILES
                ) as StorytellerView['profile'][]
              ).map((key) => ({
                value: key,
                label: STORYTELLER_PROFILES[key].label,
                hint: STORYTELLER_PROFILES[key].hint,
                icon: STORYTELLER_PROFILES[key].icon,
              }))}
              onChange={(profile) => {
                if (profile !== view.profile)
                  set.mutate({ profile, values: {}, release: [] })
              }}
            />
            <Spotlight view={view} busy={busy} onSet={set.mutate} />
            <RecordEditor
              title='Hold the tension and pace'
              note='Values you set are held: the storyteller stops moving them until you release them.'
              fields={[
                {
                  key: 'profile',
                  label: 'Storyteller',
                  kind: 'pick',
                  table: table(STORYTELLER_PROFILES),
                },
                {
                  key: 'tension',
                  label: 'Tension',
                  kind: 'number',
                  min: 0,
                  max: SPAN,
                },
                {
                  key: 'boost_pct',
                  label: 'Pace of events (%)',
                  kind: 'number',
                  min: -SPAN,
                  max: SPAN,
                },
                {
                  key: 'cycle_offset',
                  label: 'Cycle offset',
                  kind: 'number',
                  min: 0,
                },
              ]}
              locked={view.locked}
              busy={busy}
              onSave={(values) => set.mutate({ values, release: [] })}
              onRelease={(release) => set.mutate({ values: {}, release })}
            />
            <StorytellerDepth view={view} blocked={readOnlyReason} />
          </>
        ) : null}
      </div>
    </Section>
  )
}

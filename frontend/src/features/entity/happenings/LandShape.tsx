import { useState } from 'react'
import {
  Activity,
  Flame,
  Gauge,
  MountainSnow,
  Sun,
  TriangleAlert,
  Waves,
  Wind,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Medallion,
  RangeField,
  Section,
  Timeline,
  TimelineItem,
  Paged,
  LoadingBlock,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  AdjustPanel,
  ChoiceEditor,
  EditorGroup,
  FlagEditor,
  HeldStrip,
  IconPicker,
  NumberEditor,
  Panel,
} from '../society/parts'
import { WORKING, badTone } from '../society/tones'
import { type LandShape, useLandShape } from './api'
import {
  CAUSE_SPEC,
  LAND_ICON,
  RIVER_SPEC,
  SOIL_SPEC,
  type SoilKind,
  fieldLabel,
} from './labels'

type Disaster = components['schemas']['Disaster']
type LandField =
  'desertification' | 'desertified' | 'volcanic' | 'volcanic_pressure'

const PERCENT = 100
const STIRRINGS: Record<
  string,
  { label: string; icon: typeof Flame; tone: 'danger' | 'warning' }
> = {
  eruption: { label: 'Eruption', icon: MountainSnow, tone: 'danger' },
  volcanic_quake: {
    label: 'Volcanic earthquake',
    icon: Activity,
    tone: 'warning',
  },
}
const LOWEST = 'lowest'

function ShapeSummary({ data }: { data: LandShape }) {
  const soil = data.soil ? SOIL_SPEC[data.soil] : null
  const river = data.river_class ? RIVER_SPEC[data.river_class] : null
  return (
    <div className='grid min-w-0 grid-cols-2 gap-3 @xl/land:grid-cols-4'>
      <KpiTile
        label='Desert'
        value={data.desertified ? 'Desert' : `${data.desertification}%`}
        icon={Wind}
        tone={data.desertified ? 'danger' : badTone(data.desertification)}
        hint={
          data.desertified
            ? `Since age ${data.desert_since_epoch ?? '?'}`
            : `Turns to desert at ${data.desertified_at}%`
        }
        meter={{
          value: data.desertification,
          max: PERCENT,
          label: 'Desertification',
        }}
      />
      <KpiTile
        label='River'
        value={river?.label ?? 'Unknown'}
        icon={river?.icon ?? Waves}
        tone={river?.tone ?? 'muted'}
        hint={
          data.course_changed_epoch !== null
            ? `New course since age ${data.course_changed_epoch}`
            : 'In its old bed'
        }
      />
      <KpiTile
        label='Volcano'
        value={data.volcanic ? `${data.volcanic_pressure}` : 'Quiet'}
        icon={MountainSnow}
        tone={data.volcanic ? badTone(data.volcanic_pressure) : 'muted'}
        hint={
          data.volcanic
            ? `${Math.round(data.eruption_chance)}% chance of eruption each age`
            : 'Not a volcanic land'
        }
        meter={
          data.volcanic
            ? {
                value: data.volcanic_pressure,
                max: PERCENT,
                label: 'Volcanic pressure',
              }
            : undefined
        }
      />
      <KpiTile
        label='Soil'
        value={soil?.label ?? 'Unknown'}
        icon={soil?.icon ?? Sun}
        tone={soil?.tone ?? 'muted'}
        hint={
          data.soil === 'ash' && data.ash_since_epoch !== null
            ? `Weathers into rich soil by age ${data.ash_since_epoch + data.ash_weathering_epochs}`
            : data.soil_locked
              ? 'Held by your hand'
              : 'Follows the land'
        }
      />
    </div>
  )
}

function Shifts({ data }: { data: LandShape }) {
  return (
    <Panel
      title='Rivers that moved'
      icon={Waves}
      tone='info'
      hint='Every time a river left its bed here'
    >
      {data.shifts.length === 0 ? (
        <Muted>No river has left its bed here.</Muted>
      ) : (
        <Timeline label='River courses'>
          <Paged items={data.shifts} as='li'>
            {(item, index) => {
              const cause = CAUSE_SPEC[item.cause]
              return (
                <TimelineItem
                  key={item.id}
                  icon={cause.icon}
                  tone='primary'
                  title={`${RIVER_SPEC[item.river_class].label}: ${item.from_region} to ${item.to_region}`}
                  timestamp={
                    item.year !== null
                      ? `Year ${item.year}`
                      : `Age ${item.epoch}`
                  }
                  last={index === data.shifts.length - 1}
                  framed
                >
                  <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                    <Badge size='sm' variant='secondary'>
                      <cause.icon />
                      {cause.label}
                    </Badge>
                    <EntityLink
                      kind='entity'
                      id={String(item.to_region_id)}
                      showIcon
                    >
                      {item.to_region}
                    </EntityLink>
                  </div>
                </TimelineItem>
              )
            }}
          </Paged>
        </Timeline>
      )}
    </Panel>
  )
}

function Stir({ data, blocked }: { data: LandShape; blocked: string | null }) {
  const [disaster, setDisaster] = useState<Disaster>('eruption')
  const [severity, setSeverity] = useState(60)
  const [target, setTarget] = useState(LOWEST)
  const stir = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/land:stir', {
          body: { region_id: data.region_id, disaster, severity },
        })
      ),
  })
  const river = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/land:river', {
          body: {
            from_region_id: data.region_id,
            to_region_id: target === LOWEST ? null : Number(target),
          },
        })
      ),
  })
  const busy = blocked ?? (stir.isPending || river.isPending ? WORKING : null)
  const neighbours = Object.fromEntries([
    [
      LOWEST,
      {
        label: 'The lowest neighbouring bed',
        icon: Waves,
        tone: 'info' as const,
      },
    ],
    ...data.neighbours.map((item) => [
      String(item.region_id),
      { label: item.region, icon: Waves, tone: 'info' as const },
    ]),
  ])
  const noRiver =
    data.river_class === null || data.river_class === 'none'
      ? 'There is no river here to move'
      : null
  return (
    <EditorGroup title='Fire and water' icon={Flame} pairs>
      <Panel
        title='Wake the mountain'
        icon={STIRRINGS[disaster].icon}
        tone={STIRRINGS[disaster].tone}
        hint='An eruption buries the land in ash; a volcanic quake can wake one'
      >
        <IconPicker
          label='What wakes'
          value={disaster}
          table={STIRRINGS}
          blocked={busy}
          onPick={(value) => setDisaster(value as Disaster)}
        />
        <RangeField
          label='Severity'
          icon={Gauge}
          value={severity}
          min={1}
          max={PERCENT}
          level={
            severity >= 70 ? 'Cataclysm' : severity >= 40 ? 'Great' : 'Small'
          }
          lowLabel='Small'
          highLabel='Cataclysm'
          onChange={setSeverity}
        />
        <Button
          size='sm'
          variant='destructive'
          className='mt-auto'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => stir.mutate(undefined)}
        >
          <MountainSnow />
          Let it break
        </Button>
      </Panel>
      <Panel
        title='Move the river'
        icon={Waves}
        tone='info'
        hint='Wells and fields follow the water into the new land'
      >
        <IconPicker
          label='Into'
          value={target}
          table={neighbours}
          blocked={busy}
          onPick={setTarget}
        />
        <Button
          size='sm'
          variant='outline'
          className='mt-auto'
          disabled={busy !== null || noRiver !== null}
          disabledReason={busy ?? noRiver ?? undefined}
          onClick={() => river.mutate(undefined)}
        >
          <Waves />
          Send the river there
        </Button>
      </Panel>
    </EditorGroup>
  )
}

function ShapeControls({
  data,
  blocked,
}: {
  data: LandShape
  blocked: string | null
}) {
  const shape = useGodAction({
    run: (values: {
      desertification?: number
      desertified?: boolean
      volcanic?: boolean
      volcanic_pressure?: number
    }) =>
      unwrap(
        api.POST('/api/actions/land:shape', {
          body: { region_id: data.region_id, hold: true, ...values },
        })
      ),
  })
  const soil = useGodAction({
    run: (value: SoilKind) =>
      unwrap(
        api.POST('/api/actions/environment:set', {
          body: { region_id: data.region_id, field: 'soil', value, lock: true },
        })
      ),
  })
  const busy = blocked ?? (shape.isPending || soil.isPending ? WORKING : null)
  return (
    <EditorGroup title='The ground itself' icon={LAND_ICON}>
      <NumberEditor
        key={`desert-${data.desertification}`}
        id={`land-${data.region_id}`}
        field={{
          key: 'desertification',
          label: 'Desertification',
          icon: Wind,
          value: data.desertification,
          min: 0,
          max: PERCENT,
        }}
        held={data.locked.includes('desertification')}
        blocked={busy}
        pending={shape.isPending}
        onSet={(value) => shape.mutate({ desertification: value })}
      />
      <FlagEditor
        label='Desert'
        hint='Sand, little rain, a desert landscape'
        icon={Wind}
        tone='danger'
        checked={data.desertified}
        held={data.locked.includes('desertified')}
        blocked={busy}
        onToggle={(value) => shape.mutate({ desertified: value })}
      />
      <FlagEditor
        label='Volcanic'
        hint='Builds pressure and can erupt'
        icon={MountainSnow}
        tone='danger'
        checked={data.volcanic}
        held={data.locked.includes('volcanic')}
        blocked={busy}
        onToggle={(value) => shape.mutate({ volcanic: value })}
      />
      <NumberEditor
        key={`pressure-${data.volcanic_pressure}`}
        id={`land-${data.region_id}`}
        field={{
          key: 'volcanic_pressure',
          label: 'Volcanic pressure',
          icon: Flame,
          value: data.volcanic_pressure,
          min: 0,
          max: PERCENT,
        }}
        held={data.locked.includes('volcanic_pressure')}
        blocked={busy}
        pending={shape.isPending}
        onSet={(value) => shape.mutate({ volcanic_pressure: value })}
      />
      {data.soil && (
        <ChoiceEditor
          label='Soil'
          hint='Salt kills the soil; ash weathers into rich volcanic soil'
          value={data.soil}
          table={SOIL_SPEC}
          held={data.soil_locked}
          blocked={busy}
          onPick={(value) => soil.mutate(value as SoilKind)}
        />
      )}
    </EditorGroup>
  )
}

export function LandShapeSection({
  regionId,
  readOnlyReason,
}: {
  regionId: number
  readOnlyReason?: string | null
}) {
  const view = useLandShape(regionId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const release = useGodAction({
    run: (fields: string[]) =>
      Promise.all(
        fields.map((field) =>
          field === 'soil'
            ? unwrap(
                api.POST('/api/actions/environment:unlock', {
                  body: { region_id: regionId, field: 'soil' },
                })
              )
            : unwrap(
                api.POST('/api/actions/land:release', {
                  body: { region_id: regionId, field: field as LandField },
                })
              )
        )
      ).then((results) => results[results.length - 1]),
  })
  const data = view.data
  const held = data
    ? [...data.locked, ...(data.soil_locked ? ['soil'] : [])]
    : []
  return (
    <Section
      id='section-land-shape'
      title='The shape of the land'
      description='Deserts that spread and retreat, rivers that move, mountains that burn, and the soil they leave.'
      icon={LAND_ICON}
      tone='warning'
    >
      {view.isPending && <LoadingBlock label='Reading the land' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Not yet surveyed'
          description={view.error.message}
        />
      )}
      {data && (
        <div
          data-surface='LandShapeSection'
          className='@container/land flex min-w-0 flex-col gap-4'
        >
          <div className='flex min-w-0 items-center gap-3 rounded-lg border bg-background p-3'>
            <Medallion
              icon={
                data.desertified
                  ? Wind
                  : data.volcanic
                    ? MountainSnow
                    : LAND_ICON
              }
              tone={data.desertified || data.volcanic ? 'danger' : 'gold'}
            />
            <div className='flex min-w-0 flex-1 flex-col gap-1'>
              <Text weight='semibold'>{data.region}</Text>
              <Muted variant='caption'>
                {[
                  data.desertified
                    ? 'a desert'
                    : data.desertification > 0
                      ? `${formatInteger(data.desertification)}% on the way to desert`
                      : 'green land',
                  data.volcanic ? 'a burning mountain stands here' : null,
                  data.last_eruption_epoch !== null
                    ? `last erupted in age ${data.last_eruption_epoch}`
                    : null,
                ]
                  .filter(Boolean)
                  .join(' · ')}
              </Muted>
            </div>
          </div>
          <ShapeSummary data={data} />
          <Shifts data={data} />
          <AdjustPanel
            title='Reshape the land'
            note='Wake an eruption, move the river, parch or green the land, raise a volcano or change the soil, salt included. Holds keep the world from undoing it; release them to let it follow again. Undoable from the ledger.'
          >
            <HeldStrip
              keys={held}
              labelOf={fieldLabel}
              blocked={blocked ?? (release.isPending ? WORKING : null)}
              onRelease={(keys) => release.mutate(keys)}
            />
            <Stir data={data} blocked={blocked} />
            <ShapeControls data={data} blocked={blocked} />
          </AdjustPanel>
        </div>
      )}
    </Section>
  )
}

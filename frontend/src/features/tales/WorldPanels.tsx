import { useState } from 'react'
import {
  Droplets,
  Flame,
  Gem,
  Hammer,
  Magnet,
  Snowflake,
  Sprout,
  Telescope,
  Trees,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { Tag } from '@/features/wars/military/parts'
import { type TalesNodeView, useTalesAction } from './api'
import {
  CRATER_ICON,
  MIGRATIONS,
  SEASON_CAUSES,
  SPELLS,
  WATER_ICON,
  ZONES,
} from './labels'
import {
  MANY,
  MORTAL_TYPES,
  PEOPLE_TYPES,
  SPAN,
  useTalesRow,
  useTalesStep,
} from './model'

type Formation = NonNullable<TalesNodeView['formation']>
type Season = NonNullable<TalesNodeView['season']>
type Forecast = TalesNodeView['forecasts'][number]
type Transformation = TalesNodeView['transformations'][number]

const UNSETTLERS: Record<Season['cause'], string> = {
  orbit: 'the orbit itself',
  natural_law: 'a natural law of the world',
  divine: 'a hand from beyond',
}

const NOT_A_WORLD =
  'Only a world forms from a disc and keeps seasons; this is not one'

function FormationCard({
  row,
  blocked,
}: {
  row: Formation
  blocked: string | null
}) {
  const action = useTalesRow(
    'formation:edit',
    'formation:delete',
    { world_id: row.world.id },
    blocked
  )
  const shaping = useTalesStep(
    'formation:reshape',
    { world_id: row.world.id },
    blocked,
    'The world takes the shape of its forming'
  )
  const zone = ZONES[row.zone]
  const migration = MIGRATIONS[row.migration]
  return (
    <Held
      icon={zone.icon}
      tone={zone.tone}
      title={`The forming of ${row.world.name}`}
      caption={`${zone.label} · ${migration.label.toLowerCase()} · read in epoch ${row.formed_epoch}${row.shaped ? ' · shaped by it' : ''}`}
      removeLabel='Forget its forming'
      editTitle='Set the forming'
      note='A world formed in a disc around its star: inside the snow line rocky and metal-rich, beyond it icy and gas-rich. The giants of the young system moved inward, scattering the inner worlds and bringing water, or outward, leaving them dry. The bombardment of its youth left craters and exotic matter; its core sets its magnetism and its mantle heat its tectonics. A world born after the forming was read takes its shape from it; older worlds keep theirs.'
      fields={[
        { key: 'zone', label: 'Formed', kind: 'pick', table: table(ZONES) },
        {
          key: 'migration',
          label: 'Giants',
          kind: 'pick',
          table: table(MIGRATIONS),
        },
        {
          key: 'bombardment',
          label: 'Bombardment',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'craters', label: 'Craters', kind: 'number', min: 0, max: MANY },
        { key: 'core_share', label: 'Core', kind: 'number', min: 0, max: SPAN },
        {
          key: 'mantle_heat',
          label: 'Mantle heat',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'water_delivered',
          label: 'Water brought',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'exotic_delivered',
          label: 'Exotic matter brought',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={migration} />}
    >
      <Meter
        label={`Bombardment (${row.bombardment} of ${SPAN})`}
        value={row.bombardment}
        tone='warning'
        icon={CRATER_ICON}
      />
      <Meter
        label={`Water brought (${row.water_delivered} of ${SPAN})`}
        value={row.water_delivered}
        tone='info'
        icon={WATER_ICON}
      />
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2 @md/tiles:grid-cols-4'>
          <KpiTile
            label='Core'
            value={row.core_share}
            icon={Magnet}
            tone='muted'
          />
          <KpiTile
            label='Mantle heat'
            value={row.mantle_heat}
            icon={Flame}
            tone='danger'
          />
          <KpiTile
            label='Craters'
            value={row.craters}
            icon={CRATER_ICON}
            tone='warning'
          />
          <KpiTile
            label='Exotic matter'
            value={row.exotic_delivered}
            icon={Gem}
            tone='verdigris'
          />
        </div>
      </div>
      <StepButton
        icon={Hammer}
        label='Shape the world by it'
        busy={shaping.busy}
        onClick={shaping.run}
      />
    </Held>
  )
}

export function FormationPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: TalesNodeView
  blocked: string | null
}) {
  const world = kind === 'world'
  const [reshape, setReshape] = useState('false')
  const reading = useTalesAction(
    'formation:read',
    (_: void) => ({ world_id: nodeId, reshape: reshape === 'true' }),
    'The forming of the world is read'
  )
  const busy = why(blocked ?? (world ? null : NOT_A_WORLD), reading.isPending)
  return (
    <div data-surface='FormationPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-formation'
        title='What the forming brought'
        legend={[
          { text: 'Core', variant: 'secondary' },
          { text: 'Water', variant: 'success' },
          { text: 'The mark is the bombardment', variant: 'outline' },
        ]}
        rows={
          data.formation
            ? [
                {
                  key: data.formation.world.id,
                  caption: `${data.formation.world.name}: core ${data.formation.core_share}, water ${data.formation.water_delivered}, bombardment ${data.formation.bombardment}`,
                  segments: [
                    {
                      value: data.formation.core_share,
                      fill: 'fill-muted-foreground',
                    },
                    {
                      value: data.formation.water_delivered,
                      fill: 'fill-info',
                    },
                  ],
                  mark: data.formation.bombardment,
                },
              ]
            : []
        }
        max={SPAN * 2}
        noun={['world', 'worlds']}
        empty='No forming is read for this.'
      />
      {data.formation && (
        <FormationCard row={data.formation} blocked={blocked} />
      )}
      <ForgeCard
        icon={Telescope}
        tone='info'
        title='Read the forming anew'
        note='The forming of the world is read again from its star and orbit; shaping it lets the forming set its metals, water, heat and magnetism.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => reading.mutate()}
          >
            <Telescope />
            Read it
          </Button>
        }
      >
        <MindPicker
          label='Shape the world by it'
          value={reshape}
          table={YES_NO}
          placeholder='No'
          blocked={blocked}
          onPick={setReshape}
        />
      </ForgeCard>
    </div>
  )
}

function SeasonCard({ row, blocked }: { row: Season; blocked: string | null }) {
  const action = useTalesRow(
    'irregular_season:edit',
    'irregular_season:delete',
    { world_id: row.world.id },
    blocked
  )
  const forecasting = useTalesStep(
    'irregular_season:forecast',
    { world_id: row.world.id },
    blocked,
    'The peoples read the seasons'
  )
  const spell = SPELLS[row.spell]
  const cause = SEASON_CAUSES[row.cause]
  return (
    <Held
      icon={spell.icon}
      tone={spell.tone}
      title={`${spell.label} on ${row.world.name}`}
      caption={`Since epoch ${row.spell_started_epoch}, for ${plural(row.spell_length, 'epoch', 'epochs')} · ${cause.label.toLowerCase()}`}
      removeLabel='Give the seasons back their measure'
      editTitle='Set the seasons'
      note='Irregular seasons run for spells of years of no set length. A long winter eats the food of every town each epoch by its severity, less for towns whose people heeded a forecast and stored food.'
      fields={[
        {
          key: 'cause',
          label: 'Cause',
          kind: 'pick',
          table: table(SEASON_CAUSES),
        },
        { key: 'spell', label: 'Spell', kind: 'pick', table: table(SPELLS) },
        {
          key: 'spell_started_epoch',
          label: 'Began in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'spell_length',
          label: 'Lasts (epochs)',
          kind: 'number',
          min: 1,
          max: MANY,
        },
        {
          key: 'severity',
          label: 'Severity',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={cause} />}
    >
      <Meter
        label={`Severity (${row.severity} of ${SPAN})`}
        value={row.severity}
        tone='info'
        icon={Snowflake}
      />
      <Facts
        items={[
          [
            'Unsettled by',
            <Ref key='by' node={row.by_node} empty={UNSETTLERS[row.cause]} />,
          ],
        ]}
      />
      <StepButton
        icon={Telescope}
        label='Have the peoples forecast it'
        busy={forecasting.busy}
        onClick={forecasting.run}
      />
    </Held>
  )
}

function ForecastCard({
  row,
  blocked,
}: {
  row: Forecast
  blocked: string | null
}) {
  const action = useTalesRow(
    'winter_forecast:edit',
    'winter_forecast:delete',
    { forecast_id: row.id },
    blocked
  )
  return (
    <Held
      icon={Telescope}
      tone={row.heeded ? 'success' : 'muted'}
      title={`${row.people.name} expect the turn by epoch ${row.predicted_end_epoch}`}
      caption={`Read in epoch ${row.made_epoch} on ${row.world.name} · ${row.heeded ? 'heeded' : 'not heeded'}`}
      removeLabel='Forget the forecast'
      editTitle='Set the forecast'
      note='Scholars learned in the sky read when a long season will turn; a people that heeds them stores food against the winter.'
      fields={[
        {
          key: 'scholar_entity_id',
          label: 'Scholar',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        {
          key: 'predicted_end_epoch',
          label: 'Expected turn in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'heeded', label: 'Heeded', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          [
            'Scholar',
            <Ref
              key='scholar'
              node={row.scholar}
              empty='no scholar; the forecast was set by hand'
            />,
          ],
        ]}
      />
    </Held>
  )
}

export function SeasonsPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: TalesNodeView
  blocked: string | null
}) {
  const world = kind === 'world'
  const [people, setPeople] = useState<number | null>(
    kind === 'people' ? nodeId : null
  )
  const [turn, setTurn] = useState('')
  const unsettling = useTalesAction(
    'irregular_season:create',
    (_: void) => ({ world_id: nodeId }),
    'The seasons lose their measure'
  )
  const forecasting = useTalesAction(
    'winter_forecast:set',
    (_: void) => ({
      world_id: data.season?.world.id ?? nodeId,
      people_id: people ?? 0,
      predicted_end_epoch: Number(turn || '0'),
      heeded: true,
    }),
    'The forecast is set'
  )
  const unsettleBusy = why(
    blocked ??
      (!world
        ? NOT_A_WORLD
        : data.season
          ? 'The seasons already run irregular'
          : null),
    unsettling.isPending
  )
  const forecastBusy = why(
    blocked ??
      (people === null
        ? 'Choose a people'
        : !world && !data.season
          ? 'Open this from the world whose seasons run irregular'
          : null),
    forecasting.isPending
  )
  return (
    <div data-surface='SeasonsPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-seasons'
        title='Severity of the long seasons'
        legend={[
          { text: 'Winter', variant: 'secondary' },
          { text: 'Summer', variant: 'warning' },
        ]}
        rows={
          data.season
            ? [
                {
                  key: data.season.world.id,
                  caption: `${data.season.world.name}: ${SPELLS[data.season.spell].label.toLowerCase()}, severity ${data.season.severity}`,
                  segments: [
                    {
                      value: data.season.severity,
                      fill:
                        data.season.spell === 'winter'
                          ? 'fill-info'
                          : 'fill-warning',
                    },
                  ],
                },
              ]
            : []
        }
        max={SPAN}
        noun={['world', 'worlds']}
        empty='The seasons here keep their measure.'
      />
      {data.season && <SeasonCard row={data.season} blocked={blocked} />}
      <Listed
        title='Forecasts'
        items={data.forecasts}
        empty='No people here has forecast the seasons.'
        noun={['forecast', 'forecasts']}
        itemKey={(item) => item.id}
      >
        {(item) => <ForecastCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Snowflake}
        tone='info'
        title='Unsettle the seasons'
        note='The summers and winters of this world will run for years of no set length.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={unsettleBusy !== null}
            disabledReason={unsettleBusy ?? undefined}
            onClick={() => unsettling.mutate()}
          >
            <Snowflake />
            Unsettle them
          </Button>
        }
      >
        <Muted variant='caption'>
          From the next epoch its summers and winters run for spells whose
          length no one knows.
        </Muted>
      </ForgeCard>
      <ForgeCard
        icon={Telescope}
        tone='success'
        title='Set a forecast'
        note='Tell a people when the long season will turn; they heed it and store food.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={forecastBusy !== null}
            disabledReason={forecastBusy ?? undefined}
            onClick={() => forecasting.mutate()}
          >
            <Telescope />
            Set it
          </Button>
        }
      >
        <NodePicker
          label='People'
          value={people}
          onChange={setPeople}
          blocked={blocked}
          types={PEOPLE_TYPES}
        />
        <NumberField
          label='Expected turn in epoch'
          value={turn}
          min={0}
          max={MANY}
          blocked={blocked}
          onChange={setTurn}
        />
      </ForgeCard>
    </div>
  )
}

function TransformationCard({
  row,
  blocked,
}: {
  row: Transformation
  blocked: string | null
}) {
  const action = useTalesRow(
    'eco_transformation:edit',
    'eco_transformation:delete',
    { plan_id: row.plan_id },
    blocked
  )
  return (
    <Held
      icon={Sprout}
      tone='success'
      title={row.plan_name}
      caption={`${row.progress} of ${plural(row.steps, 'step', 'steps')} · ${plural(row.regions_changed, 'land', 'lands')} changed · worked in epoch ${row.last_epoch}`}
      removeLabel='Stop it aiming the land'
      editTitle='Set the remaking of the land'
      note='Each epoch the plan moves the moisture, forest and soil of its lands a step toward its targets; a harsh climate takes part of each step back, and folk who live from the land as it is may sabotage it.'
      fields={[
        {
          key: 'target_moisture',
          label: 'Target moisture',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'target_forest',
          label: 'Target forest',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'target_fertility',
          label: 'Target soil',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'regions_changed',
          label: 'Lands changed',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'resistance',
          label: 'Resistance of the climate',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'sabotage',
          label: 'Sabotages',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Progress (${row.progress} of ${row.steps})`}
        value={row.progress}
        max={Math.max(1, row.steps)}
        tone='success'
        icon={Sprout}
      />
      <Meter
        label={`Resistance of the climate (${row.resistance} of ${SPAN})`}
        value={row.resistance}
        tone='warning'
        icon={Flame}
      />
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-3 gap-2'>
          <KpiTile
            label='Moisture'
            value={row.target_moisture}
            icon={Droplets}
            tone='info'
          />
          <KpiTile
            label='Forest'
            value={row.target_forest}
            icon={Trees}
            tone='success'
          />
          <KpiTile
            label='Soil'
            value={row.target_fertility}
            icon={Sprout}
            tone='gold'
          />
        </div>
      </div>
      <Facts
        items={[
          ['Held by', <Ref key='holder' node={row.holder} empty='no one' />],
          ['Remaking', <Ref key='target' node={row.target} empty='nowhere' />],
          ['Sabotages', String(row.sabotage)],
        ]}
      />
    </Held>
  )
}

export function TransformationPanel({
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: TalesNodeView
  blocked: string | null
}) {
  const [plan, setPlan] = useState('')
  const [moisture, setMoisture] = useState('60')
  const [forest, setForest] = useState('50')
  const [soil, setSoil] = useState('60')
  const plans = Object.fromEntries(
    data.transformations.map((row) => [String(row.plan_id), row.plan_name])
  )
  const aiming = useTalesAction(
    'eco_transformation:set',
    (_: void) => ({
      plan_id: Number(plan),
      target_moisture: Number(moisture),
      target_forest: Number(forest),
      target_fertility: Number(soil),
    }),
    'The plan aims the land'
  )
  const busy = why(
    blocked ??
      (data.transformations.length === 0
        ? 'No plan to remake the land touches this; start one as a long plan'
        : plan === ''
          ? 'Choose a plan'
          : null),
    aiming.isPending
  )
  return (
    <div
      data-surface='TransformationPanel'
      className='flex min-w-0 flex-col gap-4'
    >
      <Bars
        chart='chart-transformation'
        title='Progress of each remaking'
        legend={[
          { text: 'Progress', variant: 'success' },
          { text: 'The mark is the climate pulling back', variant: 'outline' },
        ]}
        rows={data.transformations.map((row) => ({
          key: row.plan_id,
          caption: `${row.plan_name}: ${row.progress} of ${row.steps}, resistance ${row.resistance}`,
          segments: [
            {
              value: (row.progress * SPAN) / Math.max(1, row.steps),
              fill: 'fill-success',
            },
          ],
          mark: row.resistance,
        }))}
        max={SPAN}
        noun={['plan', 'plans']}
        empty='No plan remakes this land.'
      />
      <Listed
        title='Remakings of the land'
        items={data.transformations}
        empty='No plan remakes this land.'
        noun={['plan', 'plans']}
        itemKey={(item) => item.plan_id}
      >
        {(item) => <TransformationCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Sprout}
        tone='success'
        title='Aim a remaking'
        note='Set the moisture, forest and soil a plan to remake the land works toward.'
        columns={4}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => aiming.mutate()}
          >
            <Sprout />
            Aim it
          </Button>
        }
      >
        <MindPicker
          label='Plan'
          value={plan}
          table={plans}
          placeholder='Choose a plan'
          blocked={blocked}
          onPick={setPlan}
        />
        <NumberField
          label='Moisture'
          value={moisture}
          min={0}
          max={SPAN}
          blocked={blocked}
          onChange={setMoisture}
        />
        <NumberField
          label='Forest'
          value={forest}
          min={0}
          max={SPAN}
          blocked={blocked}
          onChange={setForest}
        />
        <NumberField
          label='Soil'
          value={soil}
          min={0}
          max={SPAN}
          blocked={blocked}
          onChange={setSoil}
        />
      </ForgeCard>
    </div>
  )
}

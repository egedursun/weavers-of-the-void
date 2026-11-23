import { type ReactNode, useState } from 'react'
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
  SPELL_REACHES,
  SPELL_SHAPES,
  SPELLS,
  WATER_ICON,
  ZONES,
} from './labels'
import {
  MANY,
  MORTAL_TYPES,
  PEOPLE_TYPES,
  REGION_TYPES,
  SPAN,
  STAR_KINDS,
  useTalesRow,
  useTalesStep,
} from './model'

type Formation = NonNullable<TalesNodeView['formation']>
type Season = TalesNodeView['seasons'][number]
type Forecast = TalesNodeView['forecasts'][number]
type Transformation = TalesNodeView['transformations'][number]

const UNSETTLERS: Record<Season['cause'], string> = {
  orbit: 'the orbit itself',
  natural_law: 'a natural law of the world',
  divine: 'a hand from beyond',
  impact: 'an impact from the sky',
  eruption: 'an eruption',
  stellar: 'a change in its star',
  ocean_shift: 'a turned current',
  made: 'the works of its peoples',
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

function sourceOf(row: Season): ReactNode {
  if (row.source_region) return <Ref node={row.source_region} empty='' />
  if (row.source_star) return <Ref node={row.source_star} empty='' />
  if (row.source_impact_id !== null)
    return <Muted as='span'>{`impact ${row.source_impact_id}`}</Muted>
  if (row.source_incident_id !== null)
    return <Muted as='span'>{`happening ${row.source_incident_id}`}</Muted>
  return <Muted as='span'>{UNSETTLERS[row.cause]}</Muted>
}

function SeasonCard({ row, blocked }: { row: Season; blocked: string | null }) {
  const action = useTalesRow(
    'irregular_season:edit',
    'irregular_season:delete',
    { long_season_id: row.id },
    blocked
  )
  const forecasting = useTalesStep(
    'irregular_season:forecast',
    { long_season_id: row.id },
    blocked,
    'The peoples read the seasons'
  )
  const spell = SPELLS[row.spell]
  const cause = SEASON_CAUSES[row.cause]
  const left = Math.max(0, row.spell_started_epoch + row.spell_length)
  return (
    <Held
      icon={spell.icon}
      tone={spell.tone}
      title={`${spell.label} on ${row.world.name}`}
      caption={`${SPELL_SHAPES[row.shape].label} · since epoch ${row.spell_started_epoch}, until epoch ${left} · ${cause.label.toLowerCase()} · ${SPELL_REACHES[row.reach].label.toLowerCase()}`}
      removeLabel='End this long season'
      editTitle='Set the long season'
      note='A long winter eats the food of every town it reaches each epoch by its severity, less where the people heeded a forecast and stored food; a long summer takes the harvest of hot and dry lands and helps cold ones. A cycling spell turns between summer and winter while its cause holds; a single spell ends by its length.'
      fields={[
        {
          key: 'cause',
          label: 'Cause',
          kind: 'pick',
          table: table(SEASON_CAUSES),
        },
        {
          key: 'shape',
          label: 'Shape',
          kind: 'pick',
          table: table(SPELL_SHAPES),
        },
        { key: 'spell', label: 'Spell', kind: 'pick', table: table(SPELLS) },
        {
          key: 'reach',
          label: 'Reach',
          kind: 'pick',
          table: table(SPELL_REACHES),
        },
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
        {
          key: 'source_region_id',
          label: 'Source region',
          kind: 'node',
          types: REGION_TYPES,
        },
        {
          key: 'source_impact_id',
          label: 'Source impact',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'source_incident_id',
          label: 'Source happening',
          kind: 'number',
          min: 0,
          max: MANY,
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
        tone={row.spell === 'winter' ? 'info' : 'warning'}
        icon={spell.icon}
      />
      <Facts
        items={[
          ['Source', <span key='source'>{sourceOf(row)}</span>],
          [
            'Begun by',
            <Ref key='by' node={row.by_node} empty={UNSETTLERS[row.cause]} />,
          ],
          ['Reach', <Tag key='reach' item={SPELL_REACHES[row.reach]} />],
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

type Cause = Season['cause']
type Shape = Season['shape']
type SourceKind = 'impact' | 'region' | 'star' | 'incident' | null

const CAUSE_SOURCE: Record<Cause, SourceKind> = {
  orbit: null,
  natural_law: null,
  divine: null,
  impact: 'impact',
  eruption: 'region',
  stellar: 'star',
  ocean_shift: 'region',
  made: 'incident',
}

const CAUSE_SHAPES: Record<Cause, Shape[]> = {
  orbit: ['cycling'],
  natural_law: ['cycling'],
  divine: ['cycling', 'single'],
  impact: ['single'],
  eruption: ['single'],
  stellar: ['single'],
  ocean_shift: ['single'],
  made: ['single'],
}

function SpellSteps({
  nodeId,
  world,
  blocked,
}: {
  nodeId: number
  world: boolean
  blocked: string | null
}) {
  const [cause, setCause] = useState<Cause>('divine')
  const [region, setRegion] = useState<number | null>(null)
  const [star, setStar] = useState<number | null>(null)
  const [impact, setImpact] = useState('')
  const [incident, setIncident] = useState('')
  const [shape, setShape] = useState<Shape>('cycling')
  const [spell, setSpell] = useState<Season['spell']>('winter')
  const [reach, setReach] = useState<Season['reach']>('world')
  const [length, setLength] = useState('2')
  const [severity, setSeverity] = useState('50')
  const source = CAUSE_SOURCE[cause]
  const shapes = CAUSE_SHAPES[cause]
  const chosenShape = shapes.includes(shape) ? shape : shapes[0]
  const creating = useTalesAction(
    'irregular_season:create',
    (_: void) => ({
      world_id: nodeId,
      cause,
      shape: chosenShape,
      spell,
      length: Number(length || '1'),
      severity: Number(severity || '0'),
      reach,
      source_impact_id: source === 'impact' ? Number(impact) : null,
      source_region_id: source === 'region' ? region : null,
      source_star_id: source === 'star' ? star : null,
      source_incident_id: source === 'incident' ? Number(incident) : null,
    }),
    'A long season begins'
  )
  const sourceMissing =
    source === 'region' && region === null
      ? 'Choose the region it comes from'
      : source === 'star' && star === null
        ? 'Choose the star that lights this world'
        : source === 'impact' && !/^\d+$/.test(impact)
          ? 'Name the impact that struck this world'
          : source === 'incident' && !/^\d+$/.test(incident)
            ? 'Name the happening that made it'
            : null
  const busy = why(
    blocked ?? (!world ? NOT_A_WORLD : sourceMissing),
    creating.isPending
  )
  return (
    <ForgeCard
      icon={Snowflake}
      tone='info'
      title='Begin a long season'
      note='Choose what causes it, where it comes from, how it runs and how hard it bites. An impact, an eruption, a star, a turned current and the works of peoples bring a single spell; an orbit and a natural law bring cycling seasons; a god may bring either.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => creating.mutate()}
        >
          <Snowflake />
          Begin it
        </Button>
      }
    >
      <MindPicker
        label='1. Cause'
        value={cause}
        table={table(SEASON_CAUSES)}
        placeholder='A god'
        blocked={blocked}
        onPick={(value) => setCause(value as Cause)}
      />
      {source === 'region' ? (
        <NodePicker
          label='2. Source region'
          value={region}
          onChange={setRegion}
          blocked={blocked}
          types={REGION_TYPES}
        />
      ) : source === 'star' ? (
        <NodePicker
          label='2. Source star'
          value={star}
          onChange={setStar}
          blocked={blocked}
          kinds={STAR_KINDS}
        />
      ) : source === 'impact' ? (
        <NumberField
          label='2. Source impact'
          value={impact}
          min={0}
          max={MANY}
          blocked={blocked}
          onChange={setImpact}
        />
      ) : source === 'incident' ? (
        <NumberField
          label='2. Source happening'
          value={incident}
          min={0}
          max={MANY}
          blocked={blocked}
          onChange={setIncident}
        />
      ) : (
        <Muted variant='caption'>2. This cause needs no source.</Muted>
      )}
      <MindPicker
        label='3. Shape'
        value={chosenShape}
        table={table(
          Object.fromEntries(shapes.map((item) => [item, SPELL_SHAPES[item]]))
        )}
        placeholder={SPELL_SHAPES[shapes[0]].label}
        blocked={
          shapes.length === 1
            ? `${SEASON_CAUSES[cause].label} brings only ${SPELL_SHAPES[shapes[0]].label.toLowerCase()} spells`
            : blocked
        }
        onPick={(value) => setShape(value as Shape)}
      />
      <MindPicker
        label='4. Spell'
        value={spell}
        table={table(SPELLS)}
        placeholder='Choose its kind'
        blocked={blocked}
        onPick={(value) => setSpell(value as Season['spell'])}
      />
      <MindPicker
        label='5. Reach'
        value={reach}
        table={table(SPELL_REACHES)}
        placeholder='The whole world'
        blocked={blocked}
        onPick={(value) => setReach(value as Season['reach'])}
      />
      <NumberField
        label='6. Lasts (epochs)'
        value={length}
        min={1}
        max={MANY}
        blocked={blocked}
        onChange={setLength}
      />
      <NumberField
        label='7. Severity'
        value={severity}
        min={0}
        max={SPAN}
        blocked={blocked}
        onChange={setSeverity}
      />
    </ForgeCard>
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
  const [spellId, setSpellId] = useState<string>(
    data.seasons[0] ? String(data.seasons[0].id) : ''
  )
  const [turn, setTurn] = useState('')
  const forecasting = useTalesAction(
    'winter_forecast:set',
    (_: void) => ({
      long_season_id: Number(spellId),
      people_id: people ?? 0,
      predicted_end_epoch: Number(turn || '0'),
      heeded: true,
    }),
    'The forecast is set'
  )
  const forecastBusy = why(
    blocked ??
      (people === null
        ? 'Choose a people'
        : spellId === ''
          ? 'No long season holds here to forecast'
          : null),
    forecasting.isPending
  )
  const spellTable = Object.fromEntries(
    data.seasons.map((row) => [
      String(row.id),
      {
        label: `${SPELLS[row.spell].label} on ${row.world.name}`,
        icon: SPELLS[row.spell].icon,
        tone: SPELLS[row.spell].tone,
      },
    ])
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
        rows={data.seasons.map((row) => ({
          key: row.id,
          caption: `${row.world.name}: ${SPELLS[row.spell].label.toLowerCase()}, severity ${row.severity}`,
          segments: [
            {
              value: row.severity,
              fill: row.spell === 'winter' ? 'fill-info' : 'fill-warning',
            },
          ],
        }))}
        max={SPAN}
        noun={['long season', 'long seasons']}
        empty='The seasons here keep their measure.'
      />
      <Listed
        title='Long seasons'
        items={data.seasons}
        empty='No long season holds here.'
        noun={['long season', 'long seasons']}
        itemKey={(item) => item.id}
      >
        {(item) => <SeasonCard row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='Forecasts'
        items={data.forecasts}
        empty='No people here has forecast the seasons.'
        noun={['forecast', 'forecasts']}
        itemKey={(item) => item.id}
      >
        {(item) => <ForecastCard row={item} blocked={blocked} />}
      </Listed>
      <SpellSteps nodeId={nodeId} world={world} blocked={blocked} />
      <ForgeCard
        icon={Telescope}
        tone='success'
        title='Set a forecast'
        note='Tell a people when a long season will end; they heed it and store food.'
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
        <MindPicker
          label='Long season'
          value={spellId}
          table={table(spellTable)}
          placeholder='No long season'
          blocked={
            data.seasons.length === 0
              ? 'No long season holds here to forecast'
              : blocked
          }
          onPick={setSpellId}
        />
        <NodePicker
          label='People'
          value={people}
          onChange={setPeople}
          blocked={blocked}
          types={PEOPLE_TYPES}
        />
        <NumberField
          label='Expected end in epoch'
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

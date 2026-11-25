import { Globe2, Snowflake, Sun, Thermometer, Waves } from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { EmptyState } from '@/components/domain'
import { Label } from '@/components/typography'
import {
  type Field,
  Facts,
  Meter,
  RecordEditor,
} from '@/features/cosmography/parts'
import {
  type WorldPhysicsRecord,
  type WorldPhysicsView,
  physicsKeys,
  usePhysicsAction,
  useWorldPhysics,
} from './api'
import { YES_NO } from './edits'
import { fixed, kelvinText } from './format'
import { QuerySection } from './parts'

type Edit = {
  values?: EditValues
  release?: string[]
}

const PERCENT_FIELD = { kind: 'number', min: 0, max: 100 } as const

const GROUPS: { title: string; note: string; fields: Field[] }[] = [
  {
    title: 'Orbit',
    note: 'How stretched and tilted its path is; a stretched path brings a season of near and far.',
    fields: [
      {
        key: 'eccentricity',
        label: 'Stretch (0 to below 1)',
        kind: 'decimal',
        min: 0,
      },
      {
        key: 'inclination',
        label: 'Tilt of the path (degrees)',
        kind: 'decimal',
        min: 0,
      },
      {
        key: 'argument',
        label: 'Turn of the path (degrees)',
        kind: 'decimal',
        min: 0,
      },
      {
        key: 'circumbinary',
        label: 'Circles both stars',
        kind: 'pick',
        table: YES_NO,
      },
    ],
  },
  {
    title: 'Body',
    note: 'Mass and size set its gravity and how well it holds its air; its make sets its ores.',
    fields: [
      { key: 'mass', label: 'Mass (worlds)', kind: 'decimal', min: 0.001 },
      { key: 'radius', label: 'Size (worlds)', kind: 'decimal', min: 0.01 },
      {
        key: 'rotation_hours',
        label: 'Turn (hours)',
        kind: 'decimal',
        min: 0.1,
      },
      { key: 'iron', label: 'Iron', ...PERCENT_FIELD },
      { key: 'rock', label: 'Rock', ...PERCENT_FIELD },
      { key: 'ice', label: 'Ice', ...PERCENT_FIELD },
      { key: 'gas', label: 'Gas', ...PERCENT_FIELD },
      { key: 'exotic', label: 'Strange matter', ...PERCENT_FIELD },
    ],
  },
  {
    title: 'Air',
    note: 'What its air holds and how thick it is; carbon dioxide, methane and water vapour warm it.',
    fields: [
      { key: 'pressure', label: 'Pressure', kind: 'decimal', min: 0 },
      { key: 'nitrogen', label: 'Nitrogen', ...PERCENT_FIELD },
      { key: 'oxygen', label: 'Oxygen', ...PERCENT_FIELD },
      { key: 'carbon_dioxide', label: 'Carbon dioxide', ...PERCENT_FIELD },
      { key: 'methane', label: 'Methane', ...PERCENT_FIELD },
      { key: 'water_vapour', label: 'Water vapour', ...PERCENT_FIELD },
      { key: 'exotic_gas', label: 'Strange gases', ...PERCENT_FIELD },
    ],
  },
  {
    title: 'Surface',
    note: 'How much light its face throws back, how restless its ground is and how much water and ice it holds.',
    fields: [
      { key: 'albedo', label: 'Brightness of its face', ...PERCENT_FIELD },
      { key: 'tectonics', label: 'Moving ground', ...PERCENT_FIELD },
      { key: 'volcanism', label: 'Volcanoes', ...PERCENT_FIELD },
      { key: 'hydrosphere', label: 'Water', ...PERCENT_FIELD },
      { key: 'cryosphere', label: 'Ice', ...PERCENT_FIELD },
    ],
  },
  {
    title: 'What follows from them',
    note: 'The heavens work these out each epoch; a value you hold here stands by your will over what they derive.',
    fields: [
      { key: 'insolation', label: 'Light it takes', kind: 'decimal', min: 0 },
      {
        key: 'surface_temperature',
        label: 'Surface warmth (kelvin)',
        kind: 'decimal',
        min: 0,
      },
      {
        key: 'heat_shift',
        label: 'Warmth it gives its regions',
        kind: 'number',
      },
      { key: 'gravity_g', label: 'Gravity', kind: 'decimal', min: 0 },
      {
        key: 'escape_velocity',
        label: 'Speed to leave it',
        kind: 'decimal',
        min: 0,
      },
      { key: 'aurora', label: 'Auroras', ...PERCENT_FIELD },
      {
        key: 'eclipse_years',
        label: 'Years between eclipses',
        kind: 'number',
        min: 0,
      },
      { key: 'sea_level', label: 'Sea level', kind: 'number' },
      {
        key: 'tidally_locked',
        label: 'One face to its star',
        kind: 'pick',
        table: YES_NO,
      },
      { key: 'ringed', label: 'Ringed', kind: 'pick', table: YES_NO },
      {
        key: 'habitable',
        label: "In its star's temperate band",
        kind: 'pick',
        table: YES_NO,
      },
    ],
  },
]

function Derived({
  view,
  physics,
}: {
  view: WorldPhysicsView
  physics: WorldPhysicsRecord
}) {
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='flex min-w-0 flex-wrap gap-1'>
        {physics.habitable && (
          <Badge size='sm' variant='success'>
            <Sun />
            In its star&apos;s temperate band
          </Badge>
        )}
        {physics.tidally_locked && (
          <Badge size='sm' variant='info'>
            <Globe2 />
            One face to its star
          </Badge>
        )}
        {physics.ringed && (
          <Badge size='sm' variant='outline'>
            <Globe2 />
            Ringed
          </Badge>
        )}
        {view.icebound && (
          <Badge size='sm' variant='info'>
            <Snowflake />
            Gripped by ice
          </Badge>
        )}
      </div>
      <Facts
        items={[
          [
            'Year',
            view.year_length_days !== null
              ? `${plural(view.year_length_days, 'day', 'days')}`
              : 'Unknown',
          ],
          [
            'Day',
            view.day_length_hours !== null
              ? `${plural(view.day_length_hours, 'hour', 'hours')}`
              : 'Unknown',
          ],
          [
            'Seasons',
            view.season_count !== null ? String(view.season_count) : 'Unknown',
          ],
          [
            'Tilt of its axis',
            view.axial_tilt !== null ? `${view.axial_tilt}°` : 'Unknown',
          ],
          [
            'Light it takes',
            `${fixed(physics.insolation, 3)} of a home world's`,
          ],
          ['Surface warmth', kelvinText(physics.surface_temperature)],
          [
            'Warmth it gives its regions',
            `${physics.heat_shift > 0 ? '+' : ''}${physics.heat_shift}`,
          ],
          ['Gravity', `${fixed(physics.gravity_g)} of a home world's`],
          ['Speed to leave it', fixed(physics.escape_velocity)],
          ['Air pressure', fixed(physics.pressure)],
          ['Tides', `${view.tidal_strength ?? 0}/100`],
          [
            'Eclipses',
            physics.eclipse_years > 0
              ? `Every ${plural(physics.eclipse_years, 'year', 'years')}`
              : 'None',
          ],
          ['Auroras', `${physics.aurora}/100`],
          ['Sea level', String(physics.sea_level)],
          [
            'Next great eclipse',
            view.next_eclipse_epoch !== null
              ? `Epoch ${view.next_eclipse_epoch}`
              : 'None in its sky',
          ],
          [
            'Worlds seen crossing its star',
            view.transits.length === 0
              ? 'None'
              : view.transits
                  .map(
                    (transit) =>
                      `${transit.inner.name} at epoch ${transit.next_epoch}`
                  )
                  .join(', '),
          ],
        ]}
      />
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
        <div className='flex min-w-0 flex-col gap-1.5'>
          <Label>Its make</Label>
          <Meter label='Iron' value={physics.iron} tone='warning' />
          <Meter label='Rock' value={physics.rock} tone='default' />
          <Meter label='Ice' value={physics.ice} tone='muted' />
          <Meter label='Gas' value={physics.gas} tone='muted' />
          <Meter
            label='Strange matter'
            value={physics.exotic}
            tone='destructive'
          />
        </div>
        <div className='flex min-w-0 flex-col gap-1.5'>
          <Label>Its air</Label>
          <Meter label='Nitrogen' value={physics.nitrogen} tone='muted' />
          <Meter label='Oxygen' value={physics.oxygen} tone='success' />
          <Meter
            label='Carbon dioxide'
            value={physics.carbon_dioxide}
            tone='warning'
          />
          <Meter label='Methane' value={physics.methane} tone='warning' />
          <Meter
            label='Water vapour'
            value={physics.water_vapour}
            tone='default'
          />
        </div>
        <div className='flex min-w-0 flex-col gap-1.5'>
          <Label>Its surface</Label>
          <Meter
            label='Water'
            value={physics.hydrosphere}
            tone='default'
            icon={Waves}
          />
          <Meter
            label='Ice'
            value={physics.cryosphere}
            tone='muted'
            icon={Snowflake}
          />
          <Meter
            label='Volcanoes'
            value={physics.volcanism}
            tone='destructive'
            icon={Thermometer}
          />
          <Meter
            label='Brightness of its face'
            value={physics.albedo}
            tone='muted'
          />
        </div>
      </div>
    </div>
  )
}

export function WorldPhysicsSection({ worldId }: { worldId: number }) {
  const query = useWorldPhysics(worldId)
  const edit = usePhysicsAction(
    'world_physics:edit',
    (vars: Edit) => ({
      world_id: worldId,
      values: vars.values ?? {},
      release: vars.release ?? [],
    }),
    'The world is reshaped',
    [physicsKeys.world(worldId)]
  )
  const busy = edit.isPending ? 'Working' : null
  return (
    <QuerySection
      id='section-world-physics'
      title='Body and sky'
      description='Its orbit, body, air and surface, and the year, warmth and gravity that follow from them.'
      icon={Globe2}
      tone='info'
      query={query}
    >
      {(view) =>
        view.physics === null ? (
          <EmptyState
            icon={Globe2}
            size='inline'
            title='Its body is not yet measured'
            description='The heavens measure it at the next epoch.'
          />
        ) : (
          <div className='flex min-w-0 flex-col gap-3'>
            <Derived view={view} physics={view.physics} />
            {GROUPS.map((group) => (
              <RecordEditor
                act={edit}
                key={group.title}
                title={group.title}
                note={group.note}
                fields={group.fields}
                locked={(view.physics?.locked ?? []).filter((key) =>
                  group.fields.some((field) => field.key === key)
                )}
                busy={busy}
                onSave={(values) => edit.mutate({ values })}
                onRelease={(release) => edit.mutate({ release })}
              />
            ))}
          </div>
        )
      }
    </QuerySection>
  )
}

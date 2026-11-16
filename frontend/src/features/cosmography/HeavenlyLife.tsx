import { type ReactNode } from 'react'
import {
  Angry,
  EyeOff,
  Frown,
  Globe2,
  Heart,
  Meh,
  Smile,
  Sun,
} from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { Muted } from '@/components/typography'
import { useSons } from '@/features/pantheon/api'
import { YES_NO } from '@/features/physics/edits'
import {
  type StarRecord,
  type WorldRecord,
  useCosmography,
  useCosmographyAction,
} from './api'
import { STAR_AGES, WORLD_AGES, ZONES } from './labels'
import { ladderOf, nameTable } from './ladder'
import { Chip, Facts, Meter, NodeLink, RecordEditor } from './parts'

const MOODS = [
  { from: 40, label: 'Loving', icon: Heart },
  { from: 10, label: 'Kind', icon: Smile },
  { from: -10, label: 'Indifferent', icon: Meh },
  { from: -40, label: 'Restless', icon: Frown },
  { from: -100, label: 'Wrathful', icon: Angry },
] as const

function moodOf(mood: number) {
  return MOODS.find((row) => mood >= row.from) ?? MOODS[MOODS.length - 1]
}

type Edit = { values: EditValues; release: string[] }

const zoneTable = Object.fromEntries(
  Object.entries(ZONES).map(([key, value]) => [key, value.label])
)
const starAgeTable = Object.fromEntries(
  Object.entries(STAR_AGES).map(([key, value]) => [key, value.label])
)

function useSonNames(): Record<string, string> {
  const sons = useSons()
  return nameTable((sons.data ?? []).map((row) => row.son))
}

export function StarLifeSection({ star }: { star: StarRecord }) {
  const view = useCosmography()
  const sons = useSonNames()
  const edit = useCosmographyAction(
    'star_life:edit',
    (vars: Edit) => ({ star_id: star.id, ...vars }),
    'The life of the star is set'
  )
  const busy = edit.isPending ? 'Working' : null
  const age = STAR_AGES[star.age_stage]
  const zone = ZONES[star.galactic_zone]
  const ladder = view.data ? ladderOf(view.data) : null
  const structures = (view.data?.structures ?? []).filter(
    (row) => row.galaxy_id === star.galaxy_id
  )
  return (
    <Section
      id='section-star-life'
      title='Life of the star'
      description='Its place in its galaxy, its age, how steady it burns and what it gives off.'
      icon={Sun}
      tone='gold'
      actions={<Chip icon={age.icon}>{age.label}</Chip>}
    >
      <div
        data-surface='StarLifeSection'
        className='flex min-w-0 flex-col gap-3'
      >
        {view.isPending ? (
          <LoadingBlock label='Reading the galaxy' />
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'>
              <Meter label='Stability' value={star.stability} tone='success' />
              <Meter
                label='Radiation'
                value={star.radiation}
                tone='destructive'
              />
              <Meter
                label='Sacredness'
                value={star.sacredness}
                tone='warning'
              />
            </div>
            <Facts
              items={[
                [
                  'Galaxy',
                  <NodeLink
                    key='galaxy'
                    kind='galaxy'
                    id={star.galaxy_id}
                    name={ladder?.names.get(star.galaxy_id ?? 0)}
                  />,
                ],
                ['Zone', zone.label],
                [
                  'Inside',
                  structures.find((row) => row.id === star.structure_id)
                    ?.name ?? 'No structure',
                ],
                [
                  'Epochs left in this age',
                  star.lifecycle_clock ?? 'Set by its type',
                ],
                [
                  'Patron',
                  <NodeLink
                    key='patron'
                    kind='son'
                    id={star.patron_son_id}
                    name={sons[String(star.patron_son_id ?? 0)]}
                  />,
                ],
              ]}
            />
            <RecordEditor
              title='Shape the life of the star'
              note='Values you set are held. Moving it to another galaxy places it anew there.'
              fields={[
                {
                  key: 'stability',
                  label: 'Stability',
                  kind: 'number',
                  min: 0,
                  max: 100,
                },
                {
                  key: 'radiation',
                  label: 'Radiation',
                  kind: 'number',
                  min: 0,
                  max: 100,
                },
                {
                  key: 'sacredness',
                  label: 'Sacredness',
                  kind: 'number',
                  min: 0,
                  max: 100,
                },
                {
                  key: 'lifecycle_clock',
                  label: 'Epochs left in this age',
                  kind: 'number',
                  min: 0,
                },
                {
                  key: 'age_stage',
                  label: 'Age',
                  kind: 'pick',
                  table: starAgeTable,
                },
                {
                  key: 'galactic_zone',
                  label: 'Zone',
                  kind: 'pick',
                  table: zoneTable,
                },
                {
                  key: 'galaxy_id',
                  label: 'Galaxy',
                  kind: 'pick',
                  table: nameTable(view.data?.galaxies ?? []),
                },
                {
                  key: 'structure_id',
                  label: 'Inside structure',
                  kind: 'pick',
                  table: nameTable(structures),
                },
                {
                  key: 'patron_son_id',
                  label: 'Patron son',
                  kind: 'pick',
                  table: sons,
                },
              ]}
              locked={star.locked ?? []}
              busy={busy}
              onSave={(values) => edit.mutate({ values, release: [] })}
              onRelease={(release) => edit.mutate({ values: {}, release })}
            />
          </>
        )}
      </div>
    </Section>
  )
}

export function WorldPlacementSection({ world }: { world: WorldRecord }) {
  const view = useCosmography()
  const edit = useCosmographyAction(
    'world_life:edit',
    (vars: Edit) => ({ world_id: world.id, ...vars }),
    'The life of the world is set'
  )
  const busy = edit.isPending ? 'Working' : null
  const ladder = view.data ? ladderOf(view.data) : null
  const placement = view.data?.placements.find(
    (row) => row.world_id === world.id
  )
  const bound =
    world.star_id !== null || world.parent_world_id !== null
      ? 'It lies where its star lies; move its star instead'
      : null
  return (
    <Section
      id='section-world-life'
      title='The world in the heavens'
      description='Where the world lies on the scale of the cosmos, what that place does to it, and its own life as a body.'
      icon={Globe2}
      tone='info'
      actions={<Chip>{WORLD_AGES[world.age_stage]}</Chip>}
    >
      <div
        data-surface='WorldPlacementSection'
        className='flex min-w-0 flex-col gap-3'
      >
        {view.isPending ? (
          <LoadingBlock label='Reading its place' />
        ) : !placement || !ladder ? (
          <EmptyState
            icon={Globe2}
            size='inline'
            title='Not placed yet'
            description='The next epoch sets it on the scale of the cosmos.'
          />
        ) : (
          <>
            <Facts
              items={[
                [
                  'Dimension',
                  <NodeLink
                    key='dimension'
                    kind='dimension'
                    id={placement.dimension_id}
                    name={ladder.names.get(placement.dimension_id ?? 0)}
                  />,
                ],
                [
                  'Cluster',
                  <NodeLink
                    key='cluster'
                    kind='cluster'
                    id={placement.cluster_id}
                    name={ladder.names.get(placement.cluster_id ?? 0)}
                  />,
                ],
                [
                  'Galaxy',
                  <NodeLink
                    key='galaxy'
                    kind='galaxy'
                    id={placement.galaxy_id}
                    name={ladder.names.get(placement.galaxy_id ?? 0)}
                  />,
                ],
                ...(placement.top_cluster_id !== null &&
                placement.top_cluster_id !== placement.cluster_id
                  ? ([
                      [
                        'Supercluster',
                        <NodeLink
                          key='top-cluster'
                          kind='cluster'
                          id={placement.top_cluster_id}
                          name={ladder.names.get(placement.top_cluster_id)}
                        />,
                      ],
                    ] satisfies [string, ReactNode][])
                  : []),
                ['Zone', ZONES[placement.zone].label],
                [
                  'Time against the prime',
                  `×${placement.pull.time.toFixed(2)}`,
                ],
                ['Travel capacity', `×${placement.pull.capacity.toFixed(2)}`],
                ['Ore', `×${placement.pull.ore.toFixed(2)}`],
                ['Magic from its place', placement.pull.magic],
                ['Leak from its place', placement.pull.leak],
                ['Sanity drain', placement.pull.sanity],
                ['Danger', placement.pull.danger],
                ['Hostility', placement.pull.hostility],
              ]}
            />
          </>
        )}
        <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'>
          <Meter label='Magnetism' value={world.magnetism} tone='info' />
          <Meter label='Radiation' value={world.radiation} tone='destructive' />
          <Meter
            label='Biosphere health'
            value={world.biosphere_health}
            tone='success'
          />
          <div className='flex min-w-0 items-center justify-between gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
            <Muted as='span' variant='caption'>
              Mood toward its peoples
            </Muted>
            <Chip
              icon={
                world.consciousness_closed ? EyeOff : moodOf(world.mood).icon
              }
            >
              {world.consciousness_closed
                ? 'Withdrawn into itself'
                : `${moodOf(world.mood).label} (${world.mood > 0 ? '+' : ''}${world.mood})`}
            </Chip>
          </div>
        </div>
        <RecordEditor
          title='Shape the life of the world'
          note={
            bound ??
            'A world free of any star can be set straight into a galaxy or a dimension.'
          }
          fields={[
            {
              key: 'magnetism',
              label: 'Magnetism',
              kind: 'number',
              min: 0,
              max: 100,
            },
            {
              key: 'radiation',
              label: 'Radiation',
              kind: 'number',
              min: 0,
              max: 100,
            },
            {
              key: 'biosphere_health',
              label: 'Biosphere health',
              kind: 'number',
              min: 0,
              max: 100,
            },
            { key: 'mood', label: 'Mood', kind: 'number', min: -100, max: 100 },
            {
              key: 'consciousness_closed',
              label: 'Withdrawn into itself',
              kind: 'pick',
              table: YES_NO,
            },
            { key: 'age_stage', label: 'Age', kind: 'pick', table: WORLD_AGES },
            ...(bound === null
              ? ([
                  {
                    key: 'galaxy_id',
                    label: 'Galaxy',
                    kind: 'pick',
                    table: nameTable(view.data?.galaxies ?? []),
                  },
                  {
                    key: 'dimension_id',
                    label: 'Dimension',
                    kind: 'pick',
                    table: nameTable(view.data?.dimensions ?? []),
                  },
                ] as const)
              : []),
          ]}
          locked={world.locked ?? []}
          busy={busy}
          onSave={(values) =>
            edit.mutate({
              values,
              release: [],
            })
          }
          onRelease={(release) => edit.mutate({ values: {}, release })}
        />
      </div>
    </Section>
  )
}

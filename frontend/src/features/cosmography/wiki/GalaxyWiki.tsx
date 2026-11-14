import { useState } from 'react'
import {
  CalendarDays,
  Crosshair,
  Flame,
  Gem,
  Globe2,
  Layers,
  Map as MapIcon,
  MousePointerClick,
  Orbit,
  Plus,
  Ruler,
  Sparkles,
  Star,
  Sun,
  Trash2,
  Waves,
  Workflow,
  X,
} from 'lucide-react'
import { type ActionBody, type EditValues } from '@/api/actions'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import {
  EmptyState,
  EntityLink,
  Medallion,
  MiniStat,
  PagedList,
  Section,
} from '@/components/domain'
import { type DrawerPageProps } from '@/components/layout/drawer/DrawerStack'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { CelestialDepthSection } from '@/features/celestial/CelestialDepthSection'
import { StarDisc } from '@/features/cosmos/Glyphs'
import { useCosmos } from '@/features/cosmos/api'
import { MindPicker } from '@/features/entity/mind/parts'
import { ThingSections } from '@/features/entity/sections/ThingSections'
import { NumberField } from '@/features/entity/wilds/parts'
import { useSons } from '@/features/pantheon/api'
import { BeingCard } from '../BeingsPanel'
import { EventsPanel } from '../EventsPanel'
import { GalaxyMap, type Pick } from '../GalaxyMap'
import {
  type CosmographyCatalog,
  type GalaxyRecord,
  type StructureRecord,
  catalogLabel,
  catalogTable,
  useCosmographyAction,
  runCosmography,
} from '../api'
import { armText, nucleusText } from '../galaxyKind'
import { type WorldMark, worldMarks } from '../galaxyWorlds'
import { GALAXY_AGES, NUCLEI, STAR_AGES, STRUCTURES, ZONES } from '../labels'
import { type Ladder, nameTable } from '../ladder'
import { Chip, Facts, Meter, NodeLink, RecordEditor, RecordRow } from '../parts'
import { GalaxyThumb } from '../visual/GalaxyThumb'
import { LAYOUT_STRUCTURES } from '../visual/galaxyForm'
import { SkyWorship } from './SkyWorship'
import { pageId, useScaleData } from './data'
import {
  DangerZone,
  Missing,
  WikiError,
  WikiHero,
  WikiLoading,
  WikiRecords,
} from './shared'

type Edit = { values: EditValues; release: string[] }

const DISCOVERY = {
  known: 'Known',
  legend: 'A legend',
  unknown: 'Unknown',
  forgotten: 'Forgotten',
}
const PERCENT = 100

function GalaxyHero({
  galaxy,
  ladder,
  catalog,
  cover,
}: {
  galaxy: GalaxyRecord
  ladder: Ladder
  catalog: CosmographyCatalog
  cover: string | null
}) {
  const nucleus = NUCLEI[galaxy.nucleus]
  const dimensionId = ladder.dimensionOfGalaxy(galaxy)
  return (
    <WikiHero
      nodeId={galaxy.id}
      name={galaxy.name}
      overline={`Galaxy · ${catalogLabel(catalog.galaxy_types, galaxy.galaxy_type)}`}
      description={galaxy.description}
      cover={cover}
      emblem={
        <GalaxyThumb
          galaxy={galaxy}
          shape={catalog.shape}
          label={galaxy.name}
          points={3200}
          className='size-portrait-xl shrink-0'
        />
      }
      badges={
        <>
          <Badge size='sm' variant='default'>
            <nucleus.icon />
            {nucleus.label}
          </Badge>
          <Badge size='sm' variant='outline'>
            <Sun />
            {GALAXY_AGES[galaxy.age_stage]}
          </Badge>
          {galaxy.cluster_id !== null && (
            <Badge size='sm' variant='outline'>
              <Workflow />
              <EntityLink kind='cluster' id={String(galaxy.cluster_id)}>
                {ladder.names.get(galaxy.cluster_id) ?? 'Its cluster'}
              </EntityLink>
            </Badge>
          )}
          {dimensionId !== null && (
            <Badge size='sm' variant='outline'>
              <Layers />
              <EntityLink kind='dimension' id={String(dimensionId)}>
                {ladder.names.get(dimensionId) ?? 'Its dimension'}
              </EntityLink>
            </Badge>
          )}
          <Badge size='sm' variant='outline'>
            <CalendarDays />
            {`Since epoch ${galaxy.created_epoch}`}
          </Badge>
          {galaxy.locked.length > 0 && (
            <Badge
              size='sm'
              variant='warning'
            >{`${plural(galaxy.locked.length, 'value', 'values')} held`}</Badge>
          )}
        </>
      }
      meter={
        <div className='flex max-w-sm min-w-0 flex-col gap-1.5'>
          <div className='flex min-w-0 items-center justify-between gap-2'>
            <Label>Star formation</Label>
            <Stat value={galaxy.star_formation} unit={`/ ${PERCENT}`} />
          </div>
          <Progress
            size='sm'
            value={galaxy.star_formation}
            tone='success'
            aria-label='Star formation'
          />
        </div>
      }
    />
  )
}

function Glance({ galaxy, ladder }: { galaxy: GalaxyRecord; ladder: Ladder }) {
  const stars = ladder.starsIn(galaxy.id)
  const worlds = ladder.placementsIn(galaxy.id)
  const structures = ladder.data.structures.filter(
    (row) => row.galaxy_id === galaxy.id && row.ended_epoch === null
  )
  return (
    <Section title='At a glance' icon={Sparkles} tone='gold'>
      <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-4'>
        <MiniStat icon={Star} tone='gold' label='Stars' value={stars.length} />
        <MiniStat
          icon={Globe2}
          tone='info'
          label='Worlds'
          value={worlds.length}
        />
        <MiniStat
          icon={Sparkles}
          tone='verdigris'
          label='Structures'
          value={structures.length}
        />
        <MiniStat
          icon={Waves}
          tone='info'
          label='Arms'
          value={galaxy.arm_count}
        />
        <MiniStat
          icon={Ruler}
          tone='muted'
          label='Radius'
          value={Math.round(galaxy.radius)}
        />
        <MiniStat
          icon={Gem}
          tone='warning'
          label='Metallicity'
          value={`${galaxy.metallicity}%`}
        />
        <MiniStat
          icon={Flame}
          tone='danger'
          label='Leak'
          value={`${galaxy.leak}%`}
        />
        <MiniStat
          icon={Orbit}
          tone='info'
          label='Merging'
          value={
            galaxy.merging_with_galaxy_id !== null
              ? `${galaxy.merge_progress}%`
              : 'No'
          }
          hint={
            galaxy.merging_with_galaxy_id !== null
              ? `With ${ladder.names.get(galaxy.merging_with_galaxy_id) ?? 'another galaxy'}`
              : undefined
          }
        />
      </div>
    </Section>
  )
}

function PickedCard({
  pick,
  worlds,
  galaxy,
  ladder,
  catalog,
  onClear,
}: {
  pick: Pick
  worlds: readonly WorldMark[]
  galaxy: GalaxyRecord
  ladder: Ladder
  catalog: CosmographyCatalog
  onClear: () => void
}) {
  if (!pick) return null
  if (pick.kind === 'world') {
    const world = worlds.find((row) => row.id === pick.id)
    if (!world) return null
    const placement = ladder.data.placements.find(
      (row) => row.world_id === world.id
    )
    const sun =
      placement?.star_id != null
        ? ladder.data.star_names[String(placement.star_id)]
        : undefined
    return (
      <div className='flex min-w-0 flex-wrap items-center gap-3 rounded-xl border bg-card p-3'>
        <Medallion icon={Globe2} tone='verdigris' />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <EntityLink kind='world' id={String(world.id)}>
            {world.name}
          </EntityLink>
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            <Chip icon={Star}>{sun ? `Circles ${sun}` : 'No sun'}</Chip>
            {placement && (
              <Chip icon={ZONES[placement.zone].icon}>
                {ZONES[placement.zone].label}
              </Chip>
            )}
            <Chip>{`In ${galaxy.name}`}</Chip>
          </div>
        </div>
        <Button variant='ghost' size='sm' onClick={onClear}>
          <X />
          Clear
        </Button>
      </div>
    )
  }
  if (pick.kind === 'star') {
    const star = ladder.data.stars.find((row) => row.id === pick.id)
    if (!star) return null
    const zone = ZONES[star.galactic_zone]
    const age = STAR_AGES[star.age_stage]
    return (
      <div className='flex min-w-0 flex-wrap items-center gap-3 rounded-xl border bg-card p-3'>
        <StarDisc type={star.star_type} />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <EntityLink kind='star' id={String(star.id)}>
            {star.name}
          </EntityLink>
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            <Chip icon={zone.icon}>{zone.label}</Chip>
            <Chip icon={age.icon}>{age.label}</Chip>
            <Chip>{`Stability ${star.stability}`}</Chip>
            <Chip>{`Radiation ${star.radiation}`}</Chip>
          </div>
        </div>
        <Button variant='ghost' size='sm' onClick={onClear}>
          <X />
          Clear
        </Button>
      </div>
    )
  }
  const structure = ladder.data.structures.find((row) => row.id === pick.id)
  if (!structure) return null
  const kind = STRUCTURES[structure.kind]
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-3 rounded-xl border bg-card p-3'>
      <div className='flex min-w-0 flex-1 flex-col gap-1'>
        <Text weight='semibold'>{structure.name}</Text>
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <Chip icon={kind.icon}>
            {catalogLabel(catalog.structure_kinds, structure.kind)}
          </Chip>
          <Chip>{`Intensity ${structure.intensity}`}</Chip>
          <Chip>{`Radius ${Math.round(structure.radius)}`}</Chip>
          <Chip>{`In ${galaxy.name}`}</Chip>
        </div>
      </div>
      <Button variant='ghost' size='sm' onClick={onClear}>
        <X />
        Clear
      </Button>
    </div>
  )
}

function StructureForm({
  galaxy,
  catalog,
  place,
  onPlaceMode,
  placing,
}: {
  galaxy: GalaxyRecord
  catalog: CosmographyCatalog
  place: [number, number] | null
  placing: boolean
  onPlaceMode: (on: boolean) => void
}) {
  const [kind, setKind] = useState('')
  const [name, setName] = useState('')
  const [radius, setRadius] = useState('60')
  const [intensity, setIntensity] = useState('60')
  const create = useCosmographyAction(
    'galactic_structure:create',
    (_: void) => ({
      galaxy_id: galaxy.id,
      kind: kind as ActionBody<'galactic_structure:create'>['kind'],
      name: name.trim(),
      radius: Number(radius) || 60,
      intensity: Number(intensity) || 60,
      x: place?.[0] ?? 0,
      y: place?.[1] ?? 0,
    }),
    'A new structure took shape'
  )
  const busy = create.isPending ? 'Shaping' : null
  const missing =
    kind === ''
      ? 'Choose what to shape first'
      : place === null
        ? 'Click the map to choose where'
        : null
  const kinds = Object.fromEntries(
    Object.entries(catalogTable(catalog.structure_kinds)).filter(
      ([key]) => !LAYOUT_STRUCTURES.has(key as StructureRecord['kind'])
    )
  )
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-xl border border-dashed bg-muted/20 p-3'>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
        <div className='flex min-w-0 flex-col gap-0.5'>
          <Text weight='semibold'>Shape a new structure</Text>
          <Muted variant='caption'>
            Choose its kind, then click the map where it should lie.
          </Muted>
        </div>
        <Button
          size='sm'
          variant={placing ? 'default' : 'outline'}
          onClick={() => onPlaceMode(!placing)}
        >
          <MousePointerClick />
          {placing ? 'Clicking the map places it' : 'Place it on the map'}
        </Button>
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4'>
        <MindPicker
          label='Kind'
          value={kind}
          table={kinds}
          blocked={busy}
          onPick={setKind}
        />
        <div className='flex min-w-0 flex-col gap-1'>
          <Label>Name</Label>
          <Input
            value={name}
            placeholder='Named by the heavens if left empty'
            onChange={(event) => setName(event.target.value)}
            aria-label='Structure name'
          />
        </div>
        <NumberField
          label='Radius'
          value={radius}
          min={1}
          disabled={busy !== null}
          onChange={setRadius}
        />
        <NumberField
          label='Intensity'
          value={intensity}
          min={0}
          max={100}
          disabled={busy !== null}
          onChange={setIntensity}
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
        <Chip icon={Crosshair}>
          {place ? `At ${place[0]}, ${place[1]}` : 'No place chosen yet'}
        </Chip>
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => create.mutate()}
        >
          <Plus />
          Shape it
        </Button>
      </div>
    </div>
  )
}

function StructureCard({
  structure,
  catalog,
  onLocate,
}: {
  structure: StructureRecord
  catalog: CosmographyCatalog
  onLocate: () => void
}) {
  const edit = useCosmographyAction(
    'galactic_structure:edit',
    (vars: Edit) => ({ structure_id: structure.id, ...vars })
  )
  const remove = useCosmographyAction(
    'galactic_structure:delete',
    (_: void) => ({ structure_id: structure.id }),
    'The structure is unmade'
  )
  const busy = edit.isPending || remove.isPending ? 'Working' : null
  const kind = STRUCTURES[structure.kind]
  return (
    <RecordRow
      icon={kind.icon}
      tone={structure.ended_epoch === null ? kind.tone : 'muted'}
      title={structure.name}
      caption={`${catalogLabel(catalog.structure_kinds, structure.kind)} · since epoch ${structure.created_epoch}`}
      aside={
        <div className='flex shrink-0 items-center gap-1'>
          <Button
            size='sm'
            variant='ghost'
            onClick={onLocate}
            aria-label={`Show ${structure.name} on the map`}
          >
            <Crosshair />
          </Button>
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => remove.mutate()}
            aria-label={`Unmake ${structure.name}`}
          >
            <Trash2 />
          </Button>
        </div>
      }
    >
      <Meter label='Intensity' value={structure.intensity} tone='warning' />
      <RecordEditor
        title='Reshape it'
        note='Its kind, place, size and strength; stars inside it follow its effects.'
        fields={[
          { key: 'name', label: 'Name', kind: 'text' },
          {
            key: 'kind',
            label: 'Kind',
            kind: 'pick',
            table: catalogTable(catalog.structure_kinds),
          },
          {
            key: 'intensity',
            label: 'Intensity',
            kind: 'number',
            min: 0,
            max: 100,
          },
          { key: 'radius', label: 'Radius', kind: 'decimal', min: 1 },
          { key: 'x', label: 'Across', kind: 'decimal' },
          { key: 'y', label: 'Down', kind: 'decimal' },
        ]}
        locked={structure.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function MapSection({
  galaxy,
  ladder,
  catalog,
}: {
  galaxy: GalaxyRecord
  ladder: Ladder
  catalog: CosmographyCatalog
}) {
  const [pick, setPick] = useState<Pick>(null)
  const [placing, setPlacing] = useState(false)
  const [place, setPlace] = useState<[number, number] | null>(null)
  const structures = ladder.data.structures.filter(
    (row) => row.galaxy_id === galaxy.id
  )
  const stars = ladder.starsIn(galaxy.id)
  const shaped = structures.filter((row) => !LAYOUT_STRUCTURES.has(row.kind))
  const cosmos = useCosmos()
  const worlds = worldMarks(cosmos.data, ladder.data, galaxy.id)
  return (
    <>
      <Section
        id='section-galaxy-map'
        title='Map of the galaxy'
        description='Drag to turn it, scroll to come closer. Click a star, a world or a structure to read it; worlds stand where the Cosmos shows them.'
        icon={MapIcon}
        tone='gold'
      >
        <div className='flex min-w-0 flex-col gap-3'>
          <GalaxyMap
            galaxy={galaxy}
            shape={catalog.shape}
            structures={structures}
            selected={pick}
            placing={placing}
            onPick={setPick}
            onPlace={(x, y) => {
              setPlace([x, y])
              setPlacing(false)
            }}
            className='h-scene lg:h-scene-lg'
            overlay={
              <>
                <div className='flex min-w-0 flex-wrap gap-1.5'>
                  <Badge
                    size='sm'
                    variant='secondary'
                  >{`${plural(stars.length, 'star')}`}</Badge>
                  <Badge
                    size='sm'
                    variant='secondary'
                  >{`${plural(worlds.length, 'world')}`}</Badge>
                  <Badge
                    size='sm'
                    variant='secondary'
                  >{`${plural(shaped.length, 'structure')}`}</Badge>
                  <Badge size='sm' variant='secondary'>
                    {catalogLabel(catalog.galaxy_types, galaxy.galaxy_type)}
                  </Badge>
                </div>
                {placing && (
                  <Badge variant='default'>
                    Click the map to place the structure
                  </Badge>
                )}
              </>
            }
            hint='Drag: turn · right-drag: pan · wheel: zoom'
          />
          <PickedCard
            pick={pick}
            worlds={worlds}
            galaxy={galaxy}
            ladder={ladder}
            catalog={catalog}
            onClear={() => setPick(null)}
          />
        </div>
      </Section>
      <Section
        id='section-galaxy-structures'
        title='Structures'
        description='Nebulae, nurseries, clusters of stars and stranger works. Each changes what the stars and worlds inside it get.'
        icon={Sparkles}
        tone='verdigris'
      >
        <div className='flex min-w-0 flex-col gap-3'>
          {shaped.length === 0 ? (
            <EmptyState
              icon={Sparkles}
              size='inline'
              title='Only its arms, core and halo so far'
              description='Shape a nebula, a nursery or a vault below.'
            />
          ) : (
            <PagedList
              items={shaped}
              initial={6}
              noun={['structure', 'structures']}
              className='grid min-w-0 grid-cols-1 gap-2 xl:grid-cols-2'
              itemKey={(row) => row.id}
            >
              {(row) => (
                <StructureCard
                  structure={row}
                  catalog={catalog}
                  onLocate={() => setPick({ kind: 'structure', id: row.id })}
                />
              )}
            </PagedList>
          )}
          <StructureForm
            galaxy={galaxy}
            catalog={catalog}
            place={place}
            placing={placing}
            onPlaceMode={setPlacing}
          />
        </div>
      </Section>
    </>
  )
}

function StarsSection({
  galaxy,
  ladder,
}: {
  galaxy: GalaxyRecord
  ladder: Ladder
}) {
  const stars = ladder.starsIn(galaxy.id)
  const worlds = ladder.placementsIn(galaxy.id)
  return (
    <Section
      title='Stars and worlds'
      description={`${plural(stars.length, 'star')} burn here and ${plural(worlds.length, 'world')} lie in their light or drift between them.`}
      icon={Star}
      tone='gold'
    >
      {stars.length === 0 ? (
        <EmptyState
          icon={Star}
          size='inline'
          title='No star burns here yet'
          description='Its nurseries bear stars over the epochs; you can hang one from the Cosmos.'
        />
      ) : (
        <PagedList
          items={stars}
          initial={8}
          noun={['star', 'stars']}
          className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'
          itemKey={(row) => row.id}
        >
          {(row) => {
            const zone = ZONES[row.galactic_zone]
            const circled = worlds.filter(
              (place) => place.star_id === row.id
            ).length
            return (
              <li className='flex min-w-0 items-center gap-3 rounded-xl border bg-background p-3'>
                <StarDisc type={row.star_type} />
                <span className='flex min-w-0 flex-1 flex-col gap-1'>
                  <EntityLink kind='star' id={String(row.id)}>
                    {row.name}
                  </EntityLink>
                  <span className='flex min-w-0 flex-wrap items-center gap-1.5'>
                    <Chip icon={zone.icon}>{zone.label}</Chip>
                    <Chip icon={Globe2}>{`${plural(circled, 'world')}`}</Chip>
                  </span>
                </span>
              </li>
            )
          }}
        </PagedList>
      )}
    </Section>
  )
}

function ShapeSection({
  galaxy,
  ladder,
  catalog,
}: {
  galaxy: GalaxyRecord
  ladder: Ladder
  catalog: CosmographyCatalog
}) {
  const edit = useCosmographyAction(
    'galaxy:edit',
    (vars: Edit) => ({ galaxy_id: galaxy.id, ...vars }),
    'The galaxy is reshaped'
  )
  const sons = useSons()
  const sonNames = Object.fromEntries(
    (sons.data ?? []).map((row) => [String(row.son.id), row.son.name])
  )
  const busy = edit.isPending ? 'Working' : null
  const nuclei = Object.fromEntries(
    Object.entries(NUCLEI).map(([key, value]) => [key, value.label])
  )
  const kindOf = catalog.galaxy_types.find(
    (row) => row.value === galaxy.galaxy_type
  )
  return (
    <Section
      id='section-galaxy'
      title='Shape the galaxy'
      description='Every value you set is held against the engine until you let the heavens decide again.'
      icon={Orbit}
      tone='gold'
      surface='card'
    >
      <div data-surface='GalaxyPage' className='flex min-w-0 flex-col gap-4'>
        <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
          <Meter
            label='Star formation'
            value={galaxy.star_formation}
            tone='success'
          />
          <Meter
            label='Metallicity'
            value={galaxy.metallicity}
            tone='warning'
          />
          <Meter label='Leak' value={galaxy.leak} tone='destructive' />
          <Meter
            label='Merge progress'
            value={galaxy.merge_progress}
            tone='info'
          />
        </div>
        <Facts
          items={[
            ['Type', catalogLabel(catalog.galaxy_types, galaxy.galaxy_type)],
            ['Nucleus', NUCLEI[galaxy.nucleus].label],
            ['Arms its kind gives', armText(kindOf?.effects)],
            ['Nuclei its kind gives', nucleusText(kindOf?.effects)],
            ['Age', GALAXY_AGES[galaxy.age_stage]],
            [
              'Place in its cluster',
              `${Math.round(galaxy.x)}, ${Math.round(galaxy.y)}`,
            ],
            [
              'Merging with',
              <NodeLink
                key='merge'
                kind='galaxy'
                id={galaxy.merging_with_galaxy_id}
                name={ladder.names.get(galaxy.merging_with_galaxy_id ?? 0)}
              />,
            ],
            [
              'Patron',
              <NodeLink
                key='patron'
                kind='son'
                id={galaxy.patron_son_id}
                name={
                  galaxy.patron_son_id !== null
                    ? sonNames[String(galaxy.patron_son_id)]
                    : 'None'
                }
              />,
            ],
            ['Known', DISCOVERY[galaxy.discovery]],
          ]}
        />
        <RecordEditor
          title='Form and look'
          note='Its name, account and the form its stars take.'
          fields={[
            { key: 'name', label: 'Name', kind: 'text' },
            {
              key: 'galaxy_type',
              label: 'Type',
              kind: 'pick',
              table: catalogTable(catalog.galaxy_types),
            },
            { key: 'arm_count', label: 'Arms', kind: 'number', min: 0 },
            { key: 'radius', label: 'Radius', kind: 'decimal', min: 1 },
            { key: 'nucleus', label: 'Nucleus', kind: 'pick', table: nuclei },
            { key: 'description', label: 'Account', kind: 'text', long: true },
          ]}
          locked={galaxy.locked}
          busy={busy}
          onSave={(values) => edit.mutate({ values, release: [] })}
          onRelease={(release) => edit.mutate({ values: {}, release })}
        />
        <RecordEditor
          title='Life of the galaxy'
          note='How fast it bears stars, how rich and how open to other dimensions it is.'
          fields={[
            {
              key: 'star_formation',
              label: 'Star formation',
              kind: 'number',
              min: 0,
              max: 100,
            },
            {
              key: 'metallicity',
              label: 'Metallicity',
              kind: 'number',
              min: 0,
              max: 100,
            },
            { key: 'leak', label: 'Leak', kind: 'number', min: 0, max: 100 },
            {
              key: 'age_stage',
              label: 'Age',
              kind: 'pick',
              table: GALAXY_AGES,
            },
            {
              key: 'discovery',
              label: 'Known',
              kind: 'pick',
              table: DISCOVERY,
            },
          ]}
          locked={galaxy.locked}
          busy={busy}
          onSave={(values) => edit.mutate({ values, release: [] })}
          onRelease={(release) => edit.mutate({ values: {}, release })}
        />
        <RecordEditor
          title='Place and fate'
          note='Move it to another cluster or dimension, or set it merging with another galaxy.'
          fields={[
            {
              key: 'cluster_id',
              label: 'Cluster',
              kind: 'pick',
              table: nameTable(ladder.data.clusters),
            },
            {
              key: 'dimension_id',
              label: 'Dimension (outside any cluster)',
              kind: 'pick',
              table: nameTable(ladder.data.dimensions),
            },
            { key: 'x', label: 'Place across', kind: 'decimal' },
            { key: 'y', label: 'Place down', kind: 'decimal' },
            {
              key: 'merging_with_galaxy_id',
              label: 'Merging with',
              kind: 'pick',
              table: nameTable(
                ladder.data.galaxies.filter((row) => row.id !== galaxy.id)
              ),
            },
            {
              key: 'merge_progress',
              label: 'Merge progress',
              kind: 'number',
              min: 0,
              max: 100,
            },
            {
              key: 'patron_son_id',
              label: 'Patron son',
              kind: 'pick',
              table: sonNames,
            },
          ]}
          locked={galaxy.locked}
          busy={busy}
          onSave={(values) => edit.mutate({ values, release: [] })}
          onRelease={(release) => edit.mutate({ values: {}, release })}
        />
      </div>
    </Section>
  )
}

export function GalaxyView({ galaxyId }: { galaxyId: number }) {
  const { view, catalog, wiki, ladder } = useScaleData(galaxyId)
  if (view.isPending || !catalog) return <WikiLoading />
  if (view.isError)
    return (
      <WikiError
        icon={Orbit}
        title='The galaxy could not be read'
        message={view.error.message}
      />
    )
  const galaxy = ladder?.data.galaxies.find((row) => row.id === galaxyId)
  if (!ladder || !galaxy) return <Missing icon={Orbit} title='No such galaxy' />
  const beings = ladder.data.beings.filter((row) => row.galaxy_id === galaxy.id)
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <GalaxyHero
        galaxy={galaxy}
        ladder={ladder}
        catalog={catalog}
        cover={wiki?.cover ?? null}
      />
      <Glance galaxy={galaxy} ladder={ladder} />
      <MapSection galaxy={galaxy} ladder={ladder} catalog={catalog} />
      <StarsSection galaxy={galaxy} ladder={ladder} />
      <ShapeSection galaxy={galaxy} ladder={ladder} catalog={catalog} />
      <EventsPanel ladder={ladder} catalog={catalog} galaxyId={galaxy.id} />
      <SkyWorship nodeId={galaxy.id} />
      <Section title='Beings that roam it' icon={Orbit} tone='warning'>
        {beings.length === 0 ? (
          <EmptyState
            icon={Orbit}
            size='inline'
            title='No cosmic being roams it'
            description='Call one from the Heavens, or wait for one to arrive.'
          />
        ) : (
          <ul className='flex min-w-0 flex-col gap-2'>
            {beings.map((row) => (
              <BeingCard
                key={row.entity_id}
                being={row}
                ladder={ladder}
                catalog={catalog}
              />
            ))}
          </ul>
        )}
      </Section>
      <CelestialDepthSection
        kind='galaxy'
        id={galaxy.id}
        name={galaxy.name}
        depth={wiki?.depth ?? null}
      />
      <WikiRecords
        nodeId={galaxy.id}
        name={galaxy.name}
        wiki={wiki}
        prompt={galaxy.image_prompt}
        savePrompt={(next) =>
          runCosmography('galaxy:edit', {
            galaxy_id: galaxy.id,
            values: { image_prompt: next },
            release: ['image_prompt'],
          })
        }
      />
      <DangerZone
        noun='galaxy'
        name={galaxy.name}
        consequence='Its structures and events are lost; its stars drift between the galaxies until another holds them.'
        action='galaxy:delete'
        target={{ galaxy_id: galaxy.id }}
      />
      <ThingSections nodeId={galaxy.id} />
    </div>
  )
}

export function GalaxyPage({ id }: DrawerPageProps) {
  const value = pageId(id)
  return value === null ? (
    <Missing icon={Orbit} title='No such galaxy' />
  ) : (
    <GalaxyView galaxyId={value} />
  )
}

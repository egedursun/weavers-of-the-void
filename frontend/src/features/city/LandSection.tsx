import { Suspense, lazy, useState } from 'react'
import {
  Gem,
  Hammer,
  Mountain,
  Pickaxe,
  Sprout,
  Trash2,
  Trees,
  Wheat,
  Wrench,
  X,
} from 'lucide-react'
import { postAction } from '@/api/actions'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  PagedList,
  Section,
} from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import {
  Chip,
  Facts,
  ForgeCard,
  Meter,
  RecordRow,
} from '@/features/cosmography/parts'
import { hasWebGL2 } from '@/features/cosmos/useCosmosViewSettings'
import { why } from '@/features/dominion/model'
import { COMMODITY } from '@/features/entity/economy/labels'
import { FIELD_LABELS, TERRAIN } from '@/features/entity/environment/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { KIND_SPEC } from '@/features/entity/society/structureLabels'
import { Ref } from '@/features/gatherings/parts'
import { useGodAction } from '@/features/pantheon/godAction'
import { LandPlan2D } from './LandPlan2D'
import { type LandPick } from './LandScene3D'
import { type LandScene, useLandScene } from './api'
import { COVERS, GROUNDS, STATES } from './labels'

const LandScene3D = lazy(() => import('./LandScene3D'))

type Cover = LandScene['tiles'][number]['cover']
type ShareField =
  | 'forest_cover'
  | 'farmed'
  | 'grazed'
  | 'wetland'
  | 'cleared'
  | 'mined'
  | 'built'
  | 'soil_fertility'
  | 'magic_density'

const FIELD_OF_COVER: Record<Cover, ShareField | null> = {
  open: null,
  forest: 'forest_cover',
  fields: 'farmed',
  pasture: 'grazed',
  marsh: 'wetland',
  cleared: 'cleared',
  built: 'built',
  mined: 'mined',
}
const SHARE_LABEL: Record<ShareField, string> = {
  forest_cover: FIELD_LABELS.forest_cover ?? 'Forest cover',
  farmed: 'Farmland',
  grazed: 'Pasture',
  wetland: FIELD_LABELS.wetland ?? 'Wetland',
  cleared: FIELD_LABELS.cleared ?? 'Cleared land',
  mined: 'Mines',
  built: 'Built up',
  soil_fertility: FIELD_LABELS.soil_fertility ?? 'Soil fertility',
  magic_density: FIELD_LABELS.magic_density ?? 'Magic density',
}

function shareOf(scene: LandScene, field: ShareField): number {
  return scene[field]
}

function clampPct(value: string): number {
  return Math.max(0, Math.min(100, Math.round(Number(value) || 0)))
}

function ShareSetter({
  scene,
  field,
  blocked,
}: {
  scene: LandScene
  field: ShareField
  blocked: string | null
}) {
  const [value, setValue] = useState(String(shareOf(scene, field)))
  const set = useGodAction({
    run: () =>
      postAction('environment:set', {
        region_id: scene.region.id,
        field,
        value: clampPct(value),
        lock: true,
      }),
    success: `${SHARE_LABEL[field]} is set and held`,
  })
  const busy = why(blocked, set.isPending)
  return (
    <div className='flex min-w-0 flex-wrap items-end gap-2'>
      <NumberField
        label={`${SHARE_LABEL[field]} (0–100)`}
        min={0}
        max={100}
        value={value}
        blocked={busy}
        onChange={setValue}
      />
      <Button
        size='sm'
        disabled={busy !== null || clampPct(value) === shareOf(scene, field)}
        disabledReason={
          busy ??
          (clampPct(value) === shareOf(scene, field)
            ? 'It already stands at that share'
            : undefined)
        }
        onClick={() => set.mutate()}
      >
        <Sprout />
        Set and hold
      </Button>
    </div>
  )
}

function TilePanel({
  scene,
  tile,
  blocked,
  onClose,
}: {
  scene: LandScene
  tile: LandScene['tiles'][number]
  blocked: string | null
  onClose: () => void
}) {
  const field = FIELD_OF_COVER[tile.cover]
  const alike = scene.tiles.filter((item) => item.cover === tile.cover).length
  return (
    <RecordRow
      icon={Mountain}
      tone='verdigris'
      title={`${GROUNDS[tile.ground]} · ${COVERS[tile.cover]}`}
      caption={`Tile ${tile.q}, ${tile.r}${tile.river ? ' on the river' : ''}; one of ${alike} tiles of ${COVERS[tile.cover].toLowerCase()}. The tiles are drawn from the land's shares; change a share and the tiles follow.`}
      aside={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Close the tile'
          onClick={onClose}
        >
          <X />
        </Button>
      }
    >
      {field ? (
        <ShareSetter
          key={field}
          scene={scene}
          field={field}
          blocked={blocked}
        />
      ) : (
        <ShareSetter
          key='forest_cover'
          scene={scene}
          field='forest_cover'
          blocked={blocked}
        />
      )}
    </RecordRow>
  )
}

function ResourcePanel({
  resource,
  blocked,
  onClose,
}: {
  resource: LandScene['resources'][number]
  blocked: string | null
  onClose: () => void
}) {
  const [reserve, setReserve] = useState(String(resource.reserve))
  const [richness, setRichness] = useState(String(resource.richness))
  const set = useGodAction({
    run: () =>
      postAction('resource:set', {
        resource_id: resource.node.id,
        reserve: Math.max(0, Math.round(Number(reserve) || 0)),
        fields: { richness: clampPct(richness) },
      }),
    success: 'The deposit is set so',
  })
  const remove = useGodAction({
    run: () => postAction('resource:delete', { resource_id: resource.node.id }),
    success: 'The deposit is unmade',
  })
  const busy = why(blocked, set.isPending, remove.isPending)
  const spec = COMMODITY[resource.commodity]
  return (
    <RecordRow
      icon={spec.icon}
      tone='gold'
      title={<Ref node={resource.node} />}
      caption={`${spec.label} · richness ${resource.richness}`}
      aside={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Close the deposit'
          onClick={onClose}
        >
          <X />
        </Button>
      }
    >
      <Meter
        label={`Left: ${resource.reserve} of ${resource.initial_reserve}`}
        value={
          resource.initial_reserve > 0
            ? Math.round((resource.reserve / resource.initial_reserve) * 100)
            : 0
        }
        tone='default'
      />
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <NumberField
          label='Reserve'
          min={0}
          value={reserve}
          blocked={busy}
          onChange={setReserve}
        />
        <NumberField
          label='Richness (0–100)'
          min={0}
          max={100}
          value={richness}
          blocked={busy}
          onChange={setRichness}
        />
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => set.mutate()}
        >
          <Wrench />
          Set
        </Button>
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => remove.mutate()}
        >
          <Trash2 />
          Unmake
        </Button>
      </div>
    </RecordRow>
  )
}

function WorkPanel({
  work,
  blocked,
  onClose,
}: {
  work: LandScene['works'][number]
  blocked: string | null
  onClose: () => void
}) {
  const finish = useGodAction({
    run: () => postAction('structure:finish', { structure_id: work.node.id }),
    success: 'The work is finished',
  })
  const repair = useGodAction({
    run: () => postAction('structure:repair', { structure_id: work.node.id }),
    success: 'The work is repaired',
  })
  const raze = useGodAction({
    run: () =>
      postAction('structure:raze', { structure_id: work.node.id, reason: '' }),
    success: 'The work is razed',
  })
  const busy = why(blocked, finish.isPending, repair.isPending, raze.isPending)
  const spec = KIND_SPEC[work.kind]
  const unfinished = work.state === 'planned' || work.state === 'building'
  const whole = work.state === 'complete' && work.condition >= 100
  return (
    <RecordRow
      icon={spec.icon}
      tone={spec.tone ?? 'muted'}
      title={<Ref node={work.node} />}
      caption={`${spec.label} · level ${work.level} · ${STATES[work.state]}`}
      aside={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Close the work'
          onClick={onClose}
        >
          <X />
        </Button>
      }
    >
      <Facts
        items={[
          ['Condition', `${work.condition}%`],
          ['Built', `${work.progress}%`],
          ['Stands at', `tile ${work.q}, ${work.r}`],
        ]}
      />
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <Button
          size='sm'
          disabled={busy !== null || !unfinished}
          disabledReason={
            busy ?? (!unfinished ? 'It is already built' : undefined)
          }
          onClick={() => finish.mutate()}
        >
          <Hammer />
          Finish now
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || whole}
          disabledReason={busy ?? (whole ? 'It is whole' : undefined)}
          onClick={() => repair.mutate()}
        >
          <Wrench />
          Repair
        </Button>
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => raze.mutate()}
        >
          <Trash2 />
          Raze
        </Button>
      </div>
    </RecordRow>
  )
}

function PlacePanel({
  item,
  kind,
  onClose,
}: {
  item: LandScene['places'][number]
  kind: 'settlement' | 'place'
  onClose: () => void
}) {
  return (
    <RecordRow
      icon={kind === 'settlement' ? Wheat : Gem}
      tone='info'
      title={<Ref node={item.node} />}
      caption={
        kind === 'settlement'
          ? `${item.detail} people; open it for its city and its controls`
          : `${item.detail.replaceAll('_', ' ')}; open it for its controls`
      }
      aside={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Close'
          onClick={onClose}
        >
          <X />
        </Button>
      }
    />
  )
}

function LandForge({
  scene,
  blocked,
}: {
  scene: LandScene
  blocked: string | null
}) {
  const [field, setField] = useState<string>('forest_cover')
  const [name, setName] = useState('')
  const [commodity, setCommodity] = useState<string>('ore')
  const [reserve, setReserve] = useState('1000')
  const [richness, setRichness] = useState('50')
  const lay = useGodAction({
    run: () =>
      postAction('resource:create', {
        place_id: scene.region.id,
        name: name.trim(),
        commodity: commodity as LandScene['resources'][number]['commodity'],
        reserve: Math.max(1, Math.round(Number(reserve) || 1)),
        richness: Math.max(1, clampPct(richness)),
        quality: 60,
        revealed: true,
        required_level: 0,
      }),
    success: () => {
      setName('')
      return 'The deposit is laid'
    },
  })
  const busy = why(blocked, lay.isPending)
  return (
    <>
      <ForgeCard
        icon={Trees}
        tone='verdigris'
        title='Shape the land'
        note='Set any share of the land; the tiles are redrawn from it and the engine holds it until you release it.'
        columns={2}
        action={
          <ShareSetter
            key={field}
            scene={scene}
            field={field as ShareField}
            blocked={blocked}
          />
        }
      >
        <MindPicker
          label='Share'
          value={field}
          table={SHARE_LABEL}
          blocked={blocked}
          onPick={setField}
        />
      </ForgeCard>
      <ForgeCard
        icon={Pickaxe}
        tone='gold'
        title='Lay a deposit'
        note='A seam, a grove or a fishing ground in this land; peoples who know the craft begin to work it.'
        columns={4}
        action={
          <Button
            size='sm'
            disabled={busy !== null || !name.trim()}
            disabledReason={
              busy ?? (!name.trim() ? 'Name the deposit first' : undefined)
            }
            onClick={() => lay.mutate()}
          >
            <Pickaxe />
            Lay it
          </Button>
        }
      >
        <div className='flex min-w-0 flex-col gap-1'>
          <Label variant='overline'>Deposit name</Label>
          <Input
            aria-label='Deposit name'
            value={name}
            disabled={blocked !== null}
            onChange={(event) => setName(event.target.value)}
          />
        </div>
        <MindPicker
          label='Yields'
          value={commodity}
          table={table(COMMODITY)}
          blocked={blocked}
          onPick={setCommodity}
        />
        <NumberField
          label='Reserve'
          min={1}
          value={reserve}
          blocked={blocked}
          onChange={setReserve}
        />
        <NumberField
          label='Richness (1–100)'
          min={1}
          max={100}
          value={richness}
          blocked={blocked}
          onChange={setRichness}
        />
      </ForgeCard>
    </>
  )
}

function LandBody({
  scene,
  blocked,
}: {
  scene: LandScene
  blocked: string | null
}) {
  const [selected, setSelected] = useState<LandPick>(null)
  const plan = (
    <LandPlan2D scene={scene} selected={selected} onPick={setSelected} />
  )
  const covers = Object.entries(
    scene.tiles.reduce<Record<string, number>>((found, tile) => {
      found[tile.cover] = (found[tile.cover] ?? 0) + 1
      return found
    }, {})
  ) as [Cover, number][]
  const tile =
    selected?.kind === 'tile'
      ? scene.tiles.find(
          (item) => item.q === selected.q && item.r === selected.r
        )
      : undefined
  const pickId = selected !== null && 'id' in selected ? selected.id : null
  const resource =
    selected?.kind === 'resource'
      ? scene.resources.find((item) => item.node.id === pickId)
      : undefined
  const work =
    selected?.kind === 'work'
      ? scene.works.find((item) => item.node.id === pickId)
      : undefined
  const town =
    selected?.kind === 'settlement'
      ? scene.settlements.find((item) => item.node.id === pickId)
      : undefined
  const place =
    selected?.kind === 'place'
      ? scene.places.find((item) => item.node.id === pickId)
      : undefined
  const close = () => setSelected(null)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
        <KpiTile
          label='Elevation'
          value={scene.elevation}
          icon={Mountain}
          tone='muted'
        />
        <KpiTile
          label='Forest'
          value={`${scene.forest_cover}%`}
          icon={Trees}
          tone='success'
        />
        <KpiTile
          label='Farmed'
          value={`${scene.farmed}%`}
          icon={Wheat}
          tone='gold'
        />
        <KpiTile
          label='Mined'
          value={`${scene.mined}%`}
          icon={Pickaxe}
          tone='warning'
        />
      </div>
      <PagedList
        items={covers}
        initial={8}
        noun={['cover', 'covers']}
        as='div'
        className='flex min-w-0 flex-wrap gap-2'
        listProps={{ role: 'group', 'aria-label': 'Cover of the land' }}
        itemKey={([cover]) => cover}
      >
        {([cover, count]) => (
          <Chip icon={Sprout}>{`${COVERS[cover]}: ${count} tiles`}</Chip>
        )}
      </PagedList>
      <Muted variant='caption'>
        {`Each tile is one part in ${scene.tiles.length} of the land: its ground follows the biome shares, its cover the land's use; a river of class ${scene.river.replaceAll('_', ' ')} and a ${scene.coast.replaceAll('_', ' ')} coast; soil fertility ${scene.soil_fertility}, magic density ${scene.magic_density}. Deposits are drawn by their richness and dim as they run out.`}
      </Muted>
      <Facts
        items={[
          [
            'Terrain',
            TERRAIN[scene.terrain]?.label ?? scene.terrain.replaceAll('_', ' '),
          ],
          ['Climate', scene.temperature.replaceAll('_', ' ')],
          ['Roughness', scene.roughness],
          ['Moisture', scene.moisture],
          [SHARE_LABEL.grazed, `${scene.grazed}%`],
          [SHARE_LABEL.wetland, `${scene.wetland}%`],
          [SHARE_LABEL.cleared, `${scene.cleared}%`],
          [SHARE_LABEL.built, `${scene.built}%`],
        ]}
      />
      <div className='relative min-w-0 overflow-hidden rounded-xl border bg-muted'>
        <div className='aspect-video w-full'>
          {hasWebGL2() ? (
            <Suspense fallback={plan}>
              <LandScene3D
                scene={scene}
                selected={selected}
                onPick={setSelected}
                fallback={plan}
              />
            </Suspense>
          ) : (
            plan
          )}
        </div>
      </div>
      {tile && (
        <TilePanel
          scene={scene}
          tile={tile}
          blocked={blocked}
          onClose={close}
        />
      )}
      {resource && (
        <ResourcePanel
          key={resource.node.id}
          resource={resource}
          blocked={blocked}
          onClose={close}
        />
      )}
      {work && <WorkPanel work={work} blocked={blocked} onClose={close} />}
      {town && <PlacePanel item={town} kind='settlement' onClose={close} />}
      {place && <PlacePanel item={place} kind='place' onClose={close} />}
      <LandForge scene={scene} blocked={blocked} />
      <Label variant='overline'>{`Deposits (${scene.resources.length})`}</Label>
      {scene.resources.length === 0 && (
        <Muted variant='caption'>
          No deposit lies in this land yet; lay one above.
        </Muted>
      )}
      <PagedList
        items={scene.resources}
        initial={4}
        noun={['deposit', 'deposits']}
        className='flex min-w-0 flex-col gap-2'
        itemKey={(row) => row.node.id}
      >
        {(row) => (
          <RecordRow
            icon={COMMODITY[row.commodity].icon}
            tone='gold'
            title={<Ref node={row.node} />}
            caption={`${COMMODITY[row.commodity].label} · richness ${row.richness} · ${row.reserve} of ${row.initial_reserve} left`}
            aside={
              <Button
                size='sm'
                variant='ghost'
                onClick={() =>
                  setSelected({ kind: 'resource', id: row.node.id })
                }
              >
                Show
              </Button>
            }
          />
        )}
      </PagedList>
      <Label variant='overline'>{`Works in the open land (${scene.works.length})`}</Label>
      {scene.works.length === 0 && (
        <Muted variant='caption'>
          No work stands in the open land; mines and quarries are raised here by
          the towns that work it.
        </Muted>
      )}
      <PagedList
        items={scene.works}
        initial={4}
        noun={['work', 'works']}
        className='flex min-w-0 flex-col gap-2'
        itemKey={(row) => row.node.id}
      >
        {(row) => (
          <RecordRow
            icon={KIND_SPEC[row.kind].icon}
            tone={KIND_SPEC[row.kind].tone ?? 'muted'}
            title={<Ref node={row.node} />}
            caption={`${KIND_SPEC[row.kind].label} · ${STATES[row.state]}`}
            aside={
              <Button
                size='sm'
                variant='ghost'
                onClick={() => setSelected({ kind: 'work', id: row.node.id })}
              >
                Show
              </Button>
            }
          />
        )}
      </PagedList>
    </div>
  )
}

export function LandSection({
  regionId,
  readOnlyReason = null,
}: {
  regionId: number
  readOnlyReason?: string | null
}) {
  const query = useLandScene(regionId)
  return (
    <Section
      id='section-land'
      title='The land'
      description='The land drawn from the engine itself: its ground and cover on their tiles, its river and coast, its towns, places, works and deposits; and the god’s hand to shape it.'
      icon={Mountain}
      tone='verdigris'
    >
      <div data-surface='LandSection' className='flex min-w-0 flex-col gap-3'>
        {query.isPending ? (
          <LoadingBlock label='Drawing the land' />
        ) : query.isError ? (
          <EmptyState
            icon={Mountain}
            size='inline'
            title='The land could not be drawn'
            description={query.error.message}
          />
        ) : (
          <LandBody scene={query.data} blocked={readOnlyReason} />
        )}
      </div>
    </Section>
  )
}

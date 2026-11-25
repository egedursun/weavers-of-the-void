import { useState } from 'react'
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
import { agree, plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { FieldTile } from '@/components/domain/FieldTile'
import { table } from '@/features/arcana/labels'
import {
  Facts,
  ForgeCard,
  Meter,
  RecordRow,
} from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { COMMODITY } from '@/features/entity/economy/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { KIND_SPEC } from '@/features/entity/society/structureLabels'
import { Ref } from '@/features/gatherings/parts'
import { useGodAction } from '@/features/pantheon/godAction'
import { type LandScene } from './api'
import { COVERS, GROUNDS, STATES } from './labels'
import { FIELD_OF_COVER, SHARE_LABEL, type ShareField } from './landShares'

function shareOf(scene: LandScene, field: ShareField): number {
  return scene[field]
}

function clampPct(value: string): number {
  return Math.max(0, Math.min(100, Math.round(Number(value) || 0)))
}

export function ShareSetter({
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
    writes: [{ lever: 'environment:set' }],
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
        act={set}
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

export function TilePanel({
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
      caption={`Tile ${tile.q}, ${tile.r}${tile.river ? ' on the river' : ''}; one of ${plural(alike, 'tile', 'tiles')} of ${COVERS[tile.cover].toLowerCase()}. The tiles are drawn from the land's shares; change a share and the tiles follow.`}
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

export function ResourcePanel({
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
    writes: [{ lever: 'resource:set' }],
    run: () =>
      postAction('resource:set', {
        resource_id: resource.node.id,
        reserve: Math.max(0, Math.round(Number(reserve) || 0)),
        fields: { richness: clampPct(richness) },
      }),
    success: 'The deposit is set so',
  })
  const remove = useGodAction({
    writes: [{ lever: 'resource:delete' }],
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
          act={set}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => set.mutate()}
        >
          <Wrench />
          Set
        </Button>
        <Button
          act={remove}
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

export function WorkPanel({
  work,
  blocked,
  onClose,
}: {
  work: LandScene['works'][number]
  blocked: string | null
  onClose: () => void
}) {
  const finish = useGodAction({
    writes: [{ lever: 'structure:finish' }],
    run: () => postAction('structure:finish', { structure_id: work.node.id }),
    success: 'The work is finished',
  })
  const repair = useGodAction({
    writes: [{ lever: 'structure:repair' }],
    run: () => postAction('structure:repair', { structure_id: work.node.id }),
    success: 'The work is repaired',
  })
  const raze = useGodAction({
    writes: [{ lever: 'structure:raze' }],
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
          act={finish}
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
          act={repair}
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
          act={raze}
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

export function PlacePanel({
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
          ? `${item.detail} ${agree(Number(item.detail), 'person', 'people')}; open it for its city and its controls`
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

export function LandForge({
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
    writes: [{ lever: 'resource:create' }],
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
            act={lay}
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
        <FieldTile label='Deposit name'>
          <Input
            aria-label='Deposit name'
            value={name}
            disabled={blocked !== null}
            onChange={(event) => setName(event.target.value)}
          />
        </FieldTile>
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

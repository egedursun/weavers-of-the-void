import { useState } from 'react'
import { Lock, Pickaxe, Trash2 } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  EmptyState,
  EntityLink,
  FieldTile,
  Medallion,
  PagedList,
  Section,
  StatBar,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import {
  PASSAGE_KIND,
  PASSAGE_STATE,
  STRATUM,
} from '@/features/entity/environment/geologyLabels'
import { TERRAIN } from '@/features/entity/environment/labels'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { type MapView } from './api'

type DeepLevel = NonNullable<MapView['level']>
type Passage = DeepLevel['passages'][number]
type Cell = DeepLevel['cells'][number]

const PERCENT = 100
const SURFACE = 'surface'

function regionName(view: MapView, id: number): string {
  return (
    view.points.find((point) => point.entity.id === id)?.entity.name ??
    'a region'
  )
}

function endLabel(
  view: MapView,
  region: number,
  stratum: string | null
): string {
  const name = regionName(view, region)
  return stratum === null
    ? `the surface of ${name}`
    : `the ${STRATUM[stratum as DeepLevel['stratum']].label.toLowerCase()} beneath ${name}`
}

function PassageRow({ view, passage }: { view: MapView; passage: Passage }) {
  const { reason } = useGodGate()
  const kind = PASSAGE_KIND[passage.kind]
  const state = PASSAGE_STATE[passage.state]
  const send = useGodAction<'deep_passage:hold' | 'deep_passage:delete'>({
    run: (action) =>
      unwrap(
        api.POST(`/api/actions/${action}`, {
          body:
            action === 'deep_passage:hold'
              ? {
                  table: 'deep_passages',
                  key: { id: passage.passage_id },
                  values: {},
                  hold: true,
                  release: [],
                }
              : { table: 'deep_passages', key: { id: passage.passage_id } },
        })
      ),
    success: (_result, action) =>
      action === 'deep_passage:hold'
        ? 'The passage is held as it is'
        : 'The passage is gone',
  })
  const blocked = reason() ?? (send.isPending ? 'Working…' : null)
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={kind.icon} tone={state.tone} size='sm' />
        <Text as='span' weight='medium' truncate>
          {kind.label}
        </Text>
        <Badge variant={passage.state === 'open' ? 'info' : 'warning'}>
          {state.label}
        </Badge>
      </div>
      <Muted variant='caption'>
        {`From ${endLabel(view, passage.first_region_id, passage.first_stratum)} to ${endLabel(view, passage.second_region_id, passage.second_stratum)}`}
      </Muted>
      <div className='grid min-w-0 grid-cols-2 gap-2'>
        <StatBar label='Width' value={passage.width} max={PERCENT} framed />
        <StatBar
          label='Progress'
          value={passage.progress}
          max={PERCENT}
          framed
        />
      </div>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          size='sm'
          variant='outline'
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={() => send.mutate('deep_passage:hold')}
        >
          <Lock />
          Hold
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={() => send.mutate('deep_passage:delete')}
        >
          <Trash2 />
          Take away
        </Button>
      </div>
    </div>
  )
}

function CellRow({ view, cell }: { view: MapView; cell: Cell }) {
  const holder =
    cell.holder_id !== null
      ? view.points.find((point) => point.entity.id === cell.holder_id)?.entity
      : undefined
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <EntityLink kind='entity' id={String(cell.region_id)}>
          {cell.name ?? regionName(view, cell.region_id)}
        </EntityLink>
        <Badge>{TERRAIN[cell.terrain]?.label ?? 'Underground'}</Badge>
        {!cell.dwellable && <Badge variant='warning'>No one dwells here</Badge>}
        {cell.held && <Badge variant='warning'>Held</Badge>}
      </div>
      <Muted variant='caption'>
        {`${holder ? `Ruled by ${holder.name}` : 'Ruled by no realm'} · ${plural(cell.settlements, 'settlement')} · ${plural(cell.peoples.length, 'people', 'peoples')}`}
      </Muted>
      <div className='grid min-w-0 grid-cols-2 gap-2'>
        <StatBar label='Extent' value={cell.extent} max={PERCENT} framed />
        <StatBar label='Light' value={cell.light} max={PERCENT} framed />
      </div>
    </div>
  )
}

function OpenPassage({ view, level }: { view: MapView; level: DeepLevel }) {
  const { reason } = useGodGate()
  const [first, setFirst] = useState<string>('')
  const [second, setSecond] = useState<string>('')
  const ends = [
    ...level.cells.map((cell) => ({
      key: `${cell.region_id}:${level.stratum}`,
      region: cell.region_id,
      stratum: level.stratum as string | null,
      label: endLabel(view, cell.region_id, level.stratum),
    })),
    ...level.cells.map((cell) => ({
      key: `${cell.region_id}:${SURFACE}`,
      region: cell.region_id,
      stratum: null as string | null,
      label: endLabel(view, cell.region_id, null),
    })),
  ]
  const byKey = new Map(ends.map((end) => [end.key, end]))
  const open = useGodAction<void>({
    run: () => {
      const one = byKey.get(first)
      const two = byKey.get(second)
      return unwrap(
        api.POST('/api/actions/deep_passage:create', {
          body: {
            table: 'deep_passages',
            values: {
              first_region_entity_id: one?.region ?? 0,
              first_stratum: one?.stratum ?? null,
              second_region_entity_id: two?.region ?? 0,
              second_stratum: two?.stratum ?? null,
            },
          },
        })
      )
    },
    success: 'A passage now joins the two ends',
  })
  const blocked =
    reason() ??
    (level.cells.length === 0
      ? 'No cell lies at this depth to open a passage from'
      : !first || !second
        ? 'Choose both ends of the passage'
        : first === second
          ? 'A passage needs two different ends'
          : open.isPending
            ? 'Working…'
            : null)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
        <FieldTile label='From'>
          <Select value={first} onValueChange={setFirst}>
            <SelectTrigger aria-label='Passage from'>
              <SelectValue placeholder='Choose an end' />
            </SelectTrigger>
            <SelectContent>
              {ends.map((end) => (
                <SelectItem key={end.key} value={end.key}>
                  {end.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FieldTile>
        <FieldTile label='To'>
          <Select value={second} onValueChange={setSecond}>
            <SelectTrigger aria-label='Passage to'>
              <SelectValue placeholder='Choose an end' />
            </SelectTrigger>
            <SelectContent>
              {ends.map((end) => (
                <SelectItem key={end.key} value={end.key}>
                  {end.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FieldTile>
      </div>
      <Button
        size='sm'
        className='self-start'
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        onClick={() => open.mutate()}
      >
        <Pickaxe />
        Open a passage
      </Button>
    </div>
  )
}

function WaysDown({ view }: { view: MapView }) {
  const openings = view.deep?.openings ?? []
  if (openings.length === 0) return null
  return (
    <Section
      surface='card'
      icon={PASSAGE_KIND.opening.icon}
      title='Ways down'
      description='Openings from the surface into the world below. Choose a depth on the map to see where each leads.'
    >
      <PagedList
        items={openings}
        initial={6}
        noun={['opening', 'openings']}
        className='flex min-w-0 flex-col gap-2'
        itemKey={(opening) => opening.passage_id}
      >
        {(opening) => (
          <div className='flex min-w-0 flex-wrap items-center gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
            <Medallion
              icon={STRATUM[opening.stratum].icon}
              tone={PASSAGE_STATE[opening.state].tone}
              size='sm'
            />
            <Text as='span' weight='medium' truncate>
              {`${regionName(view, opening.region_id)} down to the ${STRATUM[opening.stratum].label.toLowerCase()}`}
            </Text>
            <Badge variant={opening.state === 'open' ? 'info' : 'warning'}>
              {PASSAGE_STATE[opening.state].label}
            </Badge>
            {opening.place_id !== null && (
              <Muted variant='caption'>
                {`Comes out at ${regionName(view, opening.place_id)}`}
              </Muted>
            )}
          </div>
        )}
      </PagedList>
    </Section>
  )
}

export function DeepMapPanel({ view }: { view: MapView }) {
  const level = view.level
  if (!level) return <WaysDown view={view} />
  const label = STRATUM[level.stratum].label
  return (
    <Section
      surface='card'
      icon={STRATUM[level.stratum].icon}
      title={`The map at the ${label.toLowerCase()}`}
      description='Cells and passages at this depth. Open a passage between two cells or up to the surface, hold one as it is, or take it away.'
    >
      <OpenPassage view={view} level={level} />
      {level.cells.length === 0 ? (
        <EmptyState
          icon={STRATUM[level.stratum].icon}
          title={`No ${label.toLowerCase()} on this world`}
          description='A god may make a cell beneath any land from the entry of its region.'
        />
      ) : (
        <PagedList
          items={level.cells}
          initial={6}
          noun={['cell', 'cells']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(cell) => cell.cell_id}
        >
          {(cell) => <CellRow view={view} cell={cell} />}
        </PagedList>
      )}
      {level.passages.length === 0 ? (
        <Muted>No passage reaches this depth yet.</Muted>
      ) : (
        <PagedList
          items={level.passages}
          initial={6}
          noun={['passage', 'passages']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(passage) => passage.passage_id}
        >
          {(passage) => <PassageRow view={view} passage={passage} />}
        </PagedList>
      )}
    </Section>
  )
}

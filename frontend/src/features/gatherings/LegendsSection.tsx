import { useState } from 'react'
import { BookMarked, Filter, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { PageControls } from '@/components/domain/PageControls'
import { Muted } from '@/components/typography'
import { Chip } from '@/features/cosmography/parts'
import { READ_ONLY_REASON } from '@/features/entity/actions/gate'
import { useWorldState } from '@/features/entity/api/queries'
import { MindPicker } from '@/features/entity/mind/parts'
import { SetDownHistory } from './HistoriesSection'
import { HistoryById, HistoryCard } from './HistoryCard'
import { type CollectionKind, useHistories } from './api'
import { useOpenHistory } from './history'
import { COLLECTION_KINDS, table } from './labels'
import { ThingPicker } from './parts'

const PAGE = 10
const ANY = 'any'
const PLACE_TYPES = ['place', 'settlement', 'structure', 'region']

export function LegendsSection({
  worlds,
}: {
  worlds: { id: number; name: string }[]
}) {
  const state = useWorldState()
  const blocked = state.data?.read_only ? READ_ONLY_REASON : null
  const [kind, setKind] = useState<string>(ANY)
  const [world, setWorld] = useState<string>(ANY)
  const [figure, setFigure] = useState<number | null>(null)
  const [place, setPlace] = useState<number | null>(null)
  const [offset, setOffset] = useState(0)
  const opened = useOpenHistory()
  const query = useHistories({
    kind: kind === ANY ? undefined : (kind as CollectionKind),
    world_id: world === ANY ? undefined : Number(world),
    node_id: figure ?? undefined,
    place_id: place ?? undefined,
    offset,
    limit: PAGE,
  })
  const items = query.data?.items ?? []
  const total = query.data?.total ?? 0
  const filtered =
    kind !== ANY || world !== ANY || figure !== null || place !== null
  const reset = () => {
    setKind(ANY)
    setWorld(ANY)
    setFigure(null)
    setPlace(null)
    setOffset(0)
  }
  return (
    <Section
      id='section-legends'
      title='Legends'
      description='Every history of the cosmos: wars and battles, journeys and pilgrimages, feasts, plagues, trials and digs, each with its figures, places and incidents.'
      icon={BookMarked}
      tone='verdigris'
    >
      <div
        data-surface='LegendsSection'
        className='flex min-w-0 flex-col gap-3'
      >
        <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2 lg:grid-cols-4'>
          <MindPicker
            label='Kind of history'
            value={kind}
            table={{ [ANY]: 'Every kind', ...table(COLLECTION_KINDS) }}
            blocked={null}
            onPick={(value) => {
              setKind(value)
              setOffset(0)
            }}
          />
          <MindPicker
            label='World'
            value={world}
            table={{
              [ANY]: 'Every world',
              ...Object.fromEntries(
                worlds.map((row) => [String(row.id), row.name])
              ),
            }}
            blocked={null}
            onPick={(value) => {
              setWorld(value)
              setOffset(0)
            }}
          />
          <ThingPicker
            label='Figure'
            value={figure}
            onChange={(value) => {
              setFigure(value)
              setOffset(0)
            }}
            blocked={null}
          />
          <ThingPicker
            label='Place'
            value={place}
            onChange={(value) => {
              setPlace(value)
              setOffset(0)
            }}
            blocked={null}
            types={PLACE_TYPES}
          />
        </div>
        <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
          <Chip
            icon={Filter}
          >{`${total} ${total === 1 ? 'history' : 'histories'}${filtered ? ' match' : ''}`}</Chip>
          <Button
            size='sm'
            variant='ghost'
            disabled={!filtered}
            disabledReason={filtered ? undefined : 'No filter is set'}
            onClick={reset}
          >
            <RotateCcw />
            Clear the filters
          </Button>
        </div>
        {opened.open !== null &&
          !items.some((row) => row.id === opened.open) && (
            <HistoryById
              id={opened.open}
              blocked={blocked}
              onClose={opened.close}
              onOpen={opened.show}
            />
          )}
        {query.isPending ? (
          <LoadingBlock label='Gathering the legends' />
        ) : query.isError ? (
          <EmptyState
            icon={BookMarked}
            size='inline'
            title='The legends could not be read'
            description={query.error.message}
          />
        ) : items.length === 0 ? (
          <EmptyState
            icon={BookMarked}
            size='inline'
            title={filtered ? 'No history matches' : 'No history is told yet'}
            description={
              filtered
                ? 'Loosen the filters to see more.'
                : 'Histories gather as the epochs pass; set one down below.'
            }
          />
        ) : (
          <div className='flex min-w-0 flex-col gap-2'>
            {items.map((row) => (
              <HistoryCard
                key={row.id}
                collection={row}
                blocked={blocked}
                open={opened.open === row.id}
                onToggle={() => opened.toggle(row.id)}
                onOpen={opened.show}
              />
            ))}
            <PageControls
              offset={offset}
              limit={PAGE}
              total={total}
              onChange={setOffset}
              label='Pages of legends'
              busy={query.isFetching}
            />
          </div>
        )}
        <Muted variant='caption'>
          A history set down here needs at least one figure.
        </Muted>
        <SetDownHistory blocked={blocked} />
      </div>
    </Section>
  )
}

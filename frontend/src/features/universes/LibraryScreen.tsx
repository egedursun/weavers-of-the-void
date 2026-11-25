import { type ReactNode, useEffect, useMemo, useState } from 'react'
import { APP_NAME, APP_VERSION } from '@/config/brand'
import { type EventSourceLike } from '@/realtime/eventStream'
import {
  Archive,
  BookPlus,
  CircleAlert,
  FileDown,
  History,
  Hourglass,
  LibraryBig,
  PackageOpen,
  SearchX,
  Star,
  Trash2,
} from 'lucide-react'
import { formatDateTime, formatInteger } from '@/lib/format'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Divider } from '@/components/ui/ornate'
import {
  AsideLayout,
  EmptyState,
  KpiTile,
  LoadingBlock,
  Section,
} from '@/components/domain'
import { Logo } from '@/components/layout/Logo'
import { Label, Muted, PageTitle } from '@/components/typography'
import { CreateUniverseDialog } from './CreateUniverseDialog'
import { ImportUniverseDialog } from './ImportUniverseDialog'
import { LibraryActivity } from './LibraryActivity'
import { LibraryWork } from './LibraryWork'
import { ServerShowMore } from './ServerShowMore'
import { ShelfFilters } from './ShelfFilters'
import { ShelfFront } from './ShelfFront'
import { TrashSheet } from './TrashSheet'
import { UniverseCard } from './UniverseCard'
import { DeleteUniverseDialog, UniverseActDialog } from './UniverseDialogs'
import {
  NO_UNIVERSE_FILTERS,
  useArchivedCount,
  useLibraryStream,
  useShelf,
  useTrash,
  useUniverses,
} from './api'
import {
  type UniverseFacets,
  type UniverseFilters,
  type UniverseSummary,
} from './types'
import { type UniverseAct, narrowedCount } from './universeModel'
import { useEnterUniverse } from './useEnterUniverse'

const SEARCH_DEBOUNCE_MS = 220
const NO_FACETS: UniverseFacets = { tags: [], origins: [], statuses: [] }

type Acting = { act: UniverseAct; universe: UniverseSummary }

function useDebounced(value: string): string {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const handle = window.setTimeout(
      () => setDebounced(value),
      SEARCH_DEBOUNCE_MS
    )
    return () => window.clearTimeout(handle)
  }, [value])
  return debounced
}

function HallHeader({
  tools,
  onCreate,
  onImport,
  onTrash,
  trashCount,
}: {
  tools: ReactNode
  onCreate: () => void
  onImport: () => void
  onTrash: () => void
  trashCount: number
}) {
  return (
    <header className='relative flex w-full max-w-7xl min-w-0 flex-col items-center gap-4 text-center'>
      {tools && (
        <div className='flex w-full min-w-0 justify-end'>
          <span className='flex items-center rounded-md border surface-framed border-gild/70 bg-card p-0.5'>
            {tools}
          </span>
        </div>
      )}
      <div className='relative flex items-center justify-center'>
        <span
          aria-hidden='true'
          className='absolute inset-4 rounded-full bg-linear-to-br from-primary/35 via-brand-violet/30 to-brand-magenta/25 blur-2xl'
        />
        <span className='relative flex h-28 w-28 items-center justify-center sm:h-36 sm:w-36'>
          <Logo
            size='md'
            className='size-full drop-shadow-xl'
            title={APP_NAME}
          />
        </span>
      </div>
      <div className='flex min-w-0 flex-wrap items-center justify-center gap-2'>
        <Label variant='overline'>{APP_NAME}</Label>
        <Badge variant='outline' size='sm' className='font-mono'>
          {`v${APP_VERSION}`}
        </Badge>
      </div>
      <div className='flex min-w-0 flex-col items-center gap-1'>
        <PageTitle className='text-gilded'>The Library of Universes</PageTitle>
        <Divider className='w-64' />
      </div>
      <Muted variant='prose'>
        Every universe you have made or brought in stands here as a book. Open
        one to rule it, or begin another.
      </Muted>
      <div className='flex min-w-0 flex-wrap items-center justify-center gap-2'>
        <Button type='button' size='lg' onClick={onCreate}>
          <BookPlus />
          Create a universe
        </Button>
        <Button type='button' size='lg' variant='outline' onClick={onImport}>
          <FileDown />
          Import a universe
        </Button>
        <Button type='button' size='lg' variant='outline' onClick={onTrash}>
          <Trash2 />
          The trash
          {trashCount > 0 && (
            <Badge variant='destructive' size='sm'>
              {formatInteger(trashCount)}
            </Badge>
          )}
        </Button>
      </div>
    </header>
  )
}

export function LibraryScreen({
  createSource,
  tools = null,
}: {
  createSource?: (url: string) => EventSourceLike
  tools?: ReactNode
}) {
  const pulse = useLibraryStream(createSource)
  const [filters, setFilters] = useState<UniverseFilters>(NO_UNIVERSE_FILTERS)
  const [text, setText] = useState('')
  const q = useDebounced(text)
  const effective = useMemo(() => ({ ...filters, q }), [filters, q])
  const query = useUniverses(effective)
  const shelf = useShelf()
  const archived = useArchivedCount()
  const trash = useTrash()
  const trashTotal = trash.data?.pages[0]?.total ?? 0
  const { enter, opening } = useEnterUniverse()
  const [creating, setCreating] = useState(false)
  const [importing, setImporting] = useState(false)
  const [trashOpen, setTrashOpen] = useState(false)
  const [acting, setActing] = useState<Acting | null>(null)
  const pages = query.data?.pages ?? []
  const shown = pages.flatMap((page) => page.items)
  const total = pages[0]?.total ?? 0
  const facets = pages[0]?.facets ?? NO_FACETS
  const shelfItems = shelf.data?.items ?? []
  const onShelf = shelf.data?.total ?? 0
  const epochs = shelfItems.reduce((sum, item) => sum + (item.epoch ?? 0), 0)
  const searching = narrowedCount(filters) > 0 || text.trim() !== ''
  const libraryEmpty =
    shelf.isSuccess && onShelf === 0 && (archived.data ?? 0) === 0
  const act = (universe: UniverseSummary, next: UniverseAct) =>
    setActing({ act: next, universe })
  const current = acting && shown.find((item) => item.id === acting.universe.id)
  const target = current ?? acting?.universe ?? null
  return (
    <main
      id='content'
      data-domain='library-of-universes'
      className='relative flex min-h-svh flex-col items-center gap-8 overflow-x-clip bg-background px-4 py-6 sm:py-10'
    >
      <span
        aria-hidden='true'
        className='pointer-events-none absolute inset-x-0 top-0 h-160 bg-linear-to-b from-brand-violet/12 via-primary/5 to-transparent'
      />
      <HallHeader
        tools={tools}
        onCreate={() => setCreating(true)}
        onImport={() => setImporting(true)}
        onTrash={() => setTrashOpen(true)}
        trashCount={trashTotal}
      />
      <div className='relative flex w-full max-w-7xl min-w-0 flex-col gap-6'>
        {shelf.isError && (
          <Alert variant='destructive'>
            <CircleAlert />
            <AlertTitle>The library could not be read</AlertTitle>
            <AlertDescription>
              {shelf.error.message}
              <Button
                type='button'
                size='sm'
                variant='outline'
                onClick={() => void shelf.refetch()}
              >
                Reload the library's numbers
              </Button>
            </AlertDescription>
          </Alert>
        )}
        <div
          aria-label='The library at a glance'
          role='group'
          className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'
        >
          <KpiTile
            label='On the shelf'
            value={shelf.isSuccess ? formatInteger(onShelf) : '…'}
            icon={LibraryBig}
            hint='Universes you can open now'
          />
          <KpiTile
            label='Epochs lived'
            value={shelf.isSuccess ? formatInteger(epochs) : '…'}
            icon={Hourglass}
            tone='verdigris'
            hint='Every epoch of every universe on the shelf'
          />
          <KpiTile
            label='Archived'
            value={archived.isSuccess ? formatInteger(archived.data) : '…'}
            icon={Archive}
            tone='muted'
            hint='Kept closed until you restore them'
          />
          <KpiTile
            label='In the trash'
            value={trash.isSuccess ? formatInteger(trashTotal) : '…'}
            icon={Trash2}
            tone='danger'
            hint='Waiting for their purge date'
          />
        </div>
        {libraryEmpty ? (
          <Section title='An empty hall' icon={LibraryBig} surface='card'>
            <EmptyState
              icon={LibraryBig}
              title='No universe stands here yet'
              description='Create your first universe and shape its birth, or import one someone shared with you.'
              action={
                <>
                  <Button type='button' onClick={() => setCreating(true)}>
                    <BookPlus />
                    Create your first universe
                  </Button>
                  <Button
                    type='button'
                    variant='outline'
                    onClick={() => setImporting(true)}
                  >
                    <FileDown />
                    Import a universe
                  </Button>
                </>
              }
            />
          </Section>
        ) : (
          <>
            <Section
              title='At hand'
              icon={Star}
              surface='card'
              description='Pinned universes and the ones you opened last. One click enters.'
            >
              {shelf.isPending ? (
                <LoadingBlock label='Reading the front of the hall' />
              ) : (
                <ShelfFront
                  shelf={shelfItems}
                  opening={opening}
                  onOpen={(universe) => enter(universe)}
                />
              )}
            </Section>
            <AsideLayout
              aside={
                <>
                  <Section
                    title='Work in hand'
                    icon={PackageOpen}
                    surface='card'
                    level={3}
                  >
                    <LibraryWork />
                  </Section>
                  <Section
                    title='Library log'
                    icon={History}
                    surface='card'
                    level={3}
                    description={
                      pulse
                        ? `Live. Last change ${formatDateTime(pulse.at)}.`
                        : 'Live changes are connecting.'
                    }
                  >
                    <LibraryActivity />
                  </Section>
                </>
              }
            >
              <Section title='The shelves' icon={LibraryBig} surface='card'>
                <ShelfFilters
                  filters={filters}
                  text={text}
                  facets={facets}
                  onText={setText}
                  onChange={setFilters}
                />
                {query.isPending ? (
                  <LoadingBlock label='Reading the shelves' />
                ) : query.isError ? (
                  <EmptyState
                    icon={CircleAlert}
                    title='The shelves could not be read'
                    description={query.error.message}
                    action={
                      <Button
                        type='button'
                        variant='outline'
                        onClick={() => void query.refetch()}
                      >
                        Reload the shelves
                      </Button>
                    }
                  />
                ) : shown.length === 0 ? (
                  <EmptyState
                    icon={searching ? SearchX : LibraryBig}
                    title={
                      searching ? 'No universe matches' : 'This shelf is empty'
                    }
                    description={
                      searching
                        ? 'Change the search or clear the filters to see more of the library.'
                        : 'Create a universe or import one to fill it.'
                    }
                    action={
                      searching ? (
                        <Button
                          type='button'
                          variant='outline'
                          onClick={() => {
                            setText('')
                            setFilters({
                              ...NO_UNIVERSE_FILTERS,
                              sort: filters.sort,
                            })
                          }}
                        >
                          Clear the search
                        </Button>
                      ) : (
                        <Button type='button' onClick={() => setCreating(true)}>
                          <BookPlus />
                          Create one for this shelf
                        </Button>
                      )
                    }
                  />
                ) : (
                  <>
                    <ul
                      aria-label='Universes'
                      className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 2xl:grid-cols-3'
                    >
                      {shown.map((universe) => (
                        <li key={universe.id} className='min-w-0'>
                          <UniverseCard
                            universe={universe}
                            opening={opening === universe.id}
                            onOpen={() => enter(universe)}
                            onAct={(next) => act(universe, next)}
                          />
                        </li>
                      ))}
                    </ul>
                    <ServerShowMore
                      shown={shown.length}
                      total={total}
                      more={query.hasNextPage}
                      loading={query.isFetchingNextPage}
                      onMore={() => void query.fetchNextPage()}
                    />
                  </>
                )}
              </Section>
            </AsideLayout>
          </>
        )}
      </div>
      <CreateUniverseDialog open={creating} onOpenChange={setCreating} />
      <ImportUniverseDialog open={importing} onOpenChange={setImporting} />
      <TrashSheet open={trashOpen} onOpenChange={setTrashOpen} />
      <UniverseActDialog
        act={acting && acting.act !== 'delete' ? acting.act : null}
        universe={acting && acting.act !== 'delete' ? target : null}
        onClose={() => setActing(null)}
      />
      <DeleteUniverseDialog
        universe={acting?.act === 'delete' ? target : null}
        onClose={() => setActing(null)}
      />
    </main>
  )
}

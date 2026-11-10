import { useCallback, useEffect, useMemo } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { getRouteApi } from '@tanstack/react-router'
import { navItem } from '@/config/navigation'
import {
  BookText,
  Download,
  Hourglass,
  ScrollText,
  Spline,
  Users,
} from 'lucide-react'
import { formatCompact } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, MiniStat, PageHeader } from '@/components/domain'
import { useGlobalWorld, useWorldFilter } from '@/components/layout/worldFilter'
import { Text } from '@/components/typography'
import { useCatalogue, useWorldState } from '@/features/entity/api/queries'
import { type ChronicleLine } from '@/features/entity/api/types'
import { scrollToSection } from '@/features/entity/scrollToSection'
import { LegendsSection } from '@/features/gatherings/LegendsSection'
import { useThreads } from '@/features/pantheon/api'
import { ChronicleFilters } from './ChronicleFilters'
import { ChronicleSearchResults } from './ChronicleSearchResults'
import { ChronicleThreads } from './ChronicleThreads'
import { CompareEpochs } from './CompareEpochs'
import { CosmicChronicleGrid } from './CosmicChronicleGrid'
import { EpochArticle } from './EpochArticle'
import { EpochStrip } from './EpochStrip'
import { EpochTraces } from './EpochTraces'
import {
  BOOK_URL,
  CODEX_URL,
  chronicleKeys,
  useChronicleCounts,
  useChronicleKindLabels,
  useEpochStatistics,
  useEpochs,
  usePerspectives,
} from './api'
import { type ChronicleSearch, kindSet } from './chronicleSearch'
import { type LineFilter, filterLines } from './lineFilter'

const ITEM = navItem('chronicle')
const route = getRouteApi('/_app/chronicle')

export function ChronicleScreen() {
  const search = route.useSearch()
  const globalWorld = useGlobalWorld()
  const navigate = route.useNavigate()
  const queryClient = useQueryClient()
  const state = useWorldState()
  const catalogue = useCatalogue()
  const epochs = useEpochs()
  const counts = useChronicleCounts()
  const perspectives = usePerspectives()
  const threads = useThreads()
  const stats = useEpochStatistics()
  const kindLabels = useChronicleKindLabels()
  const setGlobalWorld = useWorldFilter((store) => store.setWorldId)
  const change = useCallback(
    (patch: Partial<ChronicleSearch>) => {
      if ('world' in patch) setGlobalWorld(patch.world ?? null)
      void navigate({
        search: (previous) => ({ ...previous, ...patch }),
        replace: true,
      })
    },
    [navigate, setGlobalWorld]
  )
  const current = state.data?.world?.epoch ?? null
  const numbers = useMemo(() => {
    const set = new Set<number>()
    for (const item of epochs.data ?? []) set.add(item.epoch)
    for (const item of counts.data ?? []) set.add(item.epoch)
    if (current !== null) set.add(current)
    return [...set].sort((left, right) => right - left)
  }, [epochs.data, counts.data, current])
  const filter: LineFilter = useMemo(
    () => ({
      q: search.q ?? '',
      kinds: kindSet(search.kinds),
      world: search.world ?? globalWorld,
    }),
    [search.q, search.kinds, search.world, globalWorld]
  )
  const loaded = queryClient
    .getQueriesData<{ items: ChronicleLine[] }>({
      queryKey: chronicleKeys.linesAll,
    })
    .filter(([, data]) => data !== undefined)
  const shown = loaded.reduce(
    (sum, [, data]) => sum + filterLines(data?.items ?? [], filter).length,
    0
  )
  const worlds = state.data?.worlds ?? []
  const multiWorld = worlds.length > 1
  useEffect(() => {
    if (search.epoch === undefined) return
    const target = search.line ? `line-${search.line}` : `epoch-${search.epoch}`
    const timer = window.setTimeout(() => scrollToSection(target), 0)
    return () => window.clearTimeout(timer)
  }, [search.epoch, search.line])
  const go = (epoch: number, line?: number) => {
    change({ epoch, line })
    scrollToSection(`epoch-${epoch}`)
  }
  const kinds = (catalogue.data?.chronicle_kinds ?? []).map((item) => ({
    key: item.key,
    label: item.label,
  }))
  const pending = epochs.isPending || counts.isPending
  const empty = !pending && numbers.length === 0
  const countOf = (epoch: number) =>
    counts.data?.find((item) => item.epoch === epoch)?.lines ?? 0
  const statOf = (epoch: number) =>
    stats.data?.find((item) => item.epoch === epoch)
  const worldName = search.world
    ? worlds.find((world) => world.id === search.world)?.name
    : undefined
  const failure = epochs.error ?? counts.error
  return (
    <>
      <PageHeader
        title={ITEM.title}
        description={
          worldName ? `Only what happened on ${worldName}.` : ITEM.description
        }
        icon={ITEM.icon}
        actions={
          <>
            <Button variant='outline' size='sm' asChild>
              <a href={CODEX_URL} download>
                <Download />
                Codex (Markdown)
              </a>
            </Button>
            <Button variant='outline' size='sm' asChild>
              <a href={BOOK_URL} target='_blank' rel='noreferrer'>
                <BookText />
                The book
              </a>
            </Button>
          </>
        }
      />
      {failure && <Text tone='destructive'>{failure.message}</Text>}
      {empty ? (
        <EmptyState
          icon={ScrollText}
          title='No history yet'
          description='Each completed epoch adds its narrative and its chronicle lines here.'
        />
      ) : (
        <>
          <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
            <MiniStat
              icon={Hourglass}
              tone='gold'
              label='Epochs'
              value={numbers.length}
            />
            <MiniStat
              icon={ScrollText}
              tone='verdigris'
              label='Lines written'
              value={formatCompact(
                (counts.data ?? []).reduce((sum, item) => sum + item.lines, 0)
              )}
            />
            <MiniStat
              icon={Spline}
              tone='info'
              label='Open stories'
              value={
                (threads.data ?? []).filter(
                  (thread) => thread.status === 'open'
                ).length
              }
            />
            <MiniStat
              icon={Users}
              label="Peoples' tellings"
              value={(perspectives.data ?? []).length}
            />
          </div>
          <ChronicleFilters
            search={{
              ...search,
              world: search.world ?? globalWorld ?? undefined,
            }}
            onChange={change}
            kinds={kinds}
            worlds={worlds.map((world) => ({ id: world.id, name: world.name }))}
            loaded={loaded.length}
            epochs={numbers.length}
            shown={shown}
          />
          <ChronicleSearchResults
            query={search.q ?? ''}
            localMatches={shown}
            onGo={go}
          />
          <EpochStrip epochs={numbers} onJump={go} />
          {pending ? (
            <div className='flex flex-col gap-4'>
              <Skeleton className='h-textarea w-full' />
              <Skeleton className='h-textarea w-full' />
            </div>
          ) : (
            <div className='flex min-w-0 flex-col gap-4'>
              {numbers.map((epoch) => (
                <EpochArticle
                  key={epoch}
                  epoch={epoch}
                  item={epochs.data?.find((item) => item.epoch === epoch)}
                  ongoing={
                    epoch === current &&
                    !epochs.data?.some((item) => item.epoch === epoch)
                  }
                  lineCount={countOf(epoch)}
                  stats={statOf(epoch)}
                  previous={statOf(epoch - 1)}
                  perspectives={(perspectives.data ?? []).filter(
                    (item) => item.epoch === epoch
                  )}
                  filter={filter}
                  forceOpen={search.all === true || search.epoch === epoch}
                  highlightLine={search.line ?? null}
                  kindLabels={kindLabels}
                />
              ))}
            </div>
          )}
          <ChronicleThreads />
          <LegendsSection
            worlds={worlds.map((world) => ({ id: world.id, name: world.name }))}
          />
          <CosmicChronicleGrid enabled={multiWorld} />
          <CompareEpochs stats={stats.data ?? []} epochs={epochs.data ?? []} />
          <EpochTraces stats={stats.data ?? []} sons={state.data?.sons ?? []} />
        </>
      )}
    </>
  )
}

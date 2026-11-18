import {
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { navItem } from '@/config/navigation'
import {
  BookOpenText,
  LayoutGrid,
  Package,
  PackageOpen,
  RotateCcw,
  Search,
  SearchX,
  WalletCards,
  X,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { RARITIES, RARITY_LABEL, type Rarity } from '@/constants/rarity'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  EmptyState,
  PageHeader,
  RarityIcon,
  Section,
} from '@/components/domain'
import { RARITY_TEXT_CLASS } from '@/components/domain/rarityClasses'
import { Label, Muted, Text } from '@/components/typography'
import { useWorldState } from '@/features/entity/api/queries'
import { CardBinder } from './CardBinder'
import { CardDeck } from './CardDeck'
import { CardInspector } from './CardInspector'
import { CardLegend } from './CardLegend'
import { type CardOrder, type CharacterCard, useCharacterCards } from './api'
import {
  CARD_STATES,
  type CardSide,
  type CardState,
  DECKS,
  DIVINE_DECKS,
  type DeckKey,
  ORDERS,
  ORDER_LABEL,
  STATE_LABEL,
  deckOf,
  deckTotal,
  filtersOf,
} from './cardModel'
import { everyOpen, everySealed, sealedIn, useCardSeals } from './sealStore'
import { useCardExport } from './useCardExport'

const ITEM = navItem('cards')
const SEARCH_DELAY_MS = 250
const SKELETONS = 6
const ANY = '__any__'
const VIEW_KEY = 'aerona.cards.view'
const GUIDE_KEY = 'aerona.cards.guide'

type CardView = 'binder' | 'deck'

const VIEWS: readonly CardView[] = ['binder', 'deck']

function stored(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function keep(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
  } catch {
    return
  }
}

function useDelayed(value: string): string {
  const [delayed, setDelayed] = useState(value)
  useEffect(() => {
    const timer = window.setTimeout(() => setDelayed(value), SEARCH_DELAY_MS)
    return () => window.clearTimeout(timer)
  }, [value])
  return delayed
}

function FilterStep({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>{label}</Label>
      <div
        className='flex min-w-0 flex-wrap items-center gap-1.5'
        role='group'
        aria-label={label}
      >
        {children}
      </div>
    </div>
  )
}

export function CardsScreen() {
  const state = useWorldState()
  const [query, setQuery] = useState('')
  const [deck, setDeck] = useState<DeckKey>('all')
  const [rarity, setRarity] = useState<Rarity | null>(null)
  const [worldId, setWorldId] = useState<number | null>(null)
  const [life, setLife] = useState<CardState>('all')
  const [order, setOrder] = useState<CardOrder>('power')
  const [view, setView] = useState<CardView>(
    () => VIEWS.find((item) => item === stored(VIEW_KEY)) ?? 'binder'
  )
  const [guide, setGuide] = useState(() => stored(GUIDE_KEY) !== 'closed')
  const [position, setPosition] = useState(0)
  const [inspected, setInspected] = useState<number | null>(null)
  const search = useDelayed(query)
  const filters = useMemo(
    () => filtersOf(search, deck, rarity, worldId, life, order),
    [search, deck, rarity, worldId, life, order]
  )
  const cards = useCharacterCards(filters)
  const seals = useCardSeals()
  const exporter = useCardExport()
  const worlds = useMemo(() => state.data?.worlds ?? [], [state.data?.worlds])
  const worldNames = useMemo(
    () => new Map(worlds.map((world) => [world.id, world.name])),
    [worlds]
  )
  const worldOf = useCallback(
    (card: CharacterCard) =>
      card.world_id !== null ? (worldNames.get(card.world_id) ?? null) : null,
    [worldNames]
  )
  const pages = useMemo(() => cards.data?.pages ?? [], [cards.data?.pages])
  const visible = useMemo(() => pages.flatMap((page) => page.items), [pages])
  const first = pages[0]
  const total = first?.total ?? 0
  const decks = first?.decks ?? []
  const rarityCounts = new Map(
    (first?.rarities ?? []).map((row) => [row.rarity, row.total])
  )
  const divineAll = DECKS.filter((item) => DIVINE_DECKS.has(item.key)).reduce(
    (sum, item) => sum + deckTotal(decks, item),
    0
  )
  const divineTotal =
    deck === 'all' ? divineAll : DIVINE_DECKS.has(deck) ? total : 0
  const filtering =
    query.trim() !== '' ||
    deck !== 'all' ||
    rarity !== null ||
    worldId !== null ||
    life !== 'all'
  const latest = first?.latest_node_id ?? null
  const shownSealed = visible.filter((item) =>
    sealedIn(seals, item.node_id)
  ).length
  const allOpen = everyOpen(seals, latest)
  const allSealed = everySealed(seals)
  const fetchMore = cards.fetchNextPage
  const loadMore = useCallback(() => {
    void fetchMore()
  }, [fetchMore])

  const reset = (next: () => void) => {
    next()
    setPosition(0)
    setInspected(null)
  }
  const clear = () =>
    reset(() => {
      setQuery('')
      setDeck('all')
      setRarity(null)
      setWorldId(null)
      setLife('all')
    })
  const chooseView = (value: string) => {
    const next = VIEWS.find((item) => item === value)
    if (!next) return
    setView(next)
    keep(VIEW_KEY, next)
  }
  const toggleGuide = () => {
    setGuide((open) => {
      keep(GUIDE_KEY, open ? 'closed' : 'open')
      return !open
    })
  }
  const download = (card: CharacterCard, side: CardSide) =>
    exporter.download(card, side)

  return (
    <>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
        meta={<Badge variant='outline'>{plural(total, 'card', 'cards')}</Badge>}
        actions={
          <>
            <Button
              variant='outline'
              size='sm'
              onClick={() => latest !== null && seals.openAll(latest)}
              disabled={allOpen}
              disabledReason={
                latest === null
                  ? 'There is no card yet.'
                  : 'Every pack is already open.'
              }
            >
              <PackageOpen />
              Open every pack
            </Button>
            <Button
              variant='outline'
              size='sm'
              onClick={seals.sealAll}
              disabled={allSealed}
              disabledReason='Every pack is already sealed.'
            >
              <Package />
              Seal every pack
            </Button>
            <Button
              variant={guide ? 'secondary' : 'outline'}
              size='sm'
              aria-pressed={guide}
              onClick={toggleGuide}
            >
              <BookOpenText />
              Card guide
            </Button>
            <ToggleGroup
              type='single'
              variant='outline'
              size='sm'
              value={view}
              onValueChange={chooseView}
              aria-label='How the cards are laid out'
            >
              <ToggleGroupItem value='binder' aria-label='Binder of cards'>
                <LayoutGrid />
                Binder
              </ToggleGroupItem>
              <ToggleGroupItem value='deck' aria-label='Swipe through a deck'>
                <WalletCards />
                Deck
              </ToggleGroupItem>
            </ToggleGroup>
          </>
        }
      />
      {guide && (
        <Section
          id='cards-guide'
          title='Reading the cards'
          icon={BookOpenText}
          level={3}
          description='What every metal, frame, dial and gem on a card means.'
        >
          <CardLegend />
        </Section>
      )}
      <Section
        id='cards-deck'
        title={deckOf(deck).label}
        icon={deckOf(deck).icon}
        level={3}
        description={
          filtering
            ? `${plural(total, 'card matches', 'cards match')} the search and filters.`
            : 'The gods lead the collection; the souls of the worlds follow, mightiest first.'
        }
      >
        <div className='flex min-w-0 flex-col gap-4 rounded-md border surface-framed border-gild/70 bg-card p-3'>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <div className='min-w-0 flex-1 basis-60'>
              <Input
                type='search'
                leadingIcon={Search}
                placeholder='Find a card by name, title, calling or account'
                aria-label='Find a card'
                value={query}
                onChange={(event) => {
                  const next = event.target.value
                  reset(() => setQuery(next))
                }}
              />
            </div>
            <Select
              value={worldId === null ? ANY : String(worldId)}
              onValueChange={(value) =>
                reset(() => setWorldId(value === ANY ? null : Number(value)))
              }
              disabled={worlds.length === 0}
            >
              <SelectTrigger
                aria-label='World'
                size='sm'
                title={
                  worlds.length === 0
                    ? 'No world has been made yet.'
                    : undefined
                }
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ANY}>Every world</SelectItem>
                {worlds.map((world) => (
                  <SelectItem key={world.id} value={String(world.id)}>
                    {world.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={life}
              onValueChange={(value) =>
                reset(() =>
                  setLife(CARD_STATES.find((item) => item === value) ?? 'all')
                )
              }
            >
              <SelectTrigger aria-label='Living or fallen' size='sm'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CARD_STATES.map((item) => (
                  <SelectItem key={item} value={item}>
                    {STATE_LABEL[item]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={order}
              onValueChange={(value) =>
                reset(() =>
                  setOrder(ORDERS.find((item) => item === value) ?? 'power')
                )
              }
            >
              <SelectTrigger aria-label='Order' size='sm'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ORDERS.map((item) => (
                  <SelectItem key={item} value={item}>
                    {ORDER_LABEL[item]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              size='sm'
              variant='ghost'
              onClick={clear}
              disabled={!filtering}
              disabledReason='No search or filter is set.'
            >
              <X />
              Clear
            </Button>
          </div>
          <FilterStep label='Deck'>
            {DECKS.map((item) => {
              const Icon = item.icon
              const count = deckTotal(decks, item)
              return (
                <Button
                  key={item.key}
                  size='sm'
                  variant={deck === item.key ? 'secondary' : 'ghost'}
                  aria-pressed={deck === item.key}
                  onClick={() => reset(() => setDeck(item.key))}
                  disabled={count === 0 && deck !== item.key}
                  disabledReason={`No card of ${item.label.toLowerCase()} matches the other filters.`}
                >
                  <Icon />
                  {`${item.label} · ${formatInteger(count)}`}
                </Button>
              )
            })}
          </FilterStep>
          <FilterStep label='Rarity'>
            {RARITIES.map((item) => (
              <Button
                key={item}
                size='sm'
                variant={rarity === item ? 'secondary' : 'ghost'}
                aria-pressed={rarity === item}
                disabled={
                  (rarityCounts.get(item) ?? 0) === 0 && rarity !== item
                }
                disabledReason={`No ${RARITY_LABEL[item].toLowerCase()} card matches the other filters.`}
                onClick={() =>
                  reset(() =>
                    setRarity((current) => (current === item ? null : item))
                  )
                }
              >
                <span className={cn('inline-flex', RARITY_TEXT_CLASS[item])}>
                  <RarityIcon rarity={item} />
                </span>
                {`${RARITY_LABEL[item]} · ${formatInteger(rarityCounts.get(item) ?? 0)}`}
              </Button>
            ))}
          </FilterStep>
        </div>
        {cards.isError ? (
          <div className='flex min-w-0 flex-wrap items-center gap-3'>
            <Text tone='destructive'>{cards.error.message}</Text>
            <Button variant='outline' onClick={() => void cards.refetch()}>
              <RotateCcw />
              Try again
            </Button>
          </div>
        ) : cards.isPending ? (
          <div
            className='grid min-w-0 grid-cols-2 gap-5 md:grid-cols-3'
            aria-busy='true'
            aria-label='Drawing the cards'
          >
            {Array.from({ length: SKELETONS }, (_, index) => (
              <div key={index} className='lore-card-shell'>
                <Skeleton className='absolute inset-0 rounded-xl' />
              </div>
            ))}
          </div>
        ) : visible.length === 0 ? (
          filtering ? (
            <EmptyState
              size='compact'
              icon={SearchX}
              title='No card matches'
              description='Loosen the search or the filters to see more cards.'
              action={
                <Button variant='outline' onClick={clear}>
                  <X />
                  Clear the search and filters
                </Button>
              }
            />
          ) : (
            <EmptyState
              icon={WalletCards}
              title='No souls yet'
              description='Cards appear as the Creator, the children, the foreign gods and the mortals, beasts, spirits and beings of the worlds come into being.'
            />
          )
        ) : view === 'deck' ? (
          <CardDeck
            visible={visible}
            total={total}
            index={Math.min(position, visible.length - 1)}
            onIndex={setPosition}
            hasMore={cards.hasNextPage}
            loadingMore={cards.isFetchingNextPage}
            onLoadMore={loadMore}
            onOpen={setInspected}
            onDownload={(card) => download(card, 'front')}
            downloadReason={exporter.busyReason}
          />
        ) : (
          <>
            <CardBinder
              visible={visible}
              divineTotal={divineTotal}
              soulsTotal={total - divineTotal}
              onOpen={setInspected}
            />
            <div className='flex min-w-0 flex-wrap items-center justify-center gap-3'>
              {cards.hasNextPage && (
                <Button
                  variant='outline'
                  onClick={loadMore}
                  disabled={cards.isFetchingNextPage}
                  disabledReason='The next cards are being drawn.'
                >
                  {cards.isFetchingNextPage
                    ? 'Drawing more cards…'
                    : `Show ${formatInteger(Math.min(first?.limit ?? 0, total - visible.length))} more`}
                </Button>
              )}
              <Muted variant='caption'>
                {`${formatInteger(visible.length)} of ${formatInteger(total)} shown · ${plural(shownSealed, 'sealed pack', 'sealed packs')}`}
              </Muted>
            </div>
          </>
        )}
      </Section>
      <CardInspector
        visible={visible}
        index={inspected}
        total={total}
        onIndex={setInspected}
        hasMore={cards.hasNextPage}
        loadingMore={cards.isFetchingNextPage}
        onLoadMore={loadMore}
        onDownload={download}
        downloadReason={exporter.busyReason}
        worldOf={worldOf}
      />
      {exporter.layer}
    </>
  )
}

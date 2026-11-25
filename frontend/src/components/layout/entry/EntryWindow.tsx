import {
  type ComponentType,
  Fragment,
  type KeyboardEvent,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import {
  ArrowLeft,
  ArrowRight,
  ChevronRight,
  ListTree,
  Wand2,
  X,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { ENTRY_KIND_ICON, Medallion } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { SpeakWithThem } from '@/features/presence/SpeakWithThem'
import { EntryActivity } from '@/features/team/Presence'
import { isTypingTarget } from '../useGlobalShortcuts'
import { type EntryFilter, EntryRail } from './EntryRail'
import { ENTRY_CATEGORIES } from './entryCategories'
import {
  COLLAPSED_ATTR,
  type Outline,
  anchorIn,
  categoryOf,
  readOutline,
  sameOutline,
} from './entryOutline'
import { type SearchHit, clearHits, findHits, paintHits } from './entrySearch'
import {
  ENTRY_KIND_LABEL,
  type EntryKind,
  type EntryRef,
  sameEntry,
  serializeEntry,
} from './entryStack'
import { useEntryStack } from './useEntryStack'

export type EntryPageProps = {
  id?: string
}

export type EntryPages = Record<EntryKind, ComponentType<EntryPageProps>>

export const ENTRY_REVEAL = 'entry-reveal'
const FLASH_ATTR = 'data-entry-flash'
const FLASH_MS = 1400
const SEARCH_KEY = '/'
const SPY_MARGIN = '0px 0px -65% 0px'
const NARROW = '(max-width: 47.99rem)'
const OVERVIEW_FIRST_FROM = 7
const EMPTY_OUTLINE: Outline = { sections: [], title: null, kind: null }

type Stack = ReturnType<typeof useEntryStack>

function EntryFallback() {
  return (
    <div className='flex min-w-0 flex-col gap-4' aria-busy='true'>
      <Skeleton className='h-control-lg w-2/3' />
      <Skeleton className='h-textarea w-full' />
      <Skeleton className='h-textarea w-full' />
    </div>
  )
}

function nextAhead(
  before: EntryRef[],
  after: EntryRef[],
  ahead: EntryRef[]
): EntryRef[] {
  if (after.length === 0) return []
  const shrank =
    after.length < before.length &&
    after.every((entry, index) => sameEntry(entry, before[index]))
  if (shrank) return [...before.slice(after.length), ...ahead]
  const grew =
    after.length === before.length + 1 &&
    before.every((entry, index) => sameEntry(entry, after[index]))
  const pushed = after.at(-1)
  if (grew && pushed && ahead[0] && sameEntry(ahead[0], pushed))
    return ahead.slice(1)
  return []
}

function useAhead(entries: EntryRef[]) {
  const [seen, setSeen] = useState(entries)
  const [ahead, setAhead] = useState<EntryRef[]>([])
  if (seen !== entries) {
    setSeen(entries)
    setAhead(nextAhead(seen, entries, ahead))
  }
  return ahead
}

function defaultFilter(outline: Outline, at: string | undefined): EntryFilter {
  if (at) return 'all'
  const overview = outline.sections.some(
    (section) => section.category === 'overview'
  )
  return overview && outline.sections.length >= OVERVIEW_FIRST_FROM
    ? 'overview'
    : 'all'
}

type EntryBodyProps = {
  entry: EntryRef
  page: ComponentType<EntryPageProps>
  stack: Stack
  ahead: EntryRef[]
  names: ReadonlyMap<string, string>
  onTitle: (key: string, title: string) => void
}

function EntryBody({
  entry,
  page: Page,
  stack,
  ahead,
  names,
  onTitle,
}: EntryBodyProps) {
  const { entries, at } = stack
  const entryKey = serializeEntry(entry)
  const paneRef = useRef<HTMLDivElement>(null)
  const [content, setContent] = useState<HTMLDivElement | null>(null)
  const searchRef = useRef<HTMLInputElement>(null)
  const placed = useRef<string | null>(null)
  const [outline, setOutline] = useState<Outline>(EMPTY_OUTLINE)
  const [chosen, setChosen] = useState<EntryFilter | null>(null)
  const [collapsed, setCollapsed] = useState<ReadonlySet<string>>(new Set())
  const [active, setActive] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [cursor, setCursor] = useState(0)
  const [current, setCurrent] = useState<SearchHit | null>(null)
  const [railOpen, setRailOpen] = useState(false)
  const filter = chosen ?? defaultFilter(outline, at)
  const sections = outline.sections

  useEffect(() => {
    const root = content
    if (!root) return
    let frame = 0
    const read = () => {
      frame = 0
      const next = readOutline(root)
      setOutline((previous) => (sameOutline(previous, next) ? previous : next))
    }
    frame = requestAnimationFrame(read)
    const observer = new MutationObserver(() => {
      if (!frame) frame = requestAnimationFrame(read)
    })
    observer.observe(root, {
      childList: true,
      subtree: true,
      characterData: true,
    })
    return () => {
      observer.disconnect()
      if (frame) cancelAnimationFrame(frame)
    }
  }, [content])

  useEffect(() => {
    if (outline.title) onTitle(entryKey, outline.title)
  }, [entryKey, outline.title, onTitle])

  useEffect(() => {
    const root = content
    for (const section of sections) {
      const anchor = anchorIn(root, section.id)
      if (!anchor) continue
      if (collapsed.has(section.id)) anchor.setAttribute(COLLAPSED_ATTR, '')
      else anchor.removeAttribute(COLLAPSED_ATTR)
    }
  }, [content, sections, collapsed])

  useEffect(() => {
    const root = content
    const pane = paneRef.current
    if (!root || !pane || sections.length === 0) return
    const visible = new Set<string>()
    const observer = new IntersectionObserver(
      (records) => {
        for (const record of records) {
          const id = (record.target as HTMLElement).id
          if (record.isIntersecting) visible.add(id)
          else visible.delete(id)
        }
        const first = sections.find((section) => visible.has(section.id))
        if (first) setActive(first.id)
      },
      { root: pane, rootMargin: SPY_MARGIN }
    )
    for (const section of sections) {
      const anchor = anchorIn(root, section.id)
      if (anchor) observer.observe(anchor)
    }
    return () => observer.disconnect()
  }, [content, sections, filter])

  const land = useCallback(
    (id: string, then?: () => void) => {
      requestAnimationFrame(() =>
        requestAnimationFrame(() => {
          const anchor = anchorIn(content, id)
          if (!anchor) return
          if (then) {
            then()
            return
          }
          anchor.scrollIntoView({ block: 'start' })
          anchor.setAttribute(FLASH_ATTR, '')
          window.setTimeout(() => anchor.removeAttribute(FLASH_ATTR), FLASH_MS)
        })
      )
    },
    [content]
  )

  const reveal = useCallback(
    (id: string, then?: () => void) => {
      const category = categoryOf(id)
      setChosen((previous) => {
        const now = previous ?? defaultFilter(outline, at)
        return now === 'all' || now === category ? now : category
      })
      setCollapsed((previous) => {
        if (!previous.has(id)) return previous
        const next = new Set(previous)
        next.delete(id)
        return next
      })
      setRailOpen(false)
      setActive(id)
      land(id, then)
    },
    [outline, at, land]
  )

  const jump = useCallback(
    (id: string) => {
      reveal(id)
      void stack.showSection(id)
    },
    [reveal, stack]
  )

  useEffect(() => {
    if (!at || placed.current === at) return
    if (!sections.some((section) => section.id === at)) return
    placed.current = at
    land(at)
  }, [at, sections, land])

  useEffect(() => {
    const root = content
    if (!root) return
    const listen = (event: Event) => {
      const id = (event as CustomEvent<string>).detail
      if (typeof id === 'string') reveal(id)
    }
    root.addEventListener(ENTRY_REVEAL, listen)
    return () => root.removeEventListener(ENTRY_REVEAL, listen)
  }, [reveal, content])

  const hits = useMemo(
    () => (outline === EMPTY_OUTLINE ? [] : findHits(content, query)),
    [content, query, outline]
  )

  useEffect(() => {
    paintHits(hits, current && hits.includes(current) ? current : null)
  }, [hits, current])

  useEffect(() => () => clearHits(), [])

  useEffect(() => {
    const pane = paneRef.current
    if (pane) pane.scrollTop = 0
  }, [filter])

  const pick = useCallback(
    (hit: SearchHit) => {
      setCursor(Math.max(0, hits.indexOf(hit)))
      setCurrent(hit)
      const show = () =>
        hit.range.startContainer.parentElement?.scrollIntoView({
          block: 'center',
        })
      if (hit.sectionId) reveal(hit.sectionId, show)
      else requestAnimationFrame(show)
    },
    [hits, reveal]
  )

  const keys = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === SEARCH_KEY && !isTypingTarget(event.target)) {
      event.preventDefault()
      setRailOpen(true)
      requestAnimationFrame(() => searchRef.current?.focus())
    }
  }

  useEffect(() => {
    if (!query && !railOpen) return
    const close = (event: globalThis.KeyboardEvent) => {
      if (event.key !== 'Escape') return
      if (!query && !window.matchMedia(NARROW).matches) return
      event.preventDefault()
      event.stopPropagation()
      if (query) {
        setQuery('')
        setCurrent(null)
      } else setRailOpen(false)
    }
    window.addEventListener('keydown', close, true)
    return () => window.removeEventListener('keydown', close, true)
  }, [query, railOpen])

  const controls = sections.find((section) => section.category === 'control')
  const kindLabel = outline.kind ?? ENTRY_KIND_LABEL[entry.kind]
  const title = names.get(entryKey) ?? kindLabel
  const filterInfo = ENTRY_CATEGORIES.find(
    (category) => category.key === filter
  )
  const counted =
    filter === 'all'
      ? sections.length
      : sections.filter((section) => section.category === filter).length

  return (
    <div
      className='flex min-h-0 min-w-0 flex-1 flex-col'
      onKeyDownCapture={keys}
    >
      <header
        data-layout='entry-header'
        className='relative flex min-h-topbar shrink-0 items-center gap-2 px-2 py-2 sm:gap-3 sm:px-3'
      >
        <div className='flex shrink-0 items-center gap-1'>
          <Button
            variant='ghost'
            size='icon'
            aria-label='Back'
            title={
              entries.length > 1
                ? 'Back to the entry this was opened from'
                : 'Nothing to go back to in this window'
            }
            disabled={entries.length <= 1}
            onClick={() => void stack.back()}
          >
            <ArrowLeft />
          </Button>
          <Button
            variant='ghost'
            size='icon'
            aria-label='Forward'
            title={
              ahead.length > 0
                ? 'Forward to the entry you came back from'
                : 'Nothing ahead to go forward to'
            }
            disabled={ahead.length === 0}
            onClick={() => ahead[0] && void stack.open(ahead[0])}
          >
            <ArrowRight />
          </Button>
        </div>
        <span className='flex shrink-0 max-sm:hidden'>
          <Medallion icon={ENTRY_KIND_ICON[entry.kind]} tone='gold' size='sm' />
        </span>
        <div className='flex min-w-0 flex-1 flex-col'>
          {entries.length > 1 && (
            <nav
              aria-label='Opened entries'
              className='flex min-w-0 items-center gap-1 overflow-hidden'
            >
              {entries.slice(0, -1).map((item, index) => {
                const key = serializeEntry(item)
                return (
                  <Fragment key={`${key}-${index}`}>
                    <Button
                      variant='link'
                      size='sm'
                      className='min-w-0 shrink px-0 text-muted-foreground'
                      onClick={() => void stack.truncate(index + 1)}
                    >
                      <span className='min-w-0 truncate'>
                        {names.get(key) ?? ENTRY_KIND_LABEL[item.kind]}
                      </span>
                    </Button>
                    <ChevronRight
                      aria-hidden='true'
                      className='size-icon-sm shrink-0 text-muted-foreground'
                    />
                  </Fragment>
                )
              })}
            </nav>
          )}
          {entries.length <= 1 && title !== kindLabel && (
            <Label variant='overline' truncate>
              {kindLabel}
            </Label>
          )}
          <DialogTitle className='min-w-0 truncate text-gilded font-display'>
            {title}
          </DialogTitle>
          <DialogDescription className='sr-only'>
            {`The whole entry in parts, with its own search, ${plural(sections.length, 'section')}.`}
          </DialogDescription>
        </div>
        <div className='flex shrink-0 items-center gap-1'>
          <Button
            variant='ghost'
            size='icon'
            className='md:hidden'
            aria-label={
              railOpen ? 'Hide the contents' : 'Show the contents and search'
            }
            aria-expanded={railOpen}
            onClick={() => setRailOpen((open) => !open)}
          >
            <ListTree />
          </Button>
          <EntryActivity nodeId={entryNodeId(entry)} />
          <SpeakWithThem entry={entry} />
          <Button
            variant='outline'
            size='sm'
            disabled={!controls}
            title={
              controls
                ? 'Jump to every lever the god holds over this entry'
                : 'This entry has no god controls of its own'
            }
            onClick={() => {
              if (!controls) return
              setChosen('control')
              jump(controls.id)
            }}
          >
            <Wand2 />
            <span className='max-sm:sr-only'>God&apos;s controls</span>
          </Button>
          <DialogClose asChild>
            <Button variant='ghost' size='icon' aria-label='Close'>
              <X />
            </Button>
          </DialogClose>
        </div>
      </header>
      <div className='relative flex min-h-0 flex-1'>
        <aside
          data-layout='entry-rail'
          aria-label='Contents and search'
          className={cn(
            'relative flex w-entry-rail shrink-0 flex-col max-md:absolute max-md:inset-0 max-md:z-10 max-md:w-full',
            !railOpen && 'max-md:hidden'
          )}
        >
          <EntryRail
            sections={sections}
            filter={filter}
            onFilter={(next) => {
              setChosen(next)
              setRailOpen(false)
            }}
            active={active}
            onJump={jump}
            collapsed={collapsed}
            onCollapse={(id, fold) =>
              setCollapsed((previous) => {
                const next = new Set(previous)
                if (fold) next.add(id)
                else next.delete(id)
                return next
              })
            }
            onCollapseMany={(ids, fold) =>
              setCollapsed((previous) => {
                const next = new Set(previous)
                for (const id of ids) {
                  if (fold) next.add(id)
                  else next.delete(id)
                }
                return next
              })
            }
            query={query}
            onQuery={(next) => {
              setQuery(next)
              setCursor(0)
              setCurrent(null)
            }}
            hits={hits}
            cursor={cursor}
            onCursor={setCursor}
            onPick={pick}
            searchRef={searchRef}
          />
        </aside>
        <div
          ref={paneRef}
          tabIndex={-1}
          className='min-h-0 min-w-0 flex-1 overflow-y-auto outline-none'
        >
          <div className='flex min-w-0 flex-col gap-6 p-4 md:p-6'>
            {filterInfo && (
              <div className='flex min-w-0 items-center gap-3'>
                <Medallion
                  icon={filterInfo.icon}
                  tone={filterInfo.key === 'control' ? 'verdigris' : 'gold'}
                  size='sm'
                />
                <div className='flex min-w-0 flex-col'>
                  <Label variant='gilded'>{filterInfo.label}</Label>
                  <Muted variant='caption'>{`${filterInfo.hint} · ${plural(counted, 'section')}`}</Muted>
                </div>
              </div>
            )}
            <div
              ref={setContent}
              data-entry-filter={filter}
              className='flex min-w-0 flex-col gap-6'
            >
              <Suspense fallback={<EntryFallback />}>
                <Page id={entry.id} />
              </Suspense>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const NOT_NODES: ReadonlySet<EntryRef['kind']> = new Set([
  'world-guide',
  'help',
  'incident',
])

function entryNodeId(entry: EntryRef): number | null {
  if (NOT_NODES.has(entry.kind) || entry.id === undefined) return null
  const id = Number(entry.id)
  return Number.isInteger(id) && id > 0 ? id : null
}

export function EntryWindow({ pages }: { pages: EntryPages }) {
  const stack = useEntryStack()
  const { entries, top } = stack
  const ahead = useAhead(entries)
  const [names, setNames] = useState<ReadonlyMap<string, string>>(new Map())
  const onTitle = useCallback(
    (key: string, title: string) =>
      setNames((previous) =>
        previous.get(key) === title
          ? previous
          : new Map(previous).set(key, title)
      ),
    []
  )
  return (
    <Dialog
      open={top !== undefined}
      onOpenChange={(open) => !open && void stack.close()}
    >
      <DialogContent
        showCloseButton={false}
        data-layout='entry'
        className='flex h-entry-tall max-h-none w-entry max-w-none flex-col gap-0 overflow-hidden p-0 max-md:inset-0 max-md:h-dvh max-md:w-screen max-md:translate-x-0 max-md:translate-y-0 max-md:rounded-none sm:max-w-none'
        onOpenAutoFocus={(event) => event.preventDefault()}
      >
        {top && (
          <EntryBody
            key={serializeEntry(top)}
            entry={top}
            page={pages[top.kind]}
            stack={stack}
            ahead={ahead}
            names={names}
            onTitle={onTitle}
          />
        )}
      </DialogContent>
    </Dialog>
  )
}

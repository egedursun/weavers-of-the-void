import { type KeyboardEvent, type RefObject, useMemo, useState } from 'react'
import {
  ChevronDown,
  ChevronRight,
  ChevronsDownUp,
  ChevronsUpDown,
  Layers,
  Minus,
  Plus,
  Search,
  SearchX,
} from 'lucide-react'
import { agree, plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Kbd } from '@/components/ui/kbd'
import { Label, Muted, Text } from '@/components/typography'
import { ENTRY_CATEGORIES, type EntryCategory } from './entryCategories'
import { type OutlineSection } from './entryOutline'
import { type SearchHit, HIT_LIMIT } from './entrySearch'

export type EntryFilter = EntryCategory | 'all'

const HITS_SHOWN = 60
const HITS_PER_SECTION = 4

type HitGroup = { sectionId: string | null; label: string; hits: SearchHit[] }

function groupHits(hits: SearchHit[], labels: Map<string, string>): HitGroup[] {
  const groups = new Map<string, HitGroup>()
  for (const hit of hits) {
    const key = hit.sectionId ?? ''
    const group = groups.get(key) ?? {
      sectionId: hit.sectionId,
      label: hit.sectionId
        ? (labels.get(hit.sectionId) ?? 'A section')
        : 'At the head of the entry',
      hits: [],
    }
    group.hits.push(hit)
    groups.set(key, group)
  }
  return [...groups.values()]
}

type EntryRailProps = {
  sections: OutlineSection[]
  filter: EntryFilter
  onFilter: (filter: EntryFilter) => void
  active: string | null
  onJump: (id: string) => void
  collapsed: ReadonlySet<string>
  onCollapse: (id: string, collapsed: boolean) => void
  onCollapseMany: (ids: string[], collapsed: boolean) => void
  query: string
  onQuery: (query: string) => void
  hits: SearchHit[]
  cursor: number
  onCursor: (cursor: number) => void
  onPick: (hit: SearchHit) => void
  searchRef: RefObject<HTMLInputElement | null>
}

export function EntryRail({
  sections,
  filter,
  onFilter,
  active,
  onJump,
  collapsed,
  onCollapse,
  onCollapseMany,
  query,
  onQuery,
  hits,
  cursor,
  onCursor,
  onPick,
  searchRef,
}: EntryRailProps) {
  const [unfolded, setUnfolded] = useState<ReadonlySet<EntryCategory>>(
    new Set()
  )
  const [folded, setFolded] = useState<ReadonlySet<EntryCategory>>(new Set())
  const [shown, setShown] = useState(HITS_SHOWN)
  const labels = useMemo(
    () => new Map(sections.map((section) => [section.id, section.label])),
    [sections]
  )
  const present = useMemo(
    () =>
      ENTRY_CATEGORIES.map((category) => ({
        ...category,
        sections: sections.filter(
          (section) => section.category === category.key
        ),
      })).filter((category) => category.sections.length > 0),
    [sections]
  )
  const activeCategory = sections.find(
    (section) => section.id === active
  )?.category
  const visibleIds = (
    filter === 'all'
      ? sections
      : sections.filter((section) => section.category === filter)
  ).map((section) => section.id)
  const titleMatches = query.trim()
    ? sections.filter((section) =>
        section.label
          .toLocaleLowerCase()
          .includes(query.trim().toLocaleLowerCase())
      )
    : []
  const listed = hits.slice(0, shown)
  const groups = groupHits(listed, labels)
  const searching = query.trim().length > 0
  const isOpen = (key: EntryCategory) =>
    unfolded.has(key) ||
    (!folded.has(key) &&
      (key === filter || (filter === 'all' && key === activeCategory)))
  const toggle = (key: EntryCategory) => {
    const open = isOpen(key)
    const without = (current: ReadonlySet<EntryCategory>) =>
      new Set([...current].filter((item) => item !== key))
    const withIt = (current: ReadonlySet<EntryCategory>) =>
      new Set([...current, key])
    setUnfolded(open ? without : withIt)
    setFolded(open ? withIt : without)
  }
  const keys = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown' && listed.length > 0) {
      event.preventDefault()
      onCursor(Math.min(listed.length - 1, cursor + 1))
    } else if (event.key === 'ArrowUp' && listed.length > 0) {
      event.preventDefault()
      onCursor(Math.max(0, cursor - 1))
    } else if (event.key === 'Enter' && listed[cursor]) {
      event.preventDefault()
      onPick(listed[cursor])
    }
  }
  return (
    <nav
      aria-label='Contents of this entry'
      className='flex min-h-0 min-w-0 flex-1 flex-col'
    >
      <div className='flex min-w-0 flex-col gap-2 p-3'>
        <div className='relative flex min-w-0 items-center'>
          <Search
            aria-hidden='true'
            className='pointer-events-none absolute inset-s-2.5 size-icon-sm text-muted-foreground'
          />
          <Input
            ref={searchRef}
            type='search'
            value={query}
            aria-label='Search this entry'
            placeholder='Search this entry'
            className='ps-8 pe-9'
            onChange={(event) => {
              onQuery(event.target.value)
              setShown(HITS_SHOWN)
            }}
            onKeyDown={keys}
          />
          {!query && <Kbd className='absolute inset-e-2.5'>/</Kbd>}
        </div>
        {searching ? (
          <Muted variant='caption' aria-live='polite'>
            {hits.length === 0
              ? 'Nothing in this entry matches'
              : `${hits.length >= HIT_LIMIT ? `${HIT_LIMIT}+ ${agree(hits.length, 'match', 'matches')}` : plural(hits.length, 'match', 'matches')} in ${plural(groups.length, 'place')} · ↑↓ to move, Enter to jump`}
          </Muted>
        ) : (
          <Muted variant='caption'>{`${plural(sections.length, 'section')} in ${plural(present.length, 'part')}`}</Muted>
        )}
      </div>
      <div className='min-h-0 flex-1 overflow-y-auto px-2 pb-3'>
        {searching ? (
          <div
            role='listbox'
            aria-label='Matches'
            className='flex min-w-0 flex-col gap-3'
          >
            {titleMatches.length > 0 && (
              <div className='flex min-w-0 flex-col gap-1'>
                <Label variant='overline' className='px-2'>
                  Sections
                </Label>
                {titleMatches.map((section) => (
                  <Button
                    key={section.id}
                    variant='ghost'
                    size='sm'
                    className='w-full justify-start'
                    onClick={() => onJump(section.id)}
                  >
                    <Layers />
                    <span className='min-w-0 flex-1 truncate text-start'>
                      {section.label}
                    </span>
                  </Button>
                ))}
              </div>
            )}
            {hits.length === 0 && titleMatches.length === 0 && (
              <div className='flex min-w-0 flex-col items-center gap-2 px-3 py-6 text-center'>
                <SearchX
                  aria-hidden='true'
                  className='size-icon-lg text-muted-foreground'
                />
                <Text variant='caption' tone='muted'>
                  Try another word; the search reads every label, value and line
                  of this entry.
                </Text>
              </div>
            )}
            {groups.map((group) => (
              <div
                key={group.sectionId ?? 'head'}
                className='flex min-w-0 flex-col gap-1'
              >
                <Label variant='overline' className='px-2' truncate>
                  {`${group.label} · ${group.hits.length}`}
                </Label>
                {group.hits.slice(0, HITS_PER_SECTION).map((hit) => {
                  const index = listed.indexOf(hit)
                  const current = index === cursor
                  return (
                    <Button
                      key={hit.key}
                      role='option'
                      aria-selected={current}
                      variant='ghost'
                      size='stage'
                      className={cn(
                        'items-start px-2 text-start',
                        current && 'plate-chosen'
                      )}
                      onClick={() => onPick(hit)}
                      onMouseEnter={() => onCursor(index)}
                    >
                      <Text
                        as='span'
                        variant='caption'
                        tone='muted'
                        className='line-clamp-2 wrap-anywhere'
                      >
                        {hit.before}
                        <mark className='rounded-sm bg-primary/25 text-foreground'>
                          {hit.match}
                        </mark>
                        {hit.after}
                      </Text>
                    </Button>
                  )
                })}
                {group.hits.length > HITS_PER_SECTION && group.sectionId && (
                  <Button
                    variant='link'
                    size='sm'
                    className='self-start'
                    onClick={() => onPick(group.hits[HITS_PER_SECTION])}
                  >
                    {`${group.hits.length - HITS_PER_SECTION} more here`}
                  </Button>
                )}
              </div>
            ))}
            {hits.length > shown && (
              <Button
                variant='outline'
                size='sm'
                onClick={() => setShown((count) => count + HITS_SHOWN)}
              >
                {`Show ${plural(Math.min(HITS_SHOWN, hits.length - shown), 'more match', 'more matches')}`}
              </Button>
            )}
          </div>
        ) : (
          <div className='flex min-w-0 flex-col gap-1'>
            <Button
              variant='ghost'
              className={cn(
                'w-full justify-start',
                filter === 'all' && 'plate-chosen'
              )}
              aria-pressed={filter === 'all'}
              onClick={() => onFilter('all')}
            >
              <Layers />
              <span className='min-w-0 flex-1 truncate text-start'>
                Everything
              </span>
              <Badge variant='outline' size='sm'>
                {sections.length}
              </Badge>
            </Button>
            {present.map((category) => {
              const open = isOpen(category.key)
              const Icon = category.icon
              return (
                <div key={category.key} className='flex min-w-0 flex-col gap-1'>
                  <div className='flex min-w-0 items-center gap-1'>
                    <Button
                      variant='ghost'
                      size='icon-sm'
                      aria-label={
                        open
                          ? `Fold ${category.label}`
                          : `Unfold ${category.label}`
                      }
                      aria-expanded={open}
                      onClick={() => toggle(category.key)}
                    >
                      {open ? <ChevronDown /> : <ChevronRight />}
                    </Button>
                    <Button
                      variant='ghost'
                      title={category.hint}
                      aria-pressed={filter === category.key}
                      className={cn(
                        'min-w-0 flex-1 justify-start',
                        filter === category.key && 'plate-chosen'
                      )}
                      onClick={() => onFilter(category.key)}
                    >
                      <Icon />
                      <span className='min-w-0 flex-1 truncate text-start'>
                        {category.label}
                      </span>
                      <Badge
                        variant={
                          category.key === 'control' ? 'default' : 'outline'
                        }
                        size='sm'
                      >
                        {category.sections.length}
                      </Badge>
                    </Button>
                  </div>
                  {open && (
                    <div className='min-w-0 ps-9 pb-1'>
                      <ul
                        className='flex min-w-0 flex-col gap-0.5 border-s border-gild/30 ps-2'
                        aria-label={category.label}
                      >
                        {category.sections.map((section) => {
                          const folded = collapsed.has(section.id)
                          const here = section.id === active
                          return (
                            <li
                              key={section.id}
                              className='flex min-w-0 items-center gap-1'
                            >
                              <Button
                                variant='ghost'
                                size='sm'
                                aria-current={here ? 'location' : undefined}
                                className={cn(
                                  'min-w-0 flex-1 justify-start font-normal',
                                  here
                                    ? 'text-primary'
                                    : 'text-muted-foreground'
                                )}
                                onClick={() => onJump(section.id)}
                              >
                                <span
                                  aria-hidden='true'
                                  className={cn(
                                    'size-1.5 shrink-0 rounded-full',
                                    here ? 'bg-primary' : 'bg-border'
                                  )}
                                />
                                <span className='min-w-0 flex-1 truncate text-start'>
                                  {section.label}
                                </span>
                              </Button>
                              <Button
                                variant='ghost'
                                size='icon-sm'
                                aria-label={
                                  folded
                                    ? `Unfold ${section.label}`
                                    : `Fold ${section.label}`
                                }
                                aria-pressed={folded}
                                onClick={() => onCollapse(section.id, !folded)}
                              >
                                {folded ? <Plus /> : <Minus />}
                              </Button>
                            </li>
                          )
                        })}
                      </ul>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
      {!searching && visibleIds.length > 1 && (
        <div className='flex min-w-0 gap-2 border-t border-gild/30 p-3'>
          <Button
            variant='outline'
            size='sm'
            className='flex-1'
            onClick={() => onCollapseMany(visibleIds, true)}
          >
            <ChevronsDownUp />
            Fold all
          </Button>
          <Button
            variant='outline'
            size='sm'
            className='flex-1'
            onClick={() => onCollapseMany(visibleIds, false)}
          >
            <ChevronsUpDown />
            Unfold all
          </Button>
        </div>
      )}
    </nav>
  )
}

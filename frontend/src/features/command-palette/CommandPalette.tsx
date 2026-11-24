import { useCallback, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { GENESIS_ITEM, NAV_GROUPS, type NavItem } from '@/config/navigation'
import {
  Activity,
  Archive,
  CheckCheck,
  CircleHelp,
  Hourglass,
  Laptop,
  Moon,
  Search,
  Square,
  Star,
  Sun,
  Zap,
} from 'lucide-react'
import { toast } from 'sonner'
import { useSearch } from '@/context/searchContext'
import { type Theme, useTheme } from '@/context/themeContext'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from '@/components/ui/command'
import { useEntryStack } from '@/components/layout/entry/useEntryStack'
import { useTakeBackup } from '@/features/backups/api'
import { useNameIndex } from '@/features/chronicle/linkTargets'
import { useCompleteEpoch, useStopEpoch } from '@/features/epoch/api'
import { useFeedDock } from '@/features/feed/useFeedDock'
import { NodeAvatar } from '@/features/images/NodeAvatar'
import { useFavorites } from '@/features/ledger/api'
import { useMarkRead } from '@/features/notifications/api'
import { ActionDialog } from './ActionDialog'
import {
  type ActionItem,
  SEARCH_MIN_LENGTH,
  useActionCatalogue,
  useWorldSearch,
} from './api'
import { HIT_ICON, HIT_LABEL, useHitRouter } from './searchRouting'

const NODE_CATEGORIES: ReadonlySet<string> = new Set([
  'son',
  'foreign_god',
  'world',
  'star',
  'entity',
])

const THEME_COMMANDS: { theme: Theme; label: string; icon: typeof Sun }[] = [
  { theme: 'light', label: 'Light theme', icon: Sun },
  { theme: 'dark', label: 'Dark theme', icon: Moon },
  { theme: 'system', label: 'System theme', icon: Laptop },
]

const COMMAND_PLACEHOLDER = 'Search the world, a screen or an action'

function report(promise: Promise<unknown>, message: string) {
  promise
    .then(() => toast.success(message))
    .catch((error: unknown) =>
      toast.error(error instanceof Error ? error.message : String(error))
    )
}

export function CommandPalette() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { setTheme } = useTheme()
  const { open, setOpen } = useSearch()
  const entryStack = useEntryStack()
  const [query, setQuery] = useState('')
  const [action, setAction] = useState<ActionItem | null>(null)
  const actions = useActionCatalogue(open)
  const favorites = useFavorites()
  const { search } = useWorldSearch(query)
  const routeHit = useHitRouter()
  const complete = useCompleteEpoch()
  const stop = useStopEpoch()
  const backup = useTakeBackup()
  const markRead = useMarkRead()
  const { setOpen: setFeedOpen } = useFeedDock()
  const names = useNameIndex()

  const close = useCallback(
    (next: boolean) => {
      setOpen(next)
      if (!next) setQuery('')
    },
    [setOpen]
  )

  const run = useCallback(
    (command: () => unknown) => {
      close(false)
      command()
    },
    [close]
  )

  const goTo = (item: NavItem) => run(() => navigate({ to: item.to }))
  const searching = query.trim().length >= SEARCH_MIN_LENGTH
  const hits = searching ? (search.data ?? []) : []

  return (
    <>
      <CommandDialog
        open={open}
        onOpenChange={close}
        title='Command palette'
        description='Search the world, jump to a screen or run any action'
      >
        <CommandInput
          placeholder={COMMAND_PLACEHOLDER}
          value={query}
          onValueChange={setQuery}
        />
        <CommandList>
          <CommandEmpty>
            {searching && search.isFetching
              ? 'Searching…'
              : `Nothing matches “${query}”.`}
          </CommandEmpty>
          {hits.length > 0 && (
            <CommandGroup heading='In the world'>
              {hits.map((hit) => {
                const Icon = HIT_ICON[hit.category]
                const pictured =
                  NODE_CATEGORIES.has(hit.category) &&
                  Boolean(names.get(hit.id)?.cover)
                return (
                  <CommandItem
                    key={`${hit.category}-${hit.id}-${hit.epoch ?? ''}`}
                    value={`${query} ${hit.title} ${hit.subtitle ?? ''} ${hit.category}-${hit.id}`}
                    onSelect={() => run(() => routeHit(hit))}
                  >
                    {pictured ? (
                      <NodeAvatar id={hit.id} name={hit.title} />
                    ) : (
                      <Icon />
                    )}
                    <span className='flex min-w-0 flex-1 flex-col'>
                      <span className='truncate'>{hit.title}</span>
                      {(hit.subtitle || hit.snippet) && (
                        <span className='truncate text-muted-foreground'>
                          {hit.subtitle ?? hit.snippet}
                        </span>
                      )}
                    </span>
                    <CommandShortcut>{HIT_LABEL[hit.category]}</CommandShortcut>
                  </CommandItem>
                )
              })}
            </CommandGroup>
          )}
          {!searching && (favorites.data ?? []).length > 0 && (
            <CommandGroup heading='Favourites'>
              {(favorites.data ?? []).map((item) => (
                <CommandItem
                  key={`favorite-${item.id}`}
                  value={`favourite ${item.name}`}
                  onSelect={() =>
                    run(() =>
                      entryStack.open({ kind: 'entity', id: String(item.id) })
                    )
                  }
                >
                  <Star />
                  <span className='min-w-0 flex-1 truncate'>{item.name}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          )}
          <CommandGroup heading='Run the world'>
            <CommandItem
              value='Complete the epoch resume'
              onSelect={() =>
                run(() => report(complete.mutateAsync(), 'The epoch begins'))
              }
            >
              <Hourglass />
              <span className='min-w-0 flex-1 truncate'>
                Complete the epoch
              </span>
            </CommandItem>
            <CommandItem
              value='Stop the epoch at a safe point'
              onSelect={() =>
                run(() =>
                  report(
                    stop.mutateAsync(),
                    'The epoch stops at the next safe point'
                  )
                )
              }
            >
              <Square />
              <span className='min-w-0 flex-1 truncate'>Stop the epoch</span>
            </CommandItem>
            <CommandItem
              value='Open the live feed'
              onSelect={() => run(() => setFeedOpen(true))}
            >
              <Activity />
              <span className='min-w-0 flex-1 truncate'>
                Open the live feed
              </span>
            </CommandItem>
            <CommandItem
              value='Take a backup now'
              onSelect={() =>
                run(() => report(backup.mutateAsync(), 'Backup taken'))
              }
            >
              <Archive />
              <span className='min-w-0 flex-1 truncate'>Take a backup now</span>
            </CommandItem>
            <CommandItem
              value='Mark all notifications read'
              onSelect={() =>
                run(() =>
                  report(
                    markRead.mutateAsync({ every: true, unread: false }),
                    'Every notification is read'
                  )
                )
              }
            >
              <CheckCheck />
              <span className='min-w-0 flex-1 truncate'>
                Mark all notifications read
              </span>
            </CommandItem>
          </CommandGroup>
          {(actions.data ?? []).length > 0 && (
            <CommandGroup heading='Actions'>
              {(actions.data ?? []).map((item) => (
                <CommandItem
                  key={item.id}
                  value={`action ${item.title} ${item.id} ${item.group}`}
                  onSelect={() => run(() => setAction(item))}
                >
                  <Zap />
                  <span className='min-w-0 flex-1 truncate'>{item.title}</span>
                  <CommandShortcut>{item.cost}</CommandShortcut>
                </CommandItem>
              ))}
            </CommandGroup>
          )}
          {NAV_GROUPS.map((group) => (
            <CommandGroup key={group.title} heading={group.title}>
              {group.items
                .flatMap((item) => [item, ...(item.children ?? [])])
                .map((item) => (
                  <CommandItem
                    key={item.id}
                    value={`${item.title} ${item.description}`}
                    onSelect={() => goTo(item)}
                  >
                    <item.icon />
                    <span className='min-w-0 flex-1 truncate'>
                      {item.title}
                    </span>
                    {item.shortcut && (
                      <CommandShortcut>{item.shortcut}</CommandShortcut>
                    )}
                  </CommandItem>
                ))}
            </CommandGroup>
          ))}
          <CommandSeparator />
          <CommandGroup heading='Interface'>
            <CommandItem
              value={`${GENESIS_ITEM.title} ${GENESIS_ITEM.description}`}
              onSelect={() => goTo(GENESIS_ITEM)}
            >
              <GENESIS_ITEM.icon />
              <span className='min-w-0 flex-1 truncate'>
                {GENESIS_ITEM.title}
              </span>
            </CommandItem>
            <CommandItem
              value='Help shortcuts glossary terms'
              onSelect={() => run(() => entryStack.open({ kind: 'help' }))}
            >
              <CircleHelp />
              <span className='min-w-0 flex-1 truncate'>Help</span>
              <CommandShortcut>?</CommandShortcut>
            </CommandItem>
            <CommandItem
              value='Refresh everything reload data'
              onSelect={() => run(() => void queryClient.invalidateQueries())}
            >
              <Search />
              <span className='min-w-0 flex-1 truncate'>
                Refresh every view
              </span>
            </CommandItem>
            {THEME_COMMANDS.map((command) => (
              <CommandItem
                key={command.theme}
                value={command.label}
                onSelect={() => run(() => setTheme(command.theme))}
              >
                <command.icon />
                <span className='min-w-0 flex-1 truncate'>{command.label}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </CommandDialog>
      <ActionDialog action={action} onClose={() => setAction(null)} />
    </>
  )
}

import { useCallback, useMemo } from 'react'
import { useNavigate, useSearch } from '@tanstack/react-router'
import {
  type DrawerEntry,
  type DrawerSearch,
  parseDrawerStack,
  pushDrawerEntry,
  serializeDrawerStack,
} from './drawerEntries'

export function drawerSearchWith(
  search: DrawerSearch,
  entries: DrawerEntry[]
): DrawerSearch {
  const drawer = serializeDrawerStack(entries)
  const rest = { ...search }
  delete rest.drawer
  return drawer === undefined ? rest : { ...rest, drawer }
}

export function useDrawerStack() {
  const search = useSearch({ strict: false }) as DrawerSearch
  const navigate = useNavigate()
  const entries = useMemo(
    () => parseDrawerStack(search.drawer),
    [search.drawer]
  )

  const update = useCallback(
    (next: (current: DrawerEntry[]) => DrawerEntry[]) =>
      navigate({
        to: '.',
        search: (previous: DrawerSearch) =>
          drawerSearchWith(previous, next(parseDrawerStack(previous.drawer))),
      }),
    [navigate]
  )

  const open = useCallback(
    (entry: DrawerEntry) =>
      update((current) => pushDrawerEntry(current, entry)),
    [update]
  )
  const replace = useCallback(
    (entry: DrawerEntry) => update(() => [entry]),
    [update]
  )
  const back = useCallback(
    () => update((current) => current.slice(0, -1)),
    [update]
  )
  const close = useCallback(() => update(() => []), [update])

  return { entries, top: entries.at(-1), open, replace, back, close }
}

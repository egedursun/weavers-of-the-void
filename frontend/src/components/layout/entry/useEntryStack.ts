import { useCallback, useMemo } from 'react'
import { useNavigate, useSearch } from '@tanstack/react-router'
import {
  type EntryRef,
  type EntrySearch,
  parseEntryStack,
  pushEntry,
  serializeEntryStack,
} from './entryStack'

export function entrySearchWith(
  search: EntrySearch,
  entries: EntryRef[]
): EntrySearch {
  const entry = serializeEntryStack(entries)
  const rest = { ...search }
  delete rest.entry
  delete rest.at
  return entry === undefined ? rest : { ...rest, entry }
}

export function useEntryStack() {
  const search = useSearch({ strict: false }) as EntrySearch
  const navigate = useNavigate()
  const entries = useMemo(() => parseEntryStack(search.entry), [search.entry])

  const update = useCallback(
    (next: (current: EntryRef[]) => EntryRef[]) =>
      navigate({
        to: '.',
        search: (previous: EntrySearch) =>
          entrySearchWith(previous, next(parseEntryStack(previous.entry))),
      }),
    [navigate]
  )

  const open = useCallback(
    (entry: EntryRef) => update((current) => pushEntry(current, entry)),
    [update]
  )
  const replace = useCallback(
    (entry: EntryRef) => update(() => [entry]),
    [update]
  )
  const back = useCallback(
    () => update((current) => current.slice(0, -1)),
    [update]
  )
  const close = useCallback(() => update(() => []), [update])
  const truncate = useCallback(
    (depth: number) => update((current) => current.slice(0, depth)),
    [update]
  )
  const showSection = useCallback(
    (at: string | undefined) =>
      navigate({
        to: '.',
        replace: true,
        search: (previous: EntrySearch) => {
          const rest = { ...previous }
          delete rest.at
          return at === undefined ? rest : { ...rest, at }
        },
      }),
    [navigate]
  )

  return {
    entries,
    top: entries.at(-1),
    at: search.at,
    open,
    replace,
    back,
    close,
    truncate,
    showSection,
  }
}

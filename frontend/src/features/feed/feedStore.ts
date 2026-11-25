import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import {
  type ViewerStorageKey,
  followViewer,
  viewerPersisted,
} from '@/lib/universeStorage'
import {
  type FeedActorFilter,
  type FeedCategory,
  type FeedLine,
  appendLines,
  closeOpenStreams,
} from './feedModel'

type FeedStore = {
  lines: FeedLine[]
  restored: boolean
  actor: FeedActorFilter
  categories: FeedCategory[]
  expanded: string[]
  add: (lines: FeedLine[]) => void
  closeOpen: () => void
  restore: (lines: FeedLine[]) => void
  setActor: (actor: FeedActorFilter) => void
  toggleCategory: (category: FeedCategory) => void
  clearCategories: () => void
  toggleGroup: (key: string) => void
  clear: () => void
}

export const useFeed = create<FeedStore>((set) => ({
  lines: [],
  restored: false,
  actor: 'all',
  categories: [],
  expanded: [],
  add: (lines) => set((state) => ({ lines: appendLines(state.lines, lines) })),
  closeOpen: () => set((state) => ({ lines: closeOpenStreams(state.lines) })),
  restore: (lines) =>
    set((state) => ({
      lines: appendLines(state.lines, lines),
      restored: true,
    })),
  setActor: (actor) => set({ actor }),
  toggleCategory: (category) =>
    set((state) => ({
      categories: state.categories.includes(category)
        ? state.categories.filter((item) => item !== category)
        : [...state.categories, category],
    })),
  clearCategories: () => set({ categories: [] }),
  toggleGroup: (key) =>
    set((state) => ({
      expanded: state.expanded.includes(key)
        ? state.expanded.filter((item) => item !== key)
        : [...state.expanded, key],
    })),
  clear: () => set({ lines: [], expanded: [] }),
}))

type FeedPreferences = {
  open: boolean | null
  sounds: boolean
  ambient: boolean
  muted: FeedCategory[]
  setOpen: (open: boolean) => void
  setSounds: (sounds: boolean) => void
  setAmbient: (ambient: boolean) => void
  toggleMuted: (category: FeedCategory) => void
}

export const FEED_PREFERENCES_KEY: ViewerStorageKey = 'aerona.feed'

export const useFeedPreferences = create<FeedPreferences>()(
  persist(
    (set) => ({
      open: null,
      sounds: false,
      ambient: false,
      muted: [],
      setOpen: (open) => set({ open }),
      setSounds: (sounds) => set({ sounds }),
      setAmbient: (ambient) => set({ ambient }),
      toggleMuted: (category) =>
        set((state) => ({
          muted: state.muted.includes(category)
            ? state.muted.filter((item) => item !== category)
            : [...state.muted, category],
        })),
    }),
    {
      ...viewerPersisted<FeedPreferences>(FEED_PREFERENCES_KEY),
    }
  )
)

followViewer(useFeedPreferences)

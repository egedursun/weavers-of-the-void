import { lazy } from 'react'
import { type EntryPages } from '@/components/layout/entry/EntryWindow'

export const ENTRY_PAGES: EntryPages = {
  son: lazy(() =>
    import('@/features/son/SonPage').then((module) => ({
      default: module.SonPage,
    }))
  ),
  entity: lazy(() =>
    import('@/features/entity/EntityPage').then((module) => ({
      default: module.EntityPage,
    }))
  ),
  'foreign-god': lazy(() =>
    import('@/features/foreign-god/ForeignGodPage').then((module) => ({
      default: module.ForeignGodPage,
    }))
  ),
  world: lazy(() =>
    import('@/features/celestial/WorldWikiPage').then((module) => ({
      default: module.WorldWikiPage,
    }))
  ),
  star: lazy(() =>
    import('@/features/celestial/StarWikiPage').then((module) => ({
      default: module.StarWikiPage,
    }))
  ),
  creator: lazy(() =>
    import('@/features/creator/CreatorPage').then((module) => ({
      default: module.CreatorPage,
    }))
  ),
  'world-guide': lazy(() =>
    import('@/features/cosmos/TravellersGuide').then((module) => ({
      default: module.TravellersGuide,
    }))
  ),
  galaxy: lazy(() =>
    import('@/features/cosmography/wiki/GalaxyWiki').then((module) => ({
      default: module.GalaxyPage,
    }))
  ),
  cluster: lazy(() =>
    import('@/features/cosmography/wiki/ClusterWiki').then((module) => ({
      default: module.ClusterPage,
    }))
  ),
  dimension: lazy(() =>
    import('@/features/cosmography/wiki/DimensionWiki').then((module) => ({
      default: module.DimensionPage,
    }))
  ),
  help: lazy(() =>
    import('@/features/help/HelpPage').then((module) => ({
      default: module.HelpPage,
    }))
  ),
  incident: lazy(() =>
    import('@/features/records/EventPage').then((module) => ({
      default: module.EventPage,
    }))
  ),
}

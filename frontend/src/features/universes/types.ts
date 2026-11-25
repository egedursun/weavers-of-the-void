import { type components, type paths } from '@/api/generated/schema'

type Schemas = components['schemas']

export {
  libraryEventKindValues,
  libraryJobStageValues,
  libraryStreamKindValues,
  universeOriginValues,
  universeSortValues,
  universeStatusValues,
} from '@/api/generated/schema'

export type UniverseStatus = Schemas['UniverseStatus']
export type UniverseOrigin = Schemas['UniverseOrigin']
export type UniverseSort = Schemas['UniverseSort']
export type LibraryEventKind = Schemas['LibraryEventKind']
export type LibraryJobStatus = Schemas['LibraryJobStatus']
export type LibraryJobStage = Schemas['LibraryJobStage']
export type LibraryJobKind = Schemas['LibraryJobKind']

export type UniverseSummary = Schemas['UniverseView']
export type UniverseDetail = Schemas['UniverseDetail']
export type UniverseFacets = Schemas['UniverseFacets']
export type LibraryJob = Schemas['LibraryJobView']
export type PackagePreview = Schemas['PackagePreviewView']
export type TrashedUniverse = Schemas['TrashEntryView']
export type UniverseEdit = Schemas['UniversePatch']
export type UniverseDraft = Schemas['UniverseCreate']
export type ImportUploadField =
  keyof Schemas['Body_import_universe_api_library_imports_post']
export type ImportStarted =
  paths['/api/library/imports']['post']['responses'][202]['content']['application/json']

export type FacetCount<K extends string> = { value: K; count: number }

export type ManifestFile = {
  path: string
  size: number
  sha256: string
}

export type UniverseManifest = {
  format_version: number | null
  app_version: string | null
  schema_revision: string | null
  universe_id: string | null
  name: string
  summary: string | null
  notes: string | null
  tags: string[]
  created_at: string | null
  exported_at: string | null
  epoch: number | null
  year: number | null
  counts: Record<string, number>
  files: ManifestFile[]
}

export type UniverseFilters = {
  q: string
  status: UniverseStatus | null
  origin: UniverseOrigin | null
  tag: string | null
  sort: UniverseSort
}

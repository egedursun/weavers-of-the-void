import {
  BookMarked,
  BookOpen,
  Clapperboard,
  ClipboardList,
  CodeXml,
  FileChartColumn,
  FileCode2,
  FileText,
  Files,
  Feather,
  Globe,
  LibraryBig,
  ListTree,
  type LucideIcon,
  NotebookPen,
  ScrollText,
  Telescope,
  Type,
} from 'lucide-react'
import { type KpiTone } from '@/components/domain'
import {
  type ArtifactFormat,
  type ArtifactKind,
  type ArtifactStatus,
  type ExportFormat,
} from '../types'

export type ArtifactCategory =
  'writing' | 'screen' | 'record' | 'working' | 'page'

export const CATEGORY_LOOK: Record<
  ArtifactCategory,
  { label: string; icon: LucideIcon; tone: KpiTone }
> = {
  writing: { label: 'Prose and verse', icon: Feather, tone: 'gold' },
  screen: { label: 'For the screen', icon: Clapperboard, tone: 'info' },
  record: { label: 'Records', icon: LibraryBig, tone: 'verdigris' },
  working: { label: 'Working papers', icon: NotebookPen, tone: 'muted' },
  page: { label: 'Pages', icon: Globe, tone: 'success' },
}

export const CATEGORY_ORDER: readonly ArtifactCategory[] = [
  'writing',
  'screen',
  'record',
  'working',
  'page',
]

export const KIND_LOOK: Record<
  ArtifactKind,
  { label: string; icon: LucideIcon; category: ArtifactCategory }
> = {
  story: { label: 'Story', icon: BookOpen, category: 'writing' },
  chapter: { label: 'Chapter', icon: BookMarked, category: 'writing' },
  novel: { label: 'Novel', icon: LibraryBig, category: 'writing' },
  poem: { label: 'Poem', icon: Feather, category: 'writing' },
  screenplay: { label: 'Screenplay', icon: Clapperboard, category: 'screen' },
  chronicle: { label: 'Chronicle', icon: ScrollText, category: 'record' },
  encyclopedia: { label: 'Encyclopedia', icon: Files, category: 'record' },
  report: { label: 'Report', icon: FileChartColumn, category: 'record' },
  outline: { label: 'Outline', icon: ListTree, category: 'working' },
  notes: { label: 'Notes', icon: NotebookPen, category: 'working' },
  plan: { label: 'Plan', icon: ClipboardList, category: 'working' },
  forecast: { label: 'Forecast', icon: Telescope, category: 'working' },
  html_page: { label: 'Web page', icon: CodeXml, category: 'page' },
}

export const KIND_ORDER: readonly ArtifactKind[] = [
  'story',
  'chapter',
  'novel',
  'poem',
  'screenplay',
  'chronicle',
  'encyclopedia',
  'report',
  'outline',
  'notes',
  'plan',
  'forecast',
  'html_page',
]

export const STATUS_LOOK: Record<
  ArtifactStatus,
  { label: string; badge: 'outline' | 'success' }
> = {
  draft: { label: 'Draft', badge: 'outline' },
  final: { label: 'Final', badge: 'success' },
}

export const STATUS_ORDER: readonly ArtifactStatus[] = ['draft', 'final']

export const FORMAT_LOOK: Record<
  ArtifactFormat,
  { label: string; icon: LucideIcon }
> = {
  markdown: { label: 'Markdown', icon: Type },
  fountain: { label: 'Screenplay script', icon: Clapperboard },
  html: { label: 'Web page', icon: FileCode2 },
}

export const FORMAT_ORDER: readonly ArtifactFormat[] = [
  'markdown',
  'fountain',
  'html',
]

export const EXPORT_LOOK: Record<
  ExportFormat,
  { label: string; icon: LucideIcon }
> = {
  md: { label: 'Markdown (.md)', icon: Type },
  html: { label: 'Web page (.html)', icon: FileCode2 },
  pdf: { label: 'PDF (.pdf)', icon: FileText },
  epub: { label: 'E-book (.epub)', icon: BookOpen },
  docx: { label: 'Word (.docx)', icon: FileText },
  fountain: { label: 'Fountain (.fountain)', icon: Clapperboard },
}

export const EXPORT_ORDER: readonly ExportFormat[] = [
  'md',
  'html',
  'pdf',
  'epub',
  'docx',
  'fountain',
]

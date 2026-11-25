import {
  ArrowRightLeft,
  BookMarked,
  BookOpen,
  BookOpenCheck,
  Calculator,
  ChartSpline,
  CircleHelp,
  ClipboardList,
  ClipboardPen,
  Compass,
  FileCog,
  FilePen,
  FilePlus2,
  FileSearch,
  Files,
  FileText,
  Globe2,
  History,
  Hourglass,
  Library,
  ListOrdered,
  ListPlus,
  ListTree,
  type LucideIcon,
  Microscope,
  Network,
  NotebookTabs,
  Paperclip,
  PlayCircle,
  RotateCcw,
  ScrollText,
  Search,
  SearchCode,
  Signpost,
  SlidersHorizontal,
  Sparkles,
  Telescope,
  Undo2,
  Waypoints,
  Tags,
} from 'lucide-react'
import { type DivineWillToolId } from './types'

export type ToolLook = { label: string; icon: LucideIcon }

export const WILL_TOOL_LOOK: Record<DivineWillToolId, ToolLook> = {
  search_lore: { label: 'Searched the lore', icon: Search },
  read_node: { label: 'Read an entry', icon: BookOpen },
  read_records: { label: 'Read records', icon: NotebookTabs },
  enumerate: { label: 'Listed every match', icon: ListOrdered },
  graph_neighbours: { label: 'Followed the bonds', icon: Network },
  graph_path: { label: 'Traced a path', icon: Waypoints },
  chronicle: { label: 'Read the chronicle', icon: ScrollText },
  explain: { label: 'Explained a happening', icon: Microscope },
  state_at: { label: 'Looked back in time', icon: History },
  ledger: { label: 'Read the ledger', icon: BookMarked },
  world_overview: { label: 'Surveyed the world', icon: Globe2 },
  read_more: { label: 'Read further', icon: Files },
  search_actions: { label: 'Searched the acts', icon: SearchCode },
  describe_action: { label: 'Studied an act', icon: CircleHelp },
  perform_action: { label: 'Performed an act', icon: Sparkles },
  job_status: { label: 'Checked a work in progress', icon: Hourglass },
  undo_action: { label: 'Undid an act', icon: Undo2 },
  search_rules: { label: 'Searched the rules', icon: FileSearch },
  read_rule: { label: 'Read a rule', icon: FileCog },
  search_mechanics: { label: 'Searched the mechanics', icon: Compass },
  read_mechanic: { label: 'Read a mechanic', icon: ArrowRightLeft },
  read_game_rules: { label: 'Read the game rules', icon: BookOpenCheck },
  set_rule: { label: 'Changed a world rule', icon: SlidersHorizontal },
  reset_rule: { label: 'Reset a world rule', icon: RotateCcw },
  plan_create: { label: 'Drafted a plan', icon: ListPlus },
  plan_read: { label: 'Read a plan', icon: ClipboardList },
  plan_revise: { label: 'Revised a plan', icon: ClipboardPen },
  forecast_estimate: { label: 'Estimated a forecast', icon: Calculator },
  forecast_run: { label: 'Started a forecast', icon: PlayCircle },
  forecast_read: { label: 'Read a forecast', icon: ChartSpline },
  artifact_create: { label: 'Wrote a new work', icon: FilePlus2 },
  artifact_read: { label: 'Read a work', icon: FileText },
  artifact_edit: { label: 'Revised a work', icon: FilePen },
  artifact_update: { label: 'Set what a work is', icon: Tags },
  artifact_list: { label: 'Browsed the Library', icon: Library },
  attachment_list: { label: 'Listed your files', icon: Paperclip },
  attachment_read: { label: 'Read a file of yours', icon: ListTree },
  attachment_search: { label: 'Searched your files', icon: Telescope },
  suggest_mode: { label: 'Suggested another mode', icon: Signpost },
}

const FALLBACK: ToolLook = { label: 'Used a tool', icon: Sparkles }

function isWillTool(tool: string): tool is DivineWillToolId {
  return tool in WILL_TOOL_LOOK
}

export function toolLook(tool: string): ToolLook {
  return isWillTool(tool) ? WILL_TOOL_LOOK[tool] : FALLBACK
}

const ARGUMENT_CHARS = 64

function shortValue(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean')
    return String(value)
  if (Array.isArray(value))
    return value.map(shortValue).filter(Boolean).join(', ')
  return Object.entries(value as Record<string, unknown>)
    .map(([key, item]) => `${key.replaceAll('_', ' ')} ${shortValue(item)}`)
    .join('; ')
}

const NOT_NODE_IDS = new Set([
  'ledger_entry_id',
  'artifact_id',
  'plan_id',
  'forecast_id',
  'cycle_id',
  'attachment_id',
  'confirmation_id',
  'job_id',
])

type NameOf = (id: number) => string | undefined

function namedValue(key: string, value: unknown, nameOf: NameOf): string {
  if (NOT_NODE_IDS.has(key) || !/_ids?$/.test(key)) return shortValue(value)
  const ids = Array.isArray(value) ? value : [value]
  return ids
    .map((id) =>
      typeof id === 'number' ? (nameOf(id) ?? String(id)) : shortValue(id)
    )
    .filter(Boolean)
    .join(', ')
}

function argumentLabel(key: string, value: unknown, nameOf: NameOf): string {
  const ids = Array.isArray(value) ? value : [value]
  const named =
    !NOT_NODE_IDS.has(key) &&
    ids.some((id) => typeof id === 'number' && nameOf(id) !== undefined)
  return (named ? key.replace(/_ids?$/, '') : key).replaceAll('_', ' ')
}

export function argumentSummary(
  input: Record<string, unknown>,
  nameOf: NameOf
): string {
  const text = Object.entries(input)
    .filter(([key]) => key !== 'handle')
    .map(([key, value]) => {
      const shown = namedValue(key, value, nameOf)
      return shown ? `${argumentLabel(key, value, nameOf)}: ${shown}` : ''
    })
    .filter(Boolean)
    .join(' · ')
  return text.length > ARGUMENT_CHARS
    ? `${text.slice(0, ARGUMENT_CHARS).trimEnd()}…`
    : text
}

export function argumentRows(
  input: Record<string, unknown>
): { key: string; label: string; value: string }[] {
  return Object.entries(input).map(([key, value]) => ({
    key,
    label: key.replaceAll('_', ' '),
    value: typeof value === 'string' ? value : JSON.stringify(value, null, 2),
  }))
}

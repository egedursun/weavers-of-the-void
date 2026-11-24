import {
  BookOpen,
  CircleHelp,
  Compass,
  Crown,
  Ghost,
  Globe2,
  Layers,
  type LucideIcon,
  Orbit,
  ScrollText,
  Star,
  Sun,
  Workflow,
} from 'lucide-react'
import { type EntryKind } from '@/components/layout/entry/entryStack'

export const ENTRY_KIND_ICON: Record<EntryKind, LucideIcon> = {
  son: Crown,
  entity: BookOpen,
  'foreign-god': Ghost,
  world: Globe2,
  star: Star,
  galaxy: Orbit,
  cluster: Workflow,
  dimension: Layers,
  creator: Sun,
  'world-guide': Compass,
  help: CircleHelp,
  incident: ScrollText,
}

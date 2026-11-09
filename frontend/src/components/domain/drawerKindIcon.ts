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
  Star,
  Sun,
  Workflow,
} from 'lucide-react'
import { type DrawerKind } from '@/components/layout/drawer/drawerEntries'

export const DRAWER_KIND_ICON: Record<DrawerKind, LucideIcon> = {
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
}

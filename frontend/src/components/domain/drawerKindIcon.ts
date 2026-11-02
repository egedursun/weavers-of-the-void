import {
  BookOpen,
  CircleHelp,
  Compass,
  Crown,
  Ghost,
  Globe2,
  type LucideIcon,
  Star,
  Sun,
} from 'lucide-react'
import { type DrawerKind } from '@/components/layout/drawer/drawerEntries'

export const DRAWER_KIND_ICON: Record<DrawerKind, LucideIcon> = {
  son: Crown,
  entity: BookOpen,
  'foreign-god': Ghost,
  world: Globe2,
  star: Star,
  creator: Sun,
  'world-guide': Compass,
  help: CircleHelp,
}

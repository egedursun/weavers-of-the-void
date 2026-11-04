import {
  BookOpen,
  Crown,
  Folder,
  Ghost,
  Globe,
  type LucideIcon,
  Star,
  Sun,
} from 'lucide-react'
import { ENTITY_TYPE_ICON } from '@/components/domain/domainIcons'
import { type AtlasNode, type AtlasNodeKind } from './atlasModel'

export const KIND_TONE: Record<AtlasNodeKind, string> = {
  group: 'text-muted-foreground',
  entity: 'text-brand-verdigris',
  son: 'text-primary',
  creator: 'text-primary',
  world: 'text-info',
  star: 'text-warning',
  'foreign-god': 'text-destructive',
}

export function nodeIcon(node: AtlasNode): LucideIcon {
  const typeKey = node.entity?.entity_type ?? node.typeKey
  if (typeKey && typeKey in ENTITY_TYPE_ICON)
    return ENTITY_TYPE_ICON[typeKey as keyof typeof ENTITY_TYPE_ICON]
  return KIND_ICON[node.kind]
}

const KIND_ICON: Record<AtlasNodeKind, LucideIcon> = {
  group: Folder,
  entity: BookOpen,
  son: Crown,
  creator: Sun,
  world: Globe,
  star: Star,
  'foreign-god': Ghost,
}

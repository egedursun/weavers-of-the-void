import { useCallback } from 'react'
import { useNavigate } from '@tanstack/react-router'
import {
  BookOpen,
  Crown,
  Ghost,
  Globe,
  Hourglass,
  Landmark,
  Languages,
  type LucideIcon,
  MapPin,
  MessageSquare,
  ScrollText,
  StickyNote,
  Sun,
} from 'lucide-react'
import { useDrawerStack } from '@/components/layout/drawer/useDrawerStack'
import { type SearchHit } from './api'

type Category = SearchHit['category']

export const HIT_ICON: Record<Category, LucideIcon> = {
  son: Crown,
  foreign_god: Ghost,
  world: Globe,
  star: Sun,
  entity: BookOpen,
  word: Languages,
  epoch: Hourglass,
  chronicle: ScrollText,
  note: StickyNote,
  map_note: MapPin,
  message: MessageSquare,
  council: Landmark,
}

export const HIT_LABEL: Record<Category, string> = {
  son: 'Son',
  foreign_god: 'Foreign god',
  world: 'World',
  star: 'Star',
  entity: 'Record',
  word: 'Word',
  epoch: 'Epoch',
  chronicle: 'Chronicle',
  note: 'Note',
  map_note: 'Map note',
  message: 'Message',
  council: 'Council',
}

export function useHitRouter() {
  const navigate = useNavigate()
  const drawers = useDrawerStack()
  return useCallback(
    (hit: SearchHit) => {
      const id = String(hit.id)
      switch (hit.category) {
        case 'son':
          return drawers.open({ kind: 'son', id })
        case 'entity':
        case 'note':
          return drawers.open({ kind: 'entity', id })
        case 'foreign_god':
          return drawers.open({ kind: 'foreign-god', id })
        case 'world':
          return drawers.open({ kind: 'world', id })
        case 'star':
          return drawers.open({ kind: 'star', id })
        case 'word':
          return navigate({ to: '/languages' })
        case 'epoch':
        case 'chronicle':
          return navigate({ to: '/chronicle' })
        case 'map_note':
          return navigate({ to: '/map' })
        case 'message':
          return navigate({ to: '/prayers' })
        case 'council':
          return navigate({ to: '/council' })
      }
    },
    [drawers, navigate]
  )
}

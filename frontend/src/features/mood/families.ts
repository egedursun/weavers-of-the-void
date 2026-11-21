import { Smile } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const MOOD: RecordFamily = {
  id: 'mood',
  section: 'section-mood',
  title: 'Mood',
  description:
    'The feelings that have spread through a place or a household: its leading feeling and the strongest feelings shared among its people, as they pass along bonds and through shared places, feed crowds and lean choices, and fade.',
  icon: Smile,
  tone: 'info',
  empty:
    'No shared feeling stands here. Settlements and households gather moods from what their people feel; beings that do not feel keep none, and other things show the moods of the places they belong to through those places.',
  tables: {
    feeling_spread: {
      create: 'feeling_spread:create',
      edit: 'feeling_spread:edit',
      remove: 'feeling_spread:delete',
    },
  },
}

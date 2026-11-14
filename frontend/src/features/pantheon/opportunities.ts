import { plural } from '@/lib/units'
import { type PlayerHints } from './api'
import { verbFor } from './labels'

export type Opportunity = { key: string; title: string; body: string }

const DOOM_WARNING_SHARE = 3
const DOOM_WARNING_DIVISOR = 4

function names(list: string[]): string {
  return list.join(', ')
}

export function opportunitiesOf(
  hints: PlayerHints,
  richEssence?: number
): Opportunity[] {
  const items: Opportunity[] = []
  const creator = hints.creator
  if (creator.unanswered_prayers > 0)
    items.push({
      key: 'prayers',
      title: 'Prayers wait',
      body: `${plural(creator.unanswered_prayers, 'prayer')} ${creator.unanswered_prayers === 1 ? 'waits' : 'wait'} for your answer; silence erodes love.`,
    })
  if (richEssence !== undefined && creator.essence >= richEssence)
    items.push({
      key: 'essence',
      title: 'Essence to spend',
      body: `${creator.essence} essence gathers unused; reveal, summon or pour it into the land before it overflows.`,
    })
  if (creator.unclaimed.length > 0)
    items.push({
      key: 'unclaimed',
      title: 'Breathe faith',
      body: `Communities without a god: ${names(creator.unclaimed)}. A son or your cult can claim them.`,
    })
  if (creator.godless_worlds.length > 0)
    items.push({
      key: 'godless',
      title: 'Godless worlds',
      body: `${names(creator.godless_worlds)} ${verbFor(creator.godless_worlds, 'has', 'have')} no patron; send a son there.`,
    })
  if (creator.rebel_sons.length > 0)
    items.push({
      key: 'rebels',
      title: 'Rebellion',
      body: `${names(creator.rebel_sons)} ${verbFor(creator.rebel_sons, 'defies', 'defy')} you: suppress or forgive ${'them'}.`,
    })
  if (creator.fading_sons.length > 0)
    items.push({
      key: 'fading',
      title: 'Fading sons',
      body: `${creator.fading_sons.map((son) => `${son.name} (${son.existence})`).join(', ')} ${verbFor(
        creator.fading_sons.map((son) => son.name),
        'is',
        'are'
      )} being forgotten; remember them.`,
    })
  if (creator.stale_threads > 0)
    items.push({
      key: 'stale',
      title: 'Stalled stories',
      body: `${plural(creator.stale_threads, 'story', 'stories')} ${creator.stale_threads === 1 ? 'has' : 'have'} not moved for a while; advance or close ${creator.stale_threads === 1 ? 'it' : 'them'}.`,
    })
  if (
    creator.doom_threshold > 0 &&
    creator.doom * DOOM_WARNING_DIVISOR >=
      creator.doom_threshold * DOOM_WARNING_SHARE
  )
    items.push({
      key: 'doom',
      title: 'Doom nears',
      body: `The doom clock stands at ${creator.doom} of ${creator.doom_threshold}; the world ends when it is reached.`,
    })
  if (hints.epoch_in_progress)
    items.push({
      key: 'epoch',
      title: 'An epoch is running',
      body: 'The world is living through an epoch; your changes land when it settles.',
    })
  if (hints.unread_notifications > 0)
    items.push({
      key: 'news',
      title: 'Unread news',
      body: `${plural(hints.unread_notifications, 'notice')} ${hints.unread_notifications === 1 ? 'waits' : 'wait'} unread.`,
    })
  if (hints.open_threads > 0)
    items.push({
      key: 'threads',
      title: 'Open stories',
      body: `${plural(hints.open_threads, 'story', 'stories')} ${hints.open_threads === 1 ? 'is' : 'are'} still open.`,
    })
  if (hints.sons_without_orders.length > 0)
    items.push({
      key: 'orders',
      title: 'Give orders',
      body: `${names(hints.sons_without_orders)} ${verbFor(hints.sons_without_orders, 'has', 'have')} no standing order.`,
    })
  if (hints.sleeping_sons.length > 0)
    items.push({
      key: 'sleep',
      title: 'Sleeping sons',
      body: `${names(hints.sleeping_sons)} ${verbFor(hints.sleeping_sons, 'is', 'are')} asleep.`,
    })
  if (hints.dead_sons.length > 0)
    items.push({
      key: 'dead',
      title: 'The dead',
      body: `${names(hints.dead_sons)} ${verbFor(hints.dead_sons, 'lies', 'lie')} dead; loyal cults gather devotion, or you can raise them.`,
    })
  if (hints.sons_without_image > 0)
    items.push({
      key: 'images',
      title: 'Likenesses',
      body: `${plural(hints.sons_without_image, 'son')} ${hints.sons_without_image === 1 ? 'has' : 'have'} no image yet.`,
    })
  return items
}

const SERVER_PHRASED = new Set([
  'prayers',
  'essence',
  'unclaimed',
  'godless',
  'rebels',
  'fading',
  'stale',
])

export function withoutServerPhrased(items: Opportunity[]): Opportunity[] {
  return items.filter((item) => !SERVER_PHRASED.has(item.key))
}

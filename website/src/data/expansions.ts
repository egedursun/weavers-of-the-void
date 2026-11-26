import english from './expansions/en.json'
import turkish from './expansions/tr.json'
import type { Locale } from '../i18n'

export type Governed = { title: string; text: string }

export type DepthLine = { text: string }

export type DepthList = { label: string; values: string[] }

export type DepthItem = DepthLine | DepthList

export type Expansion = {
  number: number
  name: string
  slug: string
  cover: number | null
  motto?: string
  intro: string
  outcome: string | null
  governs: Governed[]
  depth: DepthItem[]
}

export type Tally = { parts: number; governs: number; lists: number; values: number }

const CATALOGUES: Record<Locale, Expansion[]> = {
  en: english as Expansion[],
  tr: turkish as Expansion[],
}

export function isList(item: DepthItem): item is DepthList {
  return 'values' in item
}

export function expansionsFor(locale: Locale): Expansion[] {
  const catalogue = CATALOGUES[locale]
  if (catalogue.length !== CATALOGUES.en.length) throw new Error(`the ${locale} expansion catalogue is incomplete`)
  return catalogue
}

export function expansionBySlug(locale: Locale, slug: string): Expansion | undefined {
  return expansionsFor(locale).find((item) => item.slug === slug)
}

export function neighbours(locale: Locale, slug: string): { previous?: Expansion; next?: Expansion } {
  const all = expansionsFor(locale)
  const index = all.findIndex((item) => item.slug === slug)
  return { previous: all[index - 1], next: all[index + 1] }
}

export function tallyOf(items: Expansion[]): Tally {
  return items.reduce<Tally>(
    (tally, item) => {
      const lists = item.depth.filter(isList)
      return {
        parts: tally.parts + 1,
        governs: tally.governs + item.governs.length,
        lists: tally.lists + lists.length,
        values: tally.values + lists.reduce((sum, list) => sum + list.values.length, 0),
      }
    },
    { parts: 0, governs: 0, lists: 0, values: 0 },
  )
}

export function leadSentence(text: string): string {
  const match = text.match(/^.+?[.!?](?=\s|$)/)
  return match ? match[0] : text
}

export function coverOf(item: Expansion): string {
  return item.cover === null ? 'art/collectors-edition.webp' : `covers/${item.cover}.webp`
}

export function backOf(item: Expansion): string | null {
  return item.cover === null ? null : `backs/${item.cover}.webp`
}

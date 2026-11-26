import english from './expansions.en.json'
import partOne from './tr/part-1.json'
import partTwo from './tr/part-2.json'
import partThree from './tr/part-3.json'
import partFour from './tr/part-4.json'
import partFive from './tr/part-5.json'
import chapterTitles from './tr/chapters.json'
import type { Locale } from '../i18n'

export type Feature = { title: string; text: string }

export type Expansion = {
  number: number
  name: string
  slug: string
  tagline: string
  intro: string[]
  features: Feature[]
  story: string
  chapter: string
}

export type Chapter = { numeral: string; title: string; sign: string; expansions: Expansion[] }

type Translation = Pick<Expansion, 'number' | 'tagline' | 'intro' | 'features' | 'story'>

const turkish = new Map<number, Translation>(
  [partOne, partTwo, partThree, partFour, partFive].flat().map((item) => [item.number, item as Translation]),
)
const turkishChapters: Record<string, string> = chapterTitles

function localised(item: Omit<Expansion, 'chapter'>, chapter: string, locale: Locale): Expansion {
  const translated = locale === 'tr' ? turkish.get(item.number) : undefined
  if (locale === 'tr' && !translated) throw new Error(`expansion ${item.number} has no Turkish text`)
  return { ...item, ...(translated ?? {}), name: item.name, slug: item.slug, chapter }
}

export function loomFor(locale: Locale): Expansion {
  return localised(english.loom, '0', locale)
}

export function chaptersFor(locale: Locale): Chapter[] {
  return english.chapters.map((chapter) => ({
    numeral: chapter.numeral,
    sign: chapter.sign,
    title: locale === 'tr' ? (turkishChapters[chapter.numeral] ?? chapter.title) : chapter.title,
    expansions: chapter.expansions.map((item) => localised(item, chapter.numeral, locale)),
  }))
}

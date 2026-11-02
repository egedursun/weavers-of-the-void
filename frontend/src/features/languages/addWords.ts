import { type components } from '@/api/generated/schema'

type WordKind = components['schemas']['WordKind']
type WordInput = components['schemas']['WordInput']

export const ANY_KIND = 'any'
export const WORD_MAX = 40
export const MEANING_MAX = 200
export const WORDS_PER_ORDER_MAX = 50

export type Row = { key: number; word: string; meaning: string; kind: string }

export const emptyRow = (key: number): Row => ({
  key,
  word: '',
  meaning: '',
  kind: ANY_KIND,
})

export function wordsOf(rows: Row[]): WordInput[] {
  return rows
    .map((row) => ({
      word: row.word.trim(),
      meaning: row.meaning.trim(),
      kind: row.kind === ANY_KIND ? null : (row.kind as WordKind),
    }))
    .filter((row) => row.word !== '' && row.meaning !== '')
}

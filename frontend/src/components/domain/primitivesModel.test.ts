import { describe, expect, it } from 'vitest'
import { acceptsFile } from './fileAccept'
import {
  chartFrame,
  directLabelOffsets,
  nearestIndex,
  niceCeiling,
  shortLabel,
  xLabelIndices,
  xScale,
  yCeiling,
} from './lineChartModel'
import {
  type MentionIndex,
  hasMentions,
  parseLore,
  parseMentions,
  threadSummary,
} from './mentionTokens'
import { selectionText, visibleOptions } from './multiSelectModel'

const INDEX: MentionIndex = {
  names: new Map([
    [12, { id: 12, name: 'Velmora', kind: 'entity' }],
    [7, { id: 7, name: 'Ithren', kind: 'son' }],
    [3, { id: 3, name: 'Saltreach', kind: 'world' }],
    [1, { id: 1, name: 'The Maker', kind: 'creator' }],
  ]),
  threads: new Map([
    [
      5,
      {
        id: 5,
        text: 'The drowned bell that rings beneath the salt sea every hundred years',
      },
    ],
  ]),
}

describe('line chart model', () => {
  it('rounds the ceiling up at the leading digit', () => {
    expect(niceCeiling(0)).toBe(1)
    expect(niceCeiling(7)).toBe(7)
    expect(niceCeiling(42)).toBe(50)
    expect(niceCeiling(1230)).toBe(2000)
    expect(
      yCeiling([
        { key: 'a', label: 'A', color: 'red', points: [{ x: 1, y: 87 }] },
      ])
    ).toBe(90)
    expect(yCeiling([], 100)).toBe(100)
  })

  it('sizes the frame by width and leaves room for direct labels', () => {
    expect(chartFrame(280, 1)).toMatchObject({ height: 140, right: 14 })
    expect(chartFrame(500, 3)).toMatchObject({ height: 170, right: 78 })
    expect(chartFrame(500, 6).right).toBe(14)
  })

  it('thins epoch labels, keeps the last and drops one that would overlap it', () => {
    const xs = Array.from({ length: 20 }, (_, index) => index + 1)
    const toX = xScale(chartFrame(320, 1), xs)
    const shown = xLabelIndices(xs, toX)
    expect(shown.length).toBeLessThanOrEqual(8)
    expect(shown.at(-1)).toBe(19)
    expect(shown).not.toContain(18)
  })

  it('spreads end labels apart and finds the nearest epoch', () => {
    expect(directLabelOffsets([50, 52, 100])).toEqual([50, 62, 100])
    const xs = [1, 2, 3]
    const toX = xScale(chartFrame(200, 1), xs)
    expect(nearestIndex(xs, toX, toX(2) + 3)).toBe(1)
    expect(shortLabel('Population of the realm')).toBe('Population ')
  })
})

describe('mention tokens', () => {
  it('links bare, prefixed and parenthesised ids and drops repeated names', () => {
    const pieces = parseMentions(
      'Velmora (#12) fell; #12 Velmora wept and son#7 Ithren laughed on world#3.',
      INDEX
    )
    expect(
      pieces
        .filter((piece) => piece.type === 'link')
        .map((piece) => [piece.text, piece.type === 'link' && piece.kind])
    ).toEqual([
      ['Velmora', 'entity'],
      ['Velmora', 'entity'],
      ['Ithren', 'son'],
      ['Saltreach', 'world-guide'],
    ])
  })

  it('quotes a thread and falls back for unknown records', () => {
    const pieces = parseMentions('It echoes thread#5.', INDEX)
    expect(pieces[1]).toEqual({
      type: 'thread',
      text: threadSummary(INDEX.threads.get(5)?.text ?? ''),
      title: INDEX.threads.get(5)?.text,
    })
    expect(threadSummary('short')).toBe('"short"')
    expect(
      parseMentions('son#99 and #404 crossed route#2; thread#8 faded', INDEX)
        .map((piece) => piece.text)
        .join('')
    ).toBe('a son and a record crossed a road; a story faded')
    expect(hasMentions('No tokens here, #hashtag only')).toBe(false)
    expect(hasMentions('Born of son#7')).toBe(true)
  })
})

describe('lore text', () => {
  const targets = [
    { id: 12, name: 'Velmora', kind: 'entity' as const },
    { id: 40, name: 'Marsh Folk', kind: 'entity' as const },
    { id: 9, name: 'Orun', kind: 'entity' as const },
  ]

  it('links known record names once, skips the record itself and keeps tokens', () => {
    const pieces = parseLore(
      '[[thread|Orun]] watched the Marsh Folk; #12 rose and Velmora again, marsh folk again.',
      INDEX,
      targets,
      9
    )
    expect(
      pieces
        .filter((piece) => piece.type === 'link')
        .map((piece) => piece.type === 'link' && [piece.text, piece.id])
    ).toEqual([
      ['Marsh Folk', 40],
      ['Velmora', 12],
    ])
    expect(pieces.map((piece) => piece.text).join('')).toBe(
      'Orun watched the Marsh Folk; Velmora rose and Velmora again, marsh folk again.'
    )
  })

  it('returns plain text when nothing is known', () => {
    expect(parseLore('A quiet shore.', INDEX)).toEqual([
      { type: 'text', text: 'A quiet shore.' },
    ])
  })
})

describe('multi-select model', () => {
  const options = [
    { value: '1', label: 'Marsh Folk', detail: 'People' },
    { value: '2', label: 'Tidebound', detail: 'Settlement' },
    { value: '3', label: 'Ash Choir', detail: 'People' },
  ]

  it('keeps checked items visible while filtering', () => {
    expect(
      visibleOptions(options, new Set(['2']), 'ash').map(
        (option) => option.value
      )
    ).toEqual(['2', '3'])
    expect(
      visibleOptions(options, new Set(), 'settle').map((option) => option.value)
    ).toEqual(['2'])
    expect(visibleOptions(options, new Set(), '  ')).toHaveLength(3)
  })

  it('counts the selection against a minimum', () => {
    expect(selectionText(1, 0)).toBe('1 selected')
    expect(selectionText(1, 2)).toBe('1 selected · at least 2')
  })
})

describe('file accept rules', () => {
  it('matches extensions, wildcards and exact types', () => {
    const pack = new File(['x'], 'Ember Hollow.AERONA')
    const image = new File(['x'], 'cover.png', { type: 'image/png' })
    expect(acceptsFile(pack, '.aerona,application/gzip')).toBe(true)
    expect(acceptsFile(image, '.aerona,application/gzip')).toBe(false)
    expect(acceptsFile(image, 'image/*')).toBe(true)
    expect(acceptsFile(image, undefined)).toBe(true)
  })
})

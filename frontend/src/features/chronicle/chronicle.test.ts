import { describe, expect, it } from 'vitest'
import { splitByNames, stripMarkers } from '@/components/domain/nameLinks'
import { type ChronicleLine } from '@/features/entity/api/types'
import { strongestKind } from './chronicleKinds'
import { kindSet, validateChronicleSearch } from './chronicleSearch'
import { filterLines } from './lineFilter'

function line(
  id: number,
  kind: string,
  text: string,
  world: number | null = 1
): ChronicleLine {
  return {
    id,
    epoch: 2,
    year: null,
    kind,
    son_id: null,
    world_id: world,
    text,
    template_key: null,
    created_at: '',
    entity_ids: [],
  } as ChronicleLine
}

describe('chronicle helpers', () => {
  const lines = [
    line(1, 'birth', 'Orun was born.'),
    line(2, 'engine_raw', 'tick'),
    line(3, 'war', 'Velmora went to war.', 2),
  ]

  it('hides the raw event log unless chosen', () => {
    expect(
      filterLines(lines, { q: '', kinds: null, world: null }).map(
        (item) => item.id
      )
    ).toEqual([1, 3])
    expect(
      filterLines(lines, {
        q: '',
        kinds: kindSet('engine_raw'),
        world: null,
      }).map((item) => item.id)
    ).toEqual([2])
  })

  it('filters by text and world', () => {
    expect(
      filterLines(lines, { q: 'velmora', kinds: null, world: null }).map(
        (item) => item.id
      )
    ).toEqual([3])
    expect(
      filterLines(lines, { q: '', kinds: null, world: 1 }).map(
        (item) => item.id
      )
    ).toEqual([1])
  })

  it('picks the weightiest kind of an epoch', () => {
    expect(strongestKind(['creation', 'birth', 'death'])).toBe('death')
  })

  it('links each named record once and strips thread markers', () => {
    const pieces = splitByNames('Orun met Velmora; Orun left.', [
      { id: 4, name: 'Orun', kind: 'entity' },
      { id: 2, name: 'Velmora', kind: 'entity' },
    ])
    expect(
      pieces.filter((piece) => piece.target).map((piece) => piece.text)
    ).toEqual(['Orun', 'Velmora'])
    expect(pieces.map((piece) => piece.text).join('')).toBe(
      'Orun met Velmora; Orun left.'
    )
    expect(stripMarkers('The [[thread|salt war]] began')).toBe(
      'The salt war began'
    )
  })

  it('validates the chronicle address', () => {
    expect(
      validateChronicleSearch({
        epoch: '3',
        line: 'x',
        kinds: 'war,birth',
        all: 'true',
      })
    ).toEqual({ epoch: 3, kinds: 'war,birth', all: true })
  })
})

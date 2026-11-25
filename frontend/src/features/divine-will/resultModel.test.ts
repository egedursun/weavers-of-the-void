import { describe, expect, it } from 'vitest'
import { parsedResult } from './resultModel'

describe('tool results', () => {
  it('reads the paging envelope apart from the text', () => {
    const found = parsedResult(
      '{"total": 128, "shown": 2, "page": 1, "next": true, "handle": "a1"}\nEvery link.\n\n- one\n- two'
    )
    expect(found.envelope).toEqual({
      total: 128,
      shown: 2,
      page: 1,
      next: true,
    })
    expect(found.lines).toEqual(['Every link.\n', '- one', '- two'])
  })

  it('keeps a text without an envelope whole', () => {
    expect(parsedResult('{not json}\nplain')).toEqual({
      envelope: null,
      lines: ['{not json}', 'plain'],
    })
  })
})

import { afterEach, describe, expect, it, vi } from 'vitest'
import { copyText } from './copyText'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('copying text', () => {
  it('says it copied when the clipboard takes the text', async () => {
    vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue(undefined)
    await expect(copyText('a-temporary-secret')).resolves.toBe(true)
  })

  it('falls back to a selection copy when the clipboard refuses', async () => {
    vi.spyOn(navigator.clipboard, 'writeText').mockRejectedValue(
      new Error('denied')
    )
    const command = vi.spyOn(document, 'execCommand').mockReturnValue(true)
    await expect(copyText('a-temporary-secret')).resolves.toBe(true)
    expect(command).toHaveBeenCalledWith('copy')
  })

  it('reports a failure when nothing could copy, so no screen claims it did', async () => {
    vi.spyOn(navigator.clipboard, 'writeText').mockRejectedValue(
      new Error('denied')
    )
    vi.spyOn(document, 'execCommand').mockReturnValue(false)
    await expect(copyText('a-temporary-secret')).resolves.toBe(false)
  })
})

import { describe, expect, it } from 'vitest'
import { isTypingTarget } from './useGlobalShortcuts'

describe('isTypingTarget', () => {
  it('recognises fields and editable content', () => {
    expect(isTypingTarget(document.createElement('input'))).toBe(true)
    expect(isTypingTarget(document.createElement('textarea'))).toBe(true)
    const editable = document.createElement('div')
    editable.contentEditable = 'true'
    document.body.append(editable)
    expect(isTypingTarget(editable)).toBe(true)
    editable.remove()
  })

  it('ignores ordinary elements', () => {
    expect(isTypingTarget(document.createElement('div'))).toBe(false)
    expect(isTypingTarget(null)).toBe(false)
  })
})

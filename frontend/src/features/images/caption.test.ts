import { describe, expect, it } from 'vitest'
import { captionFromFileName, isMeaningfulCaption } from './caption'

describe('captions from file names', () => {
  it('keeps names a person chose', () => {
    expect(captionFromFileName('The salt gate at dusk.png')).toBe(
      'The salt gate at dusk'
    )
    expect(captionFromFileName('velmora_harbour.webp')).toBe('velmora harbour')
  })

  it('drops camera, screenshot, generator and uuid names', () => {
    expect(captionFromFileName('IMG_20240102_1200.jpg')).toBeNull()
    expect(captionFromFileName('Screenshot 2024-01-01 at 10.00.png')).toBeNull()
    expect(captionFromFileName('Gemini_Generated_Image_abc.png')).toBeNull()
    expect(
      captionFromFileName('3f2a9c1d-1234-4abc-9def-001122334455.png')
    ).toBeNull()
    expect(captionFromFileName('render_000123.png')).toBeNull()
    expect(isMeaningfulCaption('')).toBe(false)
  })
})

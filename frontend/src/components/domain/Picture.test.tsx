import '@/styles/index.css'
import { describe, expect, it } from 'vitest'
import { render } from 'vitest-browser-react'
import { page } from 'vitest/browser'
import { Picture } from './Picture'

describe('Picture with no file', () => {
  it('fills the room it was given and says what is missing', async () => {
    await page.viewport(1280, 900)
    const screen = await render(
      <div className='w-full max-w-lg'>
        <Picture
          src='/media/missing-file.webp'
          alt='A likeness'
          missingClassName='aspect-video w-full'
          className='max-h-lightbox w-auto max-w-full object-contain'
        />
      </div>
    )
    const missing = screen.getByRole('img', { name: 'A likeness' })
    await expect
      .element(missing)
      .toHaveAttribute('data-domain', 'picture-missing')
    await expect.element(screen.getByText('No image file')).toBeVisible()
    const box = missing.element().getBoundingClientRect()
    expect(box.width).toBeGreaterThan(400)
    expect(box.height).toBeGreaterThan(200)
  })

  it('stays a small mark when compact', async () => {
    const screen = await render(
      <Picture src={null} alt='' compact className='size-8' />
    )
    const missing = document.querySelector('[data-domain=picture-missing]')
    expect(missing).not.toBeNull()
    expect(screen.container.textContent).toBe('')
  })
})

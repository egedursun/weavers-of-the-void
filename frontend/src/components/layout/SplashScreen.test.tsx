import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import shell from '../../../index.html?raw'
import { SplashScreen } from './SplashScreen'

const BOOT_LOGO = /<div class="boot-mark">\s*<img src="([^"]+)"/

describe('the splash logo', () => {
  it('shows the very image the page shell already loaded, so it never waits on the network', async () => {
    const bootLogo = BOOT_LOGO.exec(shell)?.[1]
    expect(bootLogo).toBeTruthy()
    const { screen } = await renderScreen(
      <SplashScreen line='Opening the gates' />
    )
    const logo = screen
      .getByRole('img', { name: 'Weavers of the Void' })
      .element()
    expect(logo.getAttribute('src')).toBe(bootLogo)
    expect(logo.hasAttribute('srcset')).toBe(false)
  })
})

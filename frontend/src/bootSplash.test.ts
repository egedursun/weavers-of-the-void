import { describe, expect, it } from 'vitest'
import shell from '../index.html?raw'
import entry from './main.tsx?raw'

describe('boot splash', () => {
  it('paints the splash inside the root and the app mounts over it', () => {
    expect(shell).toMatch(/<div id="root">\s*<div class="boot"/)
    expect(entry).not.toMatch(/innerHTML/)
    expect(entry).toMatch(/createRoot\(rootElement\)/)
  })
})

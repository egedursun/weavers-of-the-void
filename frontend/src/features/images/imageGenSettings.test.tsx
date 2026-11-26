import { ruleList, worldState } from '@/test-utils/fixtures'
import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { ImageGenSettings } from './ImageGenSettings'

const RULES = ruleList({
  'image_gen.width': 720,
  'image_gen.height': 720,
  'image_gen.steps': 4,
  'image_gen.auto': 1,
  'image_gen.retries': 1,
  'image_gen.idle_unload_seconds': 600,
  'image_gen.image_timeout_seconds': 300,
  'image_gen.startup_timeout_seconds': 300,
  'image_gen.log_lines': 200,
})

async function settingsDuring(running: boolean) {
  return renderScreen(<ImageGenSettings />, {
    'GET /api/rules': RULES,
    'GET /api/state': worldState({ epoch_running: running }),
    'PATCH /api/rules': RULES,
  })
}

describe('image generation settings', () => {
  it('saves a new resolution when no epoch runs', async () => {
    const { screen, server } = await settingsDuring(false)
    await screen.getByRole('radio', { name: /480p/ }).click()
    await screen.getByRole('button', { name: /Save 2/ }).click()
    await expect.poll(() => server.callsTo('PATCH /api/rules').length).toBe(1)
  })

  it('refuses to save while an epoch runs and says why', async () => {
    const { screen, server } = await settingsDuring(true)
    await expect
      .element(screen.getByText('Saving waits for the epoch'))
      .toBeVisible()
    await screen.getByRole('radio', { name: /480p/ }).click()
    const save = screen.getByRole('button', { name: /Save 2/ })
    await expect
      .element(save)
      .toHaveAttribute(
        'aria-description',
        'An epoch is running; rules can be changed again when it ends.'
      )
    await save.click({ force: true })
    expect(server.callsTo('PATCH /api/rules')).toHaveLength(0)
  })
})

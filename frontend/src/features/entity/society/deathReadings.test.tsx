import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DeathReadingsPanel } from './DeathReadings'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const CULTURE = {
  death_readings: [
    { cause: 'old_age', reading: 'honourable', authored: true, held: true },
  ],
} as never

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 50 },
  })
  onApi('GET', '/api/names', [])
}

describe('death readings', () => {
  beforeEach(resetApi)

  it('shows how a people reads each death and sets, creates and resets a reading', async () => {
    serve()
    onApi('POST', '/api/actions/death_reading:edit', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/death_reading:create', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/death_reading:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <DeathReadingsPanel peopleId={12} culture={CULTURE} blocked={null} />
    )
    await expect
      .element(screen.getByText('Honourable · set by you · held'))
      .toBeVisible()
    await screen
      .getByRole('combobox', { name: 'How they read old age' })
      .click()
    await screen.getByRole('option', { name: 'Glorious' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/death_reading:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/death_reading:edit')[0].body).toEqual({
      people_id: 12,
      cause: 'old_age',
      reading: 'glorious',
      hold: true,
    })
    await screen
      .getByRole('switch', { name: 'Hold their reading of wounds' })
      .click()
    await screen.getByRole('combobox', { name: 'How they read wounds' }).click()
    await screen.getByRole('option', { name: 'Shameful' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/death_reading:create'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/death_reading:create')[0].body
    ).toEqual({
      people_id: 12,
      cause: 'wounds',
      reading: 'shameful',
      hold: false,
    })
    await screen
      .getByRole('button', { name: 'Read from values' })
      .first()
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/death_reading:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/death_reading:delete')[0].body
    ).toEqual({ people_id: 12, cause: 'old_age' })
  })

  it('says why a death with no reading cannot be reset', async () => {
    serve()
    const { screen } = await renderApp(
      <DeathReadingsPanel peopleId={12} culture={CULTURE} blocked={null} />
    )
    const reset = screen
      .getByRole('button', { name: 'Read from values' })
      .nth(1)
    await expect.element(reset).toBeDisabled()
    await expect
      .element(reset)
      .toHaveAccessibleDescription('They hold no reading of it yet')
  })
})

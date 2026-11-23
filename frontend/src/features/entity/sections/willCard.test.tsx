import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { WillCard } from './WillCard'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const HILD = { id: 502, kind: 'entity' as const, name: 'Hild' }
const EDRIC = { id: 503, kind: 'entity' as const, name: 'Edric' }

const WILL = {
  made_epoch: 48,
  witnesses: [EDRIC],
  forged: false,
  read_epoch: null,
  contested: true,
  set_aside: false,
  held: true,
  heirs: [
    { heir: HILD, share: 60 },
    { heir: EDRIC, share: 40 },
  ],
} as never

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 50 },
  })
  onApi('GET', '/api/names', [
    { id: 501, kind: 'entity', type: 'mortal', name: 'Oswin', world_id: 1 },
    { id: 502, kind: 'entity', type: 'mortal', name: 'Hild', world_id: 1 },
    { id: 503, kind: 'entity', type: 'mortal', name: 'Edric', world_id: 1 },
    { id: 504, kind: 'entity', type: 'mortal', name: 'Wyn', world_id: 1 },
  ])
}

describe('will card', () => {
  beforeEach(resetApi)

  it('shows the heirs and their shares, names an heir, strikes one, marks the hand and tears it up', async () => {
    serve()
    onApi('POST', '/api/actions/will:set', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/will:remove', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <WillCard testatorId={501} will={WILL} blocked={null} hold={true} />
    )
    await expect
      .element(screen.getByText('Contested', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText('60 of every hundred parts of what they own'))
      .toBeVisible()
    await expect.element(screen.getByText('Witnessed by Edric')).toBeVisible()
    await screen.getByRole('combobox', { name: 'Heir' }).click()
    await screen.getByRole('option', { name: /Wyn/ }).click()
    await screen.getByRole('button', { name: 'Add to the will' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/will:set'))
      .toHaveLength(1)
    const added = callsTo('POST', '/api/actions/will:set')[0].body as {
      heirs: { heir_id: number; share: number }[]
      forged: boolean
      hold: boolean
      witnesses: number[]
    }
    expect(added.heirs.map((line) => line.heir_id).sort()).toEqual([
      502, 503, 504,
    ])
    expect(added.heirs.reduce((sum, line) => sum + line.share, 0)).toBe(100)
    expect(added.witnesses).toEqual([503])
    expect(added.hold).toBe(true)
    await screen.getByRole('button', { name: 'Strike out' }).first().click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/will:set'))
      .toHaveLength(2)
    expect(callsTo('POST', '/api/actions/will:set')[1].body).toMatchObject({
      heirs: [{ heir_id: 503, share: 100 }],
      forged: false,
    })
    await screen
      .getByRole('switch', { name: 'Written in a forged hand' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/will:set'))
      .toHaveLength(3)
    expect(callsTo('POST', '/api/actions/will:set')[2].body).toMatchObject({
      heirs: [
        { heir_id: 502, share: 60 },
        { heir_id: 503, share: 40 },
      ],
      forged: true,
    })
    await screen.getByRole('button', { name: 'Tear up the will' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/will:remove'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/will:remove')[0].body).toEqual({
      testator_id: 501,
    })
  })

  it('says why an heir cannot be named twice and why there is nothing to tear up', async () => {
    serve()
    const { screen } = await renderApp(
      <WillCard testatorId={501} will={null} blocked={null} hold={false} />
    )
    await expect
      .element(
        screen.getByText('No will is written; custom decides the heirs.')
      )
      .toBeVisible()
    const write = screen.getByRole('button', { name: 'Write the will' })
    await expect
      .element(write)
      .toHaveAccessibleDescription('Choose an heir first.')
    await screen.getByRole('combobox', { name: 'Heir' }).click()
    await screen.getByRole('option', { name: /Oswin/ }).click()
    await expect
      .element(write)
      .toHaveAccessibleDescription('No one is their own heir.')
    await expect
      .element(screen.getByRole('button', { name: 'Tear up the will' }))
      .toHaveAccessibleDescription('No will is written.')
    await expect
      .element(screen.getByRole('switch', { name: 'Written in a forged hand' }))
      .toBeDisabled()
  })
})

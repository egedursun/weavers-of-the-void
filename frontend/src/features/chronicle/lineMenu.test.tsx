import { worldState } from '@/test-utils/fixtures'
import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { ChronicleEntry } from './ChronicleEntry'

const LINE = {
  id: 41,
  epoch: 3,
  year: 312,
  kind: 'birth',
  son_id: null,
  world_id: 1,
  text: 'Velmora was founded on the salt shore shore.',
  template_key: null,
  created_at: '2026-01-01T12:00:00Z',
  entity_ids: [],
} as never

const DONE = {
  action: 'chronicle:edit',
  message: 'The chronicle line was amended (text).',
  ledger_entry_id: 3,
  job_id: null,
}

function routes(extra: Record<string, unknown> = {}) {
  return {
    'GET /api/state': worldState(),
    'GET /api/names': [],
    'POST /api/actions/chronicle:edit': DONE,
    'POST /api/notifications/from-chronicle/{chronicle_id}': { id: 1 },
    ...extra,
  }
}

describe('chronicle line menu', () => {
  it('amends a line through the edit action', async () => {
    const { screen, server } = await renderScreen(
      <ChronicleEntry line={LINE} />,
      routes()
    )
    await screen
      .getByRole('button', { name: 'Line actions for epoch 3' })
      .click()
    await screen.getByRole('menuitem', { name: 'Amend the line' }).click()
    const save = screen.getByRole('button', { name: 'Save the line' })
    await expect
      .element(save)
      .toHaveAttribute('aria-description', 'Nothing has changed.')
    await screen.getByRole('textbox', { name: 'The line' }).fill('')
    await expect
      .element(save)
      .toHaveAttribute(
        'aria-description',
        'A line cannot be emptied; hide it instead.'
      )
    await screen
      .getByRole('textbox', { name: 'The line' })
      .fill('Velmora was founded on the salt shore.')
    await save.click()
    await expect
      .poll(() => server.callsTo('POST /api/actions/chronicle:edit').length)
      .toBe(1)
    expect(server.callsTo('POST /api/actions/chronicle:edit')[0].body).toEqual({
      chronicle_id: 41,
      text: 'Velmora was founded on the salt shore.',
    })
    await expect
      .element(screen.getByText('The chronicle line was amended (text).'))
      .toBeVisible()
  })

  it('hides a line only after confirmation and pins one to the notifications', async () => {
    const { screen, server } = await renderScreen(
      <ChronicleEntry line={LINE} />,
      routes()
    )
    await screen
      .getByRole('button', { name: 'Line actions for epoch 3' })
      .click()
    await screen
      .getByRole('menuitem', { name: 'Hide from the chronicle' })
      .click()
    expect(server.callsTo('POST /api/actions/chronicle:edit')).toHaveLength(0)
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Hide the line' })
      .click()
    await expect
      .poll(() => server.callsTo('POST /api/actions/chronicle:edit').length)
      .toBe(1)
    expect(server.callsTo('POST /api/actions/chronicle:edit')[0].body).toEqual({
      chronicle_id: 41,
      visible: false,
    })
    await screen
      .getByRole('button', { name: 'Line actions for epoch 3' })
      .click()
    await screen.getByRole('menuitem', { name: 'Pin to notifications' }).click()
    await expect
      .poll(
        () =>
          server.callsTo(
            'POST /api/notifications/from-chronicle/{chronicle_id}'
          ).length
      )
      .toBe(1)
    expect(
      server.callsTo('POST /api/notifications/from-chronicle/{chronicle_id}')[0]
        .path
    ).toBe('/api/notifications/from-chronicle/41')
    await expect
      .element(screen.getByText('Pinned to your notifications'))
      .toBeVisible()
  })

  it('offers no editing in a read-only guest world and none when not editable', async () => {
    const guest = await renderScreen(
      <ChronicleEntry line={LINE} />,
      routes({ 'GET /api/state': worldState({ read_only: true }) })
    )
    await guest.screen
      .getByRole('button', { name: 'Line actions for epoch 3' })
      .click()
    await expect
      .element(guest.screen.getByRole('menuitem', { name: 'Amend the line' }))
      .toHaveAttribute('aria-disabled', 'true')
  })

  it('resolves id tokens in a line', async () => {
    const line = {
      ...(LINE as object),
      text: 'The prophecy was found on old stones (thread#5).',
    } as never
    const { screen } = await renderScreen(
      <ChronicleEntry line={line} editable={false} />,
      routes({
        'GET /api/state': worldState({
          threads: [
            {
              id: 5,
              epoch: 1,
              text: 'The drowned bell',
              status: 'open',
              closing_text: null,
              closed_epoch: null,
              progress: 0,
            },
          ],
        }),
      })
    )
    await expect.element(screen.getByText('"The drowned bell"')).toBeVisible()
    expect(document.querySelector('[aria-label^="Line actions"]')).toBeNull()
  })
})

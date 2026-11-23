import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PersuasionsCard } from './cards'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const VIEW = {
  node_id: 501,
  persuasions: [
    {
      id: 3,
      speaker: { id: 501, name: 'Oswin', kind: 'entity', type: 'mortal' },
      target: { id: 502, name: 'Hild', kind: 'entity', type: 'mortal' },
      appeal: 'fear',
      appeal_label: 'Fear',
      aim: 'surrender',
      aim_label: 'Surrender',
      axis: null,
      subject: { id: 30, name: 'Fenwick', kind: 'entity', type: 'settlement' },
      score: 61,
      success: true,
      epoch: 50,
    },
  ],
  appeals: [
    { key: 'belief', label: 'Belief' },
    { key: 'fear', label: 'Fear' },
  ],
  aims: [
    { key: 'belief', label: 'A belief' },
    { key: 'surrender', label: 'Surrender' },
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
    {
      id: 30,
      kind: 'entity',
      type: 'settlement',
      name: 'Fenwick',
      world_id: 1,
    },
  ])
}

describe('arguments', () => {
  beforeEach(resetApi)

  it('shows an argument with its aim and town and calls a besieged town to surrender', async () => {
    serve()
    onApi('POST', '/api/actions/persuasion:attempt', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <PersuasionsCard view={VIEW} blocked={null} hold={false} />
    )
    await expect
      .element(screen.getByText('Fear · surrender · at Fenwick · epoch 50'))
      .toBeVisible()
    await expect.element(screen.getByText('Swayed · 61')).toBeVisible()
    const argue = screen.getByRole('button', { name: 'Argue', exact: true })
    await expect
      .element(argue)
      .toHaveAccessibleDescription('Pick who to argue with.')
    await screen.getByRole('combobox', { name: 'With' }).click()
    await screen.getByRole('option', { name: /Hild/ }).click()
    await screen.getByRole('combobox', { name: 'Aim' }).click()
    await screen.getByRole('option', { name: 'Surrender' }).click()
    await expect
      .element(screen.getByRole('combobox', { name: 'Belief' }))
      .toBeDisabled()
    await expect
      .element(argue)
      .toHaveAccessibleDescription('Pick the besieged town.')
    await screen.getByRole('combobox', { name: 'Besieged town' }).click()
    await screen.getByRole('option', { name: /Fenwick/ }).click()
    await argue.click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/persuasion:attempt'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/persuasion:attempt')[0].body
    ).toMatchObject({
      speaker_id: 501,
      target_id: 502,
      appeal: 'belief',
      aim: 'surrender',
      axis: null,
      subject_id: 30,
    })
  })
})

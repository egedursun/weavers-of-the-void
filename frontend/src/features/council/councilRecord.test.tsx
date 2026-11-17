import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  CouncilRecordControls,
  CouncilRecordForge,
} from './CouncilRecordControls'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

describe('council record controls', () => {
  beforeEach(() => resetApi())

  it('sets down a council with its topic and outcome', async () => {
    onApi('POST', '/api/actions/council_record:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CouncilRecordForge />)
    const button = screen.getByRole('button', { name: 'Set it down' })
    await expect.element(button).toBeDisabled()
    await screen
      .getByLabelText('Set down a council of the gods')
      .fill('Who keeps the tides')
    await screen.getByRole('switch', { name: 'The motion passed' }).click()
    await button.click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/council_record:create'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/council_record:create')[0].body
    ).toEqual({ topic: 'Who keeps the tides', passed: true })
  })

  it('rewrites a council and strikes it only after confirming', async () => {
    onApi('POST', '/api/actions/council_record:edit', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/council_record:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <CouncilRecordControls councilId={4} topic='Old topic' passed={false} />
    )
    const rewrite = screen.getByRole('button', { name: 'Rewrite the record' })
    await expect.element(rewrite).toBeDisabled()
    await screen.getByLabelText('Topic of the council').fill('New topic')
    await rewrite.click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/council_record:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/council_record:edit')[0].body).toEqual(
      { council_id: 4, topic: 'New topic', passed: false }
    )
    await screen
      .getByRole('button', { name: 'Strike it from the record' })
      .click()
    expect(callsTo('POST', '/api/actions/council_record:delete')).toHaveLength(
      0
    )
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Strike it' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/council_record:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/council_record:delete')[0].body
    ).toEqual({ council_id: 4 })
  })
})

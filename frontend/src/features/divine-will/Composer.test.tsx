import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { userEvent } from 'vitest/browser'
import { Input } from '@/components/ui/input'
import { Composer } from './Composer'
import { willActive } from './willFixtures'
import { useWill } from './willStore'

const CAPABILITIES = willActive([]).capabilities

const ROUTES = {
  'GET /api/divine-will/modes': { modes: [] },
  'POST /api/divine-will/cycles': { cycle_id: 4, session_id: 1, ordinal: 1 },
  'POST /api/divine-will/cycles/{cycle_id}/cancel': {},
}

function reset() {
  useWill.setState({ mode: 'command', draft: '', seed: null, live: {} })
}

beforeEach(reset)
afterEach(reset)

function modeRadio(
  screen: Awaited<ReturnType<typeof renderScreen>>['screen'],
  name: string
) {
  return screen.getByRole('radio', { name })
}

describe('Divine Will composer', () => {
  it('switches modes with Tab and Shift+Tab inside the composer', async () => {
    const { screen } = await renderScreen(
      <Composer
        capabilities={CAPABILITIES}
        runningCycleId={null}
        awaiting={false}
      />,
      ROUTES
    )
    const field = screen.getByRole('textbox', {
      name: /Your words to the Divine Will/,
    })
    await field.click()
    await expect
      .element(modeRadio(screen, 'Command'))
      .toHaveAttribute('aria-checked', 'true')
    await userEvent.keyboard('{Tab}')
    await expect
      .element(modeRadio(screen, 'Plan'))
      .toHaveAttribute('aria-checked', 'true')
    await expect.element(field).toHaveFocus()
    await userEvent.keyboard('{Shift>}{Tab}{/Shift}')
    await userEvent.keyboard('{Shift>}{Tab}{/Shift}')
    await expect
      .element(modeRadio(screen, 'Foresight'))
      .toHaveAttribute('aria-checked', 'true')
    expect(useWill.getState().mode).toBe('foresight')
  })

  it('leaves Tab alone in other fields and during an input method composition', async () => {
    const { screen } = await renderScreen(
      <>
        <Input aria-label='Another field' />
        <Composer
          capabilities={CAPABILITIES}
          runningCycleId={null}
          awaiting={false}
        />
      </>,
      ROUTES
    )
    await screen.getByRole('textbox', { name: 'Another field' }).click()
    await userEvent.keyboard('{Tab}')
    expect(useWill.getState().mode).toBe('command')
    const field = screen.getByRole('textbox', {
      name: /Your words to the Divine Will/,
    })
    const element = field.element() as HTMLTextAreaElement
    element.focus()
    element.dispatchEvent(
      new KeyboardEvent('keydown', {
        key: 'Tab',
        bubbles: true,
        cancelable: true,
        isComposing: true,
      })
    )
    expect(useWill.getState().mode).toBe('command')
  })

  it('sends with Enter, breaks lines with Shift+Enter and clears the draft', async () => {
    const { screen, server } = await renderScreen(
      <Composer
        capabilities={CAPABILITIES}
        runningCycleId={null}
        awaiting={false}
      />,
      ROUTES
    )
    const field = screen.getByRole('textbox', {
      name: /Your words to the Divine Will/,
    })
    await expect
      .element(screen.getByRole('button', { name: 'Send' }))
      .toHaveAttribute('aria-description', 'Write what you wish first.')
    await field.click()
    await userEvent.keyboard('First line{Shift>}{Enter}{/Shift}second line')
    await expect.element(field).toHaveValue('First line\nsecond line')
    expect(server.callsTo('POST /api/divine-will/cycles')).toHaveLength(0)
    await userEvent.keyboard('{Enter}')
    await expect
      .poll(() => server.callsTo('POST /api/divine-will/cycles'))
      .toHaveLength(1)
    expect(server.callsTo('POST /api/divine-will/cycles')[0].body).toEqual({
      text: 'First line\nsecond line',
      mode: 'command',
      attachment_ids: [],
    })
    await expect.element(field).toHaveValue('')
  })

  it('offers Stop while a cycle runs and explains why sending waits', async () => {
    useWill.setState({ draft: 'More' })
    const { screen, server } = await renderScreen(
      <Composer
        capabilities={CAPABILITIES}
        runningCycleId={5}
        awaiting={false}
      />,
      ROUTES
    )
    await expect
      .element(screen.getByRole('button', { name: 'Send' }))
      .not.toBeInTheDocument()
    await screen.getByRole('button', { name: 'Stop' }).click()
    await expect
      .poll(() =>
        server
          .callsTo('POST /api/divine-will/cycles/{cycle_id}/cancel')
          .map((call) => call.path)
      )
      .toEqual(['/api/divine-will/cycles/5/cancel'])
  })

  it('waits for an approval before it sends again', async () => {
    useWill.setState({ draft: 'More' })
    const { screen } = await renderScreen(
      <Composer capabilities={CAPABILITIES} runningCycleId={null} awaiting />,
      ROUTES
    )
    await expect
      .element(screen.getByRole('button', { name: 'Send' }))
      .toHaveAttribute(
        'aria-description',
        'An act waits for your approval above; approve or decline it first.'
      )
  })

  it('tells that images cannot be seen and honours the file limit', async () => {
    const { screen } = await renderScreen(
      <Composer
        capabilities={{ ...CAPABILITIES, upload_max_files: 0 }}
        runningCycleId={null}
        awaiting={false}
      />,
      ROUTES
    )
    await expect
      .element(screen.getByText('Cannot see images'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: 'Attach' }))
      .toHaveAttribute('aria-description', 'Only 0 files fit in one message.')
  })
})

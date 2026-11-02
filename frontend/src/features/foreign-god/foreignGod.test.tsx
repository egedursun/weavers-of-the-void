import { ruleList, worldState } from '@/test-utils/fixtures'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, describe, expect, it } from 'vitest'
import { userEvent } from 'vitest/browser'
import { CompareToggle } from '@/features/pantheon/CompareCards'
import { DepthView } from '@/features/pantheon/DepthView'
import { AttitudeBar } from './AttitudeBar'
import { ForeignGodCard } from './ForeignGodCard'
import { ForeignGodPowerPanel } from './ForeignGodPowerPanel'

const GOD = {
  id: 3,
  name: 'Old Nyx',
  title: 'Mother of Silence',
  domain_primary: 'death',
  domain_secondary: null,
  world_id: 1,
  power: 7,
  faith: 12.5,
  stance: -4,
  status: 'awake',
  contacted: false,
  description: 'She hums beneath the salt.',
}

function detail(
  overrides: Record<string, unknown> = {},
  god: Record<string, unknown> = {}
) {
  return {
    god: { ...GOD, ...god },
    powers: [],
    kill_cost: 150,
    drain_amount: 2,
    drain_gain: 30,
    world: { id: 1, name: 'Aerona' },
    ...overrides,
  } as never
}

function routes(
  state: Record<string, unknown> = {},
  extra: Record<string, unknown> = {}
) {
  return {
    'GET /api/state': worldState({ creator: { essence: 500 }, ...state }),
    'GET /api/rules': ruleList({
      'pantheon.son_war_max_attitude': 3,
      'pantheon.foreign_friend_min_attitude': 5,
    }),
    'GET /api/names': [
      { id: 21, name: 'Mara', kind: 'entity', type: 'mortal', world_id: 1 },
      {
        id: 22,
        name: 'Salt Temple',
        kind: 'entity',
        type: 'structure',
        world_id: 1,
      },
    ],
    'GET /api/catalogue': { domains: [{ key: 'death', label: 'Death' }] },
    ...extra,
  }
}

afterEach(() => localStorage.clear())

describe('foreign god power panel', () => {
  it('shows the gain of draining and disables it when no power is left', async () => {
    const { screen } = await renderScreen(
      <ForeignGodPowerPanel detail={detail()} />,
      routes()
    )
    await expect
      .element(screen.getByLabelText('gain 30 essence'))
      .toBeInTheDocument()
  })

  it('disables draining when no power is left', async () => {
    const { screen } = await renderScreen(
      <ForeignGodPowerPanel detail={detail({ drain_amount: 0 })} />,
      routes()
    )
    await expect
      .element(screen.getByRole('button', { name: /Drain power/ }))
      .toHaveAttribute('aria-description', 'No power left to drain.')
  })

  it('drains only after confirmation', async () => {
    const { screen, server } = await renderScreen(
      <ForeignGodPowerPanel detail={detail()} />,
      routes(
        {},
        { 'POST /api/foreign-gods/3/drain': { action: 'drain', message: 'ok' } }
      )
    )
    await screen.getByRole('button', { name: /Drain power/ }).click()
    expect(server.callsTo('POST /api/foreign-gods/3/drain')).toHaveLength(0)
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: /Drain power/ })
      .click()
    await expect.element(screen.getByText('Power drained')).toBeInTheDocument()
    expect(server.callsTo('POST /api/foreign-gods/3/drain')).toHaveLength(1)
  })

  it('kills with a reason and devour after confirmation, priced by the server', async () => {
    const { screen, server } = await renderScreen(
      <ForeignGodPowerPanel detail={detail()} />,
      routes(
        {},
        { 'POST /api/foreign-gods/3/kill': { action: 'kill', message: 'ok' } }
      )
    )
    await expect
      .element(screen.getByLabelText('costs 150 essence'))
      .toBeInTheDocument()
    await screen
      .getByLabelText('Why? Written in the chronicle')
      .fill('She hoarded the dead')
    await screen.getByLabelText('Devour: the power passes to you').click()
    await screen.getByRole('button', { name: /^Kill/ }).click()
    await expect
      .element(screen.getByRole('heading', { name: 'Kill Old Nyx?' }))
      .toBeInTheDocument()
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: /^Kill/ })
      .click()
    await expect.element(screen.getByText('Old Nyx died')).toBeInTheDocument()
    expect(server.callsTo('POST /api/foreign-gods/3/kill')[0].body).toEqual({
      reason: 'She hoarded the dead',
      devour: true,
    })
  })

  it('refuses to kill without essence and notes deathless gods', async () => {
    const { screen } = await renderScreen(
      <ForeignGodPowerPanel
        detail={detail({
          powers: [
            { slot: 1, name: 'x', effect: 'deathless', description: '' },
          ],
        })}
      />,
      routes({ creator: { essence: 10 } })
    )
    await expect
      .element(screen.getByRole('button', { name: /^Kill/ }))
      .toHaveAttribute('aria-description', '150 essence needed; you have 10.')
    await expect
      .element(screen.getByText('Deathless: killing costs more.'))
      .toBeInTheDocument()
  })

  it('offers waking only for sleeping or defeated gods', async () => {
    const { screen } = await renderScreen(
      <ForeignGodPowerPanel detail={detail({}, { status: 'asleep' })} />,
      routes()
    )
    await expect
      .element(screen.getByRole('button', { name: 'Wake' }))
      .toBeInTheDocument()
  })

  it('does not offer waking an awake god', async () => {
    const { screen } = await renderScreen(
      <ForeignGodPowerPanel detail={detail()} />,
      routes()
    )
    await expect
      .element(screen.getByRole('button', { name: 'Raise new land' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: 'Wake' }))
      .not.toBeInTheDocument()
  })

  it('needs a picked mortal to strike', async () => {
    const { screen } = await renderScreen(
      <ForeignGodPowerPanel detail={detail()} />,
      routes()
    )
    await expect
      .element(screen.getByRole('button', { name: 'Strike' }))
      .toHaveAttribute('aria-description', 'Pick a mortal.')
    await expect
      .element(screen.getByRole('button', { name: 'Raid' }))
      .toHaveAttribute('aria-description', 'Pick a temple.')
  })

  it('points a dead god to the status edit for revival', async () => {
    const { screen } = await renderScreen(
      <ForeignGodPowerPanel
        detail={detail({}, { status: 'dead', death_epoch: 6 })}
      />,
      routes()
    )
    await expect
      .element(screen.getByText('Old Nyx died · Epoch 6'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText(/change the status in the edit form/))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: /Drain power/ }))
      .not.toBeInTheDocument()
  })

  it('is read-only in a guest world', async () => {
    const { screen } = await renderScreen(
      <ForeignGodPowerPanel detail={detail()} />,
      routes({ read_only: true })
    )
    await expect
      .element(screen.getByRole('button', { name: /Drain power/ }))
      .toHaveAttribute('aria-description', 'A guest world is open read-only.')
  })
})

describe('attitude bar', () => {
  const cases: [number, string][] = [
    [-3, 'Hostile'],
    [-1, 'Suspicious'],
    [0, 'Neutral'],
    [2, 'Close'],
    [5, 'Friend'],
  ]
  for (const [stance, label] of cases)
    it(`reads ${stance} as ${label} using the world rules`, async () => {
      const { screen } = await renderScreen(
        <AttitudeBar stance={stance} />,
        routes()
      )
      await expect
        .element(screen.getByText(label, { exact: true }))
        .toBeInTheDocument()
    })
})

describe('foreign god card', () => {
  it('shows status, world, power, faith, attitude and the no-contact chip', async () => {
    const { screen } = await renderScreen(
      <ForeignGodCard god={GOD as never} worldName='Aerona' />,
      routes()
    )
    await expect
      .element(screen.getByRole('link', { name: 'Old Nyx' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Mother of Silence'))
      .toBeInTheDocument()
    await expect.element(screen.getByText('Awake')).toBeInTheDocument()
    await expect.element(screen.getByText('Aerona')).toBeInTheDocument()
    await expect.element(screen.getByLabelText('Power 7')).toBeInTheDocument()
    await expect
      .element(screen.getByLabelText('Faith 12.5'))
      .toBeInTheDocument()
    await expect.element(screen.getByText('No contact yet')).toBeInTheDocument()
    await expect
      .element(screen.getByText('She hums beneath the salt.'))
      .toBeInTheDocument()
  })
})

describe('depth view', () => {
  const depth = {
    history: 'Born of salt.',
    names: [{ name: 'Nyx', used_by: 'Salt clans', meaning: 'night' }],
    secrets: ['She fears the sea'],
    fears: [],
    taboos: ['Never speak her name'],
    gifts: [],
    desire: 'To be remembered',
    sayings: [{ form: 'proverb', text: 'Salt keeps' }],
    rumours: [],
    hidden_truth: 'She is the first dead god.',
    view_of_pantheon: 'Unworthy',
    worship: 'Whispered',
    epoch: 4,
  } as never

  it('renders its blocks and hides the empty ones', async () => {
    const { screen } = await renderScreen(<DepthView depth={depth} />)
    await expect
      .element(screen.getByText('Deepened in Epoch 4'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Salt clans · night'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('She fears the sea'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('proverb: Salt keeps'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Fears', { exact: true }))
      .not.toBeInTheDocument()
    await expect
      .element(screen.getByText('Hidden truth (only you know)'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('She is the first dead god.'))
      .toBeInTheDocument()
  })
})

describe('compare toggle', () => {
  it('limits the comparison to three sons and remembers the choice in the browser', async () => {
    const { screen } = await renderScreen(
      <>
        <CompareToggle sonId={1} name='A' />
        <CompareToggle sonId={2} name='B' />
        <CompareToggle sonId={3} name='C' />
        <CompareToggle sonId={4} name='D' />
      </>
    )
    for (const name of ['A', 'B', 'C'])
      await screen.getByRole('button', { name: `Compare ${name}` }).click()
    await expect
      .element(screen.getByRole('button', { name: 'Compare D' }))
      .toHaveAttribute('aria-disabled', 'true')
    expect(localStorage.getItem('aerona.compare')).toBe('[1,2,3]')
    await userEvent.click(
      screen.getByRole('button', { name: 'Remove B from comparison' })
    )
    await expect
      .element(screen.getByRole('button', { name: 'Compare D' }))
      .toBeEnabled()
    expect(localStorage.getItem('aerona.compare')).toBe('[1,3]')
  })
})

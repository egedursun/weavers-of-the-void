import { ruleList, worldState } from '@/test-utils/fixtures'
import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { OuterBargainForm } from './OuterBargainForm'
import { SiblingSchemes } from './SiblingSchemes'

function son(
  id: number,
  name: string,
  overrides: Record<string, unknown> = {}
) {
  return {
    id,
    name,
    status: 'active',
    essence: 120,
    outer_bargain_forbidden: false,
    ...overrides,
  } as never
}

const RULES = ruleList({
  'death.sibling_rite_cost': 45,
  'death.sibling_descent_cost': 70,
  'death.sibling_bargain_cost': 60,
  'death.scatter_bones_cost': 30,
  'death.scatter_bones_devotion_loss': 35,
  'son_tools.outer_bargain_per_epoch': 1,
})

const DONE = { action: 'done', message: 'It is done.' }

describe('sibling schemes for a dead son', () => {
  it('lets an awake sibling scheme for the return with the chosen kind', async () => {
    const dead = son(10, 'Orveth', { status: 'dead' })
    const { screen, server } = await renderScreen(
      <SiblingSchemes son={dead} />,
      {
        'GET /api/state': worldState({ creator: { essence: 100 } }),
        'GET /api/rules': RULES,
        'GET /api/sons': [{ son: son(7, 'Ithren') }, { son: dead }],
        'POST /api/sons/{son_id}/scheme': DONE,
      }
    )
    await expect
      .element(screen.getByRole('button', { name: 'Scheme for their return' }))
      .toHaveAttribute('aria-description', 'Choose a sibling first.')
    await screen.getByRole('combobox', { name: 'Sibling' }).click()
    await screen.getByRole('option', { name: /Ithren/ }).click()
    await screen.getByRole('radio', { name: 'Descent below' }).click()
    await screen
      .getByRole('button', { name: 'Scheme for their return' })
      .click()
    await expect
      .poll(() => server.callsTo('POST /api/sons/{son_id}/scheme').length)
      .toBe(1)
    const call = server.callsTo('POST /api/sons/{son_id}/scheme')[0]
    expect(call.path).toBe('/api/sons/10/scheme')
    expect(call.body).toEqual({ sibling_id: 7, kind: 'descent' })
  })

  it('scatters the bones only after confirmation', async () => {
    const dead = son(10, 'Orveth', { status: 'dead' })
    const { screen, server } = await renderScreen(
      <SiblingSchemes son={dead} />,
      {
        'GET /api/state': worldState({ creator: { essence: 100 } }),
        'GET /api/rules': RULES,
        'GET /api/sons': [{ son: son(7, 'Ithren') }, { son: dead }],
        'POST /api/sons/{son_id}/scatter-bones': DONE,
      }
    )
    await screen.getByRole('combobox', { name: 'Sibling' }).click()
    await screen.getByRole('option', { name: /Ithren/ }).click()
    await screen.getByRole('button', { name: 'Scatter their bones' }).click()
    expect(
      server.callsTo('POST /api/sons/{son_id}/scatter-bones')
    ).toHaveLength(0)
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Scatter them' })
      .click()
    await expect
      .poll(
        () => server.callsTo('POST /api/sons/{son_id}/scatter-bones').length
      )
      .toBe(1)
    expect(
      server.callsTo('POST /api/sons/{son_id}/scatter-bones')[0].body
    ).toEqual({ sibling_id: 7 })
  })
})

describe('outer bargains', () => {
  it('forbids and allows a son to bargain', async () => {
    const free = await renderScreen(
      <OuterBargainForm sons={[son(7, 'Ithren')]} fixedSonId={7} />,
      {
        'GET /api/state': worldState({ creator: { essence: 100 } }),
        'GET /api/rules': RULES,
        'GET /api/names': [],
        'POST /api/actions/son:outer_bargain': DONE,
      }
    )
    await expect
      .element(free.screen.getByText('Free to bargain'))
      .toBeInTheDocument()
    await expect
      .element(free.screen.getByRole('button', { name: 'Force the bargain' }))
      .toHaveAttribute('aria-description', 'Choose an outer being first.')
    await free.screen.getByRole('button', { name: 'Forbid bargaining' }).click()
    await expect
      .poll(
        () => free.server.callsTo('POST /api/actions/son:outer_bargain').length
      )
      .toBe(1)
    expect(
      free.server.callsTo('POST /api/actions/son:outer_bargain')[0].body
    ).toMatchObject({ son_id: 7, mode: 'forbid' })
  })

  it('offers to allow a son who is forbidden', async () => {
    const { screen } = await renderScreen(
      <OuterBargainForm
        sons={[son(7, 'Ithren', { outer_bargain_forbidden: true })]}
        fixedSonId={7}
      />,
      {
        'GET /api/state': worldState({ creator: { essence: 100 } }),
        'GET /api/rules': RULES,
        'GET /api/names': [],
      }
    )
    await expect
      .element(screen.getByText('Forbidden to bargain'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: 'Allow bargaining' }))
      .toBeInTheDocument()
  })
})

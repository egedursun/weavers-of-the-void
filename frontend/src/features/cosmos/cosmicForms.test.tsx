import {
  ACCEPTED_ACTION,
  apiCalls,
  callsTo,
  failure,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { userEvent } from 'vitest/browser'
import actions from '../../../e2e/fixtures/actions.json'
import cosmosFixture from '../../../e2e/fixtures/cosmos.json'
import { IgniteStarForm } from './IgniteStarForm'
import { OpenRouteForm } from './OpenRouteForm'
import { SendVoyageForm } from './SendVoyageForm'
import { type CosmosData } from './api'
import { indexCosmos } from './model/cosmosModel'
import { buildRuleBook, type RuleBook } from './model/rules'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const COSMOS = cosmosFixture.cosmos as unknown as CosmosData
const RULES: RuleBook = buildRuleBook(cosmosFixture.rules as never)
const INDEX = indexCosmos(COSMOS)

function stateWith(essence: number, epochRunning = false, readOnly = false) {
  return {
    creator: { essence },
    epoch_running: epochRunning,
    read_only: readOnly,
    world: { epoch: 6 },
  }
}

function serve(essence = 500, epochRunning = false, readOnly = false) {
  onApi('GET', '/api/state', stateWith(essence, epochRunning, readOnly))
  onApi('GET', '/api/actions', actions)
  onApi('POST', '/api/cosmic/hang-star', ACCEPTED_ACTION)
  onApi('POST', '/api/routes', ACCEPTED_ACTION)
}

describe('cosmic action gating', () => {
  beforeEach(resetApi)

  it('shows the ignite cost from the rules and runs the action with the typed fields', async () => {
    serve()
    const { screen } = await renderApp(
      <IgniteStarForm index={INDEX} rules={RULES} />
    )
    await expect.element(screen.getByText('80')).toBeInTheDocument()
    await screen.getByLabelText('Name').fill('  Lantern of Vel  ')
    await screen
      .getByLabelText('Description')
      .fill('A pale eye only the dead can see')
    await screen.getByRole('button', { name: /Ignite/ }).click()
    await expect
      .element(screen.getByText('A new star ignited'))
      .toBeInTheDocument()
    expect(callsTo('POST', '/api/cosmic/hang-star')[0]?.body).toEqual({
      name: 'Lantern of Vel',
      star_type: 'yellow_dwarf',
      description: 'A pale eye only the dead can see',
      world_id: null,
      galaxy_id: null,
    })
  })

  it('hangs a void star in the galaxy shown and turns the view to where it landed', async () => {
    serve()
    onApi('POST', '/api/cosmic/hang-star', {
      ...ACCEPTED_ACTION,
      values: { galaxy_id: 9 },
    })
    const landed = vi.fn()
    const { screen } = await renderApp(
      <IgniteStarForm
        index={INDEX}
        rules={RULES}
        galaxyId={9}
        onGalaxy={landed}
      />
    )
    await screen.getByRole('button', { name: /Ignite/ }).click()
    await expect.poll(() => landed.mock.calls).toEqual([[9]])
    expect(callsTo('POST', '/api/cosmic/hang-star')[0]?.body).toMatchObject({
      world_id: null,
      galaxy_id: 9,
    })
  })

  it('lets a star set in a world’s sky follow that world’s galaxy', async () => {
    serve()
    const world = INDEX.worlds[0].world
    const { screen } = await renderApp(
      <IgniteStarForm index={INDEX} rules={RULES} galaxyId={9} />
    )
    await screen.getByLabelText('Where it hangs').click()
    await screen
      .getByRole('option', { name: `In the sky of ${world.name}` })
      .click()
    await expect
      .element(screen.getByLabelText('Where it hangs'))
      .toHaveTextContent(`In the sky of ${world.name}`)
    await screen.getByRole('button', { name: /Ignite/ }).click()
    await expect
      .poll(() => callsTo('POST', '/api/cosmic/hang-star'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/cosmic/hang-star')[0]?.body).toMatchObject({
      world_id: world.id,
      galaxy_id: null,
    })
  })

  it('disables the action with the missing essence as the reason', async () => {
    serve(10)
    const { screen } = await renderApp(
      <IgniteStarForm index={INDEX} rules={RULES} />
    )
    const button = screen.getByRole('button', { name: /Ignite/ })
    await expect.element(button).toHaveAttribute('aria-disabled', 'true')
    await expect
      .element(button)
      .toHaveAttribute('aria-description', '80 essence needed; you have 10.')
    await button.click({ force: true })
    expect(callsTo('POST', '/api/cosmic/hang-star')).toHaveLength(0)
  })

  it('stays closed while an epoch is running', async () => {
    serve(500, true)
    const { screen } = await renderApp(
      <IgniteStarForm index={INDEX} rules={RULES} />
    )
    await expect
      .element(screen.getByRole('button', { name: /Ignite/ }))
      .toHaveAttribute(
        'aria-description',
        'An epoch is running; this opens when it is done.'
      )
  })

  it('stays closed in a read-only guest world', async () => {
    serve(500, false, true)
    const { screen } = await renderApp(
      <IgniteStarForm index={INDEX} rules={RULES} />
    )
    await expect
      .element(screen.getByRole('button', { name: /Ignite/ }))
      .toHaveAttribute('aria-description', 'A guest world is open read-only.')
  })

  it('reports the API error message when the action fails', async () => {
    serve()
    onApi(
      'POST',
      '/api/cosmic/hang-star',
      failure(409, 'The sky is too crowded.')
    )
    const { screen } = await renderApp(
      <IgniteStarForm index={INDEX} rules={RULES} />
    )
    await screen.getByRole('button', { name: /Ignite/ }).click()
    await expect
      .element(screen.getByText('The sky is too crowded.'))
      .toBeInTheDocument()
  })

  it('offers an undo link when the ledger recorded the action', async () => {
    serve()
    onApi('POST', '/api/cosmic/hang-star', {
      ...ACCEPTED_ACTION,
      ledger_entry_id: 31,
    })
    onApi('POST', '/api/ledger/31/undo', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <IgniteStarForm index={INDEX} rules={RULES} />
    )
    await screen.getByRole('button', { name: /Ignite/ }).click()
    const undo = screen.getByRole('button', { name: 'Undo' })
    await expect.element(undo).toBeVisible()
    await expect
      .poll(async () => {
        if (callsTo('POST', '/api/ledger/31/undo').length === 0)
          await undo.click()
        return callsTo('POST', '/api/ledger/31/undo').length
      })
      .toBe(1)
    await expect.element(screen.getByText('Undone')).toBeInTheDocument()
  })
})

describe('open route form', () => {
  beforeEach(resetApi)

  it('opens a route between two chosen worlds with the chosen method', async () => {
    serve()
    const { screen } = await renderApp(
      <OpenRouteForm index={INDEX} rules={RULES} worldId={3} />
    )
    await screen.getByRole('button', { name: /Open the route/ }).click()
    await expect
      .element(screen.getByText('A new route was opened'))
      .toBeInTheDocument()
    const body = callsTo('POST', '/api/routes')[0]?.body as Record<
      string,
      unknown
    >
    expect(body.first_world_id).toBe(3)
    expect(body.second_world_id).not.toBe(3)
    expect(body.method).toBe('ancient_gate')
  })

  it('needs two remembered worlds', async () => {
    serve()
    const single = indexCosmos({
      ...COSMOS,
      worlds: COSMOS.worlds.slice(0, 1),
      routes: [],
      journeys: [],
    })
    const { screen } = await renderApp(
      <OpenRouteForm index={single} rules={RULES} worldId={3} />
    )
    await expect
      .element(screen.getByRole('button', { name: /Open the route/ }))
      .toHaveAttribute(
        'aria-description',
        'Two remembered worlds are needed for a route.'
      )
  })
})

describe('send voyage form', () => {
  beforeEach(resetApi)

  it('asks for a traveller before it can run', async () => {
    serve()
    const { screen } = await renderApp(
      <SendVoyageForm index={INDEX} rules={RULES} defaultWorldId={3} />
    )
    const button = screen.getByRole('button', { name: /Set out/ })
    await expect.element(button).toHaveAttribute('aria-disabled', 'true')
  })

  it('sends the chosen traveller along the open route with the typed share', async () => {
    serve()
    onApi('POST', '/api/entities/:id/expedition', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <SendVoyageForm index={INDEX} rules={RULES} defaultWorldId={3} />
    )
    await screen.getByLabelText('Traveller').click()
    await screen.getByRole('option').first().click()
    await userEvent.fill(screen.getByLabelText('Share of the population'), '10')
    await screen.getByRole('button', { name: /Set out/ }).click()
    await expect.element(screen.getByText('Voyage set out')).toBeInTheDocument()
    const call = apiCalls.find((item) =>
      /\/api\/entities\/\d+\/expedition/.test(item.path)
    )
    expect(call?.body).toMatchObject({ percent: 10, intent: 'exploration' })
  })

  it('rejects a percent above the rule limit', async () => {
    serve()
    const { screen } = await renderApp(
      <SendVoyageForm index={INDEX} rules={RULES} defaultWorldId={3} />
    )
    await screen.getByLabelText('Traveller').click()
    await screen.getByRole('option').first().click()
    await userEvent.fill(
      screen.getByLabelText('Share of the population'),
      '1000'
    )
    await expect
      .element(screen.getByRole('button', { name: /Set out/ }))
      .toHaveAttribute(
        'aria-description',
        expect.stringMatching(/whole percent from 1 to/)
      )
  })
})

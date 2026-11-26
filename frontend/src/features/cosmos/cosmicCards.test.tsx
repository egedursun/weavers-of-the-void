import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { ruleMap } from '@/test-utils/ruleValues'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import actions from '../../../e2e/fixtures/actions.json'
import cosmosFixture from '../../../e2e/fixtures/cosmos.json'
import { CreatorHandPanel } from './CreatorHandPanel'
import { StarCard } from './StarCard'
import { VoyageCard } from './VoyageCard'
import { type CosmosData } from './api'
import { indexCosmos } from './model/cosmosModel'
import { buildRuleBook } from './model/rules'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const COSMOS = cosmosFixture.cosmos as unknown as CosmosData
const RULES = buildRuleBook(ruleMap(cosmosFixture.rules))
const INDEX = indexCosmos(COSMOS)

function serve(essence = 500) {
  onApi('GET', '/api/state', {
    creator: { essence },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/actions', actions)
}

function worldItem(id: number) {
  const item = INDEX.worlds.find((entry) => entry.world.id === id)
  if (!item) throw new Error(`world ${id} missing`)
  return item
}

describe('creator hand panel', () => {
  beforeEach(resetApi)

  it('cleanses leakage for the rule cost and posts the world', async () => {
    serve()
    onApi('POST', '/api/cosmic/cleanse-leak', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <CreatorHandPanel item={worldItem(5)} isHome={false} rules={RULES} />
    )
    await screen.getByRole('button', { name: /Cleanse leakage/ }).click()
    await expect
      .element(screen.getByText('Leakage cleansed'))
      .toBeInTheDocument()
    expect(callsTo('POST', '/api/cosmic/cleanse-leak')[0]?.body).toEqual({
      world_id: 5,
    })
  })

  it('explains cleansing power from the rule amount', async () => {
    serve()
    const { screen } = await renderApp(
      <CreatorHandPanel item={worldItem(5)} isHome={false} rules={RULES} />
    )
    await expect
      .element(screen.getByText(/Cleansing lowers leakage by/))
      .toBeInTheDocument()
  })

  it('buries a world only after the confirmation dialog', async () => {
    serve()
    onApi('POST', '/api/cosmic/forget-world', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <CreatorHandPanel item={worldItem(5)} isHome={false} rules={RULES} />
    )
    await screen.getByRole('button', { name: /Bury in oblivion/ }).click()
    expect(callsTo('POST', '/api/cosmic/forget-world')).toHaveLength(0)
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Bury in mist' })
      .click()
    await expect
      .element(screen.getByText(/was buried in oblivion/))
      .toBeInTheDocument()
    expect(callsTo('POST', '/api/cosmic/forget-world')).toHaveLength(1)
  })

  it('never offers oblivion for the home world', async () => {
    serve()
    const { screen } = await renderApp(
      <CreatorHandPanel item={worldItem(3)} isHome rules={RULES} />
    )
    await expect
      .element(screen.getByText(/The first world cannot be buried/))
      .toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /Bury in oblivion/ }).elements()
    ).toHaveLength(0)
  })

  it('offers to remember a forgotten world instead of wrath', async () => {
    serve()
    onApi('PATCH', '/api/worlds/9', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <CreatorHandPanel item={worldItem(9)} isHome={false} rules={RULES} />
    )
    expect(screen.getByText('World wrath').elements()).toHaveLength(0)
    await screen.getByRole('button', { name: /Remember this world/ }).click()
    await expect
      .element(screen.getByText(/is remembered again/))
      .toBeInTheDocument()
    expect(callsTo('PATCH', '/api/worlds/9')[0]?.body).toEqual({
      discovery: 'known',
      automatic_mortal_agents: false,
    })
  })

  it('brings wrath down on every region with the chosen disaster after confirming', async () => {
    serve()
    onApi('POST', '/api/worlds/5/wrath', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <CreatorHandPanel item={worldItem(5)} isHome={false} rules={RULES} />
    )
    await screen.getByRole('combobox', { name: 'Disaster' }).click()
    await screen.getByRole('option', { name: 'Flood' }).click()
    await screen
      .getByRole('button', { name: /Bring down on the whole world/ })
      .click()
    await expect
      .element(screen.getByText(/Flood strikes every region at/))
      .toBeInTheDocument()
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Bring it down' })
      .click()
    await expect.element(screen.getByText(/tasted wrath/)).toBeInTheDocument()
    expect(callsTo('POST', '/api/worlds/5/wrath')[0]?.body).toEqual({
      disaster: 'flood',
    })
  })

  it('blocks wrath when the essence is below the rule cost', async () => {
    serve(1)
    const { screen } = await renderApp(
      <CreatorHandPanel item={worldItem(5)} isHome={false} rules={RULES} />
    )
    await expect
      .element(
        screen.getByRole('button', { name: /Bring down on the whole world/ })
      )
      .toHaveAttribute(
        'aria-description',
        expect.stringMatching(/essence needed; you have 1/)
      )
  })

  it('summons an outer being only after confirming', async () => {
    serve()
    onApi('POST', '/api/actions/horror:outer_being', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <CreatorHandPanel item={worldItem(5)} isHome={false} rules={RULES} />
    )
    await screen.getByRole('button', { name: /Summon an outer being/ }).click()
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Summon' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/horror:outer_being').length)
      .toBe(1)
  })
})

describe('star card', () => {
  beforeEach(resetApi)

  const deadStar = COSMOS.stars.find((star) => star.id === 10)!
  const liveStar = COSMOS.stars.find((star) => star.id === 11)!

  it('re-ignites a dead star and describes the rule effect', async () => {
    serve()
    onApi('POST', '/api/cosmic/rekindle-star', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <StarCard
        star={deadStar}
        index={INDEX}
        rules={RULES}
        onSelectWorld={vi.fn()}
      />
    )
    await expect
      .element(screen.getByText(/The star burns again at brightness/))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: /Re-ignite/ }).click()
    await expect
      .element(screen.getByText('The dead star burns again'))
      .toBeInTheDocument()
    expect(callsTo('POST', '/api/cosmic/rekindle-star')[0]?.body).toEqual({
      star_id: 10,
    })
  })

  it('offers re-ignition only for dead stars', async () => {
    serve()
    const { screen } = await renderApp(
      <StarCard
        star={liveStar}
        index={INDEX}
        rules={RULES}
        onSelectWorld={vi.fn()}
      />
    )
    expect(
      screen.getByRole('button', { name: /Re-ignite/ }).elements()
    ).toHaveLength(0)
  })

  it('selects a world from the list of worlds in its orbit', async () => {
    serve()
    const onSelectWorld = vi.fn()
    const { screen } = await renderApp(
      <StarCard
        star={liveStar}
        index={INDEX}
        rules={RULES}
        onSelectWorld={onSelectWorld}
      />
    )
    await screen.getByRole('button', { name: /Brightmoor/ }).click()
    expect(onSelectWorld).toHaveBeenCalledWith(12)
  })

  it('removes an unorbited star after confirming and mentions the ledger undo', async () => {
    serve()
    onApi('DELETE', '/api/stars/99', ACCEPTED_ACTION)
    const lonely = { ...liveStar, id: 99, name: 'Lonely Spark' }
    const { screen } = await renderApp(
      <StarCard
        star={lonely}
        index={INDEX}
        rules={RULES}
        onSelectWorld={vi.fn()}
      />
    )
    await expect
      .element(screen.getByText(/can be undone from the ledger/).first())
      .toBeInTheDocument()
    await screen.getByRole('button', { name: /Remove from the sky/ }).click()
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Remove' })
      .click()
    await expect
      .element(screen.getByText('Lonely Spark was removed from the sky'))
      .toBeInTheDocument()
  })

  it('hides removal while a world still orbits the star', async () => {
    serve()
    const { screen } = await renderApp(
      <StarCard
        star={liveStar}
        index={INDEX}
        rules={RULES}
        onSelectWorld={vi.fn()}
      />
    )
    expect(
      screen.getByRole('button', { name: /Remove from the sky/ }).elements()
    ).toHaveLength(0)
  })
})

describe('voyage card', () => {
  beforeEach(resetApi)

  const underway = COSMOS.journeys.find(
    (journey) => journey.status === 'underway'
  )!
  const arrived = COSMOS.journeys.find(
    (journey) => journey.status === 'arrived'
  )!

  it('recalls a voyage under way only after confirming', async () => {
    serve()
    onApi('POST', `/api/voyages/${underway.id}/recall`, ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <VoyageCard journey={underway} index={INDEX} />
    )
    await expect
      .element(screen.getByRole('progressbar', { name: 'Voyage progress' }))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: /Recall/ }).click()
    expect(callsTo('POST', `/api/voyages/${underway.id}/recall`)).toHaveLength(
      0
    )
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Recall' })
      .click()
    await expect
      .element(screen.getByText('Voyage recalled'))
      .toBeInTheDocument()
  })

  it('shows an arrived voyage without a recall control', async () => {
    serve()
    const { screen } = await renderApp(
      <VoyageCard journey={arrived} index={INDEX} />
    )
    expect(
      screen.getByRole('button', { name: /Recall/ }).elements()
    ).toHaveLength(0)
    await expect
      .element(screen.getByText(`Set out in epoch ${arrived.start_epoch}`))
      .toBeInTheDocument()
  })

  it('shows that a storm closed the route under a voyage', async () => {
    serve()
    const closed = {
      ...COSMOS,
      routes: COSMOS.routes.map((route) =>
        route.id === underway.route_id
          ? {
              ...route,
              active: false,
              closure: 'severed',
              temp_closed_until_epoch: 9,
              status: {
                open: false,
                state: 'severed',
                reason: 'A storm severed the route.',
                opens_epoch: 9,
                closes_epoch: null,
              },
            }
          : route
      ),
    } as unknown as CosmosData
    const { screen } = await renderApp(
      <VoyageCard journey={underway} index={indexCosmos(closed)} />
    )
    await expect
      .element(screen.getByText('Waiting for the seam to close'))
      .toBeInTheDocument()
  })
})

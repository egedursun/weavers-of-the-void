import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import actions from '../../../e2e/fixtures/actions.json'
import cosmosFixture from '../../../e2e/fixtures/cosmos.json'
import { EconomyControls } from './EconomyControls'
import { HorizonSection } from './HorizonSection'
import { StarCard } from './StarCard'
import { WorldLaws } from './WorldLore'
import { type CosmosData } from './api'
import { indexCosmos } from './model/cosmosModel'
import { buildRuleBook } from './model/rules'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const COSMOS = cosmosFixture.cosmos as unknown as CosmosData
const RULES = buildRuleBook(cosmosFixture.rules as never)
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

const ADDICTION = {
  community: { id: 31, kind: 'entity', name: 'Ashford' },
  resource: { id: 40, kind: 'entity', name: 'Dream Salt' },
  owned_epochs: 5,
  addicted_since_epoch: 4,
  withdrawal_since_epoch: null,
}

describe('cosmic controls', () => {
  beforeEach(resetApi)

  it('extinguishes a burning star only after confirming', async () => {
    serve()
    onApi('POST', '/api/actions/cosmic:extinguish_star', ACCEPTED_ACTION)
    const star = COSMOS.stars.find((item) => item.star_type === 'yellow_dwarf')
    if (!star) throw new Error('no live star')
    const { screen } = await renderApp(
      <StarCard
        star={star}
        index={INDEX}
        rules={RULES}
        onSelectWorld={vi.fn()}
      />
    )
    await screen.getByRole('button', { name: /^Extinguish/ }).click()
    expect(callsTo('POST', '/api/actions/cosmic:extinguish_star')).toHaveLength(
      0
    )
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Extinguish' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/cosmic:extinguish_star').length)
      .toBe(1)
    expect(
      callsTo('POST', '/api/actions/cosmic:extinguish_star')[0]?.body
    ).toEqual({ star_id: star.id })
  })

  it('never offers to extinguish a dead star', async () => {
    serve()
    const dead = COSMOS.stars.find((item) => item.star_type === 'black_sun')
    if (!dead) throw new Error('no dead star')
    const { screen } = await renderApp(
      <StarCard
        star={dead}
        index={INDEX}
        rules={RULES}
        onSelectWorld={vi.fn()}
      />
    )
    await expect
      .element(screen.getByRole('button', { name: /Re-ignite/ }))
      .toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /^Extinguish/ }).elements()
    ).toHaveLength(0)
  })

  it('lets a waiting intuition go, or all of them after confirming', async () => {
    serve()
    onApi('GET', '/api/discovery-summary', cosmosFixture.discovery)
    onApi('POST', '/api/actions/intuition:discard', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/intuition:discard_all', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <HorizonSection worldId={3} index={INDEX} rules={RULES} />
    )
    await screen.getByRole('button', { name: 'Let it go' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/intuition:discard').length)
      .toBe(1)
    expect(callsTo('POST', '/api/actions/intuition:discard')[0]?.body).toEqual({
      intuition_id: 1,
    })
    await screen.getByRole('button', { name: 'Let every intuition go' }).click()
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Let them go' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/intuition:discard_all').length)
      .toBe(1)
  })

  it('runs the economy by hand and cures a craving', async () => {
    serve()
    onApi('GET', '/api/addictions', [ADDICTION])
    onApi('POST', '/api/actions/economy:resources', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/economy:cosmic', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/addiction:cure', ACCEPTED_ACTION)
    const { screen } = await renderApp(<EconomyControls />)
    await screen
      .getByRole('button', { name: /Run the resource mechanics/ })
      .click()
    await screen.getByRole('button', { name: /Run the cosmic economy/ }).click()
    await screen.getByRole('button', { name: /^Cure/ }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/addiction:cure').length)
      .toBe(1)
    expect(callsTo('POST', '/api/actions/addiction:cure')[0]?.body).toEqual({
      entity_id: 31,
      resource_id: 40,
    })
    expect(callsTo('POST', '/api/actions/economy:resources')).toHaveLength(1)
    expect(callsTo('POST', '/api/actions/economy:cosmic')).toHaveLength(1)
  })

  it('lists the laws of a world with their mechanics', async () => {
    onApi('GET', '/api/worlds/3/laws', [
      {
        entity: {
          id: 60,
          name: 'The Law of Returning',
          entity_type: 'natural_law',
          world_id: 3,
        },
        mechanic: 'dead_return',
      },
    ])
    const { screen } = await renderApp(<WorldLaws worldId={3} />)
    await expect
      .element(screen.getByText('The Law of Returning'))
      .toBeInTheDocument()
    await expect.element(screen.getByText('Dead return')).toBeInTheDocument()
  })
})

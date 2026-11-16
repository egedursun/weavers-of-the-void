import { type ReactNode, useState } from 'react'
import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { page, userEvent } from 'vitest/browser'
import actions from '../../../e2e/fixtures/actions.json'
import cosmosFixture from '../../../e2e/fixtures/cosmos.json'
import { CosmosLegend } from './CosmosLegend'
import { CosmosSidePanel } from './CosmosSidePanel'
import { CosmosTopBar } from './CosmosTopBar'
import { CosmosViewSettings } from './CosmosViewSettings'
import { TravellersGuide } from './TravellersGuide'
import { type CosmosData, type SonPublic } from './api'
import { type CommandSection, type CosmosPanel } from './cosmosSearch'
import { indexCosmos } from './model/cosmosModel'
import { buildRuleBook } from './model/rules'
import { useCosmosViewSettings } from './useCosmosViewSettings'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const COSMOS = cosmosFixture.cosmos as unknown as CosmosData
const RULES = buildRuleBook(cosmosFixture.rules as never)
const INDEX = indexCosmos(COSMOS)
const SONS = [
  {
    son: { id: 4, name: 'Ithren', rarity: 'legendary', status: 'active' },
    cover: null,
  },
  {
    son: { id: 7, name: 'Seravel', rarity: 'rare', status: 'active' },
    cover: null,
  },
] as unknown as SonPublic[]
const WRITES = [
  'POST /api/worlds',
  'PATCH /api/worlds/:id',
  'PUT /api/worlds/:id/orbit',
  'POST /api/worlds/:id/discovery-round',
  'PATCH /api/stars/:id',
  'POST /api/cosmic/seal-gate',
  'POST /api/routes/:id/sever',
  'POST /api/routes/:id/restore',
  'POST /api/routes/:id/reveal',
  'POST /api/cosmic/sky-event',
  'PUT /api/climate',
  'POST /api/federations',
  'PUT /api/cosmic-resource',
  'POST /api/cosmic-resource/deposits',
  'POST /api/actions/:key',
]

function serve(essence = 900) {
  onApi('GET', '/api/state', {
    creator: { essence },
    epoch_running: false,
    read_only: false,
    world: { epoch: 11, primary_world_id: 3 },
    worlds: [],
  })
  onApi('GET', '/api/actions', actions)
  onApi('GET', '/api/rules', cosmosFixture.rules)
  onApi('GET', '/api/cosmos', COSMOS)
  onApi('GET', '/api/jobs', [])
  onApi('GET', '/api/names', [])
  onApi('GET', '/api/cosmos/epoch-star', { current: [], history: [] })
  for (const key of WRITES) {
    const [method, path] = key.split(' ')
    onApi(method, path, ACCEPTED_ACTION)
  }
}

function calls(method: string, path: string) {
  return callsTo(method, path)
}

type HarnessProps = {
  world?: number
  panel?: CosmosPanel
  section?: CommandSection
  star?: number
  resource?: {
    name: string
    rule: string
    description: string
    side_effect: string
  } | null
  galaxyPanel?: ReactNode
}

function Harness({
  world = 3,
  panel = 'world',
  section,
  star,
  resource = null,
  galaxyPanel,
}: HarnessProps) {
  const [worldId, setWorldId] = useState<number | undefined>(world)
  const [current, setCurrent] = useState<CosmosPanel>(panel)
  const [focus, setFocus] = useState<CommandSection | undefined>(section)
  const [descended, setDescended] = useState<number | null>(null)
  return (
    <>
      <output aria-label='Descended world'>{descended ?? ''}</output>
      <CosmosSidePanel
        index={INDEX}
        rules={RULES}
        sons={SONS}
        homeWorldId={3}
        worldId={worldId}
        starId={star}
        panel={current}
        section={focus}
        resource={resource as never}
        onSelectWorld={(id) => {
          setWorldId(id)
          setCurrent('world')
        }}
        onSelectStar={() => undefined}
        onOpenPanel={(next, nextSection) => {
          setCurrent(next)
          setFocus(nextSection)
        }}
        onDescend={setDescended}
        galaxyPanel={galaxyPanel}
      />
    </>
  )
}

beforeEach(() => {
  resetApi()
  localStorage.clear()
  serve()
})

describe('cosmos side panel', () => {
  it('has World, Voyages, Gods and Command tabs with counts and a Star tab only for a chosen star', async () => {
    const { screen } = await renderApp(<Harness />)
    const tabs = screen.getByRole('tablist', { name: 'Cosmos panel' })
    await expect
      .element(tabs.getByRole('tab', { name: 'World' }))
      .toHaveAttribute('data-state', 'active')
    await expect
      .element(tabs.getByRole('tab', { name: /Voyages/ }))
      .toHaveTextContent(/2/)
    await expect
      .element(tabs.getByRole('tab', { name: /Gods/ }))
      .toHaveTextContent('2')
    await expect
      .element(tabs.getByRole('tab', { name: 'Star' }))
      .not.toBeInTheDocument()
    await tabs.getByRole('tab', { name: /Gods/ }).click()
    await expect.element(screen.getByText('Ulmaresh').first()).toBeVisible()
  })

  it('keeps every tab in sight beside the galaxy card in a side panel', async () => {
    await page.viewport(1200, 800)
    const { screen } = await renderApp(
      <div className='w-md'>
        <Harness panel='star' star={11} galaxyPanel={<div>Galaxy card</div>} />
      </div>
    )
    await expect.element(screen.getByText('Galaxy card')).toBeVisible()
    const tabs = screen.getByRole('tablist', { name: 'Cosmos panel' })
    for (const name of [/World/, /Voyages/, /Gods/, /Command/, /Star/])
      await expect
        .element(tabs.getByRole('tab', { name }), { message: String(name) })
        .toBeInViewport({ ratio: 0.95 })
  })

  it('shows the star tab while a star is chosen and edits the star', async () => {
    const { screen } = await renderApp(<Harness panel='star' star={11} />)
    await expect
      .element(screen.getByRole('tab', { name: 'Star' }))
      .toHaveAttribute('data-state', 'active')
    await screen.getByRole('button', { name: /Edit the star/ }).click()
    const name = screen.getByRole('textbox', { name: 'Name', exact: true })
    await name.clear()
    await name.fill('Keth Lantern')
    await screen.getByRole('combobox', { name: 'Type' }).click()
    await screen.getByRole('option', { name: 'Red giant' }).click()
    await screen.getByRole('button', { name: /Save the star/ }).click()
    await expect.poll(() => calls('PATCH', '/api/stars/11').length).toBe(1)
    expect(calls('PATCH', '/api/stars/11')[0].body).toMatchObject({
      name: 'Keth Lantern',
      star_type: 'red_giant',
    })
  })

  it('chooses between worlds with buttons that mark forgotten worlds', async () => {
    const { screen } = await renderApp(<Harness />)
    const chooser = screen.getByRole('radiogroup', { name: 'Choose a world' })
    await expect
      .element(chooser.getByRole('radio', { name: 'Hollow Choir, forgotten' }))
      .toBeVisible()
    await chooser.getByRole('radio', { name: 'Oru' }).click()
    await expect
      .element(screen.getByRole('heading', { name: 'Oru' }))
      .toBeVisible()
    await expect
      .element(chooser.getByRole('radio', { name: 'Oru' }))
      .toHaveAttribute('aria-checked', 'true')
  })
})

describe('world card', () => {
  it('opens the dialect accordion and remembers it per world', async () => {
    window.localStorage.removeItem('aerona.cosmos.dialect.3')
    const { screen } = await renderApp(<Harness />)
    const toggle = screen.getByRole('button', {
      name: 'Its dialect: how names are born here',
    })
    await expect.element(toggle).toHaveAttribute('aria-expanded', 'false')
    await toggle.click()
    await expect
      .element(
        screen.getByText(
          /^Flowing names of 2 to 3 syllables; often ending in -ar, -eth, -os; never z, k\.$/
        )
      )
      .toBeVisible()
    await expect
      .element(screen.getByText('Velmora', { exact: true }).first())
      .toBeVisible()
    expect(window.localStorage.getItem('aerona.cosmos.dialect.3')).toBe('true')
  })

  it('descends to the map, opens Atlas and the traveller guide drawer', async () => {
    const { screen, router } = await renderApp(<Harness />)
    await screen.getByRole('button', { name: 'Descend to its map' }).click()
    await expect
      .element(
        screen
          .getByRole('status', { name: 'Descended world' })
          .or(screen.getByLabelText('Descended world'))
      )
      .toHaveTextContent('3')
    await screen.getByRole('button', { name: "Traveller's guide" }).click()
    await expect
      .poll(() => JSON.stringify(router.state.location.search))
      .toContain('world-guide')
    await screen.getByRole('button', { name: 'Open in Atlas' }).click()
    await expect
      .poll(() => router.state.location.href)
      .toContain('/atlas?world=3')
  })

  it('shows description, cosmology and the count chips', async () => {
    const { screen } = await renderApp(<Harness />)
    await expect
      .element(screen.getByText('Regions', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText('Peoples', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText('Settlements', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText('Living records', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText('6.9K', { exact: true }))
      .toBeVisible()
  })

  it('lists physics with orbit, gravity, atmosphere, time, the climate link and danger', async () => {
    const { screen } = await renderApp(<Harness />)
    await expect.element(screen.getByText('Mortal agents')).toBeVisible()
    await expect.element(screen.getByText('1.2 units')).toBeVisible()
    await expect
      .element(screen.getByText('Gravity', { exact: true }).first())
      .toBeVisible()
    await expect
      .element(screen.getByText('Atmosphere', { exact: true }).first())
      .toBeVisible()
    await screen.getByRole('button', { name: 'Climate cycle' }).click()
    await expect
      .element(screen.getByRole('tab', { name: 'Command' }))
      .toHaveAttribute('data-state', 'active')
    await expect
      .element(
        document.querySelector(
          '[data-command-section="climate"]'
        ) as HTMLElement
      )
      .toHaveAttribute('data-state', 'open')
  })

  it('warns at the first leakage threshold', async () => {
    const { screen } = await renderApp(<Harness world={5} />)
    await expect
      .element(screen.getByText('Something is leaking in from outside.'))
      .toBeVisible()
  })

  it('names Outsiders taking root at the second leakage threshold', async () => {
    const { screen } = await renderApp(<Harness world={8} />)
    await expect
      .element(screen.getByText(/Outsiders are taking root in this world/))
      .toBeVisible()
  })

  it("shows the epoch's star, the guardian son with the automatic note and the mirror twin link", async () => {
    const { screen } = await renderApp(<Harness />)
    await expect.element(screen.getByText("This epoch's star:")).toBeVisible()
    await expect
      .element(screen.getByText(/became guardian on its own/))
      .toBeVisible()
    await screen.getByRole('radio', { name: /^Mirevast/ }).click()
    await expect
      .element(screen.getByText(/declared this world sacred/))
      .toBeVisible()
    await expect.element(screen.getByText('Mirror twin:')).toBeVisible()
    await screen
      .getByRole('button', { name: 'Oru', exact: true })
      .last()
      .click()
    await expect
      .element(screen.getByRole('heading', { name: 'Oru' }))
      .toBeVisible()
  })

  it('shows the sons present as links and an empty note elsewhere', async () => {
    const { screen } = await renderApp(<Harness />)
    await expect
      .element(screen.getByRole('link', { name: 'Ithren' }).first())
      .toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: 'Seravel' }).first())
      .toBeVisible()
    await screen.getByRole('radio', { name: 'Oru' }).click()
    await expect
      .element(screen.getByText('No son is in this world right now.'))
      .toBeVisible()
  })

  it('lists its routes with method, other world, duration, danger, controller and closed styling', async () => {
    const { screen } = await renderApp(<Harness />)
    await expect
      .element(screen.getByRole('heading', { name: /^Routes \(\d+\)$/ }))
      .toBeVisible()
    const closed = document.querySelector('li[data-route-id="6"]')
    expect(closed?.className).toContain('border-dashed')
    await expect
      .element(screen.getByText('A void storm tore the dream apart.'))
      .toBeVisible()
    const gate = document.querySelector('li[data-route-id="1"]')
    expect(gate?.textContent).toContain('Ancient gate')
    expect(gate?.textContent).toMatch(/1 epoch · danger \d+/)
    expect(gate?.className).not.toContain('border-dashed')
  })

  it('lists the gods of this world inside the card', async () => {
    const { screen } = await renderApp(<Harness world={5} />)
    await expect
      .element(screen.getByRole('heading', { name: "This world's gods" }))
      .toBeVisible()
    await expect.element(screen.getByText('Ulmaresh').first()).toBeVisible()
  })

  it('lists voyages coming here inside the card', async () => {
    const { screen } = await renderApp(<Harness world={6} />)
    await expect
      .element(screen.getByRole('heading', { name: 'Voyages coming here' }))
      .toBeVisible()
  })

  it('edits the world with a PATCH and keeps the forgotten option away from the home world', async () => {
    const { screen } = await renderApp(<Harness />)
    await screen
      .getByRole('button', {
        name: /Edit the world: name, type, physics, orbit and story/,
      })
      .click()
    const name = screen.getByRole('textbox', { name: 'Name', exact: true })
    await name.clear()
    await name.fill('Velar Prime')
    const leakage = screen.getByRole('spinbutton', { name: 'Leakage' })
    await leakage.clear()
    await leakage.fill('12')
    const discovery = screen.getByRole('combobox', { name: 'Discovery' })
    ;(discovery.element() as HTMLElement).focus()
    await userEvent.keyboard('{Enter}')
    await expect
      .element(screen.getByRole('option', { name: /Known/ }))
      .toBeVisible()
    expect(
      screen.getByRole('option', { name: /Forgotten/ }).elements()
    ).toHaveLength(0)
    await userEvent.keyboard('{Escape}')
    await expect.element(screen.getByRole('listbox')).not.toBeInTheDocument()
    await screen.getByRole('button', { name: /Reshape the world/ }).click()
    await expect.poll(() => calls('PATCH', '/api/worlds/3').length).toBe(1)
    expect(calls('PATCH', '/api/worlds/3')[0].body).toMatchObject({
      name: 'Velar Prime',
      leakage: 12,
    })
  })
})

describe('route actions', () => {
  it('seals an open route at the rule cost and severs another for chosen epochs after confirming', async () => {
    const { screen } = await renderApp(<Harness />)
    const gate = screen
      .getByRole('listitem')
      .filter({ hasText: 'Ancient gate' })
      .first()
    await gate.getByRole('button', { name: /^Seal/ }).click()
    await expect
      .poll(() => calls('POST', '/api/cosmic/seal-gate').length)
      .toBe(1)
    expect(calls('POST', '/api/cosmic/seal-gate')[0].body).toEqual({
      route_id: 1,
    })
    await gate.getByRole('button', { name: 'Sever' }).click()
    await screen.getByLabelText('Closed for how many epochs').fill('4')
    await screen.getByRole('button', { name: /^Sever the route/ }).click()
    await expect
      .element(screen.getByRole('alertdialog'))
      .toHaveTextContent(/closes for 4 epochs/)
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Sever' })
      .click()
    await expect.poll(() => calls('POST', '/api/routes/1/sever').length).toBe(1)
    expect(calls('POST', '/api/routes/1/sever')[0].body).toEqual({
      duration: 4,
    })
  })

  it('stitches a severed route again', async () => {
    const { screen } = await renderApp(<Harness />)
    const dream = screen
      .getByRole('listitem')
      .filter({ hasText: 'A void storm tore the dream apart.' })
      .first()
    await expect
      .element(dream.getByRole('button', { name: /^Seal/ }))
      .not.toBeInTheDocument()
    await dream.getByRole('button', { name: /^Stitch again/ }).click()
    await expect
      .poll(() => calls('POST', '/api/routes/6/restore').length)
      .toBe(1)
  })

  it('reveals a hidden route', async () => {
    const { screen } = await renderApp(<Harness world={8} />)
    await expect
      .element(screen.getByRole('heading', { name: /^Routes/ }))
      .toBeVisible()
    const hidden = document.querySelector('li[data-route-id="5"]')
    expect(hidden?.className).toContain('opacity-80')
    await page
      .elementLocator(hidden as HTMLElement)
      .getByRole('button', { name: /^Reveal/ })
      .click()
    await expect
      .poll(() => calls('POST', '/api/routes/5/reveal').length)
      .toBe(1)
  })
})

describe('horizon', () => {
  it('rolls an exploration round for this world', async () => {
    const { screen } = await renderApp(<Harness />)
    await expect
      .element(screen.getByRole('heading', { name: 'Horizon and exploration' }))
      .toBeVisible()
    await screen.getByRole('button', { name: /^Exploration round/ }).click()
    await expect
      .poll(() => calls('POST', '/api/worlds/3/discovery-round').length)
      .toBe(1)
  })
})

describe('command forms', () => {
  it('creates a world of a chosen type around a chosen star', async () => {
    const { screen } = await renderApp(
      <Harness panel='command' section='world' />
    )
    await screen
      .getByRole('radio', { name: /^Ocean/ })
      .first()
      .click()
    await screen.getByLabelText('Inspiration').fill('Bells under the waves.')
    await screen.getByRole('radio', { name: 'Around a star' }).click()
    await screen.getByRole('button', { name: /^Create the world/ }).click()
    await expect.poll(() => calls('POST', '/api/worlds').length).toBe(1)
    expect(calls('POST', '/api/worlds')[0].body).toEqual({
      world_type: 'ocean',
      inspiration: 'Bells under the waves.',
      new_star: false,
      star_id: 2,
    })
  })

  it('creates a world as a new star system', async () => {
    const { screen } = await renderApp(
      <Harness panel='command' section='world' />
    )
    await screen.getByRole('radio', { name: 'New star system' }).click()
    await screen.getByRole('button', { name: /^Create the world/ }).click()
    await expect.poll(() => calls('POST', '/api/worlds').length).toBe(1)
    expect(calls('POST', '/api/worlds')[0].body).toMatchObject({
      new_star: true,
    })
  })

  it('commands a sky event on a world or a star and swaps to route fields for a void storm', async () => {
    const { screen } = await renderApp(
      <Harness panel='command' section='sky' />
    )
    await screen
      .getByRole('button', { name: /^Command the sky/ })
      .last()
      .click()
    await expect
      .poll(() => calls('POST', '/api/cosmic/sky-event').length)
      .toBe(1)
    expect(calls('POST', '/api/cosmic/sky-event')[0].body).toEqual({
      kind: 'eclipse',
      world_id: 3,
    })
    await screen.getByRole('combobox', { name: 'Event' }).click()
    await screen.getByRole('option', { name: /storm/i }).click()
    await expect
      .element(screen.getByRole('combobox', { name: 'Which route breaks' }))
      .toBeVisible()
    await screen
      .getByRole('spinbutton', { name: 'For how many epochs' })
      .fill('2')
    await screen
      .getByRole('button', { name: /^Command the sky/ })
      .last()
      .click()
    await expect
      .poll(() => calls('POST', '/api/cosmic/sky-event').length)
      .toBe(2)
    expect(calls('POST', '/api/cosmic/sky-event')[1].body).toMatchObject({
      kind: 'void_storm',
      duration: 2,
    })
  })

  it('starts a climate cycle for one world within the rule cap', async () => {
    const { screen } = await renderApp(
      <Harness panel='command' section='climate' />
    )
    const world = screen.getByRole('combobox', { name: 'World' })
    ;(world.element() as HTMLElement).focus()
    await userEvent.keyboard('{Enter}')
    await expect
      .element(screen.getByRole('option', { name: /^Velar · now/ }))
      .toBeVisible()
    await expect
      .poll(() => document.activeElement?.textContent)
      .toBe('All worlds')
    await userEvent.keyboard('{ArrowDown}')
    await expect
      .poll(() => document.activeElement?.textContent)
      .toMatch(/^Velar · now/)
    await userEvent.keyboard('{Enter}')
    await expect
      .poll(() => (world.element() as HTMLElement).textContent)
      .toMatch(/^Velar · now/)
    await screen.getByRole('spinbutton', { name: 'Epochs' }).fill('6')
    await screen.getByRole('button', { name: /^Start the cycle/ }).click()
    await expect.poll(() => calls('PUT', '/api/climate').length).toBe(1)
    expect(calls('PUT', '/api/climate')[0].body).toMatchObject({
      epochs: 6,
      world_id: 3,
    })
    await expect
      .element(screen.getByText(/1 to 50; blank uses 4\./))
      .toBeVisible()
  })

  it('founds a federation of at least two living communities', async () => {
    const { screen } = await renderApp(
      <Harness panel='command' section='federation' />
    )
    const found = screen.getByRole('button', { name: /^Found the federation/ })
    await expect.element(found).toBeVisible()
    const picker = screen.getByRole('button', {
      name: /^Communities · 0 selected · at least 2/,
    })
    await expect.element(picker).toBeVisible()
    for (const [query, community] of [
      ['Marsh', /Marsh Folk/],
      ['Tide', /Tidebound/],
    ] as const) {
      await screen.getByRole('button', { name: /^Communities · / }).click()
      await screen.getByPlaceholder('Search community…').fill(query)
      await screen.getByRole('checkbox', { name: community }).click()
      await userEvent.keyboard('{Escape}')
    }
    await expect
      .element(
        screen.getByRole('button', { name: /^Communities · 2 selected/ })
      )
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Remove Marsh Folk' }))
      .toBeVisible()
    await screen
      .getByPlaceholder('The name of the federation')
      .fill('Salt League')
    await found.click()
    await expect.poll(() => calls('POST', '/api/federations').length).toBe(1)
    expect(calls('POST', '/api/federations')[0].body).toEqual({
      member_ids: [21, 22],
      name: 'Salt League',
    })
  })

  it('defines the travel resource, open by default while undefined, and opens a deposit', async () => {
    const { screen } = await renderApp(<Harness panel='command' />)
    await expect
      .element(
        document.querySelector(
          '[data-command-section="resource"]'
        ) as HTMLElement
      )
      .toHaveAttribute('data-state', 'open')
    await screen.getByPlaceholder('The name of the resource').fill('Hour sand')
    await screen
      .getByPlaceholder('Only gathered in one season')
      .fill('Gathered at dusk')
    await screen
      .getByRole('button', { name: /Define|Save|Set the resource/ })
      .first()
      .click()
    await expect.poll(() => calls('PUT', '/api/cosmic-resource').length).toBe(1)
    expect(calls('PUT', '/api/cosmic-resource')[0].body).toMatchObject({
      name: 'Hour sand',
      rule: 'Gathered at dusk',
    })
  })

  it('opens a deposit of a defined resource in a chosen region', async () => {
    const resource = {
      name: 'Hour sand',
      rule: 'At dusk',
      description: 'Sand.',
      side_effect: '',
    }
    const { screen } = await renderApp(
      <Harness panel='command' section='resource' resource={resource} />
    )
    await screen.getByRole('combobox', { name: 'Region or place' }).click()
    await screen.getByRole('option', { name: /Saltmarch/ }).click()
    await screen.getByRole('button', { name: /^Open the deposit/ }).click()
    await expect
      .poll(() => calls('POST', '/api/cosmic-resource/deposits').length)
      .toBe(1)
    expect(calls('POST', '/api/cosmic-resource/deposits')[0].body).toEqual({
      place_id: 41,
    })
  })
})

describe('cosmos chrome', () => {
  it('summarises stars, worlds, open and closed routes and voyages under way', async () => {
    const { screen } = await renderApp(
      <CosmosTopBar
        index={INDEX}
        rules={RULES}
        epoch={11}
        alignmentUntil={null}
        resource={null}
        view='2d'
        quality='medium'
        failure={null}
        onView={() => undefined}
        onQuality={() => undefined}
        onOpenResource={() => undefined}
      />
    )
    await expect.element(screen.getByText('3 stars')).toBeVisible()
    await expect.element(screen.getByText('9 worlds')).toBeVisible()
    await expect.element(screen.getByText('5 open routes')).toBeVisible()
    await expect.element(screen.getByText('3 closed')).toBeVisible()
    await expect.element(screen.getByText('2 voyages under way')).toBeVisible()
    await expect
      .element(
        screen.getByRole('button', { name: 'Travel resource: not defined' })
      )
      .toBeVisible()
  })

  it('draws one legend glyph per travel method present and the voyage arrow', async () => {
    const { screen } = await renderApp(<CosmosLegend index={INDEX} />)
    const legend = screen.getByLabelText('Route legend')
    for (const label of [
      'Ancient gate',
      'Light sail',
      'Divine bridge',
      'Dream journey',
      'Space fold',
      'River of the dead',
    ])
      await expect.element(legend.getByText(label)).toBeVisible()
    await expect.element(legend.getByText('Voyage under way')).toBeVisible()
    expect(
      legend.element().querySelectorAll('svg').length
    ).toBeGreaterThanOrEqual(8)
  })

  it('remembers the view mode and 3D quality in the browser and disables 3D without WebGL', async () => {
    function Settings() {
      const settings = useCosmosViewSettings()
      return (
        <CosmosViewSettings
          view={settings.view}
          quality={settings.quality}
          failure={settings.failure}
          onView={settings.setView}
          onQuality={settings.setQuality}
        />
      )
    }
    const { screen } = await renderApp(<Settings />)
    await screen.getByRole('combobox', { name: '3D quality' }).click()
    await screen.getByRole('option', { name: 'High' }).click()
    expect(localStorage.getItem('aerona.cosmos.quality')).toBe('high')
    await screen.getByRole('radio', { name: '2D view' }).click()
    expect(localStorage.getItem('aerona.cosmos.view')).toBe('2d')
    await expect
      .element(screen.getByRole('combobox', { name: '3D quality' }))
      .not.toBeInTheDocument()
  })

  it('disables 3D when WebGL failed', async () => {
    const { screen } = await renderApp(
      <CosmosViewSettings
        view='2d'
        quality='low'
        failure='WebGL 2 is not available'
        onView={() => undefined}
        onQuality={() => undefined}
      />
    )
    await expect
      .element(screen.getByRole('radio', { name: '3D view' }))
      .toBeDisabled()
  })
})

describe("traveller's guide", () => {
  it('shows discovery, type, star, time, atmosphere, gravity, leakage, climate and the map and codex buttons', async () => {
    onApi('GET', '/api/worlds/3/guide', cosmosFixture.guide)
    const { screen, router } = await renderApp(<TravellersGuide id='3' />)
    await expect
      .element(screen.getByRole('heading', { name: 'Velar' }).first())
      .toBeVisible()
    await expect.element(screen.getByText('Ordinary world')).toBeVisible()
    await expect
      .element(screen.getByText('Velar Sun · Yellow dwarf'))
      .toBeVisible()
    await expect.element(screen.getByText('Leakage').first()).toBeVisible()
    await expect
      .element(screen.getByText(/Rain age \(3 epochs left\)/))
      .toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: /codex/i }))
      .toHaveAttribute('href', '/api/codex.zip')
    await screen.getByRole('button', { name: /map/i }).first().click()
    await expect
      .poll(() => router.state.location.href)
      .toContain('/map?world=3')
  })

  it('lists cosmology, dangers, peoples, resources with mechanisms, roads, native gods and sky', async () => {
    onApi('GET', '/api/worlds/3/guide', cosmosFixture.guide)
    const { screen } = await renderApp(<TravellersGuide id='3' />)
    await expect
      .element(screen.getByText(/The sea was the first word spoken/))
      .toBeVisible()
    await expect
      .element(
        screen.getByText('A cult that drowns strangers at the spring tide.')
      )
      .toBeVisible()
    await expect.element(screen.getByText(/4\.2K souls/)).toBeVisible()
    await expect.element(screen.getByText(/worships Ithren/)).toBeVisible()
    await expect
      .element(screen.getByText('Sand that holds a moment.'))
      .toBeVisible()
    await expect.element(screen.getByText(/decaying/i).first()).toBeVisible()
    await expect
      .element(screen.getByText('Ancient gate → Mirevast'))
      .toBeVisible()
    await expect.element(screen.getByText(/attitude -45/)).toBeVisible()
    await expect
      .element(screen.getByText('The sky of this world holds nothing named.'))
      .toBeVisible()
  })

  it('describes the local dialect', async () => {
    onApi('GET', '/api/worlds/3/guide', cosmosFixture.guide)
    const { screen } = await renderApp(<TravellersGuide id='3' />)
    await expect
      .element(screen.getByRole('heading', { name: 'Local dialect' }))
      .toBeVisible()
    await expect
      .element(screen.getByText('z, k', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText('CV, CVC, V', { exact: true }))
      .toBeVisible()
    await expect.element(screen.getByText('Tharos')).toBeVisible()
  })
})

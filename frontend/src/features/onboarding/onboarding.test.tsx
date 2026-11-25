import { worldState } from '@/test-utils/fixtures'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { universeKey } from '@/lib/universeStorage'
import { useFeed } from '@/features/feed/feedStore'
import { FirstEpochsGuide } from './FirstEpochsGuide'
import { GenesisScreen } from './GenesisScreen'
import { GenesisWizard } from './GenesisWizard'
import { OnboardingTracker } from './OnboardingTracker'
import {
  ONBOARDING_STEPS,
  stepForLocation,
  useOnboarding,
} from './onboardingStore'

function resetOnboarding() {
  useOnboarding.setState({ done: [], dismissed: false })
  localStorage.clear()
}

beforeEach(resetOnboarding)
afterEach(resetOnboarding)

describe('first epochs guide', () => {
  it('lists the six steps with progress and marks done steps', async () => {
    useOnboarding.getState().mark('map')
    useOnboarding.getState().mark('son')
    const { screen } = await renderScreen(<FirstEpochsGuide epoch={1} />)
    await expect
      .element(screen.getByText(/2 of 6 steps taken/))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('link', { name: 'Look at the map' }))
      .toBeInTheDocument()
    await expect.element(screen.getByText('Done.').first()).toBeInTheDocument()
    await expect
      .element(screen.getByRole('link', { name: 'Glance at the world rules' }))
      .toHaveAttribute('href', '/settings/world-rules')
  })

  it('hides itself after the third epoch', async () => {
    const { screen } = await renderScreen(<FirstEpochsGuide epoch={4} />)
    await expect
      .element(screen.getByText('The first epochs'))
      .not.toBeInTheDocument()
  })

  it('is dismissed with Got it and the choice is remembered in the browser', async () => {
    const { screen } = await renderScreen(<FirstEpochsGuide epoch={2} />)
    await screen.getByRole('button', { name: 'Got it, hide' }).click()
    await expect
      .element(screen.getByText('The first epochs'))
      .not.toBeInTheDocument()
    expect(localStorage.getItem(universeKey('aerona.onboarding'))).toContain(
      '"dismissed":true'
    )
  })

  it('can be reopened after dismissal', async () => {
    useOnboarding.getState().dismiss()
    const { screen } = await renderScreen(<FirstEpochsGuide epoch={1} />)
    await expect
      .element(screen.getByText('The first epochs'))
      .not.toBeInTheDocument()
    useOnboarding.getState().reopen()
    await expect
      .element(screen.getByText('The first epochs'))
      .toBeInTheDocument()
  })
})

describe('onboarding store', () => {
  it('marks each step once and keeps them in order of completion', () => {
    const { mark } = useOnboarding.getState()
    mark('rules')
    mark('prayers')
    mark('rules')
    expect(useOnboarding.getState().done).toEqual(['rules', 'prayers'])
    expect(localStorage.getItem(universeKey('aerona.onboarding'))).toContain(
      'rules'
    )
  })

  it('knows every step by its location', () => {
    expect(stepForLocation('/map', undefined)).toBe('map')
    expect(stepForLocation('/prayers', undefined)).toBe('prayers')
    expect(stepForLocation('/chronicle', undefined)).toBe('chronicle')
    expect(stepForLocation('/settings/world-rules', undefined)).toBe('rules')
    expect(stepForLocation('/pantheon', 'entity:3,son:7')).toBe('son')
    expect(stepForLocation('/pantheon', 'entity:3')).toBeNull()
    expect(ONBOARDING_STEPS).toHaveLength(6)
  })
})

describe('onboarding tracker', () => {
  it('marks the epoch step when the world is past its first epoch', async () => {
    await renderScreen(<OnboardingTracker />, {
      'GET /api/state': worldState({
        world: { id: 1, name: 'Aerona', epoch: 2 },
      }),
    })
    await expect.poll(() => useOnboarding.getState().done).toContain('epoch')
  })

  it('marks the step of the page being visited', async () => {
    await renderScreen(
      <OnboardingTracker />,
      { 'GET /api/state': worldState() },
      '/prayers'
    )
    await expect.poll(() => useOnboarding.getState().done).toContain('prayers')
  })

  it('sends a player without a world to creation', async () => {
    const { router } = await renderScreen(
      <OnboardingTracker />,
      { 'GET /api/state': worldState({ world: null }) },
      '/pantheon'
    )
    await expect.poll(() => router.state.location.pathname).toBe('/genesis')
  })

  it('leaves settings reachable without a world', async () => {
    const { router, server } = await renderScreen(
      <OnboardingTracker />,
      { 'GET /api/state': worldState({ world: null }) },
      '/settings'
    )
    await expect
      .poll(() => server.callsTo('GET /api/state').length)
      .toBeGreaterThan(0)
    expect(router.state.location.pathname).toBe('/settings')
  })
})

describe('creation screen', () => {
  const idle = {
    'GET /api/jobs': [],
    'GET /api/backups': [],
    'GET /api/activity-log': [],
  }

  it('says the world already exists and offers the way back', async () => {
    const { screen } = await renderScreen(<GenesisScreen />, {
      ...idle,
      'GET /api/state': worldState(),
    })
    await expect
      .element(screen.getByText('Aerona already exists'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('link', { name: /Back to the overview/ }))
      .toBeInTheDocument()
  })

  it('explains that the language model is off and still offers worlds to open', async () => {
    const { screen } = await renderScreen(<GenesisScreen />, {
      ...idle,
      'GET /api/state': worldState({ world: null, llm_enabled: false }),
    })
    await expect
      .element(screen.getByText('The language model is turned off'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Export the whole world'))
      .not.toBeInTheDocument()
  })

  it('locks the form behind a progress note while genesis runs and shows system notes', async () => {
    useFeed.setState({ lines: [], restored: true })
    const genesisJob = {
      id: 'g1',
      kind: 'genesis',
      status: 'running',
      progress: 0.3,
      stage: 'Writing the cosmology',
      params: {},
      result: null,
      error: null,
      created_at: '2026-01-01T12:00:00Z',
      started_at: '2026-01-01T12:00:00Z',
      finished_at: null,
    }
    const { screen } = await renderScreen(<GenesisScreen />, {
      ...idle,
      'GET /api/jobs': [genesisJob],
      'GET /api/state': worldState({ world: null }),
    })
    await expect
      .element(screen.getByText('The world is being thought'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Writing the cosmology'))
      .toBeInTheDocument()
    await expect.element(screen.getByText('World seed')).not.toBeInTheDocument()
  })

  it('welcomes the newborn world and carries the god into it when genesis finishes', async () => {
    const { router, emit, screen } = await renderScreen(
      <GenesisScreen />,
      { ...idle, 'GET /api/state': worldState() },
      '/genesis'
    )
    emit('genesis.finished', {})
    await expect.element(screen.getByText(/is born\./)).toBeInTheDocument()
    await screen.getByRole('button', { name: /Enter your world/ }).click()
    await expect.poll(() => router.state.location.pathname).toBe('/overview')
  })
})

const WIZARD_OPTIONS = {
  technology: { iron: 'Iron age', bronze: 'Bronze age' },
  technology_levels: { iron: 3, bronze: 2 },
  technology_level_max: 10,
  language: { free: 'Free', sibilant: 'Sibilant' },
  numeral_bases: { decimal: 'Counts in tens', vigesimal: 'Counts in twenties' },
  cosmos: [
    { size: 'single', label: 'Single world', worlds: 1 },
    { size: 'small', label: 'Small cosmos', worlds: 2 },
  ],
  shapes: [
    { shape: 'one_sun', label: 'One sun', hint: 'Around the first sun' },
    { shape: 'many_suns', label: 'Many suns', hint: 'Own suns' },
    { shape: 'layered', label: 'Layered', hint: 'A second layer' },
  ],
  layer_kinds: [
    { kind: 'astral', label: 'Astral plane', description: 'Thought' },
  ],
  world_types: [
    { world_type: 'ordinary', label: 'Ordinary world', description: 'Plain' },
    { world_type: 'ocean', label: 'Ocean world', description: 'Water' },
  ],
  climate_eras: [{ era: 'rain', label: 'Rain age', description: 'Wet' }],
  world_ages: { young: 'Young', old: 'Old' },
  prehistory: { default: 0, maximum: 1000 },
  storyteller: { cyclic: 'Cyclic', rising: 'Rising' },
  age_cycles: { linear: 'Linear', cyclic: 'Cyclic' },
  lore_languages: { english: 'English', turkish: 'Turkish' },
  templates: [
    {
      key: 'drowned_world',
      name: 'Drowned world',
      tone: 'restless',
      magic: 55,
      danger: 50,
      technology: 'iron',
      language: 'sibilant',
      peoples: 3,
      cosmos: 'single',
      seed: 'A world where the sea covers almost everything.',
      storyteller: 'cyclic',
      shape: 'one_sun',
      world_type: 'ocean',
      climate_era: null,
      world_age: null,
    },
  ],
  first_sons: {
    minimum: 1,
    maximum: 5,
    rarities: ['common', 'rare'],
    default: ['common'],
  },
}

describe('genesis wizard', () => {
  it('fills the first world from a template, explains every locked control and sends the choices', async () => {
    const { screen, server } = await renderScreen(
      <GenesisWizard llmEnabled />,
      {
        'GET /api/genesis/wizard': WIZARD_OPTIONS,
        'POST /api/genesis': { job_id: 'g1', kind: 'genesis' },
      }
    )
    await screen.getByRole('radio', { name: /Drowned world/ }).click()
    await expect.element(screen.getByText('Ocean world').first()).toBeVisible()
    await expect
      .element(
        screen.getByRole('radio', { name: /Drowned world/ }).getByText('Chosen')
      )
      .toBeVisible()
    await screen.getByRole('button', { name: /Next: The Creator/ }).click()
    await expect
      .element(
        screen.getByRole('radio', { name: /English/ }).getByText('Chosen')
      )
      .toBeVisible()
    await screen.getByPlaceholder('A name for the Creator').fill('Aeron')
    await screen.getByRole('button', { name: /Next: Seed and tone/ }).click()
    await screen.getByRole('button', { name: /Next: The first world/ }).click()
    await expect
      .element(screen.getByText(/The seed shapes the land/).first())
      .toBeVisible()
    await screen
      .getByRole('switch', { name: 'Shape the land yourself' })
      .click()
    await expect
      .element(screen.getByText(/The seed shapes the land/))
      .not.toBeInTheDocument()
    await screen.getByRole('button', { name: /Next: Peoples/ }).click()
    await screen
      .getByRole('button', { name: /Next: Cosmos and telling/ })
      .click()
    await expect
      .element(screen.getByText(/A single world has no further worlds/))
      .toBeVisible()
    await expect
      .element(screen.getByText(/Only a layered cosmos has a second layer/))
      .toBeVisible()
    await screen.getByRole('radio', { name: /Small cosmos/ }).click()
    await screen.getByRole('radio', { name: /Layered/ }).click()
    await expect
      .element(screen.getByText(/Only a layered cosmos has a second layer/))
      .not.toBeInTheDocument()
    await screen.getByRole('button', { name: /Next: First sons/ }).click()
    await screen.getByRole('button', { name: /Create the world/ }).click()
    await expect.poll(() => server.callsTo('POST /api/genesis').length).toBe(1)
    const body = server.callsTo('POST /api/genesis')[0].body as {
      wizard: Record<string, unknown>
    }
    expect(body.wizard).toMatchObject({
      template: 'drowned_world',
      danger: 50,
      world_type: 'ocean',
      sea_pct: 50,
      cosmos: 'small',
      shape: 'layered',
      layer_kind: null,
    })
  })
})

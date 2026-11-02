import { worldState } from '@/test-utils/fixtures'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { useFeed } from '@/features/feed/feedStore'
import { FirstEpochsGuide } from './FirstEpochsGuide'
import { GenesisScreen } from './GenesisScreen'
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
    expect(localStorage.getItem('aerona.onboarding')).toContain(
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
    expect(localStorage.getItem('aerona.onboarding')).toContain('rules')
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

  it('returns to the overview when genesis finishes', async () => {
    const { router, emit } = await renderScreen(
      <GenesisScreen />,
      { ...idle, 'GET /api/state': worldState({ world: null }) },
      '/genesis'
    )
    emit('genesis.finished', {})
    await expect.poll(() => router.state.location.pathname).toBe('/')
  })
})

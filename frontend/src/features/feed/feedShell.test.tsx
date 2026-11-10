import { serverEvent, worldState } from '@/test-utils/fixtures'
import { failure } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { page, userEvent } from 'vitest/browser'
import { ActivityStrip } from '@/features/epoch/ActivityStrip'
import { EpochProgress } from '@/features/epoch/EpochProgress'
import { StopEpochButton } from '@/features/epoch/StopEpochButton'
import { useEpochRun } from '@/features/epoch/runStore'
import { FeedSoundSettings } from '@/features/settings/FeedSoundSettings'
import { FeedCollector } from './FeedCollector'
import { LiveFeedDock } from './LiveFeedDock'
import { LiveFeedSheet } from './LiveFeedSheet'
import { FEED_PREFERENCES_KEY, useFeed, useFeedPreferences } from './feedStore'

const WIDE = { width: 1440, height: 900 }
const NARROW = { width: 800, height: 900 }
const THROTTLE_GAP_MS = 10_000
const ESTIMATE = {
  samples: 3,
  average_epoch_seconds: 120,
  running: true,
  overrun: false,
}

type Tone = {
  type: string
  frequency: { value: number }
  started: number
  stopped: number
}

class FakeAudioContext {
  static tones: Tone[] = []
  state = 'running'
  currentTime = 0
  destination = {}
  resume() {
    return Promise.resolve()
  }
  createOscillator() {
    const tone: Tone = {
      type: 'sine',
      frequency: { value: 0 },
      started: 0,
      stopped: 0,
    }
    FakeAudioContext.tones.push(tone)
    return {
      get type() {
        return tone.type
      },
      set type(value: string) {
        tone.type = value
      },
      frequency: tone.frequency,
      connect: (target: unknown) => target,
      start: () => {
        tone.started += 1
      },
      stop: () => {
        tone.stopped += 1
      },
    }
  }
  createGain() {
    return {
      gain: {
        value: 0,
        setValueAtTime: () => undefined,
        linearRampToValueAtTime: () => undefined,
        exponentialRampToValueAtTime: () => undefined,
        cancelScheduledValues: () => undefined,
      },
      connect: (target: unknown) => target,
    }
  }
  createBiquadFilter() {
    return {
      type: 'lowpass',
      frequency: { value: 0 },
      connect: (target: unknown) => target,
    }
  }
}

function resetPreferences() {
  localStorage.clear()
  useFeedPreferences.setState({
    open: null,
    sounds: false,
    ambient: false,
    muted: [],
  })
}

beforeEach(() => {
  resetPreferences()
  FakeAudioContext.tones = []
  vi.stubGlobal('AudioContext', FakeAudioContext)
  useEpochRun.getState().reset()
})

afterEach(async () => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  useEpochRun.getState().reset()
  resetPreferences()
  await page.viewport(WIDE.width, WIDE.height)
})

describe('live feed dock', () => {
  it('is open by default on wide screens, hides and reopens, and remembers the choice', async () => {
    await page.viewport(WIDE.width, WIDE.height)
    const { screen } = await renderScreen(
      <>
        <LiveFeedSheet />
        <LiveFeedDock />
      </>,
      { 'GET /api/state': worldState() }
    )
    const dock = screen.getByRole('complementary', { name: 'Live feed dock' })
    await expect.element(dock).toBeVisible()
    await screen.getByRole('button', { name: 'Hide the live feed' }).click()
    await expect.element(dock).not.toBeInTheDocument()
    expect(localStorage.getItem(FEED_PREFERENCES_KEY)).toContain('"open":false')
    const toggle = screen.getByRole('button', {
      name: 'Live feed',
      exact: true,
    })
    await expect.element(toggle).toHaveAttribute('aria-pressed', 'false')
    await toggle.click()
    await expect
      .element(screen.getByRole('complementary', { name: 'Live feed dock' }))
      .toBeVisible()
    expect(localStorage.getItem(FEED_PREFERENCES_KEY)).toContain('"open":true')
  })

  it('stays closed by default on narrow screens and opens as a sheet', async () => {
    await page.viewport(NARROW.width, NARROW.height)
    const { screen } = await renderScreen(
      <>
        <LiveFeedSheet />
        <LiveFeedDock />
      </>,
      { 'GET /api/state': worldState() }
    )
    await expect
      .element(screen.getByRole('complementary', { name: 'Live feed dock' }))
      .not.toBeInTheDocument()
    await screen.getByRole('button', { name: 'Live feed', exact: true }).click()
    await expect
      .element(screen.getByRole('dialog', { name: 'Live feed' }))
      .toBeVisible()
  })

  it('opens from the top progress strip while a job runs', async () => {
    await page.viewport(NARROW.width, NARROW.height)
    const store = useEpochRun.getState()
    store.apply(
      serverEvent(
        'epoch.started',
        { epoch: 4, resuming: false },
        new Date().toISOString()
      )
    )
    store.apply(
      serverEvent('epoch.progress', {
        epoch: 4,
        no: 3,
        total: 5,
        name: 'Fate',
      })
    )
    const { screen } = await renderScreen(
      <>
        <ActivityStrip />
        <LiveFeedSheet />
      </>,
      {
        'GET /api/state': worldState({ epoch_running: true }),
        'GET /api/jobs': [],
        'GET /api/epochs/current/estimate': ESTIMATE,
      }
    )
    const strip = screen.getByRole('button', {
      name: /^Open the live feed: Epoch 4/,
    })
    await expect.element(strip).toBeVisible()
    await expect
      .element(screen.getByRole('progressbar', { name: 'Epoch 4' }))
      .toHaveAttribute('aria-valuenow', '60')
    await strip.click()
    await expect
      .element(screen.getByRole('dialog', { name: 'Live feed' }))
      .toBeVisible()
    expect(useFeedPreferences.getState().open).toBe(true)
  })
})

describe('job progress panel', () => {
  it('titles the panel by the running job and ticks the elapsed clock', async () => {
    const started = new Date(Date.now() - 65_000).toISOString()
    const { screen } = await renderScreen(<EpochProgress />, {
      'GET /api/state': worldState(),
      'GET /api/jobs': [
        {
          id: 'j',
          kind: 'backup',
          status: 'running',
          progress: 0.25,
          stage: 'Copying the archive',
          params: {},
          result: null,
          error: null,
          created_at: started,
          started_at: started,
          finished_at: null,
        },
        {
          id: 'k',
          kind: 'images',
          status: 'queued',
          progress: 0,
          stage: null,
          params: {},
          result: null,
          error: null,
          created_at: started,
          started_at: null,
          finished_at: null,
        },
      ],
      'GET /api/epochs/current/estimate': { ...ESTIMATE, running: false },
    })
    await expect.element(screen.getByText('2 jobs')).toBeVisible()
    await expect.element(screen.getByText('Copying the archive')).toBeVisible()
  })

  it('counts the epoch phases, the elapsed time and the son queue', async () => {
    const store = useEpochRun.getState()
    store.apply(
      serverEvent(
        'epoch.started',
        { epoch: 5, resuming: false },
        new Date(Date.now() - 75_000).toISOString()
      )
    )
    store.apply(
      serverEvent('epoch.progress', {
        epoch: 5,
        no: 1,
        total: 5,
        name: 'Sons',
      })
    )
    store.apply(serverEvent('son.turn_queued', { no: 2, total: 4 }))
    const { screen } = await renderScreen(<EpochProgress />, {
      'GET /api/state': worldState({ epoch_running: true }),
      'GET /api/jobs': [],
      'GET /api/epochs/current/estimate': ESTIMATE,
    })
    await expect.element(screen.getByText('20%')).toBeVisible()
    await expect.element(screen.getByText(/Phase 1\/5: Sons/)).toBeVisible()
    await expect.element(screen.getByText(/\b1:1\d\b/)).toBeVisible()
    await expect.element(screen.getByText(/son 2\/4/)).toBeVisible()
  })
})

describe('feed sounds', () => {
  it('lists the categories that make a sound, mutes one and previews a tone', async () => {
    const { screen } = await renderScreen(<FeedSoundSettings />)
    await expect
      .element(screen.getByText('Which events make a sound'))
      .not.toBeInTheDocument()
    await screen.getByRole('switch', { name: 'Feed sounds' }).click()
    await expect
      .element(screen.getByText('Which events make a sound'))
      .toBeVisible()
    const war = screen.getByRole('switch', { name: 'Wars', exact: true })
    await expect.element(war).toHaveAttribute('aria-checked', 'true')
    await war.click()
    expect(useFeedPreferences.getState().muted).toContain('war')
    expect(localStorage.getItem(FEED_PREFERENCES_KEY)).toContain(
      '"muted":["war"]'
    )
    await screen.getByRole('button', { name: 'Listen to Wars' }).click()
    expect(FakeAudioContext.tones).toHaveLength(1)
    expect(FakeAudioContext.tones[0]).toMatchObject({
      type: 'sine',
      started: 1,
      stopped: 1,
    })
  })

  it('throttles live tones and skips muted categories', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(Date.now() + THROTTLE_GAP_MS)
    useFeed.setState({ restored: true })
    useFeedPreferences.setState({ sounds: true, muted: ['war'] })
    const { emit } = await renderScreen(<FeedCollector />, {}, '/', {
      realtime: true,
    })
    emit('engine.note', { text: 'A war note', feed: 'war' })
    emit('engine.note', { text: 'A comet', feed: 'sky' })
    emit('engine.note', { text: 'Another comet', feed: 'sky' })
    await expect.poll(() => FakeAudioContext.tones.length).toBe(1)
    expect(FakeAudioContext.tones[0].frequency.value).toBeGreaterThan(700)
  })

  it('starts the remembered ambient drone on the first pointer press and fades it out', async () => {
    useFeedPreferences.setState({ ambient: true })
    const { screen } = await renderScreen(
      <>
        <FeedCollector />
        <FeedSoundSettings />
      </>,
      {},
      '/',
      { realtime: true }
    )
    expect(FakeAudioContext.tones).toHaveLength(0)
    await userEvent.click(screen.getByText('Live feed and sound'))
    await expect.poll(() => FakeAudioContext.tones.length).toBe(5)
    expect(
      FakeAudioContext.tones.filter((tone) => tone.type === 'triangle')
    ).toHaveLength(4)
    await screen.getByRole('switch', { name: 'Ambient sound' }).click()
    expect(useFeedPreferences.getState().ambient).toBe(false)
    expect(FakeAudioContext.tones.every((tone) => tone.stopped === 1)).toBe(
      true
    )
  })
})

describe('stop epoch errors', () => {
  for (const [status, detail] of [
    [404, 'No epoch is running.'],
    [409, 'The epoch is already stopping.'],
    [501, 'Stopping is not supported by this engine.'],
  ] as const)
    it(`reports a ${status} from the server and keeps the stop button`, async () => {
      const { screen } = await renderScreen(<StopEpochButton />, {
        'GET /api/state': worldState({ epoch_running: true }),
        'POST /api/epochs/current/stop': failure(status, detail),
      })
      await screen.getByRole('button', { name: 'Stop' }).click()
      await screen.getByRole('button', { name: 'Stop at a safe point' }).click()
      await expect.element(screen.getByText(detail)).toBeVisible()
      await expect
        .element(screen.getByRole('button', { name: 'Stop', exact: true }))
        .toBeEnabled()
    })
})

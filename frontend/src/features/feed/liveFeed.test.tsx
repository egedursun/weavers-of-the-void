import { serverEvent } from '@/test-utils/fixtures'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { userEvent } from 'vitest/browser'
import { FeedCollector } from './FeedCollector'
import { FeedSoundControls } from './FeedSoundControls'
import { LiveFeedPanel } from './LiveFeedPanel'
import { type FeedLine, toFeedLine } from './feedModel'
import { FEED_PREFERENCES_KEY, useFeed, useFeedPreferences } from './feedStore'

function line(
  id: number,
  kind: string,
  payload: Record<string, unknown>
): FeedLine {
  const built = toFeedLine(
    serverEvent(kind, { epoch: 3, ...payload }, undefined, id)
  )
  if (!built) throw new Error(`no line for ${kind}`)
  return built
}

function warNote(id: number): FeedLine {
  return line(id, 'engine.note', { text: `War note ${id}`, feed: 'war' })
}

function resetFeed() {
  useFeed.setState({
    lines: [],
    restored: false,
    actor: 'all',
    categories: [],
    expanded: [],
  })
  useFeedPreferences.setState({ sounds: false, ambient: false, muted: [] })
}

beforeEach(resetFeed)
afterEach(resetFeed)

describe('live feed panel', () => {
  it('shows a quiet empty state and a disabled clear button', async () => {
    const { screen } = await renderScreen(<LiveFeedPanel />)
    await expect.element(screen.getByText('Quiet')).toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: 'Clear the feed' }))
      .toHaveAttribute('aria-disabled', 'true')
  })

  it('renders lines with epoch stamps and clears them', async () => {
    useFeed
      .getState()
      .add([
        line(1, 'system.note', { text: 'The sun rises' }),
        line(2, 'system.note', { text: 'The moon sets' }),
      ])
    const { screen } = await renderScreen(<LiveFeedPanel />)
    await expect.element(screen.getByText('The sun rises')).toBeInTheDocument()
    await expect.element(screen.getByText('The moon sets')).toBeInTheDocument()
    await expect.element(screen.getByText(/Epoch 3 ·/)).toBeInTheDocument()
    await screen.getByRole('button', { name: 'Clear the feed' }).click()
    await expect.element(screen.getByText('Quiet')).toBeInTheDocument()
  })

  it('filters by actor and explains an empty filter result', async () => {
    useFeed.getState().add([
      line(1, 'system.note', { text: 'System speaks' }),
      line(2, 'son.turn_started', {
        son_id: 7,
        son_name: 'Ithren',
        resumed: false,
      }),
    ])
    const { screen } = await renderScreen(<LiveFeedPanel />)
    await screen.getByRole('radio', { name: 'Gods' }).click()
    await expect
      .element(screen.getByText('Ithren takes their turn'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('System speaks'))
      .not.toBeInTheDocument()
    await screen.getByRole('radio', { name: 'Fate' }).click()
    await expect
      .element(screen.getByText('Nothing matches this filter'))
      .toBeInTheDocument()
  })

  it('offers category chips only for categories present and filters by them', async () => {
    useFeed
      .getState()
      .add([
        line(1, 'engine.note', { text: 'Walls fall', feed: 'war' }),
        line(2, 'engine.note', { text: 'Waters rise', feed: 'disaster' }),
      ])
    const { screen } = await renderScreen(<LiveFeedPanel />)
    await expect
      .element(screen.getByRole('button', { name: 'Sky events' }))
      .not.toBeInTheDocument()
    await screen.getByRole('button', { name: 'Wars' }).click()
    await expect.element(screen.getByText('Walls fall')).toBeInTheDocument()
    await expect
      .element(screen.getByText('Waters rise'))
      .not.toBeInTheDocument()
  })

  it('groups long same-category runs and expands them on demand', async () => {
    useFeed.getState().add([1, 2, 3, 4, 5].map(warNote))
    const { screen } = await renderScreen(<LiveFeedPanel />)
    await expect.element(screen.getByText('War note 2')).toBeInTheDocument()
    await expect.element(screen.getByText('War note 4')).not.toBeInTheDocument()
    await screen.getByRole('button', { name: '+3 similar: Wars' }).click()
    await expect.element(screen.getByText('War note 5')).toBeInTheDocument()
    await screen.getByRole('button', { name: 'Collapse' }).click()
    await expect.element(screen.getByText('War note 5')).not.toBeInTheDocument()
  })

  it('inserts a continues header when parallel actors interleave', async () => {
    useFeed.getState().add([
      line(1, 'son.turn_started', {
        son_id: 1,
        son_name: 'Ithren',
        resumed: false,
      }),
      line(2, 'son.turn_started', {
        son_id: 2,
        son_name: 'Valka',
        resumed: false,
      }),
      line(3, 'son.turn_finished', {
        son_id: 1,
        son_name: 'Ithren',
        status: 'success',
      }),
    ])
    const { screen } = await renderScreen(<LiveFeedPanel />)
    await expect
      .element(screen.getByText('Ithren continues'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Valka continues'))
      .not.toBeInTheDocument()
  })

  it('counts unseen events when scrolled away from the bottom and jumps back', async () => {
    useFeed
      .getState()
      .add(
        Array.from({ length: 30 }, (_, index) =>
          line(index + 1, 'system.note', { text: `Event number ${index + 1}` })
        )
      )
    const { screen } = await renderScreen(<LiveFeedPanel />)
    const scroller = screen.getByLabelText('Feed lines', { exact: true })
    const element = (await scroller.element()) as HTMLElement
    element.scrollTop = 0
    element.dispatchEvent(new Event('scroll'))
    useFeed
      .getState()
      .add([
        line(100, 'system.note', { text: 'Late news' }),
        line(101, 'system.note', { text: 'Later news' }),
      ])
    const badge = screen.getByRole('button', { name: '2 new events' })
    await expect.element(badge).toBeInTheDocument()
    await badge.click()
    await expect
      .element(screen.getByRole('button', { name: /new event/ }))
      .not.toBeInTheDocument()
  })

  it('renders system errors with a link and the retry note', async () => {
    useFeed.getState().add([
      line(1, 'system.error', {
        text: 'The son stumbled',
        will_retry: true,
        son_id: 4,
      }),
    ])
    const { screen } = await renderScreen(<LiveFeedPanel />)
    await expect
      .element(screen.getByText('The son stumbled'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('It will be retried.'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('link', { name: 'Open the son' }))
      .toBeInTheDocument()
  })

  it('renders world engine lines, a quiet epoch, record events and the network repair line', async () => {
    useFeed.getState().add([
      line(1, 'engine.finished', { notes: 0 }),
      line(2, 'engine.finished', { notes: 3 }),
      line(3, 'entity.deepened', { entity_id: 9, name: 'Stonehold' }),
      line(4, 'foreign_god.deepened', { id: 5, name: 'Old Nyx' }),
      line(5, 'network.repaired', {
        text: '12 records examined, 4 links made',
      }),
      line(6, 'ledger.undone', { entry_id: 8, applied: 5, conflicts: 2 }),
    ])
    const { screen } = await renderScreen(<LiveFeedPanel />)
    await expect
      .element(
        screen.getByText('A quiet epoch: the world engine wrote nothing')
      )
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('The world engine wrote 3 notes'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('link', { name: 'Stonehold' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('link', { name: 'Old Nyx' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('12 records examined, 4 links made'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('5 changes reverted, 2 conflicts skipped.'))
      .toBeInTheDocument()
  })

  it('shows the restored note after replaying the journal', async () => {
    useFeed
      .getState()
      .restore([line(1, 'system.note', { text: 'Before reload' })])
    const { screen } = await renderScreen(<LiveFeedPanel />)
    await expect
      .element(
        screen.getByText('Earlier events were restored from the server.')
      )
      .toBeInTheDocument()
  })
})

describe('feed collector', () => {
  it('restores the journal once and drops quiet kinds', async () => {
    const journal = [
      serverEvent('system.note', { text: 'Restored one' }, undefined, 1),
      serverEvent(
        'job.progress',
        { job_id: 'a', kind: 'epoch', progress: 0.5 },
        undefined,
        2
      ),
      serverEvent(
        'epoch.finished',
        { epoch: 2, new_epoch: 3, duration_s: 60 },
        undefined,
        3
      ),
    ]
    const { screen, server } = await renderScreen(
      <>
        <FeedCollector />
        <LiveFeedPanel />
      </>,
      { 'GET /api/activity-log': journal },
      '/',
      { realtime: true }
    )
    await expect.element(screen.getByText('Restored one')).toBeInTheDocument()
    expect(useFeed.getState().restored).toBe(true)
    expect(useFeed.getState().lines.map((item) => item.id)).not.toContain(2)
    expect(server.callsTo('GET /api/activity-log')).toHaveLength(1)
  })

  it('appends live events from the stream as they arrive', async () => {
    useFeed.setState({ restored: true })
    const { screen, emit } = await renderScreen(
      <>
        <FeedCollector />
        <LiveFeedPanel />
      </>,
      {},
      '/',
      { realtime: true }
    )
    emit('system.note', { text: 'A comet passes' })
    await expect.element(screen.getByText('A comet passes')).toBeInTheDocument()
  })

  it('plays no tone for muted or silent preferences but keeps lines', async () => {
    useFeed.setState({ restored: true })
    useFeedPreferences.setState({ sounds: true, muted: ['war'] })
    const { screen, emit } = await renderScreen(
      <>
        <FeedCollector />
        <LiveFeedPanel />
      </>,
      {},
      '/',
      { realtime: true }
    )
    emit('engine.note', { text: 'Muted war note', feed: 'war' })
    await expect.element(screen.getByText('Muted war note')).toBeInTheDocument()
  })
})

describe('feed sound controls', () => {
  it('toggles feed sounds and persists the choice', async () => {
    const { screen } = await renderScreen(<FeedSoundControls />)
    const toggle = screen.getByRole('button', { name: 'Feed sounds' })
    await expect.element(toggle).toHaveAttribute('aria-pressed', 'false')
    await toggle.click()
    await expect.element(toggle).toHaveAttribute('aria-pressed', 'true')
    expect(useFeedPreferences.getState().sounds).toBe(true)
    expect(localStorage.getItem(FEED_PREFERENCES_KEY)).toContain(
      '"sounds":true'
    )
  })

  it('toggles the ambient drone preference and remembers it', async () => {
    const { screen } = await renderScreen(<FeedSoundControls />)
    const toggle = screen.getByRole('button', { name: 'Ambient sound' })
    await toggle.click()
    expect(useFeedPreferences.getState().ambient).toBe(true)
    await userEvent.click(toggle)
    expect(useFeedPreferences.getState().ambient).toBe(false)
    expect(localStorage.getItem(FEED_PREFERENCES_KEY)).toContain(
      '"ambient":false'
    )
  })
})

describe('feed store', () => {
  it('keeps lines ordered, de-duplicated and capped, and toggles categories and groups', () => {
    const store = useFeed.getState()
    store.add([
      line(2, 'system.note', { text: 'b' }),
      line(1, 'system.note', { text: 'a' }),
    ])
    store.add([line(2, 'system.note', { text: 'b again' })])
    expect(useFeed.getState().lines.map((item) => item.id)).toEqual([1, 2])
    store.toggleCategory('war')
    store.toggleCategory('sky')
    store.toggleCategory('war')
    expect(useFeed.getState().categories).toEqual(['sky'])
    store.clearCategories()
    expect(useFeed.getState().categories).toEqual([])
    store.toggleGroup('g')
    store.toggleGroup('g')
    expect(useFeed.getState().expanded).toEqual([])
  })
})

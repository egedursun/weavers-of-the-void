import { onApi, renderApp, resetApi } from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FeelingsSection } from './FeelingsSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

function dream(id: number, readingName: string | null) {
  return {
    id,
    kind: 'prophetic',
    label: `Dream ${id}`,
    epoch: 4,
    intensity: 60,
    content: [],
    sender: null,
    partner: null,
    world: null,
    reading: 'warning',
    reading_name: readingName,
    reader: null,
    reading_true: null,
    recurring: false,
  }
}

function serve(dreams: ReturnType<typeof dream>[]) {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/minds/7/feelings', {
    node_id: 7,
    name: 'Kel',
    applies: true,
    locked: [],
    lockable: [],
    mood: 'fine',
    mood_score: 0,
    mood_held: false,
    thoughts: [],
    emotions: [],
    formative: [],
    griefs: [],
    dreams,
    thought_kinds: [],
    emotion_kinds: [],
    dream_kinds: [{ key: 'prophetic', label: 'Prophetic' }],
    readings: [{ key: 'warning', label: 'A warning' }],
    long_term_threshold: 50,
  })
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 7, name: 'Kel', type: 'mortal', status: 'canon' },
  ])
}

describe('dream log', () => {
  beforeEach(resetApi)

  it('shows the reading a people gives a dream in its own way', async () => {
    serve([dream(1, 'the reading of the Ardan')])
    const { screen } = await renderApp(<FeelingsSection nodeId={7} />)
    await expect
      .element(
        screen.getByText('Read in their way as the reading of the Ardan')
      )
      .toBeInTheDocument()
  })

  it('shows no such badge when the people has no reading of its own', async () => {
    serve([dream(2, null)])
    const { screen } = await renderApp(<FeelingsSection nodeId={7} />)
    await expect.element(screen.getByText('Dream 2')).toBeInTheDocument()
    expect(document.body.textContent).not.toContain('Read in their way as')
  })
})

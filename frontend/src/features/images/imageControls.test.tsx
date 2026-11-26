import { serverEvent, worldState } from '@/test-utils/fixtures'
import { type MockRoutes } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, describe, expect, it } from 'vitest'
import { userEvent } from 'vitest/browser'
import { BulkImageGenPanel } from './BulkImageGenPanel'
import { GenerateImageButton } from './GenerateImageButton'
import { GenerateImageMini } from './GenerateImageMini'
import { PortraitGenerateOverlay } from './PortraitGenerateOverlay'
import { useImageGenStore } from './imageGenState'

const IDLE_BULK = {
  running: false,
  stop_requested: false,
  auto: false,
  total: 0,
  done: 0,
  failed: 0,
  skipped: 0,
  rerun_requested: false,
  restyle: false,
}

function queue(overrides: Record<string, unknown> = {}) {
  return {
    available: true,
    reason: null,
    current: null,
    queue: [],
    bulk: IDLE_BULK,
    width: 512,
    height: 512,
    steps: 20,
    log: [],
    ...overrides,
  }
}

function routes(
  status: Record<string, unknown> = {},
  extra: MockRoutes = {},
  configured = true
): MockRoutes {
  return {
    'GET /api/state': worldState({
      promptless_count: 2,
      role_models: [
        { role: 'world_agents', model: 'quick · Studio key' },
        { role: 'writing', model: 'quick · Studio key' },
        { role: 'conversation', model: 'quick · Studio key' },
        { role: 'images', model: configured ? 'painter · Studio key' : '' },
      ],
    }),
    'GET /api/image-gen': { status: queue(status), missing: 7, off_style: 0 },
    'GET /api/names': [],
    'GET /api/jobs': [],
    'POST /api/image-gen': { queued: true, position: 0 },
    ...extra,
  }
}

afterEach(() => useImageGenStore.setState({ progress: {}, lines: [] }))

describe('generate image button', () => {
  it('generates the first image or one more when images exist', async () => {
    const first = await renderScreen(
      <GenerateImageButton nodeId={42} hasImages={false} />,
      routes()
    )
    const button = first.screen.getByRole('button', { name: /Generate image/ })
    await expect.element(button).toBeEnabled()
    await button.click()
    await expect
      .poll(() => first.server.callsTo('POST /api/image-gen').length)
      .toBe(1)
    expect(first.server.callsTo('POST /api/image-gen')[0].body).toMatchObject({
      node_id: 42,
    })
  })

  it('offers one more image when the record already has some', async () => {
    const { screen } = await renderScreen(
      <GenerateImageButton nodeId={42} hasImages />,
      routes()
    )
    await expect
      .element(screen.getByRole('button', { name: /Generate one more/ }))
      .toBeVisible()
  })

  it('is disabled with the reason when the model is missing', async () => {
    const { screen } = await renderScreen(
      <GenerateImageButton nodeId={42} hasImages={false} />,
      routes({ available: false, reason: 'The model file is missing.' })
    )
    const button = screen.getByRole('button', { name: /Generate image/ })
    await expect
      .element(button)
      .toHaveAttribute('aria-description', 'The model file is missing.')
  })

  it('is disabled in a read-only world', async () => {
    const { screen } = await renderScreen(
      <GenerateImageButton
        nodeId={42}
        hasImages={false}
        readOnlyReason='A guest world is open read-only.'
      />,
      routes()
    )
    await expect
      .element(screen.getByRole('button', { name: /Generate image/ }))
      .toHaveAttribute('aria-description', 'A guest world is open read-only.')
  })
})

describe('mini generate button', () => {
  it('queues an image from an atlas row and shows the queue position', async () => {
    const { screen, server } = await renderScreen(
      <GenerateImageMini nodeId={42} name='Velmora' />,
      routes()
    )
    const mini = screen.getByRole('button', { name: /Velmora/ })
    await mini.click()
    await expect
      .poll(() => server.callsTo('POST /api/image-gen').length)
      .toBe(1)
  })

  it('shows the progress ring while its image is painted', async () => {
    const { screen, emit } = await renderScreen(
      <GenerateImageMini nodeId={42} name='Velmora' />,
      routes({
        current: {
          node_id: 42,
          name: 'Velmora',
          started_at: new Date().toISOString(),
        },
      })
    )
    emit('image.progress', { node_id: 42, stage: 'steps', percent: 40 })
    await expect
      .element(screen.getByRole('button', { name: /Velmora/ }))
      .toHaveAttribute('aria-disabled', 'true')
  })

  it('reports how many images wait ahead in the queue', async () => {
    const { screen } = await renderScreen(
      <GenerateImageMini nodeId={42} name='Velmora' />,
      routes({
        current: { node_id: 9, name: 'Other' },
        queue: [
          { node_id: 8, name: 'A' },
          { node_id: 42, name: 'Velmora' },
        ],
      })
    )
    await expect
      .element(screen.getByRole('button', { name: /Velmora/ }))
      .toHaveAttribute('aria-description', 'Queued; 2 ahead.')
  })
})

describe('portrait generate overlay', () => {
  it('turns an empty portrait into a generate button reachable by keyboard', async () => {
    let opened = 0
    const { screen, server } = await renderScreen(
      <PortraitGenerateOverlay
        nodeId={42}
        name='Velmora'
        cover={null}
        onOpen={() => (opened += 1)}
      />,
      routes()
    )
    const portrait = screen.getByRole('button', { name: /Velmora/ })
    await expect.element(portrait).toBeVisible()
    ;(portrait.element() as HTMLElement).focus()
    await userEvent.keyboard('{Enter}')
    await expect
      .poll(() => server.callsTo('POST /api/image-gen').length)
      .toBe(1)
    expect(opened).toBe(0)
  })

  it('shows the stage text and a large progress ring while painting', async () => {
    const { screen } = await renderScreen(
      <PortraitGenerateOverlay
        nodeId={42}
        name='Velmora'
        cover={null}
        onOpen={() => undefined}
      />,
      routes({ current: { node_id: 42, name: 'Velmora' } })
    )
    await expect
      .element(screen.getByRole('progressbar', { name: 'Image generation' }))
      .toBeVisible()
    await expect.element(screen.getByText('Preparing')).toBeVisible()
    useImageGenStore
      .getState()
      .record(
        serverEvent(
          'image.progress',
          { node_id: 42, stage: 'steps', percent: 55 },
          new Date().toISOString()
        )
      )
    await expect.element(screen.getByText('Painting')).toBeVisible()
    await expect
      .element(screen.getByRole('progressbar', { name: 'Image generation' }))
      .toHaveAttribute('aria-valuenow', '55')
  })

  it('opens the image when a cover exists', async () => {
    let opened = 0
    const { screen, server } = await renderScreen(
      <PortraitGenerateOverlay
        nodeId={42}
        name='Velmora'
        cover='/api/media/velmora.png'
        onOpen={() => (opened += 1)}
      />,
      routes()
    )
    await screen
      .getByRole('link', { name: 'Open the images of Velmora' })
      .click()
    expect(opened).toBe(1)
    expect(server.callsTo('POST /api/image-gen')).toHaveLength(0)
  })
})

describe('bulk image generation panel', () => {
  it('summarises missing and promptless images and updates live from bulk events', async () => {
    let bulk = IDLE_BULK
    const { screen, server, emit } = await renderScreen(<BulkImageGenPanel />, {
      ...routes(),
      'GET /api/image-gen': () => ({
        status: queue({ bulk }),
        missing: 7,
        off_style: 0,
      }),
    })
    await expect
      .element(
        screen.getByRole('button', { name: 'Generate 7 missing images' })
      )
      .toBeVisible()
    await expect.element(screen.getByText('512 × 512 · 20 steps')).toBeVisible()
    const before = server.callsTo('GET /api/image-gen').length
    bulk = { ...IDLE_BULK, running: true, total: 7, done: 3, failed: 1 }
    emit('image.status', {})
    emit('image.done', { node_id: 5, file: 'a.png' })
    await expect
      .poll(() => server.callsTo('GET /api/image-gen').length)
      .toBeGreaterThan(before)
    await expect
      .element(screen.getByText('3 done · 1 failed · 0 skipped of 7'))
      .toBeVisible()
    await expect
      .element(
        screen.getByRole('progressbar', { name: 'Bulk image generation' })
      )
      .toBeVisible()
  })
})

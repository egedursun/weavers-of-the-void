import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { FakeEventSource, serverEvent } from '@/test-utils/fakeEventSource'
import { beforeEach, describe, expect, it } from 'vitest'
import { render } from 'vitest-browser-react'
import { RealtimeProvider } from './RealtimeProvider'
import { useRealtimeStatus } from './realtimeContext'
import { useEvent } from './useEvent'

function Probe() {
  const status = useRealtimeStatus()
  const [stage, setStage] = useState('none')
  useEvent('job.progress', (event) => setStage(event.payload.stage ?? 'none'))
  return (
    <p>
      {status} {stage}
    </p>
  )
}

const createSource = (url: string) => new FakeEventSource(url)

describe('RealtimeProvider', () => {
  beforeEach(() => FakeEventSource.reset())

  it('opens one stream and routes events to subscribers', async () => {
    const screen = await render(
      <QueryClientProvider client={new QueryClient()}>
        <RealtimeProvider url='/api/events' createSource={createSource}>
          <Probe />
        </RealtimeProvider>
      </QueryClientProvider>
    )
    const source = FakeEventSource.latest()
    expect(source.url).toBe('/api/events')
    source.open()
    source.emit(
      'job.progress',
      serverEvent(1, 'job.progress', {
        job_id: 'a',
        kind: 'epoch',
        progress: 0.5,
        stage: 'Fate judges',
      })
    )
    await expect
      .element(screen.getByText('open Fate judges'))
      .toBeInTheDocument()
  })
})

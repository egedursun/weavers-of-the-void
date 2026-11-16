import { renderApp } from '@/test-utils/fakeApi'
import { Trash2 } from 'lucide-react'
import { describe, expect, it, vi } from 'vitest'
import { Button } from '@/components/ui/button'
import { RecordRow } from './parts'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

describe('a record row', () => {
  it('keeps its title readable at phone width beside a long action', async () => {
    const { screen } = await renderApp(
      <div className='w-80'>
        <ul>
          <RecordRow
            icon={Trash2}
            tone='info'
            title='Long winter on Orvael'
            caption='Since epoch 5, for 3 epochs'
            aside={
              <Button size='sm' variant='ghost'>
                <Trash2 />
                Give the seasons back their measure
              </Button>
            }
          />
        </ul>
      </div>
    )
    await expect
      .element(screen.getByText('Long winter on Orvael'))
      .toBeVisible()
  })
})

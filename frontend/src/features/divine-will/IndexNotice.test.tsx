import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { IndexNotice } from './IndexNotice'

describe('the notice while the Divine Will reads the world', () => {
  it('shows how much of the world it has read as a share and in numbers', async () => {
    const { screen } = await renderScreen(<IndexNotice />, {
      'GET /api/divine-will/index': {
        status: 'building',
        note: '',
        semantic: true,
        passages: 110864,
        embedded: 30832,
        pending: 72,
        share: 0.28,
        sources: [],
        built_at: null,
        model: 'model',
      },
    })
    await expect
      .element(screen.getByText('The Divine Will is still reading the world'))
      .toBeVisible()
    await expect.element(screen.getByText('28%')).toBeVisible()
    await expect
      .element(screen.getByText('110,864 passages read'))
      .toBeVisible()
    await expect
      .element(screen.getByText(/72 parts of the world still to read/))
      .toBeVisible()
  })

  it('shows no share before the first passage is written', async () => {
    const { screen } = await renderScreen(<IndexNotice />, {
      'GET /api/divine-will/index': {
        status: 'building',
        note: 'Reading the whole world once; later changes are read as they happen.',
        semantic: true,
        passages: 0,
        embedded: 0,
        pending: 640,
        share: 0,
        sources: [],
        built_at: null,
        model: 'model',
      },
    })
    await expect
      .element(
        screen.getByText('The Divine Will is preparing what it will read')
      )
      .toBeVisible()
    expect(screen.getByText('0%').query()).toBeNull()
    expect(screen.getByText('0 passages read').query()).toBeNull()
  })
})

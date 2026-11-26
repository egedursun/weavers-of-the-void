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
        pending: 80032,
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
      .element(screen.getByText('30,832 of 110,864 read'))
      .toBeVisible()
  })

  it('shows no finished share while it gathers and cuts the world before reading', async () => {
    const { screen } = await renderScreen(<IndexNotice />, {
      'GET /api/divine-will/index': {
        status: 'building',
        note: 'Cutting what it gathered into passages.',
        semantic: true,
        passages: 763333,
        embedded: 763333,
        pending: 0,
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
    expect(screen.getByText('100%').query()).toBeNull()
    expect(screen.getByText('763,333 of 763,333 read').query()).toBeNull()
  })
})

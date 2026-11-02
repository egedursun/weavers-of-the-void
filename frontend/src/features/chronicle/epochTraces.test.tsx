import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { EpochTraces } from './EpochTraces'

type Props = Parameters<typeof EpochTraces>[0]

function stat(
  epoch: number,
  sons: Record<string, { faith: number; existence: number }>
) {
  return {
    epoch,
    data: {
      population: 1000 * epoch,
      followers: 400 * epoch,
      words: 50 * epoch,
      entities: 30 * epoch,
      sons,
    },
  }
}

const SONS = [
  { son: { id: 7, name: 'Thalassir', rarity: 'legendary' } },
  { son: { id: 9, name: 'Kharun the Ashen', rarity: 'rare' } },
  { son: { id: 11, name: 'Never Traced', rarity: 'common' } },
] as unknown as Props['sons']

describe('epoch traces', () => {
  it('draws one small-multiple card per traced son with faith and existence charts', async () => {
    const stats = [
      stat(1, {
        '7': { faith: 4, existence: 60 },
        '9': { faith: 20, existence: 30 },
      }),
      stat(2, {
        '7': { faith: 9, existence: 70 },
        '9': { faith: 12, existence: 15 },
      }),
      stat(3, { '7': { faith: 18, existence: 72 } }),
    ] as unknown as Props['stats']
    const { screen } = await renderScreen(
      <EpochTraces stats={stats} sons={SONS} />,
      {},
      '/',
      { realtime: false }
    )
    await expect
      .element(screen.getByText('Sons through the epochs'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: 'Thalassir' }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: 'Kharun the Ashen' }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: 'Never Traced' }))
      .not.toBeInTheDocument()
    await expect
      .poll(
        () =>
          screen.getByRole('heading', { name: 'Faith', exact: true }).elements()
            .length
      )
      .toBe(2)
    await expect
      .poll(
        () =>
          screen
            .getByRole('heading', { name: 'Existence', exact: true })
            .elements().length
      )
      .toBe(2)
    for (const title of [
      'Population',
      'Disciples',
      'Words in the lexicons',
      'Records in canon',
    ])
      await expect
        .element(screen.getByRole('heading', { name: title }))
        .toBeVisible()
  })

  it('waits for two closed epochs before drawing', async () => {
    const stats = [
      stat(1, { '7': { faith: 4, existence: 60 } }),
    ] as unknown as Props['stats']
    const { screen } = await renderScreen(
      <EpochTraces stats={stats} sons={SONS} />,
      {},
      '/',
      { realtime: false }
    )
    await expect
      .element(screen.getByText('Not enough epochs yet'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Sons through the epochs'))
      .not.toBeInTheDocument()
  })
})

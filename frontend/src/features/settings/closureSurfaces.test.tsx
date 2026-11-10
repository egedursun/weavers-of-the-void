import { worldState } from '@/test-utils/fixtures'
import { type MockRequest, failure } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { SecondaryTargetForm } from '@/features/backups/SecondaryTargetForm'
import { SeedPanel } from '@/features/engine/SeedPanel'
import { AddWordsForm } from '@/features/languages/AddWordsForm'
import { wordsOf } from '@/features/languages/addWords'
import { SnapshotButton } from '@/features/map/MapTimeSlider'
import { GenesisRecord } from '@/features/onboarding/GenesisRecord'

const DONE = {
  action: 'done',
  message: 'It is done.',
  ledger_entry_id: null,
  job_id: null,
}

describe('second backup folder', () => {
  it('saves a folder, then stops copying', async () => {
    let directory: string | null = null
    const { screen, server } = await renderScreen(
      <SecondaryTargetForm readOnly={false} />,
      {
        'GET /api/backups/secondary': () => ({ directory, keep: 5 }),
        'PUT /api/backups/secondary': (request: MockRequest) => {
          directory = (request.body as { directory: string | null }).directory
          return { directory, keep: 5 }
        },
      }
    )
    const save = screen.getByRole('button', { name: 'Save the folder' })
    await expect
      .element(save)
      .toHaveAttribute('aria-description', 'Write a folder path first')
    await expect
      .element(screen.getByText(/The last 5 copies are kept there\./))
      .toBeVisible()
    await screen
      .getByRole('textbox', { name: 'A second copy elsewhere' })
      .fill('~/Sync/aerona')
    await save.click()
    await expect
      .poll(() => server.callsTo('PUT /api/backups/secondary').length)
      .toBe(1)
    expect(server.callsTo('PUT /api/backups/secondary')[0].body).toEqual({
      directory: '~/Sync/aerona',
    })
    await expect
      .element(screen.getByText('Now copying to ~/Sync/aerona'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Stop copying' }).click()
    await expect
      .poll(() => server.callsTo('PUT /api/backups/secondary').length)
      .toBe(2)
    expect(server.callsTo('PUT /api/backups/secondary')[1].body).toEqual({
      directory: null,
    })
  })

  it('stays read-only in a guest world', async () => {
    const { screen } = await renderScreen(<SecondaryTargetForm readOnly />, {
      'GET /api/backups/secondary': { directory: '/mnt/backup', keep: 3 },
    })
    await expect
      .element(screen.getByRole('button', { name: 'Stop copying' }))
      .toBeDisabled()
  })

  it('shows the server refusal', async () => {
    const failed = await renderScreen(
      <SecondaryTargetForm readOnly={false} />,
      {
        'GET /api/backups/secondary': failure(
          500,
          'The folder cannot be read.'
        ),
      }
    )
    await expect
      .element(failed.screen.getByText('The folder cannot be read.'))
      .toBeVisible()
  })
})

describe('engine seed', () => {
  it('shows the world seed, epoch and the step streams', async () => {
    const { screen } = await renderScreen(<SeedPanel />, {
      'GET /api/engine/seed': {
        world_seed: 918273,
        epoch: 12,
        stream_format: "world seed + epoch + '<phase>.<stream>'",
        phase_streams: ['population', 'warfare'],
      },
    })
    await expect.element(screen.getByText('918273')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Copy the world seed' }))
      .toBeVisible()
    await screen.getByRole('button', { name: '2 step streams' }).click()
    await expect
      .element(screen.getByText('Population', { exact: true }))
      .toBeVisible()
  })
})

describe('genesis record', () => {
  it('lists the choices kept from the genesis wizard', async () => {
    const { screen } = await renderScreen(<GenesisRecord />, {
      'GET /api/genesis/settings': {
        lore_language: 'english',
        seed_idea: 'A sea of salt that remembers',
        tone: 'Grave and tidal',
        settings: {
          template: 'mythic_age',
          magic: 60,
          darkness: 30,
          technology: 'bronze',
          language_texture: 'flowing',
          peoples: 3,
          cosmos_size: 'small',
          storyteller: 'rising',
        },
      },
    })
    await expect
      .element(screen.getByText('A sea of salt that remembers'))
      .toBeVisible()
    await expect.element(screen.getByText('Mythic age')).toBeVisible()
    await expect.element(screen.getByText('Flowing')).toBeVisible()
    await expect.element(screen.getByText('Rising')).toBeVisible()
  })
})

describe('teaching a language new words', () => {
  it('keeps only rows with a word and a meaning', () => {
    expect(
      wordsOf([
        { key: 1, word: ' sal ', meaning: ' salt ', kind: 'noun' },
        { key: 2, word: 'orr', meaning: '', kind: 'any' },
        { key: 3, word: 'tem', meaning: 'tide', kind: 'any' },
      ])
    ).toEqual([
      { word: 'sal', meaning: 'salt', kind: 'noun' },
      { word: 'tem', meaning: 'tide', kind: null },
    ])
  })

  it('adds several rows through the language words route', async () => {
    const { screen, server } = await renderScreen(
      <AddWordsForm languageId={55} languageName='Saltspeech' />,
      {
        'GET /api/state': worldState(),
        'POST /api/languages/{language_id}/words': {
          ...DONE,
          message: '2 words were added to Saltspeech.',
        },
      }
    )
    await expect
      .element(screen.getByRole('button', { name: 'Add the word' }))
      .toHaveAttribute(
        'aria-description',
        'Write at least one word and its meaning.'
      )
    await screen.getByRole('textbox', { name: 'Word 1' }).fill('sal')
    await screen.getByRole('textbox', { name: 'Meaning 1' }).fill('salt')
    await screen.getByRole('button', { name: 'Another word' }).click()
    await screen.getByRole('textbox', { name: 'Word 2' }).fill('tem')
    await screen.getByRole('textbox', { name: 'Meaning 2' }).fill('tide')
    await screen.getByRole('combobox', { name: 'Kind of word 2' }).click()
    await screen.getByRole('option', { name: 'Verb' }).click()
    await screen.getByRole('button', { name: 'Add 2 words' }).click()
    await expect
      .poll(
        () => server.callsTo('POST /api/languages/{language_id}/words').length
      )
      .toBe(1)
    const call = server.callsTo('POST /api/languages/{language_id}/words')[0]
    expect(call.path).toBe('/api/languages/55/words')
    expect(call.body).toEqual({
      words: [
        { word: 'sal', meaning: 'salt', kind: null },
        { word: 'tem', meaning: 'tide', kind: 'verb' },
      ],
    })
    await expect
      .element(screen.getByText('2 words were added to Saltspeech.'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('textbox', { name: 'Word 1' }))
      .toHaveValue('')
  })
})

describe('map snapshot', () => {
  it('records the maps of this epoch now', async () => {
    const { screen, server } = await renderScreen(<SnapshotButton />, {
      'GET /api/state': worldState(),
      'POST /api/actions/map:snapshot': DONE,
    })
    await screen.getByRole('button', { name: 'Record this epoch' }).click()
    await expect
      .poll(() => server.callsTo('POST /api/actions/map:snapshot').length)
      .toBe(1)
    await expect
      .element(screen.getByText('The maps of this epoch were recorded'))
      .toBeVisible()
  })

  it('waits while an epoch runs', async () => {
    const busy = await renderScreen(<SnapshotButton />, {
      'GET /api/state': worldState({ epoch_running: true }),
    })
    await expect
      .element(busy.screen.getByRole('button', { name: 'Record this epoch' }))
      .toHaveAttribute(
        'aria-description',
        'An epoch is running; this opens when it ends.'
      )
  })
})

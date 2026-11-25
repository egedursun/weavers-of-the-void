import { FakeEventSource } from '@/test-utils/fakeEventSource'
import { type MockRequest, failure } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { userEvent } from 'vitest/browser'
import { libraryQueryClient } from '@/api/queryClients'
import { chooseUniverse, releaseDocument } from '@/api/universeStore'
import { LibraryScreen } from './LibraryScreen'
import { UniverseSwitcher } from './UniverseSwitcher'
import { type UniverseSummary } from './types'
import {
  FIRST_ID,
  SECOND_ID,
  libraryJob,
  trashPage,
  universePage,
  universeSummary,
} from './universeFixtures'

const NO_EVENTS = { items: [], total: 0, offset: 0, limit: 50 }

function libraryRoutes(
  shelf: UniverseSummary[],
  extra: Record<string, unknown> = {}
) {
  return {
    'GET /api/library/universes': (request: MockRequest) =>
      universePage(
        request.query.get('status') === 'archived'
          ? shelf.filter((item) => item.status === 'archived')
          : shelf.filter((item) => item.status === 'active')
      ),
    'GET /api/library/universes/{id}': (request: MockRequest) => ({
      ...(shelf.find((item) => request.path.endsWith(item.id)) ?? shelf[0]),
      events: [],
    }),
    'GET /api/library/trash': trashPage(),
    'GET /api/library/events': NO_EVENTS,
    ...extra,
  }
}

function renderLibrary(routes: Record<string, unknown>) {
  return renderScreen(
    <LibraryScreen createSource={(url) => new FakeEventSource(url)} />,
    routes,
    '/',
    { realtime: false }
  )
}

beforeEach(() => {
  libraryQueryClient.clear()
  libraryQueryClient.setDefaultOptions({
    queries: { retry: false, gcTime: 0 },
    mutations: { retry: false },
  })
})

afterEach(() => {
  chooseUniverse(null)
  releaseDocument()
  localStorage.removeItem('aerona.universe.last')
})

describe('the Library of Universes', () => {
  it('offers to create or import when the hall is empty', async () => {
    const { screen } = await renderLibrary(libraryRoutes([]))
    await expect
      .element(screen.getByText('No universe stands here yet'))
      .toBeInTheDocument()
    await expect
      .element(
        screen.getByRole('button', { name: 'Create a universe' }).first()
      )
      .toBeInTheDocument()
    await expect
      .element(
        screen.getByRole('button', { name: 'Import a universe' }).first()
      )
      .toBeInTheDocument()
  })

  it('stands every universe on the shelf with its facts and listens to the library', async () => {
    const shelf = [
      universeSummary({ pinned: true }),
      universeSummary({
        id: SECOND_ID,
        name: 'Saltwyrd',
        origin: 'imported',
        epoch: 9,
        year: 450,
        tags: ['favourite'],
      }),
    ]
    const { screen } = await renderLibrary(libraryRoutes(shelf))
    const books = screen.getByRole('list', { name: 'Universes' })
    await expect
      .element(books.getByRole('heading', { name: 'Saltwyrd' }))
      .toBeInTheDocument()
    await expect
      .element(books.getByRole('heading', { name: 'Eldmark' }))
      .toBeInTheDocument()
    await expect
      .element(books.getByText('Epoch 9 · Year 450').first())
      .toBeInTheDocument()
    await expect.element(books.getByText('Imported')).toBeInTheDocument()
    await expect
      .element(
        screen
          .getByRole('list', { name: 'Pinned and recent universes' })
          .getByRole('button', { name: 'Open Eldmark' })
      )
      .toBeInTheDocument()
    expect(FakeEventSource.latest().url).toBe('/api/library/events/stream')
  })

  it('says when the shelves cannot be read', async () => {
    const { screen } = await renderLibrary(
      libraryRoutes([], {
        'GET /api/library/universes': failure(500, 'The catalogue is locked.'),
      })
    )
    await expect
      .element(screen.getByText('The shelves could not be read'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('The catalogue is locked.').first())
      .toBeInTheDocument()
  })

  it('creates a universe and enters its birth', async () => {
    const created = universeSummary({
      id: SECOND_ID,
      name: 'Morrow',
      epoch: 0,
    })
    const { screen, server, router } = await renderLibrary(
      libraryRoutes([universeSummary()], {
        'POST /api/library/universes': created,
        'POST /api/library/universes/{id}/open': created,
      })
    )
    await screen
      .getByRole('button', { name: 'Create a universe' })
      .first()
      .click()
    await userEvent.fill(
      screen.getByLabelText('Name', { exact: true }),
      'Morrow'
    )
    await userEvent.fill(
      screen.getByLabelText('Tags', { exact: true }),
      'sea, sea, dusk'
    )
    await userEvent.fill(
      screen.getByLabelText('Summary', { exact: true }),
      'A tide that never turns'
    )
    await screen.getByRole('button', { name: 'Create and shape it' }).click()
    await expect.poll(() => router.state.location.pathname).toBe('/genesis')
    expect(server.callsTo('POST /api/library/universes')[0].body).toEqual({
      name: 'Morrow',
      notes: '',
      summary: 'A tide that never turns',
      tags: ['sea', 'dusk'],
    })
    expect(
      server.callsTo('POST /api/library/universes/{id}/open')
    ).toHaveLength(1)
    expect(sessionStorage.getItem('aerona.universe')).toBe(SECOND_ID)
  })

  it('refuses a nameless universe with a reason', async () => {
    const { screen, server } = await renderLibrary(
      libraryRoutes([universeSummary()])
    )
    await screen
      .getByRole('button', { name: 'Create a universe' })
      .first()
      .click()
    await screen.getByRole('button', { name: 'Create and shape it' }).click()
    await expect
      .element(screen.getByText('Give the universe a name.'))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/library/universes')).toHaveLength(0)
  })

  it('deletes a universe only after a dialog that names it', async () => {
    const { screen, server } = await renderLibrary(
      libraryRoutes([universeSummary()], {
        'DELETE /api/library/universes/{id}': null,
      })
    )
    await screen.getByRole('button', { name: 'Delete' }).click()
    await expect
      .element(screen.getByRole('alertdialog', { name: 'Delete Eldmark?' }))
      .toBeInTheDocument()
    expect(server.callsTo('DELETE /api/library/universes/{id}')).toHaveLength(0)
    await screen.getByRole('button', { name: 'Delete Eldmark' }).click()
    await expect
      .poll(() => server.callsTo('DELETE /api/library/universes/{id}').length)
      .toBe(1)
    expect(server.callsTo('DELETE /api/library/universes/{id}')[0].path).toBe(
      `/api/library/universes/${FIRST_ID}`
    )
  })

  it('blocks delete and archive while an epoch runs, and says why', async () => {
    const { screen } = await renderLibrary(
      libraryRoutes([universeSummary({ running_jobs: ['epoch'] })])
    )
    const remove = screen.getByRole('button', { name: 'Delete' })
    await expect.element(remove).toHaveAttribute('aria-disabled', 'true')
    await expect
      .element(remove)
      .toHaveAccessibleDescription(
        'An epoch is running in this universe. Wait for it to end first.'
      )
    await expect
      .element(screen.getByRole('button', { name: 'Archive' }))
      .toHaveAttribute('aria-disabled', 'true')
  })

  it('exports with progress and offers the file', async () => {
    let polls = 0
    const { screen } = await renderLibrary(
      libraryRoutes([universeSummary()], {
        'POST /api/library/universes/{id}/export': libraryJob({
          stage: 'snapshot',
          progress: 0,
        }),
        'GET /api/library/exports/{job}': () => {
          polls += 1
          return polls < 2
            ? libraryJob()
            : libraryJob({
                status: 'done',
                progress: 1,
                file_name: 'Eldmark.aerona',
                size_bytes: 4_200_000,
              })
        },
      })
    )
    await screen.getByRole('button', { name: 'Export as a file' }).click()
    await screen.getByRole('button', { name: 'Start the export' }).click()
    await expect
      .element(
        screen.getByRole('progressbar', { name: /Packing the universe/ })
      )
      .toBeInTheDocument()
    const download = screen.getByRole('link', { name: 'Download the file' })
    await expect
      .element(download)
      .toHaveAttribute('href', '/api/library/exports/job1/file')
    await expect
      .element(screen.getByText(/Eldmark\.aerona/))
      .toBeInTheDocument()
  })

  it('pins a universe and renames it in place', async () => {
    const { screen, server } = await renderLibrary(
      libraryRoutes([universeSummary()], {
        'PATCH /api/library/universes/{id}': universeSummary(),
      })
    )
    await screen.getByRole('button', { name: 'Pin Eldmark' }).click()
    await expect
      .poll(() => server.callsTo('PATCH /api/library/universes/{id}')[0]?.body)
      .toEqual({ pinned: true })
    await screen.getByRole('button', { name: 'Rename Eldmark' }).click()
    await userEvent.fill(
      screen.getByLabelText('New name for Eldmark'),
      'Eldmark Reborn'
    )
    await screen.getByRole('button', { name: 'Save the name' }).click()
    await expect
      .poll(() => server.callsTo('PATCH /api/library/universes/{id}')[1]?.body)
      .toEqual({ name: 'Eldmark Reborn' })
  })

  it('keeps an archived universe shut until it is restored', async () => {
    const { screen, server } = await renderLibrary(
      libraryRoutes([universeSummary({ status: 'archived' })], {
        'GET /api/library/universes': universePage([
          universeSummary({ status: 'archived' }),
        ]),
        'POST /api/library/universes/{id}/restore': universeSummary(),
      })
    )
    const open = screen.getByRole('button', { name: 'Open Eldmark' }).last()
    await expect.element(open).toHaveAttribute('aria-disabled', 'true')
    await screen.getByRole('button', { name: 'Restore to the shelf' }).click()
    await expect
      .poll(
        () => server.callsTo('POST /api/library/universes/{id}/restore').length
      )
      .toBe(1)
  })
})

describe('the universe switcher', () => {
  it('names the universe and switches to a recent one', async () => {
    chooseUniverse(FIRST_ID)
    const shelf = [
      universeSummary(),
      universeSummary({ id: SECOND_ID, name: 'Saltwyrd' }),
    ]
    const { screen, server, router } = await renderScreen(
      <UniverseSwitcher />,
      libraryRoutes(shelf, {
        'POST /api/library/universes/{id}/open': shelf[1],
      }),
      '/atlas',
      { realtime: false }
    )
    await expect
      .element(
        screen.getByRole('link', { name: 'Back to the Library of Universes' })
      )
      .toHaveAttribute('href', '/')
    const trigger = screen.getByRole('button', {
      name: 'Eldmark: switch universe',
    })
    await expect.element(trigger).toBeInTheDocument()
    await trigger.click()
    await screen.getByRole('menuitem', { name: /Saltwyrd/ }).click()
    await expect.poll(() => router.state.location.pathname).toBe('/overview')
    expect(
      server.callsTo('POST /api/library/universes/{id}/open')[0].path
    ).toBe(`/api/library/universes/${SECOND_ID}/open`)
    expect(sessionStorage.getItem('aerona.universe')).toBe(SECOND_ID)
  })
})

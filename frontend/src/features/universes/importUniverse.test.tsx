import { renderScreen } from '@/test-utils/renderScreen'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { userEvent } from 'vitest/browser'
import { libraryQueryClient } from '@/api/queryClients'
import { ImportUniverseDialog } from './ImportUniverseDialog'
import { uploadUniverse } from './api'
import { ManifestError, readPackageManifest } from './packageManifest'
import { type LibraryJob } from './types'
import { SECOND_ID, libraryJob } from './universeFixtures'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  uploadUniverse: vi.fn(),
}))

const BLOCK = 512
const SIZE_AT = 124
const TYPE_AT = 156

function member(name: string, data: Uint8Array): Uint8Array<ArrayBuffer> {
  const header = new Uint8Array(BLOCK)
  header.set(new TextEncoder().encode(name), 0)
  header.set(
    new TextEncoder().encode(`${data.length.toString(8).padStart(11, '0')}\0`),
    SIZE_AT
  )
  header[TYPE_AT] = '0'.charCodeAt(0)
  const body = new Uint8Array(Math.ceil(data.length / BLOCK) * BLOCK)
  body.set(data)
  const out = new Uint8Array(header.length + body.length)
  out.set(header)
  out.set(body, header.length)
  return out
}

async function aeronaFile(
  members: [string, unknown][],
  fileName = 'Eldmark.aerona'
): Promise<File> {
  const parts = members.map(([name, value]) =>
    member(
      name,
      value instanceof Uint8Array
        ? value
        : new TextEncoder().encode(JSON.stringify(value))
    )
  )
  const tar = new Blob([...parts, new Uint8Array(BLOCK * 2)])
  const zipped = await new Response(
    tar.stream().pipeThrough(new CompressionStream('gzip'))
  ).blob()
  return new File([zipped], fileName)
}

const PACKAGE = {
  format: 'aerona-world',
  version: 2,
  name: 'Eldmark',
  epoch: 6,
  creator: 'Asha',
  date: '2026-11-21T08:00:00Z',
  objects: [{ key: 'originals/abc.png', sha256: 'f'.repeat(64), size: 2048 }],
  library: {
    format: 'aerona-universe',
    version: 1,
    universe_id: 'zzzzzzzzzzzz',
    name: 'Eldmark',
    summary: 'A cosmos grown from its seed.',
    tags: ['favourite'],
    epoch: 6,
    year: 300,
    app_version: '0.1.0',
    schema_revision: 'w52',
    counts: { entities: 420, sons: 4 },
  },
}

beforeEach(() => {
  libraryQueryClient.clear()
  libraryQueryClient.setDefaultOptions({
    queries: { retry: false, gcTime: 0 },
  })
  vi.mocked(uploadUniverse).mockReset()
})

describe('reading a universe file before it is uploaded', () => {
  it('shows the manifest the package carries', async () => {
    const file = await aeronaFile([
      ['manifest.json', PACKAGE],
      ['world.db', new Uint8Array(4096)],
    ])
    const manifest = await readPackageManifest(file)
    expect(manifest.name).toBe('Eldmark')
    expect(manifest.epoch).toBe(6)
    expect(manifest.year).toBe(300)
    expect(manifest.counts).toEqual({ entities: 420, sons: 4 })
    expect(manifest.files).toEqual([
      { path: 'originals/abc.png', size: 2048, sha256: 'f'.repeat(64) },
    ])
    expect(manifest.exported_at).toBe('2026-11-21T08:00:00Z')
  })

  it('reads a library manifest kept as a member of its own', async () => {
    const { library, ...world } = PACKAGE
    const file = await aeronaFile([
      ['manifest.json', world],
      ['universe.json', { ...library, notes: 'Shared by a friend' }],
      ['world.db', new Uint8Array(1024)],
    ])
    const manifest = await readPackageManifest(file)
    expect(manifest.universe_id).toBe('zzzzzzzzzzzz')
    expect(manifest.notes).toBe('Shared by a friend')
    expect(manifest.format_version).toBe(1)
  })

  it('refuses a file that is not a universe', async () => {
    const file = new File([new Uint8Array([1, 2, 3, 4])], 'notes.aerona')
    await expect(readPackageManifest(file)).rejects.toBeInstanceOf(
      ManifestError
    )
  })
})

describe('the import dialog', () => {
  it('shows what the file holds, uploads and checks it, then brings it in under the chosen name', async () => {
    let finish: (job: LibraryJob) => void = () => undefined
    vi.mocked(uploadUniverse).mockImplementation(
      (_file, onProgress) =>
        new Promise((resolve) => {
          onProgress(0.5)
          finish = resolve
        })
    )
    let confirmed = false
    const checked = libraryJob({
      id: 'imp1',
      kind: 'import',
      stage: 'check',
      status: 'waiting',
      universe_id: null,
      universe_name: 'Eldmark',
      preview: {
        name: 'Eldmark',
        summary: 'A cosmos grown from its seed.',
        notes: '',
        tags: ['favourite'],
        source_id: 'zzzzzzzzzzzz',
        created_at: null,
        exported_at: '2026-11-21T08:00:00Z',
        app_version: '0.1.0',
        schema_revision: 'w52',
        epoch: 6,
        year: 300,
        population: 9100,
        sons: 4,
        files: 12,
        size_bytes: 80_000,
        legacy: false,
        dropped: 0,
      },
    })
    const { screen, server } = await renderScreen(
      <ImportUniverseDialog open onOpenChange={() => undefined} />,
      {
        'GET /api/library/imports/{job}': () =>
          confirmed
            ? libraryJob({
                id: 'imp1',
                kind: 'import',
                stage: 'register',
                status: 'done',
                progress: 1,
                universe_id: SECOND_ID,
                universe_name: 'Eldmark from a friend',
              })
            : checked,
        'POST /api/library/imports/{job}/confirm': () => {
          confirmed = true
          return { ...checked, status: 'running', stage: 'place' }
        },
      },
      '/',
      { realtime: false }
    )
    const file = await aeronaFile([
      ['manifest.json', PACKAGE],
      ['world.db', new Uint8Array(2048)],
    ])
    await userEvent.upload(
      screen.getByLabelText('Drop a .aerona file here'),
      file
    )
    const preview = screen.getByRole('region', { name: 'What the file holds' })
    await expect
      .element(preview.getByRole('heading', { name: 'Eldmark' }))
      .toBeInTheDocument()
    await expect
      .element(preview.getByText('Not checked yet'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('progressbar', { name: /Uploading the file/ }))
      .toBeInTheDocument()
    const bring = screen.getByRole('button', {
      name: 'Bring it into the library',
    })
    await expect.element(bring).toHaveAttribute('aria-disabled', 'true')
    finish(libraryJob({ id: 'imp1', kind: 'import', stage: 'check' }))
    await expect.element(preview.getByText('Checked')).toBeInTheDocument()
    await expect.element(preview.getByText('9,100')).toBeInTheDocument()
    const name = screen.getByLabelText('Name on your shelf')
    await expect.element(name).toHaveValue('Eldmark')
    await userEvent.fill(name, 'Eldmark from a friend')
    await bring.click()
    await expect
      .element(screen.getByText('Eldmark from a friend stands on the shelf'))
      .toBeInTheDocument()
    expect(
      server.callsTo('POST /api/library/imports/{job}/confirm')[0].body
    ).toEqual({ name: 'Eldmark from a friend' })
    await expect
      .element(screen.getByRole('button', { name: 'Open it' }))
      .toBeInTheDocument()
  })

  it('says why a file cannot be shown and keeps the import shut', async () => {
    const { screen } = await renderScreen(
      <ImportUniverseDialog open onOpenChange={() => undefined} />,
      {},
      '/',
      { realtime: false }
    )
    await userEvent.upload(
      screen.getByLabelText('Drop a .aerona file here'),
      new File([new Uint8Array([9, 9, 9])], 'broken.aerona')
    )
    await expect
      .element(screen.getByText('This file cannot be shown'))
      .toBeInTheDocument()
    await expect
      .element(
        screen.getByRole('button', { name: 'Bring it into the library' })
      )
      .toHaveAttribute('aria-disabled', 'true')
    expect(uploadUniverse).not.toHaveBeenCalled()
  })
})

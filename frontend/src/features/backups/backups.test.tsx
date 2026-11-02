import { failure, type MockRequest } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, describe, expect, it } from 'vitest'
import { userEvent } from 'vitest/browser'
import { isReadOnly, setReadOnly } from '@/api/readOnly'
import { BackupsPanel } from './BackupsPanel'
import { DiscoveryBanner } from './DiscoveryBanner'
import { ShareWorld } from './ShareWorld'
import { databaseUrl, exportUrl, packageUrl } from './api'

afterEach(() => setReadOnly(false))

const BACKUPS = [
  {
    file: 'epoch-3.db',
    size: 2048,
    modified: '2026-01-01T12:00:00Z',
    label: 'Before epoch 3',
  },
  {
    file: 'epoch-2.db',
    size: 1024,
    modified: '2026-01-01T11:00:00Z',
    label: '',
  },
]

const RULES = [
  {
    namespace: 'backup',
    key: 'recent_epoch_backups',
    value: 5,
    default: 5,
    minimum: 1,
    maximum: 50,
    group: 'backup',
    label: 'Recent',
    integer: true,
  },
  {
    namespace: 'backup',
    key: 'milestone_epoch_multiple',
    value: 10,
    default: 10,
    minimum: 1,
    maximum: 100,
    group: 'backup',
    label: 'Milestone',
    integer: true,
  },
]

describe('backups panel', () => {
  it('lists backups with size and both download links, and states the retention rules', async () => {
    const { screen } = await renderScreen(<BackupsPanel readOnly={false} />, {
      'GET /api/backups': BACKUPS,
      'GET /api/rules': RULES,
    })
    await expect.element(screen.getByText('Before epoch 3')).toBeInTheDocument()
    await expect
      .element(screen.getByText(/epoch-3\.db · 2 KB/))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('link', { name: 'Database' }).first())
      .toHaveAttribute('href', databaseUrl('epoch-3.db'))
    await expect
      .element(screen.getByRole('link', { name: 'Package' }).first())
      .toHaveAttribute('href', packageUrl('epoch-3.db'))
    await expect
      .element(
        screen.getByText(
          /the last 5 are kept, and every 10th epoch's copy is always kept/
        )
      )
      .toBeInTheDocument()
  })

  it('shows an empty state without backups', async () => {
    const { screen } = await renderScreen(<BackupsPanel readOnly={false} />, {
      'GET /api/backups': [],
      'GET /api/rules': RULES,
    })
    await expect.element(screen.getByText('No backups yet')).toBeInTheDocument()
  })

  it('takes a backup now and relists', async () => {
    const list = [...BACKUPS]
    const { screen, server } = await renderScreen(
      <BackupsPanel readOnly={false} />,
      {
        'GET /api/backups': () => list,
        'GET /api/rules': RULES,
        'POST /api/backups': () => {
          const taken = {
            file: 'manual.db',
            size: 10,
            modified: '2026-01-02T00:00:00Z',
            label: 'Manual',
          }
          list.unshift(taken)
          return taken
        },
      }
    )
    await screen.getByRole('button', { name: 'Take a backup now' }).click()
    await expect
      .element(screen.getByText('Backup taken: manual.db'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Manual', { exact: true }))
      .toBeInTheDocument()
    expect(server.callsTo('GET /api/backups').length).toBeGreaterThan(1)
  })

  it('restores only after typing RESTORE, one dialog at a time', async () => {
    const { screen, server } = await renderScreen(
      <BackupsPanel readOnly={false} />,
      {
        'GET /api/backups': BACKUPS,
        'GET /api/rules': RULES,
        'POST /api/backups/restore': (request: MockRequest) => ({
          restored: (request.body as { file: string }).file,
          safety_backup: 'safety-1.db',
        }),
      }
    )
    await screen.getByRole('button', { name: 'Restore' }).first().click()
    await expect
      .element(screen.getByRole('heading', { name: 'Restore this backup?' }))
      .toBeInTheDocument()
    const confirm = screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Restore' })
    await expect.element(confirm).toBeDisabled()
    await userEvent.type(
      screen.getByLabelText('Type RESTORE to confirm'),
      'restore'
    )
    await expect.element(confirm).toBeDisabled()
    await screen.getByLabelText('Type RESTORE to confirm').clear()
    await userEvent.type(
      screen.getByLabelText('Type RESTORE to confirm'),
      'RESTORE'
    )
    await confirm.click()
    await expect
      .element(
        screen.getByText(
          'The world returned to the backup. Safety copy: safety-1.db'
        )
      )
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/backups/restore')[0].body).toEqual({
      file: 'epoch-3.db',
      confirm: 'RESTORE',
    })
  })

  it('shows the server error when a restore fails', async () => {
    const { screen } = await renderScreen(<BackupsPanel readOnly={false} />, {
      'GET /api/backups': BACKUPS,
      'GET /api/rules': RULES,
      'POST /api/backups/restore': failure(400, 'The backup file is damaged.'),
    })
    await screen.getByRole('button', { name: 'Restore' }).first().click()
    await userEvent.type(
      screen.getByLabelText('Type RESTORE to confirm'),
      'RESTORE'
    )
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Restore' })
      .click()
    await expect
      .element(screen.getByText('The backup file is damaged.'))
      .toBeInTheDocument()
  })

  it('disables restoring and backing up in a guest world', async () => {
    const { screen } = await renderScreen(<BackupsPanel readOnly />, {
      'GET /api/backups': BACKUPS,
      'GET /api/rules': RULES,
    })
    await expect
      .element(screen.getByRole('button', { name: 'Take a backup now' }))
      .toHaveAttribute('aria-disabled', 'true')
    await expect
      .element(screen.getByRole('button', { name: 'Restore' }).first())
      .toHaveAttribute('aria-description', 'A guest world is read-only')
  })
})

describe('share the world', () => {
  const packageFile = () => new File(['archive'], 'sky.aerona')
  const pickPackage = () =>
    userEvent.upload(
      document.querySelector(
        '[data-domain="file-picker"] input[type="file"]'
      ) as HTMLInputElement,
      packageFile()
    )

  it('links the export with and without images', async () => {
    const { screen } = await renderScreen(
      <ShareWorld hasWorld readOnly={false} />
    )
    await expect
      .element(screen.getByRole('link', { name: /^With images/ }))
      .toHaveAttribute('href', exportUrl(true))
    await expect
      .element(screen.getByRole('link', { name: /^Without images/ }))
      .toHaveAttribute('href', exportUrl(false))
  })

  it('hides the export before a world exists', async () => {
    const { screen } = await renderScreen(
      <ShareWorld hasWorld={false} readOnly={false} />
    )
    await expect
      .element(screen.getByRole('link', { name: /^With images/ }))
      .not.toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: 'With images' }))
      .toHaveAttribute('aria-description', 'There is no world to export yet')
  })

  it('needs a file before it can open anything', async () => {
    const { screen } = await renderScreen(
      <ShareWorld hasWorld readOnly={false} />
    )
    await expect
      .element(screen.getByRole('button', { name: 'Open read-only' }))
      .toHaveAttribute('aria-description', 'Choose a .aerona file first')
  })

  it('opens a package read-only without any confirmation', async () => {
    const { screen, server } = await renderScreen(
      <ShareWorld hasWorld readOnly={false} />,
      {
        'POST /api/world/import': {
          mode: 'discovery',
          world: { name: 'Sky', epoch: 4, creator: 'Ana', date: 'x' },
          safety_backup: null,
        },
      }
    )
    await pickPackage()
    await expect.element(screen.getByText('sky.aerona')).toBeVisible()
    await screen.getByRole('button', { name: 'Open read-only' }).click()
    await expect
      .element(screen.getByText('Sky opened read-only'))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/world/import')[0].query.get('mode')).toBe(
      'discovery'
    )
    expect(
      server.callsTo('POST /api/world/import')[0].query.get('confirm')
    ).toBeNull()
  })

  it('opens a package dropped onto the picker', async () => {
    const { screen, server } = await renderScreen(
      <ShareWorld hasWorld readOnly={false} />,
      {
        'POST /api/world/import': {
          mode: 'discovery',
          world: { name: 'Sky', epoch: 4, creator: 'Ana', date: 'x' },
          safety_backup: null,
        },
      }
    )
    const zone = document.querySelector(
      '[data-domain="file-picker"]'
    ) as HTMLElement
    const transfer = new DataTransfer()
    transfer.items.add(packageFile())
    const over = new DragEvent('dragover', {
      bubbles: true,
      cancelable: true,
      dataTransfer: transfer,
    })
    zone.dispatchEvent(over)
    expect(over.defaultPrevented).toBe(true)
    zone.dispatchEvent(
      new DragEvent('drop', {
        bubbles: true,
        cancelable: true,
        dataTransfer: transfer,
      })
    )
    await expect.element(screen.getByText('sky.aerona')).toBeVisible()
    await screen.getByRole('button', { name: 'Open read-only' }).click()
    await expect
      .element(screen.getByText('Sky opened read-only'))
      .toBeInTheDocument()
    expect(server.callsTo('POST /api/world/import')).toHaveLength(1)
  })

  it('replaces the world only after typing REPLACE', async () => {
    const { screen, server } = await renderScreen(
      <ShareWorld hasWorld readOnly={false} />,
      {
        'POST /api/world/import': {
          mode: 'replace',
          world: { name: 'Sky', epoch: 4, creator: 'Ana', date: 'x' },
          safety_backup: 'safe.db',
        },
      }
    )
    await pickPackage()
    await expect.element(screen.getByText('sky.aerona')).toBeVisible()
    await screen.getByRole('radio', { name: /^Replace/ }).click()
    await expect
      .element(
        screen.getByText(
          /A safety backup of the current world is taken before it is replaced/
        )
      )
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Import and replace' }).click()
    const confirm = screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Replace my world' })
    await expect.element(confirm).toBeDisabled()
    await userEvent.type(
      screen.getByLabelText('Type REPLACE to confirm'),
      'REPLACE'
    )
    await confirm.click()
    await expect.element(screen.getByText('Sky imported')).toBeInTheDocument()
    expect(
      server.callsTo('POST /api/world/import')[0].query.get('confirm')
    ).toBe('REPLACE')
    expect(server.callsTo('POST /api/world/import')[0].query.get('mode')).toBe(
      'replace'
    )
  })

  it('blocks replacing and merging inside a guest world', async () => {
    const { screen } = await renderScreen(<ShareWorld hasWorld readOnly />)
    await pickPackage()
    await expect.element(screen.getByText('sky.aerona')).toBeVisible()
    await screen.getByRole('radio', { name: /^Merge/ }).click()
    await expect
      .element(screen.getByRole('button', { name: 'Merge into my world' }))
      .toHaveAttribute(
        'aria-description',
        'Return to your own world before changing it'
      )
  })
})

describe('discovery banner', () => {
  const guest = { name: 'Sky', epoch: 4, creator: 'Ana', date: null }

  it('stays hidden and leaves the world editable when not in discovery', async () => {
    const { screen } = await renderScreen(<DiscoveryBanner />, {
      'GET /api/discovery': { active: false, guest: null },
    })
    await expect.element(screen.getByRole('status')).not.toBeInTheDocument()
    expect(isReadOnly()).toBe(false)
  })

  it('announces the read-only guest world and turns on the read-only guard', async () => {
    const { screen } = await renderScreen(<DiscoveryBanner />, {
      'GET /api/discovery': { active: true, guest },
    })
    await expect
      .element(
        screen.getByText(
          'Discovery mode: Sky is open read-only (made by Ana, epoch 4). Your own world waits aside.'
        )
      )
      .toBeInTheDocument()
    expect(isReadOnly()).toBe(true)
  })

  it('refuses changes while in discovery and returns to the own world on request', async () => {
    let active = true
    const { screen, server } = await renderScreen(<DiscoveryBanner />, {
      'GET /api/discovery': () => ({ active, guest: active ? guest : null }),
      'POST /api/discovery/end': () => {
        active = false
        return {}
      },
    })
    await expect.element(screen.getByRole('status')).toBeInTheDocument()
    await screen.getByRole('button', { name: 'Return to my world' }).click()
    await expect
      .element(screen.getByText('You returned to your own world'))
      .toBeInTheDocument()
    await expect.element(screen.getByRole('status')).not.toBeInTheDocument()
    expect(server.callsTo('POST /api/discovery/end')).toHaveLength(1)
    expect(isReadOnly()).toBe(false)
  })
})

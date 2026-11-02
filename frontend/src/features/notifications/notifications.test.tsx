import { worldState } from '@/test-utils/fixtures'
import { type MockRequest } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { NotificationBell } from './NotificationBell'
import { NotificationSettings } from './NotificationSettings'
import { NotificationsScreen } from './NotificationsScreen'
import { SelfNoteForm } from './SelfNoteForm'

type Item = {
  id: number
  epoch: number | null
  category: string
  severity: number
  title: string
  body: string | null
  target_node_id: number | null
  chronicle_id: number | null
  is_read: boolean
  created_at: string
}

function item(
  id: number,
  category: string,
  isRead: boolean,
  title: string
): Item {
  return {
    id,
    epoch: 2,
    category,
    severity: 2,
    title,
    body: null,
    target_node_id: null,
    chronicle_id: null,
    is_read: isRead,
    created_at: '2026-01-01T12:00:00Z',
  }
}

const CATEGORIES = [
  { category: 'death', label: 'Deaths', severity: 3, enabled_by_default: true },
  {
    category: 'prayer',
    label: 'Prayers',
    severity: 2,
    enabled_by_default: true,
  },
  { category: 'note', label: 'Notes', severity: 1, enabled_by_default: false },
]

function notificationRoutes(initial: Item[], pageSize = 60) {
  const items = [...initial]
  const settings: Record<string, boolean> = {}
  const list = (request: MockRequest) => {
    const category = request.query.get('category')
    const unreadOnly = request.query.get('unread_only') === 'true'
    const before = request.query.get('before')
    const limit = Number(request.query.get('limit') ?? 60)
    let rows = [...items].sort((a, b) => b.id - a.id)
    if (category) rows = rows.filter((row) => row.category === category)
    if (unreadOnly) rows = rows.filter((row) => !row.is_read)
    if (before) rows = rows.filter((row) => row.id < Number(before))
    return {
      unread: items.filter((row) => !row.is_read).length,
      counts: CATEGORIES.map((info) => ({
        category: info.category,
        total: items.filter((row) => row.category === info.category).length,
        unread: items.filter(
          (row) => row.category === info.category && !row.is_read
        ).length,
      })),
      settings,
      categories: CATEGORIES,
      items: rows.slice(0, limit),
    }
  }
  return {
    items,
    settings,
    routes: {
      'GET /api/notifications': list,
      'GET /api/names': [],
      'GET /api/rules': [
        {
          namespace: 'server',
          key: 'notification_page_size',
          value: pageSize,
          default: 60,
          minimum: 1,
          maximum: 200,
          group: 'server',
          label: 'Page size',
          integer: true,
        },
        {
          namespace: 'notifications',
          key: 'toast_min_importance',
          value: 3,
          default: 3,
          minimum: 1,
          maximum: 4,
          group: 'notifications',
          label: 'Toast importance',
          integer: true,
        },
      ],
      'POST /api/notifications/read': (request: MockRequest) => {
        const body = request.body as {
          ids?: number[]
          every: boolean
          category?: string | null
          unread: boolean
        }
        let changed = 0
        for (const row of items) {
          const hit = body.every
            ? !body.category || row.category === body.category
            : (body.ids ?? []).includes(row.id)
          if (hit && row.is_read !== !body.unread) {
            row.is_read = !body.unread
            changed += 1
          }
        }
        return { changed }
      },
      'POST /api/notifications': (request: MockRequest) => {
        const body = request.body as { title: string; body: string | null }
        items.push({
          ...item(items.length + 1, 'note', false, body.title),
          body: body.body,
        })
        return { id: items.length }
      },
      'PUT /api/notifications/settings': (request: MockRequest) => {
        Object.assign(settings, request.body)
        return {}
      },
      'GET /api/state': worldState({ notifications_unread: 2 }),
    },
  }
}

describe('notifications screen', () => {
  it('summarises unread counts, category chips and importance of each item', async () => {
    const { routes } = notificationRoutes([
      item(1, 'death', false, 'Ithren has died'),
      item(2, 'prayer', true, 'A prayer was made'),
      item(3, 'prayer', false, 'Another prayer'),
    ])
    const { screen } = await renderScreen(<NotificationsScreen />, routes)
    await expect
      .element(screen.getByText('2 unread', { exact: true }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: /^Deaths\s*1 new · 1$/ }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: /^Prayers\s*1 new · 2$/ }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Ithren has died'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Epoch 2').first())
      .toBeInTheDocument()
  })

  it('filters by category and by only unread', async () => {
    const { routes } = notificationRoutes([
      item(1, 'death', false, 'Ithren has died'),
      item(2, 'prayer', true, 'A prayer was made'),
      item(3, 'prayer', false, 'Another prayer'),
    ])
    const { screen } = await renderScreen(<NotificationsScreen />, routes)
    await screen.getByRole('button', { name: /^Prayers/ }).click()
    await expect
      .element(screen.getByText('Ithren has died'))
      .not.toBeInTheDocument()
    await expect
      .element(screen.getByText('A prayer was made'))
      .toBeInTheDocument()
    await screen.getByRole('switch', { name: 'Only unread' }).click()
    await expect
      .element(screen.getByText('A prayer was made'))
      .not.toBeInTheDocument()
    await expect.element(screen.getByText('Another prayer')).toBeInTheDocument()
  })

  it('shows an empty state when nothing matches', async () => {
    const { routes } = notificationRoutes([
      item(1, 'death', true, 'Ithren has died'),
    ])
    const { screen } = await renderScreen(<NotificationsScreen />, routes)
    await screen.getByRole('switch', { name: 'Only unread' }).click()
    await expect
      .element(screen.getByText('Nothing unread here'))
      .toBeInTheDocument()
  })

  it('toggles one notification read and unread in place', async () => {
    const { routes, items } = notificationRoutes([
      item(1, 'death', false, 'Ithren has died'),
    ])
    const { screen, server } = await renderScreen(
      <NotificationsScreen />,
      routes
    )
    await screen.getByRole('button', { name: 'Mark read' }).click()
    await expect
      .element(screen.getByRole('button', { name: 'Mark unread' }))
      .toBeInTheDocument()
    expect(items[0].is_read).toBe(true)
    expect(server.callsTo('POST /api/notifications/read')[0].body).toEqual({
      ids: [1],
      every: false,
      unread: false,
    })
    await screen.getByRole('button', { name: 'Mark unread' }).click()
    await expect
      .element(screen.getByRole('button', { name: 'Mark read' }))
      .toBeInTheDocument()
    expect(items[0].is_read).toBe(false)
  })

  it('marks a whole category read and disables the button when nothing is unread', async () => {
    const { routes, items } = notificationRoutes([
      item(1, 'prayer', false, 'Prayer one'),
      item(2, 'prayer', false, 'Prayer two'),
      item(3, 'death', false, 'Death one'),
    ])
    const { screen, server } = await renderScreen(
      <NotificationsScreen />,
      routes
    )
    await screen.getByRole('button', { name: /^Prayers\s*2 new · 2$/ }).click()
    await screen.getByRole('button', { name: 'Mark these read' }).click()
    await expect.element(screen.getByText('2 marked read')).toBeInTheDocument()
    expect(
      server.callsTo('POST /api/notifications/read')[0].body
    ).toMatchObject({
      every: true,
      category: 'prayer',
    })
    expect(items.filter((row) => row.is_read).map((row) => row.id)).toEqual([
      1, 2,
    ])
    await expect
      .element(screen.getByRole('button', { name: 'Mark these read' }))
      .toHaveAttribute('aria-disabled', 'true')
  })

  it('appends older notifications by cursor', async () => {
    const { routes } = notificationRoutes(
      [1, 2, 3, 4, 5].map((id) =>
        item(id, 'prayer', true, `Prayer number ${id}`)
      ),
      2
    )
    const { screen, server } = await renderScreen(
      <NotificationsScreen />,
      routes
    )
    await expect
      .element(screen.getByText('That is everything.'))
      .toBeInTheDocument()
    for (const id of [5, 4, 3, 2, 1]) {
      await expect
        .element(screen.getByText(`Prayer number ${id}`))
        .toBeInTheDocument()
    }
    const feed = server
      .callsTo('GET /api/notifications')
      .filter((call) => call.query.get('limit') === '2')
    expect(feed.map((call) => call.query.get('before'))).toEqual([
      null,
      '4',
      '2',
    ])
  })
})

describe('self note form', () => {
  it('requires a title, files the note and clears the form', async () => {
    const { routes, items } = notificationRoutes([])
    const { screen, server } = await renderScreen(<SelfNoteForm />, routes)
    const add = screen.getByRole('button', { name: 'Add the note' })
    await expect.element(add).toHaveAttribute('aria-disabled', 'true')
    await screen.getByLabelText('Title').fill('Reconcile the sons')
    await screen.getByLabelText('Details').fill('Before the next epoch')
    await add.click()
    await expect.element(screen.getByText('Note added')).toBeInTheDocument()
    expect(server.callsTo('POST /api/notifications')[0].body).toEqual({
      title: 'Reconcile the sons',
      body: 'Before the next epoch',
    })
    expect(items[0].title).toBe('Reconcile the sons')
    await expect.element(screen.getByLabelText('Title')).toHaveValue('')
  })
})

describe('notification settings', () => {
  it('switches categories with their importance and saves only when changed', async () => {
    const { routes, settings } = notificationRoutes([
      item(1, 'death', true, 'Ithren has died'),
    ])
    const { screen, server } = await renderScreen(
      <NotificationsScreen />,
      routes
    )
    const save = screen.getByRole('button', { name: 'Save preferences' })
    await expect.element(save).toHaveAttribute('aria-disabled', 'true')
    await expect
      .element(screen.getByLabelText('Importance 3 of 4'))
      .toBeInTheDocument()
    await expect
      .element(
        screen.getByText(
          /Notifications of importance 3 and above also appear briefly/
        )
      )
      .toBeInTheDocument()
    await screen.getByRole('switch', { name: 'Notes' }).click()
    await save.click()
    await expect
      .element(screen.getByText('Notification preferences saved'))
      .toBeInTheDocument()
    expect(server.callsTo('PUT /api/notifications/settings')).toHaveLength(1)
    expect(settings.note).toBe(true)
  })
})

describe('notification settings in a narrow panel', () => {
  it('wraps long category names beside the switch instead of under it', async () => {
    const list = {
      unread: 0,
      counts: [],
      settings: {},
      items: [],
      categories: [
        {
          category: 'apocalypse',
          label: 'Omen of doomsday',
          severity: 4,
          enabled_by_default: true,
        },
        {
          category: 'rebellion',
          label: "Son's rebellion",
          severity: 3,
          enabled_by_default: true,
        },
      ],
    }
    const { screen } = await renderScreen(
      <div className='w-48'>
        <NotificationSettings list={list as never} />
      </div>
    )
    for (const name of ['Omen of doomsday', "Son's rebellion"]) {
      const toggle = screen.getByRole('switch', { name })
      await expect.element(toggle).toBeVisible()
      const label = screen.getByText(name, { exact: true }).element()
      const row = toggle.element().closest('li')
      expect(row).not.toBeNull()
      expect(label.getBoundingClientRect().right).toBeLessThanOrEqual(
        toggle.element().getBoundingClientRect().left
      )
      expect(row!.scrollWidth).toBeLessThanOrEqual(row!.clientWidth)
    }
  })
})

describe('notification bell', () => {
  it('shows the unread count capped at 99 plus', async () => {
    const { screen } = await renderScreen(<NotificationBell />, {
      'GET /api/state': worldState({ notifications_unread: 150 }),
    })
    await expect.element(screen.getByText('99+')).toBeInTheDocument()
    await expect
      .element(screen.getByRole('link', { name: '150 unread notifications' }))
      .toBeInTheDocument()
  })

  it('has no badge when everything is read', async () => {
    const { screen } = await renderScreen(<NotificationBell />, {
      'GET /api/state': worldState(),
    })
    await expect
      .element(screen.getByRole('link', { name: 'Notifications' }))
      .toBeInTheDocument()
  })

  it('toasts achievements always and others only when flagged', async () => {
    const { screen, emit } = await renderScreen(
      <NotificationBell />,
      { 'GET /api/state': worldState() },
      '/',
      { realtime: true }
    )
    const base = {
      id: 1,
      category: 'achievement',
      label: 'Achievement',
      severity: 4,
      body: 'Ten sons',
      toast: false,
    }
    emit('notification.created', { ...base, title: 'First ascension' })
    await expect
      .element(screen.getByText('First ascension'))
      .toBeInTheDocument()
    emit('notification.created', {
      ...base,
      category: 'death',
      title: 'Quiet death',
      toast: false,
    })
    emit('notification.created', {
      ...base,
      category: 'death',
      title: 'Loud death',
      toast: true,
    })
    await expect.element(screen.getByText('Loud death')).toBeInTheDocument()
    await expect
      .element(screen.getByText('Quiet death'))
      .not.toBeInTheDocument()
  })
})

import { type Middleware } from 'openapi-fetch'
import { afterEach, describe, expect, it } from 'vitest'
import { actNoteMiddleware, isLeverRoute, withQuery } from './conflicts'
import { noteRevision, watchEditing } from './editSession'

type OnRequest = NonNullable<Middleware['onRequest']>

function post(path: string, body: unknown): Request {
  return new Request(new URL(path, window.location.origin), {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  })
}

async function noted(request: Request): Promise<Request | undefined> {
  const onRequest = actNoteMiddleware.onRequest as OnRequest
  const result = await onRequest({ request } as Parameters<OnRequest>[0])
  return result instanceof Request ? result : undefined
}

let unwatch: (() => void) | null = null

function pinRevision(revision: number): void {
  unwatch = watchEditing()
  noteRevision(revision)
  const field = document.createElement('input')
  document.body.append(field)
  field.focus()
  field.remove()
}

afterEach(() => {
  unwatch?.()
  unwatch = null
})

describe('the act note on a write', () => {
  it('leaves a write that is no lever untouched while an edit is pinned', async () => {
    pinRevision(35256)
    const request = post('/api/divine-will/cycles', {
      text: 'what happened in the café',
    })
    expect(isLeverRoute('POST', '/api/divine-will/cycles')).toBe(false)
    expect(await noted(request)).toBeUndefined()
  })

  it('pins the revision on a lever and keeps its body', async () => {
    pinRevision(35256)
    expect(isLeverRoute('POST', '/api/facts')).toBe(true)
    const next = await noted(post('/api/facts', { text: 'déjà vu' }))
    expect(next).toBeDefined()
    expect(new URL(next!.url).searchParams.get('expected_revision')).toBe(
      '35256'
    )
    expect(await next!.text()).toBe(JSON.stringify({ text: 'déjà vu' }))
  })

  it('rebuilds a request the browser can send over plain HTTP', async () => {
    const url = new URL('/index.html', window.location.origin)
    url.searchParams.set('reason', 'x')
    const rebuilt = await withQuery(post('/index.html', { a: 1 }), url)
    const response = await fetch(rebuilt)
    expect(response.status).toBeGreaterThan(0)
  })
})

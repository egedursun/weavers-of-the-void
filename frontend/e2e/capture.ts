import { type Page, type Route } from '@playwright/test'

export type Write = { method: string; path: string; body: unknown }

function parsedBody(raw: string | null): unknown {
  if (raw === null) return null
  try {
    return JSON.parse(raw)
  } catch {
    return raw
  }
}

export async function captureWrites(page: Page): Promise<Write[]> {
  const writes: Write[] = []
  await page.route('**/api/**', async (route) => {
    const request = route.request()
    if (request.method() !== 'GET') {
      const body = parsedBody(request.postData())
      writes.push({ method: request.method(), path: new URL(request.url()).pathname, body })
    }
    await route.fallback()
  })
  return writes
}

export function writesTo(writes: Write[], method: string, pattern: RegExp): Write[] {
  return writes.filter((write) => write.method === method && pattern.test(write.path))
}

export async function replyWith(
  page: Page,
  method: string,
  pattern: RegExp,
  body: unknown,
  status = 200
): Promise<void> {
  await page.route(pattern, async (route: Route) => {
    if (route.request().method() !== method) return route.fallback()
    return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
  })
}

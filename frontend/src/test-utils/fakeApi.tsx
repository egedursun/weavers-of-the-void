import { type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRouter,
} from '@tanstack/react-router'
import '@/styles/index.css'
import createClient from 'openapi-fetch'
import { Toaster } from 'sonner'
import { render } from 'vitest-browser-react'
import { type paths } from '@/api/generated/schema'
import { TooltipProvider } from '@/components/ui/tooltip'
import { validateEntrySearch } from '@/components/layout/entry/entryStack'

const TEST_TOASTS = {
  classNames: {
    toast: 'pointer-events-none',
    actionButton: 'pointer-events-auto',
    cancelButton: 'pointer-events-auto',
    closeButton: 'pointer-events-auto',
  },
}

export type ApiCall = {
  method: string
  path: string
  search: URLSearchParams
  body: unknown
}

type Reply = { status: number; body: unknown }
type Responder = unknown | ((call: ApiCall) => unknown)

const STATUS_OK = 200
const STATUS_NOT_FOUND = 404

const responders = new Map<string, Responder>()

export const apiCalls: ApiCall[] = []

export function failure(status: number, detail: string): Reply {
  return { status, body: { detail } }
}

function isReply(value: unknown): value is Reply {
  return (
    typeof value === 'object' &&
    value !== null &&
    'status' in value &&
    'body' in value &&
    typeof (value as Reply).status === 'number'
  )
}

export function onApi(
  method: string,
  path: string,
  responder: Responder
): void {
  responders.set(`${method.toUpperCase()} ${path}`, responder)
}

export function resetApi(): void {
  responders.clear()
  apiCalls.length = 0
}

export function callsTo(method: string, path: string): ApiCall[] {
  return apiCalls.filter(
    (call) => call.method === method.toUpperCase() && call.path === path
  )
}

const NONE = Symbol('none')

function findResponder(call: ApiCall): unknown {
  for (const [key, responder] of responders) {
    const [method, pattern = ''] = key.split(' ')
    if (method !== call.method) continue
    const expression = new RegExp(`^${pattern.replace(/:\w+/g, '[^/]+')}$`)
    if (expression.test(call.path)) return responder
  }
  return NONE
}

async function fakeFetch(request: Request): Promise<Response> {
  const url = new URL(request.url, window.location.origin)
  const text = request.method === 'GET' ? '' : await request.text()
  const call: ApiCall = {
    method: request.method,
    path: url.pathname,
    search: url.searchParams,
    body: text ? JSON.parse(text) : null,
  }
  apiCalls.push(call)
  const responder = findResponder(call)
  if (responder === NONE) {
    return Response.json({ detail: 'Not found' }, { status: STATUS_NOT_FOUND })
  }
  const value = typeof responder === 'function' ? responder(call) : responder
  if (isReply(value)) return Response.json(value.body, { status: value.status })
  return Response.json(value ?? null, { status: STATUS_OK })
}

export function createFakeClient() {
  return createClient<paths>({ baseUrl: '', fetch: fakeFetch })
}

export const ACCEPTED_ACTION = {
  action: 'done',
  message: 'The deed is done.',
  essence_spent: 0,
  essence_gained: 0,
  target_node_id: null,
  created_ids: [],
  ledger_entry_id: null,
  values: {},
  job_id: null,
}

export function freshQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  })
}

export async function renderApp(node: ReactNode, path = '/') {
  const queryClient = freshQueryClient()
  const rootRoute = createRootRoute({
    validateSearch: validateEntrySearch,
    component: () => (
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          {node}
          <Toaster toastOptions={TEST_TOASTS} />
        </TooltipProvider>
      </QueryClientProvider>
    ),
  })
  const router = createRouter({
    routeTree: rootRoute,
    history: createMemoryHistory({ initialEntries: [path] }),
  })
  const screen = await render(<RouterProvider router={router} />)
  return { screen, router, queryClient }
}

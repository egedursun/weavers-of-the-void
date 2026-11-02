import createClient from 'openapi-fetch'
import { API_BASE_URL } from '@/constants/api'
import type { paths } from './generated/schema'
import { readOnlyGuard } from './readOnly'

export const api = createClient<paths>({
  baseUrl: API_BASE_URL,
  fetch: (request) => globalThis.fetch(request),
})

api.use(readOnlyGuard)

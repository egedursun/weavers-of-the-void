import createClient from 'openapi-fetch'
import { API_BASE_URL } from '@/constants/api'
import { authMiddleware } from './authMiddleware'
import { actNoteMiddleware } from './conflicts'
import type { paths } from './generated/schema'
import { holdGuard } from './holdGuard'
import { readOnlyGuard } from './readOnly'
import { universeMiddleware } from './universeMiddleware'

export const api = createClient<paths>({
  baseUrl: API_BASE_URL,
  fetch: (request) => globalThis.fetch(request),
})

api.use(authMiddleware)
api.use(universeMiddleware)
api.use(holdGuard)
api.use(actNoteMiddleware)
api.use(readOnlyGuard)

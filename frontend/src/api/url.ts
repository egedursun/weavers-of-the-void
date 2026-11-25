import { API_BASE_URL } from '@/constants/api'
import { type paths } from './generated/schema'
import { UNIVERSE_PARAM, currentUniverse } from './universeStore'

export type ApiPath = `/api/${string}`

export type QueryValue = string | number | boolean | null | undefined

const LIBRARY_API_PREFIX = '/api/library/'

export function isLibraryApi(pathname: string): boolean {
  return pathname.startsWith(LIBRARY_API_PREFIX)
}

export function apiUrl(
  path: ApiPath,
  params: Record<string, QueryValue> | URLSearchParams = {}
): string {
  const query = new URLSearchParams()
  const entries =
    params instanceof URLSearchParams
      ? [...params.entries()]
      : Object.entries(params)
  for (const [key, value] of entries)
    if (value !== null && value !== undefined) query.append(key, String(value))
  const universe = currentUniverse()
  if (universe !== null && !isLibraryApi(path) && !query.has(UNIVERSE_PARAM))
    query.set(UNIVERSE_PARAM, universe)
  const search = query.toString()
  return `${API_BASE_URL}${path}${search ? `?${search}` : ''}`
}

type PathKey = Extract<keyof paths, ApiPath>

export function typedPath<P extends PathKey>(
  path: P,
  values: Record<string, string | number>
): ApiPath {
  return path.replace(/\{([a-z_]+)\}/g, (hole, key: string) =>
    key in values ? encodeURIComponent(String(values[key])) : hole
  ) as ApiPath
}

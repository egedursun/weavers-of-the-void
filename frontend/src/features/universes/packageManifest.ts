import { type ManifestFile, type UniverseManifest } from './types'

const BLOCK = 512
const NAME_END = 100
const SIZE_START = 124
const SIZE_END = 136
const TYPE_AT = 156
const PREFIX_START = 345
const PREFIX_END = 500
const OCTAL = 8
const MANIFEST_MAX_BYTES = 8 * 1024 * 1024
const MEMBERS_READ = 6
const WORLD_FORMAT = 'aerona-world'
const LIBRARY_FORMATS = new Set(['aerona-library-package', 'aerona-universe'])
const FILE_TYPES = new Set([0, 48])

export class ManifestError extends Error {}

const NOT_A_PACKAGE = 'This file is not a universe exported from the Library.'
const NO_MANIFEST = 'The file holds no manifest, so it cannot be shown.'

type Member = { name: string; data: Uint8Array | null }

class ByteQueue {
  private chunks: Uint8Array[] = []
  private held = 0
  private done = false

  constructor(
    private readonly reader: ReadableStreamDefaultReader<Uint8Array>
  ) {}

  async take(count: number): Promise<Uint8Array | null> {
    while (this.held < count && !this.done) {
      const next = await this.reader.read()
      if (next.done) this.done = true
      else {
        this.chunks.push(next.value)
        this.held += next.value.length
      }
    }
    if (this.held < count) return null
    const out = new Uint8Array(count)
    let filled = 0
    while (filled < count) {
      const head = this.chunks[0]
      const used = Math.min(head.length, count - filled)
      out.set(head.subarray(0, used), filled)
      filled += used
      if (used === head.length) this.chunks.shift()
      else this.chunks[0] = head.subarray(used)
    }
    this.held -= count
    return out
  }

  async skip(count: number): Promise<boolean> {
    let left = count
    while (left > 0) {
      const part = await this.take(Math.min(left, BLOCK * OCTAL))
      if (part === null) return false
      left -= part.length
    }
    return true
  }

  close(): void {
    this.reader.cancel().catch(() => undefined)
  }
}

function text(bytes: Uint8Array): string {
  const end = bytes.indexOf(0)
  return new TextDecoder().decode(end >= 0 ? bytes.subarray(0, end) : bytes)
}

function memberName(header: Uint8Array): string {
  const name = text(header.subarray(0, NAME_END))
  const prefix = text(header.subarray(PREFIX_START, PREFIX_END))
  return prefix ? `${prefix}/${name}` : name
}

function memberSize(header: Uint8Array): number {
  const raw = text(header.subarray(SIZE_START, SIZE_END)).trim()
  const size = Number.parseInt(raw || '0', OCTAL)
  return Number.isFinite(size) ? size : 0
}

function padded(size: number): number {
  return Math.ceil(size / BLOCK) * BLOCK
}

async function readMembers(queue: ByteQueue): Promise<Member[]> {
  const members: Member[] = []
  while (members.length < MEMBERS_READ) {
    const header = await queue.take(BLOCK)
    if (header === null || header.every((byte) => byte === 0)) break
    const name = memberName(header)
    const size = memberSize(header)
    const wanted =
      FILE_TYPES.has(header[TYPE_AT]) &&
      name.endsWith('.json') &&
      size <= MANIFEST_MAX_BYTES
    if (wanted) {
      const body = await queue.take(padded(size))
      if (body === null) break
      members.push({ name, data: body.subarray(0, size) })
    } else {
      if (members.some((member) => member.data !== null)) break
      members.push({ name, data: null })
      if (!(await queue.skip(padded(size)))) break
    }
  }
  return members
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}

function stringOf(...values: unknown[]): string | null {
  for (const value of values)
    if (typeof value === 'string' && value.trim()) return value
  return null
}

function numberOf(...values: unknown[]): number | null {
  for (const value of values)
    if (typeof value === 'number' && Number.isFinite(value)) return value
  return null
}

function tagsOf(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : []
}

function countsOf(value: unknown): Record<string, number> {
  const counts: Record<string, number> = {}
  for (const [key, item] of Object.entries(record(value)))
    if (typeof item === 'number' && Number.isFinite(item)) counts[key] = item
  return counts
}

function filesOf(...values: unknown[]): ManifestFile[] {
  for (const value of values) {
    if (!Array.isArray(value)) continue
    return value.flatMap((item) => {
      const entry = record(item)
      const path = stringOf(entry['path'], entry['key'])
      const size = numberOf(entry['size'])
      return path !== null && size !== null
        ? [{ path, size, sha256: stringOf(entry['sha256']) ?? '' }]
        : []
    })
  }
  return []
}

export function manifestOf(documents: unknown[]): UniverseManifest {
  const parsed = documents.map(record)
  const world = parsed.find((item) => item['format'] === WORLD_FORMAT)
  const nested = world ? record(world['library']) : {}
  const library =
    parsed.find((item) => LIBRARY_FORMATS.has(String(item['format']))) ??
    (Object.keys(nested).length > 0 ? nested : undefined)
  if (!world && !library) throw new ManifestError(NOT_A_PACKAGE)
  const lib = library ?? {}
  const base = world ?? {}
  return {
    format_version: numberOf(lib['format_version'], lib['version']),
    app_version: stringOf(lib['app_version']),
    schema_revision: stringOf(lib['schema_revision']),
    universe_id: stringOf(lib['universe_id']),
    name: stringOf(lib['name'], base['name']) ?? '',
    summary: stringOf(lib['summary']),
    notes: stringOf(lib['notes']),
    tags: tagsOf(lib['tags']),
    created_at: stringOf(lib['created_at'], lib['created']),
    exported_at: stringOf(lib['exported_at'], lib['exported'], base['date']),
    epoch: numberOf(lib['epoch'], base['epoch']),
    year: numberOf(lib['year']),
    counts: countsOf(lib['counts']),
    files: filesOf(lib['files'], base['objects']),
  }
}

export async function readPackageManifest(
  file: Blob
): Promise<UniverseManifest> {
  let queue: ByteQueue
  try {
    queue = new ByteQueue(
      file.stream().pipeThrough(new DecompressionStream('gzip')).getReader()
    )
  } catch {
    throw new ManifestError(NOT_A_PACKAGE)
  }
  let members: Member[]
  try {
    members = await readMembers(queue)
  } catch {
    throw new ManifestError(NOT_A_PACKAGE)
  } finally {
    queue.close()
  }
  const documents = members.flatMap((member) => {
    if (member.data === null) return []
    try {
      return [JSON.parse(new TextDecoder().decode(member.data)) as unknown]
    } catch {
      return []
    }
  })
  if (members.length === 0) throw new ManifestError(NOT_A_PACKAGE)
  if (documents.length === 0) throw new ManifestError(NO_MANIFEST)
  return manifestOf(documents)
}

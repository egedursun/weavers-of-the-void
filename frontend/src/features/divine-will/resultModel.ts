export type ResultEnvelope = {
  total: number
  shown: number
  page: number
  next: boolean
}

export type ParsedResult = {
  envelope: ResultEnvelope | null
  lines: string[]
}

function envelopeOf(line: string): ResultEnvelope | null {
  if (!line.trimStart().startsWith('{')) return null
  try {
    const value: unknown = JSON.parse(line)
    if (typeof value !== 'object' || value === null) return null
    const { total, shown, page, next } = value as Record<string, unknown>
    return typeof total === 'number' &&
      typeof shown === 'number' &&
      typeof page === 'number' &&
      typeof next === 'boolean'
      ? { total, shown, page, next }
      : null
  } catch {
    return null
  }
}

export function parsedResult(text: string): ParsedResult {
  const all = text.split('\n')
  const envelope = all.length > 0 ? envelopeOf(all[0]) : null
  const body = envelope === null ? all : all.slice(1)
  const lines: string[] = []
  for (const line of body) {
    if (line.trim() === '' && lines.length > 0)
      lines[lines.length - 1] = `${lines[lines.length - 1]}\n`
    else if (line.trim() !== '') lines.push(line)
  }
  return { envelope, lines }
}

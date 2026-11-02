type JsonSchema = {
  type?: string
  title?: string
  description?: string
  enum?: unknown[]
  default?: unknown
  items?: JsonSchema
  anyOf?: JsonSchema[]
  $ref?: string
  properties?: Record<string, JsonSchema>
  required?: string[]
  $defs?: Record<string, JsonSchema>
  minimum?: number
  maximum?: number
}

export type FieldKind =
  | 'string'
  | 'integer'
  | 'number'
  | 'boolean'
  | 'enum'
  | 'integer-list'
  | 'enum-list'
  | 'string-list'
  | 'json'

export type FormField = {
  name: string
  label: string
  kind: FieldKind
  required: boolean
  options: string[]
  defaultValue: unknown
}

export type FieldValues = Record<string, string | boolean | string[]>

function resolve(
  schema: JsonSchema,
  defs: Record<string, JsonSchema>
): JsonSchema {
  if (schema.$ref) {
    const name = schema.$ref.split('/').at(-1) ?? ''
    return { ...(defs[name] ?? {}), ...schema, $ref: undefined }
  }
  return schema
}

function unwrapNullable(
  schema: JsonSchema,
  defs: Record<string, JsonSchema>
): JsonSchema {
  const resolved = resolve(schema, defs)
  if (!resolved.anyOf) return resolved
  const concrete = resolved.anyOf.filter((option) => option.type !== 'null')
  if (concrete.length !== 1) return { type: 'object' }
  return {
    ...resolve(concrete[0], defs),
    title: resolved.title,
    default: resolved.default,
  }
}

export function humanizeName(name: string): string {
  const words = name.replaceAll('_', ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}

function kindOf(
  schema: JsonSchema,
  defs: Record<string, JsonSchema>
): { kind: FieldKind; options: string[] } {
  if (schema.enum) return { kind: 'enum', options: schema.enum.map(String) }
  if (schema.type === 'array') {
    const item = unwrapNullable(schema.items ?? {}, defs)
    if (item.enum) return { kind: 'enum-list', options: item.enum.map(String) }
    if (item.type === 'integer') return { kind: 'integer-list', options: [] }
    if (item.type === 'string') return { kind: 'string-list', options: [] }
    return { kind: 'json', options: [] }
  }
  if (schema.type === 'integer') return { kind: 'integer', options: [] }
  if (schema.type === 'number') return { kind: 'number', options: [] }
  if (schema.type === 'boolean') return { kind: 'boolean', options: [] }
  if (schema.type === 'string') return { kind: 'string', options: [] }
  return { kind: 'json', options: [] }
}

export function fieldsOf(raw: Record<string, unknown>): FormField[] {
  const schema = raw as JsonSchema
  const defs = schema.$defs ?? {}
  const required = new Set(schema.required ?? [])
  return Object.entries(schema.properties ?? {}).map(([name, property]) => {
    const concrete = unwrapNullable(property, defs)
    const { kind, options } = kindOf(concrete, defs)
    return {
      name,
      label: property.title ?? concrete.title ?? humanizeName(name),
      kind,
      required: required.has(name),
      options,
      defaultValue: property.default ?? concrete.default,
    }
  })
}

export function initialValues(fields: FormField[]): FieldValues {
  const values: FieldValues = {}
  for (const field of fields) {
    if (field.kind === 'boolean')
      values[field.name] = field.defaultValue === true
    else if (field.kind === 'enum-list')
      values[field.name] = Array.isArray(field.defaultValue)
        ? field.defaultValue.map(String)
        : []
    else if (field.defaultValue === null || field.defaultValue === undefined)
      values[field.name] = ''
    else if (typeof field.defaultValue === 'object')
      values[field.name] = JSON.stringify(field.defaultValue)
    else values[field.name] = String(field.defaultValue)
  }
  return values
}

function splitList(text: string): string[] {
  return text
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
}

export function buildPayload(
  fields: FormField[],
  values: FieldValues
): { payload: Record<string, unknown> } | { error: string } {
  const payload: Record<string, unknown> = {}
  for (const field of fields) {
    const value = values[field.name]
    if (field.kind === 'boolean') {
      if (value !== (field.defaultValue === true))
        payload[field.name] = value === true
      continue
    }
    if (field.kind === 'enum-list') {
      const chosen = Array.isArray(value) ? value : []
      if (chosen.length > 0 || field.required) payload[field.name] = chosen
      continue
    }
    const text = typeof value === 'string' ? value.trim() : ''
    if (text === '') {
      if (field.required) return { error: `${field.label} is required.` }
      continue
    }
    if (field.kind === 'integer' || field.kind === 'number') {
      const number = Number(text)
      if (
        !Number.isFinite(number) ||
        (field.kind === 'integer' && !Number.isInteger(number))
      )
        return {
          error: `${field.label} must be ${field.kind === 'integer' ? 'a whole number' : 'a number'}.`,
        }
      payload[field.name] = number
    } else if (field.kind === 'integer-list') {
      const numbers = splitList(text).map(Number)
      if (numbers.some((number) => !Number.isInteger(number)))
        return {
          error: `${field.label} must be whole numbers separated by commas.`,
        }
      payload[field.name] = numbers
    } else if (field.kind === 'string-list') {
      payload[field.name] = splitList(text)
    } else if (field.kind === 'json') {
      try {
        payload[field.name] = JSON.parse(text)
      } catch {
        return { error: `${field.label} must be valid JSON.` }
      }
    } else {
      payload[field.name] = text
    }
  }
  return { payload }
}

export function routeFor(
  path: string,
  payload: Record<string, unknown>
): { url: string; body: Record<string, unknown> } | { error: string } {
  const body = { ...payload }
  let missing: string | null = null
  const url = path.replace(/\{([^}]+)\}/g, (_, name: string) => {
    const value = body[name]
    delete body[name]
    if (value === undefined || value === null || value === '') {
      missing = humanizeName(name)
      return ''
    }
    return encodeURIComponent(String(value))
  })
  if (missing) return { error: `${missing} is required.` }
  return { url, body }
}

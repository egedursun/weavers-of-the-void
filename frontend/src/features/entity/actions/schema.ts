export type FieldValue = string | number | boolean | null | FieldMap

export type FieldMap = { [key: string]: number }

export type FieldModel =
  | {
      key: string
      kind: 'enum'
      required: boolean
      options: string[]
      fallback: string | null
    }
  | { key: string; kind: 'boolean'; required: boolean; fallback: boolean }
  | {
      key: string
      kind: 'integer' | 'number'
      required: boolean
      fallback: number | null
      min?: number
      max?: number
    }
  | {
      key: string
      kind: 'string'
      required: boolean
      fallback: string
      maxLength?: number
    }
  | { key: string; kind: 'map'; required: boolean; keys: string[] }
  | { key: string; kind: 'unsupported'; required: boolean }

type JsonSchema = {
  type?: string
  $ref?: string
  anyOf?: JsonSchema[]
  enum?: string[]
  default?: unknown
  minimum?: number
  maximum?: number
  maxLength?: number
  propertyNames?: JsonSchema
  properties?: Record<string, JsonSchema>
  required?: string[]
  $defs?: Record<string, JsonSchema>
}

const REF_PREFIX = '#/$defs/'

function resolve(node: JsonSchema, defs: Record<string, JsonSchema>) {
  if (node.$ref?.startsWith(REF_PREFIX))
    return defs[node.$ref.slice(REF_PREFIX.length)] ?? node
  return node
}

function concrete(
  node: JsonSchema,
  defs: Record<string, JsonSchema>
): JsonSchema {
  if (node.anyOf) {
    const option = node.anyOf.find((item) => item.type !== 'null')
    if (option) return resolve(option, defs)
  }
  return resolve(node, defs)
}

function fieldOf(
  key: string,
  raw: JsonSchema,
  required: boolean,
  defs: Record<string, JsonSchema>
): FieldModel {
  const node = concrete(raw, defs)
  const fallback = raw.default ?? node.default
  if (node.enum)
    return {
      key,
      kind: 'enum',
      required,
      options: node.enum,
      fallback: typeof fallback === 'string' ? fallback : null,
    }
  if (node.type === 'boolean')
    return { key, kind: 'boolean', required, fallback: fallback === true }
  if (node.type === 'integer' || node.type === 'number')
    return {
      key,
      kind: node.type,
      required,
      fallback: typeof fallback === 'number' ? fallback : null,
      min: node.minimum,
      max: node.maximum,
    }
  if (node.type === 'string')
    return {
      key,
      kind: 'string',
      required,
      fallback: typeof fallback === 'string' ? fallback : '',
      maxLength: node.maxLength,
    }
  if (node.type === 'object' && node.propertyNames) {
    const names = concrete(node.propertyNames, defs)
    if (names.enum) return { key, kind: 'map', required, keys: names.enum }
  }
  return { key, kind: 'unsupported', required }
}

export function fieldsOf(schema: Record<string, unknown>): FieldModel[] {
  const root = schema as JsonSchema
  const defs = root.$defs ?? {}
  const required = new Set(root.required ?? [])
  return Object.entries(root.properties ?? {}).map(([key, node]) =>
    fieldOf(key, node, required.has(key), defs)
  )
}

export function initialValue(field: FieldModel): FieldValue {
  switch (field.kind) {
    case 'enum':
      return (
        field.fallback ?? (field.required ? (field.options[0] ?? null) : null)
      )
    case 'boolean':
      return field.fallback
    case 'integer':
    case 'number':
      return field.fallback
    case 'string':
      return field.fallback
    case 'map':
      return {}
    default:
      return null
  }
}

export function humanize(key: string): string {
  const words = key
    .replace(/_id$/, '')
    .replace(/_pct$/, ' percent')
    .split('_')
    .filter(Boolean)
    .join(' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}

export function missingRequired(
  fields: FieldModel[],
  values: Record<string, FieldValue>,
  skip: ReadonlySet<string>
): FieldModel | null {
  for (const field of fields) {
    if (!field.required || skip.has(field.key)) continue
    const value = values[field.key]
    if (value === null || value === undefined || value === '') return field
    if (field.kind === 'map' && Object.keys(value as FieldMap).length === 0)
      return field
  }
  return null
}

export function bodyOf(
  fields: FieldModel[],
  values: Record<string, FieldValue>,
  skip: ReadonlySet<string>
): Record<string, FieldValue> {
  const body: Record<string, FieldValue> = {}
  for (const field of fields) {
    if (skip.has(field.key) || field.kind === 'unsupported') continue
    const value = values[field.key]
    if (value === undefined) continue
    if (value === null || value === '') {
      if (field.required) body[field.key] = value
      continue
    }
    if (field.kind === 'map' && Object.keys(value as FieldMap).length === 0)
      continue
    body[field.key] = value
  }
  return body
}

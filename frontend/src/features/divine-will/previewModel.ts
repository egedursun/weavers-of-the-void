import { numberField, objectField, textField } from './traceModel'

type Payload = Record<string, unknown>

export type PreviewChange = {
  table: string
  operation: string
  nodeId: number | null
  nodeName: string
  field: string
  before: string
  after: string
}

export type PreviewTally = { operation: string; table: string; count: number }

export type Preview = {
  title: string
  cost: string
  message: string
  essence: number
  gained: number
  job: boolean
  deletedNodes: { nodeId: number | null; name: string; kind: string }[]
  deletedRecords: PreviewChange[]
  ended: PreviewChange[]
  tallies: PreviewTally[]
  changes: PreviewChange[]
  values: Payload
}

function rows(payload: Payload, field: string): Payload[] {
  const value = payload[field]
  return Array.isArray(value)
    ? value.filter(
        (item): item is Payload =>
          Boolean(item) && typeof item === 'object' && !Array.isArray(item)
      )
    : []
}

function changeOf(row: Payload): PreviewChange {
  return {
    table: textField(row, 'table'),
    operation: textField(row, 'operation'),
    nodeId: numberField(row, 'node_id'),
    nodeName: textField(row, 'node_name'),
    field: textField(row, 'field'),
    before: textField(row, 'before'),
    after: textField(row, 'after'),
  }
}

export function parsePreview(preview: Payload): Preview {
  return {
    title: textField(preview, 'title'),
    cost: textField(preview, 'cost'),
    message: textField(preview, 'message'),
    essence: numberField(preview, 'essence') ?? 0,
    gained: numberField(preview, 'essence_gained') ?? 0,
    job: preview['job'] === true,
    deletedNodes: rows(preview, 'deleted_nodes').map((row) => ({
      nodeId: numberField(row, 'node_id'),
      name: textField(row, 'name'),
      kind: textField(row, 'kind'),
    })),
    deletedRecords: rows(preview, 'deleted_records').map(changeOf),
    ended: rows(preview, 'ended').map(changeOf),
    tallies: rows(preview, 'tallies').map((row) => ({
      operation: textField(row, 'operation'),
      table: textField(row, 'table'),
      count: numberField(row, 'count') ?? 0,
    })),
    changes: rows(preview, 'changes').map(changeOf),
    values: objectField(preview, 'values'),
  }
}

export function tableWords(table: string): string {
  return table.replaceAll('_', ' ')
}

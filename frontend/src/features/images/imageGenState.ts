import { useMemo } from 'react'
import { type ServerEvent, useEvent } from '@/realtime'
import { create } from 'zustand'
import { useRoleModel } from '@/features/providers/api'
import { useImageGenStatus } from './api'

export type ImageLine = {
  key: string
  nodeId: number | null
  tone: 'info' | 'progress' | 'done' | 'failed' | 'bulk'
  text: string
  file?: string
  percent?: number
  at: string
}

type Progress = { stage: string; percent: number }

type ImageGenStore = {
  since: number
  progress: Record<number, Progress>
  lines: ImageLine[]
  record: (event: ServerEvent) => void
}

export const IMAGE_LINES_KEPT = 40
const PERCENT = 100

const STAGE_TEXT: Record<string, string> = {
  prepare: 'Preparing',
  prompt: 'Writing the prompt',
  loading: 'Loading the model',
  encoding: 'Reading the prompt',
  steps: 'Painting',
  decoding: 'Finishing',
  done: 'Done',
}

export function stageText(stage: string | null | undefined): string {
  if (!stage) return 'Working'
  return STAGE_TEXT[stage] ?? stage
}

function isLive(event: ServerEvent, since: number): boolean {
  const at = Date.parse(event.at)
  return Number.isNaN(at) || at >= since
}

function withLine(lines: ImageLine[], line: ImageLine): ImageLine[] {
  const rest = lines.filter((item) => item.key !== line.key)
  return [line, ...rest].slice(0, IMAGE_LINES_KEPT)
}

export const useImageGenStore = create<ImageGenStore>((set, get) => ({
  since: Date.now(),
  progress: {},
  lines: [],
  record: (event) => {
    if (!isLive(event, get().since)) return
    set((current) => {
      switch (event.kind) {
        case 'image.queued': {
          const { node_id, position } = event.payload
          return {
            lines: withLine(current.lines, {
              key: `node-${node_id}`,
              nodeId: node_id,
              tone: 'info',
              text: position > 0 ? `Queued, ${position} ahead` : 'Queued',
              at: event.at,
            }),
          }
        }
        case 'image.progress': {
          const { node_id, stage, percent } = event.payload
          return {
            progress: { ...current.progress, [node_id]: { stage, percent } },
            lines: withLine(current.lines, {
              key: `node-${node_id}`,
              nodeId: node_id,
              tone: 'progress',
              text: `${stageText(stage)} · ${Math.round(percent)}%`,
              percent,
              at: event.at,
            }),
          }
        }
        case 'image.done': {
          const { node_id, file } = event.payload
          const progress = { ...current.progress }
          delete progress[node_id]
          return {
            progress,
            lines: withLine(current.lines, {
              key: `node-${node_id}`,
              nodeId: node_id,
              tone: 'done',
              text: 'Image finished',
              file,
              at: event.at,
            }),
          }
        }
        case 'image.failed': {
          const { node_id, error } = event.payload
          const progress = { ...current.progress }
          delete progress[node_id]
          return {
            progress,
            lines: withLine(current.lines, {
              key: `node-${node_id}`,
              nodeId: node_id,
              tone: 'failed',
              text: error,
              at: event.at,
            }),
          }
        }
        case 'image.bulk_log': {
          const text = event.payload.text ?? event.payload.line ?? ''
          if (!text) return {}
          return {
            lines: withLine(current.lines, {
              key: `bulk-${event.id}`,
              nodeId: null,
              tone: 'bulk',
              text,
              at: event.at,
            }),
          }
        }
        default:
          return {}
      }
    })
  },
}))

export function useImageGenEvents(): void {
  const record = useImageGenStore((store) => store.record)
  useEvent('image.queued', record)
  useEvent('image.progress', record)
  useEvent('image.done', record)
  useEvent('image.failed', record)
  useEvent('image.bulk_log', record)
}

export type NodeImageState =
  | { phase: 'disabled'; reason: string }
  | { phase: 'idle' }
  | { phase: 'queued'; ahead: number }
  | { phase: 'running'; stage: string; percent: number }

export const WORKER_OFF_REASON =
  'Image generation is off: no image model is set. Add one under Team and workspace, Models.'

export function useNodeImageState(nodeId: number): NodeImageState {
  const status = useImageGenStatus()
  const imageModel = useRoleModel('images')
  const live = useImageGenStore((store) => store.progress[nodeId])
  return useMemo((): NodeImageState => {
    if (imageModel === '')
      return { phase: 'disabled', reason: WORKER_OFF_REASON }
    const queue = status.data?.status
    if (queue && !queue.available)
      return {
        phase: 'disabled',
        reason: queue.reason ?? 'The image model is not available right now.',
      }
    if (queue?.current?.node_id === nodeId)
      return {
        phase: 'running',
        stage: live?.stage ?? 'prepare',
        percent: live?.percent ?? 0,
      }
    const index =
      queue?.queue.findIndex((item) => item.node_id === nodeId) ?? -1
    if (index >= 0)
      return { phase: 'queued', ahead: index + (queue?.current ? 1 : 0) }
    if (live)
      return { phase: 'running', stage: live.stage, percent: live.percent }
    return { phase: 'idle' }
  }, [imageModel, status.data, live, nodeId])
}

export function percentOf(state: NodeImageState): number {
  return state.phase === 'running' ? Math.min(PERCENT, state.percent) : 0
}

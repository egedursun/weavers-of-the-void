import {
  Bot,
  Braces,
  CircleCheck,
  CircleDashed,
  CircleX,
  type LucideIcon,
} from 'lucide-react'
import { type KpiTone } from '@/components/domain'
import {
  type LlmCallKind,
  type LlmCallStatus,
  type UsageBucket,
  type UsageSort,
} from './api'

export type Look = { label: string; icon: LucideIcon; tone: KpiTone }

export const KIND_LOOK: Record<LlmCallKind, Look> = {
  agent: { label: 'Agent run', icon: Bot, tone: 'info' },
  structured: { label: 'Structured', icon: Braces, tone: 'verdigris' },
}

export const STATUS_LOOK: Record<LlmCallStatus, Look> = {
  ok: { label: 'Completed', icon: CircleCheck, tone: 'success' },
  partial: { label: 'Cut short', icon: CircleDashed, tone: 'warning' },
  error: { label: 'Failed', icon: CircleX, tone: 'danger' },
}

export const STATUS_BADGE: Record<
  LlmCallStatus,
  'success' | 'warning' | 'destructive'
> = {
  ok: 'success',
  partial: 'warning',
  error: 'destructive',
}

export const SORT_LABEL: Record<UsageSort, string> = {
  time: 'Time',
  total_tokens: 'Total tokens',
  input_tokens: 'Tokens in',
  output_tokens: 'Tokens out',
  duration: 'Duration',
  epoch: 'Epoch',
  model: 'Model',
  step: 'Step',
}

export const BUCKET_LABEL: Record<UsageBucket, string> = {
  epoch: 'By epoch',
  hour: 'By hour',
  day: 'By day',
}

export const RANGES = [
  { key: 'all', label: 'All time', hours: null },
  { key: 'day', label: 'Last 24 hours', hours: 24 },
  { key: 'week', label: 'Last 7 days', hours: 24 * 7 },
  { key: 'month', label: 'Last 30 days', hours: 24 * 30 },
] as const

export type RangeKey = (typeof RANGES)[number]['key']

export const INPUT_COLOR = 'var(--chart-3)'
export const OUTPUT_COLOR = 'var(--chart-2)'
export const SERIES_COLORS = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
  'var(--chart-5)',
] as const

export function seriesColor(position: number): string {
  return SERIES_COLORS[position % SERIES_COLORS.length]
}

export function totalOf(item: {
  input_tokens: number
  output_tokens: number
}): number {
  return item.input_tokens + item.output_tokens
}

export function shareOf(part: number, whole: number): number {
  return whole > 0 ? part / whole : 0
}

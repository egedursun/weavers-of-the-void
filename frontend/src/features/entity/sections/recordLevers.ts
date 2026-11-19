import type { LucideIcon } from 'lucide-react'
import type { ActionName } from '@/api/actions'
import type { KpiTone } from '@/components/domain/KpiTile'

export type RowStep = {
  action: ActionName
  label: string
  field: string
  icon: LucideIcon
  ready: (values: Record<string, unknown>) => string | null
}

export type RowLevers = {
  create: ActionName
  edit: ActionName
  remove: ActionName
  step?: RowStep
}

export const RECORD_LEVERS: RowLevers = {
  create: 'record_row:create',
  edit: 'record_row:edit',
  remove: 'record_row:delete',
}

export type RecordFamily = {
  id: string
  section: string
  title: string
  description: string
  icon: LucideIcon
  tone: KpiTone
  empty: string
  tables: Record<string, RowLevers>
}

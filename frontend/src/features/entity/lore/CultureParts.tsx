import { Lock, Shapes } from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { ChoicePicker } from './LoreFields'
import { NONE, withNone } from './cultureLabels'
import { useCustomKinds } from './forge/kindApi'
import { type LoreNamed, busyOf, useLoreEdit } from './model'

type Catalog = components['schemas']['CustomCatalog']
export function OptionalChoice({
  entityId,
  field,
  label,
  value,
  table,
  blocked,
  noneLabel,
}: {
  entityId: number
  field: string
  label: string
  value: string | null | undefined
  table: Record<string, LoreNamed>
  blocked: string | null
  noneLabel?: string
}) {
  const edit = useLoreEdit(entityId)
  return (
    <ChoicePicker
      act={edit}
      label={label}
      value={value ?? NONE}
      table={withNone(table, noneLabel)}
      blocked={busyOf(blocked, edit.isPending)}
      onPick={(next) =>
        edit.mutate({ values: { [field]: next === NONE ? null : next } })
      }
    />
  )
}

export function CustomKindChoice({
  entityId,
  field,
  catalog,
  value,
  blocked,
}: {
  entityId: number
  field: string
  catalog: Catalog
  value: number | null | undefined
  blocked: string | null
}) {
  const kinds = useCustomKinds(catalog)
  const edit = useLoreEdit(entityId)
  const table: Record<string, LoreNamed> = Object.fromEntries(
    (kinds.data?.kinds ?? []).map((kind) => [
      String(kind.id),
      { label: kind.name, icon: Shapes, tone: 'gold' as const },
    ])
  )
  return (
    <ChoicePicker
      act={edit}
      label='A kind of your own'
      value={value ? String(value) : NONE}
      table={withNone(table, 'Only the base kind')}
      blocked={busyOf(blocked, edit.isPending)}
      onPick={(next) =>
        edit.mutate({
          values: { [field]: next === NONE ? null : Number(next) },
        })
      }
    />
  )
}

export function HeldBadge({ held }: { held: boolean | null | undefined }) {
  if (!held) return null
  return (
    <Badge size='sm' variant='default'>
      <Lock aria-hidden='true' />
      Held
    </Badge>
  )
}

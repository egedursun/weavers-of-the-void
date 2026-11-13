import { type ReactNode, useState } from 'react'
import { type LucideIcon, Save } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Medallion } from '@/components/domain'
import { type KpiTone } from '@/components/domain/KpiTile'
import { Label, Muted, PageTitle } from '@/components/typography'
import { AdjustPanel } from '@/features/entity/wilds/parts'

export function KindHeader({
  icon,
  tone,
  overline,
  title,
  caption,
  chips,
}: {
  icon: LucideIcon
  tone: KpiTone | undefined
  overline: string
  title: string
  caption: string
  chips?: ReactNode
}) {
  return (
    <div className='flex min-w-0 items-start gap-3'>
      <Medallion icon={icon} tone={tone ?? 'muted'} />
      <div className='flex min-w-0 flex-1 flex-col gap-1'>
        <Label variant='overline'>{overline}</Label>
        <PageTitle truncate={2}>{title}</PageTitle>
        <Muted variant='caption'>{caption}</Muted>
        {chips && <div className='flex min-w-0 flex-wrap gap-1.5'>{chips}</div>}
      </div>
    </div>
  )
}

export type ListField = { key: string; label: string; note: string }

export function ListEditor({
  field,
  options,
  value,
  held,
  blocked,
  onSet,
}: {
  field: ListField
  options: Record<string, string>
  value: readonly string[]
  held: boolean
  blocked: string | null
  onSet: (next: string[]) => void
}) {
  const [draft, setDraft] = useState<string[] | null>(null)
  const chosen = draft ?? [...value]
  const same =
    draft === null ||
    (draft.length === value.length &&
      draft.every((item) => value.includes(item)))
  const toggle = (key: string) =>
    setDraft(
      chosen.includes(key)
        ? chosen.filter((item) => item !== key)
        : [...chosen, key]
    )
  return (
    <AdjustPanel title={field.label} note={field.note}>
      <div
        role='group'
        aria-label={field.label}
        className='flex min-w-0 flex-wrap gap-1.5'
      >
        {Object.entries(options).map(([key, label]) => (
          <Button
            key={key}
            size='sm'
            variant={chosen.includes(key) ? 'default' : 'outline'}
            aria-pressed={chosen.includes(key)}
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={() => toggle(key)}
          >
            {label}
          </Button>
        ))}
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        {held && (
          <Badge size='sm' variant='secondary'>
            Held
          </Badge>
        )}
        <Button
          size='sm'
          disabled={blocked !== null || same}
          disabledReason={
            blocked ?? (same ? 'Change the choice first' : undefined)
          }
          onClick={() => {
            onSet(chosen)
            setDraft(null)
          }}
        >
          <Save />
          Hold this choice
        </Button>
      </div>
    </AdjustPanel>
  )
}

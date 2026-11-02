import { X } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { ENTITY_TYPE_ICON } from '@/components/domain/domainIcons'
import { type EntityTypeInfo } from '@/features/entity/api/types'

const CHIPS_SHOWN = 8

type TypeChipsProps = {
  types: EntityTypeInfo[]
  counts: Map<string, number>
  active: string | null
  onPick: (type: string | null) => void
}

export function TypeChips({ types, counts, active, onPick }: TypeChipsProps) {
  const ranked = types
    .filter((type) => (counts.get(type.key) ?? 0) > 0)
    .sort(
      (first, second) =>
        (counts.get(second.key) ?? 0) - (counts.get(first.key) ?? 0)
    )
    .slice(0, CHIPS_SHOWN)
  if (ranked.length === 0) return null
  return (
    <div
      role='group'
      aria-label='Quick kinds'
      className='flex min-w-0 flex-wrap gap-1.5'
    >
      {ranked.map((type) => {
        const Icon = ENTITY_TYPE_ICON[type.key as keyof typeof ENTITY_TYPE_ICON]
        const on = active === type.key
        return (
          <Button
            key={type.key}
            variant={on ? 'default' : 'outline'}
            size='sm'
            aria-pressed={on}
            onClick={() => onPick(on ? null : type.key)}
          >
            {Icon && <Icon />}
            {`${type.plural} · ${formatInteger(counts.get(type.key) ?? 0)}`}
          </Button>
        )
      })}
      {active && (
        <Button variant='ghost' size='sm' onClick={() => onPick(null)}>
          <X />
          Every kind
        </Button>
      )}
    </div>
  )
}

import { SelectItem } from '@/components/ui/select'
import { type StarRecord } from './api'

type StarOptionsProps = {
  stars: readonly StarRecord[]
  selected: string | undefined
  open: boolean
  valueOf: (star: StarRecord) => string
  label: (star: StarRecord) => string
  disabled?: (star: StarRecord) => boolean
}

export function StarOptions({
  stars,
  selected,
  open,
  valueOf,
  label,
  disabled,
}: StarOptionsProps) {
  const shown = open
    ? stars
    : stars.filter((star) => valueOf(star) === selected)
  return shown.map((star) => (
    <SelectItem
      key={valueOf(star)}
      value={valueOf(star)}
      disabled={disabled?.(star)}
    >
      {label(star)}
    </SelectItem>
  ))
}

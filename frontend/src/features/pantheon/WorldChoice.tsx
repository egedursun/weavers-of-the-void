import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useWorldState } from './api'
import { FATE_CHOOSES } from './fateChoice'

export function WorldChoice({
  value,
  onChange,
  label,
  size = 'default',
}: {
  value: string
  onChange: (value: string) => void
  label: string
  size?: 'sm' | 'default'
}) {
  const state = useWorldState()
  const worlds = state.data?.worlds ?? []
  if (worlds.length < 2) return null
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger aria-label={label} size={size} className='w-48'>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={FATE_CHOOSES}>Let Fate choose</SelectItem>
        {worlds.map((world) => (
          <SelectItem key={world.id} value={String(world.id)}>
            {world.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

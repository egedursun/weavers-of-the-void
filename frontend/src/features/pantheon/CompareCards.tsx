import { Check, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useCompareSelection } from './compareStore'

export function CompareToggle({
  sonId,
  name,
}: {
  sonId: number
  name: string
}) {
  const { selected, toggle, full } = useCompareSelection()
  const on = selected.includes(sonId)
  return (
    <Button
      size='sm'
      variant={on ? 'secondary' : 'ghost'}
      aria-pressed={on}
      aria-label={on ? `Remove ${name} from comparison` : `Compare ${name}`}
      disabled={!on && full}
      disabledReason='At most three sons can be compared.'
      onClick={() => toggle(sonId)}
    >
      {on ? <Check /> : <Plus />}
      Compare
    </Button>
  )
}

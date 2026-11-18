import { Check } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

export function ChosenMark() {
  return (
    <Badge
      data-domain='chosen-mark'
      variant='solid'
      size='sm'
      className='absolute -top-2.5 right-3 z-10 shrink-0 animate-in shadow-md shadow-primary/40 zoom-in-90 fade-in'
    >
      <Check aria-hidden='true' />
      Chosen
    </Badge>
  )
}

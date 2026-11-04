import { type ReactNode, useState } from 'react'
import { type LucideIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'

export function Opener({
  icon: Icon,
  label,
  children,
}: {
  icon: LucideIcon
  label: string
  children: (close: () => void) => ReactNode
}) {
  const [open, setOpen] = useState(false)
  return (
    <Collapsible
      open={open}
      onOpenChange={setOpen}
      className='flex min-w-0 flex-col gap-3'
    >
      <CollapsibleTrigger asChild>
        <Button size='sm' variant={open ? 'outline' : 'default'}>
          <Icon />
          {label}
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='flex min-w-0 flex-col'>
        {children(() => setOpen(false))}
      </CollapsibleContent>
    </Collapsible>
  )
}

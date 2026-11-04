import { type ReactNode, useState } from 'react'
import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
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
      className={cn(
        'flex min-w-0 flex-col items-start gap-3',
        open && 'basis-full'
      )}
    >
      <CollapsibleTrigger asChild>
        <Button size='sm' variant={open ? 'outline' : 'default'}>
          <Icon />
          {label}
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='flex w-full min-w-0 flex-col'>
        {children(() => setOpen(false))}
      </CollapsibleContent>
    </Collapsible>
  )
}

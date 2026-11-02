import { useState } from 'react'
import { Activity } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { LiveFeedHeader } from './LiveFeedHeader'
import { LiveFeedPanel } from './LiveFeedPanel'
import { useFeed } from './feedStore'
import { useFeedDock } from './useFeedDock'

const BADGE_CAP = 99

function useUnseen(open: boolean): number {
  const total = useFeed((state) => state.lines.length)
  const [seen, setSeen] = useState(total)
  if ((open && seen !== total) || total < seen) setSeen(total)
  return open ? 0 : Math.max(0, total - seen)
}

export function LiveFeedSheet() {
  const { docked, open, setOpen } = useFeedDock()
  const unseen = useUnseen(open)
  const label = unseen > 0 ? `Live feed, ${unseen} new events` : 'Live feed'
  return (
    <>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant='ghost'
            size={unseen > 0 ? 'sm' : 'icon'}
            aria-label={label}
            aria-pressed={open}
            data-live-feed-toggle
            onClick={() => setOpen(!open)}
            className={open ? 'bg-accent text-primary' : undefined}
          >
            <Activity />
            {unseen > 0 && (
              <Badge size='sm' variant='default'>
                {unseen > BADGE_CAP ? `${BADGE_CAP}+` : unseen}
              </Badge>
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent>{open ? 'Hide the live feed' : label}</TooltipContent>
      </Tooltip>
      <Sheet open={open && !docked} onOpenChange={setOpen}>
        <SheetContent
          side='right'
          showCloseButton={false}
          className='flex w-full flex-col gap-0 bg-sidebar sm:max-w-xl'
        >
          <div className='flex min-w-0 flex-col gap-2 border-b bg-linear-to-b from-primary/8 to-transparent p-4'>
            <LiveFeedHeader
              title={<SheetTitle>Live feed</SheetTitle>}
              onClose={() => setOpen(false)}
            />
            <SheetDescription>
              The thoughts of the sons, the turns of the mortals, the world
              engine and Fate, as they happen.
            </SheetDescription>
          </div>
          <div className='flex min-h-0 flex-1 flex-col p-4'>
            <LiveFeedPanel layout='fill' />
          </div>
        </SheetContent>
      </Sheet>
    </>
  )
}

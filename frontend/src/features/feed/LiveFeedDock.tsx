import { LiveFeedHeader } from './LiveFeedHeader'
import { LiveFeedPanel } from './LiveFeedPanel'
import { useFeedDock } from './useFeedDock'

export function LiveFeedDock() {
  const { docked, open, setOpen } = useFeedDock()
  if (!docked || !open) return null
  return (
    <aside
      data-layout='feed-dock'
      aria-label='Live feed dock'
      className='sticky top-0 flex h-svh w-144 shrink-0 flex-col border-l bg-sidebar'
    >
      <div className='border-b bg-linear-to-b from-primary/8 to-transparent p-4'>
        <LiveFeedHeader onClose={() => setOpen(false)} />
      </div>
      <div className='flex min-h-0 min-w-0 flex-1 flex-col p-4'>
        <LiveFeedPanel layout='fill' />
      </div>
    </aside>
  )
}

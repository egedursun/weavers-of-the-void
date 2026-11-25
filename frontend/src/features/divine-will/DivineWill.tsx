import { useEffect } from 'react'
import {
  History,
  LibraryBig,
  type LucideIcon,
  MessagesSquare,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Kbd } from '@/components/ui/kbd'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { DivineCrest } from '@/components/layout/divine-will/DivineCrest'
import { DivineWillDock } from '@/components/layout/divine-will/DivineWillDock'
import {
  WILL_VIEWS,
  type WillView,
  useWillDock,
} from '@/components/layout/divine-will/dockStore'
import { Label, Text } from '@/components/typography'
import { FEED_DOCK_REM, useFeedDock } from '@/features/feed/useFeedDock'
import { ShareToggle } from '@/features/team/share'
import { MemoryMeter, ResetSessionButton } from './SessionTools'
import { ChatView, PastSessionsView, WritingsView } from './WillViews'
import { useWillSignals } from './useWillSignals'
import { useWillStream } from './useWillStream'
import { useWill } from './willStore'

const VIEW_LOOK: Record<WillView, { label: string; icon: LucideIcon }> = {
  chat: { label: 'Exchanges', icon: MessagesSquare },
  writings: { label: 'Writings', icon: LibraryBig },
  sessions: { label: 'Past sessions', icon: History },
}

function isView(value: string): value is WillView {
  return (WILL_VIEWS as readonly string[]).includes(value)
}

function DivineWillPanel() {
  const signals = useWillSignals()
  const view = useWillDock((state) => state.view)
  const setView = useWillDock((state) => state.setView)
  const setOpen = useWillDock((state) => state.setOpen)
  return (
    <div className='@container/will flex min-h-0 min-w-0 flex-1 flex-col'>
      <div className='flex min-w-0 flex-col gap-3 border-b bg-linear-to-b from-primary/8 to-transparent px-4 pt-4 pb-3'>
        <div className='flex min-w-0 items-center gap-3'>
          <DivineCrest size='md' tone={signals.awaiting ? 'warning' : 'gold'} />
          <div className='flex min-w-0 flex-1 flex-col'>
            <Label variant='overline'>The Creator’s own hand</Label>
            <Text
              weight='semibold'
              truncate
              className='text-gilded font-display'
            >
              The Divine Will
            </Text>
          </div>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant='ghost'
                size='icon-sm'
                aria-label='Close the Divine Will'
                onClick={() => setOpen(false)}
              >
                <X />
              </Button>
            </TooltipTrigger>
            <TooltipContent className='flex items-center gap-2'>
              Close
              <Kbd>Esc</Kbd>
            </TooltipContent>
          </Tooltip>
        </div>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          {signals.ready && (
            <div className='flex min-w-0 flex-1 basis-60'>
              <MemoryMeter
                remembered={signals.remembered}
                limit={signals.limit}
              />
            </div>
          )}
          {signals.session && (
            <ShareToggle
              kind='session'
              id={signals.session.id}
              shared={signals.session.shared}
              mine={signals.session.mine}
              author={signals.session.author?.name}
            />
          )}
          <ResetSessionButton
            busy={signals.running || signals.awaiting}
            empty={signals.total === 0}
          />
        </div>
      </div>
      <Tabs
        value={view}
        onValueChange={(value) => {
          if (isView(value)) setView(value)
        }}
        className='flex min-h-0 min-w-0 flex-1 flex-col gap-0'
      >
        <div className='px-4 pt-3'>
          <TabsList aria-label='What the Divine Will shows' className='w-full'>
            {WILL_VIEWS.map((item) => {
              const look = VIEW_LOOK[item]
              const Icon = look.icon
              return (
                <TabsTrigger key={item} value={item}>
                  <Icon />
                  {look.label}
                </TabsTrigger>
              )
            })}
          </TabsList>
        </div>
        <TabsContent
          value='chat'
          className='flex min-h-0 min-w-0 flex-1 flex-col'
        >
          <ChatView />
        </TabsContent>
        <TabsContent
          value='writings'
          className='flex min-h-0 min-w-0 flex-1 flex-col'
        >
          <WritingsView />
        </TabsContent>
        <TabsContent
          value='sessions'
          className='flex min-h-0 min-w-0 flex-1 flex-col'
        >
          <PastSessionsView />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export function DivineWill() {
  useWillStream()
  const signals = useWillSignals()
  const open = useWillDock((state) => state.open)
  const unread = useWill((state) => state.unread)
  const clearUnread = useWill((state) => state.clearUnread)
  const feed = useFeedDock()
  useEffect(() => {
    if (open && unread > 0) clearUnread()
  }, [open, unread, clearUnread])
  return (
    <DivineWillDock
      running={signals.running}
      attention={signals.awaiting}
      unread={unread}
      neighbourRem={feed.docked && feed.open ? FEED_DOCK_REM : 0}
    >
      <DivineWillPanel />
    </DivineWillDock>
  )
}

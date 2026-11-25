import {
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
} from 'react'
import { DIVINE_WILL_SHORTCUT } from '@/config/navigation'
import { cn } from '@/lib/utils'
import { useIsMobile } from '@/hooks/useIsMobile'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Kbd } from '@/components/ui/kbd'
import { GEM_CLASS } from '@/components/ui/ornate'
import { useSidebar } from '@/components/ui/sidebar'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { isTypingTarget } from '../useGlobalShortcuts'
import { DivineCrest } from './DivineCrest'
import {
  PANEL_MAX_REM,
  PANEL_MIN_REM,
  PANEL_STEP_REM,
  clampWidth,
  useWillDock,
} from './dockStore'

const PAGE_ROOM_REM = 64
const SIDEBAR_OPEN_REM = 16
const SIDEBAR_ICON_REM = 3
const COUNT_CAP = 9
const EDGE_REM = 1

export type DockSignal = {
  running: boolean
  attention: boolean
  unread: number
}

type DivineWillDockProps = DockSignal & {
  neighbourRem: number
  children: ReactNode
}

function remSize(): number {
  return parseFloat(getComputedStyle(document.documentElement).fontSize) || 16
}

function subscribeResize(callback: () => void): () => void {
  window.addEventListener('resize', callback)
  return () => window.removeEventListener('resize', callback)
}

function useViewportRem(): number {
  return useSyncExternalStore(
    subscribeResize,
    () => window.innerWidth / remSize(),
    () => 0
  )
}

function overlayOpen(): boolean {
  return (
    document.querySelector(
      '[role="dialog"],[role="alertdialog"],[role="menu"],[role="listbox"]'
    ) !== null
  )
}

function orbLabel({ running, attention, unread }: DockSignal): string {
  const parts = ['Open the Divine Will']
  if (attention) parts.push('it waits for your approval')
  if (running) parts.push('it is at work')
  if (unread > 0)
    parts.push(
      unread === 1 ? 'one new answer' : `${String(unread)} new answers`
    )
  return parts.join(', ')
}

function WillOrb({
  signal,
  neighbourRem,
  onOpen,
  orbRef,
}: {
  signal: DockSignal
  neighbourRem: number
  onOpen: () => void
  orbRef: React.RefObject<HTMLButtonElement | null>
}) {
  const tone = signal.attention ? 'warning' : 'gold'
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          ref={orbRef}
          variant='ghost'
          aria-label={orbLabel(signal)}
          data-divine-will-orb
          data-running={signal.running ? true : undefined}
          data-attention={signal.attention ? true : undefined}
          onClick={onOpen}
          className={cn(
            'will-orb fixed z-40 p-0 hover:bg-transparent',
            GEM_CLASS[tone]
          )}
          style={{
            right: `${neighbourRem + EDGE_REM}rem`,
            bottom: `calc(${EDGE_REM}rem + env(safe-area-inset-bottom))`,
          }}
        >
          <span aria-hidden='true' className='will-orb-glow' />
          <DivineCrest />
          {signal.unread > 0 && (
            <Badge
              size='sm'
              variant='solid'
              aria-hidden='true'
              className='will-orb-count'
            >
              {signal.unread > COUNT_CAP ? `${COUNT_CAP}+` : signal.unread}
            </Badge>
          )}
        </Button>
      </TooltipTrigger>
      <TooltipContent side='left' className='flex items-center gap-2'>
        The Divine Will
        <Kbd>{DIVINE_WILL_SHORTCUT.keys}</Kbd>
      </TooltipContent>
    </Tooltip>
  )
}

function ResizeHandle({
  width,
  onResize,
  onResizing,
}: {
  width: number
  onResize: (width: number) => void
  onResizing: (resizing: boolean) => void
}) {
  const start = useRef<{ x: number; width: number } | null>(null)
  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.currentTarget.setPointerCapture(event.pointerId)
    start.current = { x: event.clientX, width }
    onResizing(true)
  }
  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!start.current) return
    const moved = (start.current.x - event.clientX) / remSize()
    onResize(start.current.width + moved)
  }
  const onPointerUp = (event: PointerEvent<HTMLDivElement>) => {
    if (!start.current) return
    event.currentTarget.releasePointerCapture(event.pointerId)
    start.current = null
    onResizing(false)
  }
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const next =
      event.key === 'ArrowLeft'
        ? width + PANEL_STEP_REM
        : event.key === 'ArrowRight'
          ? width - PANEL_STEP_REM
          : event.key === 'Home'
            ? PANEL_MIN_REM
            : event.key === 'End'
              ? PANEL_MAX_REM
              : null
    if (next === null) return
    event.preventDefault()
    onResize(next)
  }
  return (
    <div
      role='separator'
      aria-orientation='vertical'
      aria-label='Resize the Divine Will'
      aria-valuemin={PANEL_MIN_REM}
      aria-valuemax={PANEL_MAX_REM}
      aria-valuenow={Math.round(width)}
      aria-valuetext={`${String(Math.round(width))} rem wide`}
      tabIndex={0}
      className='will-resize-handle'
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onKeyDown={onKeyDown}
    />
  )
}

export function DivineWillDock({
  running,
  attention,
  unread,
  neighbourRem,
  children,
}: DivineWillDockProps) {
  const open = useWillDock((state) => state.open)
  const setOpen = useWillDock((state) => state.setOpen)
  const width = useWillDock((state) => state.width)
  const setWidth = useWillDock((state) => state.setWidth)
  const phone = useIsMobile()
  const viewport = useViewportRem()
  const sidebar = useSidebar()
  const [resizing, setResizing] = useState(false)
  const orbRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLElement>(null)
  const wasOpen = useRef(open)
  const sidebarRem = sidebar.isMobile
    ? 0
    : sidebar.state === 'expanded'
      ? SIDEBAR_OPEN_REM
      : SIDEBAR_ICON_REM
  const shown = clampWidth(width)
  const pushes =
    !phone && viewport - sidebarRem - neighbourRem - PAGE_ROOM_REM >= shown

  useEffect(() => {
    if (wasOpen.current && !open) orbRef.current?.focus()
    wasOpen.current = open
  }, [open])

  const onKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key !== 'Escape' || event.defaultPrevented || overlayOpen())
      return
    if (
      isTypingTarget(event.target) &&
      (event.target as HTMLTextAreaElement).value
    )
      return
    event.preventDefault()
    setOpen(false)
  }

  if (!open)
    return (
      <WillOrb
        signal={{ running, attention, unread }}
        neighbourRem={phone ? 0 : neighbourRem}
        onOpen={() => setOpen(true)}
        orbRef={orbRef}
      />
    )

  return (
    <aside
      ref={panelRef}
      role='complementary'
      aria-label='The Divine Will'
      tabIndex={-1}
      data-layout='divine-will'
      data-placement={phone ? 'sheet' : pushes ? 'docked' : 'overlay'}
      data-resizing={resizing ? true : undefined}
      onKeyDown={onKeyDown}
      className={cn(
        'will-panel will-panel-enter flex min-w-0 flex-col bg-sidebar text-sidebar-foreground outline-none',
        phone
          ? 'fixed inset-0 z-40'
          : pushes
            ? 'sticky top-0 h-svh shrink-0 border-l'
            : 'fixed inset-y-0 z-40 border-l shadow-2xl'
      )}
      style={
        phone
          ? {
              paddingTop: 'env(safe-area-inset-top)',
              paddingBottom: 'env(safe-area-inset-bottom)',
            }
          : {
              width: `${shown}rem`,
              maxWidth: `calc(100vw - ${neighbourRem + EDGE_REM}rem)`,
              right: pushes ? undefined : `${neighbourRem}rem`,
            }
      }
    >
      {!phone && (
        <ResizeHandle
          width={shown}
          onResize={setWidth}
          onResizing={setResizing}
        />
      )}
      {children}
    </aside>
  )
}

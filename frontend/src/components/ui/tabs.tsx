import * as React from 'react'
import * as TabsPrimitive from '@radix-ui/react-tabs'
import { cn } from '@/lib/utils'
import {
  type ControlSize,
  controlHeight,
  controlIcon,
  controlText,
} from './control-size'

const TabsSizeContext = React.createContext<ControlSize>('default')

function Tabs({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Root>) {
  return (
    <TabsPrimitive.Root
      data-slot='tabs'
      className={cn('flex min-w-0 flex-col gap-4', className)}
      {...props}
    />
  )
}

function TabsList({
  className,
  size = 'default',
  ...props
}: React.ComponentProps<typeof TabsPrimitive.List> & { size?: ControlSize }) {
  return (
    <TabsSizeContext value={size}>
      <TabsPrimitive.List
        data-slot='tabs-list'
        data-control-size={size}
        className={cn(
          'no-scrollbar inline-flex w-fit max-w-full items-center justify-start gap-0.5 overflow-x-auto rounded-lg bg-muted p-0.5 text-muted-foreground',
          controlHeight[size],
          controlText,
          className
        )}
        {...props}
      />
    </TabsSizeContext>
  )
}

function TabsTrigger({
  className,
  ref: forwardedRef,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Trigger>) {
  const size = React.useContext(TabsSizeContext)
  const ref = React.useRef<HTMLButtonElement>(null)
  React.useEffect(() => {
    const trigger = ref.current
    const list = trigger?.parentElement
    if (!trigger || !list || trigger.dataset.state !== 'active') return
    const start = trigger.offsetLeft - list.offsetLeft
    const end = start + trigger.offsetWidth
    if (start < list.scrollLeft || end > list.scrollLeft + list.clientWidth)
      list.scrollLeft = start - (list.clientWidth - trigger.offsetWidth) / 2
  })
  return (
    <TabsPrimitive.Trigger
      ref={(node) => {
        ref.current = node
        if (typeof forwardedRef === 'function') forwardedRef(node)
        else if (forwardedRef) forwardedRef.current = node
      }}
      data-slot='tabs-trigger'
      className={cn(
        'inline-flex h-full flex-1 shrink-0 basis-auto items-center justify-center gap-1.5 rounded-md border border-transparent px-3 font-medium whitespace-nowrap text-muted-foreground transition-[color,background-color,box-shadow] outline-none',
        'hover:text-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50',
        'data-[state=active]:border-border data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-xs',
        '[&_svg]:pointer-events-none [&_svg]:shrink-0',
        controlIcon[size],
        className
      )}
      {...props}
    />
  )
}

function TabsContent({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Content>) {
  return (
    <TabsPrimitive.Content
      data-slot='tabs-content'
      className={cn('min-w-0 flex-1 outline-none', className)}
      {...props}
    />
  )
}

export { Tabs, TabsList, TabsTrigger, TabsContent }

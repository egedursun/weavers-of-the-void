import * as React from 'react'
import * as SelectPrimitive from '@radix-ui/react-select'
import { CheckIcon, ChevronDownIcon, ChevronUpIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  type ControlSize,
  controlFieldPadding,
  controlHeight,
  controlIcon,
  controlText,
} from './control-size'
import { fieldSurface } from './input'

type SelectState = { open: boolean; value: string | undefined }

const SelectStateContext = React.createContext<SelectState>({
  open: true,
  value: undefined,
})

function Select({
  open,
  defaultOpen,
  onOpenChange,
  value,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Root>) {
  const [ownOpen, setOwnOpen] = React.useState(defaultOpen ?? false)
  const isOpen = open ?? ownOpen
  const state = React.useMemo(() => ({ open: isOpen, value }), [isOpen, value])
  return (
    <SelectStateContext.Provider value={state}>
      <SelectPrimitive.Root
        data-slot='select'
        open={isOpen}
        onOpenChange={(next) => {
          if (open === undefined) setOwnOpen(next)
          onOpenChange?.(next)
        }}
        value={value}
        {...props}
      />
    </SelectStateContext.Provider>
  )
}

function SelectGroup({
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Group>) {
  return <SelectPrimitive.Group data-slot='select-group' {...props} />
}

function SelectValue({
  placeholder = 'Choose…',
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Value>) {
  return (
    <SelectPrimitive.Value
      data-slot='select-value'
      placeholder={placeholder}
      {...props}
    />
  )
}

function SelectTrigger({
  className,
  size = 'default',
  children,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Trigger> & {
  size?: ControlSize
}) {
  return (
    <SelectPrimitive.Trigger
      data-slot='select-trigger'
      data-control-size={size}
      className={cn(
        'flex w-fit max-w-full min-w-0 items-center justify-between gap-2 py-0 font-normal whitespace-nowrap',
        fieldSurface,
        controlHeight[size],
        controlFieldPadding[size],
        controlIcon[size],
        controlText,
        'hover:bg-field-hover data-placeholder:text-muted-foreground',
        '*:data-[slot=select-value]:line-clamp-1 *:data-[slot=select-value]:flex *:data-[slot=select-value]:min-w-0 *:data-[slot=select-value]:items-center *:data-[slot=select-value]:gap-2',
        '[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg]:text-muted-foreground',
        className
      )}
      {...props}
    >
      {children}
      <SelectPrimitive.Icon asChild>
        <ChevronDownIcon />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  )
}

function SelectContent({
  className,
  children,
  position = 'popper',
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Content>) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        data-slot='select-content'
        className={cn(
          'relative z-50 max-h-(--radix-select-content-available-height) max-w-(--radix-select-content-available-width) min-w-32 origin-(--radix-select-content-transform-origin) overflow-x-hidden overflow-y-auto rounded-md surface-ornate text-popover-foreground data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
          position === 'popper' &&
            'data-[side=bottom]:translate-y-1 data-[side=left]:-translate-x-1 data-[side=right]:translate-x-1 data-[side=top]:-translate-y-1',
          className
        )}
        position={position}
        {...props}
      >
        <SelectScrollUpButton />
        <SelectPrimitive.Viewport
          className={cn(
            'p-1',
            position === 'popper' &&
              'h-(--radix-select-trigger-height) w-full min-w-(--radix-select-trigger-width) scroll-my-1'
          )}
        >
          {children}
        </SelectPrimitive.Viewport>
        <SelectScrollDownButton />
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  )
}

function SelectLabel({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Label>) {
  return (
    <SelectPrimitive.Label
      data-slot='select-label'
      className={cn(
        'px-2 py-1.5 text-caption text-muted-foreground',
        className
      )}
      {...props}
    />
  )
}

function SelectItem({
  className,
  children,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Item>) {
  const { open, value } = React.useContext(SelectStateContext)
  if (!open && value !== undefined && props.value !== value) return null
  return (
    <SelectPrimitive.Item
      data-slot='select-item'
      className={cn(
        'relative flex w-full min-w-0 cursor-default items-center gap-2 rounded-sm py-1.5 ps-2 pe-8 text-control wrap-anywhere outline-hidden select-none focus:bg-accent focus:text-accent-foreground data-disabled:pointer-events-none data-disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-icon-md [&_svg]:shrink-0 [&_svg]:text-muted-foreground *:[span]:last:flex *:[span]:last:min-w-0 *:[span]:last:items-center *:[span]:last:gap-2',
        className
      )}
      {...props}
    >
      <span className='absolute inset-e-2 flex size-icon-md items-center justify-center'>
        <SelectPrimitive.ItemIndicator>
          <CheckIcon />
        </SelectPrimitive.ItemIndicator>
      </span>
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
  )
}

function SelectSeparator({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Separator>) {
  return (
    <SelectPrimitive.Separator
      data-slot='select-separator'
      className={cn('pointer-events-none -mx-1 my-1 h-px bg-border', className)}
      {...props}
    />
  )
}

function SelectScrollUpButton({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.ScrollUpButton>) {
  return (
    <SelectPrimitive.ScrollUpButton
      data-slot='select-scroll-up-button'
      className={cn(
        'flex cursor-default items-center justify-center py-1',
        className
      )}
      {...props}
    >
      <ChevronUpIcon className='size-icon-md' />
    </SelectPrimitive.ScrollUpButton>
  )
}

function SelectScrollDownButton({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.ScrollDownButton>) {
  return (
    <SelectPrimitive.ScrollDownButton
      data-slot='select-scroll-down-button'
      className={cn(
        'flex cursor-default items-center justify-center py-1',
        className
      )}
      {...props}
    >
      <ChevronDownIcon className='size-icon-md' />
    </SelectPrimitive.ScrollDownButton>
  )
}

export {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectScrollDownButton,
  SelectScrollUpButton,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
}

import * as React from 'react'
import * as ToggleGroupPrimitive from '@radix-ui/react-toggle-group'
import { type VariantProps } from 'class-variance-authority'
import { type ActProp, refusalOf } from '@/api/mutation'
import { cn } from '@/lib/utils'
import { Refusal } from './refusal'
import { toggleVariants } from './toggle'

const ToggleGroupContext = React.createContext<
  VariantProps<typeof toggleVariants>
>({
  size: 'default',
  variant: 'default',
})

function ToggleGroup({
  className,
  variant,
  size,
  children,
  act,
  disabled,
  ...props
}: React.ComponentProps<typeof ToggleGroupPrimitive.Root> &
  VariantProps<typeof toggleVariants> & { act?: ActProp }) {
  const refusal = refusalOf(act)
  return (
    <Refusal reason={refusal}>
      <ToggleGroupPrimitive.Root
        disabled={disabled || refusal !== null}
        data-slot='toggle-group'
        data-variant={variant ?? 'default'}
        data-size={size ?? 'default'}
        className={cn(
          'group/toggle-group flex w-fit max-w-full flex-wrap items-center gap-1 rounded-md',
          className
        )}
        {...props}
      >
        <ToggleGroupContext value={{ variant, size }}>
          {children}
        </ToggleGroupContext>
      </ToggleGroupPrimitive.Root>
    </Refusal>
  )
}

function ToggleGroupItem({
  className,
  children,
  ...props
}: React.ComponentProps<typeof ToggleGroupPrimitive.Item>) {
  const context = React.useContext(ToggleGroupContext)
  return (
    <ToggleGroupPrimitive.Item
      data-slot='toggle-group-item'
      data-control-size={context.size ?? 'default'}
      className={cn(
        toggleVariants({ variant: context.variant, size: context.size }),
        className
      )}
      {...props}
    >
      {children}
    </ToggleGroupPrimitive.Item>
  )
}

export { ToggleGroup, ToggleGroupItem }

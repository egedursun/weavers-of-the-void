import * as React from 'react'
import * as TogglePrimitive from '@radix-ui/react-toggle'
import { cva, type VariantProps } from 'class-variance-authority'
import { type ActProp, refusalOf } from '@/api/mutation'
import { cn } from '@/lib/utils'
import { controlHeight, controlIcon } from './control-size'
import { Refusal } from './refusal'

const toggleVariants = cva(
  [
    'inline-flex max-w-full shrink-0 items-center justify-center gap-2 rounded-md border font-medium whitespace-nowrap text-control text-muted-foreground transition-[color,background-color,box-shadow] outline-none',
    'hover:bg-field-hover hover:text-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50',
    'data-[state=on]:plate-active',
    '[&_svg]:pointer-events-none [&_svg]:shrink-0',
  ],
  {
    variants: {
      variant: {
        default: 'border-transparent bg-transparent',
        outline: 'plate-track',
      },
      size: {
        sm: [controlHeight.sm, controlIcon.sm, 'min-w-control-sm gap-1.5 px-2'],
        default: [
          controlHeight.default,
          controlIcon.default,
          'min-w-control-md px-2.5',
        ],
        lg: [controlHeight.lg, controlIcon.lg, 'min-w-control-lg px-3'],
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

function Toggle({
  className,
  variant,
  size,
  act,
  disabled,
  ...props
}: React.ComponentProps<typeof TogglePrimitive.Root> &
  VariantProps<typeof toggleVariants> & { act?: ActProp }) {
  const refusal = refusalOf(act)
  return (
    <Refusal reason={refusal}>
      <TogglePrimitive.Root
        disabled={disabled || refusal !== null}
        data-slot='toggle'
        data-control-size={size ?? 'default'}
        className={cn(toggleVariants({ variant, size, className }))}
        {...props}
      />
    </Refusal>
  )
}

export { Toggle, toggleVariants }

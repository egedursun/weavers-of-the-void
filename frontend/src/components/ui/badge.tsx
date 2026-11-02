import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex w-fit max-w-full min-w-0 shrink-0 items-center justify-center gap-1 overflow-hidden rounded-md border text-caption font-medium whitespace-nowrap transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 [&>svg]:pointer-events-none [&>svg]:size-icon-xs [&>svg]:shrink-0',
  {
    variants: {
      variant: {
        default:
          'border-primary/35 bg-primary/12 text-primary [a&]:hover:bg-primary/20',
        secondary:
          'border-transparent bg-secondary text-secondary-foreground [a&]:hover:bg-secondary/90',
        destructive:
          'border-destructive/35 bg-destructive/12 text-destructive [a&]:hover:bg-destructive/20',
        success:
          'border-success/35 bg-success/12 text-success [a&]:hover:bg-success/20',
        warning:
          'border-warning/35 bg-warning/12 text-warning [a&]:hover:bg-warning/20',
        info: 'border-info/35 bg-info/12 text-info [a&]:hover:bg-info/20',
        solid:
          'border-transparent bg-primary text-primary-foreground [a&]:hover:bg-primary/90',
        outline:
          'border-border text-foreground [a&]:hover:bg-accent [a&]:hover:text-accent-foreground',
      },
      size: {
        sm: 'h-badge-sm px-1.5',
        default: 'h-badge-md px-2',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

function Badge({
  className,
  variant,
  size,
  asChild = false,
  children,
  ...props
}: React.ComponentProps<'span'> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : 'span'

  return (
    <Comp
      data-slot='badge'
      data-badge-size={size ?? 'default'}
      className={cn(badgeVariants({ variant, size }), className)}
      {...props}
    >
      {asChild
        ? children
        : React.Children.map(children, (child) =>
            typeof child === 'string' || typeof child === 'number' ? (
              <span className='min-w-0 truncate'>{child}</span>
            ) : (
              child
            )
          )}
    </Comp>
  )
}

export { Badge, badgeVariants }

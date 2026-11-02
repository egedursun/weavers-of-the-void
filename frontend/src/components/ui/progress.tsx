import * as React from 'react'
import * as ProgressPrimitive from '@radix-ui/react-progress'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const progressVariants = cva(
  'relative w-full min-w-0 overflow-hidden rounded-full bg-muted',
  {
    variants: {
      size: {
        sm: 'h-meter-sm',
        default: 'h-meter-md',
      },
    },
    defaultVariants: {
      size: 'default',
    },
  }
)

const indicatorVariants = cva(
  'h-full w-full flex-1 rounded-full transition-transform',
  {
    variants: {
      tone: {
        default: 'bg-primary',
        success: 'bg-success',
        warning: 'bg-warning',
        destructive: 'bg-destructive',
        muted: 'bg-muted-foreground',
        info: 'bg-info',
        verdigris: 'bg-brand-verdigris',
        common: 'bg-rarity-common',
        uncommon: 'bg-rarity-uncommon',
        rare: 'bg-rarity-rare',
        epic: 'bg-rarity-epic',
        legendary: 'bg-rarity-legendary',
        mythic: 'bg-rarity-mythic',
      },
    },
    defaultVariants: {
      tone: 'default',
    },
  }
)

type ProgressTone = NonNullable<VariantProps<typeof indicatorVariants>['tone']>

const PERCENT = 100

function Progress({
  className,
  value,
  size,
  tone,
  indeterminate = false,
  ...props
}: React.ComponentProps<typeof ProgressPrimitive.Root> &
  VariantProps<typeof progressVariants> &
  VariantProps<typeof indicatorVariants> & { indeterminate?: boolean }) {
  const clamped = Math.min(PERCENT, Math.max(0, value ?? 0))
  return (
    <ProgressPrimitive.Root
      data-slot='progress'
      data-size={size ?? 'default'}
      className={cn(progressVariants({ size }), className)}
      value={indeterminate ? null : clamped}
      {...props}
    >
      <ProgressPrimitive.Indicator
        data-slot='progress-indicator'
        className={cn(
          indicatorVariants({ tone }),
          indeterminate && 'w-2/5 animate-indeterminate'
        )}
        style={
          indeterminate
            ? undefined
            : { transform: `translateX(-${PERCENT - clamped}%)` }
        }
      />
    </ProgressPrimitive.Root>
  )
}

export { Progress }
export type { ProgressTone }

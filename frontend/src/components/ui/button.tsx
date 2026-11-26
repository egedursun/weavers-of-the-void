import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { type ActProp, refusalOf } from '@/api/mutation'
import { cn } from '@/lib/utils'
import {
  type ControlSize,
  controlHeight,
  controlIcon,
  controlSquare,
} from './control-size'
import { Tooltip, TooltipContent, TooltipTrigger } from './tooltip'

const buttonVariants = cva(
  [
    'relative inline-flex max-w-full min-w-0 shrink-0 items-center justify-center gap-2 rounded-md border border-transparent font-medium whitespace-nowrap text-control select-none',
    'transition-[color,background-color,border-color,box-shadow] outline-none',
    'focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50',
    'disabled:pointer-events-none disabled:opacity-50 aria-disabled:cursor-not-allowed aria-disabled:opacity-50',
    'aria-invalid:border-destructive aria-invalid:ring-destructive/20',
    '[&_svg]:pointer-events-none [&_svg]:shrink-0',
  ],
  {
    variants: {
      variant: {
        default: 'gilded-control font-display font-bold tracking-wide',
        destructive: 'gilded-control font-display font-bold tracking-wide',
        outline:
          'border-gild/45 bg-plate text-plate-ink shadow-xs hover:border-gild/80 hover:bg-plate-hover aria-checked:plate-chosen',
        field: 'well font-normal text-foreground',
        secondary:
          'bg-secondary text-secondary-foreground shadow-xs hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        chrome:
          'text-foreground hover:bg-gild/15 hover:text-gild-hi aria-expanded:bg-gild/15 aria-expanded:text-gild-hi',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        sm: [
          controlHeight.sm,
          controlIcon.sm,
          'gap-1.5 px-3.5 has-[>svg]:px-3',
        ],
        default: [
          controlHeight.default,
          controlIcon.default,
          'px-5 has-[>svg]:px-4',
        ],
        lg: [controlHeight.lg, controlIcon.lg, 'px-6 has-[>svg]:px-5'],
        'icon-sm': [controlSquare.sm, controlIcon.sm],
        icon: [controlSquare.default, controlIcon.default],
        'icon-lg': [controlSquare.lg, controlIcon.lg],
        tile: [
          controlIcon.default,
          'h-auto min-h-control-lg w-full justify-start gap-2.5 rounded-lg p-2.5 text-start font-normal whitespace-normal',
        ],
        figure: [
          'h-auto flex-col items-center gap-1 rounded-xl p-2 font-normal',
        ],
        stage: [
          'h-auto w-full flex-col items-stretch gap-2 rounded-lg px-0 py-1.5 font-normal whitespace-normal',
        ],
        card: [
          controlIcon.default,
          'h-full min-h-control-lg w-full flex-col items-stretch justify-start gap-2 rounded-lg p-3 text-start font-normal whitespace-normal',
        ],
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

type ButtonSize = NonNullable<VariantProps<typeof buttonVariants>['size']>

const CARD_SIZES = new Set<ButtonSize>(['tile', 'figure', 'card'])

const OWN_SURFACE = /(^|\s|:)bg-/

function craftedPlate(
  variant: ButtonProps['variant'],
  size: ButtonSize,
  className: string | undefined,
  role: string | undefined
) {
  return (
    variant === 'outline' &&
    !CARD_SIZES.has(size) &&
    role !== 'combobox' &&
    !OWN_SURFACE.test(className ?? '')
  )
}

const CONTROL_SIZE_OF: Record<ButtonSize, ControlSize> = {
  sm: 'sm',
  default: 'default',
  lg: 'lg',
  'icon-sm': 'sm',
  icon: 'default',
  'icon-lg': 'lg',
  tile: 'lg',
  figure: 'lg',
  stage: 'lg',
  card: 'lg',
}

type ButtonProps = React.ComponentProps<'button'> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
    disabledReason?: string
    act?: ActProp
  }

function wrapText(children: React.ReactNode) {
  return React.Children.map(children, (child) =>
    typeof child === 'string' || typeof child === 'number' ? (
      <span className='min-w-0 truncate'>{child}</span>
    ) : (
      child
    )
  )
}

function Button({
  className,
  variant,
  size,
  asChild = false,
  disabled,
  disabledReason,
  act,
  onClick,
  children,
  ...props
}: ButtonProps) {
  const Comp = asChild ? Slot : 'button'
  const refusal = refusalOf(act)
  const reason = refusal ?? disabledReason
  const blocked = Boolean(disabled) || refusal !== null
  const explained = Boolean(blocked && reason)
  const shape = size ?? 'default'
  const crafted = craftedPlate(variant, shape, className, props.role)
  const button = (
    <Comp
      data-slot='button'
      data-control-size={CONTROL_SIZE_OF[size ?? 'default']}
      data-variant={variant ?? 'default'}
      data-shape={CARD_SIZES.has(shape) ? 'card' : 'plate'}
      className={cn(
        buttonVariants({ variant, size }),
        crafted && 'gilded-control font-display font-semibold tracking-wide',
        variant === 'outline' &&
          CARD_SIZES.has(shape) &&
          'surface-sheen border-gild/60 bg-card hover:bg-accent',
        className
      )}
      disabled={explained ? undefined : blocked}
      aria-disabled={explained ? true : undefined}
      aria-description={explained ? reason : undefined}
      onClick={
        explained
          ? (event: React.MouseEvent<HTMLButtonElement>) =>
              event.preventDefault()
          : onClick
      }
      {...props}
    >
      {asChild ? children : wrapText(children)}
    </Comp>
  )
  if (!explained) return button
  return (
    <Tooltip>
      <TooltipTrigger asChild>{button}</TooltipTrigger>
      <TooltipContent>{reason}</TooltipContent>
    </Tooltip>
  )
}

export { Button, buttonVariants }
export type { ButtonProps }

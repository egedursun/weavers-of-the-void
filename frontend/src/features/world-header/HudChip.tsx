import { type ComponentProps, type ReactNode } from 'react'
import { Link } from '@tanstack/react-router'
import { type NavRoute } from '@/config/navigation'
import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { type KpiTone } from '@/components/domain'
import { Muted } from '@/components/typography'
import { HUD_ICON_CLASS } from './hudTones'

type HudChipBody = {
  icon: LucideIcon
  tone?: KpiTone
  label?: string
  spinning?: boolean
  children?: ReactNode
}

function HudContent({
  icon: Icon,
  tone = 'muted',
  label,
  spinning = false,
  children,
}: HudChipBody) {
  return (
    <>
      <Icon
        aria-hidden='true'
        className={cn(
          HUD_ICON_CLASS[tone],
          spinning && 'animate-spin motion-reduce:animate-none'
        )}
      />
      {label && (
        <Muted
          as='span'
          variant='caption'
          className='hidden @6xl/header:inline'
        >
          {label}
        </Muted>
      )}
      {children}
    </>
  )
}

export function HudChip({
  icon,
  tone,
  label,
  spinning,
  children,
  className,
  ...props
}: HudChipBody & Omit<ComponentProps<typeof Button>, 'children'>) {
  return (
    <Button
      variant='outline'
      size='sm'
      data-hud-chip
      className={cn('max-w-none gap-1.5 bg-card/70', className)}
      {...props}
    >
      <HudContent icon={icon} tone={tone} label={label} spinning={spinning}>
        {children}
      </HudContent>
    </Button>
  )
}

export function HudLink({
  to,
  icon,
  tone,
  label,
  spinning,
  children,
  className,
  ...props
}: HudChipBody & { to: NavRoute } & Omit<ComponentProps<'a'>, 'children'>) {
  return (
    <Button
      variant='outline'
      size='sm'
      asChild
      data-hud-chip
      className={cn('max-w-none gap-1.5 bg-card/70', className)}
    >
      <Link to={to} {...props}>
        <HudContent icon={icon} tone={tone} label={label} spinning={spinning}>
          {children}
        </HudContent>
      </Link>
    </Button>
  )
}

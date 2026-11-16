import * as React from 'react'
import { cn } from '@/lib/utils'
import { OrnateFrame } from './ornate'

function Card({
  className,
  crest = true,
  frame = 'card',
  ...props
}: React.ComponentProps<'div'> & {
  crest?: boolean
  frame?: 'card' | 'panel'
}) {
  const panel = frame === 'panel'
  return (
    <OrnateFrame
      data-slot='card'
      frame={frame}
      crest={crest}
      footCrest={panel}
      className={cn(
        'flex min-w-0 flex-col gap-4 text-card-foreground',
        panel ? 'px-2 py-9 sm:px-4' : 'py-5',
        className
      )}
      {...props}
    />
  )
}

function CardHeader({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot='card-header'
      className={cn(
        '@container/card-header grid auto-rows-min grid-rows-[auto_auto] items-start gap-1 px-5 has-data-[slot=card-action]:grid-cols-[minmax(0,1fr)_auto] [.border-b]:pb-5',
        className
      )}
      {...props}
    />
  )
}

function CardTitle({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot='card-title'
      data-typography='section-title'
      className={cn(
        'min-w-0 text-gilded font-display text-title font-semibold',
        className
      )}
      {...props}
    />
  )
}

function CardDescription({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot='card-description'
      className={cn('min-w-0 text-body text-muted-foreground', className)}
      {...props}
    />
  )
}

function CardAction({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot='card-action'
      className={cn(
        'col-start-2 row-span-2 row-start-1 self-start justify-self-end',
        className
      )}
      {...props}
    />
  )
}

function CardContent({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot='card-content'
      className={cn('min-w-0 px-5', className)}
      {...props}
    />
  )
}

function CardFooter({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot='card-footer'
      className={cn('flex items-center gap-2 px-5 [.border-t]:pt-5', className)}
      {...props}
    />
  )
}

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
}

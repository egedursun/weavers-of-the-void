import { type HTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { type TextTag, Truncatable } from './Truncatable'
import {
  type TextTone,
  type TextVariant,
  type TextWeight,
  type Truncate,
  textVariants,
  toneClass,
} from './textStyles'

export type TextProps = HTMLAttributes<HTMLElement> & {
  as?: TextTag
  variant?: TextVariant
  weight?: TextWeight
  tone?: TextTone
  truncate?: Truncate
  italic?: boolean
  htmlFor?: string
  dateTime?: string
  children?: ReactNode
}

export function Text({
  as = 'p',
  variant = 'body',
  weight = 'normal',
  tone = 'default',
  italic = false,
  className,
  ...props
}: TextProps) {
  return (
    <Truncatable
      as={as}
      data-typography={variant}
      className={cn(
        textVariants({ variant, weight }),
        toneClass[tone],
        italic && 'italic',
        variant === 'prose' && 'max-w-reading',
        className
      )}
      {...props}
    />
  )
}

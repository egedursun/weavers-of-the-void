import { cva } from 'class-variance-authority'

export type Truncate = boolean | 1 | 2 | 3 | 4

export const truncateClass: Record<1 | 2 | 3 | 4, string> = {
  1: 'block min-w-0 truncate',
  2: 'min-w-0 line-clamp-2 wrap-anywhere',
  3: 'min-w-0 line-clamp-3 wrap-anywhere',
  4: 'min-w-0 line-clamp-4 wrap-anywhere',
}

export function truncationClass(truncate: Truncate | undefined): string {
  if (!truncate) return 'wrap-anywhere'
  return truncateClass[truncate === true ? 1 : truncate]
}

export const toneClass = {
  default: 'text-foreground',
  muted: 'text-muted-foreground',
  primary: 'text-primary',
  success: 'text-success',
  warning: 'text-warning',
  destructive: 'text-destructive',
  inherit: '',
} as const

export type TextTone = keyof typeof toneClass

export const textVariants = cva('m-0', {
  variants: {
    variant: {
      body: 'text-body',
      prose: 'text-prose',
      caption: 'text-caption',
    },
    weight: {
      normal: 'font-normal',
      medium: 'font-medium',
      semibold: 'font-semibold',
    },
  },
  defaultVariants: {
    variant: 'body',
    weight: 'normal',
  },
})

export type TextVariant = 'body' | 'prose' | 'caption'
export type TextWeight = 'normal' | 'medium' | 'semibold'

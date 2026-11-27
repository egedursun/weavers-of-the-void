import { cn } from '@/lib/utils'

type LogoProps = {
  className?: string
  title?: string
  size?: 'sm' | 'md' | 'lg' | 'boot'
}

const SOURCES = {
  boot: {
    src: '/brand/logo-256.webp',
    srcSet: undefined,
  },
  sm: {
    src: '/brand/logo-64.webp',
    srcSet: '/brand/logo-64.webp 1x, /brand/logo-128.webp 2x',
  },
  md: {
    src: '/brand/logo-256.webp',
    srcSet: '/brand/logo-256.webp 1x, /brand/logo-512.webp 2x',
  },
  lg: {
    src: '/brand/logo-512.webp',
    srcSet: '/brand/logo-512.webp 1x, /brand/logo-1024.webp 2x',
  },
} as const

export function Logo({
  className,
  title = 'Weavers of the Void',
  size = 'sm',
}: LogoProps) {
  const source = SOURCES[size]
  return (
    <img
      src={source.src}
      srcSet={source.srcSet}
      alt={title}
      draggable={false}
      decoding='async'
      className={cn('shrink-0 object-contain select-none', className)}
    />
  )
}

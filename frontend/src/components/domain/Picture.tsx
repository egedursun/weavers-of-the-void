import { type ComponentProps, type ReactNode, useState } from 'react'
import { ImageOff, LoaderCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Label } from '@/components/typography'
import { Medallion } from './KpiTile'

type PictureProps = Omit<ComponentProps<'img'>, 'src'> & {
  src: string | null | undefined
  fallback?: ReactNode
  missingClassName?: string
  compact?: boolean
}

export function Picture({
  src,
  fallback,
  missingClassName,
  compact = false,
  className,
  alt = '',
  onLoad,
  onError,
  ...props
}: PictureProps) {
  const [broken, setBroken] = useState<string | null>(null)
  const [loaded, setLoaded] = useState<string | null>(null)
  const fail: ComponentProps<'img'>['onError'] = (event) => {
    setBroken(src ?? null)
    onError?.(event)
  }
  if (!src || broken === src)
    return (
      fallback ?? (
        <span
          role={alt ? 'img' : undefined}
          aria-label={alt || undefined}
          aria-hidden={alt ? undefined : true}
          data-domain='picture-missing'
          className={cn(
            'flex min-w-0 flex-col items-center justify-center gap-2 overflow-hidden rounded-md p-2 text-center sealed-well',
            missingClassName ?? className
          )}
        >
          {compact ? (
            <ImageOff
              aria-hidden='true'
              className='size-icon-sm text-muted-foreground'
            />
          ) : (
            <>
              <Medallion icon={ImageOff} tone='muted' size='sm' />
              <Label truncate className='max-w-full'>
                No image file
              </Label>
            </>
          )}
        </span>
      )
    )
  if (loaded !== src)
    return (
      <span
        role='status'
        aria-label='Loading image'
        aria-busy='true'
        data-domain='picture-loading'
        className={cn(
          'relative flex min-w-0 animate-skeleton flex-col items-center justify-center gap-2 overflow-hidden rounded-md bg-accent p-2 text-center',
          missingClassName ?? className
        )}
      >
        <LoaderCircle
          aria-hidden='true'
          className={cn(
            'animate-spin text-primary',
            compact ? 'size-icon-sm' : 'size-icon-lg'
          )}
        />
        {!compact && (
          <Label truncate className='max-w-full'>
            Loading image
          </Label>
        )}
        <img
          {...props}
          ref={(node) => {
            if (node?.complete && node.naturalWidth > 0) setLoaded(src)
          }}
          src={src}
          alt={alt}
          className='absolute inset-0 size-full opacity-0'
          onLoad={(event) => {
            setLoaded(src)
            onLoad?.(event)
          }}
          onError={fail}
        />
      </span>
    )
  return (
    <img
      src={src}
      alt={alt}
      data-domain='picture'
      className={className}
      onLoad={onLoad}
      onError={fail}
      {...props}
    />
  )
}

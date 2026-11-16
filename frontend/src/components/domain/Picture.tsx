import { type ComponentProps, type ReactNode, useState } from 'react'
import { ImageOff } from 'lucide-react'
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
  ...props
}: PictureProps) {
  const [broken, setBroken] = useState<string | null>(null)
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
  return (
    <img
      src={src}
      alt={alt}
      data-domain='picture'
      className={className}
      onError={() => setBroken(src)}
      {...props}
    />
  )
}

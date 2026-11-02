import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { type Rarity } from '@/constants/rarity'

const STROKE = 1.6
const FACET = 0.22
const TABLE = 0.38

const SHAPES: Record<Rarity, ReactNode> = {
  common: (
    <>
      <path
        d='M4.8 13.2c0-4.2 3.2-7.4 7.2-7.4s7.2 3 7.2 7.2-3.1 6.2-7.2 6.2-7.2-1.9-7.2-6z'
        fillOpacity={FACET}
      />
      <path d='M8.6 11.2c.8-1.7 2.3-2.6 4.1-2.7' fill='none' />
    </>
  ),
  uncommon: (
    <>
      <path
        d='M12 2.8c3.9 3.3 6 6.3 6 9.2s-2.1 5.9-6 9.2c-3.9-3.3-6-6.3-6-9.2s2.1-5.9 6-9.2z'
        fillOpacity={FACET}
      />
      <path d='M12 2.8v18.4M12 7.6l-3.4 4.4L12 16.4l3.4-4.4z' fill='none' />
    </>
  ),
  rare: (
    <>
      <path d='M12 2.6l8.1 4.7v9.4L12 21.4l-8.1-4.7V7.3z' fillOpacity={FACET} />
      <path d='M12 7.4l4 2.3v4.6l-4 2.3-4-2.3V9.7z' fillOpacity={TABLE} />
      <path
        d='M12 2.6v4.8M20.1 7.3l-4.1 2.4M20.1 16.7l-4.1-2.4M12 21.4v-4.8M3.9 16.7l4.1-2.4M3.9 7.3l4.1 2.4'
        fill='none'
      />
    </>
  ),
  epic: (
    <>
      <path d='M12 2.4l3.2 5.2v13.6H8.8V7.6z' fillOpacity={TABLE} />
      <path d='M8.8 9.6L6 8.2l-2.4 4.6v8.4h5.2' fillOpacity={FACET} />
      <path d='M15.2 9.6L18 8.2l2.4 4.6v8.4h-5.2' fillOpacity={FACET} />
      <path d='M12 2.4v18.8M3.6 21.2h16.8' fill='none' />
    </>
  ),
  legendary: (
    <>
      <path
        d='M3.2 7.6l4.6 4L12 4.4l4.2 7.2 4.6-4-1.9 10.2H5.1z'
        fillOpacity={FACET}
      />
      <path d='M5.1 17.8h13.8v2.6H5.1z' fillOpacity={TABLE} />
      <circle cx='12' cy='13.6' r='1.7' fillOpacity={TABLE + FACET} />
      <circle cx='3.2' cy='7.6' r='0.9' />
      <circle cx='12' cy='4.4' r='0.9' />
      <circle cx='20.8' cy='7.6' r='0.9' />
    </>
  ),
  mythic: (
    <>
      <path d='M7.4 7.2h9.2l3.6 4.2L12 21 3.8 11.4z' fillOpacity={FACET} />
      <path d='M3.8 11.4h16.4' fill='none' />
      <path d='M9.4 7.2l-1.6 4.2L12 21l4.2-9.6-1.6-4.2' fill='none' />
      <path d='M12 7.2l-2.2 4.2h4.4z' fillOpacity={TABLE} />
      <path
        d='M12 1.4v2.4M4.4 3.8l1.7 1.7M19.6 3.8l-1.7 1.7M1.6 11.4h1.1M21.3 11.4h1.1'
        fill='none'
      />
    </>
  ),
}

type RarityIconProps = {
  rarity: Rarity
  className?: string
  label?: string
}

export function RarityIcon({ rarity, className, label }: RarityIconProps) {
  return (
    <svg
      data-rarity-icon={rarity}
      viewBox='0 0 24 24'
      fill='currentColor'
      stroke='currentColor'
      strokeWidth={STROKE}
      strokeLinecap='round'
      strokeLinejoin='round'
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      className={cn('shrink-0', className)}
    >
      {SHAPES[rarity]}
    </svg>
  )
}

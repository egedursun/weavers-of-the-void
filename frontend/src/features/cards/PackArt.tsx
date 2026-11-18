import { useMemo } from 'react'
import { APP_NAME } from '@/config/brand'
import { lacePath, ticksPath } from './packModel'

const CORNERS = ['tl', 'tr', 'bl', 'br'] as const

function BrandSeal({ className }: { className: string }) {
  return (
    <span className={`brand-seal ${className}`} aria-hidden='true'>
      <span className='brand-seal-ring' />
      <span className='brand-seal-logo' />
    </span>
  )
}

function Corners({ className }: { className: string }) {
  return CORNERS.map((corner) => (
    <span key={corner} data-corner={corner} className={className} />
  ))
}

export function PackFace({ still = false }: { still?: boolean }) {
  return (
    <div className='pack-face' data-still={still || undefined}>
      <span className='pack-face-void' />
      <span className='pack-face-holo' />
      <span className='pack-face-grain' />
      <span className='pack-face-frame' />
      <Corners className='pack-face-corner' />
      <span className='pack-face-crest' data-edge='top' />
      <BrandSeal className='pack-face-seal' />
      <span className='pack-face-title'>
        <span className='pack-face-title-main'>Weavers</span>
        <span className='pack-face-title-sub'>of the Void</span>
      </span>
      <span className='pack-face-divider' />
      <span className='pack-face-label'>Card pack</span>
      <span className='pack-face-count'>One card inside</span>
      <span className='pack-face-crest' data-edge='bottom' />
      <span className='pack-face-shade' />
      <span className='pack-face-sheen' />
      <span className='pack-face-crimp' data-edge='top' />
      <span className='pack-face-crimp' data-edge='bottom' />
    </div>
  )
}

export function CardReverse() {
  const lace = useMemo(
    () => ({
      outer: lacePath({ outer: 36, roller: 15, pen: 13, radius: 47 }),
      inner: lacePath({ outer: 30, roller: 11, pen: 8, radius: 34, turn: 0.4 }),
      rim: ticksPath(144, 45.2, 46.6),
    }),
    []
  )
  return (
    <div
      className='card-reverse'
      role='img'
      aria-label={`${APP_NAME} card, face down`}
    >
      <div className='card-reverse-face'>
        <svg
          viewBox='0 0 100 100'
          className='card-reverse-lace'
          aria-hidden='true'
        >
          <path d={lace.outer} strokeWidth='0.18' />
          <path d={lace.inner} strokeWidth='0.22' />
          <path d={lace.rim} strokeWidth='0.22' />
          <circle cx='50' cy='50' r='47.8' strokeWidth='0.3' />
        </svg>
        <span className='card-reverse-rule' />
        <Corners className='card-reverse-corner' />
        <span className='card-reverse-crest' data-edge='top' />
        <BrandSeal className='card-reverse-seal' />
        <span className='card-reverse-name'>
          <span className='card-reverse-name-main'>Weavers</span>
          <span className='card-reverse-name-sub'>of the Void</span>
        </span>
        <span className='card-reverse-crest' data-edge='bottom' />
      </div>
      <span className='card-reverse-charge' />
      <span className='card-reverse-glint' />
    </div>
  )
}

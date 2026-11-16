import * as React from 'react'
import cornerSmallUrl from '@/assets/ornate/corner-small.webp'
import cornerUrl from '@/assets/ornate/corner.webp'
import crestUrl from '@/assets/ornate/crest.webp'
import dividerUrl from '@/assets/ornate/divider.webp'
import wingUrl from '@/assets/ornate/wing.webp'
import { cn } from '@/lib/utils'

type GemTone =
  'gold' | 'verdigris' | 'info' | 'success' | 'warning' | 'danger' | 'muted'

const GEM_CLASS: Record<GemTone, string> = {
  gold: 'gem-gold',
  verdigris: 'gem-verdigris',
  info: 'gem-info',
  success: 'gem-success',
  warning: 'gem-warning',
  danger: 'gem-danger',
  muted: 'gem-muted',
}

const InsideFrame = React.createContext(false)

function useInsideFrame() {
  return React.useContext(InsideFrame)
}

type Corner = 'tl' | 'tr' | 'bl' | 'br'

const CORNERS: Corner[] = ['tl', 'tr', 'bl', 'br']

function Ornament({
  src,
  className,
  ...props
}: Omit<React.ComponentProps<'img'>, 'alt'> & { src: string }) {
  return (
    <img
      src={src}
      alt=''
      aria-hidden='true'
      draggable={false}
      decoding='async'
      className={className}
      {...props}
    />
  )
}

type FrameLevel = 'panel' | 'card' | 'tile'

type OrnateFrameProps = React.ComponentProps<'div'> & {
  frame?: FrameLevel
  crest?: boolean
  footCrest?: boolean
  tone?: GemTone
  nameplate?: React.ReactNode
  bayClassName?: string
}

function FrameCorners({ frame }: { frame: FrameLevel | 'rail' }) {
  if (frame === 'tile')
    return CORNERS.map((place) => (
      <span
        key={place}
        aria-hidden='true'
        data-corner={place}
        className='ornate-stud'
      />
    ))
  const corner = frame === 'panel' ? cornerUrl : cornerSmallUrl
  return CORNERS.map((place) => (
    <Ornament
      key={place}
      src={corner}
      data-corner={place}
      data-frame={frame}
      className='ornate-corner'
    />
  ))
}

function OrnateFrame({
  frame = 'panel',
  crest = false,
  footCrest = false,
  tone = 'gold',
  nameplate,
  bayClassName,
  className,
  children,
  ...props
}: OrnateFrameProps) {
  const plated = nameplate ? true : undefined
  return (
    <div
      data-slot='ornate-bay'
      data-frame={frame}
      data-plated={plated}
      data-crested={crest && frame === 'panel' ? true : undefined}
      className={cn('ornate-bay', bayClassName)}
    >
      <div
        data-slot='ornate-frame'
        data-frame={frame}
        data-plated={plated}
        className={cn('ornate-frame', GEM_CLASS[tone], className)}
        {...props}
      >
        <FrameCorners frame={frame} />
        {crest &&
          (frame !== 'panel' ? (
            <span aria-hidden='true' className='ornate-gem' />
          ) : (
            <Ornament src={crestUrl} className='ornate-crest' />
          ))}
        {footCrest && (
          <Ornament
            src={crestUrl}
            data-edge='bottom'
            className='ornate-crest'
          />
        )}
        {nameplate && <Nameplate>{nameplate}</Nameplate>}
        <InsideFrame value>{children}</InsideFrame>
      </div>
    </div>
  )
}

function Nameplate({ children }: { children: React.ReactNode }) {
  return (
    <div data-slot='nameplate' className='ornate-nameplate'>
      <Ornament
        src={wingUrl}
        data-side='start'
        className='ornate-nameplate-wing'
      />
      {children}
      <Ornament
        src={wingUrl}
        data-side='end'
        className='ornate-nameplate-wing'
      />
    </div>
  )
}

function Flourish({ className }: { className?: string }) {
  return (
    <Ornament
      src={wingUrl}
      data-slot='flourish'
      className={cn('ornate-flourish', className)}
    />
  )
}

function Divider({ className }: { className?: string }) {
  return (
    <Ornament
      src={dividerUrl}
      data-slot='divider'
      className={cn('ornate-divider', className)}
    />
  )
}

export {
  Divider,
  Flourish,
  FrameCorners,
  GEM_CLASS,
  OrnateFrame,
  useInsideFrame,
}
export type { GemTone }

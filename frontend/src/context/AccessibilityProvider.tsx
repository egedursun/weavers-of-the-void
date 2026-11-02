import { useEffect, useMemo, useState } from 'react'
import { getCookie, removeCookie, setCookie } from '@/lib/cookies'
import {
  AccessibilityContext,
  CONTRASTS,
  MOTIONS,
  TEXT_SIZES,
  type Contrast,
  type Motion,
  type TextSize,
} from './accessibilityContext'

const TEXT_SIZE_COOKIE = 'aerona-text-size'
const CONTRAST_COOKIE = 'aerona-contrast'
const MOTION_COOKIE = 'aerona-motion'
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365

function readChoice<T extends string>(name: string, options: readonly T[]): T {
  const saved = getCookie(name)
  return options.find((option) => option === saved) ?? options[0]
}

export function AccessibilityProvider({
  children,
}: {
  children: React.ReactNode
}) {
  const [textSize, setTextSizeState] = useState<TextSize>(() =>
    readChoice(TEXT_SIZE_COOKIE, TEXT_SIZES)
  )
  const [contrast, setContrastState] = useState<Contrast>(() =>
    readChoice(CONTRAST_COOKIE, CONTRASTS)
  )
  const [motion, setMotionState] = useState<Motion>(() =>
    readChoice(MOTION_COOKIE, MOTIONS)
  )

  useEffect(() => {
    const root = document.documentElement
    for (const option of TEXT_SIZES)
      root.classList.remove(`text-size-${option}`)
    root.classList.add(`text-size-${textSize}`)
    root.classList.toggle('contrast-high', contrast === 'high')
    root.classList.toggle('reduce-motion', motion === 'reduce')
  }, [textSize, contrast, motion])

  const value = useMemo(
    () => ({
      textSize,
      contrast,
      motion,
      setTextSize: (next: TextSize) => {
        setCookie(TEXT_SIZE_COOKIE, next, COOKIE_MAX_AGE)
        setTextSizeState(next)
      },
      setContrast: (next: Contrast) => {
        setCookie(CONTRAST_COOKIE, next, COOKIE_MAX_AGE)
        setContrastState(next)
      },
      setMotion: (next: Motion) => {
        setCookie(MOTION_COOKIE, next, COOKIE_MAX_AGE)
        setMotionState(next)
      },
      resetAccessibility: () => {
        removeCookie(TEXT_SIZE_COOKIE)
        removeCookie(CONTRAST_COOKIE)
        removeCookie(MOTION_COOKIE)
        setTextSizeState(TEXT_SIZES[0])
        setContrastState(CONTRASTS[0])
        setMotionState(MOTIONS[0])
      },
    }),
    [textSize, contrast, motion]
  )

  return <AccessibilityContext value={value}>{children}</AccessibilityContext>
}

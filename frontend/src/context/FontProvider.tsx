import { useEffect, useMemo, useState } from 'react'
import { fonts } from '@/config/fonts'
import { getCookie, removeCookie, setCookie } from '@/lib/cookies'
import { type Font, FontContext } from './fontContext'

const FONT_COOKIE_NAME = 'aerona-font'
const FONT_COOKIE_MAX_AGE = 60 * 60 * 24 * 365

function readFont(): Font {
  const saved = getCookie(FONT_COOKIE_NAME)
  return fonts.find((font) => font === saved) ?? fonts[0]
}

export function FontProvider({ children }: { children: React.ReactNode }) {
  const [font, setFontState] = useState<Font>(readFont)

  useEffect(() => {
    const root = document.documentElement
    for (const option of fonts) root.classList.remove(`font-${option}`)
    root.classList.add(`font-${font}`)
  }, [font])

  const value = useMemo(
    () => ({
      font,
      setFont: (next: Font) => {
        setCookie(FONT_COOKIE_NAME, next, FONT_COOKIE_MAX_AGE)
        setFontState(next)
      },
      resetFont: () => {
        removeCookie(FONT_COOKIE_NAME)
        setFontState(fonts[0])
      },
    }),
    [font]
  )

  return <FontContext value={value}>{children}</FontContext>
}

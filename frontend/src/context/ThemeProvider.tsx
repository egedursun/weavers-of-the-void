import { useEffect, useMemo, useState } from 'react'
import { getCookie, removeCookie, setCookie } from '@/lib/cookies'
import {
  type ResolvedTheme,
  THEME_COOKIE_NAME,
  type Theme,
  ThemeContext,
  type ThemeContextValue,
} from './themeContext'

const DEFAULT_THEME: Theme = 'dark'
const THEME_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
const DARK_QUERY = '(prefers-color-scheme: dark)'
const THEMES: readonly Theme[] = ['dark', 'light', 'system']

function readTheme(fallback: Theme): Theme {
  const saved = getCookie(THEME_COOKIE_NAME)
  return THEMES.find((theme) => theme === saved) ?? fallback
}

function systemTheme(): ResolvedTheme {
  return window.matchMedia(DARK_QUERY).matches ? 'dark' : 'light'
}

function applyTheme(resolved: ResolvedTheme) {
  const root = document.documentElement
  root.classList.remove('light', 'dark')
  root.classList.add(resolved)
  const background = getComputedStyle(root)
    .getPropertyValue('--background')
    .trim()
  document
    .querySelector("meta[name='theme-color']")
    ?.setAttribute('content', background)
}

export function ThemeProvider({
  children,
  defaultTheme = DEFAULT_THEME,
}: {
  children: React.ReactNode
  defaultTheme?: Theme
}) {
  const [theme, setThemeState] = useState<Theme>(() => readTheme(defaultTheme))
  const [system, setSystem] = useState<ResolvedTheme>(systemTheme)
  const resolvedTheme = theme === 'system' ? system : theme

  useEffect(() => {
    const query = window.matchMedia(DARK_QUERY)
    const onChange = () => setSystem(query.matches ? 'dark' : 'light')
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])

  useEffect(() => applyTheme(resolvedTheme), [resolvedTheme])

  const value = useMemo<ThemeContextValue>(
    () => ({
      defaultTheme,
      resolvedTheme,
      theme,
      setTheme: (next) => {
        setCookie(THEME_COOKIE_NAME, next, THEME_COOKIE_MAX_AGE)
        setThemeState(next)
      },
      resetTheme: () => {
        removeCookie(THEME_COOKIE_NAME)
        setThemeState(defaultTheme)
      },
    }),
    [defaultTheme, resolvedTheme, theme]
  )

  return <ThemeContext value={value}>{children}</ThemeContext>
}

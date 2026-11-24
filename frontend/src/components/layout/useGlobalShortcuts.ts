import { useEffect } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { shortcutItems } from '@/config/navigation'
import { useEntryStack } from './entry/useEntryStack'

const HELP_KEY = '?'

export function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return (
    target.isContentEditable ||
    ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) ||
    target.closest('[role="combobox"],[role="textbox"]') !== null
  )
}

function overlayOpen(): boolean {
  return (
    document.querySelector(
      '[role="dialog"],[role="alertdialog"],[role="menu"]'
    ) !== null
  )
}

export function useGlobalShortcuts() {
  const navigate = useNavigate()
  const { open } = useEntryStack()

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (
        event.defaultPrevented ||
        event.metaKey ||
        event.ctrlKey ||
        event.altKey
      )
        return
      if (isTypingTarget(event.target) || overlayOpen()) return
      if (event.key === HELP_KEY) {
        event.preventDefault()
        open({ kind: 'help' })
        return
      }
      const item = shortcutItems().find(
        (candidate) => candidate.shortcut === event.key
      )
      if (!item) return
      event.preventDefault()
      void navigate({ to: item.to })
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [navigate, open])
}

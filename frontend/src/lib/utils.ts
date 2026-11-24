import { type ClassValue, clsx } from 'clsx'
import { extendTailwindMerge } from 'tailwind-merge'

export const TEXT_ROLES = [
  'display',
  'title',
  'body',
  'prose',
  'caption',
  'overline',
  'kpi',
  'control',
] as const

export const SPACING_TOKENS = [
  'control-sm',
  'control-md',
  'control-lg',
  'icon-xs',
  'icon-sm',
  'icon-md',
  'icon-lg',
  'icon-xl',
  'badge-sm',
  'badge-md',
  'textarea',
  'meter-sm',
  'meter-md',
  'portrait-xs',
  'portrait-sm',
  'portrait-md',
  'portrait-lg',
  'portrait-xl',
  'portrait-2xl',
  'topbar',
  'label-track',
  'entry',
  'entry-tall',
  'entry-rail',
  'reading',
  'emblem',
  'scene',
  'scene-lg',
] as const

const twMerge = extendTailwindMerge({
  extend: {
    theme: {
      spacing: [...SPACING_TOKENS],
    },
    classGroups: {
      'font-size': [{ text: [...TEXT_ROLES] }],
      'text-color': [{ text: ['gilded'] }],
    },
  },
})

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getDisplayNameInitials(displayName: string): string {
  const parts = displayName.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase()
  }
  const first = parts[0][0] ?? ''
  const last = parts[parts.length - 1]?.[0] ?? ''
  return (first + last).toUpperCase()
}

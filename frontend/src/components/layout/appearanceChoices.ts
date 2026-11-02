import {
  ALargeSmall,
  CaseSensitive,
  Feather,
  Laptop,
  Monitor,
  Moon,
  Sun,
  Type,
} from 'lucide-react'
import { type TextSize } from '@/context/accessibilityContext'
import { type Font } from '@/context/fontContext'
import { type Theme } from '@/context/themeContext'
import { type Choice } from '@/components/domain/SettingsKit'

export const THEME_CHOICES: readonly Choice<Theme>[] = [
  { value: 'dark', label: 'Dark', hint: 'The night of the Void', icon: Moon },
  { value: 'light', label: 'Light', hint: 'Parchment by day', icon: Sun },
  {
    value: 'system',
    label: 'System',
    hint: 'Follow this device',
    icon: Monitor,
  },
]

export const FONT_CHOICE: Record<Font, Omit<Choice<Font>, 'value'>> = {
  nunito: {
    label: 'Nunito Sans',
    hint: 'The studio face, soft and clear',
    icon: Feather,
  },
  inter: { label: 'Inter', hint: 'Crisp and modern', icon: Type },
  system: { label: 'System font', hint: 'Native to this device', icon: Laptop },
}

export const TEXT_SIZE_CHOICES: readonly Choice<TextSize>[] = [
  { value: 'default', label: 'Default', hint: 'As designed', icon: Type },
  {
    value: 'large',
    label: 'Large',
    hint: 'A little bigger',
    icon: CaseSensitive,
  },
  {
    value: 'larger',
    label: 'Larger',
    hint: 'Easiest to read',
    icon: ALargeSmall,
  },
]

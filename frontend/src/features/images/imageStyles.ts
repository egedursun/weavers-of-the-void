import anime from '@/assets/image-styles/anime.jpg'
import ink from '@/assets/image-styles/ink.jpg'
import painting from '@/assets/image-styles/painting.jpg'
import photoreal from '@/assets/image-styles/photoreal.jpg'
import watercolor from '@/assets/image-styles/watercolor.jpg'
import { type components } from '@/api/generated/schema'

export type ImageStyle = components['schemas']['ImageStyle']

export const CUSTOM_STYLE_MAX = 300
export const DEFAULT_IMAGE_STYLE: ImageStyle = 'photoreal'

export type ImageStyleOption = {
  value: ImageStyle
  label: string
  hint: string
  sample: string | null
}

export const IMAGE_STYLES: readonly ImageStyleOption[] = [
  {
    value: 'photoreal',
    label: 'Photoreal',
    hint: 'Like a photograph: true light, true texture.',
    sample: photoreal,
  },
  {
    value: 'painting',
    label: 'Classical painting',
    hint: 'Oil on canvas, brushwork and deep shadow.',
    sample: painting,
  },
  {
    value: 'ink',
    label: 'Book illustration',
    hint: 'Pen and ink engraving, fine hatching.',
    sample: ink,
  },
  {
    value: 'watercolor',
    label: 'Watercolour',
    hint: 'Soft washes and paper grain.',
    sample: watercolor,
  },
  {
    value: 'anime',
    label: 'Anime',
    hint: 'Clean line art and cel shading.',
    sample: anime,
  },
  {
    value: 'custom',
    label: 'Custom',
    hint: 'Describe any look in your own words.',
    sample: null,
  },
]

export function imageStyleLabel(style: ImageStyle, custom: string): string {
  if (style === 'custom') return custom.trim() || 'Custom'
  return IMAGE_STYLES.find((option) => option.value === style)?.label ?? style
}

export function imageStyleProblem(
  style: ImageStyle,
  custom: string
): string | null {
  if (style !== 'custom') return null
  if (custom.trim() === '') return 'Describe the custom image style.'
  if (custom.length > CUSTOM_STYLE_MAX)
    return `The custom image style is limited to ${CUSTOM_STYLE_MAX} characters.`
  return null
}

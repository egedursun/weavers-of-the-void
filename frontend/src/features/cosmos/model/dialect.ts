import { type components } from '@/api/generated/schema'

export type Phonology = components['schemas']['Phonology']
export type LanguageTexture = components['schemas']['LanguageTexture']

export const TEXTURE_LABEL: Record<LanguageTexture, string> = {
  flowing: 'Flowing',
  hard: 'Hard',
  guttural: 'Guttural',
  sibilant: 'Sibilant',
  long: 'Long',
  free: 'Free',
}

const LIST_SEPARATOR = ', '

export function soundList(sounds: readonly string[]): string {
  return sounds.join(LIST_SEPARATOR)
}

export function syllableText(phonology: Phonology): string {
  const { min_syllables: min, max_syllables: max } = phonology
  if (min === max) return min === 1 ? '1 syllable' : `${min} syllables`
  return `${min} to ${max} syllables`
}

export function dialectSummary(phonology: Phonology): string {
  const parts = [
    `${TEXTURE_LABEL[phonology.texture]} names of ${syllableText(phonology)}`,
  ]
  if (phonology.preferred_endings.length > 0)
    parts.push(
      `often ending in ${phonology.preferred_endings.map((ending) => `-${ending}`).join(LIST_SEPARATOR)}`
    )
  if (phonology.forbidden_sounds.length > 0)
    parts.push(`never ${soundList(phonology.forbidden_sounds)}`)
  return `${parts.join('; ')}.`
}

export function dialectRows(
  phonology: Phonology
): { label: string; value: string }[] {
  const rows = [
    { label: 'Vowels', value: soundList(phonology.vowels) },
    { label: 'Consonants', value: soundList(phonology.consonants) },
    { label: 'Never heard', value: soundList(phonology.forbidden_sounds) },
    { label: 'Word starts', value: soundList(phonology.onsets) },
    { label: 'Word ends', value: soundList(phonology.codas) },
    { label: 'Syllable shapes', value: soundList(phonology.syllable_patterns) },
    {
      label: 'Favoured endings',
      value: soundList(phonology.preferred_endings),
    },
    { label: 'Length', value: syllableText(phonology) },
  ]
  return rows.filter((row) => row.value !== '')
}

import { type EditValues } from '@/api/actions'
import { type Values } from '@/features/cosmography/parts'

export const YES_NO = { true: 'Yes', false: 'No' } as const

export function typed(
  values: Values,
  kinds: { ids?: readonly string[]; flags?: readonly string[] }
): EditValues {
  return Object.fromEntries(
    Object.entries(values).map(([key, value]) => [
      key,
      value === null
        ? null
        : kinds.flags?.includes(key)
          ? value === 'true'
          : kinds.ids?.includes(key)
            ? Number(value)
            : value,
    ])
  )
}

import { plural } from '@/lib/units'

export function battles(count: number): string {
  return count === 1 ? '1 battle' : `${plural(count, 'battle', 'battles')}`
}

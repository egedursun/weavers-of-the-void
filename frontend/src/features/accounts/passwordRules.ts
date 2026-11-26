export const PASSWORD_MIN = 10
export const PASSWORD_MAX = 256

export type PasswordCheck = {
  key: 'length' | 'name' | 'match'
  label: string
  met: boolean
}

export type Strength = 0 | 1 | 2 | 3 | 4 | 5

const CLASSES = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/] as const
const LONG = 16
const VERY_LONG = 24

export function passwordChecks(
  password: string,
  repeat: string,
  names: readonly string[],
  min: number = PASSWORD_MIN
): PasswordCheck[] {
  const lower = password.toLowerCase()
  const clashes = names
    .map((name) => name.trim().toLowerCase())
    .filter((name) => name.length >= 3)
    .some((name) => lower.includes(name))
  return [
    {
      key: 'length',
      label: `At least ${min} characters`,
      met: password.length >= min && password.length <= PASSWORD_MAX,
    },
    {
      key: 'name',
      label: 'Does not contain your username or e-mail name',
      met: password.length > 0 && !clashes,
    },
    {
      key: 'match',
      label: 'Both entries match',
      met: password.length > 0 && password === repeat,
    },
  ]
}

export function strengthOf(
  password: string,
  min: number = PASSWORD_MIN
): Strength {
  if (password.length < min) return password.length === 0 ? 0 : 1
  const kinds = CLASSES.filter((pattern) => pattern.test(password)).length
  const score =
    2 +
    (kinds >= 3 ? 1 : 0) +
    (password.length >= LONG ? 1 : 0) +
    (password.length >= VERY_LONG || kinds === CLASSES.length ? 1 : 0)
  return Math.min(5, score) as Strength
}

export function emailName(email: string): string {
  return email.split('@')[0] ?? ''
}

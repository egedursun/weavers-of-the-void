export const USERNAME_MIN = 3
export const USERNAME_MAX = 32
export const DISPLAY_NAME_MAX = 80
export const EMAIL_MAX = 254

const USERNAME = /^[a-z0-9._-]+$/
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function usernameProblem(value: string): string | null {
  const name = value.trim()
  if (name.length === 0) return 'Choose a username.'
  if (name.length < USERNAME_MIN)
    return `A username has at least ${USERNAME_MIN} characters.`
  if (name.length > USERNAME_MAX)
    return `A username has at most ${USERNAME_MAX} characters.`
  if (!USERNAME.test(name))
    return 'Use lowercase letters, digits, dots, dashes and underscores.'
  return null
}

export function emailProblem(value: string): string | null {
  const email = value.trim()
  if (email.length === 0) return 'Give an e-mail address.'
  if (email.length > EMAIL_MAX || !EMAIL.test(email))
    return 'That is not an e-mail address.'
  return null
}

export function displayNameProblem(value: string): string | null {
  const name = value.trim()
  if (name.length === 0) return 'Give a display name.'
  if (name.length > DISPLAY_NAME_MAX)
    return `A display name has at most ${DISPLAY_NAME_MAX} characters.`
  return null
}

export function firstProblem(
  ...problems: readonly (string | null)[]
): string | null {
  return problems.find((problem) => problem !== null) ?? null
}

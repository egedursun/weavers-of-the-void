export const WORKSPACE_NAME_MAX = 80

export function workspaceNameProblem(value: string): string | null {
  const name = value.trim()
  if (name.length === 0) return 'Name the workspace first.'
  if (name.length > WORKSPACE_NAME_MAX)
    return `A workspace name has at most ${WORKSPACE_NAME_MAX} characters.`
  return null
}

export function labelKey(
  kind: 'world' | 'star' | 'avatars',
  id: number
): string {
  return `${kind}:${id}`
}

export function toolTitle(name: string): string {
  const words = name.replaceAll('_', ' ').trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

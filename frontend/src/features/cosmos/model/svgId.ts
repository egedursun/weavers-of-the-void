export function svgId(reactId: string): string {
  return `cosmos-${reactId.replace(/[^a-zA-Z0-9_-]/g, '')}`
}

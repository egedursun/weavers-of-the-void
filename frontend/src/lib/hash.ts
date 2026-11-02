const FNV_OFFSET = 0x811c9dc5
const FNV_PRIME = 0x01000193
const UNIT_STEPS = 10000

export function fnv1a(text: string): number {
  let hash = FNV_OFFSET
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index)
    hash = Math.imul(hash, FNV_PRIME) >>> 0
  }
  return hash >>> 0
}

export function unitHash(text: string): number {
  return (fnv1a(text) % UNIT_STEPS) / UNIT_STEPS
}

export function signedHash(text: string): number {
  return unitHash(text) * 2 - 1
}

export function seededRandom(seed: number): () => number {
  let state = seed % 2147483647
  if (state <= 0) state += 2147483646
  return () => {
    state = (state * 16807) % 2147483647
    return (state - 1) / 2147483646
  }
}

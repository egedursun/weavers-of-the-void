import type { ServerEvent } from '@/realtime'

let knownWorld: string | null | undefined

export function leavesWorld(event: ServerEvent): boolean {
  if (event.kind === 'world.replaced') {
    knownWorld = undefined
    return true
  }
  if (event.kind !== 'stream.hello') return false
  const payload = event.payload as { world_key?: string | null }
  const world = payload.world_key ?? null
  const changed = knownWorld !== undefined && knownWorld !== world
  knownWorld = world
  return changed
}

export function forgetWorld(): void {
  knownWorld = undefined
}

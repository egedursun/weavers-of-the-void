import { useCallback, useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { queryKeys } from '@/api/queryKeys'
import { applyChanges } from './changePatch'
import { useEvent } from './useEvent'

export function ChangeFeed() {
  const client = useQueryClient()
  const version = useRef<string | null>(null)
  const busy = useRef(false)
  const again = useRef(false)
  const pull = useCallback(
    async function pull(apply: boolean): Promise<void> {
      if (busy.current) {
        again.current = true
        return
      }
      busy.current = true
      try {
        const changes = await unwrap(
          api.GET('/api/changes', {
            params: { query: { since: version.current ?? undefined } },
          })
        )
        version.current = changes.version
        if (apply) applyChanges(client, changes)
      } catch {
        version.current = null
        void client.invalidateQueries({ queryKey: queryKeys.world.all })
      } finally {
        busy.current = false
        if (again.current) {
          again.current = false
          void pull(true)
        }
      }
    },
    [client]
  )
  useEffect(() => {
    void pull(false)
  }, [pull])
  useEvent('world.changes', () => {
    void pull(true)
  })
  return null
}

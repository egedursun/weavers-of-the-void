import { useState } from 'react'
import { useEvent } from '@/realtime'

export function useActingSons(): ReadonlySet<number> {
  const [acting, setActing] = useState<ReadonlySet<number>>(new Set())
  useEvent('son.turn_started', (event) => {
    setActing((current) => new Set([...current, event.payload.son_id]))
  })
  useEvent('son.turn_finished', (event) => {
    setActing((current) => {
      const next = new Set(current)
      next.delete(event.payload.son_id)
      return next
    })
  })
  return acting
}

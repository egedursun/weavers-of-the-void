import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { paramEquals, useRunningJob } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'

export function useRedrawLikeness() {
  const running = useRunningJob((job) =>
    paramEquals(job, 'kind', 'creator_portrait')
  )
  const action = useGodAction({
    writes: [{ lever: 'creator:content' }],
    run: () => unwrap(api.POST('/api/creator/portrait')),
    success: 'The likeness is being redrawn',
  })
  return { action, running }
}

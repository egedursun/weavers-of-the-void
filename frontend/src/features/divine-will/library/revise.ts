import { useWillDock } from '@/components/layout/divine-will/dockStore'
import { type WillArtifactSummary } from '../types'
import { useWill } from '../willStore'

export function useReviseArtifact() {
  const plant = useWill((state) => state.plant)
  const setOpen = useWillDock((state) => state.setOpen)
  const setView = useWillDock((state) => state.setView)
  return (artifact: Pick<WillArtifactSummary, 'id' | 'title'>) => {
    plant({
      mode: 'creative_work',
      text: `Revise artifact#${String(artifact.id)} “${artifact.title}”: `,
    })
    setView('chat')
    setOpen(true)
  }
}

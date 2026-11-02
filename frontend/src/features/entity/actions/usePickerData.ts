import { useMemo } from 'react'
import {
  useCosmos,
  useForeignGods,
  useKnowledge,
  useNames,
  useThreads,
  useWorldState,
} from '../api/queries'
import { type PickerData } from './pickers'

export function usePickerData(): PickerData {
  const names = useNames()
  const state = useWorldState()
  const cosmos = useCosmos()
  const knowledge = useKnowledge()
  const foreignGods = useForeignGods()
  const threads = useThreads()
  return useMemo(
    () => ({
      names: names.data ?? [],
      state: state.data,
      cosmos: cosmos.data,
      knowledge: knowledge.data ?? [],
      foreignGods: foreignGods.data ?? [],
      threads: threads.data ?? [],
    }),
    [
      names.data,
      state.data,
      cosmos.data,
      knowledge.data,
      foreignGods.data,
      threads.data,
    ]
  )
}

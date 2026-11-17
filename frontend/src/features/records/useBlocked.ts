import { READ_ONLY_REASON } from '@/features/entity/actions/gate'
import { useWorldState } from '@/features/entity/api/queries'

export function useBlocked(): string | null {
  const state = useWorldState()
  return state.data?.read_only ? READ_ONLY_REASON : null
}

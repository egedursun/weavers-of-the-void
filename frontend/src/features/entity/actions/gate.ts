import { useCallback } from 'react'
import { formatInteger } from '@/lib/format'
import { modelBlock } from '@/features/providers/modelReadiness'
import { useWorldState } from '../api/queries'

export const BUSY_REASON = 'An epoch is running; this opens when it ends.'
export const READ_ONLY_REASON = 'A guest world is open read-only.'
export const PENDING_REASON = 'Working on it.'

const ESSENCE_COST = /^(\d+) essence$/
const FREE = 'Free'

export function essenceReason(cost: number, essence: number): string {
  return `${formatInteger(cost)} essence needed; you have ${formatInteger(essence)}.`
}

export function fixedCost(text: string | undefined): number | null {
  if (!text) return null
  if (text === FREE) return 0
  const match = ESSENCE_COST.exec(text.trim())
  return match ? Number(match[1]) : null
}

export type GateNeeds = {
  cost?: number | null
  world?: boolean
  llm?: boolean
}

export function useLoreGate() {
  const state = useWorldState()
  const essence = state.data?.creator?.essence ?? 0
  const busy = state.data?.epoch_running ?? false
  const readOnly = state.data?.read_only ?? false
  const llmBlock = modelBlock(state.data, 'writing')
  const reason = useCallback(
    (needs: GateNeeds = {}): string | null => {
      if (readOnly) return READ_ONLY_REASON
      if (needs.llm && llmBlock !== null) return llmBlock
      if (needs.world && busy) return BUSY_REASON
      if (
        needs.cost !== undefined &&
        needs.cost !== null &&
        needs.cost > essence
      )
        return essenceReason(needs.cost, essence)
      return null
    },
    [busy, essence, llmBlock, readOnly]
  )
  return {
    essence,
    busy,
    readOnly,
    llm: llmBlock === null,
    reason,
    state: state.data,
  }
}

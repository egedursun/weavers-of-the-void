import { createContext, useContext } from 'react'
import { type EntityContext } from './context'

export const EntityCtx = createContext<EntityContext | null>(null)

export function useEntityCtx(): EntityContext | null {
  return useContext(EntityCtx)
}

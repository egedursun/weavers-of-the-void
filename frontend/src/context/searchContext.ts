import { createContext, useContext } from 'react'

export type SearchContextValue = {
  open: boolean
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export const SearchContext = createContext<SearchContextValue | null>(null)

export function useSearch(): SearchContextValue {
  const context = useContext(SearchContext)
  if (!context)
    throw new Error('useSearch has to be used within SearchProvider')
  return context
}

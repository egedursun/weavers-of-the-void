import { useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { toast } from 'sonner'
import {
  UNIVERSE_PARAM,
  chooseUniverse,
  documentHolder,
} from '@/api/universeStore'
import { adoptLegacyStorage } from '@/lib/universeStorage'
import { useOpenUniverse } from './api'
import { type UniverseSummary } from './types'

export type UniverseLanding = '/overview' | '/genesis'

type Enterable = Pick<UniverseSummary, 'id' | 'name' | 'origin'>

export function useEnterUniverse() {
  const navigate = useNavigate()
  const open = useOpenUniverse()
  const [opening, setOpening] = useState<string | null>(null)
  const enter = (universe: Enterable, to: UniverseLanding = '/overview') => {
    setOpening(universe.id)
    open.mutate(universe.id, {
      onSuccess: () => {
        if (universe.origin === 'adopted') adoptLegacyStorage(universe.id)
        const holder = documentHolder()
        if (holder !== null && holder !== universe.id) {
          window.location.assign(`${to}?${UNIVERSE_PARAM}=${universe.id}`)
          return
        }
        chooseUniverse(universe.id)
        setOpening(null)
        toast.success(`You enter ${universe.name}`)
        void navigate({ to })
      },
      onError: (error) => {
        setOpening(null)
        toast.error(error.message)
      },
    })
  }
  return { enter, opening }
}

import { useEffect } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { onTeamView } from './teamSignals'

export function TeamViewOpener() {
  const navigate = useNavigate()
  useEffect(
    () =>
      onTeamView((view) => {
        if (view === 'team') void navigate({ to: '/team' })
      }),
    [navigate]
  )
  return null
}

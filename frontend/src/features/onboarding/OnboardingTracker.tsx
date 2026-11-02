import { useEffect } from 'react'
import { useNavigate, useRouterState } from '@tanstack/react-router'
import { useWorldState } from '@/features/overview/api'
import { stepForLocation, useOnboarding } from './onboardingStore'

const FIRST_EPOCH = 1
const WORLDLESS_PATHS = ['/settings', '/design']

export function OnboardingTracker() {
  const mark = useOnboarding((state) => state.mark)
  const navigate = useNavigate()
  const state = useWorldState()
  const location = useRouterState({ select: (router) => router.location })
  const drawer = (location.search as { drawer?: string }).drawer

  useEffect(() => {
    const step = stepForLocation(location.pathname, drawer)
    if (step) mark(step)
  }, [drawer, location.pathname, mark])

  const epoch = state.data?.world?.epoch ?? 0
  useEffect(() => {
    if (epoch > FIRST_EPOCH) mark('epoch')
  }, [epoch, mark])

  const noWorld = state.isSuccess && state.data.world === null
  const exempt = WORLDLESS_PATHS.some((path) =>
    location.pathname.startsWith(path)
  )
  useEffect(() => {
    if (noWorld && !exempt) void navigate({ to: '/genesis' })
  }, [exempt, navigate, noWorld])

  return null
}

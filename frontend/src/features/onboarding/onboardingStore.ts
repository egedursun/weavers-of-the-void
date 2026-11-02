import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

export const ONBOARDING_STEPS = [
  'son',
  'map',
  'prayers',
  'chronicle',
  'rules',
  'epoch',
] as const

export type OnboardingStep = (typeof ONBOARDING_STEPS)[number]

export const ONBOARDING_HIDE_AFTER_EPOCH = 3

type OnboardingStore = {
  done: OnboardingStep[]
  dismissed: boolean
  mark: (step: OnboardingStep) => void
  dismiss: () => void
  reopen: () => void
}

export const useOnboarding = create<OnboardingStore>()(
  persist(
    (set) => ({
      done: [],
      dismissed: false,
      mark: (step) =>
        set((state) =>
          state.done.includes(step) ? state : { done: [...state.done, step] }
        ),
      dismiss: () => set({ dismissed: true }),
      reopen: () => set({ dismissed: false }),
    }),
    {
      name: 'aerona.onboarding',
      storage: createJSONStorage(() => localStorage),
    }
  )
)

export function stepForLocation(
  pathname: string,
  drawer: string | undefined
): OnboardingStep | null {
  if (drawer?.split(',').some((entry) => entry.startsWith('son:'))) return 'son'
  if (pathname.startsWith('/map')) return 'map'
  if (pathname.startsWith('/prayers')) return 'prayers'
  if (pathname.startsWith('/chronicle')) return 'chronicle'
  if (pathname.startsWith('/settings/world-rules')) return 'rules'
  return null
}

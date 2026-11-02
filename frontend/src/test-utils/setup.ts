import { afterEach } from 'vitest'
import { installNetworkGuard, takeNetworkViolations } from './networkGuard'

installNetworkGuard()

afterEach(() => {
  const violations = takeNetworkViolations()
  if (violations.length > 0)
    throw new Error(
      `The test reached the real network: ${violations.join(', ')}. Mock it with renderScreen routes or createFakeClient.`
    )
})

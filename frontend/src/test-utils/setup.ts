import { afterEach } from 'vitest'
import { installNestingGuard, takeNestingViolations } from './domNesting'
import { installNetworkGuard, takeNetworkViolations } from './networkGuard'

installNetworkGuard()
installNestingGuard()

afterEach(() => {
  const violations = takeNetworkViolations()
  if (violations.length > 0)
    throw new Error(
      `The test reached the real network: ${violations.join(', ')}. Mock it with renderScreen routes or createFakeClient.`
    )
  const nesting = takeNestingViolations()
  if (nesting.length > 0)
    throw new Error(`The screen rendered invalid HTML nesting: ${nesting[0]}`)
})

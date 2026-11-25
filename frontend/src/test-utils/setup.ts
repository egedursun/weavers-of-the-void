import { afterEach, beforeEach } from 'vitest'
import { viewerExit } from '@/api/viewerExit'
import { chooseWorkspace, forgetLastWorkspace } from '@/api/workspaceStore'
import { installNestingGuard, takeNestingViolations } from './domNesting'
import { installNetworkGuard, takeNetworkViolations } from './networkGuard'

installNetworkGuard()
installNestingGuard()
viewerExit.reload = () => undefined

beforeEach(() => {
  chooseWorkspace(null)
  forgetLastWorkspace()
})

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

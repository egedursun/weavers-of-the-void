import { setAccountScope } from './accountScope'
import { dropEveryQueryClient } from './queryClients'
import {
  chooseUniverse,
  forgetUniverse,
  lastUniverse,
  releaseDocument,
} from './universeStore'
import { chooseWorkspace, forgetLastWorkspace } from './workspaceStore'

export const viewerExit = {
  reload: () => window.location.reload(),
}

export function forgetViewer(): void {
  dropEveryQueryClient()
  const last = lastUniverse()
  if (last !== null) forgetUniverse(last)
  chooseUniverse(null)
  chooseWorkspace(null)
  forgetLastWorkspace()
  releaseDocument()
  setAccountScope(null)
  viewerExit.reload()
}

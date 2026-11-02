import { type SettingsPatch, type WorldSettings } from './api'

export type Draft = {
  fateAuto: boolean
  distribution: WorldSettings['son_distribution']
  council: string
  automaticMortals: boolean
  mortals: string
  parallelism: string
}

export function draftOf(settings: WorldSettings): Draft {
  return {
    fateAuto: settings.fate_mode === 'auto',
    distribution: settings.son_distribution,
    council: String(settings.council_every_epochs ?? ''),
    automaticMortals: settings.mortal_agents_per_epoch === null,
    mortals: String(settings.mortal_agents_per_epoch ?? ''),
    parallelism: String(settings.mortal_agent_parallelism ?? ''),
  }
}

function wholeOrNull(text: string): number | null {
  if (text.trim() === '') return null
  const value = Number(text)
  return Number.isInteger(value) ? value : Number.NaN
}

export function patchFrom(
  settings: WorldSettings,
  draft: Draft
): SettingsPatch | string {
  const council = wholeOrNull(draft.council)
  const mortals = wholeOrNull(draft.mortals)
  const parallelism = wholeOrNull(draft.parallelism)
  if ([council, mortals, parallelism].some((value) => Number.isNaN(value)))
    return 'Use whole numbers only.'
  const patch: SettingsPatch = { automatic_mortal_agents: false }
  const fate = draft.fateAuto ? 'auto' : 'off'
  if (fate !== settings.fate_mode) patch.fate_mode = fate
  if (draft.distribution !== settings.son_distribution)
    patch.son_distribution = draft.distribution
  if (council !== null && council !== settings.council_every_epochs)
    patch.council_every_epochs = council
  if (draft.automaticMortals) {
    if (settings.mortal_agents_per_epoch !== null)
      patch.automatic_mortal_agents = true
  } else if (mortals !== null && mortals !== settings.mortal_agents_per_epoch)
    patch.mortal_agents_per_epoch = mortals
  if (parallelism !== null && parallelism !== settings.mortal_agent_parallelism)
    patch.mortal_agent_parallelism = parallelism
  const changed = patch.automatic_mortal_agents || Object.keys(patch).length > 1
  return changed ? patch : 'Nothing has changed.'
}

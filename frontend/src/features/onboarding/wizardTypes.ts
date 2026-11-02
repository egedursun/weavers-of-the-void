import { type WizardOptions } from './api'
import { type WizardDraft } from './wizardModel'

export type StepProps = {
  draft: WizardDraft
  update: (next: Partial<WizardDraft>) => void
  options: WizardOptions
  peoplesMax: number
}

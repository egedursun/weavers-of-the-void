import type { components } from '@/api/generated/schema'

type Schema = components['schemas']

export const CONURBATION_GOVERNANCE: Record<
  Schema['ConurbationGovernance'],
  string
> = {
  one_council: 'one council',
  federated_councils: 'councils joined in federation',
  ruled_by_core: 'the rule of its core',
}

import type { components } from '@/api/generated/schema'

type Schema = components['schemas']

export const CAMPAIGN_STAGE: Record<Schema['CampaignStage'], string> = {
  gathering: 'Gathering',
  transit: 'Crossing',
  supremacy: 'Fighting for the space around the world',
  landing: 'Landing',
  holding: 'Holding the land',
  withdrawn: 'Withdrawn',
}

export const MIGRATION_CAUSE: Record<Schema['MigrationCause'], string> = {
  flight: 'Flight',
  land_hunger: 'Hunger for land',
  faith_call: 'The call of a faith',
  exile: 'Exile',
  labour_draw: 'The draw of work',
  world_dying: 'A dying world',
  resettlement: 'Resettlement',
}

export const MIGRATION_RECEPTION: Record<Schema['MigrationReception'], string> =
  {
    welcome: 'welcomed',
    quota: 'let in by quota',
    refusal: 'refused',
  }

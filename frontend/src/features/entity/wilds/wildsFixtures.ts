import { onApi } from '@/test-utils/fakeApi'

export const LAND = { id: 30, kind: 'entity', name: 'Saltreach' }
export const KIN = { id: 40, kind: 'entity', name: 'Dune Hare' }
export const FOLK = { id: 50, kind: 'entity', name: 'Reed Folk' }
export const KIND = { id: 7, kind: 'entity', name: 'Sand Crawler' }

export const SPECIES = {
  species_id: 7,
  world_id: 1,
  body_plan: 'quadruped',
  size_class: 'small',
  lifespan_years: 6,
  maturity_years: 1,
  litter_size: 5,
  breeding_seasons: 2,
  diet: 'omnivore',
  metabolism: 65,
  habitat: { desert: 100 },
  temperature_min: 48,
  temperature_max: 78,
  water_need: 50,
  altitude_min: 0,
  altitude_max: 1523,
  nocturnal: false,
  migratory: false,
  migration_path: [],
  aggression: 65,
  territoriality: 47,
  sociality: 'herd',
  cunning: 67,
  fear_of_people: 45,
  tameability: 60,
  stage: 'wild',
  domesticated_from: null,
  sacred_to: null,
  traits: ['mind_reader', 'stoneskin'],
  uses: ['food', 'companion'],
  yields: [
    {
      product: 'meat',
      commodity: 'livestock',
      material: null,
      world_material_id: null,
      world_material: null,
      rate: 2,
    },
  ],
  hosts: [],
  ranges: [
    {
      region: LAND,
      abundance: 68,
      trend: 'falling',
      fit: 76,
      hunted: 1,
      since_epoch: 50,
      locked: [],
    },
  ],
  herds: [
    {
      community: FOLK,
      species: null,
      head: 11,
      stage: 'tamed',
      since_epoch: 50,
      fed_epochs: 1,
      locked: [],
    },
  ],
  hunts: [KIN],
  hunted_by: [],
  descendants: [],
  beasts: [],
  pinned_prey: [],
  barred_prey: [],
  custom_uses: [],
  totem_of: [],
  abundance: 68,
  stage_epoch: 0,
  locked: ['diet'],
}

export const BEAST = {
  beast_id: 9,
  species: KIND,
  endurance: 72,
  perception: 55,
  willpower: 64,
  intelligence: 38,
  age: 140,
  lifespan: 400,
  size_class: 'huge',
  lair: LAND,
  temper: 'territorial',
  bound_to: null,
  hoard: { luxuries: 40 },
  raids: 7,
  woke_epoch: 44,
  terror: 78,
  renown: 62,
  wounds: [{ by: FOLK, epoch: 48 }],
  injuries: [
    {
      part: 'left_foreleg',
      kind: 'deep_cut',
      severity: 60,
      state: 'healing',
      function_loss: 30,
    },
  ],
  body_plan: 'quadruped',
  hp: 320,
  treasures: [],
  tributes: [],
  reach: 3,
  harm_taken_pct: 64,
  wake_pct: 76,
  tame_pct: 49,
  rest_pct: 20,
  rideable: true,
  locked: ['temper'],
}

export function serveBasics() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 51 },
  })
  onApi('GET', '/api/names', [])
  onApi('GET', '/api/sons', [])
}

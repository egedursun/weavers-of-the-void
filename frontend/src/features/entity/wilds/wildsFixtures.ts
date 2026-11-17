import { onApi } from '@/test-utils/fakeApi'

export const LAND = { id: 30, kind: 'entity', name: 'Saltreach' }
export const KIN = { id: 40, kind: 'entity', name: 'Dune Hare' }
export const FOLK = { id: 50, kind: 'entity', name: 'Reed Folk' }
export const KIND = { id: 7, kind: 'entity', name: 'Sand Crawler' }

export const SPECIES = {
  species_id: 7,
  world_id: 1,
  species_class: 'animal',
  biochemistry: 'carbon_water',
  bearable: true,
  plant: null,
  sown_in: [],
  pests: [],
  pest_of: [],
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
  uses: ['meat', 'companion'],
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
      training: null,
      trained: 0,
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
  pet_of: null,
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
  onApi('GET', '/api/nodes/7/anatomy', ANATOMY)
  onApi('GET', '/api/nodes/9/anatomy', { ...ANATOMY, node_id: 9 })
}

export const ANATOMY = {
  node_id: 7,
  limbs: 6,
  heads: 2,
  wings: 0,
  tails: 1,
  skin: 'plates',
  bone: 'rigid',
  bite: null,
  temperament: 'seizes_prey',
  hoards: 'gold',
  hates: 'fire',
  awakening: 'deep_mining',
  habitat: 'deep',
  armour_pct: 35,
  harm_pct: 70,
  generated_epoch: 3,
  locked: [],
}

export const FIELD = { id: 31, kind: 'entity', name: 'Barley Downs' }
export const MOTH = { id: 41, kind: 'entity', name: 'Grain Moth' }

export const PLANT = {
  ...SPECIES,
  species_id: 8,
  species_class: 'plant',
  diet: 'photosynthetic',
  body_plan: 'arboreal',
  uses: [],
  yields: [
    {
      product: 'grain',
      commodity: 'grain',
      material: null,
      world_material_id: null,
      world_material: null,
      rate: 2,
    },
  ],
  herds: [],
  hunts: [],
  traits: [],
  locked: [],
  plant: {
    growth_cycle: 'annual',
    growing_seasons: 1,
    soil_need: 30,
    cultivation: 'cultivated',
    cultivar_of: null,
    since_epoch: 3,
    locked: [],
  },
  sown_in: [{ region: FIELD, share: 60, fit: 82, since_epoch: 3, locked: [] }],
  pests: [MOTH],
}

export const CROPS = {
  region_id: 31,
  world_id: 1,
  harvest_pct: 91,
  crop_cap: 6,
  crops: [
    {
      plant: { id: 8, kind: 'entity', name: 'Downs Barley' },
      share: 60,
      fit: 82,
      cultivation: 'cultivated',
      products: ['grain', 'fibre'],
      pests: [MOTH],
      since_epoch: 3,
      locked: ['share'],
    },
  ],
}

export const LIFE = {
  world_id: 1,
  kinds: [
    {
      biochemistry: 'carbon_water',
      label: 'Carbon and water',
      borne: true,
      anywhere: false,
      kinds: 3,
    },
    {
      biochemistry: 'silicon',
      label: 'Silicon',
      borne: false,
      anywhere: false,
      kinds: 0,
    },
    {
      biochemistry: 'spirit',
      label: 'Spirit',
      borne: false,
      anywhere: true,
      kinds: 1,
    },
  ],
}

export const OWNER = { id: 60, kind: 'entity', name: 'Tilla' }
export const HOUND = { id: 61, kind: 'entity', name: 'Grey of Tilla' }

export const PETS = {
  mortal_id: 60,
  pets: [
    {
      pet: HOUND,
      species: KIND,
      size_class: 'small',
      age: 3,
      lifespan: 6,
      hunts: true,
      since_epoch: 4,
    },
  ],
  kinds: [KIND],
  other_kinds: [KIN],
}

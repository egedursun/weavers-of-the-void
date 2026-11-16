import {
  SprayCan,
  Sprout,
  Dna,
  Cpu,
  Moon,
  Accessibility,
  BatteryLow,
  CircleDot,
  Droplet,
  Layers,
  ScanSearch,
  Unplug,
  Activity,
  Angry,
  Axe,
  Baby,
  Bandage,
  Biohazard,
  Bird,
  Bone,
  BookOpen,
  Bot,
  Bug,
  Cloud,
  Crosshair,
  Crown,
  Drumstick,
  Ear,
  EarOff,
  Eclipse,
  Eye,
  EyeOff,
  Feather,
  Fish,
  Flame,
  Footprints,
  Frown,
  Ghost,
  Hammer,
  Hand,
  HandHeart,
  HeartPulse,
  Hourglass,
  MicOff,
  PersonStanding,
  Pill,
  Scissors,
  Shell,
  ShieldHalf,
  Skull,
  Snowflake,
  Sparkles,
  Speech,
  Star,
  Stethoscope,
  Sun,
  Swords,
  Syringe,
  Target,
  TreeDeciduous,
  Utensils,
  Wind,
  Worm,
  Zap,
  Brain,
  Bomb,
  FlaskConical,
  Radiation,
  BrainCircuit,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { MATERIAL_LABEL } from '../economy/labels'
import { type Named, named, plain } from '../environment/labels'

export { named, plain }

export const PLANS: Record<string, Named> = {
  humanoid: { label: 'Humanoid', icon: PersonStanding, tone: 'gold' },
  quadruped: { label: 'Four-legged', icon: Footprints, tone: 'success' },
  avian: { label: 'Winged', icon: Bird, tone: 'info' },
  serpentine: { label: 'Serpentine', icon: Worm, tone: 'verdigris' },
  insectoid: { label: 'Insectoid', icon: Bug, tone: 'warning' },
  aquatic: { label: 'Aquatic', icon: Fish, tone: 'info' },
  amorphous: { label: 'Amorphous', icon: Shell, tone: 'verdigris' },
  arboreal: { label: 'Tree-bodied', icon: TreeDeciduous, tone: 'success' },
  incorporeal: { label: 'Incorporeal', icon: Ghost, tone: 'muted' },
  colossal: { label: 'Colossal', icon: Accessibility, tone: 'warning' },
  construct: { label: 'Construct', icon: Bot, tone: 'muted' },
  divine_manifest: {
    label: 'Divine manifestation',
    icon: Sparkles,
    tone: 'gold',
  },
}

export const FUNCTIONS: Record<string, Named> = {
  grasp: { label: 'Grasp', icon: Hand },
  fine_manipulation: { label: 'Fingers', icon: Hand, tone: 'verdigris' },
  locomotion: { label: 'Walking', icon: Footprints, tone: 'success' },
  sight: { label: 'Sight', icon: Eye, tone: 'info' },
  hearing: { label: 'Hearing', icon: Ear, tone: 'info' },
  speech: { label: 'Speech', icon: Speech, tone: 'gold' },
  breath: { label: 'Breath', icon: Wind, tone: 'info' },
  vital: { label: 'Vital organs', icon: HeartPulse, tone: 'danger' },
  cognition: { label: 'Mind', icon: Brain, tone: 'verdigris' },
  reproduction: { label: 'Reproduction', icon: Baby, tone: 'success' },
  flight: { label: 'Flight', icon: Feather, tone: 'info' },
  venom: { label: 'Venom', icon: Syringe, tone: 'warning' },
  horn: { label: 'Horn', icon: Target, tone: 'warning' },
  tail: { label: 'Tail', icon: Worm },
  presence: { label: 'Presence', icon: Crown, tone: 'gold' },
}

export const CAPACITIES: Record<
  string,
  Named & { hint: string; base: string }
> = {
  melee: {
    label: 'Melee',
    icon: Swords,
    tone: 'danger',
    base: 'strength',
    hint: 'Strength through the weapon hand, the legs and the eyes, dulled by pain. Duels, hunts, commanders and war strength read it.',
  },
  missile: {
    label: 'Missile',
    icon: Crosshair,
    tone: 'warning',
    base: 'agility',
    hint: 'Agility through sight and the fingers. Seizing treasures reads it.',
  },
  command: {
    label: 'Command',
    icon: Crown,
    tone: 'gold',
    base: 'intellect and charisma',
    hint: 'Orders need speech, sight, hearing and a clear mind. Commanders, army morale and veterans read it.',
  },
  craft: {
    label: 'Craft',
    icon: Hammer,
    tone: 'verdigris',
    base: 'intellect',
    hint: 'Hands, fingers, sight and mind. Making items, works and prostheses read it.',
  },
  scholarship: {
    label: 'Scholarship',
    icon: BookOpen,
    tone: 'info',
    base: 'intellect',
    hint: 'Reading needs sight; a blind scholar needs an apprentice to read aloud. Wits, sensing hidden roads and teaching read it.',
  },
  presence: {
    label: 'Presence',
    icon: Sparkles,
    tone: 'gold',
    base: 'charisma',
    hint: 'The face and voice, read through what their people make of scars. Preaching reads it.',
  },
  mobility: {
    label: 'Mobility',
    icon: Footprints,
    tone: 'success',
    base: 'agility',
    hint: 'Legs or wings, breath and vital organs. Escapes, quests, exploring and duels read it.',
  },
  fertility: {
    label: 'Fertility',
    icon: Baby,
    tone: 'success',
    base: 'age',
    hint: 'Reproductive organs and age. Couples bear children by it.',
  },
}

export const INJURIES: Record<components['schemas']['InjuryKind'], Named> = {
  bruise: { label: 'Bruise', icon: Bandage, tone: 'muted' },
  cut: { label: 'Cut', icon: Scissors, tone: 'warning' },
  deep_cut: { label: 'Deep cut', icon: Axe, tone: 'danger' },
  puncture: { label: 'Piercing wound', icon: Target, tone: 'danger' },
  fracture: { label: 'Broken bone', icon: Bone, tone: 'warning' },
  crush: { label: 'Crushed', icon: Hammer, tone: 'danger' },
  burn: { label: 'Burns', icon: Flame, tone: 'warning' },
  frostbite: { label: 'Frostbite', icon: Snowflake, tone: 'info' },
  bite: { label: 'Bite', icon: Drumstick, tone: 'danger' },
  venom: { label: 'Venom', icon: Syringe, tone: 'verdigris' },
  severed: { label: 'Severed', icon: Axe, tone: 'danger' },
  gouged: { label: 'Gouged out', icon: EyeOff, tone: 'danger' },
  destroyed: { label: 'Ruined', icon: Skull, tone: 'danger' },
  curse_wither: {
    label: 'Withered by a curse',
    icon: Sparkles,
    tone: 'verdigris',
  },
  void_touch: { label: 'Touched by the void', icon: Eclipse, tone: 'danger' },
  divine_brand: { label: 'Divine brand', icon: Sun, tone: 'gold' },
  sickness: { label: 'Ravaged by sickness', icon: Biohazard, tone: 'danger' },
  gunshot: { label: 'Gunshot wound', icon: Target, tone: 'danger' },
  shrapnel: { label: 'Shrapnel', icon: Bomb, tone: 'danger' },
  concussion: { label: 'Concussion', icon: Brain, tone: 'warning' },
  electrical_burn: { label: 'Electrical burn', icon: Zap, tone: 'warning' },
  chemical_burn: {
    label: 'Chemical burn',
    icon: FlaskConical,
    tone: 'warning',
  },
  radiation_sickness: {
    label: 'Radiation sickness',
    icon: Radiation,
    tone: 'danger',
  },
  mind_scar: {
    label: 'Scar on the mind',
    icon: BrainCircuit,
    tone: 'verdigris',
  },
}

export const STATES: Record<string, Named & { badge: BadgeTone }> = {
  fresh: { label: 'Fresh', icon: Bandage, tone: 'warning', badge: 'warning' },
  infected: {
    label: 'Festering',
    icon: Biohazard,
    tone: 'danger',
    badge: 'destructive',
  },
  healing: { label: 'Healing', icon: Activity, tone: 'info', badge: 'info' },
  healed_scar: {
    label: 'Healed scar',
    icon: Bandage,
    tone: 'success',
    badge: 'success',
  },
  permanent: {
    label: 'For life',
    icon: Hourglass,
    tone: 'muted',
    badge: 'secondary',
  },
  lethal: { label: 'Fatal', icon: Skull, tone: 'danger', badge: 'destructive' },
}

export type BadgeTone =
  'secondary' | 'info' | 'success' | 'warning' | 'destructive' | 'default'

export const DAMAGE: Record<components['schemas']['DamageType'], string> = {
  cut: 'Blade',
  pierce: 'Point',
  blunt: 'Blunt',
  fire: 'Fire',
  cold: 'Cold',
  venom: 'Venom',
  magic: 'Magic',
  void: 'Void',
  holy: 'Holy',
  ballistic: 'Ballistic',
  explosive: 'Blast',
  energy: 'Energy',
  electric: 'Electric',
  radiation: 'Radiation',
  chemical: 'Chemical',
  sonic: 'Sonic',
  psychic: 'Psychic',
}

export const CAUSES: Record<components['schemas']['HarmCause'], string> = {
  battle: 'Battle',
  duel: 'Duel',
  punishment: 'Punishment',
  torture: 'Torture',
  accident: 'Accident',
  monster: 'A beast',
  disaster: 'Disaster',
  curse: 'Curse',
  magic_backlash: 'Magic backlash',
  god: 'A god',
  poison: 'Poison',
  quest: 'A quest',
  escape: 'An escape',
  sacrifice: 'Sacrifice',
  age: 'Age',
  player: 'Your hand',
  exposure: 'Exposure',
  ritual: 'A rite',
  bombardment: 'Bombardment',
  industrial: 'Industrial accident',
  crash: 'A crash',
  radiation: 'Radiation',
  decompression: 'Decompression',
  experiment: 'An experiment',
  power: 'A power',
}

export const CONDITIONS: Record<string, Named> = {
  chronic_illness: { label: 'Lingering illness', icon: Pill, tone: 'warning' },
  paranoia: { label: 'Paranoia', icon: Eye, tone: 'verdigris' },
  visions: { label: 'Visions', icon: Sparkles, tone: 'verdigris' },
  rage: { label: 'Fits of rage', icon: Angry, tone: 'danger' },
  melancholy: { label: 'Melancholy', icon: Cloud, tone: 'info' },
  addiction: { label: 'Addiction', icon: Pill, tone: 'danger' },
  age_blindness: { label: 'Blind with age', icon: EyeOff, tone: 'muted' },
  age_deafness: { label: 'Deaf with age', icon: EarOff, tone: 'muted' },
  withered_limb: { label: 'Withered limb', icon: Sparkles, tone: 'verdigris' },
  endless_hunger: { label: 'Endless hunger', icon: Utensils, tone: 'danger' },
  possession: { label: 'Possessed', icon: Ghost, tone: 'verdigris' },
  void_taint: { label: 'Void taint', icon: Eclipse, tone: 'danger' },
  chosen_mark: { label: 'Mark of the chosen', icon: Star, tone: 'gold' },
  divine_brand: { label: "A god's brand", icon: Sun, tone: 'gold' },
  nightmares: { label: 'Recurring nightmares', icon: Moon, tone: 'verdigris' },
  comatose: { label: 'Comatose', icon: EyeOff, tone: 'muted' },
  cognitive_decline: { label: 'Failing mind', icon: Brain, tone: 'warning' },
  malnutrition: {
    label: 'Wasted by a poor diet',
    icon: Utensils,
    tone: 'warning',
  },
}

export const MEDICINE: Record<
  components['schemas']['MedicineTier'],
  Named & { hint: string }
> = {
  none: {
    label: 'No medicine',
    icon: Frown,
    tone: 'muted',
    hint: 'Wounds are left to fate.',
  },
  herbs: {
    label: 'Herbal remedies',
    icon: Pill,
    tone: 'success',
    hint: 'Herbs keep wounds from festering.',
  },
  surgery: {
    label: 'Surgery',
    icon: Scissors,
    tone: 'info',
    hint: 'A festering limb is cut away instead of a life lost.',
  },
  prosthetics: {
    label: 'Prosthetics',
    icon: Hand,
    tone: 'gold',
    hint: 'Lost limbs and eyes are replaced.',
  },
  reattachment: {
    label: 'Reattachment',
    icon: Zap,
    tone: 'verdigris',
    hint: 'Lost parts can be made whole again.',
  },
  antisepsis: {
    label: 'Antisepsis',
    icon: SprayCan,
    tone: 'info',
    hint: 'Clean hands and tools keep wounds from festering.',
  },
  anaesthesia: {
    label: 'Anaesthesia',
    icon: Moon,
    tone: 'info',
    hint: 'Deep cuts can be made without the shock that kills.',
  },
  immunisation: {
    label: 'Immunisation',
    icon: Syringe,
    tone: 'success',
    hint: 'Folk are guarded against sicknesses before they come.',
  },
  antimicrobials: {
    label: 'Antimicrobials',
    icon: Pill,
    tone: 'success',
    hint: 'Festering and plague can be driven out of the body.',
  },
  transplantation: {
    label: 'Transplantation',
    icon: HeartPulse,
    tone: 'gold',
    hint: 'Failed organs can be replaced from another body.',
  },
  mind_medicine: {
    label: 'Medicine of the mind',
    icon: Brain,
    tone: 'verdigris',
    hint: 'Harm to the mind is treated and heals faster.',
  },
  regeneration: {
    label: 'Regeneration',
    icon: Sprout,
    tone: 'verdigris',
    hint: 'The body regrows what it lost.',
  },
  genome_repair: {
    label: 'Genome repair',
    icon: Dna,
    tone: 'gold',
    hint: 'Flaws carried in the blood are mended.',
  },
  cellular_machines: {
    label: 'Cellular machines',
    icon: Cpu,
    tone: 'gold',
    hint: 'Minute machines repair the body from within.',
  },
}

export const READINGS: Record<string, Named & { hint: string }> = {
  neutral: {
    label: 'Pity for the maimed',
    icon: HandHeart,
    tone: 'muted',
    hint: 'Missing parts lower presence a little.',
  },
  martial_honour: {
    label: 'Honour in scars',
    icon: Swords,
    tone: 'gold',
    hint: 'Battle scars raise presence; the marks of punishment lower it.',
  },
  purity: {
    label: 'Purity of body',
    icon: Sun,
    tone: 'info',
    hint: 'Visible wounds and missing parts lower presence; a whole body may be required to rule.',
  },
  sanctified_suffering: {
    label: 'Sanctified suffering',
    icon: Flame,
    tone: 'verdigris',
    hint: 'Scars and suffering raise presence; cults of suffering take in the maimed.',
  },
}

export const MAIMED: Record<string, Named> = {
  one_armed: { label: 'One-armed', icon: Hand, tone: 'warning' },
  one_legged: { label: 'One-legged', icon: Footprints, tone: 'warning' },
  one_eyed: { label: 'One-eyed', icon: EyeOff, tone: 'warning' },
  blind: { label: 'Blind', icon: EyeOff, tone: 'danger' },
  deaf: { label: 'Deaf', icon: EarOff, tone: 'info' },
  mute: { label: 'Mute', icon: MicOff, tone: 'info' },
  lame: { label: 'Lame', icon: Accessibility, tone: 'warning' },
  scarred: { label: 'Disfigured', icon: Bandage, tone: 'muted' },
  broken_minded: { label: 'Broken in mind', icon: Brain, tone: 'verdigris' },
}

export const MATERIALS: Record<string, string> = MATERIAL_LABEL

export const REGIONS: Record<string, string> = {
  head: 'Head',
  torso: 'Torso',
  arms: 'Arms',
  legs: 'Legs',
  wings: 'Wings',
  tail: 'Tail',
}

export const BODY_VALUES: Record<string, string> = {
  armour_head: 'Head armour',
  armour_torso: 'Body armour',
  armour_limbs: 'Limb armour',
  pain: 'Pain',
  fingers: 'Fingers',
  toes: 'Toes',
  teeth: 'Teeth',
  blood: 'Blood',
  exertion: 'Exertion',
  consciousness: 'Consciousness',
  hp_max: 'Health ceiling',
}

export const HEALER_ICON = Stethoscope
export const ARMOUR_ICON = ShieldHalf

export function bodyValueLabel(key: string): string {
  return CAPACITIES[key]?.label ?? BODY_VALUES[key] ?? plain({}, key)
}

export const HEIGHTS: Record<string, string> = {
  short: 'Short',
  average: 'Of middling height',
  tall: 'Tall',
  giant: 'Giant',
}

export const BUILDS: Record<string, string> = {
  slight: 'Slight',
  average: 'Middling',
  heavy: 'Heavy',
  giant: 'Giant',
}

export const TISSUES: Record<string, Named> = {
  skin: { label: 'Skin', icon: Layers, tone: 'muted' },
  scale: { label: 'Scales', icon: Shell, tone: 'verdigris' },
  chitin: { label: 'Chitin', icon: Bug, tone: 'verdigris' },
  bark: { label: 'Bark', icon: TreeDeciduous, tone: 'success' },
  fat: { label: 'Fat', icon: Layers, tone: 'muted' },
  muscle: { label: 'Muscle', icon: Activity, tone: 'warning' },
  tendon: { label: 'Tendons and ligaments', icon: Unplug, tone: 'warning' },
  bone: { label: 'Bone', icon: Bone, tone: 'warning' },
  artery: { label: 'Artery', icon: Droplet, tone: 'danger' },
  motor_nerve: { label: 'Motor nerve', icon: Zap, tone: 'danger' },
  sensory_nerve: { label: 'Sensory nerve', icon: Zap, tone: 'info' },
  organ: { label: 'Organ', icon: HeartPulse, tone: 'danger' },
}

export const NERVES: Record<string, Named> = {
  none: { label: 'Nerves whole', icon: Zap, tone: 'success' },
  motor: { label: 'Limp: motor nerve cut', icon: Zap, tone: 'danger' },
  sensory: { label: 'Numb: sensory nerve cut', icon: Zap, tone: 'info' },
}

export const CONSCIOUSNESS: Record<string, Named & { hint: string }> = {
  awake: {
    label: 'Awake',
    icon: Eye,
    tone: 'success',
    hint: 'Clear-headed and able to act.',
  },
  nauseous: {
    label: 'Nauseous',
    icon: Frown,
    tone: 'warning',
    hint: 'Pain churns the stomach; fine work and command suffer.',
  },
  dizzy: {
    label: 'Dizzy',
    icon: CircleDot,
    tone: 'warning',
    hint: 'The world spins; every capacity falls away.',
  },
  unconscious: {
    label: 'Unconscious',
    icon: EyeOff,
    tone: 'danger',
    hint: 'Senseless: cannot act and is captured if foes find them.',
  },
}

export const TREATMENTS: Record<string, Named> = {
  diagnose: { label: 'Diagnose', icon: ScanSearch, tone: 'info' },
  clean: { label: 'Clean', icon: Droplet, tone: 'info' },
  suture: { label: 'Suture', icon: Scissors, tone: 'warning' },
  set_bone: { label: 'Set the bone', icon: Bone, tone: 'warning' },
  splint: { label: 'Splint', icon: Hammer, tone: 'warning' },
  dress: { label: 'Dress', icon: Bandage, tone: 'info' },
  amputate: { label: 'Amputate', icon: Axe, tone: 'danger' },
  cauterise: { label: 'Cauterise', icon: Flame, tone: 'danger' },
  crutch: { label: 'Crutch', icon: Accessibility, tone: 'muted' },
  traction: { label: 'Traction', icon: Footprints, tone: 'muted' },
}

export const BLOOD_ICON = Droplet
export const EXERTION_ICON = BatteryLow

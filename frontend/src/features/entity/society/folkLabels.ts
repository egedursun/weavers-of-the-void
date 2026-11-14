import {
  Anchor,
  Bird,
  Bone,
  Bot,
  Bug,
  Church,
  Cloud,
  Crown,
  Droplet,
  Droplets,
  Ear,
  Eye,
  Feather,
  Fish,
  Flame,
  Gem,
  Ghost,
  HeartPulse,
  Landmark,
  Mountain,
  Network,
  PawPrint,
  PersonStanding,
  Ruler,
  Scaling,
  ScrollText,
  Shell,
  Shield,
  ShieldPlus,
  Shovel,
  Skull,
  Snail,
  Snowflake,
  Sparkles,
  Sun,
  Sunrise,
  Syringe,
  TreeDeciduous,
  Turtle,
  Utensils,
  Vegan,
  Wheat,
  type LucideIcon,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain'
import { type Spec, fieldLabel } from './labels'

type Schemas = components['schemas']
export type BodyPlan = Schemas['BodyPlan']
export type SizeClass = Schemas['SizeClass']
export type FolkDiet = Schemas['FolkDiet']
export type NaturalTrait = Schemas['NaturalTrait']
export type FuneralCustom = Schemas['FuneralCustom']

export const BODY_SPEC: Record<BodyPlan, Spec> = {
  humanoid: {
    label: 'Two-legged folk',
    icon: PersonStanding,
    tone: 'gold',
    hint: 'Ride, sail and work like any people',
  },
  quadruped: {
    label: 'Four-legged folk',
    icon: PawPrint,
    tone: 'warning',
    hint: 'Their own mounts; herders and those who plough',
  },
  avian: {
    label: 'Winged folk',
    icon: Bird,
    tone: 'info',
    hint: 'Fly over heights; poor miners and sailors',
  },
  serpentine: {
    label: 'Serpent folk',
    icon: Snail,
    tone: 'success',
    hint: 'Masters of marsh and jungle; cannot ride',
  },
  insectoid: {
    label: 'Insect folk',
    icon: Bug,
    tone: 'warning',
    hint: 'Builders and diggers who eat little',
  },
  aquatic: {
    label: 'Sea folk',
    icon: Fish,
    tone: 'info',
    hint: 'Born fishers and fleets; wither in deserts',
  },
  amorphous: {
    label: 'Shapeless folk',
    icon: Droplets,
    tone: 'verdigris',
    hint: 'Hardy against sickness; seep through caves',
  },
  arboreal: {
    label: 'Tree folk',
    icon: TreeDeciduous,
    tone: 'success',
    hint: 'Forest wrights who fight best among trees',
  },
  incorporeal: {
    label: 'Spirit folk',
    icon: Ghost,
    tone: 'verdigris',
    hint: 'Barely eat, never sicken; priests, not miners',
  },
  colossal: {
    label: 'Giant folk',
    icon: Mountain,
    tone: 'danger',
    hint: 'Raise walls and break lines; eat a world',
  },
  construct: {
    label: 'Made folk',
    icon: Bot,
    tone: 'muted',
    hint: 'Tireless miners who never fall sick',
  },
  divine_manifest: {
    label: 'God-touched folk',
    icon: Sparkles,
    tone: 'gold',
    hint: 'Born to the clergy; live on essence',
  },
}

export const SIZE_CLASS_SPEC: Record<SizeClass, Spec> = {
  tiny: { label: 'Tiny', icon: Scaling, tone: 'muted' },
  small: { label: 'Small', icon: Scaling, tone: 'info' },
  medium: { label: 'Middling', icon: Ruler, tone: 'gold' },
  large: { label: 'Large', icon: Ruler, tone: 'warning' },
  huge: { label: 'Huge', icon: Mountain, tone: 'warning' },
  colossal: { label: 'Colossal', icon: Mountain, tone: 'danger' },
}

export const DIET_SPEC: Record<FolkDiet, Spec> = {
  omnivore: {
    label: 'Eat anything',
    icon: Utensils,
    tone: 'gold',
    hint: 'Grain, herds and fish alike',
  },
  herbivore: {
    label: 'Plant eaters',
    icon: Vegan,
    tone: 'success',
    hint: 'Only the fields feed them',
  },
  carnivore: {
    label: 'Meat eaters',
    icon: Bone,
    tone: 'danger',
    hint: 'Herds and fish, never grain',
  },
  piscivore: {
    label: 'Fish eaters',
    icon: Fish,
    tone: 'info',
    hint: 'Starve far from the sea',
  },
  scavenger: {
    label: 'Scavengers',
    icon: Bone,
    tone: 'muted',
    hint: 'Anything at all, but poorly',
  },
  sanguivore: {
    label: 'Blood drinkers',
    icon: Droplet,
    tone: 'danger',
    hint: 'Live on the blood of herds',
  },
  lithovore: {
    label: 'Stone eaters',
    icon: Gem,
    tone: 'warning',
    hint: 'Ore and stone are bread to them',
  },
  essence_feeder: {
    label: 'Essence feeders',
    icon: Sparkles,
    tone: 'verdigris',
    hint: 'Fed by magic in the land and lore',
  },
  phototroph: {
    label: 'Light eaters',
    icon: Sun,
    tone: 'gold',
    hint: 'Fed by the sun; hunger in the cold',
  },
}

export const TRAIT_SPEC: Record<NaturalTrait, Spec> = {
  dark_sight: {
    label: 'Dark sight',
    icon: Eye,
    tone: 'verdigris',
    hint: 'Fight best at night, mine deeper',
  },
  cold_blooded: {
    label: 'Cold-blooded',
    icon: Turtle,
    tone: 'info',
    hint: 'Eat less; falter in snow, thrive in heat',
  },
  winged: {
    label: 'Winged',
    icon: Feather,
    tone: 'info',
    hint: 'Rule heights and rivers; fast traders',
  },
  amphibious: {
    label: 'Amphibious',
    icon: Shell,
    tone: 'info',
    hint: 'At home in marsh and river; great fishers',
  },
  thick_hide: {
    label: 'Thick hide',
    icon: Shield,
    tone: 'warning',
    hint: 'Hard to wound; bear the cold',
  },
  keen_senses: {
    label: 'Keen senses',
    icon: Ear,
    tone: 'gold',
    hint: 'Never surprised; fine herders',
  },
  venomous: {
    label: 'Venomous',
    icon: Syringe,
    tone: 'danger',
    hint: 'Every wound they give festers',
  },
  regenerating: {
    label: 'Regenerating',
    icon: HeartPulse,
    tone: 'success',
    hint: 'Heal wounds and sickness; eat more',
  },
  burrowing: {
    label: 'Burrowing',
    icon: Shovel,
    tone: 'warning',
    hint: 'Dig in to defend; need little room above',
  },
  hive_minded: {
    label: 'Hive-minded',
    icon: Network,
    tone: 'verdigris',
    hint: 'Build as one; plagues run through them',
  },
}

export const FUNERAL_SPEC: Record<FuneralCustom, Spec> = {
  burial: {
    label: 'Burial',
    icon: Shovel,
    tone: 'muted',
    hint: 'Laid in the earth',
  },
  cremation: {
    label: 'Cremation',
    icon: Flame,
    tone: 'warning',
    hint: 'Burned on pyres; little sickness, few ghosts',
  },
  sky_burial: {
    label: 'Sky burial',
    icon: Cloud,
    tone: 'info',
    hint: 'Given to the birds; corpses carry sickness',
  },
  sea_burial: {
    label: 'Sea burial',
    icon: Anchor,
    tone: 'info',
    hint: 'Given to the waters; some return restless',
  },
  entombment: {
    label: 'Entombment',
    icon: Landmark,
    tone: 'gold',
    hint: 'Sealed in tombs; ancestors watch and are mourned',
  },
  ancestor_shrine: {
    label: 'Ancestor shrines',
    icon: Church,
    tone: 'verdigris',
    hint: 'Bones kept at home; many guardian spirits',
  },
  endocannibalism: {
    label: 'The last feast',
    icon: Utensils,
    tone: 'danger',
    hint: 'They eat of their dead; sickness spreads',
  },
  reanimation: {
    label: 'Raising the dead',
    icon: Skull,
    tone: 'danger',
    hint: 'The dead march in the levy; ghosts walk',
  },
  soul_binding: {
    label: 'Soul stones',
    icon: Gem,
    tone: 'verdigris',
    hint: 'Souls bound in stone; no restless dead',
  },
}

export const MOUNT_SPEC: Record<string, Spec> = {
  rides: { label: 'Ride beasts', icon: PawPrint, tone: 'gold' },
  is_mount: { label: 'Are their own mounts', icon: PawPrint, tone: 'success' },
  flies: { label: 'Take to the air', icon: Bird, tone: 'info' },
  cannot: { label: 'Cannot ride', icon: Snowflake, tone: 'muted' },
}

export const FOLK_FIELDS: Record<string, string> = {
  body_plan: 'Body',
  size_class: 'Size',
  diet: 'Diet',
  traits: 'Natural traits',
  acclimatised: 'Home climate',
  staple: 'Staple',
  immunities: 'Immunities',
  staples: 'Staples',
  funeral_rite: 'Funeral rite',
  funeral_rite_id: 'Funeral tradition',
  liturgical_language_id: 'Tongue of prayer',
  trade_language_id: 'Tongue of trade',
  martial_record: 'Battle record',
  biochemistry: 'Body chemistry',
  air: 'Breath',
  gravity_low: 'Least gravity',
  gravity_high: 'Most gravity',
}

export const LANGUAGE_ICON: LucideIcon = ScrollText
export const TRADE_ICON: LucideIcon = Wheat
export const RECORD_ICON: LucideIcon = Crown
export const FOUND_ICON: LucideIcon = Sunrise
export const IMMUNE_ICON: LucideIcon = ShieldPlus

const PERCENT = 100

export function folkLabel(key: string): string {
  return FOLK_FIELDS[key] ?? fieldLabel(key)
}

export function effectTone(pct: number, good: 'high' | 'low'): KpiTone {
  if (pct === PERCENT) return 'muted'
  const better = good === 'high' ? pct > PERCENT : pct < PERCENT
  return better ? 'success' : 'warning'
}

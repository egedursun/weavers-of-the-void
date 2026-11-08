import {
  Anchor,
  Bird,
  Bone,
  Brain,
  Church,
  CloudFog,
  Cog,
  Droplet,
  Eclipse,
  Eye,
  Feather,
  Flame,
  Footprints,
  Gem,
  Ghost,
  Hand,
  Layers,
  MoonStar,
  Mountain,
  Orbit,
  Pickaxe,
  Search,
  Shield,
  Smile,
  Snowflake,
  Sparkles,
  Swords,
  TreeDeciduous,
  Volume2,
  Wind,
  Zap,
} from 'lucide-react'
import { type Named } from './labels'

export const TISSUE: Record<string, Named> = {
  flesh: { label: 'Flesh', icon: Hand, tone: 'muted' },
  hide: { label: 'Hide', icon: Layers, tone: 'warning' },
  scale: { label: 'Scale', icon: Shield, tone: 'verdigris' },
  chitin: { label: 'Chitin', icon: Shield, tone: 'warning' },
  feather: { label: 'Feather', icon: Feather, tone: 'info' },
  bone: { label: 'Bone', icon: Bone, tone: 'muted' },
  wood: { label: 'Wood', icon: TreeDeciduous, tone: 'success' },
  stone: { label: 'Stone', icon: Mountain, tone: 'muted' },
  crystal: { label: 'Crystal', icon: Gem, tone: 'gold' },
  metal: { label: 'Metal', icon: Cog, tone: 'info' },
  ice: { label: 'Ice', icon: Snowflake, tone: 'info' },
  fire: { label: 'Fire', icon: Flame, tone: 'danger' },
  steam: { label: 'Steam', icon: CloudFog, tone: 'muted' },
  void_stuff: { label: 'Void', icon: Eclipse, tone: 'muted' },
}

export const BREATH: Record<string, Named> = {
  fire: { label: 'Fire', icon: Flame, tone: 'danger' },
  frost: { label: 'Frost', icon: Snowflake, tone: 'info' },
  venom_gas: { label: 'Venom gas', icon: CloudFog, tone: 'success' },
  web: { label: 'Web', icon: Sparkles, tone: 'muted' },
  steam: { label: 'Steam', icon: Wind, tone: 'warning' },
}

export const BITE: Record<string, Named> = {
  snake_venom: { label: 'Venom', icon: Droplet, tone: 'success' },
  lycanthropy: { label: 'Were-curse', icon: MoonStar, tone: 'warning' },
  vampirism: { label: 'Blood-curse', icon: Droplet, tone: 'danger' },
  void_taint: { label: 'Void taint', icon: Eclipse, tone: 'muted' },
}

export const GAZE: Record<string, Named & { hint: string }> = {
  terror: {
    label: 'Terror',
    icon: Eye,
    tone: 'danger',
    hint: 'Lays stress on every mortal of a town it raids',
  },
  petrify: {
    label: 'Turns to stone',
    icon: Mountain,
    tone: 'muted',
    hint: 'Turns a limb of someone in a town it raids to stone',
  },
  sleep: {
    label: 'Sleep',
    icon: MoonStar,
    tone: 'info',
    hint: 'Lulls the watch, so its raids cut deeper',
  },
  madness: {
    label: 'Madness',
    icon: Brain,
    tone: 'verdigris',
    hint: 'Drives someone in a town it raids mad',
  },
}

export const TEMPERAMENT_KIND: Record<string, Named & { hint: string }> = {
  placid: {
    label: 'Placid',
    icon: Smile,
    tone: 'success',
    hint: 'Slow to anger',
  },
  skittish: {
    label: 'Skittish',
    icon: Footprints,
    tone: 'info',
    hint: 'Flees before it fights',
  },
  curious: {
    label: 'Curious',
    icon: Search,
    tone: 'verdigris',
    hint: 'Draws near to see',
  },
  fierce: {
    label: 'Fierce',
    icon: Swords,
    tone: 'danger',
    hint: 'Quick to attack',
  },
  cunning: {
    label: 'Cunning',
    icon: Brain,
    tone: 'gold',
    hint: 'Waits and chooses its moment',
  },
  abductor: {
    label: 'Abductor',
    icon: Ghost,
    tone: 'warning',
    hint: 'Carries people off rather than killing them',
  },
}

export const AVERSION: Record<string, Named> = {
  fire: { label: 'Fire', icon: Flame, tone: 'danger' },
  iron: { label: 'Iron', icon: Cog, tone: 'info' },
  noise: { label: 'Noise', icon: Volume2, tone: 'warning' },
  water: { label: 'Water', icon: Droplet, tone: 'info' },
  holy_ground: { label: 'Holy ground', icon: Church, tone: 'gold' },
}

export const AWAKENING: Record<string, Named & { hint: string }> = {
  deep_mining: {
    label: 'Deep mining',
    icon: Pickaxe,
    tone: 'warning',
    hint: 'Wakes when the mines of its land are dug deep',
  },
  desecration: {
    label: 'Desecration',
    icon: Zap,
    tone: 'danger',
    hint: 'Wakes when something holy in its land is desecrated',
  },
}

export const HABITAT: Record<string, Named> = {
  land: { label: 'Land', icon: Footprints, tone: 'success' },
  water: { label: 'Water', icon: Anchor, tone: 'info' },
  sky: { label: 'Sky', icon: Bird, tone: 'info' },
  deep: { label: 'The deep', icon: Pickaxe, tone: 'muted' },
  void: { label: 'The void', icon: Orbit, tone: 'muted' },
}

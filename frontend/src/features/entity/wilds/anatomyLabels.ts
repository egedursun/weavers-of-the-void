import {
  Bone,
  Anchor,
  Bird,
  Brain,
  Church,
  CloudFog,
  Cog,
  Droplet,
  Eclipse,
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
  Swords,
  TreeDeciduous,
  Volume2,
  Zap,
} from 'lucide-react'
import { type Named } from './labels'

export const TISSUE: Record<string, Named> = {
  soft_tissue: { label: 'Soft tissue', icon: Hand, tone: 'muted' },
  hide: { label: 'Hide', icon: Layers, tone: 'warning' },
  plates: { label: 'Plates', icon: Shield, tone: 'verdigris' },
  shell: { label: 'Shell', icon: Shield, tone: 'warning' },
  plumage: { label: 'Plumage', icon: Feather, tone: 'info' },
  rigid: { label: 'Rigid frame', icon: Bone, tone: 'muted' },
  fibrous: { label: 'Fibrous', icon: TreeDeciduous, tone: 'success' },
  frozen: { label: 'Frozen', icon: Snowflake, tone: 'info' },
  vapour: { label: 'Vapour', icon: CloudFog, tone: 'muted' },
  mineral: { label: 'Mineral', icon: Mountain, tone: 'muted' },
  metallic: { label: 'Metallic', icon: Cog, tone: 'info' },
  crystalline: { label: 'Crystalline', icon: Gem, tone: 'gold' },
  gel: { label: 'Gel', icon: Droplet, tone: 'success' },
  energy: { label: 'Energy', icon: Zap, tone: 'danger' },
  insubstantial: { label: 'Insubstantial', icon: Ghost, tone: 'muted' },
}

export const BITE: Record<string, Named> = {
  snake_venom: { label: 'Venom', icon: Droplet, tone: 'success' },
  lycanthropy: { label: 'Were-curse', icon: MoonStar, tone: 'warning' },
  vampirism: { label: 'Blood-curse', icon: Droplet, tone: 'danger' },
  void_taint: { label: 'Void taint', icon: Eclipse, tone: 'muted' },
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

import {
  Brain,
  CloudLightning,
  Clover,
  Crown,
  Droplet,
  Eclipse,
  Eye,
  EyeOff,
  Flame,
  FlaskConical,
  Ghost,
  Heart,
  HeartHandshake,
  Leaf,
  Lock,
  MessageCircle,
  Moon,
  ScanEye,
  Shuffle,
  Skull,
  Sparkles,
  Sun,
  Syringe,
  Utensils,
  Wine,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '../environment/labels'

export const PACKAGE_LOOKS: Record<
  components['schemas']['PackageKind'],
  Named
> = {
  snake_venom: { label: 'Venom', icon: Syringe, tone: 'verdigris' },
  drink_dependence: { label: 'Drink dependence', icon: Wine, tone: 'warning' },
  drug_dependence: { label: 'Drug dependence', icon: Leaf, tone: 'warning' },
  lycanthropy: { label: 'Beast curse', icon: Moon, tone: 'danger' },
  vampirism: { label: 'Blood curse', icon: Droplet, tone: 'danger' },
  divine_blessing: { label: 'Divine blessing', icon: Sun, tone: 'gold' },
  void_taint: { label: 'Void taint', icon: Eclipse, tone: 'danger' },
  possession: { label: 'Possession', icon: Ghost, tone: 'verdigris' },
  trauma: { label: 'Trauma', icon: Brain, tone: 'info' },
  hunger_curse: { label: 'Hunger curse', icon: Utensils, tone: 'danger' },
  warping: { label: 'Warping', icon: Sparkles, tone: 'verdigris' },
  vis_dependence: {
    label: 'Vis dependence',
    icon: FlaskConical,
    tone: 'warning',
  },
  geas_doom: { label: 'Geas doom', icon: Skull, tone: 'danger' },
  soul_trapped: { label: 'Soul trapped', icon: Ghost, tone: 'muted' },
  fortune: { label: 'Fortune', icon: Clover, tone: 'gold' },
  transformation: { label: 'Transformation', icon: Shuffle, tone: 'verdigris' },
  charm: { label: 'Charm', icon: HeartHandshake, tone: 'warning' },
}

export const TRANSMISSIONS: Record<
  components['schemas']['Transmission'],
  string
> = {
  contact: 'Touch',
  bite: 'A bite',
  ingestion: 'Eating or drinking',
  inhalation: 'Breathing it in',
  blood: 'Blood',
  curse: 'A curse',
  birth: 'Birth',
  rite: 'A rite',
  gaze: 'A gaze',
  experience: 'What they lived through',
  water: 'Water',
  spirit: 'Spirits',
  void: 'The void',
  intimate: 'Intimacy',
  objects: 'Goods and bedding',
}

export const CURES: Record<string, string> = {
  rite: 'A rite',
  technique: 'A healing technique',
  medicine: 'Medicine',
  time: 'Time',
  quest: 'A quest',
}

export const VISIBILITY: Record<
  string,
  Named & { badge: 'secondary' | 'outline' | 'warning' }
> = {
  obvious: { label: 'Plain to see', icon: Eye, badge: 'warning' },
  noticeable: {
    label: 'Noticed by those close',
    icon: ScanEye,
    badge: 'secondary',
  },
  hidden: { label: 'Hidden', icon: EyeOff, badge: 'outline' },
}

export const STAT_LABELS: Record<string, string> = {
  strength: 'Strength',
  agility: 'Agility',
  endurance: 'Endurance',
  intelligence: 'Intelligence',
  charisma: 'Charisma',
  willpower: 'Willpower',
  wisdom: 'Wisdom',
  sanity: 'Sanity',
}

export const CHANGE_SIGNS: Record<components['schemas']['ChangeSign'], Named> =
  {
    season: { label: 'Each season', icon: Leaf, tone: 'success' },
    sky_event: { label: 'A sign in the sky', icon: Moon, tone: 'info' },
    emotion: { label: 'A strong feeling', icon: Flame, tone: 'danger' },
    word: { label: 'A spoken word', icon: MessageCircle, tone: 'gold' },
    none: { label: 'Fixed for good', icon: Lock, tone: 'muted' },
  }

export const CHARMS: Record<components['schemas']['CharmKind'], Named> = {
  love: { label: 'Love', icon: Heart, tone: 'danger' },
  obedience: { label: 'Obedience', icon: Crown, tone: 'warning' },
  devotion: { label: 'Devotion', icon: Sparkles, tone: 'gold' },
}

export const FORTUNE_SIGNS: Record<string, Named> = {
  '1': { label: 'Good fortune', icon: Clover, tone: 'success' },
  '-1': { label: 'Ill fortune', icon: CloudLightning, tone: 'danger' },
}

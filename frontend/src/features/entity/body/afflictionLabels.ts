import {
  Brain,
  CircleDashed,
  CloudLightning,
  Clover,
  Crown,
  Droplet,
  Eclipse,
  Eraser,
  Eye,
  EyeOff,
  Fingerprint,
  Flame,
  FlaskConical,
  Ghost,
  Hand,
  HandHeart,
  Heart,
  HeartHandshake,
  History,
  Hourglass,
  Leaf,
  Lock,
  MessageCircle,
  Moon,
  ScanEye,
  Shuffle,
  Skull,
  Sparkles,
  Sun,
  Swords,
  Syringe,
  UserMinus,
  Utensils,
  Wine,
  Bed,
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
  possession: { label: 'Possession', icon: Eye, tone: 'verdigris' },
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
  ageing: { label: 'Ageing', icon: Hourglass, tone: 'warning' },
  forgetting: { label: 'Forgetting', icon: CircleDashed, tone: 'warning' },
  sleep: { label: 'Sleep', icon: Bed, tone: 'info' },
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
  soil: 'lying in the ground',
  sound: 'carried by a sound',
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
  marked: {
    label: 'Marked for those who know',
    icon: Fingerprint,
    badge: 'warning',
  },
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

export const FORGET_SCOPES: Record<
  components['schemas']['ForgetScope'],
  Named
> = {
  recent: { label: 'What came last', icon: History, tone: 'info' },
  person: {
    label: 'A person and all tied to them',
    icon: UserMinus,
    tone: 'warning',
  },
  skill: { label: 'What the hands knew', icon: Hand, tone: 'warning' },
  all: { label: 'A share of everything', icon: Eraser, tone: 'danger' },
}

export const SLEEP_UNTILS: Record<components['schemas']['SleepUntil'], Named> =
  {
    time: { label: 'Until its time runs out', icon: Hourglass, tone: 'info' },
    deed: { label: 'Until a deed is done', icon: Swords, tone: 'gold' },
    act: { label: 'Until one person acts', icon: HandHeart, tone: 'success' },
  }

import {
  Brain,
  Droplet,
  Eclipse,
  Eye,
  EyeOff,
  Ghost,
  Leaf,
  Moon,
  ScanEye,
  Sun,
  Syringe,
  Utensils,
  Wine,
  Sparkles,
  FlaskConical,
  Skull,
} from 'lucide-react'
import { type Named } from '../environment/labels'

export const PACKAGE_LOOKS: Record<string, Named> = {
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
}

export const TRANSMISSIONS: Record<string, string> = {
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

import {
  Angry,
  Annoyed,
  Cloud,
  CloudRain,
  Eye,
  Flame,
  Frown,
  Ghost,
  Gift,
  Hand,
  Handshake,
  Heart,
  HeartCrack,
  Hourglass,
  Laugh,
  Lightbulb,
  Medal,
  Meh,
  Moon,
  Skull,
  Smile,
  SmilePlus,
  Sparkles,
  Sun,
  Sunrise,
  Users,
  Wind,
  Zap,
} from 'lucide-react'
import { type Named } from '../environment/labels'

export const FEELINGS_ICON = Heart
export const DREAM_ICON = Moon
export const GRIEF_ICON = HeartCrack

export const EMOTION_ICONS: Record<string, Named> = {
  joy: { label: 'Joy', icon: Laugh, tone: 'gold' },
  contentment: { label: 'Contentment', icon: Smile, tone: 'success' },
  pride: { label: 'Pride', icon: Medal, tone: 'gold' },
  love: { label: 'Love', icon: Heart, tone: 'danger' },
  gratitude: { label: 'Gratitude', icon: Gift, tone: 'success' },
  relief: { label: 'Relief', icon: Wind, tone: 'info' },
  hope: { label: 'Hope', icon: Sunrise, tone: 'gold' },
  awe: { label: 'Awe', icon: Sparkles, tone: 'verdigris' },
  amusement: { label: 'Amusement', icon: SmilePlus, tone: 'warning' },
  fear: { label: 'Fear', icon: Ghost, tone: 'danger' },
  anxiety: { label: 'Anxiety', icon: Zap, tone: 'warning' },
  anger: { label: 'Anger', icon: Angry, tone: 'danger' },
  rage: { label: 'Rage', icon: Flame, tone: 'danger' },
  grief: { label: 'Grief', icon: HeartCrack, tone: 'muted' },
  sadness: { label: 'Sadness', icon: CloudRain, tone: 'info' },
  shame: { label: 'Shame', icon: Frown, tone: 'muted' },
  guilt: { label: 'Guilt', icon: Hand, tone: 'muted' },
  envy: { label: 'Envy', icon: Eye, tone: 'warning' },
  jealousy: { label: 'Jealousy', icon: Eye, tone: 'danger' },
  disgust: { label: 'Disgust', icon: Annoyed, tone: 'muted' },
  loneliness: { label: 'Loneliness', icon: Users, tone: 'info' },
  boredom: { label: 'Boredom', icon: Meh, tone: 'muted' },
  despair: { label: 'Despair', icon: Skull, tone: 'muted' },
  longing: { label: 'Longing', icon: Moon, tone: 'verdigris' },
}

export const MOOD_ICONS: Record<string, Named> = {
  elated: { label: 'Elated', icon: Sun, tone: 'gold' },
  content: { label: 'Content', icon: Smile, tone: 'success' },
  fine: { label: 'Fine', icon: Meh, tone: 'info' },
  uneasy: { label: 'Uneasy', icon: Cloud, tone: 'warning' },
  unhappy: { label: 'Unhappy', icon: Frown, tone: 'warning' },
  miserable: { label: 'Miserable', icon: CloudRain, tone: 'danger' },
  broken: { label: 'Broken', icon: HeartCrack, tone: 'danger' },
}

export const GRIEF_STAGES: Record<string, Named> = {
  shock: { label: 'Shock', icon: Zap, tone: 'danger' },
  mourning: { label: 'Mourning', icon: CloudRain, tone: 'info' },
  acceptance: { label: 'Acceptance', icon: Handshake, tone: 'success' },
  complicated: {
    label: 'A grief that will not heal',
    icon: HeartCrack,
    tone: 'muted',
  },
}

export const DREAM_KINDS: Record<string, Named> = {
  ordinary: { label: 'Ordinary dream', icon: Moon, tone: 'info' },
  nightmare: { label: 'Nightmare', icon: Ghost, tone: 'danger' },
  longing: { label: 'Dream of longing', icon: Hourglass, tone: 'verdigris' },
  prophetic: { label: 'Prophetic dream', icon: Eye, tone: 'gold' },
  visitation: { label: 'Visitation', icon: Sparkles, tone: 'gold' },
  shared: { label: 'Shared dream', icon: Users, tone: 'success' },
}

export const READING_ICON = Lightbulb

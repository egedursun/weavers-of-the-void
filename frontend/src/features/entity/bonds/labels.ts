import {
  Beer,
  BookOpen,
  Crown,
  Drama,
  Feather,
  Flame,
  Gem,
  GraduationCap,
  Handshake,
  Heart,
  HeartCrack,
  HeartHandshake,
  Home,
  Landmark,
  Medal,
  MessageCircle,
  Music,
  Puzzle,
  Scale,
  Ship,
  Shield,
  Skull,
  Sparkles,
  Swords,
  Target,
  Trees,
  User,
  Users,
} from 'lucide-react'
import { type Named } from '../environment/labels'

export const BONDS_ICON = HeartHandshake
export const PASSION_ICON = Flame
export const CIRCLE_ICON = Users
export const STANDING_ICON = Crown
export const CONTEST_ICON = Medal
export const PERSUASION_ICON = MessageCircle

export const RELATION_TYPES: Record<string, Named> = {
  acquaintance: { label: 'Acquaintance', icon: User, tone: 'muted' },
  friend: { label: 'Friend', icon: Handshake, tone: 'success' },
  close_friend: {
    label: 'Close friend',
    icon: HeartHandshake,
    tone: 'success',
  },
  best_friend: { label: 'Best friend', icon: Sparkles, tone: 'gold' },
  confidant: { label: 'Confidant', icon: MessageCircle, tone: 'verdigris' },
  crush: { label: 'Crush', icon: Heart, tone: 'warning' },
  lover: { label: 'Lover', icon: Heart, tone: 'danger' },
  ex_lover: { label: 'Former lover', icon: HeartCrack, tone: 'muted' },
  spouse: { label: 'Spouse', icon: Gem, tone: 'gold' },
  rival: { label: 'Rival', icon: Target, tone: 'warning' },
  nemesis: { label: 'Nemesis', icon: Skull, tone: 'danger' },
  enemy: { label: 'Enemy', icon: Swords, tone: 'danger' },
  mentor: { label: 'Mentor', icon: GraduationCap, tone: 'info' },
  protege: { label: 'Protégé', icon: BookOpen, tone: 'info' },
  comrade_in_arms: { label: 'Comrade in arms', icon: Shield, tone: 'danger' },
  drinking_companion: {
    label: 'Drinking companion',
    icon: Beer,
    tone: 'success',
  },
  patron: { label: 'Patron', icon: Landmark, tone: 'gold' },
  client: { label: 'Client', icon: Scale, tone: 'muted' },
}

export const PASSION_KINDS: Record<string, Named> = {
  love: { label: 'Love', icon: Heart, tone: 'danger' },
  loyalty: { label: 'Loyalty', icon: Shield, tone: 'gold' },
  hatred: { label: 'Hatred', icon: Skull, tone: 'danger' },
  devotion: { label: 'Devotion', icon: Sparkles, tone: 'verdigris' },
}

export const CIRCLE_KINDS: Record<string, Named> = {
  drinking_circle: { label: 'Drinking circle', icon: Beer, tone: 'success' },
  poets_circle: { label: "Poets' circle", icon: Feather, tone: 'verdigris' },
  hunting_circle: { label: 'Hunting circle', icon: Trees, tone: 'success' },
  secret_society: { label: 'Secret society', icon: Drama, tone: 'muted' },
  study_circle: { label: 'Study circle', icon: BookOpen, tone: 'info' },
  prayer_circle: { label: 'Prayer circle', icon: Sparkles, tone: 'gold' },
  music_circle: { label: 'Music circle', icon: Music, tone: 'verdigris' },
  craft_circle: { label: 'Craft circle', icon: Gem, tone: 'warning' },
}

export const GROUP_KINDS: Record<string, Named> = {
  household: { label: 'Household', icon: Home, tone: 'gold' },
  court: { label: 'Court', icon: Crown, tone: 'gold' },
  circle: { label: 'Circle', icon: Users, tone: 'success' },
  warband: { label: 'Warband', icon: Swords, tone: 'danger' },
  crew: { label: 'Crew', icon: Ship, tone: 'info' },
}

export const CONTEST_KINDS: Record<string, Named> = {
  riddle_game: { label: 'Riddle game', icon: Puzzle, tone: 'info' },
  insult_contest: {
    label: 'Contest of insults',
    icon: Feather,
    tone: 'warning',
  },
  debate: { label: 'Debate', icon: Scale, tone: 'info' },
  game_of_skill: { label: 'Game of skill', icon: Target, tone: 'success' },
  trial_of_wisdom: { label: 'Trial of wisdom', icon: BookOpen, tone: 'gold' },
  song_contest: { label: 'Song contest', icon: Music, tone: 'verdigris' },
  storytelling: { label: 'Storytelling', icon: Drama, tone: 'verdigris' },
}

export const OUTCOMES: Record<string, string> = {
  challenger: 'Challenger won',
  defender: 'Defender won',
  drawn: 'Drawn',
}

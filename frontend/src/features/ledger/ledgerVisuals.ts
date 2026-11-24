import {
  Bot,
  Crown,
  Droplet,
  Feather,
  Ghost,
  GraduationCap,
  Hand,
  Handshake,
  Heart,
  Infinity as InfinityIcon,
  type LucideIcon,
  MessageCircle,
  Moon,
  PenLine,
  Route,
  Scale,
  ScrollText,
  Skull,
  Sparkles,
  Star,
  Sun,
  Swords,
  Users,
  Wand2,
  Zap,
  Bolt,
  Flame,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain'

export type ActionKind = components['schemas']['ActionKind']
export type ActorKind = components['schemas']['ActorKind']

export const ACTION_ICON: Partial<Record<ActionKind, LucideIcon>> = {
  create_entity: Sparkles,
  revelation: ScrollText,
  summon_son: Crown,
  bear_child: Crown,
  command: Crown,
  absolute_command: Crown,
  bless_essence: Droplet,
  bless_hp: Heart,
  bless_stat: Sparkles,
  bless_existence: InfinityIcon,
  ascend: Crown,
  lightning: Bolt,
  chat: MessageCircle,
  answer_prayer: MessageCircle,
  resurrect_son: Heart,
  resurrect_mortal: Heart,
  kill_son: Skull,
  take_life: Skull,
  kill_foreign_god: Skull,
  devour: Skull,
  drain_essence: Droplet,
  wrath: Zap,
  world_wrath: Zap,
  edit_record: PenLine,
  edit_creator: PenLine,
  merge_records: PenLine,
  archive_record: PenLine,
  hang_star: Star,
  ignite_star: Star,
  rekindle_star: Star,
  extinguish_star: Star,
  reveal_route: Route,
  repair_route: Route,
  sever_route: Route,
  cleanse_leak: Wand2,
  miracle: Wand2,
  disaster: Flame,
  teach_knowledge: GraduationCap,
  advance_knowledge: GraduationCap,
  set_knowledge_level: GraduationCap,
  curse: Ghost,
  dream: Moon,
  influence: Hand,
  declare_chosen: Crown,
  incite_war: Swords,
  covenant: Handshake,
  change_anchor: Feather,
}

export const DEFAULT_ACTION_ICON: LucideIcon = Hand

export const ACTOR: Record<
  ActorKind,
  { label: string; icon: LucideIcon; tone: KpiTone }
> = {
  creator: { label: 'You', icon: Sun, tone: 'gold' },
  son: { label: 'Sons', icon: Crown, tone: 'verdigris' },
  mortal: { label: 'Mortals', icon: Users, tone: 'info' },
  foreign_god: { label: 'Foreign gods', icon: Ghost, tone: 'danger' },
  fate: { label: 'Fate', icon: Scale, tone: 'warning' },
  engine: { label: 'The world engine', icon: Bot, tone: 'muted' },
  system: { label: 'The system', icon: Bot, tone: 'muted' },
}

export const ACTOR_KINDS = Object.keys(ACTOR) as ActorKind[]

export function sentence(label: string): string {
  return label ? label.charAt(0).toUpperCase() + label.slice(1) : label
}

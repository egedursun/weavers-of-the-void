import {
  Anchor,
  Ban,
  CheckCircle2,
  Coins,
  Crown,
  Flag,
  Globe,
  HandCoins,
  Handshake,
  Landmark,
  Link,
  Map as MapIcon,
  Orbit,
  Scale,
  Shield,
  ShieldAlert,
  Swords,
  TriangleAlert,
  Unlink,
  Users,
} from 'lucide-react'
import { type Named } from '../environment/labels'

export const STATECRAFT_ICON = Globe
export const THREAT_ICON = ShieldAlert
export const TRUST_ICON = Handshake
export const CRISIS_ICON = TriangleAlert
export const SPHERE_ICON = Orbit
export const SUBJECT_ICON = Crown
export const CAPACITY_ICON = Users

export const DEMANDS: Record<string, Named> = {
  cede_region: { label: 'Cede a land', icon: MapIcon, tone: 'warning' },
  release_vassal: { label: 'Release a vassal', icon: Unlink, tone: 'info' },
  convert: { label: 'Take up a faith', icon: Landmark, tone: 'verdigris' },
  pay: { label: 'Pay what is owed', icon: Coins, tone: 'gold' },
}

export const CRISIS_STATES: Record<string, Named> = {
  escalating: { label: 'Escalating', icon: TriangleAlert, tone: 'warning' },
  backed_down: { label: 'The demander backed down', icon: Ban, tone: 'muted' },
  conceded: { label: 'Conceded', icon: CheckCircle2, tone: 'success' },
  war: { label: 'Came to war', icon: Swords, tone: 'danger' },
}

export const SIDES: Record<string, Named> = {
  demander: { label: 'Backs the demander', icon: Flag, tone: 'warning' },
  target: { label: 'Backs the target', icon: Shield, tone: 'info' },
}

export const SUBJECT_KINDS: Record<string, Named> = {
  vassal: { label: 'Vassal', icon: Crown, tone: 'gold' },
  tributary: { label: 'Tributary', icon: HandCoins, tone: 'gold' },
  march: { label: 'March', icon: Shield, tone: 'danger' },
  personal_union: { label: 'Personal union', icon: Link, tone: 'verdigris' },
  client: { label: 'Client', icon: Orbit, tone: 'info' },
  colony: { label: 'Colony', icon: Globe, tone: 'success' },
  protectorate: { label: 'Protectorate', icon: Anchor, tone: 'info' },
}

export const STANDINGS: Record<string, Named> = {
  hegemon: { label: 'Hegemon', icon: Crown, tone: 'gold' },
  great_power: { label: 'Great power', icon: Landmark, tone: 'gold' },
  minor_power: { label: 'Minor power', icon: Scale, tone: 'muted' },
  client: { label: 'Client', icon: Orbit, tone: 'info' },
}

export function labelTable(
  specs: Record<string, Named>
): Record<string, string> {
  return Object.fromEntries(
    Object.entries(specs).map(([key, spec]) => [key, spec.label])
  )
}

export function spec(
  table: Record<string, Named>,
  key: string | null | undefined
): Named {
  return (
    (key ? table[key] : undefined) ?? {
      label: key ?? 'Unknown',
      icon: Globe,
      tone: 'muted',
    }
  )
}

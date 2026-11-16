import {
  Wine,
  Swords,
  FileWarning,
  Database,
  Backpack,
  Footprints,
  Car,
  Plane,
  Cable,
  ArrowUpFromLine,
  PawPrint,
  Network,
  Zap,
  HandHeart,
  TreePine,
  Library,
  Landmark,
  Warehouse,
  Drama,
  Droplets,
  TrainFront,
  RadioTower,
  Bath,
  BookOpen,
  Building,
  Building2,
  Castle,
  Church,
  Coins,
  Dice5,
  Droplet,
  Eye,
  Flame,
  Grid3x3,
  Hand,
  HandCoins,
  Home,
  Hospital,
  KeyRound,
  type LucideIcon,
  PackageOpen,
  Repeat,
  Sailboat,
  Scale,
  Ship,
  Shrub,
  Snowflake,
  Sparkles,
  Store,
  Target,
  Tent,
  TrendingDown,
  TrendingUp,
  Truck,
  UserX,
  Users,
  Waves,
  Wheat,
  Orbit,
  Rocket,
  Expand,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain/KpiTile'

type Schema = components['schemas']
export type Named = { label: string; icon: LucideIcon; tone: KpiTone }

export const URBAN_ICON: LucideIcon = Building2

export const HOUSING: Record<Schema['HousingLevel'], Named> = {
  hut: { label: 'Huts', icon: Tent, tone: 'muted' },
  cottage: { label: 'Cottages', icon: Home, tone: 'info' },
  house: { label: 'Houses', icon: Building, tone: 'verdigris' },
  townhouse: { label: 'Townhouses', icon: Building2, tone: 'gold' },
  manor: { label: 'Manors', icon: Castle, tone: 'gold' },
  apartment: { label: 'Apartments', icon: Building2, tone: 'info' },
  tenement: { label: 'Tenements', icon: Building, tone: 'muted' },
  tower_block: { label: 'Tower blocks', icon: Building2, tone: 'verdigris' },
  arcology_unit: { label: 'Arcology units', icon: Building2, tone: 'gold' },
  habitat_module: { label: 'Habitat modules', icon: Orbit, tone: 'info' },
  ship_berth: { label: 'Ship berths', icon: Rocket, tone: 'muted' },
}

export const SERVICES: Record<Schema['UrbanService'], Named> = {
  water: { label: 'Water', icon: Droplet, tone: 'info' },
  faith: { label: 'Faith', icon: Church, tone: 'gold' },
  watch: { label: 'Watch', icon: Eye, tone: 'warning' },
  healing: { label: 'Healing', icon: Hospital, tone: 'success' },
  market: { label: 'Market', icon: Store, tone: 'gold' },
  school: { label: 'School', icon: BookOpen, tone: 'verdigris' },
  bath: { label: 'Baths', icon: Bath, tone: 'info' },
  fire: { label: 'Fire brigade', icon: Flame, tone: 'danger' },
  sanitation: { label: 'Sewers and waste', icon: Droplets, tone: 'info' },
  transport: { label: 'Transport', icon: TrainFront, tone: 'muted' },
  communication: {
    label: 'Communication',
    icon: RadioTower,
    tone: 'verdigris',
  },
  power: { label: 'Power', icon: Zap, tone: 'warning' },
  courts: { label: 'Courts', icon: Scale, tone: 'info' },
  welfare: { label: 'Welfare', icon: HandHeart, tone: 'verdigris' },
  granary: { label: 'Granaries', icon: Wheat, tone: 'success' },
  parks: { label: 'Parks', icon: TreePine, tone: 'success' },
  library: { label: 'Libraries', icon: Library, tone: 'info' },
  burial: { label: 'Burial', icon: Landmark, tone: 'muted' },
  depot: { label: 'Depots', icon: Warehouse, tone: 'muted' },
  administration: { label: 'Administration', icon: Building2, tone: 'info' },
  entertainment: { label: 'Entertainment', icon: Drama, tone: 'gold' },
}

export const MORPHOLOGIES: Record<Schema['Morphology'], Named> = {
  organic: { label: 'Grown at random', icon: Shrub, tone: 'muted' },
  planned: { label: 'Planned on a grid', icon: Grid3x3, tone: 'info' },
  concentric: { label: 'Grown in rings', icon: Target, tone: 'gold' },
  grid: { label: 'Laid out on a street grid', icon: Grid3x3, tone: 'info' },
  vertical: { label: 'Built upward', icon: Building2, tone: 'verdigris' },
  sprawl: { label: 'Sprawling', icon: Expand, tone: 'warning' },
}

export const RACKETS: Record<Schema['RacketKind'], Named> = {
  protection: { label: 'Protection', icon: Hand, tone: 'danger' },
  smuggling: { label: 'Smuggling', icon: PackageOpen, tone: 'warning' },
  gambling: { label: 'Gambling', icon: Dice5, tone: 'warning' },
  fencing: { label: 'Fencing', icon: Coins, tone: 'muted' },
  kidnapping: { label: 'Kidnapping', icon: UserX, tone: 'danger' },
  counterfeiting: { label: 'Counterfeiting', icon: Repeat, tone: 'warning' },
  fraud: { label: 'Fraud', icon: FileWarning, tone: 'danger' },
  extortion: { label: 'Extortion', icon: HandCoins, tone: 'danger' },
  trafficking: { label: 'Trafficking', icon: Truck, tone: 'danger' },
  intoxicants: { label: 'Intoxicants', icon: Wine, tone: 'danger' },
  data_theft: { label: 'Data theft', icon: Database, tone: 'danger' },
  loan_sharking: { label: 'Loan sharking', icon: Coins, tone: 'danger' },
  arms: { label: 'Arms', icon: Swords, tone: 'danger' },
}

export const STANCES: Record<Schema['CrimeStance'], Named> = {
  suppress: { label: 'Suppressed', icon: Scale, tone: 'danger' },
  co_opt: { label: 'Co-opted', icon: HandCoins, tone: 'gold' },
}

export const ORDER_LAWS: Record<Schema['OrderLaw'], Named> = {
  spare_members: {
    label: 'Spare fellow members',
    icon: Users,
    tone: 'success',
  },
  no_outer_dealings: {
    label: 'No dealing with outer beings',
    icon: Sparkles,
    tone: 'warning',
  },
  share_discoveries: {
    label: 'Share discoveries',
    icon: BookOpen,
    tone: 'info',
  },
  keep_secrecy: {
    label: 'Keep the order secret',
    icon: KeyRound,
    tone: 'muted',
  },
}

export const VERDICTS: Record<Schema['TribunalVerdict'], Named> = {
  acquitted: { label: 'Acquitted', icon: Scale, tone: 'success' },
  fined: { label: 'Fined', icon: Coins, tone: 'warning' },
  expelled: { label: 'Cast out', icon: UserX, tone: 'danger' },
  stripped: { label: 'Stripped of rank', icon: TrendingDown, tone: 'warning' },
}

export const CONVOY_STATUS: Record<Schema['ConvoyStatus'], Named> = {
  loading: { label: 'Loading', icon: PackageOpen, tone: 'muted' },
  travelling: { label: 'On the road', icon: Truck, tone: 'info' },
  delayed: { label: 'Delayed', icon: Snowflake, tone: 'warning' },
  arrived: { label: 'Arrived', icon: Store, tone: 'success' },
  raided: { label: 'Raided', icon: UserX, tone: 'danger' },
  lost: { label: 'Lost', icon: Waves, tone: 'danger' },
}

export const PRESERVATION: Record<Schema['Preservation'], Named> = {
  none: { label: 'Not preserved', icon: PackageOpen, tone: 'muted' },
  salted: { label: 'Salted', icon: Wheat, tone: 'info' },
  iced: { label: 'Iced', icon: Snowflake, tone: 'info' },
  magic: { label: 'Kept by magic', icon: Sparkles, tone: 'gold' },
}

export const TRANSPORT: Record<Schema['TransportKind'], Named> = {
  porters: { label: 'Porters', icon: Backpack, tone: 'muted' },
  pack_animals: { label: 'Pack animals', icon: Footprints, tone: 'success' },
  animal_carts: { label: 'Animal carts', icon: Truck, tone: 'gold' },
  rail: { label: 'Rail', icon: TrainFront, tone: 'info' },
  road_motor: { label: 'Motor transport', icon: Car, tone: 'info' },
  river_and_canal: {
    label: 'River and canal boats',
    icon: Sailboat,
    tone: 'info',
  },
  sea: { label: 'Sea ships', icon: Ship, tone: 'verdigris' },
  air: { label: 'Aircraft', icon: Plane, tone: 'warning' },
  pipeline: { label: 'Pipelines', icon: Cable, tone: 'muted' },
  orbital_lift: { label: 'Orbital lifts', icon: ArrowUpFromLine, tone: 'gold' },
  space: { label: 'Space freighters', icon: Rocket, tone: 'gold' },
  teleport: { label: 'Teleport', icon: Zap, tone: 'verdigris' },
  living: { label: 'Living carriers', icon: PawPrint, tone: 'success' },
  rite: { label: 'Bound conveyance', icon: Sparkles, tone: 'verdigris' },
  network: { label: 'Networks', icon: Network, tone: 'info' },
}

export const PLAYS: Record<Schema['MarketPlay'], Named> = {
  corner: { label: 'Cornered', icon: TrendingUp, tone: 'danger' },
  dump: { label: 'Flooded', icon: TrendingDown, tone: 'warning' },
}

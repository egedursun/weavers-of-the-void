import {
  Anchor,
  Baby,
  BadgeCheck,
  Ban,
  Biohazard,
  Bird,
  Bot,
  Boxes,
  Brain,
  BrickWall,
  Briefcase,
  Building2,
  Castle,
  Church,
  CircleCheck,
  ClipboardList,
  Coins,
  Copy,
  Cpu,
  Crown,
  DoorOpen,
  Drama,
  Droplet,
  Droplets,
  Eye,
  EyeOff,
  Feather,
  Fence,
  Fish,
  Flag,
  FlaskConical,
  Footprints,
  Gavel,
  Gem,
  Gift,
  Globe,
  GraduationCap,
  Hammer,
  HandCoins,
  HandHeart,
  Handshake,
  Heart,
  HeartCrack,
  HeartHandshake,
  Hexagon,
  Hourglass,
  House,
  Landmark,
  Leaf,
  Lock,
  Map,
  Map as MapIcon,
  Medal,
  Megaphone,
  Moon,
  Network,
  PartyPopper,
  PenLine,
  Radiation,
  RefreshCw,
  Repeat,
  Scale,
  ScrollText,
  Server,
  Shield,
  ShieldCheck,
  ShieldOff,
  Ship,
  Signpost,
  Skull,
  Sparkles,
  Stethoscope,
  Sun,
  Swords,
  Trees,
  TrendingUp,
  Trophy,
  Undo2,
  UserPlus,
  Users,
  VolumeX,
  Vote,
  WandSparkles,
  Banknote,
  Building,
  HourglassCog,
  Route,
  Users2,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain'
import { type Named, named, plain } from '../environment/labels'

export { named, plain }
export type { Named }

export const GOVERNMENTS: Record<string, Named> = {
  chiefdom: { label: 'Chiefdom', icon: Flag, tone: 'warning' },
  monarchy: { label: 'Monarchy', icon: Crown, tone: 'gold' },
  theocracy: { label: 'Theocracy', icon: Church, tone: 'verdigris' },
  oligarchy: { label: 'Oligarchy', icon: Gem, tone: 'info' },
  republic: { label: 'Republic', icon: Landmark, tone: 'info' },
  tribal_confederation: {
    label: 'Tribal confederation',
    icon: Users,
    tone: 'success',
  },
  empire: { label: 'Empire', icon: Castle, tone: 'gold' },
  hive_council: { label: 'Hive council', icon: Hexagon, tone: 'verdigris' },
  god_realm: { label: 'Realm ruled by a god', icon: Sun, tone: 'gold' },
  occupation: { label: 'Occupation', icon: Swords, tone: 'danger' },
  junta: { label: 'Military government', icon: Medal, tone: 'danger' },
  corporate_state: { label: 'Corporate state', icon: Briefcase, tone: 'gold' },
  technocracy: { label: 'Technocracy', icon: FlaskConical, tone: 'info' },
  federation: { label: 'Federation', icon: Network, tone: 'success' },
  commune: { label: 'Commune', icon: Users, tone: 'success' },
  machine_rule: { label: 'Machine rule', icon: Cpu, tone: 'verdigris' },
  colonial_administration: { label: 'Colony', icon: Flag, tone: 'warning' },
}

export const RULES: Record<string, Named & { hint: string }> = {
  autocratic: {
    label: 'Autocratic',
    icon: Gavel,
    tone: 'gold',
    hint: 'The ruler alone decides',
  },
  council: {
    label: 'By council',
    icon: Users,
    tone: 'info',
    hint: 'A council of the great decides',
  },
  assembly: {
    label: 'By assembly',
    icon: Vote,
    tone: 'success',
    hint: 'The free people vote',
  },
  divine: {
    label: 'By divine will',
    icon: Sparkles,
    tone: 'verdigris',
    hint: 'Omens and priests decide',
  },
}

export const STANDINGS: Record<
  components['schemas']['RegionalStanding'],
  Named
> = {
  hegemon: { label: 'Hegemon', icon: Trophy, tone: 'gold' },
  great_power: { label: 'Great power', icon: Medal, tone: 'info' },
  minor_power: { label: 'Minor power', icon: Shield, tone: 'muted' },
  client: { label: 'Client state', icon: Lock, tone: 'warning' },
  neutral: { label: 'Neutral', icon: Scale, tone: 'info' },
  isolated: { label: 'Isolated', icon: Ban, tone: 'gold' },
}

export const OFFICES: Record<string, Named> = {
  ruler: { label: 'Ruler', icon: Castle, tone: 'gold' },
  heir_designate: { label: 'Heir designate', icon: Baby, tone: 'success' },
  regent: { label: 'Regent', icon: Hourglass, tone: 'verdigris' },
  chancellor: { label: 'Chancellor', icon: ScrollText, tone: 'info' },
  marshal: { label: 'Marshal', icon: Swords, tone: 'danger' },
  treasurer: { label: 'Treasurer', icon: Coins, tone: 'gold' },
  high_judge: { label: 'High judge', icon: Scale, tone: 'info' },
  spymaster: { label: 'Spymaster', icon: Eye, tone: 'verdigris' },
  governor: { label: 'Governor', icon: MapIcon, tone: 'success' },
  ambassador: { label: 'Ambassador', icon: Handshake, tone: 'info' },
  herald: { label: 'Herald', icon: Megaphone, tone: 'warning' },
  chaplain: { label: 'Court chaplain', icon: Church, tone: 'verdigris' },
  court_scholar: { label: 'Court scholar', icon: GraduationCap, tone: 'info' },
  head_of_state: { label: 'Head of state', icon: Crown, tone: 'gold' },
  head_of_government: {
    label: 'Head of government',
    icon: Landmark,
    tone: 'info',
  },
  minister: { label: 'Minister', icon: Briefcase, tone: 'info' },
  general: { label: 'General', icon: Medal, tone: 'danger' },
  admiral: { label: 'Admiral', icon: Anchor, tone: 'info' },
  speaker: { label: 'Speaker', icon: Megaphone, tone: 'verdigris' },
  chief_scientist: {
    label: 'Chief scientist',
    icon: FlaskConical,
    tone: 'info',
  },
  jester: { label: 'Court jester', icon: Drama, tone: 'gold' },
  warden: { label: 'Warden of the grounds', icon: Fish, tone: 'verdigris' },
  censor: { label: 'Censor', icon: ClipboardList, tone: 'info' },
}

export const LAW_AREAS: Record<string, Named> = {
  succession: { label: 'Succession', icon: Crown, tone: 'gold' },
  property: { label: 'Property', icon: House, tone: 'success' },
  fiscal: { label: 'Taxes and coin', icon: Coins, tone: 'gold' },
  penal: { label: 'Crime and punishment', icon: Gavel, tone: 'danger' },
  military: { label: 'War and levies', icon: Swords, tone: 'danger' },
  social: { label: 'Society', icon: Users, tone: 'info' },
  public_health: {
    label: 'Public health',
    icon: Stethoscope,
    tone: 'success',
  },
  magic: { label: 'Magic', icon: WandSparkles, tone: 'verdigris' },
  constitutional: {
    label: 'The fundamental law',
    icon: ScrollText,
    tone: 'gold',
  },
  commerce: { label: 'Trade and contracts', icon: Banknote, tone: 'gold' },
  faith: { label: 'Faith and rites', icon: Sparkles, tone: 'verdigris' },
  labour: { label: 'Work and wages', icon: Hammer, tone: 'info' },
  family: { label: 'Family', icon: Users2, tone: 'success' },
  environment: { label: 'Environment', icon: Trees, tone: 'verdigris' },
}

export const LAW_KINDS: Record<string, string> = {
  succession_rule: 'Law of succession',
  inheritance_split: 'Inheritance',
  land_tenure: 'Land tenure',
  slavery: 'Slavery',
  serfdom: 'Serfdom',
  tax_rate: 'Tax rate',
  tithe: 'Tithe',
  tolls: 'Tolls',
  debt_law: 'Debt',
  penal_code: 'Penal code',
  levy_law: 'Levy',
  conscription: 'Conscription',
  standing_army: 'Standing army',
  veteran_pension: 'Veterans’ pension',
  ransom_custom: 'Ransom custom',
  marriage_law: 'Marriage',
  sumptuary: 'Sumptuary law',
  guild_charter: 'Association charter',
  foreigner_rights: 'Rights of foreigners',
  religious_tolerance: 'Religious tolerance',
  worship_ban: 'Worship ban',
  censorship: 'Censorship',
  blood_feud: 'Blood feud',
  quarantine: 'Quarantine',
  burial_law: 'Burial',
  sanitation: 'Sanitation',
  fair_market: 'Fair market',
  magic_ban: 'Ban on magic',
  licensed_magic: 'Licensed magic',
  rite_restrictions: 'Restricted rites',
  franchise: 'Franchise',
  constitution: 'Constitution',
  custom: 'Custom',
  labour_law: 'Labour law',
  environment_law: 'Environment law',
  data_privacy: 'Privacy law',
  weapons_law: 'Weapons law',
  intellectual_property: 'Patent law',
  machine_law: 'Machine law',
  space_law: 'Space law',
  closed_season: 'Closed season',
  protected_waters: 'Protected waters',
  catch_quota: 'Catch quota',
  gear_ban: 'Gear ban',
  mind_status: 'Standing of made minds',
  copy_law: 'Copying of minds',
  copy_succession: 'Succession among copies',
  competition_law: 'Fair dealing',
  erasure_law: 'Ending a made mind',
  augment_law: 'Augmentation',
  network_law: 'Networks',
  surveillance_law: 'Surveillance',
  provision_law: 'Provision of goods',
  power_law: 'Powers',
  source_law: 'Sources of power',
  living_craft_law: 'Living craft',
  clone_law: 'Making clones',
  clone_status: 'Standing of clones',
  germline_law: 'Changing what passes to descendants',
  designed_status: 'Standing of designed peoples',
}

export const LAW_PARAMS: Record<string, string> = {
  allowed: 'Allowed',
  amount: 'Amount',
  arson: 'Arson',
  assault: 'Assault',
  automatic: 'Automatic',
  banditry: 'Banditry',
  banned: 'Banned',
  banned_method: 'Banned method',
  blasphemy: 'Blasphemy',
  bodies: 'Worker bodies stand',
  bribery: 'Bribery',
  burglary: 'Burglary',
  cartel_ban: 'Pursuit of cartels',
  child_labour: 'Child labour',
  claims: 'Claims beyond the world',
  cloning: 'Cloning',
  contempt_of_court: 'Contempt of court',
  corruption: 'Corruption',
  counterfeiting: 'Counterfeiting',
  cowardice: 'Cowardice',
  custom: 'Custom',
  customs_fraud: 'Customs fraud',
  debasement: 'Debasing the coin',
  decision_rule: 'Decided by',
  desecration: 'Desecration',
  desertion: 'Desertion',
  divorce: 'Divorce',
  duelling: 'Duelling where it is banned',
  duration: 'Duration (seasons)',
  election_fraud: 'Fraud in an election',
  embezzlement: 'Embezzlement',
  endogamy: 'Marry within',
  enforced: 'Enforced',
  enforcer: 'Enforced by',
  engineering: 'Engineering of life',
  epochs: 'Epochs',
  erasure: 'Ending a mind',
  espionage: 'Espionage',
  estates_rights: 'Rights of the estates',
  false_claim: 'Pressing a false claim',
  fee: 'Fee',
  fixing_contests: 'Fixing a contest',
  forbidden_food: 'Eating what is forbidden',
  forbidden_rite: 'Working a forbidden rite',
  forced_edit: 'Editing a mind by force',
  forged_line: 'Forging a line of descent',
  form: 'Form of union',
  fraud: 'Fraud',
  gear: 'Gear of the catch',
  sex_rule: 'Which sexes may succeed',
  government: 'Government',
  guild_id: 'Association',
  heir_murder: 'Murder of an heir',
  heresy: 'Heresy',
  impersonation: 'Passing as another by a copy',
  insider_ban: 'Pursuit of trading on secrets',
  intoxication: 'Intoxication where it is banned',
  jubilee_epochs: 'Jubilee every (epochs)',
  kidnapping: 'Kidnapping',
  labour_days: 'Labour days',
  level: 'Level',
  licence_limit: 'Limits on licences',
  looting: 'Looting against orders',
  machine_seizure: 'Seizing a made thing',
  manslaughter: 'Manslaughter',
  max_hours: 'Most hours of work a week',
  hereditary_trades: 'Trades pass from parent to child',
  merchant_luxury: 'Merchant luxury',
  merger_review: 'Review of mergers',
  merging: 'Merged species',
  min_age: 'Minimum age',
  mind_compulsion: 'Compelling a mind by a power',
  mind_powers: 'Powers over minds',
  mind_theft: 'Theft of a mind',
  monopoly: 'Monopoly',
  monopoly_break: 'Breaking single sellers',
  murder: 'Murder',
  mutiny: 'Mutiny',
  noble_luxury: 'Noble luxury',
  oathbreaking: 'Oathbreaking',
  perjury: 'Perjury',
  piracy: 'Piracy',
  plural_side: 'Side that may take more than one partner',
  poaching: 'Poaching',
  price: 'Price',
  price_cap: 'Price caps',
  purity_breach: 'Breaching purity',
  quarantine_breach: 'Breaking quarantine',
  rate: 'Rate (%)',
  rebellion: 'Rebellion',
  receiving: 'Receiving stolen goods',
  remedy: 'Remedy',
  riot: 'Riot',
  rite: 'Rite',
  robbery: 'Robbery',
  rule: 'Rule',
  sacrilege: 'Sacrilege',
  sedition: 'Sedition',
  severity: 'Severity',
  sexual_violence: 'Sexual violence',
  shaping: 'Shaping of bodies',
  share: 'Share (%)',
  smuggling: 'Smuggling',
  son_id: 'Banned god',
  split: 'Split',
  status: 'Status',
  strength: 'Strength',
  strictness: 'Strictness',
  pollutant: 'Pollution it aims at',
  sumptuary_breach: 'Sumptuary breach',
  synthesis: 'Synthesis of life',
  taboo_breach: 'Breaking a taboo',
  tainted_goods: 'Selling tainted goods',
  tax_evasion: 'Evading taxes',
  tenure: 'Tenure',
  term: 'Protection (epochs)',
  theft: 'Theft',
  threats: 'Threats',
  torture: 'Questioning under torture',
  trafficking: 'Enslavement and trafficking',
  treason: 'Treason',
  trespass: 'Trespass',
  trial: 'Trial by',
  union_offence: 'An offence against a union the culture names',
  unions: 'Unions',
  unlawful_assembly: 'Unlawful assembly',
  unlawful_pollution: 'Polluting against the law',
  unlicensed_copying: 'Copying a mind without leave',
  unlicensed_power: 'Using a power without a licence',
  unlicensed_trade: 'Trading without a licence',
  usurpation: 'Usurpation',
  vagrancy: 'Vagrancy where it is banned',
  vandalism: 'Vandalism',
  voters: 'Who votes',
  war_crimes: 'Crimes of war under treaty',
  well_poisoning: 'Poisoning the wells',
  wergild_allowed: 'Wergild allowed',
  wholeness_required: 'Must be whole of body',
  witchcraft: 'Witchcraft',
  works: 'Works',
}

export const LEGITIMACY_BASES: Record<string, Named> = {
  custom: { label: 'By custom', icon: ScrollText, tone: 'muted' },
  decree: { label: 'By decree', icon: Gavel, tone: 'gold' },
  divine: { label: 'By divine will', icon: Sparkles, tone: 'verdigris' },
  council: { label: 'By council', icon: Users, tone: 'info' },
}

export const CLAIM_BASES: Record<string, Named> = {
  prophecy: { label: 'By prophecy', icon: Eye, tone: 'verdigris' },
  inheritance: { label: 'By blood', icon: Crown, tone: 'gold' },
  marriage: { label: 'By marriage', icon: Heart, tone: 'danger' },
  conquest: { label: 'By conquest', icon: Swords, tone: 'danger' },
  divine: { label: 'By divine right', icon: Sparkles, tone: 'verdigris' },
  fabricated: { label: 'Forged', icon: Feather, tone: 'warning' },
  de_jure: { label: 'By right of the land', icon: Map, tone: 'info' },
  election: { label: 'By election', icon: Vote, tone: 'verdigris' },
  adoption: { label: 'By adoption', icon: UserPlus, tone: 'gold' },
}

export const TREATY_KINDS: Record<string, Named & { plural: string }> = {
  peace: { label: 'Peace', plural: 'Peaces', icon: Bird, tone: 'success' },
  truce: { label: 'Truce', plural: 'Truces', icon: Hourglass, tone: 'warning' },
  alliance_defensive: {
    label: 'Defensive alliance',
    plural: 'Defensive alliances',
    icon: ShieldCheck,
    tone: 'info',
  },
  alliance_offensive: {
    label: 'Offensive alliance',
    plural: 'Offensive alliances',
    icon: Swords,
    tone: 'danger',
  },
  non_aggression: {
    label: 'Non-aggression pact',
    plural: 'Non-aggression pacts',
    icon: Ban,
    tone: 'muted',
  },
  vassalage: {
    label: 'Vassalage',
    plural: 'Vassalages',
    icon: Crown,
    tone: 'gold',
  },
  tribute: { label: 'Tribute', plural: 'Tributes', icon: Coins, tone: 'gold' },
  marriage_pact: {
    label: 'Marriage pact',
    plural: 'Marriage pacts',
    icon: HeartHandshake,
    tone: 'verdigris',
  },
  trade_pact: {
    label: 'Trade pact',
    plural: 'Trade pacts',
    icon: Ship,
    tone: 'success',
  },
  condotta: {
    label: 'Condotta',
    plural: 'Condottas',
    icon: HandCoins,
    tone: 'warning',
  },
  guarantee: {
    label: 'Guarantee',
    plural: 'Guarantees',
    icon: BadgeCheck,
    tone: 'info',
  },
  interworld: {
    label: 'Interworld pact',
    plural: 'Interworld pacts',
    icon: Globe,
    tone: 'verdigris',
  },
  coalition: {
    label: 'Coalition',
    plural: 'Coalitions',
    icon: Users,
    tone: 'danger',
  },
  divine_pact: {
    label: 'Divine pact',
    plural: 'Divine pacts',
    icon: Sparkles,
    tone: 'gold',
  },
  naval_limit: {
    label: 'Naval treaty',
    plural: 'Naval treaties',
    icon: Anchor,
    tone: 'info',
  },
  arms_limit: {
    label: 'Arms treaty',
    plural: 'Arms treaties',
    icon: Radiation,
    tone: 'info',
  },
  mutual_aid: {
    label: 'Mutual aid',
    plural: 'Pacts of mutual aid',
    icon: HandHeart,
    tone: 'success',
  },
  border_accord: {
    label: 'Border accord',
    plural: 'Border accords',
    icon: Fence,
    tone: 'info',
  },
}

export const TREATY_STATUSES: Record<
  components['schemas']['TreatyStatus'],
  Named
> = {
  in_force: { label: 'In force', icon: CircleCheck, tone: 'success' },
  fulfilled: { label: 'Fulfilled', icon: BadgeCheck, tone: 'info' },
  expired: { label: 'Expired', icon: Hourglass, tone: 'muted' },
  broken: { label: 'Broken', icon: HeartCrack, tone: 'danger' },
  proposed: { label: 'Proposed', icon: PenLine, tone: 'gold' },
  rejected: { label: 'Rejected', icon: Ban, tone: 'muted' },
  suspended: { label: 'Suspended', icon: HourglassCog, tone: 'warning' },
  renegotiating: {
    label: 'Under renegotiation',
    icon: RefreshCw,
    tone: 'success',
  },
}

export const PARTY_ROLES: Record<string, Named> = {
  signatory: { label: 'Signatory', icon: PenLine, tone: 'gold' },
  overlord: { label: 'Overlord', icon: Crown, tone: 'gold' },
  vassal: { label: 'Vassal', icon: Shield, tone: 'muted' },
  guarantor: { label: 'Guarantor', icon: ShieldCheck, tone: 'info' },
  mediator: { label: 'Mediator', icon: Scale, tone: 'verdigris' },
  witness: { label: 'Witness', icon: Eye, tone: 'info' },
}

export const CLAUSES: Record<string, Named> = {
  call_to_arms: { label: 'Call to arms', icon: Swords, tone: 'danger' },
  tribute: { label: 'Tribute', icon: Coins, tone: 'gold' },
  cession: { label: 'Cession of land', icon: MapIcon, tone: 'warning' },
  hostage: { label: 'Hostages', icon: Lock, tone: 'warning' },
  marriage: { label: 'Marriage', icon: Heart, tone: 'verdigris' },
  trade_rights: { label: 'Trade rights', icon: Ship, tone: 'success' },
  tolls_waived: { label: 'Tolls waived', icon: Signpost, tone: 'success' },
  religious_freedom: {
    label: 'Freedom of worship',
    icon: Church,
    tone: 'verdigris',
  },
  demilitarised: { label: 'Demilitarised land', icon: ShieldOff },
  champion: { label: 'Champions', icon: Medal, tone: 'gold' },
  extradition: { label: 'Extradition', icon: Gavel, tone: 'info' },
  wergild: { label: 'Wergild', icon: HandCoins, tone: 'gold' },
  non_aggression: { label: 'Non-aggression', icon: Ban, tone: 'muted' },
  route_control: {
    label: 'Road and tolls ceded',
    icon: Route,
    tone: 'gold',
  },
  resource_demand: {
    label: 'Tribute to a living resource',
    icon: Gem,
    tone: 'verdigris',
  },
  research_agreement: {
    label: 'Shared research',
    icon: GraduationCap,
    tone: 'info',
  },
  fleet_limit: {
    label: 'Fleet limit',
    icon: Ship,
    tone: 'info',
  },
  autonomous_weapons_ban: {
    label: 'No instructed weapons',
    icon: Bot,
    tone: 'warning',
  },
  mind_seizure_ban: {
    label: 'No seizing of minds or machines',
    icon: Cpu,
    tone: 'warning',
  },
  soldier_copy_ban: {
    label: 'No copied soldiers',
    icon: Copy,
    tone: 'warning',
  },
  replicator_weapon_ban: {
    label: 'No self-making weapons',
    icon: Boxes,
    tone: 'danger',
  },
  civil_network_shield: {
    label: 'Civil networks spared',
    icon: Network,
    tone: 'info',
  },
  civil_host_shield: {
    label: 'Hosts of realms spared',
    icon: Server,
    tone: 'info',
  },
  no_mind_compulsion: {
    label: 'No bending of minds by powers',
    icon: Brain,
    tone: 'info',
  },
  no_plague_powers: {
    label: 'No powers of plague',
    icon: Biohazard,
    tone: 'info',
  },
  no_designed_disease: {
    label: 'No diseases made by design',
    icon: Biohazard,
    tone: 'info',
  },
  mass_weapon_limit: {
    label: 'Limit on weapons of mass harm',
    icon: Radiation,
    tone: 'info',
  },
  return_of_refugees: {
    label: 'Return of refugees',
    icon: Undo2,
    tone: 'warning',
  },
  shared_water: { label: 'Shared water', icon: Droplets, tone: 'info' },
  captive_exchange: {
    label: 'Exchange of captives',
    icon: Repeat,
    tone: 'success',
  },
}

export const OATHS: Record<string, Named> = {
  fealty: { label: 'Fealty', icon: Crown, tone: 'gold' },
  vengeance: { label: 'Vengeance', icon: Swords, tone: 'danger' },
  celibacy: { label: 'Celibacy', icon: Moon, tone: 'verdigris' },
  pilgrimage: { label: 'Pilgrimage', icon: Footprints, tone: 'info' },
  protection: { label: 'Protection', icon: Shield, tone: 'success' },
  silence: { label: 'Silence', icon: VolumeX, tone: 'muted' },
  sworn_kinship: {
    label: 'Sworn kinship',
    icon: Droplet,
    tone: 'danger',
  },
  service: { label: 'Service', icon: Handshake, tone: 'info' },
  poverty: { label: 'Poverty', icon: Coins, tone: 'muted' },
  nonviolence: { label: 'Nonviolence', icon: Leaf, tone: 'success' },
  fidelity: { label: 'Fidelity', icon: Heart, tone: 'verdigris' },
  secrecy: { label: 'Secrecy', icon: Lock, tone: 'muted' },
  testimony: { label: 'Testimony', icon: Gavel, tone: 'gold' },
  office: { label: 'Oath of office', icon: Landmark, tone: 'gold' },
}

export const OATH_STATUSES: Record<string, Named> = {
  sworn: { label: 'Sworn', icon: PenLine, tone: 'info' },
  kept: { label: 'Kept', icon: CircleCheck, tone: 'success' },
  fulfilled: { label: 'Fulfilled', icon: BadgeCheck, tone: 'success' },
  broken: { label: 'Broken', icon: HeartCrack, tone: 'danger' },
}

export const OATH_PENALTIES: Record<
  components['schemas']['OathPenalty'],
  Named
> = {
  shame: { label: 'Shame', icon: EyeOff, tone: 'warning' },
  fine: { label: 'A fine', icon: Coins, tone: 'gold' },
  exile: { label: 'Exile', icon: DoorOpen, tone: 'danger' },
  outlawry: { label: 'Outlawry', icon: Ban, tone: 'danger' },
  curse: { label: 'A curse', icon: Skull, tone: 'danger' },
}

export const TREASURY_ENTRIES: Record<string, Named> = {
  tax: { label: 'Taxes', icon: Landmark, tone: 'gold' },
  tolls: { label: 'Tolls', icon: Signpost, tone: 'gold' },
  investment: { label: 'Investment', icon: TrendingUp, tone: 'success' },
  garrison: { label: 'Garrison and court upkeep', icon: Shield },
  walls: { label: 'Walls', icon: BrickWall },
  building: { label: 'Building works', icon: Building },
  festival: { label: 'Festival', icon: PartyPopper, tone: 'verdigris' },
  alms: { label: 'Alms', icon: HandHeart, tone: 'success' },
  fire: { label: 'Fire', icon: Building2, tone: 'danger' },
  plunder: { label: 'Plunder', icon: Swords, tone: 'danger' },
  grant: { label: 'Grant', icon: Gift, tone: 'gold' },
  loan: { label: 'Loan', icon: Coins, tone: 'info' },
  upkeep: { label: 'Upkeep', icon: Hammer, tone: 'muted' },
  office_sale: { label: 'Office sold', icon: Coins, tone: 'gold' },
  relief: {
    label: 'Relief for the needy',
    icon: HeartHandshake,
    tone: 'success',
  },
  rebuilding: { label: 'Rebuilding', icon: Hammer, tone: 'info' },
  monopoly: { label: 'Monopoly trade', icon: Gem, tone: 'gold' },
}

export const MEMBER_TYPES: Record<string, Named> = {
  people: { label: 'People', icon: Users, tone: 'info' },
  settlement: { label: 'Settlement', icon: Castle, tone: 'gold' },
  tribe: { label: 'Tribe', icon: Flag, tone: 'success' },
  polity: { label: 'Realm', icon: Crown, tone: 'gold' },
}

export const TINCTURES: Record<string, Named> = {
  gules: { label: 'Gules', icon: Shield, tone: 'danger' },
  or: { label: 'Or', icon: Shield, tone: 'gold' },
  azure: { label: 'Azure', icon: Shield, tone: 'info' },
  vert: { label: 'Vert', icon: Shield, tone: 'success' },
  sable: { label: 'Sable', icon: Shield, tone: 'muted' },
  argent: { label: 'Argent', icon: Shield, tone: 'muted' },
  purpure: { label: 'Purpure', icon: Shield, tone: 'verdigris' },
}

export const REALM_FIELDS: Record<string, string> = {
  government: 'Government',
  decision_rule: 'Who decides',
  legitimacy: 'Legitimacy',
  stability: 'Stability',
  treasury: 'Treasury',
  debt: 'Debt',
  war_weariness: 'War weariness',
  standing: 'Standing',
}

export type Band = { label: string; tone: KpiTone }

const QUARTERS = [25, 50, 75]

function quarter(value: number): number {
  return QUARTERS.filter((edge) => value >= edge).length
}

export function goodBand(
  value: number,
  words: [string, string, string, string]
): Band {
  const index = quarter(value)
  const tones: KpiTone[] = ['danger', 'warning', 'gold', 'success']
  return { label: words[index], tone: tones[index] }
}

export function badBand(
  value: number,
  words: [string, string, string, string]
): Band {
  const index = quarter(value)
  const tones: KpiTone[] = ['success', 'gold', 'warning', 'danger']
  return { label: words[index], tone: tones[index] }
}

export function badgeVariant(
  tone: KpiTone | undefined
): 'default' | 'secondary' | 'success' | 'warning' | 'destructive' | 'info' {
  if (tone === 'gold') return 'default'
  if (tone === 'success') return 'success'
  if (tone === 'warning') return 'warning'
  if (tone === 'danger') return 'destructive'
  if (tone === 'info' || tone === 'verdigris') return 'info'
  return 'secondary'
}

export function sentence(value: string): string {
  return plain({}, value)
}

export function labels(table: Record<string, Named>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(table).map(([key, value]) => [key, value.label])
  )
}

import {
  Building2,
  Coins,
  Archive,
  Bell,
  BookOpen,
  ChartColumnBig,
  Cpu,
  Eye,
  FileText,
  Crown,
  Gamepad2,
  HandHeart,
  Hourglass,
  ImagePlus,
  Images,
  Languages,
  Layers,
  LibraryBig,
  LayoutDashboard,
  type LucideIcon,
  Map as MapIcon,
  NotebookPen,
  Orbit,
  Palette,
  Scale,
  ScrollText,
  Settings,
  Shapes,
  Share2,
  SlidersHorizontal,
  Sparkles,
  Speech,
  Swords,
  SunMoon,
  Target,
  UsersRound,
  WalletCards,
  Waypoints,
  Wrench,
} from 'lucide-react'

export type NavRoute =
  | '/overview'
  | '/epoch'
  | '/pantheon'
  | '/cards'
  | '/goals'
  | '/council'
  | '/presence'
  | '/prayers'
  | '/cosmos'
  | '/heavens'
  | '/map'
  | '/cities'
  | '/atlas'
  | '/network'
  | '/interconnections'
  | '/wars'
  | '/economy'
  | '/kinds'
  | '/chronicle'
  | '/languages'
  | '/gallery'
  | '/library'
  | '/ledger'
  | '/usage'
  | '/notifications'
  | '/settings/appearance'
  | '/settings/game'
  | '/settings/records'
  | '/settings/data'
  | '/settings/world-rules'
  | '/settings/engine'
  | '/settings/fate'
  | '/settings/prompts'
  | '/settings/maintenance'
  | '/settings/images'
  | '/design'
  | '/genesis'

export type NavItem = {
  id: string
  title: string
  to: NavRoute
  icon: LucideIcon
  description: string
  shortcut?: string
}

export type NavSection = NavItem & {
  children?: NavItem[]
}

export type NavGroup = {
  title: string
  items: NavSection[]
}

export const SETTINGS_TABS: NavItem[] = [
  {
    id: 'settings-appearance',
    title: 'Appearance',
    to: '/settings/appearance',
    icon: SunMoon,
    description: 'Theme, font and motion preferences for this browser.',
  },
  {
    id: 'settings-game',
    title: 'Game',
    to: '/settings/game',
    icon: Gamepad2,
    description: 'Fate, sons, councils, mortal agents and guide settings.',
  },
  {
    id: 'settings-records',
    title: 'Records',
    to: '/settings/records',
    icon: NotebookPen,
    description: 'Model metrics, book and codex exports.',
  },
  {
    id: 'settings-data',
    title: 'Data',
    to: '/settings/data',
    icon: Archive,
    description: 'Backups, import, export, health and world reset.',
  },
  {
    id: 'settings-world-rules',
    title: 'World rules',
    to: '/settings/world-rules',
    icon: SlidersHorizontal,
    description: 'Every tunable number of the world, grouped and searchable.',
  },
  {
    id: 'settings-engine',
    title: 'Engine',
    to: '/settings/engine',
    icon: Cpu,
    description:
      'Switch world-engine steps on or off, run one now, and check integrity.',
  },
  {
    id: 'settings-fate',
    title: 'Fate',
    to: '/settings/fate',
    icon: Scale,
    description:
      "Fate's debt, limbo, retries, overruled verdicts and historian accounts.",
  },
  {
    id: 'settings-prompts',
    title: 'Prompts',
    to: '/settings/prompts',
    icon: FileText,
    description:
      'Son prompts, context blocks, the prompt catalogue and recurring images.',
  },
  {
    id: 'settings-images',
    title: 'Images',
    to: '/settings/images',
    icon: ImagePlus,
    description: 'Bulk image generation, missing images and the image worker.',
  },
  {
    id: 'settings-maintenance',
    title: 'Maintenance',
    to: '/settings/maintenance',
    icon: Wrench,
    description: 'Missing content, writing jobs and every housekeeping task.',
  },
]

export const NAV_GROUPS: NavGroup[] = [
  {
    title: 'Pantheon',
    items: [
      {
        id: 'overview',
        title: 'Overview',
        to: '/overview',
        icon: LayoutDashboard,
        description: 'The state of your cosmos at a glance.',
        shortcut: '1',
      },
      {
        id: 'epoch',
        title: 'Epoch',
        to: '/epoch',
        icon: Hourglass,
        description: 'Run, stop and resume the epoch, or let one son act.',
        shortcut: '2',
      },
      {
        id: 'pantheon',
        title: 'Pantheon',
        to: '/pantheon',
        icon: Crown,
        description: 'Your sons, their cards, storylines and rivalries.',
        shortcut: '3',
      },
      {
        id: 'cards',
        title: 'Cards',
        to: '/cards',
        icon: WalletCards,
        description:
          'Every god, mortal, beast, spirit and being as a collectible card: search, swipe, turn over and save.',
      },
      {
        id: 'prayers',
        title: 'Prayers',
        to: '/prayers',
        icon: HandHeart,
        description: 'Wishes from sons and mortals awaiting your answer.',
        shortcut: '4',
      },
      {
        id: 'council',
        title: 'Council',
        to: '/council',
        icon: UsersRound,
        description: 'Councils of the pantheon and their verdicts.',
      },
      {
        id: 'presence',
        title: 'Summon to Presence',
        to: '/presence',
        icon: Speech,
        description:
          'Call any son, foreign god, mortal, spirit, being or beast that can speak, living or dead, and speak with it one to one.',
      },
      {
        id: 'goals',
        title: 'Goals',
        to: '/goals',
        icon: Target,
        description: 'Scenario goals, score and achievements.',
      },
    ],
  },
  {
    title: 'World',
    items: [
      {
        id: 'cosmos',
        title: 'Cosmos',
        to: '/cosmos',
        icon: Orbit,
        description: 'Stars, worlds, routes, voyages and foreign gods.',
        shortcut: '5',
      },
      {
        id: 'heavens',
        title: 'Heavens',
        to: '/heavens',
        icon: Layers,
        description:
          'Dimensions, clusters, galaxies, rifts, cosmic beings and phenomena.',
      },
      {
        id: 'map',
        title: 'Map',
        to: '/map',
        icon: MapIcon,
        description: 'Regions, settlements, peoples, roads and wars.',
        shortcut: '6',
      },
      {
        id: 'cities',
        title: 'Cities',
        to: '/cities',
        icon: Building2,
        description:
          'Every town on its hexes and every land on its tiles, drawn from the engine, with the god’s hand on each.',
      },
      {
        id: 'atlas',
        title: 'Atlas',
        to: '/atlas',
        icon: BookOpen,
        description: 'Every record of the world, by type and family.',
        shortcut: '7',
      },
      {
        id: 'network',
        title: 'Network',
        to: '/network',
        icon: Waypoints,
        description: 'The knowledge graph of records and their bonds.',
        shortcut: '8',
      },
      {
        id: 'interconnections',
        title: 'Interconnections',
        to: '/interconnections',
        icon: Share2,
        description:
          'How every mechanic feeds the others: the subsystem matrix and the links of each mechanic.',
      },
      {
        id: 'wars',
        title: 'Wars',
        to: '/wars',
        icon: Swords,
        description: 'Wars, armies, battles, sieges, captives and tributes.',
      },
      {
        id: 'economy',
        title: 'Economy',
        to: '/economy',
        icon: Coins,
        description:
          'Trade routes, market prices, materials, coins, loans and debts.',
      },
      {
        id: 'kinds',
        title: 'Kinds',
        to: '/kinds',
        icon: Shapes,
        description:
          'Every kind of thing the peoples make and hold: goods, dishes, drinks, dress, crafts, games, professions and more.',
      },
    ],
  },
  {
    title: 'History',
    items: [
      {
        id: 'chronicle',
        title: 'Chronicle',
        to: '/chronicle',
        icon: ScrollText,
        description: 'Epoch by epoch, the history Fate has written.',
        shortcut: '9',
      },
      {
        id: 'languages',
        title: 'Languages',
        to: '/languages',
        icon: Languages,
        description: 'Dictionaries, language families and knowledge.',
        shortcut: '0',
      },
      {
        id: 'gallery',
        title: 'Gallery',
        to: '/gallery',
        icon: Images,
        description: 'Every image of the world and the missing ones.',
      },
      {
        id: 'library',
        title: 'Library',
        to: '/library',
        icon: LibraryBig,
        description:
          'Every writing of the Divine Will, with its versions, its subjects and its exports.',
      },
    ],
  },
  {
    title: 'Records',
    items: [
      {
        id: 'ledger',
        title: 'Ledger',
        to: '/ledger',
        icon: NotebookPen,
        description: 'Your actions with undo, notes and bookmarks.',
      },
      {
        id: 'usage',
        title: 'Usage',
        to: '/usage',
        icon: ChartColumnBig,
        description:
          'Token usage of every language model call: trends, breakdowns and the full call log.',
      },
      {
        id: 'notifications',
        title: 'Notifications',
        to: '/notifications',
        icon: Bell,
        description: 'What happened while you were away.',
      },
    ],
  },
  {
    title: 'System',
    items: [
      {
        id: 'settings',
        title: 'Settings',
        to: '/settings/appearance',
        icon: Settings,
        description: 'Preferences, game options, data and world rules.',
        children: SETTINGS_TABS,
      },
      {
        id: 'design',
        title: 'Design reference',
        to: '/design',
        icon: Palette,
        description: 'Every component and text role in both themes.',
      },
    ],
  },
]

export const GENESIS_ITEM: NavItem = {
  id: 'genesis',
  title: 'Genesis',
  to: '/genesis',
  icon: Sparkles,
  description: 'Create a new world, its Creator and the first sons.',
}

export function allNavItems(): NavItem[] {
  return [
    ...NAV_GROUPS.flatMap((group) =>
      group.items.flatMap((item) => [item, ...(item.children ?? [])])
    ),
    GENESIS_ITEM,
  ]
}

export type PanelShortcut = {
  id: string
  title: string
  key: string
  keys: string
  icon: LucideIcon
}

export const DIVINE_WILL_SHORTCUT: PanelShortcut = {
  id: 'divine-will',
  title: 'Open or close the Divine Will',
  key: 'w',
  keys: 'W',
  icon: Eye,
}

export const PANEL_SHORTCUTS: PanelShortcut[] = [DIVINE_WILL_SHORTCUT]

export function isDivineWillKey(key: string): boolean {
  return key === DIVINE_WILL_SHORTCUT.key
}

export const SHORTCUT_KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']

export function shortcutItems(): NavItem[] {
  return allNavItems()
    .filter((item) => item.shortcut !== undefined)
    .sort(
      (left, right) =>
        SHORTCUT_KEYS.indexOf(left.shortcut ?? '') -
        SHORTCUT_KEYS.indexOf(right.shortcut ?? '')
    )
}

export function navItem(id: string): NavItem {
  const found = allNavItems().find((item) => item.id === id)
  if (!found) throw new Error(`Unknown navigation item: ${id}`)
  return found
}

export function isNavItemActive(pathname: string, item: NavItem): boolean {
  return pathname === item.to || pathname.startsWith(`${item.to}/`)
}

import {
  Atom,
  BookOpenText,
  Box,
  Crown,
  Database,
  Fingerprint,
  HandHeart,
  Hourglass,
  ImagePlus,
  Infinity as InfinityIcon,
  Languages,
  Layers,
  type LucideIcon,
  Orbit,
  ScrollText,
  Sparkles,
  Swords,
  Waypoints,
  Wind,
  Zap,
} from 'lucide-react'

export type GamePillar = {
  title: string
  body: string
  icon: LucideIcon
}

export type TechRune = {
  name: string
  role: string
  icon: LucideIcon
}

export const GAME_TAGLINE =
  'You are the Creator. Your sons are gods. The Void is listening.'

export const GAME_PITCH =
  'Weavers of the Void is a self-generating lore engine. You rule as the Creator while your sons, living god cards, wake once per epoch as AI agents to scheme, pray and wage war. Between their turns a deterministic engine weaves the world forward, so no two cosmoses ever tell the same story.'

export const GAME_PILLARS: readonly GamePillar[] = [
  {
    title: 'Raise a Pantheon',
    body: 'Summon sons as god cards, from common sparks to mythic titans.',
    icon: Crown,
  },
  {
    title: 'Turn the Epochs',
    body: 'Each epoch the gods act, and the world answers.',
    icon: Hourglass,
  },
  {
    title: 'Shape the Cosmos',
    body: 'Stars, worlds, routes and voyages drawn from nothing.',
    icon: Orbit,
  },
  {
    title: 'Watch Wars Ignite',
    body: 'Rivalries boil over into wars that rewrite the map.',
    icon: Swords,
  },
  {
    title: 'Hear New Tongues',
    body: 'Peoples grow their own languages, names and words.',
    icon: Languages,
  },
  {
    title: 'Read the Chronicle',
    body: 'Every deed lands in a living chronicle and gallery.',
    icon: ScrollText,
  },
]

export const CREATOR_PATH: readonly GamePillar[] = [
  {
    title: 'Speak the Seed',
    body: 'Genesis turns a single idea into a cosmology, a world and its first peoples.',
    icon: Sparkles,
  },
  {
    title: 'Summon Your Sons',
    body: 'Draw god cards. Each son brings a domain, a temper and a rarity.',
    icon: Crown,
  },
  {
    title: 'Turn the Epoch',
    body: 'The sons act as AI agents, then the engine simulates decades of history.',
    icon: Hourglass,
  },
  {
    title: 'Answer Prayers',
    body: 'Sons and mortals beg for miracles. Grant them, refuse them or stay silent.',
    icon: HandHeart,
  },
  {
    title: 'Read What Was Woven',
    body: 'Chronicles, maps, tongues and portraits remember every age.',
    icon: BookOpenText,
  },
]

export const RARITY_LADDER_TEXT =
  'Every son is drawn at a rarity. Common sparks must fight for every follower; mythic titans bend the world around them.'

export const TECH_RUNES: readonly TechRune[] = [
  { name: 'Claude Agent SDK', role: 'The minds of the gods', icon: Sparkles },
  { name: 'FastAPI', role: 'The engine heart', icon: Zap },
  { name: 'SQLite', role: 'The eternal ledger', icon: Database },
  { name: 'React', role: 'The window', icon: Atom },
  { name: 'TanStack', role: 'Routes and memory', icon: Layers },
  { name: 'Three.js', role: 'Stars in 3D', icon: Box },
  { name: 'Tailwind CSS', role: 'The robes', icon: Wind },
  { name: 'MLX & Diffusers', role: 'The painters', icon: ImagePlus },
]

export const VISION_TITLE = 'The Deepest World Ever Woven'

export const VISION_MANIFESTO = [
  'Weavers of the Void exists to build the deepest, most interconnected fantasy universe ever simulated. Deeper than any game world. Richer than any written canon.',
  'Not a backdrop of flavour text, but a living web: every god, mortal, war, tongue, relic and prophecy is bound to the rest, and every thread can be pulled back to the moment it was spun.',
]

export const VISION_VOWS: readonly GamePillar[] = [
  {
    title: 'Depth beyond canon',
    body: 'Every record carries history, motive and consequence, layered epoch after epoch until it outgrows any written lore.',
    icon: InfinityIcon,
  },
  {
    title: 'Everything is connected',
    body: 'A war reshapes a language. A prayer births a cult. A relic outlives the god who forged it.',
    icon: Waypoints,
  },
  {
    title: 'Never scripted',
    body: 'Seeded by one idea, simulated by an engine, narrated by gods. No two cosmoses will ever repeat.',
    icon: Fingerprint,
  },
]

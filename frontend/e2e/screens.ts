import { NAV_GROUPS, GENESIS_ITEM } from '../src/config/navigation'

export type Screen = {
  name: string
  path: string
  openPalette?: boolean
  toggleSidebar?: boolean
  mock?: 'empty' | 'llm-off' | 'discovery'
  recordsTab?: string
  interact?: readonly Interaction[]
}

export type Interaction =
  | { choose: { field: string; option: string } }
  | { click: string }
  | { see: string }
  | { fill: { field: string; value: string } }
  | { upload: { field: string; name: string } }

const navScreens: Screen[] = NAV_GROUPS.flatMap((group) =>
  group.items.flatMap((item) => [item, ...(item.children ?? [])])
).map((item) => ({ name: item.id, path: item.to }))

export const SCREENS: Screen[] = [
  ...navScreens,
  { name: GENESIS_ITEM.id, path: GENESIS_ITEM.to },
  { name: 'settings-index', path: '/settings' },
  { name: 'not-found', path: '/missing-page' },
  { name: 'drawer-son', path: '/pantheon?drawer=son:7' },
  { name: 'drawer-creator', path: '/pantheon?drawer=creator' },
  { name: 'drawer-foreign-god', path: '/pantheon?drawer=foreign-god:3' },
  { name: 'drawer-stack', path: '/atlas?drawer=entity:42,foreign-god:3' },
  { name: 'ledger-notes', path: '/ledger', recordsTab: 'notes' },
  { name: 'drawer-dead-son', path: '/pantheon?drawer=son:10' },
  { name: 'drawer-help', path: '/?drawer=help' },
  { name: 'drawer-entity-settlement', path: '/chronicle?drawer=entity:43' },
  { name: 'drawer-entity-mortal', path: '/languages?drawer=entity:45' },
  { name: 'atlas-detail', path: '/atlas?select=entity:43' },
  { name: 'atlas-list', path: '/atlas?view=list&select=entity:42' },
  { name: 'atlas-search', path: '/atlas?q=glass' },
  { name: 'chronicle-open', path: '/chronicle?all=true' },
  { name: 'chronicle-search', path: '/chronicle?q=glass' },
  { name: 'languages-tree', path: '/languages?view=tree&language=47' },
  { name: 'languages-knowledge', path: '/languages?view=knowledge' },
  { name: 'map-past', path: '/map?epoch=8' },
  { name: 'network-focus', path: '/network?focus=10' },
  { name: 'cosmos-world', path: '/cosmos?world=5' },
  { name: 'cosmos-voyages', path: '/cosmos?panel=voyages' },
  { name: 'cosmos-gods', path: '/cosmos?panel=gods' },
  { name: 'cosmos-command', path: '/cosmos?panel=command' },
  { name: 'cosmos-star', path: '/cosmos?panel=star&star=10' },
  { name: 'drawer-world-guide', path: '/cosmos?drawer=world-guide:3' },
  { name: 'wars-captives', path: '/wars?tab=captives' },
  { name: 'wars-tributes', path: '/wars?tab=tributes' },
  { name: 'wars-focus', path: '/wars?war=1' },
  {
    name: 'cosmos-command-economy',
    path: '/cosmos?panel=command',
    interact: [{ click: 'Economy: resources, deposits and cravings' }, { see: 'Addicted communities' }],
  },
  { name: 'cosmos-star-burning', path: '/cosmos?panel=star&star=2' },
  {
    name: 'cosmos-world-geography',
    path: '/cosmos?world=3',
    interact: [{ click: 'Geography as the sons and mortals read it' }, { see: 'Known regions: 3.' }],
  },
  {
    name: 'languages-shape',
    path: '/languages?view=tree&language=47',
    interact: [{ click: 'Sound out names' }, { see: 'Ashkareth' }],
  },
  { name: 'command-palette', path: '/', openPalette: true },
  { name: 'genesis-wizard', path: '/genesis', mock: 'empty' },
  { name: 'genesis-llm-off', path: '/genesis', mock: 'llm-off' },
  { name: 'discovery-mode', path: '/settings/data', mock: 'discovery' },
  { name: 'drawer-son-half-turn', path: '/pantheon?drawer=son:9' },
  { name: 'epoch-star-popover', path: '/', interact: [{ click: 'Star of the epoch' }] },
  { name: 'map-epoch-star', path: '/map' },
  { name: 'cosmos-dialect', path: '/cosmos?world=3', interact: [{ click: 'Its dialect' }, { see: 'Names born here' }] },
  { name: 'chronicle-kinds', path: '/chronicle', interact: [{ click: 'Kinds ·' }] },
  { name: 'chronicle-line-menu', path: '/chronicle?all=true', interact: [{ click: 'Line actions' }] },
  {
    name: 'genesis-first-sons',
    path: '/genesis',
    mock: 'empty',
    interact: [
      { click: 'Dark fantasy' },
      { click: 'Next' },
      { fill: { field: 'Name of the Creator', value: 'Aeron' } },
      { click: 'Next' },
      { click: 'Next' },
      { choose: { field: 'Number of first sons', option: '4' } },
      { choose: { field: 'Rarity of son 4', option: 'Epic' } },
    ],
  },
  {
    name: 'settings-merge-explained',
    path: '/settings/data',
    interact: [{ choose: { field: 'How it opens', option: 'Merge: add its entities and places to your world' } }],
  },
  {
    name: 'settings-merge-result',
    path: '/settings/data',
    interact: [
      { choose: { field: 'How it opens', option: 'Merge: add its entities and places to your world' } },
      { upload: { field: 'Package', name: 'ember-hollow.aerona' } },
      { click: 'Merge into my world' },
      { fill: { field: 'Type MERGE to confirm', value: 'MERGE' } },
      { click: 'Merge into my world' },
      { see: 'Rows added per table' },
    ],
  },
  { name: 'settings-prompts-son', path: '/settings/prompts?son=7' },
  { name: 'settings-prompts-blocks', path: '/settings/prompts?view=blocks' },
  { name: 'settings-prompts-catalogue', path: '/settings/prompts?view=catalogue', interact: [{ click: 'fate_judgment_user' }, { see: 'Template source' }] },
  { name: 'settings-prompts-motifs', path: '/settings/prompts?view=motifs' },
  { name: 'settings-fate-override', path: '/settings/fate', interact: [{ click: 'Reject' }, { see: 'Your reason' }] },
  { name: 'settings-maintenance-run', path: '/settings/maintenance', interact: [{ click: 'Run now' }, { click: 'Run now' }, { see: 'Notifications 12' }] },
  { name: 'settings-maintenance-llm-off', path: '/settings/maintenance', mock: 'llm-off' },
  { name: 'sidebar-toggled', path: '/settings/appearance', toggleSidebar: true },
]

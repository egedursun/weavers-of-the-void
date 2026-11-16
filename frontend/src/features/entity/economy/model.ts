import { Shapes } from 'lucide-react'
import { type KpiTone } from '@/components/domain'
import { useGodGate } from '@/features/pantheon/gate'
import { useWorldMaterials } from './api'
import {
  BRANCH_LABEL,
  type KnowledgeBranch,
  MATERIAL_FAMILY,
  MATERIAL_KINDS,
  MATERIAL_LABEL,
  type MaterialKind,
  type Named,
  branch,
} from './labels'

export const WORKING = 'Working…'
export const NONE = 'none'

const ICON_TONE: Record<KpiTone, string> = {
  gold: 'text-primary',
  verdigris: 'text-brand-verdigris',
  info: 'text-info',
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-destructive',
  muted: 'text-muted-foreground',
}

export function iconTone(tone: KpiTone): string {
  return ICON_TONE[tone]
}

export function whole(value: string, max?: number, min = 0): number {
  const parsed = Math.round(Number(value) || 0)
  return Math.max(min, max === undefined ? parsed : Math.min(max, parsed))
}

export function useBusy(
  readOnlyReason: string | null | undefined,
  ...pending: boolean[]
): string | null {
  const { reason } = useGodGate()
  return readOnlyReason ?? reason() ?? (pending.some(Boolean) ? WORKING : null)
}

export function branchChoices(noneLabel: string): Record<string, Named> {
  return {
    [NONE]: { ...branch('trade'), label: noneLabel, tone: 'muted' },
    ...Object.fromEntries(
      (Object.keys(BRANCH_LABEL) as KnowledgeBranch[]).map((key) => [
        key,
        branch(key),
      ])
    ),
  }
}

export type MaterialRef = {
  material: MaterialKind | null
  world_material_id: number | null
}

export function materialKey(ref: MaterialRef): string {
  if (ref.world_material_id !== null) return `sub:${ref.world_material_id}`
  if (ref.material !== null) return `kind:${ref.material}`
  return NONE
}

export function materialRef(key: string): MaterialRef {
  if (key.startsWith('sub:'))
    return { material: null, world_material_id: Number(key.slice(4)) }
  if (key.startsWith('kind:'))
    return { material: key.slice(5) as MaterialKind, world_material_id: null }
  return { material: null, world_material_id: null }
}

export function useMaterialChoices(
  worldId: number | null,
  only?: readonly MaterialKind[]
): Record<string, Named> {
  const view = useWorldMaterials(worldId)
  const rows = view.data?.materials ?? []
  const allowed = only ? new Set<MaterialKind>(only) : null
  const fits = (kind: MaterialKind | null | undefined) =>
    allowed === null ||
    (kind !== null && kind !== undefined && allowed.has(kind))
  const choices: Record<string, Named> = {}
  const listed = new Set<MaterialKind>()
  for (const row of rows) {
    if (!fits(row.kind ?? row.base_kind)) continue
    const family = MATERIAL_FAMILY[row.family]
    if (row.kind !== null) listed.add(row.kind)
    choices[
      materialKey({
        material: row.kind,
        world_material_id: row.world_material_id,
      })
    ] = { label: row.label, icon: family.icon, tone: family.tone }
  }
  for (const kind of only ?? MATERIAL_KINDS) {
    if (listed.has(kind)) continue
    choices[`kind:${kind}`] = {
      label: MATERIAL_LABEL[kind],
      icon: Shapes,
      tone: 'muted',
    }
  }
  return choices
}

export function useKindChoices(
  worldId: number | null,
  only?: readonly MaterialKind[]
): Record<string, Named> {
  const choices = useMaterialChoices(worldId, only)
  return Object.fromEntries(
    Object.entries(choices)
      .filter(([key]) => key.startsWith('kind:'))
      .map(([key, item]) => [key.slice(5), item])
  )
}

export const FORM_CARD =
  '@container/form flex min-w-0 flex-col gap-4 rounded-md p-4 sealed-well'

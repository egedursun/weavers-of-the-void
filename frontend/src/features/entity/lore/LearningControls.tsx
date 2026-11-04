import { useState } from 'react'
import { EyeOff, GraduationCap, Save, Shapes, Unlock } from 'lucide-react'
import { knowledgeBranchValues } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Label, Muted, Text } from '@/components/typography'
import { AdjustBlock, ChoicePicker } from './LoreFields'
import { type LearningCard } from './api'
import { KindForge } from './forge/KindForge'
import { useCustomKinds } from './forge/kindApi'
import { PERCENT, branchOf, busyOf } from './model'
import { useLoreAction } from './panels/controlParts'

const BRANCHES = Object.fromEntries(
  knowledgeBranchValues.map((branch) => [branch, branchOf(branch)])
)

export function LearningShaping({
  holderId,
  card,
  blocked,
}: {
  holderId: number
  card: LearningCard
  blocked: string | null
}) {
  const [branch, setBranch] = useState<string>(card.levels[0]?.branch ?? '')
  const current = card.levels.find((item) => item.branch === branch)
  const [practitioners, setPractitioners] = useState('')
  const [progress, setProgress] = useState('')
  const [secret, setSecret] = useState(current?.secret ?? false)
  const kinds = useCustomKinds('technique')
  const edit = useLoreAction<{
    values: Record<string, number | boolean>
    release: string[]
  }>('/api/actions/research:holder', (value) => ({
    holder_id: holderId,
    branch,
    values: value.values,
    release: value.release,
  }))
  const custom = useLoreAction<{ kind: number; held: boolean }>(
    '/api/actions/research:custom_technique',
    (value) => ({
      holder_id: holderId,
      kind_id: value.kind,
      held: value.held,
      secret: false,
    })
  )
  const busy = busyOf(blocked, edit.isPending, custom.isPending)
  const values: Record<string, number | boolean> = { secret }
  if (practitioners !== '')
    values.practitioners = Math.max(0, Math.round(Number(practitioners)))
  if (progress !== '')
    values.progress = Math.max(
      0,
      Math.min(PERCENT, Math.round(Number(progress)))
    )
  const held = new Set(card.custom_techniques.map((item) => item.kind_id))
  return (
    <div
      data-surface='LearningControls'
      className='flex min-w-0 flex-col gap-3'
    >
      <AdjustBlock
        title='Shape a branch of their learning'
        icon={GraduationCap}
      >
        <ChoicePicker
          label='Branch'
          value={branch}
          table={BRANCHES}
          blocked={busy}
          placeholder='Choose a branch'
          onPick={setBranch}
        />
        {current && (
          <Muted variant='caption'>{`Level ${current.level} of a frontier at ${current.frontier}, ${current.progress}% toward the next, ${current.practitioners} practitioners.`}</Muted>
        )}
        <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'>
          <div className='flex min-w-0 flex-col gap-1'>
            <Label>Practitioners</Label>
            <Input
              type='number'
              min={0}
              aria-label='Practitioners'
              value={practitioners}
              placeholder={String(current?.practitioners ?? 0)}
              onChange={(event) => setPractitioners(event.target.value)}
            />
          </div>
          <div className='flex min-w-0 flex-col gap-1'>
            <Label>Progress (0–100)</Label>
            <Input
              type='number'
              min={0}
              max={PERCENT}
              aria-label='Progress'
              value={progress}
              placeholder={String(current?.progress ?? 0)}
              onChange={(event) => setProgress(event.target.value)}
            />
          </div>
          <label className='flex min-w-0 items-center gap-2'>
            <Switch
              checked={secret}
              aria-label='Kept secret'
              onCheckedChange={setSecret}
            />
            <Text as='span'>Kept secret</Text>
          </label>
        </div>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={busy !== null || branch === ''}
            disabledReason={
              busy ?? (branch === '' ? 'Choose a branch' : undefined)
            }
            onClick={() => edit.mutate({ values, release: [] })}
          >
            <Save />
            Hold it so
          </Button>
          {current && current.locked.length > 0 && (
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() =>
                edit.mutate({ values: {}, release: [...current.locked] })
              }
            >
              <Unlock />
              Let the world decide again
            </Button>
          )}
          {current?.secret && (
            <Badge variant='outline'>
              <EyeOff aria-hidden='true' />
              Kept secret
            </Badge>
          )}
        </div>
      </AdjustBlock>
      <AdjustBlock title='Techniques of your own making' icon={Shapes}>
        {(kinds.data?.kinds ?? []).length === 0 && (
          <Muted variant='caption'>
            Name a technique of your own below first.
          </Muted>
        )}
        <div className='flex min-w-0 flex-wrap gap-2'>
          {(kinds.data?.kinds ?? []).map((kind) => (
            <Button
              key={kind.id}
              size='sm'
              variant={held.has(kind.id) ? 'default' : 'outline'}
              aria-pressed={held.has(kind.id)}
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() =>
                custom.mutate({ kind: kind.id, held: !held.has(kind.id) })
              }
            >
              <Shapes />
              {kind.name}
            </Button>
          ))}
        </div>
      </AdjustBlock>
      <KindForge catalog='technique' />
    </div>
  )
}

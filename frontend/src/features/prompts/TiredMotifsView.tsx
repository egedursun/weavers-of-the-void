import { useId, useMemo, useState } from 'react'
import {
  Ban,
  Check,
  Eraser,
  Globe2,
  Images,
  Orbit,
  Pin,
  Plus,
  Repeat,
} from 'lucide-react'
import { toast } from 'sonner'
import { type ActProp } from '@/api/mutation'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  EmptyState,
  Medallion,
  Paged,
  PagedList,
  Section,
  StatBar,
} from '@/components/domain'
import { type Choice, ChoiceTiles } from '@/components/domain/SettingsKit'
import { Muted, Text } from '@/components/typography'
import { useNames } from '@/features/pantheon/api'
import { useGodGate } from '@/features/pantheon/gate'
import {
  type MotifChange,
  type MotifOverrideMode,
  type TiredMotifReport,
  useSetMotifOverride,
  useTiredMotifs,
} from './api'

const EVERY_WORLD = 'every'
const PERCENT_MAX = 100
const MOTIF_KEY_MAX = 120

const MODES: readonly Choice<MotifOverrideMode>[] = [
  {
    value: 'pinned',
    label: 'Always tired',
    hint: 'Fate always holds it back',
    icon: Pin,
  },
  {
    value: 'allowed',
    label: 'Never tired',
    hint: 'Fate stops refusing it',
    icon: Ban,
  },
]

const MODE_LABEL: Record<MotifOverrideMode, string> = {
  pinned: 'Always tired',
  allowed: 'Never tired',
}

const SAVED: Record<string, string> = {
  pinned: 'Pinned as tired',
  allowed: 'Allowed again',
  cleared: 'Override cleared',
}

function useWorldOptions() {
  const names = useNames()
  return useMemo(
    () => (names.data ?? []).filter((entry) => entry.kind === 'world'),
    [names.data]
  )
}

const COUNTED = 'counted'

function MotifActions({
  motif,
  mode,
  blocked,
  pending,
  onChange,
  act,
}: {
  motif: string
  mode: MotifOverrideMode | null
  blocked: string | null
  pending: boolean
  onChange: (motif: string, mode: MotifOverrideMode | null) => void
  act?: ActProp
}) {
  return (
    <ToggleGroup
      act={act}
      type='single'
      variant='outline'
      size='sm'
      aria-label={`How Fate treats ${motif}`}
      title={blocked ?? undefined}
      disabled={blocked !== null || pending}
      value={mode ?? COUNTED}
      onValueChange={(value) => {
        if (!value) return
        const next = value === COUNTED ? null : (value as MotifOverrideMode)
        if (next !== mode) onChange(motif, next)
      }}
    >
      <ToggleGroupItem value={COUNTED}>
        <Repeat />
        Counted
      </ToggleGroupItem>
      <ToggleGroupItem value='pinned'>
        <Pin />
        Pinned
      </ToggleGroupItem>
      <ToggleGroupItem value='allowed'>
        <Check />
        Allowed
      </ToggleGroupItem>
    </ToggleGroup>
  )
}

function MotifList({
  report,
  blocked,
  pending,
  onChange,
  act,
}: {
  report: TiredMotifReport
  blocked: string | null
  pending: boolean
  onChange: (motif: string, mode: MotifOverrideMode | null) => void
  act?: ActProp
}) {
  const modes = new Map(report.overrides.map((item) => [item.motif, item.mode]))
  if (report.motifs.length === 0)
    return (
      <EmptyState
        size='compact'
        icon={Repeat}
        title='No tired motifs'
        description='No motif has been used often enough to be held back.'
      />
    )
  return (
    <ul className='flex min-w-0 flex-col'>
      <Paged items={report.motifs} as='li'>
        {(motif) => (
          <li
            key={motif.key}
            data-motif={motif.key}
            className='flex min-w-0 flex-wrap items-center gap-x-4 gap-y-2 border-b py-3 last:border-b-0'
          >
            <div className='flex min-w-0 flex-1 basis-60 flex-col gap-1'>
              <StatBar
                label={motif.key}
                value={motif.percent / PERCENT_MAX}
                max={1}
                format='percent'
                showMax={false}
                tone={motif.pinned ? 'warning' : 'default'}
              />
            </div>
            <MotifActions
              act={act}
              motif={motif.key}
              mode={modes.get(motif.key) ?? null}
              blocked={blocked}
              pending={pending}
              onChange={onChange}
            />
          </li>
        )}
      </Paged>
    </ul>
  )
}

function AddOverride({
  blocked,
  pending,
  onAdd,
  act,
}: {
  blocked: string | null
  pending: boolean
  onAdd: (motif: string, mode: MotifOverrideMode) => void
  act?: ActProp
}) {
  const inputId = useId()
  const [motif, setMotif] = useState('')
  const [mode, setMode] = useState<MotifOverrideMode>('pinned')
  const key = motif.trim()
  const reason =
    blocked ?? (pending ? 'Saving.' : key === '' ? 'Type a motif key.' : null)
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-md p-3 sealed-well'>
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={Plus} tone='gold' size='sm' />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <FieldLabel htmlFor={inputId}>Add an override</FieldLabel>
          <Muted variant='caption'>
            Pin a motif so Fate always holds it back, or allow one it keeps
            refusing.
          </Muted>
        </div>
      </div>
      <Input
        id={inputId}
        value={motif}
        maxLength={MOTIF_KEY_MAX}
        placeholder='A motif key'
        onChange={(event) => setMotif(event.target.value)}
      />
      <ChoiceTiles
        label='Override mode'
        value={mode}
        options={MODES}
        onChange={setMode}
        columns={2}
      />
      <Button
        act={act}
        className='self-end'
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
        onClick={() => {
          onAdd(key, mode)
          setMotif('')
        }}
      >
        <Pin />
        Save the override
      </Button>
    </div>
  )
}

export function TiredMotifsView() {
  const worlds = useWorldOptions()
  const { reason } = useGodGate()
  const [worldId, setWorldId] = useState<number | null>(null)
  const report = useTiredMotifs(worldId)
  const save = useSetMotifOverride()
  const blocked = reason()
  const change = (motif: string, mode: MotifOverrideMode | null) => {
    const request: MotifChange = { motif, mode, worldId }
    save.mutate(request, {
      onSuccess: () => toast.success(`${SAVED[mode ?? 'cleared']}: ${motif}`),
      onError: (error) => toast.error(error.message),
    })
  }
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <ChoiceTiles
        label='World'
        value={worldId === null ? EVERY_WORLD : String(worldId)}
        options={[
          {
            value: EVERY_WORLD,
            label: 'Every world',
            hint: 'Overrides here apply everywhere',
            icon: Orbit,
          },
          ...worlds.map((world) => ({
            value: String(world.id),
            label: world.name,
            hint: 'Counted for this world',
            icon: Globe2,
          })),
        ]}
        onChange={(value) =>
          setWorldId(value === EVERY_WORLD ? null : Number(value))
        }
        columns={4}
      />
      {report.isPending && <Skeleton className='h-textarea w-full' />}
      {report.isError && <Text tone='destructive'>{report.error.message}</Text>}
      {report.data && (
        <>
          <Section
            title='Tired motifs'
            description='Fate tags every creation with motifs. Those used too often are held back from new creations until they rest.'
            surface='card'
            level={3}
            icon={Repeat}
            tone='warning'
          >
            <MotifList
              act={save}
              report={report.data}
              blocked={blocked}
              pending={save.isPending}
              onChange={change}
            />
          </Section>
          <Section
            title='Overrides'
            description={
              worldId === null
                ? 'Your overrides for every world.'
                : 'Your overrides for this world only.'
            }
            surface='card'
            level={3}
            icon={Pin}
          >
            {report.data.overrides.length === 0 ? (
              <Muted variant='caption'>No override yet.</Muted>
            ) : (
              <ul className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2'>
                <Paged items={report.data.overrides} as='li'>
                  {(item) => (
                    <li
                      key={item.id}
                      className='flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2 rounded-md border surface-framed border-gild/70 bg-card p-3'
                    >
                      <Medallion
                        icon={item.mode === 'pinned' ? Pin : Ban}
                        tone={item.mode === 'pinned' ? 'warning' : 'success'}
                        size='sm'
                      />
                      <div className='flex min-w-0 flex-1 basis-60 items-center gap-2'>
                        <Text as='span' weight='medium' truncate>
                          {item.motif}
                        </Text>
                        <Badge
                          size='sm'
                          variant={
                            item.mode === 'pinned' ? 'warning' : 'success'
                          }
                        >
                          {item.mode === 'pinned' ? <Pin /> : <Ban />}
                          {MODE_LABEL[item.mode]}
                        </Badge>
                      </div>
                      <Button
                        act={save}
                        variant='ghost'
                        size='sm'
                        disabled={blocked !== null || save.isPending}
                        disabledReason={blocked ?? 'Saving.'}
                        onClick={() => change(item.motif, null)}
                      >
                        <Eraser />
                        Clear
                      </Button>
                    </li>
                  )}
                </Paged>
              </ul>
            )}
            <AddOverride
              act={save}
              blocked={blocked}
              pending={save.isPending}
              onAdd={(motif, mode) => change(motif, mode)}
            />
          </Section>
          <Section
            title='Borrowed images'
            description='Motifs tired in the home world that this world has never used. Its creations are told not to borrow them.'
            surface='card'
            level={3}
            icon={Images}
            tone='info'
          >
            {report.data.foreign_images.length === 0 ? (
              <Muted variant='caption'>
                {worldId === null
                  ? 'Pick a world other than the home world to see them.'
                  : 'None for this world.'}
              </Muted>
            ) : (
              <PagedList
                items={report.data.foreign_images}
                initial={12}
                noun={['entry', 'entries']}
                as='div'
                className='flex min-w-0 flex-wrap items-center gap-1.5'
                itemKey={(image) => image}
              >
                {(image) => (
                  <Badge key={image} size='sm' variant='outline'>
                    {image}
                  </Badge>
                )}
              </PagedList>
            )}
          </Section>
        </>
      )}
    </div>
  )
}

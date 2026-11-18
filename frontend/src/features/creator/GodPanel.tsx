import { useState } from 'react'
import {
  BookOpen,
  CloudLightning,
  Droplets,
  Eye,
  Footprints,
  Gift,
  Handshake,
  Hourglass,
  type LucideIcon,
  Moon,
  Scale,
  Sparkles,
  Stamp,
  Sun,
  TriangleAlert,
  Undo2,
  VolumeX,
  Zap,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { FormRow, KpiTile, Section, FieldTile } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { NamePicker } from '@/features/pantheon/NamePicker'
import { doomTone } from '@/features/pantheon/doom'
import { useGodGate, useRuleLookup } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'

type SignKind = components['schemas']['CreatorSignKind']

const SIGNS: {
  key: SignKind
  label: string
  icon: LucideIcon
  hint: string
}[] = [
  {
    key: 'wrath',
    label: 'Wrath',
    icon: Zap,
    hint: 'Harms those who do not worship you and raises their dread.',
  },
  {
    key: 'grace',
    label: 'Grace',
    icon: Sun,
    hint: 'A blessing falls on those who worship you.',
  },
  {
    key: 'silence',
    label: 'Silence',
    icon: VolumeX,
    hint: 'You send nothing for a while; the world notices the quiet.',
  },
  {
    key: 'dream',
    label: 'Dream',
    icon: Moon,
    hint: 'Those who listen for you receive a dream.',
  },
  {
    key: 'omen',
    label: 'Omen',
    icon: Eye,
    hint: 'A sign they read as yours: awe rises and ignorance of you falls.',
  },
  {
    key: 'warning',
    label: 'Warning',
    icon: TriangleAlert,
    hint: 'A sign of what you may do: dread rises, with some awe.',
  },
  {
    key: 'revelation',
    label: 'Revelation',
    icon: BookOpen,
    hint: 'You show them much of what you are: ignorance falls far and awe rises.',
  },
  {
    key: 'visitation',
    label: 'Visitation',
    icon: Footprints,
    hint: 'You come among them: love, awe and piety rise.',
  },
  {
    key: 'mark',
    label: 'Mark',
    icon: Stamp,
    hint: 'One of them is marked as your chosen.',
  },
  {
    key: 'wonder',
    label: 'Wonder',
    icon: Sparkles,
    hint: 'Something they cannot explain: awe, gratitude and prestige rise.',
  },
  {
    key: 'withdrawal',
    label: 'Withdrawal',
    icon: Undo2,
    hint: 'You turn away from them: resentment and ignorance rise and love falls.',
  },
  {
    key: 'test',
    label: 'Test',
    icon: Scale,
    hint: 'A hardship that tries them: prosperity falls and piety rises.',
  },
  {
    key: 'reward',
    label: 'Reward',
    icon: Gift,
    hint: 'You reward them: prosperity, gratitude and love rise.',
  },
  {
    key: 'covenant_offer',
    label: 'Covenant offer',
    icon: Handshake,
    hint: 'Their people are offered a covenant: worship for your protection.',
  },
]

export function GodPanel({ doom }: { doom: number }) {
  const rule = useRuleLookup()
  const { reason, essence } = useGodGate()
  const threshold = rule('balance.apocalypse_threshold')
  const [pour, setPour] = useState('10')
  const [clock, setClock] = useState(String(doom))
  const [sign, setSign] = useState<SignKind>('grace')
  const [signTarget, setSignTarget] = useState<string | null>(null)
  const [calling, setCalling] = useState(false)
  const pourAction = useGodAction({
    run: (amount: number) =>
      unwrap(api.POST('/api/actions/essence:pour', { body: { amount } })),
  })
  const clockAction = useGodAction({
    run: (value: number) =>
      unwrap(api.POST('/api/actions/doom:clock', { body: { value } })),
    success: 'The doom clock was set',
  })
  const apocalypse = useGodAction({
    run: (value: boolean) =>
      unwrap(
        api.POST('/api/actions/doom:apocalypse', { body: { calling: value } })
      ),
  })
  const signAction = useGodAction({
    run: (variables: { kind: SignKind; target: string | null }) =>
      unwrap(
        api.POST('/api/actions/creator:sign', {
          body: {
            kind: variables.kind,
            target_id:
              variables.target === null ? null : Number(variables.target),
          },
        })
      ),
    onDone: () => setSignTarget(null),
  })
  const pourAmount = Number(pour)
  const tone = doomTone(
    doom,
    threshold,
    rule('apocalypse.warning_1_pct'),
    rule('apocalypse.warning_2_pct')
  )
  return (
    <Section
      title="The Creator's hand"
      description='Your essence, the doom clock and your signs. Everything here also happens on its own as epochs pass.'
      surface='card'
      level={3}
    >
      <FormRow
        label='Pour essence into the land'
        description='Overflowing essence makes the most barren regions fertile.'
      >
        {(id) => (
          <>
            <Input
              id={id}
              type='number'
              min={1}
              max={essence}
              value={pour}
              className='w-32'
              onChange={(event) => setPour(event.target.value)}
            />
            <ActionButton
              label='Pour'
              icon={Droplets}
              cost={pourAmount > 0 ? pourAmount : undefined}
              blocked={
                reason({ cost: pourAmount }) ??
                (pourAmount > 0 ? null : 'Choose how much to pour.')
              }
              pending={pourAction.isPending}
              onRun={() => pourAction.mutate(pourAmount)}
            />
          </>
        )}
      </FormRow>
      <div className='flex min-w-0 flex-col gap-3'>
        <KpiTile
          label='Doom clock'
          icon={Hourglass}
          tone={
            tone === 'destructive'
              ? 'danger'
              : tone === 'warning'
                ? 'warning'
                : 'muted'
          }
          value={threshold !== undefined ? `${doom}/${threshold}` : doom}
          valueTone={tone}
          meter={
            threshold !== undefined
              ? { value: doom, max: threshold, label: 'Doom' }
              : undefined
          }
        />
        <Muted variant='caption'>
          Godlessness, curses, restless spirits and rebel sons advance the
          clock; faith, miracles, peace and wonders push it back. At the
          threshold the world that leaks most is destroyed.
        </Muted>
        <FormRow label='Set the clock'>
          {(id) => (
            <>
              <Input
                id={id}
                type='number'
                min={0}
                max={threshold}
                value={clock}
                className='w-32'
                onChange={(event) => setClock(event.target.value)}
              />
              <ActionButton
                label='Set'
                blocked={reason() ?? (clock === '' ? 'Enter a value.' : null)}
                pending={clockAction.isPending}
                onRun={() => clockAction.mutate(Number(clock))}
              />
            </>
          )}
        </FormRow>
        <div className='flex min-w-0 flex-wrap items-center gap-3'>
          <div className='flex min-w-0 items-center gap-2'>
            <FieldTile id='doom-calling' label='Turn it into the Calling'>
              <Switch
                id='doom-calling'
                checked={calling}
                onCheckedChange={setCalling}
              />
            </FieldTile>
          </div>
          <ActionButton
            label='Bring the apocalypse now'
            icon={CloudLightning}
            variant='destructive'
            blocked={reason({ world: true })}
            pending={apocalypse.isPending}
            confirm={{
              title: 'Bring the apocalypse?',
              description: calling
                ? 'The end turns into the Calling: the world is transformed rather than destroyed.'
                : 'The world that leaks the most is destroyed now.',
            }}
            onRun={() => apocalypse.mutate(calling)}
          />
        </div>
      </div>
      <div className='flex min-w-0 flex-col gap-3'>
        <Label variant='overline'>Send a sign</Label>
        <div
          role='radiogroup'
          aria-label='Sign'
          className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-7'
        >
          {SIGNS.map((item) => {
            const Icon = item.icon
            const chosen = sign === item.key
            return (
              <Button
                key={item.key}
                role='radio'
                aria-checked={chosen}
                variant={chosen ? 'default' : 'outline'}
                onClick={() => setSign(item.key)}
              >
                <Icon />
                {item.label}
              </Button>
            )
          })}
        </div>
        <Muted variant='caption'>
          {`${SIGNS.find((item) => item.key === sign)?.hint ?? ''} Pick a record to aim it, or leave it open and the Creator chooses.`}
        </Muted>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          {sign !== 'silence' && (
            <div className='min-w-0 flex-1 basis-60'>
              <NamePicker
                value={signTarget}
                onChange={setSignTarget}
                kinds={['entity']}
                placeholder='Anywhere the sign fits'
              />
            </div>
          )}
          <ActionButton
            label='Send'
            icon={Sparkles}
            blocked={reason()}
            pending={signAction.isPending}
            onRun={() =>
              signAction.mutate({
                kind: sign,
                target: sign === 'silence' ? null : signTarget,
              })
            }
          />
        </div>
      </div>
    </Section>
  )
}

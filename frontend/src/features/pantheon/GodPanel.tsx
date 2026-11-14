import { useState } from 'react'
import {
  BookOpen,
  Brush,
  Crown,
  Ghost,
  HandHeart,
  Handshake,
  Hourglass,
  Images,
  Languages,
  Library,
  Lightbulb,
  Route,
  ScrollText,
  Sparkles,
  Swords,
  UserCheck,
  Users,
  WholeWord,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatCompact, formatDecimal, formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Label as FieldLabel } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { KpiTile, MiniStat, Portrait } from '@/components/domain'
import { useDrawerStack } from '@/components/layout/drawer/useDrawerStack'
import { Label, Muted, PageTitle, Text } from '@/components/typography'
import { RedrawLikenessButton } from '@/features/creator/CreatorHero'
import { MoodGauges } from '@/features/creator/MoodPanel'
import { useCreator, useCreatorReputation } from '@/features/creator/api'
import { ActionButton } from './ActionButton'
import { type WorldState } from './api'
import { doomTone } from './doom'
import { useGodGate, useRuleLookup } from './gate'
import { useGodAction } from './godAction'
import {
  MOOD_BADGE,
  MOOD_LABEL,
  REPUTATION_BADGE,
  REPUTATION_LABEL,
} from './labels'
import { mediaUrl } from './media'

type ChipProps = {
  label: string
  hint?: string
  variant?:
    'default' | 'secondary' | 'destructive' | 'success' | 'warning' | 'outline'
}

function Chip({ label, hint, variant = 'outline' }: ChipProps) {
  const badge = (
    <Badge size='sm' variant={variant}>
      {label}
    </Badge>
  )
  if (!hint) return badge
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span tabIndex={0} className='inline-flex min-w-0'>
          {badge}
        </span>
      </TooltipTrigger>
      <TooltipContent>{hint}</TooltipContent>
    </Tooltip>
  )
}

function PromptBox({ prompt }: { prompt: string | null }) {
  const [draft, setDraft] = useState(prompt ?? '')
  const { reason } = useGodGate()
  const save = useGodAction({
    run: () =>
      unwrap(api.PATCH('/api/creator', { body: { image_prompt: draft } })),
    success: 'Portrait prompt saved',
  })
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <FieldLabel htmlFor='creator-prompt'>Portrait prompt</FieldLabel>
      <Textarea
        id='creator-prompt'
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <ActionButton
          label='Save prompt'
          blocked={
            reason() ?? (draft === (prompt ?? '') ? 'Nothing changed.' : null)
          }
          pending={save.isPending}
          onRun={() => save.mutate()}
        />
        <RedrawLikenessButton />
      </div>
    </div>
  )
}

export function GodPanel({ state }: { state: WorldState }) {
  const { open } = useDrawerStack()
  const creator = state.creator
  const detail = useCreator()
  const reputation = useCreatorReputation()
  const rule = useRuleLookup()
  if (!creator) return null
  const mood = state.mood
  const pulse = state.pulse
  const doom = state.world?.doom_clock ?? 0
  const threshold = rule('balance.apocalypse_threshold')
  const tone = doomTone(
    doom,
    threshold,
    rule('apocalypse.warning_1_pct'),
    rule('apocalypse.warning_2_pct')
  )
  const entities = Object.values(state.counts).reduce(
    (sum, value) => sum + value,
    0
  )
  const rebels = state.sons.filter(
    (view) => view.son.rebel && view.son.status !== 'dead'
  ).length
  const faith = detail.data?.faith
  const cult = detail.data?.cult.length
  const multi = state.worlds.length > 1
  return (
    <Card data-god-panel>
      <CardContent className='flex min-w-0 flex-col gap-5'>
        <div className='flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start'>
          <div className='flex shrink-0 flex-col items-start gap-2'>
            <Portrait
              name={creator.name}
              src={mediaUrl(state.creator_cover)}
              size='xl'
              shape='square'
              rarity='legendary'
            />
            <Button
              variant='ghost'
              size='sm'
              onClick={() => open({ kind: 'creator' })}
            >
              <Images />
              Images
            </Button>
          </div>
          <div className='flex min-w-0 flex-1 flex-col gap-2'>
            <Label variant='overline'>Creator · immortal</Label>
            <PageTitle truncate={2}>{creator.name}</PageTitle>
            <Muted>{creator.title ?? 'No likeness is drawn yet.'}</Muted>
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              {mood && (
                <Badge variant={MOOD_BADGE[mood.label]}>
                  {MOOD_LABEL[mood.label]}
                </Badge>
              )}
              {reputation.data && (
                <Chip
                  variant={REPUTATION_BADGE[reputation.data.label]}
                  label={`Sons see: ${REPUTATION_LABEL[reputation.data.label]}`}
                  hint={`Love ${reputation.data.love} · fear ${reputation.data.fear} · forgotten ${reputation.data.forgotten}`}
                />
              )}
              <Button
                variant='default'
                size='sm'
                onClick={() => open({ kind: 'creator' })}
              >
                <BookOpen />
                Epic and depth
              </Button>
            </div>
            {mood && (
              <MoodGauges
                short
                values={{
                  contentment: mood.contentment,
                  anger: mood.anger,
                  interest: mood.interest,
                  loneliness: mood.loneliness,
                }}
              />
            )}
            {creator.appearance && (
              <Text truncate={3}>{creator.appearance}</Text>
            )}
            {creator.temperament && (
              <Muted italic truncate={2}>
                {creator.temperament}
              </Muted>
            )}
          </div>
        </div>
        <div className='flex min-w-0 flex-col gap-3'>
          {multi && (
            <Label variant='overline'>{`Whole cosmos · ${plural(state.worlds.length, 'world', 'worlds')}`}</Label>
          )}
          <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4'>
            <KpiTile
              label='Essence'
              icon={Sparkles}
              tone='verdigris'
              value={formatInteger(creator.essence)}
              hint='Spent on revelations, summons and councils; refills each epoch.'
            />
            <KpiTile
              label='Faith'
              icon={HandHeart}
              value={
                faith === undefined
                  ? '—'
                  : cult && faith < 1
                    ? '<1'
                    : formatDecimal(faith, 1)
              }
              hint={`${cult ?? 0} in the cult of the Creator`}
            />
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
                  ? { value: doom, max: threshold, label: 'Doom clock' }
                  : undefined
              }
              hint='At the threshold the world that leaks most is destroyed.'
            />
            <KpiTile
              label='Sons'
              icon={Crown}
              tone={rebels > 0 ? 'danger' : 'gold'}
              value={state.sons.length}
              hint={rebels > 0 ? `${rebels} in rebellion` : 'None in rebellion'}
            />
          </div>
          <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-6'>
            {pulse && (
              <>
                <MiniStat
                  icon={Users}
                  tone='info'
                  label='Mortals'
                  value={formatCompact(pulse.population)}
                />
                <MiniStat
                  icon={UserCheck}
                  tone='gold'
                  label='Followers'
                  value={formatCompact(pulse.followers)}
                />
                {pulse.godless > 0 && (
                  <MiniStat
                    icon={Ghost}
                    tone='warning'
                    label='Godless communities'
                    value={pulse.godless}
                    hint='Each one gnaws at your essence income.'
                  />
                )}
                <MiniStat
                  icon={Languages}
                  tone='verdigris'
                  label='Languages'
                  value={pulse.languages}
                />
                <MiniStat
                  icon={WholeWord}
                  tone='verdigris'
                  label='Words'
                  value={formatCompact(pulse.words)}
                />
                <MiniStat
                  icon={Lightbulb}
                  tone='info'
                  label='Knowledge'
                  value={pulse.knowledge}
                />
                <MiniStat
                  icon={Swords}
                  tone={pulse.wars > 0 ? 'danger' : 'muted'}
                  label='Hostilities'
                  value={pulse.wars}
                />
                <MiniStat
                  icon={Route}
                  tone='success'
                  label='Trade routes'
                  value={pulse.trade_routes}
                />
                <MiniStat
                  icon={Handshake}
                  tone='success'
                  label='Alliances'
                  value={pulse.alliances}
                />
              </>
            )}
            <MiniStat
              icon={Library}
              label='Records'
              value={formatCompact(entities)}
            />
            <MiniStat
              icon={ScrollText}
              label='Open stories'
              value={state.threads.length}
            />
            <MiniStat
              icon={Images}
              label='Images'
              value={formatCompact(state.image_count)}
            />
          </div>
        </div>
        <Collapsible className='flex min-w-0 flex-col gap-3'>
          <CollapsibleTrigger asChild>
            <Button variant='ghost' size='sm' className='self-start'>
              <Brush />
              Portrait prompt and likeness
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <PromptBox
              key={creator.image_prompt ?? ''}
              prompt={creator.image_prompt}
            />
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  )
}

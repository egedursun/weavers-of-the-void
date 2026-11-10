import { CircleAlert, CircleCheck, ImageIcon, Lock, Users } from 'lucide-react'
import { cn } from '@/lib/utils'
import { RARITY_LABEL } from '@/constants/rarity'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { ExpandableText, RarityIcon } from '@/components/domain'
import { RARITY_TEXT_CLASS } from '@/components/domain/rarityClasses'
import { Label, Muted, Text } from '@/components/typography'
import { imageStyleLabel } from '@/features/images/imageStyles'
import { type WizardOptions } from './api'
import {
  STEP_TITLE,
  WIZARD_STEPS,
  type WizardDraft,
  stepProblem,
} from './wizardModel'
import {
  COSMOS_ICON,
  LANGUAGE_ICON,
  STORYTELLER_ICON,
  TECHNOLOGY_ICON,
  TEMPLATE_ICON,
  darknessLevel,
  magicLevel,
} from './wizardVisuals'

type GenesisPreviewProps = {
  draft: WizardDraft
  options: WizardOptions
  peoplesMax: number
}

function Meter({
  label,
  value,
  level,
}: {
  label: string
  value: number
  level: string
}) {
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <div className='flex min-w-0 items-baseline justify-between gap-2'>
        <Label variant='overline'>{label}</Label>
        <Text as='span' variant='caption' tone='primary' weight='medium'>
          {`${level} · ${Number.isFinite(value) ? value : 0}`}
        </Text>
      </div>
      <Progress size='sm' value={Number.isFinite(value) ? value : 0} />
    </div>
  )
}

export function GenesisPreview({
  draft,
  options,
  peoplesMax,
}: GenesisPreviewProps) {
  const template = options.templates.find((item) => item.key === draft.template)
  const TemplateIcon = template ? TEMPLATE_ICON[template.key] : null
  const cosmos = options.cosmos.find((item) => item.size === draft.cosmos)
  const sons = draft.firstSons ?? options.first_sons.default
  const TechIcon = TECHNOLOGY_ICON[draft.technology]
  const LanguageIcon = LANGUAGE_ICON[draft.language]
  const CosmosIcon = COSMOS_ICON[draft.cosmos]
  const StorytellerIcon = STORYTELLER_ICON[draft.storyteller]
  return (
    <aside
      aria-label='Your world so far'
      data-onboarding='preview'
      className='flex min-w-0 flex-col gap-4 overflow-hidden rounded-xl border bg-card shadow-sm'
    >
      <div className='flex min-w-0 flex-col gap-1 border-b bg-linear-to-br from-primary/15 via-brand-violet/10 to-transparent p-4'>
        <Label variant='overline'>Your world so far</Label>
        <Text
          as='span'
          weight='semibold'
          truncate
          className='font-display'
          tone={draft.creatorName.trim() ? 'default' : 'muted'}
        >
          {draft.creatorName.trim() || 'An unnamed Creator'}
        </Text>
        <div className='flex min-w-0 flex-wrap gap-1.5 pt-1'>
          {template && TemplateIcon ? (
            <Badge size='sm' variant='default'>
              <TemplateIcon />
              {template.name}
            </Badge>
          ) : (
            <Badge size='sm' variant='outline'>
              Blank canvas
            </Badge>
          )}
          <Badge size='sm' variant='outline'>
            <Lock />
            {options.lore_languages[draft.loreLanguage] ?? draft.loreLanguage}
          </Badge>
        </div>
      </div>
      <div className='flex min-w-0 flex-col gap-4 px-4'>
        <div className='flex min-w-0 flex-col gap-1'>
          <Label variant='overline'>Seed</Label>
          {draft.seed.trim() ? (
            <ExpandableText italic lines={4}>
              {draft.seed}
            </ExpandableText>
          ) : (
            <Muted italic>The void is still empty.</Muted>
          )}
          {draft.tone.trim() && (
            <Muted variant='caption'>{`Tone: ${draft.tone}`}</Muted>
          )}
        </div>
        <Meter
          label='Magic'
          value={draft.magic}
          level={magicLevel(draft.magic)}
        />
        <Meter
          label='Darkness'
          value={draft.darkness}
          level={darknessLevel(draft.darkness)}
        />
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <Badge variant='outline'>
            <TechIcon />
            {options.technology[draft.technology] ?? draft.technology}
          </Badge>
          <Badge variant='outline'>
            <LanguageIcon />
            {options.language[draft.language] ?? draft.language}
          </Badge>
          <Badge variant='outline'>
            <CosmosIcon />
            {cosmos
              ? `${cosmos.label} · ${cosmos.worlds} ${cosmos.worlds === 1 ? 'world' : 'worlds'}`
              : draft.cosmos}
          </Badge>
          <Badge variant='outline'>
            <StorytellerIcon />
            {`${options.storyteller[draft.storyteller] ?? draft.storyteller} storyteller`}
          </Badge>
          <Badge variant='outline'>
            <Users />
            {`${draft.peoples} ${draft.peoples === 1 ? 'people' : 'peoples'}`}
          </Badge>
          <Badge variant='outline' className='max-w-full'>
            <ImageIcon />
            <span className='truncate'>
              {imageStyleLabel(draft.imageStyle, draft.imageStyleCustom)}
            </span>
          </Badge>
        </div>
        <div className='flex min-w-0 flex-col gap-1.5'>
          <Label variant='overline'>{`First sons · ${sons.length}`}</Label>
          <ul className='flex min-w-0 flex-wrap gap-2'>
            {sons.map((rarity, index) => (
              <li
                key={index}
                title={RARITY_LABEL[rarity]}
                className='flex size-control-md items-center justify-center rounded-full border bg-background'
              >
                <RarityIcon
                  rarity={rarity}
                  label={RARITY_LABEL[rarity]}
                  className={cn('size-icon-md', RARITY_TEXT_CLASS[rarity])}
                />
              </li>
            ))}
          </ul>
        </div>
      </div>
      <ul className='flex min-w-0 flex-col gap-1.5 border-t bg-muted/30 p-4'>
        {WIZARD_STEPS.map((step) => {
          const problem = stepProblem(step, draft, peoplesMax)
          return (
            <li key={step} className='flex min-w-0 items-center gap-2'>
              {problem ? (
                <CircleAlert
                  aria-hidden='true'
                  className='size-icon-sm shrink-0 text-warning'
                />
              ) : (
                <CircleCheck
                  aria-hidden='true'
                  className='size-icon-sm shrink-0 text-success'
                />
              )}
              <Text as='span' variant='caption' weight='medium'>
                {STEP_TITLE[step]}
              </Text>
              <Muted as='span' variant='caption' truncate>
                {problem ?? 'Ready'}
              </Muted>
            </li>
          )
        })}
      </ul>
    </aside>
  )
}

import {
  Check,
  Feather,
  Globe,
  Lock,
  PenLine,
  ShieldAlert,
  Sparkles,
  Users,
  Wand2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { RARITY_LABEL } from '@/constants/rarity'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { FormRow, Medallion, RangeField, RarityIcon } from '@/components/domain'
import {
  type Choice,
  ChoiceTiles,
  SettingGroup,
} from '@/components/domain/SettingsKit'
import {
  RARITY_BORDER_CLASS,
  RARITY_TEXT_CLASS,
} from '@/components/domain/rarityClasses'
import { Label, Muted, Text } from '@/components/typography'
import { ImageStylePicker } from '@/features/images/ImageStylePicker'
import { romanNumeral } from '@/features/pantheon/labels'
import { Counter } from './Counter'
import { CosmosFields, FirstWorldFields, MindsFields } from './WorldShapeFields'
import {
  type LanguageTexture,
  type LoreLanguage,
  type Rarity,
  type AgeCycle,
  type StorytellerProfile,
  type TechnologyEra,
  type WizardTemplate,
} from './api'
import {
  CREATOR_NAME_MAX,
  PERCENT_MAX,
  SEED_MAX,
  TONE_MAX,
  resizeFirstSons,
} from './wizardModel'
import { type StepProps } from './wizardTypes'
import {
  LANGUAGE_HINT,
  LANGUAGE_ICON,
  LORE_LANGUAGE_ICON,
  AGE_CYCLE_HINT,
  AGE_CYCLE_ICON,
  STORYTELLER_HINT,
  STORYTELLER_ICON,
  TECHNOLOGY_HINT,
  TECHNOLOGY_ICON,
  TEMPLATE_ICON,
  SHAPE_ICON,
  TONE_SUGGESTIONS,
  dangerLevel,
  magicLevel,
} from './wizardVisuals'

function TemplateCard({
  template,
  chosen,
  technology,
  worldKind,
  shape,
  onPick,
}: {
  template: WizardTemplate
  chosen: boolean
  technology: string
  worldKind: string | null
  shape: string | null
  onPick: () => void
}) {
  const Icon = TEMPLATE_ICON[template.key]
  const ShapeIcon = SHAPE_ICON[template.shape]
  return (
    <Button
      role='radio'
      aria-checked={chosen}
      variant='outline'
      size='card'
      onClick={onPick}
      className={cn(chosen && 'border-primary/70 bg-primary/10 shadow-md')}
    >
      <span className='flex min-w-0 items-center gap-2.5'>
        <Medallion icon={Icon} tone={chosen ? 'gold' : 'muted'} size='sm' />
        <Text as='span' weight='semibold' truncate className='flex-1'>
          {template.name}
        </Text>
        {chosen && (
          <Check aria-hidden='true' className='size-icon-sm text-primary' />
        )}
      </span>
      <Muted as='span' variant='caption' truncate={2}>
        {template.tone}
      </Muted>
      <span className='flex min-w-0 flex-wrap gap-1'>
        <Badge size='sm' variant='outline'>
          <Wand2 />
          {template.magic}
        </Badge>
        <Badge size='sm' variant='outline'>
          <ShieldAlert />
          {template.danger}
        </Badge>
        <Badge size='sm' variant='outline'>
          {technology}
        </Badge>
        <Badge size='sm' variant='outline'>
          <Users />
          {template.peoples}
        </Badge>
        {worldKind && (
          <Badge size='sm' variant='outline'>
            <Globe />
            {worldKind}
          </Badge>
        )}
        {shape && (
          <Badge size='sm' variant='outline'>
            <ShapeIcon />
            {shape}
          </Badge>
        )}
      </span>
    </Button>
  )
}

export function TemplateStep({
  draft,
  options,
  onPick,
}: StepProps & { onPick: (key: string | null) => void }) {
  const chosen = options.templates.find((item) => item.key === draft.template)
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <Muted>
        Begin from a myth, or from nothing at all. A template fills in the seed,
        the tone and every setting; you can change all of it in the next steps.
      </Muted>
      <div
        role='radiogroup'
        aria-label='Templates'
        className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3'
      >
        <Button
          role='radio'
          aria-checked={draft.template === null}
          variant='outline'
          size='card'
          onClick={() => onPick(null)}
          className={cn(
            'border-dashed',
            draft.template === null && 'border-primary/70 bg-primary/10'
          )}
        >
          <span className='flex min-w-0 items-center gap-2.5'>
            <Medallion
              icon={PenLine}
              tone={draft.template === null ? 'gold' : 'muted'}
              size='sm'
            />
            <Text as='span' weight='semibold' truncate className='flex-1'>
              Blank canvas
            </Text>
            {draft.template === null && (
              <Check aria-hidden='true' className='size-icon-sm text-primary' />
            )}
          </span>
          <Muted as='span' variant='caption' truncate={2}>
            Write your own seed and pick every setting yourself.
          </Muted>
        </Button>
        {options.templates.map((template) => (
          <TemplateCard
            key={template.key}
            template={template}
            chosen={draft.template === template.key}
            technology={
              options.technology[template.technology] ?? template.technology
            }
            worldKind={
              template.world_type
                ? (options.world_types.find(
                    (item) => item.world_type === template.world_type
                  )?.label ?? template.world_type)
                : null
            }
            shape={
              template.shape === 'one_sun'
                ? null
                : (options.shapes.find((item) => item.shape === template.shape)
                    ?.label ?? template.shape)
            }
            onPick={() => onPick(template.key)}
          />
        ))}
      </div>
      {chosen && (
        <div className='flex min-w-0 flex-col gap-1.5 rounded-lg border border-primary/30 bg-primary/5 p-4'>
          <Label variant='overline'>{`The seed of ${chosen.name}`}</Label>
          <Text italic variant='prose'>
            {chosen.seed}
          </Text>
        </div>
      )}
    </div>
  )
}

export function CreatorStep({ draft, update, options }: StepProps) {
  const languages: Choice<LoreLanguage>[] = Object.entries(
    options.lore_languages
  ).map(([key, label]) => ({
    value: key as LoreLanguage,
    label,
    hint: `Every chronicle, name and story in ${label}`,
    icon: LORE_LANGUAGE_ICON[key as LoreLanguage] ?? Feather,
  }))
  return (
    <div className='flex min-w-0 flex-col gap-5'>
      <FormRow
        label='Name of the Creator'
        description='That is you. Your sons, the peoples and the chronicle will call you by it.'
      >
        {(id) => (
          <div className='flex w-full min-w-0 flex-col gap-1'>
            <Input
              id={id}
              required
              size='lg'
              maxLength={CREATOR_NAME_MAX}
              placeholder='A name for the Creator'
              value={draft.creatorName}
              onChange={(event) => update({ creatorName: event.target.value })}
            />
            <Muted variant='caption'>
              {`${draft.creatorName.length} / ${CREATOR_NAME_MAX}`}
            </Muted>
          </div>
        )}
      </FormRow>
      <SettingGroup
        label='Lore language'
        description='The language every chronicle, name and story is written in.'
      >
        <ChoiceTiles
          label='Lore language'
          value={draft.loreLanguage}
          options={languages}
          onChange={(loreLanguage) => update({ loreLanguage })}
          columns={2}
        />
      </SettingGroup>
      <Alert>
        <Lock />
        <AlertTitle>Chosen once, forever</AlertTitle>
        <AlertDescription>
          The lore language is fixed when the Creator is made. It cannot be
          changed afterwards.
        </AlertDescription>
      </Alert>
    </div>
  )
}

function toggleTone(tone: string, word: string): string {
  const parts = tone
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
  const next = parts.includes(word)
    ? parts.filter((part) => part !== word)
    : [...parts, word]
  return next.join(', ').slice(0, TONE_MAX)
}

export function WorldStep({ draft, update, options, peoplesMax }: StepProps) {
  const tones = draft.tone
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
  const technology: Choice<TechnologyEra>[] = Object.entries(
    options.technology
  ).map(([key, label]) => ({
    value: key as TechnologyEra,
    label,
    hint: TECHNOLOGY_HINT[key as TechnologyEra],
    icon: TECHNOLOGY_ICON[key as TechnologyEra] ?? Sparkles,
  }))
  const language: Choice<LanguageTexture>[] = Object.entries(
    options.language
  ).map(([key, label]) => ({
    value: key as LanguageTexture,
    label,
    hint: LANGUAGE_HINT[key as LanguageTexture],
    icon: LANGUAGE_ICON[key as LanguageTexture] ?? Sparkles,
  }))
  const ageCycles: Choice<AgeCycle>[] = Object.entries(options.age_cycles).map(
    ([key, label]) => ({
      value: key as AgeCycle,
      label,
      hint: AGE_CYCLE_HINT[key as AgeCycle],
      icon: AGE_CYCLE_ICON[key as AgeCycle] ?? Sparkles,
    })
  )
  const storyteller: Choice<StorytellerProfile>[] = Object.entries(
    options.storyteller
  ).map(([key, label]) => ({
    value: key as StorytellerProfile,
    label,
    hint: STORYTELLER_HINT[key as StorytellerProfile],
    icon: STORYTELLER_ICON[key as StorytellerProfile] ?? Sparkles,
  }))
  return (
    <div className='flex min-w-0 flex-col gap-5'>
      <FormRow
        label='World seed'
        description='One idea, in your own words. From it grow the cosmology, the language, the first world and its sky.'
      >
        {(id) => (
          <div className='flex w-full min-w-0 flex-col gap-1'>
            <Textarea
              id={id}
              required
              rows={5}
              maxLength={SEED_MAX}
              placeholder='Your idea for the world, in a sentence or a page: its premise, its land and sky, what makes it its own.'
              value={draft.seed}
              onChange={(event) => update({ seed: event.target.value })}
            />
            <Muted variant='caption'>{`${draft.seed.length} / ${SEED_MAX}`}</Muted>
          </div>
        )}
      </FormRow>
      <FormRow
        label='Tone'
        description='Optional. Type freely or pick a few moods.'
      >
        {(id) => (
          <div className='flex w-full min-w-0 flex-col gap-2'>
            <Input
              id={id}
              maxLength={TONE_MAX}
              placeholder='Any tone you like'
              value={draft.tone}
              onChange={(event) => update({ tone: event.target.value })}
            />
            <div className='flex min-w-0 flex-wrap gap-1.5'>
              {TONE_SUGGESTIONS.map((word) => {
                const on = tones.includes(word)
                return (
                  <Button
                    key={word}
                    variant={on ? 'secondary' : 'outline'}
                    size='sm'
                    aria-pressed={on}
                    onClick={() =>
                      update({ tone: toggleTone(draft.tone, word) })
                    }
                    className={cn(on && 'border-primary/60 text-primary')}
                  >
                    {on && <Check />}
                    {word}
                  </Button>
                )
              })}
            </div>
          </div>
        )}
      </FormRow>
      <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
        <RangeField
          label='Magic'
          icon={Wand2}
          hint='How much of the world bends to wonder'
          value={draft.magic}
          min={0}
          max={PERCENT_MAX}
          level={magicLevel(draft.magic)}
          lowLabel='Mundane'
          highLabel='Saturated'
          onChange={(magic) => update({ magic })}
        />
        <RangeField
          label='Danger'
          icon={ShieldAlert}
          hint='How perilous its lands are'
          value={draft.danger}
          min={0}
          max={PERCENT_MAX}
          level={dangerLevel(draft.danger)}
          lowLabel='Safe'
          highLabel='Deadly'
          onChange={(danger) => update({ danger })}
        />
      </div>
      <FirstWorldFields
        draft={draft}
        update={update}
        options={options}
        peoplesMax={peoplesMax}
      />
      <SettingGroup
        label='Technology'
        description='Where the first peoples stand when the world begins.'
      >
        <ChoiceTiles
          label='Technology'
          value={draft.technology}
          options={technology}
          onChange={(value) => update({ technology: value })}
        />
      </SettingGroup>
      <MindsFields
        draft={draft}
        update={update}
        options={options}
        peoplesMax={peoplesMax}
      />
      <SettingGroup
        label='Texture of the language'
        description='How the names and words of the world sound.'
      >
        <ChoiceTiles
          label='Texture of the language'
          value={draft.language}
          options={language}
          onChange={(value) => update({ language: value })}
        />
      </SettingGroup>
      <CosmosFields
        draft={draft}
        update={update}
        options={options}
        peoplesMax={peoplesMax}
      />
      <SettingGroup
        label='Storyteller'
        description='How the tension of the world rises and falls across the epochs. You can change it later in the world drawer.'
      >
        <ChoiceTiles
          label='Storyteller'
          value={draft.storyteller}
          options={storyteller}
          onChange={(value) => update({ storyteller: value })}
          columns={2}
        />
      </SettingGroup>
      <SettingGroup
        label='Ages'
        description='Whether the end of the cosmos is final or turns a new age. You can change it later in the drawer of any record, under tales and ages.'
      >
        <ChoiceTiles
          label='Ages'
          value={draft.ageCycle}
          options={ageCycles}
          onChange={(value) => update({ ageCycle: value })}
          columns={2}
        />
      </SettingGroup>
      <SettingGroup
        label='Image style'
        description='How every portrait and scene of this world is painted. You can change it later in Settings, under Images.'
      >
        <ImageStylePicker
          value={draft.imageStyle}
          custom={draft.imageStyleCustom}
          onChange={(imageStyle) => update({ imageStyle })}
          onCustomChange={(imageStyleCustom) => update({ imageStyleCustom })}
        />
      </SettingGroup>
      <Counter
        label='First peoples'
        hint={`1 to ${peoplesMax}; the limit is a world rule (Genesis wizard).`}
        icon={Users}
        value={draft.peoples}
        min={1}
        max={peoplesMax}
        onChange={(peoples) => update({ peoples })}
      />
    </div>
  )
}

function SonSlot({
  index,
  rarity,
  rarities,
  onChange,
}: {
  index: number
  rarity: Rarity
  rarities: Rarity[]
  onChange: (rarity: Rarity) => void
}) {
  return (
    <li
      className={cn(
        'flex min-w-0 flex-col items-center gap-2 rounded-xl border-2 bg-card p-4 text-center',
        RARITY_BORDER_CLASS[rarity]
      )}
    >
      <RarityIcon
        rarity={rarity}
        className={cn('size-icon-xl', RARITY_TEXT_CLASS[rarity])}
      />
      <Label variant='overline'>{`First son ${romanNumeral(index + 1)}`}</Label>
      <Select
        value={rarity}
        onValueChange={(value) => onChange(value as Rarity)}
      >
        <SelectTrigger
          aria-label={`Rarity of son ${index + 1}`}
          className='w-full'
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {rarities.map((item) => (
            <SelectItem key={item} value={item}>
              <RarityIcon
                rarity={item}
                className={cn('size-icon-sm', RARITY_TEXT_CLASS[item])}
              />
              {RARITY_LABEL[item]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </li>
  )
}

export function SonsStep({ draft, update, options }: StepProps) {
  const { minimum, maximum, rarities } = options.first_sons
  const sons = draft.firstSons ?? options.first_sons.default
  return (
    <div className='flex min-w-0 flex-col gap-5'>
      <Muted>
        Your first sons are gods in their own right. Each acts as an agent once
        per epoch; rarer sons are wiser, stronger and carry more powers.
      </Muted>
      <Counter
        label='Number of first sons'
        hint={`${minimum} to ${maximum}. More can be summoned or born later.`}
        icon={Sparkles}
        value={sons.length}
        min={minimum}
        max={maximum}
        onChange={(count) =>
          update({ firstSons: resizeFirstSons(sons, count, rarities[0]) })
        }
      />
      <ul className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-3'>
        {sons.map((rarity, index) => (
          <SonSlot
            key={index}
            index={index}
            rarity={rarity}
            rarities={rarities}
            onChange={(value) =>
              update({
                firstSons: sons.map((item, at) =>
                  at === index ? value : item
                ),
              })
            }
          />
        ))}
      </ul>
      <Muted variant='caption'>
        Creation is a language model job and takes from a few seconds to a few
        minutes. You can watch it unfold here.
      </Muted>
    </div>
  )
}

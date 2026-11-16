import { useId } from 'react'
import { Link } from '@tanstack/react-router'
import { fonts } from '@/config/fonts'
import {
  ArrowRight,
  Check,
  CirclePause,
  Contrast,
  type LucideIcon,
  Monitor,
  Moon,
  Palette,
  Sun,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { TEXT_SIZES, useAccessibility } from '@/context/accessibilityContext'
import { type Font, useFont } from '@/context/fontContext'
import {
  type ResolvedTheme,
  type Theme,
  useTheme,
} from '@/context/themeContext'
import { Button } from '@/components/ui/button'
import { Label as FieldLabel } from '@/components/ui/label'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Switch } from '@/components/ui/switch'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Medallion } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import {
  FONT_CHOICE,
  TEXT_SIZE_CHOICES,
  THEME_CHOICES,
} from './appearanceChoices'

const FONT_CLASS: Record<Font, string> = {
  nunito: 'font-nunito',
  inter: 'font-inter',
  system: 'font-system',
}

const FONT_SHORT: Record<Font, string> = {
  nunito: 'Nunito',
  inter: 'Inter',
  system: 'System',
}

function isFont(value: string): value is Font {
  return (fonts as readonly string[]).includes(value)
}

function isTextSize(value: string): value is (typeof TEXT_SIZES)[number] {
  return (TEXT_SIZES as readonly string[]).includes(value)
}

function PreviewPane({ mode }: { mode: ResolvedTheme }) {
  return (
    <span
      className={cn(
        mode,
        'flex min-w-0 flex-1 flex-col gap-1 bg-background p-1.5'
      )}
    >
      <span className='flex items-center gap-1'>
        <span className='size-1.5 rounded-full bg-primary' />
        <span className='h-1 w-6 rounded-full bg-muted-foreground/40' />
      </span>
      <span className='flex min-h-0 flex-1 gap-1'>
        <span className='w-2.5 rounded-sm bg-sidebar' />
        <span className='flex flex-1 flex-col justify-end gap-0.5 rounded-md border surface-sheen border-gild/60 bg-card p-1'>
          <span className='h-1 w-3/4 rounded-full bg-foreground/50' />
          <span className='h-1 w-1/2 rounded-full bg-primary' />
        </span>
      </span>
    </span>
  )
}

function ThemePreview({ theme }: { theme: Theme }) {
  return (
    <span
      aria-hidden='true'
      className='flex h-16 w-full overflow-hidden rounded-md border'
    >
      {theme === 'system' ? (
        <>
          <PreviewPane mode='light' />
          <PreviewPane mode='dark' />
        </>
      ) : (
        <PreviewPane mode={theme} />
      )}
    </span>
  )
}

function ThemeTiles() {
  const { theme, setTheme } = useTheme()
  return (
    <div
      role='radiogroup'
      aria-label='Theme'
      className='grid grid-cols-3 gap-2'
    >
      {THEME_CHOICES.map((option) => {
        const active = option.value === theme
        const Icon = option.icon
        return (
          <Button
            key={option.value}
            role='radio'
            aria-checked={active}
            variant='outline'
            size='tile'
            title={option.hint}
            onClick={() => setTheme(option.value)}
            className={cn(
              'flex-col items-stretch gap-1.5 p-1.5',
              active && 'border-primary/60 bg-primary/10'
            )}
          >
            <ThemePreview theme={option.value} />
            <span className='flex min-w-0 items-center gap-1 px-0.5'>
              <Icon
                aria-hidden='true'
                className={cn(
                  'size-icon-xs shrink-0',
                  active ? 'text-primary' : 'text-muted-foreground'
                )}
              />
              <Text as='span' variant='caption' weight='medium' truncate>
                {option.label}
              </Text>
              {active && (
                <Check
                  aria-hidden='true'
                  className='ms-auto size-icon-xs shrink-0 text-primary'
                />
              )}
            </span>
          </Button>
        )
      })}
    </div>
  )
}

function QuickSwitch({
  icon,
  label,
  hint,
  checked,
  onChange,
}: {
  icon: LucideIcon
  label: string
  hint: string
  checked: boolean
  onChange: (checked: boolean) => void
}) {
  const id = useId()
  return (
    <div className='flex min-w-0 items-center gap-2.5 rounded-lg border bg-field p-2'>
      <Medallion icon={icon} tone={checked ? 'gold' : 'muted'} size='sm' />
      <span className='flex min-w-0 flex-1 flex-col'>
        <FieldLabel htmlFor={id}>{label}</FieldLabel>
        <Muted as='span' variant='caption' truncate>
          {hint}
        </Muted>
      </span>
      <Switch id={id} checked={checked} onCheckedChange={onChange} />
    </div>
  )
}

function TriggerIcon({ theme }: { theme: Theme }) {
  if (theme === 'system') return <Monitor />
  return theme === 'dark' ? <Moon /> : <Sun />
}

export function ThemeSwitch() {
  const { theme } = useTheme()
  const { font, setFont } = useFont()
  const accessibility = useAccessibility()
  return (
    <Popover>
      <Tooltip>
        <TooltipTrigger asChild>
          <PopoverTrigger asChild>
            <Button
              variant='ghost'
              size='icon'
              aria-label='Appearance'
              data-theme-picker
            >
              <TriggerIcon theme={theme} />
            </Button>
          </PopoverTrigger>
        </TooltipTrigger>
        <TooltipContent>Appearance</TooltipContent>
      </Tooltip>
      <PopoverContent
        align='end'
        className='flex w-84 max-w-[calc(100vw-2rem)] flex-col gap-4'
      >
        <div className='flex min-w-0 items-center gap-3'>
          <Medallion icon={Palette} />
          <div className='flex min-w-0 flex-1 flex-col'>
            <Text as='span' weight='semibold'>
              Appearance
            </Text>
            <Muted as='span' variant='caption'>
              Stored in this browser only
            </Muted>
          </div>
        </div>
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Theme</Label>
          <ThemeTiles />
        </div>
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Font</Label>
          <ToggleGroup
            type='single'
            size='sm'
            variant='outline'
            value={font}
            onValueChange={(value) => isFont(value) && setFont(value)}
            aria-label='Font'
            className='w-full'
          >
            {fonts.map((option) => (
              <ToggleGroupItem
                key={option}
                value={option}
                title={FONT_CHOICE[option].label}
                className={cn('flex-1', FONT_CLASS[option])}
              >
                {FONT_SHORT[option]}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </div>
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Text size</Label>
          <ToggleGroup
            type='single'
            size='sm'
            variant='outline'
            value={accessibility.textSize}
            onValueChange={(value) =>
              isTextSize(value) && accessibility.setTextSize(value)
            }
            aria-label='Text size'
            className='w-full'
          >
            {TEXT_SIZE_CHOICES.map((option) => {
              const Icon = option.icon
              return (
                <ToggleGroupItem
                  key={option.value}
                  value={option.value}
                  title={option.hint}
                  className='flex-1'
                >
                  <Icon aria-hidden='true' />
                  {option.label}
                </ToggleGroupItem>
              )
            })}
          </ToggleGroup>
        </div>
        <div className='flex min-w-0 flex-col gap-2'>
          <QuickSwitch
            icon={Contrast}
            label='High contrast'
            hint='Stronger text and borders'
            checked={accessibility.contrast === 'high'}
            onChange={(next) =>
              accessibility.setContrast(next ? 'high' : 'default')
            }
          />
          <QuickSwitch
            icon={CirclePause}
            label='Reduce motion'
            hint='Animations stop'
            checked={accessibility.motion === 'reduce'}
            onChange={(next) =>
              accessibility.setMotion(next ? 'reduce' : 'system')
            }
          />
        </div>
        <Button variant='ghost' size='sm' asChild className='justify-between'>
          <Link to='/settings/appearance'>
            All appearance settings
            <ArrowRight />
          </Link>
        </Button>
      </PopoverContent>
    </Popover>
  )
}

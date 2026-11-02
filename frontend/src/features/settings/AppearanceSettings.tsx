import { fonts } from '@/config/fonts'
import {
  Accessibility,
  Activity,
  AppWindow,
  CirclePause,
  Contrast as ContrastIcon,
  EyeOff,
  Palette,
  PanelLeft,
  PanelLeftClose,
  PanelLeftDashed,
  PanelLeftOpen,
  RotateCcw,
  SunDim,
} from 'lucide-react'
import {
  type Contrast,
  type Motion,
  useAccessibility,
} from '@/context/accessibilityContext'
import { useFont } from '@/context/fontContext'
import {
  type Collapsible,
  type Variant,
  useLayout,
} from '@/context/layoutContext'
import { useTheme } from '@/context/themeContext'
import { Button } from '@/components/ui/button'
import { Section } from '@/components/domain'
import {
  type Choice,
  ChoiceTiles,
  SettingGroup,
} from '@/components/domain/SettingsKit'
import {
  FONT_CHOICE,
  TEXT_SIZE_CHOICES,
  THEME_CHOICES,
} from '@/components/layout/appearanceChoices'

const VARIANTS: readonly Choice<Variant>[] = [
  {
    value: 'inset',
    label: 'Inset',
    hint: 'The page floats beside it',
    icon: AppWindow,
  },
  {
    value: 'sidebar',
    label: 'Attached',
    hint: 'Flush against the page',
    icon: PanelLeft,
  },
  {
    value: 'floating',
    label: 'Floating',
    hint: 'A detached panel',
    icon: PanelLeftDashed,
  },
]

const COLLAPSES: readonly Choice<Collapsible>[] = [
  {
    value: 'icon',
    label: 'Collapse to icons',
    hint: 'A thin rail stays',
    icon: PanelLeftClose,
  },
  {
    value: 'offcanvas',
    label: 'Hide completely',
    hint: 'All room for the page',
    icon: EyeOff,
  },
  {
    value: 'none',
    label: 'Always open',
    hint: 'Never folds away',
    icon: PanelLeftOpen,
  },
]

const CONTRASTS: readonly Choice<Contrast>[] = [
  {
    value: 'default',
    label: 'Standard',
    hint: 'Soft borders and text',
    icon: SunDim,
  },
  {
    value: 'high',
    label: 'High contrast',
    hint: 'Stronger text and borders',
    icon: ContrastIcon,
  },
]

const MOTIONS: readonly Choice<Motion>[] = [
  {
    value: 'system',
    label: 'Follow the system',
    hint: 'Animate unless the device asks not to',
    icon: Activity,
  },
  {
    value: 'reduce',
    label: 'Always reduce',
    hint: 'Animations stop',
    icon: CirclePause,
  },
]

export function AppearanceSettings() {
  const { theme, setTheme, resetTheme } = useTheme()
  const { font, setFont, resetFont } = useFont()
  const accessibility = useAccessibility()
  const { variant, setVariant, collapsible, setCollapsible, resetLayout } =
    useLayout()
  return (
    <>
      <Section
        title='Look and feel'
        description='Stored in this browser only.'
        surface='card'
        icon={Palette}
        actions={
          <Button
            variant='outline'
            size='sm'
            onClick={() => {
              resetTheme()
              resetFont()
              resetLayout()
              accessibility.resetAccessibility()
            }}
          >
            <RotateCcw />
            Reset to defaults
          </Button>
        }
      >
        <SettingGroup label='Theme'>
          <ChoiceTiles
            label='Theme'
            value={theme}
            options={THEME_CHOICES}
            onChange={setTheme}
          />
        </SettingGroup>
        <SettingGroup
          label='Font'
          description='Used for every text except titles.'
        >
          <ChoiceTiles
            label='Font'
            value={font}
            options={fonts.map((option) => ({
              value: option,
              ...FONT_CHOICE[option],
            }))}
            onChange={setFont}
            columns={3}
          />
        </SettingGroup>
        <SettingGroup label='Sidebar style'>
          <ChoiceTiles
            label='Sidebar style'
            value={variant}
            options={VARIANTS}
            onChange={setVariant}
          />
        </SettingGroup>
        <SettingGroup label='Sidebar collapse'>
          <ChoiceTiles
            label='Sidebar collapse'
            value={collapsible}
            options={COLLAPSES}
            onChange={setCollapsible}
          />
        </SettingGroup>
      </Section>
      <Section
        title='Reading comfort'
        description='Sizes, contrast and motion for easier reading.'
        surface='card'
        icon={Accessibility}
        tone='info'
      >
        <SettingGroup
          label='Text size'
          description='Scales every text and control.'
        >
          <ChoiceTiles
            label='Text size'
            value={accessibility.textSize}
            options={TEXT_SIZE_CHOICES}
            onChange={accessibility.setTextSize}
          />
        </SettingGroup>
        <SettingGroup label='Contrast'>
          <ChoiceTiles
            label='Contrast'
            value={accessibility.contrast}
            options={CONTRASTS}
            onChange={accessibility.setContrast}
            columns={2}
          />
        </SettingGroup>
        <SettingGroup label='Motion'>
          <ChoiceTiles
            label='Motion'
            value={accessibility.motion}
            options={MOTIONS}
            onChange={accessibility.setMotion}
            columns={2}
          />
        </SettingGroup>
      </Section>
    </>
  )
}

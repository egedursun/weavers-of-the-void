import { navItem } from '@/config/navigation'
import { PageHeader } from '@/components/domain'
import { Label } from '@/components/typography'
import { BrandSpecimens } from './BrandSpecimens'
import { ControlSpecimens } from './ControlSpecimens'
import { DomainSpecimens } from './DomainSpecimens'
import { SonCardSpecimens } from './SonCardSpecimens'
import { SurfaceSpecimens } from './SurfaceSpecimens'
import { TypographySpecimens } from './TypographySpecimens'

const ITEM = navItem('design')

const THEMES = [
  { id: 'dark', title: 'Dark theme' },
  { id: 'light', title: 'Light theme' },
] as const

export function DesignScreen() {
  return (
    <>
      <PageHeader
        title={ITEM.title}
        description='The Weavers of the Void® brand kit: mark, palette, type, components and voice, in both themes.'
        icon={ITEM.icon}
      />
      {THEMES.map((theme) => (
        <div
          key={theme.id}
          data-theme-panel={theme.id}
          className={`${theme.id} flex min-w-0 flex-col gap-8 rounded-xl border bg-background p-4 text-foreground md:p-6`}
        >
          <Label variant='overline'>{theme.title}</Label>
          <BrandSpecimens />
          <TypographySpecimens />
          <ControlSpecimens />
          <SurfaceSpecimens />
          <DomainSpecimens />
          <SonCardSpecimens />
        </div>
      ))}
    </>
  )
}

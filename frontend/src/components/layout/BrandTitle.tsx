import { useState } from 'react'
import { APP_NAME, APP_SUBTITLE } from '@/config/brand'
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'
import { Label, Text } from '@/components/typography'
import { Logo } from './Logo'
import { AboutDialog } from './about/AboutDialog'

export function BrandTitle() {
  const [aboutOpen, setAboutOpen] = useState(false)
  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton
          size='lg'
          tooltip={`${APP_NAME}®`}
          aria-haspopup='dialog'
          onClick={() => setAboutOpen(true)}
        >
          <span className='flex size-8 shrink-0 items-center justify-center'>
            <Logo className='size-full' title={APP_NAME} />
          </span>
          <span className='grid min-w-0 flex-1 text-start'>
            <Text
              as='span'
              weight='semibold'
              truncate
              className='font-brand text-primary'
            >
              {`${APP_NAME}®`}
            </Text>
            <Label truncate>{APP_SUBTITLE}</Label>
          </span>
        </SidebarMenuButton>
        <AboutDialog open={aboutOpen} onOpenChange={setAboutOpen} />
      </SidebarMenuItem>
    </SidebarMenu>
  )
}

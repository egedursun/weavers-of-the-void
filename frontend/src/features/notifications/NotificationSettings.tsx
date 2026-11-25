import { useState } from 'react'
import { Save } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Label as FieldLabel } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Medallion, Paged, Section } from '@/components/domain'
import { Muted } from '@/components/typography'
import { useRuleValue } from '@/features/world-rules/api'
import {
  type NotificationCategory,
  type NotificationList,
  useSaveNotificationSettings,
} from './api'
import { CATEGORY_ICON, CATEGORY_TONE } from './notificationVisuals'

const TOAST_RULE = 'notifications.toast_min_importance'
const SEVERITY_STEPS = [1, 2, 3, 4] as const

type NotificationSettingsProps = {
  list: NotificationList
}

export function NotificationSettings({ list }: NotificationSettingsProps) {
  const save = useSaveNotificationSettings()
  const threshold = useRuleValue(TOAST_RULE)
  const [draft, setDraft] = useState<
    Partial<Record<NotificationCategory, boolean>>
  >(() => ({ ...list.settings }))
  const changed = list.categories.some(
    (info) =>
      (draft[info.category] ?? info.enabled_by_default) !==
      (list.settings[info.category] ?? info.enabled_by_default)
  )
  const ordered = [...list.categories].sort(
    (left, right) => right.severity - left.severity
  )
  return (
    <Section
      title='Which events are notified'
      description='Categories you turn off never enter the list.'
      surface='card'
      level={3}
    >
      <ul className='@container/notify flex min-w-0 flex-col gap-1.5'>
        <Paged items={ordered} as='li'>
          {(info) => {
            const on = draft[info.category] ?? info.enabled_by_default
            const id = `notify-${info.category}`
            return (
              <li
                key={info.category}
                className={cn(
                  'flex min-w-0 items-center gap-3 rounded-md border surface-sheen border-gild/60 bg-card p-2',
                  on ? 'bg-card' : 'bg-muted/40'
                )}
              >
                <div className='hidden shrink-0 @3xs/notify:block'>
                  <Medallion
                    icon={CATEGORY_ICON[info.category]}
                    tone={on ? CATEGORY_TONE[info.category] : 'muted'}
                    size='sm'
                  />
                </div>
                <div className='flex min-w-0 flex-1 flex-col gap-1'>
                  <FieldLabel
                    htmlFor={id}
                    className='block min-w-0 wrap-break-word'
                  >
                    {info.label}
                  </FieldLabel>
                  <span
                    className='flex items-center gap-0.5'
                    aria-label={`Importance ${info.severity} of 4`}
                    title={`Importance ${info.severity} of 4`}
                  >
                    {SEVERITY_STEPS.map((step) => (
                      <span
                        key={step}
                        className={cn(
                          'h-1 w-3 rounded-full',
                          step <= info.severity ? 'bg-primary' : 'bg-muted'
                        )}
                      />
                    ))}
                  </span>
                </div>
                <Switch
                  id={id}
                  checked={on}
                  onCheckedChange={(checked) =>
                    setDraft((current) => ({
                      ...current,
                      [info.category]: checked,
                    }))
                  }
                />
              </li>
            )
          }}
        </Paged>
      </ul>
      {threshold !== null && (
        <Muted variant='caption'>
          {`Notifications of importance ${threshold} and above also appear briefly on screen. The threshold is a world rule (Notifications).`}
        </Muted>
      )}
      <Button
        act={save}
        variant='outline'
        className='self-start'
        disabled={!changed || save.isPending}
        disabledReason={changed ? 'Saving' : 'Nothing has changed'}
        onClick={() =>
          save.mutate(draft, {
            onSuccess: () => toast.success('Notification preferences saved'),
            onError: (error) => toast.error(error.message),
          })
        }
      >
        <Save />
        Save preferences
      </Button>
    </Section>
  )
}

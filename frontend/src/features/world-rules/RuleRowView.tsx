import {
  ChevronDown,
  ChevronRight,
  RotateCcw,
  TriangleAlert,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { Switch } from '@/components/ui/switch'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Medallion } from '@/components/domain'
import { Label, Muted, SectionTitle, Text } from '@/components/typography'
import { type Rule } from './api'
import { RULE_GROUP_FALLBACK, RULE_GROUP_ICON } from './ruleGroupIcons'
import {
  type RuleRow,
  exceedsMaximum,
  formatRuleValue,
  isChanged,
  isSwitch,
} from './rulesModel'

type GroupHeaderProps = {
  row: Extract<RuleRow, { type: 'group' }>
  onToggle: (group: string) => void
  onResetGroup: (group: string) => void
  busy: boolean
}

export function GroupHeader({
  row,
  onToggle,
  onResetGroup,
  busy,
}: GroupHeaderProps) {
  const Icon = row.open ? ChevronDown : ChevronRight
  return (
    <div className='flex min-w-0 items-center gap-2 border-b pt-4 pb-2'>
      <Medallion
        icon={RULE_GROUP_ICON[row.group] ?? RULE_GROUP_FALLBACK}
        tone={row.changed > 0 ? 'warning' : 'gold'}
        size='sm'
      />
      <Button
        variant='ghost'
        size='sm'
        aria-expanded={row.open}
        onClick={() => onToggle(row.group)}
        className='min-w-0 flex-1 justify-start'
      >
        <Icon />
        <SectionTitle level={3} truncate>
          {row.group}
        </SectionTitle>
      </Button>
      <Label className='shrink-0'>
        {row.total === 1 ? '1 rule' : `${row.total} rules`}
      </Label>
      {row.changed > 0 && (
        <>
          <Badge size='sm' variant='warning'>
            {`${row.changed} changed`}
          </Badge>
          <Button
            variant='ghost'
            size='sm'
            disabled={busy}
            disabledReason='Saving'
            onClick={() => onResetGroup(row.group)}
          >
            <RotateCcw />
            Reset group
          </Button>
        </>
      )}
    </div>
  )
}

const PERCENT = 100

function rangeShare(rule: Rule, shown: string): number {
  const value = Number(shown)
  const span = rule.maximum - rule.minimum
  if (!Number.isFinite(value) || span <= 0) return 0
  return Math.max(
    0,
    Math.min(PERCENT, ((value - rule.minimum) / span) * PERCENT)
  )
}

type RuleLineProps = {
  rule: Rule
  path: string
  draft: string | undefined
  error: string | undefined
  busy: boolean
  onDraft: (path: string, text: string | null) => void
  onReset: (rule: Rule) => void
}

export function RuleLine({
  rule,
  path,
  draft,
  error,
  busy,
  onDraft,
  onReset,
}: RuleLineProps) {
  const changed = isChanged(rule)
  const pending = draft !== undefined
  const shown = draft ?? String(rule.value)
  const controlId = `rule-${path}`
  const advisory = pending ? exceedsMaximum(rule, shown) : rule.warning != null
  const advisoryText =
    rule.warning ??
    `Above the advised maximum of ${formatRuleValue(rule, rule.maximum)}.`
  return (
    <div
      data-rule={path}
      data-changed={changed || undefined}
      className={cn(
        'grid min-w-0 grid-cols-1 items-center gap-x-4 gap-y-2 border-b py-3 md:grid-cols-6',
        (changed || pending) && 'bg-accent/40'
      )}
    >
      <div className='flex min-w-0 flex-col gap-0.5 px-2 md:col-span-3'>
        <Tooltip>
          <TooltipTrigger asChild>
            <Text as='label' htmlFor={controlId} weight='medium' truncate={2}>
              {rule.label}
            </Text>
          </TooltipTrigger>
          <TooltipContent>{path}</TooltipContent>
        </Tooltip>
        <Muted variant='caption' truncate>
          {`Default ${formatRuleValue(rule, rule.default)} · minimum ${formatRuleValue(rule, rule.minimum)}, advised maximum ${formatRuleValue(rule, rule.maximum)}`}
        </Muted>
        {!isSwitch(rule) && (
          <Progress
            size='sm'
            tone={
              advisory ? 'warning' : changed || pending ? 'default' : 'muted'
            }
            value={rangeShare(rule, shown)}
            aria-label={`${rule.label} within its range`}
          />
        )}
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2 px-2 md:col-span-2'>
        {isSwitch(rule) ? (
          <Switch
            id={controlId}
            checked={shown === '1'}
            disabled={busy}
            onCheckedChange={(checked) => {
              const next = checked ? '1' : '0'
              onDraft(path, next === String(rule.value) ? null : next)
            }}
          />
        ) : (
          <Input
            id={controlId}
            type='number'
            inputMode={rule.integer ? 'numeric' : 'decimal'}
            min={rule.minimum}
            step={rule.integer ? 1 : 'any'}
            value={shown}
            disabled={busy}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? `${controlId}-error` : undefined}
            onChange={(event) =>
              onDraft(
                path,
                event.target.value === String(rule.value)
                  ? null
                  : event.target.value
              )
            }
            className='w-36'
          />
        )}
        {advisory && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Badge size='sm' variant='warning' data-advisory={path}>
                <TriangleAlert />
                Above advised maximum
              </Badge>
            </TooltipTrigger>
            <TooltipContent>{advisoryText}</TooltipContent>
          </Tooltip>
        )}
        {(changed || pending) && (
          <Badge size='sm' variant={pending ? 'default' : 'warning'}>
            {pending ? 'Unsaved' : 'Differs from default'}
          </Badge>
        )}
      </div>
      <div className='flex min-w-0 items-center justify-end gap-1 px-2'>
        {pending && (
          <Button variant='ghost' size='sm' onClick={() => onDraft(path, null)}>
            Discard
          </Button>
        )}
        {changed && (
          <Button
            variant='ghost'
            size='sm'
            disabled={busy}
            disabledReason='Saving'
            aria-label={`Reset ${rule.label} to ${formatRuleValue(rule, rule.default)}`}
            onClick={() => onReset(rule)}
          >
            <RotateCcw />
            {formatRuleValue(rule, rule.default)}
          </Button>
        )}
      </div>
      {error && (
        <Text
          id={`${controlId}-error`}
          variant='caption'
          tone='destructive'
          role='alert'
          className='px-2 md:col-span-6'
        >
          {error}
        </Text>
      )}
    </div>
  )
}

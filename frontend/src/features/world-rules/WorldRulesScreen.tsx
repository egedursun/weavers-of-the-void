import { useMemo, useRef, useState } from 'react'
import { useSearch } from '@tanstack/react-router'
import {
  FilePen,
  FolderTree,
  Layers,
  RotateCcw,
  Save,
  Search,
  SlidersHorizontal,
  TriangleAlert,
} from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  ConfirmDialog,
  EmptyState,
  MiniStat,
  Section,
} from '@/components/domain'
import { Muted, Stat, Text } from '@/components/typography'
import { GroupHeader, RuleLine } from './RuleRowView'
import { Spacer } from './Spacer'
import {
  type Rule,
  rulePath,
  useResetAllRules,
  useResetGroup,
  useResetRule,
  useRules,
  useSaveRules,
} from './api'
import { RULE_GROUP_FALLBACK, RULE_GROUP_ICON } from './ruleGroupIcons'
import {
  ALL_GROUPS,
  buildRows,
  errorsByPath,
  groupsOf,
  isChanged,
  parseDraft,
} from './rulesModel'
import { useRowWindow } from './useRowWindow'

const ESTIMATED_GROUP_PX = 56
const ESTIMATED_RULE_PX = 76
const OVERSCAN = 12

type RulesEditorProps = {
  rules: Rule[]
}

function RulesEditor({ rules }: RulesEditorProps) {
  const search = useSearch({ from: '/_app/settings/world-rules' })
  const [query, setQuery] = useState(search.q ?? '')
  const [group, setGroup] = useState(ALL_GROUPS)
  const [onlyChanged, setOnlyChanged] = useState(false)
  const [open, setOpen] = useState<Set<string>>(
    () => new Set(rules.filter(isChanged).map((rule) => rule.group))
  )
  const [drafts, setDrafts] = useState<Map<string, string>>(new Map())
  const [serverErrors, setServerErrors] = useState<Map<string, string>>(
    new Map()
  )
  const [generalError, setGeneralError] = useState<string | null>(null)
  const [confirmAll, setConfirmAll] = useState(false)
  const resetRule = useResetRule()
  const resetGroup = useResetGroup()
  const resetAll = useResetAllRules()
  const save = useSaveRules()
  const busy =
    save.isPending ||
    resetRule.isPending ||
    resetGroup.isPending ||
    resetAll.isPending

  const byPath = useMemo(
    () => new Map(rules.map((rule) => [rulePath(rule), rule])),
    [rules]
  )
  const groups = useMemo(() => groupsOf(rules), [rules])
  const rows = useMemo(
    () => buildRows(rules, { query, group, onlyChanged, open }),
    [group, onlyChanged, open, query, rules]
  )
  const changedCount = rules.filter(isChanged).length
  const aboveCount = rules.filter((rule) => rule.value > rule.maximum).length
  const groupStats = useMemo(() => {
    const map = new Map<string, { total: number; changed: number }>()
    for (const rule of rules) {
      const stat = map.get(rule.group) ?? { total: 0, changed: 0 }
      stat.total += 1
      if (isChanged(rule)) stat.changed += 1
      map.set(rule.group, stat)
    }
    return map
  }, [rules])
  const chooseGroup = (name: string) => {
    setGroup(name)
    if (name !== ALL_GROUPS) setOpen((current) => new Set(current).add(name))
    scroller.current?.scrollTo({ top: 0 })
  }
  const shownRules = rows.reduce(
    (sum, row) => (row.type === 'group' ? sum + row.total : sum),
    0
  )

  const clientErrors = useMemo(() => {
    const found = new Map<string, string>()
    for (const [path, text] of drafts) {
      const rule = byPath.get(path)
      if (!rule) continue
      const parsed = parseDraft(rule, text)
      if (typeof parsed === 'string') found.set(path, parsed)
    }
    return found
  }, [byPath, drafts])

  const scroller = useRef<HTMLDivElement>(null)
  const { items, before, after, measure } = useRowWindow({
    count: rows.length,
    scroller,
    estimateSize: (index) =>
      rows[index].type === 'group' ? ESTIMATED_GROUP_PX : ESTIMATED_RULE_PX,
    overscan: OVERSCAN,
    getItemKey: (index) => {
      const row = rows[index]
      return row.type === 'group' ? `group:${row.group}` : row.path
    },
  })

  const onDraft = (path: string, text: string | null) => {
    setGeneralError(null)
    setServerErrors((current) => {
      if (!current.has(path)) return current
      const next = new Map(current)
      next.delete(path)
      return next
    })
    setDrafts((current) => {
      const next = new Map(current)
      if (text === null) next.delete(path)
      else next.set(path, text)
      return next
    })
  }

  const toggleGroup = (name: string) =>
    setOpen((current) => {
      const next = new Set(current)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })

  const fail = (error: Error) => toast.error(error.message)

  const onSave = () => {
    if (drafts.size === 0) {
      toast.info('No rule has changed.')
      return
    }
    if (clientErrors.size > 0) {
      setGeneralError('Fix the marked rules before saving.')
      return
    }
    const changes = new Map<Rule, number>()
    for (const [path, text] of drafts) {
      const rule = byPath.get(path)
      if (rule) changes.set(rule, Number(text))
    }
    save.mutate(changes, {
      onSuccess: () => {
        toast.success(`${drafts.size} rules updated`)
        setDrafts(new Map())
        setServerErrors(new Map())
        setGeneralError(null)
      },
      onError: (error) => {
        setServerErrors(errorsByPath(error.message, drafts.keys()))
        setGeneralError(error.message)
      },
    })
  }

  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-5'>
        <MiniStat
          icon={SlidersHorizontal}
          label='Rules'
          value={rules.length}
          tone='gold'
        />
        <MiniStat
          icon={FolderTree}
          label='Groups'
          value={groups.length}
          tone='verdigris'
        />
        <MiniStat
          icon={Layers}
          label='Differ from default'
          value={changedCount}
          tone={changedCount > 0 ? 'warning' : 'muted'}
        />
        <MiniStat
          icon={FilePen}
          label='Unsaved'
          value={drafts.size}
          tone={drafts.size > 0 ? 'info' : 'muted'}
        />
        <MiniStat
          icon={TriangleAlert}
          label='Above advised max'
          value={aboveCount}
          tone={aboveCount > 0 ? 'danger' : 'success'}
        />
      </div>
      <Muted>
        Numbers you change take effect immediately: costs, the sons&apos; tools
        and the world engine all read the new value.{' '}
        {changedCount > 0 && (
          <>
            <Stat value={changedCount} /> rules differ from the default.
          </>
        )}
      </Muted>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Input
          type='search'
          leadingIcon={Search}
          aria-label='Search rules'
          placeholder='Search rules, for example doom, war or plague'
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className='flex-1 basis-64'
        />
        <Select value={group} onValueChange={chooseGroup}>
          <SelectTrigger
            aria-label='Rule group'
            className='w-full sm:w-56 lg:hidden'
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_GROUPS}>All groups</SelectItem>
            {groups.map((name) => (
              <SelectItem key={name} value={name}>
                {name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className='flex items-center gap-2'>
          <Checkbox
            id='rules-only-changed'
            checked={onlyChanged}
            onCheckedChange={(checked) => setOnlyChanged(checked === true)}
          />
          <FieldLabel htmlFor='rules-only-changed'>Only changed</FieldLabel>
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
        <Muted variant='caption'>
          {shownRules === rules.length
            ? `${rules.length} rules in ${groups.length} groups`
            : `${shownRules} of ${rules.length} rules shown`}
        </Muted>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Button
            variant='outline'
            disabled={changedCount === 0 || busy}
            disabledReason={
              changedCount === 0 ? 'No rule differs from its default' : 'Saving'
            }
            onClick={() => setConfirmAll(true)}
          >
            <RotateCcw />
            Reset all
          </Button>
          <Button
            onClick={onSave}
            disabled={drafts.size === 0 || busy}
            disabledReason={
              drafts.size === 0 ? 'Change a rule first' : 'Saving'
            }
          >
            <Save />
            {drafts.size > 0 ? `Save ${drafts.size} changes` : 'Save changes'}
          </Button>
        </div>
      </div>
      {generalError && (
        <Text tone='destructive' role='alert'>
          {generalError}
        </Text>
      )}
      <div className='grid min-w-0 grid-cols-1 gap-3 lg:grid-cols-4'>
        <nav
          aria-label='Rule groups'
          className='hidden h-160 min-w-0 flex-col gap-0.5 overflow-y-auto rounded-lg border bg-background p-1.5 lg:flex'
        >
          <Button
            variant={group === ALL_GROUPS ? 'secondary' : 'ghost'}
            size='sm'
            className='w-full justify-start'
            aria-current={group === ALL_GROUPS ? 'true' : undefined}
            onClick={() => chooseGroup(ALL_GROUPS)}
          >
            <SlidersHorizontal />
            <span className='min-w-0 flex-1 truncate text-start'>
              All groups
            </span>
            <Badge size='sm' variant='outline'>
              {rules.length}
            </Badge>
          </Button>
          {groups.map((name) => {
            const Icon = RULE_GROUP_ICON[name] ?? RULE_GROUP_FALLBACK
            const stat = groupStats.get(name)
            const active = group === name
            return (
              <Button
                key={name}
                variant={active ? 'secondary' : 'ghost'}
                size='sm'
                className='w-full justify-start'
                aria-current={active ? 'true' : undefined}
                onClick={() => chooseGroup(name)}
              >
                <Icon />
                <span className='min-w-0 flex-1 truncate text-start'>
                  {name}
                </span>
                {stat && stat.changed > 0 ? (
                  <Badge size='sm' variant='warning'>
                    {stat.changed}
                  </Badge>
                ) : (
                  <Badge size='sm' variant='outline'>
                    {stat?.total ?? 0}
                  </Badge>
                )}
              </Button>
            )
          })}
        </nav>
        <div
          ref={scroller}
          data-feature='rules-scroller'
          className={cn(
            'h-160 min-w-0 overflow-y-auto overscroll-contain rounded-lg border lg:col-span-3'
          )}
        >
          {rows.length === 0 ? (
            <div className='p-4'>
              <EmptyState
                size='compact'
                icon={SlidersHorizontal}
                title='No rule matches'
                description='Try another word, another group, or turn off Only changed.'
              />
            </div>
          ) : (
            <div className='flex min-w-0 flex-col px-2'>
              <Spacer height={before} />
              {items.map((item) => {
                const row = rows[item.index]
                return (
                  <div key={item.key} data-index={item.index} ref={measure}>
                    {row.type === 'group' ? (
                      <GroupHeader
                        row={row}
                        busy={busy}
                        onToggle={toggleGroup}
                        onResetGroup={(name) =>
                          resetGroup.mutate(
                            rules.filter(
                              (rule) => rule.group === name && isChanged(rule)
                            ),
                            {
                              onSuccess: () =>
                                toast.success(`${name} reset to defaults`),
                              onError: fail,
                            }
                          )
                        }
                      />
                    ) : (
                      <RuleLine
                        rule={row.rule}
                        path={row.path}
                        draft={drafts.get(row.path)}
                        error={
                          clientErrors.get(row.path) ??
                          serverErrors.get(row.path)
                        }
                        busy={busy}
                        onDraft={onDraft}
                        onReset={(rule) =>
                          resetRule.mutate(rule, {
                            onSuccess: () => {
                              onDraft(rulePath(rule), null)
                              toast.success('Rule reset to its default')
                            },
                            onError: fail,
                          })
                        }
                      />
                    )}
                  </div>
                )
              })}
              <Spacer height={after} />
            </div>
          )}
        </div>
      </div>
      <ConfirmDialog
        open={confirmAll}
        onOpenChange={setConfirmAll}
        title='Reset every rule?'
        desc={`${changedCount} rules return to their defaults. The world keeps running with the default numbers from now on.`}
        confirmText='Reset all rules'
        destructive
        isLoading={resetAll.isPending}
        handleConfirm={() =>
          resetAll.mutate(undefined, {
            onSuccess: () => {
              setConfirmAll(false)
              setDrafts(new Map())
              toast.success('All rules reset to their defaults')
            },
            onError: (error) => {
              setConfirmAll(false)
              fail(error)
            },
          })
        }
      />
    </div>
  )
}

export function WorldRulesScreen() {
  const rules = useRules()
  return (
    <Section
      title='World rules'
      description='Every tunable number of the world, grouped by subsystem. Values that differ from the default are marked; related rules are checked together when you save.'
      surface='card'
      icon={SlidersHorizontal}
    >
      {rules.isPending && <Skeleton className='h-160 w-full' />}
      {rules.isError && <Text tone='destructive'>{rules.error.message}</Text>}
      {rules.data && rules.data.length === 0 && (
        <EmptyState
          size='compact'
          icon={SlidersHorizontal}
          title='No rules loaded'
          description='The server returned no rules.'
        />
      )}
      {rules.data && rules.data.length > 0 && (
        <RulesEditor rules={rules.data} />
      )}
    </Section>
  )
}

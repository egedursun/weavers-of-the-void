import { describe, expect, it } from 'vitest'
import { render } from 'vitest-browser-react'
import {
  chronicleKindValues,
  commodityValues,
  creatorPassionValues,
  entityTypeValues,
  mortalToolIdValues,
  passionValues,
  sonToolIdValues,
  statValues,
} from '@/api/generated/schema'
import { toolIcon } from '@/features/feed/feedToolIcons'
import { ChronicleKindIcon } from './ChronicleKindIcon'
import { DomainIcon } from './DomainIcon'
import { ToolIcon } from './ToolIcon'
import {
  CHRONICLE_FALLBACK_ICON,
  CHRONICLE_KIND_ICON,
  chronicleKindIcon,
} from './chronicleKindIcons'
import {
  DOMAIN_ICON_FALLBACK,
  ICON_VOCABULARIES,
  domainIcon,
} from './domainIcons'
import { TOOL_FALLBACK_ICON, TOOL_ICON, toolIdIcon } from './toolIcons'

describe('chronicle kind icons', () => {
  it('give every backend chronicle kind its own entry', () => {
    for (const kind of chronicleKindValues) {
      expect(Object.hasOwn(CHRONICLE_KIND_ICON, kind), kind).toBe(true)
      expect(chronicleKindIcon(kind), kind).not.toBe(CHRONICLE_FALLBACK_ICON)
    }
    expect(Object.keys(CHRONICLE_KIND_ICON).sort()).toEqual(
      [...chronicleKindValues].sort()
    )
  })

  it('falls back for an unknown kind and renders an svg', async () => {
    expect(chronicleKindIcon('unheard_of')).toBe(CHRONICLE_FALLBACK_ICON)
    const screen = await render(<ChronicleKindIcon kind='war' />)
    const icon = screen.container.querySelector('[data-chronicle-kind="war"]')
    expect(icon?.tagName.toLowerCase()).toBe('svg')
  })
})

describe('tool icons', () => {
  const toolIds = [...new Set([...sonToolIdValues, ...mortalToolIdValues])]

  it('give every son and mortal tool id its own entry', () => {
    for (const tool of toolIds) {
      expect(Object.hasOwn(TOOL_ICON, tool), tool).toBe(true)
      expect(toolIdIcon(tool), tool).toBe(TOOL_ICON[tool])
      expect(toolIcon(tool), tool).toBe(TOOL_ICON[tool])
    }
    expect(Object.keys(TOOL_ICON).sort()).toEqual(toolIds.sort())
  })

  it('falls back to a wrench for an unknown tool and renders an svg', async () => {
    expect(toolIdIcon('dig_a_moat')).toBeNull()
    expect(toolIcon(null)).toBe(TOOL_FALLBACK_ICON)
    const screen = await render(<ToolIcon tool='miracle' />)
    expect(
      screen.container.querySelector('svg[data-tool="miracle"]')
    ).not.toBeNull()
  })
})

describe('domain icon vocabulary', () => {
  const vocabularies = {
    'entity-type': entityTypeValues,
    stat: statValues,
    passion: passionValues,
    'creator-passion': creatorPassionValues,
    commodity: commodityValues,
  } as const

  it('maps every entity type, stat, passion and commodity of the backend', () => {
    for (const [vocabulary, values] of Object.entries(vocabularies)) {
      const table = ICON_VOCABULARIES[vocabulary as keyof typeof vocabularies]
      expect(Object.keys(table).sort(), vocabulary).toEqual([...values].sort())
      for (const value of values)
        expect(
          domainIcon(vocabulary as keyof typeof vocabularies, value)
        ).not.toBe(DOMAIN_ICON_FALLBACK)
    }
  })

  it('falls back for an unknown value and renders an svg', async () => {
    expect(domainIcon('stat', 'luck')).toBe(DOMAIN_ICON_FALLBACK)
    const screen = await render(
      <DomainIcon vocabulary='entity-type' value='settlement' />
    )
    expect(
      screen.container.querySelector('svg[data-icon-value="settlement"]')
    ).not.toBeNull()
  })
})

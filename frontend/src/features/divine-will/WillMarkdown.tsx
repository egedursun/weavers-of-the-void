import { type ComponentProps, type ReactNode, useMemo } from 'react'
import { Link } from '@tanstack/react-router'
import ReactMarkdown, {
  type Components,
  defaultUrlTransform,
} from 'react-markdown'
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'
import { cn } from '@/lib/utils'
import { EntityLink, Picture } from '@/components/domain'
import { Text } from '@/components/typography'
import { useNames } from '@/features/entity/api/queries'
import {
  type NameEntry,
  REFERENCE_PROTOCOLS,
  parseReferenceHref,
  referenceHref,
  resolveReference,
  splitReferences,
} from './references'

type MdNode = {
  type: string
  value?: string
  url?: string
  children?: MdNode[]
}

const SKIPPED = new Set(['link', 'linkReference', 'code', 'inlineCode', 'html'])

function linkReferences(node: MdNode) {
  if (!node.children || SKIPPED.has(node.type)) return
  const next: MdNode[] = []
  for (const child of node.children) {
    if (child.type !== 'text' || !child.value) {
      linkReferences(child)
      next.push(child)
      continue
    }
    for (const piece of splitReferences(child.value)) {
      if (piece.type === 'text') next.push({ type: 'text', value: piece.text })
      else
        next.push({
          type: 'link',
          url: referenceHref(piece.reference),
          children: [{ type: 'text', value: piece.text }],
        })
    }
  }
  node.children = next
}

function remarkReferences() {
  return (tree: MdNode) => linkReferences(tree)
}

const SCHEMA = {
  ...defaultSchema,
  protocols: {
    ...defaultSchema.protocols,
    href: [...(defaultSchema.protocols?.href ?? []), ...REFERENCE_PROTOCOLS],
  },
}

function keepReferences(url: string): string {
  return parseReferenceHref(url) ? url : defaultUrlTransform(url)
}

function textOf(children: ReactNode): string {
  if (typeof children === 'string') return children
  if (Array.isArray(children)) return children.map(textOf).join('')
  return ''
}

function ReferenceLink({
  href,
  children,
  names,
}: {
  href: string | undefined
  children: ReactNode
  names: ReadonlyMap<number, NameEntry>
}) {
  const reference = parseReferenceHref(href)
  if (!reference)
    return (
      <a href={href} target='_blank' rel='noreferrer noopener'>
        {children}
      </a>
    )
  const target = resolveReference(reference, names)
  const shown = textOf(children)
  const token = /^[a-z_]*#\d+$/.test(shown)
  const label = token ? target.label : children
  if (target.type === 'entry')
    return (
      <EntityLink kind={target.kind} id={target.id}>
        {label}
      </EntityLink>
    )
  if (target.type === 'artifact')
    return (
      <Link
        to='/library'
        search={{ artifact: target.id }}
        className='text-primary underline-offset-4 hover:underline'
      >
        {label}
      </Link>
    )
  return (
    <Text as='span' weight='medium'>
      {label}
    </Text>
  )
}

type WillMarkdownProps = {
  text: string
  size?: 'body' | 'prose'
  className?: string
}

export function WillMarkdown({
  text,
  size = 'body',
  className,
}: WillMarkdownProps) {
  const names = useNames(/[a-z_]*#\d+|\]\(\w+:/.test(text))
  const byId = useMemo(() => {
    const map = new Map<number, NameEntry>()
    for (const entry of names.data ?? []) map.set(entry.id, entry)
    return map
  }, [names.data])
  const components = useMemo<Components>(
    () => ({
      a: ({ href, children }) => (
        <ReferenceLink href={href} names={byId}>
          {children}
        </ReferenceLink>
      ),
      img: ({ src, alt }: ComponentProps<'img'>) => (
        <Picture
          src={typeof src === 'string' ? src : null}
          alt={alt ?? ''}
          className='max-w-full rounded-md'
        />
      ),
    }),
    [byId]
  )
  return (
    <div
      data-domain='will-markdown'
      data-size={size}
      className={cn('will-prose', className)}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkReferences]}
        rehypePlugins={[[rehypeSanitize, SCHEMA]]}
        urlTransform={keepReferences}
        components={components}
      >
        {text}
      </ReactMarkdown>
    </div>
  )
}

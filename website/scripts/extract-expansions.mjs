import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const root = join(here, '..', '..')
const readme = readFileSync(join(root, 'README.md'), 'utf8').split('\n')
const output = join(here, '..', 'src', 'data', 'expansions.en.json')

const CHAPTER = /^### (\S+) ([IVX]+)\. (.+)$/
const EXPANSION = /^#### (\d+)\. (.+)$/
const FEATURE = /^- \*\*(.+?)\*\* — (.+)$/
const STORY = /^\*\*In your world:\*\* (.+)$/
const TAGLINE = /^\*(.+)\*$/

function plain(text) {
  return text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .trim()
}

function slugOf(name) {
  return name
    .toLowerCase()
    .replace(/['’]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

function readBlock(start, stop) {
  const block = { tagline: '', intro: [], features: [], story: '' }
  for (let index = start; index < stop; index += 1) {
    const line = readme[index].trim()
    if (!line || line.startsWith('<') || line.startsWith('#')) continue
    const feature = FEATURE.exec(line)
    const story = STORY.exec(line)
    const tagline = TAGLINE.exec(line)
    if (feature) block.features.push({ title: plain(feature[1]), text: plain(feature[2]) })
    else if (story) block.story = plain(story[1])
    else if (tagline && !block.tagline && block.intro.length === 0) block.tagline = plain(tagline[1])
    else if (block.features.length === 0 && !line.startsWith('- ')) block.intro.push(plain(line))
  }
  return block
}

function boundary(from) {
  for (let index = from + 1; index < readme.length; index += 1) {
    const line = readme[index]
    if (EXPANSION.test(line) || CHAPTER.test(line) || line.startsWith('## ') || line.startsWith('### ')) return index
  }
  return readme.length
}

const loomStart = readme.findIndex((line) => line.trim() === '### The Loom')
const loom = {
  number: 0,
  name: 'The Loom',
  slug: 'the-loom',
  ...readBlock(loomStart + 1, boundary(loomStart)),
}

const chapters = []
let chapter = null
readme.forEach((line, index) => {
  const heading = CHAPTER.exec(line)
  if (heading) {
    chapter = { numeral: heading[2], title: heading[3], sign: heading[1], expansions: [] }
    chapters.push(chapter)
    return
  }
  const expansion = EXPANSION.exec(line)
  if (expansion && chapter) {
    const name = plain(expansion[2])
    chapter.expansions.push({
      number: Number(expansion[1]),
      name,
      slug: slugOf(name),
      ...readBlock(index + 1, boundary(index)),
    })
  }
})

const count = chapters.reduce((sum, item) => sum + item.expansions.length, 0)
if (chapters.length !== 15 || count !== 99) {
  throw new Error(`expected 15 chapters and 99 expansions, found ${chapters.length} and ${count}`)
}
for (const item of [loom, ...chapters.flatMap((entry) => entry.expansions)]) {
  if (!item.tagline || item.features.length === 0 || !item.story || item.intro.length === 0) {
    throw new Error(`expansion ${item.number} ${item.name} is missing its tagline, intro, features or story`)
  }
}

mkdirSync(dirname(output), { recursive: true })
writeFileSync(output, `${JSON.stringify({ loom, chapters }, null, 2)}\n`)
console.log(`expansions: ${count} in ${chapters.length} chapters, plus The Loom`)

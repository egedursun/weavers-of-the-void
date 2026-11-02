import { readFileSync, statSync, writeFileSync } from 'node:fs'
import { globSync } from 'node:fs'
import ts from 'typescript'

const SOURCE_GLOBS = ['src/**/*.{ts,tsx}', '*.{ts,js,mjs}', 'scripts/**/*.mjs', 'e2e/**/*.ts', 'eslint/**/*.js']
const IGNORED = /routeTree\.gen\.ts$/

function stripTypeScript(text, fileName) {
  const source = ts.createSourceFile(fileName, text, ts.ScriptTarget.Latest, true, fileName.endsWith('x') ? ts.ScriptKind.TSX : ts.ScriptKind.TS)
  const ranges = []
  const visit = (node) => {
    if (ts.isJsxExpression(node) && !node.expression) {
      ranges.push([node.getStart(source), node.getEnd()])
      return
    }
    ts.forEachChild(node, visit)
  }
  visit(source)
  const commentRanges = []
  const collect = (position) => {
    for (const range of ts.getLeadingCommentRanges(text, position) ?? []) commentRanges.push([range.pos, range.end])
    for (const range of ts.getTrailingCommentRanges(text, position) ?? []) commentRanges.push([range.pos, range.end])
  }
  const walk = (node) => {
    collect(node.getFullStart())
    collect(node.getEnd())
    ts.forEachChild(node, walk)
  }
  walk(source)
  collect(source.endOfFileToken.getFullStart())
  const all = [...ranges, ...commentRanges]
    .filter(([start]) => !ranges.some(([outerStart, outerEnd]) => start > outerStart && start < outerEnd))
    .sort((a, b) => b[0] - a[0])
  let result = text
  let lastStart = Infinity
  for (const [start, end] of all) {
    if (end > lastStart) continue
    if (text.slice(start, end).startsWith('#!')) continue
    result = result.slice(0, start) + result.slice(end)
    lastStart = start
  }
  return result
    .split('\n')
    .map((line) => line.replace(/[ \t]+$/, ''))
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
}

const files = SOURCE_GLOBS.flatMap((pattern) => globSync(pattern)).filter((file) => !IGNORED.test(file) && statSync(file).isFile())
let changed = 0
for (const file of files) {
  const original = readFileSync(file, 'utf8')
  const stripped = stripTypeScript(original, file)
  if (stripped !== original) {
    writeFileSync(file, stripped)
    changed += 1
  }
}
console.log(`stripped comments in ${changed} file(s)`)

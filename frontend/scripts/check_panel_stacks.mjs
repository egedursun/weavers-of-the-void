import fs from 'node:fs'
import path from 'node:path'
import ts from 'typescript'

const ROOT = path.resolve(import.meta.dirname, '..')
const SOURCE = path.join(ROOT, 'src')
const WIDE_GRID = /(^|\s)(md|lg|xl|2xl):grid-cols-([2-9]|1[0-2])(\s|$)/
const COLUMN = /(^|\s)flex-col(\s|$)/

function sourceFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(directory, entry.name)
    if (entry.isDirectory()) return sourceFiles(full)
    return entry.name.endsWith('.tsx') && !entry.name.endsWith('.test.tsx') ? [full] : []
  })
}

function classText(node) {
  const attributes = ts.isJsxElement(node) ? node.openingElement.attributes : node.attributes
  const parts = []
  for (const attribute of attributes.properties) {
    if (!ts.isJsxAttribute(attribute) || attribute.name.getText() !== 'className') continue
    const visit = (child) => {
      if (ts.isStringLiteralLike(child)) parts.push(child.text)
      ts.forEachChild(child, visit)
    }
    if (attribute.initializer) visit(attribute.initializer)
  }
  return parts.join(' ')
}

function tagName(node) {
  return (ts.isJsxElement(node) ? node.openingElement.tagName : node.tagName).getText()
}

function elements(children) {
  const found = []
  const take = (node) => {
    if (ts.isJsxElement(node) || ts.isJsxSelfClosingElement(node)) found.push(node)
    else if (ts.isJsxFragment(node)) node.children.forEach(take)
    else if (ts.isJsxExpression(node) && node.expression) take(node.expression)
    else if (ts.isBinaryExpression(node)) take(node.right)
    else if (ts.isConditionalExpression(node)) {
      take(node.whenTrue)
      take(node.whenFalse)
    } else if (ts.isParenthesizedExpression(node)) take(node.expression)
  }
  children.forEach(take)
  return found
}

function isComponent(node) {
  return /^[A-Z]/.test(tagName(node))
}

function attributeValue(node, name) {
  const attributes = ts.isJsxElement(node) ? node.openingElement.attributes : node.attributes
  for (const attribute of attributes.properties) {
    if (!ts.isJsxAttribute(attribute) || attribute.name.getText() !== name) continue
    const initializer = attribute.initializer
    if (initializer && ts.isStringLiteral(initializer)) return initializer.text
    return initializer ? initializer.getText() : 'true'
  }
  return null
}

function framesItself(node) {
  const tag = tagName(node)
  if (tag === 'OrnateFrame') return true
  return tag === 'Section' && attributeValue(node, 'surface') === 'card'
}

const sources = sourceFiles(SOURCE).map((file) => ({
  file,
  source: ts.createSourceFile(file, fs.readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX),
}))

const uses = new Map()
const framed = new Set()
for (const { source } of sources) {
  const visit = (node, owner) => {
    let current = owner
    if ((ts.isFunctionDeclaration(node) || ts.isVariableDeclaration(node)) && node.name && /^[A-Z]/.test(node.name.getText())) {
      current = node.name.getText()
      if (!uses.has(current)) uses.set(current, new Set())
    }
    if (current && (ts.isJsxElement(node) || ts.isJsxSelfClosingElement(node))) {
      if (framesItself(node)) framed.add(current)
      else uses.get(current).add(tagName(node))
    }
    ts.forEachChild(node, (child) => visit(child, current))
  }
  visit(source, null)
}
let grew = true
while (grew) {
  grew = false
  for (const [name, tags] of uses) {
    if (framed.has(name)) continue
    for (const tag of tags) {
      if (framed.has(tag)) {
        framed.add(name)
        grew = true
        break
      }
    }
  }
}

function isPanel(node) {
  return isComponent(node) && (framesItself(node) || framed.has(tagName(node)))
}

const problems = []
for (const { file, source } of sources) {
  const visit = (node) => {
    if (ts.isJsxElement(node) && WIDE_GRID.test(classText(node))) {
      for (const column of elements(node.children)) {
        if (isComponent(column) || !ts.isJsxElement(column) || !COLUMN.test(classText(column))) continue
        const stacked = elements(column.children).filter(isPanel)
        if (stacked.length < 2) continue
        const { line } = source.getLineAndCharacterOfPosition(column.getStart())
        problems.push(
          `${path.relative(ROOT, file)}:${line + 1}: a column of ${stacked.length} framed panels (${stacked.map(tagName).join(', ')}) inside a multi-column grid; rows stop lining up. Put each panel straight into PanelGrid.`
        )
      }
    }
    ts.forEachChild(node, visit)
  }
  visit(source)
}

for (const problem of problems) console.log(problem)
console.log(`panel stacks: ${problems.length}`)
process.exit(problems.length ? 1 : 0)

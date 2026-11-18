import fs from 'node:fs'
import path from 'node:path'
import ts from 'typescript'

const ROOT = path.resolve(import.meta.dirname, '..')
const SOURCE = process.argv[2] ? path.resolve(process.argv[2]) : path.join(ROOT, 'src', 'features')
const BARE = new Set(['StatBar'])
const FRAMED = new Set(['MiniStat'])
const TILE_SURFACE = /(^|\s)surface-(sheen|framed)(\s|$)/

function sourceFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(directory, entry.name)
    if (entry.isDirectory()) return sourceFiles(full)
    return entry.name.endsWith('.tsx') && !entry.name.endsWith('.test.tsx') ? [full] : []
  })
}

function tagName(node) {
  return (ts.isJsxElement(node) ? node.openingElement.tagName : node.tagName).getText()
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

function framedProp(node) {
  const attributes = ts.isJsxElement(node) ? node.openingElement.attributes : node.attributes
  return attributes.properties.some(
    (attribute) =>
      ts.isJsxAttribute(attribute) &&
      attribute.name.getText() === 'framed' &&
      (!attribute.initializer || attribute.initializer.getText() !== '{false}')
  )
}

function face(node) {
  const name = tagName(node)
  if (BARE.has(name)) return framedProp(node) ? `framed ${name}` : `bare ${name}`
  if (FRAMED.has(name)) return `framed ${name}`
  if (!/^[a-z]/.test(name)) return null
  if (TILE_SURFACE.test(classText(node))) return `framed <${name}> tile`
  if (!ts.isJsxElement(node)) return null
  const inner = rendered([...node.children]).map(face).filter(Boolean)
  if (inner.length === 0) return null
  if (inner.every((item) => item.startsWith('bare'))) return inner[0]
  if (inner.every((item) => item.startsWith('framed'))) return inner[0]
  return null
}

function returned(fn) {
  if (!ts.isArrowFunction(fn) && !ts.isFunctionExpression(fn)) return []
  if (!ts.isBlock(fn.body)) return [fn.body]
  const found = []
  const visit = (node) => {
    if (ts.isReturnStatement(node) && node.expression) found.push(node.expression)
    else if (!ts.isFunctionLike(node)) ts.forEachChild(node, visit)
  }
  visit(fn.body)
  return found
}

function rendered(children) {
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
    else if (ts.isCallExpression(node) && node.arguments.length > 0)
      returned(node.arguments[0]).forEach(take)
  }
  children.forEach(take)
  return found
}

const problems = []
for (const file of sourceFiles(SOURCE)) {
  const text = fs.readFileSync(file, 'utf8')
  if (!text.includes('StatBar')) continue
  const source = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
  const visit = (node) => {
    if (ts.isJsxElement(node)) {
      const faces = new Set(rendered([...node.children]).map(face).filter(Boolean))
      const bare = [...faces].filter((item) => item.startsWith('bare'))
      const framed = [...faces].filter((item) => item.startsWith('framed'))
      if (bare.length > 0 && framed.length > 0) {
        const { line } = source.getLineAndCharacterOfPosition(node.getStart())
        problems.push(
          `${path.relative(ROOT, file)}:${line + 1} lays a ${bare.join(', ')} beside a ${framed.join(', ')}; frame every value the same way`
        )
      }
    }
    ts.forEachChild(node, visit)
  }
  visit(source)
}

for (const problem of problems) console.log(problem)
console.log(`value frames: ${problems.length}`)
process.exit(problems.length > 0 ? 1 : 0)

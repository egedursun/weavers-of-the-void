import { describe, expect, it } from 'vitest'
import { ApiError, errorFromResponse, serverDown, unwrap } from './errors'

function response(status: number) {
  return new Response(null, { status })
}

describe('api errors', () => {
  it('prefers the server detail message', () => {
    const error = errorFromResponse(response(409), {
      detail: 'The son is asleep.',
    })
    expect(error.message).toBe('The son is asleep.')
    expect(error.status).toBe(409)
  })

  it('reads the error field of the server error body', () => {
    const error = errorFromResponse(response(402), {
      error: '40 essence needed; you have 12.',
      code: 'insufficient',
    })
    expect(error.message).toBe('40 essence needed; you have 12.')
  })

  it('falls back to a message per status', () => {
    expect(errorFromResponse(response(404), null).message).toBe(
      'The requested record does not exist.'
    )
    expect(errorFromResponse(response(418), null).message).toBe(
      'The server refused the request.'
    )
    expect(errorFromResponse(response(507), null).message).toBe(
      'The server failed to complete the request.'
    )
  })

  it('never shows a body that is not the server error object', () => {
    const page =
      '<html> <head><title>502 Bad Gateway</title></head> <body> <center><h1>502 Bad Gateway</h1></center> <hr><center>nginx</center> </body> </html> <!-- a padding to disable MSIE and Chrome friendly error page -->'
    for (const body of [
      page,
      'Internal Server Error',
      ['detail'],
      { detail: [{ msg: 'field required' }] },
      42,
    ]) {
      for (const status of [400, 422, 500, 502, 503, 504]) {
        const message = errorFromResponse(response(status), body).message
        expect(message).not.toMatch(/[<>]|Bad Gateway|nginx|Internal Server/)
        expect(message.length).toBeGreaterThan(0)
      }
    }
  })

  it('tells a server that is down from one that refused', () => {
    expect(serverDown(errorFromResponse(response(502), 'x'))).toBe(true)
    expect(serverDown(errorFromResponse(response(504), null))).toBe(true)
    expect(serverDown(errorFromResponse(undefined, null))).toBe(true)
    expect(serverDown(errorFromResponse(response(409), null))).toBe(false)
    expect(serverDown(new Error('x'))).toBe(false)
  })

  it('reports an unreachable server', () => {
    expect(errorFromResponse(undefined, null).status).toBeNull()
  })

  it('unwraps data and throws api errors', async () => {
    await expect(
      unwrap(Promise.resolve({ data: 5, response: response(200) }))
    ).resolves.toBe(5)
    await expect(
      unwrap(
        Promise.resolve({ error: { detail: 'No.' }, response: response(400) })
      )
    ).rejects.toBeInstanceOf(ApiError)
    await expect(
      unwrap(Promise.reject(new TypeError('fetch failed')))
    ).rejects.toMatchObject({
      status: null,
    })
  })
})

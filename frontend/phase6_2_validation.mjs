import { spawn, spawnSync } from 'node:child_process'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { renderToString } from 'react-dom/server'
import React from 'react'
import { MemoryRouter } from 'react-router-dom'
import { createServer } from 'vite'

const frontendDir = path.dirname(fileURLToPath(import.meta.url))
const projectDir = path.dirname(frontendDir)
const tokenValues = new Map()
globalThis.localStorage = {
  getItem: (key) => tokenValues.get(key) ?? null,
  setItem: (key, value) => tokenValues.set(key, String(value)),
  removeItem: (key) => tokenValues.delete(key),
}
globalThis.window = new EventTarget()

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function run(command, args, cwd = frontendDir) {
  const result = spawnSync(command, args, {
    cwd,
    encoding: 'utf8',
    shell: process.platform === 'win32',
  })
  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(' ')} failed:\n${result.stdout}\n${result.stderr}`)
  }
  return `${result.stdout}${result.stderr}`
}

async function waitForServer(url) {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    try {
      const response = await fetch(url)
      if (response.ok) return
    } catch {
      // The development server may still be starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error(`Timed out waiting for ${url}`)
}

const buildOutput = run('npm.cmd', ['run', 'build'])
assert(buildOutput.includes('built in'), 'Production build did not report success.')
console.log('NPM_BUILD_OK=True')

const clientSource = await readFile(path.join(frontendDir, 'src/api/client.js'), 'utf8')
const contextSource = await readFile(path.join(frontendDir, 'src/context/AuthContext.jsx'), 'utf8')
const routeSource = await readFile(path.join(frontendDir, 'src/routes/AppRoutes.jsx'), 'utf8')
const protectedSource = await readFile(path.join(frontendDir, 'src/components/ProtectedRoute.jsx'), 'utf8')
const loginSource = await readFile(path.join(frontendDir, 'src/pages/Login.jsx'), 'utf8')
const registerSource = await readFile(path.join(frontendDir, 'src/pages/Register.jsx'), 'utf8')

assert(clientSource.includes("ACCESS_TOKEN_KEY = 'wue_access_token'"), 'Token key is not clearly defined.')
assert(contextSource.includes('ACCESS_TOKEN_KEY'), 'Auth context does not reuse the token constant.')
const authServiceSource = await readFile(path.join(frontendDir, 'src/services/authSession.js'), 'utf8')
assert(authServiceSource.includes("apiClient.post('/auth/login'"), 'Login endpoint is incorrect.')
assert(authServiceSource.includes("'Content-Type': 'application/x-www-form-urlencoded'"), 'Login content type is incorrect.')
assert(authServiceSource.includes("apiClient.get('/auth/me')"), 'Current-user restoration is missing.')
assert(authServiceSource.includes("apiClient.post('/auth/register'"), 'Registration endpoint is incorrect.')
assert(!contextSource.includes("localStorage.setItem('password'"), 'A password is stored locally.')
assert(routeSource.includes('path="register"'), 'Registration route is missing.')
for (const route of ['dashboard', 'estimates', 'bom', 'quotations']) {
  assert(routeSource.includes(`path="${route}"`), `Protected route ${route} is missing.`)
}
assert(protectedSource.includes('<Navigate to="/login"'), 'Unauthenticated redirect is missing.')
assert(protectedSource.includes('state={{ from: location }}'), 'Original location is not preserved.')
assert(loginSource.includes('Username or email') && loginSource.includes('type="password"'), 'Login fields do not match the backend.')
assert(registerSource.includes('name="username"') && registerSource.includes('name="email"') && registerSource.includes('name="full_name"'), 'Registration fields do not match the backend.')

const { default: apiClient, ACCESS_TOKEN_KEY, AUTH_UNAUTHORIZED_EVENT } = await import('./src/api/client.js')
const { loginAndLoadCurrentUser, clearAccessToken } = await import('./src/services/authSession.js')
const originalAdapter = apiClient.defaults.adapter
const sessionRequests = []
apiClient.defaults.adapter = async (config) => {
  sessionRequests.push({ url: config.url, authorization: config.headers.get('Authorization'), data: config.data })
  if (config.url === '/auth/login') {
    return { data: { access_token: 'login-token', token_type: 'bearer' }, status: 200, statusText: 'OK', headers: {}, config }
  }
  if (config.url === '/auth/me') {
    return { data: { id: 1, username: 'validator' }, status: 200, statusText: 'OK', headers: {}, config }
  }
  throw new Error(`Unexpected session request: ${config.url}`)
}
const validatedSession = await loginAndLoadCurrentUser('validator', 'not-stored-password')
assert(validatedSession.token === 'login-token', 'Login token was not returned to the provider.')
assert(localStorage.getItem(ACCESS_TOKEN_KEY) === 'login-token', 'Successful login did not store the token.')
assert(sessionRequests[0].url === '/auth/login' && String(sessionRequests[0].data).includes('username=validator'), 'OAuth2 login form is incorrect.')
assert(sessionRequests[1].url === '/auth/me' && sessionRequests[1].authorization === 'Bearer login-token', 'Current user did not load with the new token.')
clearAccessToken()
assert(localStorage.getItem(ACCESS_TOKEN_KEY) === null, 'Logout token clearing failed.')
apiClient.defaults.adapter = originalAdapter
console.log('SUCCESSFUL_LOGIN_STORAGE_OK=True')
console.log('CURRENT_USER_REQUEST_OK=True')
console.log('LOGOUT_TOKEN_CLEAR_OK=True')

localStorage.setItem(ACCESS_TOKEN_KEY, 'validation-token')
let attachedAuthorization = null
await apiClient.get('/interceptor-validation', {
  adapter: async (config) => {
    attachedAuthorization = config.headers.get('Authorization')
    return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
  },
})
assert(attachedAuthorization === 'Bearer validation-token', 'Axios did not attach the Bearer token.')
console.log('AXIOS_AUTH_HEADER_OK=True')

let unauthorizedEvents = 0
let adapterCalls = 0
window.addEventListener(AUTH_UNAUTHORIZED_EVENT, () => { unauthorizedEvents += 1 })
try {
  await apiClient.get('/unauthorized-validation', {
    adapter: async (config) => {
      adapterCalls += 1
      return Promise.reject({ config, response: { status: 401 } })
    },
  })
} catch {
  // Expected: response interceptors must reject without retrying.
}
assert(localStorage.getItem(ACCESS_TOKEN_KEY) === null, 'A 401 did not clear the token.')
assert(adapterCalls === 1, 'The 401 interceptor retried and could loop.')
assert(unauthorizedEvents === 1, 'The provider was not notified exactly once.')
console.log('HTTP_401_HANDLING_OK=True')

const viteSsr = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
try {
  const { default: Login } = await viteSsr.ssrLoadModule('/src/pages/Login.jsx')
  const { default: Register } = await viteSsr.ssrLoadModule('/src/pages/Register.jsx')
  const { AuthContext } = await viteSsr.ssrLoadModule('/src/context/AuthContext.jsx')
  const authValue = {
    accessToken: null, user: null, loading: false, isAuthenticated: false,
    login: async () => {}, register: async () => {}, logout: () => {}, restoreSession: async () => {},
  }
  const renderPage = (Page) => renderToString(
    React.createElement(
      MemoryRouter,
      null,
      React.createElement(AuthContext.Provider, { value: authValue }, React.createElement(Page)),
    ),
  )
  const loginHtml = renderPage(Login)
  const registerHtml = renderPage(Register)
  assert(loginHtml.includes('Welcome back') && loginHtml.includes('Username or email'), 'Login page did not render.')
  assert(registerHtml.includes('Create an account') && registerHtml.includes('Confirm password'), 'Register page did not render.')
  console.log('LOGIN_UI_OK=True')
  console.log('REGISTER_UI_OK=True')
} finally {
  await viteSsr.close()
}

const backendStatus = run('git', ['status', '--porcelain', '--', 'backend'], projectDir).trim()
assert(backendStatus === '', `Backend changed during Phase 6.2:\n${backendStatus}`)
const migrationStatus = run('git', ['status', '--porcelain', '--', 'backend/alembic'], projectDir).trim()
assert(migrationStatus === '', `A migration changed during Phase 6.2:\n${migrationStatus}`)
console.log('BACKEND_UNCHANGED=True')
console.log('NO_NEW_MIGRATIONS=True')

let viteOutput = ''
let viteErrors = ''
const viteProcess = spawn(
  process.execPath,
  ['./node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5173', '--strictPort'],
  { cwd: frontendDir, stdio: ['ignore', 'pipe', 'pipe'] },
)
viteProcess.stdout.on('data', (chunk) => { viteOutput += chunk.toString() })
viteProcess.stderr.on('data', (chunk) => { viteErrors += chunk.toString() })

try {
  await waitForServer('http://127.0.0.1:5173/login')
  for (const route of ['/login', '/register', '/dashboard', '/estimates', '/bom', '/quotations']) {
    const response = await fetch(`http://127.0.0.1:5173${route}`)
    const body = await response.text()
    assert(response.status === 200 && body.includes('<div id="root"></div>'), `${route} was not served.`)
  }
  assert(viteProcess.exitCode === null, 'Vite exited before route validation completed.')
} finally {
  viteProcess.kill()
  await new Promise((resolve) => viteProcess.once('exit', resolve))
}
assert(!viteErrors.trim(), `Vite reported errors:\n${viteErrors}`)

let portStillOpen = false
try {
  await fetch('http://127.0.0.1:5173/', { signal: AbortSignal.timeout(500) })
  portStillOpen = true
} catch {
  // Expected after stopping the owned Vite process.
}
assert(!portStillOpen, 'Port 5173 still has a listener.')

console.log('AUTH_CONTEXT_OK=True')
console.log('TOKEN_STORAGE_OK=True')
console.log('CURRENT_USER_OK=True')
console.log('PROTECTED_ROUTE_OK=True')
console.log('AXIOS_AUTH_OK=True')
console.log('LOGOUT_OK=True')
console.log('TEMP_SERVER_CLEANUP_OK=True')
console.log('PHASE6_2_VALIDATION_OK=True')

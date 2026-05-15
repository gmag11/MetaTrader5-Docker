const API_BASE = '/api'

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  const config = {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  }

  const response = await fetch(url, config)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

export const api = {
  // Health
  getHealth: () => request('/health'),
  getStatus: () => request('/status'),

  // Accounts
  getAccounts: () => request('/accounts'),
  getAccount: (name) => request(`/accounts/${name}`),
  reconnectAccount: (name) => request(`/accounts/${name}/reconnect`, { method: 'POST' }),

  // Slaves
  getSlaves: () => request('/accounts/slaves'),
  createSlave: (data) => request('/accounts/slaves', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  // Deploy new slave (creates container + registers)
  deploySlave: (data) => request('/deploy/slave', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  updateSlave: (name, data) => request(`/accounts/slaves/${name}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  deleteSlave: (name, closePositions = false) =>
    request(`/accounts/slaves/${name}?close_positions=${closePositions}`, { method: 'DELETE' }),
  enableSlave: (name) => request(`/accounts/slaves/${name}/enable`, { method: 'POST' }),
  disableSlave: (name, closePositions = false) =>
    request(`/accounts/slaves/${name}/disable?close_positions=${closePositions}`, { method: 'POST' }),

  // Positions
  getPositions: () => request('/positions'),
  getPositionStats: () => request('/positions/stats'),
}

export default api

const KEY = 'quest_parent_token'

export function getToken() { return localStorage.getItem(KEY) }
export function setToken(t) { localStorage.setItem(KEY, t) }
export function clearToken() { localStorage.removeItem(KEY) }
export function isLoggedIn() { return !!getToken() }

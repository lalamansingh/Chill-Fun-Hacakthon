import client from './client.js'

export const authApi = {
  register: (body) => client.post('/auth/register', body).then((r) => r.data),
  login: (body) => client.post('/auth/login', body).then((r) => r.data),
  me: () => client.get('/auth/me').then((r) => r.data),
}

export const imagesApi = {
  upload: (file, onUploadProgress) => {
    const fd = new FormData()
    fd.append('file', file)
    return client.post('/images', fd, { onUploadProgress }).then((r) => r.data)
  },
  list: () => client.get('/images').then((r) => r.data),
  get: (id) => client.get(`/images/${id}`).then((r) => r.data),
  remove: (id) => client.delete(`/images/${id}`),
}

export const analysesApi = {
  create: (imageId) => client.post('/analyses', { image_id: imageId }).then((r) => r.data),
  get: (id) => client.get(`/analyses/${id}`).then((r) => r.data),
  restore: (id, body) => client.post(`/analyses/${id}/restore`, body).then((r) => r.data),
}

export const historyApi = {
  list: ({ q, verdict, page = 1, page_size = 10 } = {}) => {
    const params = { page, page_size }
    if (q) params.q = q
    if (verdict) params.verdict = verdict
    return client.get('/history', { params }).then((r) => r.data)
  },
}

export const dashboardApi = {
  stats: () => client.get('/dashboard/stats').then((r) => r.data),
}

export const healthApi = {
  get: () => client.get('/health').then((r) => r.data),
}

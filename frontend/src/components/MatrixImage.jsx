import { API_URL } from '../api.js'

export default function MatrixImage({ id }) {
  if (!id) return null
  const src = `${API_URL}/api/static/matrices/${id}.png`
  return (
    <div className="my-3 flex justify-center">
      <img src={src} alt={id} className="max-w-xs rounded-lg shadow-sm" />
    </div>
  )
}

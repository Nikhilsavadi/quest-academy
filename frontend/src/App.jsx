import { Routes, Route, Navigate } from 'react-router-dom'
import ChildEntry from './pages/ChildEntry.jsx'
import ChildHome from './pages/ChildHome.jsx'
import Quest from './pages/Quest.jsx'
import ReviewPage from './pages/ReviewPage.jsx'
import Login from './pages/Login.jsx'
import ParentDashboard from './pages/ParentDashboard.jsx'
import { isLoggedIn, getToken } from './auth.js'

function RequireParent({ children }) {
  return isLoggedIn() ? children : <Navigate to="/admin/login" replace />
}

function RequireChild({ children }) {
  return getToken() ? children : <Navigate to="/" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<ChildEntry />} />
      <Route path="/home" element={<RequireChild><ChildHome /></RequireChild>} />
      <Route path="/quest/:id" element={<RequireChild><Quest /></RequireChild>} />
      <Route path="/review/:id" element={<RequireChild><ReviewPage /></RequireChild>} />
      <Route path="/admin/login" element={<Login />} />
      <Route path="/admin/*" element={<RequireParent><ParentDashboard /></RequireParent>} />
      {/* legacy redirects */}
      <Route path="/parent/login" element={<Navigate to="/admin/login" replace />} />
      <Route path="/parent/*" element={<Navigate to="/admin" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

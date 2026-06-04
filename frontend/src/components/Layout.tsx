// frontend/src/components/Layout.tsx
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { FileText, MessageSquare, Cpu, LogOut, Brain } from 'lucide-react'
import { useAuthStore } from '../hooks/useAuth'
import { useQuery } from '@tanstack/react-query'
import { systemApi } from '../api/services'
import clsx from 'clsx'

export default function Layout() {
  const { user, logout } = useAuthStore()
  const { data: npuData } = useQuery({
    queryKey: ['npu-status'],
    queryFn: () => systemApi.npuStatus().then((r) => r.data),
    refetchInterval: 30_000,
  })

  const navItems = [
    { to: '/', icon: FileText, label: 'Documents', end: true },
    { to: '/chat/new', icon: MessageSquare, label: 'Chat' },
  ]

  return (
    <div className="flex h-screen bg-gray-50 font-sans">
      {/* Sidebar */}
      <aside className="w-60 bg-white border-r border-gray-200 flex flex-col">
        {/* Logo */}
        <div className="p-5 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Brain className="text-brand-500" size={22} />
            <span className="font-semibold text-gray-900 text-lg">NeuroLens</span>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">Document Intelligence</p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  isActive
                    ? 'bg-brand-50 text-brand-600 font-medium'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                )
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* NPU Status Badge */}
        {npuData && (
          <div className="mx-3 mb-3 p-3 rounded-lg bg-gray-50 border border-gray-100">
            <div className="flex items-center gap-2 mb-1">
              <Cpu size={13} className={npuData.npu_available ? 'text-green-500' : 'text-gray-400'} />
              <span className="text-xs font-medium text-gray-700">NPU Status</span>
            </div>
            <p className="text-xs text-gray-500 truncate">
              {npuData.active_embed_provider || 'Loading...'}
            </p>
            <div className={clsx(
              'mt-1.5 text-xs font-medium',
              npuData.npu_available ? 'text-green-600' : 'text-amber-500'
            )}>
              {npuData.vitisai_available
                ? '⚡ VitisAI (NPU)'
                : npuData.directml_available
                ? '⚡ DirectML (GPU/NPU)'
                : '🖥 CPU Mode'}
            </div>
          </div>
        )}

        {/* User + Logout */}
        <div className="p-3 border-t border-gray-100">
          <div className="flex items-center justify-between">
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{user?.name}</p>
              <p className="text-xs text-gray-400 truncate">{user?.email}</p>
            </div>
            <button
              onClick={logout}
              className="p-1.5 text-gray-400 hover:text-gray-700 rounded-md hover:bg-gray-100 transition-colors"
              title="Logout"
            >
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}

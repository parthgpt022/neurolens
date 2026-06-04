// frontend/src/pages/DashboardPage.tsx
import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Upload, FileText, Clock, CheckCircle2, XCircle, Loader2, MessageSquare, Trash2 } from 'lucide-react'
import { documentsApi, chatApi, type Document } from '../api/services'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

const STATUS_ICON = {
  pending:    <Clock size={14} className="text-amber-400" />,
  processing: <Loader2 size={14} className="text-blue-400 animate-spin" />,
  done:       <CheckCircle2 size={14} className="text-green-500" />,
  failed:     <XCircle size={14} className="text-red-400" />,
}

const STATUS_LABEL = {
  pending: 'Pending',
  processing: 'Processing…',
  done: 'Ready',
  failed: 'Failed',
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({})
  const [selectedIds, setSelectedIds] = useState<string[]>([])

  const { data: docs = [], isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentsApi.list().then((r) => r.data),
    refetchInterval: (data) =>
      data?.some((d) => d.status === 'processing' || d.status === 'pending') ? 3000 : false,
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      documentsApi.upload(file, (pct) =>
        setUploadProgress((prev) => ({ ...prev, [file.name]: pct }))
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      setUploadProgress({})
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentsApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents'] }),
  })

  const startChatMutation = useMutation({
    mutationFn: (ids: string[]) =>
      chatApi.createSession(ids, `Chat — ${ids.length} document${ids.length > 1 ? 's' : ''}`),
    onSuccess: (res) => navigate(`/chat/${res.data.id}`),
  })

  const onDrop = useCallback((files: File[]) => {
    files.forEach((f) => uploadMutation.mutate(f))
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'], 'image/*': ['.png', '.jpg', '.jpeg', '.tiff', '.webp'] },
    maxSize: 50 * 1024 * 1024,
  })

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    )
  }

  const readyDocs = docs.filter((d) => d.status === 'done')
  const selectedReady = selectedIds.filter((id) => readyDocs.some((d) => d.id === id))

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900">Document Library</h1>
        <p className="text-gray-500 mt-1 text-sm">
          Upload PDFs or images. NeuroLens extracts text using NPU-accelerated OCR and indexes them for Q&A.
        </p>
      </div>

      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={clsx(
          'border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors mb-8',
          isDragActive
            ? 'border-brand-500 bg-brand-50'
            : 'border-gray-200 hover:border-brand-300 hover:bg-gray-50'
        )}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto mb-3 text-gray-300" size={32} />
        <p className="text-sm font-medium text-gray-600">
          {isDragActive ? 'Drop files here…' : 'Drag & drop PDFs or images, or click to browse'}
        </p>
        <p className="text-xs text-gray-400 mt-1">PDF, PNG, JPEG, TIFF, WebP — up to 50 MB</p>
      </div>

      {/* Upload Progress */}
      {Object.entries(uploadProgress).map(([name, pct]) => (
        <div key={name} className="mb-3 p-3 bg-blue-50 rounded-lg">
          <div className="flex justify-between text-xs text-blue-700 mb-1">
            <span className="truncate">{name}</span>
            <span>{pct}%</span>
          </div>
          <div className="h-1.5 bg-blue-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      ))}

      {/* Chat with selected */}
      {selectedReady.length > 0 && (
        <div className="mb-4 flex items-center gap-3 p-3 bg-brand-50 border border-brand-100 rounded-lg">
          <span className="text-sm text-brand-700 font-medium">
            {selectedReady.length} document{selectedReady.length > 1 ? 's' : ''} selected
          </span>
          <button
            onClick={() => startChatMutation.mutate(selectedReady)}
            disabled={startChatMutation.isPending}
            className="ml-auto flex items-center gap-2 px-4 py-1.5 bg-brand-500 text-white rounded-lg text-sm font-medium hover:bg-brand-600 transition-colors disabled:opacity-50"
          >
            <MessageSquare size={14} />
            Start Chat
          </button>
          <button
            onClick={() => setSelectedIds([])}
            className="text-xs text-brand-400 hover:text-brand-600"
          >
            Clear
          </button>
        </div>
      )}

      {/* Document List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="animate-spin text-gray-300" size={24} />
        </div>
      ) : docs.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <FileText className="mx-auto mb-3" size={32} />
          <p className="text-sm">No documents yet. Upload one above.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {docs.map((doc) => (
            <DocumentRow
              key={doc.id}
              doc={doc}
              selected={selectedIds.includes(doc.id)}
              onToggle={() => toggleSelect(doc.id)}
              onView={() => navigate(`/documents/${doc.id}`)}
              onDelete={() => deleteMutation.mutate(doc.id)}
              onChat={() => startChatMutation.mutate([doc.id])}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function DocumentRow({
  doc, selected, onToggle, onView, onDelete, onChat,
}: {
  doc: Document
  selected: boolean
  onToggle: () => void
  onView: () => void
  onDelete: () => void
  onChat: () => void
}) {
  return (
    <div
      className={clsx(
        'flex items-center gap-4 p-4 rounded-xl border transition-colors',
        selected
          ? 'border-brand-300 bg-brand-50'
          : 'border-gray-100 bg-white hover:border-gray-200'
      )}
    >
      {/* Checkbox */}
      {doc.status === 'done' && (
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggle}
          className="rounded border-gray-300 text-brand-500 focus:ring-brand-500"
        />
      )}

      <FileText size={18} className="text-gray-300 flex-shrink-0" />

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">{doc.original_filename}</p>
        <p className="text-xs text-gray-400 mt-0.5">
          {(doc.file_size_bytes / 1024).toFixed(0)} KB
          {doc.page_count > 0 && ` · ${doc.page_count} pages`}
          {' · '}
          {formatDistanceToNow(new Date(doc.created_at), { addSuffix: true })}
        </p>
      </div>

      {/* Status */}
      <div className="flex items-center gap-1.5">
        {STATUS_ICON[doc.status]}
        <span className={clsx('text-xs', {
          'text-amber-500': doc.status === 'pending',
          'text-blue-500': doc.status === 'processing',
          'text-green-600': doc.status === 'done',
          'text-red-400': doc.status === 'failed',
        })}>
          {STATUS_LABEL[doc.status]}
        </span>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1">
        {doc.status === 'done' && (
          <>
            <button
              onClick={onView}
              className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
              title="View document"
            >
              <FileText size={14} />
            </button>
            <button
              onClick={onChat}
              className="p-1.5 text-gray-400 hover:text-brand-500 hover:bg-brand-50 rounded-md transition-colors"
              title="Chat with document"
            >
              <MessageSquare size={14} />
            </button>
          </>
        )}
        <button
          onClick={onDelete}
          className="p-1.5 text-gray-300 hover:text-red-400 hover:bg-red-50 rounded-md transition-colors"
          title="Delete"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  )
}

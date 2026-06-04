// frontend/src/pages/DocumentPage.tsx
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { ArrowLeft, MessageSquare, Loader2, Tag, FileText, Cpu } from 'lucide-react'
import { documentsApi, chatApi } from '../api/services'
import clsx from 'clsx'

const ENTITY_COLORS: Record<string, string> = {
  AMOUNT:   'bg-green-50 text-green-700 border-green-100',
  DATE:     'bg-blue-50 text-blue-700 border-blue-100',
  GSTIN:    'bg-purple-50 text-purple-700 border-purple-100',
  PAN:      'bg-amber-50 text-amber-700 border-amber-100',
  COMPANY:  'bg-pink-50 text-pink-700 border-pink-100',
  DEFAULT:  'bg-gray-50 text-gray-600 border-gray-100',
}

export default function DocumentPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: doc, isLoading } = useQuery({
    queryKey: ['document', id],
    queryFn: () => documentsApi.get(id!).then((r) => r.data),
    enabled: !!id,
  })

  const { data: entities = [] } = useQuery({
    queryKey: ['entities', id],
    queryFn: () => documentsApi.getEntities(id!).then((r) => r.data),
    enabled: !!id && doc?.status === 'done',
  })

  const startChatMutation = useMutation({
    mutationFn: () => chatApi.createSession([id!], doc?.original_filename),
    onSuccess: (res) => navigate(`/chat/${res.data.id}`),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="animate-spin text-gray-300" size={24} />
      </div>
    )
  }

  if (!doc) return null

  const meta = doc.ocr_metadata as any

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-start gap-4 mb-8">
        <button
          onClick={() => navigate('/')}
          className="p-2 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-700 transition-colors mt-0.5"
        >
          <ArrowLeft size={16} />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-semibold text-gray-900 truncate">{doc.original_filename}</h1>
          <p className="text-sm text-gray-400 mt-1">
            {doc.page_count} pages · {(doc.file_size_bytes / 1024).toFixed(0)} KB
          </p>
        </div>
        <button
          onClick={() => startChatMutation.mutate()}
          disabled={startChatMutation.isPending || doc.status !== 'done'}
          className="flex items-center gap-2 px-4 py-2 bg-brand-500 text-white rounded-xl text-sm font-medium hover:bg-brand-600 transition-colors disabled:opacity-50"
        >
          <MessageSquare size={15} />
          Chat with this doc
        </button>
      </div>

      {/* Processing stats */}
      {meta && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {[
            { label: 'Pages', value: meta.page_count },
            { label: 'Text chunks', value: meta.chunk_count },
            { label: 'OCR latency', value: `${meta.ocr_latency_ms}ms` },
            { label: 'Embed provider', value: meta.embed_provider?.replace('ExecutionProvider', '') || 'CPU' },
          ].map(({ label, value }) => (
            <div key={label} className="bg-white border border-gray-100 rounded-xl p-4">
              <p className="text-xs text-gray-400">{label}</p>
              <p className="text-sm font-semibold text-gray-900 mt-1">{value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Extracted text */}
        <div className="lg:col-span-2">
          <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-50 flex items-center gap-2">
              <FileText size={15} className="text-gray-400" />
              <h2 className="text-sm font-medium text-gray-900">Extracted Text</h2>
            </div>
            <div className="p-5 max-h-96 overflow-y-auto">
              <pre className="text-xs text-gray-600 whitespace-pre-wrap font-mono leading-relaxed">
                {doc.extracted_text || 'No text extracted yet.'}
              </pre>
            </div>
          </div>
        </div>

        {/* Entities */}
        <div>
          <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-50 flex items-center gap-2">
              <Tag size={15} className="text-gray-400" />
              <h2 className="text-sm font-medium text-gray-900">
                Entities ({entities.length})
              </h2>
            </div>
            <div className="p-4 max-h-96 overflow-y-auto space-y-2">
              {entities.length === 0 ? (
                <p className="text-xs text-gray-400 text-center py-6">
                  No entities extracted yet.
                  <br />
                  <span className="text-gray-300">NER model coming in Phase 4.</span>
                </p>
              ) : (
                entities.map((e) => (
                  <div
                    key={e.id}
                    className={clsx(
                      'px-3 py-2 rounded-lg border text-xs',
                      ENTITY_COLORS[e.entity_type] || ENTITY_COLORS.DEFAULT
                    )}
                  >
                    <div className="font-medium">{e.value}</div>
                    <div className="opacity-60 mt-0.5">
                      {e.entity_type} · p.{e.page_number} · {(e.confidence * 100).toFixed(0)}%
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

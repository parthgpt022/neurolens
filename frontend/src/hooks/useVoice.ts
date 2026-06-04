// frontend/src/hooks/useVoice.ts
// Records audio from the microphone and sends it to the backend STT endpoint.
// Returns the transcribed text, which the chat UI uses as the message input.

import { useState, useRef, useCallback } from 'react'
import { apiClient } from '../api/client'

type VoiceState = 'idle' | 'recording' | 'transcribing' | 'error'

interface UseVoiceReturn {
  state: VoiceState
  transcript: string
  startRecording: () => Promise<void>
  stopRecording: () => void
  clearTranscript: () => void
  error: string | null
}

export function useVoice(): UseVoiceReturn {
  const [state, setState] = useState<VoiceState>('idle')
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState<string | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const startRecording = useCallback(async () => {
    setError(null)
    setTranscript('')

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      mediaRecorderRef.current = recorder
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = async () => {
        setState('transcribing')
        stream.getTracks().forEach((t) => t.stop())

        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        const form = new FormData()
        form.append('audio', blob, 'recording.webm')

        try {
          const { data } = await apiClient.post<{ text: string }>(
            '/speech/transcribe',
            form,
            { headers: { 'Content-Type': 'multipart/form-data' } }
          )
          setTranscript(data.text)
          setState('idle')
        } catch (err) {
          setError('Transcription failed. Is the speech service running?')
          setState('error')
        }
      }

      recorder.start(250) // Collect data every 250ms
      setState('recording')
    } catch (err) {
      setError('Microphone access denied or not available')
      setState('error')
    }
  }, [])

  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop()
  }, [])

  const clearTranscript = useCallback(() => {
    setTranscript('')
    setState('idle')
    setError(null)
  }, [])

  return { state, transcript, startRecording, stopRecording, clearTranscript, error }
}

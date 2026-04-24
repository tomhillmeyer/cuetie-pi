import { useState, useCallback, useRef } from 'react'
import { createFile } from 'mp4box'

export function useTranscode() {
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState('idle')
  const [message, setMessage] = useState('')
  const abortRef = useRef(false)

  const transcode = useCallback(async (file) => {
    abortRef.current = false

    if (!('VideoEncoder' in window)) {
      setStatus('unsupported')
      setMessage('Video transcoding requires Chrome or Edge')
      throw new Error('WebCodecs not supported')
    }

    setStatus('checking')
    setMessage('Preparing video...')
    setProgress(0)

    try {
      const mp4boxFile = createFile()
      const arrayBuffer = await file.arrayBuffer()
      arrayBuffer.fileStart = 0
      mp4boxFile.appendBuffer(arrayBuffer)

      const info = await new Promise((resolve) => {
        mp4boxFile.onReady = (info) => resolve(info)
      })

      const videoTrack = info.videoTracks[0]
      if (!videoTrack) throw new Error('No video track found')

      const height = videoTrack.video.height
      let bitrate = height >= 2160 ? 8_000_000 :
                    height >= 1080 ? 4_000_000 :
                    height >= 720 ? 2_500_000 : 1_500_000

      setStatus('transcoding')
      setMessage(`Transcoding ${videoTrack.video.width}x${height}...`)

      const outputChunks = []
      let processedSamples = 0
      const totalSamples = videoTrack.nb_samples

      let encoder = null
      let decoder = null

      const onEncoderOutput = (chunk, metadata) => {
        const chunkData = new Uint8Array(chunk.byteLength)
        chunk.copyTo(chunkData)
        outputChunks.push(chunkData)

        const progress = Math.round((processedSamples / totalSamples) * 100)
        setProgress(Math.min(progress, 99))
      }

      encoder = new VideoEncoder({
        output: onEncoderOutput,
        error: (error) => { throw error }
      })

      await encoder.configure({
        codec: 'avc1.640028',
        width: videoTrack.video.width,
        height: videoTrack.video.height,
        bitrate: bitrate,
        framerate: videoTrack.frame_rate || 30
      })

      decoder = new VideoDecoder({
        output: (frame) => {
          if (abortRef.current) {
            frame.close()
            return
          }
          encoder.encode(frame, { keyFrame: frame.isKeyFrame })
          frame.close()
        },
        error: (error) => { throw error }
      })

      await decoder.configure({
        codec: videoTrack.codec,
        codedWidth: videoTrack.video.width,
        codedHeight: videoTrack.video.height
      })

      mp4boxFile.setExtractionOptions(videoTrack.id, null, { nbSamples: 50 })
      mp4boxFile.start()

      await new Promise((resolve, reject) => {
        mp4boxFile.onSamples = (trackId, ref, samples) => {
          if (abortRef.current) {
            resolve()
            return
          }
          for (const sample of samples) {
            if (abortRef.current) break
            decoder.decode(new EncodedVideoChunk({
              type: sample.is_sync ? 'key' : 'delta',
              timestamp: sample.cts * 1000000 / videoTrack.timescale,
              duration: sample.duration * 1000000 / videoTrack.timescale,
              data: sample.data
            }))
            processedSamples++
          }
          setProgress(Math.round((processedSamples / totalSamples) * 100))
        }

        setTimeout(() => resolve(), 100)
      })

      if (abortRef.current) {
        if (encoder) encoder.close()
        if (decoder) decoder.close()
        return null
      }

      await decoder.flush()
      decoder.close()
      await encoder.flush()
      encoder.close()

      if (abortRef.current) return null

      setProgress(100)
      setStatus('complete')
      setMessage('Transcoding complete!')

      return new Blob(outputChunks, { type: 'video/mp4' })

    } catch (error) {
      if (abortRef.current) {
        setStatus('idle')
        return null
      }
      setStatus('error')
      setMessage(error.message || 'Transcoding failed')
      throw error
    }
  }, [])

  const abort = useCallback(() => {
    abortRef.current = true
    setStatus('idle')
    setMessage('')
    setProgress(0)
  }, [])

  return { transcode, abort, progress, status, message }
}
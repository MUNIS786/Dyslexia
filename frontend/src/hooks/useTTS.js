import { useState, useCallback, useRef, useEffect } from 'react'

export function useTTS() {
  const [speaking, setSpeaking] = useState(false)
  const [wordIndex, setWordIndex] = useState(-1)
  const [words, setWords] = useState([])
  const utterRef = useRef(null)
  const speedRef = useRef(1)

  const stop = useCallback(() => {
    window.speechSynthesis?.cancel()
    setSpeaking(false)
    setWordIndex(-1)
  }, [])

  useEffect(() => {
    return () => window.speechSynthesis?.cancel()
  }, [])

  const speak = useCallback((text, speed = 1) => {
    if (!window.speechSynthesis) return
    stop()
    const wordList = text.split(/\s+/).filter(Boolean)
    setWords(wordList)
    speedRef.current = speed

    const utter = new SpeechSynthesisUtterance(text)
    utter.rate = speed
    utter.lang = 'en-IN'
    utterRef.current = utter

    let idx = 0
    utter.onboundary = (e) => {
      if (e.name === 'word') {
        setWordIndex(idx)
        idx++
      }
    }
    utter.onend = () => {
      setSpeaking(false)
      setWordIndex(-1)
    }
    utter.onerror = () => {
      setSpeaking(false)
      setWordIndex(-1)
    }

    setSpeaking(true)
    window.speechSynthesis.speak(utter)
  }, [stop])

  const toggle = useCallback((text, speed) => {
    if (speaking) {
      stop()
    } else {
      speak(text, speed)
    }
  }, [speaking, speak, stop])

  return { speak, stop, toggle, speaking, wordIndex, words }
}

/**
 * frontend/src/components/accessibility/VisualTintOverlay.jsx
 *
 * Fullscreen Color Tint Overlay for Visual Stress & Glare Reduction (Irlen Syndrome accommodations).
 * Softens harsh white background contrast for sensitive eyes.
 */
import React from 'react'
import { useAccessibility } from '../../context/AccessibilityContext'

const TINT_COLORS = {
  peach: 'rgba(255, 218, 193, 0.18)',
  mint: 'rgba(212, 237, 218, 0.18)',
  sky: 'rgba(207, 234, 255, 0.18)',
  butter: 'rgba(255, 243, 176, 0.18)',
}

export default function VisualTintOverlay() {
  const { preferences } = useAccessibility()
  const { tintOverlay = 'none' } = preferences

  if (!tintOverlay || tintOverlay === 'none' || !TINT_COLORS[tintOverlay]) {
    return null
  }

  return (
    <div
      className="fixed inset-0 pointer-events-none z-30 transition-colors duration-300"
      style={{
        backgroundColor: TINT_COLORS[tintOverlay],
        mixBlendMode: 'multiply',
      }}
      aria-hidden="true"
    />
  )
}

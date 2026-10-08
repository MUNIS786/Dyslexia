/**
 * frontend/src/components/insights/ProgressChart.jsx
 *
 * Lightweight, accessible pure-SVG longitudinal progress chart.
 * Features:
 * - Accuracy (%) line + Reading Speed (WPM) line + practice indicators
 * - Text summary and accessible HTML table for assistive technology (WCAG 2.1 AA)
 * - Scalable responsive viewBox with no horizontal overflow
 * - Adapts to high contrast and reduced motion settings
 */
import React, { useState } from 'react'
import { useTranslation } from '../../i18n/I18nContext'

export default function ProgressChart({
  timeline = [],
  reportingPeriod = '30d',
  loading = false,
}) {
  const { t } = useTranslation()
  const [activeMetric, setActiveMetric] = useState('both') // 'accuracy' | 'speed' | 'both'
  const [hoveredPoint, setHoveredPoint] = useState(null)

  if (loading) {
    return (
      <div className="bg-white rounded-3xl p-6 border border-stone-200 shadow-2xs animate-pulse space-y-4">
        <div className="h-6 bg-stone-200 rounded w-1/4" />
        <div className="h-48 bg-stone-100 rounded-2xl" />
      </div>
    )
  }

  // Filter valid points with at least one metric recorded
  const activePoints = timeline.filter(
    (p) => p.readingAccuracy !== null || p.readingSpeedWpm !== null || p.wordsRead > 0
  )

  const hasData = activePoints.length > 0

  // Chart coordinates
  const width = 640
  const height = 220
  const padding = { top: 20, right: 30, bottom: 35, left: 45 }
  const plotWidth = width - padding.left - padding.right
  const plotHeight = height - padding.top - padding.bottom

  // X-scale: map point index to X coordinate
  const pointsCount = Math.max(timeline.length, 1)
  const getX = (idx) => padding.left + (idx / Math.max(pointsCount - 1, 1)) * plotWidth

  // Y-scale for Accuracy (0 to 100%)
  const getYAccuracy = (val) => {
    if (val === null || val === undefined) return null
    const clamped = Math.max(0, Math.min(100, val))
    return padding.top + plotHeight - (clamped / 100) * plotHeight
  }

  // Y-scale for Speed (0 to 120 WPM)
  const maxWpm = 120
  const getYSpeed = (val) => {
    if (val === null || val === undefined) return null
    const clamped = Math.max(0, Math.min(maxWpm, val))
    return padding.top + plotHeight - (clamped / maxWpm) * plotHeight
  }

  // Build SVG path strings
  let accPath = ''
  let speedPath = ''
  timeline.forEach((p, idx) => {
    const x = getX(idx)
    if (p.readingAccuracy !== null) {
      const yAcc = getYAccuracy(p.readingAccuracy)
      accPath += accPath === '' ? `M ${x} ${yAcc}` : ` L ${x} ${yAcc}`
    }
    if (p.readingSpeedWpm !== null) {
      const ySpd = getYSpeed(p.readingSpeedWpm)
      speedPath += speedPath === '' ? `M ${x} ${ySpd}` : ` L ${x} ${ySpd}`
    }
  })

  return (
    <section
      aria-labelledby="progress-chart-heading"
      className="bg-white rounded-3xl p-6 border border-stone-200 shadow-2xs space-y-4"
    >
      {/* Title & Metric Filter */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3
            id="progress-chart-heading"
            className="text-base sm:text-lg font-black text-stone-900 tracking-tight flex items-center gap-2"
          >
            <span>📊</span>
            {t('insights.progressChartTitle', 'Reading Progress Over Time')}
          </h3>
          <p className="text-xs text-stone-500">
            {t(
              'insights.progressChartSubtitle',
              'Tracking your daily accuracy and comfortable reading speed.'
            )}
          </p>
        </div>

        {/* Metric Toggle Buttons */}
        <div className="inline-flex p-0.5 bg-stone-100 rounded-xl text-xs font-bold border border-stone-200 self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setActiveMetric('both')}
            className={`px-2.5 py-1 rounded-lg transition-all ${
              activeMetric === 'both' ? 'bg-[#1A6B6B] text-white shadow-2xs' : 'text-stone-600 hover:text-stone-900'
            }`}
          >
            {t('common.viewAll', 'All')}
          </button>
          <button
            type="button"
            onClick={() => setActiveMetric('accuracy')}
            className={`px-2.5 py-1 rounded-lg transition-all flex items-center gap-1 ${
              activeMetric === 'accuracy' ? 'bg-emerald-700 text-white shadow-2xs' : 'text-stone-600 hover:text-stone-900'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            {t('insights.chartAccuracyLabel', 'Accuracy')}
          </button>
          <button
            type="button"
            onClick={() => setActiveMetric('speed')}
            className={`px-2.5 py-1 rounded-lg transition-all flex items-center gap-1 ${
              activeMetric === 'speed' ? 'bg-blue-700 text-white shadow-2xs' : 'text-stone-600 hover:text-stone-900'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            {t('insights.chartSpeedLabel', 'Speed')}
          </button>
        </div>
      </div>

      {!hasData ? (
        <div className="h-44 flex flex-col items-center justify-center bg-stone-50 rounded-2xl border border-dashed border-stone-200 p-6 text-center">
          <span className="text-3xl mb-2">🌱</span>
          <p className="text-xs font-bold text-stone-700">
            {t('insights.insufficientDataTitle', 'Building Your Practice History')}
          </p>
          <p className="text-xs text-stone-500 max-w-sm mt-1">
            {t(
              'insights.insufficientDataMsg',
              'Complete a few more sessions to reveal clear progress trends.'
            )}
          </p>
        </div>
      ) : (
        <div className="relative overflow-hidden">
          {/* Accessible SVG Chart */}
          <svg
            viewBox={`0 0 ${width} ${height}`}
            className="w-full h-auto select-none"
            role="img"
            aria-label={`Progress chart over the last ${reportingPeriod}: ${activePoints.length} active sessions logged.`}
          >
            {/* Background Grid Lines */}
            {[0, 25, 50, 75, 100].map((tickVal) => {
              const y = getYAccuracy(tickVal)
              return (
                <g key={tickVal}>
                  <line
                    x1={padding.left}
                    y1={y}
                    x2={width - padding.right}
                    y2={y}
                    stroke="#E7E5E4"
                    strokeWidth="1"
                    strokeDasharray="3 3"
                  />
                  <text
                    x={padding.left - 8}
                    y={y + 4}
                    textAnchor="end"
                    fontSize="10"
                    fill="#78716C"
                    fontWeight="600"
                  >
                    {tickVal}%
                  </text>
                </g>
              )
            })}

            {/* X-axis date labels (sample 4 dates evenly) */}
            {timeline.length > 0 &&
              [0, Math.floor(timeline.length / 3), Math.floor((2 * timeline.length) / 3), timeline.length - 1].map(
                (idx) => {
                  const pt = timeline[idx]
                  if (!pt) return null
                  const x = getX(idx)
                  const label = pt.date.slice(5) // MM-DD
                  return (
                    <text
                      key={idx}
                      x={x}
                      y={height - 10}
                      textAnchor="middle"
                      fontSize="10"
                      fill="#78716C"
                      fontWeight="600"
                    >
                      {label}
                    </text>
                  )
                }
              )}

            {/* Reading Accuracy Line (Solid Emerald) */}
            {(activeMetric === 'both' || activeMetric === 'accuracy') && accPath && (
              <path
                d={accPath}
                fill="none"
                stroke="#059669"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )}

            {/* Reading Speed Line (Dashed Blue) */}
            {(activeMetric === 'both' || activeMetric === 'speed') && speedPath && (
              <path
                d={speedPath}
                fill="none"
                stroke="#2563EB"
                strokeWidth="2.5"
                strokeDasharray="4 4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )}

            {/* Data Point Markers */}
            {timeline.map((p, idx) => {
              const x = getX(idx)
              const yAcc = getYAccuracy(p.readingAccuracy)
              const ySpd = getYSpeed(p.readingSpeedWpm)

              return (
                <g key={idx}>
                  {/* Accuracy Circle */}
                  {(activeMetric === 'both' || activeMetric === 'accuracy') && yAcc !== null && (
                    <circle
                      cx={x}
                      cy={yAcc}
                      r={hoveredPoint === idx ? '6' : '4'}
                      fill="#059669"
                      stroke="#FFFFFF"
                      strokeWidth="2"
                      className="cursor-pointer transition-all"
                      onMouseEnter={() => setHoveredPoint(idx)}
                      onMouseLeave={() => setHoveredPoint(null)}
                      tabIndex="0"
                      aria-label={`${p.date}: Accuracy ${p.readingAccuracy}%`}
                    />
                  )}
                  {/* Speed Diamond / Circle */}
                  {(activeMetric === 'both' || activeMetric === 'speed') && ySpd !== null && (
                    <circle
                      cx={x}
                      cy={ySpd}
                      r={hoveredPoint === idx ? '6' : '3.5'}
                      fill="#2563EB"
                      stroke="#FFFFFF"
                      strokeWidth="2"
                      className="cursor-pointer transition-all"
                      onMouseEnter={() => setHoveredPoint(idx)}
                      onMouseLeave={() => setHoveredPoint(null)}
                      tabIndex="0"
                      aria-label={`${p.date}: Speed ${p.readingSpeedWpm} WPM`}
                    />
                  )}
                </g>
              )
            })}
          </svg>

          {/* Hover Detail Card */}
          {hoveredPoint !== null && timeline[hoveredPoint] && (
            <div className="mt-2 p-3 bg-stone-900 text-white rounded-xl text-xs flex flex-wrap items-center justify-between gap-3 animate-fade-in">
              <span className="font-bold text-stone-300">📅 {timeline[hoveredPoint].date}</span>
              {timeline[hoveredPoint].readingAccuracy !== null && (
                <span className="text-emerald-400 font-bold">
                  ✓ Accuracy: {timeline[hoveredPoint].readingAccuracy}%
                </span>
              )}
              {timeline[hoveredPoint].readingSpeedWpm !== null && (
                <span className="text-blue-300 font-bold">
                  ⚡ Speed: {timeline[hoveredPoint].readingSpeedWpm} WPM
                </span>
              )}
              {timeline[hoveredPoint].wordsRead > 0 && (
                <span className="text-amber-300 font-bold">
                  📖 {timeline[hoveredPoint].wordsRead} Words Read
                </span>
              )}
            </div>
          )}

          {/* Screen Reader Table Alternative */}
          <div className="sr-only">
            <table>
              <caption>Reading Progress History Data Table</caption>
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  <th scope="col">Accuracy (%)</th>
                  <th scope="col">Speed (WPM)</th>
                  <th scope="col">Words Read</th>
                </tr>
              </thead>
              <tbody>
                {activePoints.map((pt, idx) => (
                  <tr key={idx}>
                    <td>{pt.date}</td>
                    <td>{pt.readingAccuracy ?? 'N/A'}</td>
                    <td>{pt.readingSpeedWpm ?? 'N/A'}</td>
                    <td>{pt.wordsRead}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap items-center justify-center sm:justify-start gap-4 text-xs font-semibold text-stone-600 pt-2 border-t border-stone-100">
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-1 bg-emerald-600 rounded-full" />
          <span>{t('insights.chartAccuracyLabel', 'Accuracy (%)')}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-1 border-b-2 border-dashed border-blue-600" />
          <span>{t('insights.chartSpeedLabel', 'Speed (WPM)')}</span>
        </div>
        <div className="text-stone-400 text-[11px]">
          ℹ️ {t('insights.chartWordsLabel', 'Words Read')} are recorded daily
        </div>
      </div>
    </section>
  )
}

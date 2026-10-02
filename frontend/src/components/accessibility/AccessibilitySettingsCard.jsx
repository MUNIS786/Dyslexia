/**
 * frontend/src/components/accessibility/AccessibilitySettingsCard.jsx
 *
 * Full-featured, child-friendly Reading & Accessibility Settings Panel.
 * Includes typography ergonomics, line and word spacing, narrow line lengths,
 * reading ruler customization, visual stress tints, high contrast, reduced motion,
 * live English & Devanagari bilingual previews, and educational non-clinical safeguards.
 */
import React, { useState } from 'react'
import { useAccessibility } from '../../context/AccessibilityContext'
import { useTranslation } from '../../i18n/I18nContext'
import { Card, Button, Select } from '../ui'
import toast from 'react-hot-toast'

const FONT_OPTIONS = [
  { value: 'Lexend, sans-serif', label: 'Lexend (Clean & Accessible)' },
  { value: 'OpenDyslexic, sans-serif', label: 'OpenDyslexic (Weighted Bottoms)' },
  { value: 'Comic Neue, cursive', label: 'Comic Neue (Friendly Letterforms)' },
  { value: 'System, sans-serif', label: 'System Default' },
]

const BG_THEMES = [
  { bg: '#FFF8F0', text: '#1A2A2A', label: 'Warm Cream (Recommended)' },
  { bg: '#FFFFFF', text: '#1A2A2A', label: 'Crisp White' },
  { bg: '#FFFDE0', text: '#1A2A2A', label: 'Soft Yellow' },
  { bg: '#E8F4F8', text: '#1A2060', label: 'Calm Blue' },
  { bg: '#EBF5EB', text: '#1A3320', label: 'Gentle Mint' },
]

export default function AccessibilitySettingsCard({ onSaveComplete }) {
  const { preferences, updateAllPreferences, resetDefaults, saving } = useAccessibility()
  const { t, locale } = useTranslation()

  // Local draft state for immediate live preview
  const [draft, setDraft] = useState({ ...preferences })
  const [previewLanguage, setPreviewLanguage] = useState(locale === 'mr' ? 'mr' : locale === 'hi' ? 'hi' : 'en')

  const setField = (key, val) => {
    setDraft((prev) => {
      const next = { ...prev, [key]: val }
      return next
    })
  }

  const handleApplyAndSave = async () => {
    try {
      await updateAllPreferences(draft)
      toast.success(t('accessibility.saveSuccess', '✅ Reading settings saved!'))
      if (onSaveComplete) onSaveComplete()
    } catch {
      toast.error(t('accessibility.saveError', 'Could not save settings to server.'))
    }
  }

  const handleReset = async () => {
    if (confirm(t('accessibility.confirmReset', 'Reset all reading settings back to defaults?'))) {
      await resetDefaults()
      toast.success(t('accessibility.resetSuccess', 'Settings restored to defaults.'))
      setDraft({ ...preferences })
    }
  }

  return (
    <div className="space-y-6">
      {/* Educational Non-Clinical Safeguard Banner */}
      <div className="bg-teal-50 border border-teal-200 rounded-3xl p-4 sm:p-5 flex items-start gap-3 shadow-2xs">
        <span className="text-2xl mt-0.5" aria-hidden="true">💡</span>
        <div className="text-xs sm:text-sm text-teal-950 leading-relaxed">
          <strong className="block font-extrabold text-teal-900 mb-0.5">
            {t('accessibility.educationalBannerTitle', 'Personalized Reading Comfort')}
          </strong>
          {t(
            'accessibility.educationalBannerBody',
            'These adjustments are designed to help you read comfortably, reduce visual fatigue, and find your ideal pace. They are personal reading preferences, not medical prescriptions.'
          )}
        </div>
      </div>

      {/* Live Reading Preview Card */}
      <Card className="border-2 border-teal-600 bg-white shadow-sm overflow-hidden">
        <div className="flex items-center justify-between pb-3 border-b border-stone-200">
          <span className="text-xs font-extrabold text-teal-800 uppercase tracking-wider flex items-center gap-1.5">
            <span>👁️</span>
            <span>{t('accessibility.livePreview', 'Live Reading Preview')}</span>
          </span>

          {/* Bilingual Preview Switcher */}
          <div className="flex items-center gap-1 bg-stone-100 p-1 rounded-xl text-xs font-bold">
            <button
              type="button"
              onClick={() => setPreviewLanguage('en')}
              className={`px-2.5 py-1 rounded-lg transition-all ${
                previewLanguage === 'en' ? 'bg-white text-teal-900 shadow-2xs' : 'text-stone-600'
              }`}
            >
              English
            </button>
            <button
              type="button"
              onClick={() => setPreviewLanguage('mr')}
              className={`px-2.5 py-1 rounded-lg transition-all ${
                previewLanguage === 'mr' ? 'bg-white text-teal-900 shadow-2xs' : 'text-stone-600'
              }`}
            >
              मराठी
            </button>
            <button
              type="button"
              onClick={() => setPreviewLanguage('hi')}
              className={`px-2.5 py-1 rounded-lg transition-all ${
                previewLanguage === 'hi' ? 'bg-white text-teal-900 shadow-2xs' : 'text-stone-600'
              }`}
            >
              हिन्दी
            </button>
          </div>
        </div>

        {/* Preview Container */}
        <div className="pt-4 flex justify-center">
          <div
            className={`w-full p-6 rounded-2xl border transition-all ${
              draft.contentWidth === 'narrow' ? 'max-w-xl' : draft.contentWidth === 'compact' ? 'max-w-2xl' : 'max-w-3xl'
            }`}
            style={{
              backgroundColor: draft.highContrast ? '#FFFFFF' : draft.bgColor,
              color: draft.highContrast ? '#000000' : draft.textColor,
              fontFamily: draft.font,
              fontSize: `${draft.fontSize}px`,
              lineHeight: draft.lineSpacing,
              letterSpacing: `${draft.letterSpacing}em`,
              wordSpacing: `${draft.wordSpacing}em`,
              borderColor: draft.highContrast ? '#000000' : '#E5E0D8',
            }}
          >
            {previewLanguage === 'en' ? (
              <p>
                Reading is a superpower and every story is an adventure. With the right letter size and spacing, words become friendly friends that unlock new ideas and imagination!
                {draft.highlightWords && (
                  <span className="bg-amber-300/80 rounded px-1 font-semibold ml-1">
                    highlighted word
                  </span>
                )}
              </p>
            ) : previewLanguage === 'mr' ? (
              <p>
                वाचन ही एक महाशक्ती आहे आणि प्रत्येक गोष्ट एक अद्भुत अनुभव आहे. योग्य फॉन्ट आणि ओळींमधील जागेमुळे वाचन अधिक सोपे आणि आनंददायी होते!
                {draft.highlightWords && (
                  <span className="bg-amber-300/80 rounded px-1 font-semibold ml-1">
                    महत्त्वाचा शब्द
                  </span>
                )}
              </p>
            ) : (
              <p>
                पढ़ना एक महाशक्ति है और हर कहानी एक नया सफर है। सही अक्षरों और शब्दों के बीच उचित दूरी से पढ़ना बहुत आसान और मजेदार हो जाता है!
                {draft.highlightWords && (
                  <span className="bg-amber-300/80 rounded px-1 font-semibold ml-1">
                    महत्वपूर्ण शब्द
                  </span>
                )}
              </p>
            )}
          </div>
        </div>
      </Card>

      {/* Typography & Sizing */}
      <Card>
        <h2 className="text-base font-bold text-stone-900 mb-4 flex items-center gap-2">
          <span>🔤</span>
          <span>{t('accessibility.typographyTitle', 'Text Style & Sizing')}</span>
        </h2>

        <div className="space-y-5">
          {/* Font Family */}
          <div>
            <Select
              label={t('accessibility.fontFamily', 'Font Style')}
              value={draft.font}
              onChange={(e) => setField('font', e.target.value)}
              options={FONT_OPTIONS}
            />
          </div>

          {/* Font Size Slider with Preset Buttons */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-bold text-stone-700">
                {t('accessibility.fontSize', 'Text Size')}: <span className="font-mono text-teal-800">{draft.fontSize}px</span>
              </label>
              <div className="flex items-center gap-1.5">
                {[
                  { label: 'Small', size: 16 },
                  { label: 'Medium', size: 18 },
                  { label: 'Large', size: 22 },
                  { label: 'Extra', size: 26 },
                ].map((preset) => (
                  <button
                    key={preset.label}
                    type="button"
                    onClick={() => setField('fontSize', preset.size)}
                    className={`px-2 py-0.5 rounded-lg text-[11px] font-bold transition-all ${
                      draft.fontSize === preset.size
                        ? 'bg-teal-700 text-white shadow-2xs'
                        : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
                    }`}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>
            <input
              type="range"
              min={14}
              max={32}
              step={1}
              value={draft.fontSize}
              onChange={(e) => setField('fontSize', parseInt(e.target.value))}
              className="w-full accent-teal-700 cursor-pointer"
            />
          </div>

          {/* Line Spacing Slider */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-bold text-stone-700">
                {t('accessibility.lineSpacing', 'Line Spacing')}: <span className="font-mono text-teal-800">{draft.lineSpacing}x</span>
              </label>
              <div className="flex items-center gap-1.5">
                {[
                  { label: 'Normal', val: 1.6 },
                  { label: 'Relaxed', val: 2.0 },
                  { label: 'Spacious', val: 2.5 },
                ].map((p) => (
                  <button
                    key={p.label}
                    type="button"
                    onClick={() => setField('lineSpacing', p.val)}
                    className={`px-2 py-0.5 rounded-lg text-[11px] font-bold transition-all ${
                      draft.lineSpacing === p.val
                        ? 'bg-teal-700 text-white shadow-2xs'
                        : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
            <input
              type="range"
              min={1.4}
              max={3.0}
              step={0.1}
              value={draft.lineSpacing}
              onChange={(e) => setField('lineSpacing', parseFloat(e.target.value))}
              className="w-full accent-teal-700 cursor-pointer"
            />
          </div>

          {/* Letter & Word Spacing Sliders */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-bold text-stone-700 block mb-1">
                {t('accessibility.letterSpacing', 'Letter Spacing')}: <span className="font-mono text-teal-800">{draft.letterSpacing}em</span>
              </label>
              <input
                type="range"
                min={0.0}
                max={0.25}
                step={0.02}
                value={draft.letterSpacing}
                onChange={(e) => setField('letterSpacing', parseFloat(e.target.value))}
                className="w-full accent-teal-700 cursor-pointer"
              />
            </div>

            <div>
              <label className="text-xs font-bold text-stone-700 block mb-1">
                {t('accessibility.wordSpacing', 'Word Spacing')}: <span className="font-mono text-teal-800">{draft.wordSpacing}em</span>
              </label>
              <input
                type="range"
                min={0.0}
                max={0.3}
                step={0.02}
                value={draft.wordSpacing}
                onChange={(e) => setField('wordSpacing', parseFloat(e.target.value))}
                className="w-full accent-teal-700 cursor-pointer"
              />
            </div>
          </div>

          {/* Reading Width Selector */}
          <div>
            <label className="text-xs font-bold text-stone-700 block mb-1.5">
              {t('accessibility.readingWidth', 'Reading Column Width')}
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setField('contentWidth', 'standard')}
                className={`p-3 rounded-2xl border text-left transition-all ${
                  draft.contentWidth === 'standard'
                    ? 'border-teal-600 bg-teal-50 ring-2 ring-teal-600 shadow-2xs'
                    : 'border-stone-200 hover:bg-stone-50'
                }`}
              >
                <p className="text-xs font-bold text-stone-900">
                  {t('accessibility.widthStandard', 'Standard Width')}
                </p>
                <p className="text-[11px] text-stone-500">
                  {t('accessibility.widthStandardHelp', 'Comfortable full view for larger screens')}
                </p>
              </button>

              <button
                type="button"
                onClick={() => setField('contentWidth', 'narrow')}
                className={`p-3 rounded-2xl border text-left transition-all ${
                  draft.contentWidth === 'narrow'
                    ? 'border-teal-600 bg-teal-50 ring-2 ring-teal-600 shadow-2xs'
                    : 'border-stone-200 hover:bg-stone-50'
                }`}
              >
                <p className="text-xs font-bold text-stone-900">
                  {t('accessibility.widthNarrow', 'Narrow Focus (~65ch)')}
                </p>
                <p className="text-[11px] text-stone-500">
                  {t('accessibility.widthNarrowHelp', 'Shorter lines prevent losing your place')}
                </p>
              </button>
            </div>
          </div>
        </div>
      </Card>

      {/* Focus & Visual Support Tools */}
      <Card>
        <h2 className="text-base font-bold text-stone-900 mb-4 flex items-center gap-2">
          <span>📏</span>
          <span>{t('accessibility.focusToolsTitle', 'Reading Focus & Visual Guides')}</span>
        </h2>

        <div className="space-y-5">
          {/* Reading Ruler Toggle */}
          <div className="flex items-center justify-between p-3.5 bg-stone-50 rounded-2xl border border-stone-200">
            <div>
              <p className="text-xs font-bold text-stone-900">
                {t('accessibility.readingRuler', 'Reading Ruler Focus Line')}
              </p>
              <p className="text-[11px] text-stone-500">
                {t('accessibility.readingRulerDetails', 'A movable focus window that dims surrounding text')}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setField('readingRuler', !draft.readingRuler)}
              className={`w-14 h-7 rounded-full transition-colors relative cursor-pointer ${
                draft.readingRuler ? 'bg-amber-500' : 'bg-stone-300'
              }`}
              role="switch"
              aria-checked={draft.readingRuler}
            >
              <div
                className={`w-5 h-5 bg-white rounded-full absolute top-1 transition-all ${
                  draft.readingRuler ? 'left-8' : 'left-1'
                }`}
              />
            </button>
          </div>

          {/* Reading Ruler Customization (when active) */}
          {draft.readingRuler && (
            <div className="p-4 bg-amber-50/70 border border-amber-200 rounded-2xl space-y-4">
              <div>
                <label className="text-xs font-bold text-amber-950 block mb-1">
                  {t('accessibility.rulerHeight', 'Ruler Window Height')}: {draft.rulerSize}px
                </label>
                <input
                  type="range"
                  min={30}
                  max={140}
                  step={10}
                  value={draft.rulerSize}
                  onChange={(e) => setField('rulerSize', parseInt(e.target.value))}
                  className="w-full accent-amber-600 cursor-pointer"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-amber-950 block mb-1.5">
                  {t('accessibility.rulerColor', 'Ruler Tint Color')}
                </label>
                <div className="flex gap-2">
                  {['amber', 'cyan', 'yellow', 'gray'].map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setField('rulerColor', c)}
                      className={`px-3 py-1 rounded-xl text-xs font-bold capitalize border transition-all ${
                        draft.rulerColor === c
                          ? 'border-amber-600 bg-white ring-2 ring-amber-500 shadow-2xs font-extrabold'
                          : 'border-stone-200 bg-white/70 hover:bg-white'
                      }`}
                    >
                      {c}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Visual Stress Color Tint Overlay */}
          <div>
            <label className="text-xs font-bold text-stone-700 block mb-1">
              {t('accessibility.tintOverlayTitle', 'Page Color Tint (Irlen Visual Stress Comfort)')}
            </label>
            <p className="text-[11px] text-stone-500 mb-2">
              {t('accessibility.tintOverlayHelp', 'Softens bright screen glare to make letters still and clear')}
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
              {[
                { id: 'none', label: 'Off', color: '#FFFFFF', desc: 'Default screen' },
                { id: 'peach', label: 'Peach', color: '#FFE5D9', desc: 'Gentle warmth' },
                { id: 'mint', label: 'Mint', color: '#E8F5E9', desc: 'Cool relaxing' },
                { id: 'sky', label: 'Sky', color: '#E1F5FE', desc: 'Calming blue' },
                { id: 'butter', label: 'Butter', color: '#FFF9C4', desc: 'Soft sunlight' },
              ].map((tint) => (
                <button
                  key={tint.id}
                  type="button"
                  onClick={() => setField('tintOverlay', tint.id)}
                  className={`p-2.5 rounded-2xl border text-center transition-all cursor-pointer ${
                    draft.tintOverlay === tint.id
                      ? 'border-teal-700 ring-2 ring-teal-600 font-extrabold shadow-xs scale-105'
                      : 'border-stone-200 hover:scale-102'
                  }`}
                  style={{ backgroundColor: tint.color }}
                >
                  <span className="block text-xs font-bold text-stone-900">{tint.label}</span>
                  <span className="block text-[10px] text-stone-600 mt-0.5">{tint.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* High Contrast & Reduced Motion Toggles */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
            <div className="flex items-center justify-between p-3.5 bg-stone-50 rounded-2xl border border-stone-200">
              <div>
                <p className="text-xs font-bold text-stone-900">
                  {t('accessibility.highContrast', 'High Contrast')}
                </p>
                <p className="text-[11px] text-stone-500">
                  {t('accessibility.highContrastDesc', 'Pure black on white with thick borders')}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setField('highContrast', !draft.highContrast)}
                className={`w-12 h-6 rounded-full transition-colors relative cursor-pointer ${
                  draft.highContrast ? 'bg-teal-700' : 'bg-stone-300'
                }`}
                role="switch"
                aria-checked={draft.highContrast}
              >
                <div
                  className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-all ${
                    draft.highContrast ? 'left-7' : 'left-1'
                  }`}
                />
              </button>
            </div>

            <div className="flex items-center justify-between p-3.5 bg-stone-50 rounded-2xl border border-stone-200">
              <div>
                <p className="text-xs font-bold text-stone-900">
                  {t('accessibility.reducedMotion', 'Reduced Motion')}
                </p>
                <p className="text-[11px] text-stone-500">
                  {t('accessibility.reducedMotionDesc', 'Suppresses bouncy and distracting animations')}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setField('reducedMotion', !draft.reducedMotion)}
                className={`w-12 h-6 rounded-full transition-colors relative cursor-pointer ${
                  draft.reducedMotion ? 'bg-teal-700' : 'bg-stone-300'
                }`}
                role="switch"
                aria-checked={draft.reducedMotion}
              >
                <div
                  className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-all ${
                    draft.reducedMotion ? 'left-7' : 'left-1'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>
      </Card>

      {/* Background & Text Colors */}
      {!draft.highContrast && (
        <Card>
          <h2 className="text-base font-bold text-stone-900 mb-4 flex items-center gap-2">
            <span>🎨</span>
            <span>{t('accessibility.colorsTitle', 'Page & Text Color Themes')}</span>
          </h2>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {BG_THEMES.map((theme) => (
              <button
                key={theme.label}
                type="button"
                onClick={() => {
                  setField('bgColor', theme.bg)
                  setField('textColor', theme.text)
                }}
                className={`p-3 rounded-2xl border-2 transition-all cursor-pointer text-left ${
                  draft.bgColor === theme.bg
                    ? 'border-teal-700 ring-2 ring-teal-600 scale-105 shadow-sm'
                    : 'border-stone-200 hover:border-stone-400'
                }`}
                style={{ backgroundColor: theme.bg }}
              >
                <div className="h-4 w-4 rounded-full border mb-1.5" style={{ backgroundColor: theme.text }} />
                <span className="text-xs font-bold block" style={{ color: theme.text }}>
                  {theme.label}
                </span>
              </button>
            ))}
          </div>
        </Card>
      )}

      {/* Action Buttons */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
        <Button
          variant="outline"
          onClick={handleReset}
          disabled={saving}
          className="text-stone-600"
        >
          {t('accessibility.restoreDefaults', 'Reset All to Defaults')}
        </Button>

        <Button
          onClick={handleApplyAndSave}
          loading={saving}
          size="lg"
          className="px-8 shadow-sm"
        >
          {t('accessibility.savePreferences', 'Save Accessibility Settings')}
        </Button>
      </div>
    </div>
  )
}

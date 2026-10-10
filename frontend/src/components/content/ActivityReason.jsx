/**
 * frontend/src/components/content/ActivityReason.jsx
 *
 * Accessible, encouraging child-friendly 'Why this was chosen' component.
 * Displays pedagogical rationale without numerical scores or clinical labels.
 */
import React from 'react'
import { useTranslation } from '../../i18n/I18nContext'

export default function ActivityReason({
  reason,
  detailedRationale,
  targetSkills = [],
}) {
  const { t } = useTranslation()

  if (!reason) return null

  return (
    <div className="rounded-2xl bg-teal-50/60 border border-teal-200/80 p-4 space-y-2.5 text-xs sm:text-sm">
      <div className="flex items-center gap-2 text-teal-900 font-extrabold">
        <span aria-hidden="true" className="text-base">💡</span>
        <span>{t('recommendations.whyTitle', 'Why this activity?')}</span>
      </div>

      <p className="text-teal-950 font-medium leading-relaxed">
        {reason}
      </p>

      {targetSkills && targetSkills.length > 0 && (
        <div className="pt-1.5 flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] font-bold text-teal-800 uppercase tracking-wider">
            {t('personalizedContent.targetSkillsTitle', 'Skills in Focus:')}
          </span>
          {targetSkills.map((skill, idx) => (
            <span
              key={idx}
              className="px-2 py-0.5 rounded-lg bg-teal-100/80 text-teal-900 text-xs font-semibold capitalize"
            >
              {skill.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

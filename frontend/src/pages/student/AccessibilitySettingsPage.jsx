/**
 * frontend/src/pages/student/AccessibilitySettingsPage.jsx
 *
 * Dedicated Student Page for Reading Ergonomics, Focus Tools & Personalization.
 */
import React from 'react'
import { PageHeader } from '../../components/ui'
import { AccessibilitySettingsCard } from '../../components/accessibility'
import { useTranslation } from '../../i18n/I18nContext'

export default function AccessibilitySettingsPage() {
  const { t } = useTranslation()

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      <PageHeader
        icon="👓"
        title={t('accessibility.pageTitle', 'Reading & Accessibility')}
        subtitle={t(
          'accessibility.pageSubtitle',
          'Customize fonts, line spacing, focus tools, and display comfort for your reading style.'
        )}
      />

      <AccessibilitySettingsCard />
    </div>
  )
}

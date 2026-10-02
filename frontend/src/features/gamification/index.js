/**
 * frontend/src/features/gamification/index.js — V2 Gamification Component Barrel.
 */
export { default as BadgeCard } from './BadgeCard'
export { default as StreakDisplay } from './StreakDisplay'
export { default as MilestoneTracker } from './MilestoneTracker'
export { default as RewardHistoryList } from './RewardHistoryList'
export { default as CelebrationModal } from './CelebrationModal'

export const GAMIFICATION_MODULE_INFO = {
  version: '2.0',
  description: 'Streaks, accessible micro-celebrations, and effort-based milestone badges',
}

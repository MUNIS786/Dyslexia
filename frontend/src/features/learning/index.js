/**
 * frontend/src/features/learning/index.js — V2 Adaptive Learning Engine Feature Module.
 */
export { default as AdaptiveTaskCarousel } from './AdaptiveTaskCarousel'
export { default as InteractiveTaskPlayer } from './InteractiveTaskPlayer'
export { default as TierProgressionCard } from './TierProgressionCard'
export { default as AdaptiveEmptyState } from './AdaptiveEmptyState'

export const LEARNING_MODULE_INFO = {
  version: '2.0',
  description: 'Adaptive learning activities and micro-task player',
}

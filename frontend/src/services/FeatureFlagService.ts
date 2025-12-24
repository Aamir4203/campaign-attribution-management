/**
 * Feature Flag Service for CAM Application
 * Handles feature toggles and flags for UI components
 */

interface FeatureFlags {
  enableFileUpload: boolean;
  enableHybridMode: boolean;
  enableAdvancedValidation: boolean;
}

class FeatureFlagService {
  private flags: FeatureFlags = {
    enableFileUpload: true,
    enableHybridMode: true,
    enableAdvancedValidation: true
  };

  constructor() {
    this.loadFlags();
  }

  /**
   * Load flags from configuration or environment
   */
  private loadFlags(): void {
    try {
      // Check if we're in a Vite environment
      if (typeof import.meta !== 'undefined' && import.meta.env) {
        this.flags = {
          enableFileUpload: import.meta.env.VITE_ENABLE_FILE_UPLOAD !== 'false',
          enableHybridMode: import.meta.env.VITE_ENABLE_HYBRID_MODE !== 'false',
          enableAdvancedValidation: import.meta.env.VITE_ENABLE_ADVANCED_VALIDATION !== 'false',
        };
      }

      // Load from localStorage if available (for runtime toggles)
      const savedFlags = localStorage.getItem('cam_feature_flags');
      if (savedFlags) {
        const parsedFlags = JSON.parse(savedFlags);
        this.flags = { ...this.flags, ...parsedFlags };
      }
    } catch (error) {
      console.warn('Failed to load feature flags:', error);
      // Use defaults
    }
  }

  /**
   * Check if file upload feature is enabled
   */
  isFileUploadEnabled(): boolean {
    return this.flags.enableFileUpload;
  }

  /**
   * Check if hybrid input mode is enabled
   */
  isHybridModeEnabled(): boolean {
    return this.flags.enableHybridMode;
  }

  /**
   * Check if advanced validation is enabled
   */
  isAdvancedValidationEnabled(): boolean {
    return this.flags.enableAdvancedValidation;
  }

  /**
   * Get all feature flags
   */
  getAllFlags(): FeatureFlags {
    return { ...this.flags };
  }

  /**
   * Set a feature flag (for runtime toggling)
   */
  setFlag(flagName: keyof FeatureFlags, value: boolean): void {
    this.flags[flagName] = value;
    this.saveFlags();
  }

  /**
   * Save flags to localStorage
   */
  private saveFlags(): void {
    try {
      localStorage.setItem('cam_feature_flags', JSON.stringify(this.flags));
    } catch (error) {
      console.warn('Failed to save feature flags:', error);
    }
  }

  /**
   * Reset flags to defaults
   */
  resetToDefaults(): void {
    this.flags = {
      enableFileUpload: true,
      enableHybridMode: true,
      enableAdvancedValidation: true
    };
    this.saveFlags();
  }
}

// Singleton instance
export const featureFlagService = new FeatureFlagService();
export type { FeatureFlags };
export default FeatureFlagService;

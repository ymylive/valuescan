/**
 * Configuration Validation Utilities
 *
 * Provides validation functions for ValueScan configuration fields
 */

import type { FieldSchema } from '../types/config'

// ==================== Validation Types ====================

export interface ValidationError {
  field: string
  message: string
  type: 'required' | 'range' | 'format' | 'custom'
}

export interface ValidationResult {
  valid: boolean
  errors: ValidationError[]
}

// ==================== Sensitive Field Detection ====================

const SENSITIVE_PATTERNS = [
  /secret/i,
  /password/i,
  /token/i,
  /api[_-]?key/i,
  /api[_-]?secret/i,
  /api[_-]?hash/i,
  /private/i,
]

/**
 * Check if a field key is sensitive (should be masked)
 * Property 1: Sensitive Field Masking
 */
export function isSensitiveKey(key: string): boolean {
  return SENSITIVE_PATTERNS.some((pattern) => pattern.test(key))
}

// ==================== Numeric Range Validation ====================

/**
 * Validate a numeric value is within the specified range
 * Property 2: Numeric Range Validation
 */
export function validateNumericRange(
  value: number | undefined | null,
  min?: number,
  max?: number
): { valid: boolean; message?: string } {
  if (value === undefined || value === null) {
    return { valid: true }
  }

  if (typeof value !== 'number' || isNaN(value)) {
    return { valid: false, message: '必须是有效数字' }
  }

  if (min !== undefined && value < min) {
    return { valid: false, message: `不能小于 ${min}` }
  }

  if (max !== undefined && value > max) {
    return { valid: false, message: `不能大于 ${max}` }
  }

  return { valid: true }
}

/**
 * Clamp a value to the specified range
 */
export function clampValue(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

// ==================== Required Field Validation ====================

/**
 * Validate that a required field has a value
 */
export function validateRequired(
  value: unknown,
  fieldName: string
): { valid: boolean; message?: string } {
  if (value === undefined || value === null) {
    return { valid: false, message: `${fieldName} 是必填项` }
  }

  if (typeof value === 'string' && value.trim() === '') {
    return { valid: false, message: `${fieldName} 不能为空` }
  }

  if (Array.isArray(value) && value.length === 0) {
    return { valid: false, message: `${fieldName} 不能为空` }
  }

  return { valid: true }
}

// ==================== Format Validation ====================

/**
 * Validate numeric input format
 */
export function isValidNumericInput(value: string): boolean {
  if (value === '' || value === '-') return true
  return /^-?\d*\.?\d*$/.test(value)
}

/**
 * Validate integer input format
 */
export function isValidIntegerInput(value: string): boolean {
  if (value === '' || value === '-') return true
  return /^-?\d*$/.test(value)
}

// ==================== Field Schema Validation ====================

/**
 * Validate a single field against its schema
 */
export function validateField(
  key: string,
  value: unknown,
  schema?: FieldSchema
): ValidationError | null {
  // Required validation
  if (schema?.required) {
    const result = validateRequired(value, schema.label || key)
    if (!result.valid) {
      return { field: key, message: result.message!, type: 'required' }
    }
  }

  // Skip further validation if value is empty and not required
  if (value === undefined || value === null || value === '') {
    return null
  }

  // Numeric range validation
  if (schema?.type === 'number' && typeof value === 'number') {
    const result = validateNumericRange(value, schema.min, schema.max)
    if (!result.valid) {
      return { field: key, message: result.message!, type: 'range' }
    }
  }

  // Pattern validation
  if (schema?.pattern && typeof value === 'string') {
    const regex = new RegExp(schema.pattern)
    if (!regex.test(value)) {
      return { field: key, message: '格式不正确', type: 'format' }
    }
  }

  return null
}

/**
 * Validate all fields in a config object
 * Property 5: Validation Error Prevention
 */
export function validateConfig(
  config: Record<string, unknown>,
  schemas: Record<string, FieldSchema>
): ValidationResult {
  const errors: ValidationError[] = []

  for (const [key, schema] of Object.entries(schemas)) {
    const error = validateField(key, config[key], schema)
    if (error) {
      errors.push(error)
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  }
}

// ==================== Search Filter ====================

/**
 * Filter configuration fields by search query
 * Property 4: Search Filter Accuracy
 */
export function filterFieldsBySearch(
  fields: Array<{ key: string; label: string; group?: string }>,
  query: string
): Array<{ key: string; label: string; group?: string }> {
  if (!query.trim()) {
    return fields
  }

  const lowerQuery = query.toLowerCase().trim()

  return fields.filter((field) => {
    const keyMatch = field.key.toLowerCase().includes(lowerQuery)
    const labelMatch = field.label.toLowerCase().includes(lowerQuery)
    const groupMatch = field.group?.toLowerCase().includes(lowerQuery) ?? false
    return keyMatch || labelMatch || groupMatch
  })
}

// ==================== Keepalive Specific Validation ====================

/**
 * Validate Keepalive check interval (10-300 seconds)
 * Property 12: Keepalive Check Interval Bounds
 */
export function validateKeepaliveCheckInterval(value: number): {
  valid: boolean
  clamped: number
  message?: string
} {
  const MIN = 10
  const MAX = 300

  if (typeof value !== 'number' || isNaN(value)) {
    return { valid: false, clamped: 60, message: '检查间隔必须是有效数字' }
  }

  const clamped = clampValue(value, MIN, MAX)
  const valid = value >= MIN && value <= MAX

  return {
    valid,
    clamped,
    message: valid ? undefined : `检查间隔必须在 ${MIN}-${MAX} 秒之间`,
  }
}

/**
 * Validate Telegram alert configuration dependency
 * Property 13: Telegram Alert Dependency
 */
export function validateTelegramAlertConfig(config: {
  enabled: boolean
  bot_token: string
  chat_id: string
}): ValidationResult {
  const errors: ValidationError[] = []

  if (config.enabled) {
    if (!config.bot_token?.trim()) {
      errors.push({
        field: 'telegram.bot_token',
        message: '启用 Telegram 告警时必须配置 Bot Token',
        type: 'required',
      })
    }
    if (!config.chat_id?.trim()) {
      errors.push({
        field: 'telegram.chat_id',
        message: '启用 Telegram 告警时必须配置 Chat ID',
        type: 'required',
      })
    }
  }

  return { valid: errors.length === 0, errors }
}

// ==================== Export Utilities ====================

/**
 * Remove sensitive fields from config for export
 * Property 10: Export Sensitive Field Handling
 */
export function removeSensitiveFields<T extends Record<string, unknown>>(
  config: T
): Partial<T> {
  const result: Partial<T> = {}

  for (const [key, value] of Object.entries(config)) {
    if (!isSensitiveKey(key)) {
      if (
        typeof value === 'object' &&
        value !== null &&
        !Array.isArray(value)
      ) {
        result[key as keyof T] = removeSensitiveFields(
          value as Record<string, unknown>
        ) as T[keyof T]
      } else {
        result[key as keyof T] = value as T[keyof T]
      }
    }
  }

  return result
}

/**
 * Redact sensitive fields (replace with placeholder)
 */
export function redactSensitiveFields<T extends Record<string, unknown>>(
  config: T,
  placeholder = '***REDACTED***'
): T {
  const result = { ...config }

  for (const key of Object.keys(result)) {
    if (isSensitiveKey(key)) {
      result[key as keyof T] = placeholder as T[keyof T]
    } else if (
      typeof result[key] === 'object' &&
      result[key] !== null &&
      !Array.isArray(result[key])
    ) {
      result[key as keyof T] = redactSensitiveFields(
        result[key] as Record<string, unknown>,
        placeholder
      ) as T[keyof T]
    }
  }

  return result
}

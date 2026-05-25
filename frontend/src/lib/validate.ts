/**
 * Input validation utilities
 * Provides functions for sanitizing and validating user inputs
 */

// Maximum allowed lengths
export const MAX_SEARCH_LENGTH = 200;
export const MAX_FILE_NAME_LENGTH = 255;
export const MAX_CATEGORY_LENGTH = 50;

/**
 * Valid category values
 */
export const VALID_CATEGORIES = [
  '通用', '变压器', '开关柜', '断路器', '隔离开关',
  '互感器', '避雷器', '电容器', '电缆', '继电保护装置', '其他',
];

/**
 * Characters not allowed in filenames (path traversal prevention)
 */
const FORBIDDEN_FILE_CHARS = /[<>:"/\\|?*\x00-\x1f]/g;

/**
 * Patterns that might indicate injection attempts
 */
const DANGEROUS_PATTERNS = [
  /\.\./g,           // Path traversal
  /<script/i,        // XSS attempts
  /javascript:/i,    // JavaScript protocol
  /data:/i,          // Data protocol
  /on\w+=/i,         // Event handlers
];

/**
 * Sanitize search input - removes HTML tags and special characters
 */
export function sanitizeSearchInput(input: string): string {
  if (!input) return '';

  // Trim whitespace
  let sanitized = input.trim();

  // Remove HTML tags
  sanitized = sanitized.replace(/<[^>]*>/g, '');

  // Remove potential XSS patterns
  sanitized = sanitized.replace(/javascript:/gi, '');
  sanitized = sanitized.replace(/on\w+=/gi, '');

  // Encode special characters
  sanitized = sanitized
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;');

  // Truncate to max length
  if (sanitized.length > MAX_SEARCH_LENGTH) {
    sanitized = sanitized.substring(0, MAX_SEARCH_LENGTH);
  }

  return sanitized;
}

/**
 * Validate filename - prevents path traversal and invalid characters
 */
export function validateFileName(fileName: string): { valid: boolean; error?: string; sanitized?: string } {
  if (!fileName) {
    return { valid: false, error: '文件名不能为空' };
  }

  // Check length
  if (fileName.length > MAX_FILE_NAME_LENGTH) {
    return { valid: false, error: `文件名长度不能超过 ${MAX_FILE_NAME_LENGTH} 个字符` };
  }

  // Remove forbidden characters
  const sanitized = fileName.replace(FORBIDDEN_FILE_CHARS, '_');

  // Check for path traversal
  if (sanitized.includes('..')) {
    return { valid: false, error: '文件名包含非法路径' };
  }

  // Check for dangerous patterns
  for (const pattern of DANGEROUS_PATTERNS) {
    if (pattern.test(sanitized)) {
      return { valid: false, error: '文件名包含非法字符' };
    }
  }

  // Check for reserved names (Windows)
  const reserved = /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\.|$)/i;
  if (reserved.test(sanitized)) {
    return { valid: false, error: '文件名不能使用系统保留名称' };
  }

  return { valid: true, sanitized };
}

/**
 * Validate category - ensures category is from allowed list
 */
export function validateCategory(category: string): { valid: boolean; sanitized?: string; error?: string } {
  if (!category) {
    return { valid: false, error: '分类不能为空' };
  }

  // Trim whitespace
  const trimmed = category.trim();

  // Check length
  if (trimmed.length > MAX_CATEGORY_LENGTH) {
    return { valid: false, error: `分类名称长度不能超过 ${MAX_CATEGORY_LENGTH} 个字符` };
  }

  // Check if in allowed list
  if (!VALID_CATEGORIES.includes(trimmed)) {
    return { valid: false, error: `分类 "${trimmed}" 不在允许列表中` };
  }

  return { valid: true, sanitized: trimmed };
}

/**
 * General max length validator
 */
export function validateMaxLength(value: string, maxLength: number): { valid: boolean; error?: string } {
  if (!value) return { valid: true }; // Empty is valid

  if (value.length > maxLength) {
    return { valid: false, error: `输入长度不能超过 ${maxLength} 个字符` };
  }

  return { valid: true };
}

/**
 * Check if input contains potential dangerous patterns
 */
export function containsDangerousPattern(input: string): boolean {
  return DANGEROUS_PATTERNS.some(pattern => pattern.test(input));
}

/**
 * Validate URL-safe string (for IDs, keys, etc.)
 */
export function validateUrlSafeString(input: string): boolean {
  if (!input) return false;
  // Allow alphanumeric, underscore, hyphen, dot
  return /^[a-zA-Z0-9_.-]+$/.test(input);
}

/**
 * Sanitize for SQL-like injection prevention (defense in depth)
 */
export function sanitizeForStorage(input: string): string {
  if (!input) return '';

  return input
    .replace(/'/g, "''")
    .replace(/"/g, '""')
    .replace(/\\/g, '\\\\')
    .replace(/;/g, '')
    .replace(/--/g, '')
    .replace(/\/\*/g, '')
    .replace(/\*\//g, '');
}
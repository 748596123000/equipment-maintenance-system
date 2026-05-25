/**
 * Security utilities for XSS protection
 * Uses DOMPurify to sanitize HTML content
 */

import DOMPurify from 'dompurify';

/**
 * Configure DOMPurify with strict security settings
 */
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  // Remove all data: protocol handlers
  if (node.hasAttribute('href')) {
    const href = node.getAttribute('href') || '';
    if (href.startsWith('javascript:') || href.startsWith('data:')) {
      node.removeAttribute('href');
    }
  }
  // Remove all event handlers
  const eventAttributes = Array.from(node.attributes)
    .filter(attr => attr.name.startsWith('on'))
    .map(attr => attr.name);
  eventAttributes.forEach(attr => node.removeAttribute(attr));
});

// Allowed tags for HTML content (minimal set for security)
const ALLOWED_TAGS = ['p', 'br', 'strong', 'b', 'em', 'i', 'u', 'code', 'pre', 'span', 'div', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'blockquote'];

// Allowed attributes
const ALLOWED_ATTR = ['href', 'class', 'title'];

/**
 * Sanitize HTML content - removes all dangerous elements and attributes
 * Use for AI-generated content that may contain HTML
 */
export function sanitizeHTML(html: string): string {
  if (!html) return '';

  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    FORBID_TAGS: ['script', 'style', 'iframe', 'form', 'input', 'button', 'object', 'embed'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur'],
    ALLOW_DATA_ATTR: false,
    ADD_ATTR: ['target'], // Allow target attribute for links
  });
}

/**
 * Sanitize plain text - escapes HTML entities to prevent XSS
 * Use for user input that should be displayed as text
 */
export function sanitizeText(text: string): string {
  if (!text) return '';

  const entityMap: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
    '/': '&#x2F;',
    '`': '&#x60;',
    '=': '&#x3D;',
  };

  return String(text).replace(/[&<>"'`=/]/g, (s) => entityMap[s] || s);
}

/**
 * Check if content contains potential XSS patterns
 * Useful for logging/monitoring suspicious activity
 */
export function detectXSS(content: string): boolean {
  const patterns = [
    /<script/i,
    /javascript:/i,
    /on\w+=/i,
    /<iframe/i,
    /<object/i,
    /<embed/i,
    /data:/i,
    /expression\s*\(/i,
  ];

  return patterns.some(pattern => pattern.test(content));
}

/**
 * Sanitize text content for display in chat bubbles
 * Preserves whitespace and line breaks
 */
export function sanitizeChatContent(content: string, isUserMessage: boolean = true): string {
  if (!content) return '';

  // User messages are always treated as plain text (never HTML)
  if (isUserMessage) {
    return sanitizeText(content);
  }

  // AI messages can contain limited HTML (like code blocks)
  // but we still sanitize to prevent XSS
  return DOMPurify.sanitize(content, {
    ALLOWED_TAGS: ['p', 'br', 'code', 'pre', 'span', 'strong', 'b', 'em', 'i', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'blockquote', 'a'],
    ALLOWED_ATTR: ['href', 'class'],
    ALLOW_DATA_ATTR: false,
    ADD_ATTR: ['target'],
    KEEP_CONTENT: true,
  });
}
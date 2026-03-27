/**
 * Component Index
 *
 * Centralized export of all form and chat components
 */

// Form components
export { default as FormRenderer } from './FormRenderer';
export { default as FormField } from './FormField';
export { default as FormCardBubble } from './FormCardBubble';

// Chat components
export { default as ChatMessage } from './ChatMessage';
export { default as ChatInput } from './ChatInput';
export { default as SkillSelector } from './SkillSelector';

// Re-export constants and types if needed
export const FIELD_TYPES = {
  TEXT: 'text',
  EMAIL: 'email',
  TEXTAREA: 'textarea',
  NUMBER: 'number',
  SELECT: 'select',
  RADIO: 'radio',
  CHECKBOX: 'checkbox',
  FILE_UPLOAD: 'file_upload',
  HIDDEN: 'hidden'
};

export const FORM_STATES = {
  EDITABLE: 'editable',
  READONLY: 'readonly'
};

export const MESSAGE_TYPES = {
  TEXT: 'text',
  FORM_CARD: 'form_card',
  SUMMARY_CARD: 'summary_card',
  IMAGE: 'image',
  FILE: 'file'
};

export const MESSAGE_SENDERS = {
  AGENT: 'agent',
  USER: 'user',
  SYSTEM: 'system'
};

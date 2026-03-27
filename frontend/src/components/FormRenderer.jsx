import React, { useState, useCallback, useMemo, useEffect } from 'react';
import PropTypes from 'prop-types';
import FormField from './FormField';
import './FormRenderer.css';

/**
 * FormRenderer Component
 *
 * Universal form rendering engine that renders any FormSchema JSON without code changes.
 * This is the core innovation of the IM form card system - Agent generates JSON,
 * FormRenderer renders it, no React code generation needed.
 *
 * @component
 * @param {Object} props
 * @param {Object} props.schema - FormSchema JSON object
 * @param {Function} props.onSubmit - Callback when form is submitted (receives formData)
 * @param {Function} props.onCancel - Callback when form is cancelled
 * @param {Function} props.onModify - Callback when form modify button is clicked
 * @param {Object} props.initialData - Initial form data values
 * @param {boolean} props.showConfirmation - Show confirmation dialogs for actions
 */
const FormRenderer = ({
  schema,
  onSubmit,
  onCancel,
  onModify,
  initialData = {},
  showConfirmation = true
}) => {
  // Form state management
  const [formData, setFormData] = useState(initialData);
  const [touched, setTouched] = useState({});
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fix 11B: 初始化 readonly 字段的值到 formData
  // 这样即使 readonly 字段不能编辑，其值也会在表单提交时被包含
  useEffect(() => {
    const initializedData = { ...formData };
    let hasReadonlyFields = false;

    schema.sections?.forEach(section => {
      section.fields?.forEach(field => {
        if (field.readonly && field.id && !initializedData[field.id]) {
          initializedData[field.id] = field.value || field.defaultValue || '';
          hasReadonlyFields = true;
        }
      });
    });

    if (hasReadonlyFields) {
      setFormData(initializedData);
    }
  }, [schema]);

  // Validation logic
  const validateField = useCallback((fieldId, value, field) => {
    // Required field validation
    if (field.required && (!value || value.toString().trim() === '')) {
      return `${field.label} 为必填项`;
    }

    // Text field length validation
    if (field.minLength && value && value.length < field.minLength) {
      return `${field.label} 最少需要 ${field.minLength} 个字符`;
    }

    if (field.maxLength && value && value.length > field.maxLength) {
      return `${field.label} 最多只能 ${field.maxLength} 个字符`;
    }

    // Pattern validation for regex
    if (field.pattern && value) {
      const regex = new RegExp(field.pattern);
      if (!regex.test(value)) {
        return `${field.label} 格式不正确`;
      }
    }

    // Email validation
    if (field.type === 'email' && value) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(value)) {
        return `${field.label} 必须是有效的邮箱`;
      }
    }

    // Number validation
    if (field.type === 'number' && value) {
      if (isNaN(value)) {
        return `${field.label} 必须是数字`;
      }
    }

    return null;
  }, []);

  // Validate entire form
  const validateForm = useCallback(() => {
    const newErrors = {};
    let isValid = true;

    schema.sections.forEach(section => {
      section.fields.forEach(field => {
        const error = validateField(field.id, formData[field.id], field);
        if (error) {
          newErrors[field.id] = error;
          isValid = false;
        }
      });
    });

    setErrors(newErrors);
    return isValid;
  }, [schema, formData, validateField]);

  // Handle field change
  const handleFieldChange = useCallback((fieldId, value) => {
    setFormData(prev => ({
      ...prev,
      [fieldId]: value
    }));

    // Clear error when user starts typing
    if (errors[fieldId]) {
      setErrors(prev => ({
        ...prev,
        [fieldId]: null
      }));
    }
  }, [errors]);

  // Handle field blur (mark as touched)
  const handleFieldBlur = useCallback((fieldId) => {
    setTouched(prev => ({
      ...prev,
      [fieldId]: true
    }));

    // Validate field on blur
    const field = findFieldById(fieldId);
    if (field) {
      const error = validateField(fieldId, formData[fieldId], field);
      setErrors(prev => ({
        ...prev,
        [fieldId]: error
      }));
    }
  }, [formData, validateField]);

  // Find field by ID from schema
  const findFieldById = useCallback((fieldId) => {
    for (const section of schema.sections) {
      const field = section.fields.find(f => f.id === fieldId);
      if (field) return field;
    }
    return null;
  }, [schema]);

  // Handle form submission
  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();

    // Validate form
    if (!validateForm()) {
      console.warn('Form validation failed');
      return;
    }

    // Show confirmation dialog if enabled
    if (showConfirmation) {
      const confirmed = window.confirm('确认提交表单吗？');
      if (!confirmed) {
        return;
      }
    }

    setIsSubmitting(true);
    try {
      // Call parent callback
      await onSubmit?.(formData);
    } catch (error) {
      console.error('Form submission error:', error);
      alert('表单提交失败，请重试');
    } finally {
      setIsSubmitting(false);
    }
  }, [formData, validateForm, showConfirmation, onSubmit]);

  // Handle form cancel
  const handleCancel = useCallback(() => {
    if (showConfirmation) {
      const confirmed = window.confirm('确认取消表单吗？');
      if (!confirmed) {
        return;
      }
    }

    onCancel?.();
  }, [showConfirmation, onCancel]);

  // Handle form modify (readonly state only)
  const handleModify = useCallback(() => {
    if (showConfirmation) {
      const confirmed = window.confirm('确认要修改已提交的表单吗？');
      if (!confirmed) {
        return;
      }
    }

    onModify?.();
  }, [showConfirmation, onModify]);

  // Determine if form is editable
  const isEditable = schema.state !== 'readonly';

  // Get actions config with defaults
  const actions = useMemo(() => ({
    showSubmit: true,
    showCancel: true,
    showModify: schema.state === 'readonly',
    submitText: '提交',
    cancelText: '取消',
    modifyText: '修改',
    ...schema.actions
  }), [schema]);

  return (
    <div className={`form-renderer form-renderer--${schema.state}`}>
      <div className="form-header">
        <h3 className="form-title">{schema.title}</h3>
        {schema.description && (
          <p className="form-description">{schema.description}</p>
        )}
      </div>

      <form className="form-content" onSubmit={handleSubmit}>
        {schema.sections.map((section, sectionIndex) => (
          <div key={section.id || sectionIndex} className="form-section">
            <div className="section-header">
              <h4 className="section-title">{section.title}</h4>
              {section.description && (
                <p className="section-description">{section.description}</p>
              )}
            </div>

            <div className="section-fields">
              {section.fields.map((field, fieldIndex) => (
                <FormField
                  key={field.id || fieldIndex}
                  field={field}
                  value={formData[field.id] || ''}
                  error={touched[field.id] ? errors[field.id] : null}
                  touched={touched[field.id]}
                  disabled={!isEditable}
                  onChange={(value) => handleFieldChange(field.id, value)}
                  onBlur={() => handleFieldBlur(field.id)}
                  onValidate={(value) => validateField(field.id, value, field)}
                />
              ))}
            </div>
          </div>
        ))}
      </form>

      {/* Form Actions */}
      {(actions.showSubmit || actions.showCancel || actions.showModify) && (
        <div className={`form-actions form-actions--${schema.state}`}>
          {actions.showCancel && (
            <button
              type="button"
              className="btn btn-cancel"
              onClick={handleCancel}
              disabled={isSubmitting}
            >
              {actions.cancelText}
            </button>
          )}

          {isEditable && actions.showSubmit && (
            <button
              type="submit"
              className="btn btn-submit"
              onClick={handleSubmit}
              disabled={isSubmitting}
            >
              {isSubmitting ? '提交中...' : actions.submitText}
            </button>
          )}

          {schema.state === 'readonly' && actions.showModify && (
            <button
              type="button"
              className="btn btn-modify"
              onClick={handleModify}
              disabled={isSubmitting}
            >
              {actions.modifyText}
            </button>
          )}
        </div>
      )}
    </div>
  );
};

FormRenderer.propTypes = {
  schema: PropTypes.shape({
    id: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    description: PropTypes.string,
    state: PropTypes.oneOf(['editable', 'readonly']).isRequired,
    sections: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.string.isRequired,
        title: PropTypes.string.isRequired,
        description: PropTypes.string,
        fields: PropTypes.array.isRequired
      })
    ).isRequired,
    actions: PropTypes.shape({
      showSubmit: PropTypes.bool,
      showCancel: PropTypes.bool,
      showModify: PropTypes.bool,
      submitText: PropTypes.string,
      cancelText: PropTypes.string,
      modifyText: PropTypes.string
    })
  }).isRequired,
  onSubmit: PropTypes.func,
  onCancel: PropTypes.func,
  onModify: PropTypes.func,
  initialData: PropTypes.object,
  showConfirmation: PropTypes.bool
};

FormRenderer.defaultProps = {
  initialData: {},
  showConfirmation: true,
  onSubmit: () => {},
  onCancel: () => {},
  onModify: () => {}
};

export default FormRenderer;

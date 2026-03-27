import React, { useCallback } from 'react';
import PropTypes from 'prop-types';
import './FormField.css';

/**
 * FormField Component
 *
 * Renders a single form field based on configuration.
 * Supports: text, email, textarea, number, select, radio, checkbox, file_upload, hidden
 *
 * @component
 * @param {Object} props
 * @param {Object} props.field - Field configuration object
 * @param {string} props.field.id - Field unique identifier
 * @param {string} props.field.type - Field type
 * @param {string} props.field.label - Field label
 * @param {*} props.value - Current field value
 * @param {string} props.error - Error message if any
 * @param {boolean} props.touched - Whether field has been touched
 * @param {boolean} props.disabled - Whether field is disabled
 * @param {Function} props.onChange - Callback on field change
 * @param {Function} props.onBlur - Callback on field blur
 */
const FormField = ({
  field,
  value,
  error,
  touched,
  disabled = false,
  onChange,
  onBlur,
  onValidate
}) => {
  const {
    id,
    type,
    label,
    placeholder,
    required,
    readonly,
    helpText,
    minLength,
    maxLength,
    defaultValue,
    // For select/radio/checkbox
    options,
    multiple,
    // For file upload
    accept,
    maxSize,
    // For number
    min,
    max,
    // For text
    pattern
  } = field;

  // File input handler
  const handleFileChange = useCallback((e) => {
    const files = e.target.files;
    if (!files) return;

    // Single file upload
    if (!multiple) {
      const file = files[0];

      // Validate file size
      if (maxSize && file.size > maxSize) {
        const sizeMB = (maxSize / 1024 / 1024).toFixed(2);
        const errorMsg = `文件大小不能超过 ${sizeMB}MB`;
        onValidate?.(null);
        // Show error message
        alert(errorMsg);
        return;
      }

      onChange?.(file);
    } else {
      // Multiple file upload
      const fileList = Array.from(files);

      // Validate each file size
      for (const file of fileList) {
        if (maxSize && file.size > maxSize) {
          const sizeMB = (maxSize / 1024 / 1024).toFixed(2);
          alert(`文件 ${file.name} 大小超过 ${sizeMB}MB`);
          return;
        }
      }

      onChange?.(fileList);
    }
  }, [maxSize, multiple, onChange, onValidate]);

  // Get display value for file uploads
  const getFileDisplayValue = useCallback((fileValue) => {
    if (!fileValue) return '';

    if (fileValue instanceof File) {
      return fileValue.name;
    }

    if (Array.isArray(fileValue)) {
      return fileValue.map(f => f instanceof File ? f.name : f).join(', ');
    }

    return String(fileValue);
  }, []);

  // Render field based on type
  const renderField = () => {
    // Fix 11B: 区分 readonly 和 disabled
    // readonly 字段显示为纯文本，但仍然在表单中管理其值
    if (readonly) {
      return (
        <>
          {/* 显示为纯文本标签（只读展示） */}
          <div
            className="form-field-readonly-display"
            id={id}
            aria-label={label}
          >
            {value || defaultValue || '(未设置)'}
          </div>
          {/* 隐藏的输入字段，确保表单提交时值被包含，且允许formData管理 */}
          <input
            type="hidden"
            name={id}
            value={value || defaultValue || ''}
            onChange={(e) => onChange?.(e.target.value)}
          />
        </>
      );
    }

    const commonProps = {
      id,
      name: id,
      value: value || defaultValue || '',
      onChange: (e) => onChange?.(e.target.value),
      onBlur: onBlur,
      disabled: disabled,  // 改为只检查 disabled，不包含 readonly
      'aria-label': label,
      'aria-invalid': !!error,
      'aria-required': required
    };

    switch (type) {
      case 'text':
        return (
          <input
            {...commonProps}
            type="text"
            placeholder={placeholder}
            minLength={minLength}
            maxLength={maxLength}
            pattern={pattern}
            className="form-field-input"
            required={required}
          />
        );

      case 'email':
        return (
          <input
            {...commonProps}
            type="email"
            placeholder={placeholder}
            className="form-field-input"
            required={required}
          />
        );

      case 'number':
        return (
          <input
            {...commonProps}
            type="number"
            placeholder={placeholder}
            min={min}
            max={max}
            className="form-field-input"
            required={required}
            onChange={(e) => onChange?.(e.target.value ? parseFloat(e.target.value) : '')}
          />
        );

      case 'textarea':
        return (
          <textarea
            {...commonProps}
            placeholder={placeholder}
            minLength={minLength}
            maxLength={maxLength}
            className="form-field-textarea"
            rows={4}
            required={required}
          />
        );

      case 'select':
        return (
          <select
            {...commonProps}
            className="form-field-select"
            multiple={multiple}
            required={required}
          >
            <option value="">-- 请选择 --</option>
            {options?.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        );

      case 'radio':
        return (
          <div className="form-field-radio-group">
            {options?.map((option) => (
              <label key={option.value} className="radio-label">
                <input
                  type="radio"
                  name={id}
                  value={option.value}
                  checked={value === option.value}
                  onChange={(e) => onChange?.(e.target.value)}
                  disabled={disabled}
                  required={required}
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        );

      case 'checkbox':
        return (
          <div className="form-field-checkbox-group">
            {options?.map((option) => (
              <label key={option.value} className="checkbox-label">
                <input
                  type="checkbox"
                  name={id}
                  value={option.value}
                  checked={
                    Array.isArray(value)
                      ? value.includes(option.value)
                      : value === option.value
                  }
                  onChange={(e) => {
                    if (multiple || Array.isArray(value)) {
                      const newValue = Array.isArray(value) ? [...value] : [];
                      if (e.target.checked) {
                        newValue.push(option.value);
                      } else {
                        newValue.splice(newValue.indexOf(option.value), 1);
                      }
                      onChange?.(newValue);
                    } else {
                      onChange?.(e.target.checked ? option.value : '');
                    }
                  }}
                  disabled={disabled}
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        );

      case 'file_upload':
        return (
          <div className="form-field-file-upload">
            <label className="file-input-label" htmlFor={id}>
              <input
                type="file"
                id={id}
                name={id}
                accept={accept}
                multiple={multiple}
                onChange={handleFileChange}
                className="file-input-hidden"
                required={required && !value}
                disabled={disabled}
                aria-label={label}
              />
              <span className="file-input-button">
                {value ? '更换文件' : '选择文件'}
              </span>
            </label>
            {value && (
              <span className="file-display-value">
                {getFileDisplayValue(value)}
              </span>
            )}
          </div>
        );

      case 'hidden':
        return (
          <input
            type="hidden"
            id={id}
            name={id}
            value={value || defaultValue || ''}
            onChange={(e) => onChange?.(e.target.value)}
          />
        );

      default:
        console.warn(`Unknown field type: ${type}`);
        return null;
    }
  };

  // Don't render container for hidden fields
  if (type === 'hidden') {
    return renderField();
  }

  return (
    <div className={`form-field form-field--${type} ${error ? 'form-field--error' : ''}`}>
      <div className="field-header">
        <label htmlFor={id} className="field-label">
          {label}
          {required && <span className="field-required">*</span>}
        </label>
      </div>

      <div className="field-input-wrapper">
        {renderField()}
      </div>

      {helpText && !error && (
        <p className="field-help-text">{helpText}</p>
      )}

      {error && touched && (
        <p className="field-error-message" role="alert">
          {error}
        </p>
      )}
    </div>
  );
};

FormField.propTypes = {
  field: PropTypes.shape({
    id: PropTypes.string.isRequired,
    type: PropTypes.oneOf([
      'text',
      'email',
      'textarea',
      'number',
      'select',
      'radio',
      'checkbox',
      'file_upload',
      'hidden'
    ]).isRequired,
    label: PropTypes.string.isRequired,
    placeholder: PropTypes.string,
    required: PropTypes.bool,
    readonly: PropTypes.bool,
    helpText: PropTypes.string,
    defaultValue: PropTypes.any,
    minLength: PropTypes.number,
    maxLength: PropTypes.number,
    min: PropTypes.number,
    max: PropTypes.number,
    pattern: PropTypes.string,
    options: PropTypes.arrayOf(
      PropTypes.shape({
        value: PropTypes.string.isRequired,
        label: PropTypes.string.isRequired
      })
    ),
    multiple: PropTypes.bool,
    accept: PropTypes.string,
    maxSize: PropTypes.number
  }).isRequired,
  value: PropTypes.any,
  error: PropTypes.string,
  touched: PropTypes.bool,
  disabled: PropTypes.bool,
  onChange: PropTypes.func,
  onBlur: PropTypes.func,
  onValidate: PropTypes.func
};

FormField.defaultProps = {
  value: '',
  error: null,
  touched: false,
  disabled: false,
  onChange: () => {},
  onBlur: () => {},
  onValidate: () => {}
};

export default FormField;

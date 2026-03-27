import React, { useCallback } from 'react';
import PropTypes from 'prop-types';
import FormRenderer from './FormRenderer';
import './FormCardBubble.css';

/**
 * FormCardBubble Component
 *
 * Displays a form as a chat bubble in the IM interface.
 * Wraps FormRenderer and provides chat-specific styling and behavior.
 *
 * @component
 * @param {Object} props
 * @param {Object} props.schema - FormSchema JSON object
 * @param {string} props.sender - Who sent this form ('agent' or 'user')
 * @param {string} props.timestamp - When the form was sent (ISO string)
 * @param {Function} props.onSubmit - Callback on form submission
 * @param {Function} props.onCancel - Callback on form cancellation
 * @param {Function} props.onModify - Callback on form modification
 * @param {Object} props.initialData - Initial form data
 * @param {string} props.className - Additional CSS classes
 */
const FormCardBubble = ({
  schema,
  sender = 'agent',
  timestamp,
  onSubmit,
  onCancel,
  onModify,
  initialData = {},
  className = ''
}) => {
  const handleSubmit = useCallback(async (formData) => {
    console.log('Form submitted:', {
      formId: schema.id,
      formData,
      timestamp: new Date().toISOString()
    });

    // Call parent callback
    await onSubmit?.(formData);
  }, [schema.id, onSubmit]);

  const handleCancel = useCallback(() => {
    console.log('Form cancelled:', {
      formId: schema.id,
      timestamp: new Date().toISOString()
    });

    onCancel?.();
  }, [schema.id, onCancel]);

  const handleModify = useCallback(() => {
    console.log('Form modify requested:', {
      formId: schema.id,
      timestamp: new Date().toISOString()
    });

    onModify?.();
  }, [schema.id, onModify]);

  // Format timestamp
  const formatTime = (isoString) => {
    if (!isoString) return '';

    const date = new Date(isoString);
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');

    return `${hours}:${minutes}`;
  };

  return (
    <div
      className={`form-card-bubble form-card-bubble--${sender} ${className}`}
      role="article"
      aria-label={`${schema.title} 表单`}
    >
      <div className="bubble-container">
        <FormRenderer
          schema={schema}
          initialData={initialData}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          onModify={handleModify}
          showConfirmation={true}
        />
      </div>

      {timestamp && (
        <div className="bubble-timestamp">
          {formatTime(timestamp)}
        </div>
      )}
    </div>
  );
};

FormCardBubble.propTypes = {
  schema: PropTypes.shape({
    id: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    state: PropTypes.oneOf(['editable', 'readonly']).isRequired,
    sections: PropTypes.array.isRequired
  }).isRequired,
  sender: PropTypes.oneOf(['agent', 'user']),
  timestamp: PropTypes.string,
  onSubmit: PropTypes.func,
  onCancel: PropTypes.func,
  onModify: PropTypes.func,
  initialData: PropTypes.object,
  className: PropTypes.string
};

FormCardBubble.defaultProps = {
  sender: 'agent',
  timestamp: null,
  initialData: {},
  className: '',
  onSubmit: () => {},
  onCancel: () => {},
  onModify: () => {}
};

export default FormCardBubble;

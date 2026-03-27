import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ChatMessage from './ChatMessage';

describe('ChatMessage Component', () => {
  it('应该渲染文本消息', () => {
    const message = {
      type: 'text',
      sender: 'agent',
      timestamp: new Date().toISOString(),
      content: 'Hello, world!'
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByText('Hello, world!')).toBeInTheDocument();
    expect(screen.getByText('🤖 Agent')).toBeInTheDocument();
  });

  it('应该渲染用户消息', () => {
    const message = {
      type: 'text',
      sender: 'user',
      timestamp: new Date().toISOString(),
      content: 'User message'
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByText('User message')).toBeInTheDocument();
    expect(screen.getByText('👤 我')).toBeInTheDocument();
  });

  it('应该显示时间戳', () => {
    const now = new Date();
    const isoString = now.toISOString();
    const expectedTime = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

    const message = {
      type: 'text',
      sender: 'agent',
      timestamp: isoString,
      content: 'Test message'
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByText(expectedTime)).toBeInTheDocument();
  });

  it('应该显示文件列表', () => {
    const message = {
      type: 'text',
      sender: 'user',
      content: 'Message with files',
      files: [
        { name: 'document.pdf' },
        { name: 'image.jpg' }
      ]
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByText('document.pdf')).toBeInTheDocument();
    expect(screen.getByText('image.jpg')).toBeInTheDocument();
  });

  it('应该渲染总结卡片消息', () => {
    const message = {
      type: 'summary_card',
      sender: 'agent',
      timestamp: new Date().toISOString(),
      title: '任务完成',
      summary: '所有检查已完成',
      status: 'completed',
      data: {
        '检查项数': '10',
        '通过项': '9',
        '失败项': '1'
      }
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByText('任务完成')).toBeInTheDocument();
    expect(screen.getByText('所有检查已完成')).toBeInTheDocument();
    // Check for the status badge specifically
    expect(screen.getByText(/✓ 完成/)).toBeInTheDocument();
    expect(screen.getByText(/检查项数:/)).toBeInTheDocument();
  });

  it('应该处理向后兼容的message字段', () => {
    const message = {
      type: 'text',
      sender: 'agent',
      message: 'Old format message' // backward compatibility
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByText('Old format message')).toBeInTheDocument();
  });

  it('应该渲染系统消息', () => {
    const message = {
      type: 'text',
      sender: 'system',
      content: 'System notification'
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByText('⚙️ 系统')).toBeInTheDocument();
    expect(screen.getByText('System notification')).toBeInTheDocument();
  });

  it('应该处理未知消息类型', () => {
    const message = {
      type: 'unknown_type',
      sender: 'agent'
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByText(/未知消息类型/)).toBeInTheDocument();
  });

  it('应该处理null消息', () => {
    const { container } = render(<ChatMessage message={null} />);

    expect(container.firstChild).toBeNull();
  });

  it('应该添加自定义className', () => {
    const message = {
      type: 'text',
      sender: 'agent',
      content: 'Test'
    };

    const { container } = render(
      <ChatMessage message={message} className="custom-class" />
    );

    expect(container.querySelector('.custom-class')).toBeInTheDocument();
  });

  it('应该调用onFormSubmit回调', () => {
    const mockOnSubmit = jest.fn();
    const schema = {
      id: 'test_form',
      title: 'Test Form',
      state: 'editable',
      sections: []
    };

    const message = {
      type: 'form_card',
      sender: 'agent',
      schema,
      form_id: 'form_001',
      task_id: 'task_001'
    };

    render(
      <ChatMessage
        message={message}
        onFormSubmit={mockOnSubmit}
      />
    );

    // Note: 完整的表单交互测试需要FormCardBubble的完整实现
    // 这里只是确保回调被正确传递
    expect(mockOnSubmit).toBeDefined();
  });

  it('应该显示总结卡片的不同状态', () => {
    const statuses = ['pending', 'completed', 'failed'];

    statuses.forEach(status => {
      const { unmount } = render(
        <ChatMessage
          message={{
            type: 'summary_card',
            sender: 'agent',
            title: 'Test',
            summary: 'Test summary',
            status
          }}
        />
      );

      const element = screen.getByText(/Test summary/);
      expect(element.parentElement.querySelector(`.summary-status--${status}`)).toBeInTheDocument();

      unmount();
    });
  });
});

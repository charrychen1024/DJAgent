import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import ChatInput from './ChatInput';

describe('ChatInput Component', () => {
  it('应该渲染输入框', () => {
    render(<ChatInput />);

    const textarea = screen.getByPlaceholderText(/输入消息/);
    expect(textarea).toBeInTheDocument();
  });

  it('应该在输入时更新值', async () => {
    const onChange = jest.fn();
    render(<ChatInput value="" onChange={onChange} />);

    const textarea = screen.getByPlaceholderText(/输入消息/);
    await userEvent.type(textarea, 'H');

    // Check that onChange was called at least once
    expect(onChange).toHaveBeenCalled();
    // The last call should have 'H'
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1];
    expect(lastCall[0]).toBe('H');
  });

  it('应该显示发送按钮', () => {
    render(<ChatInput />);

    const sendButton = screen.getByLabelText('Send message');
    expect(sendButton).toBeInTheDocument();
  });

  it('应该在没有文本时禁用发送按钮', () => {
    render(<ChatInput value="" files={[]} />);

    const sendButton = screen.getByLabelText('Send message');
    expect(sendButton).toBeDisabled();
  });

  it('应该在有文本时启用发送按钮', () => {
    render(<ChatInput value="Hello" files={[]} />);

    const sendButton = screen.getByLabelText('Send message');
    expect(sendButton).not.toBeDisabled();
  });

  it('应该在点击发送按钮时调用onSend', () => {
    const onSend = jest.fn();
    render(<ChatInput value="Hello" onSend={onSend} />);

    const sendButton = screen.getByLabelText('Send message');
    fireEvent.click(sendButton);

    expect(onSend).toHaveBeenCalled();
  });

  it('应该在按Enter时发送消息', async () => {
    const onSend = jest.fn();
    render(<ChatInput value="Hello" onSend={onSend} />);

    const textarea = screen.getByPlaceholderText(/输入消息/);
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

    expect(onSend).toHaveBeenCalled();
  });

  it('应该在按Shift+Enter时不发送消息', async () => {
    const onSend = jest.fn();
    render(<ChatInput value="Hello" onSend={onSend} />);

    const textarea = screen.getByPlaceholderText(/输入消息/);
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });

    expect(onSend).not.toHaveBeenCalled();
  });

  it('应该显示文件列表', () => {
    const files = [
      { name: 'document.pdf' },
      { name: 'image.jpg' }
    ];

    render(<ChatInput files={files} />);

    expect(screen.getByText('document.pdf')).toBeInTheDocument();
    expect(screen.getByText('image.jpg')).toBeInTheDocument();
  });

  it('应该在移除文件时调用onFileRemove', () => {
    const onFileRemove = jest.fn();
    const files = [{ name: 'test.pdf' }];

    render(<ChatInput files={files} onFileRemove={onFileRemove} />);

    const removeButton = screen.getByLabelText('Remove test.pdf');
    fireEvent.click(removeButton);

    expect(onFileRemove).toHaveBeenCalledWith(files[0]);
  });

  it('应该禁用输入框当disabled为真', () => {
    render(<ChatInput disabled={true} />);

    const textarea = screen.getByPlaceholderText(/输入消息/);
    expect(textarea).toBeDisabled();
  });

  it('应该显示加载状态', () => {
    render(<ChatInput loading={true} />);

    const sendButton = screen.getByLabelText('Send message');
    expect(sendButton).toBeInTheDocument();
    expect(sendButton).toHaveTextContent('⏳');
  });

  it('应该在有文件时启用发送按钮', () => {
    const files = [{ name: 'test.pdf' }];
    render(<ChatInput value="" files={files} />);

    const sendButton = screen.getByLabelText('Send message');
    expect(sendButton).not.toBeDisabled();
  });

  it('应该显示文件上传按钮', () => {
    render(<ChatInput />);

    const uploadButton = screen.getByLabelText('Upload file');
    expect(uploadButton).toBeInTheDocument();
  });

  it('应该处理文件选择', () => {
    const onFileSelect = jest.fn();
    const file = new File(['content'], 'test.txt', { type: 'text/plain' });

    render(<ChatInput onFileSelect={onFileSelect} />);

    const input = screen.getByLabelText('Select files');
    fireEvent.change(input, { target: { files: [file] } });

    expect(onFileSelect).toHaveBeenCalled();
  });

  it('应该显示字符数', () => {
    render(<ChatInput value="Hello world!" />);

    expect(screen.getByText('12')).toBeInTheDocument();
  });

  it('应该不显示字符数当输入为空', () => {
    render(<ChatInput value="" />);

    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });

  it('应该显示helper文本', () => {
    const files = [{ name: 'test.pdf' }];
    render(<ChatInput files={files} />);

    expect(screen.getByText(/已选择 1 个文件/)).toBeInTheDocument();
  });

  it('应该处理自定义placeholder', () => {
    render(<ChatInput placeholder="Custom placeholder" />);

    expect(screen.getByPlaceholderText('Custom placeholder')).toBeInTheDocument();
  });

  it('应该在有文件时不禁用文件上传', () => {
    const files = [{ name: 'test.pdf' }];
    render(<ChatInput files={files} />);

    const uploadButton = screen.getByLabelText('Upload file');
    expect(uploadButton).not.toBeDisabled();
  });

  it('应该在loading时禁用操作', () => {
    render(<ChatInput loading={true} />);

    const uploadButton = screen.getByLabelText('Upload file');
    expect(uploadButton).toBeDisabled();
  });
});

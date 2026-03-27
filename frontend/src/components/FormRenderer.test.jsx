import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import FormRenderer from './FormRenderer';

describe('FormRenderer Component', () => {
  const mockSchema = {
    id: 'test_form',
    title: '测试表单',
    description: '这是一个测试表单',
    state: 'editable',
    sections: [
      {
        id: 'section1',
        title: '基本信息',
        fields: [
          {
            id: 'name',
            type: 'text',
            label: '姓名',
            placeholder: '请输入姓名',
            required: true,
            minLength: 2,
            maxLength: 50
          },
          {
            id: 'email',
            type: 'email',
            label: '邮箱',
            required: true
          },
          {
            id: 'description',
            type: 'textarea',
            label: '描述',
            minLength: 10,
            maxLength: 500,
            required: true
          }
        ]
      },
      {
        id: 'section2',
        title: '选择项',
        fields: [
          {
            id: 'category',
            type: 'select',
            label: '分类',
            required: true,
            options: [
              { value: 'A', label: '分类A' },
              { value: 'B', label: '分类B' }
            ]
          }
        ]
      }
    ]
  };

  const mockReadonlySchema = {
    ...mockSchema,
    state: 'readonly'
  };

  it('应该正确渲染表单标题和描述', () => {
    render(
      <FormRenderer
        schema={mockSchema}
        onSubmit={jest.fn()}
      />
    );

    expect(screen.getByText('测试表单')).toBeInTheDocument();
    expect(screen.getByText('这是一个测试表单')).toBeInTheDocument();
  });

  it('应该正确渲染所有的字段', () => {
    render(
      <FormRenderer
        schema={mockSchema}
        onSubmit={jest.fn()}
      />
    );

    expect(screen.getByLabelText('姓名')).toBeInTheDocument();
    expect(screen.getByLabelText('邮箱')).toBeInTheDocument();
    expect(screen.getByLabelText('描述')).toBeInTheDocument();
    expect(screen.getByLabelText('分类')).toBeInTheDocument();
  });

  it('应该显示必填项标记', () => {
    render(
      <FormRenderer
        schema={mockSchema}
        onSubmit={jest.fn()}
      />
    );

    const requiredMarks = screen.getAllByText('*');
    expect(requiredMarks.length).toBeGreaterThan(0);
  });

  it('应该在空表单提交时显示错误', async () => {
    const onSubmit = jest.fn();
    render(
      <FormRenderer
        schema={mockSchema}
        onSubmit={onSubmit}
      />
    );

    const submitButton = screen.getByText('提交');
    fireEvent.click(submitButton);

    // 模拟确认对话框
    window.confirm = jest.fn(() => true);

    await waitFor(() => {
      expect(onSubmit).not.toHaveBeenCalled();
    });
  });

  it('应该在编辑状态显示提交按钮', () => {
    render(
      <FormRenderer
        schema={mockSchema}
        onSubmit={jest.fn()}
      />
    );

    expect(screen.getByText('提交')).toBeInTheDocument();
    expect(screen.getByText('取消')).toBeInTheDocument();
  });

  it('应该在只读状态显示修改按钮', () => {
    render(
      <FormRenderer
        schema={mockReadonlySchema}
        onSubmit={jest.fn()}
      />
    );

    expect(screen.getByText('修改')).toBeInTheDocument();
    expect(screen.queryByText('提交')).not.toBeInTheDocument();
  });

  it('应该在取消时调用 onCancel 回调', async () => {
    const onCancel = jest.fn();
    render(
      <FormRenderer
        schema={mockSchema}
        onCancel={onCancel}
        showConfirmation={false}
      />
    );

    const cancelButton = screen.getByText('取消');
    fireEvent.click(cancelButton);

    await waitFor(() => {
      expect(onCancel).toHaveBeenCalled();
    });
  });

  it('应该验证邮箱格式', async () => {
    render(
      <FormRenderer
        schema={mockSchema}
        onSubmit={jest.fn()}
      />
    );

    const nameInput = screen.getByLabelText('姓名');
    const emailInput = screen.getByLabelText('邮箱');
    const descriptionInput = screen.getByLabelText('描述');
    const categorySelect = screen.getByLabelText('分类');

    // 输入有效数据
    fireEvent.change(nameInput, { target: { value: '张三' } });
    fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
    fireEvent.change(descriptionInput, { target: { value: '这是一个测试的描述信息' } });
    fireEvent.change(categorySelect, { target: { value: 'A' } });

    // Blur to trigger validation
    fireEvent.blur(emailInput);

    await waitFor(() => {
      expect(screen.getByText(/邮箱必须是有效的邮箱/)).toBeInTheDocument();
    });
  });

  it('应该验证最小长度', async () => {
    render(
      <FormRenderer
        schema={mockSchema}
        onSubmit={jest.fn()}
      />
    );

    const descriptionInput = screen.getByLabelText('描述');

    fireEvent.change(descriptionInput, { target: { value: '短' } });
    fireEvent.blur(descriptionInput);

    await waitFor(() => {
      expect(screen.getByText(/描述最少需要 10 个字符/)).toBeInTheDocument();
    });
  });

  it('应该通过有效数据提交表单', async () => {
    const onSubmit = jest.fn();
    render(
      <FormRenderer
        schema={mockSchema}
        onSubmit={onSubmit}
        showConfirmation={false}
      />
    );

    const nameInput = screen.getByLabelText('姓名');
    const emailInput = screen.getByLabelText('邮箱');
    const descriptionInput = screen.getByLabelText('描述');
    const categorySelect = screen.getByLabelText('分类');

    fireEvent.change(nameInput, { target: { value: '张三' } });
    fireEvent.change(emailInput, { target: { value: 'zhangsan@example.com' } });
    fireEvent.change(descriptionInput, { target: { value: '这是一个很长的描述信息，满足最小长度要求' } });
    fireEvent.change(categorySelect, { target: { value: 'A' } });

    const submitButton = screen.getByText('提交');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        name: '张三',
        email: 'zhangsan@example.com',
        description: '这是一个很长的描述信息，满足最小长度要求',
        category: 'A'
      });
    });
  });

  it('应该正确处理初始数据', () => {
    const initialData = {
      name: '初始名字',
      email: 'initial@example.com'
    };

    render(
      <FormRenderer
        schema={mockSchema}
        onSubmit={jest.fn()}
        initialData={initialData}
      />
    );

    expect(screen.getByDisplayValue('初始名字')).toBeInTheDocument();
    expect(screen.getByDisplayValue('initial@example.com')).toBeInTheDocument();
  });
});

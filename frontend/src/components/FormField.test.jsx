import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import FormField from './FormField';

describe('FormField Component', () => {
  it('应该渲染文本输入字段', () => {
    const field = {
      id: 'name',
      type: 'text',
      label: '姓名',
      placeholder: '请输入姓名'
    };

    render(
      <FormField
        field={field}
        value=""
        onChange={jest.fn()}
      />
    );

    expect(screen.getByLabelText('姓名')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('请输入姓名')).toBeInTheDocument();
  });

  it('应该渲染邮箱输入字段', () => {
    const field = {
      id: 'email',
      type: 'email',
      label: '邮箱',
      required: true
    };

    render(
      <FormField
        field={field}
        value=""
        onChange={jest.fn()}
      />
    );

    expect(screen.getByLabelText(/邮箱/)).toBeInTheDocument();
    expect(screen.getByText('*')).toBeInTheDocument(); // Required mark
  });

  it('应该渲染textarea字段', () => {
    const field = {
      id: 'description',
      type: 'textarea',
      label: '描述',
      maxLength: 500
    };

    render(
      <FormField
        field={field}
        value=""
        onChange={jest.fn()}
      />
    );

    const textarea = screen.getByLabelText('描述');
    expect(textarea.tagName).toBe('TEXTAREA');
    expect(textarea).toHaveAttribute('maxlength', '500');
  });

  it('应该渲染select下拉列表', () => {
    const field = {
      id: 'category',
      type: 'select',
      label: '分类',
      options: [
        { value: 'A', label: '分类A' },
        { value: 'B', label: '分类B' }
      ]
    };

    render(
      <FormField
        field={field}
        value=""
        onChange={jest.fn()}
      />
    );

    expect(screen.getByLabelText('分类')).toBeInTheDocument();
    expect(screen.getByText('分类A')).toBeInTheDocument();
    expect(screen.getByText('分类B')).toBeInTheDocument();
  });

  it('应该渲染radio单选按钮', () => {
    const field = {
      id: 'option',
      type: 'radio',
      label: '选项',
      options: [
        { value: '1', label: '选项1' },
        { value: '2', label: '选项2' }
      ]
    };

    render(
      <FormField
        field={field}
        value=""
        onChange={jest.fn()}
      />
    );

    const radios = screen.getAllByRole('radio');
    expect(radios.length).toBe(2);
  });

  it('应该渲染checkbox多选框', () => {
    const field = {
      id: 'checkbox',
      type: 'checkbox',
      label: '多选',
      options: [
        { value: '1', label: '选项1' },
        { value: '2', label: '选项2' }
      ]
    };

    render(
      <FormField
        field={field}
        value={[]}
        onChange={jest.fn()}
      />
    );

    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes.length).toBe(2);
  });

  it('应该渲染number数字输入', () => {
    const field = {
      id: 'count',
      type: 'number',
      label: '数量',
      min: 1,
      max: 100
    };

    render(
      <FormField
        field={field}
        value=""
        onChange={jest.fn()}
      />
    );

    const input = screen.getByLabelText('数量');
    expect(input).toHaveAttribute('type', 'number');
    expect(input).toHaveAttribute('min', '1');
    expect(input).toHaveAttribute('max', '100');
  });

  it('应该显示帮助文本', () => {
    const field = {
      id: 'email',
      type: 'email',
      label: '邮箱',
      helpText: '请输入有效的邮箱地址'
    };

    render(
      <FormField
        field={field}
        value=""
        onChange={jest.fn()}
      />
    );

    expect(screen.getByText('请输入有效的邮箱地址')).toBeInTheDocument();
  });

  it('应该显示错误信息', () => {
    const field = {
      id: 'name',
      type: 'text',
      label: '姓名'
    };

    render(
      <FormField
        field={field}
        value=""
        error="姓名为必填项"
        touched={true}
        onChange={jest.fn()}
      />
    );

    expect(screen.getByText('姓名为必填项')).toBeInTheDocument();
  });

  it('应该当disabled时禁用输入', () => {
    const field = {
      id: 'name',
      type: 'text',
      label: '姓名'
    };

    render(
      <FormField
        field={field}
        value=""
        disabled={true}
        onChange={jest.fn()}
      />
    );

    const input = screen.getByLabelText('姓名');
    expect(input).toBeDisabled();
  });

  it('应该在值改变时调用onChange', () => {
    const onChange = jest.fn();
    const field = {
      id: 'name',
      type: 'text',
      label: '姓名'
    };

    render(
      <FormField
        field={field}
        value=""
        onChange={onChange}
      />
    );

    const input = screen.getByLabelText('姓名');
    fireEvent.change(input, { target: { value: '张三' } });

    expect(onChange).toHaveBeenCalledWith('张三');
  });

  it('应该在blur时调用onBlur', () => {
    const onBlur = jest.fn();
    const field = {
      id: 'name',
      type: 'text',
      label: '姓名'
    };

    render(
      <FormField
        field={field}
        value=""
        onChange={jest.fn()}
        onBlur={onBlur}
      />
    );

    const input = screen.getByLabelText('姓名');
    fireEvent.blur(input);

    expect(onBlur).toHaveBeenCalled();
  });

  it('应该渲染文件上传字段', () => {
    const field = {
      id: 'file',
      type: 'file_upload',
      label: '上传文件',
      accept: 'image/*',
      maxSize: 5000000
    };

    render(
      <FormField
        field={field}
        value=""
        onChange={jest.fn()}
      />
    );

    expect(screen.getByLabelText('上传文件')).toBeInTheDocument();
    expect(screen.getByText(/选择文件/)).toBeInTheDocument();
  });

  it('应该不显示只读字段的错误信息', () => {
    const field = {
      id: 'name',
      type: 'text',
      label: '姓名'
    };

    render(
      <FormField
        field={field}
        value="张三"
        error="某个错误"
        touched={false}
        onChange={jest.fn()}
      />
    );

    expect(screen.queryByText('某个错误')).not.toBeInTheDocument();
  });
});

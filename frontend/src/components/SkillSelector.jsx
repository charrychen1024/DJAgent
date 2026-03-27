import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import './SkillSelector.css';

/**
 * SkillSelector 下拉框组件
 *
 * 功能：
 * - 显示紧凑的 Skill 下拉菜单
 * - 紧挨着按钮，类似传统下拉框
 * - 支持搜索和过滤
 * - 快速选择
 *
 * @component
 * @param {Object} props
 * @param {boolean} props.visible - 下拉框是否显示
 * @param {Function} props.onClose - 关闭下拉框回调
 * @param {Function} props.onSelect - 选择 Skill 回调
 * @param {HTMLElement} props.anchorEl - 锚点元素（定位参考）
 * @param {string} props.userRole - 用户角色（manager/staff）
 */
const SkillSelector = ({ visible, onClose, onSelect, anchorEl, userRole = 'manager' }) => {
  const [skills, setSkills] = useState([]);
  const [filteredSkills, setFilteredSkills] = useState([]);
  const [searchText, setSearchText] = useState('');
  const [loading, setLoading] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [actualHeight, setActualHeight] = useState(0);
  const [finalPosition, setFinalPosition] = useState({ top: 0, left: 0, width: 0 });
  const dropdownRef = useRef(null);
  const searchInputRef = useRef(null);

  // 获取 Skill 列表
  useEffect(() => {
    if (!visible) return;

    const fetchSkills = async () => {
      setLoading(true);
      try {
        const response = await fetch('/api/skills');
        if (!response.ok) throw new Error('获取 Skill 列表失败');
        const data = await response.json();

        // 根据用户角色过滤
        let filtered = data.skills || [];
        if (userRole === 'staff') {
          filtered = filtered.filter(s => s.available_for_staff !== false);
        } else if (userRole === 'manager') {
          filtered = filtered.filter(s => s.available_for_manager !== false);
        }

        setSkills(filtered);
        setFilteredSkills(filtered);
        setHighlightedIndex(-1);
        setSearchText('');
      } catch (err) {
        console.error('获取 Skill 列表错误:', err);
        setSkills([]);
        setFilteredSkills([]);
      } finally {
        setLoading(false);
      }
    };

    fetchSkills();
  }, [visible, userRole]);

  // 搜索和过滤
  useEffect(() => {
    if (!searchText.trim()) {
      setFilteredSkills(skills);
    } else {
      const keyword = searchText.toLowerCase();
      const filtered = skills.filter(skill =>
        skill.name.toLowerCase().includes(keyword) ||
        skill.description.toLowerCase().includes(keyword)
      );
      setFilteredSkills(filtered);
    }
    setHighlightedIndex(-1);
  }, [searchText, skills]);

  // 测量实际高度并重新定位（简化版 - 在 DOM 完全渲染后立即定位）
  useEffect(() => {
    if (!visible || !anchorEl || !dropdownRef.current) return;

    // 立即保存按钮位置（在 dropdown 渲染之前）
    const rect = anchorEl.getBoundingClientRect();
    console.log(`[SkillSelector] 保存按钮位置: top=${rect.top}, bottom=${rect.bottom}`);

    // 使用一个 timeout 确保 DOM 已完全渲染
    const timerId = setTimeout(() => {
      const dropdown = dropdownRef.current;

      if (!dropdown) return;

      const ddHeight = dropdown.clientHeight;

      if (ddHeight === 0) {
        // 尚未渲染，重试
        return;
      }

      console.log(`[SkillSelector] 定位: height=${ddHeight}, button.top=${rect.top}`);

      const VIEWPORT_MARGIN = 10;
      const spaceBelow = window.innerHeight - rect.bottom;
      const spaceAbove = rect.top;

      let top;

      if (spaceBelow >= ddHeight + VIEWPORT_MARGIN) {
        top = rect.bottom;
        console.log(`[SkillSelector] 显示在下方: top=${top}`);
      } else if (spaceAbove >= ddHeight + VIEWPORT_MARGIN) {
        top = rect.top - ddHeight;
        console.log(`[SkillSelector] 显示在上方: top=${top}`);
      } else {
        top = Math.max(
          VIEWPORT_MARGIN,
          window.innerHeight - ddHeight - VIEWPORT_MARGIN
        );
        console.log(`[SkillSelector] 空间受限: top=${top}`);
      }

      setFinalPosition({
        top,
        left: rect.left,
        width: rect.width
      });

      setActualHeight(ddHeight);
    }, 50);  // 50ms 延迟确保 DOM 渲染完成

    return () => clearTimeout(timerId);
  }, [visible, anchorEl]);

  // 重置高度和位置（当 visible 变为 false）
  useEffect(() => {
    if (!visible) {
      setActualHeight(0);
      setFinalPosition({ top: 0, left: 0, width: 0 });
    }
  }, [visible]);

  // 处理键盘导航
  const handleKeyDown = (e) => {
    if (!visible) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex(prev =>
          prev < filteredSkills.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex(prev => (prev > 0 ? prev - 1 : -1));
        break;
      case 'Enter':
        e.preventDefault();
        if (highlightedIndex >= 0 && highlightedIndex < filteredSkills.length) {
          handleSelectSkill(filteredSkills[highlightedIndex]);
        }
        break;
      case 'Escape':
        e.preventDefault();
        onClose?.();
        break;
      default:
        break;
    }
  };

  // 处理 Skill 选择
  const handleSelectSkill = (skill) => {
    const insertText = `使用${skill.name}技能`;
    onSelect?.(skill, insertText);
    onClose?.();
  };

  // 点击外部关闭（改进版 - 直接在 document 上监听）
  useEffect(() => {
    if (!visible) return;

    const handleClickOutside = (e) => {
      // 检查点击是否在 dropdown 或 anchorEl 外部
      const isClickInDropdown = dropdownRef.current && dropdownRef.current.contains(e.target);
      const isClickInAnchor = anchorEl && anchorEl.contains(e.target);

      if (!isClickInDropdown && !isClickInAnchor) {
        console.log('[SkillSelector] 点击外部，关闭dropdown');
        onClose?.();
      }
    };

    // 使用 'mousedown' 而不是 'click'，这样可以更早捕获
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [visible, onClose, anchorEl]);

  // 自动聚焦搜索框
  useEffect(() => {
    if (visible && searchInputRef.current) {
      setTimeout(() => searchInputRef.current?.focus(), 100);
    }
  }, [visible]);

  if (!visible || !anchorEl) return null;

  return (
    <div
      ref={dropdownRef}
      className="skill-selector-dropdown"
      style={{
        top: `${finalPosition.top}px`,
        left: `${finalPosition.left}px`,
        minWidth: `${finalPosition.width}px`,
        opacity: actualHeight > 0 ? 1 : 0, // 隐藏直到高度测量完成
        pointerEvents: actualHeight > 0 ? 'auto' : 'none', // 禁用交互直到渲染完成
        transition: 'opacity 0.15s ease-out'
      }}
      onKeyDown={handleKeyDown}
    >
      {/* 搜索框 */}
      <div className="skill-dropdown-search">
        <input
          ref={searchInputRef}
          type="text"
          placeholder="搜索..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          className="skill-dropdown-input"
          onKeyDown={handleKeyDown}
        />
      </div>

      {/* 下拉列表 */}
      <div className="skill-dropdown-list">
        {loading && (
          <div className="skill-dropdown-empty">
            <span>加载中...</span>
          </div>
        )}

        {!loading && filteredSkills.length === 0 && (
          <div className="skill-dropdown-empty">
            <span>{skills.length === 0 ? '暂无Skill' : '无匹配'}</span>
          </div>
        )}

        {filteredSkills.map((skill, index) => (
          <div
            key={skill.name}
            className={`skill-dropdown-item ${highlightedIndex === index ? 'skill-dropdown-item--highlighted' : ''}`}
            onClick={() => handleSelectSkill(skill)}
            onMouseEnter={() => setHighlightedIndex(index)}
          >
            <div className="skill-item-name">{skill.name}</div>
            <div className="skill-item-desc">{skill.description}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

SkillSelector.propTypes = {
  visible: PropTypes.bool,
  onClose: PropTypes.func,
  onSelect: PropTypes.func,
  anchorEl: PropTypes.instanceOf(Element),
  userRole: PropTypes.oneOf(['manager', 'staff'])
};

SkillSelector.defaultProps = {
  visible: false,
  onClose: () => {},
  onSelect: () => {},
  anchorEl: null,
  userRole: 'manager'
};

export default SkillSelector;

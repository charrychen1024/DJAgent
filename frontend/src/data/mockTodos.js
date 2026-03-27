/**
 * Mock 待办项数据 - 20个示例
 * 来自 TODOIST_FEATURE_DESIGN.md 文档第 8.1 章
 */

export const mockTodos = [
  // ========== 运单数据问题 (12个) ==========
  {
    id: 'TODO-2026-001',
    title: '运单WLYD9585102时间异常核查 - 高风险',
    description: '运单时间逻辑混乱：揽收时间2026-12-24（未来时间）早于发货时间2025-09-09一年多，签收时间2025-02-11早于发货时间。货物：电子产品，重量1307kg，客户：王静贸易公司，地区：上海区。需紧急确认真实运单信息。',
    category: '运单数据问题',
    type: '时间异常',
    priority: 'P0',
    status: '未处理',
    severity: 'critical',
    source_data: {
      date: '2026-03-25',
      region: '华南',
      metrics: { import: 10000, export: 15000, span_percentage: 150 }
    },
    analysis: {
      trend: '上升趋势明显，需关注',
      change_rate: '150%',
      affected_items: 5,
      root_cause: '出口订单增加，进口原料减少'
    },
    recommended_assignee: {
      user_id: 'user_002',
      name: '王经理',
      reason: '华南地区负责人，具有数据核查权限'
    },
    expected_handling_time: {
      start_date: '2026-03-26',
      due_date: '2026-03-27',
      priority_hours: 24
    },
    metadata: {
      created_at: '2026-03-26T09:30:00Z',
      created_by: 'system',
      updated_at: '2026-03-26T09:30:00Z',
      related_task_ids: [],
      related_chat_messages: []
    }
  },
  {
    id: 'TODO-2026-009',
    title: '浙江地区风险评分异常',
    description: '浙江地区风险评分突增至 92 分，涉及进出口和库存两个维度',
    category: '运单数据问题',
    type: '评分异常',
    priority: 'P0',
    status: '未处理',
    severity: 'critical',
    source_data: {
      date: '2026-03-25',
      region: '浙江',
      risk_score: 92,
      previous_score: 58,
      change: 34
    },
    analysis: {
      contributing_factors: {
        进出口风险: 95,
        库存风险: 88,
        市场风险: 65
      },
      root_cause: '大订单取消，库存积压，进口延迟'
    },
    recommended_assignee: {
      user_id: 'user_006',
      name: '孙浙江负责人',
      reason: '浙江地区负责人，最了解当地情况'
    },
    expected_handling_time: {
      start_date: '2026-03-26',
      due_date: '2026-03-27',
      priority_hours: 24
    },
    metadata: {
      created_at: '2026-03-26T10:15:00Z',
      created_by: 'system',
      updated_at: '2026-03-26T10:15:00Z',
      related_task_ids: [],
      related_chat_messages: []
    }
  },
  {
    id: 'TODO-2026-015',
    title: '上海地区评分异常预警',
    description: '上海地区评分达 88 分，涉及多维度风险，需深入分析',
    category: '运单数据问题',
    type: '评分异常',
    priority: 'P0',
    status: '未处理',
    severity: 'critical',
    source_data: {
      date: '2026-03-25',
      region: '上海',
      risk_score: 88,
      previous_score: 62,
      change: 26
    },
    analysis: {
      multi_dimension_risk: {
        进出口: 90,
        库存: 85,
        融资: 92,
        物流: 75
      },
      critical_factors: ['融资成本上升', '库存压力大', '出口不确定性增加']
    },
    recommended_assignee: {
      user_id: 'user_001',
      name: '张总经理',
      reason: '总经理，需对集团战略做出反应'
    },
    expected_handling_time: {
      start_date: '2026-03-26',
      due_date: '2026-03-27',
      priority_hours: 18
    },
    metadata: {
      created_at: '2026-03-26T08:30:00Z',
      created_by: 'system',
      updated_at: '2026-03-26T08:30:00Z',
      related_task_ids: [],
      related_chat_messages: []
    }
  },
  {
    id: 'TODO-2026-002',
    title: '华东地区缺少 2026-03-25 数据',
    description: '华东地区风险数据未按时上报，距预期时间已超 4 小时',
    category: '运单数据问题',
    type: '缺数据',
    priority: 'P1',
    status: '未处理',
    severity: 'high',
    source_data: {
      date: '2026-03-25',
      region: '华东',
      expected_time: '2026-03-26T08:00:00Z',
      actual_time: null
    },
    analysis: {
      trend: '延迟上报，可能系统故障或人员问题',
      expected_items: 50,
      received_items: 0,
      root_cause: '待确认'
    },
    recommended_assignee: {
      user_id: 'user_003',
      name: '李数据',
      reason: '数据管理员，负责数据导入'
    },
    expected_handling_time: {
      start_date: '2026-03-26',
      due_date: '2026-03-26',
      priority_hours: 2
    },
    metadata: {
      created_at: '2026-03-26T12:15:00Z',
      created_by: 'system',
      updated_at: '2026-03-26T12:15:00Z',
      related_task_ids: [],
      related_chat_messages: []
    }
  },
  {
    id: 'TODO-2026-003',
    title: '华北地区评分异常预警',
    description: '风险评分 87 分，较历史平均值高 35 分，建议重点关注',
    category: '运单数据问题',
    type: '评分异常',
    priority: 'P1',
    status: '未处理',
    severity: 'high',
    source_data: {
      date: '2026-03-25',
      region: '华北',
      risk_score: 87,
      historical_avg: 52,
      threshold: 70
    },
    analysis: {
      trend: '风险评分大幅上升，需深入分析原因',
      top_risk_factors: ['进出口异常', '库存堆积'],
      recommendation: '建议立即启动风险应对方案'
    },
    recommended_assignee: {
      user_id: 'user_001',
      name: '张总经理',
      reason: '总经理，负责全局风险评估'
    },
    expected_handling_time: {
      start_date: '2026-03-26',
      due_date: '2026-03-26',
      priority_hours: 4
    },
    metadata: {
      created_at: '2026-03-26T10:45:00Z',
      created_by: 'system',
      updated_at: '2026-03-26T10:45:00Z',
      related_task_ids: [],
      related_chat_messages: []
    }
  },
  {
    id: 'TODO-2026-010',
    title: '江苏地区进出口倍数异常',
    description: '进出口比例达 1:8，远超历史平均 1:2，需核实数据真实性',
    category: '运单数据问题',
    type: '跨度异常',
    priority: 'P1',
    status: '未处理',
    severity: 'high',
    source_data: {
      date: '2026-03-25',
      region: '江苏',
      import: 2000,
      export: 16000,
      ratio: '1:8',
      historical_avg_ratio: '1:2'
    },
    analysis: {
      trend: '出口激增，可能受新订单驱动',
      change_rate: '400%',
      data_quality: '需确认是否重复计算'
    },
    recommended_assignee: {
      user_id: 'user_007',
      name: '吴江苏负责人',
      reason: '江苏地区负责人，具有数据审核权限'
    },
    expected_handling_time: {
      start_date: '2026-03-26',
      due_date: '2026-03-27',
      priority_hours: 24
    },
    metadata: {
      created_at: '2026-03-26T11:30:00Z',
      created_by: 'system',
      updated_at: '2026-03-26T11:30:00Z',
      related_task_ids: [],
      related_chat_messages: []
    }
  },
  {
    id: 'TODO-2026-011',
    title: '福建地区库存数据缺失',
    description: '福建地区库存数据缺少 5 个关键指标（SKU 库存、成本、周转率），影响风险评估准确性',
    category: '运单数据问题',
    type: '缺数据',
    priority: 'P1',
    status: '未处理',
    severity: 'high',
    source_data: {
      date: '2026-03-25',
      region: '福建',
      missing_metrics: ['库存金额', '库存数量', '周转率', '滞销率', '成本占比'],
      expected_count: 10,
      received_count: 5
    },
    analysis: {
      impact: '无法准确评估库存风险，评分降低',
      last_received: '2026-03-24',
      trend: '持续缺失，需紧急处理'
    },
    recommended_assignee: {
      user_id: 'user_008',
      name: '郭福建负责人',
      reason: '福建地区负责人，负责数据完整性'
    },
    expected_handling_time: {
      start_date: '2026-03-26',
      due_date: '2026-03-26',
      priority_hours: 6
    },
    metadata: {
      created_at: '2026-03-26T12:40:00Z',
      created_by: 'system',
      updated_at: '2026-03-26T12:40:00Z',
      related_task_ids: [],
      related_chat_messages: []
    }
  },
  {
    id: 'TODO-2026-013',
    title: '广东地区风险评分预警',
    description: '广东地区风险评分升至 85 分，环比上升 18 分，重点关注出口业务',
    category: '运单数据问题',
    type: '评分异常',
    priority: 'P1',
    status: '未处理',
    severity: 'high',
    source_data: {
      date: '2026-03-25',
      region: '广东',
      risk_score: 85,
      previous_score: 67,
      change: 18
    },
    analysis: {
      main_driver: '出口订单取消率上升至 12%（历史 5%）',
      impact_range: '珠三角制造企业',
      recommendation: '主动联系大客户，了解需求变化'
    },
    recommended_assignee: {
      user_id: 'user_009',
      name: '陈广东负责人',
      reason: '广东地区负责人，掌握客户关系'
    },
    expected_handling_time: {
      start_date: '2026-03-26',
      due_date: '2026-03-27',
      priority_hours: 24
    },
    metadata: {
      created_at: '2026-03-26T09:00:00Z',
      created_by: 'system',
      updated_at: '2026-03-26T09:00:00Z',
      related_task_ids: [],
      related_chat_messages: []
    }
  },
  {
    id: 'TODO-2026-014',
    title: '山东地区缺少配套数据',
    description: '山东地区风险评分为 78，但配套的详细数据（物流、融资等）未更新',
    category: '运单数据问题',
    type: '缺数据',
    priority: 'P2',
    status: '未处理',
    severity: 'medium',
    source_data: {
      date: '2026-03-25',
      region: '山东',
      risk_score: 78,
      missing_detail_categories: ['物流风险', '融资风险', '供应链风险'],
      last_update: '2026-03-20'
    },
    analysis: {
      impact: '评分可能不准确，缺乏细节支撑',
      estimated_delay: '3-5 天数据滞后'
    },
    recommended_assignee: {
      user_id: 'user_010',
      name: '赵山东负责人',
      reason: '山东地区负责人'
    },
    expected_handling_time: {
      start_date: '2026-03-26',
      due_date: '2026-03-28',
      priority_hours: 48
    },
    metadata: {
      created_at: '2026-03-26T13:20:00Z',
      created_by: 'system',
      updated_at: '2026-03-26T13:20:00Z',
      related_task_ids: [],
      related_chat_messages: []
    }
  },

  // ========== 任务问题 (6个) ==========
  {
    id: 'TODO-2026-004',
    title: 'TASK-2026-123 已超期 48 小时',
    description: '任务"华中风险数据分析" 截止时间已过，当前状态仍为"进行中"',
    category: '任务问题',
    type: '任务超期',
    priority: 'P0',
    status: '未处理',
    severity: 'critical',
    source_data: {
      task_id: 'TASK-2026-123',
      task_title: '华中风险数据分析',
      deadline: '2026-03-24T17:00:00Z',
      current_time: '2026-03-26T14:00:00Z',
      overdue_hours: 45
    },
    analysis: {
      current_status: '进行中',
      progress: 40,
      assigned_to: '李经理',
      last_update: '2026-03-24T16:30:00Z'
    },
    recommended_assignee: {
      user_id: 'user_001',
      name: '张总经理',
      reason: '任务创建者，负责督促和协调'
    },
    expected_handling_time: {
      start_date: '2026-03-26',
      due_date: '2026-03-26',
      priority_hours: 1
    },
    metadata: {
      created_at: '2026-03-26T14:05:00Z',
      created_by: 'system',
      updated_at: '2026-03-26T14:05:00Z',
      related_task_ids: ['TASK-2026-123'],
      related_chat_messages: []
    }
  },
  {
    id: 'TODO-2026-005',
    title: 'TASK-2026-456 长期未更新（72 小时）',
    description: '任务"西南地区数据验证" 已 72 小时未有任何更新，需了解进展',
    category: '任务问题',
    type: '长期未更新',
    priority: 'P1',
    status: '未处理',
    severity: 'high',
    source_data: {
      task_id: 'TASK-2026-456',
      task_title: '西南地区数据验证',
      created_at: '2026-03-23T09:00:00Z',
      last_update: '2026-03-23T14:30:00Z',
      hours_since_update: 72
    },
    analysis: {
      current_status: '进行中',
      progress: 25,
      assigned_to: '王经理',
      possible_reasons: ['人员超负荷', '遇到技术困难', '优先级调整']
    },
    recommended_assignee: {
      user_id: 'user_002',
      name: '王经理',
      reason: '任务执行人，需主动汇报进展'
    },
    expected_handling_time: {
      start_date: '2026-03-26',
      due_date: '2026-03-26',
      priority_hours: 2
    },
    metadata: {
      created_at: '2026-03-26T11:20:00Z',
      created_by: 'system',
      updated_at: '2026-03-26T11:20:00Z',
      related_task_ids: ['TASK-2026-456'],
      related_chat_messages: []
    }
  },
  {
    id: 'TODO-2026-006',
    title: 'TASK-2026-789 进度缓慢预警',
    description: '任务"东南风险评估"已 96 小时，进度仅 15%，预期进度应为 60%+',
    category: '任务问题',
    type: '进度缓慢',
    priority: 'P2',
    status: '未处理',
    severity: 'medium',
    source_data: {
      task_id: 'TASK-2026-789',
      task_title: '东南风险评估',
      created_at: '2026-03-22T08:00:00Z',
      current_progress: 15,
      expected_progress: 60,
      assigned_to: '李经理'
    },
    analysis: {
      progress_gap: 45,
      average_rate: '6% per day',
      estimated_completion: '10 days',
      deadline: '2026-03-31',
      risk: '可能无法按时完成'
    },
    recommended_assignee: {
      user_id: 'user_001',
      name: '张总经理',
      reason: '评估是否需要调整资源或截止时间'
    },
    expected_handling_time: {
      start_date: '2026-03-26',
      due_date: '2026-03-28',
      priority_hours: 48
    },
    metadata: {
      created_at: '2026-03-26T09:50:00Z',
      created_by: 'system',
      updated_at: '2026-03-26T09:50:00Z',
      related_task_ids: ['TASK-2026-789'],
      related_chat_messages: []
    }
  },
  {
    id: 'TODO-2026-012',
    title: 'TASK-2026-999 已超期 24 小时',
    description: '任务"北京市场分析" 已超期，状态为"进行中"，当前进度 60%',
    category: '任务问题',
    type: '任务超期',
    priority: 'P1',
    status: '未处理',
    severity: 'high',
    source_data: {
      task_id: 'TASK-2026-999',
      task_title: '北京市场分析',
      deadline: '2026-03-25T17:00:00Z',
      current_time: '2026-03-26T14:00:00Z',
      overdue_hours: 21,
      progress: 60
    },
    analysis: {
      completion_estimate: '2-3 小时内可完成',
      blocker: '等待市场数据反馈',
      assigned_to: '王经理'
    },
    recommended_assignee: {
      user_id: 'user_001',
      name: '张总经理',
      reason: '了解延迟原因，是否可接受'
    },
    expected_handling_time: {
      start_date: '2026-03-26',
      due_date: '2026-03-26',
      priority_hours: 2
    },
    metadata: {
      created_at: '2026-03-26T14:10:00Z',
      created_by: 'system',
      updated_at: '2026-03-26T14:10:00Z',
      related_task_ids: ['TASK-2026-999'],
      related_chat_messages: []
    }
  },
  {
    id: 'TODO-2026-016',
    title: 'TASK-2026-555 进度停滞 48 小时',
    description: '任务"四川风险评估" 创建已 5 天，进度一直停留在 35%，最后更新在 2 天前',
    category: '任务问题',
    type: '长期未更新',
    priority: 'P1',
    status: '未处理',
    severity: 'high',
    source_data: {
      task_id: 'TASK-2026-555',
      task_title: '四川风险评估',
      created_at: '2026-03-21T09:00:00Z',
      current_progress: 35,
      last_update: '2026-03-24T10:30:00Z',
      hours_without_update: 52
    },
    analysis: {
      assigned_to: '李经理',
      deadline: '2026-03-28',
      days_remaining: 2,
      estimated_workload: '需要 5-6 天完成',
      risk: '严重延期风险'
    },
    recommended_assignee: {
      user_id: 'user_011',
      name: '周四川负责人',
      reason: '地区负责人，可提供现场支持'
    },
    expected_handling_time: {
      start_date: '2026-03-26',
      due_date: '2026-03-26',
      priority_hours: 4
    },
    metadata: {
      created_at: '2026-03-26T10:50:00Z',
      created_by: 'system',
      updated_at: '2026-03-26T10:50:00Z',
      related_task_ids: ['TASK-2026-555'],
      related_chat_messages: []
    }
  },
  {
    id: 'TODO-2026-018',
    title: 'TASK-2026-222 进度缓慢',
    description: '任务"海南消费者分析" 执行已 3 天，进度仅 10%，预计完成需 20 天，严重延期风险',
    category: '任务问题',
    type: '进度缓慢',
    priority: 'P2',
    status: '未处理',
    severity: 'medium',
    source_data: {
      task_id: 'TASK-2026-222',
      task_title: '海南消费者分析',
      created_at: '2026-03-23T14:00:00Z',
      current_progress: 10,
      expected_progress_by_today: 40,
      assigned_to: '高经理'
    },
    analysis: {
      completion_estimate_days: 20,
      deadline: '2026-03-31',
      days_remaining: 5,
      likelihood: '几乎无法按时完成'
    },
    recommended_assignee: {
      user_id: 'user_001',
      name: '张总经理',
      reason: '考虑是否需要延期或增加资源'
    },
    expected_handling_time: {
      start_date: '2026-03-26',
      due_date: '2026-03-27',
      priority_hours: 24
    },
    metadata: {
      created_at: '2026-03-26T09:40:00Z',
      created_by: 'system',
      updated_at: '2026-03-26T09:40:00Z',
      related_task_ids: ['TASK-2026-222'],
      related_chat_messages: []
    }
  },

  // ========== 异常问题 (2个) ==========
  {
    id: 'TODO-2026-007',
    title: '风险数据导入系统故障',
    description: '数据导入 API 返回 500 错误，影响华中、华东地区数据上传',
    category: '异常问题',
    type: '系统异常',
    priority: 'P0',
    status: '未处理',
    severity: 'critical',
    source_data: {
      error_code: 500,
      endpoint: '/api/risk-data/import',
      affected_regions: ['华中', '华东'],
      first_occurrence: '2026-03-26T13:45:00Z'
    },
    analysis: {
      service_status: '不可用',
      error_message: '数据库连接超时',
      impact: '无法导入新数据，影响数据完整性'
    },
    recommended_assignee: {
      user_id: 'user_004',
      name: '赵技术',
      reason: '系统管理员，负责基础设施维护'
    },
    expected_handling_time: {
      start_date: '2026-03-26',
      due_date: '2026-03-26',
      priority_hours: 1
    },
    metadata: {
      created_at: '2026-03-26T13:50:00Z',
      created_by: 'system',
      updated_at: '2026-03-26T13:50:00Z',
      related_task_ids: [],
      related_chat_messages: []
    }
  },
  {
    id: 'TODO-2026-020',
    title: '华东地区异常率突增 - 高风险',
    description: '华东地区本周异常率 12.5%，相比过去 4 周平均水平 (4.8%) 上升 7.7 个百分点 (增幅 160%)。高风险订单集中在运费异常和虚假签收两类，需分析根源并采取措施。',
    category: '异常问题',
    type: '地区风险指标异常',
    priority: 'P1',
    status: '未处理',
    severity: 'high',
    source_data: {
      region: '华东',
      week: '2026-03-26',
      current_abnormal_rate: 12.5,
      historical_avg_rate: 4.8,
      rate_increase: 7.7,
      increase_percentage: 160,
      high_risk_count: 58,
      abnormality_types: ['运费异常', '虚假签收', '货物损坏'],
      affected_suppliers: ['供应商A', '供应商B']
    },
    analysis: {
      trend: '异常率持续上升，已连续 3 周上升',
      possible_causes: ['新增供应商质量问题', '运输线路变化', '人员调整影响'],
      impact: '客户投诉率提高 45%，可能影响地区信誉评分'
    },
    recommended_assignee: {
      user_id: 'user_009',
      name: '陈华东负责人',
      reason: '华东地区负责人，可进行实地调查和改进措施'
    },
    expected_handling_time: {
      start_date: '2026-03-26',
      due_date: '2026-03-28',
      priority_hours: 48
    },
    metadata: {
      created_at: '2026-03-26T10:20:00Z',
      created_by: 'system',
      updated_at: '2026-03-26T10:20:00Z',
      related_task_ids: [],
      related_chat_messages: []
    }
  }
];

/**
 * 导出分组后的待办项数据（按优先级和分类）
 */
export const groupTodosByCategory = (todos) => {
  const groups = {};

  // 按分类分组
  todos.forEach(todo => {
    if (!groups[todo.category]) {
      groups[todo.category] = {};
    }
    if (!groups[todo.category][todo.type]) {
      groups[todo.category][todo.type] = [];
    }
    groups[todo.category][todo.type].push(todo);
  });

  // 每个类型内按优先级排序
  Object.keys(groups).forEach(category => {
    Object.keys(groups[category]).forEach(type => {
      groups[category][type].sort((a, b) => {
        const priorityOrder = { P0: 0, P1: 1, P2: 2, P3: 3 };
        return priorityOrder[a.priority] - priorityOrder[b.priority];
      });
    });
  });

  return groups;
};

/**
 * 获取今日未处理的待办项（按优先级排序）
 */
export const getTodayUnprocessedTodos = (todos) => {
  return todos
    .filter(todo => todo.status === '未处理')
    .sort((a, b) => {
      const priorityOrder = { P0: 0, P1: 1, P2: 2, P3: 3 };
      return priorityOrder[a.priority] - priorityOrder[b.priority];
    });
};

/**
 * 按分类统计待办项数量
 */
export const getTodoStats = (todos) => {
  const stats = {};
  todos.forEach(todo => {
    if (!stats[todo.category]) {
      stats[todo.category] = 0;
    }
    stats[todo.category]++;
  });
  return stats;
};

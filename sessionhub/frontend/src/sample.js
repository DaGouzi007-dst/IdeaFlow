// 内置样例。样例 A 与仓库 docs/样例/会话导入样例.json 内容一致（含 system 消息和
// created_at 为 null 的边界），source_conversation_id 为 null，不参与查重，可重复导入。
// 样例 B 带来源编号 demo-conv-001：第一次导入成功，再次导入触发 409，用于演示覆盖导入。
const SAMPLE_BASIC = {
  title: '讨论会话导入格式的边界',
  source: 'synthetic',
  source_conversation_id: null,
  messages: [
    {
      role: 'system',
      content: '本会话为人工编造的演示数据，用于验证第一模块的导入格式与会话读取流程。',
      created_at: null,
    },
    {
      role: 'user',
      content: '第一阶段导入功能只支持我们约定的 JSON 格式，还是也要支持直接粘贴文本？',
      created_at: '2026-11-05T20:05:00+08:00',
    },
    {
      role: 'assistant',
      content: '建议第一阶段只做约定的 JSON 格式：字段固定、便于校验，也能先把导入、查看和检索的流程打通。粘贴文本的切分和角色识别放到后续迭代更稳妥。',
      created_at: '2026-11-05T20:06:12+08:00',
    },
    {
      role: 'user',
      content: '如果一条消息在原来的工具里没有记录时间怎么办？',
      created_at: '2026-11-05T20:07:03+08:00',
    },
    {
      role: 'assistant',
      content: 'created_at 允许为 null：导入时原样保存，界面上不显示时间即可，不要编造时间。',
      created_at: '2026-11-05T20:07:40+08:00',
    },
    {
      role: 'user',
      content: '重复导入同一份会话怎么处理？',
      created_at: null,
    },
    {
      role: 'assistant',
      content: '第一版先做同 source_conversation_id 的重复提示；立项报告里跨工具的重复导入检查放到第 2 至 3 周迭代实现。',
      created_at: '2026-11-05T20:09:15+08:00',
    },
  ],
}

const SAMPLE_409 = {
  ...SAMPLE_BASIC,
  title: '重复导入处理演示（带来源编号）',
  source_conversation_id: 'demo-conv-001',
}

export const SAMPLE_BASIC_TEXT = JSON.stringify(SAMPLE_BASIC, null, 2)
export const SAMPLE_409_TEXT = JSON.stringify(SAMPLE_409, null, 2)

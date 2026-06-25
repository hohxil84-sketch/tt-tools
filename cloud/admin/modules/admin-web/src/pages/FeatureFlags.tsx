/**
 * 功能开关管理 — 可视化开关界面，替代原始 JSON 编辑。
 */
import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Sheet, priBtn, secBtn, inpS } from '../components/shared';

interface Feat {
  plan_id: string; plan_code: string; plan_name: string;
  enabled_features_json: Record<string, unknown>; plan_status: string;
}

/** 将功能值解析为统一结构 */
interface FeatureEntry {
  key: string;
  enabled: boolean;
  dailyLimit: number | null;   // 仅 object 类型时有值
}

function parseFeatures(json: Record<string, unknown>): FeatureEntry[] {
  return Object.entries(json).map(([key, val]) => {
    if (typeof val === 'object' && val !== null && !Array.isArray(val)) {
      const obj = val as Record<string, unknown>;
      return {
        key,
        enabled: true,
        dailyLimit: typeof obj.daily_limit === 'number' ? obj.daily_limit : null,
      };
    }
    return { key, enabled: !!val, dailyLimit: null };
  });
}

function featuresToJson(entries: FeatureEntry[]): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const e of entries) {
    if (!e.enabled) { result[e.key] = false; continue; }
    if (e.dailyLimit !== null) {
      result[e.key] = { daily_limit: e.dailyLimit };
    } else {
      result[e.key] = true;
    }
  }
  return result;
}

/** 已知功能码的中文名 */
const FEATURE_LABELS: Record<string, string> = {
  ai_copy_cloud: 'AI 文案生成',
  ai_render_cloud: 'AI 效果图',
  ai_image_tools_cloud: 'AI 高级图片',
  resize_image_local_paid: '本地图片处理',
  priority_queue: '优先队列',
  reseller_panel: '经销商面板',
};

/** 所有可选功能码（下拉框用） */
const ALL_FEATURE_CODES = Object.keys(FEATURE_LABELS);

export default function FeatureFlags() {
  const [items, setItems] = useState<Feat[]>([]);
  const [pc, setPc] = useState(''); const [err, setErr] = useState('');
  const [edit, setEdit] = useState<Feat | null>(null);

  const load = useCallback(async () => {
    setErr('');
    try { const d = await apiRequest<{ items: Feat[] }>('/admin/feature-flags', { params: { plan_code: pc || undefined } }); setItems(d.items); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [pc]);
  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', marginBottom: 20 }}>功能开关</h2>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <input placeholder="套餐编码筛选" value={pc} onChange={e => setPc(e.target.value)} style={inpS} />
        <button onClick={load} style={secBtn}>刷新</button>
      </div>
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: 16 }}>
        {items.map(it => (
          <div key={it.plan_id} style={{
            background: 'var(--white)', borderRadius: 'var(--radius-lg)', padding: '20px 24px',
            border: '1px solid var(--gray-200)', boxShadow: 'var(--shadow-sm)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <div>
                <h4 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 2px 0' }}>{it.plan_name}</h4>
                <code style={{ fontSize: 12, color: 'var(--blue)' }}>{it.plan_code}</code>
                <span style={{
                  marginLeft: 8, fontSize: 11, fontWeight: 500,
                  color: it.plan_status === 'active' ? '#34c759' : 'var(--gray-400)',
                }}>
                  {it.plan_status === 'active' ? '● 启用' : '○ 停用'}
                </span>
              </div>
              <button onClick={() => setEdit(it)} style={{ ...secBtn, fontSize: 11, padding: '4px 14px' }}>编辑</button>
            </div>
            {/* 开关预览 */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {parseFeatures(it.enabled_features_json).map(f => (
                <span key={f.key} style={{
                  display: 'inline-flex', alignItems: 'center', gap: 4,
                  padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 500,
                  background: f.enabled ? 'rgba(52,199,89,0.12)' : 'var(--gray-100)',
                  color: f.enabled ? '#34c759' : 'var(--gray-400)',
                  border: `1px solid ${f.enabled ? 'rgba(52,199,89,0.25)' : 'var(--gray-200)'}`,
                }}>
                  {FEATURE_LABELS[f.key] || f.key}
                  {f.dailyLimit !== null && ` (${f.dailyLimit}/天)`}
                </span>
              ))}
              {Object.keys(it.enabled_features_json).length === 0 && (
                <span style={{ fontSize: 11, color: 'var(--gray-400)' }}>暂无配置</span>
              )}
            </div>
          </div>
        ))}
        {items.length === 0 && <div style={{ color: 'var(--gray-400)', fontSize: 13 }}>暂无配置</div>}
      </div>
      {edit && <EditModal item={edit} close={() => setEdit(null)} done={() => { setEdit(null); load(); }} />}
    </div>
  );
}

/** ==================== 编辑弹窗：可视化开关 ==================== */

function EditModal({ item, close, done }: { item: Feat; close: () => void; done: () => void }) {
  const [entries, setEntries] = useState<FeatureEntry[]>(() => parseFeatures(item.enabled_features_json));
  const [saving, setSaving] = useState(false);
  const [selectedFeature, setSelectedFeature] = useState('');

  // 计算未被添加的可选功能码
  const addedKeys = new Set(entries.map(e => e.key));
  const availableFeatures = ALL_FEATURE_CODES.filter(code => !addedKeys.has(code));

  const toggle = (idx: number) => {
    setEntries(prev => prev.map((e, i) => i === idx ? { ...e, enabled: !e.enabled } : e));
  };

  const setLimit = (idx: number, val: number) => {
    setEntries(prev => prev.map((e, i) => i === idx ? { ...e, dailyLimit: val } : e));
  };

  const addFeature = () => {
    if (!selectedFeature) return;
    setEntries(prev => [...prev, { key: selectedFeature, enabled: true, dailyLimit: null }]);
    setSelectedFeature('');
  };

  const removeFeature = (idx: number) => {
    setEntries(prev => prev.filter((_, i) => i !== idx));
  };

  const save = async () => {
    setSaving(true);
    try {
      await apiRequest(`/admin/plans/${item.plan_id}/features`, {
        method: 'PATCH',
        body: { enabled_features_json: featuresToJson(entries) },
      });
      done();
    } catch (e: unknown) { alert(e instanceof Error ? e.message : '保存失败'); }
    finally { setSaving(false); }
  };

  return (
    <Sheet title={`功能开关: ${item.plan_name}`} close={close}>
      <div style={{ marginBottom: 16 }}>
        <code style={{ fontSize: 12, color: 'var(--blue)' }}>{item.plan_code}</code>
        <span style={{ marginLeft: 8, fontSize: 11, color: 'var(--gray-400)' }}>
          {item.plan_status === 'active' ? '已启用' : '已停用'}
        </span>
      </div>

      {/* 开关列表 */}
      <div style={{ marginBottom: 20 }}>
        {entries.length === 0 && (
          <div style={{ color: 'var(--gray-400)', fontSize: 13, padding: '16px 0', textAlign: 'center' }}>
            暂未配置任何功能
          </div>
        )}
        {entries.map((feat, idx) => (
          <div key={feat.key} style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '10px 0', borderBottom: '1px solid var(--gray-100)',
          }}>
            <div style={{ flex: 1 }}>
              <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--gray-800)' }}>
                {FEATURE_LABELS[feat.key] || feat.key}
              </span>
              <code style={{ display: 'block', fontSize: 11, color: 'var(--gray-400)', marginTop: 2 }}>
                {feat.key}
              </code>
            </div>

            {/* 每日限额输入（仅 object 类型） */}
            {feat.enabled && feat.dailyLimit !== null && (
              <input
                type="number" min={0} max={9999}
                value={feat.dailyLimit}
                onChange={e => setLimit(idx, Math.max(0, Number(e.target.value)))}
                style={{
                  width: 56, padding: '4px 6px', marginRight: 10,
                  border: '1px solid var(--gray-300)', borderRadius: 'var(--radius-sm)',
                  fontSize: 12, textAlign: 'center',
                }}
                title="每日使用次数上限"
              />
            )}

            {/* 开关 */}
            <button
              onClick={() => toggle(idx)}
              style={{
                width: 44, height: 26, borderRadius: 13, border: 'none',
                background: feat.enabled ? '#34c759' : 'var(--gray-300)',
                position: 'relative', cursor: 'pointer',
                transition: 'background 0.2s ease', flexShrink: 0,
              }}
              title={feat.enabled ? '已开启，点击关闭' : '已关闭，点击开启'}
            >
              <span style={{
                position: 'absolute', top: 3,
                left: feat.enabled ? 21 : 3,
                width: 20, height: 20, borderRadius: '50%',
                background: '#fff',
                boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
                transition: 'left 0.2s ease',
              }} />
            </button>

            {/* 删除 */}
            <button
              onClick={() => removeFeature(idx)}
              style={{
                marginLeft: 8, background: 'none', border: 'none',
                color: 'var(--gray-400)', fontSize: 14, cursor: 'pointer', padding: 4,
              }}
              title="移除此功能"
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      {/* 新增功能码 — 下拉框选择 */}
      <div style={{
        display: 'flex', gap: 8, padding: '10px 0', marginBottom: 20,
        borderTop: '1px solid var(--gray-200)', alignItems: 'center',
      }}>
        <select
          value={selectedFeature}
          onChange={e => setSelectedFeature(e.target.value)}
          style={{ flex: 1, padding: '7px 12px', border: '1px solid var(--gray-300)', borderRadius: 'var(--radius-sm)', fontSize: 12, background: 'var(--white)' }}
        >
          <option value="">-- 选择要添加的功能 --</option>
          {availableFeatures.map(code => (
            <option key={code} value={code}>{FEATURE_LABELS[code]} ({code})</option>
          ))}
          {availableFeatures.length === 0 && (
            <option value="" disabled>所有功能已添加</option>
          )}
        </select>
        <button onClick={addFeature} disabled={!selectedFeature} style={{
          ...secBtn, fontSize: 12, opacity: selectedFeature ? 1 : 0.5,
        }}>+ 添加</button>
      </div>

      {/* 底部操作 */}
      <div style={{ display: 'flex', gap: 8 }}>
        <button onClick={save} disabled={saving} style={priBtn}>
          {saving ? '保存中…' : '保存'}
        </button>
        <button onClick={close} style={secBtn}>取消</button>
      </div>
    </Sheet>
  );
}

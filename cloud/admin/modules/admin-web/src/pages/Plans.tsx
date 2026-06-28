import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Card, Tbl, ActBtn, Pager, Sheet, Modal, Fld, priBtn, secBtn, inpS, selS, finpS, showToast } from '../components/shared';

interface Plan { id: string; name: string; monthly_grant: number; expire_days?: number; is_default?: boolean; plan_tier?: string; status: string; created_at: string; enabled_features_json?: Record<string, unknown>; updated_at?: string; }
interface FeatureCode { id: string; code: string; name: string; category: string; is_active: boolean; description?: string | null; }

/** 功能开关条目（可视化用） */
interface FeatureToggle {
  code: string;      // 功能码
  name: string;      // 中文名
  enabled: boolean;  // 是否开启
  hasDailyLimit: boolean;  // 是否有每日限制
  dailyLimit: number;      // 每日限制次数
}

const CAT: Record<string, string> = { local_free: '本地免费', local_paid: '本地付费', cloud_ai: '云端AI' };

export default function Plans() {
  const [items, setItems] = useState<Plan[]>([]);
  const [err, setErr] = useState('');
  const [search, setSearch] = useState(''); const [sf, setSf] = useState(''); const [pg, setPg] = useState(0);
  const [edit, setEdit] = useState<Plan | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [ct, setCt] = useState<Plan | null>(null);
  const [cd, setCd] = useState<Plan | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [limit, setLimit] = useState(10);

  const load = useCallback(async () => {
    setErr('');
    try { const d = await apiRequest<{ items: Plan[] }>('/admin/plans', { params: { limit, search: search || undefined, status: sf || undefined } }); setItems(d.items); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [search, sf, pg, limit, refreshKey]);
  useEffect(() => { load(); }, [load]);

  const toggle = async (id: string, ns: string) => { try { await apiRequest(`/admin/plans/${id}/status`, { method: 'PATCH', body: { status: ns } }); showToast('操作成功', 'success'); setCt(null); setRefreshKey(k => k + 1); load(); } catch (e: unknown) { showToast(e instanceof Error ? e.message : '操作失败', 'error'); } };
  const del = async () => { if (!cd) return; try { await apiRequest(`/admin/plans/${cd.id}`, { method: 'DELETE' }); showToast('删除成功', 'success'); setCd(null); setRefreshKey(k => k + 1); load(); } catch (e: unknown) { showToast(e instanceof Error ? e.message : '删除失败', 'error'); } };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', margin: 0 }}>套餐管理</h2>
        <button onClick={() => setShowNew(true)} style={priBtn}>+ 新建套餐</button>
      </div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <input placeholder="搜索套餐名称..." value={search} onChange={e => { setSearch(e.target.value); }} style={inpS} />
        <select value={sf} onChange={e => { setSf(e.target.value); }} style={selS}><option value="">全部</option><option value="active">启用</option><option value="disabled">停用</option></select>
        <button onClick={load} style={secBtn}>刷新</button>
      </div>
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}
      <Card><Tbl heads={['名称', '月赠额度', '到期', '默认', '状态', '创建时间', '']} colAligns={['l', 'r', 'c', 'c', 'c', 'l', 'r']}>
        {items.map(p => (
          <tr key={p.id}>
            <td style={{ fontWeight: 600, fontSize: 13, width: '22%' }}>{p.name}</td>
            <td style={{ fontSize: 13, width: '10%', textAlign: 'right' }}>{p.monthly_grant.toLocaleString()}</td>
            <td style={{ fontSize: 13, width: '12%', textAlign: 'center', color: (p.expire_days || 0) > 0 ? 'var(--orange)' : 'var(--gray-400)', fontWeight: (p.expire_days || 0) > 0 ? 600 : 400 }}>{p.expire_days ? `${p.expire_days} 天` : '永不过期'}</td>
            <td style={{ fontSize: 13, width: '8%', textAlign: 'center' }}>{p.is_default ? <span style={{ fontSize: 12, fontWeight: 600, color: '#fff', background: '#ff9500', padding: '2px 10px', borderRadius: 10 }}>默认</span> : <span style={{ color: 'var(--gray-400)' }}>—</span>}</td>
            <td style={{ fontSize: 13, width: '8%', textAlign: 'center' }}><span style={{ fontWeight: 600, color: p.status === 'active' ? '#34c759' : 'var(--gray-400)' }}>{p.status === 'active' ? '● 启用' : '○ 停用'}</span></td>
            <td style={{ fontSize: 12, width: '20%', color: 'var(--gray-500)' }}>{new Date(p.created_at).toLocaleString('zh-CN')}</td>
            <td style={{ textAlign: 'right', width: '20%', whiteSpace: 'nowrap' }}>
              <ActBtn kind="edit" onClick={() => setEdit(p)}>编辑</ActBtn>
              <ActBtn kind={p.status === 'active' ? 'block' : 'unblock'} onClick={() => setCt(p)}>{p.status === 'active' ? '停用' : '启用'}</ActBtn>
              <ActBtn kind="delete" onClick={() => setCd(p)}>删除</ActBtn>
            </td>
          </tr>
        ))}
      </Tbl></Card>
      <Pager pg={pg} tp={Math.ceil(items.length / limit)} total={items.length} limit={limit} onLimitChange={(n) => { setLimit(n); setPg(0); }} onPrev={() => setPg(pg - 1)} onNext={() => setPg(pg + 1)} />
      {ct && <Modal title="确认" close={() => setCt(null)} action={() => toggle(ct.id, ct.status === 'active' ? 'disabled' : 'active')} danger><p>{ct.status === 'active' ? '停用' : '启用'}套餐 <b>{ct.name}</b>？</p></Modal>}
      {cd && <Modal title="删除套餐" close={() => setCd(null)} action={del} danger><p>永久删除 <b>{cd.name}</b>？</p></Modal>}
      {(edit || showNew) && <PlanForm plan={edit} close={() => { setEdit(null); setShowNew(false); }} done={() => { setEdit(null); setShowNew(false); setRefreshKey(k => k + 1); load(); }} />}
    </div>
  );
}

/** ==================== 套餐表单（可视化功能开关） ==================== */

function PlanForm({ plan, close, done }: { plan?: Plan | null; close: () => void; done: () => void }) {
  const isEdit = !!plan;

  // 基本字段
  const [name, setName] = useState(plan?.name || '');
  const [mg, setMg] = useState(plan?.monthly_grant || 0);
  const [expDays, setExpDays] = useState(plan?.expire_days || 0);
  const [planTier, setPlanTier] = useState((plan as any)?.plan_tier || 'standard');
  const [isDefault, setIsDefault] = useState(plan?.is_default || false);

  // 全部可用功能码列表（从后端拉取）
  const [allFeatures, setAllFeatures] = useState<FeatureCode[]>([]);
  const [featuresLoading, setFeaturesLoading] = useState(true);
  const [featuresError, setFeaturesError] = useState('');

  // 功能开关状态
  const [toggles, setToggles] = useState<FeatureToggle[]>([]);
  const [saving, setSaving] = useState(false);

  // 从后端加载全部可用功能码（数据库是唯一数据源）
  useEffect(() => {
    (async () => {
      try {
        const data = await apiRequest<{ items: FeatureCode[] }>('/admin/feature-codes/list', { params: { limit: 200 } });
        setAllFeatures(data.items || []);
      } catch (e: unknown) {
        setFeaturesError(e instanceof Error ? e.message : '加载功能码失败');
        setAllFeatures([]);
      }
      finally { setFeaturesLoading(false); }
    })();
  }, []);

  // 当功能码列表和已有配置都就绪时，构建 toggles
  useEffect(() => {
    if (allFeatures.length === 0) return;
    const existing = (plan?.enabled_features_json || {}) as Record<string, unknown>;
    const built: FeatureToggle[] = allFeatures.map(fc => {
      const val = existing[fc.code];
      let enabled = false;
      let hasDailyLimit = false;
      let dailyLimit = 0;
      if (val === true) {
        enabled = true;
      } else if (typeof val === 'object' && val !== null && !Array.isArray(val)) {
        const obj = val as Record<string, unknown>;
        enabled = true;
        if (typeof obj.daily_limit === 'number') {
          hasDailyLimit = true;
          dailyLimit = obj.daily_limit;
        }
      }
      return { code: fc.code, name: fc.name, enabled, hasDailyLimit, dailyLimit };
    });
    setToggles(built);
  }, [allFeatures, plan?.enabled_features_json]);

  // 切换开关
  const toggleFeature = (idx: number) => {
    setToggles(prev => prev.map((t, i) =>
      i === idx ? { ...t, enabled: !t.enabled, hasDailyLimit: false, dailyLimit: 0 } : t
    ));
  };

  // 切换每日限制
  const toggleDailyLimit = (idx: number) => {
    setToggles(prev => prev.map((t, i) =>
      i === idx ? { ...t, hasDailyLimit: !t.hasDailyLimit, dailyLimit: t.hasDailyLimit ? 0 : 10 } : t
    ));
  };

  // 修改每日限制值
  const setDailyLimitVal = (idx: number, val: number) => {
    setToggles(prev => prev.map((t, i) =>
      i === idx ? { ...t, dailyLimit: Math.max(0, val) } : t
    ));
  };

  // 构建 JSON
  const buildFeaturesJson = (): Record<string, unknown> => {
    const result: Record<string, unknown> = {};
    for (const t of toggles) {
      if (!t.enabled) { result[t.code] = false; continue; }
      if (t.hasDailyLimit) {
        result[t.code] = { daily_limit: t.dailyLimit };
      } else {
        result[t.code] = true;
      }
    }
    return result;
  };

  const submit = async (e: React.FormEvent) => { e.preventDefault(); setSaving(true);
    const featuresJson = buildFeaturesJson();
    try {
      if (isEdit) {
        await apiRequest(`/admin/plans/${plan!.id}`, { method: 'PATCH', body: { name, monthly_grant: mg, expire_days: expDays, is_default: isDefault, plan_tier: planTier, enabled_features_json: featuresJson } });
      } else {
        await apiRequest('/admin/plans', { method: 'POST', body: { name, monthly_grant: mg, expire_days: expDays, is_default: isDefault, plan_tier: planTier, enabled_features_json: featuresJson } });
      }
      showToast('保存成功', 'success'); done();
    } catch (e: unknown) { showToast(e instanceof Error ? e.message : '保存失败', 'error'); }
    finally { setSaving(false); }
  };

  // 按分类分组
  const grouped = new Map<string, { fc: FeatureCode; toggle: FeatureToggle; idx: number }[]>();
  toggles.forEach((t, i) => {
    const fc = allFeatures.find(f => f.code === t.code);
    const cat = fc?.category || 'other';
    if (!grouped.has(cat)) grouped.set(cat, []);
    grouped.get(cat)!.push({ fc: fc!, toggle: t, idx: i });
  });

  return <Sheet title={isEdit ? `编辑: ${plan!.name}` : '新建套餐'} close={close}>
    <form onSubmit={submit}>
      <Fld label="名称"><input value={name} onChange={e => setName(e.target.value)} required style={finpS} /></Fld>
      <Fld label="套餐等级"><select value={planTier} onChange={e => setPlanTier(e.target.value)} style={selS}><option value="free">免费</option><option value="standard">标准</option><option value="pro">专业</option></select></Fld>
      <Fld label="月赠额度"><input type="number" value={mg} onChange={e => setMg(Number(e.target.value))} min={0} style={finpS} /></Fld>
      <Fld label="到期天数（0=永不过期）"><input type="number" value={expDays} onChange={e => setExpDays(Math.max(0, Number(e.target.value)))} min={0} style={finpS} /></Fld>
      <Fld label="">
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 14 }}>
          <input type="checkbox" checked={isDefault} onChange={e => setIsDefault(e.target.checked)} style={{ width: 18, height: 18 }} />
          设为默认套餐（新用户自动获得）
        </label>
      </Fld>

      {/* 功能开关 — 可视化选择 */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: 'var(--gray-600)', marginBottom: 8 }}>
          功能开关
        </label>
        {featuresError && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 8 }}>{featuresError}</div>}
        {featuresLoading ? (
          <div style={{ fontSize: 12, color: 'var(--gray-400)', padding: '20px 0', textAlign: 'center' }}>加载功能码列表…</div>
        ) : toggles.length === 0 ? (
          <div style={{ fontSize: 12, color: 'var(--gray-400)', padding: '20px 0', textAlign: 'center' }}>暂无可用功能码</div>
        ) : (
          <div style={{
            border: '1px solid var(--gray-200)', borderRadius: 'var(--radius-md)',
            padding: '8px 0', maxHeight: 360, overflowY: 'auto',
          }}>
            {[...grouped.entries()].map(([category, items]) => (
              <div key={category}>
                <div style={{
                  padding: '6px 16px', fontSize: 11, fontWeight: 600,
                  color: 'var(--gray-400)', textTransform: 'uppercase',
                  letterSpacing: '0.04em', background: 'var(--gray-50)',
                }}>
                  {CAT[category] || category}
                </div>
                {items.map(({ toggle, idx }) => (
                  <div key={toggle.code} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '8px 16px', borderBottom: '1px solid var(--gray-50)',
                  }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--gray-800)' }}>
                        {toggle.name}
                      </span>
                      <code style={{ display: 'block', fontSize: 11, color: 'var(--gray-400)', marginTop: 1 }}>
                        {toggle.code}
                      </code>
                    </div>

                    {/* 每日限制控件 */}
                    {toggle.enabled && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginRight: 10 }}>
                        {toggle.hasDailyLimit ? (
                          <>
                            <input
                              type="number" min={0} max={9999}
                              value={toggle.dailyLimit}
                              onChange={e => setDailyLimitVal(idx, Math.max(0, Number(e.target.value)))}
                              style={{
                                width: 48, padding: '3px 4px', fontSize: 11, textAlign: 'center',
                                border: '1px solid var(--gray-300)', borderRadius: 'var(--radius-sm)',
                              }}
                            />
                            <span style={{ fontSize: 10, color: 'var(--gray-400)', whiteSpace: 'nowrap' }}>/天</span>
                          </>
                        ) : (
                          <button
                            type="button"
                            onClick={() => toggleDailyLimit(idx)}
                            style={{
                              fontSize: 10, color: 'var(--gray-400)', cursor: 'pointer',
                              background: 'none', border: 'none', whiteSpace: 'nowrap',
                            }}
                            title="添加每日使用次数限制"
                          >
                            +限额
                          </button>
                        )}
                      </div>
                    )}

                    {/* 开关 */}
                    <button
                      type="button"
                      onClick={() => toggleFeature(idx)}
                      style={{
                        width: 44, height: 26, borderRadius: 13, border: 'none',
                        background: toggle.enabled ? '#34c759' : 'var(--gray-300)',
                        position: 'relative', cursor: 'pointer', flexShrink: 0,
                        transition: 'background 0.2s ease',
                      }}
                    >
                      <span style={{
                        position: 'absolute', top: 3,
                        left: toggle.enabled ? 21 : 3,
                        width: 20, height: 20, borderRadius: '50%',
                        background: '#fff',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
                        transition: 'left 0.2s ease',
                      }} />
                    </button>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
        <button type="submit" disabled={saving} style={priBtn}>{saving ? '保存中…' : '保存'}</button>
        <button type="button" onClick={close} style={secBtn}>取消</button>
      </div>
    </form>
  </Sheet>;
}

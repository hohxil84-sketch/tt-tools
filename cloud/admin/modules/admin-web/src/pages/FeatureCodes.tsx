import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Card, Tbl, Badge, ActBtn, Pager, Sheet, Modal, secBtn, inpS, selS, priBtn, showToast } from '../components/shared';

interface FC { id: string; code: string; name: string; category: string; is_active: boolean; plan_count?: number; description?: string | null; created_at: string; }
interface PlanRef { id: string; name: string; monthly_grant: number; status: string; }
interface List { items: FC[]; total: number; limit: number; offset: number; }
const CATS: Record<string, string> = { local_free: '本地免费', local_paid: '本地付费', cloud_ai: '云端AI' };
const SLS: Record<string, string> = { active: '启用', disabled: '停用' };

export default function FeatureCodes() {
  const [d, setD] = useState<List | null>(null);
  const [pricing, setPricing] = useState<Record<string, number>>({});
  const [rate, setRate] = useState('10');
  const [savingRate, setSavingRate] = useState(false);
  const [cat, setCat] = useState(''); const [pg, setPg] = useState(0); const [err, setErr] = useState('');
  const [create, setCreate] = useState(false);
  const [delTarget, setDelTarget] = useState<FC | null>(null);
  const [edit, setEdit] = useState<FC | null>(null);
  const [toggleTarget, setToggleTarget] = useState<FC | null>(null);
  const [creditEdit, setCreditEdit] = useState<{code:string;name:string;val:number} | null>(null);
  const [detailFC, setDetailFC] = useState<FC | null>(null);  // 详情：关联套餐列表
  const [detailPlans, setDetailPlans] = useState<PlanRef[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [limit, setLimit] = useState(10);
  const [order, setOrder] = useState('desc');
  const [form, setForm] = useState({ code: '', name: '', category: 'cloud_ai', description: '' });

  const load = useCallback(async () => {
    setErr('');
    try {
      const [fcData, fpData, cfgData] = await Promise.all([
        apiRequest<List>('/admin/feature-codes/list', { params: { limit, offset: pg * limit, order, category: cat || undefined } }),
        apiRequest<{items:{feature_code:string;min_credits:number}[]}>('/admin/billing/feature-pricing'),
        apiRequest<{[key:string]:{value:string}}>('/admin/billing/system-config'),
      ]);
      setD(fcData);
      const pmap: Record<string,number> = {};
      for (const fp of fpData.items) pmap[fp.feature_code] = fp.min_credits;
      setPricing(pmap);
      if (cfgData?.credits_exchange_rate) setRate(cfgData.credits_exchange_rate.value);
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [pg, cat, limit, order, refreshKey]);
  useEffect(() => { load(); }, [load]);
  const TP = d ? Math.ceil(d.total / limit) : 0;

  const saveRate = async () => {
    setSavingRate(true);
    try { await apiRequest('/admin/billing/system-config/credits_exchange_rate', { method:'PUT', body:{value:rate} }); showToast('算力率已更新','success'); setRefreshKey(k=>k+1); }
    catch(e:unknown){ showToast(e instanceof Error?e.message:'保存失败','error'); }
    finally{setSavingRate(false);}
  };

  const doCreate = async () => {
    try { await apiRequest('/admin/feature-codes', { method:'POST', body:{code:form.code,name:form.name,category:form.category,description:form.description||undefined} }); showToast('创建成功','success'); setCreate(false); setForm({code:'',name:'',category:'cloud_ai',description:''}); setRefreshKey(k=>k+1); load(); }
    catch(e:unknown){ showToast(e instanceof Error?e.message:'创建失败','error'); }
  };
  const doEdit = async () => {
    if(!edit) return;
    try { await apiRequest(`/admin/feature-codes/${edit.id}`, { method:'PATCH', body:{name:form.name,category:form.category,description:form.description||undefined} }); showToast('保存成功','success'); setEdit(null); setRefreshKey(k=>k+1); load(); }
    catch(e:unknown){ showToast(e instanceof Error?e.message:'编辑失败','error'); }
  };
  const doDelete = async () => {
    if(!delTarget) return;
    try { await apiRequest(`/admin/feature-codes/${delTarget.id}`, { method:'DELETE' }); showToast('删除成功','success'); setDelTarget(null); setRefreshKey(k=>k+1); load(); }
    catch(e:unknown){ showToast(e instanceof Error?e.message:'删除失败','error'); }
  };
  const doToggle = async (fc:FC) => {
    try { await apiRequest(`/admin/feature-codes/${fc.id}`, { method:'PATCH', body:{is_active:!fc.is_active} }); showToast(fc.is_active?'已禁用':'已启用','success'); setRefreshKey(k=>k+1); load(); }
    catch(e:unknown){ showToast(e instanceof Error?e.message:'操作失败','error'); }
  };
  const doSaveCredits = async () => {
    if(!creditEdit) return;
    try { await apiRequest(`/admin/billing/feature-pricing/${creditEdit.code}`, { method:'PUT', body:{min_credits:creditEdit.val} }); showToast('已更新','success'); setCreditEdit(null); setRefreshKey(k=>k+1); load(); }
    catch(e:unknown){ showToast(e instanceof Error?e.message:'失败','error'); }
  };
  const doDetail = async (fc: FC) => {
    setDetailFC(fc); setDetailPlans([]); setDetailLoading(true);
    try {
      const data = await apiRequest<PlanRef[]>(`/admin/feature-codes/${fc.id}/plans`);
      setDetailPlans(data || []);
    } catch (e: unknown) { showToast(e instanceof Error ? e.message : '加载失败', 'error'); }
    finally { setDetailLoading(false); }
  };

  return (
    <div>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
        <h2 style={{ fontSize:22, fontWeight:600, letterSpacing:'-0.02em', margin:0 }}>功能码管理 & 定价</h2>
        <button onClick={()=>{setCreate(true);setForm({code:'',name:'',category:'cloud_ai',description:''});}} style={priBtn}>新增功能码</button>
      </div>
      {/* 汇率 */}
      <div style={{ background:'var(--white)', borderRadius:'var(--radius-lg)', padding:'12px 20px', border:'1px solid var(--gray-200)', boxShadow:'var(--shadow-sm)', marginBottom:16, display:'flex', alignItems:'center', gap:12 }}>
        <span style={{ fontSize:14, fontWeight:600 }}>算力率：1 CNY =</span>
        <input type="number" step="0.1" value={rate} onChange={e=>setRate(e.target.value)} style={{ width:80, padding:'5px 8px', fontSize:13, textAlign:'center', border:'1px solid var(--gray-300)', borderRadius:'var(--radius-sm)' }} />
        <span style={{ fontSize:14, fontWeight:600 }}>算力</span>
        <button onClick={saveRate} disabled={savingRate} style={{ ...priBtn, fontSize:12, padding:'5px 16px' }}>{savingRate?'保存中':'更新算力率'}</button>
      </div>
      <div style={{ display:'flex', gap:10, marginBottom:20 }}>
        <select value={cat} onChange={e=>{setCat(e.target.value);setPg(0);}} style={selS}>
          <option value="">全部分类</option><option value="local_free">本地免费</option><option value="local_paid">本地付费</option><option value="cloud_ai">云端AI</option>
        </select>
        <button onClick={load} style={secBtn}>刷新</button>
      </div>
      {err && <div style={{ color:'var(--red)', fontSize:12, marginBottom:12 }}>{err}</div>}
      <Card><Tbl heads={['功能码','名称','分类','起步算力','状态','关联套餐','创建时间','']} colAligns={['c','c','c','c','c','c','c','r']}>
        {d?.items.map(fc=>(
          <tr key={fc.id}>
            <td style={{ fontSize:13, width:'11%', textAlign:'center' }}><code style={{ fontSize:12, fontWeight:600 }}>{fc.code}</code></td>
            <td style={{ fontWeight:500, fontSize:13, width:'11%', textAlign:'center' }}>{fc.name}</td>
            <td style={{ fontSize:13, width:'9%', textAlign:'center' }}><Badge t={CATS[fc.category]||fc.category} c="var(--blue)" /></td>
            <td style={{ fontSize:14, fontWeight:700, width:'8%', textAlign:'center', color: pricing[fc.code] ? 'var(--orange)' : 'var(--gray-400)', cursor:'pointer' }}
                onClick={()=>setCreditEdit({code:fc.code,name:fc.name,val:pricing[fc.code]||0})}>
              {pricing[fc.code] ?? '—'}
            </td>
            <td style={{ fontSize:13, width:'8%', textAlign:'center' }}><span style={{ fontSize:12, fontWeight:500, color:fc.is_active?'#34c759':'var(--gray-400)', cursor:'pointer' }} onClick={()=>setToggleTarget(fc)}>{fc.is_active?'启用':'禁用'}</span></td>
            <td style={{ fontSize:13, width:'8%', textAlign:'center', paddingRight:24 }}><span style={{ fontSize:13, fontWeight:600, color:(fc.plan_count||0)>0?'var(--blue)':'var(--gray-400)' }}>{fc.plan_count??0}</span></td>
            <td style={{ fontSize:12, color:'var(--gray-500)', width:'14%', textAlign:'center' }}>{new Date(fc.created_at).toLocaleString('zh-CN')}</td>
            <td style={{ textAlign:'right', width:'16%', whiteSpace:'nowrap' }}>
              <ActBtn kind="detail" onClick={()=>doDetail(fc)}>详情</ActBtn>
              <ActBtn kind="edit" onClick={()=>{setEdit(fc);setForm({code:fc.code,name:fc.name,category:fc.category,description:fc.description||''});}}>编辑</ActBtn>
              <ActBtn kind="delete" onClick={()=>setDelTarget(fc)}>删除</ActBtn>
            </td>
          </tr>
        ))}
      </Tbl></Card>
      <Pager pg={pg} tp={TP} total={d?.total||0} limit={limit} onLimitChange={(n)=>{setLimit(n);setPg(0);}} onPrev={()=>setPg(pg-1)} onNext={()=>setPg(pg+1)} order={order} onOrderChange={o => { setOrder(o); setPg(0); }} />

      {delTarget && <Modal title="删除功能码" close={()=>setDelTarget(null)} action={doDelete} danger><p>确认删除功能码 <b>{delTarget.code}</b>？此操作不可撤销。</p></Modal>}
      {toggleTarget && <Modal title={toggleTarget.is_active?'禁用功能码':'启用功能码'} close={()=>setToggleTarget(null)} action={()=>{doToggle(toggleTarget);setToggleTarget(null);}} danger={toggleTarget.is_active}><p>确认{toggleTarget.is_active?'禁用':'启用'}功能码 <b>{toggleTarget.code}</b>？</p></Modal>}
      {creditEdit && <Sheet title={`编辑起步算力: ${creditEdit.name}`} close={()=>setCreditEdit(null)}>
        <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
          <Fld label="功能码"><code>{creditEdit.code}</code></Fld>
          <Fld label="起步算力"><input type="number" min={1} value={creditEdit.val} onChange={e=>setCreditEdit({...creditEdit,val:Math.max(1,Number(e.target.value))})} style={inpS} /></Fld>
          <button onClick={doSaveCredits} style={priBtn}>保存</button>
        </div>
      </Sheet>}
      {create && <Sheet title="新增功能码" close={()=>setCreate(false)}>
        <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
          <input placeholder="功能码 (如 my_new_feature_cloud)" value={form.code} onChange={e=>setForm({...form,code:e.target.value})} style={inpS} />
          <input placeholder="名称" value={form.name} onChange={e=>setForm({...form,name:e.target.value})} style={inpS} />
          <select value={form.category} onChange={e=>setForm({...form,category:e.target.value})} style={{...inpS,width:'100%'}}><option value="cloud_ai">云端AI</option><option value="local_paid">本地付费</option><option value="local_free">本地免费</option></select>
          <input placeholder="说明（可选）" value={form.description} onChange={e=>setForm({...form,description:e.target.value})} style={inpS} />
          <button onClick={doCreate} style={priBtn}>创建</button>
        </div>
      </Sheet>}
      {edit && <Sheet title={`编辑: ${edit.code}`} close={()=>setEdit(null)}>
        <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
          <Fld label="功能码"><code style={{ fontSize:12, color:'var(--blue)' }}>{edit.code}</code></Fld>
          <Fld label="名称"><input value={form.name} onChange={e=>setForm({...form,name:e.target.value})} style={inpS} /></Fld>
          <Fld label="分类"><select value={form.category} onChange={e=>setForm({...form,category:e.target.value})} style={{...inpS,width:'100%'}}><option value="cloud_ai">云端AI</option><option value="local_paid">本地付费</option><option value="local_free">本地免费</option></select></Fld>
          <Fld label="说明"><input value={form.description} onChange={e=>setForm({...form,description:e.target.value})} style={inpS} placeholder="说明（可选）" /></Fld>
          <button onClick={doEdit} style={priBtn}>保存</button>
        </div>
      </Sheet>}
      {/* 功能码关联套餐详情 */}
      {detailFC && <Sheet title={`关联套餐: ${detailFC.name}`} close={()=>{setDetailFC(null);setDetailPlans([]);}} maxHeight="70vh">
        {detailLoading ? <p style={{ fontSize:13, color:'var(--gray-400)', textAlign:'center', padding:20 }}>加载中…</p> :
         detailPlans.length === 0 ? <p style={{ fontSize:13, color:'var(--gray-400)', textAlign:'center', padding:20 }}>暂无套餐关联此功能码</p> :
         <table style={{ width:'100%', borderCollapse:'collapse', fontSize:13 }}>
           <thead><tr style={{ borderBottom:'2px solid var(--gray-200)' }}>
             <th style={{ textAlign:'left', padding:'8px 4px' }}>套餐名称</th>
             <th style={{ textAlign:'right', padding:'8px 4px' }}>月推算力</th>
             <th style={{ textAlign:'center', padding:'8px 4px' }}>状态</th>
           </tr></thead>
           <tbody>{detailPlans.map(p => (
             <tr key={p.id} style={{ borderBottom:'1px solid var(--gray-100)' }}>
               <td style={{ padding:'8px 4px', fontWeight:500 }}>{p.name}</td>
               <td style={{ textAlign:'right', padding:'8px 4px', color:'var(--orange)', fontWeight:600 }}>{p.monthly_grant.toLocaleString()}</td>
               <td style={{ textAlign:'center', padding:'8px 4px', color: p.status==='active' ? '#34c759' : 'var(--gray-400)', fontWeight:500 }}>{SLS[p.status] || p.status}</td>
             </tr>
           ))}</tbody>
         </table>
        }
      </Sheet>}
    </div>
  );
}

function Fld({ label, children }: { label: string; children: React.ReactNode }) {
  return (<div style={{ display:'flex', flexDirection:'column', gap:4 }}><label style={{ fontSize:13, fontWeight:500, color:'var(--gray-600)' }}>{label}</label>{children}</div>);
}

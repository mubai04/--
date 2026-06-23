#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""网文伪数学联合审计器 v1.0.2 CANDIDATE。
正式八维输入只能是八维探针正式报告；不调用API。"""
from __future__ import annotations
import argparse, copy, hashlib, importlib.util, json, math, re, statistics, sys, tempfile
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as SchemaValidationError

VERSION="1.0.2-CANDIDATE"; SCHEMA_VERSION="1.0.2"; PROBE_VERSION="3.2.1"; PROBE_SCHEMA="3.2.1"; PROBE_RUBRIC="八维伪线性探针-v3.2.1"
CHAPTER_WEIGHTS={"理解成立度":.15,"因果推进度":.20,"人物主动度":.15,"情绪成立度":.15,"当章回报度":.20,"后续牵引度":.15}
CHAPTER_CRITICAL=["理解成立度","因果推进度","人物主动度","当章回报度","后续牵引度"]
LIT_KEYS=["声音独特度","感知具体度","意义复层度","节律控制度","视角控制度","表达陌生度"]
AI_KEYS=["模板重复","句法均质","过度解释","通用抽象","语义复述","套语过渡"]
SM_KEYS=["因果连续性","目标连续性","状态继承连续性","事件显著性差异","重新解释与意外","真实路径分叉","节拍不规则度"]
RISK_KEYS=["叙事结构","文风语言","创意设定","角色心理","技术连续性","阅读体验","概率趋同","肉身经验缺失","留白不足"]
HEV_KEYS=["长程回收","人物声纹","功能性不对称"]
GATE_KEYS=["因果闸门","人物闸门","连续性闸门","视角闸门"]
MODULES=["输入完整性","直接测量","四硬闸门","章级六维","文学表现","AI味","情节平滑化","九维风险","AI参与伪概率","八维探针","商业六门","联合裁决"]
class AuditError(ValueError): pass

def req(c,m):
    if not c: raise AuditError(m)
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,o): Path(p).write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
def sha_file(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical_hash(o): return hashlib.sha256(json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def load_probe_module(path:Path):
    sys.path.insert(0,str(path.parent)); spec=importlib.util.spec_from_file_location('probe_runtime_v321',path); mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod); return mod

def schema_validate(obj,schema_path,label):
    schema=load(schema_path); v=Draft202012Validator(schema); errs=sorted(v.iter_errors(obj),key=lambda e:list(e.path))
    if errs:
        e=errs[0]; loc='.'.join(map(str,e.path)) or '<root>'; raise AuditError(f'{label} Schema失败：{loc}: {e.message}')

def body_text(raw):
    lines=raw.splitlines(); start=0
    for i,line in enumerate(lines):
        if re.match(r'^#\s*第[一二三四五六七八九十百千万0-9]+章',line.strip()): start=i+1; break
    return '\n'.join(lines[start:]).strip()
def measure_source(path):
    raw=Path(path).read_text(encoding='utf-8'); body=body_text(raw); paras=[x.strip() for x in body.splitlines() if x.strip() and not x.strip().startswith('#')]; zh=lambda s:re.findall(r'[\u4e00-\u9fff]',s); sent=[]
    for p in paras:
        for x in re.split(r'(?<=[。！？!?；;])',p):
            if zh(x): sent.append(x.strip())
    lens=[len(zh(x)) for x in sent]; pl=[len(zh(x)) for x in paras]; mean=sum(lens)/len(lens) if lens else 0
    return {'正文汉字数':len(zh(body)),'自然段数':len(paras),'有效句子数':len(sent),'平均句长':round(mean,2),'句长中位数':round(statistics.median(lens),2) if lens else 0,'句长标准差':round(statistics.pstdev(lens),2) if len(lens)>1 else 0,'句长变异系数':round(statistics.pstdev(lens)/mean,4) if len(lens)>1 and mean else 0,'8字以内短段占比':round(sum(x<=8 for x in pl)/len(pl),4) if pl else 0,'5字以内短段占比':round(sum(x<=5 for x in pl)/len(pl),4) if pl else 0,'直接引语数量':len(re.findall(r'“[^”]+”',body))}

def validate_evidence(items,raw,label):
    for i,e in enumerate(items):
        if e['类型']=='DIRECT_QUOTE': anchors=[e]
        else: anchors=e['锚点']
        for j,a in enumerate(anchors):
            s=a['起始字符']; t=a['结束字符']; text=a['文本']; req(s<t<=len(raw),f'{label}[{i}]锚点[{j}]越界'); req(raw[s:t]==text,f'{label}[{i}]锚点[{j}]与正文不匹配')
def walk_evidence(broad,raw):
    for sec in ['硬闸门','章级六维','文学表现','AI味','情节平滑化','九维风险','AI参与反向证据']:
        for k,v in broad[sec].items(): validate_evidence(v['证据'],raw,f'{sec}.{k}.证据')
def evidence_text(items):
    out=[]
    for e in items:
        if e['类型']=='DIRECT_QUOTE': out.append(f"引文[{e['起始字符']}:{e['结束字符']}] {e['文本']}")
        else: out.append(f"归纳：{e['说明']}（锚点{len(e['锚点'])}处）")
    return '；'.join(out)

def compare_manual(manual,auto):
    if not manual: return {'状态':'未提供','差异':[]}
    dif=[]
    for k in ['正文汉字数','自然段数','有效句子数']:
        if k in manual and manual[k]!=auto[k]: dif.append(f'{k}: {manual[k]} != {auto[k]}')
    for k,t in [('平均句长',.05),('句长变异系数',.01),('8字以内短段占比',.005)]:
        if k in manual and abs(float(manual[k])-float(auto[k]))>t: dif.append(f'{k}: {manual[k]} != {auto[k]}')
    req(not dif,'直接测量与正文不一致：'+'；'.join(dif)); return {'状态':'通过','差异':[]}

def module_record(name,status='COMPUTED',inputs=None,outputs=None,formulas=None,evidence_count=0,error=None): return {'模块':name,'状态':status,'输入字段':inputs or [],'输出字段':outputs or [],'使用公式':formulas or [],'证据数量':evidence_count,'异常':error}
def chapter_state(blocker,s,chap):
    if blocker:return '阻断'
    if s<2.5:return '重写'
    if s<2.8 or any(chap[k]<2 for k in CHAPTER_CRITICAL):return '定向修复'
    return '稳健通过'
def count_evidence(sec): return sum(len(v['证据']) for v in sec.values())

def validate_probe_formal(report,source,probe_mod):
    req(report['run']['version']==PROBE_VERSION,'八维脚本版本不匹配'); req(report['run']['schema_version']==PROBE_SCHEMA,'八维Schema版本不匹配'); req(report['run']['rubric_version']==PROBE_RUBRIC,'八维规则版本不匹配')
    source_sha=sha_file(source); req(report['run']['source_name']==source.name,'八维正式报告源文件名不匹配'); req(report['run']['source_sha256']==source_sha,'八维正式报告正文哈希不匹配'); req(report['extraction']['source_sha256']==source_sha,'八维提取正文哈希不匹配')
    text=source.read_text(encoding='utf-8'); ex=copy.deepcopy(report['extraction'])
    task={'schema_version':PROBE_SCHEMA,'rubric_version':PROBE_RUBRIC,'task_id':ex['task_id'],'created_at':report['run']['created_at'],'input_type':report['run']['input_type'],'source':{'name':source.name,'path':str(source),'sha256':source_sha,'character_count':len(text)},'metadata':report['run']['metadata'],'text':text,'truncated':report['run']['truncated']}
    task=probe_mod.validate_task(task); ex=probe_mod.validate_extraction(ex,task)
    lr=report['linear_result']; ws=probe_mod.WeightSet(weights={k:float(v) for k,v in lr['weights'].items()},bias=float(lr['bias']),thresholds={k:float(v) for k,v in lr['thresholds'].items()},critical_axes=tuple(lr['critical_axes']),source=lr['weight_source'],status=lr['weight_status'])
    recomputed=probe_mod.compute_linear_result(ex,ws)
    fields=['raw_z','activation','coverage','weighted_coverage','missing_axes','missing_critical_axes','raw_level','final_level','cap_reasons','features','overload_factors','high_overload_axes','weights','critical_axes','bias','thresholds','weight_status','weight_config_sha256','commercial_gate_result','contributions','top_positive','top_negative']
    for f in fields:
        req(recomputed[f]==lr[f],f'八维正式报告内部不一致：linear_result.{f}')
    req(recomputed['weight_config_sha256']==canonical_hash({'weights':ws.weights,'bias':ws.bias,'thresholds':ws.thresholds,'critical_axes':list(ws.critical_axes)}),'八维权重配置哈希不一致')
    return ex,recomputed

def compute(source,broad,probe_report,base_dir):
    src=Path(source); req(src.is_file(),'正文不存在'); raw=src.read_text(encoding='utf-8'); source_sha=sha_file(src); records=[]
    schema_validate(broad,base_dir/'广域审计输入_v1.0.2.schema.json','广域输入'); schema_validate(probe_report,base_dir/'八维正式报告_v3.2.1.schema.json','八维正式报告')
    req(Path(broad['元数据']['输入']).name==src.name,'广域输入文件名不匹配'); req(broad['元数据']['源文件SHA256']==source_sha,'广域正文哈希不匹配'); walk_evidence(broad,raw)
    probe_mod=load_probe_module(base_dir.parent/'01_八维探针程序'/'pseudo_linear_probe.py'); ex,linear=validate_probe_formal(probe_report,src,probe_mod)
    records.append(module_record('输入完整性',outputs=['Schema、版本、哈希、证据锚点、八维复算'],formulas=['SHA-256','Draft2020-12 Schema'],evidence_count=count_evidence(broad['硬闸门'])+sum(len(a['evidence']) for a in ex['axes'])+sum(len(g['evidence']) for g in ex['gates'])))
    auto=measure_source(src); manual_status=compare_manual(broad['直接测量'],auto); records.append(module_record('直接测量',outputs=list(auto),formulas=['正文自动计数'],evidence_count=0))
    req(broad['AI伪概率不确定度']['正文汉字数']==auto['正文汉字数'],'AI伪概率正文汉字数与自动测量不一致')
    blocker=[k for k,v in broad['硬闸门'].items() if not v['通过']]; records.append(module_record('四硬闸门',outputs=['失败项','状态'],formulas=['布尔硬闸门'],evidence_count=count_evidence(broad['硬闸门'])))
    chap={k:v['分数'] for k,v in broad['章级六维'].items()}; s_ch=sum(chap[k]*w for k,w in CHAPTER_WEIGHTS.items()); ch_state=chapter_state(blocker,s_ch,chap); records.append(module_record('章级六维',outputs=['综合值','状态'],formulas=['加权和+短板闸门'],evidence_count=count_evidence(broad['章级六维'])))
    lit={k:v['分数'] for k,v in broad['文学表现'].items()}; lv=list(lit.values()); lit_out={'六维':broad['文学表现'],'平均值':round(statistics.mean(lv),4),'最低项':min(lit,key=lit.get),'最低值':min(lv),'偏科标准差':round(statistics.pstdev(lv),4)}; records.append(module_record('文学表现',outputs=['平均值','最低项','偏科标准差'],formulas=['均值','最小值','标准差'],evidence_count=count_evidence(broad['文学表现'])))
    ai={k:v['分数'] for k,v in broad['AI味'].items()}; ai_r=statistics.mean([ai['模板重复'],ai['句法均质'],ai['套语过渡']]); ai_s=statistics.mean([ai['过度解释'],ai['通用抽象'],ai['语义复述']]); records.append(module_record('AI味',outputs=['AI_R','AI_S'],formulas=['双轴平均'],evidence_count=count_evidence(broad['AI味'])))
    sm={k:v['分数'] for k,v in broad['情节平滑化'].items()}; co=statistics.mean([sm['因果连续性'],sm['目标连续性'],sm['状态继承连续性']]); va=statistics.mean([sm['事件显著性差异'],sm['重新解释与意外'],sm['真实路径分叉'],sm['节拍不规则度']]); ps=co*(4-va)/4; records.append(module_record('情节平滑化',outputs=['Co','Va','Ps'],formulas=['Co×(4−Va)/4'],evidence_count=count_evidence(broad['情节平滑化'])))
    risks={k:v['分数'] for k,v in broad['九维风险'].items()}; records.append(module_record('九维风险',outputs=list(risks),formulas=['风险向量'],evidence_count=count_evidence(broad['九维风险'])))
    hev={k:v['分数'] for k,v in broad['AI参与反向证据'].items()}; a_pos=.28*ai_r+.28*ai_s+.16*risks['概率趋同']+.10*ps+.10*risks['留白不足']+.08*risks['肉身经验缺失']; h_neg=.40*hev['长程回收']+.30*hev['人物声纹']+.30*hev['功能性不对称']; p_ai=100/(1+math.exp(-1.4*(a_pos-h_neg-1.6))); u=broad['AI伪概率不确定度']; l=max(0,1-u['正文汉字数']/3000); width=max(12,min(35,12+12*u['评审分歧']+10*l+8*int(u['缺同类型基线'])+8*int(u['疑似深度人机混编']))); interval=[max(0,p_ai-width),min(100,p_ai+width)]; records.append(module_record('AI参与伪概率',outputs=['中心值','区间'],formulas=['C0 sigmoid伪概率'],evidence_count=count_evidence(broad['AI参与反向证据'])))
    records.append(module_record('八维探针',outputs=['复算activation','等级','覆盖率'],formulas=['八维正式报告复算'],evidence_count=sum(len(a['evidence']) for a in ex['axes'])))
    commercial=linear['commercial_gate_result']; records.append(module_record('商业六门',outputs=['门控状态','失败门','缺失门'],formulas=['八维唯一商业门控'],evidence_count=sum(len(g['evidence']) for g in ex['gates'])))
    priority=sorted(risks.items(),key=lambda x:x[1],reverse=True); high=[k for k,v in priority if v>=3]; level=linear['final_level']
    if blocker: decision='阻断：先修硬错误；八维结果仅作诊断材料'
    elif ch_state=='重写': decision='章级判断要求重写；八维高分只能保留为局部优势'
    elif ch_state=='定向修复': decision='章级判断未稳健通过；先修章级最低维度'
    elif level=='证据不足': decision='章级结构通过，但八维证据不足；不得输出商业通过'
    elif commercial['status']=='证据不足': decision='商业六门证据不足；不得输出商业通过'
    elif commercial['status']=='未通过': decision='商业六门未通过；八维activation不得补偿'
    elif high and level=='高': decision='结构与商业门通过，但广域高风险显著；先专项修复'
    elif level=='高': decision='章级结构与商业六门通过；进入表达层定向修复或发布前复核'
    elif level in {'低','很低'}: decision='章级结构通过，但追读执行强度低；重构商业执行路径'
    else: decision='章级结构和商业六门通过，商业执行中等；补强最低轴'
    records.append(module_record('联合裁决',outputs=['结论','优先级'],formulas=['固定优先级路由'],evidence_count=0))
    coverage={r['模块']:r['状态'] for r in records}
    return {'运行信息':{'联合审计器版本':VERSION,'schema_version':SCHEMA_VERSION,'源文件名':src.name,'源文件SHA256':source_sha,'广域输入SHA256':canonical_hash(broad),'八维正式报告文件SHA256':canonical_hash(probe_report),'八维脚本版本':PROBE_VERSION,'八维规则版本':PROBE_RUBRIC,'校准状态':'C0/uncalibrated'},'输入完整性':{'广域Schema':'通过','八维正式报告Schema':'通过','正文_广域_八维哈希':'一致','证据锚点':'通过','八维正式报告复算':'一致','直接测量人工交叉验证':manual_status},'模块执行记录':records,'功能覆盖':coverage,'直接测量':auto,'硬闸门':{'失败项':blocker,'状态':'通过' if not blocker else '阻断','详情':broad['硬闸门']},'章级判断':{'六维':broad['章级六维'],'综合值':round(s_ch,4),'状态':ch_state,'关键维度':CHAPTER_CRITICAL},'文学表现':lit_out,'AI味风险':{'表面规则化_AI_R':round(ai_r,4),'语义封闭化_AI_S':round(ai_s,4),'六项':broad['AI味'],'边界':'风格风险，不是作者身份概率'},'情节平滑化':{'连贯度_Co':round(co,4),'结构变化度_Va':round(va,4),'平滑化风险_Ps':round(ps,4),'七项':broad['情节平滑化'],'判定':'高连贯低变化' if co>=2.8 and va<2 else ('连贯且有变化' if co>=2.8 and va>=2 else '需检查混乱或低推进')},'九维风险向量':{'分数':risks,'详情':broad['九维风险']},'AI参与伪概率':{'A_pos':round(a_pos,4),'H_neg':round(h_neg,4),'中心值_P_AI星':round(p_ai,2),'不确定宽度_W':round(width,2),'区间':[round(interval[0],2),round(interval[1],2)],'反向证据':broad['AI参与反向证据'],'边界':'C0伪概率，仅用于内部版本比较，不进入放行'},'八维探针':{'正式报告身份':probe_report['run'],'复算线性结果':linear,'提取':ex},'商业六门':commercial,'联合裁决':{'结论':decision,'章级状态':ch_state,'商业门状态':commercial['status'],'广域风险优先级':priority,'禁止外推':['真实作者身份','爆款概率','签约率','真实留存','收入','平台推荐']}}

def render(r):
    L=['# 网文伪数学完整联合审计报告 v1.0.2','']
    for k,v in r['运行信息'].items(): L.append(f'- **{k}**：{v}')
    L += ['','## 0. 输入完整性','']
    for k,v in r['输入完整性'].items(): L.append(f'- {k}：{v}')
    L += ['','## 1. 模块执行记录','','| 模块 | 状态 | 公式 | 证据数 |','|---|---|---|---:|']
    for x in r['模块执行记录']: L.append(f"| {x['模块']} | {x['状态']} | {'；'.join(x['使用公式'])} | {x['证据数量']} |")
    L += ['','## 2. 直接测量','']+[f'- {k}：{v}' for k,v in r['直接测量'].items()]
    L += ['','## 3. 硬闸门','',f"状态：**{r['硬闸门']['状态']}**",'']
    for k,v in r['硬闸门']['详情'].items(): L.append(f"- {k}：{'通过' if v['通过'] else '失败'}；{evidence_text(v['证据'])}；{v['判定']}")
    def sec(title,d):
        L.extend(['',title,'','| 维度 | 分数 | 证据 | 判定 |','|---|---:|---|---|'])
        for k,v in d.items(): L.append(f"| {k} | {v['分数']:.2f} | {evidence_text(v['证据'])} | {v['判定']} |")
    sec('## 4. 章级六维',r['章级判断']['六维']); L.append(f"\n综合值：**{r['章级判断']['综合值']:.4f}**；状态：**{r['章级判断']['状态']}**")
    sec('## 5. 文学表现',r['文学表现']['六维']); L.append(f"\n平均值：{r['文学表现']['平均值']:.4f}；最低项：{r['文学表现']['最低项']}={r['文学表现']['最低值']:.2f}")
    sec('## 6. AI味风险',r['AI味风险']['六项']); L.append(f"\nAI_R={r['AI味风险']['表面规则化_AI_R']:.4f}；AI_S={r['AI味风险']['语义封闭化_AI_S']:.4f}")
    sec('## 7. 情节平滑化',r['情节平滑化']['七项']); L.append(f"\nCo={r['情节平滑化']['连贯度_Co']:.4f}；Va={r['情节平滑化']['结构变化度_Va']:.4f}；Ps={r['情节平滑化']['平滑化风险_Ps']:.4f}")
    sec('## 8. 九维风险',r['九维风险向量']['详情'])
    sec('## 9. AI参与反向证据',r['AI参与伪概率']['反向证据']); L.append(f"\n中心值：**{r['AI参与伪概率']['中心值_P_AI星']}%**；区间：{r['AI参与伪概率']['区间'][0]}%—{r['AI参与伪概率']['区间'][1]}%（C0未校准）")
    lr=r['八维探针']['复算线性结果']; ex=r['八维探针']['提取']; L += ['','## 10. 八维探针','',f"等级：**{lr['final_level']}**；activation：{lr['activation']:.4f}；覆盖率：{lr['coverage']:.1%}；权重覆盖率：{lr['weighted_coverage']:.1%}",'','### 八维向量','','| 维度 | 分数 | 置信度 | 贡献 | 证据 |','|---|---:|---:|---:|---|']
    for a in ex['axes']: L.append(f"| {a['axis']} | {a['score']} | {a['confidence']}% | {lr['contributions'][a['axis']]} | {'；'.join(a['evidence'])} |")
    L += ['','## 11. 商业六门','',f"门控状态：**{r['商业六门']['status']}**",'','| 门 | 分数 | 置信度 | 证据 |','|---|---:|---:|---|']
    for g in ex['gates']: L.append(f"| {g['gate']} | {g['score']} | {g['confidence']}% | {'；'.join(g['evidence'])} |")
    L += ['','## 12. 联合裁决','',f"**{r['联合裁决']['结论']}**",'', '风险优先级：']+[f'- {k}：{v:.2f}' for k,v in r['联合裁决']['广域风险优先级']]
    return '\n'.join(L)+'\n'

def self_test(base):
    sample=base/'测试样本'; src=sample/'第一章_第三扇门不能开.md'; broad0=load(sample/'第一章_广域审计_v1.0.2.json'); probe0=load(sample/'第一章_八维正式报告.json')
    r=compute(src,broad0,probe0,base); assert len(r['模块执行记录'])==12 and all(x['状态']=='COMPUTED' for x in r['模块执行记录'])
    cases=[]
    def bmut(fn): x=copy.deepcopy(broad0); fn(x); return x,probe0
    def pmut(fn): x=copy.deepcopy(probe0); fn(x); return broad0,x
    cases += [('广域哈希',*bmut(lambda x:x['元数据'].__setitem__('源文件SHA256','0'*64))),('布尔字符串',*bmut(lambda x:x['硬闸门']['因果闸门'].__setitem__('通过','false'))),('额外字段',*bmut(lambda x:x.__setitem__('未声明字段','x'))),('分数越界',*bmut(lambda x:x['AI味']['模板重复'].__setitem__('分数',5))),('字数小数',*bmut(lambda x:x['AI伪概率不确定度'].__setitem__('正文汉字数',1.5))),('分歧越界',*bmut(lambda x:x['AI伪概率不确定度'].__setitem__('评审分歧',1.5))),('证据文本伪造',*bmut(lambda x:x['章级六维']['理解成立度']['证据'][0]['锚点'][0].__setitem__('文本','不存在'))),('证据越界',*bmut(lambda x:x['章级六维']['理解成立度']['证据'][0]['锚点'][0].__setitem__('结束字符',999999))),('人工测量冲突',*bmut(lambda x:x['直接测量'].__setitem__('正文汉字数',1))),('八维版本',*pmut(lambda x:x['run'].__setitem__('version','0.0'))),('规则版本',*pmut(lambda x:x['run'].__setitem__('rubric_version','x'))),('八维哈希',*pmut(lambda x:x['run'].__setitem__('source_sha256','0'*64))),('activation篡改',*pmut(lambda x:x['linear_result'].__setitem__('activation',1.0))),('贡献篡改',*pmut(lambda x:x['linear_result']['contributions'].__setitem__('因果代价轴',9))),('覆盖率篡改',*pmut(lambda x:x['linear_result'].__setitem__('coverage',0))),('等级篡改',*pmut(lambda x:x['linear_result'].__setitem__('final_level','低'))),('权重篡改',*pmut(lambda x:x['linear_result']['weights'].__setitem__('因果代价轴',9))),('缺轴',*pmut(lambda x:x['extraction'].__setitem__('axes',x['extraction']['axes'][:-1]))),('商业门全零',*pmut(lambda x:[g.__setitem__('score',0) for g in x['extraction']['gates']])),('商业门缺失',*pmut(lambda x:x['extraction'].__setitem__('gates',x['extraction']['gates'][:-1]))),('报告额外字段',*pmut(lambda x:x.__setitem__('extra',1))),('八维提取哈希',*pmut(lambda x:x['extraction'].__setitem__('source_sha256','0'*64)))]
    failures=[]
    for name,b,p in cases:
        try: compute(src,b,p,base); failures.append(name)
        except (AuditError,SchemaValidationError,ValueError,KeyError,TypeError): pass
    if failures: raise AssertionError('负向测试未拒绝：'+','.join(failures))
    print(f'JOINT-AUDIT SELF-TEST PASS: 正向1项，负向{len(cases)}项，12模块动态执行')

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True); s=sub.add_parser('score'); s.add_argument('--source',required=True); s.add_argument('--broad',required=True); s.add_argument('--probe-report',required=True); s.add_argument('--output',required=True); m=sub.add_parser('measure'); m.add_argument('--source',required=True); m.add_argument('--output'); sub.add_parser('self-test'); a=ap.parse_args(); base=Path(__file__).resolve().parent
    try:
        if a.cmd=='score':
            r=compute(a.source,load(a.broad),load(a.probe_report),base); dump(a.output,r); Path(a.output).with_suffix('.md').write_text(render(r),encoding='utf-8'); print('JOINT-AUDIT PASS')
        elif a.cmd=='measure':
            r=measure_source(a.source); dump(a.output,r) if a.output else print(json.dumps(r,ensure_ascii=False,indent=2))
        else: self_test(base)
    except Exception as e: raise SystemExit('JOINT-AUDIT ERROR: '+str(e))
if __name__=='__main__': main()

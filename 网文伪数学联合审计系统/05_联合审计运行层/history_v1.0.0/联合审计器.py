#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""网文伪数学联合审计器 v1.0 CANDIDATE
读取广域审计JSON与八维探针摘要，计算章级、文学性、AI味、平滑化、九维风险、AI参与伪概率与联合裁决。
不调用API，不判断真实作者身份，不预测签约率/留存率/收入。
"""
from __future__ import annotations
import argparse, json, math, statistics
from pathlib import Path
from typing import Any

VERSION = "1.0.0-CANDIDATE"
CHAPTER_WEIGHTS = {"理解成立度":0.15,"因果推进度":0.20,"人物主动度":0.15,"情绪成立度":0.15,"当章回报度":0.20,"后续牵引度":0.15}
RISK_KEYS = ["叙事结构","文风语言","创意设定","角色心理","技术连续性","阅读体验","概率趋同","肉身经验缺失","留白不足"]

def clip(x, lo=0.0, hi=4.0): return max(lo, min(hi, float(x)))
def avg(vals):
    vals=[float(v) for v in vals if v is not None]
    return sum(vals)/len(vals) if vals else None

def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def dump(path,obj): Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def score_map(obj, expected):
    if set(obj) != set(expected): raise ValueError(f"字段不完整，应为：{expected}，实际：{list(obj)}")
    out={}
    for k,v in obj.items():
        if not isinstance(v,(int,float)) or not 0<=v<=4: raise ValueError(f"{k}必须为0—4")
        out[k]=float(v)
    return out

def compute(broad:dict[str,Any], probe:dict[str,Any])->dict[str,Any]:
    gates=broad['硬闸门']
    required_gates=['因果闸门','人物闸门','连续性闸门','视角闸门']
    if set(gates)!=set(required_gates): raise ValueError('硬闸门字段不完整')
    blocker=[k for k,v in gates.items() if not bool(v['通过'])]

    chap=score_map(broad['章级六维'], CHAPTER_WEIGHTS.keys())
    s_ch=sum(chap[k]*w for k,w in CHAPTER_WEIGHTS.items())

    lit_keys=['声音独特度','感知具体度','意义复层度','节律控制度','视角控制度','表达陌生度']
    lit=score_map(broad['文学表现'],lit_keys)
    lit_vals=list(lit.values())
    lit_avg=avg(lit_vals); lit_floor=min(lit_vals); lit_sd=statistics.pstdev(lit_vals)

    ai_keys=['模板重复','句法均质','过度解释','通用抽象','语义复述','套语过渡']
    ai=score_map(broad['AI味'],ai_keys)
    ai_r=avg([ai['模板重复'],ai['句法均质'],ai['套语过渡']])
    ai_s=avg([ai['过度解释'],ai['通用抽象'],ai['语义复述']])

    sm_keys=['因果连续性','目标连续性','状态继承连续性','事件显著性差异','重新解释与意外','真实路径分叉','节拍不规则度']
    sm=score_map(broad['情节平滑化'],sm_keys)
    co=avg([sm['因果连续性'],sm['目标连续性'],sm['状态继承连续性']])
    va=avg([sm['事件显著性差异'],sm['重新解释与意外'],sm['真实路径分叉'],sm['节拍不规则度']])
    ps=co*(4-va)/4

    risks=score_map(broad['九维风险'],RISK_KEYS)
    hev=score_map(broad['AI参与反向证据'],['长程回收','人物声纹','功能性不对称'])
    a_pos=(0.28*ai_r+0.28*ai_s+0.16*risks['概率趋同']+0.10*ps+0.10*risks['留白不足']+0.08*risks['肉身经验缺失'])
    h_neg=0.40*hev['长程回收']+0.30*hev['人物声纹']+0.30*hev['功能性不对称']
    p_ai=100/(1+math.exp(-1.4*(a_pos-h_neg-1.6)))
    unc=broad['AI伪概率不确定度']
    n_chars=int(unc['正文汉字数']); d_rater=float(unc['评审分歧']); b_missing=int(bool(unc['缺同类型基线'])); h_mix=int(bool(unc['疑似深度人机混编']))
    l_short=max(0,1-n_chars/3000)
    width=max(12,min(35,12+12*d_rater+10*l_short+8*b_missing+8*h_mix))
    p_interval=[max(0,p_ai-width),min(100,p_ai+width)]

    # 联合裁决
    broad_priority=sorted(risks.items(), key=lambda x:x[1], reverse=True)
    high=[k for k,v in broad_priority if v>=3]
    medium=[k for k,v in broad_priority if 2<=v<3]
    probe_level=probe['本章追读执行强度']
    if blocker:
        decision='阻断：先修硬错误；八维结果仅作诊断材料'
    elif high and probe_level=='高':
        decision='商业执行强但广域病灶显著：不得直接发布，先定向修复'
    elif not high and probe_level=='高':
        decision='结构与商业执行通过：进入表达层定向修复'
    elif probe_level=='低':
        decision='基础审计后仍缺追读发动机：重构核心执行路径'
    else:
        decision='证据或执行强度中等：补证据并定向修复最低项'

    return {
      '运行信息': {'联合审计器版本':VERSION,'输入':broad['元数据']['输入'],'输入类型':broad['元数据']['输入类型'],'广域提取端':broad['元数据']['提取端'],'八维提取端':probe.get('特征提取端','未知'),'校准状态':'C0/uncalibrated'},
      '直接测量': broad['直接测量'],
      '硬闸门': {'失败项':blocker,'状态':'通过' if not blocker else '阻断','详情':gates},
      '章级判断': {'六维':chap,'综合值':round(s_ch,4),'状态':'稳健通过' if not blocker and s_ch>=2.8 and min(chap.values())>=2 else ('阻断' if blocker else '定向修复')},
      '文学表现': {'六维':lit,'平均值':round(lit_avg,4),'最低项':min(lit,key=lit.get),'最低值':lit_floor,'偏科标准差':round(lit_sd,4)},
      'AI味风险': {'表面规则化_AI_R':round(ai_r,4),'语义封闭化_AI_S':round(ai_s,4),'六项':ai,'边界':'风格风险，不是作者身份概率'},
      '情节平滑化': {'连贯度_Co':round(co,4),'结构变化度_Va':round(va,4),'平滑化风险_Ps':round(ps,4),'七项':sm,'判定':'高连贯低变化' if co>=2.8 and va<2 else ('连贯且有变化' if co>=2.8 and va>=2 else '需检查混乱或低推进')},
      '九维风险向量': risks,
      'AI参与伪概率': {'A_pos':round(a_pos,4),'H_neg':round(h_neg,4),'中心值_P_AI星':round(p_ai,2),'不确定宽度_W':round(width,2),'区间':[round(p_interval[0],2),round(p_interval[1],2)],'纯AI直出倾向':'NA（无版本历史H_edit）','边界':'C0伪概率，仅用于内部复核与版本比较'},
      '八维探针': probe,
      '联合裁决': {'结论':decision,'广域风险优先级':broad_priority,'高风险':high,'中风险':medium,'禁止外推':['真实作者身份','爆款概率','签约率','真实留存','收入','平台推荐']},
      '功能覆盖': {'直接测量':True,'四硬闸门':True,'章级六维':True,'文学表现':True,'AI味':True,'情节平滑化':True,'九维风险':True,'AI参与伪概率':True,'八维探针':True,'商业六门':bool(probe.get('商业六门')),'联合裁决':True}
    }

def render(r):
    lines=['# 网文伪数学完整联合审计报告','']
    info=r['运行信息']
    for k,v in info.items(): lines.append(f'- **{k}**：{v}')
    lines += ['', '## 1. 功能覆盖', '', '| 模块 | 已执行 |','|---|---|']
    for k,v in r['功能覆盖'].items(): lines.append(f'| {k} | {"是" if v else "否"} |')
    lines += ['', '## 2. 直接测量','']
    for k,v in r['直接测量'].items(): lines.append(f'- {k}：{v}')
    lines += ['', '## 3. 硬闸门', '', f"状态：**{r['硬闸门']['状态']}**"]
    for k,v in r['硬闸门']['详情'].items(): lines.append(f"- {k}：{'通过' if v['通过'] else '失败'}；证据：{v['证据']}")
    lines += ['', '## 4. 章级六维', '', '| 维度 | 分数 |','|---|---:|']
    for k,v in r['章级判断']['六维'].items(): lines.append(f'| {k} | {v:.2f} |')
    lines += [f"\n综合值：**{r['章级判断']['综合值']:.4f}**；状态：**{r['章级判断']['状态']}**"]
    lines += ['', '## 5. 文学表现', '', '| 维度 | 分数 |','|---|---:|']
    for k,v in r['文学表现']['六维'].items(): lines.append(f'| {k} | {v:.2f} |')
    lines += [f"\n平均值：{r['文学表现']['平均值']:.4f}；最低项：{r['文学表现']['最低项']}={r['文学表现']['最低值']:.2f}；偏科标准差：{r['文学表现']['偏科标准差']:.4f}"]
    lines += ['', '## 6. AI味风险', '', f"表面规则化 AI_R：**{r['AI味风险']['表面规则化_AI_R']:.4f}**", f"语义封闭化 AI_S：**{r['AI味风险']['语义封闭化_AI_S']:.4f}**", '', '| 子项 | 风险 |','|---|---:|']
    for k,v in r['AI味风险']['六项'].items(): lines.append(f'| {k} | {v:.2f} |')
    lines += ['', '## 7. 情节平滑化', '', f"连贯度 Co：**{r['情节平滑化']['连贯度_Co']:.4f}**", f"结构变化度 Va：**{r['情节平滑化']['结构变化度_Va']:.4f}**", f"平滑化风险 Ps：**{r['情节平滑化']['平滑化风险_Ps']:.4f}**", f"判定：**{r['情节平滑化']['判定']}**"]
    lines += ['', '## 8. 九维风险向量', '', '| 模块 | 风险 |','|---|---:|']
    for k,v in sorted(r['九维风险向量'].items(),key=lambda x:x[1],reverse=True): lines.append(f'| {k} | {v:.2f} |')
    p=r['AI参与伪概率']
    lines += ['', '## 9. AI参与伪概率（C0）','', f"A_pos：{p['A_pos']}",f"H_neg：{p['H_neg']}",f"中心值：**{p['中心值_P_AI星']}%**",f"不确定区间：**{p['区间'][0]}%—{p['区间'][1]}%**",f"纯AI直出倾向：{p['纯AI直出倾向']}",f"边界：{p['边界']}"]
    pr=r['八维探针']
    lines += ['', '## 10. 八维探针与商业六门','',f"追读执行强度：**{pr['本章追读执行强度']}**",f"activation：**{pr['线性激活值']}**",f"特征覆盖率：{pr['特征覆盖率']}",f"权重覆盖率：{pr['权重覆盖率']}",'','### 八维向量','', '| 维度 | 分数 | 贡献 |','|---|---:|---:|']
    for x in pr['八维向量']: lines.append(f"| {x['维度']} | {x['分数']} | {x['贡献']} |")
    lines += ['','### 商业六门','', '| 门 | 分数 |','|---|---:|']
    for x in pr['商业六门']: lines.append(f"| {x['门']} | {x['分数']} |")
    lines += ['', '## 11. 联合裁决','',f"**{r['联合裁决']['结论']}**",'', '风险优先级：']
    for k,v in r['联合裁决']['广域风险优先级']: lines.append(f'- {k}：{v:.2f}')
    lines += ['', '禁止外推：' + '、'.join(r['联合裁决']['禁止外推'])]
    return '\n'.join(lines)+'\n'

def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('score'); s.add_argument('--broad',required=True); s.add_argument('--probe',required=True); s.add_argument('--output',required=True)
    sub.add_parser('self-test')
    a=ap.parse_args()
    if a.cmd=='score':
        r=compute(load(a.broad),load(a.probe)); dump(a.output,r); Path(a.output).with_suffix('.md').write_text(render(r),encoding='utf-8'); print('JOINT-AUDIT PASS')
    else:
        broad={'元数据':{'输入':'x','输入类型':'单章','提取端':'synthetic'},'直接测量':{},'硬闸门':{k:{'通过':True,'证据':'x'} for k in ['因果闸门','人物闸门','连续性闸门','视角闸门']},'章级六维':{k:2 for k in CHAPTER_WEIGHTS},'文学表现':{k:2 for k in ['声音独特度','感知具体度','意义复层度','节律控制度','视角控制度','表达陌生度']},'AI味':{k:2 for k in ['模板重复','句法均质','过度解释','通用抽象','语义复述','套语过渡']},'情节平滑化':{k:2 for k in ['因果连续性','目标连续性','状态继承连续性','事件显著性差异','重新解释与意外','真实路径分叉','节拍不规则度']},'九维风险':{k:2 for k in RISK_KEYS},'AI参与反向证据':{k:2 for k in ['长程回收','人物声纹','功能性不对称']},'AI伪概率不确定度':{'正文汉字数':3000,'评审分歧':0,'缺同类型基线':False,'疑似深度人机混编':False}}
        probe={'本章追读执行强度':'中','线性激活值':0.5,'特征覆盖率':'100%','权重覆盖率':'100%','八维向量':[],'商业六门':[]}
        r=compute(broad,probe)
        assert r['章级判断']['综合值']==2.0
        assert abs(r['AI味风险']['表面规则化_AI_R']-2)<1e-9
        assert abs(r['情节平滑化']['平滑化风险_Ps']-1)<1e-9
        assert all(r['功能覆盖'][k] for k in ['直接测量','四硬闸门','章级六维','文学表现','AI味','情节平滑化','九维风险','AI参与伪概率','八维探针','联合裁决'])
        print('JOINT-AUDIT SELF-TEST PASS')
if __name__=='__main__': main()

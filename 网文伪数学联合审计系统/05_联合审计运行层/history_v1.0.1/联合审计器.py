#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""网文伪数学联合审计器 v1.0.1 CANDIDATE

功能：
1. 从正文直接计算基础文本测量；
2. 严格校验广域审计与八维探针输入；
3. 用 SHA-256 绑定正文、广域输入和八维输入；
4. 保留章级、文学性、AI味、平滑化、九维风险、AI参与伪概率、八维探针、商业六门和联合裁决全部模块；
5. 不调用 API，不判断真实作者身份，不预测签约率、留存率或收入。
"""
from __future__ import annotations
import argparse, copy, hashlib, json, math, re, statistics, tempfile
from pathlib import Path
from typing import Any

VERSION = "1.0.1-CANDIDATE"
SCHEMA_VERSION = "1.0.1"
CHAPTER_WEIGHTS = {"理解成立度":0.15,"因果推进度":0.20,"人物主动度":0.15,"情绪成立度":0.15,"当章回报度":0.20,"后续牵引度":0.15}
CHAPTER_CRITICAL = ["理解成立度","因果推进度","人物主动度","当章回报度","后续牵引度"]
LIT_KEYS = ["声音独特度","感知具体度","意义复层度","节律控制度","视角控制度","表达陌生度"]
AI_KEYS = ["模板重复","句法均质","过度解释","通用抽象","语义复述","套语过渡"]
SM_KEYS = ["因果连续性","目标连续性","状态继承连续性","事件显著性差异","重新解释与意外","真实路径分叉","节拍不规则度"]
RISK_KEYS = ["叙事结构","文风语言","创意设定","角色心理","技术连续性","阅读体验","概率趋同","肉身经验缺失","留白不足"]
HEV_KEYS = ["长程回收","人物声纹","功能性不对称"]
GATE_KEYS = ["因果闸门","人物闸门","连续性闸门","视角闸门"]
AXIS_KEYS = ["因果代价轴","期待违背轴","极速流转轴","章尾钩子轴","活人冲突轴","侧面烘托轴","反差造梗轴","设定动作化轴"]
COMMERCIAL_GATE_KEYS = ["卖点识别门","情绪承诺门","开篇入口门","主角发动机门","最小兑现门","连载扩展门"]
PROBE_LEVELS = {"高","中","低","证据不足"}
INPUT_TYPES = {"单章","章节组","全书","single_chapter","chapter_group","full_book"}

class ValidationError(ValueError): pass

def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def dump(path,obj): Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
def sha256_file(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def require(cond: bool, msg: str):
    if not cond: raise ValidationError(msg)
def is_number(v): return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(float(v))
def number(v,name,lo=None,hi=None):
    require(is_number(v), f"{name}必须为有限数值")
    x=float(v)
    if lo is not None: require(x>=lo,f"{name}不得小于{lo}")
    if hi is not None: require(x<=hi,f"{name}不得大于{hi}")
    return x
def strict_bool(v,name):
    require(type(v) is bool, f"{name}必须是JSON布尔值true/false，不接受字符串或数字")
    return v
def nonempty_text(v,name):
    require(isinstance(v,str) and v.strip(),f"{name}必须是非空字符串")
    return v.strip()
def evidence_list(v,name):
    require(isinstance(v,list) and len(v)>=1,f"{name}必须是至少含1项的证据数组")
    out=[]
    for i,x in enumerate(v): out.append(nonempty_text(x,f"{name}[{i}]"))
    return out

def body_text(raw: str) -> str:
    lines=raw.splitlines(); start=0
    for i,line in enumerate(lines):
        if re.match(r"^#\s*第[一二三四五六七八九十百千万0-9]+章",line.strip()): start=i+1; break
    return "\n".join(lines[start:]).strip()

def measure_source(path: Path) -> dict[str,Any]:
    raw=path.read_text(encoding="utf-8")
    body=body_text(raw)
    paras=[x.strip() for x in body.splitlines() if x.strip() and not x.strip().startswith("#")]
    chinese=lambda s: re.findall(r"[\u4e00-\u9fff]",s)
    sentences=[]
    for para in paras:
        for part in re.split(r"(?<=[。！？!?；;])",para):
            part=part.strip()
            if chinese(part): sentences.append(part)
    lens=[len(chinese(s)) for s in sentences]
    para_lens=[len(chinese(p)) for p in paras]
    mean=sum(lens)/len(lens) if lens else 0.0
    cv=statistics.pstdev(lens)/mean if len(lens)>1 and mean else 0.0
    return {
        "正文汉字数":len(chinese(body)),
        "自然段数":len(paras),
        "有效句子数":len(sentences),
        "平均句长":round(mean,2),
        "句长中位数":round(statistics.median(lens),2) if lens else 0.0,
        "句长变异系数":round(cv,4),
        "8字以内短段占比":round(sum(x<=8 for x in para_lens)/len(para_lens),4) if para_lens else 0.0,
        "5字以内短段占比":round(sum(x<=5 for x in para_lens)/len(para_lens),4) if para_lens else 0.0,
    }

def parse_percent(v,name):
    if is_number(v):
        x=float(v)
        if x>1: x/=100
    elif isinstance(v,str) and v.strip().endswith("%"):
        
        try: x=float(v.strip()[:-1])/100
        except ValueError: raise ValidationError(f"{name}百分比格式错误")
    else: raise ValidationError(f"{name}必须是0—1数值或百分数字符串")
    require(0<=x<=1,f"{name}必须位于0—1")
    return x

def validate_scored_section(obj, expected, section):
    require(isinstance(obj,dict),f"{section}必须是对象")
    require(set(obj)==set(expected),f"{section}字段必须严格等于{expected}，实际为{list(obj)}")
    scores={}; details={}
    for k in expected:
        item=obj[k]
        require(isinstance(item,dict),f"{section}.{k}必须是对象，包含分数、证据、判定")
        require(set(item)>={"分数","证据","判定"},f"{section}.{k}缺少分数/证据/判定")
        s=number(item["分数"],f"{section}.{k}.分数",0,4)
        ev=evidence_list(item["证据"],f"{section}.{k}.证据")
        judge=nonempty_text(item["判定"],f"{section}.{k}.判定")
        scores[k]=s; details[k]={"分数":s,"证据":ev,"判定":judge}
    return scores,details

def validate_broad(broad,source:Path,source_sha:str):
    require(isinstance(broad,dict),"广域审计根节点必须是对象")
    require(broad.get("schema_version")==SCHEMA_VERSION,f"广域schema_version必须为{SCHEMA_VERSION}")
    meta=broad.get("元数据"); require(isinstance(meta,dict),"缺少元数据")
    for k in ["输入","输入类型","提取端","校准状态","源文件SHA256"]: nonempty_text(meta.get(k),f"元数据.{k}")
    require(meta["输入类型"] in INPUT_TYPES,"元数据.输入类型不在允许集合")
    require(Path(meta["输入"]).name==source.name,"广域元数据输入文件名与--source不一致")
    require(meta["源文件SHA256"]==source_sha,"广域源文件SHA256与正文不一致")
    gates=broad.get("硬闸门"); require(isinstance(gates,dict) and set(gates)==set(GATE_KEYS),"硬闸门字段不完整")
    gate_out={}
    for k in GATE_KEYS:
        item=gates[k]; require(isinstance(item,dict),f"{k}必须是对象")
        passed=strict_bool(item.get("通过"),f"{k}.通过")
        ev=evidence_list(item.get("证据"),f"{k}.证据")
        judge=nonempty_text(item.get("判定"),f"{k}.判定")
        gate_out[k]={"通过":passed,"证据":ev,"判定":judge}
    chap,chap_d=validate_scored_section(broad.get("章级六维"),CHAPTER_WEIGHTS.keys(),"章级六维")
    lit,lit_d=validate_scored_section(broad.get("文学表现"),LIT_KEYS,"文学表现")
    ai,ai_d=validate_scored_section(broad.get("AI味"),AI_KEYS,"AI味")
    sm,sm_d=validate_scored_section(broad.get("情节平滑化"),SM_KEYS,"情节平滑化")
    risks,risks_d=validate_scored_section(broad.get("九维风险"),RISK_KEYS,"九维风险")
    hev,hev_d=validate_scored_section(broad.get("AI参与反向证据"),HEV_KEYS,"AI参与反向证据")
    unc=broad.get("AI伪概率不确定度"); require(isinstance(unc,dict),"缺少AI伪概率不确定度")
    n_chars=int(number(unc.get("正文汉字数"),"AI伪概率不确定度.正文汉字数",1))
    d_rater=number(unc.get("评审分歧"),"AI伪概率不确定度.评审分歧",0,1)
    missing=strict_bool(unc.get("缺同类型基线"),"AI伪概率不确定度.缺同类型基线")
    mix=strict_bool(unc.get("疑似深度人机混编"),"AI伪概率不确定度.疑似深度人机混编")
    manual=broad.get("直接测量",{})
    require(isinstance(manual,dict),"直接测量必须是对象")
    return {"元数据":meta,"直接测量人工记录":manual,"硬闸门":gate_out,"章级六维":chap,"章级六维详情":chap_d,"文学表现":lit,"文学表现详情":lit_d,"AI味":ai,"AI味详情":ai_d,"情节平滑化":sm,"情节平滑化详情":sm_d,"九维风险":risks,"九维风险详情":risks_d,"AI参与反向证据":hev,"AI参与反向证据详情":hev_d,"不确定度":{"正文汉字数":n_chars,"评审分歧":d_rater,"缺同类型基线":missing,"疑似深度人机混编":mix}}

def validate_probe(probe,source:Path,source_sha:str):
    require(isinstance(probe,dict),"八维探针摘要根节点必须是对象")
    require(probe.get("schema_version")==SCHEMA_VERSION,f"八维摘要schema_version必须为{SCHEMA_VERSION}")
    require(Path(nonempty_text(probe.get("源文件名"),"源文件名")).name==source.name,"八维摘要源文件名与--source不一致")
    require(nonempty_text(probe.get("源文件SHA256"),"源文件SHA256")==source_sha,"八维摘要源文件SHA256与正文不一致")
    nonempty_text(probe.get("脚本版本"),"脚本版本"); nonempty_text(probe.get("规则版本"),"规则版本"); nonempty_text(probe.get("特征提取端"),"特征提取端")
    level=probe.get("本章追读执行强度"); require(level in PROBE_LEVELS,"本章追读执行强度非法")
    activation=number(probe.get("线性激活值"),"线性激活值",0,1)
    coverage=parse_percent(probe.get("特征覆盖率"),"特征覆盖率")
    weighted=parse_percent(probe.get("权重覆盖率"),"权重覆盖率")
    axes=probe.get("八维向量"); require(isinstance(axes,list) and len(axes)==8,"八维向量必须恰好8项")
    require([x.get("维度") for x in axes]==AXIS_KEYS,"八维向量顺序或名称不正确")
    norm_axes=[]
    for i,x in enumerate(axes):
        require(isinstance(x,dict),f"八维向量[{i}]必须是对象")
        score=number(x.get("分数"),f"八维向量[{i}].分数",0,4)
        conf=number(x.get("置信度"),f"八维向量[{i}].置信度",0,100)
        contrib=number(x.get("贡献"),f"八维向量[{i}].贡献",-10,10)
        ev=evidence_list(x.get("证据"),f"八维向量[{i}].证据")
        judge=nonempty_text(x.get("判断"),f"八维向量[{i}].判断")
        norm_axes.append({**x,"分数":score,"置信度":conf,"贡献":contrib,"证据":ev,"判断":judge})
    gates=probe.get("商业六门"); require(isinstance(gates,list) and len(gates)==6,"商业六门必须恰好6项")
    require([x.get("门") for x in gates]==COMMERCIAL_GATE_KEYS,"商业六门顺序或名称不正确")
    norm_gates=[]
    for i,x in enumerate(gates):
        score=number(x.get("分数"),f"商业六门[{i}].分数",0,4)
        conf=number(x.get("置信度"),f"商业六门[{i}].置信度",0,100)
        ev=evidence_list(x.get("证据"),f"商业六门[{i}].证据")
        judge=nonempty_text(x.get("判断"),f"商业六门[{i}].判断")
        norm_gates.append({**x,"分数":score,"置信度":conf,"证据":ev,"判断":judge})
    return {**probe,"线性激活值":activation,"特征覆盖率数值":coverage,"权重覆盖率数值":weighted,"八维向量":norm_axes,"商业六门":norm_gates}

def compare_manual_measurements(manual,auto):
    warnings=[]; hard=[]
    exact=["正文汉字数","自然段数","有效句子数"]
    for k in exact:
        if k in manual and int(manual[k])!=int(auto[k]): hard.append(f"{k}: 人工记录{manual[k]} != 自动测量{auto[k]}")
    tolerances={"平均句长":0.05,"句长变异系数":0.01}
    for k,tol in tolerances.items():
        if k in manual and abs(float(manual[k])-float(auto[k]))>tol: hard.append(f"{k}: 人工记录{manual[k]} != 自动测量{auto[k]}")
    if "8字以内短段占比" in manual:
        m=parse_percent(manual["8字以内短段占比"],"直接测量.8字以内短段占比")
        if abs(m-auto["8字以内短段占比"])>0.005: hard.append("8字以内短段占比与自动测量不一致")
    for k in manual:
        if k not in auto and k!="主要事件节点": warnings.append(f"人工记录字段未自动复算：{k}")
    if hard: raise ValidationError("直接测量与正文不一致："+"；".join(hard))
    return warnings

def chapter_state(blocker,s,chap):
    if blocker:return "阻断"
    if s<2.5:return "重写"
    if s<2.8 or any(chap[k]<2 for k in CHAPTER_CRITICAL):return "定向修复"
    return "稳健通过"

def compute(source_path:str,broad_raw:dict[str,Any],probe_raw:dict[str,Any])->dict[str,Any]:
    source=Path(source_path); require(source.is_file(),"正文文件不存在")
    source_sha=sha256_file(source)
    broad=validate_broad(broad_raw,source,source_sha)
    probe=validate_probe(probe_raw,source,source_sha)
    auto=measure_source(source)
    warnings=compare_manual_measurements(broad["直接测量人工记录"],auto)
    if "主要事件节点" in broad["直接测量人工记录"]: auto["主要事件节点_人工编码"]=int(number(broad["直接测量人工记录"]["主要事件节点"],"主要事件节点",0))
    if broad["不确定度"]["正文汉字数"]!=auto["正文汉字数"]: raise ValidationError("AI伪概率不确定度.正文汉字数与正文自动测量不一致")
    gates=broad["硬闸门"]; blocker=[k for k,v in gates.items() if not v["通过"]]
    chap=broad["章级六维"]; s_ch=sum(chap[k]*w for k,w in CHAPTER_WEIGHTS.items()); ch_state=chapter_state(blocker,s_ch,chap)
    lit=broad["文学表现"]; lit_vals=list(lit.values())
    lit_avg=sum(lit_vals)/len(lit_vals); lit_floor=min(lit_vals); lit_sd=statistics.pstdev(lit_vals)
    ai=broad["AI味"]; ai_r=statistics.mean([ai["模板重复"],ai["句法均质"],ai["套语过渡"]]); ai_s=statistics.mean([ai["过度解释"],ai["通用抽象"],ai["语义复述"]])
    sm=broad["情节平滑化"]; co=statistics.mean([sm["因果连续性"],sm["目标连续性"],sm["状态继承连续性"]]); va=statistics.mean([sm["事件显著性差异"],sm["重新解释与意外"],sm["真实路径分叉"],sm["节拍不规则度"]]); ps=co*(4-va)/4
    risks=broad["九维风险"]; hev=broad["AI参与反向证据"]
    a_pos=0.28*ai_r+0.28*ai_s+0.16*risks["概率趋同"]+0.10*ps+0.10*risks["留白不足"]+0.08*risks["肉身经验缺失"]
    h_neg=0.40*hev["长程回收"]+0.30*hev["人物声纹"]+0.30*hev["功能性不对称"]
    p_ai=100/(1+math.exp(-1.4*(a_pos-h_neg-1.6)))
    unc=broad["不确定度"]; l_short=max(0,1-unc["正文汉字数"]/3000); width=max(12,min(35,12+12*unc["评审分歧"]+10*l_short+8*int(unc["缺同类型基线"])+8*int(unc["疑似深度人机混编"]))); p_interval=[max(0,p_ai-width),min(100,p_ai+width)]
    priority=sorted(risks.items(),key=lambda x:x[1],reverse=True); high=[k for k,v in priority if v>=3]; medium=[k for k,v in priority if 2<=v<3]; level=probe["本章追读执行强度"]
    if blocker: decision="阻断：先修硬错误；八维结果仅作诊断材料"
    elif ch_state=="重写": decision="章级判断要求重写；八维高分只能保留为局部优势，不得宣布结构通过"
    elif ch_state=="定向修复": decision="章级判断未稳健通过；先修章级最低维度，再复核八维商业执行"
    elif level=="证据不足": decision="章级结构通过，但八维证据不足；补齐八维关键证据后再裁决"
    elif high and level=="高": decision="章级结构通过、商业执行强，但广域病灶显著；不得直接发布，先定向修复"
    elif not high and level=="高": decision="章级结构与商业执行通过；进入表达层定向修复或发布前复核"
    elif level=="低": decision="章级结构通过，但追读执行强度低；重构商业执行路径"
    else: decision="章级结构通过，商业执行中等；补强最低商业维度并复核"
    return {
      "运行信息":{"联合审计器版本":VERSION,"schema_version":SCHEMA_VERSION,"源文件名":source.name,"源文件SHA256":source_sha,"输入类型":broad["元数据"]["输入类型"],"广域提取端":broad["元数据"]["提取端"],"八维提取端":probe["特征提取端"],"校准状态":"C0/uncalibrated"},
      "输入完整性":{"正文_广域_八维哈希一致":True,"正文文件名一致":True,"广域Schema通过":True,"八维Schema通过":True,"直接测量一致":True,"警告":warnings},
      "直接测量":auto,
      "硬闸门":{"失败项":blocker,"状态":"通过" if not blocker else "阻断","详情":gates},
      "章级判断":{"六维":broad["章级六维详情"],"综合值":round(s_ch,4),"状态":ch_state,"关键维度":CHAPTER_CRITICAL},
      "文学表现":{"六维":broad["文学表现详情"],"平均值":round(lit_avg,4),"最低项":min(lit,key=lit.get),"最低值":lit_floor,"偏科标准差":round(lit_sd,4)},
      "AI味风险":{"表面规则化_AI_R":round(ai_r,4),"语义封闭化_AI_S":round(ai_s,4),"六项":broad["AI味详情"],"边界":"风格风险，不是作者身份概率"},
      "情节平滑化":{"连贯度_Co":round(co,4),"结构变化度_Va":round(va,4),"平滑化风险_Ps":round(ps,4),"七项":broad["情节平滑化详情"],"判定":"高连贯低变化" if co>=2.8 and va<2 else ("连贯且有变化" if co>=2.8 and va>=2 else "需检查混乱或低推进")},
      "九维风险向量":{"分数":risks,"详情":broad["九维风险详情"]},
      "AI参与伪概率":{"A_pos":round(a_pos,4),"H_neg":round(h_neg,4),"中心值_P_AI星":round(p_ai,2),"不确定宽度_W":round(width,2),"区间":[round(p_interval[0],2),round(p_interval[1],2)],"反向证据":broad["AI参与反向证据详情"],"纯AI直出倾向":"NA（无版本历史H_edit）","边界":"C0伪概率，仅用于内部复核与版本比较，不得用于身份定案"},
      "八维探针":probe,
      "联合裁决":{"结论":decision,"章级状态":ch_state,"广域风险优先级":priority,"高风险":high,"中风险":medium,"禁止外推":["真实作者身份","爆款概率","签约率","真实留存","收入","平台推荐"]},
      "功能覆盖":{"输入完整性":True,"直接测量":True,"四硬闸门":True,"章级六维":True,"文学表现":True,"AI味":True,"情节平滑化":True,"九维风险":True,"AI参与伪概率":True,"八维探针":True,"商业六门":True,"联合裁决":True}
    }

def row_details(lines,details):
    lines += ["| 维度 | 分数 | 证据 | 判定 |","|---|---:|---|---|"]
    for k,d in details.items(): lines.append(f"| {k} | {d['分数']:.2f} | {'；'.join(d['证据'])} | {d['判定']} |")

def render(r):
    lines=["# 网文伪数学完整联合审计报告",""]
    for k,v in r["运行信息"].items(): lines.append(f"- **{k}**：{v}")
    lines += ["","## 0. 输入完整性",""]
    for k,v in r["输入完整性"].items(): lines.append(f"- {k}：{v}")
    lines += ["","## 1. 功能覆盖","","| 模块 | 已执行 |","|---|---|"]
    for k,v in r["功能覆盖"].items(): lines.append(f"| {k} | {'是' if v else '否'} |")
    lines += ["","## 2. 直接测量",""]
    for k,v in r["直接测量"].items(): lines.append(f"- {k}：{v}")
    lines += ["","## 3. 硬闸门","",f"状态：**{r['硬闸门']['状态']}**","","| 闸门 | 结果 | 证据 | 判定 |","|---|---|---|---|"]
    for k,v in r["硬闸门"]["详情"].items(): lines.append(f"| {k} | {'通过' if v['通过'] else '失败'} | {'；'.join(v['证据'])} | {v['判定']} |")
    lines += ["","## 4. 章级六维",""]; row_details(lines,r["章级判断"]["六维"]); lines += [f"\n综合值：**{r['章级判断']['综合值']:.4f}**；状态：**{r['章级判断']['状态']}**"]
    lines += ["","## 5. 文学表现",""]; row_details(lines,r["文学表现"]["六维"]); lines += [f"\n平均值：{r['文学表现']['平均值']:.4f}；最低项：{r['文学表现']['最低项']}={r['文学表现']['最低值']:.2f}；偏科标准差：{r['文学表现']['偏科标准差']:.4f}"]
    lines += ["","## 6. AI味风险","",f"表面规则化 AI_R：**{r['AI味风险']['表面规则化_AI_R']:.4f}**",f"语义封闭化 AI_S：**{r['AI味风险']['语义封闭化_AI_S']:.4f}**",""]; row_details(lines,r["AI味风险"]["六项"])
    lines += ["","## 7. 情节平滑化","",f"连贯度 Co：**{r['情节平滑化']['连贯度_Co']:.4f}**",f"结构变化度 Va：**{r['情节平滑化']['结构变化度_Va']:.4f}**",f"平滑化风险 Ps：**{r['情节平滑化']['平滑化风险_Ps']:.4f}**",f"判定：**{r['情节平滑化']['判定']}**",""]; row_details(lines,r["情节平滑化"]["七项"])
    lines += ["","## 8. 九维风险向量",""]; row_details(lines,r["九维风险向量"]["详情"])
    p=r["AI参与伪概率"]; lines += ["","## 9. AI参与伪概率（C0）","",f"A_pos：{p['A_pos']}",f"H_neg：{p['H_neg']}",f"中心值：**{p['中心值_P_AI星']}%**",f"不确定区间：**{p['区间'][0]}%—{p['区间'][1]}%**",f"边界：{p['边界']}","","### 反向证据",""]; row_details(lines,p["反向证据"])
    pr=r["八维探针"]; lines += ["","## 10. 八维探针与商业六门","",f"追读执行强度：**{pr['本章追读执行强度']}**",f"activation：**{pr['线性激活值']}**",f"特征覆盖率：{pr['特征覆盖率']}",f"权重覆盖率：{pr['权重覆盖率']}","","### 八维向量","","| 维度 | 分数 | 置信度 | 贡献 | 证据 | 判断 |","|---|---:|---:|---:|---|---|"]
    for x in pr["八维向量"]: lines.append(f"| {x['维度']} | {x['分数']} | {x['置信度']:.0f}% | {x['贡献']:.4f} | {'；'.join(x['证据'])} | {x['判断']} |")
    lines += ["","### 商业六门","","| 门 | 分数 | 置信度 | 证据 | 判断 |","|---|---:|---:|---|---|"]
    for x in pr["商业六门"]: lines.append(f"| {x['门']} | {x['分数']} | {x['置信度']:.0f}% | {'；'.join(x['证据'])} | {x['判断']} |")
    lines += ["","## 11. 联合裁决","",f"**{r['联合裁决']['结论']}**","","风险优先级："]
    for k,v in r["联合裁决"]["广域风险优先级"]: lines.append(f"- {k}：{v:.2f}")
    lines += ["","禁止外推："+"、".join(r["联合裁决"]["禁止外推"])]
    return "\n".join(lines)+"\n"

def valid_synthetic(source:Path):
    h=sha256_file(source); auto=measure_source(source)
    def section(keys,val=2): return {k:{"分数":val,"证据":["合成测试证据"],"判定":"合成测试判断"} for k in keys}
    broad={"schema_version":SCHEMA_VERSION,"元数据":{"输入":source.name,"输入类型":"单章","提取端":"synthetic","校准状态":"C0","源文件SHA256":h},"直接测量":{"正文汉字数":auto["正文汉字数"],"自然段数":auto["自然段数"],"有效句子数":auto["有效句子数"],"平均句长":auto["平均句长"],"句长变异系数":auto["句长变异系数"],"8字以内短段占比":auto["8字以内短段占比"],"主要事件节点":1},"硬闸门":{k:{"通过":True,"证据":["合成测试证据"],"判定":"通过"} for k in GATE_KEYS},"章级六维":section(CHAPTER_WEIGHTS.keys()),"文学表现":section(LIT_KEYS),"AI味":section(AI_KEYS),"情节平滑化":section(SM_KEYS),"九维风险":section(RISK_KEYS),"AI参与反向证据":section(HEV_KEYS),"AI伪概率不确定度":{"正文汉字数":auto["正文汉字数"],"评审分歧":0,"缺同类型基线":False,"疑似深度人机混编":False}}
    axes=[]
    for k in AXIS_KEYS: axes.append({"维度":k,"分数":2,"置信度":80,"贡献":0.1,"证据":["合成测试证据"],"判断":"合成测试判断"})
    gates=[]
    for k in COMMERCIAL_GATE_KEYS: gates.append({"门":k,"分数":2,"置信度":80,"证据":["合成测试证据"],"判断":"合成测试判断"})
    probe={"schema_version":SCHEMA_VERSION,"源文件名":source.name,"源文件SHA256":h,"脚本版本":"3.2.1","规则版本":"八维伪线性探针-v3.2.1","特征提取端":"synthetic","本章追读执行强度":"中","线性激活值":0.5,"特征覆盖率":"100%","权重覆盖率":"100%","八维向量":axes,"商业六门":gates,"主要问题":"无"}
    return broad,probe

def expect_fail(fn,label):
    try: fn()
    except ValidationError: return
    raise AssertionError(label+"未被拒绝")

def self_test():
    with tempfile.TemporaryDirectory() as d:
        src=Path(d)/"测试章.md"; src.write_text("# 第一章 测试\n\n甲推门。\n\n乙后退。",encoding="utf-8")
        broad,probe=valid_synthetic(src)
        r=compute(str(src),broad,probe)
        assert r["章级判断"]["综合值"]==2.0
        assert r["章级判断"]["状态"]=="重写"
        assert "章级判断要求重写" in r["联合裁决"]["结论"]
        assert all(r["功能覆盖"].values())
        assert len(r["八维探针"]["商业六门"])==6
        b=copy.deepcopy(broad); b["硬闸门"]["因果闸门"]["通过"]="false"; expect_fail(lambda:compute(str(src),b,probe),"字符串false")
        b=copy.deepcopy(broad); b["元数据"]["源文件SHA256"]="0"*64; expect_fail(lambda:compute(str(src),b,probe),"广域哈希不匹配")
        p=copy.deepcopy(probe); p["源文件SHA256"]="0"*64; expect_fail(lambda:compute(str(src),broad,p),"八维哈希不匹配")
        p=copy.deepcopy(probe); p["线性激活值"]=99; expect_fail(lambda:compute(str(src),broad,p),"非法activation")
        p=copy.deepcopy(probe); p["本章追读执行强度"]="宇宙级"; expect_fail(lambda:compute(str(src),broad,p),"非法等级")
        p=copy.deepcopy(probe); p["商业六门"]=p["商业六门"][:-1]; expect_fail(lambda:compute(str(src),broad,p),"缺失商业门")
        b=copy.deepcopy(broad); b["章级六维"]["理解成立度"]["证据"]=[]; expect_fail(lambda:compute(str(src),b,probe),"缺少证据")
        b=copy.deepcopy(broad); b["直接测量"]["正文汉字数"]+=1; expect_fail(lambda:compute(str(src),b,probe),"测量不一致")
        src.write_text(src.read_text(encoding="utf-8")+"\n新增。",encoding="utf-8"); expect_fail(lambda:compute(str(src),broad,probe),"正文变化后旧输入")
    print("JOINT-AUDIT SELF-TEST PASS: 正向1项，负向9项，11个原有功能模块+输入完整性全部覆盖")

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    s=sub.add_parser("score"); s.add_argument("--source",required=True); s.add_argument("--broad",required=True); s.add_argument("--probe",required=True); s.add_argument("--output",required=True)
    m=sub.add_parser("measure"); m.add_argument("--source",required=True); m.add_argument("--output")
    sub.add_parser("self-test")
    a=ap.parse_args()
    try:
        if a.cmd=="score":
            r=compute(a.source,load(a.broad),load(a.probe)); dump(a.output,r); Path(a.output).with_suffix(".md").write_text(render(r),encoding="utf-8"); print("JOINT-AUDIT PASS")
        elif a.cmd=="measure":
            r=measure_source(Path(a.source));
            if a.output: dump(a.output,r)
            else: print(json.dumps(r,ensure_ascii=False,indent=2))
        else:self_test()
    except (ValidationError,KeyError,TypeError,ValueError) as e:
        raise SystemExit("JOINT-AUDIT ERROR: "+str(e))
if __name__=="__main__":main()

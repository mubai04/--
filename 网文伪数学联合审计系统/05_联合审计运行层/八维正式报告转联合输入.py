#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""八维正式报告绑定描述生成器。正式联合审计仍直接读取正式报告。"""
import argparse,hashlib,json
from pathlib import Path
ap=argparse.ArgumentParser(); ap.add_argument('--report',required=True); ap.add_argument('--output',required=True); a=ap.parse_args(); p=Path(a.report); o=json.loads(p.read_text(encoding='utf-8'))
out={'schema_version':'1.0.2','正式报告文件':p.name,'正式报告SHA256':hashlib.sha256(p.read_bytes()).hexdigest(),'源文件名':o['run']['source_name'],'源文件SHA256':o['run']['source_sha256'],'脚本版本':o['run']['version'],'规则版本':o['run']['rubric_version']}
Path(a.output).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')

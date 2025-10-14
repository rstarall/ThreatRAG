import re
import sys
from typing import Tuple, Dict, Any
import json
import time
import requests
import pandas as pd


CH_STOPWORDS = {
    "的", "了", "在", "是", "和", "与", "及", "或", "以及", "一个", "一次", "对于", "这种",
    "中", "中间", "相关", "进行", "主要", "主要是", "包括", "其中", "等", "共计", "还有", "有关",
    "问题", "回答", "问题是", "答案", "生成", "模型", "如果", "但", "但是", "并且", "以及",
}
EN_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "with", "for", "by", "at",
    "from", "as", "that", "this", "these", "those", "is", "are", "was", "were", "be", "been",
    "it", "its", "their", "there", "here", "into", "over", "under", "about", "without",
}


def extract_entities(text: str) -> Dict[str, set]:
    ips = set(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text))
    cves = set(re.findall(r"CVE-\d{4}-\d+", text, flags=re.IGNORECASE))
    nums = set(re.findall(r"\b\d{2,}\b", text))
    upper_terms = set([t for t in re.findall(
        r"\b[A-Z][A-Z0-9_\-]{2,}\b", text) if not t.startswith("CVE-")])
    return {"ip": ips, "cve": cves, "num": nums, "upper": upper_terms}


def normalize(text: str) -> str:
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._\-]", " ", text)
    return text.lower()


def tokenize(text: str) -> set:
    text = normalize(text)
    tokens = [t for t in text.split() if t]
    filtered = set(
        t for t in tokens
        if t not in EN_STOPWORDS and t not in CH_STOPWORDS and len(t) > 1
    )
    return filtered


def coverage_score(ground: str, generated: str) -> Tuple[float, Dict[str, Any]]:
    gt_tokens = tokenize(ground)
    gen_tokens = tokenize(generated)

    token_cov = (len(gt_tokens & gen_tokens) /
                 max(1, len(gt_tokens))) if gt_tokens else 0.0

    gt_entities = extract_entities(ground)
    gen_entities = extract_entities(generated)

    entity_scores = {}
    weights = {"ip": 0.4, "cve": 0.3, "num": 0.15, "upper": 0.15}
    ent_cov_total = 0.0
    for k, w in weights.items():
        gt_set = gt_entities.get(k, set())
        if not gt_set:
            s = 1.0
        else:
            inter = gt_set & gen_entities.get(k, set())
            s = len(inter) / max(1, len(gt_set))
        entity_scores[k] = s
        ent_cov_total += w * s

    score = 0.7 * token_cov + 0.3 * ent_cov_total
    details = {
        "token_coverage": round(token_cov, 4),
        "entity_coverage": {k: round(v, 4) for k, v in entity_scores.items()},
        "composite_score": round(score, 4),
    }
    return score, details


def evaluate_answer(original_query: str, ground_truth: str, generated: str) -> Dict[str, str]:
    score, details = coverage_score(ground_truth, generated)
    threshold = 0.8
    relevant = score >= threshold
    analysis = (
        f"词汇覆盖率{int(details['token_coverage']*100)}%，"
        f"实体覆盖综合{int((details['entity_coverage']['ip']*0.4 + details['entity_coverage']['cve']*0.3 + details['entity_coverage']['num']*0.15 + details['entity_coverage']['upper']*0.15)*100)}%，"
        f"综合得分{int(details['composite_score']*100)}%。"
        + ("关键信息覆盖基本完整，判定为相关。" if relevant else "核心要点覆盖不足，判定为不相关。")
    )
    return {"分析过程": analysis, "评判结果": "相关" if relevant else "不相关"}


def build_llm_prompt(original_query: str, ground_truth: str, generated: str) -> list:
    instruction = (
        "# 角色\n"
        "你是一名资深的AI问答（QA）系统评测专家。你的任务是精确、客观地评估由AI生成的答案是否与标准的正确答案（Ground Truth）高度相关。\n\n"
        "# 核心任务\n"
        "你需要对比一个“生成答案”和一个“标准答案”之间的语义相关性。根据以下量化标准，你必须给出一个最终的评判：如果“生成答案”包含了“标准答案”中超过80%的核心信息，则评判为“相关”，否则评判为“不相关”。\n\n"
        "# 输入\n"
        "对于每一次评测，你将收到三个部分：\n\n"
        "原始问题 (Original Query): 这是提出问题的上下文。\n\n"
        "标准答案 (Ground Truth Answer): 这是被认为是完全正确、标准的参考答案。\n\n"
        "生成答案 (Generated Answer): 这是由AI模型生成的、需要被评测的答案。\n\n"
        "# 评判标准：如何定义“80%相关性”\n\n"
        "这是一个关于信息覆盖率的语义判断，而不是简单的关键词匹配。请遵循以下准则：\n\n"
        "将被评判为“相关” (Judged as \"Relevant\") (相关性 > 80%) 的情况：\n\n"
        "核心信息完全匹配: “生成答案”必须准确无误地包含“标准答案”中的所有关键实体、事实和结论。\n\n"
        "允许次要信息缺失: “生成答案”可以省略“标准答案”中的一些补充性描述、举例或不那么重要的细节。\n\n"
        "允许表述方式不同: “生成答案”无需与“标准答案”使用完全相同的措辞，只要语义上保持一致即可。\n\n"
        "无严重事实错误: “生成答案”不能包含与“标准答案”相悖的严重事实性错误（幻觉）。\n\n"
        "将被评判为“不相关” (Judged as \"Irrelevant\") (相关性 < 80%) 的情况：\n\n"
        "核心信息缺失: “生成答案”遗漏了“标准答案”中的关键论点或主要事实。\n\n"
        "事实性矛盾: “生成答案”中包含与“标准答案”直接冲突的错误信息。\n\n"
        "回答了错误的问题: “生成答案”虽然内容可能正确，但没有针对“原始问题”进行回答，偏离了主题。\n\n"
        "过于模糊或无信息量: “生成答案”过于笼统，没有提供任何有价值的具体信息。\n\n"
        "# 工作流程\n\n"
        "仔细阅读 原始问题 以理解提问的意图。\n\n"
        "仔细阅读 标准答案 以掌握正确答案应包含的所有核心要点。\n\n"
        "仔细阅读 生成答案。\n\n"
        "基于上述“80%相关性”的评判标准，对比 生成答案 和 标准答案。\n\n"
        "在内心或草稿中进行简要的分析，说明你的判断依据。\n\n"
        "按照指定的输出格式，给出你的最终评判。\n\n"
        "# 输出格式\n"
        "你的输出必须包含以下两个部分：\n\n"
        "分析过程: [在这里用一两句话简要解释你的判断逻辑。例如：生成答案准确地指出了核心攻击手法和IP地址，只是缺少了具体的端口信息，符合大于80%相关的标准。]\n"
        "评判结果: [相关/不相关]\n\n"
        "# 示例\n\n"
        "示例 1:\n\n"
        "原始问题: 在1月6日的重点攻击中，IP 47.116.13.239 的主要攻击手法是什么？\n\n"
        "标准答案: 该IP主要利用了多种Web漏洞，包括网康安全网关文件读取和MetInfo SQL注入。其最常用的攻击载荷是“文件读取”，共计657次。此外，它还与“炫彩蛇黑客工具”和“VIPER”红队系统有关。\n\n"
        "生成答案: IP 47.116.13.239主要通过利用Web漏洞进行攻击，特别是文件读取和SQL注入。\n\n"
        "你的输出:\n\n"
        "分析过程: 生成答案准确地指出了“Web漏洞利用”、“文件读取”和“SQL注入”这几个核心攻击手法，覆盖了标准答案中的主要信息点。虽然它遗漏了工具名称等次要细节，但核心相关性超过80%。\n"
        "评判结果: 相关\n\n"
        "示例 2:\n\n"
        "原始问题: 攻击次数最多的历史IP是哪个？它来自哪里？\n\n"
        "标准答案: 攻击次数最多的历史IP是 107.172.21.17，共计28,834次攻击。该IP来自美国。\n\n"
        "生成答案: 攻击次数最多的IP进行了大量扫描活动，这些攻击通常来自海外。\n\n"
        "你的输出:\n\n"
        "分析过程: 生成答案虽然提到了“扫描”和“来自海外”，但完全遗漏了“107.172.21.17”这个最核心的IP地址信息，以及“美国”这个具体来源地。核心信息缺失，相关性远低于80%。\n"
        "评判结果: 不相关\n"
    )
    user_msg = (
        f"原始问题:\n{original_query}\n\n"
        f"标准答案:\n{ground_truth}\n\n"
        f"生成答案:\n{generated}\n\n"
        "请严格按照指定的输出格式，仅输出两行结果。"
    )
    return [
        {"role": "system", "content": instruction},
        {"role": "user", "content": user_msg},
    ]


def evaluate_with_llm(original: str, ground: str, generated: str,
                      model_provider: str = None, model_name: str = None) -> dict:
    from packages.models import select_model
    model = select_model(model_provider=model_provider, model_name=model_name)
    messages = build_llm_prompt(original, ground, generated)
    resp = model.predict(messages)
    text = resp.content.strip()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) >= 2:
        return {"分析过程": lines[0].replace("分析过程:", "").strip(),
                "评判结果": lines[1].replace("评判结果:", "").strip()}
    return {"分析过程": text, "评判结果": "不相关"}


def main():
    """命令行用法：
    1) 规则评测（本地）：
       python benchmark/query_test.py "<原始问题>" "<标准答案>" "<生成答案>"
    2) 大模型评测（GeminiPro/其他OpenAI兼容）：
       MODEL_PROVIDER=custom MODEL_NAME=gemini-1.5-pro \
       python benchmark/query_test.py --llm "<原始问题>" "<标准答案>" "<生成答案>"
    3) 批量评测（读取Excel并调用后端 /chat/stream）：
       MODEL_PROVIDER=custom MODEL_NAME=gemini-1.5-pro \
       python benchmark/query_test.py --batch --llm \
         --server http://localhost:8000 \
         --db kb_ffe24eeb \
         --dataset /home/lxp/workspace/ThreatRAG/benchmark/dataset.xlsx \
         --out /home/lxp/workspace/ThreatRAG/benchmark/result.csv
    未提供参数则运行内置示例。
    """
    import os
    use_llm = False
    args = sys.argv[1:]
    # 允许 --llm 出现在任意位置
    if "--llm" in args:
        use_llm = True
        args = [a for a in args if a != "--llm"]

    # 批量评测模式
    if "--batch" in args:
        args = [a for a in args if a != "--batch"]

        # 默认参数
        server = "http://localhost:8000"
        db_id = "kb_ffe24eeb"
        dataset_path = "/home/lxp/workspace/ThreatRAG/benchmark/dataset.xlsx"
        out_path = None

        # 简易解析
        i = 0
        while i < len(args):
            if args[i] == "--server" and i + 1 < len(args):
                server = args[i+1]
                i += 2
                continue
            if args[i] == "--db" and i + 1 < len(args):
                db_id = args[i+1]
                i += 2
                continue
            if args[i] == "--dataset" and i + 1 < len(args):
                dataset_path = args[i+1]
                i += 2
                continue
            if args[i] == "--out" and i + 1 < len(args):
                out_path = args[i+1]
                i += 2
                continue
            i += 1

        def call_chat_stream(query: str) -> str:
            url = server.rstrip("/") + "/chat/stream"
            payload = {
                "query": query,
                "meta": {"db_id": db_id, "show_retrieval_info": True},
                "history": []
            }
            headers = {"Content-Type": "application/json"}
            resp = requests.post(url, data=json.dumps(
                payload), headers=headers, stream=True, timeout=120)
            resp.raise_for_status()
            answer = []
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("status") == "loading" and obj.get("response"):
                    answer.append(obj["response"])
                elif obj.get("status") == "finished":
                    break
            return "".join(answer).strip()

        # 读取数据集
        df = pd.read_excel(dataset_path)
        query_col = next(
            (c for c in df.columns if c.lower().strip() in ("query", "question")), None)
        answer_col = next((c for c in df.columns if c.lower().strip() in (
            "answer", "ground truth", "ground_truth")), None)
        if not query_col or not answer_col:
            print("数据集必须包含 Query 与 Answer 列")
            return

        results = []
        correct = 0
        total = 0
        provider = os.getenv("MODEL_PROVIDER") or None
        name = os.getenv("MODEL_NAME") or None
        start_time = time.time()

        for idx, row in df.iterrows():
            q = str(row[query_col]).strip()
            gt = str(row[answer_col]).strip()
            if not q or not gt:
                continue
            try:
                pred = call_chat_stream(q)
            except Exception as e:
                pred = f"<调用失败: {e}>"
            judge = evaluate_with_llm(
                q, gt, pred, provider, name) if use_llm else evaluate_answer(q, gt, pred)
            is_rel = 1 if judge.get("评判结果") == "相关" else 0
            correct += is_rel
            total += 1
            results.append({
                "id": idx + 1,
                "query": q,
                "pred": pred,
                "gt": gt,
                "judge": judge.get("评判结果"),
                "analysis": judge.get("分析过程"),
                "is_correct": is_rel,
            })

        accuracy = (correct / total) if total else 0.0
        elapsed = time.time() - start_time
        print("评测完成：")
        print(f"样本数: {total}, 准确率(相关判定占比): {accuracy:.2%}, 用时: {elapsed:.1f}s")
        out_df = pd.DataFrame(results, columns=[
                              "id", "judge", "is_correct", "query", "pred", "gt", "analysis"])
        if out_path:
            out_df.to_csv(out_path, index=False)
            print(f"明细已保存: {out_path}")
        else:
            print(out_df[["id", "judge", "is_correct"]].head(
                10).to_string(index=False))
        return

    if "--batch" in args:
        # 批量模式强制使用LLM判分
        args = [a for a in args if a != "--batch"]
        # 默认参数
        server = "http://localhost:8000"
        db_id = "kb_ffe24eeb"
        dataset_path = "/home/lxp/workspace/ThreatRAG/benchmark/dataset.xlsx"
        out_path = None

        i = 0
        while i < len(args):
            if args[i] == "--server" and i + 1 < len(args):
                server = args[i+1]
                i += 2
                continue
            if args[i] == "--db" and i + 1 < len(args):
                db_id = args[i+1]
                i += 2
                continue
            if args[i] == "--dataset" and i + 1 < len(args):
                dataset_path = args[i+1]
                i += 2
                continue
            if args[i] == "--out" and i + 1 < len(args):
                out_path = args[i+1]
                i += 2
                continue
            i += 1

        import json
        import requests
        import pandas as pd
        import time
        import os

        def call_chat_stream(query: str) -> str:
            url = server.rstrip("/") + "/chat/stream"
            payload = {
                "query": query,
                "meta": {"db_id": db_id, "show_retrieval_info": True},
                "history": []
            }
            headers = {"Content-Type": "application/json"}
            resp = requests.post(url, data=json.dumps(
                payload), headers=headers, stream=True, timeout=120)
            resp.raise_for_status()
            answer = []
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("status") == "loading" and obj.get("response"):
                    answer.append(obj["response"])
                elif obj.get("status") == "finished":
                    break
            return "".join(answer).strip()

        df = pd.read_excel(dataset_path)
        query_col = next(
            (c for c in df.columns if c.lower().strip() in ("query", "question")), None)
        answer_col = next((c for c in df.columns if c.lower().strip() in (
            "answer", "ground truth", "ground_truth")), None)
        if not query_col or not answer_col:
            print("数据集必须包含 Query 与 Answer 列")
            return

        results = []
        correct = 0
        total = 0
        provider = os.getenv("MODEL_PROVIDER") or None
        name = os.getenv("MODEL_NAME") or None
        start_time = time.time()

        for idx, row in df.iterrows():
            q = str(row[query_col]).strip()
            gt = str(row[answer_col]).strip()
            if not q or not gt:
                continue
            try:
                pred = call_chat_stream(q)
            except Exception as e:
                pred = f"<调用失败: {e}>"
            judge = evaluate_with_llm(q, gt, pred, provider, name)
            is_rel = 1 if judge.get("评判结果") == "相关" else 0
            correct += is_rel
            total += 1
            results.append({
                "id": idx + 1,
                "query": q,
                "pred": pred,
                "gt": gt,
                "judge": judge.get("评判结果"),
                "analysis": judge.get("分析过程"),
                "is_correct": is_rel,
            })

        accuracy = (correct / total) if total else 0.0
        elapsed = time.time() - start_time
        print("评测完成：")
        print(f"样本数: {total}, 准确率(相关判定占比): {accuracy:.2%}, 用时: {elapsed:.1f}s")
        import pandas as pd
        out_df = pd.DataFrame(results, columns=[
                              "id", "judge", "is_correct", "query", "pred", "gt", "analysis"])
        if out_path:
            out_df.to_csv(out_path, index=False)
            print(f"明细已保存: {out_path}")
        else:
            print(out_df[["id", "judge", "is_correct"]].head(
                10).to_string(index=False))
        return

    if len(args) >= 3:
        original, ground, generated = args[0], args[1], args[2]
        provider = os.getenv("MODEL_PROVIDER") or None
        name = os.getenv("MODEL_NAME") or None
        res = evaluate_with_llm(original, ground, generated, provider, name)
        print(f"分析过程: {res['分析过程']}")
        print(f"评判结果: {res['评判结果']}")
    else:
        pass


if __name__ == "__main__":
    main()

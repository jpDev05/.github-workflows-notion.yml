import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from policy import load

GROQ_API_KEY = os.environ.get("GROQ_API_KEY","")
AI_PROVIDER = os.environ.get("AI_DEVOPS_PROVIDER","groq").lower()
AI_API_KEY = os.environ.get("AI_DEVOPS_API_KEY","")
AI_ENDPOINT = os.environ.get("AI_DEVOPS_ENDPOINT","https://api.openai.com/v1/chat/completions")
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPOSITORY = os.environ["REPOSITORY"]
PR_NUMBER = int(os.environ["PR_NUMBER"])
BASE_SHA = os.environ["BASE_SHA"]
HEAD_SHA = os.environ["HEAD_SHA"]
MERGE_SHA = os.environ.get("MERGE_SHA", HEAD_SHA)
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
POLICY=load()
REVIEW_POLICY=POLICY.get("review",{})
PR_POLICY=POLICY.get("pull_request",{})
REVIEW_EVENT=(os.environ.get("AI_DEVOPS_REVIEW_EVENT") or PR_POLICY.get("event","COMMENT")).upper()
MIN_SCORE = float(os.environ.get("AI_DEVOPS_MIN_SCORE") or REVIEW_POLICY.get("min_score",0))
FAIL_ON_HIGH_RISK = str(os.environ.get("AI_DEVOPS_FAIL_ON_HIGH_RISK") if os.environ.get("AI_DEVOPS_FAIL_ON_HIGH_RISK") not in (None,"") else REVIEW_POLICY.get("fail_on_high_risk",False)).lower()=="true"
MAX_INLINE = int(os.environ.get("AI_DEVOPS_MAX_INLINE_FINDINGS") or REVIEW_POLICY.get("max_inline_findings",8))

if REVIEW_EVENT not in {"COMMENT", "APPROVE", "REQUEST_CHANGES"}:
    raise RuntimeError("review-event deve ser COMMENT, APPROVE ou REQUEST_CHANGES.")


def git(*args):
    return subprocess.check_output(
        ["git", *args],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def read_file(path, limit=3500):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()[:limit]
    except OSError:
        return ""


def project_context():
    candidates = [
        "README.md",
        "package.json",
        "requirements.txt",
        "pyproject.toml",
        "pom.xml",
        "build.gradle",
        "go.mod",
        "Cargo.toml",
        "Dockerfile",
        "docker-compose.yml",
        "tsconfig.json",
    ]
    chunks = []
    for path in candidates:
        content = read_file(path)
        if content:
            chunks.append(f"===== {path} =====\n{content}")
    return "\n\n".join(chunks)[:4500]


SCHEMA = {
    "type": "object",
    "properties": {
        "resumo": {"type": "string"},
        "o_que_mudou": {"type": "string"},
        "impacto": {"type": "string"},
        "seguranca": {"type": "string"},
        "testes": {"type": "string"},
        "melhorias": {"type": "string"},
        "qualidade": {"type": "number"},
        "seguranca_nota": {"type": "number"},
        "manutenibilidade": {"type": "number"},
        "risco": {"type": "string", "enum": ["Baixo", "Médio", "Alto"]},
        "confianca": {"type": "number"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severidade": {
                        "type": "string",
                        "enum": ["Baixa", "Média", "Alta"],
                    },
                    "arquivo": {"type": "string"},
                    "linha": {"type": "integer"},
                    "titulo": {"type": "string"},
                    "problema": {"type": "string"},
                    "evidencia": {"type": "string"},
                    "sugestao": {"type": "string"},
                    "confianca": {"type": "number"},
                },
                "required": [
                    "severidade",
                    "arquivo",
                    "linha",
                    "titulo",
                    "problema",
                    "evidencia",
                    "sugestao",
                    "confianca",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "resumo",
        "o_que_mudou",
        "impacto",
        "seguranca",
        "testes",
        "melhorias",
        "qualidade",
        "seguranca_nota",
        "manutenibilidade",
        "risco",
        "confianca",
        "findings",
    ],
    "additionalProperties": False,
}


SYSTEM_PROMPT = """
Você é um principal engineer especializado em code review de pull requests.

PRINCÍPIO ABSOLUTO: EVIDÊNCIA ANTES DE OPINIÃO.

Analise somente o diff e o contexto fornecido. O objetivo é produzir uma
review profissional que um engenheiro sênior poderia publicar diretamente
em uma pull request.

NUNCA invente bugs, vulnerabilidades, testes executados, arquivos, linhas,
comportamento não demonstrado ou resultados de execução.

Um finding só pode existir quando o diff fornece evidência concreta de um
problema. Possibilidades hipotéticas devem permanecer fora de findings.

LINHAS:
- linha deve ser uma linha do lado RIGHT de uma alteração adicionada;
- use a linha real do arquivo;
- se não houver uma linha adicionada que sustente o finding, não crie o finding.

SEGURANÇA:
Priorize segredos expostos, autenticação/autorização, injeção, execução
arbitrária, validação de entrada, permissões, SSRF, XSS, SQL/command
injection, path traversal, desserialização insegura e configurações claramente
perigosas, mas somente quando houver evidência.

PYTHON:
{{ e }} podem ser escapes legítimos dentro de f-strings. Nunca trate isso
isoladamente como erro de sintaxe ou Jinja.

TESTES:
Diferencie testes observados no diff de testes recomendados. Nunca afirme
que um teste foi executado sem evidência.

NOTAS:
Avalie apenas a mudança desta PR. 0–10, sem notas artificiais.

RISCO:
Baixo = sem impacto perigoso evidente.
Médio = regressão ou impacto relevante é plausível e sustentado.
Alto = defeito grave, vulnerabilidade grave ou mudança crítica sustentada.

CONFIANÇA:
0.0–1.0 e proporcional à evidência.

Escreva em português do Brasil, seja objetivo e tecnicamente preciso.
"""


def groq(prompt):
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "reasoning_effort": "medium",
        "max_tokens": 3000,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "ai_devops_pr_review",
                "strict": True,
                "schema": SCHEMA,
            },
        },
    }

    request = urllib.request.Request(
        AI_ENDPOINT if AI_PROVIDER != "groq" else "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {AI_API_KEY_ACTIVE}",
            "Content-Type": "application/json",
            "User-Agent": "ai-devops-pr-review/2.0",
        },
    )

    for attempt in range(1, 4):
        try:
            print(f"🤖 PR Review → Groq | tentativa={attempt}/3")
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode())

            content = payload["choices"][0]["message"]["content"].strip()
            return json.loads(content)

        except urllib.error.HTTPError as error:
            details = error.read().decode(errors="replace")

            if error.code in {429, 500, 502, 503, 504} and attempt < 3:
                retry_after = error.headers.get("retry-after")
                try:
                    wait = max(5, int(float(retry_after))) + 2
                except (TypeError, ValueError):
                    wait = 22
                print(f"⚠️ Groq HTTP {error.code}; aguardando {wait}s.")
                time.sleep(wait)
                continue

            try:
                payload = json.loads(details)
                info = payload.get("error", {})
                failed = info.get("failed_generation")

                if (
                    error.code == 400
                    and info.get("code") == "json_validate_failed"
                ):
                    if isinstance(failed, str) and failed.strip():
                        try:
                            return json.loads(failed)
                        except json.JSONDecodeError:
                            pass

                    if attempt < 3:
                        wait = attempt * 3
                        print(
                            "⚠️ Groq rejeitou a saída estruturada sem "
                            f"geração recuperável; aguardando {wait}s e tentando novamente."
                        )
                        time.sleep(wait)
                        continue

            except (json.JSONDecodeError, TypeError, ValueError):
                pass

            raise RuntimeError(f"Groq API {error.code}: {details}")

        except (json.JSONDecodeError, KeyError, TypeError) as error:
            if attempt < 3:
                time.sleep(attempt * 2)
                continue
            raise RuntimeError(f"Review inválido: {error}")

    raise RuntimeError("Groq não retornou uma review válida.")


def changed_lines(diff_text):
    result = {}
    current_file = None
    new_line = None

    for raw in diff_text.splitlines():
        if raw.startswith("+++ b/"):
            current_file = raw[6:]
            result.setdefault(current_file, set())
            continue

        if raw.startswith("@@"):
            match = re.search(r"\+(\d+)(?:,(\d+))?", raw)
            if match:
                new_line = int(match.group(1))
            continue

        if current_file is None or new_line is None:
            continue

        if raw.startswith("+") and not raw.startswith("+++"):
            result.setdefault(current_file, set()).add(new_line)
            new_line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            continue
        else:
            new_line += 1

    return result


def normalize(review):
    def score(value):
        try:
            return max(0.0, min(10.0, float(value)))
        except (TypeError, ValueError):
            return 0.0

    def confidence(value):
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.0

    findings = review.get("findings")
    if not isinstance(findings, list):
        findings = []

    cleaned = []

    for item in findings[:20]:
        if not isinstance(item, dict):
            continue

        try:
            line = int(item.get("linha"))
        except (TypeError, ValueError):
            continue

        cleaned.append({
            "severidade": item.get("severidade", "Baixa"),
            "arquivo": str(item.get("arquivo", "")),
            "linha": line,
            "titulo": str(item.get("titulo", "Finding")),
            "problema": str(item.get("problema", "")),
            "evidencia": str(item.get("evidencia", "")),
            "sugestao": str(item.get("sugestao", "")),
            "confianca": confidence(item.get("confianca")),
        })

    review["findings"] = cleaned
    review["qualidade"] = score(review.get("qualidade"))
    review["seguranca_nota"] = score(review.get("seguranca_nota"))
    review["manutenibilidade"] = score(review.get("manutenibilidade"))
    review["confianca"] = confidence(review.get("confianca"))
    review["risco"] = (
        review.get("risco")
        if review.get("risco") in {"Baixo", "Médio", "Alto"}
        else "Médio"
    )
    return review


def github_api(method, path, body=None):
    url = f"https://api.github.com/{path}"
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode()

    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "X-GitHub-Api-Version": "2026-03-10",
            "Content-Type": "application/json",
            "User-Agent": "ai-devops-pr-review/2.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        details = error.read().decode(errors="replace")
        raise RuntimeError(f"GitHub API {error.code}: {details}")


def review_body(review, inline_count, skipped_count):
    lines = [
        "<!-- ai-devops-pr-review -->",
        "## 🤖 AI DevOps — Pull Request Review",
        "",
        f"**Qualidade:** {review['qualidade']:.1f}/10  ·  "
        f"**Segurança:** {review['seguranca_nota']:.1f}/10  ·  "
        f"**Manutenibilidade:** {review['manutenibilidade']:.1f}/10",
        "",
        f"**Risco:** {review['risco']}  ·  "
        f"**Confiança:** {review['confianca'] * 100:.0f}%",
        "",
        "### 🧠 Resumo",
        review.get("resumo", "Não informado."),
        "",
        "### 📌 O que mudou",
        review.get("o_que_mudou", "Não informado."),
        "",
        "### 🔐 Segurança",
        review.get("seguranca", "Não informado."),
        "",
        "### 🧪 Testes",
        review.get("testes", "Não informado."),
        "",
        "### 💡 Melhorias",
        review.get("melhorias", "Não informado."),
        "",
        f"📍 Findings inline publicados: **{inline_count}**",
        f"🗂️ Findings sem linha válida: **{skipped_count}**",
        "",
        "_Review gerada automaticamente pelo AI DevOps utilizando Groq._",
    ]
    return "\n".join(lines)


def main():
    print(f"🔎 Analisando PR #{PR_NUMBER}: {REPOSITORY}")

    diff = git("diff", "--no-ext-diff", "--unified=40", BASE_SHA, HEAD_SHA)

    if not diff:
        raise RuntimeError("O diff da pull request está vazio.")

    max_diff = 14000
    if len(diff) > max_diff:
        diff = diff[:max_diff] + "\n\n[DIFF TRUNCADO AUTOMATICAMENTE]\n"

    changed = changed_lines(diff)

    prompt = f"""
Analise esta pull request como um code review sênior.

REPOSITÓRIO:
{REPOSITORY}

PR:
#{PR_NUMBER}

BASE:
{BASE_SHA}

HEAD:
{HEAD_SHA}

CONTEXTO:
{project_context()}

DIFF:
{diff}

Regras adicionais:
1. Findings inline precisam apontar exclusivamente para linhas adicionadas.
2. O arquivo e a linha precisam existir no diff.
3. Se um problema não puder ser ancorado em uma linha adicionada, não o
   transforme em finding inline.
4. Não crie findings para preferências de estilo sem impacto técnico.
5. Prefira poucos findings fortes a muitos findings especulativos.
6. Retorne somente o JSON definido pelo schema.
"""

    review = normalize(groq(prompt))

    valid_findings = []
    skipped = 0

    for finding in review["findings"]:
        path = finding["arquivo"]
        line = finding["linha"]

        if (
            path in changed
            and line in changed[path]
            and finding["confianca"] >= 0.70
        ):
            valid_findings.append(finding)
        else:
            skipped += 1

    valid_findings = valid_findings[:MAX_INLINE]

    comments = []

    for finding in valid_findings:
        body = (
            f"### {finding['severidade']} — {finding['titulo']}\n\n"
            f"{finding['problema']}\n\n"
            f"**Evidência:** {finding['evidencia']}\n\n"
            f"**Sugestão:** {finding['sugestao']}\n\n"
            f"**Confiança:** {finding['confianca'] * 100:.0f}%"
        )

        comments.append({
            "path": finding["arquivo"],
            "line": finding["linha"],
            "side": "RIGHT",
            "body": body,
        })

    requested_event = REVIEW_EVENT

    if requested_event == "APPROVE":
        if (
            review["risco"] == "Alto"
            or any(f["severidade"] == "Alta" for f in review["findings"])
        ):
            print("⚠️ APPROVE bloqueado: existem findings de alto impacto.")
            requested_event = "COMMENT"

    quality_gate_failure = (
        FAIL_ON_HIGH_RISK and review["risco"] == "Alto"
    )

    if MIN_SCORE > 0:
        lowest = min(
            review["qualidade"],
            review["seguranca_nota"],
            review["manutenibilidade"],
        )
        if lowest < MIN_SCORE:
            quality_gate_failure = True

    body = review_body(review, len(comments), skipped)

    payload = {
        "commit_id": MERGE_SHA,
        "body": body,
        "event": requested_event,
        "comments": comments,
    }

    print(f"📝 Publicando review GitHub: {requested_event}")

    github_api(
        "POST",
        f"repos/{REPOSITORY}/pulls/{PR_NUMBER}/reviews",
        payload,
    )

    output = os.environ.get("GITHUB_OUTPUT")

    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(
                f"quality={review['qualidade']:.1f}\n"
                f"security={review['seguranca_nota']:.1f}\n"
                f"maintainability={review['manutenibilidade']:.1f}\n"
                f"risk={review['risco']}\n"
                f"confidence={review['confianca']:.2f}\n"
                f"review-event={requested_event}\n"
            )

    summary = os.environ.get("GITHUB_STEP_SUMMARY")

    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(body + "\n")

    if quality_gate_failure:
        print("❌ AI DevOps PR quality gate reprovado.")
        raise SystemExit(2)

    print("✅ AI DevOps PR review concluído.")


if __name__ == "__main__":
    main()
